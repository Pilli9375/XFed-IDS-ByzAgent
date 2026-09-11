"""ByzAgent Phase 3, Step 3b -- analysis over scripts/phase3_verification_gate.py's
raw replay output (results/inspection/phase3_gate_raw_a0.5_s42.json).

Computes, per 01_Planning's Step 3b/reasoning-audit spec:
  1. Decision distribution per round/condition, malicious vs clean.
  2. Malicious-silo correct-flag rate and clean-silo false-positive rate,
     plus the Krum mechanism-level comparison.
  3. Decision-variance stability (3x same-input repeats).
  4. Reasoning-vs-outcome audit:
     a) stat citation frequency (by decision type, by true malicious/clean)
     b) citation accuracy (cited "low"/"high" vs actual within-round
        percentile), automated + a hand-check sample dumped to disk
     c) decision-stat correlation (Spearman, decision severity vs each
        stat's within-round percentile)

No new LLM calls -- pure analysis of already-collected data.
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/phase3_gate_raw_a0.5_s42.json"
OUT_PATH = PROJECT_ROOT / "results/inspection/phase3_gate_analysis_a0.5_s42.json"
HAND_CHECK_PATH = PROJECT_ROOT / "results/inspection/phase3_citation_accuracy_sample.json"

DECISION_SEVERITY = {"trust": 0, "downweight": 1, "quarantine": 2}
STATS = ["update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy"]

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
    """Fraction of the OTHER values strictly less than `value`, averaged with
    ties given half credit -- standard midrank percentile, 0=lowest, 1=highest
    among the round's 10 silos for that stat.
    """
    n = len(all_values)
    if n <= 1:
        return 0.5
    less = sum(1 for v in all_values if v < value)
    equal = sum(1 for v in all_values if v == value)
    return (less + 0.5 * (equal - 1)) / (n - 1)


def main() -> None:
    raw = json.loads(RAW_PATH.read_text())
    conditions = raw["conditions"]
    results = raw["results"]

    report: dict = {"conditions": {}}

    # ------------------------------------------------------------------
    # 1+2: decision distribution, correct-flag rate, FPR, Krum comparison
    # ------------------------------------------------------------------
    for cond_name, cond_meta in conditions.items():
        malicious = set(cond_meta["malicious_silos"])
        cond_results = results[cond_name]

        per_round_dist = {}
        malicious_flag_events = []  # 1 if flagged (downweight/quarantine), else 0
        malicious_quarantine_events = []
        clean_flag_events = []
        clean_quarantine_events = []

        for round_str, rd in cond_results.items():
            dist = {"trust": 0, "downweight": 0, "quarantine": 0}
            dist_malicious = {"trust": 0, "downweight": 0, "quarantine": 0}
            dist_clean = {"trust": 0, "downweight": 0, "quarantine": 0}
            for d in rd["decisions"]:
                silo_num = int(d["client_id"].split("_")[1])
                dec = d["decision"]
                dist[dec] += 1
                is_mal = silo_num in malicious
                (dist_malicious if is_mal else dist_clean)[dec] += 1
                flagged = 1 if dec in ("downweight", "quarantine") else 0
                quarantined = 1 if dec == "quarantine" else 0
                if is_mal:
                    malicious_flag_events.append(flagged)
                    malicious_quarantine_events.append(quarantined)
                else:
                    clean_flag_events.append(flagged)
                    clean_quarantine_events.append(quarantined)
            per_round_dist[round_str] = {"all": dist, "malicious": dist_malicious, "clean": dist_clean}

        def rate(events):
            return (sum(events) / len(events)) if events else None

        report["conditions"][cond_name] = {
            "malicious_silos": sorted(malicious),
            "per_round_decision_distribution": per_round_dist,
            "malicious_silo_flag_rate_downweight_or_quarantine": rate(malicious_flag_events),
            "malicious_silo_quarantine_only_rate": rate(malicious_quarantine_events),
            "clean_silo_false_positive_rate_downweight_or_quarantine": rate(clean_flag_events),
            "clean_silo_quarantine_only_rate": rate(clean_quarantine_events),
            "n_malicious_observations": len(malicious_flag_events),
            "n_clean_observations": len(clean_flag_events),
            "krum_comparison_note": (
                "Krum's mechanism-level malicious-silo exclusion rate (Phase 2, "
                "PHASE2_SUMMARY.md) was 0.0000 at BOTH f=3 and f=2 -- Krum's "
                "weight-space distance metric never once excluded a truly "
                "malicious silo. Krum has NO chance-baseline analogy that "
                "applies cleanly to ByzAgent: Krum's f/n chance baseline follows "
                "from its fixed num_excluded=f construction, which ByzAgent has "
                "no equivalent of (ByzAgent's decisions are a free 3-way choice "
                "per client, not a fixed-count selection). The clean_silo_"
                "false_positive_rate above is the honest empirical baseline to "
                "compare malicious_silo_flag_rate against instead -- if the two "
                "rates are close, that is as uninformative as Krum's 0.0000, "
                "reported the same way Phase 2 corrected the trimmed-mean f/n "
                "baseline rather than reusing an ill-fitting analogy."
            ),
        }

    # ------------------------------------------------------------------
    # 3: decision-variance stability
    # ------------------------------------------------------------------
    variance = raw["variance_check"]
    variance_report = {"round": variance["round"], "repeats": variance["repeats"], "by_condition": {}}
    for cond_name, repeats in variance["by_condition"].items():
        by_silo = defaultdict(list)
        for rep in repeats:
            for d in rep:
                by_silo[d["client_id"]].append({"decision": d["decision"], "explanation": d["explanation"]})
        silo_stability = {}
        for cid, entries in by_silo.items():
            decisions_seen = [e["decision"] for e in entries]
            stable = len(set(decisions_seen)) == 1
            # crude explanation-consistency check: do all 3 explanations cite
            # the same SET of stats (via the same keyword matcher used below)?
            cited_sets = []
            for e in entries:
                cited = {s for s, pat in STAT_KEYWORD_PATTERNS.items() if pat.search(e["explanation"])}
                cited_sets.append(cited)
            explanation_consistent = len(set(frozenset(s) for s in cited_sets)) == 1
            silo_stability[cid] = {
                "decisions": decisions_seen,
                "stable": stable,
                "cited_stat_sets": [sorted(s) for s in cited_sets],
                "explanation_cites_same_stats_all_3x": explanation_consistent,
            }
        n_stable = sum(1 for v in silo_stability.values() if v["stable"])
        variance_report["by_condition"][cond_name] = {
            "per_silo": silo_stability,
            "n_silos": len(silo_stability),
            "n_stable": n_stable,
            "stability_rate": n_stable / len(silo_stability) if silo_stability else None,
        }
    report["decision_variance"] = variance_report

    # ------------------------------------------------------------------
    # 4a: stat citation frequency
    # ------------------------------------------------------------------
    citation_freq = {
        cond_name: {
            "overall": {s: 0 for s in STATS},
            "by_decision": {dec: {s: 0 for s in STATS} for dec in ("trust", "downweight", "quarantine")},
            "by_truth": {"malicious": {s: 0 for s in STATS}, "clean": {s: 0 for s in STATS}},
            "n_explanations": 0,
            "n_explanations_malicious": 0,
            "n_explanations_clean": 0,
        }
        for cond_name in conditions
    }

    all_citation_rows = []  # for accuracy audit + correlation
    for cond_name, cond_meta in conditions.items():
        malicious = set(cond_meta["malicious_silos"])
        cond_results = results[cond_name]
        freq = citation_freq[cond_name]

        for round_str, rd in cond_results.items():
            # per-stat list of all 10 silos' values this round, for percentile calc
            round_values = {s: [c[s] for c in rd["client_stats"]] for s in STATS}

            for d in rd["decisions"]:
                cid = d["client_id"]
                silo_num = int(cid.split("_")[1])
                is_mal = silo_num in malicious
                dec = d["decision"]
                expl = d["explanation"]

                freq["n_explanations"] += 1
                (freq["n_explanations_malicious"] if is_mal else freq["n_explanations_clean"])
                if is_mal:
                    freq["n_explanations_malicious"] += 1
                else:
                    freq["n_explanations_clean"] += 1

                cited_here = set()
                for stat, pattern in STAT_KEYWORD_PATTERNS.items():
                    if pattern.search(expl):
                        cited_here.add(stat)
                        freq["overall"][stat] += 1
                        freq["by_decision"][dec][stat] += 1
                        freq["by_truth"]["malicious" if is_mal else "clean"][stat] += 1

                # -------- 4b/4c raw material: extract (stat, direction, value) --------
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
                    else:  # moderate
                        correct = 0.25 <= pct <= 0.75
                        strict_verdict = "correct" if 0.25 <= pct <= 0.75 else "wrong"
                    all_citation_rows.append({
                        "condition": cond_name, "round": int(round_str), "client_id": cid,
                        "decision": dec, "is_malicious": is_mal, "stat": stat,
                        "adjective": adj_raw.lower(), "direction": direction,
                        "cited_value": value, "actual_round_percentile": round(pct, 3),
                        "correct": correct, "strict_verdict": strict_verdict, "explanation": expl,
                    })

    report["citation_frequency"] = citation_freq

    # ------------------------------------------------------------------
    # 4b: citation accuracy
    # ------------------------------------------------------------------
    classifiable = [r for r in all_citation_rows]
    n_correct = sum(1 for r in classifiable if r["correct"])
    error_rate = 1 - (n_correct / len(classifiable)) if classifiable else None

    n_strict_wrong = sum(1 for r in classifiable if r["strict_verdict"] == "wrong")
    n_strict_ambiguous = sum(1 for r in classifiable if r["strict_verdict"] == "ambiguous")
    n_strict_correct = sum(1 for r in classifiable if r["strict_verdict"] == "correct")

    by_stat_error = {}
    for stat in STATS:
        rows = [r for r in classifiable if r["stat"] == stat]
        if rows:
            acc = sum(1 for r in rows if r["correct"]) / len(rows)
            strict_wrong = sum(1 for r in rows if r["strict_verdict"] == "wrong")
            strict_ambig = sum(1 for r in rows if r["strict_verdict"] == "ambiguous")
            strict_denom = len(rows) - strict_ambig
            by_stat_error[stat] = {
                "n": len(rows), "accuracy": acc, "loose_error_rate": 1 - acc,
                "strict_wrong": strict_wrong, "strict_ambiguous": strict_ambig,
                "strict_error_rate_excl_ambiguous": (strict_wrong / strict_denom) if strict_denom else None,
            }

    report["citation_accuracy"] = {
        "n_citations_extracted": len(classifiable),
        "n_correct": n_correct,
        "loose_overall_error_rate": error_rate,
        "strict_overall_error_rate_excl_ambiguous": (
            n_strict_wrong / (n_strict_wrong + n_strict_correct)
            if (n_strict_wrong + n_strict_correct) else None
        ),
        "strict_ambiguous_fraction": n_strict_ambiguous / len(classifiable) if classifiable else None,
        "by_stat": by_stat_error,
        "method_note": (
            "LOOSE: a citation is 'correct' if its qualitative direction (low/"
            "high/moderate) matches the cited value's actual within-round "
            "percentile rank among that round's 10 silos for that stat "
            "(low<=0.5, high>=0.5, moderate in [0.25,0.75]) -- this is a strict "
            "median split with no dead zone, so a value at e.g. the 55.6th "
            "percentile called 'low' counts as an error even though, at n=10 "
            "silos, that is only one rank above the exact median and may read "
            "as reasonable to a human, especially for train_loss where clean-"
            "round values often cluster tightly near zero regardless of local "
            "rank. STRICT (excl. ambiguous): requires high>=0.6 / low<=0.4 to "
            "count as correct, wrong requires the clear opposite side "
            "(high<=0.4 / low>=0.6), and the 0.4-0.6 band is excluded from the "
            "denominator entirely (ambiguous, not scored either way) -- this "
            "isolates genuinely clear-cut misreadings from boundary-threshold "
            "artifacts. Both are reported; hand-checked sample "
            "(phase3_citation_accuracy_sample.json) confirmed both real "
            "unambiguous errors (e.g. a value at the round's 100th percentile "
            "called 'low') and boundary-artifact cases (percentile ~0.44-0.56 "
            "flagged 'incorrect' under the loose rule alone) are present in "
            "the loose-rule sample -- the strict rate is the more defensible "
            "number for 'genuine misreading', the loose rate is the more "
            "conservative upper bound."
        ),
    }

    # hand-check sample: up to 20 flagged-incorrect + 10 flagged-correct, for
    # manual verification that the automated extractor itself is sound
    random.seed(3)
    incorrect_rows = [r for r in classifiable if not r["correct"]]
    correct_rows = [r for r in classifiable if r["correct"]]
    sample = (
        random.sample(incorrect_rows, min(20, len(incorrect_rows)))
        + random.sample(correct_rows, min(10, len(correct_rows)))
    )
    HAND_CHECK_PATH.write_text(json.dumps(sample, indent=2))

    # ------------------------------------------------------------------
    # 4c: decision-stat correlation (pooled + per condition)
    # ------------------------------------------------------------------
    correlation_rows = []  # (condition, stat, decision_severity, percentile)
    for cond_name, cond_meta in conditions.items():
        cond_results = results[cond_name]
        for round_str, rd in cond_results.items():
            round_values = {s: [c[s] for c in rd["client_stats"]] for s in STATS}
            stats_by_client = {c["client_id"]: c for c in rd["client_stats"]}
            for d in rd["decisions"]:
                cid = d["client_id"]
                sev = DECISION_SEVERITY[d["decision"]]
                for stat in STATS:
                    pct = percentile_rank(stats_by_client[cid][stat], round_values[stat])
                    correlation_rows.append((cond_name, stat, sev, pct))

    correlation_report = {"pooled": {}, "by_condition": {}}
    for stat in STATS:
        sevs = [r[2] for r in correlation_rows if r[1] == stat]
        pcts = [r[3] for r in correlation_rows if r[1] == stat]
        rho, pval = spearmanr(sevs, pcts)
        correlation_report["pooled"][stat] = {"spearman_rho": float(rho), "p_value": float(pval), "n": len(sevs)}

    for cond_name in conditions:
        correlation_report["by_condition"][cond_name] = {}
        for stat in STATS:
            sevs = [r[2] for r in correlation_rows if r[1] == stat and r[0] == cond_name]
            pcts = [r[3] for r in correlation_rows if r[1] == stat and r[0] == cond_name]
            rho, pval = spearmanr(sevs, pcts)
            correlation_report["by_condition"][cond_name][stat] = {
                "spearman_rho": float(rho), "p_value": float(pval), "n": len(sevs)
            }

    correlation_report["method_note"] = (
        "Spearman correlation between decision severity (trust=0, "
        "downweight=1, quarantine=2) and each stat's WITHIN-ROUND percentile "
        "rank (0=lowest of that round's 10 silos, 1=highest) -- percentile, "
        "not raw value, so cross-round scale drift (e.g. train_loss shrinking "
        "over training) does not confound the correlation. Negative rho for "
        "cosine_to_global/cosine_to_peer_mean is expected in the correct "
        "direction (higher cosine = more aligned = less severe decision); "
        "positive rho expected for update_norm/train_loss (higher = more "
        "severe decision); val_accuracy's expected sign is deliberately NOT "
        "stated here -- read the caveat note in citation_frequency/prompt "
        "before interpreting it. This is computed independent of what the "
        "explanations claim -- compare against citation_frequency above for "
        "the 'right answer, wrong stated reason' check."
    )
    report["decision_stat_correlation"] = correlation_report

    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Wrote analysis to {OUT_PATH}")
    print(f"Wrote hand-check sample ({len(sample)} rows) to {HAND_CHECK_PATH}")

    # ------------------------------------------------------------------
    # console summary
    # ------------------------------------------------------------------
    print("\n=== SUMMARY ===")
    for cond_name, c in report["conditions"].items():
        print(f"\n[{cond_name}] malicious={c['malicious_silos']}")
        print(f"  malicious flag rate (downweight|quarantine): {c['malicious_silo_flag_rate_downweight_or_quarantine']}")
        print(f"  malicious quarantine-only rate:               {c['malicious_silo_quarantine_only_rate']}")
        print(f"  clean false-positive rate (downweight|quarantine): {c['clean_silo_false_positive_rate_downweight_or_quarantine']}")
        print(f"  clean quarantine-only rate:                    {c['clean_silo_quarantine_only_rate']}")

    print("\n=== CITATION FREQUENCY (overall count per stat, by condition) ===")
    for cond_name, freq in citation_freq.items():
        print(f"  [{cond_name}] n_explanations={freq['n_explanations']}: {freq['overall']}")

    ca = report["citation_accuracy"]
    print(f"\n=== CITATION ACCURACY === n={ca['n_citations_extracted']} "
          f"loose_error_rate={ca['loose_overall_error_rate']:.3f} "
          f"strict_error_rate_excl_ambiguous={ca['strict_overall_error_rate_excl_ambiguous']:.3f} "
          f"ambiguous_fraction={ca['strict_ambiguous_fraction']:.3f}")
    for stat, v in by_stat_error.items():
        print(f"  {stat}: n={v['n']} loose_error_rate={v['loose_error_rate']:.3f} "
              f"strict_error_rate={v['strict_error_rate_excl_ambiguous']}")

    print("\n=== DECISION-STAT CORRELATION (pooled, Spearman rho) ===")
    for stat, v in correlation_report["pooled"].items():
        print(f"  {stat}: rho={v['spearman_rho']:.3f} p={v['p_value']:.4g} n={v['n']}")

    print("\n=== DECISION VARIANCE STABILITY ===")
    for cond_name, v in variance_report["by_condition"].items():
        print(f"  [{cond_name}] {v['n_stable']}/{v['n_silos']} silos stable across 3x repeats "
              f"(rate={v['stability_rate']:.2f})")


if __name__ == "__main__":
    main()
