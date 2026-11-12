# Part 3 — Honesty and rigor {#part-3}

This part collects every disclosure in one place. Present it as a strength: **we checked, and here is what we found.** An examiner who finds a problem you didn't mention will doubt everything; an examiner who hears you name it first will trust everything else more.

## 3.1 The test-set story, start to finish {#test-story}

**In one line:** all model and round selection used validation data; the test set was nevertheless read in several documented ways during development; three early choices were recorded with test numbers as their justification and were re-checked on validation; and since 2026-10-12 only one preregistered configuration may ever be scored on test.

### The plain version

A test set is like a final exam you may sit only once. While we were building the project, our code looked at that exam paper in several ways — mostly to log or display things, never to pick anything — and three early settings were written down with exam scores as the reason. We checked those three settings again using practice data and got the same answers. We published a full list of every look. Since 12 October 2026, only one configuration, chosen beforehand, may ever be scored on the test set (source: `CLAUDE.md`, "Test-set use").

### What the rule should be

From [1.3.1](#bg-splits): choose everything on validation, score the test set once at the end. The test set is `data/processed/test_global.parquet`, 478,376 rows (source: `docs/test_set_exposure_audit.md`).

### What actually happened

On 2026-10-13 we ran a read-only audit of every way code in the repository had read the test set (source: `docs/test_set_exposure_audit.md`). The full disclosure, as agreed by the team and used everywhere:

> All model and round selection used validation data. Three early design choices were recorded with test-set numbers as their justification: 3 local epochs, FedProx μ=0.0005 and StandardScaler. Re-checked on validation, the same μ and scaler are selected; for local epochs, validation also selects 3 epochs over 1 at α=0.5 in all three seeds (mean best-by-validation macro-F1 0.9425 vs 0.8602). Headline test metrics come from one evaluation of each run's validation-selected checkpoint. The test set was also read, without informing any later choice, in these ways: (a) legacy client-side per-round scoring in 35 runs, unread by any analysis; (b) round-20 scoring for an earlier round-lottery comparison, since replaced by a validation-based one; (c) 14 fixed rows as SHAP explanation inputs; (d) display-only use: 514 extracted rows, and the dashboard simulator before 2026-10-13 (not logged, no aggregate); (e) centralized pilot and baseline runs (18) and XGBoost seeds (3) scored on test during development; (f) one preregistered re-evaluation of a single validation-selected configuration (`docs/preregistration_accuracy.md`).

(source: `CLAUDE.md`, "Test-set use"; `docs/test_set_exposure_audit.md`)

![Every way the test set was read, and whether anything was chosen from it. Only the three recorded rationales cited test numbers, and all three were re-checked on validation.](img/fig22_test_exposure.svg)

### Each item in plain words

| Item | What happened | Did it influence a choice? |
|---|---|---|
| Headline test numbers | One evaluation of each run's validation-selected checkpoint | No — the checkpoint was already chosen |
| Three recorded rationales | 3 local epochs, μ=0.0005 and StandardScaler were *written down* with test numbers as the reason | Yes, as recorded. Re-checked on validation: same μ and scaler; 3 epochs beat 1 in all three seeds (0.9425 vs 0.8602) |
| (a) Legacy client-side scoring | 35 runs scored each silo on its own test shard every round | No — nothing reads those rows |
| (b) Round-20 scoring | Round-20 test scores fed an early round-lottery figure | No — replaced by `round_lottery_val.csv` |
| (c) 14 SHAP rows | 14 fixed test rows are the explanation inputs | No — inputs, never a selection score |
| (d) Display | 514 rows extracted for the demo; the simulator replayed test rows before 2026-10-13 | No — display only, nothing aggregated |
| (e) Development runs | 18 centralized pilot/baseline runs and 3 XGBoost seeds scored on test | Pilots ranked on validation, but some lock rationales cite test (see above) |
| (f) The prereg | One evaluation of the sealed FedAvgM checkpoints | No — selection, sealing and commit came first |

Also checked and *not* exposures: hot-swap retraining, backend model loading, XGBoost tuning (early-stops on validation), all ByzAgent statistics, the new method runs (source: `docs/test_set_exposure_audit.md`).

### How we disclosed it

- An earlier sentence — "No model selection, stopping round, hyperparameter or method choice used any test score" — **was not used**, because the audit showed it wasn't strictly true. The planning chat replaced it with the disclosure above, now in `README.md`, `PROJECT_INSTRUCTIONS.md` and `docs/contribution_a_results.md` (source: `docs/test_set_exposure_audit.md` §2).
- The round-20 test score was **removed from the site export** and disclosed in contribution B (commit `2fcf8c4`).
- The simulator was switched to **validation rows by default**, with test replay blocked by an empty allowlist (commit `ea59b83`).
- Legacy client-side test scoring is **off by default** (commit `61460e3`).
- **Rule going forward** (team decision, planning chat, 2026-10-12): **no configuration other than the preregistered one is ever scored on the test set** (source: `CLAUDE.md`).

### How to say it out loud (30 seconds)

"All selection was done on validation. Our audit found the test set had also been read during development — mostly for logging and display, nothing chosen from it — and three early settings had been written down with test numbers as the reason. We re-checked those three on validation and got the same choices. We published the full table, and since October 12 only one preregistered configuration can ever be scored on test."

## 3.2 Every audit we ran, and what it found {#audits}

| Audit | What it checked | Finding | Source |
|---|---|---|---|
| Test-set exposure audit | Every read of `test_global.parquet` | 9 kinds of exposure; 3 choices with test-cited rationales, all re-confirmed on validation | `docs/test_set_exposure_audit.md` |
| Epochs provenance on validation | Was "3 local epochs" right without test? | 3 > 1 in all three seeds (0.9425 vs 0.8602) | `results/federated/epochs_provenance_val.json` |
| Round lottery (validation only) | Best round vs round 20 | Up to 0.118 (α=5.0, seed 42) | `results/federated/round_lottery_val.csv` |
| Additivity residual audit | 594 stored SHAP files | 4 of 99 final FedAvg files above 3.336, clustered at α=0.1 small silos; none at α=0.5 | `results/inspection/residual_audit.md` |
| Residual sensitivity (pre-specified) | Does excluding flagged silos move the headline? | α=0.1 Jaccard@10 0.333 → 0.333; τ 0.592 → 0.597 | `results/inspection/residual_sensitivity.json` |
| Unbacked residual figure | Was "~3–8%" traceable? | No backing file → dropped; replaced by median 3.2%, p95 7.7%, max 21.2% | `results/shap/fedavg_a0.5_s42/val_pool_summary.json` |
| Explainer cross-check | Kernel vs Gradient SHAP | τ 0.730, Jaccard@10 0.538 (n=14) | `results/inspection/kernel_vs_gradient_validation.csv`; `docs/contribution_a_results.md` §3 |
| Background ablation | Common vs per-silo background | τ 0.807, Jaccard@10 0.603 (n=42) | `results/inspection/common_background_ablation.csv`; `docs/contribution_a_results.md` §3 |
| Faithfulness spot-check | Deletion < insertion AUC? | Yes for all four probed models (one config) | `results/inspection/deletion_auc.csv`, `insertion_auc.csv` |
| Parity monitor single-draw bug | Do flags reproduce? | Single-draw flags were artifacts (MAD crushed to 0.042); fixed with N≥3 draws | `docs/contribution_a_results.md` §4 |
| SHAP determinism | Same inputs, same SHAP? | No: mean abs. difference 0.0188, max 0.403 — sampling is unseeded | `docs/contribution_a_results.md`, Lim. #17 |
| Eval-set duplication | Were 7 copies of the eval-set code identical? | Yes, byte-identical; consolidated into `tools/eval_set_config.py` (latent defect that did not fire) | `docs/measurement_protocol.md` §2 |
| Bot/WebAttack near-duplication | Do near-duplicate rows inflate agreement? | Tested, **not confirmed** | `docs/contribution_a_results.md`, Lim. #2 |
| Krum/trimmed-mean clean control | Is the confound attack-independent? | Confirmed: same silos excluded with zero attackers | `docs/contribution_b_results.md` §4 |
| ByzAgent decision stability | Repeat calls agree? | 27/30 exact; 30/30 on trust/flag boundary | `docs/contribution_b_results.md` §5 |
| ByzAgent citation accuracy | Are cited numbers correct? | 11.7% error (seed 42), 22.5% (seeds 1337/2024) | `docs/contribution_b_results.md` §5, §8 |
| Trend-claim hand-check | Is the 45.00% automated figure trustworthy? | 32/35 validated, 3 ambiguous, 0 disagreements; ≈35–45% | `docs/contribution_b_results.md` §8 |
| `agent_config.json` claim | Does the cited file exist? | No — disclosed, deliberately not created afterwards | `docs/contribution_b_results.md` §5 |
| Wrong-harness landmine | Could a bare `flwr run` train the wrong app? | Yes → root Flower section removed; now fails on purpose | `docs/contribution_b_results.md` §10 |
| CPU vs GPU | Which device trained federated runs? | CPU (torch 2.13.0+cpu in Flower's env), disclosed | `docs/preregistration_accuracy.md` |
| FedAvg regression run | Does the new code path match published runs? | Identical over all 21 rounds | `docs/preregistration_accuracy.md` |
| ONNX startup gate | Same predictions as PyTorch? | 0 differences on 143,513 validation rows | `docs/efficiency_results.md` |
| Data cleaning bugs | Conflict/dedup keys | Two caught (58,307 and 58,228 rows would have been lost) | `data/README.md` §4 |

**Negative results we report on purpose:** rolling history failed its pre-registered test; the train_loss pre-screen didn't transfer; int8 quantization was dropped; compression showed no detectable effect at n=3; entropy failed the size conditioning; the live ByzAgent run was not done because it couldn't be interpreted.

**n=1 experiments, by design:** Phase 2 baselines, the Phase 4 matrix and gradual mode (seed 42 only) (source: `CLAUDE.md`). Only the confound/canary finding, the fidelity audit and the trend hand-check were multi-seeded (source: `docs/contribution_b_results.md` §10).

## 3.3 What we do NOT claim {#not-claim}

Memorise this list. Each line is a sentence you should never say, or a stronger version you should correct if someone else says it. The numbers in it are sourced in chapters [2.4](#ch-expl), [2.5](#ch-trust), [2.6](#ch-prereg) and [2.7](#ch-eff).

1. We do **not** claim to be the first to measure explanation agreement in federated IDS.
2. We do **not** claim the broad "FL + IDS + XAI" combination as new; several 2025–2026 papers cover it.
3. We do **not** claim the α=0.1 below-floor result is significant. It is **directional, not significant**.
4. We do **not** claim heterogeneity *causes* lower agreement; the KL result is observational.
5. We do **not** claim ByzAgent beats Krum, Multi-Krum or trimmed mean.
6. We do **not** claim ByzAgent "explains its reasoning." It produces decisions plus a rationale of measured fidelity.
7. We do **not** claim any attack here is realistic; all are worst-case, full-knowledge.
8. We do **not** credit classical Krum with the 0% figure; it belongs to Multi-Krum.
9. We do **not** cite Multi-Krum's f=2 recovery (1.35) as attack mitigation.
10. We do **not** claim "33.8×–154.3×" is a detection threshold; it's a seed-42 effect-size ratio.
11. We do **not** claim the LLM summary sentences on the dashboard are research results.
12. We do **not** claim FedAvgM is a tuned optimum, or that it changes explanation agreement (untested).
13. We do **not** claim compression is harmless; the effect is unresolved at n=3.
14. We do **not** claim the faithfulness check covers every configuration; it's one spot-check.
15. We do **not** claim federated training ran on the GPU.
16. We do **not** blend the explanation check and the trust check into a single claim.
17. We do **not** report p-values for silo-level correlations.
