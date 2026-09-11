"""Client Trust Monitor -- Contribution B / ByzAgent panel.

Visualizes ByzAgent's already-logged per-round trust decisions
(agent_decisions*.jsonl) and behavioral stats (client_stats.jsonl).
NO NEW COMPUTATION happens here: every number is read from an artifact
already on disk under results/federated/ and results/attacks/.

Separate from Section 3 (Explain / SHAP): that panel explains model
predictions on individual flows; this one explains ByzAgent's trust
decisions about federation clients. Different subjects, kept apart.

FRAMING, non-negotiable (see docs/contribution_b_results.md Sections
4-7): ByzAgent's malicious-silo flag rate is confounded by compositional
extremity -- some silos are flagged at high rates with zero attack
present, because the agent's geometry-based stats key on the same
low-Benign-share axis Phase 0's worst-case attacker selection also
selects on. Real attack-responsive detection is also genuinely present
(visible once a silo's clean-run rate isn't already near 1.00). Both
are true; neither is asserted here without the other. Consequently: a
raw flag rate must never be shown in this panel without its clean-run
companion alongside it.
"""
from __future__ import annotations

import streamlit as st

from app_lib import plots, theme, trust_loaders as tl
from app_lib.sections import PLOTLY_CONFIG


def _mode_options(condition_key: str) -> dict[str, str]:
    modes = tl.CONDITIONS[condition_key]["modes"]
    return {k: v["label"] for k, v in modes.items()}


