#!/usr/bin/env python
"""Near-duplicate audit: is the test set actually new data, or paraphrased train?

The group-aware split guarantees no test row is byte-identical to a train row.
It says nothing about rows differing in the eighth decimal of one column --
flows from the same attack session, functionally the same row. If test flows are
near-duplicates of train flows, a macro-F1 of 0.99 is memorization, and "we used
StratifiedGroupKFold" is not an answer to that.

Method: for a stratified sample of test rows, compute the Euclidean distance to
the nearest training row in the scaled feature space. Then do the same for a
held-out sample of TRAIN rows against the rest of train. That second number is
the reference: it is what "distance to a row from the same distribution I have
already memorized" looks like.

  test NN distance >> train-internal NN distance  -> test is genuinely held out
  test NN distance ~= train-internal NN distance  -> test rows are near-copies

Reported per family, because the concern is family-specific: DDoS at F1 1.0000
is the row that needs explaining, not Benign.

Usage:
    python scripts/audit_near_duplicates.py
    python scripts/audit_near_duplicates.py --n-probe 4000 --scaler standard
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable regardless of how this script is invoked.
# `python scripts\audit_near_duplicates.py` only puts scripts\ on sys.path;
# the project root (one level up) is where `src` actually lives.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from src.data.loaders import load_centralized
from src.data.schema import load_yaml


def stratified_probe(y: np.ndarray, n: int, seed: int, min_per_class: int) -> np.ndarray:
    """Sample n rows, proportional by class, with a floor per present class.

    The floor matters more than the total: the families under suspicion are the
    rare ones, and a median over twenty rows is not evidence.
    """
    rng = np.random.default_rng(seed)
    out = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        take = min(len(idx), max(min_per_class, int(round(len(idx) * n / len(y)))))
        out.append(rng.choice(idx, size=take, replace=False))
    return np.concatenate(out)


@torch.no_grad()
def nearest_distances(
    probe: np.ndarray,
    reference: np.ndarray,
    device: torch.device,
    chunk: int = 20_000,
    self_indices: np.ndarray | None = None,
) -> np.ndarray:
    """Min Euclidean distance from each probe row to any reference row.

    Chunked over the reference set: the full distance matrix would be
    len(probe) x len(reference), which does not fit. Running minimum instead.

    self_indices gives each probe row's own position in the reference array, and
    ONLY that position is masked out. Masking every zero distance instead would
    also remove a row's exact duplicates, which inflates the baseline precisely
    for the families that are heavily duplicated -- the ones under suspicion.
    """
    P = torch.from_numpy(probe).to(device)
    best = torch.full((len(P),), float("inf"), device=device)
    rows = torch.arange(len(P), device=device)

    for i in range(0, len(reference), chunk):
        R = torch.from_numpy(reference[i:i + chunk]).to(device)
        d = torch.cdist(P, R)

        if self_indices is not None:
            local = self_indices - i
            hit = (local >= 0) & (local < R.shape[0])
            if hit.any():
                h = torch.from_numpy(np.flatnonzero(hit)).to(device)
                d[rows[h], torch.from_numpy(local[hit]).to(device)] = float("inf")

        best = torch.minimum(best, d.min(dim=1).values)
        del R, d

    return best.cpu().numpy()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-config", type=Path, default=Path("configs/data.yaml"))
    p.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    p.add_argument("--data-root", type=Path, default=Path("data/processed"))
    p.add_argument("--scaler", default=None, help="Defaults to the config value.")
    p.add_argument("--n-probe", type=int, default=3000)
    p.add_argument("--min-per-class", type=int, default=250,
                   help="Floor per family. The rare families are the ones in question.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("results/near_duplicate_audit.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_cfg = load_yaml(args.data_config)
    model_cfg = load_yaml(args.model_config)

    print("Loading ...")
    s = load_centralized(data_cfg, model_cfg, args.data_root, args.scaler)
    print(f"  {s.summary()}\n")

    X_train = np.ascontiguousarray(s.X_train)

    test_idx = stratified_probe(s.y_test, args.n_probe, args.seed, args.min_per_class)
    print(f"Test probe: {len(test_idx):,} rows vs {len(X_train):,} train rows ...")
    d_test = nearest_distances(
        np.ascontiguousarray(s.X_test[test_idx]), X_train, device
    )   # no self-exclusion: test rows are not in the train array at all

    train_idx = stratified_probe(s.y_train, args.n_probe, args.seed + 1, args.min_per_class)
    print(f"Train probe: {len(train_idx):,} rows vs the rest of train ...")
    d_train = nearest_distances(
        np.ascontiguousarray(X_train[train_idx]), X_train, device, self_indices=train_idx
    )

    y_test_probe = s.y_test[test_idx]
    y_train_probe = s.y_train[train_idx]

    print(f"\n  {'family':<14}{'n':>7}{'test NN':>12}{'train NN':>12}{'ratio':>9}{'  verdict'}")
    report = {}
    for ci, name in enumerate(s.class_names):
        t = d_test[y_test_probe == ci]
        r = d_train[y_train_probe == ci]
        if len(t) == 0 or len(r) == 0:
            continue
        mt, mr = float(np.median(t)), float(np.median(r))
        ratio = mt / mr if mr > 0 else float("inf")

        if ratio < 1.5:
            verdict = "  NEAR-DUPLICATE RISK"
        elif ratio < 3.0:
            verdict = "  borderline"
        else:
            verdict = "  ok"

        print(f"  {name:<14}{len(t):>7,}{mt:>12.4f}{mr:>12.4f}{ratio:>9.2f}{verdict}")
        report[name] = {
            "n_probe": int(len(t)),
            "median_test_nn_distance": mt,
            "median_train_internal_nn_distance": mr,
            "ratio": ratio,
            "frac_test_below_train_median": float((t < mr).mean()),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "scaler": s.scaler_kind,
        "n_probe_requested": args.n_probe,
        "min_per_class": args.min_per_class,
        "seed": args.seed,
        "per_family": report,
    }, indent=2))

    print(f"\n  Ratio near 1.0 means test rows sit as close to the training set as")
    print(f"  training rows sit to each other -- the test set is then not measuring")
    print(f"  generalization for that family, and its F1 should be reported with that")
    print(f"  stated. A high ratio means the split is doing its job.")
    print(f"\n  written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
