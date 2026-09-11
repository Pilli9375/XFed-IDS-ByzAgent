"""ByzAgent Phase 2 -- per-run analysis: the 4 locked statistics, recovery
fraction, and mechanism-level signature. Read-only against a completed run's
artifacts (round_history.json, krum_selection.jsonl / trim_rate.jsonl).

Locked anchors (PHASE0_SUMMARY.md, paired same-seed vs. clean_s42,
final-5-round mean of val_macro_f1_headline):
    f=3 {0,3,5}: clean 0.9513, poisoned-FedAvg 0.8746, gap 0.0767
    f=2 {0,3}:   clean 0.9513, poisoned-FedAvg 0.8787, gap 0.0726

recovery_fraction = (defense_final5mean - poisoned_FedAvg_final5mean)
                     / (clean_final5mean - poisoned_FedAvg_final5mean)
Threshold: >= 0.5 succeeds (recovers at least half the gap), < 0.5 fails.
Always report the raw fraction, never just pass/fail.

Mechanism-level signature (Krum family): per-round exclusion rate of the
TRUE malicious silos (selected: false), vs. chance baseline f/n_silos --
this equals the exact hypergeometric expectation ONLY when num_excluded
(= n_silos - num_nodes_to_select) equals f, which holds by construction for
Multi-Krum (num_nodes_to_select = n - f) but NOT for classical Krum
(num_nodes_to_select = 1 always, so num_excluded = n-1 regardless of f) --
flagged explicitly in the output, not silently corrected.

Mechanism-level signature (trimmed-mean): per-(round,silo) trim_rate for the
TRUE malicious silos, vs. the LOCKED f/n chance baseline (pre-registration
text, verbatim). Also reports 2*beta (= 2f/n), the mechanically-derived
symmetric chance baseline for a two-tailed per-coordinate trim -- computed
and shown alongside, NOT substituted for the locked f/n number, flagged as
an open methodology question for 01_Planning to review rather than resolved
here.
"""
import json
import statistics
import sys
from pathlib import Path

ANCHORS = {
    "f3": {"clean_final5mean": 0.9513, "poisoned_fedavg_final5mean": 0.8746},
    "f2": {"clean_final5mean": 0.9513, "poisoned_fedavg_final5mean": 0.8787},
}


def load_round_history(run_dir: Path) -> list[dict]:
    rh = json.loads((run_dir / "round_history.json").read_text())
    return [r for r in rh if r["round"] >= 1]  # exclude round 0 (pre-training initial eval)


def four_stats(rounds: list[dict]) -> dict:
    vals = [r["val_macro_f1_headline"] for r in rounds]
    final5 = [r["val_macro_f1_headline"] for r in rounds if r["round"] >= len(rounds) - 4]
    return {
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "final5mean": statistics.mean(final5),
        "max": max(vals),
    }


def recovery_fraction(defense_final5mean: float, condition: str) -> float:
    a = ANCHORS[condition]
    gap = a["clean_final5mean"] - a["poisoned_fedavg_final5mean"]
    return (defense_final5mean - a["poisoned_fedavg_final5mean"]) / gap


def krum_mechanism(run_dir: Path, malicious_silos: list[int], f: int, n_silos: int = 10) -> dict:
    path = run_dir / "krum_selection.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    num_nodes_to_select = rows[0]["num_nodes_to_select"]
    num_excluded = n_silos - num_nodes_to_select

    rounds = sorted(set(r["round"] for r in rows))
    excl_rates = []
    for rnd in rounds:
        round_rows = {r["silo_id"]: r for r in rows if r["round"] == rnd}
        mal_excluded = sum(1 for s in malicious_silos if not round_rows[s]["selected"])
        excl_rates.append(mal_excluded / len(malicious_silos))

    observed = statistics.mean(excl_rates)
    chance_f_over_n = f / n_silos
    mechanically_correct_chance = num_excluded / n_silos
    return {
        "num_nodes_to_select": num_nodes_to_select,
        "num_excluded_per_round": num_excluded,
        "observed_malicious_exclusion_rate": observed,
        "chance_baseline_f_over_n": chance_f_over_n,
        "mechanically_correct_chance_baseline": mechanically_correct_chance,
        "baseline_note": (
            "f/n IS the correct hypergeometric chance baseline here (num_excluded == f by construction)"
            if num_excluded == f else
            f"f/n is NOT the mechanically correct chance baseline here -- num_excluded={num_excluded} != f={f}; "
            f"true chance baseline is num_excluded/n_silos={mechanically_correct_chance:.3f}"
        ),
        "per_round_exclusion_rate": dict(zip(rounds, excl_rates)),
    }