def render_trust_monitor() -> None:
    theme.section_header(
        "Contribution B",
        "Client Trust Monitor",
        "ByzAgent's per-round trust decisions (trust / downweight / "
        "quarantine) for each of the 10 federation silos, read directly "
        "from <code>agent_decisions*.jsonl</code> and "
        "<code>client_stats.jsonl</code> already on disk. Nothing on this "
        "page is retrained or recomputed.",
    )
    theme.rule()

    theme.callout(
        "<b>This is not a demonstration of a working Byzantine detector.</b> "
        "ByzAgent's malicious-silo flag rate is confounded by "
        "compositional extremity: some silos are flagged at high rates "
        "with <b>zero attack present</b>, because the agent's stats key on "
        "the same low-Benign-share axis this project's worst-case attacker "
        "selection also selects on. Genuine attack-responsive detection is "
        "also present, visible mainly where a silo's clean-run rate isn't "
        "already near 1.00. Both are true at once — see "
        "<code>docs/contribution_b_results.md</code> §§4-7. Every flag "
        "rate below is shown next to its own clean-run baseline so this "
        "is visible on screen, not left to a caveat.",
        theme.WARN,
    )
    st.write("")

    with st.expander("ByzAgent vs. the classical baselines — the oracle asymmetry"):
        st.markdown(
            "Multi-Krum, classical Krum, and FedTrimmedAvg (Phase 2) were "
            "all given the **true** number of malicious silos (`f`) as an "
            "oracle. ByzAgent was given **neither** `f` nor any "
            "malicious-silo identity — it decides from behavioral stats "
            "alone. This is documented in prose in "
            "`docs/contribution_b_results.md` and "
            "`results/agents/PHASE3_SUMMARY.md`, not in a machine-readable "
            "config: no `agent_config.json` exists on disk, despite "
            "earlier phase-summary text claiming one is written per run — "
            "both documents now carry a dated correction note about that "
            "discrepancy. It changes no result; the asymmetry itself is "
            "real and unaffected."
        )

    # --- Controls ------------------------------------------------------
    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        seed = st.selectbox("Seed", tl.SEEDS, key="trust_seed")
    conditions = tl.conditions_for_seed(seed)
    with c2:
        condition_key = st.selectbox(
            "Attack condition",
            list(conditions.keys()),
            format_func=lambda k: conditions[k]["label"],
            key="trust_condition",
        )
    mode_opts = _mode_options(condition_key)
    with c3:
        mode_key = st.selectbox(
            "Agent mode",
            list(mode_opts.keys()),
            format_func=lambda k: mode_opts[k],
            key="trust_mode",
        )

    try:
        bundle = tl.load_condition_bundle(condition_key, mode_key)
    except FileNotFoundError as e:
        st.error(f"Missing artifact: {e}")
        return
    except ValueError as e:
        st.error(f"Data integrity check failed, refusing to render: {e}")
        return

    malicious = bundle["malicious_silos"]
    cond = tl.CONDITIONS[condition_key]

    theme.rule()

    # --- View 3: true malicious silos, read from attack_config.json ----
    theme.subhead(
        "Ground truth for this condition",
        f"Read from <code>results/attacks/{cond['attacks_tag']}/attack_config.json</code> "
        "— never hardcoded.",
    )
    theme.pills(
        [(f"malicious: silo {s}", theme.ALERT) for s in malicious]
        + [(f"clean: silo {s}", theme.TEXT_FAINT)
           for s in range(bundle["n_silos"]) if s not in malicious]
    )
    st.write("")

    theme.rule()

    # --- View 1: per-round decision grid --------------------------------
    theme.subhead(
        "Per-round decisions",
        "Rows = silos, columns = rounds. The attack-condition grid and its "
        "clean-run counterpart are shown together — a silo flagged in "
        "nearly every clean-run round is not attack-responsive detection.",
    )
    theme.pills([
        ("trust", theme.POSITIVE), ("downweight", theme.WARN), ("quarantine", theme.ALERT),
        ("⚠ = malicious under this condition", theme.TEXT_MUTED),
    ])
    st.write("")

    if bundle["mode_kind"] == "rolling":
        theme.callout(
            "<b>These decisions are LLM-generated, not deterministic</b> — "
            "the grid renders one sampled outcome per cell, not a fixed "
            "function of the stats. Stability was spot-checked, not "
            "assumed: at round 10 with current-round mode (3× independent "
            "repeats), the trust/flagged boundary was 100% stable "
            "(<code>results/agents/PHASE3_SUMMARY.md</code>). Under "
            "rolling-history — the mode shown below — that same boundary "
            "check regresses to <b>70-80% stability</b> "
            "(<code>results/agents/PHASE4_SUMMARY.md</code>, "
            "<code>docs/contribution_b_results.md</code> §6). A cell shown "
            "here as \"quarantine\" is not guaranteed to reproduce on a "
            "re-run.",
            theme.WARN,
        )
    else:
        theme.callout(
            "<b>These decisions are LLM-generated, not deterministic</b> — "
            "the grid renders one sampled outcome per cell, not a fixed "
            "function of the stats. Stability was spot-checked, not "
            "assumed, at round 10 only (3× independent repeats, not every "
            "round): 90% of decisions matched exactly, and every "
            "disagreement was a downweight↔quarantine wobble — the "
            "trust/flagged boundary itself was 100% stable "
            "(<code>results/agents/PHASE3_SUMMARY.md</code>, "
            "decision-variance stability).",
            theme.WARN,
        )
    st.write("")

    st.caption(f"Attack condition — {cond['label']}, {mode_opts[mode_key]}")
    attack_grid = tl.decision_grid(bundle["attack_decisions"], bundle["n_rounds"], bundle["n_silos"])
    st.plotly_chart(
        plots.decision_grid_heatmap(attack_grid, malicious),
        use_container_width=True, config=PLOTLY_CONFIG,
    )

    st.caption(f"Clean run (no attack) — same silos, same agent mode: {mode_opts[mode_key]}")
    clean_grid = tl.decision_grid(bundle["clean_decisions"], bundle["n_rounds"], bundle["n_silos"])
    st.plotly_chart(
        plots.decision_grid_heatmap(clean_grid, malicious),
        use_container_width=True, config=PLOTLY_CONFIG,
    )

    theme.rule()

    # --- View 2: clean vs. attack side by side, with lift ---------------
    theme.subhead(
        "Clean-vs-attack flag rate, and lift",
        "Lift (attack flag rate − clean flag rate) is the only honest "
        "detection measure here — a raw flag rate alone cannot tell "
        "attack-response apart from a silo the agent always flags.",
    )
    cmp_df = tl.clean_vs_attack_table(bundle)
    st.plotly_chart(
        plots.clean_vs_attack_lift(cmp_df),
        use_container_width=True, config=PLOTLY_CONFIG,
    )

    display = cmp_df.copy()
    display["silo"] = display["silo"].apply(lambda s: f"silo {int(s)}" + (" (malicious)" if s in malicious else ""))
    display["clean_flag_rate"] = display["clean_flag_rate"].map("{:.2f}".format)
    display["attack_flag_rate"] = display["attack_flag_rate"].map("{:.2f}".format)
    display["lift"] = display["lift"].map("{:+.2f}".format)
    st.dataframe(
        display.drop(columns=["malicious"]).rename(columns={
            "silo": "Silo", "clean_flag_rate": "Clean flag rate",
            "attack_flag_rate": "Attack flag rate", "lift": "Lift",
        }),
        use_container_width=True, hide_index=True,
    )

    theme.rule()

    # --- View 4: explanation on demand -----------------------------------
    theme.subhead(
        "Explanation for one decision",
        "The agent's actual natural-language rationale for a chosen "
        "(silo, round). Explanation fidelity — whether a cited stat "
        "genuinely matches the decision — was independently measured, not "
        "assumed; see <code>docs/contribution_b_results.md</code> §8 and "
        "the reasoning-vs-outcome audit in "
        "<code>results/agents/PHASE3_SUMMARY.md</code> before treating any "
        "one explanation below as self-evidently correct.",
    )
    d1, d2, d3 = st.columns([1, 1, 1])
    with d1:
        side = st.radio("Run", ["Attack condition", "Clean run"], key="trust_explain_side", horizontal=True)
    decisions_for_explain = bundle["attack_decisions"] if side == "Attack condition" else bundle["clean_decisions"]
    with d2:
        exp_silo = st.selectbox("Silo", list(range(bundle["n_silos"])), key="trust_explain_silo")
    with d3:
        exp_round = st.selectbox("Round", list(range(1, bundle["n_rounds"] + 1)), key="trust_explain_round")

    exp = tl.get_explanation(decisions_for_explain, exp_silo, exp_round)
    if exp is None:
        st.info("No decision logged for that (silo, round) in this run.")
    else:
        tone = {"trust": theme.POSITIVE, "downweight": theme.WARN, "quarantine": theme.ALERT}[exp["decision"]]
        theme.verdict(
            exp["decision"],
            f"silo {exp_silo}, round {exp_round}"
            + (" — malicious under this condition" if exp_silo in malicious else " — not malicious under this condition"),
            tone,
        )
        st.write("")
        st.markdown(f"**Explanation:** {exp['explanation']}")
        with st.expander("Raw stats given to the agent this round"):
            raw = {k: v for k, v in exp["raw_stats_given"].items() if k != "client_id"}
            st.json(raw)

    theme.rule()

    # --- View 5: stat trend per silo --------------------------------------
    theme.subhead(
        "Behavioral stat trend",
        "The 5 stats fed to the agent, over rounds, for one silo — this is "
        "the raw input the decisions above were made from.",
    )
    t1, t2 = st.columns([1, 1])
    with t1:
        trend_silo = st.selectbox("Silo", list(range(bundle["n_silos"])), key="trust_trend_silo")
    with t2:
        trend_side = st.radio("Run", ["Attack condition", "Clean run"], key="trust_trend_side", horizontal=True)
    trend_stats = bundle["attack_stats"] if trend_side == "Attack condition" else bundle["clean_stats"]
    trend_df = tl.silo_stat_trend(trend_stats, trend_silo)
    if trend_df.empty:
        st.info("No client_stats rows for that silo in this run.")
    else:
        st.plotly_chart(
            plots.stat_small_multiples(trend_df),
            use_container_width=True, config=PLOTLY_CONFIG,
        )
