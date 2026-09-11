"""
XFed-IDS -- Phase 3, step 3: Dirichlet partitioning into silo shards.

Partitions train_pool and test_global across N simulated organizations (silos)
using a Dirichlet distribution over labels, for every combination of
alpha and seed in the config.

WHAT DIRICHLET ALPHA CONTROLS
    For each family k independently, draw a proportion vector over the N silos:
        p_k ~ Dir(alpha * 1_N)
    p_k[i] is the fraction of family k's flows assigned to silo i.

    alpha -> 0    draws approach one-hot: a family lands almost entirely in one
                  silo. Severe heterogeneity, the pathological case.
    alpha -> inf  draws approach uniform: every silo gets ~1/N of every family.
                  Effectively IID -- the control condition.
    alpha = 1     flat; all proportion vectors equally likely.

    Sweeping alpha is what lets us report HOW performance degrades with
    heterogeneity rather than just that it does. Without the near-IID control
    we could not separate "federation costs accuracy" from "non-IID costs
    accuracy" -- those are different claims.

WHY ASSIGNMENTS, NOT DATA COPIES
    Writing 90 full shards (10 silos x 3 alphas x 3 seeds) would cost several
    GB and would be invalidated by any change upstream in cleaning. Writing the
    row -> silo assignment costs ~2MB per config, and the manifest hash covers
    the assignment array itself. That is stronger verification than hashing
    file contents: it catches a partitioning bug that yields different output
    from identical config inputs.

    Use load_silo() below to materialize a silo's rows at training time.

A silo's train and test partitions use the SAME p_k, so each silo's local test
distribution matches its own local train distribution -- which is what makes a
per-silo evaluation meaningful.

Input:  <processed_dir>/train_pool.parquet, test_global.parquet
Output: <processed_dir>/partitions/assign_a{alpha}_s{seed}.parquet
        <processed_dir>/partitions/manifest.json
        <processed_dir>/partitions/label_distribution_a{alpha}_s{seed}.csv

Usage:
    python src/data/partition.py [--config configs/data.yaml]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dirichlet_assign(
    families: pd.Series,
    n_silos: int,
    alpha: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, list[float]]]:
    """
    Assign each row to a silo via a per-family Dirichlet draw.

    Returns the silo assignment array and the proportion vectors actually
    drawn (recorded in the manifest so a run can be audited without rerunning).

    Proportions are applied by splitting each family's shuffled row indices at
    the cumulative proportion boundaries. This gives the exact requested
    proportions rather than the multinomial noise you would get from sampling
    each row independently -- which matters for the small families, where
    sampling noise could swing a silo's share by a lot.
    """
    assignment = np.empty(len(families), dtype=np.int16)
    proportions: dict[str, list[float]] = {}

    for family in sorted(families.unique()):
        idx = np.flatnonzero((families == family).to_numpy())
        rng.shuffle(idx)

        p = rng.dirichlet(np.full(n_silos, alpha))
        proportions[family] = [float(x) for x in p]

        # Cumulative boundaries -> contiguous chunks of the shuffled indices.
        cuts = (np.cumsum(p) * len(idx)).astype(int)[:-1]
        for silo, chunk in enumerate(np.split(idx, cuts)):
            assignment[chunk] = silo

    return assignment, proportions


def hash_assignment(arr: np.ndarray) -> str:
    """SHA256 over the raw assignment bytes. Order-sensitive by design."""
    return hashlib.sha256(arr.tobytes()).hexdigest()


def load_silo(
    processed_dir: Path,
    silo: int,
    alpha: float,
    seed: int,
    split: str = "train",
    verify_hash: bool = True,
) -> pd.DataFrame:
    """
    Materialize one silo's rows for a given (alpha, seed, split).

    This is the function Chat 03 / 04 should call. It checks the assignment
    against the manifest hash before returning anything, so a silently
    regenerated or corrupted partition fails loudly instead of quietly
    changing your results.

    split: "train" (from train_pool) or "test" (from test_global)
    """
    part_dir = processed_dir / "partitions"
    tag = f"a{alpha}_s{seed}"
    assign = pd.read_parquet(part_dir / f"assign_{tag}_{split}.parquet")["silo"].to_numpy(np.int16)

    if verify_hash:
        manifest = json.loads((part_dir / "manifest.json").read_text())
        entry = manifest["configs"][tag]
        if hash_assignment(assign) != entry[f"hash_{split}"]:
            raise RuntimeError(
                f"Assignment hash mismatch for {tag} ({split}). The partition on "
                f"disk is not the one recorded in the manifest. Do not train on "
                f"this -- regenerate with partition.py or restore the original."
            )

    source = "train_pool.parquet" if split == "train" else "test_global.parquet"
    df = pd.read_parquet(processed_dir / source)
    if len(assign) != len(df):
        raise RuntimeError(
            f"Assignment length {len(assign):,} != {source} length {len(df):,}. "
            f"The partition was generated against a different version of the "
            f"data. Re-run the pipeline from clean.py."
        )
    return df.loc[assign == silo].copy()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    processed = Path(cfg["paths"]["processed_dir"])
    part_dir = processed / "partitions"
    part_dir.mkdir(parents=True, exist_ok=True)

    n_silos = cfg["federation"]["n_silos"]
    alphas = cfg["federation"]["alphas"]
    seeds = cfg["federation"]["seeds"]

    print("[1/3] loading splits")
    train = pd.read_parquet(processed / "train_pool.parquet", columns=["family"])
    test = pd.read_parquet(processed / "test_global.parquet", columns=["family"])
    print(f"        train_pool: {len(train):,}  test_global: {len(test):,}")
    print(f"        {n_silos} silos, alphas={alphas}, seeds={seeds}")

    manifest: dict = {
        "n_silos": n_silos,
        "alphas": alphas,
        "seeds": seeds,
        "n_train_pool": len(train),
        "n_test_global": len(test),
        "source_family_counts": train["family"].value_counts().to_dict(),
        "configs": {},
    }

    print(f"\n[2/3] generating {len(alphas) * len(seeds)} partitions")
    empty_cells_report = []

    for alpha in alphas:
        for seed in seeds:
            tag = f"a{alpha}_s{seed}"
            rng = np.random.default_rng(seed)

            train_assign, props = dirichlet_assign(
                train["family"], n_silos, alpha, rng
            )
            # Same rng stream continues -> test draws its own proportions.
            # Reseeded deliberately so a silo's test mix mirrors its train mix.
            rng_test = np.random.default_rng(seed)
            test_assign, _ = dirichlet_assign(
                test["family"], n_silos, alpha, rng_test
            )

            pd.DataFrame({"silo": train_assign}).to_parquet(
                part_dir / f"assign_{tag}_train.parquet", index=False
            )
            pd.DataFrame({"silo": test_assign}).to_parquet(
                part_dir / f"assign_{tag}_test.parquet", index=False
            )

            # Per-silo per-family counts -> artifact 4.
            dist = (
                pd.crosstab(pd.Series(train_assign, name="silo"), train["family"].to_numpy())
                .reindex(range(n_silos), fill_value=0)
            )
            dist.to_csv(part_dir / f"label_distribution_{tag}.csv")

            empty = int((dist == 0).sum().sum())
            if empty:
                empty_cells_report.append((tag, empty))

            manifest["configs"][tag] = {
                "alpha": alpha,
                "seed": seed,
                "hash_train": hash_assignment(train_assign),
                "hash_test": hash_assignment(test_assign),
                "dirichlet_proportions_train": props,
                "silo_sizes_train": pd.Series(train_assign).value_counts().sort_index().to_dict(),
                "empty_silo_family_cells": empty,
            }
            print(f"        {tag}: {empty} empty (silo, family) cells")

    print("\n[3/3] writing manifest")
    (part_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    print(f"\nWrote {len(alphas) * len(seeds)} assignments + manifest to {part_dir}")
    if empty_cells_report:
        print("\n  Empty (silo, family) cells by config -- expected at low alpha,")
        print("  and a reportable finding for the paper:")
        for tag, n in empty_cells_report:
            print(f"    {tag}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