def trimmedmean_mechanism(run_dir: Path, malicious_silos: list[int], f: int, beta: float, n_silos: int = 10) -> dict:
    path = run_dir / "trim_rate.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    mal_rows = [r for r in rows if r["silo_id"] in malicious_silos]
    clean_rows = [r for r in rows if r["silo_id"] not in malicious_silos]
    observed_mal = statistics.mean(r["trim_rate"] for r in mal_rows)
    observed_clean = statistics.mean(r["trim_rate"] for r in clean_rows)
    return {
        "observed_malicious_trim_rate": observed_mal,
        "observed_clean_trim_rate": observed_clean,
        "chance_baseline_f_over_n_LOCKED": f / n_silos,
        "chance_baseline_2beta_MECHANICAL_not_locked": 2 * beta,
        "note": (
            "LOCKED pre-registration baseline is f/n. Mechanical derivation (2*lowercut/n_silos = 2*beta, "
            "since BOTH tails count as 'discarded' each coordinate) gives a different value -- shown for "
            "transparency, NOT substituted for the locked comparison. Flagged for 01_Planning, not resolved here."
        ),
    }


def report(run_dir: str, condition: str, defense_strategy: str, malicious_silos: list[int] | None, f: int | None, beta: float | None):
    run_dir = Path(run_dir)
    rounds = load_round_history(run_dir)
    stats = four_stats(rounds)
    print(f"=== {run_dir.name} ({defense_strategy}, condition={condition}) ===")
    print(f"ORACLE f disclosure: this defense was given the TRUE attack strength "
          f"(num_malicious_nodes={f if f is not None else 'n/a (clean control, assumed f=3)'}), not estimated.")
    print(f"mean={stats['mean']:.4f}  median={stats['median']:.4f}  "
          f"final5mean={stats['final5mean']:.4f}  max={stats['max']:.4f}")

    if condition in ("f3", "f2"):
        rf = recovery_fraction(stats["final5mean"], condition)
        verdict = "SUCCEEDS (>=0.5)" if rf >= 0.5 else "FAILS AS PRE-REGISTERED (<0.5)"
        print(f"recovery_fraction = {rf:.4f}  -> {verdict}")

        if defense_strategy in ("multikrum", "krum"):
            mech = krum_mechanism(run_dir, malicious_silos, f)
            print(f"mechanism: observed malicious exclusion rate = "
                  f"{mech['observed_malicious_exclusion_rate']:.4f}  "
                  f"vs chance f/n = {mech['chance_baseline_f_over_n']:.4f}")
            print(f"  {mech['baseline_note']}")
        elif defense_strategy == "trimmed_mean":
            mech = trimmedmean_mechanism(run_dir, malicious_silos, f, beta)
            print(f"mechanism: observed malicious trim rate = "
                  f"{mech['observed_malicious_trim_rate']:.4f}  "
                  f"(clean silos: {mech['observed_clean_trim_rate']:.4f})  "
                  f"vs LOCKED chance f/n = {mech['chance_baseline_f_over_n_LOCKED']:.4f}  "
                  f"(mechanical 2*beta = {mech['chance_baseline_2beta_MECHANICAL_not_locked']:.4f})")
    else:
        print("condition=clean: no recovery_fraction / mechanism-level signature (no true malicious silos).")
    print()


if __name__ == "__main__":
    # Usage: python phase2_analysis.py <run_dir> <condition:f3|f2|clean> <strategy> [malicious_silos csv] [f] [beta]
    run_dir = sys.argv[1]
    condition = sys.argv[2]
    strategy = sys.argv[3]
    malicious_silos = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else None
    f = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else None
    beta = float(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else None
    report(run_dir, condition, strategy, malicious_silos, f, beta)
