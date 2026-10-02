"""Traffic simulator for the Phase 2 dashboard demo.

Reads rows from test_global.parquet and POSTs each one to the backend's
POST /predict, at a configurable rate (configs/backend.yaml: simulator.*).

This is a demo-serving read of the test set, not an evaluation read: it
never computes or reports a metric, it only replays held-out rows as
example live traffic for the dashboard to show something moving. It is
kept entirely separate from backend/model_loader.py:load_and_verify(),
which must never touch test_global.parquet -- see that function's own
val-only comment and configs/backend.yaml's verify: block for why.

Runs as its own process, separate from the API server: it talks to the
backend over plain HTTP like any other client, so backend/main.py serves
/health, /config, /predict, /shap, /agreement, /parity normally whether or
not this is running. If this process is down, GET /alerts simply stops
growing (or stays empty, if it never ran).

Place at: backend/simulator.py
Run as:   python -m backend.simulator
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import requests

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.model_loader import load_backend_config, resolve_path  # noqa: E402
from src.data.schema import derive_feature_cols, load_yaml  # noqa: E402

log = logging.getLogger(__name__)


def _load_demo_rows(cfg_paths: dict, shuffle_seed: int) -> tuple[pd.DataFrame, list[str]]:
    """The demo-serving read this module exists to isolate: source rows for
    the live traffic feed, not an evaluation set. feature_cols is derived
    the same way model_loader.py derives it (schema.derive_feature_cols),
    so a row posted here always matches what /predict expects.

    Row order is permuted ONCE here with shuffle_seed, then replayed
    sequentially (and looped) by run() -- not resampled per tick. File
    order is chronological (CICIDS2017 day-files), so the first ~2,000 rows
    are 100% Benign; a fixed one-time shuffle fixes that without sampling
    with replacement (which would show repeated rows in a scrolling list)
    and without stratifying or curating the family mix (the natural
    distribution -- heavily Benign, like real traffic -- is the honest one
    to show).

    Deliberately does NOT reset_index after the shuffle (Step 7): each
    row's pandas index stays its original test_global.parquet row
    position, which is exactly the identifier results/shap/<tag>/
    streamed_pool.npz's sample_id array uses -- run() reads it straight off
    row.name rather than tracking a second parallel array."""
    data_cfg = load_yaml(resolve_path(cfg_paths, "data_config"))
    test_path = resolve_path(cfg_paths, "test_global")
    cols = pq.ParquetFile(test_path).schema_arrow.names
    feature_cols = derive_feature_cols(cols, data_cfg)
    df = pd.read_parquet(test_path, columns=feature_cols + ["family"])

    order = np.random.default_rng(shuffle_seed).permutation(len(df))
    df = df.iloc[order]
    return df, feature_cols


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
    df, feature_cols = _load_demo_rows(cfg["paths"], shuffle_seed)
    streamed_pool_ids = _load_streamed_pool_ids(cfg["paths"], tag)
    n_rows = len(df)
    log.info(
        "loaded %d demo rows (%d features) from test_global.parquet, shuffled once with seed=%d, "
        "rate=%.3f/s target=%s/predict",
        n_rows, len(feature_cols), shuffle_seed, rate, backend_url,
    )

    session = requests.Session()
    i = 0
    while True:
        if i >= n_rows:
            if not loop:
                log.info("reached end of test_global.parquet (simulator.loop=false), stopping.")
                return
            i = 0

        row = df.iloc[i]
        # row.name is the row's original position in test_global.parquet
        # (preserved through the shuffle, see _load_demo_rows) -- the exact
        # identifier streamed_pool.npz's sample_id array uses.
        test_global_position = int(row.name)
        has_shap = test_global_position in streamed_pool_ids
        payload = {
            "features": {c: float(row[c]) for c in feature_cols},
            "true_family": str(row["family"]),
            # Opt-in: the simulator is the one caller of /predict whose rows
            # are real replayed traffic with a source row behind them, so it
            # is the one caller that sets this. Everyone else defaults False.
            "record_alert": True,
            # Only set when this exact row is one of the 500 in the
            # streamed pool -- ~500 of ~478k rows, so almost always None.
            # The backend re-validates this against its own loaded pool
            # before trusting it (see /predict).
            "shap_sample_id": test_global_position if has_shap else None,
        }
        try:
            resp = session.post(f"{backend_url}/predict", json=payload, timeout=5)
            resp.raise_for_status()
            body = resp.json()
            log.info(
                "row=%d (test_global pos=%d) true=%s predicted=%s confidence=%.4f%s",
                i, test_global_position, payload["true_family"], body["family"], body["confidence"],
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
