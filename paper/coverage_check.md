# Coverage check

Every finding listed in `PROJECT_INSTRUCTIONS.md` ("Findings that limit what can be claimed"
and "Headline numbers"), `docs/contribution_a_results.md`, `docs/contribution_b_results.md`,
`docs/efficiency_results.md` and `docs/preregistration_accuracy.md`, mapped to where it
appears in the paper. Roman numerals are body sections; letters are appendices (e.g. D-C =
Appendix D, subsection C). "Tab." and "Fig." refer to the full version (`main.pdf`).

**Result: all findings covered. Five gaps were found on the first pass and fixed before
this file was written** (marked *added*): the off-manifold SHAP baseline, true-class
anchoring as a choice, the preregistration's stop-and-flag outcome, the unbuilt ByzAgent
benchmarking harness, and the statement that the trust check does not claim ByzAgent beats
the classical rules.

## PROJECT_INSTRUCTIONS.md — Findings that limit what can be claimed (explanation check)

| Finding | Where |
|---|---|
| Round lottery up to 0.118 (α=5.0, seed 42); validation selection required | IV-B Tab. II; C (Tab. fedruns, Fig. valcurves) |
| α=0.1 below-floor result is directional, not significant; CI [0.250, 0.429] vs floor [0.429, 0.484] | Abstract; VI-B; VII; D-B; J |
| Size not independent of skew; KL partial r −0.57 / −0.82 / −0.87; r and n only; entropy tried first, then KL | VI-B; D-C (Tab. kl, Fig. kl) |
| Size-controlled partitions impossible; observational analysis replaced them | VI-B; D-C; J |
| Round-wise agreement declines 5→20 at α=0.1/0.5, flat at 5.0; directional; nsamples=1000 | VI-B; D-D (Tab. roundwise, Fig. roundwise) |
| FedProx μ=0.0005 only: α=0.5 improves with flat accuracy; α=0.1 inconclusive; α=5.0 none | VII; D-E (Tab. fedprox); J |
| Parity monitor needs N≥3 draws; single-draw flags were artifacts | VII; D-F (Tab. parity); J |
| Bot/WebAttack near-duplication tested, not confirmed | VII; D-H; J |
| PortScan genuine generalisation family (23× test-NN distance) | VII; D-H |
| GradientExplainer not DeepExplainer (LayerNorm, additivity error 2.43) | IV-C; D-G; J |
| Val-pool relative residual median 3.2%, p95 7.7%, max 21.2%; 18 rows >8% (Bot 7, Benign 4, WebAttack 4); definition; "~3–8%" dropped; not recomputable for 14 test rows | E (Tab. valpool); J |
| Residuals above 3.336 mainly at α=0.1 (3 of 90 silo files); Spearman r=−0.237 (n=29); pre-specified exclusion leaves 0.333 / 0.592→0.597; post-hoc α=5.0 s1337 drop leaves 0.667 / 0.844 | VI-B; E (Tab. residaudit) |
| Faithfulness is a single-config spot-check, not a gate | VII; D-G (Tab. faith) |

## PROJECT_INSTRUCTIONS.md — Findings that limit what can be claimed (trust check)

| Finding | Where |
|---|---|
| Selection by best-by-validation max; effects as final-5 mean; all four statistics reported | IV-D; V; F-A (Tab. phase0, gradual), F-F (Tab. portability), H (Tab. compf1) |
| train_loss only strong signal (33.8×–154.3×); geometry weak-to-null; val_accuracy inverts | VI-C; F-B (Tab. phase1) |
| 33.8×–154.3× is an effect-size ratio, not a threshold; seed-42 threshold did not transfer (0.017 vs 0.483) | VI-C; H (Tab. prescreen); J |
| Multi-Krum excluded a malicious silo 0% of the time; classical Krum chance-level; f=2 "success" compositional artifact | Abstract; VI-C; F-C (Tab. exclusion, phase2); J |
| Cost of defending with no attack: Krum −22.7pp, Multi-Krum −4.9pp, trimmed mean −1.6pp | VI-C; F-C |
| Locked ByzAgent claim (verbatim) | VI-C (quoted) |
| Rolling history failed its pre-registered test | VI-C; F-G (Tab. phase4, phase4lift); J |
| "produces decisions plus a rationale of measured fidelity"; ~35–45% of trend claims contradicted the data | Abstract; VI-C; F-E; F-G |
| LLM decisions nondeterministic; decision stability reported | VI-C; F-D; F-G |
| Phase 2 baselines, Phase 4 matrix and gradual mode are n=1 by design | VI-C; F (intro) |

## PROJECT_INSTRUCTIONS.md — Headline numbers

