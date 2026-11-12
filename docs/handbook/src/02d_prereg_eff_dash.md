## 2.6 Accuracy improvement (preregistered) {#ch-prereg}

### In one line

We wrote down, before running anything, how we would pick a better federated optimizer using validation data only; the rule picked FedAvgM with server momentum 0.9; we sealed its 9 checkpoints by SHA256 and scored them on the test set exactly once.

### Why this exists

FedAvg collapses at α=0.1 (0.516 ± 0.048). The obvious question: does a smarter way of combining updates help? But the test set had already been read in several documented ways (Part 3), and trying optimizers until one looks good on test would be exactly the "peeking at the exam" problem. So on 2026-10-12 the team adopted a rule: **the test set is evaluated one further time, once, for a single federated configuration selected beforehand on validation data only. No other configuration is ever scored on the test set** (source: `docs/preregistration_accuracy.md`; commit `b2b9bee`).

### How it works — the sealed envelope

![The pre-registration timeline on 2026-10-12, from git history: rule → Part 1 → budget revisions → selection → seal → single test.](img/fig18_prereg_timeline.svg)

1. **Part 1, committed before any candidate run** (commit `ad249bd`): the question, the candidates, the baseline and the selection rule.
2. Run the candidates on validation only. The method path has **no test evaluation at all**: client-side evaluation is switched off and `client_app.evaluate` refuses method runs (source: `docs/preregistration_accuracy.md`).
3. Apply the rule mechanically (`tools/select_federated_method.py`).
4. **Part 2, committed on its own before the test** (commit `1a17277`): the chosen configuration, and the SHA256 of each of its 9 checkpoints.
5. Run `tools/federated_method_test_once.py` **once**. Before touching test it checks the preregistration is committed and clean, re-hashes every checkpoint, re-computes each checkpoint's validation score (must match exactly), writes a LOCK file, then scores (source: `docs/preregistration_accuracy.md`, Procedure).
6. Report the result **whatever it is**.

**The selection rule** (source: `docs/preregistration_accuracy.md`):

1. **Guard:** a candidate is eligible only if its α=0.5 validation mean is at least FedAvg's minus 0.01 (i.e. ≥ 0.9325).
2. **Pick:** among eligible candidates, the highest α=0.1 validation mean.
3. **Threshold:** if that is below FedAvg's α=0.1 mean + 0.02 (0.5428), the outcome is "no improvement" and **the test set is not touched**.
4. **Ties:** higher α=0.5 mean, then table order.

### What we actually did

**Candidates planned: 9 (plus FedAvg as baseline)** — FedProx μ ∈ {0.001, 0.01, 0.1}, FedAvgM momentum ∈ {0.5, 0.9}, FedAdam η ∈ {0.01, 0.001}, FedYogi η ∈ {0.01, 0.001} (source: `docs/preregistration_accuracy.md`).

**Only 4 of the 9 were run.** The other 5 were cut on wall-time grounds only, each recorded in the preregistration *before that candidate started* (source: `docs/contribution_a_results.md`, optimizer section):

- `fedprox_mu0.1` was cut by the budget estimate before any candidate ran.
- `fedprox_mu0.001`, `fedprox_mu0.01`, `fedadam_lr0.001`, `fedyogi_lr0.001` were dropped by a **timing-only budget guard** (it reads wall times, never scores). Disclosure: the guard was added after one `fedavgm_m0.5` validation score (α=0.1, seed 42) had been seen; none of the four candidates it could drop had started (source: `docs/preregistration_accuracy.md`).
- SCAFFOLD was not run: no Flower strategy, it needs persistent client state, and its correction assumes local SGD while our local optimizer is AdamW.

**Regression check:** FedAvg re-run on the new code path reproduced the published α=0.1 seed 42 validation curve **exactly**, all 21 rounds (max difference 0.0) (source: `docs/preregistration_accuracy.md`).

**Validation results (selection)** (source: `results/federated_methods/selection.json`):

