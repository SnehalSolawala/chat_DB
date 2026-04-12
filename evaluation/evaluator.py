def evaluate_semantic_roles(predicted_output, ground_truth):
    correct = 0
    total = len(ground_truth)

    details = []

    for col in predicted_output["columns"]:
        col_name = col["name"]
        predicted_role = col["semantic_role"]

        expected_role = ground_truth.get(col_name)

        if expected_role:
            is_correct = predicted_role == expected_role

            details.append({
                "column": col_name,
                "predicted": predicted_role,
                "expected": expected_role,
                "correct": is_correct
            })

            if is_correct:
                correct += 1

    accuracy = correct / total if total > 0 else 0

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "details": details
    }