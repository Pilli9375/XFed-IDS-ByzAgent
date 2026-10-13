"""Traffic simulator for the Phase 2 dashboard demo.

Reads rows and POSTs each one to the backend's POST /predict, at a
configurable rate (configs/backend.yaml: simulator.*). The source is
simulator.source_split: "val_shap_pool" (default: the 500 validation rows of
results/shap/<tag>/val_pool.npz, replayed in stored order, every one with
precomputed SHAP), "val" (all rows of train_pool.parquet where
val_mask.is_val is true, no SHAP) or "test" (test_global.parquet). "test" is refused unless the served model's
checkpoint hash is in simulator.test_split_checkpoint_allowlist, which is
empty by default -- so no unsealed candidate (e.g. a hot-swapped model)
can ever show test-row correctness.

This is a display-traffic read, not an evaluation read: it never computes
or reports a metric. The dashboard marks each alert against its true label;
nothing is aggregated or selected from those marks. It is kept entirely
separate from backend/model_loader.py:load_and_verify(), which must never
touch test_global.parquet -- see that function's own val-only comment and
configs/backend.yaml's verify: block for why.

Runs as its own process, separate from the API server: it talks to the
backend over plain HTTP like any other client, so backend/main.py serves
/health, /config, /predict, /shap, /agreement, /parity normally whether or
not this is running. If this process is down, GET /alerts simply stops
growing (or stays empty, if it never ran).

Place at: backend/simulator.py
Run as:   python -m backend.simulator
"""

from __future__ import annotations

import hashlib
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import requests
import torch

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.model_loader import _load_manifest_entry, load_backend_config, resolve_path  # noqa: E402
from src.data.schema import derive_feature_cols, load_yaml  # noqa: E402

log = logging.getLogger(__name__)


def _load_demo_rows(
    cfg_paths: dict, shuffle_seed: int, source_split: str
) -> tuple[pd.DataFrame, list[str]]:
    """The read this module exists to isolate: source rows for the live
    traffic feed, not an evaluation set. feature_cols is derived the same
    way model_loader.py derives it (schema.derive_feature_cols), so a row
    posted here always matches what /predict expects.

    source_split "val": train_pool.parquet rows where val_mask.is_val is
    true (the same split load_and_verify() scores). Each row's pandas index
    is its position in train_pool.parquet; those positions are NOT
    test_global positions, so no SHAP id is ever claimed for them.
    source_split "test": test_global.parquet; the caller has already passed
    the checkpoint allowlist (see _require_test_split_allowed).

    Row order is permuted ONCE here with shuffle_seed, then replayed
    sequentially (and looped) by run() -- not resampled per tick. File
    order is chronological (CICIDS2017 day-files), so the first ~2,000 rows
    are 100% Benign; a fixed one-time shuffle fixes that without sampling
    with replacement (which would show repeated rows in a scrolling list)
    and without stratifying or curating the family mix (the natural
    distribution -- heavily Benign, like real traffic -- is the honest one
    to show).

    Deliberately does NOT reset_index after the shuffle: each row's pandas
    index stays its original parquet row position (for the test split,
    exactly the identifier results/shap/<tag>/streamed_pool.npz's sample_id
    array uses -- run() reads it straight off row.name)."""
    data_cfg = load_yaml(resolve_path(cfg_paths, "data_config"))
    if source_split == "val":
        src_path = resolve_path(cfg_paths, "train_pool")
    else:
        src_path = resolve_path(cfg_paths, "test_global")
    cols = pq.ParquetFile(src_path).schema_arrow.names
    feature_cols = derive_feature_cols(cols, data_cfg)
    df = pd.read_parquet(src_path, columns=feature_cols + ["family"])
    if source_split == "val":
        mask = pd.read_parquet(resolve_path(cfg_paths, "val_mask"))["is_val"].to_numpy(dtype=bool)
        if len(mask) != len(df):
            raise RuntimeError(
                f"val_mask has {len(mask):,} rows but train_pool has {len(df):,}; refusing to replay."
            )
        df = df[mask]

    order = np.random.default_rng(shuffle_seed).permutation(len(df))
    df = df.iloc[order]
    return df, feature_cols


