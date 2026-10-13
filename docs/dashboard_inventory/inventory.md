# Dashboard inventory (backend/ FastAPI + frontend/ React)

> Snapshot of `master` at `6e12776`. Items 5.1 and 5.6–5.10 were addressed
> afterwards on branch `dashboard-fixes`; 5.3–5.5 are left for the redesign.

Read-only inventory. Taken 2026-10-13 on `master` at `6e12776`, clean tree.
No source, config or result file was changed.

**How it was run**, per README §7:

- `uvicorn backend.main:app --port 8000` (xfed env). Startup verification
  passed: val macro-F1 0.9759668074, diff 0.000e+00. The ONNX fp32 engine
  matched torch on all 143,513 validation rows (0 prediction differences).
- `python -m backend.simulator` used the default `source_split: val` at
  1 row/s.
- The frontend ran from the Vite dev server (`react-dashboard` in
  `.claude/launch.json`, port 5173). It proxies `/api` to `:8000`.
- Screenshots: headless Chromium (Playwright from `film/node_modules`),
  1440×900 viewport, `fullPage: true`, saved next to this file. Across the
  whole capture run there were **no** browser console errors or warnings
  and **no** HTTP responses ≥400.

| File | View |
|---|---|
| `01_federation-status.png` | Federation Status |
| `02_detect.png` | Detect (preset row) |
| `03_explain.png` | Explain |
| `04_explanation-agreement.png` | Explanation Agreement (Jaccard@10 tab) |
| `05_faithfulness.png` | Faithfulness |
| `06_methods-limits.png` | Methods & Limits |
| `07_client-trust-monitor.png` | Client Trust Monitor |
| `08_alert-stream.png` | Alert Stream (nothing selected) |
| `09_explanation-agreement_tau-tab.png` | Explanation Agreement, per-family chart on the Weighted τ tab |
| `10_alert-stream_selected.png` | Alert Stream with an alert selected |
| `11_detect_custom-flow.png` | Detect, Custom flow mode |

The PNGs are **not** git-ignored: `.gitignore` only ignores
`results/**/*.png`. They show up as untracked; `.gitignore` was left as is.

---

## 1. Global chrome (on every view)

| Element | Shows | Endpoint | Source on disk | Update | Interaction |
|---|---|---|---|---|---|
| Sidebar nav | 3 groups: *Sections* (6), *Trust check (ByzAgent)* (1), *Analyst tools* (1) | none | `frontend/src/sections/registry.js` | static | route links |
| Sidebar footer (model identity) | tag, α, seed, best round, n_features, n_classes, a green dot if `model_loaded` | `GET /health`, `GET /config` | `configs/backend.yaml` → `best_rounds_manifest.json`, `round_checkpoints/round_018.pt` | once on app mount | none |
| Hot-swap banner (`HotSwapBanner.jsx`, above `<Routes>`) | Hidden unless a swap is active, running, crashed or errored. When active it shows a **Revert to base model** button | `GET /hotswap/status` | in-memory `HotSwapState`. The worker writes `state/hotswap_log/` | **polled every 3 s** | Revert → `POST /hotswap/revert` |
| Footer | static project/model/data blurb | none | `layout/Footer.jsx` | static | none |

---

## 2. Panels by view

### 2.1 Federation Status (`/federation-status`), `01`

All panels come from **`GET /federation`**, fetched once on mount. The
backend builds it once at startup (`backend/federation.py`) through
`app_lib.loaders`, which reads `configs/data.yaml`,
`results/inspection/best_rounds_manifest.json` and
`results/inspection/silo_sizes.csv`.

| Panel | Shows | Interaction |
|---|---|---|
| 4 stat tiles | Silos 10 · α {0.1, 0.5, 5.0} · seeds {42, 1337, 2024} · 7 headline families (+2 below floor) | none |
| Per-config results table | 9 FedAvg runs: best round, val macro-F1 (headline), **test macro-F1 (headline)** | none |
| Headline taxonomy | 7 headline-family pills, 2 below-floor pills | none |
| Silo size floor | 1 / 90 excluded (floor 500 flows); 90 training | expander "Excluded silo(s)" |
| Explanation-eligibility | 22 / 81 excluded (family, α, seed) triples; rule ≥50 flows · ≥4 silos | 2 expanders (full matrix, excluded detail) |
| Label skew heatmap | log-scaled flows per silo × family for one (α, seed) | α and seed dropdowns; expander with the raw silo-sizes table (680 rows) |

### 2.2 Detect (`/detect`), `02`, `11`

| Panel | Shows | Endpoint | Source | Update | Interaction |
|---|---|---|---|---|---|
| Input: preset row | dropdown of the 14 fixed evaluation rows plus their true label | `GET /shap/0..13` (14 parallel calls) | `results/shap/fedavg_a0.5_s42/global_shap.npz` + `eval_rows_sidecar.npz` | once on mount | row dropdown; Preset/Custom radio |
| Input: custom flow | paste 82 values or upload a 1-row CSV; a template expander | none (parsed client-side, `lib/detect.js`) | none | on edit | textarea, file input |
| Prediction verdict + class-confidence bar chart | family, confidence, tier, ✓/✗ against the true label; 9-class softmax | `POST /predict` (`record_alert` false) | served model + refit scaler (in memory) | on every row change or input change | none |

