"""Cached artifact loaders for the XFed-IDS Streamlit app.

Every function here either reads an artifact already on disk (confirmed in
Chat 05 against the real project) or calls the exact deterministic function
the training/SHAP pipeline itself used -- never a hand-rolled approximation.

If an artifact is genuinely missing, a function raises FileNotFoundError (for
app.py to surface cleanly) or returns None with a comment explaining why --
never a fabricated number. See non-negotiables in the project instructions.

Path source of truth for each loader is noted inline, pointing back to the
script that originally produced or consumed that path
(tools/centralized_shap_floor.py, federated/xfed_federated/task.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import torch

# --- Project root & vendored-module import path ---------------------------
# app.py is expected to live at the project root (same level as configs/,
# data/, results/, federated/). If you place it elsewhere, this breaks --
# keep it at root.
ROOT = Path(__file__).resolve().parent.parent
FEDERATED_DIR = ROOT / "federated"
TOOLS_DIR = ROOT / "tools"
if str(FEDERATED_DIR) not in sys.path:
    sys.path.insert(0, str(FEDERATED_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Same import pattern as tools/centralized_shap_floor.py -- these are the
# vendored copies Flower's isolated runtime uses, but they work fine
# imported directly too since we're not running under `flwr run` here.
from xfed_federated import task  # noqa: E402
from xfed_federated._vendored.schema import (  # noqa: E402
    derive_feature_cols,
    load_label_vocabulary,
)

# Must match tools/eval_set_config.py exactly, or the "fixed" eval rows
# won't actually be fixed relative to what's in the SHAP .npz files.
from eval_set_config import N_EVAL_ROWS, EVAL_SEED  # noqa: E402

DATA_ROOT = ROOT / "data" / "processed"
RESULTS_ROOT = ROOT / "results"
CONFIGS_ROOT = ROOT / "configs"
CENTRALIZED_CKPT_DIR = RESULTS_ROOT / "centralized"

BACKGROUND_TARGET = 200
BACKGROUND_SEED_BASE = 999


def _rel(p: str) -> Path:
    """Manifest paths were written on Windows with backslashes. Normalize
    before joining, so this works regardless of OS."""
    return ROOT / p.replace("\\", "/")


# --- Configs ---------------------------------------------------------------

@st.cache_resource
def load_configs() -> tuple[dict, dict]:
    data_cfg = task.load_yaml("configs/data.yaml")
    model_cfg = task.load_yaml("configs/model.yaml")
    return data_cfg, model_cfg


@st.cache_resource
def load_manifest() -> list[dict]:
    path = RESULTS_ROOT / "inspection" / "best_rounds_manifest.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())


def get_manifest_entry(tag: str) -> dict:
    matches = [m for m in load_manifest() if m["tag"] == tag]
    if not matches:
        raise KeyError(f"No manifest entry for tag={tag!r}")
    return matches[0]


def config_tag(alpha: str, seed: int) -> str:
    return f"fedavg_a{alpha}_s{seed}"


# --- Label vocabulary & feature columns -------------------------------------

@st.cache_resource
def get_label_vocab() -> dict:
    _, model_cfg = load_configs()
    vocab = load_label_vocabulary(model_cfg)  # name -> idx
    return {
        "vocab": vocab,
        "idx_to_name": {v: k for k, v in vocab.items()},
        "headline_classes": model_cfg["labels"]["headline_classes"],
        "below_floor_classes": model_cfg["labels"]["below_floor_classes"],
        "n_classes": model_cfg["labels"]["n_classes"],
    }


@st.cache_resource
def get_feature_cols() -> list[str]:
    """The exact 82, in model-input order. Derived the same way the
    training/SHAP pipeline derived them -- NOT a hand-filtered list."""
    import pyarrow.parquet as pq

    data_cfg, _ = load_configs()
    test_path = DATA_ROOT / "test_global.parquet"
    if not test_path.exists():
        raise FileNotFoundError(str(test_path))
    columns = list(pq.ParquetFile(test_path).schema_arrow.names)
    return derive_feature_cols(columns, data_cfg)


# --- Federation shape (Section 1) -------------------------------------------

@st.cache_resource
def get_federation_shape() -> dict:
    data_cfg, _ = load_configs()
    fed = data_cfg["federation"]
    return {"n_silos": fed["n_silos"], "alphas": fed["alphas"], "seeds": fed["seeds"]}


@st.cache_resource
def get_all_manifest_summaries() -> pd.DataFrame:
    """One row per (alpha, seed) config: best round, val/test macro-F1.
    Reads only the manifest -- nothing recomputed."""
    rows = [
        {
            "alpha": m["alpha"],
            "seed": m["seed"],
            "tag": m["tag"],
            "best_round": m["best_round"],
            "val_macro_f1_headline": m["best_val_macro_f1_headline"],
            "test_macro_f1_headline": m["test_macro_f1_headline"],
        }
        for m in load_manifest()
    ]
    return pd.DataFrame(rows).sort_values(["alpha", "seed"]).reset_index(drop=True)


@st.cache_resource
def get_silo_sizes() -> pd.DataFrame | None:
    """Per-silo flow counts, if the artifact exists. Returns None (not a
    fabricated table) if it doesn't."""
    path = RESULTS_ROOT / "inspection" / "silo_sizes.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


