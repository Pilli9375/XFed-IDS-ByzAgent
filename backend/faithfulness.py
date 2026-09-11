"""Builds the GET /faithfulness snapshot (AUC table + curve figures) once at
startup. Single config only (alpha=0.5, seed=42) -- faithfulness was never
computed for the other 8, per app_lib/loaders.py's FAITHFULNESS_CONFIG_LABEL.

Per-step deletion/insertion curve data does not exist: tools/deletion_curve.py
and tools/insertion_curve.py wrote only the final AUC (results/inspection/
{deletion,insertion}_auc.csv) and a PNG (results/figures/{kind}_curve.png).
This module does not regenerate, recompute, or modify either -- it reads
both, once, and nothing else.

Reuses app_lib/loaders.py's load_faithfulness_auc() / get_faithfulness_figure_path()
/ FAITHFULNESS_CONFIG_LABEL rather than reimplementing the CSV merge.

Place at: backend/faithfulness.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_lib.loaders import (  # noqa: E402
    FAITHFULNESS_CONFIG_LABEL,
    get_faithfulness_figure_path,
    load_faithfulness_auc,
)


def build_faithfulness_snapshot() -> dict:
    auc = load_faithfulness_auc()
    if auc is None:
        raise RuntimeError(
            "results/inspection/deletion_auc.csv and/or insertion_auc.csv are "
            "required for GET /faithfulness but app_lib.loaders reported them missing."
        )
    return {
        "config_label": FAITHFULNESS_CONFIG_LABEL,
        "auc": json.loads(auc["table"].to_json(orient="records")),
    }


def load_faithfulness_figures() -> dict[str, bytes]:
    """Reads both PNGs fully into memory once, at startup, and returns raw
    bytes -- served from memory by GET /faithfulness/{kind}_curve.png,
    never re-read from disk per request."""
    figures = {}
    for kind in ("deletion", "insertion"):
        path = get_faithfulness_figure_path(kind)
        if path is None:
            raise RuntimeError(
                f"results/figures/{kind}_curve.png is required for GET /faithfulness "
                f"but app_lib.loaders reported it missing."
            )
        figures[kind] = path.read_bytes()
    return figures
