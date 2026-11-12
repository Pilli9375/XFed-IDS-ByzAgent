# XFed-IDS-ByzAgent Team Handbook — outline and table of contents

Written before the chapters, as the plan for `XFed_Team_Handbook.md`.
Every Part 2 chapter follows the same eight sections:
In one line · Why this exists · How it works · What we actually did ·
What we found · What this does NOT mean · Where it lives in the code ·
Questions an examiner might ask.

Rules carried from `CLAUDE.md`: no new numbers (every number cites its file),
locked wording used verbatim, explanation check and trust check never merged,
every limitation and disclosure included, plain English before any formula.

## Part 0 — Start here
- 0.1 What the project is (one paragraph, one picture)
- 0.2 The one-line pitch
- 0.3 Map of the five stages
- 0.4 How to use this handbook
- 0.5 The project in 5 minutes (memorise this)

## Part 1 — Background from scratch
- 1.1 Network traffic, flows and features
- 1.2 What an intrusion detection system is
- 1.3 Basic machine learning: train / validation / test; overfitting; the MLP;
  softmax and confidence; macro-F1 vs accuracy; class imbalance and class weights
- 1.4 Federated learning: the problem; clients and server; rounds and FedAvg;
  non-IID; the Dirichlet α slider; FedProx and FedAvgM
- 1.5 Explainable AI: SHAP ("sharing the bill"); base value and logits;
  additivity and the residual; GradientExplainer vs DeepExplainer
- 1.6 Comparing explanations: top-k lists; Jaccard@10; weighted Kendall's τ;
  chance level; the null control / seed-noise floor
- 1.7 Poisoning and Byzantine attacks: label flipping; f attackers; Krum,
  Multi-Krum, trimmed mean; the oracle attacker count
- 1.8 LLM agents: what an LLM is; local Ollama llama3.1:8b; nondeterminism
- 1.9 Statistics we used: mean ± sd; median and IQR; cluster bootstrap;
  Spearman and partial correlation; effect size; r and n without p-values;
  pre-registration
- 1.10 Self-check: could a non-ML friend follow this?

## Part 2 — The system, stage by stage (8-part pattern each)
- 2.1 Data
- 2.2 Model and training
- 2.3 Federated training
- 2.4 Explanation check
- 2.5 Trust check (ByzAgent)
- 2.6 Accuracy improvement (preregistered FedAvgM)
- 2.7 Efficiency
- 2.8 Dashboard
- 2.9 Showcase site and film

## Part 3 — Honesty and rigor
- 3.1 The test-set story, start to finish
- 3.2 Every audit we ran, and what it found
- 3.3 What we do NOT claim

## Part 4 — Prior work
- 4.1 Oki et al.; Gholizade et al.; Krum / Multi-Krum / trimmed mean
- 4.2 How we differ (docs only; "[to verify in lit review]" where needed)

## Part 5 — Running it
- 5.1 Running the dashboard for a demo on Windows
- 5.2 Five-minute demo script
- 5.3 If something breaks

## Part 6 — Final-review preparation
- 6.1 Top 40 examiner questions (model answers under 80 words)
- 6.2 Who explains what: four-speaker split with hand-off lines

## Part 7 — Reference
- 7.1 Glossary A–Z
- 7.2 Headline numbers with sources
- 7.3 Repository map
- 7.4 Timeline from git history
- 7.5 Citations as they appear in the docs

## Diagrams planned (≥15, SVG, in `img/`)
Five-stage pipeline · client/server rounds · α=0.1 vs α=5.0 silo composition
(real counts) · train/val/test split · MLP shape · softmax confidence ·
family imbalance · round lottery curve (real) · SHAP "bill" bars · Jaccard
overlap of two top-10 lists · number line with chance and floor · Krum picking ·
Multi-Krum vs trimmed mean · compositional confound · trust dumbbell (real) ·
ByzAgent loop · pre-registration timeline · test-set exposure map · cleaning
funnel · dashboard architecture · hot-swap gate. Plus `results/figures/*.png`
and the six `docs/dashboard_v2/screens/*_1440.png` screenshots.

## Build
`docs/handbook/build/` holds the scripts: figure generation (reads result
files directly), Markdown → HTML (single self-contained file) and HTML → PDF
with the Playwright Chromium already installed for `film/`.
