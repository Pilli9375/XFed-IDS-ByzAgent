"""Loads the frozen federated global model for the Phase 2 dashboard backend
and verifies it reproduces the reported numbers before anything is served.

Read-only against results/, docs/, and federated/. Every path, tag, and
tolerance used here lives in configs/backend.yaml -- see that file for the
verification contract this module implements.

Place at: backend/model_loader.py
"""

from __future__ import annotations

import hashlib
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = _PROJECT_ROOT  # public: other backend modules resolve paths against this
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Reused verbatim from the canonical training/eval code, not reimplemented --
# a second copy of the scaler-fit or metrics formula is exactly the kind of
# silent drift this module exists to catch. See src/train/centralized.py's
# own "duplicated from ..." precedent for the one function (predict) small
# enough that importing it isn't worth the coupling either way -- copied here
# instead, kept in sync deliberately.
from src.data.schema import (  # noqa: E402
    class_names,
    derive_feature_cols,
    encode_families,
    headline_class_indices,
    load_label_vocabulary,
    load_yaml,
)
from src.models.mlp import build_model  # noqa: E402
from src.train.metrics import compute_metrics  # noqa: E402

log = logging.getLogger(__name__)


@dataclass
class LoadedModel:
    """Everything the rest of the backend needs to serve predictions."""

    model: nn.Module
    scaler: StandardScaler
    scaler_sha256: str
    feature_cols: list[str]
    class_names: list[str]
    headline_idx: np.ndarray
    model_cfg: dict
    tag: str
    alpha: str
    seed: int
    best_round: int
    device: str


@torch.no_grad()
def _predict(model: nn.Module, X: torch.Tensor, batch_size: int = 8192) -> torch.Tensor:
    """Batched inference. Duplicated from src/train/centralized.py (8 lines --
    not worth importing a training-script module into the serving path)."""
    model.eval()
    out = []
    for i in range(0, len(X), batch_size):
        out.append(model(X[i : i + batch_size]).argmax(dim=1))
    return torch.cat(out)


def resolve_path(cfg_paths: dict, key: str) -> Path:
    """Public: main.py resolves its own config-driven paths (SHAP, CSVs)
    through this, so there is exactly one place project-root-relative
    resolution happens."""
    return _PROJECT_ROOT / cfg_paths[key]


# Old private name, kept as an alias so load_and_verify() below doesn't need
# a mechanical rename.
_resolve = resolve_path


def load_backend_config(backend_config_path: str | Path = "configs/backend.yaml") -> dict:
    """Public: main.py loads the same configs/backend.yaml through this,
    so there is exactly one YAML-loading path for backend config."""
    return load_yaml(_PROJECT_ROOT / backend_config_path)


def _load_manifest_entry(manifest_path: Path, tag: str) -> dict:
    import json

    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, list):
        raise RuntimeError(f"{manifest_path} is not a list of run entries.")
    for entry in manifest:
        if entry.get("tag") == tag:
            return entry
    known = sorted(e.get("tag") for e in manifest)
    raise RuntimeError(f"tag {tag!r} not found in {manifest_path}. Known tags: {known}")


def _load_round_history_entry(federated_results_dir: Path, tag: str, best_round: int) -> dict:
    import json

    path = federated_results_dir / tag / "round_history.json"
    history = json.loads(path.read_text())
    for entry in history:
        if entry.get("round") == best_round:
            return entry
    raise RuntimeError(f"round {best_round} not found in {path}.")


