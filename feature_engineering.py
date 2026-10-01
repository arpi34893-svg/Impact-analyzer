import os
import sys
import json
import random
import subprocess
import traceback

import requests
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from features import RepoContext

GITHUB_API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

TRAINING_DATA_FILE = "training_data.json"
CLONE_DIR = "repositories"
OUTPUT_CSV = "feature_table.csv"
CLONE_TIMEOUT_SECONDS = 60
MAX_REPO_SIZE_KB = 50_000
MAX_PAIRS_PER_PR = 50  # stops one giant PR from dominating a repo's data

random.seed(42)


def get_repo_size_kb(repo_full_name: str) -> int:
    try:
        r = requests.get(f"{GITHUB_API}/repos/{repo_full_name}", headers=HEADERS, timeout=10)
        return r.json().get("size", -1) if r.status_code == 200 else -1
    except Exception:
        return -1


def clone_repo(repo_full_name: str, dest_dir: str) -> bool:
    if os.path.exists(dest_dir):
        return True  # already cloned, no network needed

    size_kb = get_repo_size_kb(repo_full_name)
    if size_kb == -1:
        print(f"  [WARN] Could not determine size for {repo_full_name}, skipping.", flush=True)
        return False
    if size_kb > MAX_REPO_SIZE_KB:
        print(f"  [SKIP] {repo_full_name} is {size_kb} KB (> limit), skipping.", flush=True)
        return False

    print(f"  Cloning {repo_full_name} ({size_kb} KB)...", flush=True)
    process = subprocess.Popen(
        ["git", "clone", "--depth", "1", f"https://github.com/{repo_full_name}.git", dest_dir],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        _, stderr = process.communicate(timeout=CLONE_TIMEOUT_SECONDS)
        if process.returncode != 0:
            print(f"  [WARN] Clone failed: {stderr.decode(errors='ignore')[:200]}", flush=True)
            return False
        return True
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        print(f"  [WARN] Clone timed out for {repo_full_name}, killed.", flush=True)
        return False


def make_row(ctx, repo, a, b, label):
    return {"repo": repo, "file_a": a, "file_b": b, **ctx.pair_features(a, b), "label": label}


def process_repo(repo: str, pr_list: list) -> list:
    dest_dir = os.path.join(CLONE_DIR, repo.replace("/", "__"))
    if not clone_repo(repo, dest_dir):
        return []

    ctx = RepoContext(dest_dir)
    if len(ctx.files) < 2:
        print("  [WARN] Not enough parsed files, skipping.", flush=True)
        return []

    rows = []
    positive_keys = set()
    missing = 0

    for pr in pr_list:
        # keep only files that still exist in the parsed repo
        files = [f for f in pr["files"] if f in ctx.file_set]
        missing += len(pr["files"]) - len(files)
        pairs = [(files[i], files[j]) for i in range(len(files)) for j in range(i + 1, len(files))]
        if len(pairs) > MAX_PAIRS_PER_PR:
            pairs = random.sample(pairs, MAX_PAIRS_PER_PR)
        for a, b in pairs:
            key = frozenset((a, b))
            if key in positive_keys:
                continue
            positive_keys.add(key)
            rows.append(make_row(ctx, repo, a, b, 1))
            rows.append(make_row(ctx, repo, b, a, 1))  # both directions

    n_pos = len(rows)
    if n_pos == 0:
        print(f"  [WARN] No usable co-change pairs ({missing} PR files not found in repo).", flush=True)
        return []

    negative_keys = set()
    attempts = 0
    while len(negative_keys) < n_pos and attempts < n_pos * 30:
        attempts += 1
        a, b = random.sample(ctx.files, 2)
        key = frozenset((a, b))
        if key in positive_keys or key in negative_keys:
            continue
        negative_keys.add(key)
        rows.append(make_row(ctx, repo, a, b, 0))

    print(f"  -> {n_pos} positive rows, {len(negative_keys)} negative rows "
          f"({missing} PR files no longer in repo, ignored)", flush=True)
    return rows


if __name__ == "__main__":
    try:
        if not os.path.exists(TRAINING_DATA_FILE):
            print(f"[ERROR] {TRAINING_DATA_FILE} not found. Run github_fetcher.py first.", flush=True)
            sys.exit(1)

        with open(TRAINING_DATA_FILE, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        os.makedirs(CLONE_DIR, exist_ok=True)
        all_rows = []
        names = list(dataset.keys())
        for i, repo in enumerate(names, start=1):
            print(f"\n[{i}/{len(names)}] Processing {repo}...", flush=True)
            try:
                all_rows.extend(process_repo(repo, dataset[repo]))
            except Exception as e:
                print(f"  [WARN] Skipping {repo}: {e}", flush=True)

        if not all_rows:
            print("\n[ERROR] No feature rows produced.", flush=True)
            sys.exit(1)

        df = pd.DataFrame(all_rows)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\nDone. {len(df)} rows from {df['repo'].nunique()} repos "
              f"({int(df['label'].sum())} positive, {int((df['label'] == 0).sum())} negative) -> {OUTPUT_CSV}",
              flush=True)

    except Exception:
        traceback.print_exc()
        sys.exit(1)