"""ByzAgent multi-seed validation, Step 4a -- reasoning-vs-outcome fidelity
audit on the Step 3 multi-seed decisions, same methodology as
scripts/phase3_analysis.py's citation frequency / citation accuracy /
decision-stat correlation sections (4a/4b/4c), reused verbatim (not
rewritten) minus the decision-variance section, which this session's Step 3
did not run (out of scope -- no variance_check key in the raw data).

No new LLM calls -- pure analysis of results/inspection/multiseed_agent_gate_raw.json.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from scipy.stats import spearmanr

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/multiseed_agent_gate_raw.json"
OUT_PATH = PROJECT_ROOT / "results/inspection/multiseed_fidelity_audit.json"
HAND_CHECK_PATH = PROJECT_ROOT / "results/inspection/multiseed_citation_accuracy_sample.json"

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

    for cond_name, cond_meta in conditions.items():
        malicious = set(cond_meta["malicious_silos"])
        cond_results = results[cond_name]
        malicious_flag_events, clean_flag_events = [], []
        for round_str, rd in cond_results.items():
            for d in rd["decisions"]:
                silo_num = int(d["client_id"].split("_")[1])
                is_mal = silo_num in malicious
                flagged = 1 if d["decision"] in ("downweight", "quarantine") else 0
                (malicious_flag_events if is_mal else clean_flag_events).append(flagged)

        def rate(events):
            return (sum(events) / len(events)) if events else None

        report["conditions"][cond_name] = {
            "malicious_silos": sorted(malicious),
            "malicious_silo_flag_rate": rate(malicious_flag_events),
            "clean_silo_false_positive_rate": rate(clean_flag_events),
        }

    citation_freq = {
        cond_name: {"overall": {s: 0 for s in STATS}, "n_explanations": 0}
        for cond_name in conditions
    }

    all_citation_rows = []
    for cond_name, cond_meta in conditions.items():
        cond_results = results[cond_name]
        freq = citation_freq[cond_name]
        for round_str, rd in cond_results.items():
            round_values = {s: [c[s] for c in rd["client_stats"]] for s in STATS}
            for d in rd["decisions"]:
                cid = d["client_id"]
                dec = d["decision"]
                expl = d["explanation"]
                freq["n_explanations"] += 1

                for stat, pattern in STAT_KEYWORD_PATTERNS.items():
                    if pattern.search(expl):
                        freq["overall"][stat] += 1

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
                    all_citation_rows.append({
                        "condition": cond_name, "round": int(round_str), "client_id": cid,
                        "decision": dec, "stat": stat, "adjective": adj_raw.lower(),
                        "direction": direction, "cited_value": value,
                        "actual_round_percentile": round(pct, 3),
                        "correct": correct, "strict_verdict": strict_verdict, "explanation": expl,
                    })

    report["citation_frequency"] = citation_freq

    classifiable = all_citation_rows
    n_correct = sum(1 for r in classifiable if r["correct"])
    error_rate = 1 - (n_correct / len(classifiable)) if classifiable else None
    n_strict_wrong = sum(1 for r in classifiable if r["strict_verdict"] == "wrong")
    n_strict_correct = sum(1 for r in classifiable if r["strict_verdict"] == "correct")
    n_strict_ambiguous = sum(1 for r in classifiable if r["strict_verdict"] == "ambiguous")

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
                "strict_error_rate_excl_ambiguous": (strict_wrong / strict_denom) if strict_denom else None,
            }

    report["citation_accuracy"] = {
        "n_citations_extracted": len(classifiable),
        "loose_overall_error_rate": error_rate,
        "strict_overall_error_rate_excl_ambiguous": (
            n_strict_wrong / (n_strict_wrong + n_strict_correct)
            if (n_strict_wrong + n_strict_correct) else None
        ),
        "strict_ambiguous_fraction": n_strict_ambiguous / len(classifiable) if classifiable else None,
        "by_stat": by_stat_error,
    }

    random.seed(3)
    incorrect_rows = [r for r in classifiable if not r["correct"]]
    correct_rows = [r for r in classifiable if r["correct"]]
    sample = (
        random.sample(incorrect_rows, min(20, len(incorrect_rows)))
        + random.sample(correct_rows, min(10, len(correct_rows)))
    )
    HAND_CHECK_PATH.write_text(json.dumps(sample, indent=2))

    correlation_rows = []
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

    correlation_report = {"pooled": {}}
    for stat in STATS:
        sevs = [r[2] for r in correlation_rows if r[1] == stat]
        pcts = [r[3] for r in correlation_rows if r[1] == stat]
        rho, pval = spearmanr(sevs, pcts)
        correlation_report["pooled"][stat] = {"spearman_rho": float(rho), "p_value": float(pval), "n": len(sevs)}
    report["decision_stat_correlation"] = correlation_report

    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Wrote analysis to {OUT_PATH}")
    print(f"Wrote hand-check sample ({len(sample)} rows) to {HAND_CHECK_PATH}")

    print("\n=== SUMMARY ===")
    for cond_name, c in report["conditions"].items():
        print(f"[{cond_name}] malicious_flag_rate={c['malicious_silo_flag_rate']} "
              f"clean_fpr={c['clean_silo_false_positive_rate']}")

    print("\n=== CITATION FREQUENCY (count, n_explanations per condition) ===")
    for cond_name, freq in citation_freq.items():
        print(f"  [{cond_name}] n={freq['n_explanations']}: {freq['overall']}")

    ca = report["citation_accuracy"]
    print(f"\n=== CITATION ACCURACY === n={ca['n_citations_extracted']} "
          f"loose={ca['loose_overall_error_rate']:.3f} "
          f"strict={ca['strict_overall_error_rate_excl_ambiguous']:.3f} "
          f"ambiguous_frac={ca['strict_ambiguous_fraction']:.3f}")
    for stat, v in by_stat_error.items():
        print(f"  {stat}: n={v['n']} loose={v['loose_error_rate']:.3f} strict={v['strict_error_rate_excl_ambiguous']}")

    print("\n=== DECISION-STAT CORRELATION (pooled, Spearman rho) ===")
    for stat, v in correlation_report["pooled"].items():
        print(f"  {stat}: rho={v['spearman_rho']:.3f} p={v['p_value']:.4g} n={v['n']}")


if __name__ == "__main__":
    main()
