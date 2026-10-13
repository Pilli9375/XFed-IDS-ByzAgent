# Test-set exposure audit

**Date:** 2026-10-13. **Scope:** every way `data/processed/test_global.parquet`
(478,376 rows) was read by code in this repository, and which choices, if any,
were made from what it returned. Read-only audit; counts re-verified on disk on
2026-10-13 (branch `accuracy-prereg`).

## 1. Exposure table

| # | What | Files on disk | Test rows | Anything selected from it? | Source script |
|---|---|---|---|---|---|
| 1 | One test evaluation of each run's validation-selected checkpoint (headline numbers) | `final_metrics.json` key `test`: 24 under `results/federated/` (9 FedAvg, 9 FedProx μ=0.0005, 3 clean defense runs, `fedprox_mu0.01_a0.5_s42`, and the `ORIGINAL_BACKUP` / `CORRUPTED_CONCURRENT_RUN` copies), 3 Chat 03 exploratory runs under `federated/results/federated/`; `metrics.json` key `test`: 3 centralized baselines, 3 XGBoost seeds | all 478,376 per evaluation | No (the checkpoint was chosen on validation before this pass) | `federated/xfed_federated/server_app.py` (legacy path), `src/train/centralized.py`, `src/train/xgboost_baseline.py` |
| 2 | Centralized pilot runs, every arm test-scored | `results/centralized/pilot_*/metrics.json` (14 arms: 3 scaler, 5 class-weight, 6 architecture/dropout) plus `results/centralized/smoke` | all, per arm | **See §2**: arms ranked on validation, but some lock rationales cite the test column | `scripts/run_pilots.py` → `src/train/centralized.py` |
| 3 | Legacy client-side per-round scoring: each silo scored on its own local test rows every round | 35 `silo_metrics.jsonl` files with 200 `"phase": "evaluate"` rows each (10 silos × rounds 1–20): FedAvg and FedProx μ=0.0005 at all α/seeds, 5 poisoned FedAvg runs, Krum / Multi-Krum / trimmed-mean (clean, f=2, f=3), plus 3 extra folders (`fedavg_a0.1_s42` contaminated backup, `fedavg_a0.5_s42_poisoned_f3_sudden`, `fedprox…_CORRUPTED_CONCURRENT_RUN`) | each silo's test shard, every round | No. The only reader, `scripts/replay_client_stats.py`, uses train-phase rows only | `federated/xfed_federated/client_app.py::evaluate` (legacy path, `fraction_evaluate=1.0`) |
| 4 | Round-20 (final, unselected) checkpoint scored once per run | `final_metrics.json` key `test_final_round_unselected`, in all 27 files of row 1 | all | No selection; it fed the earlier round-lottery figure (`results/aggregated/round_lottery.csv`, max 0.1199 at α=0.5 seed 1337), now superseded by the validation-only `results/federated/round_lottery_val.csv` | `server_app.py` (legacy path); `scripts/aggregate_federated.py` |
| 5 | `site/public/data/baselines.json` field `test_macro_f1_headline_final_round` (row 4's value for the 3 clean defense runs; exported, never rendered) | removed from the site export 2026-10-13 (commit `2fcf8c4`); still in `final_metrics.json` | — | No | `tools/export_showcase_data.py` |
| 6 | SHAP explanation inputs: 14 fixed test rows (2 per headline family, `EVAL_SEED=12345`), explained at the selected round, at rounds 5/10/15/20 (round-wise agreement), and used by the parity monitor and the deletion/insertion faithfulness curves | `results/shap/**`, `results/inspection/*agreement*`, `parity_monitor*` | 14 (features; labels used only to stratify the draw and pick the explained class) | No. Inputs only, never a selection score | `tools/local_shap_pipeline.py`, `tools/round_wise_shap.py`, `tools/parity_monitor.py`, `tools/deletion_curve.py`, `tools/insertion_curve.py` |
| 7 | Display extractions: raw feature values of already-explained rows, for the demo dashboard | `results/shap/fedavg_a0.5_s42/eval_rows_sidecar.npz` (14 rows), `streamed_pool.npz` (500 rows) = 514 | 514 | No | `tools/build_shap_eval_sidecar.py`, `tools/build_shap_streamed_pool.py` |
| 8 | Dashboard simulator before 2026-10-13: replayed test rows to the backend, and each alert carried a per-alert match mark (true vs predicted family) | none. Alerts live in a 200-entry in-memory ring buffer (`configs/backend.yaml` `alerts.buffer_size`); log lines go to the console only | possible, not logged | No. No aggregate was ever computed or stored | `backend/simulator.py`, `backend/main.py`. Changed to replay validation by default in `ea59b83` on `master`/`readme`; that change is not on this branch yet |
| 9 | One preregistered re-evaluation of a single configuration selected on validation | `results/federated_methods/test_once/result.json` (9 sealed checkpoints of fedavgm_m0.9) | all, ×9 | No (selection, sealing and commit came first; see `docs/preregistration_accuracy.md`) | `tools/federated_method_test_once.py` |

Not test exposures (checked): hot-swap retraining (`src/hotswap/retrain.py`
never reads test), backend model loading (validation check only), XGBoost
tuning (`scripts/tune_xgboost.py` early-stops on validation), all ByzAgent
statistics (`client_stats.jsonl`: train loss, centralized validation, weight
geometry), the new method runs (`results/federated_methods/runs/`,
validation only), and `fedavg_a0.1_s999x` folders (checkpoints only).

## 2. Provenance of locked choices: which split chose them

| Choice | Record on disk | What the recorded decision cites | Validation-best arm/value | Test score used? |
|---|---|---|---|---|
| **3 local epochs** | comment in `federated/pyproject.toml` ("epochs=3 → macro-F1 0.9747, WebAttack recall 0.9436 (F1 0.9671)"; "Bot recall regressed 0.9430 → 0.7823") | These equal the **round-20 test score** of `results/federated/fedavg_a0.5_s42/final_metrics.json` `test_final_round_unselected` (0.9747 / 0.9436 / 0.9671 / Bot 0.7823). The epochs=1 run is not on disk | unknown (epochs=1 run not on disk) | **Yes** |
| **FedProx μ=0.0005** | `results/chat03_claims.md` §3, runs in `federated/results/federated/` | Test macro-F1: μ=0.0005 0.9794 vs FedAvg 0.9753 (α=0.5 s42); μ=0.01 0.7119 | μ=0.0005 also best on val (0.9787 vs FedAvg 0.9760, μ=0.01 0.7114) | **Yes** (as recorded; validation agrees) |
| **StandardScaler** (scaler pilot) | `results/pilots/scaler_comparison.csv`; `configs/model.yaml` comment | Test only: "standard 0.9924 vs robust_clipped 0.9228 vs robust 0.9179 (test macro-F1)" | standard (val 0.9941) | **Yes** (as recorded; validation agrees) |
| Class-weight β=0.999 | `results/pilots/weights_comparison.csv`; `configs/model.yaml` comment | Both: val 0.9941 and test 0.9924 | eff_999 (val 0.9941) | Mixed (both cited; validation agrees) |
| Architecture [128, 64] | `results/pilots/architecture_comparison.csv`; `configs/model.yaml` comment | Validation (top 4 arms within 0.0008 val) plus parameter count | h128_64_d01 (val 0.9939) | No |
| Dropout 0.1 | same pilot | "inside noise"; chosen arm is the validation-best arm | h128_64_d01 | No |
| 3 local epochs, re-checked on validation (2026-10-13) | `results/federated/epochs_provenance_val.json` | FedAvg α=0.5, best-by-validation val macro-F1, 1 vs 3 local epochs: seed 42 0.8644 vs 0.9760, seed 1337 0.8654 vs 0.9871, seed 2024 0.8508 vs 0.8644; mean 0.8602 vs 0.9425 | 3 epochs (all 3 seeds) | No (validation only, pre-registered as report-only) |
| Centralized pilot runs | `scripts/run_pilots.py` | Ranks on validation and prints "Select on the validation column"; also prints test "to confirm the ranking" | — | All 14 arms test-scored (row 2) |
| Stopping epoch (centralized, XGBoost) / best round (federated) | `src/train/centralized.py`, `scripts/tune_xgboost.py`, harness `global_evaluate` | Validation | — | No |

**Outcome:** two locked choices (3 local epochs; FedProx μ=0.0005) and the
scaler's written rationale rest on test scores, as recorded. Re-checked on
validation, all three are the validation-preferred values: μ and the scaler
from the existing pilot and exploratory runs, local epochs from the 2026-10-13
check above (3 epochs beat 1 at α=0.5 in every seed, mean 0.9425 vs 0.8602;
pre-registered as report-only, nothing locked changed). The sentence "No
model selection, stopping round, hyperparameter or method choice used any
test score" was therefore not used; the planning chat replaced it with the
disclosure now in `README.md`, `PROJECT_INSTRUCTIONS.md` and
`docs/contribution_a_results.md`, which names these three choices.