| Candidate | α=0.1 val mean | α=0.5 val mean | Guard (≥ 0.9325) |
|---|---|---|---|
| FedAvg (baseline) | 0.5228 | 0.9425 | — |
| FedAvgM m=0.5 | 0.5386 | 0.9502 | pass |
| **FedAvgM m=0.9** | **0.6068** | **0.9861** | pass |
| FedAdam η=0.01 | 0.4583 | 0.8482 | fail |
| FedYogi η=0.01 | 0.4627 | 0.9004 | fail |

FedAvgM m=0.9 cleared the 0.5428 threshold → selected. Then trained at α=5.0 too, so all three α can be tested.

**Recorded before the test, so it couldn't be explained away later:** FedAvgM m=0.9's α=0.1 validation curves oscillate strongly, and its best rounds are often spikes. Its *final-round* α=0.1 val mean (0.5248) is close to FedAvg's (0.5062). Taking the max over noisy rounds favours a jumpier method, so some of the +0.084 validation gain was expected to shrink on test (source: `docs/preregistration_accuracy.md`, Part 2).

### What we found

**The single test evaluation** (source: `results/federated_methods/test_once/result.json`; prereg commit `1a172773523e9ce549952631fe3b89797af83bb7`):

| α | FedAvg (published) | FedAvgM m=0.9 | Per seed 42 / 1337 / 2024 (FedAvg → FedAvgM) |
|---|---|---|---|
| 0.1 | 0.516 ± 0.048 | **0.5930 ± 0.0632** | 0.5426→0.6558 / 0.4481→0.5065 / 0.5572→0.6167 |
| 0.5 | 0.941 ± 0.057 | **0.9852 ± 0.0005** | 0.9753→0.9846 / 0.9866→0.9856 / 0.8605→0.9856 |
| 5.0 | 0.990 ± 0.001 | **0.9911 ± 0.0005** | 0.9900→0.9918 / 0.9905→0.9906 / 0.9889→0.9910 |

(per-seed values: `docs/contribution_a_results.md`, optimizer section)

**What it means, in the agreed wording** (source: `docs/contribution_a_results.md`):

- **α=0.5: stability.** Mean 0.941 → 0.985, spread 0.057 → 0.0005. Most of the change is seed 2024 (0.8605 → 0.9856); seed 1337 moved −0.001. It removes a bad seed rather than raising good ones.
- **α=0.1: consistent but modest.** Up in all 3 seeds (+0.113, +0.058, +0.060). Still far below centralized (0.990); whole families still get F1 near 0 in some seeds.
- **α=5.0: parity.** +0.0001 to +0.0021 per seed, within the centralized model's own seed spread.
- As predicted, the α=0.1 validation gain (+0.084) was larger than the test gain (+0.077).

### What this does NOT mean

- **Not a tuned optimum**: "the best of these four." Momentum only tried at {0.5, 0.9}; server lr fixed at 1.0.
- **n=3 seeds**; no significance test is claimed.
- **Not GPU results**: Flower's runtime trained with torch 2.13.0+cpu.
- **Explanation and trust findings remain FedAvg findings.** Whether momentum changes explanation agreement is untested. The headline explanation numbers were *not* recomputed.
- **α=0.1 is not solved.** Per-class F1 at α=0.1 for PortScan is 0.2964 and WebAttack 0.3088 (source: `docs/contribution_a_results.md`, per-class table).
- Side note: Flower 1.33's FedAdam sends float64 weights from round 2 (1.5× the per-round payload, 2,381,880 vs 1,587,920 bytes); it wasn't selected (source: `docs/contribution_a_results.md`).

### Where it lives in the code

| File | What it does |
|---|---|
| `docs/preregistration_accuracy.md` | The preregistration, Parts 1 and 2 |
| `configs/federated_methods.yaml` | Candidates, `cut:` and `skipped:` reasons |
| `tools/run_federated_methods.py` | Sequential driver with `budget_allows` guard |
| `tools/select_federated_method.py` | Applies the selection rule |
| `tools/federated_method_test_once.py` | The one-shot test, with all its checks |
| `results/federated_methods/` | `selection.json`, `budget_guard.jsonl`, `sealed_checkpoints.json`, `test_once/result.json`, per-run logs |

