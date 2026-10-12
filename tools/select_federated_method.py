"""Apply the preregistered selection rule (docs/preregistration_accuracy.md,
Part 1) to the validation-only grid. Reads round_history.json files only --
no test-set metric exists for any method run, and this script never opens
final_metrics.json for the FedAvg baseline either.

  python tools/select_federated_method.py

Writes results/federated_methods/validation_summary.json and selection.json.
Std is numpy's default (population, ddof=0), the convention of the published
headline table (scripts/aggregate_federated.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "federated_methods.yaml").read_text())
EXP, SEL = CFG["experiment"], CFG["selection"]
RES = ROOT / EXP["results_root"]
METRIC = SEL["metric"]


def best_of(hist: list[dict]) -> dict:
    # First maximum, same tie behaviour as the harness (strict > while scanning).
    best = max(hist, key=lambda r: (r[METRIC], -r["round"]))
    return {"best_round": best["round"], "best_val": best[METRIC],
            "final_round_val": hist[-1][METRIC], "n_rounds_logged": len(hist)}


def baseline_run(alpha: str, seed: int) -> Path:
    b = EXP["baseline"]
    return ROOT / b["runs_dir"] / b["tag_pattern"].format(alpha=alpha, seed=seed) / "round_history.json"


def method_run(method: str, alpha: str, seed: int, group: str = "runs") -> Path:
    return RES / group / f"{method}_a{alpha}_s{seed}"


def comm_summary(run_dir: Path) -> dict:
    rows = [json.loads(l) for l in (run_dir / "round_timing_comm.jsonl").read_text().splitlines()]
    return {"wall_time_s_per_round_mean": float(np.mean([r["wall_time_s"] for r in rows])),
            "wall_time_s_total_rounds": float(np.sum([r["wall_time_s"] for r in rows])),
            "bytes_per_round": sorted({r["bytes_total"] for r in rows})}


def candidates() -> tuple[list[str], list[str]]:
    """The YAML grid minus whatever the timing-only budget guard dropped
    (results/federated_methods/budget_guard.jsonl, rule in the prereg)."""
    dropped: list[str] = []
    guard = RES / "budget_guard.jsonl"
    if guard.exists():
        for line in guard.read_text().splitlines():
            rec = json.loads(line)
            if not rec["allowed"]:
                dropped = rec["remaining_candidates"]
    return [m for m in CFG["grid"] if m not in dropped], dropped


def main() -> None:
    alphas, seeds = EXP["alphas"], EXP["seeds"]
    grid, dropped = candidates()
    summary: dict = {"metric": METRIC, "std": "population (ddof=0)", "candidates": grid,
                     "dropped_by_budget_guard": dropped, "methods": {}}

    # Baseline: published FedAvg runs.
    entry = {"source": "published runs, " + EXP["baseline"]["runs_dir"], "alphas": {}}
    for a in alphas:
        runs = {s: best_of(json.loads(baseline_run(a, s).read_text())) for s in seeds}
        vals = [runs[s]["best_val"] for s in seeds]
        entry["alphas"][a] = {"per_seed": runs, "mean": float(np.mean(vals)), "std": float(np.std(vals))}
    summary["methods"]["fedavg"] = entry

    missing = []
    for m in grid:
        entry = {"source": str((RES / "runs").relative_to(ROOT)), "alphas": {}}
        for a in alphas:
            runs = {}
            for s in seeds:
                d = method_run(m, a, s)
                if not (d / "run_summary.json").exists():
                    missing.append(f"{m}_a{a}_s{s}")
                    continue
                rs = json.loads((d / "run_summary.json").read_text())
                assert rs["test_evaluated"] is False
                runs[s] = {**best_of(json.loads((d / "round_history.json").read_text())), **comm_summary(d)}
            if len(runs) == len(seeds):
                vals = [runs[s]["best_val"] for s in seeds]
                entry["alphas"][a] = {"per_seed": runs, "mean": float(np.mean(vals)), "std": float(np.std(vals))}
            else:
                entry["alphas"][a] = {"per_seed": runs, "incomplete": True}
        summary["methods"][m] = entry

    # Regression check: FedAvg re-run on the new path vs the published curve.
    reg = method_run("fedavg", "0.1", 42, "regression")
    if (reg / "round_history.json").exists():
        new = json.loads((reg / "round_history.json").read_text())
        old = json.loads(baseline_run("0.1", 42).read_text())
        diffs = [abs(n[METRIC] - o[METRIC]) for n, o in zip(new, old)]
        summary["regression_fedavg_a0.1_s42"] = {
            "rounds_compared": len(diffs), "max_abs_diff": float(max(diffs)),
            "per_round_new": [n[METRIC] for n in new], "per_round_published": [o[METRIC] for o in old],
            "best_new": best_of(new), "best_published": best_of(old),
        }

    (RES / "validation_summary.json").write_text(json.dumps(summary, indent=2))
    if missing:
        print("INCOMPLETE, missing runs:", missing)
        return

    # ---- the preregistered rule ----
    p, g = SEL["primary_alpha"], SEL["guard_alpha"]
    base_p = summary["methods"]["fedavg"]["alphas"][p]["mean"]
    base_g = summary["methods"]["fedavg"]["alphas"][g]["mean"]
    flags = []
    for m in grid:
        for s, r in summary["methods"][m]["alphas"][p]["per_seed"].items():
            if r["best_val"] > SEL["centralized_ceiling"]:
                flags.append(f"STOP AND FLAG: {m} alpha={p} seed={s} val {r['best_val']:.4f} > {SEL['centralized_ceiling']}")

    table = []
    for order, m in enumerate(grid):
        mp = summary["methods"][m]["alphas"][p]["mean"]
        mg = summary["methods"][m]["alphas"][g]["mean"]
        table.append({"method": m, "order": order, f"mean_a{p}": mp, f"mean_a{g}": mg,
                      f"delta_a{p}_vs_fedavg": mp - base_p, f"delta_a{g}_vs_fedavg": mg - base_g,
                      "guard_pass": mg >= base_g - SEL["guard_max_drop"]})
    eligible = [t for t in table if t["guard_pass"]]
    eligible.sort(key=lambda t: (-round(t[f"mean_a{p}"], 4), -t[f"mean_a{g}"], t["order"]))
    chosen = eligible[0] if eligible else None
    if chosen is None:
        outcome, reason = "no improvement", "no candidate passed the alpha=0.5 guard"
    elif chosen[f"mean_a{p}"] < base_p + SEL["min_improvement"]:
        outcome = "no improvement"
        reason = (f"best eligible {chosen['method']} alpha={p} mean {chosen[f'mean_a{p}']:.4f} < "
                  f"FedAvg {base_p:.4f} + {SEL['min_improvement']} = {base_p + SEL['min_improvement']:.4f}")
    else:
        outcome = "selected"
        reason = (f"{chosen['method']} alpha={p} mean {chosen[f'mean_a{p}']:.4f} >= "
                  f"{base_p + SEL['min_improvement']:.4f}; alpha={g} mean {chosen[f'mean_a{g}']:.4f} >= "
                  f"{base_g - SEL['guard_max_drop']:.4f}")

    selection = {
        "rule": SEL, "fedavg_baseline": {f"mean_a{p}": base_p, f"mean_a{g}": base_g},
        "threshold_primary": base_p + SEL["min_improvement"],
        "threshold_guard": base_g - SEL["guard_max_drop"],
        "dropped_by_budget_guard": dropped, "candidates": table, "outcome": outcome,
        "chosen": chosen["method"] if outcome == "selected" else None,
        "best_eligible": chosen["method"] if chosen else None,
        "reason": reason, "flags": flags,
    }
    (RES / "selection.json").write_text(json.dumps(selection, indent=2))
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