def _assert_architecture(state_dict: dict, model_cfg: dict) -> None:
    """Checks the checkpoint's shape against configs/model.yaml before a
    single tensor is loaded into a live model, so a mismatch fails with a
    specific reason instead of an opaque strict-load key-mismatch error."""
    m = model_cfg["model"]
    hidden_dims = [int(h) for h in m["hidden_dims"]]
    input_dim = int(m["input_dim"])
    n_classes = int(model_cfg["labels"]["n_classes"])

    if str(m["norm"]) != "layernorm":
        raise RuntimeError(
            f"configs/model.yaml model.norm={m['norm']!r}, expected 'layernorm'. "
            f"model_loader.py only knows how to verify the locked LayerNorm "
            f"architecture (src/models/mlp.py)."
        )

    bn_stat_suffixes = ("running_mean", "running_var", "num_batches_tracked")
    bn_keys = [k for k in state_dict if k.endswith(bn_stat_suffixes)]
    if bn_keys:
        raise RuntimeError(
            f"Checkpoint carries BatchNorm running-stat keys {bn_keys}. FedAvg "
            f"cannot average those meaningfully across silos with differing "
            f"input distributions (see src/models/mlp.py docstring) -- this "
            f"checkpoint was not produced by the locked LayerNorm architecture."
        )

    # net.<4*i+1> is the LayerNorm after hidden layer i, matching
    # src/models/mlp.py's [Linear, LayerNorm, activation, Dropout] block.
    expected_ln_keys = {
        f"net.{4 * i + 1}.{p}" for i in range(len(hidden_dims)) for p in ("weight", "bias")
    }
    missing_ln = expected_ln_keys - set(state_dict)
    if missing_ln:
        raise RuntimeError(
            f"Checkpoint is missing expected LayerNorm keys {sorted(missing_ln)} "
            f"for hidden_dims={hidden_dims} (configs/model.yaml)."
        )

    first_w = state_dict.get("net.0.weight")
    if first_w is None or tuple(first_w.shape) != (hidden_dims[0], input_dim):
        raise RuntimeError(
            f"net.0.weight shape {None if first_w is None else tuple(first_w.shape)} "
            f"does not match configs/model.yaml input_dim={input_dim}, "
            f"hidden_dims[0]={hidden_dims[0]}."
        )

    last_key = f"net.{4 * len(hidden_dims)}.weight"
    last_w = state_dict.get(last_key)
    if last_w is None or tuple(last_w.shape) != (n_classes, hidden_dims[-1]):
        raise RuntimeError(
            f"{last_key} shape {None if last_w is None else tuple(last_w.shape)} "
            f"does not match configs/model.yaml n_classes={n_classes}, "
            f"hidden_dims[-1]={hidden_dims[-1]}."
        )


def _fit_scaler(train_pool_path: Path, val_mask_path: Path, feature_cols: list[str]):
    """Refit on train_pool.parquet MINUS val_mask.parquet -- matches
    configs/model.yaml preprocessing.fit_scope_centralized: train_split. A
    scaler fit on a different scope than the reported model is not
    acceptable for a serving path (see src/data/loaders.py:load_centralized,
    the canonical implementation of this exact scope, which this function
    deliberately does not call because it also reads test_global.parquet --
    forbidden here, see the val-only comment in load_and_verify)."""
    pool = pd.read_parquet(train_pool_path, columns=feature_cols + ["family"])
    pool[feature_cols] = pool[feature_cols].astype(np.float32)

    mask = pd.read_parquet(val_mask_path)["is_val"].to_numpy()
    if len(mask) != len(pool):
        raise RuntimeError(
            f"val_mask has {len(mask):,} rows but train_pool has {len(pool):,}. "
            f"The mask is positional; a length mismatch means it was built "
            f"against a different train_pool."
        )

    X_train = pool.loc[~mask, feature_cols].to_numpy(np.float32)
    scaler = StandardScaler().fit(X_train)
    return scaler, pool, mask


