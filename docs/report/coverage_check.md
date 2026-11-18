# Coverage check: Capstone report

Every finding and item from the project's canonical sources, mapped to the report section where it
appears. Section numbers are those of the built report (chapters 1–7; appendix sections 6.A–6.S).
"Covered" means the item is stated with its numbers and caveats, not only named.

**Result: no uncovered item.** Items skipped on purpose are listed at the end with the reason.

## 1. PROJECT_INSTRUCTIONS.md: "Findings that limit what can be claimed"

| Finding | Report section |
|---|---|
| Round lottery up to 0.118 (validation); validation selection required | 4.1, 4.7, 6.D.1, 6.E.11 |
| α=0.1 below floor is directional, not significant (CIs [0.250, 0.429] vs [0.429, 0.484]) | Abstract, 4.2, 4.6, 6.E.3 |
| Size not independent of skew; KL partial r −0.57 / −0.82 / −0.87; r and n only; entropy first, then KL | 4.2, 6.E.4, 4.7 |
| Size-controlled partitions impossible | 4.2, 6.E.4, 4.5 |
| Round-wise agreement declines at α=0.1, 0.5; flat at 5.0; directional, reduced fidelity | 4.2, 6.E.5 |
| FedProx μ=0.0005 only: α=0.5 gain, α=0.1 inconclusive, α=5.0 no effect | 4.2, 6.E.6 |
| Parity flags need N≥3 draws; single-draw flags were artifacts | 4.2, 4.7, 6.E.7 |
| Bot/WebAttack near-duplication tested, not confirmed | 6.E.9, 4.5 |
| PortScan is the genuine generalisation family (23×) | 6.E.9 |
| GradientExplainer not DeepExplainer (2.43); residual median 3.2%, p95 7.7%, max 21.2%; 18 rows above 8%; "3–8%" dropped | 2.2.4, 4.7, 6.E.8, 6.F.1 |
| Residuals above 3.336 mainly at α=0.1; Spearman −0.237 (n=29); pre-specified exclusion leaves headline; post-hoc α=5.0 drop labelled post-hoc | 4.2, 6.F.2, 6.F.3 |
| Faithfulness is a single-config spot-check | 4.2, 4.6, 6.E.8 |
| Trust: model selection by max, attack effect by final-5 mean; all four statistics | 2.2.5, 4.3, 6.G.1 |
| train_loss the only strong signal (33.8×–154.3×); geometry weak; val_accuracy inverts | 4.3, 6.G.2 |
| 33.8×–154.3× is an effect size, not a threshold; seed-1337 transfer failure (0.017 vs 0.483) | 4.3, 6.G.2, 6.I.5 |
| Multi-Krum 0%; classical Krum chance-level; f=2 success a compositional artifact; costs −22.7 / −4.9 / −1.6 pp | 4.3, 6.G.3 |
| Locked ByzAgent claim, verbatim | 4.3 |
| Rolling history failed its preregistered test | 4.3, 4.7, 6.G.7 |
| "Produces decisions plus a rationale of measured fidelity"; 35–45% trend claims wrong | Abstract, 4.3, 6.G.5, 6.G.7 |
| LLM decisions nondeterministic; stability reported | 4.3, 6.G.4 |
| Phase 2, Phase 4 matrix, gradual mode are n=1 | 4.3, 4.6, 6.G |
| Test-set use: three choices first justified on test, validation re-check, (a)–(f) reads, rule of 2026-10-12 | 2.2.7, 6.J |

## 2. PROJECT_INSTRUCTIONS.md: "Headline numbers"

| Quantity | Report section |
|---|---|
| Centralized MLP 0.9900 ± 0.0022; XGBoost 0.9946 ± 0.0001 | Abstract, 4.1, 6.D.2 |
| FedAvg 0.516 / 0.941 / 0.990 with std | Abstract, 4.1, 6.D.1 |
| Jaccard@10 0.333 → 0.538 → 0.667; τ 0.592 → 0.787 → 0.844 | Abstract, 4.2, 6.E.2 |
| Chance 0.065 (5.1×–10.3×); floor 0.429 [0.429, 0.484] | Abstract, 4.2, 6.E.3 |
| Served model fedavg_a0.5_s42, round 18, 0.9760 | 2.4.1, 4.1, 6.I.1 |
| FedAvgM preregistered 0.5930 / 0.9852 / 0.9911 | 4.1, 6.H.5 |
| Latency 45.7 vs 186.5 µs | 3.3, 4.4, 6.I.1 |
| Bytes per round 1,587,920 (793,960 each way) | 3.3, 4.4, 6.I.2 |

## 3. docs/contribution_a_results.md (explanation check)

