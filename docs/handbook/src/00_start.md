# Part 0 — Start here {#part-0}

## 0.1 What the project is {#what-it-is}

XFed-IDS-ByzAgent is an intrusion detection system (IDS) for network traffic, built by four students as a VIT-AP capstone project. Ten organizations each hold their own network logs. They want one shared attack detector, but they are not allowed to pool their traffic in one place. So they use **federated learning**: each organization trains the detector on its own data, and only the model's learned numbers travel to a central server, which averages them into one shared model. Then the project asks two questions that most federated IDS projects skip. First: **do the organizations' models detect attacks for the same reasons?** (the *explanation check*). Second: **is any organization secretly poisoning the shared model?** (the *trust check*, done by an LLM agent we call ByzAgent). A live dashboard shows detection, explanations and trust decisions side by side.

![The five stages of XFed-IDS-ByzAgent. Stages 3 and 4 are separate experiments that both sit on top of the trained federated model.](img/fig01_pipeline.svg)

## 0.2 The one-line pitch {#pitch}

> **A federated IDS that doesn't just detect attacks, but checks whether its own explanations and its own participants can be trusted.**

(source: `CLAUDE.md`, "The project")

## 0.3 Map of the five stages {#stage-map}

| Stage | Question it answers | Main output | Chapter |
|---|---|---|---|
| 1. Data | What traffic do we learn from, and is it clean? | 1,913,502 cleaned flows in 8 attack families + Benign (source: `data/README.md`) | [2.1](#ch-data) |
| 2. Federated training | Can 10 organizations train one detector without sharing data? | 9 trained runs (3 α × 3 seeds) | [2.2](#ch-model), [2.3](#ch-fl) |
| 3. Explanation check | Do the organizations' models detect attacks for the same reasons? | Jaccard@10 and weighted τ vs α, against chance and a seed-noise floor | [2.4](#ch-expl) |
| 4. Trust check (ByzAgent) | Is any organization poisoning the model? | Trust / downweight / quarantine decisions, compared with Krum, Multi-Krum, trimmed mean | [2.5](#ch-trust) |
| 5. Dashboard | Can an analyst see all of this live? | FastAPI backend + React dashboard, three routes | [2.8](#ch-dash) |

Two later additions sit beside these stages and are reported on their own: a preregistered **accuracy improvement** ([2.6](#ch-prereg)) and an **efficiency** study ([2.7](#ch-eff)). A public **showcase site and film** ([2.9](#ch-site)) present the results to a general audience.

**One rule you must never break when you speak:** stages 3 and 4 are *different experiments with different evidence*. Never combine them into one sentence like "our system explains and defends itself." Say what each one found, separately.

## 0.4 How to use this handbook {#how-to-use}

- **If you have one evening:** read Part 0, then the "In one line" and "What we found" sections of each Part 2 chapter, then Part 6.
- **If you are presenting a stage:** read the Part 1 background it depends on, then its full Part 2 chapter, then its examiner questions.
- **Every number has a source.** It appears like this: 0.333 (source: `results/inspection/agreement_metrics.csv`). If an examiner asks "where does that come from?", open that file. Never quote a number you cannot point to.
- **Locked wording** is marked with a quote bar. Say it exactly as written; it was agreed by the team because looser versions overclaim.
- **Boxes titled "Questions an examiner might ask"** are practice. Read the question, answer it out loud, then compare with the model answer.
- Part 7 has a glossary. If a word confuses you, look there first.

## 0.5 The project in 5 minutes {#five-minutes}

Memorise this. It is the whole project in the order you would tell it.

1. **The problem.** Organizations want a shared attack detector but can't share their network traffic. Federated learning lets them train together while each keeps its data.
2. **The data.** We used Distrinet CICIDS2017 V4, a corrected version of the well-known CICIDS2017 dataset. After cleaning: 1,913,502 flows (source: `data/README.md`), grouped into 8 attack families plus Benign. Infiltration (66 flows) and Heartbleed (11 flows) are below our 1,000-flow floor, so they are reported per class but left out of the headline score (source: `data/README.md`).
3. **The setup.** 10 organizations ("silos"). We control how different their data is with a slider called Dirichlet α: 0.1 (very different), 0.5 (realistic), 5.0 (nearly identical). Three seeds each: 42, 1337, 2024.
4. **Accuracy.** A normal, centralized MLP scores macro-F1 0.9900 ± 0.0022 (source: `results/aggregated/centralized_headline.csv`). Federated averaging (FedAvg) scores 0.516 ± 0.048 / 0.941 ± 0.057 / 0.990 ± 0.001 at α = 0.1 / 0.5 / 5.0 (source: `results/aggregated/federated_headline.csv`). So: when the organizations' data is similar, federation costs nothing; when it is very different, accuracy collapses.
5. **Explanation check.** We use SHAP to find which features each model relies on, and compare each organization's top-10 list with the global model's. Agreement (Jaccard@10) goes 0.333 → 0.538 → 0.667 as α grows (source: `results/inspection/agreement_metrics.csv`). The key trick: a **null control**. Three centralized models that differ only in random seed agree at a median of 0.429 (source: `results/inspection/centralized_instability_floor.csv`). At α=0.1, federated agreement (0.333) falls below even that seed-noise floor — though this is **directional, not significant**, because the confidence intervals overlap.
6. **Trust check.** We poison 3 organizations by flipping 40% of their attack labels to "Benign". An LLM agent (ByzAgent, llama3.1:8b running locally) reads five behaviour statistics per organization each round and says trust, downweight or quarantine. Classical defenses fail here: Multi-Krum excluded a malicious silo 0% of the time (source: `docs/contribution_b_results.md` §4). ByzAgent's result, in the locked words: *"Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition."*
7. **Honesty.** ByzAgent "produces decisions plus a rationale of measured fidelity" — we measured how often its written reasons are wrong. The test set was used in documented ways, which we disclose in full; since 2026-10-12, only one preregistered configuration may ever be scored on it.
8. **Extras.** A preregistered optimizer comparison picked FedAvgM (server momentum 0.9), which on its single test run scored 0.5930 ± 0.0632 / 0.9852 ± 0.0005 / 0.9911 ± 0.0005 (source: `results/federated_methods/test_once/result.json`). ONNX serving cut per-flow latency to 45.7 µs from 186.5 µs (source: `results/efficiency/inference_speed_summary.json`). A dashboard shows it all live.
