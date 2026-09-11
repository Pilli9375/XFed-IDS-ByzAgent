"""Builds the GET /federation snapshot once at startup.

Unlike every other endpoint in this backend (/predict, /shap, /trust, which
all serve the single loaded tag from configs/backend.yaml's model.tag), this
serves ALL 9 (alpha, seed) configs -- intentional, per the task. GET /config
stays loaded-model identity only; this module is never merged into it.

Reuses app_lib/loaders.py's canonical functions (get_federation_shape,
get_label_vocab, get_all_manifest_summaries, get_silo_total_eligibility,
get_eligibility_summary, get_silo_sizes) rather than reimplementing any
parsing or threshold logic. SILO_TOTAL_MIN_FLOWS / SILO_FAMILY_MIN_FLOWS /
FAMILY_MIN_ELIGIBLE_SILOS live in that module as fixed constants -- this
module never re-derives or restates them, just reports whatever those
functions return.

Place at: backend/federation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_lib.loaders import (  # noqa: E402
    get_all_manifest_summaries,
    get_eligibility_summary,
    get_federation_shape,
    get_label_vocab,
    get_silo_sizes,
    get_silo_total_eligibility,
)


def _records(df) -> list[dict]:
    """DataFrame -> JSON-native records. alpha is normalized to the same
    string form best_rounds_manifest.json already uses ("0.1"/"0.5"/"5.0"),
    since CSV-sourced alpha columns come back as float64 (0.1, 0.5, 5.0)
    from pandas -- confirmed str(0.1) == '0.1' etc. round-trips exactly to
    the manifest's own convention before relying on it here."""
    if df is None:
        return []
    df = df.copy()
    if "alpha" in df.columns:
        df["alpha"] = df["alpha"].astype(str)
    return json.loads(df.to_json(orient="records"))


def build_federation_snapshot() -> dict:
    shape = get_federation_shape()
    # configs/data.yaml's federation.alphas parses as YAML floats (0.1, 0.5,
    # 5.0). Every per-row alpha below is normalized to the manifest's own
    # string convention via _records() -- shape.alphas must match, or a
    # frontend filter comparing shape.alphas against a row's alpha silently
    # matches nothing (exactly what happened before this fix).
    shape = {**shape, "alphas": [str(a) for a in shape["alphas"]]}
    vocab = get_label_vocab()
    manifest_summaries = get_all_manifest_summaries()

    silo_total = get_silo_total_eligibility()
    family_elig = get_eligibility_summary()
    sizes = get_silo_sizes()

    if silo_total is None or family_elig is None or sizes is None:
        raise RuntimeError(
            "results/inspection/silo_sizes.csv is required for GET /federation "
            "(silo_total_eligibility, family_eligibility, and silo_sizes all "
            "derive from it via app_lib.loaders) but was reported missing."
        )

    return {
        "shape": shape,
        "label_vocab": {
            "headline_classes": vocab["headline_classes"],
            "below_floor_classes": vocab["below_floor_classes"],
            "n_classes": vocab["n_classes"],
        },
        "manifest_summaries": _records(manifest_summaries),
        "silo_total_eligibility": {
            "threshold_flows": silo_total["threshold_flows"],
            "n_excluded": silo_total["n_excluded"],
            "n_total": silo_total["n_total"],
            # Every row, not just excluded ones -- the frontend filters on
            # below_floor itself.
            "table": _records(silo_total["table"]),
        },
        "family_eligibility": {
            "threshold_flows": family_elig["threshold_flows"],
            "min_eligible_silos": family_elig["min_eligible_silos"],
            "n_excluded": family_elig["n_excluded"],
            "n_total": family_elig["n_total"],
            # Every row, not just excluded ones -- the frontend filters on
            # family_included itself.
            "matrix": _records(family_elig["matrix"]),
        },
        # Raw rows -- the frontend pivots for the heatmap, not this backend.
        "silo_sizes": _records(sizes),
    }
