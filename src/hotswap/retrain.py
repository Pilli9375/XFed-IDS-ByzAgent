"""Hot-swap retraining service -- Step 2A (see PROJECT_INSTRUCTIONS.md and
the design writeup in this project's session history).

Flow: an analyst confirms or rejects a live alert, which supplies a FAMILY
LABEL (never a feature vector -- see the note on why below). That label
drives a short, warm-started federated continuation over the 10 existing
silos. The result only replaces the served model if it does not regress a
strict validation gate; otherwise nothing changes and nothing is logged
(see run_hotswap()'s return contract).

Why this never reads test_global.parquet, structurally, not by discipline:
backend/main.py's Alert model (checked directly, not assumed) stores only
`timestamp`, `predicted_family`, `confidence`, `true_family`,
`shap_available` -- the 82-feature vector /predict computes a prediction
from is a local variable inside that function and never reaches the alert
buffer. So "a confirmed alert" can only ever supply a family name to this
module, never a row. This module deliberately does not add feature-vector
storage anywhere to make its own job easier -- do not add it. Every sample
this module trains on is instead resolved to a real position in
data/processed/train_pool.parquet (see select_new_sample_ids()), which is
exactly what src/hotswap/audit_log.py's sample_ids field already requires
and can verify.

Per-silo local training deliberately duplicates
federated/xfed_federated/task.py's local_train_epochs() (~15 lines) rather
than importing it: that module lives under federated/xfed_federated/,
which Flower's Simulation Runtime copies into an ISOLATED environment with
its own dependency install (see that module's own docstring) -- it cannot
be imported from the project's normal src/ tree, and invoking the full
Flower simulation runtime for a short, live-triggered hot-swap round would
be exactly the wrong tool (that runtime is for the from-scratch, 20-round,
10-silo experimental sweeps under results/federated/). This module runs
the same FedAvg math directly, in-process, against the already-loaded
warm-start checkpoint.

Similarly, src/data/loaders.py's load_silo() and load_centralized() cannot
be reused here even though they do almost exactly what per-silo loading
needs: both unconditionally read data/processed/test_global.parquet as
part of building a Splits object (to populate X_test/y_test), even when
the caller never touches those fields. This module reads ONLY
train_pool.parquet and val_mask.parquet -- see _load_silo_train_arrays()
and _pooled_val_split().

Place at: src/hotswap/retrain.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
import torch.nn as nn

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.loaders import _apply_scaler, _fit_scaler, _read_frame  # noqa: E402
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
from src.hotswap import audit_log as hs  # noqa: E402

# model_loader.py's pooled-scaler fit (train_pool minus val_mask, NEVER
# test_global.parquet -- confirmed by reading it) is exactly the global,
# non-per-silo validation-gate procedure this module needs, and it's
# already the procedure that produced every best_val_macro_f1_headline
# this module compares against. Importing it (rather than writing a second
# copy) means the gate and the incumbent's own recorded number were
# computed identically.
from backend.model_loader import _fit_scaler as _fit_pooled_scaler  # noqa: E402

# model_loader.py's metric-key mapping: round_history.json / best_rounds_
# manifest.json key their metric "val_macro_f1_headline"; compute_metrics()
# returns it as "macro_f1_headline". Same translation, same reason.
_METRIC_KEY_MAP = {"val_macro_f1_headline": "macro_f1_headline", "val_macro_f1_all": "macro_f1_all"}


class HotSwapGateRejected(Exception):
    """Raised (not silently swallowed) when no candidate round clears the
    validation gate. Caller decides what to do with a rejection; this
    module never swaps or logs on this path."""


# --------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------- #

def load_hotswap_config(path: str | Path = "configs/hotswap.yaml") -> dict:
    return load_yaml(hs.PROJECT_ROOT / path)


def _load_global_class_weights(model_cfg: dict, path: Path) -> np.ndarray:
    """Same weights every silo must use identically -- duplicated from
    federated/xfed_federated/task.py::load_global_class_weights() for the
    same isolated-environment reason documented at the top of this file."""
    data = json.loads(path.read_text())
    vocab = load_label_vocabulary(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])
    arr = np.zeros(n_classes, dtype=np.float32)
    for name, idx in vocab.items():
        if name not in data["weights"]:
            raise KeyError(f"{name} missing from {path}. Re-run scripts/export_class_weights.py.")
        arr[idx] = data["weights"][name]
    return arr


# --------------------------------------------------------------------- #
# Target-silo and sample selection
# --------------------------------------------------------------------- #

def select_target_silo(manifest: dict, alpha: str, seed: int, family: str) -> int:
    """ENGINEERING CHOICE for the live Phase-2 system, NOT a research
    finding -- must never appear in or near the explanation-parity
    (Contribution A) narrative. Signed off explicitly: routes a
    confirmed sample to whichever of the 10 existing silos ALREADY has the
    highest Dirichlet-drawn share of this family (manifest.json's own
    dirichlet_proportions_train, already computed at partition time -- no
    new statistic). Rationale is purely operational: under this project's
    non-IID partition each family is already concentrated in a few silos by
    construction, so reinforcing the silo that already specializes in a
    family keeps the live system's behavior legible (you can look at that
    one silo's local metrics before/after and see the effect) without
    touching the other 9 silos' frozen, hash-verified base partitions at
    all. It says nothing about explanation parity, agreement, or any
    Contribution A measurement.
    """
    tag = f"a{alpha}_s{seed}"
    cfg = manifest.get("configs", {}).get(tag)
    if cfg is None:
        raise ValueError(f"{tag!r} not found in manifest.json configs. Known: {sorted(manifest.get('configs', {}))}")
    props = cfg.get("dirichlet_proportions_train", {}).get(family)
    if props is None:
        raise ValueError(f"family {family!r} not found in {tag}'s dirichlet_proportions_train")
    return int(np.argmax(props))


def select_new_sample_ids(
    family_col: pd.Series,
    val_mask: np.ndarray,
    base_assign: np.ndarray,
    family: str,
    target_silo: int,
    n_requested: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Positions (0-based, into train_pool.parquet) of family-matching rows
    that (a) are not in the frozen validation split -- a candidate round
    must never be validated on rows it just trained on -- and (b) are not
    already part of target_silo's own base partition, so this is a genuine
    new exposure for that silo rather than a no-op resample of data it
    already has. Never test_global.parquet: this function's only inputs
    are train_pool-derived arrays, positionally aligned to it.

    Capped to whatever is eligible, never padded -- some families have too
    few rows to reach n_requested at all (Heartbleed: 8 rows total).
    """
    eligible = (family_col.to_numpy() == family) & (~val_mask) & (base_assign != target_silo)
    idx = np.flatnonzero(eligible)
    if len(idx) == 0:
        raise ValueError(
            f"no eligible train_pool rows for family={family!r}: none exist outside silo "
            f"{target_silo} and outside the validation split"
        )
    n = min(n_requested, len(idx))
    chosen = rng.choice(idx, size=n, replace=False)
    return np.sort(chosen).astype(int)


