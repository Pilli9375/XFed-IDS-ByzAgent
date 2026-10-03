import { NAV_ICONS } from '../theme/tokens';

// Nav order, section identity, and header copy -- ported verbatim from the
// theme.section_header(eyebrow, title, lede) calls in app_lib/sections.py
// and app_lib/trust_monitor.py. Group 'trust' is the trust check (ByzAgent);
// group 'sections' is everything else. Kept as two visibly separate nav
// groups so the explanation check (explanation parity) and the trust check (trust
// monitor) never read as one narrative -- see PHASE2_OPENING_PROMPT.md's
// hard constraint.
export const SECTIONS = [
  {
    key: 'federation-status',
    path: '/federation-status',
    navLabel: 'Federation Status',
    icon: NAV_ICONS['Federation Status'],
    eyebrow: 'Overview',
    title: 'Federation Status',
    lede:
      'Ten simulated organizations, each holding a private, non-IID partition of ' +
      'corrected CIC-IDS2017. Every figure on this page is read directly from ' +
      '<code>best_rounds_manifest.json</code> and <code>configs/data.yaml</code> — nothing is recomputed.',
    group: 'sections',
  },
  {
    key: 'detect',
    path: '/detect',
    navLabel: 'Detect',
    icon: NAV_ICONS.Detect,
    eyebrow: 'Inference',
    title: 'Detect',
    lede:
      'Every prediction here — centralized or federated — is scaled with the same ' +
      'centralized scaler <code>server_app.py</code> uses to score the global model each ' +
      'round. Confirmed against that file, not assumed.',
    group: 'sections',
  },
  {
    key: 'explain',
    path: '/explain',
    navLabel: 'Explain',
    icon: NAV_ICONS.Explain,
    eyebrow: 'Attribution',
    title: 'Explain',
    lede:
      'SHAP contributions for a row from the fixed 14, read from the precomputed ' +
      '<code>.npz</code> artifacts. Only the base value is computed live — the background’s ' +
      'mean logit, used by both pipelines for their additivity checks but never persisted. ' +
      'Values are in <b>logit space</b>, the space SHAP explains for this model — not probabilities.',
    group: 'sections',
  },
  {
    key: 'explanation-agreement',
    path: '/explanation-agreement',
    navLabel: 'Explanation Agreement',
    icon: NAV_ICONS['Explanation Agreement'],
    eyebrow: 'Core contribution',
    title: 'Explanation Agreement',
    lede:
      '<b>Accuracy parity between silos does not imply explanation parity.</b> Two silos can ' +
      'agree on <i>what</i> a flow is and disagree on <i>why</i>. Measured as agreement between ' +
      'each silo’s local SHAP ranking and the global model’s, over <code>agreement_metrics.csv</code>. ' +
      'Median over eligible rows — the aggregation confirmed to reproduce the project’s stated ' +
      'figures to six decimal places.',
    group: 'sections',
  },
  {
    key: 'faithfulness',
    path: '/faithfulness',
    navLabel: 'Faithfulness',
    icon: NAV_ICONS.Faithfulness,
    eyebrow: 'Validation',
    title: 'Faithfulness',
    lede:
      'A faithful explanation should make confidence <b>collapse</b> as top-ranked features are ' +
      'deleted, and <b>recover</b> as they are reinserted. This is what stops the agreement result ' +
      'from being two possibly-wrong explainers agreeing with each other.',
    group: 'sections',
  },
  {
    key: 'methods-limits',
    path: '/methods-limits',
    navLabel: 'Methods & Limits',
    icon: NAV_ICONS['Methods & Limits'],
    eyebrow: 'Disclosure',
    // Plain '&', not the '&amp;' entity theme.py's Python source uses --
    // that file feeds it through st.markdown(unsafe_allow_html=True); here
    // it's plain JSX text content (see SectionHeader), which renders '&'
    // correctly without an entity.
    title: 'Methods & Limits',
    lede:
      'Stated up front, not buried in an appendix. Everything below is either computed live ' +
      'from a real artifact or a documented limitation from the project record. Nothing here ' +
      'is a placeholder.',
    group: 'sections',
  },
  {
    key: 'client-trust-monitor',
    path: '/client-trust-monitor',
    navLabel: 'Client Trust Monitor',
    icon: NAV_ICONS['Client Trust Monitor'],
    eyebrow: 'Trust check (ByzAgent)',
    title: 'Client Trust Monitor',
    lede:
      'ByzAgent’s per-round trust decisions (trust / downweight / quarantine) for each of the ' +
      '10 federation silos, read directly from <code>agent_decisions*.jsonl</code> and ' +
      '<code>client_stats.jsonl</code> already on disk. Nothing on this page is retrained or recomputed.',
    group: 'trust',
  },
  {
    key: 'alert-stream',
    path: '/alert-stream',
    navLabel: 'Alert Stream',
    icon: NAV_ICONS['Alert Stream'],
    eyebrow: 'Analyst tools',
    title: 'Alert Stream',
    lede:
      'Alerts recorded by the traffic simulator, which replays held-out test flows through the ' +
      'live model. Open an alert to see its precomputed SHAP explanation, when one exists — ' +
      'a small fixed subset of streamed rows has one, the rest do not, and nothing is computed ' +
      'on demand. An operational view: <b>not</b> a result of either research contribution.',
    group: 'analyst',
  },
];