### Questions an examiner might ask

**Q: Didn't you just keep trying optimizers until the test score went up?**
A: No. The rule and candidates were committed before any run, selection used validation only, the chosen 9 checkpoints were sealed by hash in a commit, and the test was run once by a script that refuses to run twice. We'd have reported a worse result too.

**Q: You only ran 4 of 9 candidates. Isn't that cherry-picking?**
A: The cuts were on wall time only, by a guard that reads timings, never scores, and each cut was recorded before that candidate started. We disclose that the guard was added after one validation score was seen. Our claim is "best of these four," not "best optimizer."

**Q: So FedAvgM solves non-IID?**
A: No. At α=0.1 it's 0.5930 ± 0.0632, still far below centralized 0.9900. The clearest effect is stability at α=0.5.

**Q: Why are FedAvgM numbers to 4 decimals but FedAvg to 3?**
A: The FedAvg row is the published table; FedAvgM's is shown to 4 decimals so no sd reads as zero (commit `1e2f453`).

---

## 2.7 Efficiency {#ch-eff}

### In one line

ONNX Runtime fp32 serves each flow about 4× faster than PyTorch (p50 45.7 vs 186.5 µs) with identical predictions; each training round moves 1,587,920 bytes; compressing updates saves 50–75% of upload with no detectable accuracy effect at n=3; and a train_loss pre-screen for ByzAgent failed — a negative result we report.

### Why this exists

An IDS has to keep up with live traffic, and federated training has to fit network budgets. Efficiency is a separate experiment from both checks and changes neither (source: `docs/efficiency_results.md`). **No test rows were read**: Part A replays logs, Part B uses the 143,513 validation rows, Part C uses parameter counts, run logs and validation-only runs.

### How it works

- **ONNX** (Open Neural Network Exchange) is a portable file format for trained models; **ONNX Runtime** is a fast engine that runs it. Analogy: compiling a script into an executable.
- **Quantization** stores weights in fewer bits (int8 instead of 32-bit floats), like saving a photo as a smaller JPEG — usually fine, sometimes visibly worse.
- **Update compression** sends each client's *change* in fp16 (half precision) or int8 instead of fp32.
- **Pre-screen**: only send an organization to the LLM if its train_loss is more than t times the round's median; auto-trust the rest. Fewer LLM calls, cheaper prompts.

### What we actually did, and what we found

**Part B — serving speed** (3 timing sessions, median [min, max]; CPU only, AMD Ryzen 7 7435HS; source: `results/efficiency/inference_speed_summary.json`, `docs/efficiency_results.md`):

| Variant | Val macro-F1 | p50 latency, batch 1 | Throughput, batch 1024 |
|---|---|---|---|
| PyTorch eager | 0.9760 | 186.5 µs [172.7, 193.2] | 1,482,368 rows/s |
| **ONNX Runtime fp32** | 0.9760 | **45.7 µs** [40.6, 46.9] | 1,071,700 rows/s |
| ONNX int8 (dynamic) | **0.8332** (−0.1428) | 47.9 µs | 1,256,956 rows/s |

- ONNX fp32 gives **identical predictions** on all 143,513 validation rows. It's about 4× faster per flow, but **slower** at large batches.
- **int8 was a stop-and-flag**: only 0.54% of predictions changed, but they fell on small classes (Bot F1 0.8815 → 0.4509; WebAttack 0.9671 → 0.4401). **int8 was dropped**.
- The backend now serves ONNX fp32 by default, behind a **startup gate** that refuses to start unless every validation prediction equals PyTorch's (source: `docs/efficiency_results.md`).