def _load_val_shap_pool_rows(cfg_paths: dict, tag: str) -> tuple[pd.DataFrame, list[str]]:
    """source_split "val_shap_pool": exactly the rows in
    results/shap/<tag>/<shap_val_pool_filename> (tools/build_shap_val_pool.py),
    in the order stored there -- no shuffle, no resampling. Raw feature values
    and family come from the .npz itself, the same arrays the backend serves
    for /shap?source=val, so the posted row is by construction the explained
    row. The index is sample_id (the train_pool.parquet position)."""
    data_cfg = load_yaml(resolve_path(cfg_paths, "data_config"))
    feature_cols = derive_feature_cols(
        pq.ParquetFile(resolve_path(cfg_paths, "train_pool")).schema_arrow.names, data_cfg
    )
    pool_path = resolve_path(cfg_paths, "shap_dir") / tag / cfg_paths["shap_val_pool_filename"]
    if not pool_path.exists():
        raise FileNotFoundError(f"{pool_path} does not exist -- run `python -m tools.build_shap_val_pool` first.")
    with np.load(pool_path) as npz:
        if str(npz["source"]) != "val":
            raise RuntimeError(f"{pool_path} does not carry source='val'; refusing to replay it.")
        if list(npz["feature_names"]) != feature_cols:
            raise RuntimeError(f"{pool_path} feature order differs from train_pool.parquet's; refusing to replay.")
        df = pd.DataFrame(npz["raw_values"], columns=feature_cols, index=npz["sample_id"].astype(np.int64))
        df["family"] = npz["eval_families"].astype(str)
    log.info("loaded %d validation SHAP-pool rows from %s (stored order)", len(df), pool_path)
    return df, feature_cols


