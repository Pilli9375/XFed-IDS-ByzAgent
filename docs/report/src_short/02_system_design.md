# XFed-IDS-ByzAgent: System Design and Methodology

This chapter describes the proposed system, how each stage works, the standards it relies on, and its software and hardware.

## Proposed System {#sec:proposed}

@fig:pipeline shows the five stages. The **data** stage cleans the corrected flows into eight attack families plus Benign and splits them once. In **federated training**, ten silos receive label-skewed shares of the training pool and train one multilayer perceptron with FedAvg; each run keeps its best round on validation. The **explanation check** has each silo explain its own model with SHAP and send only its top-ranked feature indices to the server. The **trust check** logs five statistics per silo and round and lets either ByzAgent or a classical robust rule weight the updates. The **dashboard** shows alerts, explanations and trust decisions to an analyst.

![Pipeline of the system; the explanation check (stage 3) and trust check (stage 4) run as separate experiments on shared training runs](docs/report/figs/fig_pipeline.png){#fig:pipeline width=11}

## Working Methodology {#sec:methodology}

### Data, partitioning and model {#sec:m-data}

The Distrinet CICIDS2017 release (version 4) [@liu2022] holds 2,099,976 raw flows with 82 numeric features once identifier columns are removed. Cleaning removed three kinds of rows: 5 with non-finite values, 44,005 whose identical feature vectors carried different families, and 142,464 duplicated across capture days. That leaves 1,913,502 flows in eight attack families plus Benign. Two families, Infiltration (66 flows) and Heartbleed (11), are below a 1,000-flow floor; they appear in per-class results only. A group-aware split keeps identical feature vectors on one side and gives 1,435,126 training-pool and 478,376 test flows; 143,513 training-pool rows form a centralized validation set that no silo trains on.
<!-- src: data/README.md; docs/efficiency_results.md -->

@tab:split gives each family's count after cleaning and how the grouped split divided it.

Table: Family counts after cleaning, and their division by the grouped split {#tab:split}
| Family | Flows | Training pool | Test | Test share (%) |
|---|---:|---:|---:|---:|
| Benign | 1,440,899 | 1,080,674 | 360,225 | 25.0 |
| PortScan | 186,160 | 139,620 | 46,540 | 25.0 |
| DoS | 177,491 | 133,118 | 44,373 | 25.0 |
| DDoS | 95,144 | 71,358 | 23,786 | 25.0 |
| BruteForce | 6,972 | 5,229 | 1,743 | 25.0 |
| Bot | 4,703 | 3,527 | 1,176 | 25.0 |
| WebAttack | 2,056 | 1,542 | 514 | 25.0 |
| Infiltration (below floor) | 66 | 50 | 16 | 24.2 |
| Heartbleed (below floor) | 11 | 8 | 3 | 27.3 |
| Total | 1,913,502 | 1,435,126 | 478,376 | 25.0 |
<!-- src: data/README.md -->

Each family's share per silo is drawn from a Dirichlet distribution with α ∈ {0.1, 0.5, 5.0} and seeds 42, 1337 and 2024, nine partitions in all; α=5.0 is the near-IID control. Row-to-silo assignments are saved with a SHA256 manifest that is checked whenever a silo is loaded. The detector is an MLP with hidden layers of 128 and 64 units, LayerNorm and dropout 0.1 (19,849 parameters), trained with AdamW for 20 FedAvg rounds of 3 local epochs in Flower [@beutel2020flower]. @tab:locked lists the locked settings.
<!-- src: PROJECT_INSTRUCTIONS.md; data/README.md; docs/efficiency_results.md; federated/pyproject.toml -->

Table: Locked model and training settings {#tab:locked}
| Setting | Reason |
|---|---|
| StandardScaler | RobustScaler degenerates on 28 of 82 zero-IQR features |
| Effective-number class weights, β=0.999 [@cui2019] | Best validation score in the weighting pilot |
| LayerNorm instead of BatchNorm | BatchNorm statistics do not average across silos |
| 3 local epochs | Validation prefers 3 over 1 at α=0.5 in all three seeds |
| All 10 silos train every round | The size floor applies only to explanation eligibility |
| Best-by-validation round | Rounds of one run differ by up to 0.118 in validation macro-F1 |
<!-- src: PROJECT_INSTRUCTIONS.md -->

@tab:mlp-arch lists the layers of the detector, and @tab:pilots the centralized pilot runs, ranked on validation, behind the locked choices.

Table: Layers of the MLP detector {#tab:mlp-arch}
| Order | Layer | Size |
|:-:|---|---|
| 1 | Linear | 82 inputs to 128 units |
| 2 | LayerNorm, ReLU, Dropout 0.1 | 128 units |
| 3 | Linear | 128 to 64 units |
| 4 | LayerNorm, ReLU, Dropout 0.1 | 64 units |
| 5 | Linear (output logits) | 64 to 9 classes |
| | Total trainable parameters | 19,849 |
<!-- src: configs/model.yaml; docs/efficiency_results.md -->

Table: Centralized pilots: validation macro-F1 (7 headline classes) and best epoch {#tab:pilots}
| Pilot | Arm | Validation macro-F1 | Best epoch |
|---|---|:-:|:-:|
| Scaler | StandardScaler | 0.9941 | 15 |
| Scaler | RobustScaler | 0.9195 | 4 |
| Scaler | RobustScaler with clipping | 0.9232 | 20 |
| Class weights | None | 0.9899 | 8 |
| Class weights | Inverse square root | 0.9741 | 11 |
| Class weights | Effective number, β=0.999 | 0.9941 | 15 |
| Class weights | Effective number, β=0.9999 | 0.9898 | 5 |
| Class weights | Effective number, β=0.99999 | 0.9617 | 12 |
| Architecture | [128, 64], dropout 0.1 | 0.9939 | 18 |
| Architecture | [128, 64], dropout 0.3 | 0.9931 | 19 |
| Architecture | [256, 128], dropout 0.1 | 0.9912 | 8 |
| Architecture | [256, 128], dropout 0.3 | 0.9878 | 5 |
| Architecture | [512, 256, 128], dropout 0.1 | 0.9936 | 18 |
| Architecture | [512, 256, 128], dropout 0.3 | 0.9938 | 18 |
<!-- src: results/pilots/scaler_comparison.csv; results/pilots/weights_comparison.csv; results/pilots/architecture_comparison.csv; docs/preregistration_accuracy.md; docs/handbook/XFed_Team_Handbook.md; configs/model.yaml -->

@tab:alternatives records the alternatives that were tried and rejected, and @tab:xgb the settings of the XGBoost reference, tuned on validation.

Table: Alternatives tried or considered, and why each was rejected {#tab:alternatives size=9.5}
| Alternative | Outcome | Reason |
|---|---|---|
| RobustScaler, with or without clipping | Rejected | Degenerates on 28 zero-IQR features; validation 0.9195 and 0.9232 against 0.9941 |
| BatchNorm | Rejected by design | Running statistics are per-silo and do not average meaningfully under FedAvg |
| SMOTE oversampling | Rejected by design | Needs per-silo neighbours that small silos lack; breaks linked features; adds synthetic rows to the explanation comparison |
| No class weights, or inverse-square-root weights | Rejected | Validation 0.9899 and 0.9741 against 0.9941 |
| Effective-number weights with β=0.9999 or 0.99999 | Rejected | Validation 0.9898 and 0.9617 |
| Wider or deeper MLPs, dropout 0.3 | Not kept | Tie with the smallest arm on validation; more parameters |
| 1 local epoch | Rejected | Validation prefers 3 epochs at α=0.5 in all three seeds (mean 0.9425 against 0.8602) |
| FedProx μ=0.01 | Rejected | Collapsed at α=0.5, seed 42 (validation 0.7114) |
| DeepExplainer for SHAP | Rejected | Additivity error 2.43 on LayerNorm |
<!-- src: results/pilots/scaler_comparison.csv; results/pilots/weights_comparison.csv; PROJECT_INSTRUCTIONS.md; docs/test_set_exposure_audit.md; docs/handbook/XFed_Team_Handbook.md; configs/model.yaml -->

Table: Selected XGBoost settings {#tab:xgb}
| Parameter | Value |
|---|---|
| Objective | multi:softprob, 9 classes |
| Tree method, device | hist, cuda |
| Maximum depth | 6 |
| Learning rate | 0.11796150167282794 |
| Row subsample | 0.9182067803770825 |
| Column subsample per tree | 0.8416043884786937 |
| Minimum child weight | 1 |
| L2 regularization (lambda) | 0.06815110776728935 |
| L1 regularization (alpha) | 0.006398213811114084 |
| Search seed | 42 |
<!-- src: configs/xgboost_tuned.json -->

### The explanation check {#sec:m-expl}

Because DeepExplainer breaks on LayerNorm, with an additivity error of 2.43, each silo uses SHAP's GradientExplainer [@lundberg2017] with a class-balanced 200-row background from its own data. All models explain the same 14 rows, using the attribution of each row's true class, and only top-k feature indices leave a silo. Agreement with the global model is measured by Jaccard@10 and by weighted Kendall's τ [@vigna2015]. Two references give these values meaning: the chance Jaccard@10 for random feature sets, 0.065, and a seed-noise floor, the agreement between three centralized models trained with different seeds. Uncertainty at α=0.1 comes from a cluster bootstrap over (seed, silo) clusters [@fieldwelsh2007], and correlations are given as r and n without p-values, because silos of one run are not independent.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/measurement_protocol.md -->

### The trust check {#sec:m-trust}

The attack runs at α=0.5 and seed 42: from round 1, each of f malicious silos marks 40% of its non-Benign training rows as Benign. The attacker sets, {0,3,5} for f=3 and {0,3} for f=2, were found by searching all 120 three-silo subsets for the strongest coverage of every attack family, which requires knowing each silo's label mix. The attack is therefore worst-case: an upper bound on what detection must handle, not a model of a real attacker. The server records five statistics per silo and round: the size of the update, how closely the update points toward the aggregate and toward the average update, the training loss, and accuracy on the validation set.
<!-- src: docs/contribution_b_results.md -->

@tab:five-stats defines the five statistics.

Table: The five per-silo statistics recorded each round {#tab:five-stats}
| Statistic | What it measures |
|---|---|
| update_norm | L2 distance between the silo's trained weights and the previous global weights |
| cosine_to_global | Cosine similarity between the silo's update and this round's aggregate |
| cosine_to_peer_mean | Cosine similarity to the unweighted mean of all silos' updates |
| train_loss | The silo's last-epoch local training loss |
| val_accuracy | Accuracy of the silo's trained model on the centralized validation set |

ByzAgent is a local Llama 3.1 8B instruct model [@grattafiori2024llama3], run through Ollama at temperature 0.2. Each round it receives the five statistics of all silos, with a warning that this attack inflates a malicious silo's validation accuracy, and must reply in a fixed JSON schema with trust, downweight (0.3 of normal weight) or quarantine for each silo, plus reasons quoting the numbers used. It never sees f or the attackers' identities, and its decisions were replayed on logged statistics. Krum, Multi-Krum and trimmed mean [@blanchard2017; @yin2018] serve as baselines and are given the true f as an oracle. Attack strength is summarised by the mean, median, final-five mean and maximum of validation macro-F1.
<!-- src: configs/agent.yaml; docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

### Preregistration and test-set use {#sec:m-testuse}

A comparison of federated optimizers was preregistered: candidates were compared on validation only, the winner's nine checkpoints were sealed by SHA256, and they were scored on the test set once. Every model and round in the project was chosen on validation, and headline test values come from one evaluation of each validation-selected checkpoint. We disclose that three early choices (3 local epochs, FedProx μ=0.0005 and the StandardScaler) were first justified with test scores; repeated on validation, each comparison picks the same value. Other reads of the test set did not inform any later choice. By a team rule adopted on 2026-10-12, only the preregistered configuration may be tested from then on; the full audit is in `docs/test_set_exposure_audit.md`.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/preregistration_accuracy.md -->

## Standards {#sec:standards}

@tab:standards lists the standards the project uses.

Table: Standards used in the project {#tab:standards}
| Standard | Where it is used |
|---|---|
| IEEE 754 binary32 and binary16 | Model weights and traffic counts in fp32; one compression scheme sends fp16 updates |
| ONNX model format | The served model runs in ONNX Runtime |
| SHA-256 (FIPS 180-4) | Partition manifest, sealed preregistered checkpoints, hot-swap audit log |
| HTTP and REST with OpenAPI | The FastAPI backend and its published interface description |
| JSON and JSON Schema | ByzAgent's enforced reply format; results and logs |
| WCAG contrast (level AA) | Text contrast on the dashboard and showcase site |
| IEEE reference style | References in this report and the project paper |

## System Details {#sec:system-details}

### Software details {#sec:software}

All federated runs use the Flower app in `federated/xfed_federated/`, started with `flwr run federated local-simulation`; after every round its server records the validation score, the five statistics of each client and the number of bytes exchanged. Analysis tools for SHAP, agreement, the parity monitor and efficiency live in `tools/`, and every parameter is read from YAML files in `configs/`. A FastAPI backend serves the deployed model (`fedavg_a0.5_s42`, round 18, validation macro-F1 0.9760) through ONNX Runtime and refuses to start unless the model reproduces its logged validation score. A React dashboard has three routes: Live (@fig:dash-live), Investigate and Limits; every displayed number links to its source file. Alerts come from a simulator that replays validation rows only. From an alert, an analyst can trigger hot-swap retraining (@fig:dash-hotswap); the retrained model replaces the served one only if its validation macro-F1 is at least as high. @tab:tools lists the main tools.
<!-- src: PROJECT_INSTRUCTIONS.md -->

@tab:endpoints lists the backend's endpoints.

Table: Backend endpoints {#tab:endpoints size=9.5}
| Endpoint | Purpose |
|---|---|
| `GET /health` | Status, with the number of validation rows verified at start-up |
| `GET /config` | The served model, engine, class and feature names, and the hot-swap state |
| `POST /predict` | Score one flow (ONNX Runtime fp32 by default) |
| `GET /shap/{sample_id}` | Stored SHAP values for an alert's row |
| `GET /explain/{sample_id}` | The stored one-sentence LLM summary for an alert's row |
| `GET /alerts` | Recent alerts posted by the simulator |
| `GET /agreement`, `GET /agreement/summary` | Explanation-check results and their summary, with the bootstrap interval and chance level |
| `GET /parity` | Parity-monitor results |
| `GET /trust` | Trust-check results: per-round statistics, agent decisions and explanations, baselines and the fidelity audit |
| `GET /federation` | Run metadata for the federation |
| `GET /accuracy` | Accuracy tables |
| `GET /faithfulness` and its two curve images | Deletion and insertion results |
| `GET /figures` | The result figures |
| `GET /limits` | The known limitations, read from the project instructions |
| `POST /hotswap/trigger`, `GET /hotswap/status`, `POST /hotswap/revert` | Analyst-driven retraining, its status, and a one-call revert |
| `GET /source/{path}` | The source file behind a displayed number, from an allow-list |

![Dashboard, Live route: flow stream, selected alert with SHAP contributions and LLM summary, and trust panel](docs/dashboard_v2/screens/live_deep-sea_1440.png){#fig:dash-live width=15.5}

![Hot-swap dialog after a rejected candidate: the validation gate kept the served model](docs/dashboard_v2/screens/hotswap_rejected_detail_deep-sea.png){#fig:dash-hotswap width=12}

Table: Main implementation tools and versions {#tab:tools}
| Component | Tool and version |
|---|---|
| Language | Python 3.11.15 |
| Federated training (CPU) | PyTorch 2.13.0 (CPU build), Flower 1.33.0 |
| Centralized MLP (GPU) | PyTorch 2.6.0+cu124 |
| Explanations | SHAP 0.51.0 |
| Baseline | XGBoost 3.2.0 |
| Serving | ONNX Runtime 1.31.0, FastAPI 0.138.2 |
| Trust agent | Ollama 0.40.16, llama3.1:8b-instruct-q4_K_M |
| Dashboard | React 19.2.8 |
<!-- src: docs/env_versions_2026-11-18.txt; federated/pyproject.toml; requirements.txt; frontend/package.json; configs/agent.yaml -->

### Hardware details {#sec:hardware}

Everything ran on one laptop with an NVIDIA RTX 4050 (6 GB), 24 GB of RAM, an AMD Ryzen 7 7435HS CPU and Windows 11. Centralized MLP training, XGBoost and Ollama used the GPU; federated training ran on the CPU, because Flower's isolated runtime uses the CPU build of PyTorch, and SHAP, serving and hot-swap retraining also ran on the CPU.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

## Testing and Verification {#sec:testing}

The repository has no unit-test suite. It relies instead on a set of checks built into the pipeline and on standalone verification scripts, summarised in @tab:checks-summary.

Table: Checks that guard the pipeline {#tab:checks-summary}
| Check | What it guards |
|---|---|
| SHA256 partition manifest | A silo is never loaded from a changed or corrupted assignment array |
| Group-aware split check | No feature vector appears in both the training pool and the test set |
| Backend start-up gate | The served model reproduces its logged validation score, and ONNX predictions match PyTorch on every validation row |
| Hot-swap gate and audit log | A retrained model replaces the served one only if it does not lose validation macro-F1, and every swap is logged with its seed and hash |
| Regression runs | Edited training code reproduces a published validation curve exactly |
| Phase verification gates | Each trust-check phase passes a stated gate before the next phase starts |
| Number, citation and overlap checks | Every number in the paper and this report matches its source file; every reference is verified; no sentence copies a source |
