## Model and Training Choices {#sec:app-model}

This section records the architecture, the training settings, the pilot runs and alternatives behind every locked choice, and the provenance of three choices first justified with test numbers. It supports Section 2.2.3 and the accuracy results of Section 4.1.

### Architecture

The detector is a feed-forward network defined in `src/models/mlp.py` (@tab:mlp-arch). Normalization is fixed to LayerNorm: the model refuses any other value, because BatchNorm's running statistics would be averaged across silos whose input distributions differ by construction. Softmax is applied by the loss, not by the model, which returns raw logits. Construction is seeded, so every silo starts from identical weights in round 0.
<!-- src: configs/model.yaml -->

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

### Training settings

@tab:train-settings lists the training settings from `configs/model.yaml`. The centralized runs use early stopping on validation macro-F1; the federated runs use a fixed number of rounds and keep the best round by the same metric.

Table: Training settings for centralized and federated runs {#tab:train-settings}
| Setting | Value |
|---|---|
| Optimizer | AdamW, learning rate 0.001, weight decay 0.0001 |
| Batch size | 1024 |
| Loss | Cross-entropy with effective-number class weights, β=0.999 |
| Centralized: maximum epochs | 50 |
| Centralized: early stopping | On validation macro-F1 (headline), patience 5 |
| Centralized: learning-rate schedule | Halve on plateau of validation macro-F1, patience 3 |
| Federated: rounds and local epochs | 20 rounds, 3 local epochs, all 10 silos every round |
| Federated: scaler | StandardScaler fit in each silo on its own training rows |
| Validation set | 10% of the training pool, seed 42, held out of every silo |
| Seeds | 42, 1337, 2024 |
<!-- src: configs/model.yaml; federated/pyproject.toml; PROJECT_INSTRUCTIONS.md -->

### Pilot runs

The locked choices were made with centralized pilot runs, compared by their validation macro-F1 on the seven headline classes (@tab:pilots). The pilots were also scored on the test set during development; that exposure is disclosed in Section 6.J, and the test values are not used here.

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

Both robust scalers break down because, for 28 features out of 82, the interquartile range is zero, so those features end up unscaled or degenerate. The four best architectures are separated by no more than 0.0008 on validation, and the smallest of them, [128, 64] with dropout 0.1, was chosen.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/test_set_exposure_audit.md -->

### Alternatives tried and rejected

@tab:alternatives collects every alternative that was tried or considered for the model and training stage, with the reason it was not kept.

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

### Provenance of choices first justified with test numbers

For three choices, the first written rationale quoted test-set scores. @tab:provenance repeats each comparison on validation; the same value wins every time. For local epochs, the run with one epoch was not on disk when the audit was made, so the comparison was redone on validation on 2026-10-13 and recorded as report-only, with nothing locked allowed to change.
<!-- src: docs/test_set_exposure_audit.md -->

Table: Provenance of locked choices: recorded rationale and validation re-check {#tab:provenance size=9.5}
| Choice | Recorded rationale | Validation re-check |
|---|---|---|
| 3 local epochs | Round-20 test score of `fedavg_a0.5_s42`: macro-F1 0.9747, WebAttack recall 0.9436 | 3 epochs beat 1 at α=0.5 in every seed: 0.9760 against 0.8644, 0.9871 against 0.8654, 0.8644 against 0.8508; mean 0.9425 against 0.8602 |
| FedProx μ=0.0005 | Test 0.9794 against FedAvg 0.9753 (α=0.5, seed 42); μ=0.01 gave 0.7119 | Validation 0.9787 against FedAvg 0.9760; μ=0.01 gave 0.7114 |
| StandardScaler | Test: standard 0.9924, robust-clipped 0.9228, robust 0.9179 | Validation: standard 0.9941, the best arm |
| Class weights β=0.999 | Validation 0.9941 and test 0.9924 both cited | Best arm on validation |
| Architecture and dropout | Validation only | Best arm on validation (0.9939) |
<!-- src: docs/test_set_exposure_audit.md -->

### XGBoost settings

The XGBoost reference was tuned with 40 trials of a hyperparameter search on a 300,000-row subsample of the training data, scored on validation, and then refit on the full data. @tab:xgb gives the selected settings exactly as stored. The search score itself is not a reportable result, because it came from the subsample.
<!-- src: configs/xgboost_tuned.json -->

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

## Federated Accuracy, Full Results {#sec:app-accuracy}

This section lists every FedAvg run, the centralized references per seed, the per-class results including the two below-floor classes, and the families that collapse under skew. It supports Section 4.1.

### All nine FedAvg runs and the round lottery

@tab:fedruns gives, for each run, the round with the best validation score, that score, the single test score of that checkpoint, and the round-20 validation score. The gap column is the round lottery: the amount that reporting round 20 instead of the best validated round would change the result. It reaches 0.1184 (α=5.0, seed 42) and 0.1172 (α=0.5, seed 1337).
<!-- src: results/federated/round_lottery_val.csv -->

Table: Every FedAvg run: the round chosen on validation, that round's validation and test macro-F1, the validation score at round 20, and the difference {#tab:fedruns}
| α | Seed | Best round | Validation | Test | Validation, round 20 | Gap |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 0.1 | 42 | 20 | 0.5440 | 0.5426 | 0.5440 | 0.0000 |
| 0.1 | 1337 | 16 | 0.4551 | 0.4481 | 0.4181 | 0.0370 |
| 0.1 | 2024 | 16 | 0.5694 | 0.5572 | 0.5565 | 0.0129 |
| 0.5 | 42 | 18 | 0.9760 | 0.9753 | 0.9745 | 0.0014 |
| 0.5 | 1337 | 11 | 0.9871 | 0.9866 | 0.8699 | 0.1172 |
| 0.5 | 2024 | 17 | 0.8644 | 0.8605 | 0.8492 | 0.0152 |
| 5.0 | 42 | 18 | 0.9898 | 0.9900 | 0.8713 | 0.1184 |
| 5.0 | 1337 | 18 | 0.9898 | 0.9905 | 0.9866 | 0.0032 |
| 5.0 | 2024 | 20 | 0.9913 | 0.9889 | 0.9913 | 0.0000 |
<!-- src: results/federated/round_lottery_val.csv; results/inspection/best_rounds_manifest.json -->

Before this table existed, the same comparison had been made with test scores of the round-20 checkpoints, which no rule had selected; the largest gap there was 0.1199, at α=0.5, seed 1337. The validation version above replaces it, and the old one is mentioned only for the record.
<!-- src: docs/contribution_a_results.md -->

### Centralized references per seed

@tab:central-seed gives the two centralized references per seed. If the two classes below the floor are added to the average, the mean macro-F1 over seeds becomes 0.9695 for the centralized MLP and 0.9752 for XGBoost.
<!-- src: results/aggregated/centralized_headline.csv; results/aggregated/xgboost_headline.csv -->

Table: Centralized references per seed: test macro-F1 over 7 classes, with validation in brackets {#tab:central-seed}
| Seed | Centralized MLP | XGBoost |
|:-:|:-:|:-:|
| 42 | 0.9931 [0.9947] | 0.9947 [0.9962] |
| 1337 | 0.9886 [0.9942] | 0.9946 [0.9967] |
| 2024 | 0.9884 [0.9946] | 0.9945 [0.9953] |
| Mean ± std | 0.9900 ± 0.0022 | 0.9946 ± 0.0001 |
<!-- src: results/centralized/baseline_s42/metrics.json; results/centralized/baseline_s1337/metrics.json; results/centralized/baseline_s2024/metrics.json; results/xgboost/xgb_s42/metrics.json; results/xgboost/xgb_s1337/metrics.json; results/xgboost/xgb_s2024/metrics.json; PROJECT_INSTRUCTIONS.md -->

### Per-class results

@tab:perclass gives per-class test F1 for every model, including Infiltration and Heartbleed, which are reported per class only. With FedAvg at α=0.1, the model hardly ever detects Bot or WebAttack, and its results for BruteForce, DoS and PortScan change sharply between seeds.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Table: Per-class test F1: mean over 3 seeds (FedAvg also shows the standard deviation) {#tab:perclass size=9.5}
| Class | FedAvg α=0.1 | FedAvg α=0.5 | FedAvg α=5.0 | Centralized MLP | XGBoost |
|---|:-:|:-:|:-:|:-:|:-:|
| Benign | 0.9449 ± 0.0130 | 0.9984 ± 0.0004 | 0.9993 ± 0.0000 | 0.9973 | 0.9996 |
| Bot | 0.1253 ± 0.1003 | 0.9404 ± 0.0410 | 0.9696 ± 0.0012 | 0.9733 | 0.9804 |
| BruteForce | 0.5730 ± 0.4182 | 0.9929 ± 0.0023 | 0.9954 ± 0.0002 | 0.9972 | 0.9978 |
| DDoS | 0.9976 ± 0.0018 | 0.9998 ± 0.0001 | 0.9999 ± 0.0001 | 1.0000 | 1.0000 |
| DoS | 0.6025 ± 0.4308 | 0.9947 ± 0.0047 | 0.9979 ± 0.0000 | 0.9981 | 0.9987 |
| PortScan | 0.3197 ± 0.4521 | 0.9965 ± 0.0005 | 0.9974 ± 0.0000 | 0.9813 | 0.9987 |
| WebAttack | 0.0490 ± 0.0693 | 0.6627 ± 0.4207 | 0.9691 ± 0.0058 | 0.9831 | 0.9870 |
| Infiltration (per class only) | 0.0000 ± 0.0000 | 0.3767 ± 0.0669 | 0.4362 ± 0.0502 | 0.7954 | 0.8148 |
| Heartbleed (per class only) | 0.3333 ± 0.4714 | 0.6000 ± 0.4320 | 0.9524 ± 0.0673 | 1.0000 | 1.0000 |
<!-- src: results/aggregated/federated_per_family.csv; results/aggregated/centralized_per_family.csv; results/aggregated/xgboost_per_family.csv -->

### Families that collapse

@tab:collapse lists every (run, family) pair whose test recall is essentially zero. Seven of the eight collapses are at α=0.1. The one at α=0.5 is WebAttack in seed 2024, which explains that run's weak macro-F1 of 0.8605.
<!-- src: results/aggregated/federated_collapse.csv; results/inspection/best_rounds_manifest.json -->

Table: Families with near-zero test recall in FedAvg runs {#tab:collapse}
| α | Seed | Family | Recall | Precision | Test support |
|:-:|:-:|---|:-:|:-:|---:|
| 0.1 | 42 | Bot | 0.0 | 0.0 | 1,176 |
| 0.1 | 42 | PortScan | 0.0 | 0.0 | 46,540 |
| 0.1 | 1337 | BruteForce | 0.0 | 0.0 | 1,743 |
| 0.1 | 1337 | DoS | 0.00002 | 1.0 | 44,373 |
| 0.1 | 1337 | WebAttack | 0.0 | 0.0 | 514 |
| 0.1 | 2024 | PortScan | 0.0 | 0.0 | 46,540 |
| 0.1 | 2024 | WebAttack | 0.0 | 0.0 | 514 |
| 0.5 | 2024 | WebAttack | 0.0350 | 1.0 | 514 |
<!-- src: results/aggregated/federated_collapse.csv -->
