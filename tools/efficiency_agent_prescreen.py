"""Efficiency Part A -- offline replay of a train_loss pre-screen in front of
ByzAgent. No LLM is called and no test rows are read: the inputs are the
existing current-round decision logs (results/federated/*/agent_decisions*.jsonl),
whose raw_stats_given carries the train_loss the agent was shown.

Pre-screen: in each round, ratio_i = train_loss_i / median_j(train_loss_j)
over all orgs. Orgs with ratio_i > t go to the LLM and keep the decision the
LLM logged for them; every other org is auto-trusted. A round with no org
over t makes no LLM call.

t is chosen on seed 42 only, by the rule fixed in configs/efficiency.yaml
(agent_prescreen.selection), then reported on seeds 1337 and 2024.

Run from project root: python tools/efficiency_agent_prescreen.py
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

import yaml

CONFIG_PATH = Path("configs/efficiency.yaml")


def load_log(path: Path) -> dict[int, dict[int, dict]]:
    """{round: {silo_index: {"decision", "train_loss"}}}"""
    by_round: dict[int, dict[int, dict]] = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            silo = int(row["silo_id"].split("_")[1])
            by_round[row["round"]][silo] = {
                "decision": row["decision"],
                "train_loss": row["raw_stats_given"]["train_loss"],
            }
    return dict(by_round)


def ratios(by_round: dict[int, dict[int, dict]]) -> dict[int, dict[int, float]]:
    out = {}
    for rnd, silos in by_round.items():
        med = statistics.median(s["train_loss"] for s in silos.values())
        out[rnd] = {i: s["train_loss"] / med for i, s in silos.items()}
    return out


def rate(num: int, den: int) -> float | None:
    return num / den if den else None


def replay(by_round, ratio, t, malicious, flag_set, auto_decision, attacked):
    n_rounds = len(by_round)
    rounds_with_call = 0
    slots_total = slots_sent = 0
    agree_exact = agree_binary = 0
    # counters keyed by group: poisoned / clean
    flags = {"poisoned": [0, 0, 0], "clean": [0, 0, 0]}  # replay, logged, n
    poisoned_logged_flags = poisoned_logged_flags_kept = 0
    for rnd, silos in by_round.items():
        sent = {i for i in silos if ratio[rnd][i] > t}
        rounds_with_call += bool(sent)
        slots_total += len(silos)
        slots_sent += len(sent)
        for i, s in silos.items():
            logged = s["decision"]
            replayed = logged if i in sent else auto_decision
            agree_exact += replayed == logged
            agree_binary += (replayed in flag_set) == (logged in flag_set)
            group = "poisoned" if (attacked and i in malicious) else "clean"
            flags[group][0] += replayed in flag_set
            flags[group][1] += logged in flag_set
            flags[group][2] += 1
            if group == "poisoned" and logged in flag_set:
                poisoned_logged_flags += 1
                poisoned_logged_flags_kept += i in sent
    out = {
        "t": t,
        "n_rounds": n_rounds,
        "llm_calls_made": rounds_with_call,
        "llm_calls_avoided_pct": 100 * (n_rounds - rounds_with_call) / n_rounds,
        "org_slots_total": slots_total,
        "org_slots_sent_to_llm": slots_sent,
        "org_slots_avoided_pct": 100 * (slots_total - slots_sent) / slots_total,
        "agreement_exact": agree_exact / slots_total,
        "agreement_trust_vs_flag": agree_binary / slots_total,
    }
    for g, (rep, logd, n) in flags.items():
        if n:
            out[f"flag_rate_{g}_replay"] = rep / n
            out[f"flag_rate_{g}_logged"] = logd / n
            out[f"n_{g}_org_rounds"] = n
    if attacked:
        out["poisoned_logged_flags"] = poisoned_logged_flags
        out["poisoned_flag_retention"] = rate(poisoned_logged_flags_kept, poisoned_logged_flags)
    return out


def main() -> None:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["agent_prescreen"]
    flag_set = set(cfg["flag_decisions"])
    grid = cfg["threshold_grid"]

    runs = {}
    for name, rc in cfg["runs"].items():
        by_round = load_log(Path(rc["log"]))
        assert len(by_round) == 20 and all(len(s) == 10 for s in by_round.values()), name
        runs[name] = {
            "rc": rc,
            "by_round": by_round,
            "ratio": ratios(by_round),
            "malicious": set(rc.get("malicious_silos", cfg["malicious_silos"])),
            "attacked": rc["attack"] != "none",
        }

    def run_at(name, t):
        r = runs[name]
        return replay(r["by_round"], r["ratio"], t, r["malicious"], flag_set,
                      cfg["auto_decision"], r["attacked"])

    # ---- selection on seed 42 only ----
    sel = cfg["selection"]
    selection_table = []
    for t in grid:
        rows = {name: run_at(name, t) for name in sel["selection_runs"]}
        ok = all(row["poisoned_flag_retention"] >= sel["min_poisoned_flag_retention"]
                 for row in rows.values())
        selection_table.append({
            "t": t,
            "passes": ok,
            "retention": {n: row["poisoned_flag_retention"] for n, row in rows.items()},
            "llm_calls_avoided_pct": {n: row["llm_calls_avoided_pct"] for n, row in rows.items()},
            "org_slots_avoided_pct": {n: row["org_slots_avoided_pct"] for n, row in rows.items()},
        })
    passing = [row["t"] for row in selection_table if row["passes"]]
    t_star = max(passing)

    # ---- per-run results at t* (seed 42 shown for completeness, labelled) ----
    at_t = {name: {"seed": r["rc"]["seed"], "attack": r["rc"]["attack"],
                   "used_for_selection": name in sel["selection_runs"],
                   **run_at(name, t_star)}
            for name, r in runs.items()}

    # Ratio of poisoned orgs that never reach the LLM (exposure diagnostic).
    exposure = {}
    for name, r in runs.items():
        if not r["attacked"]:
            continue
        below = [(rnd, i, round(r["ratio"][rnd][i], 3)) for rnd in sorted(r["ratio"])
                 for i in sorted(r["malicious"]) if r["ratio"][rnd][i] <= t_star]
        exposure[name] = {"poisoned_org_rounds_never_sent": len(below),
                          "of": 20 * len(r["malicious"]),
                          "list_round_silo_ratio": below}

    # Sensitivity curve on report seeds -- NOT used for selection.
    sensitivity = {name: [run_at(name, t) for t in grid]
                   for name, r in runs.items() if r["rc"]["seed"] in cfg["report_seeds"]}

    # Logged per-call wall time (no pre-screen), for converting skipped calls to seconds.
    timing = {}
    for src in cfg["call_timing_sources"]:
        d = json.loads(Path(src).read_text())
        for cond, rounds in d["results"].items():
            el = [v["elapsed_sec"] for v in rounds.values()]
            timing[f"{Path(src).name}:{cond}"] = {
                "n_calls": len(el), "mean_sec": statistics.mean(el),
                "median_sec": statistics.median(el), "min_sec": min(el), "max_sec": max(el)}

    out = {
        "source": ("Offline replay of logged ByzAgent current-round decisions; no LLM "
                   "calls, no test rows. Logs: " + ", ".join(rc["log"] for rc in cfg["runs"].values())
                   + ". Script: tools/efficiency_agent_prescreen.py. Config: configs/efficiency.yaml."),
        "kind": "replay against one logged sample of a nondeterministic agent",
        "definitions": {
            "ratio": "train_loss / median(train_loss of all 10 orgs in the same round)",
            "sent_to_llm": f"ratio > t ({cfg['comparison']})",
            "auto_decision": cfg["auto_decision"],
            "flag": sorted(flag_set),
            "llm_calls_avoided_pct": "rounds with no org over t / 20; the agent makes one batched call per round",
            "org_slots_avoided_pct": "(org,round) pairs not sent to the LLM / 200",
            "agreement_exact": "replayed decision == logged decision (3-way)",
            "agreement_trust_vs_flag": "same side of trust vs downweight|quarantine",
            "poisoned_flag_retention": "logged flags on poisoned (org,round) pairs that the pre-screen still sends to the LLM",
        },
        "selection_rule": sel,
        "selection_table_seed42": selection_table,
        "t_selected": t_star,
        "results_at_t_selected": at_t,
        "poisoned_exposure_at_t_selected": exposure,
        "sensitivity_report_seeds_not_used_for_selection": sensitivity,
        "logged_call_timing_no_prescreen": timing,
    }
    out_path = Path(cfg["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))

    print("selection (seed 42):")
    for row in selection_table:
        print(f"  t={row['t']:>5}: pass={row['passes']}  retention={row['retention']}  "
              f"calls_avoided={row['llm_calls_avoided_pct']}")
    print(f"t* = {t_star}")
    for name, row in at_t.items():
        print(f"\n{name}: " + ", ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                                       for k, v in row.items()))
    for name, e in exposure.items():
        print(f"{name}: poisoned org-rounds never sent = {e['poisoned_org_rounds_never_sent']}/{e['of']}")
    print("\nsensitivity on report seeds (not used for selection):")
    for name, rows in sensitivity.items():
        print(f"  {name}: " + "  ".join(
            f"t={row['t']}:slots_avoided={row['org_slots_avoided_pct']:.1f}%"
            + (f",ret={row['poisoned_flag_retention']:.3f}" if "poisoned_flag_retention" in row else "")
            + f",clean_flag={row['flag_rate_clean_replay']:.3f}"
            for row in rows))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
