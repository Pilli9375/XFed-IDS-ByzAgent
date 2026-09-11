"""Metrics. The 7-vs-9 reporting rule lives here and nowhere else.

Accuracy is never returned as a headline number: Benign is 75% of the data, so a
classifier that predicts Benign for everything scores 0.75 and detects nothing.

Place at: src/train/metrics.py
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_classes: int,
    class_names: list[str],
    headline_idx: np.ndarray,
) -> dict:
    """Per-class figures plus both macro averages and the two IDS rates.

    headline_idx selects the 7 above-floor families. Infiltration (45 train
    rows) and Heartbleed (7) are reported per-class but excluded from the
    headline average, because a macro mean over classes with single-digit
    support is dominated by noise from classes nobody can learn.
    """
    labels = np.arange(n_classes)
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    per_class = {
        class_names[i]: {
            "precision": float(prec[i]),
            "recall": float(rec[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i in labels
    }

    benign_idx = class_names.index("Benign")
    is_benign_true = y_true == benign_idx
    is_benign_pred = y_pred == benign_idx

    n_benign = int(is_benign_true.sum())
    n_attack = int((~is_benign_true).sum())

    # What a SOC actually pays for: benign flows raised as alerts, and attacks
    # waved through. Recall over all attack classes pooled, not per family.
    false_positive_rate = (
        float((is_benign_true & ~is_benign_pred).sum() / n_benign) if n_benign else float("nan")
    )
    attack_recall = (
        float(((~is_benign_true) & (~is_benign_pred)).sum() / n_attack) if n_attack else float("nan")
    )

    return {
        "macro_f1_headline": float(f1[headline_idx].mean()),   # the headline number
        "macro_f1_all": float(f1.mean()),                      # appendix only
        "false_positive_rate": false_positive_rate,
        "attack_recall": attack_recall,
        "accuracy": float((y_true == y_pred).mean()),          # reported, never headlined
        "per_class": per_class,
    }


def confusion(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> list[list[int]]:
    """Rows are true classes, columns predicted. JSON-serializable."""
    return confusion_matrix(y_true, y_pred, labels=np.arange(n_classes)).tolist()


def format_per_class(metrics: dict, headline_classes: list[str]) -> str:
    """Console table. Below-floor families are marked so they are never misread
    as contributing to the headline average."""
    lines = [f"  {'family':<14}{'prec':>8}{'recall':>8}{'F1':>8}{'support':>10}"]
    for name, m in metrics["per_class"].items():
        mark = "" if name in headline_classes else "  (below floor)"
        lines.append(
            f"  {name:<14}{m['precision']:>8.4f}{m['recall']:>8.4f}"
            f"{m['f1']:>8.4f}{m['support']:>10,}{mark}"
        )
    lines.append("")
    lines.append(f"  macro-F1 (7 headline) : {metrics['macro_f1_headline']:.4f}")
    lines.append(f"  macro-F1 (all 9)      : {metrics['macro_f1_all']:.4f}")
    lines.append(f"  false positive rate   : {metrics['false_positive_rate']:.5f}")
    lines.append(f"  attack recall         : {metrics['attack_recall']:.4f}")
    return "\n".join(lines)
