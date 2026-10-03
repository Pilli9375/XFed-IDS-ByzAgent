#!/usr/bin/env python
"""One-time offline script: builds a sidecar artifact of UNSCALED raw
feature values and base_values (the SHAP additivity baseline: mean model
logit per class over the background set) for the fixed 14-row SHAP eval set,
for one federated tag.

Why this exists: results/shap/<tag>/global_shap.npz has shap_values, eval_y,
eval_families, additivity_max_diff, background_size -- but never the eval
rows' own raw feature values or the base_values SHAP additivity is checked
against. app_lib/loaders.py's get_fixed_eval_rows() and get_base_values()
compute both live, on demand, for the Streamlit app. The dashboard backend
must never do that (no per-request or even per-startup live computation
against the test set) -- so this script runs the identical computation
ONCE, offline, and persists the result.

This is a deliberate, logged, one-time read of data/processed/test_global.parquet
after the explanation check closed -- the test set is otherwise spent and every
other path in this project (backend/model_loader.py:load_and_verify(), every
GET /trust and GET /agreement path) is built to never touch it. Run this
script by hand, read its log output, and keep it -- that log is the audit
trail for this one exception.

Writes to a NEW file, results/shap/<tag>/eval_rows_sidecar.npz. Never opens
global_shap.npz for writing -- the explanation check's SHAP artifacts are read-only
and this script does not change that.

Reuses app_lib.loaders' canonical functions (get_fixed_eval_rows,
get_base_values, get_feature_cols, load_global_model_for_config,
get_federated_global_background) rather than reimplementing any of the
selection, scaling, or background-sampling logic.

Run as: python -m tools.build_shap_eval_sidecar --tag fedavg_a0.5_s42
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_lib.loaders import (  # noqa: E402
    get_base_values,
    get_feature_cols,
    get_federated_global_background,
    load_global_model_for_config,
)
from app_lib.loaders import get_fixed_eval_rows  # noqa: E402
from src.data.schema import derive_feature_cols, load_yaml  # noqa: E402

SHAP_ROOT = ROOT / "results" / "shap"
TEST_GLOBAL_PATH = ROOT / "data" / "processed" / "test_global.parquet"
TRAIN_POOL_PATH = ROOT / "data" / "processed" / "train_pool.parquet"

log = logging.getLogger("build_shap_eval_sidecar")


def _verify_feature_order(feature_cols_from_test_global: list[str]) -> None:
    """get_feature_cols() derives column order from test_global.parquet's
    schema. The live backend derives its /shap feature_names from
    train_pool.parquet's schema instead (backend/model_loader.py) -- a
    DIFFERENT file. Both call the same derive_feature_cols(), but on two
    different files' raw column listings, so identical output isn't
    guaranteed by construction. Confirmed empirically equal before writing
    this script; asserted here on every run rather than trusted from memory,
    because a silently different order here is exactly "a misaligned
    raw_values array that produces confident wrong tooltips"."""
    import pyarrow.parquet as pq

    data_cfg = load_yaml(ROOT / "configs" / "data.yaml")
    train_pool_cols = pq.ParquetFile(TRAIN_POOL_PATH).schema_arrow.names
    backend_order = derive_feature_cols(train_pool_cols, data_cfg)
    if backend_order != feature_cols_from_test_global:
        first_mismatch = next(
            (i for i, (a, b) in enumerate(zip(backend_order, feature_cols_from_test_global)) if a != b),
            None,
        )
        raise RuntimeError(
            "Feature order mismatch: train_pool.parquet-derived order (what the "
            "live backend's /shap reports as feature_names) does not match "
            "test_global.parquet-derived order (what this sidecar's raw_values "
            f"columns are in). First mismatch at index {first_mismatch}. "
            "Refusing to write a sidecar that would silently misalign."
        )
    log.info("feature order verified: train_pool.parquet-derived order == test_global.parquet-derived order (%d features)",
              len(feature_cols_from_test_global))


def build_sidecar(tag: str) -> Path:
    t0 = time.time()
    feature_cols = get_feature_cols()
    _verify_feature_order(feature_cols)

    log.info("reading %s once, via app_lib.loaders.get_fixed_eval_rows() -- "
              "the same fixed EVAL_SEED/N_EVAL_ROWS selection tools/centralized_shap_floor.py "
              "used to build the SHAP eval set in the first place", TEST_GLOBAL_PATH)
    X_raw, eval_y, eval_families = get_fixed_eval_rows()
    log.info("selected %d rows x %d features, families=%s (unscaled, straight from parquet)",
              X_raw.shape[0], X_raw.shape[1], eval_families)

    model, entry = load_global_model_for_config(tag)
    log.info("loaded global model for tag=%s, best_round=%d, checkpoint=%s",
              tag, entry["best_round"], entry["global_checkpoint"])

    background = get_federated_global_background()
    base_values = get_base_values(model, background)
    log.info("base_values computed: mean logit per class over %d-row background (fixed seed 777, "
              "pooled centralized X_train)", len(background))

    raw_hash = hashlib.sha256(np.ascontiguousarray(X_raw).tobytes()).hexdigest()
    feature_names_arr = np.array(feature_cols, dtype="<U64")
    eval_families_arr = np.array(eval_families, dtype="<U32")

    out_dir = SHAP_ROOT / tag
    if not out_dir.exists():
        raise FileNotFoundError(f"{out_dir} does not exist -- no global_shap.npz for tag={tag!r}?")
    out_path = out_dir / "eval_rows_sidecar.npz"
    np.savez(
        out_path,
        raw_values=X_raw.astype(np.float32),
        base_values=base_values.astype(np.float32),
        feature_names=feature_names_arr,
        eval_y=eval_y,
        eval_families=eval_families_arr,
    )

    elapsed = time.time() - t0
    log.info(
        "WROTE %s | tag=%s | source=%s | rows=%d features=%d classes=%d | "
        "raw_values sha256=%s | elapsed=%.1fs",
        out_path, tag, TEST_GLOBAL_PATH, X_raw.shape[0], X_raw.shape[1], base_values.shape[0],
        raw_hash, elapsed,
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="e.g. fedavg_a0.5_s42")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_sidecar(args.tag)


if __name__ == "__main__":
    main()