# --------------------------------------------------------------------- #
# Data loading -- train_pool.parquet + val_mask.parquet ONLY, never
# test_global.parquet (see module docstring for why load_silo()/
# load_centralized() are not reused here).
# --------------------------------------------------------------------- #

def _read_pool_and_masks(feature_cols: list[str], alpha: str, base_seed: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    pool = _read_frame(hs.TRAIN_POOL_PATH, feature_cols)
    val_mask = pd.read_parquet(hs.PROJECT_ROOT / "data" / "processed" / "val_mask.parquet")["is_val"].to_numpy()
    base_assign = pd.read_parquet(
        hs.PARTITIONS_DIR / f"assign_a{alpha}_s{base_seed}_train.parquet"
    )["silo"].to_numpy()
    for name, arr in (("val_mask", val_mask), ("base_assign", base_assign)):
        if len(arr) != len(pool):
            raise ValueError(f"{name} has {len(arr):,} rows, train_pool has {len(pool):,}")
    return pool, val_mask, base_assign


def _silo_train_arrays(
    pool: pd.DataFrame,
    base_assign: np.ndarray,
    val_mask: np.ndarray,
    silo_id: int,
    feature_cols: list[str],
    model_cfg: dict,
    vocab: dict[str, int],
    extra_row_positions: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, int]:
    """One silo's scaled (X, y) training arrays, scaler fit on exactly this
    silo's rows (fit_scope_federated: per_silo_train, matching
    configs/model.yaml). extra_row_positions (only for the target silo) are
    included in the fit -- the scaler must see the new rows too, not be
    reused stale from the base run."""
    mine = (base_assign == silo_id) & (~val_mask)
    rows = pool[mine]
    if extra_row_positions is not None and len(extra_row_positions) > 0:
        rows = pd.concat([rows, pool.iloc[extra_row_positions]], axis=0)

    X = rows[feature_cols].to_numpy(np.float32)
    y = encode_families(rows["family"], vocab)

    pre = model_cfg["preprocessing"]
    scaler, clip_lo, clip_hi, _ = _fit_scaler(X, pre["scaler"], feature_cols, tuple(pre["clip_percentiles"]))
    Xs = _apply_scaler(X, scaler, clip_lo, clip_hi)
    return Xs, y, len(y)


def _pooled_val_split(feature_cols: list[str], model_cfg: dict, vocab: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    """The SAME procedure backend/model_loader.py uses to verify a served
    model: StandardScaler fit on train_pool minus val_mask (pooled, not
    per-silo), applied to the val split. Reused via import (not duplicated)
    specifically so the hot-swap gate and the incumbent's own recorded
    best_val_macro_f1_headline are computed by the identical code path."""
    val_mask_path = hs.PROJECT_ROOT / "data" / "processed" / "val_mask.parquet"
    scaler, pool, mask = _fit_pooled_scaler(hs.TRAIN_POOL_PATH, val_mask_path, feature_cols)
    X_val = pool.loc[mask, feature_cols].to_numpy(np.float32)
    Xv_scaled = scaler.transform(X_val).astype(np.float32)
    y_val = encode_families(pool.loc[mask, "family"], vocab)
    return Xv_scaled, y_val


# --------------------------------------------------------------------- #
# FedAvg-lite: local training + aggregation, run in-process (not via
# Flower's Simulation Runtime -- see module docstring).
# --------------------------------------------------------------------- #

def local_train_epochs(
    model: nn.Module, X: np.ndarray, y: np.ndarray, class_weights: np.ndarray,
    model_cfg: dict, epochs: int, mu: float, device: str,
) -> dict:
    """One silo's local training from whatever global weights are already
    loaded into `model`. Mirrors federated/xfed_federated/task.py's
    local_train_epochs() exactly (same math, same FedProx mu>0 handling) --
    duplicated, not imported, per the module docstring."""
    Xt = torch.from_numpy(X.copy()).to(device)
    yt = torch.from_numpy(y.copy()).to(device)
    wt = torch.from_numpy(class_weights.copy()).to(device)

    global_params = [p.detach().clone() for p in model.parameters()] if mu > 0 else None

    tr = model_cfg["training"]
    criterion = nn.CrossEntropyLoss(weight=wt)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(tr["lr"]), weight_decay=float(tr["weight_decay"]))
    batch_size = int(tr["batch_size"])
    n = len(yt)

    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n, device=device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(Xt[idx]), yt[idx])
            if mu > 0:
                prox = sum(((p - gp) ** 2).sum() for p, gp in zip(model.parameters(), global_params))
                loss = loss + (mu / 2.0) * prox
            loss.backward()
            optimizer.step()

    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def fedavg_aggregate(state_dicts: list[dict], n_samples: list[int]) -> dict:
    """Standard FedAvg weighted average by sample count -- the same
    aggregation every strategy in this project starts from
    (PROJECT_INSTRUCTIONS.md: 'Start with FedAvg')."""
    total = float(sum(n_samples))
    weights = [n / total for n in n_samples]
    keys = state_dicts[0].keys()
    agg = {}
    for k in keys:
        acc = sum(w * sd[k].float() for w, sd in zip(weights, state_dicts))
        agg[k] = acc.to(state_dicts[0][k].dtype)
    return agg


