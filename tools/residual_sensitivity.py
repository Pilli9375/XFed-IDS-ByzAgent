#!/usr/bin/env python
"""Pre-specified sensitivity check (planning chat, 2026-10-14), read-only,
stored files only.

Rule, fixed before computing: exclude any (alpha, seed, silo) whose FINAL
FedAvg SHAP file has additivity_max_diff > 3.336. 3.336 is the largest
per-row residual in the 500-row validation pool
(results/shap/fedavg_a0.5_s42/val_pool_summary.json). Flags come from
results/inspection/residual_audit.csv (tools/residual_audit.py).

Recomputes the headline medians the way tools/agreement_metrics.py does --
median over family-eligible (silo, sample) rows of
results/inspection/agreement_metrics.csv, per alpha -- with and without the
exclusion. As a secondary view, it also gives the median of the per-silo
medians in per_silo_agreement.csv. The baseline must reproduce the stated
headline numbers or the script refuses to write.

The one flagged GLOBAL model (alpha=5.0, seed 1337) is not a silo, so the
rule does not exclude it. Every silo's agreement in that config is measured
against that global model, though, so a separately labelled variant drops
the whole (5.0, 1337) config.

Writes results/inspection/residual_sensitivity.json. Edits no headline number.
Run as: python -m tools.residual_sensitivity
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INSPECTION = ROOT / "results" / "inspection"
VAL_POOL_SUMMARY = ROOT / "results" / "shap" / "fedavg_a0.5_s42" / "val_pool_summary.json"

# Stated headline medians (CLAUDE.md / PROJECT_INSTRUCTIONS.md "Headline
# numbers"), used only to check the baseline recomputation reproduces them.
EXPECTED = {0.1: (0.333, 0.592), 0.5: (0.538, 0.787), 5.0: (0.667, 0.844)}


def _summ(rows: pd.DataFrame) -> dict:
    return {
        "jaccard_at_10_median": round(float(rows["jaccard_at_10"].median()), 6),
        "kendall_weighted_tau_median": round(float(rows["kendall_weighted_tau"].median()), 6),
        "n_rows": int(len(rows)),
        "n_silos": int(rows[["seed", "silo"]].drop_duplicates().shape[0]),
    }


def main() -> None:
    threshold = json.loads(VAL_POOL_SUMMARY.read_text())["additivity_abs_logit"]["max"]
    audit = pd.read_csv(INSPECTION / "residual_audit.csv")
    final = audit[(audit["algo"] == "fedavg") & (audit["pass"] == "final")]
    flagged = final[final["additivity_max_diff"] > threshold]
    flagged_silos = flagged[flagged["model"] == "silo"][["alpha", "seed", "silo", "additivity_max_diff"]]
    flagged_globals = flagged[flagged["model"] == "global"][["alpha", "seed", "additivity_max_diff"]]
    excl = {(float(r.alpha), int(r.seed), int(r.silo)) for r in flagged_silos.itertuples()}

    am = pd.read_csv(INSPECTION / "agreement_metrics.csv")
    elig = am[am["family_eligible"]].copy()
    elig["key"] = list(zip(elig["alpha"].astype(float), elig["seed"].astype(int), elig["silo"].astype(int)))
    per_silo = pd.read_csv(INSPECTION / "per_silo_agreement.csv")
    per_silo["key"] = list(zip(per_silo["alpha"].astype(float), per_silo["seed"].astype(int), per_silo["silo"].astype(int)))

    out = {
        "rule": f"exclude (alpha, seed, silo) whose final FedAvg SHAP additivity_max_diff > {threshold} "
                "(val-pool per-row max); pre-specified before computing",
        "threshold": threshold,
        "threshold_source": VAL_POOL_SUMMARY.relative_to(ROOT).as_posix(),
        "flagged_silos": flagged_silos.round({"additivity_max_diff": 3}).to_dict("records"),
        "flagged_global_models_not_excluded_by_rule": flagged_globals.round({"additivity_max_diff": 3}).to_dict("records"),
        "by_alpha": {},
    }
    for alpha in sorted(elig["alpha"].unique()):
        a = float(alpha)
        rows = elig[elig["alpha"] == alpha]
        base = _summ(rows)
        exp_j, exp_t = EXPECTED[a]
        if round(base["jaccard_at_10_median"], 3) != exp_j or round(base["kendall_weighted_tau_median"], 3) != exp_t:
            raise RuntimeError(f"baseline at alpha={a} does not reproduce the headline ({base} vs {EXPECTED[a]})")
        kept = rows[~rows["key"].isin(excl)]
        flagged_here = sorted(k for k in excl if k[0] == a)
        present = sorted({k for k in rows["key"] if k in excl})
        ps = per_silo[per_silo["alpha"] == alpha]
        entry = {
            "baseline": base,
            "rule_applied": _summ(kept),
            "flagged_silos_in_alpha": [list(k) for k in flagged_here],
            "flagged_silos_with_eligible_rows": [list(k) for k in present],
            "rows_dropped": int(len(rows) - len(kept)),
            "silos_dropped": int(base["n_silos"] - _summ(kept)["n_silos"]) if len(kept) else base["n_silos"],
            "secondary_median_of_per_silo_medians": {
                "baseline": round(float(ps["jaccard_at_10"].median()), 6),
                "rule_applied": round(float(ps[~ps["key"].isin(excl)]["jaccard_at_10"].median()), 6),
                "n_silos_baseline": int(len(ps)),
                "n_silos_rule_applied": int((~ps["key"].isin(excl)).sum()),
            },
        }
        g = flagged_globals[flagged_globals["alpha"] == alpha]
        if len(g):
            seeds = set(int(s) for s in g["seed"])
            kept_v = kept[~kept["seed"].astype(int).isin(seeds)]
            entry["variant_also_drop_configs_with_flagged_global"] = {
                "dropped_seeds": sorted(seeds),
                **_summ(kept_v),
                "rows_dropped_vs_baseline": int(len(rows) - len(kept_v)),
            }
        out["by_alpha"][str(a)] = entry

    path = INSPECTION / "residual_sensitivity.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