**Part C1 — bytes per round** (source: `results/efficiency/communication.json`): 19,849 parameters × 4 bytes = 79,396 bytes per model; × 10 orgs = 793,960 bytes each way; **1,587,920 bytes per round both directions**. Cross-checked exactly against harness logs over 500 logged rounds. Excludes metadata and gRPC/TLS framing; simulation on one machine.

**Part C2 — wall time**: median 51.4 s per round over 500 rounds from 25 runs on CPU (range 26.8–98.7 s) (source: `results/efficiency/communication.json`).

**Part C3 — update compression** (α=0.5, 3 seeds, validation; source: `results/efficiency/update_compression.json`):

| Scheme | Uplink per round | Saved vs fp32 uplink | Mean best-by-val change |
|---|---|---|---|
| fp32 | 793,960 B | — | — |
| fp16 | 396,980 B | 50.0% | −0.0007 ± 0.0054 |
| int8 per-tensor | 198,890 B | 74.9% | −0.0011 ± 0.0048 |

Agreed reading: **no detectable effect at n=3** (seed 2024 −0.0068 / −0.0066, within round-to-round noise). Not "harmless," not "harmful": unresolved. The byte saving is exact. Seed 2024 crossed the session's 0.005 stop-and-flag bound for both schemes; it was flagged and reported, not tuned (source: `docs/efficiency_results.md`).

**Part A — the failed pre-screen** (replay; source: `results/efficiency/agent_prescreen_replay.json`): t was chosen on seed 42 as the largest value keeping every logged flag on a poisoned org: **t = 10.0**. On seed 1337 it hid the attack: poisoned flag rate **0.017 vs logged 0.483**; 59 of 60 poisoned (org, round) pairs never reached the LLM. Why: at seed 1337, poisoned silo 0 is 95.4% Benign, so flipping its few attack rows barely moves its loss, while some clean but unusual silos reach 24.6× the median. Worse, in the gradual run at 100% flip the attackers' loss *collapses* (ratios 0.005 / 0.096 / 0.126), because fully flipped labels become self-consistent. **Reported as a negative result; no redesign planned** (source: `docs/efficiency_results.md`).

**Why a negative result is still a result.** It tells the next person not to waste time on this idea, and it sharpens the trust check's message: "33.8×–154.3×" is an effect size, not a threshold that transfers.

### What this does NOT mean

- 4× faster per flow is on one laptop CPU, batch 1. At batch 1024 PyTorch wins.
- A hot-swapped model always runs on torch, not ONNX.
- Compression's accuracy effect is unresolved at n=3, not shown to be zero.
- The pre-screen replay is one sample of a nondeterministic agent, and assumes the LLM would decide the same with fewer orgs in the prompt.

### Where it lives in the code

| File | What it does |
|---|---|
| `configs/efficiency.yaml` | All efficiency parameters; `serving.engine` |
| `tools/efficiency_inference_speed.py`, `tools/efficiency_inference_summary.py` | Part B |
| `tools/efficiency_communication.py` | Parts C1, C2 |
| `tools/efficiency_compression_runs.py`, `tools/efficiency_compression_summary.py` | Part C3 |
| `tools/efficiency_agent_prescreen.py` | Part A |
| `backend/model_loader.py` | `load_and_verify()` and the ONNX startup gate |
| `docs/efficiency_results.md` | Canonical write-up |

### Questions an examiner might ask

**Q: Why not quantize to int8 — it's standard?**
A: We tried. Validation macro-F1 fell by 0.1428 because the changed predictions hit small classes: WebAttack F1 dropped from 0.9671 to 0.4401. Aggregate agreement (99.46%) hides that. We dropped it.

**Q: How do you know the ONNX model is the same model?**
A: The backend refuses to start unless ONNX predictions equal PyTorch's on all 143,513 validation rows.

**Q: Does compression hurt accuracy?**
A: At n=3 we can't tell: mean change −0.0007 (fp16) and −0.0011 (int8), smaller than normal round-to-round swings. The byte saving (50% / 74.9% uplink) is exact.

