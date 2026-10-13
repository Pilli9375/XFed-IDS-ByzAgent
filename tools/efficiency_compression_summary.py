"""Efficiency Part C3 -- compressed client->server updates vs uncompressed
FedAvg at alpha=0.5, seeds 42/1337/2024. Validation macro-F1 only (the method
path has no test evaluation). Reads run outputs; trains nothing.

Uncompressed baseline: the published FedAvg round_history.json per seed
(compression.baseline in configs/efficiency.yaml). The regression run on the
edited code path (compression.runs.regression_seeds) is compared with the
published curve to show the default path is unchanged.

Run from project root: python tools/efficiency_compression_summary.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def curve(path: Path) -> list[float]:
    hist = sorted(json.loads(path.read_text()), key=lambda r: r["round"])
    return [r["val_macro_f1_headline"] for r in hist]


def stats(c: list[float], final_k: int) -> dict:
    best = max(range(len(c)), key=lambda i: c[i])
    return {"best_by_val": c[best], "best_round": best, "final_round": c[-1],
            f"final_{final_k}_mean": statistics.mean(c[-final_k:]),
            "mean_rounds_1_to_20": statistics.mean(c[1:])}


def mean_sd(xs):
    return {"mean": statistics.mean(xs), "sd": statistics.stdev(xs) if len(xs) > 1 else None, "values": xs}


def main() -> None:
    eff = yaml.safe_load((ROOT / "configs/efficiency.yaml").read_text())
    ccfg = eff["compression"]
    bound = float(eff["inference"]["max_abs_macro_f1_delta"])
    fm = yaml.safe_load((ROOT / "configs/federated_methods.yaml").read_text())
    runs_root = ROOT / fm["experiment"]["results_root"] / ccfg["runs"]["run_group"]
    alpha, method = str(ccfg["runs"]["alpha"]), ccfg["runs"]["method"]
    final_k = 5

    def base_path(seed):
        return ROOT / ccfg["baseline"]["runs_dir"] / ccfg["baseline"]["tag_pattern"].format(alpha=alpha, seed=seed) / "round_history.json"

    # Regression: uncompressed run on the edited code vs the published curve.
    regression = {}
    for seed in ccfg["runs"]["regression_seeds"]:
        new = curve(runs_root / f"{method}_a{alpha}_s{seed}" / "round_history.json")
        old = curve(base_path(seed))
        regression[str(seed)] = {"rounds": len(new), "identical": new == old,
                                 "max_abs_diff": max(abs(a - b) for a, b in zip(new, old))}
    reg_timing = {}
    for seed in ccfg["runs"]["regression_seeds"]:
        rows = [json.loads(l) for l in (runs_root / f"{method}_a{alpha}_s{seed}" / "round_timing_comm.jsonl").read_text().splitlines()]
        reg_timing[str(seed)] = {"bytes_up_per_round": sorted({r["bytes_up"] for r in rows}),
                                 "bytes_down_per_round": sorted({r["bytes_down"] for r in rows}),
                                 "wall_s_rounds2plus_median": statistics.median(r["wall_time_s"] for r in rows[1:])}

    schemes = {}
    flags = []
    for scheme in ccfg["runs"]["schemes"]:
        per_seed = {}
        for seed in ccfg["runs"]["seeds"]:
            d = runs_root / f"{method}_up-{scheme}_a{alpha}_s{seed}"
            comp, base = curve(d / "round_history.json"), curve(base_path(seed))
            sc, sb = stats(comp, final_k), stats(base, final_k)
            rows = [json.loads(l) for l in (d / "round_timing_comm.jsonl").read_text().splitlines()]
            summary = json.loads((d / "run_summary.json").read_text())
            assert summary["upload_compression"] == scheme and summary["test_evaluated"] is False
            up = sorted({r["bytes_up"] for r in rows})
            down = sorted({r["bytes_down"] for r in rows})
            per_seed[str(seed)] = {
                "compressed": sc, "uncompressed_published": sb,
                "delta": {k: sc[k] - sb[k] for k in sc if k != "best_round"},
                "bytes_up_per_round": up, "bytes_down_per_round": down,
                "wall_s_rounds2plus_median": statistics.median(r["wall_time_s"] for r in rows[1:]),
                "run_dir": str(d.relative_to(ROOT)).replace("\\", "/"),
            }
        fp32_up = 79396 * 10
        up_vals = {v for s in per_seed.values() for v in s["bytes_up_per_round"]}
        assert len(up_vals) == 1, up_vals
        up_b = up_vals.pop()
        down_b = per_seed[str(ccfg["runs"]["seeds"][0])]["bytes_down_per_round"][0]
        agg = {k: mean_sd([s["delta"][k] for s in per_seed.values()])
               for k in ("best_by_val", "final_round", f"final_{final_k}_mean", "mean_rounds_1_to_20")}
        schemes[scheme] = {
            "bytes_up_per_round": up_b,
            "bytes_up_saved_vs_fp32": fp32_up - up_b,
            "bytes_up_saved_pct": 100 * (fp32_up - up_b) / fp32_up,
            "bytes_total_per_round": up_b + down_b,
            "bytes_total_saved_pct": 100 * (fp32_up - up_b) / (2 * fp32_up),
            "delta_vs_uncompressed_over_seeds": agg,
            "per_seed": per_seed,
        }
        for k, v in agg.items():
            if k == "best_by_val":
                over = [x for x in v["values"] if abs(x) > bound]
                if over or abs(v["mean"]) > bound:
                    flags.append(f"{scheme}: best-by-val delta per seed {v['values']} (mean {v['mean']:+.4f}) exceeds {bound}")

    out = {
        "source": (f"Validation-only method-path runs in {runs_root.relative_to(ROOT).as_posix()}/ "
                   f"({method}, alpha={alpha}, seeds {ccfg['runs']['seeds']}, schemes {ccfg['runs']['schemes']}); "
                   f"uncompressed baseline = published {ccfg['baseline']['runs_dir']}/fedavg_a{alpha}_s*/round_history.json; "
                   "run log results/efficiency/compression_run_log.jsonl. Script: tools/efficiency_compression_summary.py. "
                   "No test rows."),
        "kind": "3 seeds per scheme, one run each; uncompressed comparison is the published run per seed",
        "metric": "val_macro_f1_headline; best_by_val = max over rounds 0..20 (selection rule); final_5_mean = rounds 16-20",
        "regression_uncompressed_vs_published": regression,
        "regression_timing": reg_timing,
        "schemes": schemes,
        "flags_delta_over_bound": flags,
    }
    (ROOT / ccfg["output"]).write_text(json.dumps(out, indent=2))
    print(json.dumps({"regression": regression, "regression_timing": reg_timing}, indent=2))
    for scheme, s in schemes.items():
        print(f"\n{scheme}: up {s['bytes_up_per_round']} B/round (saved {s['bytes_up_saved_pct']:.1f}% of uplink, "
              f"{s['bytes_total_saved_pct']:.1f}% of total)")
        for k, v in s["delta_vs_uncompressed_over_seeds"].items():
            print(f"  delta {k}: mean {v['mean']:+.4f} sd {v['sd']:.4f}  per seed {[round(x, 4) for x in v['values']]}")
        for seed, p in s["per_seed"].items():
            print(f"  s{seed}: comp best {p['compressed']['best_by_val']:.4f}@{p['compressed']['best_round']} "
                  f"base best {p['uncompressed_published']['best_by_val']:.4f}@{p['uncompressed_published']['best_round']} "
                  f"wall {p['wall_s_rounds2plus_median']:.1f}s")
    print("\nflags:", flags)


if __name__ == "__main__":
    main()