# Whole-silo size floor (separate from the per-family eligibility rule
# above). A silo's TOTAL flow count (summed across all families) below
# this threshold excludes it from the size-based silo count shown in
# Federation Status. Confirmed against the known "1/90 excluded" figure --
# threshold=500 is the only value in {100, 500, 1000} that reproduces it
# exactly (0/90, 1/90, 2/90 respectively).
SILO_TOTAL_MIN_FLOWS = 500


@st.cache_resource
def get_silo_total_eligibility() -> dict | None:
    """Whole-silo size check: how many of the 90 (alpha, seed, silo)
    combinations fall below the total-flow floor, regardless of family."""
    sizes = get_silo_sizes()
    if sizes is None:
        return None
    tot = sizes.groupby(["alpha", "seed", "silo"])["n"].sum().reset_index()
    tot = tot.rename(columns={"n": "total_flows"})
    tot["below_floor"] = tot["total_flows"] < SILO_TOTAL_MIN_FLOWS
    excluded = tot[tot["below_floor"]]
    return {
        "table": tot.sort_values("total_flows").reset_index(drop=True),
        "threshold_flows": SILO_TOTAL_MIN_FLOWS,
        "n_excluded": len(excluded),
        "n_total": len(tot),
        "excluded_detail": excluded,
    }
# analysis). Reverse-engineered from precheck_C.py's output rather than
# hardcoded from memory: any threshold in [17, 62) reproduces the known
# PortScan result (7/5/4 eligible silos across seeds 42/1337/2024) exactly.
# 50 is a defensible midpoint of that range, proven equivalent on the one
# ground-truth number available. If a different exact value turns up later,
# only this constant needs to change.
SILO_FAMILY_MIN_FLOWS = 50

# How many eligible silos (out of 10) a family needs before it's included
# in cross-silo explanation-agreement analysis for that (alpha, seed).
# Stated directly in project memory: "PortScan clears >=4 eligible-silo
# threshold."
FAMILY_MIN_ELIGIBLE_SILOS = 4


@st.cache_resource
def get_eligibility_matrix() -> pd.DataFrame | None:
    """One row per (alpha, seed, family): how many silos have >= 50 flows
    of that family, and whether that clears the >=4-silo bar for inclusion
    in cross-silo agreement analysis. Built entirely from silo_sizes.csv --
    no separate eligibility artifact needed."""
    sizes = get_silo_sizes()
    if sizes is None:
        return None
    df = sizes.copy()
    df["eligible"] = df["n"] >= SILO_FAMILY_MIN_FLOWS
    matrix = (
        df.groupby(["alpha", "seed", "family"])["eligible"]
        .sum()
        .reset_index()
        .rename(columns={"eligible": "eligible_silos"})
    )
    matrix["family_included"] = matrix["eligible_silos"] >= FAMILY_MIN_ELIGIBLE_SILOS
    return matrix.sort_values(["alpha", "seed", "family"]).reset_index(drop=True)


