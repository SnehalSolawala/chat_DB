def build_prompt(data):
    table = data.table

    prompt = f"""
You are a data expert AI agent.

Your task is to analyze table metadata and provide business-friendly insights.

Table: {table.table_name}
Domain: {data.domain_hint}

Columns:
"""

    for col in table.columns:
        samples = table.sample_values.get(col.name, [])
        prompt += f"""
- {col.name}
  type: {col.type}
  null%: {col.null_percent}
  distinct: {col.distinct_count}
  samples: {samples}
"""

    prompt += """

Instructions:
- Classify each column into one of: dimension, measure, time, id
- If column name contains "id", treat it as "id" (even if repeated)
- Generate business-friendly column names
- Identify data quality issues (nulls, skew, no null values, etc.) Never skip this section

Join Recommendations (MANDATORY):
- ALWAYS analyze columns for potential joins
- If ANY column contains "id" or looks like a key, you MUST suggest at least one join
- If no clear join exists, return an empty list [] explicitly
- Never skip this section

Return STRICT JSON ONLY (no markdown, no explanation):

{
  "table_description": "",
  "columns": [
    {
      "name": "",
      "semantic_role": "dimension | measure | time | id",
      "business_name": ""
    }
  ],
  "data_quality_notes": [],
  "recommended_joins": [
    {
      "table": "",
      "on": "",
      "reason": ""
    }
  ]
}
"""

    return prompt


"""
Join Recommendations:
- If a column looks like a foreign key (e.g., *_id), suggest joins
- Assume realistic table names (e.g., customer_id → customers table)
- Explain WHY the join is useful and WHAT data it provides
"""