| Quantity | Where |
|---|---|
| Centralized MLP 0.9900 ± 0.0022 | Tab. III; C (Tab. centralseed) |
| XGBoost 0.9946 ± 0.0001 | Tab. III; C |
| FedAvg 0.516 ± 0.048 / 0.941 ± 0.057 / 0.990 ± 0.001 | Abstract; Tab. III; C; G |
| Jaccard@10 0.333 → 0.538 → 0.667 | Abstract; VI-B; Fig. 2; D-A |
| Weighted τ 0.592 → 0.787 → 0.844 | VI-B; Fig. 2; D-A |
| Chance Jaccard@10 0.065 (5.1×–10.3×) | Abstract; IV-C; VI-B; D-B |
| Floor median 0.429, range [0.429, 0.484] | Abstract; VI-B; D-B (Tab. floor) |
| Served model fedavg_a0.5_s42, round 18, val 0.9760 | VI-A; H |
| FedAvgM β=0.9 preregistered 0.5930 ± 0.0632 / 0.9852 ± 0.0005 / 0.9911 ± 0.0005 | Tab. III; G (Tab. prereg_test) |
| Latency p50 45.7 µs vs 186.5 µs | Tab. IV; H (Tab. serving) |
| Bytes per round 1,587,920 (793,960 each way) | Tab. IV; H |

## PROJECT_INSTRUCTIONS.md — test-set use and rule going forward

| Item | Where |
|---|---|
| Three choices justified with test numbers; validation agrees (0.9425 vs 0.8602) | V; B (Tab. provenance) |
| Reads (a)–(f) without informing choices | V; I (Tab. exposure) |
| Rule going forward (2026-10-12) | V; I |
| Simulator replays validation; public site uses 500 stored test-row outputs | I; K |

## docs/contribution_a_results.md (beyond the list above)

| Finding | Where |
|---|---|
| Claim framed as boundary conditions on Oki et al., not "first to measure"; null control as methodological contribution | I; II-G |
| Kernel-vs-gradient check (τ 0.730, J@10 0.538, n=14) | D-G |
| Common vs per-silo background ablation (τ 0.807, J@10 0.603, n=42) | D-G |
| Deletion/insertion AUCs for 4 models | D-G (Tab. faith) |
| Zero parity flags at α=0.1 ≠ healthy (median deviation 0.694) | D-F |
| Single-draw bug mechanism (MAD 0.042; seeds 1001/2002/3003) | D-F |
| Zero-order size correlation (r=+0.46 at α=0.1, +0.07 at α=5.0), no p-value shown | D-C |
| Entropy partial r flips sign (+0.23/+0.13, n=30) | VI-B; D-C |
| Recurring α=0.5 pattern, no mechanism proposed | D-I |
| Limitations 1–6, 8 (family-level conflicts, 58,307 rows), 9 (abs residual 0.472/1.105/3.336), 12, 13 (floor is 3 points), 15 (chance assumes uniformity), 16 (no AUC threshold), 17 (SHAP unseeded, 0.0188/0.403), 18 (silos not independent), 19 (n=3 ceiling), 20 (μ single point), 21 (residuals) | VII; A; D-B/C/E/G; E |
| Limitation 7: CPU beats GPU for SHAP (~3×) | D-G; J |
| Limitation 10: explanations never leave the client raw (top-k only) | III; IV-C |
| Limitation 11: background substitution is off-manifold | D (intro) — *added* |
| Limitation 14: ground-truth-class anchoring is a choice | IV-C; D (intro) — *added* |
| Stored residual range 0.156–15.874 (commit-message correction) | E |
| Preregistered optimizer section: protocol, 4 of 9 candidates, SCAFFOLD not run, regression identical, sealed in 1a17277, per-seed and per-class test results, readings, limits (n=3, val gain > test gain, CPU not GPU, FedAdam float64, momentum effect on agreement untested) | VI-A; G (Tabs. prereggrid, prereg_val, sealed, prereg_test, prereg_class); H |

## docs/contribution_b_results.md (beyond the list above)