def get_eligibility_summary() -> dict | None:
    """Rollup for display: how many (alpha, seed, family) combinations get
    excluded, plus the full matrix for drill-down."""
    matrix = get_eligibility_matrix()
    if matrix is None:
        return None
    excluded = matrix[~matrix["family_included"]]
    return {
        "matrix": matrix,
        "threshold_flows": SILO_FAMILY_MIN_FLOWS,
        "min_eligible_silos": FAMILY_MIN_ELIGIBLE_SILOS,
        "n_excluded": len(excluded),
        "n_total": len(matrix),
        "excluded_detail": excluded,
    }


# --- Model / checkpoint loading ---------------------------------------------

def _load_checkpoint_into_model(model: torch.nn.Module, path: Path) -> torch.nn.Module:
    """Same wrapper-format tolerance as tools/centralized_shap_floor.py --
    fails loudly with the actual keys found rather than guessing."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and all(isinstance(v, torch.Tensor) for v in obj.values()):
        model.load_state_dict(obj)
        return model
    if isinstance(obj, dict) and "state_dict" in obj:
        model.load_state_dict(obj["state_dict"])
        return model
    if isinstance(obj, dict) and "model_state_dict" in obj:
        model.load_state_dict(obj["model_state_dict"])
        return model
    keys = list(obj.keys()) if isinstance(obj, dict) else type(obj)
    raise ValueError(f"Unrecognized checkpoint format at {path}: {keys}")


@st.cache_resource
def load_global_model_for_config(tag: str):
    """Best-round GLOBAL checkpoint for one (alpha, seed) config, e.g.
    tag='fedavg_a0.5_s42'. Returns (model, manifest_entry)."""
    _, model_cfg = load_configs()
    entry = get_manifest_entry(tag)
    model = task.build_model(model_cfg, seed=entry["seed"], device="cpu")
    model = _load_checkpoint_into_model(model, _rel(entry["global_checkpoint"]))
    model.eval()
    return model, entry


@st.cache_resource
def load_silo_model_for_config(tag: str, silo_idx: int):
    """Best-round LOCAL checkpoint for one silo within a config."""
    _, model_cfg = load_configs()
    entry = get_manifest_entry(tag)
    model = task.build_model(model_cfg, seed=entry["seed"], device="cpu")
    model = _load_checkpoint_into_model(model, _rel(entry["silo_checkpoints"][silo_idx]))
    model.eval()
    return model


# --- Section 2: Detect ------------------------------------------------------
# Confirmed against federated/xfed_federated/server_app.py: the global model
# is evaluated every round against load_centralized_for_server()'s val/test
# split, NOT any per-silo scaler. So every number in best_rounds_manifest.json
# -- centralized or federated -- was produced with this one scaler. Section 2
# reuses it for every prediction, federated or centralized alike. No
# per-config scaler branching needed.

@st.cache_resource
def get_centralized_splits():
    """The exact scaler (and val/test arrays) both the centralized baseline
    and federated server-side evaluation were scored with. NOT used for
    Section 2 prediction anymore -- see get_centralized_scaler(), which
    loads the same values from the persisted scaler.npz instead of a full
    parquet refit. Kept here because Section 3 (SHAP) needs X_train for
    background sampling, which this still provides."""
    data_cfg, model_cfg = load_configs()
    return task.load_centralized_for_server(data_cfg, model_cfg)


@st.cache_resource
def get_fixed_eval_rows():
    """The same 14 rows (2 per headline family) tools/centralized_shap_floor.py
    used for the SHAP .npz files -- identical EVAL_SEED and selection logic,
    so a prediction shown here always matches the row a SHAP explanation
    (Section 3) will later explain."""
    data_cfg, model_cfg = load_configs()
    vocab_info = get_label_vocab()
    feature_cols = get_feature_cols()

    test_path = DATA_ROOT / "test_global.parquet"
    if not test_path.exists():
        raise FileNotFoundError(str(test_path))
    df = pd.read_parquet(test_path, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)

    n_per_class = max(1, N_EVAL_ROWS // len(vocab_info["headline_classes"]))
    picked_X, picked_fam = [], []
    for fam in vocab_info["headline_classes"]:
        fam_df = df[df.family == fam]
        n = min(n_per_class, len(fam_df))
        s = fam_df.sample(n=n, random_state=EVAL_SEED)
        picked_X.append(s[feature_cols].to_numpy(np.float32))
        picked_fam.extend([fam] * n)

    X_raw = np.concatenate(picked_X, axis=0)
    y = np.array([vocab_info["vocab"][f] for f in picked_fam], dtype=np.int64)
    return X_raw, y, picked_fam


@st.cache_resource
def get_centralized_scaler() -> dict:
    """Loads the scaler PERSISTED at training time instead of refitting
    from the full 1.9M-row train_pool.parquet on every cold start. Same
    values by construction -- _prepare() in the vendored loaders wrote
    this file directly from the fitted scaler -- just without re-reading
    gigabytes of parquet to get them.

    baseline_s42's copy is used as canonical: scaler fitting has no
    dependency on model seed (train/val split and scaler fit happen
    identically regardless of which seed later trains on top of them), so
    all three centralized seeds' scaler.npz files should be identical.

    Feature-name order is checked against get_feature_cols() and fails
    loudly on any mismatch rather than silently misaligning a column.
    """
    path = CENTRALIZED_CKPT_DIR / "baseline_s42" / "scaler.npz"
    if not path.exists():
        raise FileNotFoundError(str(path))
    d = np.load(path, allow_pickle=True)

    saved_features = list(d["feature_names"])
    expected_features = get_feature_cols()
    if saved_features != expected_features:
        raise ValueError(
            "scaler.npz feature order does not match derive_feature_cols() "
            "output -- refusing to use it until this is resolved, rather "
            "than silently misaligning a column."
        )

    return {"center": d["center"].astype(np.float32), "scale": d["scale"].astype(np.float32)}


def scale_with_centralized_scaler(X_raw: np.ndarray) -> np.ndarray:
    scaler = get_centralized_scaler()
    return ((X_raw - scaler["center"]) / scaler["scale"]).astype(np.float32)


@st.cache_resource
def load_centralized_model(seed: int):
    """Same checkpoint path pattern as tools/centralized_shap_floor.py:
    results/centralized/baseline_s{seed}/model.pt"""
    _, model_cfg = load_configs()
    ckpt_path = CENTRALIZED_CKPT_DIR / f"baseline_s{seed}" / "model.pt"
    model = task.build_model(model_cfg, seed=seed, device="cpu")
    model = _load_checkpoint_into_model(model, ckpt_path)
    model.eval()
    return model


def get_available_models() -> list[dict]:
    """Every model Section 2 can predict with: 3 centralized seeds plus
    every federated (alpha, seed) config in the manifest."""
    data_cfg, _ = load_configs()
    options = [
        {"label": f"Centralized MLP (seed {seed})", "kind": "centralized", "identifier": seed}
        for seed in data_cfg["federation"]["seeds"]
    ]
    options += [
        {
            "label": f"Federated global — α={m['alpha']}, seed={m['seed']}",
            "kind": "federated",
            "identifier": m["tag"],
        }
        for m in load_manifest()
    ]
    return options


@torch.no_grad()
def predict_row(model, X_scaled_row: np.ndarray) -> np.ndarray:
    """Softmax confidence vector for one already-scaled row."""
    x = torch.from_numpy(X_scaled_row.copy()).unsqueeze(0)
    logits = model(x)
    return torch.softmax(logits, dim=-1).squeeze(0).numpy()


# --- Arbitrary-flow input (PREDICTION ONLY -- never explanation) ------------
# A forward pass is not a SHAP computation: no explainer is constructed, no
# background is sampled, no gradients are taken. It is sub-millisecond and
# fully deterministic. Explanations remain restricted to the fixed 14 eval
# rows, which are the only rows with precomputed .npz artifacts -- an
# arbitrary flow has no stored explanation and one is never generated for it.


class FlowParseError(ValueError):
    """Raised with a message intended to be shown directly to the user."""


def parse_arbitrary_flow(raw_text: str | None, uploaded_df: pd.DataFrame | None) -> np.ndarray:
    """Parse one flow's 82 raw (unscaled) feature values.

    Accepts either a comma/whitespace-separated list of 82 numbers, or a
    single-row DataFrame from an uploaded CSV. A CSV carrying named columns
    is reordered to model-input order by name; a headerless one is taken
    positionally and the ordering assumption is surfaced to the caller.
    """
    feature_cols = get_feature_cols()

    if uploaded_df is not None:
        df = uploaded_df
        if len(df) < 1:
            raise FlowParseError("The uploaded file has no data rows.")
        named = [c for c in feature_cols if c in df.columns]
        if len(named) == len(feature_cols):
            row = df.iloc[0][feature_cols].to_numpy(dtype=np.float64)
        elif df.shape[1] == len(feature_cols):
            row = df.iloc[0].to_numpy(dtype=np.float64)
        else:
            missing = [c for c in feature_cols if c not in df.columns]
            raise FlowParseError(
                f"Need {len(feature_cols)} features. The file has "
                f"{df.shape[1]} columns and is missing {len(missing)} "
                f"expected names — first few: {missing[:5]}"
            )
    elif raw_text and raw_text.strip():
        tokens = [t for t in raw_text.replace(",", " ").split() if t]
        if len(tokens) != len(feature_cols):
            raise FlowParseError(
                f"Expected {len(feature_cols)} values, got {len(tokens)}."
            )
        try:
            row = np.array([float(t) for t in tokens], dtype=np.float64)
        except ValueError as exc:
            raise FlowParseError(f"Could not parse a value as a number: {exc}") from exc
    else:
        raise FlowParseError("No input provided.")

    if not np.isfinite(row).all():
        raise FlowParseError(
            "Input contains NaN or infinite values. The training pipeline "
            "dropped such rows rather than imputing them, so a prediction "
            "here would not be meaningful."
        )
    return row.astype(np.float32)


def get_eval_row_as_csv_text(row_idx: int) -> str:
    """One of the fixed eval rows, as a header+value CSV. Gives the user a
    correctly-shaped template to edit instead of assembling 82 values by
    hand."""
    X_raw, _y, _fams = get_fixed_eval_rows()
    feature_cols = get_feature_cols()
    header = ",".join(feature_cols)
    values = ",".join(f"{v:g}" for v in X_raw[row_idx])
    return f"{header}\n{values}"


# --- Section 3: Explain (Centralized only for now) --------------------------
# Federated SHAP (global_shap.npz, silo_N_shap.npz) is deliberately NOT wired
# in yet -- background construction for the global/per-silo federated
# explanations hasn't been confirmed against tools/local_shap_pipeline.py.
# Guessing it risks showing an explanation that doesn't match what was
# actually computed. Centralized is fully confirmed end-to-end.

SHAP_CENTRALIZED_DIR = RESULTS_ROOT / "shap" / "centralized"


@st.cache_resource
def load_centralized_shap(seed: int) -> dict:
    path = SHAP_CENTRALIZED_DIR / f"seed_{seed}_shap.npz"
    if not path.exists():
        raise FileNotFoundError(str(path))
    d = np.load(path, allow_pickle=True)
    return {
        "shap_values": d["shap_values"],       # (14, 82, 9)
        "eval_y": d["eval_y"],                 # (14,)
        "eval_families": d["eval_families"],   # (14,)
        "additivity_max_diff": float(d["additivity_max_diff"]),
    }


def _build_stratified_background(X: np.ndarray, y: np.ndarray, target_total: int, seed: int) -> np.ndarray:
    """Exact reproduction of tools/centralized_shap_floor.py's
    build_stratified_background -- identical algorithm, so a given seed
    always returns the identical index set the original pipeline used."""
    rng = np.random.default_rng(seed)
    classes = np.unique(y)
    class_idx = {c: np.where(y == c)[0] for c in classes}
    base = max(1, target_total // len(classes))
    chosen: dict[int, np.ndarray] = {}
    used = 0
    for c in classes:
        avail = class_idx[c]
        take = min(base, len(avail))
        chosen[c] = rng.choice(avail, size=take, replace=False)
        used += take
    remaining = target_total - used
    if remaining > 0:
        room = [c for c in classes if len(class_idx[c]) > len(chosen[c])]
        while remaining > 0 and room:
            for c in list(room):
                if remaining <= 0:
                    break
                avail = class_idx[c]
                already = set(chosen[c].tolist())
                pool = np.array([i for i in avail if i not in already])
                if len(pool) == 0:
                    room.remove(c)
                    continue
                extra = rng.choice(pool, size=1, replace=False)
                chosen[c] = np.concatenate([chosen[c], extra])
                remaining -= 1
                if len(pool) == 1:
                    room.remove(c)
    idx = np.concatenate(list(chosen.values()))
    rng.shuffle(idx)
    return idx


@st.cache_resource
def get_centralized_background(seed: int) -> np.ndarray:
    """Same background rows tools/centralized_shap_floor.py used to produce
    this seed's SHAP file -- same seed formula (BACKGROUND_SEED_BASE +
    seed), same stratification. First call loads the full training pool
    (get_centralized_splits) -- slow once, cached after."""
    splits = get_centralized_splits()
    idx = _build_stratified_background(
        splits.X_train, splits.y_train, BACKGROUND_TARGET, BACKGROUND_SEED_BASE + seed
    )
    return splits.X_train[idx]


@torch.no_grad()
def get_base_values(model, background: np.ndarray) -> np.ndarray:
    """Mean logit per class over the background -- the same f_bg
    computation tools/centralized_shap_floor.py used for its additivity
    check, just never persisted there. Shape (9,)."""
    bt = torch.from_numpy(background.copy())
    return model(bt).numpy().mean(axis=0)


# --- Section 3 (federated): global + per-silo explanations -----------------
# Confirmed against tools/local_shap_pipeline.py. Two things that differ from
# the centralized pipeline and are NOT interchangeable with it:
#   - Background seed base is 777, not 999+seed.
#   - The GLOBAL model's background is the POOLED centralized X_train (not
#     any one silo's), while each SILO's background is that silo's own
#     scaled X_train, using that silo's own scaler.

SHAP_ROOT = RESULTS_ROOT / "shap"
FEDERATED_BACKGROUND_SEED_BASE = 777


@st.cache_resource
def load_federated_shap(tag: str, silo_idx: int | None) -> dict:
    """silo_idx=None -> global_shap.npz; otherwise silo_{silo_idx}_shap.npz."""
    fname = "global_shap.npz" if silo_idx is None else f"silo_{silo_idx}_shap.npz"
    path = SHAP_ROOT / tag / fname
    if not path.exists():
        raise FileNotFoundError(str(path))
    d = np.load(path, allow_pickle=True)
    out = {
        "shap_values": d["shap_values"],
        "eval_y": d["eval_y"],
        "eval_families": d["eval_families"],
        "additivity_max_diff": float(d["additivity_max_diff"]),
    }
    if "background_size" in d:
        out["background_size"] = int(d["background_size"])
    return out


@st.cache_resource
def get_federated_global_background() -> np.ndarray:
    """Global-model background: pooled centralized X_train, fixed seed 777.
    Same seed and source for every (alpha, seed) config -- confirmed from
    the script, not the per-silo scheme decision 4 might suggest at a
    glance."""
    splits = get_centralized_splits()
    idx = _build_stratified_background(
        splits.X_train, splits.y_train, BACKGROUND_TARGET, FEDERATED_BACKGROUND_SEED_BASE
    )
    return splits.X_train[idx]


@st.cache_resource
def get_silo_splits(silo_id: int, alpha: str, seed: int):
    """One silo's Splits -- scaled X_train/val/test with that silo's own
    scaler. Cached once per (silo, alpha, seed) so background sampling and
    scaling below don't each trigger a separate refit."""
    data_cfg, model_cfg = load_configs()
    class_weights = task.load_global_class_weights(model_cfg)
    return task.load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)


