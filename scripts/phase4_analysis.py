"""ByzAgent Phase 4, Step 3 -- analysis over scripts/phase4_verification_gate.py's
raw replay output (results/inspection/phase4_gate_raw_a0.5_s42.json).

Computes, per the locked Step 3 reporting spec:
  1. Per-silo flag rate, per condition, per mode -- NOT aggregated
     malicious-vs-clean (this is the format that caught Phase 3's
     compositional-extremity confound; reused deliberately, same reasoning).
  2. Lift-over-clean-baseline: each malicious silo's flag rate under attack
     MINUS that same silo's flag rate in the clean run, same mode -- the
     only defensible detection measure, never a raw flag rate alone.
  3. Silo 8 (never malicious, compositionally extreme, flagged 0.95-1.00 in
     Phase 3) as the standing false-positive canary, every cell.
  4. Rounds-to-detection under gradual mode: first round each malicious silo
     is flagged, rolling-history vs current-round-only, evaluated against
     the PRE-REGISTERED rounds-1-8 window (locked before this script ran --
     see the Step 1 gate exchange). Also: per-round flag/trust sequences for
     silos {0,3,5,8} so a single early flip isn't misread as sustained
     detection, and an early-rounds-informativeness proxy (per-round false-
     positive rate among ORDINARY clean silos {1,2,4,6,7,9}, excluding silo
     8, under the clean condition) to locate when each mode's signal stops
     looking like noise -- tracked per explicit instruction, does not
     override the locked rounds-1-8 window.
  5. Decision-variance stability (3x same-input repeats, round 10, same
     round Phase 3 used), per condition per mode.

No new LLM calls -- pure analysis of already-collected data.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/phase4_gate_raw_a0.5_s42.json"
OUT_PATH = PROJECT_ROOT / "results/inspection/phase4_gate_analysis_a0.5_s42.json"

MODES = ("current_round", "rolling_history")
CONDITION_ORDER = ("clean", "sudden_{0,3,5}", "gradual_{0,3,5}")
DETECTION_WINDOW = 8  # pre-registered strength-matched window, locked before this ran
ORDINARY_CLEAN_SILOS = [1, 2, 4, 6, 7, 9]  # never malicious anywhere, not silo 8
CANARY_SILO = 8


def flagged(decision: str) -> bool:
    return decision in ("downweight", "quarantine")


def main() -> None:
    raw = json.loads(RAW_PATH.read_text())
    conditions = raw["conditions"]
    results = raw["results"]  # [cond][mode][round_str] -> {"decisions": [...], ...}

    report: dict = {}

    # ------------------------------------------------------------------
    # 1. per-silo flag rate, per condition, per mode (20 rounds each)
    # ------------------------------------------------------------------
    # flag_rate[silo][cond][mode] = rate
    flag_rate: dict[int, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    per_round_decision: dict[str, dict[str, dict[int, dict[int, str]]]] = defaultdict(lambda: defaultdict(dict))
    # per_round_decision[cond][mode][silo][round] = decision string

    for cond_name in conditions:
        for mode in MODES:
            cond_mode_results = results[cond_name][mode]
            counts = {i: 0 for i in range(10)}
            totals = {i: 0 for i in range(10)}
            for round_str, rd in cond_mode_results.items():
                round_num = int(round_str)
                for d in rd["decisions"]:
                    silo_num = int(d["client_id"].split("_")[1])
                    totals[silo_num] += 1
                    if flagged(d["decision"]):
                        counts[silo_num] += 1
                    per_round_decision[cond_name][mode].setdefault(silo_num, {})[round_num] = d["decision"]
            for i in range(10):
                flag_rate[i][cond_name][mode] = counts[i] / totals[i] if totals[i] else None

    per_silo_table = []
    for i in range(10):
        row = {"silo": i}
        for cond_name in conditions:
            for mode in MODES:
                row[f"{cond_name}__{mode}"] = flag_rate[i][cond_name][mode]
        per_silo_table.append(row)
    report["per_silo_flag_rate_table"] = per_silo_table

    # ------------------------------------------------------------------
    # 2. lift-over-clean-baseline, malicious silos only, per attack condition per mode
    # ------------------------------------------------------------------
    lift_table = []
    for cond_name, cond_meta in conditions.items():
        if cond_name == "clean":
            continue
        for silo in sorted(cond_meta["malicious_silos"]):
            row = {"silo": silo, "condition": cond_name}
            for mode in MODES:
                atk_rate = flag_rate[silo][cond_name][mode]
                clean_rate = flag_rate[silo]["clean"][mode]
                row[f"{mode}__clean_rate"] = clean_rate
                row[f"{mode}__attack_rate"] = atk_rate
                row[f"{mode}__lift"] = (
                    round(atk_rate - clean_rate, 4) if atk_rate is not None and clean_rate is not None else None
                )
            lift_table.append(row)
    report["lift_over_clean_baseline"] = lift_table

    # ------------------------------------------------------------------
    # 3. silo 8 canary, every cell
    # ------------------------------------------------------------------
    canary = {}
    for cond_name in conditions:
        for mode in MODES:
            canary[f"{cond_name}__{mode}"] = flag_rate[CANARY_SILO][cond_name][mode]
    report["silo_8_canary_flag_rate"] = canary

    # ------------------------------------------------------------------
    # 4. rounds-to-detection, gradual mode, both agent modes
    # ------------------------------------------------------------------
    gradual_cond = "gradual_{0,3,5}"
    malicious = sorted(conditions[gradual_cond]["malicious_silos"])
    rounds_to_detection = {}
    for mode in MODES:
        per_silo_first = {}
        for silo in malicious:
            seq = per_round_decision[gradual_cond][mode][silo]
            first_round = None
            for r in sorted(seq.keys()):
                if flagged(seq[r]):
                    first_round = r
                    break
            per_silo_first[silo] = {
                "first_flagged_round_full_20": first_round,
                "within_locked_1_to_8_window": (first_round is not None and first_round <= DETECTION_WINDOW),
            }
        rounds_to_detection[mode] = per_silo_first
    report["rounds_to_detection_gradual"] = {
        "locked_window_note": (
            f"Pre-registered BEFORE this replay ran: rounds 1-{DETECTION_WINDOW} are the ONLY "
            f"strength-matched regime (gradual reaches sudden mode's constant 0.40 flip_fraction "
            f"exactly at round 8). Detection at or before round {DETECTION_WINDOW} is the meaningful "
            f"result; detection after round {DETECTION_WINDOW} demonstrates nothing new (sudden mode "
            f"at 0.40 was already trivially detected by train_loss in Phase 1/3). Full 20-round "
            f"first-flag data is reported below regardless, per instruction."
        ),
        "by_mode": rounds_to_detection,
    }

    # full per-round flag sequence for silos {malicious..., CANARY_SILO}, gradual, both modes --
    # context so a single early flip is not misread as sustained detection
    watch_silos = sorted(set(malicious) | {CANARY_SILO})
    sequences = {}
    for mode in MODES:
        seq_by_silo = {}
        for silo in watch_silos:
            seq = per_round_decision[gradual_cond][mode][silo]
            seq_by_silo[silo] = [seq[r][0] for r in sorted(seq.keys())]  # 't'/'d'/'q' per round 1..20
        sequences[mode] = seq_by_silo
    report["gradual_per_round_flag_sequence"] = {
        "silos": watch_silos,
        "round_order": "index 0 = round 1, index 19 = round 20; value is 't'=trust 'd'=downweight 'q'=quarantine",
        "by_mode": sequences,
    }

    # ------------------------------------------------------------------
    # 4b. early-rounds informativeness proxy: per-round FP rate among
    # ORDINARY clean silos (excl. silo 8), clean condition, both modes.
    # Tracks whether/when each mode's signal stops looking like noise.
    # Does NOT change the locked rounds-1-8 window -- reported alongside it.
    # ------------------------------------------------------------------
    informativeness = {}
    for mode in MODES:
        per_round_fp = {}
        for r in range(1, 21):
            flags = [flagged(per_round_decision["clean"][mode][s][r]) for s in ORDINARY_CLEAN_SILOS]
            per_round_fp[r] = round(sum(flags) / len(flags), 3)
        informativeness[mode] = per_round_fp
    report["early_rounds_informativeness_proxy"] = {
        "method_note": (
            "Per-round false-positive rate (downweight|quarantine) among the 6 silos "
            "{1,2,4,6,7,9} -- ordinary clean, never malicious anywhere, and NOT the "
            "compositionally-extreme silo 8 -- under the CLEAN (no-attack) condition. "
            "A high/noisy rate here means the agent is flagging ordinary clean silos "
            "at that round, i.e. it does not yet have enough signal to discriminate -- "
            "used to locate when each mode's window actually starts being informative, "
            "not to redefine the locked rounds-1-8 detection window."
        ),
        "by_mode": informativeness,
    }

    # ------------------------------------------------------------------
    # 5. decision-variance stability, round 10, 3 repeats, per condition per mode
    # ------------------------------------------------------------------
    variance = raw["variance_check"]
    variance_report = {"round": variance["round"], "repeats": variance["repeats"], "by_condition_mode": {}}
    for cond_name, by_mode in variance["by_condition_mode"].items():
        for mode, repeats in by_mode.items():
            by_silo = defaultdict(list)
            for rep in repeats:
                for d in rep:
                    by_silo[d["client_id"]].append(d["decision"])
            silo_stability = {}
            for cid, decs in by_silo.items():
                stable = len(set(decs)) == 1
                flagged_binary = [flagged(d) for d in decs]
                boundary_stable = len(set(flagged_binary)) == 1  # never crosses trust<->flagged
                silo_stability[cid] = {
                    "decisions": decs,
                    "exact_stable": stable,
                    "trust_vs_flagged_boundary_stable": boundary_stable,
                }
            n_stable = sum(1 for v in silo_stability.values() if v["exact_stable"])
            n_boundary_stable = sum(1 for v in silo_stability.values() if v["trust_vs_flagged_boundary_stable"])
            n_silos = len(silo_stability)
            variance_report["by_condition_mode"][f"{cond_name}__{mode}"] = {
                "per_silo": silo_stability,
                "n_silos": n_silos,
                "n_exact_stable": n_stable,
                "exact_stability_rate": n_stable / n_silos if n_silos else None,
                "n_boundary_stable": n_boundary_stable,
                "boundary_stability_rate": n_boundary_stable / n_silos if n_silos else None,
            }
    report["decision_variance"] = variance_report

    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Wrote analysis to {OUT_PATH}")

    # ------------------------------------------------------------------
    # console summary
    # ------------------------------------------------------------------
    print("\n=== PER-SILO FLAG RATE TABLE ===")
    header = "silo  " + "  ".join(f"{c}__{m}" for c in CONDITION_ORDER for m in MODES)
    print(header)
    for row in per_silo_table:
        vals = "  ".join(f"{row[f'{c}__{m}']:.2f}" for c in CONDITION_ORDER for m in MODES)
        marker = " <-- CANARY" if row["silo"] == CANARY_SILO else ""
        print(f"{row['silo']:>4}  {vals}{marker}")

    print("\n=== LIFT OVER CLEAN BASELINE (malicious silos only) ===")
    for row in lift_table:
        print(f"  silo {row['silo']} [{row['condition']}]: "
              f"current_round lift={row['current_round__lift']:+.4f} "
              f"(attack={row['current_round__attack_rate']:.2f} clean={row['current_round__clean_rate']:.2f}) | "
              f"rolling_history lift={row['rolling_history__lift']:+.4f} "
              f"(attack={row['rolling_history__attack_rate']:.2f} clean={row['rolling_history__clean_rate']:.2f})")

    print(f"\n=== SILO 8 CANARY (flag rate, every cell) ===")
    for k, v in canary.items():
        print(f"  {k}: {v:.2f}")

    print(f"\n=== ROUNDS-TO-DETECTION, gradual (locked window = rounds 1-{DETECTION_WINDOW}) ===")
    for mode in MODES:
        print(f"  [{mode}]")
        for silo, info in rounds_to_detection[mode].items():
            print(f"    silo {silo}: first_flagged_round={info['first_flagged_round_full_20']} "
                  f"within_1_to_8={info['within_locked_1_to_8_window']}")

    print("\n=== GRADUAL PER-ROUND FLAG SEQUENCE (t=trust d=downweight q=quarantine) ===")
    for mode in MODES:
        print(f"  [{mode}]")
        for silo in watch_silos:
            seq = "".join(sequences[mode][silo])
            tag = " (CANARY)" if silo == CANARY_SILO else " (malicious)"
            print(f"    silo {silo}{tag}: {seq}")

    print("\n=== EARLY-ROUNDS INFORMATIVENESS PROXY (ordinary-clean FP rate, clean condition) ===")
    for mode in MODES:
        vals = " ".join(f"{informativeness[mode][r]:.2f}" for r in range(1, 9))
        print(f"  [{mode}] rounds 1-8: {vals}")

    print("\n=== DECISION-VARIANCE STABILITY (round 10, 3x) ===")
    for k, v in variance_report["by_condition_mode"].items():
        print(f"  [{k}] exact={v['n_exact_stable']}/{v['n_silos']} ({v['exact_stability_rate']:.2f})  "
              f"boundary={v['n_boundary_stable']}/{v['n_silos']} ({v['boundary_stability_rate']:.2f})")


if __name__ == "__main__":
    main()
