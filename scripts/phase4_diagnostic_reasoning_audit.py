"""ByzAgent Phase 4 -- closing diagnostic (01_Planning, post-Step-3 verdict).

Purpose: the Step 3 verdict (rolling history does NOT separate temporal
attack onset from static compositional atypicality -- negative branch of
the pre-registered rule) is settled and does not change based on anything
here. What is NOT yet settled is WHY rolling-history mode also showed three
independent signs of getting worse, not just neutral: clean-condition
baselines rose under zero attack for several ordinary silos, the
ordinary-clean FP proxy never settled across 20 rounds where current-round
drops to ~0 by round 4, and decision-variance boundary stability regressed
100% -> 70-80%. Two different claims are entangled and must be told apart
before the write-up:
  (A) "rolling history as an approach fails to separate composition from
      attack" -- a finding about the METHOD.
  (B) "this agent's reasoning degrades over denser prompts" -- a finding
      about THIS MODEL under a longer, more complex prompt, which could in
      principle be fixed by a different model/prompt without rescuing (A).

This script reuses Phase 3's reasoning-vs-outcome audit machinery
(scripts/phase3_analysis.py: citation frequency, citation accuracy via
loose/strict within-round percentile matching, Spearman decision-severity
correlation) against Phase 4's already-collected rolling-history AND
current-round replay data (results/inspection/phase4_gate_raw_a0.5_s42.json),
so the two modes are compared on THE SAME data, THE SAME 3 conditions,
computed THE SAME way -- plus one new check (d) specific to sequences:
whether trend language (increasing/decreasing/stable) the agent uses in
rolling-history explanations is factually consistent with the actual
sequence it was given.

REPORT ONLY. No prompt tuning happens here or in response to this script's
output -- per explicit instruction, this determines how the Step 3 verdict
is WORDED in the write-up, not whether it holds.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/phase4_gate_raw_a0.5_s42.json"
OUT_PATH = PROJECT_ROOT / "results/inspection/phase4_diagnostic_reasoning_audit.json"

MODES = ("current_round", "rolling_history")
STATS = ["update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy"]
DECISION_SEVERITY = {"trust": 0, "downweight": 1, "quarantine": 2}

# ---- reused verbatim from scripts/phase3_analysis.py (same method, so the
# two audits are comparable, not two different instruments) ----
STAT_KEYWORD_PATTERNS = {
    "update_norm": re.compile(r"update[\s_]norm", re.IGNORECASE),
    "cosine_to_global": re.compile(r"cosine[\s_](to[\s_])?(similarity[\s_](to[\s_])?)?global", re.IGNORECASE),
    "cosine_to_peer_mean": re.compile(r"(cosine.*peer|peer[\s_]mean)", re.IGNORECASE),
    "train_loss": re.compile(r"train(ing)?[\s_]loss", re.IGNORECASE),
    "val_accuracy": re.compile(r"val(idation)?[\s_]accuracy", re.IGNORECASE),
}

CITATION_RE = re.compile(
    r"(very\s+high|very\s+low|extremely\s+high|extremely\s+low|unusually\s+high|unusually\s+low|"
    r"high|low|moderate)\s+([a-zA-Z][a-zA-Z_\s]{2,45}?)\s*[\(:]?\s*(-?\d+\.\d+|-?\d+)\)?",
    re.IGNORECASE,
)


def classify_stat_span(span: str) -> str | None:
    for stat, pattern in STAT_KEYWORD_PATTERNS.items():
        if pattern.search(span):
            return stat
    return None


def direction_of(adjective: str) -> str:
    adj = adjective.lower()
    if "low" in adj:
        return "low"
    if "high" in adj:
        return "high"
    return "moderate"


def percentile_rank(value: float, all_values: list[float]) -> float:
    n = len(all_values)
    if n <= 1:
        return 0.5
    less = sum(1 for v in all_values if v < value)
    equal = sum(1 for v in all_values if v == value)
    return (less + 0.5 * (equal - 1)) / (n - 1)


# ---- new for this diagnostic: trend-language extraction (check d) ----
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


def current_value(entry_val):
    """entry_val is either a scalar (current_round mode) or a list, oldest-
    to-newest (rolling_history mode). Returns the value for THIS round --
    the last element of the sequence in rolling_history mode, the scalar
    itself in current_round mode -- so citation accuracy/correlation are
    computed against the same quantity in both modes.
    """
    return entry_val[-1] if isinstance(entry_val, list) else entry_val


def classify_actual_trend(seq: list[float]) -> str | None:
    """seq: oldest-to-newest list. None if fewer than 2 points (no trend is
    definable). 'stable' if the relative endpoint change is small, else
    'increasing'/'decreasing' by sign of last-first. Deliberately simple
    (endpoint comparison, not a regression) -- documented as such; this is a
    supplementary diagnostic, not the headline citation-accuracy metric.
    """
    if len(seq) < 2 or seq[0] is None or seq[-1] is None:
        return None
    first, last = seq[0], seq[-1]
    diff = last - first
    tol = 0.05 * ((abs(first) + abs(last)) / 2) + 1e-6
    if abs(diff) <= tol:
        return "stable"
    return "increasing" if diff > 0 else "decreasing"


def extract_trend_claims(explanation: str) -> list[dict]:
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
            continue  # ambiguous (e.g. two different trend words near one stat) -- skip, don't guess
        nearby.sort(key=lambda x: x[1])
        claims.append({"stat": stat, "cited_direction": nearby[0][0]})
    return claims


def main() -> None:
    raw = json.loads(RAW_PATH.read_text())
    conditions = raw["conditions"]
    results = raw["results"]  # [cond][mode][round_str] -> {"decisions", "raw_stats_by_client", ...}

    report: dict = {"by_mode": {}}

    citation_rows_by_mode: dict[str, list[dict]] = {m: [] for m in MODES}
    correlation_rows_by_mode: dict[str, list[tuple]] = {m: [] for m in MODES}
    citation_freq_by_mode = {
        m: {s: 0 for s in STATS} for m in MODES
    }
    n_explanations_by_mode = {m: 0 for m in MODES}
    trend_rows = []  # rolling_history only

    for cond_name in conditions:
        for mode in MODES:
            cond_mode_results = results[cond_name][mode]
            for round_str, rd in cond_mode_results.items():
                round_num = int(round_str)
                raw_by_client = rd["raw_stats_by_client"]
                # current-round value per stat, all clients this round -- for percentile ranking
                round_values = {
                    s: [current_value(raw_by_client[cid][s]) for cid in raw_by_client] for s in STATS
                }

                for d in rd["decisions"]:
                    cid = d["client_id"]
                    expl = d["explanation"]
                    n_explanations_by_mode[mode] += 1

                    for stat, pattern in STAT_KEYWORD_PATTERNS.items():
                        if pattern.search(expl):
                            citation_freq_by_mode[mode][stat] += 1

                    for m in CITATION_RE.finditer(expl):
                        adj_raw, stat_span, value_str = m.groups()
                        stat = classify_stat_span(stat_span)
                        if stat is None:
                            continue
                        try:
                            value = float(value_str)
                        except ValueError:
                            continue
                        direction = direction_of(adj_raw)
                        pct = percentile_rank(value, round_values[stat])
                        if direction == "high":
                            correct = pct >= 0.5
                            strict_verdict = "correct" if pct >= 0.6 else ("wrong" if pct <= 0.4 else "ambiguous")
                        elif direction == "low":
                            correct = pct <= 0.5
                            strict_verdict = "correct" if pct <= 0.4 else ("wrong" if pct >= 0.6 else "ambiguous")
                        else:
                            correct = 0.25 <= pct <= 0.75
                            strict_verdict = "correct" if 0.25 <= pct <= 0.75 else "wrong"
                        citation_rows_by_mode[mode].append({
                            "condition": cond_name, "round": round_num, "client_id": cid, "stat": stat,
                            "cited_value": value, "actual_round_percentile": round(pct, 3),
                            "correct": correct, "strict_verdict": strict_verdict,
                        })

                    sev = DECISION_SEVERITY[d["decision"]]
                    for stat in STATS:
                        pct = percentile_rank(current_value(raw_by_client[cid][stat]), round_values[stat])
                        correlation_rows_by_mode[mode].append((stat, sev, pct))

                    if mode == "rolling_history":
                        for claim in extract_trend_claims(expl):
                            stat = claim["stat"]
                            seq = raw_by_client[cid][stat]
                            window_size = raw_by_client[cid]["window_size"]
                            actual = classify_actual_trend(seq)
                            trend_rows.append({
                                "condition": cond_name, "round": round_num, "client_id": cid, "stat": stat,
                                "cited_direction": claim["cited_direction"], "actual_direction": actual,
                                "window_size": window_size, "sequence": seq,
                                "insufficient_history": window_size < 2,
                                "correct": (actual is not None and actual == claim["cited_direction"]),
                            })

    # ------------------------------------------------------------------
    # (a) citation accuracy, (b) citation frequency, (c) correlation -- per mode
    # ------------------------------------------------------------------
    for mode in MODES:
        rows = citation_rows_by_mode[mode]
        n_correct = sum(1 for r in rows if r["correct"])
        loose_error = 1 - (n_correct / len(rows)) if rows else None
        n_wrong = sum(1 for r in rows if r["strict_verdict"] == "wrong")
        n_amb = sum(1 for r in rows if r["strict_verdict"] == "ambiguous")
        n_ok = sum(1 for r in rows if r["strict_verdict"] == "correct")
        strict_error = n_wrong / (n_wrong + n_ok) if (n_wrong + n_ok) else None

        by_stat = {}
        for stat in STATS:
            srows = [r for r in rows if r["stat"] == stat]
            if not srows:
                continue
            acc = sum(1 for r in srows if r["correct"]) / len(srows)
            s_wrong = sum(1 for r in srows if r["strict_verdict"] == "wrong")
            s_amb = sum(1 for r in srows if r["strict_verdict"] == "ambiguous")
            s_ok = sum(1 for r in srows if r["strict_verdict"] == "correct")
            by_stat[stat] = {
                "n": len(srows), "loose_error_rate": round(1 - acc, 4),
                "strict_error_rate_excl_ambiguous": round(s_wrong / (s_wrong + s_ok), 4) if (s_wrong + s_ok) else None,
                "strict_ambiguous_fraction": round(s_amb / len(srows), 4),
            }

        corr_rows = correlation_rows_by_mode[mode]
        correlation = {}
        for stat in STATS:
            sevs = [r[1] for r in corr_rows if r[0] == stat]
            pcts = [r[2] for r in corr_rows if r[0] == stat]
            rho, pval = spearmanr(sevs, pcts)
            correlation[stat] = {"spearman_rho": round(float(rho), 4), "p_value": float(pval), "n": len(sevs)}

        report["by_mode"][mode] = {
            "n_explanations": n_explanations_by_mode[mode],
            "citation_frequency_count": citation_freq_by_mode[mode],
            "citation_frequency_rate": {
                s: round(citation_freq_by_mode[mode][s] / n_explanations_by_mode[mode], 4) for s in STATS
            },
            "citation_accuracy": {
                "n_citations_extracted": len(rows),
                "loose_overall_error_rate": round(loose_error, 4) if loose_error is not None else None,
                "strict_overall_error_rate_excl_ambiguous": round(strict_error, 4) if strict_error is not None else None,
                "strict_ambiguous_fraction": round(n_amb / len(rows), 4) if rows else None,
                "by_stat": by_stat,
            },
            "decision_stat_correlation": correlation,
        }

    # ------------------------------------------------------------------
    # (d) trend-language factual-consistency check, rolling_history only
    # ------------------------------------------------------------------
    scoreable = [r for r in trend_rows if not r["insufficient_history"]]
    insufficient = [r for r in trend_rows if r["insufficient_history"]]
    n_correct_trend = sum(1 for r in scoreable if r["correct"])
    by_stat_trend = {}
    for stat in STATS:
        srows = [r for r in scoreable if r["stat"] == stat]
        if srows:
            by_stat_trend[stat] = {
                "n": len(srows),
                "error_rate": round(1 - sum(1 for r in srows if r["correct"]) / len(srows), 4),
            }
    report["trend_language_check"] = {
        "method_note": (
            "Rolling-history explanations only. For each stat the explanation mentions with a "
            "trend word (increasing/decreasing/stable-family) within 90 chars, the CITED direction "
            "is compared against the ACTUAL direction computed from the sequence itself (endpoint "
            "comparison: stable if |last-first| <= 5% relative tolerance, else sign of last-first -- "
            "a simple rule, not a regression fit, documented as such). Claims where the two nearest "
            "trend words disagree (ambiguous attribution) are skipped, not guessed. "
            "insufficient_history = the claim was made when window_size < 2, i.e. the round genuinely "
            "had no prior data to form a trend from -- a spurious/hallucinated trend claim if it occurs."
        ),
        "n_trend_claims_total": len(trend_rows),
        "n_scoreable_window_ge_2": len(scoreable),
        "n_insufficient_history_window_lt_2": len(insufficient),
        "overall_error_rate": round(1 - (n_correct_trend / len(scoreable)), 4) if scoreable else None,
        "by_stat": by_stat_trend,
        "insufficient_history_examples": insufficient[:10],
    }

    # ------------------------------------------------------------------
    # (e) direct side-by-side vs Phase 3's PUBLISHED numbers (different
    # condition set: Phase 3 = clean/f3_{0,3,5}/f2_{0,3}; this replay =
    # clean/sudden_{0,3,5}/gradual_{0,3,5} -- sudden_{0,3,5} IS the same
    # condition as Phase 3's f3_{0,3,5}, f2 replaced by gradual here, so
    # the pooled numbers are not drawn from an identical condition set.
    # Flagged explicitly, not smoothed over.
    # ------------------------------------------------------------------
    report["comparison_to_phase3_published"] = {
        "caveat": (
            "Phase 3's published pooled numbers were computed over "
            "{clean, f3_{0,3,5}, f2_{0,3}}; this replay's pooled numbers are computed over "
            "{clean, sudden_{0,3,5}, gradual_{0,3,5}} -- sudden_{0,3,5} is the identical condition "
            "to Phase 3's f3_{0,3,5}, but f2_{0,3} is replaced by gradual_{0,3,5} here, so the two "
            "pooled numbers are not from an identical condition set. current_round mode's numbers "
            "below are this replay's OWN fresh current_round pass (same prompt/model as Phase 3, new "
            "sample) -- the cleanest same-conditions-modulo-f2-vs-gradual comparison point for "
            "rolling_history is against THIS replay's own current_round column, not directly against "
            "Phase 3's on-disk numbers."
        ),
        "phase3_published": {
            "citation_accuracy_strict_overall_error_rate": 0.117,
            "citation_accuracy_strict_by_stat_error_rate": {
                "update_norm": 0.251, "cosine_to_global": 0.044, "cosine_to_peer_mean": None,
                "train_loss": 0.038, "val_accuracy": 0.086,
            },
            "decision_stat_correlation_spearman_rho": {
                "cosine_to_global": -0.808, "train_loss": 0.793, "val_accuracy": -0.745,
                "update_norm": 0.419, "cosine_to_peer_mean": 0.298,
            },
        },
    }

    OUT_PATH.write_text(json.dumps(report, indent=2, default=str))
    print(f"Wrote {OUT_PATH}")

    # ------------------------------------------------------------------
    # console summary
    # ------------------------------------------------------------------
    print("\n=== (a) CITATION ACCURACY, this replay, both modes (pooled over clean/sudden/gradual) ===")
    for mode in MODES:
        ca = report["by_mode"][mode]["citation_accuracy"]
        print(f"  [{mode}] n={ca['n_citations_extracted']} loose_error={ca['loose_overall_error_rate']} "
              f"strict_error_excl_ambig={ca['strict_overall_error_rate_excl_ambiguous']} "
              f"ambiguous_frac={ca['strict_ambiguous_fraction']}")
        for stat, v in ca["by_stat"].items():
            print(f"      {stat}: n={v['n']} loose={v['loose_error_rate']} strict={v['strict_error_rate_excl_ambiguous']}")

    print("\n=== (b) CITATION FREQUENCY RATE, both modes ===")
    for mode in MODES:
        print(f"  [{mode}] n_explanations={report['by_mode'][mode]['n_explanations']}: "
              f"{report['by_mode'][mode]['citation_frequency_rate']}")

    print("\n=== (c) DECISION-STAT CORRELATION (Spearman rho), both modes ===")
    for mode in MODES:
        print(f"  [{mode}]")
        for stat, v in report["by_mode"][mode]["decision_stat_correlation"].items():
            print(f"      {stat}: rho={v['spearman_rho']:+.4f} p={v['p_value']:.3g} n={v['n']}")
    print(f"  [phase3_published]")
    for stat, rho in report["comparison_to_phase3_published"]["phase3_published"]["decision_stat_correlation_spearman_rho"].items():
        print(f"      {stat}: rho={rho:+.3f}")

    print("\n=== (d) TREND-LANGUAGE FACTUAL CONSISTENCY (rolling_history only) ===")
    tl = report["trend_language_check"]
    print(f"  n_trend_claims_total={tl['n_trend_claims_total']} "
          f"n_scoreable(window>=2)={tl['n_scoreable_window_ge_2']} "
          f"n_insufficient_history(window<2)={tl['n_insufficient_history_window_lt_2']}")
    print(f"  overall_error_rate={tl['overall_error_rate']}")
    for stat, v in tl["by_stat"].items():
        print(f"    {stat}: n={v['n']} error_rate={v['error_rate']}")


if __name__ == "__main__":
    main()
