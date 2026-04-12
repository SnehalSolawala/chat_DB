import pandas as pd
import math
from db import get_connection


def sanitize(value):
    """Convert NaN / Inf / -Inf → None so JSON never fails."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def execute_sql(sql: str, session_id: str):
    try:
        conn = get_connection(session_id)
        df = pd.read_sql(sql, conn)
        conn.close()
        records = df.where(pd.notnull(df), None).to_dict(orient="records")
        return [{k: sanitize(v) for k, v in row.items()} for row in records]
    except Exception as e:
        return {"error": str(e)}
