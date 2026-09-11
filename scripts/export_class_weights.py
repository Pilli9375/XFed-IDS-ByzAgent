#!/usr/bin/env python
"""Export the frozen, global class weights every federated silo must share.

Run ONCE, from the project root, before any Flower run:
    python scripts/export_class_weights.py

Writes configs/global_class_weights.json -- a 9-number file every silo reads
identically. This is the mechanism, not just the policy, behind "class weights
are global and fixed, not per-silo": if each client computed its own weights
from local counts, each would minimize a different loss and FedAvg would
average models that were never optimizing the same objective.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loaders import load_centralized
from src.data.schema import load_yaml


def main() -> int:
    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")

    print("Loading centralized split to compute global class weights ...")
    s = load_centralized(data_cfg, model_cfg)
    print(f"  {s.summary()}")

    out = {
        "scheme": model_cfg["training"]["class_weighting"]["scheme"],
        "beta": model_cfg["training"]["class_weighting"]["beta"],
        "weights": {name: float(w) for name, w in zip(s.class_names, s.class_weights)},
    }

    path = Path("configs/global_class_weights.json")
    path.write_text(json.dumps(out, indent=2))

    print(f"\n  weights: {out['weights']}")
    print(f"  written: {path}")
    print(f"\n  Every federated client_app.py call reads this file. If you ever change")
    print(f"  the class_weighting scheme or beta in model.yaml, re-run this script")
    print(f"  before the next federated run, or every silo will train against a")
    print(f"  stale objective.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
