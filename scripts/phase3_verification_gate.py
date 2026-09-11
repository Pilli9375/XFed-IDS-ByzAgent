"""ByzAgent Phase 3, Step 3b -- full 20-round retrospective replay, all 3
conditions (clean, f=3 {0,3,5}, f=2 {0,3}), against client_stats.jsonl
already on disk from Phase 0/1. No retraining -- same pattern Phase 1's
scripts/replay_client_stats.py / scripts/phase1_verification_gate.py used.

Also runs the decision-variance check (same round's stats sent 3x
independently, per condition) here, since it needs the same live Ollama
calls as the main replay and there is no reason to spin up a second pass.

Writes:
  - results/federated/{tag}/agent_decisions.jsonl  (one row per round per
    silo, overwritten fresh by this script -- retrospective replay, not an
    append-mode live log)
  - results/inspection/phase3_gate_raw_a0.5_s42.json  (everything needed
    for scripts/phase3_analysis.py's numbers, so the expensive LLM calls
    never need to be re-run to change how the numbers are computed)

Run with the xfed conda env's python (needs the project's src/ on path,
nothing else special -- byz_agent.py itself only needs the stdlib).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agents.byz_agent import AgentConfig, decide_round, log_decisions  # noqa: E402

CONDITIONS = {
    "clean": {
        "tag": "fedavg_a0.5_s42",
        "malicious_silos": [],
    },
    "f3_{0,3,5}": {
        "tag": "fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5",
        "malicious_silos": [0, 3, 5],
    },
    "f2_{0,3}": {
        "tag": "fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3",
        "malicious_silos": [0, 3],
    },
}

VARIANCE_CHECK_ROUND = 10  # same round used in Step 3a's manual check
VARIANCE_CHECK_REPEATS = 3

OUT_RAW = PROJECT_ROOT / "results/inspection/phase3_gate_raw_a0.5_s42.json"


def load_rounds(stats_path: Path) -> dict[int, list[dict]]:
    rows_by_round: dict[int, list[dict]] = {}
    with open(stats_path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rows_by_round.setdefault(row["round"], []).append(row)
    return rows_by_round


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
    cfg = AgentConfig()
    all_results: dict[str, dict] = {}
    variance_results: dict[str, list[dict]] = {}

    t_start = time.time()

    for cond_name, cond in CONDITIONS.items():
        print(f"\n===== CONDITION: {cond_name} (tag={cond['tag']}) =====", flush=True)
        out_dir = PROJECT_ROOT / "results/federated" / cond["tag"]
        stats_path = out_dir / "client_stats.jsonl"
        rows_by_round = load_rounds(stats_path)
        agent_log_path = out_dir / "agent_decisions.jsonl"
        if agent_log_path.exists():
            agent_log_path.unlink()  # fresh retrospective replay, not an append

        cond_results: dict[str, dict] = {}
        for round_num in sorted(rows_by_round.keys()):
            rows = rows_by_round[round_num]
            client_stats = to_client_stats(rows)
            t0 = time.time()
            decisions, prompt, raw = decide_round(round_num, client_stats, cfg=cfg)
            elapsed = time.time() - t0

            raw_stats_by_client = {c["client_id"]: c for c in client_stats}
            log_decisions(agent_log_path, round_num, decisions, raw_stats_by_client)

            cond_results[str(round_num)] = {
                "decisions": decisions,
                "client_stats": client_stats,
                "elapsed_sec": round(elapsed, 2),
            }
            summary = ", ".join(f"{d['client_id']}={d['decision'][0]}" for d in decisions)
            print(f"  round {round_num:2d} ({elapsed:5.1f}s): {summary}", flush=True)

        all_results[cond_name] = cond_results

        # --- decision-variance check: same round, 3 independent calls ---
        print(f"  -- variance check, round {VARIANCE_CHECK_ROUND}, "
              f"{VARIANCE_CHECK_REPEATS}x independent calls --", flush=True)
        var_rows = rows_by_round[VARIANCE_CHECK_ROUND]
        var_client_stats = to_client_stats(var_rows)
        repeats = []
        for i in range(VARIANCE_CHECK_REPEATS):
            decisions, _prompt, _raw = decide_round(VARIANCE_CHECK_ROUND, var_client_stats, cfg=cfg)
            repeats.append(decisions)
            print(f"    repeat {i + 1}: " +
                  ", ".join(f"{d['client_id']}={d['decision'][0]}" for d in decisions), flush=True)
        variance_results[cond_name] = repeats

    total_elapsed = time.time() - t_start
    print(f"\nTotal elapsed: {total_elapsed / 60:.1f} min")

    output = {
        "conditions": {name: cond for name, cond in CONDITIONS.items()},
        "results": all_results,
        "variance_check": {
            "round": VARIANCE_CHECK_ROUND,
            "repeats": VARIANCE_CHECK_REPEATS,
            "by_condition": variance_results,
        },
        "agent_config": {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "downweight_multiplier": cfg.downweight_multiplier,
        },
    }
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW.write_text(json.dumps(output, indent=2))
    print(f"Wrote raw results to {OUT_RAW}")


if __name__ == "__main__":
    main()