@st.cache_resource
def get_federated_silo_background(silo_id: int, alpha: str, seed: int) -> np.ndarray:
    """Per-silo background: that silo's own scaled X_train, seed =
    777 + silo_id + 1, confirmed from the script."""
    splits = get_silo_splits(silo_id, alpha, seed)
    idx = _build_stratified_background(
        splits.X_train, splits.y_train, BACKGROUND_TARGET,
        FEDERATED_BACKGROUND_SEED_BASE + silo_id + 1,
    )
    return splits.X_train[idx]


def scale_with_silo_scaler(X_raw: np.ndarray, silo_id: int, alpha: str, seed: int) -> np.ndarray:
    splits = get_silo_splits(silo_id, alpha, seed)
    return ((X_raw - splits.scaler_center) / splits.scaler_scale).astype(np.float32)


# --- Section 4: Explanation Agreement ---------------------------------------

AGREEMENT_METRICS_PATH = RESULTS_ROOT / "inspection" / "agreement_metrics.csv"

# Stated in the project's own locked headline numbers; no separate artifact
# file was found holding this value in isolation. Traced to that existing
# record, not derived from agreement_metrics.csv here.
CHANCE_LEVEL_JACCARD_AT_10 = 0.065


@st.cache_resource
def load_agreement_metrics() -> pd.DataFrame:
    if not AGREEMENT_METRICS_PATH.exists():
        raise FileNotFoundError(str(AGREEMENT_METRICS_PATH))
    return pd.read_csv(AGREEMENT_METRICS_PATH)


