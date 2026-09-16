from datasets import load_dataset


def load_swebench_lite(split: str = "test"):
    """
    Loads SWE-bench Lite from Hugging Face.
    split: 'dev' or 'test'
    Returns a Hugging Face Dataset object (list-like of dicts).
    """
    dataset = load_dataset("SWE-bench/SWE-bench_Lite", split=split)
    return dataset


def get_instance_by_index(dataset, index: int = 0) -> dict:
    """Grabs one example instance to work with."""
    instance = dataset[index]
    return {
        "instance_id": instance["instance_id"],
        "repo": instance["repo"],
        "base_commit": instance["base_commit"],
        "problem_statement": instance["problem_statement"],
        "patch": instance["patch"],
        "test_patch": instance["test_patch"],
        "FAIL_TO_PASS": instance["FAIL_TO_PASS"],
        "PASS_TO_PASS": instance["PASS_TO_PASS"],
    }


if __name__ == "__main__":
    # quick manual test — run this file directly to check it works
    ds = load_swebench_lite("test")
    print(f"Loaded {len(ds)} instances.")
    example = get_instance_by_index(ds, 0)
    print(f"First instance repo: {example['repo']}")
    print(f"Instance ID: {example['instance_id']}")