## System Implementation {#sec:app-system}

This section describes the software that implements the five stages: the federated harness, the configuration files, the backend and its endpoints, the dashboard, hot swap, the earlier Streamlit app and the showcase site. It supports Section 2.4.

### The federated harness

All federated results come from the Flower app in `federated/xfed_federated/`, run with the command `flwr run federated local-simulation`; a bare `flwr run` deliberately fails. One (α, seed) combination is run per invocation, with overrides passed through `--run-config`, for example `alpha='0.1' seed=1337`.

The server app wraps Flower's built-in strategies (FedAvg, FedAvgM, FedAdam, FedYogi, Krum, MultiKrum and FedTrimmedAvg) in logging classes (`LoggingFedAvg`, `LoggingMultiKrum`, `LoggingKrum`, `LoggingFedTrimmedAvg`). A shared logging mixin records the five client statistics, Krum's kept and excluded silos or trimmed mean's per-silo trim rates, and the bytes moved, without changing the aggregation itself, so a logged run is identical to the plain strategy. After every round the server scores the global model on the centralized validation set and keeps the best round's checkpoint. The client app trains with `local_train_epochs`, which turns into FedProx when μ is above zero (Section 6.S). If an attack is enabled in `configs/attack.yaml`, the client relabels only its own training labels before local training, and every flip is logged to an audit file. Validation and test labels are never touched.

The Flower app's dependencies are pinned in `federated/pyproject.toml` to the versions that its isolated runtime resolved for the published runs, including the CPU build of PyTorch 2.13.0. A later method path for the preregistered study and the compression runs is validation-only by construction.
<!-- src: federated/pyproject.toml; docs/preregistration_accuracy.md -->

### Configuration files

Every parameter lives in a YAML or JSON file under `configs/`; nothing is hard-coded in the scripts (@tab:configs).

