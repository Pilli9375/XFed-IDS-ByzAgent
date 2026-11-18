## Reference: Software, Models, Hardware and Tools {#sec:app-ref-tools}

This section lists everything the project used: every software package it imports or runs, every model, the hardware and what ran on it, and the development tools, including our disclosure of AI assistance. It supports Section 2.4 and Chapter 3.

### Software and libraries

@tab:sw-python lists the Python packages that the project's code imports or runs, with the version pinned in `requirements.txt` (the `xfed` environment) and, for the Flower runtime, in `federated/pyproject.toml`. @tab:sw-js lists the JavaScript packages of the dashboard, the showcase site and the film, with the version ranges given in their `package.json` files. Packages that are only dependencies of other packages are not listed.
<!-- src: requirements.txt; federated/pyproject.toml -->

Table: Python packages used, with versions and purpose {#tab:sw-python size=9.5}
| Package | Version | Used for |
|---|---|---|
| Python | 3.11.15 | Everything in the back end |
| PyTorch | 2.6.0+cu124 (xfed); 2.13.0 CPU build (Flower runtime) | The MLP: centralized training on the GPU, federated training on the CPU, SHAP, serving, hot swap |
| Flower (flwr) | 1.33.0 | Federated simulation, strategies (FedAvg, FedAvgM, FedAdam, FedYogi, Krum, MultiKrum, FedTrimmedAvg) |
| Ray | 2.55.1 | Execution engine behind Flower's simulation |
| NumPy | 2.4.6 | Arrays throughout |
| pandas | 3.0.3 (xfed); 3.0.5 (Flower runtime) | Tables and CSV results |
| PyArrow | 24.0.0 (xfed); 25.0.1 (Flower runtime) | Parquet files for the data and partitions |
| scikit-learn | 1.9.0 | Scalers, the group-aware split, F1 metrics |
| SciPy | 1.17.1 | Weighted Kendall's τ, Spearman correlation, statistics |
| SHAP | 0.51.0 | GradientExplainer and KernelExplainer |
| XGBoost | 3.2.0 | The centralized gradient-boosting reference |
| ONNX | 1.23.2 | Exporting the served model |
| ONNX Runtime | 1.31.0 | The default serving engine |
| FastAPI | 0.138.2 | The backend |
| Starlette | 1.3.1 | Web framework underneath FastAPI (gzip middleware) |
| Pydantic | 2.13.4 | Request and response models in the backend |
| Uvicorn | 0.49.0 | Server that runs the backend |
| Requests | 2.34.2 | The simulator's HTTP calls to the backend |
| PyYAML | 6.0.3 | Reading every configuration file |
| Matplotlib | 3.11.1 | Result and paper figures |
| Streamlit | 1.61.1 | The Phase 1 dashboard |
| Plotly | 6.9.0 | Charts in the Streamlit app |
<!-- src: docs/env_versions_2026-11-18.txt; requirements.txt; federated/pyproject.toml -->

Table: JavaScript packages used, with version ranges and purpose {#tab:sw-js size=9.5}
| Package | Version range | Used in | Used for |
|---|---|---|---|
| React, React DOM | ^19.2.8 | Dashboard | The user interface |
| React Router DOM | ^7.18.3 | Dashboard | The three routes |
| Vite, @vitejs/plugin-react | ^8.2.2, ^6.1.0 | Dashboard | Development server and build |
| oxlint | ^1.79.0 | Dashboard | Linting |
| React, React DOM | ^18.3.1 | Showcase site | The site |
| GSAP | ^3.15.0 | Showcase site | Animation |
| Lenis | ^1.3.26 | Showcase site | Smooth scrolling |
| Vite, @vitejs/plugin-react | ^8.3.3, ^6.1.2 | Showcase site | Build |
| Fontsource fonts (Alegreya, Atkinson Hyperlegible Mono, Brygada 1918, Schibsted Grotesk) | ^5.3.0 | Showcase site | Self-hosted fonts |
| Remotion | 4.0.533 | Explainer film | Rendering the film from code |
<!-- src: frontend/package.json; site/package.json; film/package.json -->

### Models

**The detector.** The MLP is described in full in Section 6.C (@tab:mlp-arch): 82 inputs, hidden layers of 128 and 64 units with LayerNorm, ReLU and dropout 0.1, 9 outputs, 19,849 trainable parameters.
<!-- src: configs/model.yaml; docs/efficiency_results.md -->

**XGBoost.** The gradient-boosting reference uses the settings in @tab:xgb: the multi-class soft-probability objective over 9 classes, histogram trees on the GPU, maximum depth 6 and the tuned learning rate, subsampling and regularization values.
<!-- src: configs/xgboost_tuned.json -->

**Language models.** Three locally run models were tried for ByzAgent (@tab:llm-select). Llama 3.1 8B instruct, 4-bit quantized (`llama3.1:8b-instruct-q4_K_M`), was picked because it was the only candidate that both produced valid output for every client and cited real numbers in most of its explanations. Qwen 2.5 7B instruct produced valid output but almost never cited real numbers, and Phi-3.5 corrupted client identifiers. All three fit within the 6 GB GPU. The same Llama model, run through Ollama, also writes the one-sentence alert summaries shown in the dashboard, which are a usability feature and not a research claim.
<!-- src: docs/contribution_b_results.md; configs/agent.yaml -->

### Hardware and what ran where

@tab:hw-where lists where each workload ran on the single laptop used for the whole project.

Table: Hardware and the workloads that ran on it {#tab:hw-where}
| Component | Specification | Workloads |
|---|---|---|
| GPU | NVIDIA RTX 4050, 6 GB (a hard ceiling) | Centralized MLP (baselines and pilots), XGBoost, Ollama for ByzAgent and the alert summaries |
| CPU | AMD Ryzen 7 7435HS, 8 cores, 16 threads | Federated training (Flower runtime, CPU build of PyTorch), SHAP, serving, hot-swap retraining |
| Memory | 24 GB RAM | All workloads |
| Operating system | Windows 11 | All workloads |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

### Development tools and AI assistance

The team used Git and GitHub for version control, the conda environment manager and pip for Python packages, Node.js and npm for the front ends, PowerShell on Windows, and Microsoft Word for exporting this report to PDF. The IEEE paper was typeset with LaTeX (the IEEEtran class).

**Disclosure of AI assistance.** An AI coding and writing assistant, Anthropic's Claude used through Claude Code, helped implement parts of the software and helped draft the project's documents, including this report, from the project's own result files, under the team's direction. The experiments, results and design decisions are the team's own work, carried out in the project repository. Safeguards were applied to the drafted text: every number is checked by a script against the results file it comes from, every reference was looked up and confirmed before it was cited, and the text was checked for 8-word overlap with the cited abstracts and the project's own documentation (Section 6.R). The team has read the full report and takes responsibility for its content.

## Reference: Algorithms, Metrics and the Attack {#sec:app-ref-methods}

This section explains, in plain terms and with its formula, every algorithm, metric and statistic the report uses, and describes the attack setup in full. It supports Sections 2.2 and 4.1 to 4.3. Formulas use w for model weights, n_i for silo i's number of training rows and n for their sum.
<!-- numcheck: ignore -->

### Algorithms

**Dirichlet partitioning.** For each class k, a vector of silo shares is drawn as p_k ~ Dir(α·1_N) over the N=10 silos, and silo i receives the fraction p_k[i] of class k. A small α puts most of a class in one or two silos; a large α spreads it almost evenly. This is how the project creates controlled non-IID data.
<!-- numcheck: ignore -->

**FedAvg** [@mcmahan2017]. In each round, every silo starts from the global weights w_t, trains locally for E epochs to get w_i, and the server averages the results weighted by data size: w_(t+1) = Σ_i (n_i / n) · w_i.
<!-- numcheck: ignore -->

**FedProx** [@li2020fedprox]. Each silo adds a proximal term to its local loss, which pulls its weights back toward the global model it received: minimise F_i(w) + (μ/2)·‖w − w_t‖². The server still averages as in FedAvg, so FedAvg is exactly the case μ=0.
<!-- numcheck: ignore -->

**FedAvgM** [@hsu2019]. The server treats the change produced by averaging as a gradient and applies momentum to it: v ← β·v + (w_t − w_avg), then w_(t+1) = w_t − η·v, where w_avg is the FedAvg average, β the server momentum and η the server learning rate (1.0 here).
<!-- numcheck: ignore -->

**FedAdam and FedYogi** [@reddi2021]. The server keeps Adam-style moment estimates of the averaged change Δ = w_avg − w_t: m ← β1·m + (1 − β1)·Δ, and v ← β2·v + (1 − β2)·Δ² for FedAdam, or v ← v − (1 − β2)·Δ²·sign(v − Δ²) for FedYogi. It then updates w_(t+1) = w_t + η·m / (√v + τ).
<!-- numcheck: ignore -->

**Krum and Multi-Krum** [@blanchard2017]. For each update w_i, Krum sums its squared distances to its n − f − 2 nearest other updates: s(i) = Σ_(j ∈ nearest) ‖w_i − w_j‖². Krum keeps the single update with the smallest score; Multi-Krum keeps the n − f updates with the smallest scores and averages them. Both assume that honest updates cluster together.
<!-- numcheck: ignore -->

**Coordinate-wise trimmed mean** [@yin2018]. For every parameter separately, the server sorts the n silo values, discards the largest and the smallest fraction β of them, and averages the rest. Here β = f/n.
<!-- numcheck: ignore -->

**SHAP** [@lundberg2017]. SHAP explains one prediction by giving each feature j an attribution φ_j such that the attributions add up to the difference between the model's output and its average output over a background sample: f(x) = E[f] + Σ_j φ_j. The attributions are Shapley values from cooperative game theory, the fair way to share a total among the players who produced it.
<!-- numcheck: ignore -->

**GradientExplainer** [@erion2021]. This estimates SHAP values for differentiable models with expected gradients: φ_j = E over background rows x′ and a ∈ U(0,1) of (x_j − x′_j) · ∂f(x′ + a(x − x′))/∂x_j. The expectation is estimated by sampling, here with 4000 samples per explanation.
<!-- numcheck: ignore -->

**KernelExplainer** [@lundberg2017]. This model-agnostic estimator fits a weighted linear model over random subsets (coalitions) z of the M features, weighting each coalition with the Shapley kernel π(z) = (M − 1) / (C(M, |z|) · |z| · (M − |z|)). It was used only to cross-check GradientExplainer.
<!-- numcheck: ignore -->

**Effective-number class weights** [@cui2019]. A class with n_c training rows gets a weight proportional to (1 − β) / (1 − β^(n_c)), so rare classes count more in the loss without the extreme weights of plain inverse frequency.
<!-- numcheck: ignore -->

### Metrics and statistics

@tab:metrics gives each metric's definition and where it is used.

Table: Metrics and statistics: definitions and where they are used {#tab:metrics size=9}
| Metric | Definition | Used in |
|---|---|---|
| Per-class F1 | F1_c = 2·P_c·R_c / (P_c + R_c), with precision P_c and recall R_c of class c | 4.1, 6.D |
| Macro-F1 | The unweighted mean of F1_c over the seven headline classes | Every accuracy result |
| Jaccard@k | J@k = \|A_k ∩ B_k\| / \|A_k ∪ B_k\| for the top-k feature sets of two rankings | 4.2, 6.E |
| Weighted Kendall's τ | Kendall's rank correlation with hyperbolic weights that count disagreements near the top more [@vigna2015] | 4.2, 6.E |
| Chance level | (k²/n) / (2k − k²/n), the approximate Jaccard of two random k-subsets of n features | 4.2, 6.E |
| Seed-noise floor | The median over the three centralized seed pairs of each pair's median agreement | 4.2, 6.E |
| Cluster bootstrap | Resample whole (seed, silo) clusters with replacement, recompute the median, and take the 2.5th and 97.5th percentiles [@fieldwelsh2007] | 4.2, 6.E |
| Spearman's ρ | The Pearson correlation of the ranks of two variables | 6.E, 6.F, 6.G |
| Partial correlation | The correlation of two variables after removing the linear effect of a third (here log silo size) from both | 4.2, 6.E |
| KL divergence | KL(p_i ‖ p) = Σ_c p_i,c · log(p_i,c / p_c), between a silo's and the global label mix | 4.2, 6.E |
| Label entropy | H(p_i) = −Σ_c p_i,c · log p_i,c | 4.2, 6.E |
| Glass's δ | (mean of the malicious group − mean of the clean group) / standard deviation of the clean group | 4.3, 6.G |
| Additivity residual | Absolute: max over classes of \|Σφ − (f(x) − E[f])\|; relative: that value divided by max over classes of \|f(x) − E[f]\| | 6.F |
| Deletion and insertion AUC | The area under the true-class probability as top-ranked features are removed (deletion) or added (insertion) [@petsiuk2018] | 6.E |
| Modified z-score | 0.6745·(x − median) / MAD, flagged above 3.5 [@iglewicz1993] | 6.E |
| Recovery fraction | (F_defended − F_poisoned) / (F_clean − F_poisoned), on the final-five mean; at least 0.5 counts as success | 4.3, 6.G |
| Flag rate and lift | The share of rounds in which a silo is downweighted or quarantined, and its increase over the same silo's clean-run rate | 4.3, 6.G |
<!-- numcheck: ignore -->

### The attack setup

The attack is label flipping, and it is always a worst-case construction, never a realistic one. @tab:attack-runs lists every attack configuration that was run. In each one, f malicious silos relabel a fraction of their own non-Benign training rows as Benign before local training. Their validation and test labels are never touched, and every flip is logged. In sudden mode the fraction is a constant 0.40 from round 1; in gradual mode it ramps as min(0.05 + 0.05(r − 1), 1) over rounds r=1 to 20. The attacker sets were chosen by a full search over all silo subsets, with knowledge of every silo's label mix, to maximise the weakest family's coverage; no deployed attacker would have that knowledge.
<!-- src: docs/contribution_b_results.md -->

Table: Attack configurations that were run (all at α=0.5, 10 silos, 20 rounds) {#tab:attack-runs size=9.5}
| Seed | f | Malicious silos | Mode | Purpose |
|:-:|:-:|---|---|---|
| 42 | 3 | {0,1,9} | Sudden | Retired size-representative rule (too weak) |
| 42 | 3 | {0,3,5} | Sudden | Locked primary worst-case attack |
| 42 | 2 | {0,3} | Sudden | Secondary worst-case attack |
| 42 | 3 | {0,3,5} | Gradual | Phase 4 temporal test |
| 1337 | 3 | {0,3,5} | Sudden | Multi-seed validation |
| 2024 | 3 | {0,3,5} | Sudden | Multi-seed validation |
<!-- src: docs/contribution_b_results.md -->

## Results Inventory {#sec:app-inventory}

This section lists the files under `results/` and `docs/` that hold results, with what each contains and the report section that uses it. Files the report does not use are marked, with the reason. It supports every results chapter.

Table: Results inventory: files under results/ {#tab:inventory-results size=9}
| Path | What it contains | Used in |
|---|---|---|
| `results/aggregated/*_headline.csv`, `*_per_family.csv` | Mean ± std of headline and per-class test F1 for FedAvg, centralized and XGBoost | 4.1, 6.D |
| `results/aggregated/federated_collapse.csv` | Families with near-zero recall per run | 6.D |
| `results/aggregated/round_lottery.csv` | Earlier test-based round lottery | Not used: superseded by the validation version |
| `results/aggregated/*.tex` | LaTeX copies of per-family tables | Not used: duplicates of the CSVs |
| `results/federated/round_lottery_val.csv` | Validation round lottery for all nine runs | 4.1, 6.D |
| `results/federated/epochs_provenance_val.json` | 1 against 3 local epochs on validation | 6.C, 6.J |
| `results/federated/<run>/` | Per run: round history, client statistics, agent decisions, checkpoints, configuration, final metrics | 4.1 to 4.3, 6.D, 6.G |
| `results/federated/*_ORIGINAL_BACKUP`, `*_CORRUPTED_CONCURRENT_RUN`, `fedavg_a0.1_s999*`, `smoke` | Backups, an aborted concurrent run, checkpoint-only folders and a smoke test | Not used: not results |
| `results/centralized/` | Centralized baselines per seed and the 14 pilot arms | 6.C, 6.D |
| `results/xgboost/` | XGBoost metrics per seed | 6.D |
| `results/pilots/*.csv` | Scaler, class-weight and architecture pilot tables | 6.C |
| `results/shap/` | SHAP values for every FedAvg and FedProx run, the centralized floor models and the validation pool | 4.2, 6.E, 6.F |
| `results/inspection/agreement_metrics*.csv` | Per-row agreement for FedAvg and FedProx | 4.2, 6.E |
| `results/inspection/centralized_instability_floor.csv` | Seed-noise floor rows | 4.2, 6.E |
| `results/inspection/round_wise_agreement*` | Round-wise agreement and its metadata | 6.E |
| `results/inspection/size_matched_heterogeneity.csv`, `silo_size*.csv`, `silo_sizes.csv` | Size, entropy, KL and agreement per silo | 4.2, 6.E |
| `results/inspection/parity_monitor*`, `parity_noise_floor*` | Parity-monitor results and the single-draw diagnostic | 6.E |
| `results/inspection/kernel_vs_gradient_validation.csv`, `common_background_ablation.csv`, `deletion_auc.csv`, `insertion_auc.csv` | Explainer, background and faithfulness checks | 6.E |
| `results/inspection/residual_*` | Residual audit, summary and sensitivity check | 4.2, 6.F |
| `results/inspection/best_rounds_manifest*.json` | Best round, validation and test score per run | 6.D, 6.E |
| `results/inspection/phase*`, `multiseed_*`, `frontier_*`, `silo_family_composition_*`, `attack_*`, `retro_replay_*`, `round_history_comparison_*`, `webattack_prediction_diff.json` | Trust-check gates, analyses, audits and attack diagnostics | 4.3, 6.G |
| `results/inspection/*.log`, `sweep_*`, `smoke_run_full_output.txt`, `precheck_C.txt`, `REPORT.md` | Console logs, sweep summaries and an early inspection note | Not used: logs behind files already cited |
| `results/inspection/raw_label_counts.csv`, `labels_per_file.csv`, `label_attempted_crosstab.csv`, `duplicates_by_label.csv`, `constant_features.csv`, `numeric_health.csv`, `file_checksums.csv` | Data-stage inspection tables | 6.A, through `data/README.md` |
| `results/attacks/`, `monitoring/`, `defenses/`, `agents/` | Phase 0 to 4 and multi-seed summaries, flip logs | 4.3, 6.G |
| `results/federated_methods/` | Preregistered study: runs, budget files, selection, sealed checkpoints, single test result, compression runs | 4.1, 6.H, 6.I |
| `results/efficiency/` | Serving, communication, compression and pre-screen results | 3.3, 4.4, 6.I |
| `results/figures/*.png` | Nine result figures | 6.E |
| `results/explanations/` | LLM alert summaries for the dashboard | 6.K (usability feature, no results drawn) |
| `results/partition_check.json` | Rows per silo for every partition | 6.B, 6.R |
| `results/val_split_report.json` | Validation split sizes and hash | 6.A |
| `results/near_duplicate_audit.json` | Nearest-neighbour audit per family | 6.E |
| `results/communication_cost.json` | Earlier communication estimate | Not used: superseded by `results/efficiency/communication.json` |
| `results/chat03_claims.md` | Early exploratory notes, including the FedProx test rationale | 6.C, 6.J (as disclosed provenance) |
<!-- src: docs/test_set_exposure_audit.md; PROJECT_INSTRUCTIONS.md -->

Table: Results inventory: files under docs/ {#tab:inventory-docs size=9}
| Path | What it contains | Used in |
|---|---|---|
| `docs/contribution_a_results.md` | Canonical explanation-check results | 4.2, 6.E, 6.F |
| `docs/contribution_b_results.md` | Canonical trust-check results | 4.3, 6.G |
| `docs/efficiency_results.md` | Efficiency results | 3.3, 4.4, 6.I |
| `docs/preregistration_accuracy.md` | The preregistration and its outcome | 4.1, 6.H |
| `docs/test_set_exposure_audit.md` | The test-set audit | 2.2, 6.J |
| `docs/measurement_protocol.md` | The explanation measurement protocol | 2.2, 6.E |
| `docs/env_versions_2026-11-18.txt` | Recorded environment versions | 2.4, 6.M |
| `docs/dashboard_v2/screens/` | Dashboard screenshots | 2.4, 6.K |
| `docs/dashboard_inventory/` | An earlier dashboard inventory | Not used: describes the replaced eight-page dashboard |
| `docs/handbook/` | The team handbook | 6.N |
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Testing and Checks {#sec:app-tests}

This section describes every automated check in the repository, what it verifies and its last recorded result. It supports Section 2.5. The repository has no unit-test suite; where a check's last result is not recorded in a file, the table says so.

Table: Automated checks, what each verifies and the last recorded result {#tab:checks size=9}
| Check | What it verifies | Last recorded result |
|---|---|---|
| Partition hash at load (`load_silo`) | The assignment array matches its SHA256 in the manifest; raises otherwise | Before the preregistered study, all 18 train and test assignments matched (`results/federated_methods/manifest_check.json`) |
| Partition summary (`scripts/check_partitions.py`) | Rows per silo, smallest and largest silo, silos below the size threshold | Recorded in `results/partition_check.json` |
| Group-aware split check | No feature vector is on both sides of the train/test split; raises otherwise | Passed when the split was made (data README) |
| Validation mask hash | The validation split is stored with its SHA-256 | Recorded in `results/val_split_report.json` |
| Backend start-up gate | The served model's validation macro-F1 equals the logged value, and ONNX predictions equal PyTorch's on every validation row | Passed with 0 differences on 143,513 rows; 50 of 50 sampled requests agreed |
| Hot-swap gate | A candidate replaces the served model only if its validation macro-F1 is at least the incumbent's | Enforced on every swap; rejected attempts change nothing and are not logged |
| Hot-swap audit log self-test (`tools/hotswap_log_selftest.py`) | The audit log's schema, writer and resolver | No result file; run by hand |
| Regression runs | Edited harness code reproduces a published validation curve | Identical at all 21 rounds, for both the method path and the compression path |
| Preregistered test-once script | The protocol is committed, every checkpoint hash matches, every validation score recomputes exactly, then a lock file is written | Passed once; the script is not run again |
| Phase verification gates (`scripts/phase*_verification_gate.py`) | Each trust-check phase meets its stated gate before the next | Recorded in `results/inspection/phase*_gate*.json` |
| Paper number check (`paper/number_check.py`) | Every number in the paper matches its source file | 2,279 of 2,279 numbers matched |
| Paper overlap check (`paper/overlap_check.py`) | No sentence shares an 8-word run with a cited abstract, the README or the handbook | 0 counted overlaps |
| Paper citation check | Every reference exists as cited | All 58 entries confirmed |
| Handbook number check | Every number in the handbook is found in a project file | 1,123 extracted; 0 not found |
| Site source-link checker (`site/scripts/check-sources.mjs`) | Every number's source link on the site resolves | No result file; run before deployment |
| Dashboard lint (`oxlint`) | JavaScript code quality | No result file |
| This report's number and overlap checks | Every number in this report matches its source; no copied sentences | `docs/report/number_check.md`, `docs/report/overlap_check.md` |
<!-- src: paper/number_check.md; docs/handbook/build/number_check.md; paper/citation_check.md; docs/efficiency_results.md; docs/preregistration_accuracy.md -->

## Key Code Excerpts {#sec:app-code}

This section shows short excerpts of the code behind the main steps, with the repository path of each. It supports Chapter 2. The excerpts are copied from the repository; long comments and logging lines are shortened, marked with "...".

### The client training step

@fig:code-train shows one silo's local training. The same function implements FedAvg and FedProx: when μ is zero, the proximal term vanishes.

Code: Client training step: local epochs with an optional FedProx term {#fig:code-train} [federated/xfed_federated/task.py]
```python
def local_train_epochs(model, splits, epochs, model_cfg, mu=0.0):
    X = torch.from_numpy(splits.X_train.copy()).to(DEVICE)
    y = torch.from_numpy(splits.y_train.copy()).to(DEVICE)
    weights = torch.from_numpy(splits.class_weights.copy()).to(DEVICE)
    global_params = ([p.detach().clone() for p in model.parameters()]
                     if mu > 0 else None)
    tr = model_cfg["training"]
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(tr["lr"]),
                                  weight_decay=float(tr["weight_decay"]))
    batch_size, n = int(tr["batch_size"]), len(y)
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n, device=DEVICE)
        total = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(X[idx]), y[idx])
            if mu > 0:
                prox = sum(((p - gp) ** 2).sum()
                           for p, gp in zip(model.parameters(), global_params))
                loss = loss + (mu / 2.0) * prox
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        epoch_loss = total / n
    return epoch_loss
```

### The SHAP explanation and the top-k export

@fig:code-shap computes one model's SHAP values and its additivity residual. @fig:code-topk turns a silo's per-row rankings into the single ordered top-k list that it sends to the server; only these feature indices cross the boundary.

Code: Explaining one model with GradientExplainer and measuring the additivity residual {#fig:code-shap} [tools/local_shap_pipeline.py]
```python
def explain_one_model(model, background_X, eval_X_scaled):
    background_t = torch.from_numpy(background_X.copy())
    eval_t = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, background_t)
    shap_values = explainer.shap_values(eval_t, nsamples=NSAMPLES)
    sv = np.array(shap_values)
    with torch.no_grad():
        f_eval = model(eval_t).numpy()
        f_bg_mean = model(background_t).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_eval - f_bg_mean[None, :])
    max_additivity_diff = float(np.abs(diff).max())
    return sv, max_additivity_diff, ...
```

Code: A silo's top-k export: per-row top-k sets combined by vote into one ordered list {#fig:code-topk} [tools/parity_monitor.py]
```python
def aggregate_topk_for_silo(shap_values, eval_y, eligible_mask, k):
    votes, rank_sum = Counter(), defaultdict(float)
    for idx in range(len(eval_y)):
        if not eligible_mask[idx]:
            continue
        true_class = int(eval_y[idx])
        vec = shap_values[idx, :, true_class]
        order = np.argsort(-np.abs(vec))[:k]
        for rank_pos, feat in enumerate(order):
            votes[int(feat)] += 1
            rank_sum[int(feat)] += rank_pos
    if not votes:
        return None
    def sort_key(feat):
        return (-votes[feat], rank_sum[feat] / votes[feat], feat)
    return sorted(votes.keys(), key=sort_key)[:k]
```

### The agreement metrics

@fig:code-agree shows the two agreement measures and the chance level. Weighted τ comes from SciPy, applied to the attribution vectors of the row's true class.

Code: Jaccard@k, the chance level and weighted Kendall's τ {#fig:code-agree} [tools/agreement_metrics.py]
```python
def jaccard_topk(a, b, k):
    """a, b: per-feature attribution vectors (signed). Top-k by |value|."""
    top_a = set(np.argsort(-np.abs(a))[:k])
    top_b = set(np.argsort(-np.abs(b))[:k])
    union = top_a | top_b
    return len(top_a & top_b) / len(union) if union else float("nan")

def chance_jaccard(k, n=N_FEATURES):
    """Expected Jaccard between two random k-subsets of n items."""
    exp_intersect = k * k / n
    return exp_intersect / (2 * k - exp_intersect)

# per evaluation row, true-class attribution vectors:
g_vec = global_sv[sample_idx, :, true_class]
s_vec = silo_sv[sample_idx, :, true_class]
tau_w, _ = weightedtau(g_vec, s_vec)          # scipy.stats.weightedtau
```

### ByzAgent: prompt summary and JSON schema

@fig:code-schema shows the JSON schema that Ollama enforces on every reply, and @fig:code-prompt the closing lines of the prompt. The opening part of the prompt, not repeated here, defines the five statistics, warns that this attack biases validation accuracy upward for malicious clients on a Benign-heavy validation set, and notes that natural non-IID differences can also move the statistics.

Code: ByzAgent's response schema {#fig:code-schema} [src/agents/byz_agent.py]
```python
DECISIONS = ("trust", "downweight", "quarantine")
DEFAULT_DOWNWEIGHT_MULTIPLIER = 0.3

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "round": {"type": "integer"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "decision": {"type": "string", "enum": list(DECISIONS)},
                    "explanation": {"type": "string"},
                },
                "required": ["client_id", "decision", "explanation"],
            },
        },
    },
    "required": ["round", "decisions"],
}
```

Code: Closing lines of ByzAgent's prompt template {#fig:code-prompt} [src/agents/byz_agent.py]
```text
For each client listed below, decide one of: trust, downweight, or
quarantine. Respond ONLY with a JSON object matching this schema, one
decision entry per client_id listed. In each explanation, cite the
specific numeric value(s) that informed this decision:
{"round": <int>, "decisions": [{"client_id": <string>, "decision":
"trust"|"downweight"|"quarantine", "explanation": <string>}]}

Round: {round_num}
Clients this round:
{client_block}
```

### The hot-swap gate

@fig:code-gate shows the non-regression gate. Every candidate round is scored on validation; the earliest round that reaches the incumbent's score is accepted, and if none does, the served model is left unchanged and nothing is logged.

Code: The hot-swap non-regression gate {#fig:code-gate} [src/hotswap/retrain.py]
```python
for r in range(1, num_rounds + 1):
    ...                                   # local training in every silo
    current_state = fedavg_aggregate(local_states, ns)
    candidate_metric = float(eval_global(current_state)[metric_key])
    round_candidates.append((r, current_state, candidate_metric))

# Strict non-regression gate, no tolerance: best candidate must be >=
# incumbent. Ties broken toward the EARLIEST round.
passing = [c for c in round_candidates if c[2] >= incumbent_metric]
if not passing:
    best_seen = max(m for _, _, m in round_candidates)
    raise HotSwapGateRejected(
        f"no candidate round cleared the gate: best {metric_name}="
        f"{best_seen:.4f} < incumbent {incumbent_metric:.4f} ... "
        f"Served model unchanged; nothing logged.")
best_round, best_state, best_metric = min(passing, key=lambda c: c[0])
```