@st.cache_resource
def get_headline_agreement() -> pd.DataFrame:
    """Median jaccard@10 / weighted tau per alpha, family_eligible==True
    rows only. Confirmed aggregation: this is the unique combination
    (median, eligible-only) that reproduces the project's own stated
    headline numbers (0.333/0.538/0.667 and 0.592/0.787/0.844) to six
    decimal places -- not assumed, checked."""
    df = load_agreement_metrics()
    elig = df[df["family_eligible"]]
    out = (
        elig.groupby("alpha")
        .agg(
            jaccard_at_10_median=("jaccard_at_10", "median"),
            jaccard_at_10_q25=("jaccard_at_10", lambda s: s.quantile(0.25)),
            jaccard_at_10_q75=("jaccard_at_10", lambda s: s.quantile(0.75)),
            tau_median=("kendall_weighted_tau", "median"),
            tau_q25=("kendall_weighted_tau", lambda s: s.quantile(0.25)),
            tau_q75=("kendall_weighted_tau", lambda s: s.quantile(0.75)),
            n_rows=("jaccard_at_10", "count"),
        )
        .reset_index()
        .sort_values("alpha")
    )
    return out


@st.cache_resource
def get_per_seed_agreement() -> pd.DataFrame:
    """Same headline metrics broken out per seed -- shows whether the alpha
    trend holds seed-by-seed or is an averaging artifact."""
    df = load_agreement_metrics()
    elig = df[df["family_eligible"]]
    out = (
        elig.groupby(["alpha", "seed"])
        .agg(
            jaccard_at_10_median=("jaccard_at_10", "median"),
            tau_median=("kendall_weighted_tau", "median"),
            n_rows=("jaccard_at_10", "count"),
        )
        .reset_index()
        .sort_values(["alpha", "seed"])
    )
    return out