**Q: Why report a failed idea?**
A: Because it's informative: a seed-42 train_loss threshold hid the attack at seed 1337 (0.017 vs 0.483 flag rate). Hiding it would leave others to repeat it.

---

## 2.8 Dashboard {#ch-dash}

### In one line

A FastAPI backend and a React frontend with three routes — **Live**, **Investigate**, **Limits** — show live detection with per-flow SHAP, the trust check, accuracy, explanation agreement and efficiency, where every number links to the results file it was read from.

### Why this exists

Results in CSV files don't help an analyst. The dashboard is stage 5: it puts detection, explanations and trust decisions together, the way an operator would use them. It also enforces honesty in the UI: numbers carry their sources, and the claims page shows the project's limitations verbatim.

### How it works

![Dashboard architecture: simulator replays validation rows → FastAPI backend (ONNX fp32 model, SHAP pool, results files) → React frontend.](img/fig20_dashboard_arch.svg)

- **Backend** (`backend/main.py`, FastAPI): loads the served model `fedavg_a0.5_s42` round 18, re-checks its validation macro-F1 against the logged value at startup, and never reads the test set (source: `README.md`, step 7). Endpoints include `/health`, `/config`, `/predict`, `/alerts`, `/shap/{id}`, `/explain/{id}`, `/trust`, `/agreement`, `/agreement/summary`, `/accuracy`, `/figures`, `/faithfulness`, `/federation`, `/limits`, `/source/{path}` and the hot-swap endpoints.
- **Simulator** (`backend/simulator.py`): replays rows as "live traffic." By default it replays the **500-row validation SHAP pool** in stored order (`simulator.source_split: val_shap_pool`), so every alert has a SHAP panel and an LLM summary. It **refuses** to replay test rows unless the served checkpoint's hash is on an allowlist, which is empty by default (source: `README.md`, step 7).
- **Frontend** (`frontend/`, React 19 + Vite): hand-built SVG/CSS charts.

**Why the demo replays validation rows.** The test set is reserved for the single preregistered evaluation. Replaying test rows on the dashboard would be another exposure, so since 2026-10-13 the simulator replays validation rows. It marks each alert against its true label, but **no aggregate metric is computed and nothing is selected from it** (source: `CLAUDE.md`). Before 2026-10-13 the simulator replayed test rows (display only, not logged, no aggregate) — disclosed in Part 3.

### What we actually did — every panel

![Live route, Deep Sea theme.](../dashboard_v2/screens/live_deep-sea_1440.png)

**Live (`/`)** — the operations console:

| Panel | What it shows | Fed by |
|---|---|---|
| Header | Route tabs, theme switch, LIVE status, served model tag, round, engine (`onnx_fp32`) | `/config`, `/health` |
| Key figures | Macro-F1 (FedAvgM prereg), per-flow latency, upload per round, traffic per round, each with its source file | `/figures` |
| Flow stream | Newest flows first, predicted family, confidence, ✓/✗ against the true label; filters (All / Attacks / Misses), Pause, Next miss, "Score a flow…" drawer | `/alerts`, `/predict` |
| Selected flow | Predicted family, confidence ring, "matches true label," **LLM-generated summary (labelled "not a research result")**, and "Why — SHAP contribution toward [family]" bars with base value, output and residual | `/shap/{id}?source=val`, `/explain/{id}` |
| Trust check (dumbbell) | Each org's share of rounds flagged, clean run vs attack run, and the lift; seed/attack selector | `/trust` |
| Hot-swap button and dialog | See below | `/hotswap/*` |

**Investigate (`/investigate`)** — four questions on one page, trust first:

![Investigate route, Aubergine theme.](../dashboard_v2/screens/investigate_aubergine_1440.png)

