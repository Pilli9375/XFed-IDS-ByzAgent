"""Loading, scaling, and class weighting. This is where leakage would live.

Two loading paths, deliberately sharing everything except scaler scope:

  load_centralized() -- pooled train split, scaler fit on it
  load_silo()        -- one silo's rows, scaler fit on that silo's rows only

Both apply the same global val mask, so centralized and federated train on an
identical row set and the comparison isolates federation itself rather than a
difference in data quantity.

Place at: src/data/loaders.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
from sklearn.preprocessing import RobustScaler, StandardScaler

from .schema import (
    class_names,
    derive_feature_cols,
    encode_families,
    load_label_vocabulary,
)

SCALER_KINDS = ("standard", "robust", "robust_clipped")


@dataclass
class Splits:
    """Scaled arrays plus everything needed to reproduce or interpret them."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray

    feature_names: list[str]
    class_names: list[str]
    class_weights: np.ndarray

    scaler_kind: str
    scaler_center: np.ndarray
    scaler_scale: np.ndarray
    clip_lo: np.ndarray | None = None
    clip_hi: np.ndarray | None = None
    degenerate_scale_features: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"train {len(self.y_train):,} | val {len(self.y_val):,} | test {len(self.y_test):,} | "
            f"{self.X_train.shape[1]} features | scaler={self.scaler_kind}"
        )


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def _read_columns(path: Path) -> list[str]:
    """Column names in parquet order, without materializing the table."""
    return list(pq.ParquetFile(path).schema_arrow.names)


def _read_frame(path: Path, feature_cols: list[str]) -> pd.DataFrame:
    """Read only the features plus family, downcast to float32.

    float64 over 1.4M x 82 is ~940MB for no benefit; float32 halves that and is
    what the model consumes anyway.
    """
    df = pd.read_parquet(path, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)
    return df


# --------------------------------------------------------------------------
# scaling
# --------------------------------------------------------------------------

def _fit_scaler(
    X_train: np.ndarray,
    kind: str,
    feature_names: list[str],
    clip_percentiles: tuple[float, float] = (0.1, 99.9),
) -> tuple[object, np.ndarray | None, np.ndarray | None, list[str]]:
    """Fit on training rows only. Returns (scaler, clip_lo, clip_hi, degenerate).

    'degenerate' lists features whose scale came out as exactly 1.0. sklearn
    substitutes 1.0 when the computed scale is zero -- zero variance for
    StandardScaler, zero IQR for RobustScaler -- which silently reduces the
    transform to centering. About 8 near-constant features here are candidates
    (URG/ECE/CWR flag counts, ICMP Type/Code, Subflow Bwd Packets). Surfacing
    them is the point; they are not dropped, per the Chat 02 decision to wait
    for feature-importance evidence rather than a variance heuristic.
    """
    if kind not in SCALER_KINDS:
        raise ValueError(f"scaler must be one of {SCALER_KINDS}, got {kind!r}")

    clip_lo = clip_hi = None
    if kind == "robust_clipped":
        lo_p, hi_p = clip_percentiles
        clip_lo = np.percentile(X_train, lo_p, axis=0).astype(np.float32)
        clip_hi = np.percentile(X_train, hi_p, axis=0).astype(np.float32)
        X_train = np.clip(X_train, clip_lo, clip_hi)

    scaler = StandardScaler() if kind == "standard" else RobustScaler()
    scaler.fit(X_train)

    scale = scaler.scale_
    degenerate = [name for name, s in zip(feature_names, scale) if s == 1.0]
    return scaler, clip_lo, clip_hi, degenerate


def _apply_scaler(
    X: np.ndarray,
    scaler: object,
    clip_lo: np.ndarray | None,
    clip_hi: np.ndarray | None,
) -> np.ndarray:
    if clip_lo is not None:
        X = np.clip(X, clip_lo, clip_hi)
    Xs = scaler.transform(X).astype(np.float32)
    if not np.isfinite(Xs).all():
        bad = int((~np.isfinite(Xs)).sum())
        raise ValueError(f"{bad:,} non-finite values after scaling. Do not train on this.")
    return Xs


# --------------------------------------------------------------------------
# class weights
# --------------------------------------------------------------------------