@st.cache_resource
def get_per_family_agreement() -> pd.DataFrame:
    """Median jaccard@10 / tau per (alpha, family), eligible rows only."""
    df = load_agreement_metrics()
    elig = df[df["family_eligible"]]
    out = (
        elig.groupby(["alpha", "family"])
        .agg(
            jaccard_at_10_median=("jaccard_at_10", "median"),
            tau_median=("kendall_weighted_tau", "median"),
            n_rows=("jaccard_at_10", "count"),
        )
        .reset_index()
        .sort_values(["alpha", "family"])
    )
    return out


# --- Section 5: Faithfulness -------------------------------------------------

DELETION_AUC_PATH = RESULTS_ROOT / "inspection" / "deletion_auc.csv"
INSERTION_AUC_PATH = RESULTS_ROOT / "inspection" / "insertion_auc.csv"
FAITHFULNESS_FIGURES_DIR = RESULTS_ROOT / "figures"

# Faithfulness was computed for ONE config only (alpha=0.5, seed=42), per
# project record. Not encoded in the CSVs themselves (no alpha/seed
# column) -- stated here from that record, not inferred from the file.
FAITHFULNESS_CONFIG_LABEL = "α=0.5, seed=42"


@st.cache_resource
def load_faithfulness_auc() -> dict | None:
    if not DELETION_AUC_PATH.exists() or not INSERTION_AUC_PATH.exists():
        return None
    deletion = pd.read_csv(DELETION_AUC_PATH)
    insertion = pd.read_csv(INSERTION_AUC_PATH)
    return {"table": deletion.merge(insertion, on="model", how="outer")}