### 2.3 Explain (`/explain`), `03`

| Panel | Shows | Endpoint | Source | Update | Interaction |
|---|---|---|---|---|---|
| Input + additivity tile | the same 14 rows; **additivity residual 1.076** for the curated set | `GET /shap/0..13` | `global_shap.npz` (`additivity_max_diff`, one scalar for all 14 rows) | once | row dropdown; checkbox "Explain the TRUE class" |
| "Why <class>?" | base value → reconstructed logit; top-10 SHAP bars + "Other 72 (sum)"; raw-values expander | `GET /shap/{id}` + `POST /predict` | as above + `eval_rows_sidecar.npz` (`base_values`, `raw_values`) | on row or checkbox change | expander |

### 2.4 Explanation Agreement (`/explanation-agreement`), `04`, `09`

The view uses **`GET /agreement`** once on mount. Aggregation happens
client-side in `lib/agreement.js`. The backend reads
`results/inspection/agreement_metrics.csv` and
`centralized_instability_floor.csv`, plus `per_silo_agreement.csv` and
`round_wise_agreement.csv`, which are **served but unused**. All four come
from `configs/backend.yaml` paths and are cached at startup.

| Panel | Shows | Interaction |
|---|---|---|
| 3 stat tiles | Jaccard@10 0.333 → 0.667 · τ 0.592 → 0.844 · 5.1×–10.3× chance (0.065) | none |
| Two line charts vs α | median, IQR band, per-seed dots, chance line (Jaccard only) | none |
| Headline numbers table | median + IQR per α, eligible rows 220 / 388 / 420 | none |
| Per-family grouped bars + table | 7 families × 3 α; PortScan/Bot/WebAttack notes | **Tabs**: Jaccard@10 / Weighted τ |
| α=0.1 vs instability floor | floor 0.429 vs federated 0.333, horizontal bars with **IQR** whiskers | none |

`CHANCE_LEVEL_JACCARD_AT_10` is a constant in `lib/agreement.js`. No
endpoint serves it.

### 2.5 Faithfulness (`/faithfulness`), `05`

| Panel | Shows | Endpoint | Source | Update |
|---|---|---|---|---|
| Scope callout, AUC table, AUC bar chart | deletion/insertion AUC for global + silos 0–2, α=0.5 s42 | `GET /faithfulness` | `results/inspection/deletion_auc.csv`, `insertion_auc.csv`, read through `app_lib.loaders` | once |
| Two curve images | the original matplotlib PNGs | `GET /faithfulness/deletion_curve.png`, `/insertion_curve.png` | `results/figures/deletion_curve.png`, `insertion_curve.png` (in memory since startup) | once |

No interaction.

### 2.6 Methods & Limits (`/methods-limits`), `06`

Static JSX (`sections/MethodsLimits.jsx`). No endpoint and no interaction.
It has 8 limitation bullets, copied by hand from PROJECT_INSTRUCTIONS.md /
contribution_a_results.md.

### 2.7 Client Trust Monitor (`/client-trust-monitor`), `07`

All panels come from **`GET /trust`**, fetched once on mount. The backend
builds it at startup (`backend/trust.py`) from:

- `results/attacks/<cond>/attack_config.json` (true malicious silos)
- `results/federated/<run>/agent_decisions*.jsonl` and `client_stats.jsonl`,
  for each clean run and each attack run
- `results/inspection/phase3_gate_analysis_a0.5_s42.json` and
  `phase4_gate_analysis_a0.5_s42.json` (decision variance)

| Panel | Shows | Interaction |
|---|---|---|
| Framing callout + "oracle asymmetry" expander | static text | expander |
| Attack-condition selector | **5 paired conditions**; 1 excluded (`a0.5_s42_f3_sudden`, no agent-decision log), with the reason shown verbatim | dropdown (drives every panel below) |
| Ground truth pills | malicious vs clean silos | none |
| Per-round decision grids | attack grid and clean grid side by side, 10 silos × 20 rounds, trust/downweight/quarantine | none |
| Clean-vs-attack flag rate + lift | dot/diamond chart + table per silo | none |
| Explanation for one decision | LLM rationale text for both runs + the nondeterminism notice | silo + round dropdowns |
| Behavioral stat trend | 5 small multiples (update_norm, cos→global, cos→peer, train_loss, val_accuracy), clean vs attack | silo dropdown |
| Decision variance table | 9 cells (Phase 3/4, current vs rolling) + the notice | none |

### 2.8 Alert Stream (`/alert-stream`), `08`, `10`

