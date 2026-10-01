import os
import sys
import shutil
import subprocess
import joblib
import pandas as pd

from features import RepoContext, FEATURE_COLUMNS

MODEL_FILE = "impact_model.joblib"
CLONE_DIR = "repositories"


class RepoAccessError(Exception):
    """Raised for problems specific to reaching/using a GitHub repo (as opposed to
    generic bugs), so the UI can show a clean message instead of a raw traceback."""
    pass


def clone_repo_if_needed(repo_full_name: str) -> str:
    dest_dir = os.path.join(CLONE_DIR, repo_full_name.replace("/", "__"))
    if os.path.exists(dest_dir):
        if not os.listdir(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)  # clean up a failed prior clone
        else:
            return dest_dir

    os.makedirs(CLONE_DIR, exist_ok=True)
    print(f"Cloning {repo_full_name}...", flush=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", f"https://github.com/{repo_full_name}.git", dest_dir],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise RepoAccessError(
            f"Timed out reaching GitHub while cloning '{repo_full_name}'. This usually means the "
            "current network is blocking github.com for command-line tools (common on campus/office "
            "WiFi) — try a mobile hotspot and run again."
        )
    except FileNotFoundError:
        raise RepoAccessError(
            "Git is not installed or not on PATH. Install Git for Windows and restart your terminal."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        shutil.rmtree(dest_dir, ignore_errors=True)  # don't leave a broken partial clone behind
        lowered = stderr.lower()
        if "could not connect" in lowered or "failed to connect" in lowered:
            raise RepoAccessError(
                f"Could not reach GitHub to clone '{repo_full_name}'. This usually means the current "
                "network is blocking github.com for command-line tools — try a mobile hotspot."
            )
        if "not found" in lowered or "repository not found" in lowered:
            raise RepoAccessError(
                f"'{repo_full_name}' was not found on GitHub. It may be private, deleted, or "
                "misspelled — check the exact owner/repo name on github.com."
            )
        if "could not resolve host" in lowered:
            raise RepoAccessError("No internet connection detected (DNS lookup failed).")
        raise RepoAccessError(f"Failed to clone '{repo_full_name}': {stderr[:300]}")

    return dest_dir


def predict_impact(repo_path_or_name: str, changed_file: str, top_n: int = 10) -> pd.DataFrame:
    """repo_path_or_name: local folder or 'owner/repo'. changed_file: path inside the repo."""
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"{MODEL_FILE} not found. Run train_model.py first.")

    repo_path = repo_path_or_name if os.path.isdir(repo_path_or_name) else clone_repo_if_needed(repo_path_or_name)
    model = joblib.load(MODEL_FILE)

    try:
        ctx = RepoContext(repo_path)
    except Exception as e:
        raise RepoAccessError(f"Could not parse '{repo_path_or_name}' as a Python repo: {e}")

    if len(ctx.files) == 0:
        raise RepoAccessError(
            f"No parsable .py files were found in '{repo_path_or_name}'. "
            "It may not be a Python project, or the clone may be incomplete."
        )

    changed = changed_file.replace("\\", "/").strip()
    if not changed:
        raise ValueError("Enter a changed file path (e.g. 'src/module.py').")
    if not changed.endswith(".py"):
        raise ValueError(f"'{changed}' does not look like a Python file — expected a '.py' path.")
    if changed not in ctx.file_set:
        examples = ", ".join(ctx.files[:5])
        raise ValueError(
            f"'{changed}' was not found among this repo's parsed .py files. "
            f"Paths are relative to the repo root. Examples of valid paths: {examples}"
        )

    rows = [{"file": c, **ctx.pair_features(changed, c)} for c in ctx.files if c != changed]
    if not rows:
        raise RepoAccessError(f"'{changed}' is the only Python file found — nothing to rank it against.")

    df = pd.DataFrame(rows)
    df["impact_probability"] = model.predict_proba(df[FEATURE_COLUMNS])[:, 1].round(4)
    cols = ["file", "impact_probability", "graph_distance", "a_imports_b", "b_imports_a"]
    return df.sort_values("impact_probability", ascending=False)[cols].head(top_n).reset_index(drop=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ml_impact_predictor.py <repo_path_or_owner/repo> <changed_file>", flush=True)
        sys.exit(1)
    try:
        result = predict_impact(sys.argv[1], sys.argv[2], top_n=10)
        print(f"\nTop predicted impacted files if '{sys.argv[2]}' changes:\n", flush=True)
        print(result.to_string(index=False), flush=True)
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        sys.exit(1)