def get_faithfulness_figure_path(kind: str) -> Path | None:
    """kind: 'deletion' or 'insertion'. No per-step data exists to
    natively redraw the curve shape -- only the final AUC survives in the
    CSVs -- so this points at the precomputed PNG the original pipeline
    already wrote, rather than fabricating a curve from one number."""
    path = FAITHFULNESS_FIGURES_DIR / f"{kind}_curve.png"
    return path if path.exists() else None


# --- Section 6: Methods & Limits --------------------------------------------

CENTRALIZED_INSTABILITY_PATH = RESULTS_ROOT / "inspection" / "centralized_instability_floor.csv"


@st.cache_resource
def load_instability_floor() -> pd.DataFrame | None:
    """Pairwise SHAP agreement between the 3 centralized seeds -- the null
    federated agreement gets compared against. Schema confirmed directly
    from tools/centralized_shap_floor.py: seed_pair, sample_idx, family,
    kendall_weighted_tau, jaccard_at_5/10/20."""
    if not CENTRALIZED_INSTABILITY_PATH.exists():
        return None
    return pd.read_csv(CENTRALIZED_INSTABILITY_PATH)


@st.cache_resource
def get_instability_floor_summary() -> dict | None:
    df = load_instability_floor()
    if df is None:
        return None
    return {
        "jaccard_at_10_median": df["jaccard_at_10"].median(),
        "jaccard_at_10_q25": df["jaccard_at_10"].quantile(0.25),
        "jaccard_at_10_q75": df["jaccard_at_10"].quantile(0.75),
        "tau_median": df["kendall_weighted_tau"].median(),
        "tau_q25": df["kendall_weighted_tau"].quantile(0.25),
        "tau_q75": df["kendall_weighted_tau"].quantile(0.75),
        "n_rows": len(df),
    }


