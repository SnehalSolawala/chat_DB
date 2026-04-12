from evaluation.ground_truth import GROUND_TRUTH
from evaluation.evaluator import evaluate_semantic_roles

# Import your pipeline
from profiler import profile_table
from agent.enrichment_agent import ProfileEnrichmentAgent
from models.schema_models import ColumnStats, TableProfile, EnrichmentInput


def run():
    table_name = "transactions"

    # Step 1: Get raw profile
    raw_profile = profile_table(table_name)

    # Step 2: Convert to model
    columns = [ColumnStats(**col) for col in raw_profile["columns"]]

    table = TableProfile(
        table_name=raw_profile["table_name"],
        columns=columns,
        sample_values=raw_profile["sample_values"]
    )

    input_data = EnrichmentInput(
        table=table,
        domain_hint="payments"
    )

    # Step 3: Run AI Agent
    agent = ProfileEnrichmentAgent()
    result = agent.enrich(input_data)

    # Step 4: Evaluate
    gt = GROUND_TRUTH[table_name]
    evaluation_result = evaluate_semantic_roles(result, gt)

    print("\n==== AI OUTPUT ====\n")
    print(result)

    print("\n==== EVALUATION RESULT ====\n")
    print(evaluation_result)


if __name__ == "__main__":
    run()