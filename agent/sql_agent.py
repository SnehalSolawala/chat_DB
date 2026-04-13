import re
from difflib import SequenceMatcher
from utils.llm_client import call_llm

# ──────────────────────────────────────────────────────────────
# Import DB functions directly — no HTTP round-trip, no cookie
# session lookup issues.
# ──────────────────────────────────────────────────────────────
from db import get_connection
import pandas as pd


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def clean_sql(sql: str) -> str:
    sql = re.sub(r"```sql|```", "", sql)
    return sql.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fetch_all_tables(session_id: str) -> list:
    """Fetch table list directly from DB — no HTTP, no cookie issues."""
    try:
        conn = get_connection(session_id)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"[fetch_all_tables] Found {len(tables)} tables: {tables}")
        return tables
    except ConnectionError as e:
        print(f"[fetch_all_tables] ConnectionError: {e}")
        raise
    except Exception as e:
        print(f"[fetch_all_tables] Error: {e}")
        return []


def pick_best_table(user_query: str, tables: list) -> str:
    query_lower = user_query.lower()
    query_words = set(re.findall(r"\w+", query_lower))

    best_table, best_score = None, -1

    for table in tables:
        tl = table.lower()
        score = 0

        # Exact word match
        if tl in query_words:
            score += 10

        # Prefix match
        for word in query_words:
            if tl.startswith(word) or word.startswith(tl):
                score += 8
                break

        # Fuzzy similarity
        for word in query_words:
            s = similarity(word, tl)
            if s > 0.7:
                score += s * 5

        # Substring match
        if tl in query_lower:
            score += 3

        # 4-char prefix match
        for word in query_words:
            if len(word) >= 4 and len(tl) >= 4 and word[:4] == tl[:4]:
                score += 4

        print(f"  Table '{table}' score: {score:.2f}")
        if score > best_score:
            best_score, best_table = score, table

    print(f"[pick_best_table] '{user_query}' → '{best_table}' (score={best_score:.2f})")
    return best_table


def fetch_schema(table_name: str, session_id: str) -> list:
    """Fetch schema directly from DB."""
    try:
        conn = get_connection(session_id)
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = [
            {
                "field": row[0],
                "type": row[1],
                "null": row[2],
                "key": row[3],
                "default": row[4],
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return columns
    except Exception as e:
        print(f"[fetch_schema] Error: {e}")
        return []


def fetch_preview(table_name: str, session_id: str, limit: int = 3) -> list:
    """Fetch sample rows directly from DB."""
    try:
        conn = get_connection(session_id)
        df = pd.read_sql(f"SELECT * FROM `{table_name}` LIMIT {limit}", conn)
        conn.close()
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"[fetch_preview] Error: {e}")
        return []


def build_sql_prompt(
    user_query: str, table_name: str, schema: list, preview: list
) -> str:
    col_lines = "\n".join(
        f"  - {col['field']}  ({col['type']})"
        + (" [PK]" if col.get("key") == "PRI" else "")
        + (" [FK]" if col.get("key") == "MUL" else "")
        for col in schema
    )

    preview_lines = ""
    if preview:
        preview_lines = "\nSample rows (first 3):\n"
        for row in preview:
            preview_lines += (
                "  " + ", ".join(f"{k}={v}" for k, v in row.items()) + "\n"
            )

    return f"""You are an expert MySQL query writer.

The user is asking about the table: `{table_name}`

Table schema:
{col_lines}
{preview_lines}
User question: "{user_query}"

Write a single valid MySQL SELECT query that answers the question.
Use ONLY the column names listed above — do NOT invent columns.
Return ONLY the raw SQL — no markdown, no explanation, no backticks.
"""


# ──────────────────────────────────────────────────────────────
# Main entry point (called by /ask with session_id)
# ──────────────────────────────────────────────────────────────
def generate_sql(user_query: str, session_id: str) -> str:
    # Step 1: Get tables directly from DB (no HTTP, no cookie)
    tables = fetch_all_tables(session_id)
    print(f"[generate_sql] Available tables: {tables}")

    if not tables:
        raise Exception("No tables found. Is the database connected?")

    # Step 2: Pick best matching table
    table_name = pick_best_table(user_query, tables)
    if not table_name:
        raise Exception("Could not determine which table to query.")

    # Step 3: Get schema directly from DB
    schema = fetch_schema(table_name, session_id)
    print(f"[generate_sql] Columns in '{table_name}': {[c['field'] for c in schema]}")

    if not schema:
        raise Exception(f"Could not fetch schema for table '{table_name}'.")

    # Step 4: Get preview rows directly from DB
    preview = fetch_preview(table_name, session_id)

    # Step 5: Build prompt and call LLM
    prompt = build_sql_prompt(user_query, table_name, schema, preview)
    raw_sql = call_llm(prompt)
    final_sql = clean_sql(raw_sql)
    print(f"[generate_sql] Final SQL: {final_sql}")

    # Step 6: Safety check
    unsafe = ["drop", "delete", "truncate", "alter", "insert", "update"]
    if any(kw in final_sql.lower() for kw in unsafe):
        raise Exception(f"Unsafe SQL detected: {final_sql}")

    return final_sql
