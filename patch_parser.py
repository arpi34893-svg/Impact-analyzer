from unidiff import PatchSet


def get_changed_files(patch_text: str) -> list:
    """
    Parses a unified diff (patch string) and returns a list of dicts:
    [{"file": "astropy/io/fits.py", "changed_lines": [45, 46, 102]}, ...]
    """
    patch = PatchSet(patch_text)
    changed = []

    for patched_file in patch:
        # skip files that were only deleted entirely (nothing to analyze)
        if patched_file.is_removed_file:
            continue

        file_path = patched_file.path
        changed_lines = []

        for hunk in patched_file:
            for line in hunk:
                if line.is_added or line.is_removed:
                    # target_line_no is None for removed lines; use source_line_no as fallback
                    line_no = line.target_line_no or line.source_line_no
                    if line_no:
                        changed_lines.append(line_no)

        changed.append({
            "file": file_path,
            "changed_lines": sorted(set(changed_lines)),
        })

    return changed


if __name__ == "__main__":
    # quick manual test using the same instance you've already cloned
    from dataset_loader import load_swebench_lite, get_instance_by_index

    ds = load_swebench_lite("test")
    example = get_instance_by_index(ds, 0)

    result = get_changed_files(example["patch"])
    print(f"Instance: {example['instance_id']}")
    print(f"Files changed by the actual fix:")
    for entry in result:
        print(f"  - {entry['file']}  (lines: {entry['changed_lines']})")