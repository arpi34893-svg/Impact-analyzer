"""
Evaluates the impact-ranking model the way it's actually used: given a changed
file, rank the OTHER files in its repo, and check whether the files that truly
co-changed with it (in real merged PRs) land near the top of that ranking.

Metrics are computed per (repo, changed_file) query, then averaged — this
mirrors real usage, where each query is "one file changes, rank the rest".
Evaluation runs ONLY on repos held out from training (never seen by the
model), so the numbers are an honest measure of generalization, not memorization.

Run: python -u evaluate_model.py
Writes: evaluation_results.json (used by the Evaluation tab in app.py)
"""
import json
import sys

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score

from features import FEATURE_COLUMNS

FEATURE_CSV = "feature_table.csv"
OUTPUT_JSON = "evaluation_results.json"
K_VALUES = [1, 3, 5]
RANDOM_STATE = 42


def new_model():
    return RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1,
    )


def precision_recall_f1_at_k(ranked_labels: list, k: int, total_positives: int):
    top_k = ranked_labels[:k]
    hits = sum(top_k)
    precision = hits / min(k, len(ranked_labels)) if ranked_labels else 0.0
    recall = hits / total_positives if total_positives > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def reciprocal_rank(ranked_labels: list) -> float:
    for i, label in enumerate(ranked_labels, start=1):
        if label == 1:
            return 1.0 / i
    return 0.0


def evaluate_queries(model, df_test: pd.DataFrame) -> dict:
    """Groups test rows by (repo, file_a) = one query per changed file, ranks
    candidates by predicted probability, scores against the true positives."""
    df_test = df_test.copy()
    df_test["pred_proba"] = model.predict_proba(df_test[FEATURE_COLUMNS])[:, 1]

    per_k = {k: {"precision": [], "recall": [], "f1": []} for k in K_VALUES}
    reciprocal_ranks = []
    queries_used = 0
    queries_skipped_no_positive = 0

    for (repo, file_a), group in df_test.groupby(["repo", "file_a"]):
        total_positives = int(group["label"].sum())
        if total_positives == 0:
            queries_skipped_no_positive += 1
            continue  # nothing to rank against for this query

        ranked = group.sort_values("pred_proba", ascending=False)
        ranked_labels = ranked["label"].tolist()

        for k in K_VALUES:
            p, r, f1 = precision_recall_f1_at_k(ranked_labels, k, total_positives)
            per_k[k]["precision"].append(p)
            per_k[k]["recall"].append(r)
            per_k[k]["f1"].append(f1)

        reciprocal_ranks.append(reciprocal_rank(ranked_labels))
        queries_used += 1

    def avg(values):
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "queries_evaluated": queries_used,
        "queries_skipped_no_positive": queries_skipped_no_positive,
        "mean_reciprocal_rank": avg(reciprocal_ranks),
        "at_k": {
            str(k): {
                "precision": avg(per_k[k]["precision"]),
                "recall": avg(per_k[k]["recall"]),
                "f1": avg(per_k[k]["f1"]),
            }
            for k in K_VALUES
        },
    }


if __name__ == "__main__":
    try:
        df = pd.read_csv(FEATURE_CSV)
    except FileNotFoundError:
        print(f"[ERROR] {FEATURE_CSV} not found. Run feature_engineering.py first.", flush=True)
        sys.exit(1)

    X, y = df[FEATURE_COLUMNS], df["label"]
    n_repos = df["repo"].nunique()

    if n_repos < 4:
        print(f"[WARN] Only {n_repos} repos in {FEATURE_CSV}; held-out evaluation needs several "
              "repos to be meaningful. Results below may be noisy.", flush=True)

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(X, y, groups=df["repo"]))
    df_train, df_test = df.iloc[train_idx], df.iloc[test_idx]

    print(f"Train: {df_train['repo'].nunique()} repos ({len(df_train)} rows) | "
          f"Held-out test: {df_test['repo'].nunique()} repos ({len(df_test)} rows)", flush=True)

    model = new_model().fit(df_train[FEATURE_COLUMNS], df_train["label"])

    pred = model.predict(df_test[FEATURE_COLUMNS])
    proba = model.predict_proba(df_test[FEATURE_COLUMNS])[:, 1]
    classification_summary = {
        "accuracy": round(accuracy_score(df_test["label"], pred), 4),
        "roc_auc": round(roc_auc_score(df_test["label"], proba), 4),
    }
    print(f"\nRow-level (pairwise) accuracy: {classification_summary['accuracy']} | "
          f"ROC AUC: {classification_summary['roc_auc']}", flush=True)

    ranking_summary = evaluate_queries(model, df_test)
    print(f"\nRanking evaluation on {ranking_summary['queries_evaluated']} held-out queries "
          f"(one query = one changed file in an unseen repo):", flush=True)
    print(f"Mean Reciprocal Rank: {ranking_summary['mean_reciprocal_rank']}", flush=True)
    for k in K_VALUES:
        m = ranking_summary["at_k"][str(k)]
        print(f"  @K={k}: precision={m['precision']}  recall={m['recall']}  f1={m['f1']}", flush=True)

    results = {
        "held_out_repos": int(df_test["repo"].nunique()),
        "held_out_rows": int(len(df_test)),
        "classification": classification_summary,
        "ranking": ranking_summary,
        "k_values": K_VALUES,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {OUTPUT_JSON}", flush=True)