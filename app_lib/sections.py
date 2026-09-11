"""Section renderers. Each function reads real artifacts via app_lib.loaders
and displays them. No number here is computed inline or invented -- if a
loader returns None, the section says so instead of showing a placeholder
that looks real.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app_lib import loaders, plots, theme

# Trimmed modebar: zoom/pan/reset are useful in a demo, the rest is noise.
PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
        "hoverClosestCartesian", "hoverCompareCartesian",
    ],
    "displayModeBar": "hover",
}


def render_federation_status() -> None:
    theme.section_header(
        "Overview",
        "Federation Status",
        "Ten simulated organizations, each holding a private, non-IID "
        "partition of corrected CIC-IDS2017. Every figure on this page is "
        "read directly from <code>best_rounds_manifest.json</code> and "
        "<code>configs/data.yaml</code> — nothing is recomputed.",
    )
    theme.rule()

    shape = loaders.get_federation_shape()
    vocab_info = loaders.get_label_vocab()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        theme.stat("Silos", str(shape["n_silos"]), "Simulated organizations", theme.ACCENT)
    with c2:
        theme.stat("Dirichlet α", ", ".join(str(a) for a in shape["alphas"]),
                   "Lower α = more heterogeneous", theme.VIOLET, small=True)
    with c3:
        theme.stat("Seeds", ", ".join(str(s) for s in shape["seeds"]),
                   "Every result indexed by (α, seed)", theme.POSITIVE, small=True)
    with c4:
        theme.stat("Headline families", str(len(vocab_info["headline_classes"])),
                   "Plus 2 below-floor, per-class only", theme.WARN)

    theme.rule()

    theme.subhead(
        "Per-config results",
        "Each row is one (α, seed) federated run. <b>Best Round</b> is the "
        "validation-selected checkpoint actually used — not necessarily the "
        "final round. Selecting on validation rather than test is what keeps "
        "these numbers unbiased.",
    )
    st.write("")
    df = loaders.get_all_manifest_summaries()
    st.dataframe(
        df.rename(
            columns={
                "alpha": "α",
                "seed": "Seed",
                "tag": "Config",
                "best_round": "Best Round (of 20)",
                "val_macro_f1_headline": "Val Macro-F1 (headline)",
                "test_macro_f1_headline": "Test Macro-F1 (headline)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    theme.rule()

    theme.subhead("Headline taxonomy")
    st.write("")
    st.markdown(
        f'<div style="color:{theme.TEXT_MUTED};font-size:0.86rem;'
        f'margin-bottom:0.5rem">Headline macro-F1 families '
        f'({len(vocab_info["headline_classes"])})</div>',
        unsafe_allow_html=True,
    )
    theme.pills([(f, theme.family_color(f)) for f in vocab_info["headline_classes"]])
    st.write("")
    st.markdown(
        f'<div style="color:{theme.TEXT_MUTED};font-size:0.86rem;'
        f'margin-bottom:0.5rem">Below the 1,000-flow floor — reported '
        f'per-class only, excluded from headline macro-F1</div>',
        unsafe_allow_html=True,
    )
    theme.pills([(f, theme.TEXT_FAINT) for f in vocab_info["below_floor_classes"]])

    theme.rule()

    theme.subhead(
        "Silo size floor",
        f"Independent of the per-family rule below: a silo whose <b>total</b> "
        f"flow count across every family falls under "
        f"{loaders.SILO_TOTAL_MIN_FLOWS} is excluded here. This is the source "
        f"of the 1-of-90 figure.",
    )
    st.write("")
    silo_total = loaders.get_silo_total_eligibility()
    if silo_total is None:
        st.warning("results/inspection/silo_sizes.csv not found — cannot compute this.")
    else:
        cc1, cc2 = st.columns([1, 2])
        with cc1:
            theme.stat("Excluded on total size",
                       f"{silo_total['n_excluded']} / {silo_total['n_total']}",
                       f"Floor: {loaders.SILO_TOTAL_MIN_FLOWS} flows", theme.WARN)
        with cc2:
            theme.stat("Silos training", f"{silo_total['n_total']}",
                       "All silos train regardless of size — exclusion applies "
                       "only to explanation analysis (locked decision 5)",
                       theme.POSITIVE)
        if silo_total["n_excluded"] > 0:
            with st.expander("Excluded silo(s) (detail)"):
                st.dataframe(
                    silo_total["excluded_detail"],
                    use_container_width=True,
                    hide_index=True,
                )

    theme.rule()

    theme.subhead("Explanation-eligibility (per family)")
    st.caption(
        f"A silo counts as eligible for a family if it has ≥"
        f"{loaders.SILO_FAMILY_MIN_FLOWS} flows of that family. A family is "
        f"included in cross-silo explanation-agreement analysis for a given "
        f"(α, seed) only if ≥{loaders.FAMILY_MIN_ELIGIBLE_SILOS} silos clear "
        f"that bar. Computed live from silo_sizes.csv — not a separate "
        f"stored artifact."
    )
    eligibility = loaders.get_eligibility_summary()
    if eligibility is None:
        st.warning("results/inspection/silo_sizes.csv not found — cannot compute eligibility.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            theme.stat("Excluded combinations",
                       f"{eligibility['n_excluded']} / {eligibility['n_total']}",
                       "(family, α, seed) triples below the bar", theme.WARN)
        with c2:
            theme.stat("Eligibility rule",
                       f"≥{loaders.SILO_FAMILY_MIN_FLOWS} flows · "
                       f"≥{loaders.FAMILY_MIN_ELIGIBLE_SILOS} silos",
                       "Per family, per (α, seed)", theme.ACCENT, small=True)

        with st.expander("Full eligibility matrix"):
            st.dataframe(
                eligibility["matrix"].rename(
                    columns={
                        "alpha": "α",
                        "seed": "Seed",
                        "family": "Family",
                        "eligible_silos": "Eligible Silos (of 10)",
                        "family_included": "Included in Agreement Analysis",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        if eligibility["n_excluded"] > 0:
            with st.expander("Excluded combinations (detail)"):
                st.dataframe(
                    eligibility["excluded_detail"],
                    use_container_width=True,
                    hide_index=True,
                )

    silo_sizes = loaders.get_silo_sizes()
    if silo_sizes is not None:
        theme.rule()
        theme.subhead(
            "Label skew across silos",
            "Flow counts per silo per family, log-scaled. This is what "
            "Dirichlet α actually does to the data — at α=0.1 a silo may hold "
            "almost none of a family the next silo is saturated with.",
        )
        st.write("")
        h1, h2, _ = st.columns([1, 1, 2])
        with h1:
            hm_alpha = st.selectbox("α", sorted(silo_sizes["alpha"].unique()), key="hm_a")
        with h2:
            hm_seed = st.selectbox("Seed", sorted(silo_sizes["seed"].unique()), key="hm_s")
        st.plotly_chart(
            plots.silo_heatmap(silo_sizes, hm_alpha, hm_seed),
            use_container_width=True, config=PLOTLY_CONFIG,
        )
        with st.expander("Silo sizes (raw table)"):
            st.dataframe(silo_sizes, use_container_width=True, hide_index=True)
    else:
        st.caption("results/inspection/silo_sizes.csv not found — skipping.")



def _render_prediction_result(model, x_scaled, vocab_info, true_name: str | None) -> None:
    """Shared prediction display for both input modes."""
    probs = loaders.predict_row(model, x_scaled)
    pred_idx = int(np.argmax(probs))
    pred_name = vocab_info["idx_to_name"][pred_idx]
    confidence = float(probs[pred_idx])
    tier = "High" if confidence >= 0.9 else "Medium" if confidence >= 0.6 else "Low"
    tone = theme.family_color(pred_name)

    if true_name is None:
        meta = (f"Confidence <b>{confidence:.1%}</b> · {tier} · "
                f"no ground-truth label for a custom flow")
    else:
        hit = pred_name == true_name
        mark = "✓ matches" if hit else "✗ differs from"
        meta = (f"Confidence <b>{confidence:.1%}</b> · {tier} · "
                f"{mark} true label <b>{true_name}</b>")
        if not hit:
            tone = theme.WARN
    theme.verdict(pred_name, meta, tone)

    st.write("")
    st.markdown(
        f'<div style="color:{theme.TEXT_FAINT};font-size:0.72rem;'
        f'font-weight:600;letter-spacing:0.07em;text-transform:uppercase;'
        f'margin-bottom:0.3rem">Class confidence</div>',
        unsafe_allow_html=True,
    )

    names = [vocab_info["idx_to_name"][i] for i in range(vocab_info["n_classes"])]
    st.plotly_chart(
        plots.class_confidence(names, probs),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )


def render_detect() -> None:
    theme.section_header(
        "Inference",
        "Detect",
        "Every prediction here — centralized or federated — is scaled with "
        "the same centralized scaler <code>server_app.py</code> uses to "
        "score the global model each round. Confirmed against that file, "
        "not assumed.",
    )
    theme.rule()

    vocab_info = loaders.get_label_vocab()
    models = loaders.get_available_models()
    model_labels = [m["label"] for m in models]

    left, right = st.columns([1, 1.3])

    with left:
        theme.subhead("Input")
        st.write("")
        model_choice = st.selectbox("Model", model_labels)
        model_info = models[model_labels.index(model_choice)]

        mode = st.radio(
            "Flow source",
            ["Preset evaluation row", "Custom flow"],
            help="Preset rows are the fixed 14 that also have precomputed "
            "SHAP artifacts, so they can be explained in the Explain "
            "section. Custom flows can be predicted but not explained.",
        )

        if model_info["kind"] == "centralized":
            model = loaders.load_centralized_model(model_info["identifier"])
        else:
            model, _entry = loaders.load_global_model_for_config(model_info["identifier"])

    if mode == "Preset evaluation row":
        X_raw, y_true, families = loaders.get_fixed_eval_rows()
        X_scaled = loaders.scale_with_centralized_scaler(X_raw)

        row_labels = []
        seen: dict[str, int] = {}
        for fam in families:
            seen[fam] = seen.get(fam, 0) + 1
            row_labels.append(f"{fam} — sample {seen[fam]}")

        with left:
            row_choice = st.selectbox("Evaluation row", row_labels)
            row_idx = row_labels.index(row_choice)
            st.caption(f"True label: **{families[row_idx]}**")
            st.caption(
                "These 14 rows are fixed and reused everywhere in the app — "
                "the same ones behind every SHAP explanation in Explain."
            )

        with right:
            theme.subhead("Prediction")
            st.write("")
            _render_prediction_result(model, X_scaled[row_idx], vocab_info, families[row_idx])

    else:
        with left:
            st.caption(
                "Paste 82 comma- or space-separated raw feature values, or "
                "upload a one-row CSV. Values must be **unscaled** — the "
                "app applies the training scaler itself."
            )
            uploaded = st.file_uploader("Upload a one-row CSV", type=["csv"])
            pasted = st.text_area("…or paste 82 values", height=110, placeholder="0, 1234, 5, 3, ...")

            with st.expander("Need a template?"):
                st.caption(
                    "Copy this correctly-shaped row (it's eval row 1) and "
                    "edit the values."
                )
                st.code(loaders.get_eval_row_as_csv_text(0), language="text")

        with right:
            theme.subhead("Prediction")
            st.write("")
            theme.callout(
                "<b>Prediction only — no explanation for custom flows.</b> "
                "SHAP explanations come from precomputed artifacts covering "
                "the fixed 14 evaluation rows. An arbitrary flow has no "
                "stored explanation, and this app never computes one on "
                "demand. Use a preset row if you need the explanation too.",
                theme.WARN,
            )

            uploaded_df = None
            if uploaded is not None:
                try:
                    uploaded_df = pd.read_csv(uploaded)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not read that CSV: {exc}")

            if uploaded_df is not None or (pasted and pasted.strip()):
                try:
                    row_raw = loaders.parse_arbitrary_flow(pasted, uploaded_df)
                except loaders.FlowParseError as exc:
                    st.error(str(exc))
                else:
                    x_scaled = loaders.scale_with_centralized_scaler(row_raw[None, :])[0]
                    _render_prediction_result(model, x_scaled, vocab_info, None)
            else:
                st.caption("Waiting for input.")


def render_explain() -> None:
    theme.section_header(
        "Attribution",
        "Explain",
        "SHAP contributions for a row from the fixed 14, read from the "
        "precomputed <code>.npz</code> artifacts. Only the base value is "
        "computed live — the background's mean logit, used by both pipelines "
        "for their additivity checks but never persisted. Values are in "
        "<b>logit space</b>, the space SHAP explains for this model — not "
        "probabilities.",
    )
    theme.rule()

    vocab_info = loaders.get_label_vocab()
    X_raw, y_true, families = loaders.get_fixed_eval_rows()
    feature_cols = loaders.get_feature_cols()

    row_labels = []
    seen: dict[str, int] = {}
    for fam in families:
        seen[fam] = seen.get(fam, 0) + 1
        row_labels.append(f"{fam} — sample {seen[fam]}")

    models = loaders.get_available_models()
    model_labels = [m["label"] for m in models]

    left, right = st.columns([1, 1.6])

    with left:
        theme.subhead("Input")
        st.write("")
        model_choice = st.selectbox("Model", model_labels, key="explain_model")
        model_info = models[model_labels.index(model_choice)]

        silo_choice = None
        if model_info["kind"] == "federated":
            entry = loaders.get_manifest_entry(model_info["identifier"])
            silo_options = ["Global model"] + [f"Silo {i}" for i in range(10)]
            silo_pick = st.selectbox(
                "Scope",
                silo_options,
                help="Global model uses the pooled centralized background "
                "(seed 777). Each silo uses its own local training data "
                "and its own scaler — confirmed from "
                "tools/local_shap_pipeline.py.",
            )
            if silo_pick != "Global model":
                silo_choice = int(silo_pick.split()[1])

        row_choice = st.selectbox("Evaluation row", row_labels, key="explain_row")
        row_idx = row_labels.index(row_choice)
        true_name = families[row_idx]
        st.caption(f"True label: **{true_name}**")

        # --- resolve model, scaled eval rows, shap file, background -------
        if model_info["kind"] == "centralized":
            seed = model_info["identifier"]
            model = loaders.load_centralized_model(seed)
            X_scaled = loaders.scale_with_centralized_scaler(X_raw)
            shap_data = loaders.load_centralized_shap(seed)
            with st.spinner("Loading background (first time only, cached after)..."):
                background = loaders.get_centralized_background(seed)

        else:
            tag = model_info["identifier"]
            entry = loaders.get_manifest_entry(tag)
            alpha, seed = entry["alpha"], entry["seed"]

            if silo_choice is None:
                model, _entry = loaders.load_global_model_for_config(tag)
                X_scaled = loaders.scale_with_centralized_scaler(X_raw)
                shap_data = loaders.load_federated_shap(tag, None)
                with st.spinner("Loading background (first time only, cached after)..."):
                    background = loaders.get_federated_global_background()
            else:
                model = loaders.load_silo_model_for_config(tag, silo_choice)
                X_scaled = loaders.scale_with_silo_scaler(X_raw, silo_choice, alpha, seed)
                shap_data = loaders.load_federated_shap(tag, silo_choice)
                with st.spinner("Loading silo background (first time only, cached after)..."):
                    background = loaders.get_federated_silo_background(silo_choice, alpha, seed)

        pred_probs = loaders.predict_row(model, X_scaled[row_idx])
        pred_idx = int(np.argmax(pred_probs))
        pred_name = vocab_info["idx_to_name"][pred_idx]
        true_idx = int(vocab_info["vocab"][true_name])

        explain_true = st.checkbox(
            f"Explain the TRUE class ({true_name}) instead of the "
            f"predicted class ({pred_name})",
            value=False,
        )
        class_idx = true_idx if explain_true else pred_idx
        class_name = true_name if explain_true else pred_name

        st.caption(
            "Reported agreement metrics (Jaccard@k, Kendall's τ) elsewhere "
            "in the project are computed relative to the TRUE class, for a "
            "stable ground truth across seeds and silos. This view "
            "defaults to the PREDICTED class instead — flip the box above "
            "to match the reported methodology exactly."
        )

        bg_sub = (f"Background: {shap_data['background_size']} rows"
                  if "background_size" in shap_data else "0 = perfect reconstruction")
        theme.stat("Additivity residual",
                   f"{shap_data['additivity_max_diff']:.3f}", bg_sub, theme.WARN)

    with right:
        theme.subhead(f"Why “{class_name}”?")
        st.write("")

        base_values = loaders.get_base_values(model, background)
        base_value = float(base_values[class_idx])

        sv_row = shap_data["shap_values"][row_idx, :, class_idx]  # (82,)
        order = np.argsort(-np.abs(sv_row))
        top_k = 10
        top_idx = order[:top_k]
        rest_sum = float(sv_row[order[top_k:]].sum())

        chart_names = [feature_cols[i] for i in top_idx] + [
            f"Other {len(feature_cols) - top_k} features (sum)"
        ]
        chart_vals = list(sv_row[top_idx]) + [rest_sum]

        st.caption(
            f"Base value (background mean logit for '{class_name}'): "
            f"**{base_value:+.3f}**  →  reconstructed model output for "
            f"this row: **{base_value + sv_row.sum():+.3f}**"
        )

        raw_row = X_raw[row_idx]
        chart_raw = [float(raw_row[i]) for i in top_idx] + [None]
        st.plotly_chart(
            plots.shap_contributions(chart_names, chart_vals, chart_raw),
            use_container_width=True,
            config=PLOTLY_CONFIG,
        )
        theme.pills([("↑ pushes toward this class", theme.ALERT),
                     ("↓ pushes away", theme.ACCENT)])
        st.write("")

        with st.expander("Raw feature values (top 10)"):
            raw_row = X_raw[row_idx]
            detail = pd.DataFrame(
                {
                    "Feature": [feature_cols[i] for i in top_idx],
                    "Raw value": [raw_row[i] for i in top_idx],
                    "SHAP contribution (logit)": [sv_row[i] for i in top_idx],
                }
            )
            st.dataframe(detail, use_container_width=True, hide_index=True)


def render_agreement() -> None:
    theme.section_header(
        "Core contribution",
        "Explanation Agreement",
        "<b>Accuracy parity between silos does not imply explanation "
        "parity.</b> Two silos can agree on <i>what</i> a flow is and "
        "disagree on <i>why</i>. Measured as agreement between each silo's "
        "local SHAP ranking and the global model's, over "
        "<code>agreement_metrics.csv</code>. Median over eligible rows — "
        "the aggregation confirmed to reproduce the project's stated "
        "figures to six decimal places.",
    )
    theme.rule()

    headline = loaders.get_headline_agreement()
    per_seed = loaders.get_per_seed_agreement()
    alphas = headline["alpha"].tolist()
    alpha_labels = [f"α={a:g}" for a in alphas]
    x_pos = np.arange(len(alphas))

    theme.subhead(
        "Agreement vs. heterogeneity",
        "Lower α means more heterogeneous silos. The shaded band is the "
        "25th–75th percentile across all eligible (silo, sample) pairs — a "
        "real spread from the data, <b>not</b> a fitted confidence interval. "
        "White dots are per-seed medians.",
    )
    st.write("")

    j_lo = float(headline["jaccard_at_10_median"].iloc[0])
    j_hi = float(headline["jaccard_at_10_median"].iloc[-1])
    t_lo = float(headline["tau_median"].iloc[0])
    t_hi = float(headline["tau_median"].iloc[-1])
    s1, s2, s3 = st.columns(3)
    with s1:
        theme.stat("Jaccard@10 range", f"{j_lo:.3f} → {j_hi:.3f}",
                   "α = 0.1 → 5.0", theme.ACCENT, small=True)
    with s2:
        theme.stat("Weighted τ range", f"{t_lo:.3f} → {t_hi:.3f}",
                   "α = 0.1 → 5.0", theme.VIOLET, small=True)
    with s3:
        theme.stat("Above chance", f"{j_lo / loaders.CHANCE_LEVEL_JACCARD_AT_10:.1f}× – "
                   f"{j_hi / loaders.CHANCE_LEVEL_JACCARD_AT_10:.1f}×",
                   f"Chance Jaccard@10 ≈ {loaders.CHANCE_LEVEL_JACCARD_AT_10:.3f}",
                   theme.POSITIVE, small=True)
    st.write("")

    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(
            plots.agreement_vs_alpha(
                alphas,
                headline["jaccard_at_10_median"].tolist(),
                headline["jaccard_at_10_q25"].tolist(),
                headline["jaccard_at_10_q75"].tolist(),
                per_seed, "jaccard_at_10_median",
                "Jaccard@10", loaders.CHANCE_LEVEL_JACCARD_AT_10,
            ),
            use_container_width=True, config=PLOTLY_CONFIG,
        )
    with g2:
        st.plotly_chart(
            plots.agreement_vs_alpha(
                alphas,
                headline["tau_median"].tolist(),
                headline["tau_q25"].tolist(),
                headline["tau_q75"].tolist(),
                per_seed, "tau_median",
                "Weighted Kendall's τ", None,
            ),
            use_container_width=True, config=PLOTLY_CONFIG,
        )

    theme.rule()
    theme.subhead("Headline numbers")
    st.write("")
    display = headline.copy()
    display["Jaccard@10 (median)"] = display["jaccard_at_10_median"].map("{:.3f}".format)
    display["Jaccard@10 IQR"] = (
        display["jaccard_at_10_q25"].map("{:.3f}".format)
        + " – "
        + display["jaccard_at_10_q75"].map("{:.3f}".format)
    )
    display["Weighted τ (median)"] = display["tau_median"].map("{:.3f}".format)
    display["Weighted τ IQR"] = (
        display["tau_q25"].map("{:.3f}".format) + " – " + display["tau_q75"].map("{:.3f}".format)
    )
    display["α"] = display["alpha"]
    display["Eligible rows"] = display["n_rows"]
    st.dataframe(
        display[
            ["α", "Jaccard@10 (median)", "Jaccard@10 IQR",
             "Weighted τ (median)", "Weighted τ IQR", "Eligible rows"]
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"Chance-level Jaccard@10 ≈ {loaders.CHANCE_LEVEL_JACCARD_AT_10:.3f} "
        f"(random top-10 overlap out of 82 features). Even at α=0.1, "
        f"agreement sits {headline['jaccard_at_10_median'].iloc[0] / loaders.CHANCE_LEVEL_JACCARD_AT_10:.1f}× "
        f"above chance — silos disagree relative to α=5.0, but not "
        f"randomly."
    )

    theme.rule()

    theme.subhead("Per-family breakdown")
    st.write("")
    theme.callout(
        "<b>PortScan is the family that actually tests explanation "
        "generalization.</b> Bot and WebAttack are flagged: a "
        "nearest-neighbour audit found near-zero train/test distance for "
        "those families, so high agreement there may reflect near-duplicate "
        "rows rather than genuine model fidelity. Reported, not suppressed.",
        theme.WARN,
    )
    st.write("")

    per_family = loaders.get_per_family_agreement()

    fam_tab1, fam_tab2 = st.tabs(["Jaccard@10", "Weighted τ"])
    with fam_tab1:
        st.plotly_chart(
            plots.per_family_grouped(per_family, "jaccard_at_10_median",
                                     "Median Jaccard@10 by family"),
            use_container_width=True, config=PLOTLY_CONFIG,
        )
    with fam_tab2:
        st.plotly_chart(
            plots.per_family_grouped(per_family, "tau_median",
                                     "Median weighted τ by family"),
            use_container_width=True, config=PLOTLY_CONFIG,
        )
    st.write("")

    caveat_families = {"Bot", "WebAttack"}
    per_family_display = per_family.copy()
    per_family_display["Jaccard@10 (median)"] = per_family_display["jaccard_at_10_median"].map("{:.3f}".format)
    per_family_display["Weighted τ (median)"] = per_family_display["tau_median"].map("{:.3f}".format)
    per_family_display["Note"] = per_family_display["family"].apply(
        lambda f: "⚠️ near-duplicate caveat" if f in caveat_families
        else ("✅ generalization signal" if f == "PortScan" else "")
    )
    per_family_display["α"] = per_family_display["alpha"]
    per_family_display["Family"] = per_family_display["family"]
    per_family_display["Eligible rows"] = per_family_display["n_rows"]
    st.dataframe(
        per_family_display[
            ["α", "Family", "Jaccard@10 (median)", "Weighted τ (median)", "Eligible rows", "Note"]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_faithfulness() -> None:
    theme.section_header(
        "Validation",
        "Faithfulness",
        "A faithful explanation should make confidence <b>collapse</b> as "
        "top-ranked features are deleted, and <b>recover</b> as they are "
        "reinserted. This is what stops the agreement result from being two "
        "possibly-wrong explainers agreeing with each other.",
    )
    theme.rule()
    theme.callout(
        f"<b>Scope:</b> computed for one config only "
        f"({loaders.FAITHFULNESS_CONFIG_LABEL}) and four models "
        f"(global + silos 0–2). A project-scope decision, not a limitation "
        f"of this app.",
        theme.VIOLET,
    )
    st.write("")

    data = loaders.load_faithfulness_auc()
    if data is None:
        st.warning(
            "results/inspection/deletion_auc.csv or insertion_auc.csv not found."
        )
        return

    table = data["table"]

    theme.subhead("AUC summary")
    st.write("")
    theme.pills([("↓ lower deletion AUC is better", theme.ALERT),
                 ("↑ higher insertion AUC is better", theme.POSITIVE)])
    st.write("")

    display = table.copy()
    display["Model"] = display["model"].apply(
        lambda m: "Global model" if m == "global" else m.replace("silo_", "Silo ")
    )
    display["Deletion AUC (lower = better)"] = display["deletion_auc"].map("{:.3f}".format)
    display["Insertion AUC (higher = better)"] = display["insertion_auc"].map("{:.3f}".format)
    st.dataframe(
        display[["Model", "Deletion AUC (lower = better)", "Insertion AUC (higher = better)"]],
        use_container_width=True,
        hide_index=True,
    )

    st.plotly_chart(
        plots.faithfulness_auc(
            display["Model"].tolist(),
            table["deletion_auc"].tolist(),
            table["insertion_auc"].tolist(),
        ),
        use_container_width=True, config=PLOTLY_CONFIG,
    )

    theme.rule()

    theme.subhead("Curve shape")
    st.caption(
        "No per-step data was persisted alongside the AUC summary above — "
        "only the final area-under-curve numbers. These are the "
        "precomputed curve images from the original run, embedded as-is "
        "rather than redrawn from a single number. Check legibility on a "
        "projector before the review — these were sized for a report "
        "page, not a demo screen."
    )
    for kind, title in [("deletion", "Deletion curve"), ("insertion", "Insertion curve")]:
        path = loaders.get_faithfulness_figure_path(kind)
        if path is not None:
            st.image(str(path), caption=title, use_container_width=True)
        else:
            st.caption(f"results/figures/{kind}_curve.png not found — skipping.")


def render_methods() -> None:
    theme.section_header(
        "Disclosure",
        "Methods &amp; Limits",
        "Stated up front, not buried in an appendix. Everything below is "
        "either computed live from a real artifact or a documented "
        "limitation from the project record. Nothing here is a placeholder.",
    )
    theme.rule()

    theme.subhead("Is the α=0.1 agreement drop real, or seed noise?")
    st.write("")
    floor = loaders.get_instability_floor_summary()
    headline = loaders.get_headline_agreement()
    if floor is None:
        st.warning("results/inspection/centralized_instability_floor.csv not found.")
    else:
        alpha01 = headline[headline["alpha"] == 0.1]
        if len(alpha01):
            a01_jaccard = float(alpha01["jaccard_at_10_median"].iloc[0])
            a01_lo = float(alpha01["jaccard_at_10_q25"].iloc[0])
            a01_hi = float(alpha01["jaccard_at_10_q75"].iloc[0])

            c1, c2 = st.columns(2)
            with c1:
                theme.stat("Instability floor — Jaccard@10",
                           f"{floor['jaccard_at_10_median']:.3f}",
                           "Centralized seed-pairs, no federation involved",
                           theme.ALERT)
            with c2:
                theme.stat("Federated agreement — Jaccard@10",
                           f"{a01_jaccard:.3f}", "α = 0.1", theme.ACCENT)
            st.write("")

            st.plotly_chart(
                plots.floor_comparison(
                    ["Instability floor<br>(centralized seed-pairs)", "Federated α=0.1"],
                    [floor["jaccard_at_10_median"], a01_jaccard],
                    [floor["jaccard_at_10_q25"], a01_lo],
                    [floor["jaccard_at_10_q75"], a01_hi],
                ),
                use_container_width=True, config=PLOTLY_CONFIG,
            )

            theme.callout(
                "<b>Directional observation, not a statistical test.</b> The "
                "IQR bands above overlap — federated α=0.1 agreement sits "
                "close to, not clearly below, the seed-to-seed instability "
                "floor measured from centralized models alone. No "
                "significance test has been run. Reported as directional, "
                "never claimed as significant.",
                theme.WARN,
            )
        else:
            st.info("No α=0.1 rows found in the headline agreement table.")

    theme.rule()

    theme.subhead("Round-lottery gap")
    st.write("")
    st.caption(
        "FedAvg's global macro-F1 can swing substantially between "
        "consecutive late rounds under non-IID partitioning — this is why "
        "every reported number uses the validation-selected round, never "
        "just whatever round training happened to stop on. Computed live "
        "per config from final_metrics.json, across all 9 configs, not a "
        "single historical example."
    )
    lottery = loaders.get_round_lottery_table()
    if lottery is None:
        st.warning("No final_metrics.json files found under results/federated/.")
    else:
        display = lottery.copy()
        display["α"] = display["alpha"]
        display["Seed"] = display["seed"]
        display["Best Round"] = display["best_round"]
        display["Best-Round Test F1"] = display["best_round_test_f1"].map("{:.4f}".format)
        display["Final-Round Test F1"] = display["final_round_test_f1"].map("{:.4f}".format)
        display["Gap"] = display["gap"].map("{:+.4f}".format)
        st.dataframe(
            display[
                ["α", "Seed", "Best Round", "Best-Round Test F1", "Final-Round Test F1", "Gap"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        max_gap = lottery["gap"].abs().max()
        st.caption(f"Largest observed gap across all 9 configs: {max_gap:.4f}.")

    theme.rule()

    theme.subhead("Other validation artifacts")
    st.write("")
    for fname, desc in [
        (
            "common_background_ablation.csv",
            "Shared background vs. per-silo background — checks whether "
            "cross-silo disagreement is a background-sampling artifact "
            "rather than a genuine model difference.",
        ),
        (
            "kernel_vs_gradient_validation.csv",
            "KernelExplainer vs. GradientExplainer spot-check — confirms "
            "GradientExplainer's rankings aren't an artifact of the "
            "explainer choice.",
        ),
    ]:
        df = loaders.load_raw_inspection_csv(fname)
        st.markdown(f"**{fname}** — {desc}")
        if df is None:
            st.caption(f"results/inspection/{fname} not found — skipping.")
        else:
            with st.expander(f"View {fname}"):
                st.dataframe(df, use_container_width=True, hide_index=True)

    theme.rule()

    theme.subhead("Known limitations")
    st.caption(
        "The consolidated, canonical version of this list — merged with "
        "PROJECT_INSTRUCTIONS.md and docs/measurement_protocol.md §10, plus "
        "newer items (unseeded SHAP Monte Carlo noise, silo non-independence, "
        "n=3 seeds as a ceiling, the FedProx μ=0.0005 single-point caveat) — "
        "lives in docs/contribution_a_results.md. This panel defers to it."
    )
    st.write("")
    st.markdown(
        "- **RobustScaler degenerates on this data.** 28 of 82 features "
        "have zero IQR; RobustScaler collapses their transform to "
        "centering-only, which measurably hurt DDoS F1 (0.716 vs. 1.000 "
        "under StandardScaler in pilot experiments). StandardScaler is "
        "locked for this reason — see `results/centralized/"
        "pilot_scaler_robust/` vs `pilot_scaler_standard/` for the raw "
        "pilot metrics.\n"
        "- **Bot and WebAttack agreement may reflect near-duplication, "
        "not fidelity.** A nearest-neighbor audit found train/test rows "
        "for these families are nearly identical, so high cross-silo "
        "agreement there could mean two silos are explaining the same "
        "row twice rather than genuinely agreeing. See the per-family "
        "table in Explanation Agreement.\n"
        "- **GradientExplainer's additivity residual is nonzero.** "
        "Typically 0.67–1.31 in logit space for this model (shown live, "
        "per seed, in Explain) — SHAP values plus the base value don't "
        "perfectly reconstruct the model's output. Disclosed, not "
        "hidden.\n"
        "- **Explanations never leave the client in raw form.** Per "
        "locked decision 4, only top-k rankings and magnitude summaries "
        "cross the client→server boundary — this protects the privacy "
        "premise of the whole project, but it also means the server-side "
        "agreement analysis only ever sees a compressed summary of each "
        "silo's explanation, not the full SHAP vector.\n"
        "- **Silo size is not a separate confound — it's a deterministic "
        "function of the label draw.** Under `dirichlet_assign()` "
        "(`src/data/partition.py`), each family's per-silo proportions "
        "are drawn from Dir(α,...,α) over the 10 silos and sum to 1 by "
        "construction, so a silo's total size is `size_i = Σ_family "
        "available_family × p_family[i]` — an output of the same "
        "label-skew draw that determines heterogeneity, not an "
        "independent quantity that happens to correlate with it. The "
        "r=+0.46 (Jaccard@10, α=0.1) correlation with size restates the "
        "label-skew effect rather than identifying a second, separable "
        "cause. Conditioning on log(size), KL divergence from the global "
        "family distribution retains a strong partial correlation with "
        "agreement (partial r=−0.57 at α=0.1; −0.82/−0.87 at α=0.5 for "
        "Jaccard@10/weighted τ, n=29/30) — heterogeneity predicts "
        "agreement independently of size, even though size and "
        "heterogeneity cannot be independently varied by this "
        "partitioner.\n"
        "- **Background substitution is off-manifold.** SHAP's "
        "\"missing feature\" baseline (the background mean) is not a "
        "real network flow — a standard, disclosed limitation of "
        "perturbation-based explainability, not specific to this "
        "project."
    )
