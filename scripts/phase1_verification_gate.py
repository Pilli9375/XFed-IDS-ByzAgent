#!/usr/bin/env python
"""Phase 1 verification gate. ByzAgent Contribution B.

Reads the already-replayed client_stats.jsonl for the clean baseline and the
locked-primary poisoned run ({0,3,5}, f=3, sudden), and for each of the 5
per-client stats, every round, computes:

  - mean/std across the 7 CLEAN silos vs the 3 MALICIOUS silos {0,3,5}, in
    the POISONED run
  - the identical grouping (same silo-index split) applied to the CLEAN
    baseline run -- this is the control: are silos {0,3,5} just different by
    construction (size, composition), independent of any attack?
  - a standardized separation measure, consistently applied across all 5
    stats: Glass's delta, (mean_malicious - mean_clean) / std_clean. The
    clean-silo group's own std is used as the reference "noise scale"
    (rather than a pooled std) because the malicious group has only n=3 --
    its own std is unstable with 2 degrees of freedom, and the question
    being asked is "how many clean-silo-noise-units away is the malicious
    group", which is exactly what std_clean as the denominator answers.

No live training. Both runs' client_stats.jsonl were produced by
scripts/replay_client_stats.py against already-saved round_checkpoints/ and
silo_checkpoints/ -- see results/attacks/PHASE0_SUMMARY.md for why those
were already complete on disk before this script existed.

Defaults reproduce the original {0,3,5} f=3 gate byte-for-byte (no args
needed). Pass --poisoned-dir / --attack-manifest / --out to point this same
analysis at a different poisoned run (e.g. the f=2 {0,3} secondary
condition) without touching or duplicating this logic -- the clean baseline
is always the same run (the attack never touches val/test, so one clean
client_stats.jsonl is valid as the control for every poisoned condition).

Usage:
    python scripts/phase1_verification_gate.py
    python scripts/phase1_verification_gate.py \\
        --poisoned-dir results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3 \\
        --attack-manifest results/attacks/a0.5_s42_f2_sudden_silos0-3/attack_config.json \\
        --out results/inspection/phase1_gate_a0.5_s42_f2_sudden_silos0-3.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_ROOT / "results" / "federated" / "fedavg_a0.5_s42"
DEFAULT_POISONED_DIR = PROJECT_ROOT / "results" / "federated" / "fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5"
DEFAULT_ATTACK_MANIFEST = PROJECT_ROOT / "results" / "attacks" / "a0.5_s42_f3_sudden_silos0-3-5" / "attack_config.json"
DEFAULT_OUT_PATH = PROJECT_ROOT / "results" / "inspection" / "phase1_gate_a0.5_s42_f3_sudden_silos0-3-5.json"

STATS = ("update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy")


def load_stats(path: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in open(path)]
    return pd.DataFrame(rows)


def glass_delta(mean_mal: float, mean_clean: float, std_clean: float) -> float:
    if std_clean == 0.0 or np.isnan(std_clean):
        return float("nan")
    return float((mean_mal - mean_clean) / std_clean)


def per_round_separation(df: pd.DataFrame, malicious_silos: list[int], stat: str) -> pd.DataFrame:
    out = []
    for r, g in df.groupby("round"):
        mal = g[g["silo_id"].isin(malicious_silos)][stat].dropna()
        cln = g[~g["silo_id"].isin(malicious_silos)][stat].dropna()
        mean_mal, std_mal = mal.mean(), mal.std(ddof=1)
        mean_cln, std_cln = cln.mean(), cln.std(ddof=1)
        out.append({
            "round": int(r),
            "n_malicious": len(mal), "n_clean": len(cln),
            "mean_malicious": float(mean_mal), "std_malicious": float(std_mal),
            "mean_clean": float(mean_cln), "std_clean": float(std_cln),
            "glass_delta": glass_delta(mean_mal, mean_cln, std_cln),
        })
    return pd.DataFrame(out).sort_values("round").reset_index(drop=True)


def summarize_trend(deltas: np.ndarray) -> dict:
    """Monotonic / one-shot / noisy, judged numerically:
      - monotonic: Spearman-style sign consistency -- the delta's sign never
        flips after round 3 (allowing early-round noise before the model has
        trained at all) AND |delta| trend (first-half mean vs second-half
        mean) does not reverse direction.
      - one-shot: a large |delta| concentrated in very few rounds (max round
        contributes disproportionately vs the rest).
      - noisy: neither of the above -- sign flips throughout, no stable trend.
    """
    d = np.asarray(deltas, dtype=float)
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return {"classification": "undefined (all-NaN)", "sign_flips": None}
    signs = np.sign(d)
    sign_flips = int(np.sum(np.diff(signs[signs != 0]) != 0)) if (signs != 0).any() else 0
    first_half_mean = float(np.mean(np.abs(d[: len(d) // 2]))) if len(d) > 1 else float(np.abs(d[0]))
    second_half_mean = float(np.mean(np.abs(d[len(d) // 2:])))
    return {
        "sign_flips_total": sign_flips,
        "mean_abs_first_half": first_half_mean,
        "mean_abs_second_half": second_half_mean,
        "mean_abs_overall": float(np.mean(np.abs(d))),
        "max_abs": float(np.max(np.abs(d))),
        "max_abs_round_share": float(np.max(np.abs(d)) / (np.sum(np.abs(d)) + 1e-12)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poisoned-dir", type=Path, default=DEFAULT_POISONED_DIR)
    ap.add_argument("--attack-manifest", type=Path, default=DEFAULT_ATTACK_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    args = ap.parse_args()

    malicious_silos = json.loads(args.attack_manifest.read_text())["malicious_silos"]
    print(f"poisoned_dir = {args.poisoned_dir}")
    print(f"malicious_silos = {malicious_silos}\n")

    clean_df = load_stats(CLEAN_DIR / "client_stats.jsonl")
    poisoned_df = load_stats(args.poisoned_dir / "client_stats.jsonl")

    report: dict = {"malicious_silos": malicious_silos, "stats": {}}

    for stat in STATS:
        sep_poisoned = per_round_separation(poisoned_df, malicious_silos, stat)
        sep_clean_control = per_round_separation(clean_df, malicious_silos, stat)

        trend_poisoned = summarize_trend(sep_poisoned["glass_delta"].to_numpy())
        trend_clean_control = summarize_trend(sep_clean_control["glass_delta"].to_numpy())

        report["stats"][stat] = {
            "poisoned_run": {
                "per_round": sep_poisoned.to_dict(orient="records"),
                "trend": trend_poisoned,
            },
            "clean_run_same_silo_grouping_control": {
                "per_round": sep_clean_control.to_dict(orient="records"),
                "trend": trend_clean_control,
            },
        }

        print(f"=== {stat} ===")
        print(f"  POISONED run   -- mean|Glass's delta| across 20 rounds: "
              f"{trend_poisoned['mean_abs_overall']:.3f}  "
              f"(first-half {trend_poisoned['mean_abs_first_half']:.3f} / "
              f"second-half {trend_poisoned['mean_abs_second_half']:.3f}, "
              f"sign flips: {trend_poisoned['sign_flips_total']})")
        print(f"  CLEAN control  -- mean|Glass's delta| across 20 rounds: "
              f"{trend_clean_control['mean_abs_overall']:.3f}  "
              f"(first-half {trend_clean_control['mean_abs_first_half']:.3f} / "
              f"second-half {trend_clean_control['mean_abs_second_half']:.3f}, "
              f"sign flips: {trend_clean_control['sign_flips_total']})")
        ratio = (trend_poisoned["mean_abs_overall"] /
                 (trend_clean_control["mean_abs_overall"] + 1e-12))
        print(f"  ratio (poisoned / clean-control): {ratio:.2f}x\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