| Finding | Where |
|---|---|
| Not a claim that ByzAgent outperforms classical rules | F (intro) — *added* |
| Oracle f for baselines vs none for ByzAgent | IV-D; F-C |
| Locked attack config (flip 0.40, targeted to Benign, seed 9001, {0,3,5}); worst-case framing; min coverage 38.60% (DoS); retired {0,1,9} at 13.98%; f=2 {0,3} at 16.73%; flips matched within 1–2 pp | IV-D; F-A |
| Max vs final-5 divergence as a methodological finding | F-A |
| Gradual mode schedule, strength-matched window rounds 1–8, final-5 2–2.5× stronger | F-A (Tab. gradual) |
| val_accuracy caveat written into the prompt | IV-D; F-D |
| Trimmed-mean 2β baseline correction; per-silo excess; silo 5 third axis; clean-control confirmation; silos 3/5 trim 0.7606/0.7216 | F-C (Tab. trim) |
| Multi-Krum excludes {2,7,9} 20/20 rounds in clean control; weight share 9.8%→21.0% (f=2), 32.6% (f=3) | F-C |
| Clean-run test values 0.9753 / 0.9261 / 0.9590 / 0.7480 | F-C |
| LLM model selection (22 cases; 65.1%, 0.8%, 0% / 59.1% ID coverage; 91.6% after citation instruction) | F-D (Tab. llmselect) |
| Fail-loud build, JSON schema, no oracle in prompt, counterfactual probe aggregate, agent_config.json correction | F-D |
| Flag distribution per condition and per silo; four lowest-Benign silos | VI-C; F-D (Tabs. agentdec, agentsilo) |
| Step 3c live re-run not run (would inherit confound) | F-D; J |
| Compositionally matched attack not constructible (211 of 3,174 Bot rows; 5.42% vs 38.60%; 4.35% vs 16.73%) | F-D; J |
| Reasoning-vs-outcome audit at seed 42 (citation frequency, ρ, strict error 11.7%) | VI-C; F-E (Tab. fidelity42) |
| Multi-seed fidelity (22.5%; update_norm +0.419 → −0.076; cited ~59%; 42.6% wrong) | VI-C; F-E (Tab. fidelitynew) |
| Ceiling effect; lifts per seed; canaries; grouping 8/10 and ~5/10; dissociation silo 0; poisonable rows 19,223 vs 48,296 | VI-C (Fig. 3); F-F (Tab. lift) |
| Attacker-selection portability (rank 8/120, 33/120; weakest family 7.91%, 4.85%; gate deltas per seed) | F-F (Tab. portability); J |
| Rolling-history verdict, canary timing, stability 70–80%, FP rate never settles; reasoning diagnostic (ρ collapses; 45.00% of 920 trend claims; 32/35 hand-check; ≈35–45%, ≈39%) | VI-C; F-G |
| Krum/trimmed mean not run in gradual mode; no prompt tuning after diagnostic | F-G; J |
| Phase 5 benchmarking harness moot | F (intro) — *added* |
| Quantization caveat (Bot n=353, WebAttack n=154) and retracted "damaged families" reading | F-G |
| Same 11 WebAttack rows misclassified in all poisoned runs | F-G |
| Two Flower harnesses; bare `flwr run` fails on purpose | K |

## docs/efficiency_results.md

| Finding | Where |
|---|---|
| Pre-screen replay, t=10 from seed 42, does not transfer (0.017 vs 0.483; 59 of 60 hidden); gradual-run loss collapse (0.005/0.096/0.126); live run not done; negative result | H (Tab. prescreen); J |
| Serving: ONNX fp32 identical on 143,513 rows, p50 45.7 vs 186.5 µs, slower at batch 1024; startup gate; 50/50 matched; hot swap uses torch | VI-D; H (Tab. serving) |
| int8 dropped (−0.1428; Bot/WebAttack/Infiltration F1 drops; rewrite check 100%) | VI-D; H; J |
| Bytes: 79,396 per model; 793,960 each way; 1,587,920 total; 1,623,600 as protobuf; logs match | Tab. IV; H |
| Wall time median 51.4 s (26.8–98.7 s; round 1 84.2 s) | Tab. IV; H |
| Compression: fp16 −50.0% / int8 −74.9% uplink; four statistics per seed; no detectable effect at n=3; seed 2024 crossed 0.005 bound | Tab. IV; H (Tabs. compbytes, compf1); J |
| FedAdam float64 downlink | H |

## docs/preregistration_accuracy.md

| Item | Where |
|---|---|
| Question, candidate grid, Flower defaults for FedAdam/FedYogi | G (Tab. prereggrid) |
| Budget estimate, revision, timing-only guard and its disclosure (one score seen) | G |
| Regression check identical at 21 rounds | G |
| Selection rule (guard 0.9325, threshold 0.5428, ties) | G |
| Validation outcome table; choice of fedavgm_m0.9 | G (Tab. prereg_val) |
| Oscillation/final-round caveat recorded before the test (0.5248 vs 0.5062) | G |
| Stop-and-flag conditions not triggered | G — *added* |
| Sealed checkpoints with hashes; single test evaluation; per-class F1 | G (Tabs. sealed, prereg_test, prereg_class) |
| Prior exposure of μ=0.01 (test-scored once before) | B (Tab. provenance); I |
| Environment: CPU build of torch in Flower's isolated env; pinned versions | V; K |
