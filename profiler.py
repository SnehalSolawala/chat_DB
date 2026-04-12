import pandas as pd
from db import get_connection


def profile_table(table_name: str, session_id: str, sample_rows: int = 1000):
    conn = get_connection(session_id)

    query = f"SELECT * FROM `{table_name}` LIMIT {sample_rows}"
    df = pd.read_sql(query, conn)
    conn.close()

    profile: dict = {
        "table_name": table_name,
        "columns": [],
        "sample_values": {},
    }

    for col in df.columns:
        col_data = df[col]

        col_profile: dict = {
            "name": col,
            "type": str(col_data.dtype),
            "null_percent": float(col_data.isnull().mean() * 100),
            "distinct_count": int(col_data.nunique()),
        }

        if pd.api.types.is_numeric_dtype(col_data):
            col_profile.update(
                {
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "mean": float(col_data.mean()),
                }
            )

        profile["sample_values"][col] = col_data.dropna().astype(str).head(3).tolist()
        profile["columns"].append(col_profile)

    return profile