@st.cache_resource
def load_raw_inspection_csv(name: str) -> pd.DataFrame | None:
    """Generic loader for inspection CSVs whose exact column semantics
    haven't been confirmed against this app -- rendered as-is rather than
    assumed into a specific chart, so nothing here is guessed structure."""
    path = RESULTS_ROOT / "inspection" / name
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_resource
def get_round_lottery_table() -> pd.DataFrame | None:
    """Best-by-validation test score vs. final-round (unselected) test
    score, per federated config -- computed live from each config's
    final_metrics.json rather than restating one historical example.
    Path and the two keys used (test.macro_f1_headline,
    test_final_round_unselected.macro_f1_headline) are confirmed directly
    from federated/xfed_federated/server_app.py."""
    rows = []
    for m in load_manifest():
        path = RESULTS_ROOT / "federated" / m["tag"] / "final_metrics.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        best_f1 = data["test"]["macro_f1_headline"]
        final_f1 = data["test_final_round_unselected"]["macro_f1_headline"]
        rows.append(
            {
                "alpha": m["alpha"],
                "seed": m["seed"],
                "tag": m["tag"],
                "best_round": m["best_round"],
                "best_round_test_f1": best_f1,
                "final_round_test_f1": final_f1,
                "gap": final_f1 - best_f1,
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values(["alpha", "seed"]).reset_index(drop=True)
