"""Measure how well the categoriser works, honestly.

A naive train/test split would put "TESCO EXPRESS 123" in training and
"TESCO EXPRESS 456" in testing, which makes accuracy look far better than
it really is. Instead we split by MERCHANT (GroupKFold): every merchant in
the test fold is one the model has never seen. That is the real job the
ML part does, since known merchants are already handled by rules.

Run:  python scripts/evaluate.py
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.categoriser import CONFIDENCE_THRESHOLD, Categoriser, build_model, load_training_data  # noqa: E402


def main():
    texts, labels, groups, kinds = load_training_data()
    texts, labels, groups, kinds = map(np.array, (texts, labels, groups, kinds))

    y_true, y_pred, confs, y_kind = [], [], [], []
    for train_idx, test_idx in GroupKFold(n_splits=5).split(texts, labels, groups):
        model = build_model().fit(texts[train_idx], labels[train_idx])
        probs = model.predict_proba(texts[test_idx])
        y_true.extend(labels[test_idx])
        y_kind.extend(kinds[test_idx])
        y_pred.extend(model.classes_[probs.argmax(axis=1)])
        confs.extend(probs.max(axis=1))

    y_true, y_pred, confs, y_kind = map(np.array, (y_true, y_pred, confs, y_kind))
    confident = confs >= CONFIDENCE_THRESHOLD

    print("=== ML on merchants never seen in training (5 fold, grouped by merchant) ===")
    print(f"Accuracy, all predictions:          {accuracy_score(y_true, y_pred):.1%}")
    print(f"Share auto categorised (conf >= {CONFIDENCE_THRESHOLD}): {confident.mean():.1%}")
    print(f"Accuracy when auto categorised:     {accuracy_score(y_true[confident], y_pred[confident]):.1%}")
    for kind in ("independent", "brand"):
        m = y_kind == kind
        mc = m & confident
        print(f"  {kind:>11} merchants: accuracy {accuracy_score(y_true[m], y_pred[m]):.1%}, "
              f"auto categorised {mc.sum() / m.sum():.0%} at {accuracy_score(y_true[mc], y_pred[mc]):.1%}")
    print()
    print(classification_report(y_true, y_pred, zero_division=0))

    # Full hybrid pipeline (rules + ML) on the sample statement
    import csv
    sample = Path(__file__).resolve().parent.parent.parent / "sample_data" / "sample_statement.csv"
    cat = Categoriser()
    sources = Counter()
    with open(sample, newline="") as f:
        for row in csv.DictReader(f):
            _, source, _, review = cat.categorise(row["Name"], float(row["Amount"]))
            sources["review" if review else source] += 1
    total = sum(sources.values())
    print("=== Sample statement: how each transaction was decided ===")
    for name, count in sources.most_common():
        print(f"{name:>8}: {count:3d}  ({count / total:.0%})")


if __name__ == "__main__":
    main()
