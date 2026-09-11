// Ports theme.py's render_footer() verbatim -- static attribution text, not
// live data, so it's a plain HTML string rather than JSX-composed markup.
const FOOTER_HTML = `<b>XFed-IDS</b> — Explainable Federated Intrusion Detection with Cross-Domain Generalization &nbsp;·&nbsp; VIT-AP capstone<br>
<b>Data</b> Distrinet corrected CIC-IDS2017 v4 (Liu et al., IEEE CNS 2022; extending Engelen et al., WTMC 2021) &nbsp;·&nbsp; <b>Model</b> XFedMLP [128, 64], LayerNorm, StandardScaler, effective-number weighting β=0.999<br>
<b>Federation</b> Flower · FedAvg · 10 silos · Dirichlet α ∈ {0.1, 0.5, 5.0} × 3 seeds &nbsp;·&nbsp; <b>Explanations</b> SHAP GradientExplainer, client-side<br>
All figures read precomputed artifacts. See <b>Methods &amp; Limits</b> for stated limitations.`;

export default function Footer() {
  return <div className="xf-footer" dangerouslySetInnerHTML={{ __html: FOOTER_HTML }} />;
}
