# Part 4 — Prior work {#part-4}

Only what our docs record is stated here. Anything an examiner might probe further, and that our docs don't record, is marked **[to verify in lit review]**.

## 4.1 The works we build on {#prior}

**Oki et al. (IEEE Networking Letters, 2024).** Measured the distance between explanations (feature sets) of distributed and non-distributed IDS models, and reported that federated learning *reduces* explanation distance (source: `docs/contribution_a_results.md` §1; `CLAUDE.md`). Their exact setup, dataset and distance measure: [to verify in lit review].

**Gholizade et al. (arXiv 2607.13045, June 2026 FedXAI survey).** Names **explanation consistency under non-IID data** as an open challenge and notes there are **no standard metrics** for it (source: `CLAUDE.md`; `docs/measurement_protocol.md` §1).

**Krum and Multi-Krum (Blanchard et al.).** Distance-based Byzantine-robust aggregation; our implementation "matches textbook Blanchard et al. Krum/Multi-Krum" (source: `results/defenses/PHASE2_SUMMARY.md`). Year and venue: [to verify in lit review].

**Coordinate-wise trimmed mean.** Implemented with Flower's `FedTrimmedAvg`, β = f/n (source: `docs/contribution_b_results.md` §4). Original paper: [to verify in lit review].

**FedAvgM (Hsu et al., 2019)** — server momentum (source: `docs/preregistration_accuracy.md`). **FedProx**, **FedAdam**, **FedYogi**, **SCAFFOLD**: used or considered as named Flower strategies; original papers [to verify in lit review].

**Dataset lineage:** Engelen, Rimmer & Joosen (WTMC 2021); Liu, Engelen, Lynar, Essam & Joosen (IEEE CNS 2022). A third correction branch, Lanvin et al. (CRiSIS 2022), is not used (source: `data/README.md` §1).

**Modified z-score threshold:** Iglewicz & Hoaglin 1993 (source: `docs/contribution_a_results.md` §4).

## 4.2 How we differ {#differ}

Using only what the docs say (source: `CLAUDE.md`, "How this project differs from prior work"; `README.md`):

- **Boundary conditions on Oki et al.**, not a contradiction: Oki et al. showed federation reduces explanation distance; we characterise **where that reduction breaks down** as client data becomes more heterogeneous (α=0.1 vs 0.5 vs 5.0).
- **A null control no prior work reports**: how much explanation rankings differ between centralized models that differ only by random seed. Without it, a reported difference can't be told apart from seed noise. (Our README words it carefully: "as far as we found.") Breadth of that search: [to verify in lit review].
- **A reusable measurement protocol** (`docs/measurement_protocol.md`) with two built-in reference lines (chance and seed noise), addressing the "no standard metrics" gap Gholizade et al. name. It doesn't invent a new statistic; Jaccard@k and weighted τ predate us.
- **The trust check tests Krum and its variants with 10 clients and an oracle attacker count** in a non-IID IDS setting, and **audits how often the agent's own explanations are accurate**.
- **What is not different:** "FL + IDS + XAI" as a combination is not new; several 2025–2026 papers cover it [to verify in lit review: which papers]. LLM-based trust agents in FL: [to verify in lit review]. The dashboard's LLM sentences are usability, not a claim.

**One sentence for the examiner:** "We don't claim the combination is new; our contributions are the seed-noise null control with a reusable protocol, the finding of where explanation agreement breaks down under heterogeneity, and an audited LLM trust agent whose limits we quantify."

# Part 5 — Running it {#part-5}

## 5.1 Running the dashboard for a demo (Windows) {#run}

**Before the day (one-time).** A fresh clone has no processed data. On the demo laptop, the data pipeline, the `fedavg_a0.5_s42` checkpoint, `best_rounds_manifest.json`, the validation SHAP pool and `node_modules` must already exist (source: `README.md`, Quick start and step 7). Check:

- `data/processed/train_pool.parquet` and `val_mask.parquet` exist;
- `results/shap/fedavg_a0.5_s42/val_pool.npz` exists (rebuild: `python -m tools.build_shap_val_pool`, about 45 minutes on CPU);
- `frontend/node_modules` exists (`cd frontend; npm ci`).

**Option A — one click.** Double-click **`APP.bat`** in the repo root. It starts the backend on port 8000, waits until `/health` answers (the backend re-checks the model, about a minute), then starts the simulator and the frontend, and opens `http://localhost:5173/` (source: `APP.bat`). Close the three windows to stop.

**Option B — three PowerShell terminals** (from the repo root; use PowerShell, because `conda activate` is a no-op in cmd.exe on this machine):