def _state_dict_sha256(state_dict: dict) -> str:
    """Canonical hash: sorted keys, raw tensor bytes -- same style as
    model_loader.py's scaler hash (mean_/scale_ .tobytes()), robust against
    non-deterministic pickle serialization the way hashing torch.save()'s
    output directly would not be."""
    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode("utf-8"))
        h.update(state_dict[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


# --------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------- #

def run_hotswap(
    confirmed_family: str,
    seed: int,
    source_model_tag: str,
    config_path: str | Path = "configs/hotswap.yaml",
) -> dict:
    """Runs one warm-started hot-swap candidate and, only if it clears the
    strict non-regression gate, persists its checkpoint and appends the
    audit record.

    Returns the written audit record (src/hotswap/audit_log.py schema) on
    acceptance. Raises HotSwapGateRejected (nothing written, nothing
    swapped, no audit entry -- see the design writeup for why a rejected
    attempt is not an "event") if no candidate round clears the gate.
    """
    cfg = load_hotswap_config(config_path)
    model_cfg = load_yaml(hs.PROJECT_ROOT / cfg["paths"]["model_config"])
    data_cfg = load_yaml(hs.PROJECT_ROOT / cfg["paths"]["data_config"])
    manifest = json.loads(hs.MANIFEST_PATH.read_text())
    vocab = load_label_vocabulary(model_cfg)

    source_cfg_path = hs.FEDERATED_RESULTS_DIR / source_model_tag / "config.json"
    source_cfg = json.loads(source_cfg_path.read_text())
    alpha, base_seed = str(source_cfg["alpha"]), int(source_cfg["seed"])

    best_rounds_manifest = json.loads((hs.PROJECT_ROOT / cfg["paths"]["best_rounds_manifest"]).read_text())
    source_entry = next((e for e in best_rounds_manifest if e["tag"] == source_model_tag), None)
    if source_entry is None:
        raise ValueError(f"{source_model_tag!r} not found in {cfg['paths']['best_rounds_manifest']}")
    source_round = int(source_entry["best_round"])
    incumbent_metric = float(source_entry["best_val_macro_f1_headline"])
    print(f"[hotswap] source={source_model_tag} round={source_round} "
          f"incumbent {cfg['verify']['metric']}={incumbent_metric:.4f}")

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    target_silo = select_target_silo(manifest, alpha, base_seed, confirmed_family)
    print(f"[hotswap] confirmed_family={confirmed_family!r} -> target_silo={target_silo} "
          f"(highest existing dirichlet_proportions_train share, an engineering choice -- "
          f"see select_target_silo() docstring)")

    feature_cols = derive_feature_cols(pq.ParquetFile(hs.TRAIN_POOL_PATH).schema_arrow.names, data_cfg)
    pool, val_mask, base_assign = _read_pool_and_masks(feature_cols, alpha, base_seed)

    n_requested = int(cfg["candidate_selection"]["samples_per_event"])
    sample_ids = select_new_sample_ids(
        pool["family"], val_mask, base_assign, confirmed_family, target_silo, n_requested, rng
    )
    sample_silo = [int(target_silo)] * len(sample_ids)
    print(f"[hotswap] selected {len(sample_ids)}/{n_requested} requested new rows "
          f"for silo {target_silo} (capped by eligibility, never padded)")

    class_weights = _load_global_class_weights(model_cfg, hs.PROJECT_ROOT / cfg["paths"]["global_class_weights"])

    n_silos = int(manifest["n_silos"])
    device = str(cfg["training"]["device"])
    silo_arrays: dict[int, tuple[np.ndarray, np.ndarray, int]] = {}
    for sid in range(n_silos):
        extra = sample_ids if sid == target_silo else None
        silo_arrays[sid] = _silo_train_arrays(
            pool, base_assign, val_mask, sid, feature_cols, model_cfg, vocab, extra
        )

    ckpt_path = hs.FEDERATED_RESULTS_DIR / source_model_tag / "round_checkpoints" / f"round_{source_round:03d}.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"source checkpoint does not exist: {ckpt_path}")
    warm_state = torch.load(ckpt_path, map_location=device, weights_only=False)

    Xv_scaled, y_val = _pooled_val_split(feature_cols, model_cfg, vocab)
    headline_idx = headline_class_indices(model_cfg)
    cnames = class_names(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])
    metric_name = cfg["verify"]["metric"]
    metric_key = _METRIC_KEY_MAP[metric_name]

    def eval_global(state_dict: dict) -> dict:
        model = build_model(model_cfg, seed=seed, device=device)
        model.load_state_dict(state_dict)
        model.eval()
        with torch.no_grad():
            Xt = torch.from_numpy(Xv_scaled.copy()).to(device)
            y_pred = model(Xt).argmax(dim=1).cpu().numpy()
        return compute_metrics(y_val, y_pred, n_classes, cnames, headline_idx)

    num_rounds = int(cfg["training"]["num_rounds"])
    local_epochs = int(cfg["training"]["local_epochs"])
    mu = float(cfg["training"]["mu"])

    current_state = warm_state
    round_candidates: list[tuple[int, dict, float]] = []
    for r in range(1, num_rounds + 1):
        local_states, ns = [], []
        for sid in range(n_silos):
            X, y, n = silo_arrays[sid]
            local_model = build_model(model_cfg, seed=seed, device=device)
            local_model.load_state_dict(current_state)
            sd = local_train_epochs(local_model, X, y, class_weights, model_cfg, local_epochs, mu, device)
            local_states.append(sd)
            ns.append(n)
        current_state = fedavg_aggregate(local_states, ns)
        metrics = eval_global(current_state)
        candidate_metric = float(metrics[metric_key])
        round_candidates.append((r, current_state, candidate_metric))
        verdict = "PASS" if candidate_metric >= incumbent_metric else "below incumbent"
        print(f"[hotswap] round {r}/{num_rounds}  {metric_name}={candidate_metric:.4f}  ({verdict})")

    # Strict non-regression gate, no tolerance: best candidate must be >=
    # incumbent. Ties broken toward the EARLIEST round (don't train more
    # than necessary to clear the bar).
    passing = [c for c in round_candidates if c[2] >= incumbent_metric]
    if not passing:
        best_seen = max(m for _, _, m in round_candidates)
        print(f"[hotswap] GATE REJECTED: best {metric_name}={best_seen:.4f} < "
              f"incumbent {incumbent_metric:.4f} -- served model unchanged, nothing logged")
        raise HotSwapGateRejected(
            f"no candidate round cleared the gate: best {metric_name}={best_seen:.4f} < "
            f"incumbent {incumbent_metric:.4f} ({source_model_tag} round {source_round}). "
            f"Served model unchanged; nothing logged."
        )
    best_round, best_state, best_metric = min(passing, key=lambda c: c[0])
    print(f"[hotswap] GATE ACCEPTED: round {best_round} {metric_name}={best_metric:.4f} "
          f">= incumbent {incumbent_metric:.4f}")

    resulting_sha = _state_dict_sha256(best_state)
    checkpoints_dir = hs.PROJECT_ROOT / cfg["paths"]["checkpoints_dir"]
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    ckpt_out_path = checkpoints_dir / f"{resulting_sha}.pt"
    if not ckpt_out_path.exists():  # content-addressed: identical result, no re-write needed
        torch.save(best_state, ckpt_out_path)

    training_config = {
        "num_rounds": num_rounds,
        "local_epochs": local_epochs,
        "mu": mu,
        "fraction_train": float(cfg["training"]["fraction_train"]),
        "fraction_evaluate": float(cfg["training"]["fraction_evaluate"]),
        "device": device,
        "scaler_kind": model_cfg["preprocessing"]["scaler"],
        "confirmed_family": confirmed_family,
        "samples_per_event_requested": n_requested,
        "samples_per_event_actual": len(sample_ids),
        "target_silo_selection": "highest_dirichlet_proportions_train_share",  # engineering choice, see select_target_silo()
    }

    fields = {
        "seed": int(seed),
        "warm_start": True,
        "source_model_tag": source_model_tag,
        "source_model_round": source_round,
        "base_partition_ref": {"alpha": alpha, "seed": base_seed},
        "sample_ids": [int(x) for x in sample_ids],
        "sample_silo": sample_silo,
        "training_config": training_config,
        "best_round": int(best_round),
        "verify_metric_name": metric_name,
        "verify_metric_value": float(best_metric),
        "resulting_checkpoint_sha256": resulting_sha,
    }

    record = hs.append_event(fields)
    return record
