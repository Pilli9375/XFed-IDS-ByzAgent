#!/usr/bin/env python
"""One-time offline script: builds a larger SHAP pool for the dashboard's
streamed simulator alerts, so GET /shap/{sample_id} isn't limited to the 14
curated rows with no link back to test_global.parquet.

500 rows, stratified across the 7 headline families (Heartbleed/Infiltration
excluded -- same exclusion as configs/model.yaml's headline_classes
everywhere else in this project), sampled from test_global.parquet.
GradientExplainer is run once per row (not batched) -- CPU, per project
history that CPU beat GPU for this workload. Same reuse discipline as
tools/build_shap_eval_sidecar.py: the model, background, and scaler all come
from app_lib/loaders.py's canonical functions, and the stratification
algorithm is reused directly from tools/local_shap_pipeline.py (the same
code that built the original 14-row eval set) rather than reimplemented.

Writes results/shap/<tag>/streamed_pool.npz -- a NEW file. Does not open
global_shap.npz or eval_rows_sidecar.npz for writing; the explanation check's SHAP
artifacts and the Step 6 eval sidecar are both untouched.

sample_id in the output is each row's POSITION in test_global.parquet (its
pandas index after a plain pd.read_parquet, which is exactly the file's own
row order) -- NOT a fresh 0..499 index. This is what lets
backend/simulator.py recognize "this streamed row happens to be one of the
500" and what lets GET /shap/{sample_id} look it up.

This is a deliberate, logged, one-time read of data/processed/test_global.parquet,
same audit posture as build_shap_eval_sidecar.py -- read that script's
docstring for why this file is otherwise off-limits everywhere else in the
backend.

Run as: python -m tools.build_shap_streamed_pool --tag fedavg_a0.5_s42
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shap
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_lib.loaders import (  # noqa: E402
    get_centralized_splits,
    get_feature_cols,
    get_federated_global_background,
    get_label_vocab,
    load_global_model_for_config,
)
from src.data.schema import derive_feature_cols, load_yaml  # noqa: E402
from tools.local_shap_pipeline import NSAMPLES, build_stratified_background  # noqa: E402

SHAP_ROOT = ROOT / "results" / "shap"
TEST_GLOBAL_PATH = ROOT / "data" / "processed" / "test_global.parquet"
TRAIN_POOL_PATH = ROOT / "data" / "processed" / "train_pool.parquet"

POOL_SIZE = 500
# Distinct from tools/eval_set_config.py's EVAL_SEED -- a different pool,
# deliberately not reusing that seed so the two artifacts can never be
# mistaken for drawing the same 14/500 rows.
STREAMED_POOL_SEED = 5005

log = logging.getLogger("build_shap_streamed_pool")


def _verify_feature_order(feature_cols_from_test_global: list[str]) -> None:
    """Same check as build_shap_eval_sidecar.py's -- get_feature_cols()
    derives order from test_global.parquet's schema, but the live backend's
    /shap reports feature_names derived from train_pool.parquet's schema
    (backend/model_loader.py). Confirmed empirically equal in Step 6;
    re-asserted here on every run rather than assumed."""
    train_pool_cols = pq.ParquetFile(TRAIN_POOL_PATH).schema_arrow.names
    data_cfg = load_yaml(ROOT / "configs" / "data.yaml")
    backend_order = derive_feature_cols(train_pool_cols, data_cfg)
    if backend_order != feature_cols_from_test_global:
        raise RuntimeError(
            "Feature order mismatch between train_pool.parquet-derived order "
            "(what /shap reports as feature_names) and test_global.parquet-derived "
            "order (what this pool's raw_values columns are in). Refusing to write."
        )
    log.info("feature order verified (%d features)", len(feature_cols_from_test_global))


def _select_pool_rows(model_cfg: dict, data_cfg: dict) -> tuple[pd.DataFrame, list[str], np.ndarray]:
    """Reads test_global.parquet ONCE, filters to the 7 headline families,
    and stratified-samples POOL_SIZE rows via the exact algorithm
    tools/local_shap_pipeline.py used for the original eval set. Returns
    (full headline-only frame, feature_cols, sample_id array of ORIGINAL
    test_global.parquet row positions) -- df's index is untouched (never
    reset), so it IS the row position throughout."""
    feature_cols = get_feature_cols()
    _verify_feature_order(feature_cols)

    headline = list(model_cfg["labels"]["headline_classes"])
    log.info("reading %s once for headline-family rows (%s)", TEST_GLOBAL_PATH, headline)
    df = pd.read_parquet(TEST_GLOBAL_PATH, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)

    headline_df = df[df["family"].isin(headline)]
    log.info("headline-family rows available: %d (of %d total)", len(headline_df), len(df))

    # build_stratified_background never reads its X argument -- only y, for
    # np.unique/np.where -- so passing None is safe and avoids copying the
    # feature matrix just to satisfy the signature.
    local_idx = build_stratified_background(
        X=None, y=headline_df["family"].to_numpy(), target_total=POOL_SIZE, seed=STREAMED_POOL_SEED
    )
    # local_idx indexes headline_df's own positional array; headline_df.index
    # (preserved through the boolean mask, never reset) is the true
    # test_global.parquet row position for each of those positions.
    sample_id = headline_df.index.to_numpy()[local_idx]
    if len(sample_id) != POOL_SIZE:
        raise RuntimeError(f"stratified sample returned {len(sample_id)} rows, expected {POOL_SIZE}")
    if len(set(sample_id.tolist())) != POOL_SIZE:
        raise RuntimeError("stratified sample contains duplicate test_global.parquet row positions")

    return df, feature_cols, sample_id


def _explain_pool(
    model: torch.nn.Module,
    background: np.ndarray,
    X_scaled: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """GradientExplainer's computation run once per row (X_scaled.shape[0]
    separate .shap_values() calls) -- CPU, per project history that CPU
    beat GPU for this workload. The explainer object itself is built once
    (background is fixed across all rows, matching the original pipeline's
    per-config-not-per-row background), only the per-row sampling repeats.
    Returns (shap_values[n,82,9], additivity_max_diff[n])."""
    background_t = torch.from_numpy(background.copy())
    explainer = shap.GradientExplainer(model, background_t)

    with torch.no_grad():
        f_bg_mean = model(background_t).numpy().mean(axis=0)

    n = X_scaled.shape[0]
    shap_values = np.empty((n, X_scaled.shape[1], f_bg_mean.shape[0]), dtype=np.float32)
    additivity = np.empty(n, dtype=np.float32)

    t0 = time.time()
    for i in range(n):
        eval_t = torch.from_numpy(X_scaled[i : i + 1].copy())
        sv = np.array(explainer.shap_values(eval_t, nsamples=NSAMPLES))  # (1, 82, 9)
        with torch.no_grad():
            f_eval = model(eval_t).numpy()  # (1, 9)
        diff = sv.sum(axis=1) - (f_eval - f_bg_mean[None, :])  # (1, 9)
        shap_values[i] = sv[0]
        additivity[i] = float(np.abs(diff).max())

        if (i + 1) % 50 == 0 or (i + 1) == n:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            log.info("explained %d/%d rows (%.2fs/row, elapsed=%.1fs, eta=%.1fs)",
                      i + 1, n, elapsed / (i + 1), elapsed, (n - i - 1) / rate if rate > 0 else float("nan"))

    return shap_values, additivity


def build_pool(tag: str, limit: int | None = None) -> Path:
    t0 = time.time()
    data_cfg = load_yaml(ROOT / "configs" / "data.yaml")
    model_cfg = load_yaml(ROOT / "configs" / "model.yaml")
    vocab_info = get_label_vocab()

    df, feature_cols, sample_id = _select_pool_rows(model_cfg, data_cfg)
    if limit is not None:
        log.warning("--limit %d set: truncating the pool for a test run, NOT the real 500-row artifact", limit)
        sample_id = sample_id[:limit]

    rows = df.loc[sample_id]
    X_raw = rows[feature_cols].to_numpy(np.float32)
    eval_y = rows["family"].map(vocab_info["vocab"]).to_numpy(np.int64)
    eval_families = rows["family"].to_numpy()
    log.info("selected %d rows, family counts: %s", len(sample_id),
              {f: int((eval_families == f).sum()) for f in sorted(set(eval_families.tolist()))})

    model, entry = load_global_model_for_config(tag)
    log.info("loaded global model for tag=%s, best_round=%d", tag, entry["best_round"])

    splits = get_centralized_splits()
    X_scaled = ((X_raw - splits.scaler_center) / splits.scaler_scale).astype(np.float32)

    background = get_federated_global_background()
    log.info("background: %d rows (fixed seed 777, pooled centralized X_train -- same as "
              "build_shap_eval_sidecar.py's base_values background)", len(background))

    shap_values, additivity = _explain_pool(model, background, X_scaled)

    class_names = [vocab_info["idx_to_name"][i] for i in range(vocab_info["n_classes"])]
    raw_hash = hashlib.sha256(np.ascontiguousarray(X_raw).tobytes()).hexdigest()

    out_dir = SHAP_ROOT / tag
    if not out_dir.exists():
        raise FileNotFoundError(f"{out_dir} does not exist -- no global_shap.npz for tag={tag!r}?")
    out_path = out_dir / "streamed_pool.npz"
    np.savez(
        out_path,
        shap_values=shap_values,
        sample_id=sample_id,
        raw_values=X_raw,
        feature_names=np.array(feature_cols, dtype="<U64"),
        class_names=np.array(class_names, dtype="<U32"),
        eval_y=eval_y,
        eval_families=np.array(eval_families, dtype="<U32"),
        additivity_max_diff=additivity,
    )

    elapsed = time.time() - t0
    log.info(
        "WROTE %s | tag=%s | rows=%d | seed=%d | source=%s | sample_id range=[%d, %d] | "
        "raw_values sha256=%s | mean additivity_max_diff=%.4f | elapsed=%.1fs (%.2fmin)",
        out_path, tag, len(sample_id), STREAMED_POOL_SEED, TEST_GLOBAL_PATH,
        int(sample_id.min()), int(sample_id.max()), raw_hash, float(additivity.mean()),
        elapsed, elapsed / 60,
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="e.g. fedavg_a0.5_s42")
    parser.add_argument("--limit", type=int, default=None,
                         help="TEST ONLY: explain only the first N of the 500 selected rows.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    build_pool(args.tag, limit=args.limit)


if __name__ == "__main__":
    main()
