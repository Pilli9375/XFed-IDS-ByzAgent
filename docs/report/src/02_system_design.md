# XFed-IDS-ByzAgent: System Design and Methodology

This chapter describes the proposed system, the working methodology of each stage, the standards the project relies on, the software and hardware details, and the checks used to test the system. The full detail behind each part is collected in the appendix, and each section points to the relevant appendix section.

## Proposed System {#sec:proposed}

XFed-IDS-ByzAgent is one system built in five stages, shown in @fig:pipeline. Each stage feeds the next, and the two checks in the middle share the same federated training runs.

![The five stages of XFed-IDS-ByzAgent. Stages 3 and 4 are separate experiments run on the same federated training and are reported separately.](docs/report/figs/fig_pipeline.png){#fig:pipeline width=12}

1. **Data.** The corrected Distrinet CICIDS2017 flows are cleaned and mapped to eight attack families plus Benign, then split once into a training pool and a test set, with a fixed validation set held out of the training pool.
2. **Federated training.** Ten simulated organizations (silos) receive Dirichlet-skewed shares of the training pool and jointly train a multilayer perceptron with FedAvg. Every silo trains in every round, and the round kept from each run is the one with the best validation score.
3. **Explanation check.** Each silo computes SHAP attributions on its own copy of the model and sends only its top-k feature indices to the server, which compares them with the global model's ranking.
4. **Trust check.** The server logs five behaviour statistics per silo and round. Either ByzAgent, a language-model agent, or a classical robust rule decides how much each silo's update counts.
5. **Dashboard.** A FastAPI backend serves the selected model, its explanations and the trust decisions to a React front end used by an analyst.
<!-- src: PROJECT_INSTRUCTIONS.md -->

The design keeps one rule throughout: data stays with its silo. The only things that cross from a silo to the server are model weights, a training-loss value and, in the explanation check, a list of top-ranked feature indices.

## Working Methodology {#sec:methodology}

### Data and cleaning {#sec:m-data}

We use the Distrinet release (version 4) of CICIDS2017 published with Liu et al. [@liu2022], which builds on the corrections of Engelen et al. [@engelen2021] to the original dataset [@sharafaldin2018]. The raw files hold 2,099,976 flows in five day files with 91 columns. Seven of those columns identify the flow (flow ID, addresses, ports and timestamp) and are dropped, which leaves 82 numeric candidate features, one label and one attempted-category code.
<!-- src: data/README.md -->

Two early decisions shaped the classes. First, flows labelled "Attempted" join their parent family. We had planned to fold them into Benign, as the dataset authors' benchmark does, but the counts ruled it out: attempts are most of the Bot class and of both web-attack subtypes, so folding them away would have emptied those classes. Second, 14 raw labels were mapped to nine classes. The internal port-scan phase of the infiltration scenario was sent to PortScan, because its features are those of a port scan; sending it to Infiltration would have built a class that was almost entirely scan traffic.
<!-- src: data/README.md -->

Cleaning ran in a fixed order: load, map families, drop non-finite values, drop conflicts, drop duplicates. It removed 5 rows with non-finite values, 44,005 rows whose identical feature vectors carried different families, and 142,464 duplicates that spanned capture days, leaving 1,913,502 flows. Families with fewer than 1,000 flows, Infiltration (66) and Heartbleed (11), stay in the data but are left out of the headline macro-F1, which averages the remaining seven classes; they are reported per class.
<!-- src: data/README.md -->

The split is global and group-aware. Every distinct feature vector forms a group, so copies of one vector never end up on both sides of the split. This gives 1,435,126 training-pool flows and 478,376 test flows, and every headline family has exactly a 25.0% test share. Ten percent of the training pool, 143,513 rows, is held out as a centralized validation set that no silo trains on.
<!-- src: data/README.md; docs/efficiency_results.md; configs/model.yaml -->

The complete cleaning record, with every count, is in Section 6.A.

### Partitioning across silos {#sec:m-partition}

For each family k, the shares that the 10 silos receive are drawn from a symmetric Dirichlet distribution, p_k ~ Dir(α·1). A small α concentrates each family in one or two silos; a large α spreads it evenly. We use α ∈ {0.1, 0.5, 5.0} with seeds 42, 1337 and 2024, which gives nine partitions. α=5.0 serves as a near-IID control. Shares are applied by cutting each family's shuffled index list at cumulative boundaries, so they are exact rather than sampled.
<!-- src: PROJECT_INSTRUCTIONS.md; data/README.md -->

The heterogeneity is real and measured. Averaged over families, the silo that receives most of a family gets 0.694 of it at α=0.1, 0.372 at α=0.5 and 0.177 at α=5.0, against 0.100 for a uniform split. At α=0.1 silo sizes are very uneven; the largest silo holds 636,676 rows (α=0.1, seed 42, silo 2).
<!-- src: data/README.md; results/inspection/silo_size_vs_agreement.csv -->

The row-to-silo assignment arrays are written to disk with a SHA256 manifest. The manifest stores a hash of each assignment array, and the loader refuses to return a silo whose hash does not match. A test showed that the check catches a single flipped entry among 1.4 million. Per-silo label counts for all nine partitions are in Section 6.B.
<!-- src: data/README.md -->

### Model and federated training {#sec:m-model}

The detector is a multilayer perceptron with 82 inputs, two hidden layers of 128 and 64 units with ReLU activation, LayerNorm and dropout of 0.1, and a 9-way output. It has 19,849 parameters. Local training uses AdamW [@loshchilov2019] with learning rate 0.001, weight decay 0.0001 and batch size 1024. Each federated run has 20 rounds of FedAvg in Flower [@beutel2020flower], with 3 local epochs per round. The scaler is fit separately in each silo, on that silo's training rows only.
<!-- src: configs/model.yaml; docs/efficiency_results.md; PROJECT_INSTRUCTIONS.md; federated/pyproject.toml -->

Every setting was fixed before the main experiments and is listed in @tab:locked with the reason it was chosen. The pilot runs behind these choices are in Section 6.C.

Table: Locked model and training settings, with the reason for each {#tab:locked}
| Setting | Reason |
|---|---|
| StandardScaler | RobustScaler degenerates on 28 of the 82 features, whose interquartile range is zero |
| Effective-number class weights, β=0.999 [@cui2019] | Best validation score in the class-weighting pilot |
| MLP [128, 64], dropout 0.1 | The top pilot arms tie on validation; this is the smallest of them |
| LayerNorm [@ba2016] instead of BatchNorm | BatchNorm's running statistics are per-silo quantities that do not average meaningfully |
| 3 local epochs | Validation prefers 3 epochs over 1 at α=0.5 in all three seeds |
| 9-wide frozen label vocabulary | Every silo shares one output layer, even when it lacks some classes |
| All 10 silos train every round | The size floor applies only to explanation eligibility, never to training |
| Best-by-validation round | A run's rounds can differ by up to 0.118 in validation macro-F1 |
<!-- src: PROJECT_INSTRUCTIONS.md -->

Two centralized references use the same features and split: the same MLP trained on the whole training pool, and an XGBoost model [@chen2016xgb]. Both are early-stopped on validation. XGBoost was tuned on validation with 40 trials of a hyperparameter search on a subsample.
<!-- src: configs/xgboost_tuned.json -->

### The explanation check {#sec:m-expl}

DeepExplainer, SHAP's usual explainer for neural networks, fails on our LayerNorm layers with an additivity error of 2.43. Every silo therefore uses SHAP's GradientExplainer [@lundberg2017; @erion2021] on its own copy of the model at the selected round. The background is 200 rows drawn once from the silo's own training partition, stratified by class under a fixed seed, and each explanation uses 4000 samples.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/measurement_protocol.md -->

All models explain the same fixed set of 14 rows, two for each headline family. Each comparison uses the attribution vector of the row's true class, so a disagreement about the prediction itself cannot leak into the agreement score. Only the top-k feature indices leave the silo; SHAP magnitudes and raw rows never do.
<!-- src: docs/measurement_protocol.md -->

Agreement between a silo ranking A and the global ranking B is measured two ways. Jaccard@k is the size of the intersection of the two top-k sets divided by the size of their union. Weighted Kendall's τ [@vigna2015] compares the full order of all 82 features and gives more weight to disagreements near the top. Silos with fewer than 400 training rows, and families with fewer than 20 rows in a silo, are left out of agreement analysis; they still train.
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

Two reference lines make the agreement values interpretable:

- **Chance level.** For two random 10-feature subsets of 82 features, the expected Jaccard is (k²/n)/(2k − k²/n) = 0.065.
- **Centralized-seed instability floor.** Three centralized models (seeds 42, 1337, 2024) are explained on the same rows with the same background construction, and their pairwise agreement is computed. The median over the three seed pairs is the floor: the agreement that random seeds alone produce.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->

Uncertainty at α=0.1 is estimated with a cluster bootstrap [@fieldwelsh2007] that resamples (seed, silo) clusters 10,000 times. Correlations are reported as r and n only, with no p-values, because silos in one run follow the same sequence of global models and are not independent samples. The formulas for every metric are in Section 6.P.
<!-- src: site/public/data/ci.json -->

### The trust check {#sec:m-trust}

**Attack.** The attack runs at α=0.5 and seed 42. f malicious silos relabel 40% of their non-Benign training rows as Benign from round 1 onward (sudden mode); a gradual mode ramps the flipped fraction up over the rounds instead. The attacker set was found by enumerating all 120 three-silo subsets and keeping the one with the highest minimum per-family coverage, which gives silos {0,3,5} for f=3; the same search gives {0,3} for f=2. The adversary is therefore worst-case: it knows the label mix of every silo. No real attacker has that view, so the attack bounds what detection must handle rather than modelling what an attacker would do.
<!-- src: docs/contribution_b_results.md -->

**Statistics.** Each round the server records five numbers per silo, listed in @tab:five-stats.

Table: The five per-silo statistics recorded each round {#tab:five-stats}
| Statistic | What it measures |
|---|---|
| update_norm | L2 distance between the silo's trained weights and the previous global weights |
| cosine_to_global | Cosine similarity between the silo's update and this round's aggregate |
| cosine_to_peer_mean | Cosine similarity to the unweighted mean of all silos' updates |
| train_loss | The silo's last-epoch local training loss |
| val_accuracy | Accuracy of the silo's trained model on the centralized validation set |

**ByzAgent.** A locally served Llama 3.1 8B instruct model [@grattafiori2024llama3], 4-bit quantized and run at temperature 0.2, receives one prompt per round. The prompt holds the five statistics of all ten silos with their definitions, and a warning that this attack pushes validation accuracy up for malicious silos. The agent must answer in a fixed JSON schema with one decision per silo: trust, downweight (to 0.3 of the silo's normal weight) or quarantine, each with an explanation that cites the numbers used. It is never told f, the attackers' identities, or which statistic is strongest. Its decisions were replayed on statistics logged from undefended FedAvg runs, so they never fed back into training.
<!-- src: configs/agent.yaml; docs/contribution_b_results.md -->

**Baselines.** Multi-Krum keeps n − f updates; classical Krum keeps one and serves only as a secondary check; trimmed mean drops a fraction β = f/n at each end of every coordinate [@blanchard2017; @yin2018]. All three are given the true f as an oracle, an advantage ByzAgent does not have.

**Measures.** The strength of an attack is summarised by four statistics of validation macro-F1 over the 20 rounds: the mean, the median, the mean of the final five rounds and the maximum. The maximum selects the deployed checkpoint; the final-five mean is the attack-effect statistic. All four are always reported together. For the defences we report the recovery fraction and how often a malicious silo is excluded, compared with the matching chance rate. For ByzAgent we report each silo's flag rate (downweight or quarantine) and its lift over the same silo's rate in a clean run.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

### The preregistered accuracy study {#sec:m-prereg}

After the main results were in, the team decided to test once whether a different federated optimizer improves accuracy under non-IID data. The protocol, `docs/preregistration_accuracy.md`, was committed in two parts. The first part fixed the question, the candidates and a selection rule before any candidate ran. The second fixed the chosen configuration and sealed its checkpoints by SHA256 before the single test evaluation. Candidates were compared on validation only at α ∈ {0.1, 0.5} with all three seeds. The chosen configuration was then trained at α=5.0 as well, and its nine checkpoints were scored on the test set exactly once. Section 6.H gives the full protocol.
<!-- src: docs/preregistration_accuracy.md -->

### Test-set use {#sec:m-testuse}

Every model and every round was selected on validation data, and headline test numbers come from one evaluation of each run's validation-selected checkpoint. We nevertheless disclose that three early design choices (3 local epochs, FedProx μ=0.0005 and the StandardScaler) were first recorded with test-set numbers as their justification. Repeating each comparison on validation picks the same value. For local epochs, validation prefers 3 epochs over 1 at α=0.5 in all three seeds, with mean best-by-validation macro-F1 of 0.9425 against 0.8602.
<!-- src: PROJECT_INSTRUCTIONS.md -->

The test set was also read in ways that informed no later choice: legacy client-side per-round scoring in 35 runs that no analysis reads; a round-20 score used by an earlier round-lottery comparison, since replaced by a validation version; 14 fixed rows used as SHAP inputs; 514 rows extracted for display, together with the dashboard simulator before 2026-10-13, which kept no log and computed no aggregate; development scoring of 18 centralized pilot and baseline runs and 3 XGBoost seeds; and one preregistered evaluation of a single validation-selected configuration. Since 2026-10-12, by a team decision, no configuration other than the preregistered one is ever scored on the test set. The full audit is in Section 6.J.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Standards {#sec:standards}

The project uses the standards in @tab:standards. Each row says where in the project the standard appears; standards that the project does not use are not listed.

Table: Standards used in the project {#tab:standards}
| Standard | Where it is used |
|---|---|
| IEEE 754 binary32 and binary16 floating point | Model weights, SHAP values and communication counts are fp32; one update-compression scheme casts updates to fp16 |
| ONNX (Open Neural Network Exchange) model format | The served model is exported to ONNX and run by ONNX Runtime |
| SHA-256, FIPS 180-4 | Hashes of the partition assignment arrays, the sealed preregistered checkpoints and every hot-swapped checkpoint |
| HTTP and REST, described with OpenAPI | The FastAPI backend serves JSON over HTTP and publishes an OpenAPI description of its endpoints |
| JSON and JSON Schema | ByzAgent's reply format is a JSON Schema enforced through Ollama's format field; results and logs are stored as JSON and JSON Lines |
| WCAG contrast guidelines (level AA) | Text contrast on the dashboard and the showcase site was raised to the AA level |
| IEEE reference style | The references in this report and in the project paper |

## System Details {#sec:system-details}

This section describes the software and hardware details of the system.

### Software details {#sec:software}

**Federated harness.** All federated results come from the Flower app in `federated/xfed_federated/`, run with the command `flwr run federated local-simulation`. The client app trains locally and returns weights and its training loss. The server app aggregates, scores the global model on the validation set every round, keeps the best round, and logs the five client statistics, Krum selections or trim rates, and the bytes moved. The repository also holds an early prototype in `src/federated/` that lacks validation-based round selection. We removed the root project's pointer to it, so a bare `flwr run` now stops with an error instead of silently using the prototype.

**Training and explanation tools.** Centralized training, the data pipeline and the attack code live under `src/`. Analysis scripts under `tools/` compute SHAP attributions, agreement metrics, the seed-noise floor, the parity monitor and the efficiency measurements; scripts under `scripts/` run the pilots, the trust-check phases and their analyses. Every parameter is read from YAML files under `configs/`.

**ByzAgent.** The agent lives in `src/agents/byz_agent.py`. It sends one batched request per round to a local Ollama server, which enforces the JSON schema. A malformed reply is retried once and then raises an error, so a round is never silently given a default decision.

**Backend.** A FastAPI service in `backend/` loads the deployed checkpoint (`fedavg_a0.5_s42`, round 18, validation macro-F1 0.9760) and refuses to start unless its validation macro-F1 equals the value logged during training. By default it serves predictions through ONNX Runtime in fp32, and it refuses to start unless every validation prediction matches PyTorch's. It has no code path that opens the test file. The full list of endpoints is in Section 6.K.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

**Dashboard.** The React front end has three routes. *Live* (@fig:dash-live) shows the alert stream, the selected alert with its SHAP contributions and a one-sentence LLM summary, and the trust panel. *Investigate* (@fig:dash-investigate) answers four questions in turn: is anyone poisoning the model, is it accurate, do the organizations agree on why, and what does it cost to run. *Limits* lists the known limitations, read directly from the project instructions. Every displayed number links to the file it came from. Alerts come from a simulator that replays validation rows through the served model and marks each alert as matching its true label or not; it never adds these marks up into a score.

![Dashboard, Live route (Deep Sea theme): flow stream, selected alert with SHAP contributions and LLM summary, and the trust panel](docs/dashboard_v2/screens/live_deep-sea_1440.png){#fig:dash-live width=15.5}

![Dashboard, Investigate route (Deep Sea theme), shown in full: trust check, detection accuracy, explanation check and efficiency](docs/dashboard_v2/screens/investigate_deep-sea_1440.png){#fig:dash-investigate width=9}

**Hot swap.** From the Live route an analyst can confirm or correct an alert's family (@fig:dash-hotswap). Only the family label is sent, never the flow's features. Retraining runs in a separate process and always starts from the original base checkpoint, so swaps never stack. It routes up to 200 extra training rows of that family to the silo that already holds most of it and runs 2 FedAvg rounds of 3 local epochs on the CPU. The new model goes live only if its validation macro-F1 is equal to or higher than that of the model in service; there is no tolerance band. Every accepted swap is written to an append-only audit log with its seed and checkpoint hash.
<!-- src: configs/hotswap.yaml -->

![Hot-swap dialog after a rejected candidate: the gate kept the served model because no candidate round reached the incumbent's validation score](docs/dashboard_v2/screens/hotswap_rejected_detail_deep-sea.png){#fig:dash-hotswap width=13}

@tab:tools lists the main tools and their versions. The complete inventory of libraries, with what each was used for, is in Section 6.O.

Table: Main implementation tools and versions {#tab:tools}
| Component | Tool and version |
|---|---|
| Language | Python 3.11.15 |
| Federated training (CPU) | PyTorch 2.13.0 (CPU build), Flower 1.33.0 |
| Centralized MLP (GPU) | PyTorch 2.6.0+cu124 |
| Explanations | SHAP 0.51.0 |
| Baseline | XGBoost 3.2.0 |
| Serving | ONNX Runtime 1.31.0, FastAPI 0.138.2 |
| Trust agent | Ollama 0.40.16, model llama3.1:8b-instruct-q4_K_M |
| Dashboard | React 19.2.8 |
<!-- src: docs/env_versions_2026-11-18.txt; federated/pyproject.toml; requirements.txt; frontend/package.json; configs/agent.yaml -->

### Hardware details {#sec:hardware}

All work ran on one laptop: an NVIDIA RTX 4050 GPU with 6 GB of memory, 24 GB of RAM, an AMD Ryzen 7 7435HS CPU, and Windows 11. The 6 GB of GPU memory was a hard ceiling for every model we tried.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

The GPU ran the centralized MLP (baselines and pilots), XGBoost, and Ollama for ByzAgent. Federated training did not use the GPU: Flower builds an isolated runtime environment, and that environment installed the CPU build of PyTorch. This was verified for the August environments and for every run from 2026-10-12 on. SHAP, model serving and hot-swap retraining are CPU jobs as well. For SHAP this was a measured choice: on this small model, the GPU ran about 3 times slower than the CPU, because kernel-launch overhead dominates.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->

## Testing and Verification {#sec:testing}

The repository has no unit-test suite. It relies instead on a set of checks built into the pipeline and on standalone verification scripts, summarised in @tab:checks-summary. Each check, what it verifies and its last recorded result are described in Section 6.R.

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
