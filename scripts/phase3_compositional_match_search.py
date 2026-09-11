"""ByzAgent Phase 3 -- compositionally-matched attack search.

Read-only, no training. Direct follow-on to the compositional-extremity
confound found in scripts/phase3_compositional_check.py: checks whether a
comparably-strong f=3/f=2 attack can be built from ONLY the high-Benign-
share silos ({1,2,4,6,7,9}, 81.5-98.0% Benign), by filtering Phase 0's
existing frontier enumeration (results/inspection/frontier_f{2,3}_a0.5_s42.csv,
already covers all C(10,3)/C(10,2) combinations) down to combos drawn
entirely from that group, plus a structural ceiling check (hypothetically
poisoning ALL SIX group members together) to confirm no reselection of any
size could do better than the best triple/pair found.

Result (see results/agents/PHASE3_SUMMARY.md, "Compositionally-matched
attacks are not constructible in this partition" for the write-up): the
group holds only 211/3,174 (6.65%) of the federation's Bot rows -- an
absolute ceiling independent of which/how-many silos from the group are
selected. Best f=3 triple (2,4,9): 5.42% min-coverage vs {0,3,5}'s 38.60%
(7.1x weaker). Best f=2 pair (2,4): 4.35% vs {0,3}'s 16.73% (3.85x weaker).
"""
from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
COMPOSITION_PATH = PROJECT_ROOT / "results/inspection/silo_family_composition_a0.5_s42.csv"
OUT_PATH = PROJECT_ROOT / "results/inspection/phase3_compositional_match_search.json"

HIGH_BENIGN_GROUP = {1, 2, 4, 6, 7, 9}
FAMILIES = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]

LOCKED = {
    "f3": {"combo": (0, 3, 5), "frontier_csv": "frontier_f3_a0.5_s42.csv"},
    "f2": {"combo": (0, 3), "frontier_csv": "frontier_f2_a0.5_s42.csv"},
}


def load_frontier(csv_path: Path) -> list[tuple[tuple, dict]]:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((ast.literal_eval(row["combo"]), row))
    return rows


def best_group_restricted(rows: list[tuple[tuple, dict]], group: set[int]) -> list[tuple[tuple, dict]]:
    candidates = [(combo, row) for combo, row in rows if set(combo).issubset(group)]
    candidates.sort(key=lambda x: float(x[1]["min_coverage"]), reverse=True)
    return candidates


def structural_ceiling(group: set[int]) -> dict:
    per_silo = {}
    with open(COMPOSITION_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            per_silo[int(row["silo"])] = {fam: int(row[fam]) for fam in FAMILIES}

    totals = {fam: sum(per_silo[s][fam] for s in per_silo) for fam in FAMILIES}
    group_totals = {fam: sum(per_silo[s][fam] for s in group) for fam in FAMILIES}
    ceiling = {fam: group_totals[fam] / totals[fam] for fam in FAMILIES}
    weakest = min(FAMILIES, key=lambda f: ceiling[f])
    return {
        "group_row_counts": group_totals,
        "federation_row_totals": totals,
        "coverage_ceiling_all_group_poisoned": ceiling,
        "weakest_link_family": weakest,
        "weakest_link_ceiling": ceiling[weakest],
    }


def main() -> None:
    result: dict = {"high_benign_group": sorted(HIGH_BENIGN_GROUP), "by_f": {}}

    ceiling = structural_ceiling(HIGH_BENIGN_GROUP)
    result["structural_ceiling"] = ceiling
    print(f"Structural ceiling (all 6 group members poisoned, flip_fraction=1.0):")
    for fam in FAMILIES:
        print(f"  {fam}: group_rows={ceiling['group_row_counts'][fam]} "
              f"federation_total={ceiling['federation_row_totals'][fam]} "
              f"ceiling={ceiling['coverage_ceiling_all_group_poisoned'][fam]:.4f}")
    print(f"  weakest link: {ceiling['weakest_link_family']} = "
          f"{ceiling['weakest_link_ceiling']:.4f} -- absolute ceiling, any subset, any size")

    for f_label, meta in LOCKED.items():
        rows = load_frontier(PROJECT_ROOT / "results/inspection" / meta["frontier_csv"])
        candidates = best_group_restricted(rows, HIGH_BENIGN_GROUP)
        best_combo, best_row = candidates[0]
        locked_row = [r for c, r in rows if c == meta["combo"]][0]

        n = len(meta["combo"])
        expect_n = 20 if n == 3 else 15
        print(f"\n=== {f_label} ===")
        print(f"  candidates within group: {len(candidates)} (expect C(6,{n})={expect_n})")
        print(f"  best group-restricted combo {best_combo}: "
              f"min_coverage={float(best_row['min_coverage']):.4f}")
        print(f"  locked {meta['combo']}: min_coverage={float(locked_row['min_coverage']):.4f}")
        ratio = float(locked_row["min_coverage"]) / float(best_row["min_coverage"])
        print(f"  ratio: locked is {ratio:.2f}x stronger")

        result["by_f"][f_label] = {
            "locked_combo": meta["combo"],
            "locked_min_coverage": float(locked_row["min_coverage"]),
            "best_group_restricted_combo": best_combo,
            "best_group_restricted_min_coverage": float(best_row["min_coverage"]),
            "best_group_restricted_full_coverage_vector": {
                fam: float(best_row[f"cov_{fam}"]) for fam in FAMILIES
            },
            "ratio_locked_stronger": ratio,
            "n_candidates_in_group": len(candidates),
        }

    OUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
