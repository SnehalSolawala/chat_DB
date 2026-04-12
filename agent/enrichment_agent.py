from agent.prompt_builder import build_prompt
from utils.llm_client import call_llm
from agent.parser import parse_output

class ProfileEnrichmentAgent:

    def enrich(self, data):
        prompt = build_prompt(data)
        llm_output = call_llm(prompt)
        return parse_output(llm_output)