import sys
import joblib
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score

from features import FEATURE_COLUMNS

FEATURE_CSV = "feature_table.csv"
MODEL_FILE = "impact_model.joblib"


def new_model():
    return RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )


if __name__ == "__main__":
    try:
        df = pd.read_csv(FEATURE_CSV)
    except FileNotFoundError:
        print(f"[ERROR] {FEATURE_CSV} not found. Run feature_engineering.py first.", flush=True)
        sys.exit(1)

    print(f"Loaded {len(df)} rows from {df['repo'].nunique()} repos", flush=True)
    X, y = df[FEATURE_COLUMNS], df["label"]

    # Split BY REPO: the test set contains repos the model has never seen.
    # This is the honest measure of "works on any Python repo".
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=df["repo"]))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    print(f"Train: {df.iloc[train_idx]['repo'].nunique()} repos ({len(X_train)} rows) | "
          f"Test (unseen repos): {df.iloc[test_idx]['repo'].nunique()} repos ({len(X_test)} rows)", flush=True)

    model = new_model().fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    print("\n--- Evaluation on UNSEEN repos ---", flush=True)
    print(f"Accuracy: {accuracy_score(y_test, pred):.4f}", flush=True)
    print(f"ROC AUC:  {roc_auc_score(y_test, proba):.4f}", flush=True)
    print(classification_report(y_test, pred, target_names=["not-impacted", "impacted"]), flush=True)

    print("Feature importances:", flush=True)
    for name, imp in sorted(zip(FEATURE_COLUMNS, model.feature_importances_), key=lambda t: -t[1]):
        print(f"  {name}: {imp:.4f}", flush=True)

    # Final model uses all repos
    final = new_model().fit(X, y)
    joblib.dump(final, MODEL_FILE)
    print(f"\nFinal model (trained on all repos) saved to {MODEL_FILE}", flush=True)