| Item | Report section |
|---|---|
| §1 Claim as boundary conditions on Oki et al.; null control | 1.2.7, 4.2 |
| §2 Headline agreement, chance, floor, CI | 4.2, 6.E.2, 6.E.3 |
| §3 Round-wise tables (J@10, τ, val F1) and three validation checks (kernel vs gradient, background ablation, deletion/insertion) | 6.E.5, 6.E.8 |
| §4 Parity monitor: 3 flags of 356, zero flags at α=0.1 not healthy, multi-draw bug and fix | 6.E.7 |
| §5 Size vs heterogeneity: derivation, zero-order r, entropy then KL | 6.E.4 |
| §6 FedProx per-seed tables at all three α | 6.E.6 |
| §7 Recurring α=0.5 pattern, no mechanism | 6.E.10 |
| Test-set access note and rule change | 2.2.7, 6.J |
| Limitations table, all 21 rows | 6.E.11 (and 4.6) |
| Correction of commit e798a36's range (0.156–15.874) | 6.F.2 |
| Added result: preregistered optimizer comparison (selection, test, per-class, reading, limits, FedAdam float64 note) | 4.1, 6.H, 6.I.2 |

## 4. docs/contribution_b_results.md (trust check)

| Item | Report section |
|---|---|
| §1 What the check is and is not; oracle asymmetry | 4.3, 6.G |
| §2 Attack configuration, worst-case framing, retired rule, coverage, four statistics, gradual mode | 2.2.5, 4.3, 6.G.1, 6.P.3 |
| §3 Five statistics and Glass's δ table; val_accuracy hazard | 4.3, 6.G.2 |
| §4 Baselines, outcomes, exclusion vs chance, compositional artifact, trimmed-mean 2β correction, clean-control confirmation, open item | 4.3, 6.G.3 |
| §5 LLM selection, build, agent_config.json correction, probe aggregate, flag rates, stability, fidelity audit, no live re-run, no matched control | 4.3, 6.G.4, 6.G.5 |
| §6 Rolling history matrix, lift, verdict, diagnostic, not-run items | 4.3, 6.G.7 |
| §7 Multi-seed validation, ceiling effect, revised claim | 4.3, 6.G.6 |
| §8 Fidelity at new seeds; hand-validation of 45.00% | 4.3, 6.G.5, 6.G.7 |
| §9 Attacker-selection portability | 6.G.6 |
| §10 Limitations: n=1 items, open entanglement, silo 0 attribution, trend range, quantization caveat, WebAttack artifact, two harnesses | 4.6, 6.G.8 |
| §11 Artifact index | 6.Q |

## 5. docs/efficiency_results.md

| Item | Report section |
|---|---|
| Part A pre-screen replay (t=10, all four runs, retention, reading, limits, decision) | 4.4, 6.I.5 |
| Part B serving: protocol, three variants, int8 per-class drop, Gemm rewrite, backend wiring and start-up gate | 4.4, 6.I.1 |
| Part C1 bytes per round and harness cross-check; FedAdam footnote | 3.3, 6.I.2 |
| Part C2 wall time per round | 3.3, 6.I.3 |
| Part C3 compression: method, bytes, four statistics per seed, absolute values, wall time | 4.4, 6.I.4 |

## 6. docs/preregistration_accuracy.md

| Item | Report section |
|---|---|
| Question, candidates, budget cut and revision, guard, regression check, SCAFFOLD, prior μ=0.01 exposure, environment | 6.H.1, 6.H.3 |
| Fixed settings, baseline, selection rule, stop-and-flag, plan if chosen | 6.H.1, 6.H.2 |
| Part 2: validation outcome, pre-test warning, chosen YAML (FedAvgM formula), sealed checkpoints, metric, procedure | 6.H.4, 6.H.5, 6.P.1 |

## 7. docs/test_set_exposure_audit.md

| Item | Report section |
|---|---|
| Exposure table, rows 1–9, and non-exposures checked | 6.J.1 |
| Provenance table of locked choices and its outcome | 6.C.5, 6.J.2 |

## 8. paper/appendix.tex, every section

| Paper appendix | Report section |
|---|---|
| A Dataset and Cleaning | 6.A, 6.B |
| B Model and Training Choices | 6.C |
| C Federated Accuracy, Full | 6.D |
| D Explanation Check, Full (subsections A–I) | 6.E |
| E SHAP Additivity Residuals | 6.F |
| F Trust Check, Full (Phases 0–4, fidelity, multi-seed) | 6.G |
| G Preregistered Accuracy Study | 6.H |
| H Efficiency | 6.I |
| I Test-Set Exposure Audit | 6.J |
| J Negative and Null Results | 4.5 |
| K System Implementation | 2.4, 6.K |
| L Reproducibility | 6.M |

## 9. docs/handbook/ chapters

| Handbook chapter | Report section |
|---|---|
| 00 Start here (pitch, five stages, project in five minutes) | Abstract, 2.1 |
| 01 Background (flows, IDS, ML basics, FL, SHAP, comparing explanations, poisoning, LLM agents, statistics) | 1.2, 6.P, List of Abbreviations, List of Symbols |
| 02a Data, model and FL | 2.2.1–2.2.3, 6.A–6.D |
| 02b Explanation check | 2.2.4, 4.2, 6.E, 6.F |
| 02c Trust check | 2.2.5, 4.3, 6.G |
| 02d Preregistration, efficiency, dashboard, site and film | 6.H, 6.I, 6.K, 6.N |
| 03 Honesty and rigour (test-set story, audits, what we do not claim) | 2.2.7, 4.5, 4.6, 6.J, 1.2.7 |
| 04 Prior work and running it | 1.2, 6.M |
| 06 Review preparation (examiner questions, speaker split) | Skipped: exam rehearsal material, not project content |
| 07 Reference (glossary, headline numbers, repository map, timeline, citations) | List of Abbreviations, 4.1–4.4, 6.M, 6.L, Chapter 7 |

