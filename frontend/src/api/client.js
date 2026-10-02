// Thin fetch wrappers over the FastAPI backend, routed through Vite's /api
// proxy (see vite.config.js) so the browser never needs CORS to reach
// http://127.0.0.1:8000 directly. Only /health and /config are needed for
// the app shell -- other endpoints get their own wrapper here when the
// section that reads them is built.

const BASE = '/api';

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

export function getHealth() {
  return getJSON('/health');
}

export function getConfig() {
  return getJSON('/config');
}

// { agreement_metrics, per_silo_agreement, round_wise_agreement,
//   centralized_instability_floor } -- raw row-level records, exactly the
// four CSVs cached at backend startup (see backend/main.py's _load_cached_endpoints).
// Aggregation (median/IQR per alpha) happens client-side in lib/agreement.js.
export function getAgreement() {
  return getJSON('/agreement');
}

// { conditions, excluded_conditions, decision_variance, nondeterminism_notice }
// -- see backend/trust.py's build_trust_snapshot(). `conditions` only ever
// contains clean+attack PAIRS (backend enforces this, moving anything
// unpaired to excluded_conditions with a reason); there is no code path
// here that can request a bare "clean" condition.
export function getTrust() {
  return getJSON('/trust');
}

// { shape, label_vocab, manifest_summaries, silo_total_eligibility,
//   family_eligibility, silo_sizes } -- see backend Step 6.
export function getFederation() {
  return getJSON('/federation');
}

// { config_label, auc: [{model, deletion_auc, insertion_auc}, ...4 rows] }
// -- see backend Step 6. The two curve images are static PNGs served at
// /faithfulness/deletion_curve.png and /insertion_curve.png (through the
// /api proxy); no per-step data exists to redraw them as charts.
export function getFaithfulness() {
  return getJSON('/faithfulness');
}

// { sample_id, tag, eval_family, feature_names, class_names, shap_values,
//   raw_values, base_values, additivity_max_diff } -- sample_id in [0,13] only.
export function getShap(sampleId) {
  return getJSON(`/shap/${sampleId}`);
}

// POST /predict. record_alert is never sent -- omitting it relies on the
// backend's own default (false); the frontend must never set it true (only
// backend/simulator.py does). trueFamily is optional and never touches the
// model -- it only lets a returned alert carry ground truth, which this
// frontend doesn't use since record_alert is always false here.
export async function postPredict(features, trueFamily) {
  const res = await fetch(`${BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ features, true_family: trueFamily ?? null }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST /predict -> HTTP ${res.status}: ${detail}`);
  }
  return res.json();
}

// Step 2B. { job_id, status, detail, hotswap: { active, event_id, swap_depth,
// base_tag, job_status, job_detail } } -- same `hotswap` shape GET /config
// carries, plus the current job's own id/status/detail. Polled, not fetched
// once: a swap can complete while the dashboard is already open.
export function getHotswapStatus() {
  return getJSON('/hotswap/status');
}

// Body is a family label only -- see backend/hotswap_service.py's docstring
// for why this can never be a feature vector. Returns immediately with
// status: "running"; poll getHotswapStatus() for the outcome.
export async function postHotswapTrigger(family) {
  const res = await fetch(`${BASE}/hotswap/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ family }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST /hotswap/trigger -> HTTP ${res.status}: ${detail}`);
  }
  return res.json();
}

// One call, no body -- reloads nothing from disk (the base model was never
// touched by a swap), just stops routing /predict to the swapped-in model.
export async function postHotswapRevert() {
  const res = await fetch(`${BASE}/hotswap/revert`, { method: 'POST' });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST /hotswap/revert -> HTTP ${res.status}: ${detail}`);
  }
  return res.json();
}

// Newest-first ring buffer of recorded alerts: [{ timestamp, predicted_family,
// confidence, true_family, shap_available, shap_sample_id }]. Read-only --
// nothing in this frontend ever sets record_alert.
export function getAlerts() {
  return getJSON('/alerts');
}

// Precomputed one-sentence analyst aid for a row in the precomputed SHAP set
// (curated + streamed pool). 404 outside that set -- callers only ask when
// an alert says shap_available.
export function getExplain(sampleId) {
  return getJSON(`/explain/${sampleId}`);
}