def _state_dict_sha256(state_dict: dict) -> str:
    """Same recipe as backend/hotswap_service.py and src/hotswap/retrain.py
    (the hash the hot-swap audit log records), duplicated here so the
    simulator does not import the backend service."""
    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode("utf-8"))
        h.update(state_dict[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _require_test_split_allowed(cfg: dict, session: requests.Session, backend_url: str) -> str:
    """Raises unless the model the backend is serving is a checkpoint whose
    state-dict sha256 is in simulator.test_split_checkpoint_allowlist.
    Returns the hash. Refuses when the allowlist is empty (the default), when
    the backend cannot be reached, or when a hot-swap is active (the swapped
    checkpoint's hash is not the base checkpoint's)."""
    allow = {str(h).lower() for h in (cfg["simulator"].get("test_split_checkpoint_allowlist") or [])}
    tag = str(cfg["model"]["tag"])
    entry = _load_manifest_entry(resolve_path(cfg["paths"], "best_rounds_manifest"), tag)
    ckpt = _PROJECT_ROOT / entry["global_checkpoint"]
    digest = _state_dict_sha256(torch.load(ckpt, map_location="cpu", weights_only=False))
    if digest.lower() not in allow:
        raise SystemExit(
            f"simulator.source_split='test' refused: checkpoint {ckpt.name} for tag {tag} has "
            f"state-dict sha256 {digest}, which is not in "
            f"simulator.test_split_checkpoint_allowlist ({len(allow)} entries). "
            f"Use source_split: val."
        )
    try:
        info = session.get(f"{backend_url}/config", timeout=5).json()
        hotswap_active = bool(info["hotswap"]["active"])
    except (requests.RequestException, KeyError, ValueError) as e:
        raise SystemExit(f"simulator.source_split='test' refused: could not read {backend_url}/config ({e}).")
    if hotswap_active:
        raise SystemExit(
            "simulator.source_split='test' refused: a hot-swapped model is active, so the "
            "served checkpoint is not the allowlisted base checkpoint."
        )
    return digest


def _load_streamed_pool_ids(cfg_paths: dict, tag: str) -> set[int]:
    """Reads ONLY the sample_id array out of results/shap/<tag>/
    streamed_pool.npz (Step 7, tools/build_shap_streamed_pool.py) -- the
    same file backend/main.py loads fully at startup, but the simulator
    only needs the id set to decide, per posted row, whether to claim
    shap_sample_id. Read once here, not re-read per tick."""
    shap_dir = resolve_path(cfg_paths, "shap_dir")
    pool_path = shap_dir / tag / cfg_paths["shap_streamed_pool_filename"]
    if not pool_path.exists():
        raise FileNotFoundError(
            f"{pool_path} does not exist -- run "
            f"`python -m tools.build_shap_streamed_pool --tag {tag}` first."
        )
    with np.load(pool_path) as npz:
        sample_id = npz["sample_id"].copy()
    ids = {int(s) for s in sample_id}
    log.info("loaded streamed SHAP pool ids from %s: %d rows", pool_path, len(ids))
    return ids


def run(backend_config_path: str | Path = "configs/backend.yaml") -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = load_backend_config(backend_config_path)
    sim_cfg = cfg["simulator"]

    backend_url = str(sim_cfg["backend_url"]).rstrip("/")
    rate = float(sim_cfg["rate_per_second"])
    loop = bool(sim_cfg["loop"])
    shuffle_seed = int(sim_cfg["shuffle_seed"])
    interval = 1.0 / rate if rate > 0 else 0.0

    tag = str(cfg["model"]["tag"])
    source_split = str(sim_cfg.get("source_split", "val")).lower()
    if source_split == "validation":
        source_split = "val"
    if source_split not in ("val_shap_pool", "val", "test"):
        raise SystemExit(f"simulator.source_split={source_split!r} must be 'val_shap_pool', 'val' or 'test'.")

    session = requests.Session()
    if source_split == "test":
        digest = _require_test_split_allowed(cfg, session, backend_url)
        log.warning("source_split=test allowed: checkpoint sha256 %s is allowlisted", digest)
    if source_split == "val_shap_pool":
        df, feature_cols = _load_val_shap_pool_rows(cfg["paths"], tag)
        split_file = f"{cfg['paths']['shap_val_pool_filename']} (validation rows, stored order)"
    else:
        df, feature_cols = _load_demo_rows(cfg["paths"], shuffle_seed, source_split)
        split_file = "test_global.parquet" if source_split == "test" else "train_pool.parquet (val_mask rows)"
        split_file += f", shuffled once with seed={shuffle_seed}"
    # The streamed SHAP pool is keyed by test_global positions, so it is only
    # meaningful for the test split; every val_shap_pool row has SHAP by
    # construction; rows of the full val split never claim a SHAP id.
    streamed_pool_ids = _load_streamed_pool_ids(cfg["paths"], tag) if source_split == "test" else set()
    shap_source = "val" if source_split == "val_shap_pool" else "test"
    n_rows = len(df)
    log.info(
        "loaded %d demo rows (%d features) from %s, rate=%.3f/s target=%s/predict",
        n_rows, len(feature_cols), split_file, rate, backend_url,
    )

    i = 0
    while True:
        if i >= n_rows:
            if not loop:
                log.info("reached end of the %s split (simulator.loop=false), stopping.", source_split)
                return
            i = 0

        row = df.iloc[i]
        # row.name is the row's original position in its source parquet
        # (preserved through the shuffle, see _load_demo_rows). For the test
        # split that is the identifier streamed_pool.npz's sample_id array
        # uses; for val_shap_pool it is val_pool.npz's sample_id (a
        # train_pool position); for the val split streamed_pool_ids is
        # empty, so has_shap is always False.
        if source_split == "test" and i > 0 and i % 50 == 0:
            _require_test_split_allowed(cfg, session, backend_url)
        source_position = int(row.name)
        has_shap = source_split == "val_shap_pool" or source_position in streamed_pool_ids
        payload = {
            "features": {c: float(row[c]) for c in feature_cols},
            "true_family": str(row["family"]),
            # Opt-in: the simulator is the one caller of /predict whose rows
            # are real replayed traffic with a source row behind them, so it
            # is the one caller that sets this. Everyone else defaults False.
            "record_alert": True,
            # Set when this exact row is in a precomputed SHAP pool: always
            # for val_shap_pool, ~500 of ~478k rows for test, never for val.
            # The backend re-validates this against its own loaded pool
            # before trusting it (see /predict).
            "shap_sample_id": source_position if has_shap else None,
            "shap_source": shap_source,
        }
        try:
            resp = session.post(f"{backend_url}/predict", json=payload, timeout=5)
            resp.raise_for_status()
            body = resp.json()
            log.info(
                "row=%d (%s pos=%d) true=%s predicted=%s confidence=%.4f%s",
                i, source_split, source_position, payload["true_family"], body["family"], body["confidence"],
                " [SHAP available]" if has_shap else "",
            )
        except requests.RequestException as e:
            # The backend being down or mid-restart is not this process's
            # problem to solve -- log and keep ticking, matching "the
            # backend serves normally whether or not [the simulator] is
            # running" applied in the other direction too.
            log.warning("POST %s/predict failed for row=%d: %s", backend_url, i, e)

        i += 1
        if interval > 0:
            time.sleep(interval)


if __name__ == "__main__":
    run()