```powershell
conda activate xfed
uvicorn backend.main:app --reload
```

```powershell
conda activate xfed
python -m backend.simulator
```

```powershell
cd frontend
npm run dev
```

Then open `http://localhost:5173/`. The API is at `http://127.0.0.1:8000`; Vite proxies `/api` to it.

**Optional:** Ollama doesn't need to run for the demo — the LLM summaries are stored in `results/explanations/fedavg_a0.5_s42/val_sentences.json`.

## 5.2 A five-minute demo script {#demo}

| Time | Click | Say |
|---|---|---|
| 0:00 | Open **Live** (Deep Sea) | "This is XFed-IDS. Ten organizations trained this detector together without sharing traffic. The flows on the left are validation rows replayed as live traffic — never test rows." |
| 0:30 | Point at **key figures** | "Top row: our preregistered FedAvgM model's test macro-F1, 0.9852 at α=0.5, scored once. Per-flow latency 45.7 µs with ONNX. Each number links to the file it came from." Click one source link. |
| 1:00 | Click a **DoS** flow in the stream | "The model says DoS. On the right is *why*: SHAP shows which features pushed it there — here packet-length statistics. Base value, output and residual are shown, because SHAP's sums aren't exact and we measured that." |
| 1:30 | Point at the **LLM summary** | "This sentence is an LLM summary for the analyst. It's labelled 'not a research result' — a usability feature." |
| 1:50 | Click **Misses** filter, then **Next miss** | "We don't hide mistakes. Here's a flow the model got wrong." |
| 2:15 | Point at the **Trust check dumbbell** | "This is the trust check, a separate experiment. Open circle: how often our LLM agent flagged each organization with no attack. Filled: under attack. At seed 1337, org 5 goes from 0.00 to 0.95 — real detection. But some orgs are flagged in almost every round with no attack at all — the note under the chart names them. That's the compositional confound." |
| 3:00 | Go to **Investigate** | "Investigate answers four questions, trust first. Multi-Krum excluded a poisoned org 0% of the time. ByzAgent's result, in our locked words:" read the quote on screen. |
| 3:40 | Scroll to **Do the orgs agree on why?** | "Explanation check. Chance is 0.065, the seed-noise floor is 0.429. At α=5.0 agreement is 0.667; at α=0.1 it's 0.333, below the floor — directional, not significant, the intervals overlap." |
| 4:20 | Scroll to **What does it cost?** | "1,587,920 bytes per round; compression saves up to 74.9% of upload with no detectable effect at n=3; and two ideas we tested and dropped." |
| 4:40 | Open **Limits** | "Finally, Limits shows our claims and limitations verbatim from the project instructions. We'd rather you read them here than find them yourself." |
| 5:00 | (optional) Switch theme | Done. |

**Optional hot-swap (adds ~2 minutes):** on Live, select an alert → **Hot-swap model…** → confirm. Say: "This retrains for two rounds from the base model in a separate process. It only replaces the served model if it's at least as good on validation; otherwise it's rejected — and that happens often, because of the round lottery." Then **revert**.

## 5.3 If something breaks {#broken}

| Symptom | Likely cause | Fix |
|---|---|---|
| `APP.bat` waits forever | Backend failed to start | Look at the "XFed backend" window. Missing parquet or checkpoint → run the data pipeline / restore files |
| Backend refuses to start mentioning ONNX | ONNX predictions differ from torch (startup gate) | Set `serving.engine: torch` in `configs/efficiency.yaml` for the demo; report it afterwards |
| Flow stream is empty | Simulator not running | Start `python -m backend.simulator` |
| SHAP panel empty | Validation SHAP pool missing | Rebuild with `python -m tools.build_shap_val_pool` (≈45 min) — do it before the day |
| Page shows skeleton forever | Frontend can't reach `/api` | Check the backend is on port 8000; restart `npm run dev` |
| `conda activate` does nothing | Running in cmd.exe | Use PowerShell |
| Port already in use | Old process still running | Close old windows, or `Stop-Process` the old python/node |
| Simulator refuses to start with "test" | `source_split: test` set and allowlist empty | Intended. Set `simulator.source_split: val_shap_pool` |
| Hot-swap rejected | Candidate scored below the incumbent on validation | Not a bug — the gate working. Say so. |
| Laptop has no network | — | Fine; everything is local. Ollama is not needed |

**Fallback:** if the live demo fails entirely, show the six screenshots in `docs/dashboard_v2/screens/` and the public site at `xfed-ids-byzagent.vercel.app`.
