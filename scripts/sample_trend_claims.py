"""ByzAgent multi-seed validation, Step 4b support -- reproduce Phase 4's
trend_rows (scoreable, rolling_history only) from
phase4_diagnostic_reasoning_audit.py exactly, then draw a random sample for
a genuine hand-check of the trend-error heuristic (owed from Phase 4, which
explicitly flagged its 45.00% figure as unvalidated).

Includes the FULL explanation text and full sequence per sampled row so each
one can be judged independently by a human, not just trusted from the
heuristic's own verdict. No new LLM calls -- reads
results/inspection/phase4_gate_raw_a0.5_s42.json, already on disk.

Usage:
    python scripts/sample_trend_claims.py [--n 35] [--seed 7] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/phase4_gate_raw_a0.5_s42.json"

STAT_KEYWORD_PATTERNS = {
    "update_norm": re.compile(r"update[\s_]norm", re.IGNORECASE),
    "cosine_to_global": re.compile(r"cosine[\s_](to[\s_])?(similarity[\s_](to[\s_])?)?global", re.IGNORECASE),
    "cosine_to_peer_mean": re.compile(r"(cosine.*peer|peer[\s_]mean)", re.IGNORECASE),
    "train_loss": re.compile(r"train(ing)?[\s_]loss", re.IGNORECASE),
    "val_accuracy": re.compile(r"val(idation)?[\s_]accuracy", re.IGNORECASE),
}
TREND_WORDS = {
    "increasing": re.compile(
        r"\b(increasing|increased|rising|risen|climbing|climbed|growing|grown|"
        r"trending\s+up|going\s+up|upward)\b", re.IGNORECASE),
    "decreasing": re.compile(
        r"\b(decreasing|decreased|falling|fallen|declining|declined|dropping|dropped|"
        r"shrinking|shrunk|trending\s+down|going\s+down|downward)\b", re.IGNORECASE),
    "stable": re.compile(
        r"\b(stable|steady|consistent|unchanged|flat|holding\s+steady|remain(ed|ing)?\s+(the\s+)?"
        r"(same|constant|stable))\b", re.IGNORECASE),
}
TREND_WINDOW_CHARS = 90


def classify_actual_trend(seq):
    if len(seq) < 2 or seq[0] is None or seq[-1] is None:
        return None
    first, last = seq[0], seq[-1]
    diff = last - first
    tol = 0.05 * ((abs(first) + abs(last)) / 2) + 1e-6
    if abs(diff) <= tol:
        return "stable"
    return "increasing" if diff > 0 else "decreasing"


def extract_trend_claims(explanation):
    stat_matches = []
    for stat, pattern in STAT_KEYWORD_PATTERNS.items():
        for m in pattern.finditer(explanation):
            stat_matches.append((stat, m.start(), m.end()))
    trend_matches = []
    for direction, pattern in TREND_WORDS.items():
        for m in pattern.finditer(explanation):
            trend_matches.append((direction, m.start(), m.end()))
    claims = []
    for stat, s_start, s_end in stat_matches:
        window_start, window_end = s_start - TREND_WINDOW_CHARS, s_end + TREND_WINDOW_CHARS
        nearby = [
            (direction, abs((t_start + t_end) / 2 - (s_start + s_end) / 2))
            for direction, t_start, t_end in trend_matches
            if t_start >= window_start and t_end <= window_end
        ]
        if not nearby:
            continue
        directions_found = {d for d, _dist in nearby}
        if len(directions_found) > 1:
            continue
        nearby.sort(key=lambda x: x[1])
        claims.append({"stat": stat, "cited_direction": nearby[0][0]})
    return claims


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=35)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "results/inspection/multiseed_trend_claim_sample.json")
    args = ap.parse_args()

    raw = json.loads(RAW_PATH.read_text())
    conditions = raw["conditions"]
    results = raw["results"]

    trend_rows = []
    for cond_name in conditions:
        cond_mode_results = results[cond_name]["rolling_history"]
        for round_str, rd in cond_mode_results.items():
            round_num = int(round_str)
            raw_by_client = rd["raw_stats_by_client"]
            for d in rd["decisions"]:
                cid = d["client_id"]
                expl = d["explanation"]
                for claim in extract_trend_claims(expl):
                    stat = claim["stat"]
                    seq = raw_by_client[cid][stat]
                    window_size = raw_by_client[cid]["window_size"]
                    if window_size < 2:
                        continue  # insufficient_history, not scoreable
                    actual = classify_actual_trend(seq)
                    trend_rows.append({
                        "condition": cond_name, "round": round_num, "client_id": cid, "stat": stat,
                        "cited_direction": claim["cited_direction"], "actual_direction": actual,
                        "window_size": window_size, "sequence": seq,
                        "heuristic_correct": (actual is not None and actual == claim["cited_direction"]),
                        "full_explanation": expl,
                    })

    print(f"Total scoreable trend claims: {len(trend_rows)}")
    n_heuristic_correct = sum(1 for r in trend_rows if r["heuristic_correct"])
    print(f"Heuristic says correct: {n_heuristic_correct}, wrong: {len(trend_rows) - n_heuristic_correct}, "
          f"error_rate={1 - n_heuristic_correct / len(trend_rows):.4f}")

    random.seed(args.seed)
    sample = random.sample(trend_rows, args.n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sample, indent=2))
    print(f"Wrote sample of {len(sample)} to {args.out}")


if __name__ == "__main__":
    main()
