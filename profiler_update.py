import pandas as pd
from db import get_connection


def profile_table(table_name: str, session_id: str, large_table_threshold: int = 100_000):
    """
    Profiles a table:
    - Small tables (< threshold): full scan via pandas.
    - Large tables (>= threshold): SQL aggregates only (no full data load).
    """
    conn = get_connection(session_id)

    total_rows = pd.read_sql(
        f"SELECT COUNT(*) as total_rows FROM `{table_name}`", conn
    ).iloc[0]["total_rows"]

    profile: dict = {
        "table_name": table_name,
        "columns": [],
        "sample_values": {},
    }

    if total_rows <= large_table_threshold:
        df = pd.read_sql(f"SELECT * FROM `{table_name}`", conn)

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

    else:
        cols_df = pd.read_sql(f"SELECT * FROM `{table_name}` LIMIT 1", conn)
        agg_parts = []
        for col in cols_df.columns:
            agg_parts.append(
                f"MIN(`{col}`) AS `{col}_min`, "
                f"MAX(`{col}`) AS `{col}_max`, "
                f"AVG(`{col}`) AS `{col}_mean`, "
                f"COUNT(DISTINCT `{col}`) AS `{col}_distinct`, "
                f"SUM(CASE WHEN `{col}` IS NULL THEN 1 ELSE 0 END) AS `{col}_nulls`"
            )
        agg_query = f"SELECT {', '.join(agg_parts)} FROM `{table_name}`"
        df_stats = pd.read_sql(agg_query, conn)

        for col in cols_df.columns:
            col_profile = {
                "name": col,
                "type": str(cols_df[col].dtype),
                "null_percent": float(
                    df_stats[f"{col}_nulls"].iloc[0] / total_rows * 100
                ),
                "distinct_count": int(df_stats[f"{col}_distinct"].iloc[0]),
            }
            if pd.api.types.is_numeric_dtype(cols_df[col]):
                col_profile.update(
                    {
                        "min": float(df_stats[f"{col}_min"].iloc[0]),
                        "max": float(df_stats[f"{col}_max"].iloc[0]),
                        "mean": float(df_stats[f"{col}_mean"].iloc[0]),
                    }
                )
            profile["sample_values"][col] = []
            profile["columns"].append(col_profile)

    conn.close()
    return profile
