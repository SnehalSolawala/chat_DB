'''import requests
import json
import re
from utils.llm_client import call_llm_with_tools

BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# CLEAN SQL
# =========================================================
def clean_sql(sql: str) -> str:
    sql = re.sub(r"```sql|```", "", sql)
    return sql.strip()


# =========================================================
# Fetch MCP tool definitions + add list_db_tables tool
# =========================================================
def get_tools():
    res = requests.get(f"{BASE_URL}/mcp/tools")
    mcp_tools = res.json()["tools"]

    openai_tools = []
    for tool in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        })

    # ✅ NEW TOOL: list actual tables from the connected database
    openai_tools.append({
        "type": "function",
        "function": {
            "name": "list_db_tables",
            "description": (
                "Lists ALL tables currently available in the connected database. "
                "Always call this FIRST to discover which table matches the user's question."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })

    # ✅ NEW TOOL: get table schema (column names + types) without full profiling
    openai_tools.append({
        "type": "function",
        "function": {
            "name": "get_table_schema",
            "description": (
                "Returns the column names and types for a specific table. "
                "Use this to quickly check schema before writing SQL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "The exact table name"}
                },
                "required": ["table_name"]
            }
        }
    })

    return openai_tools


# =========================================================
# Call MCP tools + new DB tools
# =========================================================
def call_tool(name, arguments):
    try:
        if name == "list_db_tables":
            res = requests.get(f"{BASE_URL}/tables")
            return res.json()

        elif name == "get_table_schema":
            table = arguments.get("table_name", "")
            res = requests.get(f"{BASE_URL}/tables/{table}/schema")
            return res.json()

        elif name == "profile_table":
            return requests.post(
                f"{BASE_URL}/mcp/tools/profile_table",
                json=arguments
            ).json()

        elif name == "get_profile":
            return requests.get(
                f"{BASE_URL}/mcp/tools/get_profile",
                params=arguments
            ).json()

        elif name == "list_profiles":
            return requests.get(
                f"{BASE_URL}/mcp/tools/list_profiles",
                params=arguments
            ).json()

    except Exception as e:
        return {"error": str(e)}

    return {}


# =========================================================
# MAIN SQL GENERATOR
# =========================================================
def generate_sql(user_query):

    tools = get_tools()

    messages = [
        {
            "role": "system",
            "content": """
You are an expert SQL generator for a MySQL database.

## STRICT PROCESS — follow this order every time:

### STEP 1 — Discover tables
Call `list_db_tables` to get ALL tables in the database.
Read the list carefully and pick the table whose name best matches the user's question.
- "employees" / "staff" / "workers"  → employees table
- "customers" / "clients" / "buyers" → customers table
- "orders" / "sales" / "purchases"   → orders table
- "housing" / "property" / "house"   → housing table
Never guess — always match the user intent to the actual table name returned.

### STEP 2 — Get schema for the CORRECT table
Call `get_table_schema` with the table you identified in Step 1.
This gives exact column names — use them as-is in your SQL.

### STEP 3 — Write SQL
Using ONLY the column names from Step 2, write the SQL query.

## RULES:
- NEVER reuse a cached profile from a previous query.
- NEVER assume which table to use without calling list_db_tables first.
- NEVER invent column names — use only what get_table_schema returns.
- Return ONLY raw SQL — no markdown, no explanation, no backticks.
- If the user's question references people (names, employees, customers), check the table name in Step 1 carefully before proceeding.
"""
        },
        {
            "role": "user",
            "content": user_query
        }
    ]

    msg = call_llm_with_tools(messages, tools)
    print("Initial LLM Response:", msg)

    MAX_TOOL_CALLS = 6
    tool_call_count = 0

    while hasattr(msg, "tool_calls") and msg.tool_calls:

        tool_call_count += 1
        if tool_call_count > MAX_TOOL_CALLS:
            print("⚠️ Max tool calls reached, stopping loop")
            break

        for tool_call in msg.tool_calls:
            name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)
            except:
                args = {}

            print(f"\nCalling Tool: {name} with args: {args}")
            tool_result = call_tool(name, args)
            print("Tool Result:", tool_result)

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args)
                        }
                    }
                ]
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })

        msg = call_llm_with_tools(messages, tools)
        print("Next LLM Response:", msg)

    final_sql = clean_sql(msg.content or "")
    print("FINAL CLEAN SQL:", final_sql)

    unsafe_keywords = ["drop", "delete", "truncate", "alter"]
    if any(word in final_sql.lower() for word in unsafe_keywords):
        raise Exception("Unsafe SQL detected")

    return final_sql '''