1. **Is anyone poisoning it?** Per-org clean/attack flag rates and lift, Multi-Krum 0%, cost with no attack (−22.7 / −4.9 / −1.6 pp), decision stability 27/30, round-by-round decision strips, the five statistics as small multiples, the agent's verbatim rationale labelled "a rationale of measured fidelity," and the locked claim.
2. **Is it accurate?** FedAvg vs FedAvgM per α, centralized and XGBoost references, per-class F1 and per-run tables.
3. **Do the orgs agree on why?** The agreement number line with chance and the floor, weighted τ, the α=0.1 CI vs floor labelled "directional, not significant," faithfulness, round-wise agreement, and a data & eligibility heatmap.
4. **What does it cost to run?** Latency, upload size, traffic per round, time per round, and the dropped int8 and pre-screen results.

**Limits (`/limits`)** renders the claims section of `PROJECT_INSTRUCTIONS.md` as written (`/limits` endpoint parses it verbatim).

![Limits route, Deep Sea theme.](../dashboard_v2/screens/limits_deep-sea_1440.png)

**Every number links to its source** through `/source/{path}`, which only serves a whitelist of results files (source: `README.md`, step 7).

**Themes and ambient light.** Three themes — Deep Sea, Aubergine, Porcelain — remembered in `localStorage`. Two blurred light pools behind the content take the colour of the newest flow on Live (benign, attack, or a stronger pulse for a miss) and of the selected organization on Investigate (poisoned, flagged without an attack, or clean). A shimmering skeleton stays up until the view's data has arrived (at least 600 ms). With `prefers-reduced-motion`, shimmer, pulse and fades are off (source: `README.md`, step 7; `frontend/src/components/Ambient.jsx`).

![Live route, Porcelain (light) theme.](../dashboard_v2/screens/live_porcelain_1440.png)

**Hot-swap and its gate.** An analyst who confirms an alert can ask for a quick model update:

![Hot-swap: warm start from the base model, a short retrain in a separate process, then a strict gate. Only a candidate at least as good on validation replaces the served model.](img/fig21_hotswap.svg)

- `POST /hotswap/trigger` takes **a family label only**. The backend picks up to 200 more training rows of that family (never validation rows) (source: `configs/hotswap.yaml`).
- Retraining **warm-starts from the base checkpoint**, never from a previous swap (no chaining), and runs 2 rounds × 3 local epochs on CPU in a **separate subprocess**, so a crash can't take down the backend (source: `configs/hotswap.yaml`).
- **The gate:** strict non-regression on `val_macro_f1_headline`, no tolerance band. The candidate replaces the served model only if it is ≥ the incumbent on validation (source: `configs/hotswap.yaml`). The round lottery is why leniency is the wrong default.
- Every event goes to an append-only audit log with code version, seed, sample IDs and the resulting checkpoint's SHA256, and the writer refuses to log against uncommitted code — so any swapped model can be reproduced from its logged seed (source: `src/hotswap/audit_log.py`).
- A banner shows on every page while a swapped model is active; **revert** is one click.
- Which silo receives the new rows is an **engineering choice for the live system, not a research finding**.

### What we found

This is an engineering stage, not an experiment; it has no research findings of its own. Verified behaviour: the startup gate passed (0 differences on 143,513 validation rows), and 50/50 sampled `/predict` calls matched the torch engine (source: `docs/efficiency_results.md`).

### What this does NOT mean

- The ✓/✗ marks on replayed alerts are not an accuracy measurement; nothing is aggregated.
- The **LLM summary sentences are a usability feature, not a research claim** (length not enforced).
- The dashboard is a demo on one machine, not a production deployment.
- A fresh clone can't run it until the data pipeline and demo files are rebuilt locally (`*.parquet` is git-ignored) (source: `README.md`).

### Where it lives in the code