def load_and_verify(backend_config_path: str | Path = "configs/backend.yaml") -> LoadedModel:
    cfg = load_backend_config(backend_config_path)
    paths = cfg["paths"]
    model_tag = cfg["model"]["tag"]
    device = cfg["model"]["device"]
    verify_cfg = cfg["verify"]
    # This function only implements one verification contract: full val
    # split, compared against round_history.json. Fail loudly rather than
    # silently ignoring a backend.yaml edit that asks for something else.
    if verify_cfg["split"] != "val":
        raise RuntimeError(
            f"configs/backend.yaml verify.split={verify_cfg['split']!r} is not "
            f"implemented -- load_and_verify() only computes the val split "
            f"(test_global.parquet must never be read here)."
        )
    if verify_cfg["source"] != "round_history":
        raise RuntimeError(
            f"configs/backend.yaml verify.source={verify_cfg['source']!r} is not "
            f"implemented -- load_and_verify() only compares against round_history.json."
        )

    model_cfg = load_yaml(_resolve(paths, "model_config"))
    data_cfg = load_yaml(_resolve(paths, "data_config"))

    # 1. Resolve the tag against the best-rounds manifest.
    manifest_path = _resolve(paths, "best_rounds_manifest")
    entry = _load_manifest_entry(manifest_path, model_tag)
    best_round = int(entry["best_round"])
    log.info("resolved tag=%s best_round=%d via %s", model_tag, best_round, manifest_path)

    # 2. Load the checkpoint at that round. global_checkpoint is the
    # manifest's own resolved path -- reusing it (rather than re-deriving
    # round_{best_round:03d}.pt here) avoids a second, independently-wrong
    # filename format.
    checkpoint_path = _PROJECT_ROOT / entry["global_checkpoint"]
    if not checkpoint_path.exists():
        raise RuntimeError(f"checkpoint {checkpoint_path} (from {manifest_path}) does not exist.")
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    # 3. Assert state_dict matches configs/model.yaml before it touches a model.
    _assert_architecture(state_dict, model_cfg)
    model = build_model(model_cfg, seed=int(entry["seed"]), device=device)
    model.load_state_dict(state_dict)  # strict=True: also catches anything the checks above missed
    model.eval()
    log.info("loaded %s onto device=%s", checkpoint_path, device)

    # 4. Refit the StandardScaler on train_split (train_pool minus val_mask).
    train_pool_path = _resolve(paths, "train_pool")
    val_mask_path = _resolve(paths, "val_mask")
    cols = pq.ParquetFile(train_pool_path).schema_arrow.names
    feature_cols = derive_feature_cols(cols, data_cfg)

    scaler, pool, mask = _fit_scaler(train_pool_path, val_mask_path, feature_cols)
    expected_n_features = int(model_cfg["model"]["input_dim"])
    if scaler.n_features_in_ != expected_n_features:
        raise RuntimeError(
            f"scaler.n_features_in_={scaler.n_features_in_}, expected "
            f"{expected_n_features} (configs/model.yaml model.input_dim)."
        )
    scaler_hash = hashlib.sha256(scaler.mean_.tobytes() + scaler.scale_.tobytes()).hexdigest()
    log.info("scaler refit on train_split: n_features_in_=%d mean_/scale_ sha256=%s",
              scaler.n_features_in_, scaler_hash)

    # 5. Verify against round_history.json for this tag/round -- val split
    # ONLY. test_global.parquet is never read by this function: the test set
    # is spent and a per-boot check must not touch it.
    vocab = load_label_vocabulary(model_cfg)
    cnames = class_names(model_cfg)
    headline_idx = headline_class_indices(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])

    X_val = pool.loc[mask, feature_cols].to_numpy(np.float32)
    Xv_scaled = scaler.transform(X_val).astype(np.float32)
    y_val = encode_families(pool.loc[mask, "family"], vocab)

    Xv_tensor = torch.from_numpy(Xv_scaled.copy()).to(device)
    y_pred = _predict(model, Xv_tensor).cpu().numpy()
    metrics = compute_metrics(y_val, y_pred, n_classes, cnames, headline_idx)

    metric_name = verify_cfg["metric"]
    # round_history.json prefixes its keys with "val_"; compute_metrics()'s
    # return dict does not. Only these two are meaningful on a val split.
    metric_key_map = {"val_macro_f1_headline": "macro_f1_headline", "val_macro_f1_all": "macro_f1_all"}
    if metric_name not in metric_key_map:
        raise RuntimeError(
            f"configs/backend.yaml verify.metric={metric_name!r} is not implemented. "
            f"Supported: {sorted(metric_key_map)}."
        )
    computed = metrics[metric_key_map[metric_name]]
    federated_results_dir = _resolve(paths, "federated_results_dir")
    history_entry = _load_round_history_entry(federated_results_dir, model_tag, best_round)
    target = float(history_entry[metric_name])
    tolerance = float(verify_cfg["tolerance"])
    diff = abs(computed - target)

    if diff > tolerance:
        raise RuntimeError(
            f"Verification failed for tag={model_tag} round={best_round}: "
            f"recomputed {metric_name}={computed!r} on the full validation "
            f"split ({len(y_val):,} rows) vs "
            f"{federated_results_dir / model_tag / 'round_history.json'}"
            f"[round={best_round}].{metric_name}={target!r}. "
            f"diff={diff!r} exceeds tolerance={tolerance!r}."
        )
    log.info("verified: computed %s=%.10f target=%.10f diff=%.3e (tolerance=%.1e)",
              metric_name, computed, target, diff, tolerance)

    return LoadedModel(
        model=model,
        scaler=scaler,
        scaler_sha256=scaler_hash,
        feature_cols=feature_cols,
        class_names=cnames,
        headline_idx=headline_idx,
        model_cfg=model_cfg,
        tag=model_tag,
        alpha=str(entry["alpha"]),
        seed=int(entry["seed"]),
        best_round=best_round,
        device=device,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    loaded = load_and_verify()
    print(f"OK: tag={loaded.tag} best_round={loaded.best_round} device={loaded.device} "
          f"n_features={len(loaded.feature_cols)}")
