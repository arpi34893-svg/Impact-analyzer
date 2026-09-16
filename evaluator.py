def evaluate_predictions(predicted_files: list, fail_to_pass: list, pass_to_pass: list) -> dict:
    """
    Heuristic evaluation: checks whether predicted impacted source files
    correspond to any of SWE-bench's real affected test files.
    NOTE: this is a name-matching heuristic, not a proven ground-truth
    mapping — disclose this limitation in your report.
    """
    all_ground_truth_tests = list(fail_to_pass) + list(pass_to_pass)
    matched_tests = []

    for test_id in all_ground_truth_tests:
        test_file = test_id.split("::")[0]
        for pred in predicted_files:
            pred_basename = pred.replace("\\", "/").split("/")[-1].replace(".py", "")
            if pred_basename and pred_basename in test_file:
                matched_tests.append(test_id)
                break

    total = len(all_ground_truth_tests)
    recall = round(len(matched_tests) / total, 3) if total else 0.0

    return {
        "ground_truth_tests": all_ground_truth_tests,
        "matched_tests": matched_tests,
        "recall": recall,
    }