## 10. Addendum items (full coverage and addendum 2)

| Item | Report section |
|---|---|
| Distrinet V4 vs original; cleaning with counts; family mapping; floor; group-aware split; duplicates; SHA256 manifest | 6.A, 6.B.2 |
| Per-silo label distributions for every α and seed (9 tables) | 6.B.3 |
| Every locked setting, pilots, alternatives, provenance | 2.2.3, 6.C |
| All nine FedAvg runs, per-class F1 incl. Infiltration and Heartbleed, round lottery, centralized and XGBoost per seed | 6.D |
| System implementation: harness and command, configs, every endpoint, dashboard (routes, panels, themes, ambient light, loading states, hot-swap gate and rejection detail, validation simulator), all six tracked screenshots, Streamlit app, showcase site | 2.4.1, 6.K |
| Development timeline from git history, with changes of direction | 6.L |
| Reproducibility: versions, commands, seeds, configs, repository link, results locations | 6.M |
| Project outputs: paper (title, both versions), handbook, README, dashboard, site, film | 6.N |
| Software and libraries with versions and use | 2.4.1, 6.O.1 |
| Models: MLP architecture and parameter count; XGBoost settings; every LLM tried and why one was picked | 6.C.1, 6.C.6, 6.G.4, 6.O.2 |
| Algorithms with formulas: FedAvg, FedProx, FedAvgM, FedAdam (and FedYogi), Krum, Multi-Krum, trimmed mean, SHAP Gradient and Kernel explainers, Dirichlet partitioning, class weights | 6.P.1 |
| Metrics with definitions and where used | 6.P.2 |
| Attack setup, worst-case | 2.2.5, 6.G.1, 6.P.3 |
| Hardware and what ran where | 2.4.2, 3.1, 6.O.3 |
| Development tools and AI-assistance disclosure | 6.O.4 |
| Results inventory with unused files marked | 6.Q |
| List of Abbreviations, List of Symbols | Front matter |
| Challenges faced and how we solved them | 4.7 |
| Testing and checks with last recorded result | 2.5, 6.R |
| Contribution of each member | 5.3 (text supplied by the team) |
| Key code excerpts with captions and paths | 6.S |
| Standards actually used | 2.3 |
| Cost analysis: nothing bought, owned hardware, free software, measured compute | Chapter 3 |

## 11. Every table and figure in paper/ and results/figures/

| Item | In the report |
|---|---|
| paper Fig. 1 pipeline (TikZ) | Figure 2.1 (cropped from paper/main.pdf) |
| paper fig_agreement_alpha | Figure 4.2 |
| paper fig_byzagent_lift | Figure 4.4 |
| paper fig_val_curves | Figure 4.1 |
| paper fig_phase0_curves | Figure 4.3 |
| paper fig_kl_scatter | Figure 6.3 |
| paper fig_round_wise | Figure 6.5 |
| paper dash_live_alert.png | Skipped: a crop of live_deep-sea_1440.png, which is used whole as Figure 2.2 |
| paper dash_hotswap.png | Skipped: replaced by the two hot-swap screenshots it was taken from (Figures 2.4 and 6.17) |
| results/figures: agreement_vs_alpha, instability_floor_vs_alpha, entropy_kl_partial_correlation, agreement_vs_round, accuracy_agreement_decoupling, fedprox_vs_fedavg_per_seed, parity_monitor, deletion_curve, insertion_curve | All nine in 6.E (Figures 6.1, 6.2, 6.4, 6.6–6.11) |
| docs/dashboard_v2/screens: six tracked 1440 px screenshots (Live and Investigate, three themes) | Figures 2.2, 2.3, 6.12–6.15 |
| Other dashboard screenshots on disk | Limits (6.16), hot-swap running (6.17) and rejection detail (2.4) used; the 360 px phone views, loading screens and duplicate dialog captures skipped as repeats |
| paper tables: related work, locked settings, accuracy, efficiency, tools | Tables 1.1, 2.1, 4.1, 4.8, 2.4 |
| paper appendix tables (attempted, family map, cleaning, families, empty cells, pilots, provenance, FedAvg runs, centralized per seed, per-class, agreement by α and family, floor, KL, round-wise, FedProx, parity, faithfulness, residual pool and audit, Phase 0–4, LLM selection, agent decisions and per-silo, fidelity, portability, lift, prereg grid, validation, sealed, test, per-class, serving, compression bytes and F1, pre-screen, exposure, negative, endpoints, commands, files) | All present in Chapters 4 and 6; wide tables are split in two (agreement by family; FedProx; serving) |
