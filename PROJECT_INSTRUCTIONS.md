# XFed-IDS-ByzAgent — Project Instructions

Single source of rules for this project. The same text lives in three places:
the claude.ai project settings, `CLAUDE.md` (read by every Claude Code session),
and `PROJECT_INSTRUCTIONS.md` in the public repo.

---

## The project

A federated intrusion detection system for network traffic, built as a VIT-AP
capstone team project. One line: **a federated IDS that doesn't just detect
attacks, but checks whether its own explanations and its own participants can
be trusted.**

One system, five stages:

1. **Data** — Distrinet CICIDS2017 V4, cleaned into 8 attack families + Benign.
2. **Federated training** — 10 organizations (silos) train a shared detector
   without sharing traffic, under realistic non-IID data (Dirichlet α).
3. **Explanation check** — do the organizations' models detect attacks for the
   same reasons? Measured as Jaccard@k and weighted Kendall's τ against α,
   compared to a centralized-seed instability floor (null control).
4. **Trust check (ByzAgent)** — is any organization poisoning the model? An LLM
   agent reads per-organization behaviour statistics each round and decides
   trust / downweight / quarantine, compared against Krum, Multi-Krum and
   trimmed-mean.
5. **Dashboard** — live detection, explanations and trust decisions together.

Present it as one system and one story. Report the findings of stage 3 and
stage 4 separately, each with its own evidence; they are different experiments
and must never be blended into one claim.

Canonical results: `docs/contribution_a_results.md` (explanation check) and
`docs/contribution_b_results.md` (trust check). Where anything else disagrees
with them, they win.

---

## Environment

- Hardware: RTX 4050 6GB VRAM (hard ceiling), 24GB RAM, Windows 11.
- Conda env `xfed`. `conda activate` is a no-op in cmd.exe on this machine;
  use PowerShell.