| Panel | Shows | Endpoint | Source | Update | Interaction |
|---|---|---|---|---|---|
| 2 stat tiles | alerts in buffer; "with precomputed SHAP: N of M" | `GET /alerts` | in-memory ring buffer (200, `alerts.buffer_size`), filled by the simulator's `POST /predict` with `record_alert: true` | **polled every 2 s** | none |
| Alert list | time, predicted-family pill, confidence, ✓/✗ against the true label, SHAP pill | `GET /alerts` | as above | 2 s | "Only alerts with SHAP" checkbox; click selects |
| Detail panel | family, confidence, truth; SHAP chart + LLM "analyst aid" sentence **if** `shap_available` | `GET /shap/{id}` + `GET /explain/{id}` | `streamed_pool.npz`, `results/explanations/fedavg_a0.5_s42/sentences.json` | on selection | none |

---

## 3. Every backend endpoint

These are real responses from this run. Full truncated samples are in the
Appendix.

| Method · path | Response shape | Built from | Used by frontend? |
|---|---|---|---|
| `GET /health` | `{status, model_loaded, scaler_sha256, uptime_seconds}` | live | yes (sidebar; only `model_loaded` is displayed) |
| `GET /config` | `{alpha, seed, tag, best_round, n_features, n_classes, hotswap:{active, event_id, swap_depth, base_tag, job_status, job_detail}}` | manifest + loaded model | yes (sidebar) |
| `POST /predict` | req `{features:{82 names→float}, true_family?, record_alert=false, shap_sample_id?}` → `{family, confidence, probabilities:{9}}` | ONNX fp32 session (torch if a hot-swap is active) | yes (Detect, Explain); simulator |
| `POST /hotswap/trigger` | req `{family}` → `{job_id, status, family, seed}`; 409 if a job is already running | `backend/hotswap_service.py` subprocess | **no UI calls it** (see §5) |
| `GET /hotswap/status` | `{job_id, status, detail, family, hotswap:{…}}` | in-memory state + job result file | yes (banner, 3 s poll) |
| `POST /hotswap/revert` | `HotSwapInfo` | in-memory | yes (banner button, only when active) |
| `GET /shap/{sample_id}` | `{sample_id, tag, eval_family, feature_names[82], class_names[9], shap_values[82][9], additivity_max_diff, raw_values[82], base_values[9]}`; 404 outside curated 0–13 ∪ the 500-row pool | `global_shap.npz` + `eval_rows_sidecar.npz`, or `streamed_pool.npz` | yes |
| `GET /explain/{sample_id}` | `{sample_id, tag, sentence, predicted_family, confidence, top_features:[{name, raw_value, shap_value}×5]}`; 404 outside the 514-row set | `results/explanations/fedavg_a0.5_s42/sentences.json` (llama3.1:8b, offline) | yes (Alert Stream only) |
| `GET /agreement` | `{agreement_metrics[1246], per_silo_agreement[89], round_wise_agreement[356], centralized_instability_floor[42]}` (raw CSV rows) | 4 CSVs in `results/inspection/` | yes, but only 2 of the 4 arrays |
| `GET /parity` | `{parity_monitor[356]: {tag, alpha, seed, round, fleet_parity, silo_id, silo_deviation, flagged}}` | `results/inspection/parity_monitor.csv` | **no** |
| `GET /alerts` | `[{timestamp, predicted_family, confidence, true_family, shap_available, shap_sample_id}]`, newest first | in-memory ring buffer | yes |
| `GET /trust` | `{conditions[5]:{attack_tag, alpha, seed, f, mode, true_malicious_silos, clean/attack:{run_tag, decision_log, per_silo[10], decision_grid{rounds, silos[{silo_id, severities[20]}]}, stat_series{rounds, silos[{5 stats×20}]}, explanations[200]}}, excluded_conditions[1], decision_variance[9], nondeterminism_notice}` (710 KB) | see §2.7 | yes |
| `GET /federation` | `{shape, label_vocab, manifest_summaries[9], silo_total_eligibility{…, table[90]}, family_eligibility{…, matrix[81]}, silo_sizes[680]}` | see §2.1 | yes |
| `GET /faithfulness` | `{config_label, auc[4]:{model, deletion_auc, insertion_auc}}` | see §2.5 | yes |
| `GET /faithfulness/deletion_curve.png` | image/png, 147,487 B | `results/figures/` | yes |
| `GET /faithfulness/insertion_curve.png` | image/png, 163,026 B | `results/figures/` | yes |

FastAPI's auto-generated `/docs` and `/openapi.json` also exist.

---

## 4. Data that exists on disk but no panel shows

**Trust check (ByzAgent)**

- **Rolling-history agent decisions.** Files:
  `agent_decisions_phase4_rolling_history.jsonl` in `fedavg_a0.5_s42` and the
  poisoned s42 runs. Only their stability numbers reach the
  decision-variance table; there are no grids or rationales for them.
- **Classical defences (Phase 2).** Runs: `krumclassical_*`, `multikrum_*`,
  `trimmedmean_*` in `results/federated/`, including `krum_selection.jsonl`
  and `defense_config.json`. Write-up: `results/defenses/PHASE2_SUMMARY.md`.
  None of these numbers are on screen: Krum/Multi-Krum exclusion rates and
  the clean-defence cost (−22.7 / −4.9 / −1.6 pp). They appear only as prose
  in the oracle-asymmetry expander.