def compute_class_weights(y: np.ndarray, n_classes: int, scheme: str, beta: float = 0.999) -> np.ndarray:
    """Loss weights from class counts. Normalized so the mean weight is 1.0.

    Computed ONCE from the centralized training split and reused unchanged by
    every silo. Per-silo weights would mean each silo minimizes a different
    objective, and FedAvg would average models trained on incompatible losses --
    worst at alpha=0.1 where a silo may hold only a handful of classes.

    effective_number: Cui et al., Class-Balanced Loss Based on Effective Number
    of Samples, CVPR 2019. w_c proportional to (1 - beta) / (1 - beta^n_c).
    Saturates for rare classes instead of exploding: plain inverse frequency
    would hand Heartbleed (7 rows) a weight ~139,000x Benign's, so a handful of
    samples would dominate every gradient.
    """
    counts = np.bincount(y, minlength=n_classes).astype(np.float64)
    present = counts > 0

    w = np.zeros(n_classes, dtype=np.float64)
    if scheme == "none":
        w[:] = 1.0
        return w.astype(np.float32)
    if scheme == "inverse_sqrt":
        w[present] = 1.0 / np.sqrt(counts[present])
    elif scheme == "effective_number":
        eff = 1.0 - np.power(beta, counts[present])
        w[present] = (1.0 - beta) / eff
    else:
        raise ValueError(f"unknown class weighting scheme {scheme!r}")

    w[present] *= present.sum() / w[present].sum()   # mean weight over present classes == 1
    return w.astype(np.float32)


# --------------------------------------------------------------------------
# loading paths
# --------------------------------------------------------------------------

def _prepare(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    model_cfg: dict,
    scaler_kind: str,
    class_weights_override: np.ndarray | None = None,
) -> Splits:
    vocab = load_label_vocabulary(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])
    pre = model_cfg["preprocessing"]

    X_train = train_df[feature_cols].to_numpy(np.float32)
    X_val = val_df[feature_cols].to_numpy(np.float32)
    X_test = test_df[feature_cols].to_numpy(np.float32)

    scaler, clip_lo, clip_hi, degenerate = _fit_scaler(
        X_train, scaler_kind, feature_cols, tuple(pre["clip_percentiles"])
    )
    if degenerate and pre.get("assert_no_silent_unit_scale", True):
        print(f"  NOTE: {len(degenerate)} feature(s) have scale_ == 1.0 "
              f"(zero variance or zero IQR on train) -> centering only: {degenerate}")

    y_train = encode_families(train_df["family"], vocab)

    if class_weights_override is not None:
        # Federated path: weights were computed once from the centralized
        # training split and must be identical on every silo. Recomputing them
        # per-silo would mean each silo minimizes a different objective --
        # worst at alpha=0.1 where a silo may hold only a handful of classes --
        # and FedAvg would then be averaging models that were never optimizing
        # the same loss.
        class_weights = np.asarray(class_weights_override, dtype=np.float32)
        if class_weights.shape != (n_classes,):
            raise ValueError(
                f"class_weights_override has shape {class_weights.shape}, "
                f"expected ({n_classes},)"
            )
    else:
        class_weights = compute_class_weights(
            y_train, n_classes,
            model_cfg["training"]["class_weighting"]["scheme"],
            float(model_cfg["training"]["class_weighting"]["beta"]),
        )

    return Splits(
        X_train=_apply_scaler(X_train, scaler, clip_lo, clip_hi),
        y_train=y_train,
        X_val=_apply_scaler(X_val, scaler, clip_lo, clip_hi),
        y_val=encode_families(val_df["family"], vocab),
        X_test=_apply_scaler(X_test, scaler, clip_lo, clip_hi),
        y_test=encode_families(test_df["family"], vocab),
        feature_names=feature_cols,
        class_names=class_names(model_cfg),
        class_weights=class_weights,
        scaler_kind=scaler_kind,
        scaler_center=np.asarray(
            scaler.center_ if hasattr(scaler, "center_") else scaler.mean_,
            dtype=np.float32,
        ),
        scaler_scale=np.asarray(scaler.scale_, dtype=np.float32),
        clip_lo=clip_lo,
        clip_hi=clip_hi,
        degenerate_scale_features=degenerate,
    )


