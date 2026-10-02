# XFed-IDS-ByzAgent — Project Instructions

Paste into Claude Code's `CLAUDE.md` at the repo root, and into the project settings of any new chat.

---

## Who I am

Vulavakayala Naga Adithya (Pilli), CSE Core, VIT-AP. Solo on Contribution A; ByzAgent is a team commitment.
Hardware: RTX 4050 6GB VRAM (hard ceiling), 24GB RAM, Windows 11, Ryzen 7 7435HS.
Environment: conda env `xfed`, project root `C:\Pilli\Capstone\xfed-ids\`, artifacts under `results/`.
Note: `conda activate` is a no-op in cmd.exe on this machine — PowerShell must be spawned explicitly.

**Reviews:** First — DONE. **Second — Sep 29–Oct 3 (30 marks) ← everything targets this.** Final — Nov 17–21 (40 marks). Report — Nov 20 (20 marks).

---

## The two contributions — keep them separate

**Contribution A (mine, protect above all): explanation parity.**
Under realistic non-IID federation, accuracy parity between silos does not imply explanation parity. Measured as Jaccard@k and weighted Kendall's τ against Dirichlet α, with a centralized-seed instability floor as null control.
**Canonical results write-up: `docs/contribution_a_results.md`.** The headline numbers, limitations list, and known-findings bullets below defer to it — update that file first when a number changes.

**Contribution B (team): ByzAgent.**
An LLM agent reasoning over per-client behavioural statistics to make and explain trust decisions during aggregation, replacing fixed-threshold rules like Krum.

Different contributions, different lineages. Keep them visibly separate in the repo, the slides, and the report.

---

## Novelty framing — exact wording

- **Never** say "first to measure." Oki et al. (IEEE Networking Letters, 2024) already measured distance between distributed and non-distributed IDS feature sets.
- The claim is **boundary conditions on Oki**: they showed FL reduces explanation distance; we characterise where that reduction breaks down under heterogeneity.
- The **null control is the headline methodological contribution** — no prior work reports a baseline for how much explanation ranking varies from random seed alone.
- Cite Gholizade et al., arXiv 2607.13045 (June 2026 FedXAI survey) for open-challenge justification: it names explanation consistency under non-IID as unsolved and flags the absence of standardised metrics.
- The LLM explanation layer is **usability, never novelty**.

---

## Five locked decisions (immutable)

1. Distrinet CICIDS2017 V4 — Liu et al. (IEEE CNS 2022) + Engelen et al. (WTMC-2021). Both cited.
2. 8 families + Benign, 1,000-flow floor. Infiltration and Heartbleed excluded from headline macro-F1, reported per-class only.
3. 10 silos, α ∈ {0.1, 0.5, 5.0}, 3 seeds, partitions on disk with SHA256 manifest.
4. Client-side SHAP, fixed seeded background 100–200 rows per silo. **Only top-k rankings cross the trust boundary.**
5. All 10 silos train regardless of size. Size floor applies to explanation-eligibility analysis only.

**Locked model config:** StandardScaler (RobustScaler degenerates on 28/82 zero-IQR features — DDoS F1 0.716 vs 1.000), effective-number β=0.999, [128,64], dropout 0.1, LayerNorm (**not** BatchNorm — batch statistics don't aggregate meaningfully in FL), 3 local epochs, 9-wide frozen vocab, best-by-validation selection. **Test touched exactly once.**

---

## How to work with me

- **Reasoning before code.** I have to defend everything orally. If I can't explain it, it doesn't ship.
- **Brutal honesty over optimism.** Tell me what isn't done. Tell me when a claim is weaker than I think.
- Step-by-step instructions; downloadable scripts over long in-conversation code blocks.
- All parameters in config YAML. Nothing hardcoded.
- **Verify schemas empirically before writing code against any file.** One-liner in PowerShell, paste output back. This rule exists because I've been burned.
- Priority stack: Understanding > Science > Architecture > Code > Optimisation.
- Prefer standard over clever. A cited method I can defend beats a novel one I can't.
- **Do not make research decisions.** Scope changes, novelty claims, and "we could also add X" route back to 01_Planning first.

---

## Scope — confirmed, nothing cut

**Contribution A:** round-wise agreement · protocol write-up · server-side parity monitoring · size-controlled partitions · full FedProx sweep

**Phase 2 app:** FastAPI backend · React + Recharts port of the 6 existing sections · family-labelled traffic simulator (9-class, not binary) · live alert stream with instant SHAP from precomputed .npz · hot-swap retraining · small LLM explanation layer

**ByzAgent:** Phase 0 (poisoning simulation) · Phase 4 (rolling history vs gradual attack) **first**, then Phases 2, 3, 5, 6

**Build order:**
round-wise agreement → protocol write-up → ByzAgent Phase 0 + Phase 4 → parity monitoring → React port → ByzAgent remaining → hot-swap → size-controlled partitions → FedProx sweep → LLM layer

ByzAgent Phase 4 is early on purpose: it is the only real finding in that track. If rolling history doesn't beat Krum on gradual poisoning, that needs to surface in week one.

---

## Known findings that constrain claims

- **Round lottery is real** — gap up to 0.118 between best-by-validation and final-round test numbers. Validation selection is not optional.
- **Bot/WebAttack near-duplication** (test-NN ≈ 0.0): the pre-registered inflation caveat was tested and **not** confirmed. State as tested-and-not-confirmed. Thin dataset support (Bot=3,527, WebAttack=1,542) is the likelier explanation.
- **PortScan is the genuine generalisation family** — 23× further test-NN distance; bimodal recall (0.9505 / 0.9506 / 0.9995).
- **Below-floor claim at α=0.1 is directional, not significant** — cluster-bootstrap CIs overlap ([0.250, 0.429] vs floor range [0.429, 0.484]). Never state as confirmed.
- **Silo size is a deterministic output of the label draw, not a separate cause** — under `dirichlet_assign()`, per-family proportions sum to 1 over silos by construction, so size and heterogeneity can't be varied independently. Conditioning on log(size), KL-from-global still predicts agreement (r=−0.57 at α=0.1, −0.82/−0.87 at α=0.5) — heterogeneity's effect holds up, size alone doesn't explain it away.
- **GradientExplainer, not DeepExplainer** — DeepExplainer fails on LayerNorm (additivity error 2.43 vs 0.01 tolerance), confirmed by probe not assumption.
- **CPU beats GPU for this SHAP workload** — GPU 3× slower, kernel-launch overhead dominates on a 19.5k-param model. Measured.
- **Family-level conflict detection** over raw-label — the raw-label approach silently destroyed 58,307 learnable rows.
- **Streamlit practical ceiling reached** — Phase 1 is at the limit of what Streamlit does well.

Canonical source for Contribution A numbers: docs/contribution_a_results.md.
Where it disagrees with this file or app_lib/sections.py, it wins.

---

## Headline numbers (state these exactly)

| Quantity | Value |
|---|---|
| Centralized MLP macro-F1 | 0.9900 ± 0.0022 |
| XGBoost macro-F1 | 0.9946 ± 0.0001 |
| FedAvg α=0.1 | 0.516 ± 0.048 |
| FedAvg α=0.5 | 0.941 ± 0.057 |
| FedAvg α=5.0 | 0.990 ± 0.001 |
| Jaccard@10 across α | 0.333 → 0.538 → 0.667 |
| Weighted Kendall's τ across α | 0.592 → 0.787 → 0.844 |
| Chance-level Jaccard@10 | 0.065 (so 5.1×–10.3× chance) |
| Centralized-seed instability floor | median 0.429, range [0.429, 0.484] |

---

## For ByzAgent specifically

- The shared implementation plan describes a **different codebase** (78 features, dropout 0.3, KernelExplainer, BatchNorm, 3 clients, binary classification). Mine is 82 features, dropout 0.1, GradientExplainer, LayerNorm, 10 silos, 9-class. **Reconcile before generating any code.**
- **Run the agent 3× per config and report decision variance.** LLM decisions are nondeterministic; a project built on reproducibility needs an answer to "is this repeatable?"
- Phase 0 is the poisoning simulation — do not build it twice as a separate item.
- Reject scope creep: no causal discovery, no multi-attack-type classification, no confidence-based human-in-loop, no additional attack types beyond label-flip. Deliberately cut.
- Log seed and round for every hot-swap so the retrained model stays auditable.

---

## Escalation triggers — surface immediately

- Any locked decision comes under pressure
- ByzAgent Phase 4 fails to beat Krum / trimmed-mean on gradual poisoning
- Federated explanation quality beats centralized (possible leakage)
- Agreement metrics stop being computable at any α (too few eligible silos)
- Anything requiring the test set to be touched a second time
- Claude Code proposes anything not in the confirmed scope list

---

## Repo layout

```
C:\Pilli\Capstone\xfed-ids\
  configs/      data.yaml, model.yaml, global_class_weights.json, xgboost_tuned.json
  data/processed/   clean.parquet, train_pool.parquet, test_global.parquet,
                    val_mask.parquet, partitions/
  src/          existing pipeline + new: attacks/, monitoring/, aggregation/, agents/
  results/      centralized/ xgboost/ federated/ shap/ inspection/ figures/ aggregated/
  backend/      FastAPI (Phase 2)
  dashboard/    React + Recharts (Phase 2)
  experiments/
```

Dataset stays outside the repo at `C:\Pilli\Capstone\Dataset\`.
`.gitignore` excludes `*.csv`, `*.parquet`, `data/shards/`, `results/runs/`, `*.pth`, `__pycache__`.
