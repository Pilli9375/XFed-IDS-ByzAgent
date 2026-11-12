# Part 7 — Reference {#part-7}

## 7.1 Glossary, A–Z {#glossary}

Numbers in the glossary are given with their sources in the chapters and in the headline table ([7.2](#headline)).

- **Accuracy** — share of all predictions that are correct; misleading here because Benign dominates, so never reported as a headline.
- **Activation function** — the simple bend a neuron applies to its weighted sum; we use ReLU.
- **AdamW** — the optimizer used for local training: Adam with decoupled weight decay.
- **Additivity** — SHAP's property that base value plus all SHAP values equals the model's output.
- **Additivity residual** — how far the estimated SHAP values miss exact additivity.
- **α (alpha), Dirichlet** — the slider controlling how different silos' data is; 0.1 severe, 0.5 realistic, 5.0 near-IID.
- **Attempted (flow)** — a flow from an attack whose payload didn't land; joined to its parent family here.
- **AUC** — area under a curve; used for deletion/insertion faithfulness curves.
- **Background (SHAP)** — the reference rows used to compute the base value; seeded and drawn from each silo's training data.
- **Base value** — the model's average output over the background; SHAP's starting point.
- **BatchNorm** — a normalisation layer with running data statistics; rejected for FL.
- **Best-by-validation round** — the round whose global model scored highest on validation; the one we report.
- **ByzAgent** — our LLM trust agent: reads five statistics per silo per round and decides trust, downweight or quarantine.
- **Byzantine client** — a participant that may send arbitrary or malicious updates.
- **Canary (silo)** — a never-malicious silo watched to see whether a detector flags it anyway (silo 8 at seed 42).
- **Ceiling effect** — when a baseline rate is already near its maximum, any increase is capped; why seed 42 showed near-zero lift.
- **Chance level** — the Jaccard@10 two random top-10 lists would get; 0.065 here.
- **CICFlowMeter** — the tool that turns packets into flow records with features.
- **Class weights** — multipliers making mistakes on rare classes cost more in training.
- **Client** — an organization that trains locally in FL; also "silo" or "org."
- **Cluster bootstrap** — estimating uncertainty by resampling whole groups (silos) rather than individual rows.
- **Compositional confound** — detectors reacting to how unusual a silo's traffic mix is, not to whether it attacks.
- **Confidence** — the softmax probability of the predicted class.
- **Cosine similarity** — how closely two vectors point the same way (1 = same direction).
- **DeepExplainer** — a fast SHAP method that failed on our LayerNorm layers.
- **Dirichlet distribution** — a way to draw random proportions that sum to 1; controlled by α.
- **Downweight** — ByzAgent decision: include the silo's update at 0.3× its normal weight.
- **Dropout** — randomly switching off neurons during training to reduce overfitting.
- **Effect size** — how big a difference is, not how surprising; we use Glass's delta.
- **Effective-number class weights** — class weights based on (1 − β)/(1 − βⁿ); β = 0.999 here.
- **Eligibility (explanation)** — rule deciding which (silo, row) pairs count: silo ≥ 400 flows and ≥ 20 of that family.
- **Epoch** — one full pass over a client's training data; 3 local epochs per round.
- **Explanation check** — stage 3: do the organizations' models detect attacks for the same reasons?
- **f** — the number of attacking silos (3 or 2 here).
- **Faithfulness** — whether an explanation reflects what the model actually relies on.
- **False positive / negative** — an alarm on normal traffic / a missed attack.
- **Family** — one of our 8 attack groups (or Benign) after mapping 14 raw labels.
- **Feature** — one number describing a flow; we use 82.
- **FedAdam / FedYogi** — server-side adaptive optimizers; candidates that failed the α=0.5 guard.
- **FedAvg** — federated averaging: weighted mean of client weights by data size.
- **FedAvgM** — FedAvg plus server momentum; selected by our preregistration (momentum 0.9).
- **Federated learning (FL)** — training a shared model across data holders without moving their data.
- **FedProx** — FedAvg with a penalty (μ) for drifting from the global model.
- **Final-5 mean** — mean validation macro-F1 over rounds 16–20; the attack-effect statistic.
- **Flow** — a summary record of one network conversation.
- **Flower (flwr)** — the FL framework we use (1.33.0).
- **Glass's delta** — (mean of group A − mean of control) ÷ sd of control.
- **GradientExplainer** — SHAP via expected gradients; our explainer.
- **Group-aware split** — a split that keeps identical feature vectors on the same side.
- **Hot-swap** — replacing the served model live with a briefly retrained one, behind a validation gate.
- **IDS** — intrusion detection system.
- **IID / non-IID** — clients' data drawn from the same mix / from different mixes.
- **IQR** — interquartile range: spread of the middle half of the data.
- **Jaccard@k** — overlap of two top-k sets ÷ their union.
- **Kendall's τ (weighted)** — rank agreement over all features, weighting important ones more.
- **KL divergence** — how far one distribution is from another, directionally; our heterogeneity measure.
- **Krum** — keeps the single most central update.
- **Label flipping** — poisoning by changing training labels; here attack → Benign.
- **LayerNorm** — per-example normalisation layer; FL-safe.
- **Lift** — flag rate under attack minus the same silo's flag rate with no attack.
- **LLM** — large language model; ours is llama3.1:8b-instruct-q4_K_M via Ollama.
- **Logit** — a raw class score before softmax.
- **Macro-F1** — unweighted mean of per-class F1; our headline metric over 7 classes.
- **Manifest (SHA256)** — file of hashes that proves partitions weren't changed.
- **MLP** — multilayer perceptron; ours is [128, 64].
- **Multi-Krum** — keeps the n − f most central updates and averages them.
- **Non-IID** — see IID.
- **Null control / seed-noise floor** — agreement between centralized models differing only by seed; median 0.429.
- **ONNX / ONNX Runtime** — portable model format / fast engine; serves our model at fp32.
- **Oracle f** — telling a defense the true number of attackers; given to baselines, not ByzAgent.
- **Overfitting** — fitting training data's quirks so well that new data suffers.
- **Parity monitor** — server-side alarm flagging silos whose top-10 lists are outliers.
- **Partial correlation** — correlation after removing the influence of a third variable.
- **Partition** — the assignment of training rows to silos.
- **Poisoning** — corrupting a model by sending bad updates or training on bad data.
- **Pre-registration** — committing the analysis plan before seeing results.
- **Precision / recall** — share of alarms that are real / share of real attacks caught.
- **Quantization** — storing numbers with fewer bits (e.g. int8).
- **Quarantine** — ByzAgent decision: exclude the silo's update that round.
- **Rationale of measured fidelity** — our wording for ByzAgent's written reasons: produced, and audited for accuracy.
- **Recovery fraction** — share of the attack's damage a defense undoes; ≥ 0.5 counts as success.
- **Round** — one cycle of send model → local training → aggregate.
- **Round lottery** — large quality swings between rounds; why we select by validation.
- **Seed** — the number fixing a run's randomness; we use 42, 1337, 2024.
- **SHAP** — SHapley Additive exPlanations; fair-share attribution of a prediction to features.
- **Silo** — an organization in our federation (10 of them).
- **Softmax** — turns logits into probabilities summing to 1.
- **Spearman correlation** — correlation on ranks.
- **StandardScaler** — rescales each feature to mean 0, sd 1.
- **Test set** — held-out data for one final measurement; 478,376 rows here.
- **Trimmed mean** — per-coordinate average after dropping the extremes.
- **Trust check** — stage 4: is any organization poisoning the model?
- **Validation set** — data used for all choices; 143,513 rows here.

## 7.2 Headline numbers with sources {#headline}

| Quantity | Value | Source |
|---|---|---|
| Centralized MLP macro-F1 | 0.9900 ± 0.0022 | `results/aggregated/centralized_headline.csv` |
| XGBoost macro-F1 | 0.9946 ± 0.0001 | `results/aggregated/xgboost_headline.csv` |
| FedAvg α=0.1 / 0.5 / 5.0 | 0.516 ± 0.048 / 0.941 ± 0.057 / 0.990 ± 0.001 | `results/aggregated/federated_headline.csv` |
| Jaccard@10 across α | 0.333 → 0.538 → 0.667 | `results/inspection/agreement_metrics.csv`; `docs/contribution_a_results.md` §2 |
| Weighted Kendall's τ across α | 0.592 → 0.787 → 0.844 | `results/inspection/agreement_metrics.csv`; `docs/contribution_a_results.md` §2 |
| Chance-level Jaccard@10 | 0.065 (5.1×–10.3× chance) | `tools/agreement_metrics.py`; `docs/contribution_a_results.md` §2 |
| Centralized-seed instability floor | median 0.429, range [0.429, 0.484] | `results/inspection/centralized_instability_floor.csv`; `docs/contribution_a_results.md` §2 |
| α=0.1 cluster-bootstrap CI | [0.250, 0.429] | `docs/contribution_a_results.md` §2 |
| Served demo model | fedavg_a0.5_s42, round 18, val macro-F1 0.9760 | `results/federated/fedavg_a0.5_s42/final_metrics.json` |
| FedAvgM β=0.9 (preregistered, test once) α=0.1 / 0.5 / 5.0 | 0.5930 ± 0.0632 / 0.9852 ± 0.0005 / 0.9911 ± 0.0005 | `results/federated_methods/test_once/result.json`; `docs/contribution_a_results.md` (optimizer section) |
| Per-flow latency p50, ONNX fp32 vs PyTorch | 45.7 µs vs 186.5 µs | `results/efficiency/inference_speed_summary.json` |
| Bytes per round (10 silos, fp32, up + down) | 1,587,920 (793,960 each way) | `results/efficiency/communication.json` |
| Round lottery (max, validation) | 0.118 (α=5.0, seed 42) | `results/federated/round_lottery_val.csv` |
| train_loss separation (Glass's delta ratio) | 33.8× (f=3) / 154.3× (f=2) | `results/monitoring/PHASE1_SUMMARY.md` |
| Multi-Krum malicious exclusion | 0% (f=3 and f=2) | `results/defenses/PHASE2_SUMMARY.md` |
| Cost of defending with no attack | Krum −22.7pp, Multi-Krum −4.9pp, trimmed mean −1.6pp | `CLAUDE.md`; underlying test macro-F1 in `docs/contribution_b_results.md` §4 |
| ByzAgent decision stability | 27/30 exact; 30/30 trust-vs-flag | `results/agents/PHASE3_SUMMARY.md` |
| Citation strict error | 11.7% (seed 42) → 22.5% (seeds 1337/2024) | `docs/contribution_b_results.md` §5, §8 |
| Trend claims contradicted (rolling history) | ≈35–45% (automated 45.00%) | `results/agents/MULTISEED_VALIDATION_SUMMARY.md` |
| Cleaned flows | 1,913,502 of 2,099,976 | `data/README.md` |
| Train / test | 1,435,126 / 478,376 | `data/README.md` |

## 7.3 Repository map {#repo}

![Repository layout at a glance.](img/fig23_repo.svg)

| Path | What's there |
|---|---|
| `CLAUDE.md`, `PROJECT_INSTRUCTIONS.md` | Project rules, locked decisions, headline numbers (identical text) |
| `README.md` | Overview, key results, reproduction steps |
| `APP.bat` | One-click dashboard start |
| `configs/` | Every parameter: `data.yaml`, `model.yaml`, `attack.yaml`, `defense.yaml`, `agent.yaml`, `backend.yaml`, `hotswap.yaml`, `efficiency.yaml`, `federated_methods.yaml`, `val_shap_pool.yaml`, `showcase_export.yaml` |
| `data/README.md` | Data decision record; `data/processed/` is git-ignored |
| `federated/xfed_federated/` | The authoritative Flower app (`server_app.py`, `client_app.py`, `_vendored/`) |
| `src/data/` | Cleaning, mapping, split, partitioning |
| `src/models/`, `src/train/` | MLP; centralized and XGBoost training |
| `src/attacks/`, `src/monitoring/`, `src/agents/` | Label flip; behaviour statistics; ByzAgent |
| `src/hotswap/` | Hot-swap retraining and audit log |
| `src/federated/` | Early prototype, unused |
| `tools/` | SHAP pipeline, agreement metrics, floor, parity monitor, audits, efficiency, prereg, showcase export |
| `scripts/` | Partition checks, aggregation, val split, class weights, trust-check phase gates |
| `results/aggregated/` | Headline tables |
| `results/federated/` | Per-run histories, metrics, checkpoints, agent logs |
| `results/inspection/` | Agreement, floor, parity, residual and phase-gate outputs |
| `results/shap/`, `results/explanations/` | SHAP files; LLM summary sentences |
| `results/attacks/`, `monitoring/`, `defenses/`, `agents/` | Trust-check phase summaries |
| `results/federated_methods/`, `results/efficiency/` | Prereg and efficiency outputs |
| `results/figures/` | Analysis figures reused in this handbook |
| `backend/` | FastAPI app, simulator, model loader, hot-swap service |
| `frontend/` | React dashboard (Live, Investigate, Limits) |
| `site/`, `film/` | Showcase site; explainer film |
| `docs/` | Canonical results A and B, protocol, prereg, test-set audit, efficiency, dashboard screenshots, this handbook |
| `app.py`, `app_lib/` | Older Streamlit dashboard |

## 7.4 Timeline from git history {#timeline}

Dates are commit dates; the repository's history begins on 2026-09-11. Work before that date (data pipeline, training, explanation and trust phases) is recorded in the docs, not in this git history.

| Date | Milestone (from commit messages) |
|---|---|
| 2026-09-11 | First commit: pipeline, backend, React dashboard (`0d9a8aa`) |
| 2026-09-13 | Hot-swap audit log; warm-started retraining service; live backend hot-swap with banner and one-click revert |
| 2026-10-02 | Streamed SHAP pool and LLM explanation layer; `contribution_a_results.md` named canonical |
| 2026-10-03 | Test-set access note; "present as one system" wording; showcase data export |
| 2026-10-07 | Showcase site built and merged; 0% exclusion attributed to Multi-Krum; WCAG AA contrast; explainer film merged |
| 2026-10-12 | README rewrite; decision to re-run the test set once for a preregistered config (`b2b9bee`); prereg Part 1 (`ad249bd`); validation grid; seal (`1a17277`); single test evaluation (`b21a4bf`) |
| 2026-10-13 | Simulator replays validation by default; validation-only round lottery; test-set exposure audit; epochs provenance; CPU disclosure; efficiency parts A–C merged; ONNX fp32 default; validation SHAP pool and summaries; "~3–8%" replaced |
| 2026-10-14 | Residual audit and pre-specified sensitivity check; headline table additions; dashboard v2 (Live, Investigate, Limits); README restyle; `APP.bat` |
| 2026-11-12 | This handbook |

## 7.5 Citations, as they appear in the docs {#citations}

- L. Liu, G. Engelen, T. Lynar, D. Essam and W. Joosen, "Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018," IEEE Conference on Communications and Network Security (CNS), 2022, pp. 254–262. (source: `README.md`)
- G. Engelen, V. Rimmer and W. Joosen, "Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study," IEEE Security and Privacy Workshops (SPW), Workshop on Traffic Measurements for Cybersecurity (WTMC), 2021. (source: `README.md`)
- Oki et al., IEEE Networking Letters, 2024. (source: `README.md`; full entry not in the docs — [to verify in lit review])
- Gholizade et al., arXiv 2607.13045 (June 2026), federated-XAI survey. (source: `README.md`; full entry [to verify in lit review])
- Lanvin et al., CRiSIS-2022 (third correction branch, not used). (source: `data/README.md`)
- Blanchard et al., Krum/Multi-Krum. (source: `results/defenses/PHASE2_SUMMARY.md`; full entry [to verify in lit review])
- Hsu et al., 2019, FedAvgM. (source: `docs/preregistration_accuracy.md`)
- Iglewicz & Hoaglin 1993, modified z-score. (source: `docs/contribution_a_results.md`)
- Repository: V Naga Adithya, T Shaun, P Sampath and D Tharun, "XFed-IDS-ByzAgent: A federated intrusion detection system that checks whether its own explanations and its own participants can be trusted," VIT-AP University capstone project, 2026. (source: `README.md`)
- Mentioned in Part 1 for teaching, not recorded in the docs: McMahan et al. (FedAvg), Li et al. (FedProx), Lundberg & Lee (SHAP), Yin et al. (trimmed mean), Cui et al. (effective number) — all [to verify in lit review].
