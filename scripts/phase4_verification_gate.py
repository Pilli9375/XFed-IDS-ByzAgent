"""ByzAgent Phase 4, Step 3 -- 6-cell verification-matrix retrospective
replay: 3 conditions (clean, sudden {0,3,5}, gradual {0,3,5}) x 2 agent modes
(current_round -- Phase 3 baseline reproduction, rolling_history window=5),
all read from client_stats.jsonl already on disk -- NO retraining. Same
retrospective-replay pattern as scripts/phase3_verification_gate.py, extended
to 2 modes and a 3rd (gradual) condition.

Writes decisions to
results/federated/{tag}/agent_decisions_phase4_{mode}.jsonl -- NEVER to
agent_decisions.jsonl. That plain filename, for the clean and sudden {0,3,5}
conditions, is Phase 3's own already-analyzed artifact (every number in
PHASE3_SUMMARY.md was computed from it) and must not be overwritten here.
current_round mode is expected to closely reproduce Phase 3's numbers (same
prompt, same model, same stats) but is NOT guaranteed byte-identical --
temperature=0.2 is not zero, so a fresh call is a new sample, not a verified
copy of the old one. Writing to a distinct filename keeps both on disk for
an honest side-by-side check rather than silently replacing one with the
other.

Decision-variance check: round 10 (same round Phase 3 used, for
comparability), 3x independent calls, per condition per mode = 18 additional
calls beyond the 3*2*20=120 base replay calls (138 total).

Usage:
  python scripts/phase4_verification_gate.py                  # full run
  python scripts/phase4_verification_gate.py --rounds-limit 2  # dry run
  python scripts/phase4_verification_gate.py --conditions clean  # subset
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agents.byz_agent import (  # noqa: E402
    AgentConfig,
    build_client_history,
    decide_round,
    decide_round_history,
    log_decisions,
)

CONDITIONS = {
    "clean": {
        "tag": "fedavg_a0.5_s42",
        "malicious_silos": [],
    },
    "sudden_{0,3,5}": {
        "tag": "fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5",
        "malicious_silos": [0, 3, 5],
    },
    "gradual_{0,3,5}": {
        "tag": "fedavg_a0.5_s42_poisoned_f3_gradual_silos0-3-5",
        "malicious_silos": [0, 3, 5],
    },
}

MODES = ("current_round", "rolling_history")
HISTORY_WINDOW = 5
VARIANCE_CHECK_ROUND = 10  # same round Phase 3 used -- comparability, not chosen post hoc
VARIANCE_CHECK_REPEATS = 3

OUT_RAW = PROJECT_ROOT / "results/inspection/phase4_gate_raw_a0.5_s42.json"


def load_rounds(stats_path: Path) -> dict[int, list[dict]]:
    rows_by_round: dict[int, list[dict]] = {}
    with open(stats_path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rows_by_round.setdefault(row["round"], []).append(row)
    return rows_by_round


def rows_up_to(rows_by_round: dict[int, list[dict]], round_num: int) -> list[dict]:
    """All rows with round <= round_num, across every round already loaded --
    the retrospective-replay counterpart of LoggingByzAgent's live
    self._history_rows accumulation (federated/xfed_federated/server_app.py).
    Rebuilt fresh from the already-loaded dict each call rather than
    incrementally maintained, so the variance check (which re-visits
    VARIANCE_CHECK_ROUND after the main per-round loop has already moved past
    it) cannot accidentally see a stale or over-extended window.
    """
    out: list[dict] = []
    for r in sorted(rows_by_round.keys()):
        if r > round_num:
            break
        out.extend(rows_by_round[r])
    return out


def to_client_stats(rows: list[dict]) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["silo_id"])
    return [
        {
            "client_id": f"silo_{r['silo_id']}",
            "update_norm": r["update_norm"],
            "cosine_to_global": r["cosine_to_global"],
            "cosine_to_peer_mean": r["cosine_to_peer_mean"],
            "train_loss": r["train_loss"],
            "val_accuracy": r["val_accuracy"],
        }
        for r in rows
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds-limit", type=int, default=None, help="Only replay the first N rounds (dry run).")
    ap.add_argument("--conditions", nargs="*", default=None, help="Subset of CONDITIONS keys to run (dry run).")
    ap.add_argument("--out", type=Path, default=OUT_RAW)
    args = ap.parse_args()

    conditions = {k: v for k, v in CONDITIONS.items() if args.conditions is None or k in args.conditions}

    cfg_current = AgentConfig()
    cfg_history = AgentConfig(history_mode="rolling_history", history_window=HISTORY_WINDOW)

    all_results: dict[str, dict[str, dict]] = {}
    variance_results: dict[str, dict[str, list]] = {}

    t_start = time.time()

    for cond_name, cond in conditions.items():
        out_dir = PROJECT_ROOT / "results/federated" / cond["tag"]
        stats_path = out_dir / "client_stats.jsonl"
        rows_by_round = load_rounds(stats_path)
        rounds_sorted = sorted(rows_by_round.keys())
        if args.rounds_limit:
            rounds_sorted = rounds_sorted[: args.rounds_limit]

        all_results[cond_name] = {}
        variance_results[cond_name] = {}

        for mode in MODES:
            print(f"\n===== CONDITION={cond_name} MODE={mode} (tag={cond['tag']}) =====", flush=True)
            cfg = cfg_current if mode == "current_round" else cfg_history
            agent_log_path = out_dir / f"agent_decisions_phase4_{mode}.jsonl"
            if agent_log_path.exists():
                agent_log_path.unlink()  # fresh retrospective replay, not an append

            cond_mode_results: dict[str, dict] = {}

            for round_num in rounds_sorted:
                t0 = time.time()
                if mode == "current_round":
                    client_stats = to_client_stats(rows_by_round[round_num])
                    decisions, _prompt, _raw = decide_round(round_num, client_stats, cfg=cfg)
                    raw_stats_by_client = {c["client_id"]: c for c in client_stats}
                else:
                    client_history = build_client_history(
                        rows_up_to(rows_by_round, round_num), current_round=round_num, window=HISTORY_WINDOW,
                    )
                    decisions, _prompt, _raw = decide_round_history(round_num, client_history, cfg=cfg)
                    raw_stats_by_client = {c["client_id"]: c for c in client_history}
                elapsed = time.time() - t0

                log_decisions(agent_log_path, round_num, decisions, raw_stats_by_client)

                cond_mode_results[str(round_num)] = {
                    "decisions": decisions,
                    "raw_stats_by_client": raw_stats_by_client,
                    "elapsed_sec": round(elapsed, 2),
                }
                summary = ", ".join(f"{d['client_id']}={d['decision'][0]}" for d in decisions)
                print(f"  round {round_num:2d} ({elapsed:5.1f}s): {summary}", flush=True)

            all_results[cond_name][mode] = cond_mode_results

            # --- decision-variance check: same round, 3 independent calls ---
            if VARIANCE_CHECK_ROUND in rows_by_round and (
                not args.rounds_limit or VARIANCE_CHECK_ROUND <= rounds_sorted[-1]
            ):
                print(
                    f"  -- variance check, round {VARIANCE_CHECK_ROUND}, "
                    f"{VARIANCE_CHECK_REPEATS}x independent calls --", flush=True,
                )
                repeats = []
                for i in range(VARIANCE_CHECK_REPEATS):
                    if mode == "current_round":
                        var_client_stats = to_client_stats(rows_by_round[VARIANCE_CHECK_ROUND])
                        decisions, _p, _r = decide_round(VARIANCE_CHECK_ROUND, var_client_stats, cfg=cfg)
                    else:
                        var_client_history = build_client_history(
                            rows_up_to(rows_by_round, VARIANCE_CHECK_ROUND),
                            current_round=VARIANCE_CHECK_ROUND, window=HISTORY_WINDOW,
                        )
                        decisions, _p, _r = decide_round_history(VARIANCE_CHECK_ROUND, var_client_history, cfg=cfg)
                    repeats.append(decisions)
                    print(
                        f"    repeat {i + 1}: "
                        + ", ".join(f"{d['client_id']}={d['decision'][0]}" for d in decisions), flush=True,
                    )
                variance_results[cond_name][mode] = repeats

    total_elapsed = time.time() - t_start
    print(f"\nTotal elapsed: {total_elapsed / 60:.1f} min")

    output = {
        "conditions": conditions,
        "modes": list(MODES),
        "history_window": HISTORY_WINDOW,
        "results": all_results,
        "variance_check": {
            "round": VARIANCE_CHECK_ROUND,
            "repeats": VARIANCE_CHECK_REPEATS,
            "by_condition_mode": variance_results,
        },
        "agent_config": {
            "model": cfg_current.model,
            "temperature": cfg_current.temperature,
            "downweight_multiplier": cfg_current.downweight_multiplier,
            "history_window": HISTORY_WINDOW,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2))
    print(f"Wrote raw results to {args.out}")


if __name__ == "__main__":
    main()
