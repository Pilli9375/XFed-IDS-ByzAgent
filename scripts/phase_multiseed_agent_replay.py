"""ByzAgent multi-seed validation, Step 3 -- current-round-mode agent replay
at seeds 1337 and 2024, clean and sudden {0,3,5} f=3 conditions. Mirrors
scripts/phase3_verification_gate.py exactly (same decide_round/log_decisions
calls, same client_stats.jsonl -> client_stats dict shape), parameterized
over (seed, tag) instead of hardcoded to seed 42's three conditions.

Rolling-history mode is explicitly OUT OF SCOPE for this session (Phase 4
already settled it at seed 42 via the canary conjunction) -- this script
only ever calls decide_round() (current-round path), never
decide_round_history().

No decision-variance check here -- not requested by this session's ground
truth (unlike Phase 3's own gate script, which ran one for its own purposes).

Writes:
  - results/federated/{tag}/agent_decisions.jsonl  (overwritten fresh)
  - results/inspection/multiseed_agent_gate_raw.json
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
    "s1337_clean": {"tag": "fedavg_a0.5_s1337", "seed": 1337, "malicious_silos": []},
    "s1337_sudden": {"tag": "fedavg_a0.5_s1337_poisoned_f3_sudden_silos0-3-5", "seed": 1337, "malicious_silos": [0, 3, 5]},
    "s2024_clean": {"tag": "fedavg_a0.5_s2024", "seed": 2024, "malicious_silos": []},
    "s2024_sudden": {"tag": "fedavg_a0.5_s2024_poisoned_f3_sudden_silos0-3-5", "seed": 2024, "malicious_silos": [0, 3, 5]},
}

OUT_RAW = PROJECT_ROOT / "results/inspection/multiseed_agent_gate_raw.json"


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
    assert cfg.history_mode == "current_round", cfg.history_mode
    all_results: dict[str, dict] = {}

    t_start = time.time()

    for cond_name, cond in CONDITIONS.items():
        print(f"\n===== CONDITION: {cond_name} (tag={cond['tag']}) =====", flush=True)
        out_dir = PROJECT_ROOT / "results/federated" / cond["tag"]
        stats_path = out_dir / "client_stats.jsonl"
        rows_by_round = load_rounds(stats_path)
        agent_log_path = out_dir / "agent_decisions_multiseed.jsonl"
        if agent_log_path.exists():
            agent_log_path.unlink()

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

    total_elapsed = time.time() - t_start
    print(f"\nTotal elapsed: {total_elapsed / 60:.1f} min")

    output = {
        "conditions": {name: cond for name, cond in CONDITIONS.items()},
        "results": all_results,
        "agent_config": {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "downweight_multiplier": cfg.downweight_multiplier,
            "history_mode": cfg.history_mode,
        },
    }
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW.write_text(json.dumps(output, indent=2))
    print(f"Wrote raw results to {OUT_RAW}")


if __name__ == "__main__":
    main()