Table: Configuration files and what each controls {#tab:configs size=9.5}
| File | What it controls |
|---|---|
| `data.yaml` | Raw and processed paths, cleaning rules, the attempted-flow handling, the family map, the 1,000-flow floor, the federation and split settings |
| `model.yaml` | Label vocabulary and headline classes, the validation split, the MLP, training, class weighting and scaler settings |
| `global_class_weights.json` | The effective-number class weights shared by every silo |
| `xgboost_tuned.json` | The XGBoost settings selected by the validation search |
| `attack.yaml` | The label-flipping attack: on or off, f, attacker set, mode, flip fraction, strategy, seed |
| `defense.yaml` | Which robust aggregation baseline to use, with the oracle f |
| `agent.yaml` | ByzAgent: the Ollama model, temperature, keep-alive, downweight multiplier, and current-round or rolling-history mode with its window |
| `federated_methods.yaml` | The preregistered candidate grid, the selection rule, the cut and skipped candidates |
| `round_lottery.yaml` | The validation-based round-lottery comparison |
| `efficiency.yaml` | The pre-screen grid, timing protocol, serving engine, communication and compression settings |
| `hotswap.yaml` | Hot-swap retraining: rows per event, rounds, local epochs, device, the verification metric |
| `backend.yaml` | Backend paths, the served model, start-up verification, alert buffer, simulator source and rate, dashboard and limits settings |
| `val_shap_pool.yaml` | The 500-row validation SHAP pool for the dashboard demo, with its seeds |
| `showcase_export.yaml` | What the showcase-site data export reads and writes |
<!-- src: configs/data.yaml; configs/val_shap_pool.yaml -->

### Backend endpoints

The FastAPI backend in `backend/` loads the served model at start-up, verifies it against validation and serves JSON over HTTP. FastAPI also publishes an OpenAPI description of the interface. Large responses are compressed with gzip. @tab:endpoints lists every endpoint.

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

### The dashboard

The React front end in `frontend/` has three routes. Every number on screen links to the file it was read from through a small source-link component, and each panel has one "Sources" disclosure.

**Live** (@fig:dash-live, @fig:dash-live-aub and @fig:dash-live-por). The header holds the route tabs, the theme switch and the served model's tag, round and engine. A row of key figures shows the preregistered FedAvgM macro-F1 at α=0.5, the per-flow latency, the upload saving under compression and the traffic per round, each linked to its results file. The *flow stream* lists alerts newest first, with filters for all, attacks and misses, a pause button, a "next miss" button and a drawer for scoring a flow by hand; each row shows the predicted family, its confidence and whether it matched the true label. The *selected flow* panel shows the prediction, the one-sentence LLM summary, labelled as a usability feature and not a research result, and a bar chart of SHAP contributions toward the predicted family with the base value and residual. From here an analyst can mark the flow reviewed or open the hot-swap dialog. The *trust check* panel plots, for each organization, the share of rounds flagged in the clean run against the attack run, for a chosen (α, seed, attack) condition.
<!-- src: PROJECT_INSTRUCTIONS.md -->

**Investigate** (@fig:dash-investigate, @fig:dash-inv-aub and @fig:dash-inv-por). A side menu leads to four questions. *Is anyone poisoning it?* shows, for a chosen organization, its flag rates and lift, the Multi-Krum exclusion rate, the cost of defending with no attack, decision stability, a round-by-round decision grid for the clean and attack runs, small charts of the five statistics, the agent's verbatim rationale for a round, the locked trust-check claim, and expandable sections for all organizations, decision stability by condition and the oracle asymmetry. *Is it accurate?* compares FedAvg with the preregistered FedAvgM at each α, with per-class and per-run tables. *Do the orgs agree on why?* draws the agreement on a number line against chance and the seed-noise floor, with the weighted τ values, the α=0.1 bootstrap interval and faithfulness, plus per-family, round-wise, faithfulness and data-eligibility sections, including a heat map of flows per organization and family. *What does it cost to run?* shows latency, upload size, traffic and time per round, and the two dropped ideas (int8 serving and the loss pre-screen).
<!-- src: PROJECT_INSTRUCTIONS.md -->

**Limits** (@fig:dash-limits) lists the project's known limitations, read verbatim from the project instructions by the backend, with sections on test-set use and engineering notes.

**Themes, light and loading.** Three themes, Deep Sea, Aubergine and Porcelain, are offered; the choice is saved in the browser. Behind the content, two blurred pools of ambient light take the colour of the current state (normal, attack or agent) and cross-fade between states. While a view loads, a skeleton is shown for a short minimum time, so it never flashes, and the two light pools pulse; switching theme replays this loading effect.

**The simulator.** Alerts come from `backend/simulator.py`, a separate process that talks to the backend over HTTP. Unless configured otherwise, it plays back the validation SHAP pool, 500 rows in their saved order, which guarantees that each alert comes with SHAP values and a summary. It marks each alert as matching its true label or not, and it never adds these marks up into a score. Replaying test rows is refused unless the served model's checkpoint hash is on an allow-list.
<!-- src: configs/backend.yaml; configs/val_shap_pool.yaml -->

![Dashboard, Live route, Aubergine theme](docs/dashboard_v2/screens/live_aubergine_1440.png){#fig:dash-live-aub width=15.5}

![Dashboard, Live route, Porcelain theme](docs/dashboard_v2/screens/live_porcelain_1440.png){#fig:dash-live-por width=15.5}

![Dashboard, Investigate route, Aubergine theme](docs/dashboard_v2/screens/investigate_aubergine_1440.png){#fig:dash-inv-aub width=9}

![Dashboard, Investigate route, Porcelain theme](docs/dashboard_v2/screens/investigate_porcelain_1440.png){#fig:dash-inv-por width=9}

![Dashboard, Limits route, Deep Sea theme](docs/dashboard_v2/screens/limits_deep-sea_1440.png){#fig:dash-limits width=10}

### Hot swap

Hot swap lets an analyst turn a confirmed or corrected alert into a retrained model (@fig:dash-hotswap-dialog). The dialog explains what will happen, asks for the family of the flow and shows the model's prediction and the true label. Only the family label is sent to the backend, never the flow's features. The backend starts the retraining in a separate worker process, because two early proof runs crashed when heavy file reads followed training in the same process, and a crash inside the backend would take prediction down with it.
<!-- src: configs/hotswap.yaml -->

Each retraining begins from the base checkpoint, never from an earlier swap, so one swap cannot build on another. The worker adds as many as 200 training rows of the chosen family to the silo that already holds the largest share of that family, an engineering choice for the live system rather than a research finding, and runs 2 rounds of FedAvg with 3 local epochs on the CPU. A retrained candidate is put into service only when it scores at least as well on validation macro-F1 as the current model; no margin is allowed, and the first round that qualifies is the one kept. If no round passes, the served model is unchanged, nothing is logged, and the dialog shows the rejection detail (@fig:dash-hotswap). Every accepted swap is appended to an audit log, written to disk immediately, with its seed, the source model and round, the sample positions, the training configuration, the best round, the verification metric and the new checkpoint's SHA-256 hash; and nothing is logged while the code has uncommitted changes. A banner on every route shows when a swapped model is live, and one click reverts to the base model.
<!-- src: configs/hotswap.yaml -->

![Hot-swap dialog while a candidate is being retrained](docs/dashboard_v2/screens/hotswap_running_deep-sea.png){#fig:dash-hotswap-dialog width=13}

### The Phase 1 Streamlit app

Before the React dashboard, the first interface was a Streamlit app (`app.py` with `app_lib/`). It has seven sections chosen from a sidebar: Federation Status, Detect, Explain, Explanation Agreement, Faithfulness, Methods & Limits, and Client Trust Monitor. It reads the same results files and is kept in the repository, but the React dashboard replaced it as the main interface.

### The showcase site

A static public site in `site/` tells the project's story for a general reader: a seven-step story that stays on screen beside a diagram that changes as the reader scrolls, the system stages, the explanation check, the trust check, a replay stream of stored alerts and the limitations. It is built with React, Vite, GSAP and Lenis, uses self-hosted fonts, and is configured for deployment on Vercel. Its data comes from `tools/export_showcase_data.py`, configured by `configs/showcase_export.yaml`, which reads results files and writes JSON summaries to `site/public/data/` without copying raw rows. A source-link checker verifies that every number's link resolves. The site's replay uses 500 stored model outputs for test rows that were extracted for display before the 2026-10-12 rule; it computes no aggregate.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Development Timeline {#sec:app-timeline}

This section lists the project's phases and milestones with dates taken only from the git history (`git log`). It supports Chapter 1 and Section 4.7. The repository's first commit, on 2026-09-11, already contained the data pipeline, the federated training, the explanation and trust checks, the backend and the React dashboard. Work before that date is therefore not dated individually by git, and its order is given from the results documents without dates.

### Before the first commit

The results documents record this order of work: the data stage (cleaning, families, split, partitions); the centralized pilots and the locked model; federated training with FedAvg and FedProx; the explanation check (SHAP, agreement metrics, the seed-noise floor, round-wise agreement, the parity monitor and its multi-draw fix, the size and skew analysis); and the trust check in Phases 0 to 4 with the multi-seed validation.

### Dated milestones

@tab:timeline lists the dated milestones.

Table: Development milestones from the git history {#tab:timeline size=9.5}
| Date | Milestone |
|---|---|
| 2026-09-11 | First commit: pipeline, backend and React dashboard |
| 2026-09-13 | Hot swap: audit log, retraining service with its gate, live backend integration, banner and revert |
| 2026-10-02 | Streamed SHAP pool and LLM explanation layer; per-round trust statistics and explanations in the dashboard |
| 2026-10-03 | Test-set access note and README; the project presented as one system; showcase data export |
| 2026-10-07 | Showcase site built; explainer film; the 0% exclusion attributed to Multi-Krum in the project instructions |
| 2026-10-12 | README rewrite; decision to re-run the test set once for a preregistered configuration; repository paths made portable; environment files exported; the preregistered study run, sealed and evaluated |
| 2026-10-13 | Simulator switched to validation rows; validation-only round lottery; test-set exposure audit; epochs provenance on validation; hardware note corrected (federated training on CPU); efficiency study; ONNX Runtime fp32 made the default engine; validation SHAP pool and LLM summaries |
| 2026-10-14 | Residual audit and pre-specified sensitivity check; headline table extended; dashboard v2 with three routes, accessibility and performance pass; README restyle; one-click launcher |
| 2026-11-12 | Team handbook: outline, all parts, figures, build and number check |
| 2026-11-18 | IEEE paper: bibliography, figures, body and appendices, number, overlap, citation and coverage checks; environment versions recorded |
<!-- src: PROJECT_INSTRUCTIONS.md -->

### Changes of direction

Several decisions changed direction during the project; each is recorded in the documents.

- **Attempted flows.** The plan to fold attempted flows into Benign was reversed once the counts showed they are most of several classes (Section 6.A).
- **Conflict and duplicate keys.** Conflicts were first keyed on the raw label and duplicates on the family; both were reversed after they silently deleted learnable rows (Section 6.A).
- **The skew covariate.** Label entropy was the planned covariate; it failed conditioning on size, and KL divergence replaced it (Section 6.E).
- **The parity monitor.** The single-draw version was replaced by a three-draw version after its flags proved to be artifacts (Section 6.E).
- **The attacker rule.** The size-representative rule {0,1,9} was retired as too weak in favour of the worst-case search (Section 6.G).
- **The ByzAgent claim.** The strong reading that the agent tracks composition only was bounded by the multi-seed ceiling-effect finding (Section 6.G).
- **Test-set use.** On 2026-10-12 the team decided to evaluate the test set once more for one preregistered configuration only; on 2026-10-13 the round lottery was moved to validation and the simulator to validation rows (Section 6.J).
- **Serving.** ONNX Runtime fp32 replaced PyTorch as the default engine, and int8 was dropped (Section 6.I).
- **The dashboard.** The eight-page React dashboard was replaced by the three-route version on 2026-10-14, and the earlier Streamlit app before it.
<!-- src: docs/contribution_b_results.md -->

## Reproducibility {#sec:app-repro}

This section lists everything needed to rerun the work: the environment, the commands, the seeds, the configuration files and where every result is stored. It supports Chapter 2.

### Repository and environment

The code and results are in the public repository at https://github.com/Pilli9375/XFed-IDS-ByzAgent. The conda environment `xfed` is defined in `environment.yml` (Python 3.11), with pinned packages in `requirements.txt`. The versions recorded on the project machine on 2026-11-18 are given in @tab:env-versions. The Flower runtime pins its own versions in `federated/pyproject.toml`. The raw dataset CSVs are kept outside the repository; their directory can be set with an environment variable.
<!-- src: environment.yml; docs/env_versions_2026-11-18.txt -->

Table: Environment versions recorded on the project machine {#tab:env-versions}
| Component | Version |
|---|---|
| Python | 3.11.15 |
| PyTorch (xfed environment) | 2.6.0+cu124 |
| PyTorch (Flower runtime) | 2.13.0, CPU build |
| Flower | 1.33.0 |
| SHAP | 0.51.0 |
| XGBoost | 3.2.0 |
| ONNX Runtime | 1.31.0 |
| FastAPI | 0.138.2 |
| Ollama | 0.40.16 |
<!-- src: docs/env_versions_2026-11-18.txt; federated/pyproject.toml -->

### Commands

@tab:commands gives the main commands in the order they are run.

Table: Main commands, in order {#tab:commands size=9.5}
| Stage | Command |
|---|---|
| Data | `python src/data/clean.py`, then `python src/data/families.py`, then `python src/data/partition.py` |
| Federated training | `flwr run federated local-simulation` (one run per α and seed, set with `--run-config`) |
| Explanation check | `python tools/local_shap_pipeline.py`, `python tools/agreement_metrics.py`, `python tools/centralized_shap_floor.py` |
| Preregistered study | `python tools/run_federated_methods.py`, `python tools/select_federated_method.py` |
| Paper figures | `python paper/figs/make_figs.py` |
| Dashboard | the backend with Uvicorn, `python backend/simulator.py`, and `npm run dev` in `frontend/`; `APP.bat` starts all three |
| This report | `python docs/report/build_report.py` |

### Seeds

The seeds are 42 for the data stage; 42, 1337 and 2024 for partitions and training; 12345 for the SHAP evaluation rows; 9001 for the attack; 1001, 2002 and 3003 for the parity-monitor draws; and 6006 for the validation SHAP pool.
<!-- src: docs/measurement_protocol.md; docs/contribution_b_results.md; docs/contribution_a_results.md; configs/val_shap_pool.yaml -->

### Where the results live

@tab:result-files maps each result to its file; the complete inventory is in Section 6.Q.

Table: Where the main results are stored {#tab:result-files size=9.5}
| Result | File |
|---|---|
| Headline accuracy | `results/aggregated/*_headline.csv` |
| Per-run selection | `results/inspection/best_rounds_manifest.json` |
| Round lottery | `results/federated/round_lottery_val.csv` |
| Agreement | `results/inspection/agreement_metrics.csv` |
| Seed-noise floor | `results/inspection/centralized_instability_floor.csv` |
| Size and skew | `results/inspection/size_matched_heterogeneity.csv` |
| Residuals | `results/inspection/residual_*` |
| Parity monitor | `results/inspection/parity_monitor.csv` |
| Trust check | `results/*/PHASE*_SUMMARY.md`, `results/agents/MULTISEED_VALIDATION_SUMMARY.md` |
| Preregistration | `results/federated_methods/` |
| Efficiency | `results/efficiency/` |
| Explanation-check text | `docs/contribution_a_results.md` |
| Trust-check text | `docs/contribution_b_results.md` |

## Project Outputs {#sec:app-outputs}

This section describes what the project produced besides the system itself, and where each output lives. It supports Chapter 5. Their text is not reproduced here.

Table: Project outputs and where they live {#tab:outputs size=9.5}
| Output | What it is | Where it lives |
|---|---|---|
| IEEE paper | "XFed-IDS-ByzAgent: Explainable and Trust-Aware Federated Intrusion Detection. Silo Explanation Agreement and an LLM Trust Agent under Non-IID Data", in two versions: a full version with complete-record appendices, and a conference version with the body and references only; both have number, overlap, citation and coverage checks | `paper/main.tex`, `paper/main.pdf`, `paper/main_conference.pdf`, with an Overleaf bundle |
| Team handbook | A learning guide for the team: background from scratch, the system stage by stage, honesty and rigour, prior work, running the demo, review preparation and a reference part, with its own figures and number check | `docs/handbook/` (Markdown, HTML and PDF) |
| README | The repository's front page: abstract, architecture, screenshots, key results with the two checks kept apart, what is not claimed, test-set use, quick start and full reproduction steps | `README.md` |
| Dashboard | The three-route React dashboard with its FastAPI backend and simulator | `frontend/`, `backend/` |
| Showcase site | The static public site with its exported data | `site/` |
| Explainer film | A short explainer film made with Remotion, in landscape and portrait cuts, with a looping hero clip used by the site | `film/`, with renders in `site/public/film/` |
| Results documents | The canonical write-ups of each experiment | `docs/contribution_a_results.md`, `docs/contribution_b_results.md`, `docs/efficiency_results.md`, `docs/preregistration_accuracy.md`, `docs/test_set_exposure_audit.md`, `docs/measurement_protocol.md` |
| This report | The capstone thesis, built from editable chapter text | `docs/report/` |