- Project root `C:\Pilli\Capstone\xfed-ids\`. Raw dataset stays outside the repo
  at `C:\Pilli\Capstone\Dataset\`.
- Authoritative FL harness: `federated/xfed_federated/` (not `src/federated/`).
  A bare `flwr run` fails on purpose; the real invocation is
  `flwr run federated local-simulation`.

---

## How this project differs from prior work

- Oki et al. (IEEE Networking Letters, 2024) showed federated training reduces
  explanation distance in a distributed IDS. This project characterises where
  that reduction breaks down as client data becomes more heterogeneous.
- It adds a null control no prior work reports: how much explanation rankings
  differ between centralized models that differ only by random seed. Without
  it, a reported difference cannot be told apart from seed noise.
- Gholizade et al. (arXiv 2607.13045, June 2026 FedXAI survey) names
  explanation consistency under non-IID data as an open challenge and notes
  there are no standard metrics for it.
- The trust check tests Krum and its variants with 10 clients and an oracle attacker
  count, and audits how often the agent's own explanations are accurate.
- The LLM explanation sentences in the dashboard are a usability feature, not a
  research claim.
- Do not claim "first to measure", and do not claim the broad
  "FL + IDS + XAI" combination as new; several 2025–2026 papers cover it.

---

## Locked decisions

1. Dataset: Distrinet CICIDS2017 V4 — Liu et al. (IEEE CNS 2022) and Engelen
   et al. (WTMC 2021). Cite both.
2. 8 attack families + Benign, 1,000-flow floor. Infiltration and Heartbleed
   are excluded from headline macro-F1 and reported per class only.
3. 10 silos, α ∈ {0.1, 0.5, 5.0}, 3 seeds (42, 1337, 2024), partitions on disk
   with a SHA256 manifest checked at load.
4. Client-side SHAP with a fixed seeded background of 100–200 rows per silo.
   Only top-k rankings cross the client→server boundary.
5. All 10 silos train regardless of size. The size floor applies only to
   explanation-eligibility analysis.

Model config: StandardScaler (RobustScaler degenerates on 28/82 zero-IQR
features), effective-number class weights β=0.999, MLP [128, 64], dropout 0.1,
LayerNorm (BatchNorm statistics don't aggregate in FL), 3 local epochs, 9-wide
frozen label vocabulary, best-by-validation round selection.

**The test set is evaluated exactly once.** Two later read-only extractions of
raw features (514 already-explained rows, for demo display) are documented in
`docs/contribution_a_results.md`; no metric derives from them.

---

## How to work

- Reasoning before code. Every choice must be explainable out loud.
- Honest over optimistic: say what isn't done and when a claim is weaker than
  it sounds.
- Verify schemas empirically (print them) before writing code against a file.
- All parameters in YAML config. Nothing hardcoded.
- Never fabricate, round up, smooth or "illustrate" a number. Every number
  shown anywhere traces to a file on disk. Placeholder or sample data must be
  labeled as such.
- Prefer standard, citable methods over clever ones.
- Claude Code implements; research decisions, scope changes, claim wording and
  "we could also add X" go back to the planning chat first.
- Report back from every Claude Code session as:
  Done / Numbers / Decided / Blocked-unsure / Next.

---

## Findings that limit what can be claimed

**Explanation check**
- Round lottery is real: up to 0.118 between best-by-validation and final-round
  numbers. Validation-based selection is required.
- The below-floor result at α=0.1 is directional, not significant
  (cluster-bootstrap CIs overlap: [0.250, 0.429] vs floor [0.429, 0.484]).
- Silo size is not independent of label skew under Dirichlet partitioning; it
  is largely determined by it. After conditioning on log(size), KL divergence
  from the global label distribution still predicts agreement (partial
  r = −0.57 at α=0.1, −0.82/−0.87 at α=0.5). Report r and n only, no p-values
  (silos within a seed are not independent). Entropy was tried first and
  failed this conditioning; KL was substituted after — state that order.
- Size-controlled partitions were proven impossible under this partitioner;
  the observational analysis above replaced them.
- Round-wise agreement declines rounds 5→20 at α=0.1 and α=0.5 while val
  macro-F1 rises; flat at α=5.0. Directional, reduced SHAP fidelity
  (nsamples=1000).
- FedProx result is at μ=0.0005 only: at α=0.5 agreement improves with flat
  accuracy across all 3 seeds; α=0.1 inconclusive at n=3; α=5.0 no effect.
- Parity monitor flags rely on multi-draw averaging (N≥3); single-draw flags
  were shown to be artifacts.
- Bot/WebAttack near-duplication caveat: tested and not confirmed.
- PortScan is the genuine generalisation family (23× further test-NN distance).
- GradientExplainer, not DeepExplainer (fails on LayerNorm, additivity error
  2.43). Additivity residual ~3–8% relative, bounded by a KernelExplainer check.
- Faithfulness is a single-config spot-check (α=0.5, seed 42), not a gate.

**Trust check (ByzAgent)**
- Model selection uses best-by-validation max; attack effects are reported as
  the final-5-round mean. Report all four statistics for every comparison.
- train_loss is the only strong attack signal (33.8×–154.3×); geometry stats
  are weak-to-null; val_accuracy inverts (malicious clients score higher on a
  Benign-heavy validation set).
- Multi-Krum excluded a malicious silo 0% of the time (classical Krum's exclusions are chance-level: it keeps 1 of 10 every round); Multi-Krum's f=2 "success"
  was a compositional artifact. Defending with nobody attacking costs Krum
  −22.7pp, Multi-Krum −4.9pp, trimmed-mean −1.6pp.
- Locked ByzAgent claim (use verbatim): "Both effects are present. A real
  compositional confound saturates some silos' flag rates independent of any
  attack; real attack-responsive detection is also present and becomes visible
  where silos are not already saturated. Seed 42's apparent null was partly a
  ceiling artifact of that seed's unusually bimodal composition."
- Rolling history failed its pre-registered test.
- Explainability wording: "produces decisions plus a rationale of measured
  fidelity", never "explains its reasoning". ~35–45% of trend claims
  contradicted the data they were given.
- LLM decisions are nondeterministic; report decision stability with them.
- Phase 2 baselines, Phase 4 matrix and gradual mode are n=1 by design.

---

## Headline numbers (state exactly)

| Quantity | Value |
|---|---|
| Centralized MLP macro-F1 | 0.9900 ± 0.0022 |
| XGBoost macro-F1 | 0.9946 ± 0.0001 |
| FedAvg α=0.1 / 0.5 / 5.0 | 0.516 ± 0.048 / 0.941 ± 0.057 / 0.990 ± 0.001 |
| Jaccard@10 across α | 0.333 → 0.538 → 0.667 |
| Weighted Kendall's τ across α | 0.592 → 0.787 → 0.844 |
| Chance-level Jaccard@10 | 0.065 (5.1×–10.3× chance) |
| Centralized-seed instability floor | median 0.429, range [0.429, 0.484] |
| Served demo model | fedavg_a0.5_s42, round 18, val macro-F1 0.9760 |

---

## Stop and flag immediately

- Anything that would touch the test set again
- A locked decision under pressure
- Federated explanation quality beating centralized (possible leakage)
- A result that looks too good
- A hot-swapped model that can't be reproduced from its logged seed
- Any proposal outside the scope above

---

## Repo layout

```
configs/      data.yaml, model.yaml, backend.yaml, hotswap.yaml, ...
data/         README.md; processed/ (git-ignored parquet)
federated/    xfed_federated/  — authoritative FL harness
src/          pipeline, attacks/, monitoring/, aggregation/, agents/, hotswap/
tools/        analysis and export scripts
results/      shap/, federated/, inspection/, figures/, attacks/, defenses/, agents/
backend/      FastAPI
frontend/     React + Recharts dashboard
docs/         contribution_a_results.md, contribution_b_results.md,
              measurement_protocol.md
app.py, app_lib/   Streamlit (Phase 1)
```