import requests
import re
from difflib import SequenceMatcher
from utils.llm_client import call_llm

BASE_URL = "http://127.0.0.1:8000"


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def clean_sql(sql: str) -> str:
    sql = re.sub(r"```sql|```", "", sql)
    return sql.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fetch_all_tables(session_id: str) -> list:
    try:
        res = requests.get(
            f"{BASE_URL}/tables",
            cookies={"chatsql_session": session_id},
            timeout=5,
        )
        return res.json().get("tables", [])
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
        if tl in query_words:
            score += 10
        for word in query_words:
            if tl.startswith(word) or word.startswith(tl):
                score += 8
                break
        for word in query_words:
            s = similarity(word, tl)
            if s > 0.7:
                score += s * 5
        if tl in query_lower:
            score += 3
        for word in query_words:
            if len(word) >= 4 and len(tl) >= 4 and word[:4] == tl[:4]:
                score += 4

        print(f"  Table '{table}' score: {score:.2f}")
        if score > best_score:
            best_score, best_table = score, table

    print(f"[pick_best_table] '{user_query}' → '{best_table}' (score={best_score:.2f})")
    return best_table


def fetch_schema(table_name: str, session_id: str) -> list:
    try:
        res = requests.get(
            f"{BASE_URL}/tables/{table_name}/schema",
            cookies={"chatsql_session": session_id},
            timeout=5,
        )
        return res.json().get("schema", [])
    except Exception as e:
        print(f"[fetch_schema] Error: {e}")
        return []


def fetch_preview(table_name: str, session_id: str, limit: int = 3) -> list:
    try:
        res = requests.get(
            f"{BASE_URL}/tables/{table_name}/preview",
            params={"limit": limit},
            cookies={"chatsql_session": session_id},
            timeout=5,
        )
        return res.json().get("rows", [])
    except Exception as e:
        print(f"[fetch_preview] Error: {e}")
        return []


def build_sql_prompt(user_query: str, table_name: str, schema: list, preview: list) -> str:
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
            preview_lines += "  " + ", ".join(f"{k}={v}" for k, v in row.items()) + "\n"

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
    tables = fetch_all_tables(session_id)
    print(f"[generate_sql] Available tables: {tables}")

    if not tables:
        raise Exception("No tables found. Is the database connected?")

    table_name = pick_best_table(user_query, tables)
    if not table_name:
        raise Exception("Could not determine which table to query.")

    schema = fetch_schema(table_name, session_id)
    print(f"[generate_sql] Columns in '{table_name}': {[c['field'] for c in schema]}")

    if not schema:
        raise Exception(f"Could not fetch schema for table '{table_name}'.")

    preview = fetch_preview(table_name, session_id)
    prompt = build_sql_prompt(user_query, table_name, schema, preview)
    raw_sql = call_llm(prompt)
    final_sql = clean_sql(raw_sql)
    print(f"[generate_sql] Final SQL: {final_sql}")

    unsafe = ["drop", "delete", "truncate", "alter", "insert", "update"]
    if any(kw in final_sql.lower() for kw in unsafe):
        raise Exception(f"Unsafe SQL detected: {final_sql}")

    return final_sql
