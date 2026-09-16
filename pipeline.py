from dataset_loader import load_swebench_lite, get_instance_by_index
from repo_manager import clone_and_checkout
from patch_parser import get_changed_files
from parser_engine import RepoParser
from impact_scorer import score_impacted_files
from evaluator import evaluate_predictions


def run_full_pipeline(instance_index: int = 0, split: str = "test") -> dict:
    ds = load_swebench_lite(split)
    instance = get_instance_by_index(ds, instance_index)

    repo_path = clone_and_checkout(
        repo_name=instance["repo"],
        base_commit=instance["base_commit"],
        instance_id=instance["instance_id"],
    )

    changed = get_changed_files(instance["patch"])
    if not changed:
        raise ValueError("No changed files detected in patch.")

    primary_changed_file = changed[0]["file"]

    parser = RepoParser(repo_path)
    graph = parser.build_dependency_graph()
    impacted = parser.get_impacted_files(primary_changed_file)

    scored = score_impacted_files(graph, primary_changed_file, impacted)
    evaluation = evaluate_predictions(list(scored.keys()), instance["FAIL_TO_PASS"], instance["PASS_TO_PASS"])

    return {
        "instance_id": instance["instance_id"],
        "repo": instance["repo"],
        "changed_file": primary_changed_file,
        "changed_lines": changed[0]["changed_lines"],
        "impacted_scored": scored,
        "evaluation": evaluation,
        "problem_statement": instance["problem_statement"],
        "raw_patch": instance["patch"],          # NEW — for the diff viewer tab
        "changed_files_count": len(changed),      # NEW — for the summary cards
    }


if __name__ == "__main__":
    result = run_full_pipeline(instance_index=0)
    print(f"Instance: {result['instance_id']}")
    print(f"Changed file: {result['changed_file']}")
    print(f"Impacted files + scores:")
    for f, info in result["impacted_scored"].items():
        print(f"  - {f}: {info['level']} ({info['score']})")
    print(f"Recall vs real tests: {result['evaluation']['recall']}")