- **Agent fidelity and citation audits.** Files:
  `multiseed_fidelity_audit.json`, `multiseed_citation_accuracy_sample.json`,
  `multiseed_trend_claim_*`, `phase3_citation_accuracy_sample.json`,
  `phase4_diagnostic_reasoning_audit.json`. The ~35–45 % contradicted
  trend-claim figure is not shown. The panel only links to the docs.
- **Compositional-confound evidence.** Files:
  `phase3_compositional_check_a0.5_s42.json`,
  `phase3_compositional_match_search.json`, `silo_family_composition_*.csv`,
  `frontier_f{2,3}_*.csv`.
- **Attack-effect statistics** (best-by-val max and final-5 mean). Files:
  `attack_val_summary.json`, `attack_row_flip_diagnostic_*`,
  `retro_replay_val_metrics_a0.5_s42.json`, plus
  `results/attacks/*/flip_log.csv`, which the config comment names but
  `trust.py` never reads.
- **Phase 1 monitoring.** `results/monitoring/PHASE1_SUMMARY.md` and the
  `phase1_gate_*.json` files.
- **Efficiency pre-screen replay.**
  `results/efficiency/agent_prescreen_replay.json`, the negative result.

**Explanation check**

- **Round-wise agreement** (`round_wise_agreement.csv`). It is in
  `GET /agreement` but nothing renders it. Same for **per-silo agreement**.
- **Parity monitor** (`parity_monitor.csv` via `GET /parity`),
  `parity_noise_floor.csv` (not served at all) and `parity_monitor.png`.
- **FedProx μ=0.0005.** Files: `agreement_metrics_fedprox_mu0.0005.csv`,
  `best_rounds_manifest_fedprox_mu0.0005.json`, 10 `fedprox_*` run dirs and
  `fedprox_vs_fedavg_per_seed.png`.
- **Size-versus-heterogeneity analysis.** Files:
  `silo_size_vs_agreement.csv`, `size_matched_heterogeneity.csv` and
  `entropy_kl_partial_correlation.png`. The partial r values appear only as
  text in Methods & Limits.
- **Round lottery.** `results/federated/round_lottery_val.csv`; it is quoted
  as a single number in Methods & Limits.
- **Ablations and checks.** `common_background_ablation.csv`,
  `kernel_vs_gradient_validation.csv`.
- **Unembedded figures.** `agreement_vs_round.png`,
  `accuracy_agreement_decoupling.png` and `instability_floor_vs_alpha.png`
  are never embedded. Only the two faithfulness PNGs are.
- **Explanation sentences for the 14 curated rows.** `GET /explain/0..13`
  exists, but the Explain view never calls it. Only Alert Stream uses
  `/explain`, and only for pool rows.

**Accuracy / models**

