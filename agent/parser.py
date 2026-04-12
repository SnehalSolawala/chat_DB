import json
import re

def clean_llm_output(output: str):
    # Remove ```json and ```
    output = re.sub(r"```json", "", output)
    output = re.sub(r"```", "", output)

    # Remove leading/trailing spaces
    output = output.strip()

    return output


def parse_output(output: str):
    try:
        cleaned = clean_llm_output(output)
        return json.loads(cleaned)
    except Exception as e:
        return {
            "error": "Invalid JSON",
            "raw": output,
            "exception": str(e)
        }