| File | What it does |
|---|---|
| `backend/main.py` | FastAPI app and endpoints |
| `backend/figures.py` | `/figures`, `/accuracy`, `/agreement/summary`, `/limits`, `/source` |
| `backend/model_loader.py` | Load and verify the served model; ONNX gate |
| `backend/simulator.py` | Replays validation rows as traffic |
| `backend/hotswap_service.py`, `src/hotswap/`, `tools/hotswap_worker.py` | Hot-swap service, retraining, audit log |
| `configs/backend.yaml`, `configs/hotswap.yaml` | Settings |
| `frontend/src/views/Live.jsx`, `Investigate.jsx`, `Limits.jsx` | The three routes |
| `frontend/src/views/live/*`, `frontend/src/views/inv/*` | Panels |
| `frontend/src/components/Ambient.jsx`, `Src.jsx`, `HotSwapDialog.jsx` | Light pools, source links, hot-swap dialog |
| `APP.bat` | One-click start on Windows |
| `app.py`, `app_lib/` | Older Streamlit dashboard (superseded) |

### Questions an examiner might ask

**Q: Is the dashboard showing test-set performance?**
A: No. It replays validation rows; each alert is marked against its true label, but no aggregate metric is computed and nothing is selected from it. Test rows can't be replayed unless a checkpoint is allowlisted, and the allowlist is empty.

**Q: What stops a hot-swap from making the model worse?**
A: A strict gate: the candidate must score at least the incumbent's validation macro-F1. We've seen candidates rejected live; every attempt is in an audit log, and revert is one click.

**Q: Are the LLM sentences explanations?**
A: They're one-sentence summaries for usability, labelled "not a research result." The research explanations are the SHAP bars.

---

## 2.9 Showcase site and film {#ch-site}

### In one line

A public static website and a 70.8-second explainer film tell the project's story to a general audience, with every number built from exported JSON files that trace back to `results/` and `docs/`.

### Why this exists

Examiners, recruiters and other students won't run the dashboard. The site and film present the same results, at the same honesty standard, to people who will only scroll or watch.

### How it works / what we did

- **Site** (`site/`, Vite + React), deployed to Vercel at `xfed-ids-byzagent.vercel.app` (source: `README.md`). Sections: hero, a pinned seven-step story with a live diagram, system stages, explanation check, trust check and trust grid, a replay stream, limits and footer (source: `site/src/sections/`; git history 2026-10-07).
- **Data:** `tools/export_showcase_data.py` reads `results/` and `docs/` (read-only) and writes small JSON files to `site/public/data/` (e.g. `headline.json`, `agreement_by_alpha.json`, `byzagent_decisions.json`, `replay_alerts.json`, `ci.json`). Each JSON carries its own source list, and `npm run check:sources` fails the build if any source link points at an untracked file (source: `README.md`, step 8).
- **The site's replay** uses the 500 stored test-row outputs documented in the test-set disclosure (source: `CLAUDE.md`). This is display only.
- **Film** (`film/`, Remotion): 70.8 s, in 16:9 and 9:16, plus a hero loop. Every on-screen number comes from the site's JSON at render time; `film/out/numbers.json` maps each number to file, key and raw value (source: `film/README.md`).
- Since 2026-10-13 the round-20 (unselected) test score is no longer exported to the site (commit `2fcf8c4`).

### What we found

Not an experiment. Accessibility work (WCAG AA contrast, self-hosted fonts) is recorded in git history (2026-10-07).

### What this does NOT mean

- The site is a presentation of results, not a new source of them. Where it disagrees with the two `contribution_*_results.md` files, they win.
- The film's README warns not to run the simulator for captures because, at the time, it read the test set; since 2026-10-13 the simulator replays validation by default.

### Where it lives in the code

`site/` (sections in `site/src/sections/`, copy in `site/src/copy.js`, sources in `site/src/sources.js`), `tools/export_showcase_data.py`, `configs/showcase_export.yaml`, `film/` (`film/src/numbers.js`, `film/src/timeline.json`), rendered film in `site/public/film/`.

### Questions an examiner might ask

**Q: Could the site show a number that isn't in your results?**
A: Every number is built from exported JSON with its source list, and the build checks that every source link is a tracked file. The film reads the same JSON.

**Q: Why does the public site replay test rows when the dashboard doesn't?**
A: It replays 500 *stored* outputs extracted earlier for display; no new test evaluation happens and nothing is computed from them. It's listed in our test-set disclosure as display-only use.