- **Per-class F1, precision and recall.** In
  `results/federated/<tag>/final_metrics.json` (`test.per_class`, including
  Infiltration and Heartbleed, which are meant to be "reported per class
  only") and `results/aggregated/*_per_family.csv`. No panel shows per-class
  numbers.
- **Centralized MLP and XGBoost headline numbers.** In
  `results/aggregated/centralized_headline.csv` and `xgboost_headline.csv`.
- **FedAvg aggregated headline.** `federated_headline.csv` (mean ± sd per α).
  The dashboard shows only the 9 per-seed rows.
- **FedAvgM (preregistered accuracy result).** In
  `results/federated_methods/chosen/fedavgm_m0.9_a5.0_s*` and
  `test_once/result.json`, plus `selection.json` and
  `validation_summary.json`. Nothing about the optimizer comparison or the
  one-shot test result is shown.
- **Efficiency.** `results/efficiency/inference_speed*.json`,
  `communication.json`, `update_compression.json` and
  `results/communication_cost.json`. The ONNX engine is used but never named
  in the UI.
- **Pilots.** `results/pilots/*.csv` (architecture, scaler, weights).
- **Data-quality inspection.** `near_duplicate_audit.json`,
  `partition_check.json`, `val_split_report.json`,
  `duplicates_by_label.csv`, `numeric_health.csv` and `constant_features.csv`.

**Operational**

- **Hot-swap audit log.** `state/hotswap_log/events.jsonl` (5 events from
  earlier sessions). No history view exists.
- **Backend fields never displayed.** `scaler_sha256` and `uptime_seconds`
  from `/health`; the active predict engine (onnx_fp32 vs torch) is not
  exposed by any endpoint.

---

## 5. Broken, empty or inconsistent right now

**Empty by design**

1. **Alert Stream never shows a SHAP panel on validation replay.** In this
   run: 0 of 137 alerts in the buffer had SHAP (`10_…selected.png`). The
   simulator replays validation rows, and the 500-row SHAP pool and 514
   sentences are keyed to `test_global.parquet` positions, so
   `shap_available` is always false. The "Only alerts with SHAP" checkbox
   therefore always empties the list. The `/explain` analyst-aid UI is
   unreachable in the default configuration. Reaching it needs
   `source_split: test` plus an allowlisted checkpoint hash. The allowlist
   is empty, and adding a hash is a test-set decision for the planning chat.
2. **Hot-swap cannot be triggered from the UI.** `postHotswapTrigger` and
   `useHotSwapStatus().trigger` are wired up, but no component calls them.
   There is no confirm/reject button on alerts. The banner and Revert
   button can only appear after a swap that was started some other way
   (curl).

**Visual bugs**

3. **Client Trust Monitor → "Clean-vs-attack flag rate, and lift" chart is
   misplotted.** The category Y axis lists silo 0–9 **twice** (20 slots).
   The points fill only the top half, the top row is clipped against the
   chart edge, and the markers do not line up with their labels. The x
   domain runs −5 %…135 %. There is no legend for grey dot (clean) vs
   diamond (attack). The table under the chart is correct. The likely cause
   is two `<Scatter>` series on a `type="category"` YAxis, each adding its
   own categories (`charts/CleanVsAttackLiftChart.jsx`). This is not
   verified by a fix.
4. **Federation Status heatmap: column labels are clipped.** The rotated
   family names are overdrawn by the first row of cells ("…rce", "…leed",
   "…tion", "…Scan", "…tack"). There is also no colour scale or legend for
   the log flow counts.
5. **Explain at 1440×900: the layout overflows.** The "Additivity residual"
   tile stretches to the full grid height (~600 px of empty card). Below
   the 1103 px of `.xf-main` the page continues on a different background.
   The footer is partly hidden behind the left column (`03_explain.png`,
   bottom).

**Wording that disagrees with CLAUDE.md or the canonical docs** (flagged
here, not changed)

6. **Explanation Agreement, α=0.1 floor callout.** It says "No significance
   test has been run" and shows IQR whiskers. CLAUDE.md records
   cluster-bootstrap CIs ([0.250, 0.429] vs floor [0.429, 0.484]), and
   Methods & Limits on the same dashboard quotes them. The two views
   disagree.
7. **Methods & Limits, silo-size addendum.** It prints `p=0.011`. CLAUDE.md
   says "Report r and n only, no p-values". It also gives no n.
8. **Methods & Limits omits** the "entropy tried first, KL substituted after"
   ordering that CLAUDE.md says to state.
9. **Stale ledes from the Streamlit port:**
   - Detect says "centralized or federated", but only the federated model is
     served.
   - Explain says "Only the base value is computed live", but `base_values`
     now come precomputed from `eval_rows_sidecar.npz`.
10. **Explain additivity tile.** It shows 1.076: one batch-wide max-abs
    residual in logit space for all 14 rows. Its only sub-text is
    "Background size not exposed". CLAUDE.md then stated the residual as
    "~3–8 %" relative (since replaced by the file-backed validation-pool
    figures in `val_pool_summary.json`). A bare 1.076 next to it can read as a large error. This needs
    labelling (absolute, logit, max over 14), not necessarily a fix.

**Not broken, but worth knowing**

11. **Trust condition `a0.5_s42_f2_sudden_silos0-3` pairs logs from
    different phases.** The clean side uses
    `agent_decisions_phase4_current_round.jsonl` and the attack side uses
    `agent_decisions.jsonl` (`trust.py`'s priority tie-break). All other s42
    pairs use phase4 current-round on both sides.
12. **Test-set exposure (already documented).** Detect and Explain post the
    14 fixed `test_global` rows to `/predict` on every page load and show
    ✓/✗ against their labels. Federation Status shows the 9 logged test
    macro-F1 values. Both are in the documented exposure list (items c and
    the per-run results). They are noted only so this inventory is complete;
    nothing new was scored.
13. **Hardcoded paths.** `/federation` and `/faithfulness` read through
    `app_lib.loaders`' hardcoded `RESULTS_ROOT` paths, not the
    `silo_sizes` / `deletion_auc` / `insertion_auc` / `figures_dir` keys in
    `configs/backend.yaml`. Those keys are declared but unused, so editing
    them changes nothing.
14. **Startup log noise.** It prints 6 "missing ScriptRunContext" Streamlit
    warnings, from `app_lib.loaders`' `st.cache_*` decorators. They are
    harmless.

---

## Appendix: real endpoint samples (truncated)

These come from `sample.py` against the running backend. Lists are cut to
their first items with a total count, and long strings are cut. The
`/predict` call used a **synthetic all-zero feature vector** to show the
shape (it is not a real flow, and its prediction means nothing). `/trust`
is cut at 4,000 characters; its top-level keys and counts are in §3.

```text
### GET /health  (application/json, 153 bytes)
{
 "status": "ok",
 "model_loaded": true,
 "scaler_sha256": "53c684d500cc99468d67dee66d0ef3890419814d42404f51ac5bf8aa609531c9",
 "uptime_seconds": 260.1143398284912
}

### GET /config  (application/json, 218 bytes)
{
 "alpha": "0.5",
 "seed": 42,
 "tag": "fedavg_a0.5_s42",
 "best_round": 18,
 "n_features": 82,
 "n_classes": 9,
 "hotswap": {
  "active": false,
  "event_id": null,
  "swap_depth": 0,
  "base_tag": "fedavg_a0.5_s42",
  "job_status": null,
  "job_detail": null
 }
}

### GET /hotswap/status  (application/json, 180 bytes)
{
 "job_id": null,
 "status": null,
 "detail": null,
 "family": null,
 "hotswap": {
  "active": false,
  "event_id": null,
  "swap_depth": 0,
  "base_tag": "fedavg_a0.5_s42",
  "job_status": null,
  "job_detail": null
 }
}

### GET /alerts  (application/json, 34,217 bytes)
[
 {
  "timestamp": "2026-10-13T16:45:01.381210+00:00",
  "predicted_family": "Benign",
  "confidence": 1.0,
  "true_family": "Benign",
  "shap_available": false,
  "shap_sample_id": null
 },
 {
  "timestamp": "2026-10-13T16:45:00.376718+00:00",
  "predicted_family": "Benign",
  "confidence": 0.9999996423721313,
  "true_family": "Benign",
  "shap_available": false,
  "shap_sample_id": null
 },
 "... (200 items total)"
]

### GET /shap/0  (application/json, 16,532 bytes)
{
 "sample_id": 0,
 "tag": "fedavg_a0.5_s42",
 "eval_family": "Benign",
 "feature_names": [
  "Protocol",
  "Flow Duration",
  "Total Fwd Packet",
  "... (82 total)"
 ],
 "class_names": [
  "Benign",
  "Bot",
  "BruteForce",
  "... (9 total)"
 ],
 "shap_values": "[[-0.0666, 0.0591, 0.0179, ...], ...]  (82 features x 9 classes)",
 "additivity_max_diff": 1.0760228147688817,
 "raw_values": [
  6.0,
  251737.0,
  12.0,
  "... (82 total)"
 ],
 "base_values": [
  -8.724130630493164,
  -19.120563507080078,
  -21.445934295654297,
  "... (9 total)"
 ]
}

### GET /shap/11375  (application/json, 16,585 bytes)
{
 "sample_id": 11375,
 "tag": "fedavg_a0.5_s42",
 "eval_family": "Benign",
 "feature_names": [
  "Protocol",
  "Flow Duration",
  "Total Fwd Packet",
  "... (82 total)"
 ],
 "class_names": [
  "Benign",
  "Bot",
  "BruteForce",
  "... (9 total)"
 ],
 "shap_values": "[[2.0832, -0.4621, 0.1161, ...], ...]  (82 features x 9 classes)",
 "additivity_max_diff": 0.5247712135314941,
 "raw_values": [
  17.0,
  1094263.0,
  2.0,
  "... (82 total)"
 ],
 "base_values": [
  -8.724130630493164,
  -19.120563507080078,
  -21.445934295654297,
  "... (9 total)"
 ]
}

### GET /explain/0  (application/json, 726 bytes)
{
 "sample_id": 0,
 "tag": "fedavg_a0.5_s42",
 "sentence": "The network flow was classified as Benign due to a combination of normal protocol behavior, including 2 FIN flags, a 1:1 down/up ratio, and packet length varian... (186 chars)",
 "predicted_family": "Benign",
 "confidence": 0.9999998807907104,
 "top_features": [
  {
   "name": "FIN Flag Count",
   "raw_value": 2.0,
   "shap_value": 2.2128653384438297
  },
  {
   "name": "Down/Up Ratio",
   "raw_value": 1.0,
   "shap_value": 0.815619223996493
  },
  "... (5 items total)"
 ]
}

### GET /agreement  (application/json, 357,179 bytes)
{
 "agreement_metrics": [
  {
   "alpha": 0.1,
   "seed": 42,
   "silo": 0,
   "sample_idx": 0,
   "family": "Benign",
   "family_eligible": false,
   "kendall_weighted_tau": 0.1060141328,
   "jaccard_at_5": 0.1111111111,
   "jaccard_at_10": 0.1764705882,
   "jaccard_at_20": 0.2903225806
  },
  {
   "alpha": 0.1,
   "seed": 42,
   "silo": 0,
   "sample_idx": 1,
   "family": "Benign",
   "family_eligible": false,
   "kendall_weighted_tau": 0.4539219997,
   "jaccard_at_5": 0.4285714286,
   "jaccard_at_10": 0.25,
   "jaccard_at_20": 0.25
  },
  "... (1246 items total)"
 ],
 "per_silo_agreement": [
  {
   "alpha": 0.1,
   "seed": 42,
   "silo": 0,
   "jaccard_at_5": 0.0555555556,
   "jaccard_at_10": 0.1437908497,
   "jaccard_at_20": 0.2903225806,
   "kendall_weighted_tau": 0.3528241247,
   "n_samples": 6
  },
  {
   "alpha": 0.1,
   "seed": 42,
   "silo": 1,
   "jaccard_at_5": 0.25,
   "jaccard_at_10": 0.3333333333,
   "jaccard_at_20": 0.311827957,
   "kendall_weighted_tau": 0.4180045167,
   "n_samples": 10
  },
  "... (89 items total)"
 ],
 "round_wise_agreement": [
  {
   "tag": "fedavg_a0.1_s42",
   "alpha": 0.1,
   "seed": 42,
   "round": 5,
   "silo_id": 0,
   "jaccard_at_10": 0.2671568627,
   "tau_w": 0.2456316139
  },
  {
   "tag": "fedavg_a0.1_s42",
   "alpha": 0.1,
   "seed": 42,
   "round": 5,
   "silo_id": 1,
   "jaccard_at_10": 0.2475133913,
   "tau_w": 0.457565325
  },
  "... (356 items total)"
 ],
 "centralized_instability_floor": [
  {
   "seed_pair": "42-1337",
   "sample_idx": 0,
   "family": "Benign",
   "kendall_weighted_tau": 0.6213235034,
   "jaccard_at_5": 0.25,
   "jaccard_at_10": 0.1764705882,
   "jaccard_at_20": 0.3333333333
  },
  {
   "seed_pair": "42-1337",
   "sample_idx": 1,
   "family": "Benign",
   "kendall_weighted_tau": 0.8111125275,
   "jaccard_at_5": 0.4285714286,
   "jaccard_at_10": 0.5384615385,
   "jaccard_at_20": 0.4814814815
  },
  "... (42 items total)"
 ]
}

### GET /parity  (application/json, 58,076 bytes)
{
 "parity_monitor": [
  {
   "tag": "fedavg_a0.1_s42",
   "alpha": 0.1,
   "seed": 42,
   "round": 5,
   "fleet_parity": 0.189949029,
   "silo_id": 0,
   "silo_deviation": 0.8671023965,
   "flagged": false
  },
  {
   "tag": "fedavg_a0.1_s42",
   "alpha": 0.1,
   "seed": 42,
   "round": 5,
   "fleet_parity": 0.189949029,
   "silo_id": 1,
   "silo_deviation": 0.8235294118,
   "flagged": false
  },
  "... (356 items total)"
 ]
}

### GET /trust  (application/json, 710,545 bytes)
{
 "conditions": [
  {
   "attack_tag": "a0.5_s1337_f3_sudden_silos0-3-5",
   "alpha": "0.5",
   "seed": 1337,
   "f": 3,
   "mode": "sudden",
   "true_malicious_silos": [
    0,
    3,
    "... (3 items total)"
   ],
   "clean": {
    "run_tag": "fedavg_a0.5_s1337",
    "decision_log": "agent_decisions_multiseed.jsonl",
    "per_silo": [
     {
      "silo_id": 0,
      "n_rounds": 20,
      "n_flagged": 1,
      "flag_rate": 0.05,
      "mean_update_norm": 3.2795433932589706,
      "mean_cosine_to_global": 0.7526945968750963,
      "mean_cosine_to_peer_mean": 0.3661495757666105,
      "mean_train_loss": 0.004418557468780567,
      "mean_val_accuracy": 0.9748834600349794
     },
     {
      "silo_id": 1,
      "n_rounds": 20,
      "n_flagged": 20,
      "flag_rate": 1.0,
      "mean_update_norm": 1.9457287184250922,
      "mean_cosine_to_global": 0.23853138958498096,
      "mean_cosine_to_peer_mean": 0.5305075571931537,
      "mean_train_loss": 0.029236192738459395,
      "mean_val_accuracy": 0.9798607094827646
     },
     "... (10 items total)"
    ],
    "decision_grid": {
     "rounds": [
      1,
      2,
      "... (20 items total)"
     ],
     "silos": [
      {
       "silo_id": 0,
       "severities": [
        0,
        0,
        "... (20 items total)"
       ]
      },
      {
       "silo_id": 1,
       "severities": [
        1,
        1,
        "... (20 items total)"
       ]
      },
      "... (10 items total)"
     ]
    },
    "stat_series": {
     "rounds": [
      1,
      2,
      "... (20 items total)"
     ],
     "silos": [
      {
       "silo_id": 0,
       "update_norm": [
        5.993405771788633,
        5.908144296799921,
        "... (20 items total)"
       ],
       "cosine_to_global": [
        0.8920079369449442,
        0.9095007219423151,
        "... (20 items total)"
       ],
       "cosine_to_peer_mean": [
        0.7593652589864823,
        0.7807264419023164,
        "... (20 items total)"
       ],
       "train_loss": [
        0.012482726379034956,
        0.007463565099258019,
        "... (20 items total)"
       ],
       "val_accuracy": [
        0.9743855957300036,
        0.971173343181454,
        "... (20 items total)"
       ]
      },
      {
       "silo_id": 1,
       "update_norm": [
        3.4503922586552025,
        2.4100476961006496,
        "... (20 items total)"
       ],
       "cosine_to_global": [
        0.5914458321641374,
        0.499749892126739,
        "... (20 items total)"
       ],
       "cosine_to_peer_mean": [
        0.7381512187129421,
        0.6513946415423221,
        "... (20 items total)"
       ],
       "train_loss": [
        0.12404338014315179,
        0.04180883120042097,
        "... (20 items total)"
       ],
       "val_accuracy": [
        0.9481789106213374,
        0.9765665828182812,
        "... (20 items total)"
       ]
      },
      "... (10 items total)"
     ]
    },
    "explanations": [
     {
      "silo_id": 0,
      "round": 1,
      "decision": "trust",
      "text": "low update_norm (5.993) and high cosine_to_global (0.892) suggest this client's update is consistent with the global model."
     },
     {
      "silo_id": 0,
      "round": 2,
      "decision": "trust",
      "text": "low update_norm (5.908144296799921) and high cosine_to_global (0.9095007219423151) indicate a trustworthy client"
     },
     "... (200 items total)"
    ]
   },
   "attack": {
    "run_tag": "fedavg_a0.5_s1337_poisoned_f3_sudden_silos0-3-5",
    "decision_log": "agent_decisions_multiseed.jsonl",
    "per_silo": [
     {
      "silo_id": 0,
      "n_rounds": 20,
      "n_flagged": 2,
      "flag_rate": 0.1,
      "mean_update_norm": 3.933814003278273,
      "mean_cosine_to_global": 0.8031573084928902,
      "mean_cosine_to_peer_mean": 0.4514328161387557,
      "mean_train_loss": 0.03382623760631329,
      "mean_val_accuracy": 0.9322988161351237
     },
     {
      "silo_id": 1,
      "n_rounds": 20,
      "n_flagged": 20,


### GET /federation  (application/json, 67,708 bytes)
{
 "shape": {
  "n_silos": 10,
  "alphas": [
   "0.1",
   "0.5",
   "... (3 items total)"
  ],
  "seeds": [
   42,
   1337,
   "... (3 items total)"
  ]
 },
 "label_vocab": {
  "headline_classes": [
   "Benign",
   "Bot",
   "... (7 items total)"
  ],
  "below_floor_classes": [
   "Heartbleed",
   "Infiltration"
  ],
  "n_classes": 9
 },
 "manifest_summaries": [
  {
   "alpha": "0.1",
   "seed": 42,
   "tag": "fedavg_a0.1_s42",
   "best_round": 20,
   "val_macro_f1_headline": 0.5440290884,
   "test_macro_f1_headline": 0.5426478662
  },
  {
   "alpha": "0.1",
   "seed": 1337,
   "tag": "fedavg_a0.1_s1337",
   "best_round": 16,
   "val_macro_f1_headline": 0.4550855011,
   "test_macro_f1_headline": 0.4480995786
  },
  "... (9 items total)"
 ],
 "silo_total_eligibility": {
  "threshold_flows": 500,
  "n_excluded": 1,
  "n_total": 90,
  "table": [
   {
    "alpha": "0.1",
    "seed": 42,
    "silo": 9,
    "total_flows": 143,
    "below_floor": true
   },
   {
    "alpha": "0.1",
    "seed": 1337,
    "silo": 8,
    "total_flows": 836,
    "below_floor": false
   },
   "... (90 items total)"
  ]
 },
 "family_eligibility": {
  "threshold_flows": 50,
  "min_eligible_silos": 4,
  "n_excluded": 22,
  "n_total": 81,
  "matrix": [
   {
    "alpha": "0.1",
    "seed": 42,
    "family": "Benign",
    "eligible_silos": 6,
    "family_included": true
   },
   {
    "alpha": "0.1",
    "seed": 42,
    "family": "Bot",
    "eligible_silos": 4,
    "family_included": true
   },
   "... (81 items total)"
  ]
 },
 "silo_sizes": [
  {
   "alpha": "0.1",
   "seed": 1337,
   "silo": 0,
   "family": "Benign",
   "n": 1056872
  },
  {
   "alpha": "0.1",
   "seed": 1337,
   "silo": 0,
   "family": "Bot",
   "n": 9
  },
  "... (680 items total)"
 ]
}

### GET /faithfulness  (application/json, 376 bytes)
{
 "config_label": "\u03b1=0.5, seed=42",
 "auc": [
  {
   "model": "global",
   "deletion_auc": 0.1672408827,
   "insertion_auc": 0.6962256374
  },
  {
   "model": "silo_0",
   "deletion_auc": 0.2740402378,
   "insertion_auc": 0.7998418296
  },
  "... (4 items total)"
 ]
}

### GET /faithfulness/deletion_curve.png  (image/png, 147,487 bytes)

### GET /faithfulness/insertion_curve.png  (image/png, 163,026 bytes)

### GET /shap/999 -> HTTP 404: {"detail":"sample_id 999 is not in the curated set [0,13] or the 500-row streamed pool."}

### GET /explain/999 -> HTTP 404: {"detail":"sample_id 999 has no precomputed explanation. Only rows in the precomputed SHAP set (curated + streamed pool) are covered."}

### POST /predict (SYNTHETIC all-zero feature vector, shape demo only, record_alert=false)
{
 "family": "Benign",
 "confidence": 0.9998631477355957,
 "probabilities": {
  "Benign": 0.9998631477355957,
  "Bot": 1.2995708686958096e-07,
  "BruteForce": 4.6849873314158685e-08,
  "DDoS": 1.4878474841051315e-10,
  "DoS": 2.2966119672673813e-07,
  "Heartbleed": 2.296805222412341e-14,
  "Infiltration": 1.8642852886441297e-11,
  "PortScan": 0.0001363224582746625,
  "WebAttack": 1.5054224888899626e-07
 }
}
```