def load_centralized(
    data_cfg: dict,
    model_cfg: dict,
    root: str | Path = "data/processed",
    scaler_kind: str | None = None,
) -> Splits:
    """Pooled training split. Scaler fit on it -- there are no silos here."""
    root = Path(root)
    scaler_kind = scaler_kind or model_cfg["preprocessing"]["scaler"]

    train_pool_path = root / "train_pool.parquet"
    feature_cols = derive_feature_cols(_read_columns(train_pool_path), data_cfg)

    pool = _read_frame(train_pool_path, feature_cols)
    mask = pd.read_parquet(root / "val_mask.parquet")["is_val"].to_numpy()
    if len(mask) != len(pool):
        raise ValueError(
            f"val_mask has {len(mask):,} rows but train_pool has {len(pool):,}. "
            f"The mask is positional; a length mismatch means it was built against "
            f"a different train_pool. Regenerate it."
        )

    test = _read_frame(root / "test_global.parquet", feature_cols)
    return _prepare(pool[~mask], pool[mask], test, feature_cols, model_cfg, scaler_kind)


def load_silo(
    silo_id: int,
    alpha: str,
    seed: int,
    data_cfg: dict,
    model_cfg: dict,
    root: str | Path = "data/processed",
    scaler_kind: str | None = None,
    class_weights_override: np.ndarray | None = None,
) -> Splits:
    """One silo's private partition. Scaler fit on this silo's rows only.

    class_weights_override should always be supplied by federated callers --
    see the note in _prepare(). It is optional here only so load_silo() stays
    usable for one-off inspection (e.g. from a notebook) without requiring the
    full federated plumbing.

    A scaler fit across silos would quietly violate the privacy premise of the
    whole project: a real bank cannot see the hospital's rows to compute a
    median. The consequence is that input distributions differ per silo on top
    of the Dirichlet label skew -- a second, independent source of heterogeneity
    worth stating in Methodology.
    """
    root = Path(root)
    parts = root / "partitions"
    scaler_kind = scaler_kind or model_cfg["preprocessing"]["scaler"]

    train_pool_path = root / "train_pool.parquet"
    feature_cols = derive_feature_cols(_read_columns(train_pool_path), data_cfg)

    pool = _read_frame(train_pool_path, feature_cols)
    val_mask = pd.read_parquet(root / "val_mask.parquet")["is_val"].to_numpy()
    assign = pd.read_parquet(parts / f"assign_a{alpha}_s{seed}_train.parquet")["silo"].to_numpy()

    for name, arr in (("val_mask", val_mask), ("assignment", assign)):
        if len(arr) != len(pool):
            raise ValueError(f"{name} has {len(arr):,} rows, train_pool has {len(pool):,}")

    mine = assign == silo_id
    if not mine.any():
        raise ValueError(f"silo {silo_id} has no rows at alpha={alpha}, seed={seed}")

    train_rows = pool[mine & ~val_mask]
    if len(train_rows) == 0:
        raise ValueError(
            f"silo {silo_id} has no training rows after the val holdout at "
            f"alpha={alpha}, seed={seed}"
        )

    test_pool = _read_frame(root / "test_global.parquet", feature_cols)
    test_assign = pd.read_parquet(parts / f"assign_a{alpha}_s{seed}_test.parquet")["silo"].to_numpy()

    return _prepare(
        train_rows,
        pool[mine & val_mask],
        test_pool[test_assign == silo_id],
        feature_cols, model_cfg, scaler_kind,
        class_weights_override=class_weights_override,
    )


# --------------------------------------------------------------------------
# tensors
# --------------------------------------------------------------------------

def to_device_tensors(
    splits: Splits, device: str | torch.device
) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    """Move every split onto the device once, whole.

    1.29M x 82 float32 is ~423MB; val and test add ~165MB. Under 600MB total,
    comfortably inside the 6GB ceiling with the model itself in the tens of KB.
    Keeping it resident removes per-batch host-to-device copies entirely, which
    is the dominant cost for a model this small.
    """
    out = {}
    for name in ("train", "val", "test"):
        # .copy() is deliberate: pandas .map() can return a read-only array, and
        # torch.from_numpy wraps memory without copying it. PyTorch warns that
        # writing to such a tensor is undefined behaviour.
        X = torch.from_numpy(getattr(splits, f"X_{name}").copy()).to(device)
        y = torch.from_numpy(getattr(splits, f"y_{name}").copy()).to(device)
        out[name] = (X, y)
    return out
