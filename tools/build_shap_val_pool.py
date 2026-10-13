#!/usr/bin/env python
"""One-time offline script: builds a SHAP pool of VALIDATION rows for the
dashboard demo, so the traffic simulator can replay rows that all have a
precomputed explanation without touching the test set.

Everything is set in configs/val_shap_pool.yaml. The sample is a fixed,
seeded set of validation rows (train_pool.parquet rows where val_mask.is_val
is true), stratified over all 9 families with the balanced-with-floor
algorithm that tools/local_shap_pipeline.py used for the original eval set.

It matches results/shap/<tag>/streamed_pool.npz in three ways:
  - explainer: tools.build_shap_streamed_pool._explain_pool, which runs
    GradientExplainer once per row with nsamples = local_shap_pipeline.NSAMPLES.
  - background: app_lib.loaders' recipe, a stratified sample of 200 rows of
    pooled centralized X_train with seed 777.
  - model: the served checkpoint, via load_global_model_for_config(tag).

The one difference is how the scaler and background are built. This script
never reads test_global.parquet. app_lib.loaders.get_centralized_splits()
would read it, because load_centralized() also scales the test split. Here
src.data.loaders._prepare is called with the validation frame standing in
for the test frame. The scaler
and background depend only on the training split, so they come out the
same. The script asserts that instead of assuming it: the background's mean
logits must equal eval_rows_sidecar.npz's base_values, and the scaler must
equal the StandardScaler the backend fits at startup.

sample_id is each row's POSITION in train_pool.parquet, not a test_global
position. The backend keeps the two pools apart: /shap takes ?source=val for
this one.

Writes:
  - results/shap/<tag>/<output_filename>: same arrays as streamed_pool.npz,
    plus source="val", predicted_y and relative_additivity.
  - results/shap/<tag>/<summary_filename>: class counts, residual stats and
    provenance as JSON.

Run as: python -m tools.build_shap_val_pool [--limit N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_lib.loaders import (  # noqa: E402
    BACKGROUND_TARGET,
    FEDERATED_BACKGROUND_SEED_BASE,
    _build_stratified_background,
    get_label_vocab,
    load_global_model_for_config,
)
from src.data.loaders import _prepare  # noqa: E402
from src.data.schema import derive_feature_cols, load_yaml  # noqa: E402
from tools.build_shap_streamed_pool import _explain_pool  # noqa: E402
from tools.local_shap_pipeline import NSAMPLES, build_stratified_background  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "val_shap_pool.yaml"
SHAP_ROOT = ROOT / "results" / "shap"
TRAIN_POOL_PATH = ROOT / "data" / "processed" / "train_pool.parquet"
VAL_MASK_PATH = ROOT / "data" / "processed" / "val_mask.parquet"

log = logging.getLogger("build_shap_val_pool")


def _load_train_pool(data_cfg: dict) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """train_pool.parquet (features + family, float32) and the val mask.
    The frame's index is the row position in train_pool.parquet and is never
    reset -- it becomes sample_id."""
    feature_cols = derive_feature_cols(pq.ParquetFile(TRAIN_POOL_PATH).schema_arrow.names, data_cfg)
    pool = pd.read_parquet(TRAIN_POOL_PATH, columns=feature_cols + ["family"])
    pool[feature_cols] = pool[feature_cols].astype(np.float32)
    mask = pd.read_parquet(VAL_MASK_PATH)["is_val"].to_numpy(dtype=bool)
    if len(mask) != len(pool):
        raise RuntimeError(f"val_mask has {len(mask):,} rows but train_pool has {len(pool):,}.")
    return pool, mask, feature_cols


def _select_val_rows(val_df: pd.DataFrame, pool_size: int, sample_seed: int, n_classes: int) -> np.ndarray:
    """Stratified over every family present in the validation split. Returns
    train_pool.parquet row positions, in the algorithm's own (shuffled)
    order -- the order the simulator replays."""
    local_idx = build_stratified_background(
        X=None, y=val_df["family"].to_numpy(), target_total=pool_size, seed=sample_seed
    )
    sample_id = val_df.index.to_numpy()[local_idx]
    if len(sample_id) != pool_size or len(set(sample_id.tolist())) != pool_size:
        raise RuntimeError(f"stratified sample has {len(sample_id)} rows / "
                           f"{len(set(sample_id.tolist()))} unique, expected {pool_size}")
    n_fam = val_df.loc[sample_id, "family"].nunique()
    if n_fam != n_classes:
        raise RuntimeError(f"sample covers {n_fam} families, expected all {n_classes}")
    return sample_id


def _verify_scaler(splits, X_train_raw: np.ndarray) -> None:
    """The backend's serving scaler is sklearn StandardScaler fit on the same
    training rows (backend/model_loader.py::_fit_scaler). Same numbers, or
    the SHAP inputs would not be what /predict sees."""
    ref = StandardScaler().fit(X_train_raw)
    if not (np.allclose(splits.scaler_center, ref.mean_, rtol=1e-6, atol=1e-6)
            and np.allclose(splits.scaler_scale, ref.scale_, rtol=1e-6, atol=1e-6)):
        raise RuntimeError("scaler from _prepare() differs from the backend's StandardScaler refit.")
    log.info("scaler verified against a StandardScaler refit on the training split")


def _verify_background(model: torch.nn.Module, background: np.ndarray, tag: str) -> np.ndarray:
    """Mean logit over the background must reproduce eval_rows_sidecar.npz's
    base_values (built from get_federated_global_background(), i.e. the
    test-reading path) -- proof the test-free rebuild gives the same 200 rows."""
    with torch.no_grad():
        f_bg_mean = model(torch.from_numpy(background.copy())).numpy().mean(axis=0)
    sidecar = SHAP_ROOT / tag / "eval_rows_sidecar.npz"
    with np.load(sidecar) as npz:
        ref = npz["base_values"].copy()
    diff = float(np.abs(f_bg_mean - ref).max())
    if diff > 1e-5:
        raise RuntimeError(f"background mean logits differ from {sidecar.name} base_values by {diff:.3e}")
    log.info("background verified: mean logits match %s base_values (max diff %.3e)", sidecar.name, diff)
    return f_bg_mean


def _stats(a: np.ndarray) -> dict:
    return {
        "mean": float(a.mean()), "median": float(np.median(a)),
        "p95": float(np.percentile(a, 95)), "max": float(a.max()), "min": float(a.min()),
    }


def build(limit: int | None = None) -> Path:
    t0 = time.time()
    cfg = load_yaml(CONFIG_PATH)
    tag = str(cfg["tag"])
    data_cfg = load_yaml(ROOT / "configs" / "data.yaml")
    model_cfg = load_yaml(ROOT / "configs" / "model.yaml")
    vocab_info = get_label_vocab()
    n_classes = int(vocab_info["n_classes"])

    pool, mask, feature_cols = _load_train_pool(data_cfg)
    train_df, val_df = pool[~mask], pool[mask]
    log.info("train_pool: %d rows, %d validation rows; test_global.parquet is not read",
             len(pool), len(val_df))

    sample_id = _select_val_rows(val_df, int(cfg["pool_size"]), int(cfg["sample_seed"]), n_classes)
    if limit is not None:
        log.warning("--limit %d: test run only, NOT the real artifact", limit)
        sample_id = sample_id[:limit]

    rows = pool.loc[sample_id]
    X_raw = rows[feature_cols].to_numpy(np.float32)
    families = rows["family"].to_numpy()
    eval_y = rows["family"].map(vocab_info["vocab"]).to_numpy(np.int64)
    class_counts = {f: int((families == f).sum()) for f in sorted(set(families.tolist()))}
    log.info("selected %d validation rows, family counts: %s", len(sample_id), class_counts)

    # _prepare() needs a non-empty test frame only to fill splits.X_test
    # (sklearn rejects 0 rows); the validation frame stands in, and that
    # field is never used below. The scaler is fit on train_df alone.
    splits = _prepare(train_df, val_df, val_df, feature_cols, model_cfg,
                      model_cfg["preprocessing"]["scaler"])
    _verify_scaler(splits, train_df[feature_cols].to_numpy(np.float32))
    background = splits.X_train[
        _build_stratified_background(splits.X_train, splits.y_train, BACKGROUND_TARGET,
                                     FEDERATED_BACKGROUND_SEED_BASE)
    ]

    model, entry = load_global_model_for_config(tag)
    log.info("loaded served checkpoint %s (best_round=%d)", entry["global_checkpoint"], entry["best_round"])
    f_bg_mean = _verify_background(model, background, tag)

    X_scaled = ((X_raw - splits.scaler_center) / splits.scaler_scale).astype(np.float32)

    seed = int(cfg["explainer_seed"])
    torch.manual_seed(seed)
    np.random.seed(seed)
    shap_values, additivity = _explain_pool(model, background, X_scaled)

    with torch.no_grad():
        f_eval = model(torch.from_numpy(X_scaled)).numpy()
    predicted_y = f_eval.argmax(axis=1).astype(np.int64)
    # Relative residual, defined here as: largest |sum(SHAP) - (f(x) - E[f])|
    # over the 9 classes, divided by the largest |f(x) - E[f]| over the same
    # classes. This script's own definition; not necessarily the one behind
    # the project-wide ~3-8% figure.
    relative = additivity / np.abs(f_eval - f_bg_mean[None, :]).max(axis=1)

    class_names = [vocab_info["idx_to_name"][i] for i in range(n_classes)]
    out_dir = SHAP_ROOT / tag
    out_name = cfg["output_filename"]
    if limit is not None:
        out_name = out_name.replace(".npz", f"_limit{limit}.npz")
    out_path = out_dir / out_name
    np.savez(
        out_path,
        shap_values=shap_values,
        sample_id=sample_id,
        raw_values=X_raw,
        feature_names=np.array(feature_cols, dtype="<U64"),
        class_names=np.array(class_names, dtype="<U32"),
        eval_y=eval_y,
        eval_families=np.array(families, dtype="<U32"),
        predicted_y=predicted_y,
        additivity_max_diff=additivity,
        relative_additivity=relative.astype(np.float32),
        source=np.array("val"),
    )

    raw_hash = hashlib.sha256(np.ascontiguousarray(X_raw).tobytes()).hexdigest()
    summary = {
        "tag": tag,
        "source": "val",
        "source_file": "data/processed/train_pool.parquet (val_mask.is_val rows)",
        "sample_id_meaning": "row position in train_pool.parquet",
        "n_rows": int(len(sample_id)),
        "limit": limit,
        "pool_size": int(cfg["pool_size"]),
        "sample_seed": int(cfg["sample_seed"]),
        "explainer_seed": seed,
        "nsamples": int(NSAMPLES),
        "background": f"{BACKGROUND_TARGET} rows, pooled centralized X_train, seed {FEDERATED_BACKGROUND_SEED_BASE}",
        "checkpoint": str(entry["global_checkpoint"]).replace("\\", "/"),
        "best_round": int(entry["best_round"]),
        "class_counts": class_counts,
        "additivity_abs_logit": _stats(additivity),
        "additivity_relative": _stats(relative),
        "relative_definition": "max_c |sum_f SHAP[f,c] - (f(x)_c - E[f]_c)| / max_c |f(x)_c - E[f]_c|",
        "raw_values_sha256": raw_hash,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": round(time.time() - t0, 1),
    }
    if limit is None:
        (out_dir / cfg["summary_filename"]).write_text(json.dumps(summary, indent=2) + "\n")
    log.info("WROTE %s\n%s", out_path, json.dumps(summary, indent=2))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None,
                        help="TEST ONLY: explain the first N selected rows into <output>_limitN.npz; no summary JSON.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    build(limit=args.limit)


if __name__ == "__main__":
    main()
