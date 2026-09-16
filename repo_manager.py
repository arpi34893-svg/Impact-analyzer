import os
import shutil
from git import Repo

REPOSITORIES_DIR = os.path.join(os.path.dirname(__file__), "repositories")


def clone_and_checkout(repo_name: str, base_commit: str, instance_id: str) -> str:
    """
    Clones a GitHub repo (if not already cloned) and checks out base_commit.
    repo_name: e.g. 'astropy/astropy'
    Returns the local path to the checked-out repo.
    """
    os.makedirs(REPOSITORIES_DIR, exist_ok=True)
    local_path = os.path.join(REPOSITORIES_DIR, instance_id)

    if os.path.exists(local_path):
        print(f"[INFO] Reusing existing clone at {local_path}")
        repo = Repo(local_path)
    else:
        github_url = f"https://github.com/{repo_name}.git"
        print(f"[INFO] Cloning {github_url} (this can take a while for big repos)...")
        repo = Repo.clone_from(github_url, local_path)

    print(f"[INFO] Checking out commit {base_commit}")
    repo.git.checkout(base_commit)

    return local_path


def cleanup_repo(instance_id: str):
    """Optional: delete a cloned repo to save disk space."""
    local_path = os.path.join(REPOSITORIES_DIR, instance_id)
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
        print(f"[INFO] Removed {local_path}")


if __name__ == "__main__":
    # quick manual test using the instance you already loaded
    from dataset_loader import load_swebench_lite, get_instance_by_index

    ds = load_swebench_lite("test")
    example = get_instance_by_index(ds, 0)

    path = clone_and_checkout(
        repo_name=example["repo"],
        base_commit=example["base_commit"],
        instance_id=example["instance_id"],
    )
    print(f"Repo ready at: {path}")