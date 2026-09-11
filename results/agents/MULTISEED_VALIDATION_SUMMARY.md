# ByzAgent Multi-Seed Validation — Compositional Confound, Explanation Fidelity, Trend-Error Heuristic

**Status: CLOSED, accepted by 01_Planning.** All 5 steps complete. This document was written incrementally, in the order the ground truth's steps ran, so every prediction below was recorded **before** the data that would test it existed. **Headline result: the ceiling effect (see its own section below) — seed 42's malicious silos started saturated (~0.95–1.00) in the clean run, mathematically capping how much lift an attack could show; seeds 1337/2024 mostly lack that ceiling, and once removed the agent visibly does respond to attack.** This bounds, but does not retract, Phase 3's seed-42 finding — see the corrected claim below.

Scope: seeds 1337 and 2024, alpha=0.5, in addition to the existing seed-42 numbers already published in `PHASE0_SUMMARY.md`–`PHASE4_SUMMARY.md`. Only three findings are being multi-seeded here (the compositional-confound/canary finding, the explanation-fidelity audit, and the owed Phase 4 trend-error hand-check) — see "What remains n=1, deliberately" at the end of this document for what is NOT in scope and why.

---

## Step 1 — partition verification + pre-registration (read-only)

### 1a — partitions confirmed on disk

Both `alpha=0.5` partitions for seeds 1337 and 2024 exist and are **hash-verified byte-exact** against `data/processed/partitions/manifest.json` (recomputed `sha256(silo_assignment.tobytes())` independently, matched both `hash_train` and `hash_test`):

| seed | train rows | test rows | hash_train | hash_test |
|---|---|---|---|---|
| 1337 | 1,435,126 | 478,376 | `228e29f12d95d485fc7b7f27515e18be265d676c5407a880989da9a42a8159c5` | `ffac93e60e2e94bb68d9616af6eba3cab1b325316f2758281733ebbf9ed440bc` |
| 2024 | 1,435,126 | 478,376 | `24f00a1f3e55e65c8a221346b6bde44e5ef0aff7fbdb372596470bab34a5ed98` | `4a9fbaae838794c767586c87bd11311aa714423b750e4c1a5543b7d75beda736` |

No regeneration performed.

### 1b — per-silo family-composition tables (train-only, val_mask excluded)

Method: reproduces `results/inspection/silo_family_composition_a0.5_s42.csv` exactly (verified byte-for-byte before trusting it on new seeds). The composition tables Phase 0/2/3 actually used are **not** the raw partition assignment — they exclude the 143,513-row centralized validation holdout (`data/processed/val_mask.parquet`, derived once from `train_pool.parquet`, identical across all partition seeds). Confirmed: reconstructing seed 42's file from `assign_a0.5_s42_train.parquet` + `val_mask.parquet` + `train_pool.parquet`'s `family` column reproduces the on-disk CSV exactly.

New artifacts: `results/inspection/silo_family_composition_a0.5_{s1337,s2024}.csv`.

**Seed 1337:**

| silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | TOTAL | Benign% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 401,889 | 251 | 122 | 8,725 | 4,427 | 0 | 0 | 5,270 | 428 | 421,112 | **95.44%** |
| 1 | 26,355 | 853 | 401 | 5,682 | 11,538 | 0 | 20 | 350 | 3 | 45,202 | 58.30% |
| 2 | 7,665 | 389 | 0 | 881 | 5,877 | 1 | 10 | 11,574 | 135 | 26,532 | 28.89% |
| 3 | 82,481 | 57 | 1,763 | 19,299 | 20,148 | 1 | 8 | 8,478 | 11 | 132,246 | **62.37%** |
| 4 | 0 | 35 | 943 | 3,407 | 12,002 | 2 | 0 | 515 | 148 | 17,052 | 0.00% |
| 5 | 27,584 | 320 | 240 | 1,996 | 5,739 | 0 | 1 | 23,558 | 405 | 59,843 | **46.09%** |
| 6 | 41,949 | 101 | 222 | 18,807 | 347 | 0 | 0 | 28,261 | 100 | 89,787 | 46.72% |
| 7 | 2,349 | 318 | 19 | 5,005 | 54,105 | 1 | 0 | 1,098 | 84 | 62,979 | 3.73% |
| 8 | 120,492 | 117 | 68 | 60 | 5,322 | 1 | 5 | 8,797 | 28 | 134,890 | 89.33% |
| 9 | 261,843 | 733 | 928 | 360 | 301 | 1 | 1 | 37,757 | 46 | 301,970 | 86.71% |

**Seed 2024:**

| silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | TOTAL | Benign% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 86,680 | 144 | 1 | 16,072 | 21,495 | 0 | 3 | 10,569 | 12 | 134,976 | **64.22%** |
| 1 | 150,879 | 102 | 1,310 | 1,912 | 412 | 2 | 1 | 311 | 216 | 155,145 | 97.25% |
| 2 | 69,227 | 166 | 82 | 6,014 | 7,457 | 0 | 4 | 33,227 | 28 | 116,205 | 59.57% |
| 3 | 40,182 | 19 | 541 | 4,518 | 3,435 | 0 | 6 | 42,492 | 399 | 91,592 | **43.87%** |
| 4 | 109,175 | 913 | 101 | 69 | 19,535 | 1 | 2 | 9,891 | 0 | 139,687 | 78.16% |
| 5 | 46,375 | 874 | 29 | 20,459 | 9,736 | 0 | 0 | 20,343 | 31 | 97,847 | **47.40%** |
| 6 | 148,368 | 164 | 783 | 12,236 | 462 | 1 | 4 | 2,084 | 623 | 164,725 | 90.07% |
| 7 | 61,036 | 654 | 423 | 159 | 23,545 | 2 | 18 | 3,636 | 8 | 89,481 | 68.21% |
| 8 | 257,362 | 128 | 302 | 2,283 | 32,874 | 0 | 1 | 0 | 45 | 292,995 | 87.84% |
| 9 | 3,323 | 10 | 1,134 | 500 | 855 | 1 | 6 | 3,105 | 26 | 8,960 | 37.09% |

(**Bold** = malicious under the locked config, `{0,3,5}`.)

### 1c — compositionally extreme vs. ordinary silos, per seed

At seed 42, the extreme/ordinary split was a clean bimodal gap (extreme 0.08–12.25% Benign, ordinary 81.5–98.0% Benign — 69pp gap between groups), and the malicious triple {0,3,5} plus canary silo 8 **were** the extreme group. **Neither new seed reproduces this clean bimodality** — composition is graded/continuous at both. Using a matched group size (lowest-4 vs. highest-6, mirroring seed 42's split) as the primary prediction:

| seed | extreme group (lowest Benign%) | ordinary group (highest Benign%) | where {0,3,5} land |
|---|---|---|---|
| 42 (reference) | {5, 3, 0, 8} | {9, 4, 2, 1, 7, 6} | all three malicious silos ARE the extreme group (minus canary 8) |
| 1337 | {4, 7, 2, 5} | {6, 1, 3, 9, 8, 0} | **only silo 5** is extreme; silo 3 is ordinary; **silo 0 is the single most compositionally ordinary silo in the entire fleet (95.44% Benign)** |
| 2024 | {9, 3, 5, 2} | {0, 1, 4, 6, 7, 8} | silos 3, 5 are extreme; **silo 0 is ordinary** (64.22%, 5th of 10, right at the boundary) |

### 1d — pre-registered predictions (CLEAN runs), stated before Step 2

> At seed 1337, under a CLEAN run with no attack whatsoever, the agent is predicted to flag the compositionally extreme silos **[2, 4, 5, 7]** at a high rate, and the ordinary silos **[0, 1, 3, 6, 8, 9]** at a low rate.
>
> At seed 2024, under a CLEAN run with no attack whatsoever, the agent is predicted to flag the compositionally extreme silos **[2, 3, 5, 9]** at a high rate, and the ordinary silos **[0, 1, 4, 6, 7, 8]** at a low rate.

**Direct, falsifiable consequence:** unlike seed 42 (all three malicious silos uniformly extreme, uniformly flagged ~0.95–1.00 clean), the confound hypothesis predicts a **non-uniform** clean-run flag-rate profile across {0,3,5} at both new seeds — silo 0 low, silo 5 high, silo 3 mixed — because composition no longer aligns with {0,3,5} as a set the way it did at seed 42. Candidate canaries (extreme, never malicious): {2,4,7} at 1337, {2,9} at 2024.

### 1d-extended — pre-registered predictions (ATTACK runs), stated before Step 2

Seed 1337 provides a **dissociation design** seed 42 could not: at seed 42, "malicious" and "compositionally extreme" were the same set (perfectly confounded — the only separating evidence was one canary, silo 8, one seed). At seed 1337, **silo 0 is malicious AND the single most Benign-heavy (compositionally ordinary) silo in the fleet** — the two hypotheses now make *opposite* predictions about it, because the Dirichlet draw at 1337 happens to pull the two variables apart where seed 42's draw could not.

**Under ATTACK (sudden {0,3,5}, f=3), at each seed:**

**IF THE AGENT TRACKS ATTACK BEHAVIOR:**
- malicious silos {0,3,5} show clear **lift** over their own clean-run baselines at that seed, **including silo 0 at seed 1337 despite it being compositionally ordinary**
- compositionally extreme, never-malicious silos ({2,4,7} at 1337, {2,9} at 2024) show **little or no lift**

**IF THE AGENT TRACKS COMPOSITION (Phase 3's confound hypothesis):**
- silo 0 at seed 1337 shows **little or no lift** and a **low absolute flag rate in both clean and attack runs**, despite genuinely being poisoned
- extreme never-malicious silos are flagged **high in both clean and attack runs**, with little lift either way
- flag rate tracks Benign-share ranking more closely than it tracks malicious status

**Mixed/partial outcomes are possible and will be reported as mixed, not forced into either box.** The framing will not be chosen after seeing the numbers — this section is written before any Step 2 run.

### 1e — attack-config sensibility check: does {0,3,5} clear Phase 0's own disqualification bar?

Phase 0 rejected the retired {0,1,9} rule at seed 42 for achieving only 13.98% overall coverage, "unevenly distributed... three of six families under 5%." Recomputed the f=3 frontier (all C(10,3)=120 triples, per-family coverage at flip_fraction=1.0, `targeted_to_benign` strategy) for both new seeds using the composition tables above (method verified to reproduce `frontier_f3_a0.5_s42.csv`'s `(0,3,5)` row exactly before trusting it on new seeds). New artifacts: `results/inspection/frontier_{f3,f2}_a0.5_{s1337,s2024}.csv`.

| seed | {0,3,5} rank / 120 | weakest-family coverage ×0.4 (locked flip_fraction) | seed's best possible f=3 triple | best triple's ceiling ×0.4 |
|---|---|---|---|---|
| 42 (reference) | 1/120 (IS the seed's own worst-case optimum) | DoS 15.44% | — (same) | — |
| 1337 | 8/120 | **Bot 7.91%** | (1,3,5): ceiling 25.77% | 10.31% |
| 2024 | 33/120 | **BruteForce 4.85%** | (2,6,7): ceiling 26.26% | 10.51% |

Full per-family coverage ×0.4:
- Seed 1337 {0,3,5}: Bot 7.91%, BruteForce 18.06%, DDoS 18.70%, DoS 10.12%, PortScan 11.88%, WebAttack 24.32% — **zero families under 5%.**
- Seed 2024 {0,3,5}: Bot 13.07%, BruteForce 4.85%, DDoS 25.57%, DoS 11.57%, PortScan 23.37%, WebAttack 12.74% — **one family at 4.85%**, essentially at the boundary (vs. the retired rule's three families under 5%).

**CONFIRMED before running: {0,3,5} clears Phase 0's own disqualification bar at both seeds.** It is a genuinely weaker attack than at seed 42 (roughly half-strength on the binding family in both cases), and this must be stated with every number reported below — but it is not a toy attack, and per PATH 1 below, using the seed-42-locked triple as-is (rather than re-optimizing per seed) is the more informative choice for the confound question this session exists to answer.

### Standalone finding — attack-config portability across seeds (methodological, not a caveat on the confound work)

**A silo-index-pinned attack configuration does not preserve its "worst-case/full-knowledge adversary" framing across seeds.** {0,3,5} is rank 1/120 (the true worst-case optimum) at seed 42, rank 8/120 at seed 1337, rank 33/120 at seed 2024 — and its three members scatter across the compositional spectrum at the new seeds rather than clustering at the extreme end the way they do (by construction) at seed 42. This is a general observation about how attacker-selection rules are specified in Dirichlet-partitioned FL research (an index-based selection frozen at one seed silently changes character under a different partition draw), separate from and orthogonal to the compositional-confound question this session is testing. It does not block the runs below.

### 01_Planning decision — PATH 1, confirmed

Proceed with {0,3,5} as locked, unchanged, at both new seeds. Justification (01_Planning, verbatim reasoning): at seed 42 the confound test was structurally weak — malicious silos and compositionally extreme silos were the same set, so "agent tracks attack" and "agent tracks composition" made identical predictions, and only one canary (silo 8) separated them. Seed 1337's Dirichlet draw accidentally produces a dissociation design (malicious silo 0 is simultaneously the most compositionally ordinary silo in the fleet) that seed 42 could not produce because its variables were perfectly confounded. Re-optimizing the attack triple per seed would destroy this dissociation and produce a weaker test, not a stronger one.

---

## Step 2 — training runs

**Config reuse note:** the two CLEAN baselines (`results/federated/fedavg_a0.5_{s1337,s2024}/`) already existed on disk — pre-existing Contribution A runs at the correct locked config (alpha=0.5, 20 rounds, local-epochs=3, mu=0.0, fraction=1.0), test set already spent on them. Re-running them would duplicate GPU time and re-touch already-spent artifacts for no benefit. Reused via `scripts/replay_client_stats.py` (Phase 1's own zero-retraining checkpoint-replay precedent) to produce `client_stats.jsonl` — no retraining, no config edits, no test-set touch. Only the 2 poisoned runs were newly trained.

**Operational note:** the seed-1337 poisoned run was launched with `cd federated; flwr run . local-simulation ...`, which resolves `configs/model.yaml`'s relative `output.results_dir: results/` against `federated/` as cwd rather than the project root — output landed in `federated/results/{federated,attacks}/...` instead of the top-level `results/`. Caught immediately after the run completed (before any analysis), verified both directories were complete and untouched, moved to the correct top-level location (`results/federated/fedavg_a0.5_s1337_poisoned_f3_sudden_silos0-3-5/`, `results/attacks/a0.5_s1337_f3_sudden_silos0-3-5/`) — nothing else under `federated/results/` (pre-existing, unrelated leftovers) was touched. The seed-2024 run was launched correctly from the project root (`flwr run federated local-simulation ...`, matching the invocation Phase 0–4 actually used) to avoid repeating this.

### Seed 1337 — CLEAN (replayed) vs. poisoned (sudden {0,3,5}, f=3, flip_fraction=0.4), live run

Hard test-guard fired correctly (deliberate stop, not a crash): `RuntimeError: HARD STOP: configs/attack.yaml has attack.enabled: true...` after writing validation-only artifacts, before any `test_global.parquet` touch. `client_stats.jsonl` confirmed written live (200 rows = 20 rounds × 10 silos), `flip_log.csv` confirmed written (attack manifest: `results/attacks/a0.5_s1337_f3_sudden_silos0-3-5/attack_config.json`).

| statistic | clean_s1337 | poisoned {0,3,5} | Δ |
|---|---|---|---|
| mean (20 rounds) | 0.9227 | 0.9132 | **−0.0095** |
| median | 0.9755 | 0.9807 | **+0.0052** |
| final-5 mean (rounds 16–20) | 0.9352 | 0.9626 | **+0.0274** |
| max (best-by-validation) | 0.9871 | 0.9888 | **+0.0017** |

**Reported plainly, not smoothed over: at seed 1337, this attack does not reproduce seed 42's macro-F1 gate.** Three of four statistics (median, final-5-mean, max) move in the *positive* direction under attack, and mean's negative move (−0.0095) is an order of magnitude smaller than seed 42's (−0.0299). This is consistent with, and further corroborates, Step 1e's finding that {0,3,5} is a substantially weaker attack at this seed (roughly half-strength on the binding family, and malicious silo 0 — 95.44% Benign — has very little non-Benign material to flip in the first place). This does not change the Phase 0 gate verdict (a seed-42-only finding, out of scope here) but must travel with every number from this run.

**Operational note, repeats for this run too:** the seed-2024 poisoned run was launched from the project root via `flwr run federated local-simulation ...` (the same invocation style the pre-existing `federated/results/federated/fedavg_a0.5_s42/`-style leftover artifacts imply prior sessions also hit) and *also* wrote to `federated/results/...` rather than the top-level `results/`. Root cause, confirmed by reading the code: `federated/xfed_federated/task.py`'s `load_yaml()` resolves config paths against a hardcoded `_PROJECT_ROOT` absolute-path constant (so `configs/*.yaml` always load correctly regardless of invocation cwd), but `server_app.py`'s output-directory computation (`Path(model_cfg["output"]["results_dir"]) / "federated" / tag`) uses `configs/model.yaml`'s relative `"results/"` value directly — and Flower's simulation backend evidently executes the server thread with cwd pinned to the app source directory (`federated/`) regardless of where `flwr run` itself was invoked from. This is an existing, structural inconsistency in the harness, not specific to how I invoked it — the stray `federated/results/federated/{fedavg_a0.5_s42, fedprox_mu*_a0.5_s42, ...}/` directories already on disk before this session are the same artifact from earlier sessions, left unmerged. Same fix applied: verified both new directories complete, moved to the correct top-level location, nothing else under `federated/results/` touched. Flagging this as a real (small) bug in `server_app.py` worth a one-line fix (`_PROJECT_ROOT / model_cfg["output"]["results_dir"]`) — not fixed here since it's outside this session's scope and every artifact this session produced was verified complete and correctly relocated by hand.

### Seed 2024 — CLEAN (replayed) vs. poisoned (sudden {0,3,5}, f=3, flip_fraction=0.4), live run

Hard test-guard fired correctly, same pattern as seed 1337. `client_stats.jsonl` confirmed written live (200 rows), attack manifest confirmed correct (`malicious_silos: [0,3,5]`, `f:3`, `mode: sudden`, `flip_fraction: 0.4`).

| statistic | clean_s2024 | poisoned {0,3,5} | Δ |
|---|---|---|---|
| mean (20 rounds) | 0.8342 | 0.8282 | **−0.0060** |
| median | 0.8495 | 0.8496 | +0.0001 |
| final-5 mean (rounds 16–20) | 0.8568 | 0.8500 | **−0.0068** |
| max (best-by-validation) | 0.8644 | 0.8503 | **−0.0141** |

**Reported plainly:** at seed 2024, three of four statistics move negative (mean, final-5-mean, max), matching seed 42's *direction* but at roughly 1/5–1/10 the *magnitude* (seed 42: mean −0.0299, final-5-mean −0.0766, max +0.0004 vs. here mean −0.0060, final-5-mean −0.0068, max −0.0141). Median is flat (+0.0001). Again consistent with Step 1e's finding that {0,3,5} is a weaker, differently-shaped attack at this seed than at seed 42 (BruteForce-bound at 4.85% vs. DoS-bound at 15.44%). Notably, unlike seed 42 (where max was essentially untouched, the textbook signature of a level-shift attack that best-by-validation selection is blind to), max *does* move here (−0.0141) — a different qualitative behavior from seed 42's own result, on top of being smaller in magnitude.

### Cross-seed macro-F1 summary (context only, out of this session's scope — reported because all four statistics must always be reported, not to re-litigate the Phase 0 gate)

| seed | mean Δ | median Δ | final-5-mean Δ | max Δ |
|---|---|---|---|---|
| 42 (Phase 0, reference) | −0.0299 | −0.0048 | −0.0766 | +0.0004 |
| 1337 | −0.0095 | **+0.0052** | **+0.0274** | **+0.0017** |
| 2024 | −0.0060 | +0.0001 | −0.0068 | −0.0141 |

The macro-F1 gate direction/magnitude does **not** reproduce cleanly across seeds under the locked, unmodified {0,3,5} config — expected, given Step 1e already established {0,3,5} is a materially weaker (and differently family-bound) attack at both new seeds. This is not a finding this session is scoped to verdict on (Phase 0's gate is a seed-42-only claim); it is reported here only because the ground truth requires all four statistics for every run, and because it is useful context for interpreting Step 3's detection numbers (a weaker underlying attack is exactly what would make detection harder to see, independent of the confound question).

---

## Step 3 — agent replay (current-round mode only)

4 cells (`{1337, 2024} × {clean, sudden}`), 20 rounds each, retrospective replay against Step 2's `client_stats.jsonl` (`scripts/phase_multiseed_agent_replay.py`, mirrors `phase3_verification_gate.py`'s `decide_round()` call exactly — current-round path only, rolling-history explicitly not invoked). 80 live Ollama calls, 58.9 min. Raw data: `results/inspection/multiseed_agent_gate_raw.json`.

### Per-silo flag rate, all 10 silos, clean vs. sudden side by side

**Seed 1337:**

| silo | clean | sudden | lift | role |
|---|---|---|---|---|
| 0 | 0.05 | 0.10 | +0.05 | **MALICIOUS**, compositionally ordinary (95.44% Benign — the dissociation silo) |
| 1 | 1.00 | 1.00 | +0.00 | ordinary (58.30% Benign) — **unpredicted high** |
| 2 | 1.00 | 0.90 | −0.10 | extreme, never malicious (canary) |
| 3 | 0.00 | 0.40 | **+0.40** | **MALICIOUS**, ordinary (62.37% Benign) |
| 4 | 1.00 | 1.00 | +0.00 | extreme, never malicious (canary) |
| 5 | 0.00 | 0.95 | **+0.95** | **MALICIOUS**, extreme (46.09% Benign) |
| 6 | 0.00 | 0.00 | +0.00 | ordinary |
| 7 | 1.00 | 1.00 | +0.00 | extreme, never malicious (canary) |
| 8 | 0.00 | 0.05 | +0.05 | ordinary |
| 9 | 0.10 | 0.15 | +0.05 | ordinary |

**Seed 2024:**

| silo | clean | sudden | lift | role |
|---|---|---|---|---|
| 0 | 0.00 | 0.35 | **+0.35** | **MALICIOUS**, compositionally ordinary (64.22% Benign — the dissociation silo) |
| 1 | 1.00 | 0.20 | −0.80 | ordinary (97.25% Benign) — **unpredicted high in clean** |
| 2 | 0.05 | 0.15 | +0.10 | extreme, never malicious (canary) — did NOT saturate |
| 3 | 1.00 | 0.95 | −0.05 | **MALICIOUS**, extreme (43.87% Benign) — saturated in both, zero lift |
| 4 | 0.00 | 0.15 | +0.15 | ordinary |
| 5 | 0.25 | 1.00 | **+0.75** | **MALICIOUS**, extreme (47.40% Benign) |
| 6 | 0.50 | 0.15 | −0.35 | ordinary |
| 7 | 0.65 | 0.30 | −0.35 | ordinary — **unpredicted mid/high in clean** |
| 8 | 0.95 | 1.00 | +0.05 | ordinary — **unpredicted high in clean** |
| 9 | 1.00 | 1.00 | +0.00 | extreme, never malicious (canary) — saturated in both |

### Lift over clean baseline, malicious silos

| seed | silo 0 | silo 3 | silo 5 |
|---|---|---|---|
| 42 (reference) | +0.05 | +0.00 | +0.00 |
| 1337 | +0.05 | **+0.40** | **+0.95** |
| 2024 | **+0.35** | −0.05 | **+0.75** |

### Canary test — extreme, never-malicious silos, clean-run flag rate

| seed | canary silos | clean flag rate |
|---|---|---|
| 42 (reference) | {8} | 0.95 |
| 1337 | {2, 4, 7} | 1.00, 1.00, 1.00 — **all saturated, reproduces seed 42's canary signature cleanly** |
| 2024 | {2, 9} | 0.05, 1.00 — **split: silo 9 reproduces the canary signature, silo 2 does not** |

### Prediction (1d) vs. outcome — CLEAN-run compositional grouping

**Seed 1337: PARTIALLY HELD.** 8/10 silos matched their predicted direction (extreme→high or ordinary→low). Two contradictions: silo 5 (predicted high as "extreme," actually 0.00 in clean) and silo 1 (predicted low as "ordinary," actually 1.00 in clean, unpredicted false-high).

**Seed 2024: LARGELY FAILED.** Only ~5/10 silos matched their predicted direction — close to chance. Extreme group split 2-high/2-low; ordinary group split 3-low/3-high (silos 1, 7, 8 all flagged mid-to-high in clean despite being in the "ordinary" group). **The simple lowest-Benign%-quartile grouping that predicted seed 42's clean-run result well has essentially no predictive power at seed 2024.** This does not mean the compositional-extremity confound is false — Step 1c already flagged that seed 2024 (like 1337) lacks seed 42's clean bimodal gap, so a single-axis (aggregate Benign%) grouping was always going to be a cruder operationalization at these seeds than it was at 42. It does mean this specific, simple test of the confound (percentile-based grouping predicting clean-run flag rate) does not reproduce cleanly away from seed 42.

### Prediction (1d-extended) vs. outcome — ATTACK-run dissociation test

**The dissociation silo (0) gives OPPOSITE answers at the two seeds:**
- **Seed 1337:** silo 0 clean=0.05, sudden=0.10, lift=+0.05 — **matches the COMPOSITION-TRACKING prediction** (low absolute rate in both conditions, minimal lift) almost exactly.
- **Seed 2024:** silo 0 clean=0.00, sudden=0.35, lift=+0.35 — **matches the ATTACK-TRACKING prediction** better (real, substantial lift).

**This dissociation is not as clean as the pre-registration hoped, for a mechanical reason not fully anticipated in Step 1:** the `targeted_to_benign` attack strategy only flips non-Benign rows, so a compositionally-ordinary (Benign-heavy) malicious silo is *mechanically* a weaker attack target regardless of whether the agent tracks composition or attack behavior — composition and attack material availability are coupled through the attack mechanism itself, not just through the (separately established, Step 1e) attacker-selection portability finding. Silo 0's non-Benign row count: **19,223 (4.56% of the silo) at seed 1337** vs. **48,296 (35.78% of the silo) at seed 2024** — an 8× difference in absolute poisonable material. Seed 1337's near-zero lift for silo 0 is therefore consistent with *either* "the agent doesn't track attack behavior in compositionally-ordinary silos" (the confound hypothesis) *or* "there was very little attack signal in silo 0's training data at this seed to detect in the first place" (a mechanical floor, independent of the agent). **This session cannot cleanly separate these two explanations with the data collected, and does not claim to.**

**Malicious silos 3 and 5, across both seeds, mostly show real, substantial lift — this is the headline departure from seed 42:**
- Silo 5 shows the largest lift of any malicious silo at **both** new seeds (+0.95 at 1337, +0.75 at 2024) — clearly attack-responsive, not flat.
- Silo 3 shows real lift at 1337 (+0.40) but is saturated-flat at 2024 (clean=1.00, sudden=0.95, lift −0.05) — the confound signature, at that seed.

**A structural observation this session's design surfaces, not anticipated in the Step 1 pre-registration:** at seed 42, all three malicious silos were *already saturated* (~0.95–1.00) in the clean run — the compositional-extremity confound put them at ceiling before any attack was applied, mechanically leaving **no room** for flag rate to rise further under attack, regardless of whether the agent would have responded to genuine attack behavior. Seeds 1337 and 2024, where the malicious silos mostly do *not* start saturated in clean (silo 3 and 5 at 1337: 0.00; silo 0 at both seeds: 0.00–0.05; silo 5 at 2024: 0.25), remove that ceiling effect — and once removed, **the agent visibly does respond to genuine attack behavior in several cases** (silo 5 at both seeds; silo 3 at 1337). This suggests seed 42's "zero lift" result may have been partly an artifact of a ceiling effect specific to that seed's unusually clean compositional bimodality, not solely evidence that the agent is purely composition-tracking and blind to attack behavior. This is stated as an observation this session's data supports, not a re-verdict on Phase 3's finding (which remains correct as a description of what happened at seed 42).

**Canaries reproduce the original finding, partially:** all 3 of seed 1337's canaries {2,4,7} saturate at ~1.00 in both clean and attack, zero lift — a clean reproduction of Phase 3's canary signature. At seed 2024, only 1 of 2 canaries {9} reproduces it; the other {2} does not (low flag rate in both conditions — a true negative, not a confound).

### Per-seed verdict — held / partially held / failed, stated plainly

**Seed 1337:** the clean-run compositional grouping partially held (8/10). The canary pattern (chronic false-positive at ceiling, attack-independent) reproduced cleanly for all 3 canaries. Two of three malicious silos (3, 5) showed large, genuine attack-responsive lift not seen at seed 42. Silo 0's near-zero lift is consistent with the confound but is separately explained (not resolved) by a near-total absence of attack material in that silo at this seed — see the Ceiling Effect section below and the dissociation-silo caveat above; this specific non-resolution is deliberate, not left incomplete by oversight.

**Seed 2024:** the clean-run compositional grouping essentially failed (~5/10, chance-level). The canary pattern reproduced for only one of two canaries. Two of three malicious silos (0, 5) showed substantial attack-responsive lift; only silo 3 showed the flat, confound-consistent pattern.

**Both effects are present, at both seeds, and the section below explains why seed 42 alone could not show this.** A real compositional confound saturates some silos' flag rates independent of any attack — the canary pattern reproduces, in some form, at every seed tested (42, 1337, 2024). Real attack-responsive detection is *also* present, and becomes visible precisely at the seeds where malicious silos are not already saturated in the clean run. Seed 42's apparent "malicious silos show ~zero lift, full stop" was not a clean absence of attack-responsive detection — it was structurally incapable of showing one, for the reason laid out next.

---

## THE CEILING EFFECT — headline finding of this session

**At seed 42, all three malicious silos {0,3,5} sat at 0.95–1.00 flag rate in the CLEAN run** (Phase 3's own published table: silo 0 = 0.95, silo 3 = 1.00, silo 5 = 1.00). Lift is defined as `sudden_flag_rate − clean_flag_rate`, and flag rate is bounded above by 1.00. **When a silo's clean-run baseline already sits at or near 1.00, lift is mathematically capped near zero regardless of what the agent does under attack** — there is no room left for the flag rate to rise. Phase 3's headline "malicious silos show ~zero lift" (+0.05/+0.00/+0.00) was therefore **partly measuring a ceiling, not an absence of attack-responsive detection.** This was not visible at the time because seed 42 offered no comparison point where the ceiling was absent — the compositional-extremity confound and the malicious-silo identity were the same set at that seed (this session's own Step 1 pre-registration flagged this as the reason seed 42's confound test was structurally weak, before knowing it would also explain the lift result).

Seeds 1337 and 2024 mostly lack this ceiling — none of their malicious silos start anywhere near 1.00 in the clean run (1337: silo 0 = 0.05, silo 3 = 0.00, silo 5 = 0.00; 2024: silo 0 = 0.00, silo 3 = 1.00 *(still saturated — and still shows ~zero lift, consistent with the ceiling explanation)*, silo 5 = 0.25). **Once the ceiling is removed, the agent visibly does respond to attack:**

| silo | seed | clean baseline | sudden | lift |
|---|---|---|---|---|
| 5 | 1337 | 0.00 | 0.95 | **+0.95** |
| 5 | 2024 | 0.25 | 1.00 | **+0.75** |
| 3 | 1337 | 0.00 | 0.40 | **+0.40** |

**Seed 42 was structurally incapable of producing numbers like these** — not because the agent doesn't respond to attack behavior there, but because its malicious silos had nowhere left to go. The one case that *stays* flat at a new seed (silo 3 at 2024, clean=1.00, lift=−0.05) is exactly the case where the ceiling is still present — internally consistent with this explanation, not an exception to it.

**This bounds Phase 3's finding; it does not retract it.** Phase 3's description of seed 42 — malicious silos flagged at ~1.00, ~indistinguishable from a never-malicious canary, ~zero measured lift — is **still an accurate description of what happened at seed 42.** What changes is the *interpretation* carried forward from it: "ByzAgent detects compositional extremity, not attacks" (the strong reading) does not hold once a seed without the ceiling shows real, substantial, attack-responsive lift. The corrected claim, to replace that strong wording everywhere it appears in this project's write-ups going forward:

> Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack — the canary pattern (never-malicious, compositionally atypical silos chronically flagged regardless of attack condition) reproduces across seeds. Real attack-responsive detection is also present, and becomes visible at seeds where silos are not already saturated. Seed 42's apparent null on malicious-silo lift was partly a ceiling artifact of that seed's unusually clean bimodal composition (malicious silos and compositionally-extreme silos were the same set, all pinned near 1.00 before any attack), not solely evidence the agent ignores attack behavior.

A forward-reference has been added to `PHASE3_SUMMARY.md` pointing here, so the two documents cannot be read in isolation and reach the superseded conclusion.

---

## Step 4 — explanation-fidelity audit at new seeds + owed Phase 4 trend-error hand-check

### 4a — reasoning-vs-outcome audit, Step 3's current-round decisions, new seeds

Same methodology as `scripts/phase3_analysis.py` (citation frequency via keyword match, citation accuracy via within-round percentile loose/strict scoring, Spearman decision-severity correlation), reused not rewritten (`scripts/phase_multiseed_fidelity_audit.py`), pooled over the 4 new-seed cells (800 decisions, 1,577 extracted citations). Full data: `results/inspection/multiseed_fidelity_audit.json`.

> **Headline of this section, stated up front, not left in a table: the agent's most-cited geometry stat has no consistent relationship to its own decisions.** `update_norm` is cited in the 2nd-most explanations of any stat (~59% average across the 4 new-seed cells) — but its correlation with the agent's actual decisions **collapses from a weak-but-real +0.419 at seed 42 to essentially zero and flips sign (ρ=−0.076, p=0.033, negligible effect size)** at the new seeds, and its citation accuracy is **the single worst of all five stats — wrong more often than right (42.6% strict error, above the 50%-random line once ambiguous cases are excluded)**. At seed 42, citing `update_norm` heavily was defensible-if-imperfect (it was at least weakly predictive). At the new seeds, the agent cites it almost as often while it carries essentially no real signal and is actively misdescribed nearly half the time it's cited with a directional word. This sharpens Phase 3's "over-cited relative to its predictive power and its own accuracy" finding considerably — it is no longer just over-cited, it is over-cited for a stat that stopped meaning anything.

**Citation frequency (% of 200 explanations per condition citing each stat):**

| stat | seed42 clean (published) | seed42 f3 (published) | s1337 clean | s1337 sudden | s2024 clean | s2024 sudden |
|---|---|---|---|---|---|---|
| update_norm | 93% | 73% | 59.0% | 53.5% | 71.5% | 51.5% |
| cosine_to_global | 99.5% | 86% | 94.0% | 93.5% | 55.0% | 73.5% |
| cosine_to_peer_mean | 7% | 11.5% | 8.5% | 26.0% | 24.5% | 24.5% |
| train_loss | 7.5% | 39% | 21.5% | 19.0% | 19.5% | 52.5% |
| val_accuracy | 43.5% | 65% | 32.0% | 43.5% | 62.5% | 60.5% |

**Citation accuracy, pooled over the 4 new-seed cells vs. seed 42's published pooled numbers:**

| stat | seed42 strict error (published) | new-seed strict error (n=1577 pooled) |
|---|---|---|
| overall | **11.7%** | **22.5%** (loose 24.7%, ambiguous 14.5%) |
| update_norm | 25.1% (worst at seed 42) | **42.6%** (worse than a coin flip — still worst) |
| cosine_to_global | 4.4% (best at seed 42) | **18.2%** (markedly worse) |
| cosine_to_peer_mean | n too small to trust | 41.5% (n=52, more usable now, still high) |
| train_loss | 3.8% | 4.7% (reproduces — still very low) |
| val_accuracy | 8.6% | 10.3% (reproduces — still low) |

**Citation accuracy regresses substantially away from seed 42** — overall strict error roughly doubles (11.7% → 22.5%), driven mainly by `cosine_to_global` (4.4% → 18.2%) and `update_norm` (25.1% → 42.6%, i.e. citing update_norm's direction is now wrong more often than right). `train_loss` and `val_accuracy` stay reliably low-error at both — this part reproduces.

**Decision-stat correlation (Spearman ρ, pooled):**

| stat | seed42 published | new-seed pooled (n=800) |
|---|---|---|
| cosine_to_global | −0.808 | −0.474 |
| train_loss | +0.793 | +0.456 |
| val_accuracy | −0.745 | **−0.577 (now the single strongest correlate)** |
| update_norm | +0.419 | **−0.076 (collapses to ~zero, sign-flips)** |
| cosine_to_peer_mean | +0.298 | −0.118 (weakens, sign-flips) |

All correlations weaken at the new seeds, and the ranking reshuffles (val_accuracy overtakes cosine_to_global as strongest), but the "big three" (cosine_to_global, train_loss, val_accuracy) stay clearly the strongest correlates at both.

**Does the "right answer, wrong stated reason" pattern reproduce? Yes — and the update_norm side of it sharpens.** `train_loss` remains relatively under-cited given its correlation strength (3rd-strongest correlate, ρ=+0.456, but only 4th-most-cited at ~28% average, below cosine_to_peer_mean's citation floor at seed 42's own ordering) — reproduces the seed-42 pattern. `update_norm` remains over-cited relative to both its predictive power and its own accuracy — and this sharpens at the new seeds: it is cited in **2nd place** (~59% average) despite its correlation with actual decisions **collapsing to essentially zero and flipping sign** (ρ=−0.076, non-significant effect size) and its citation accuracy being **the single worst of all five stats, wrong more often than right** (42.6% strict error, above the 50%-is-random line for a binary high/low call once ambiguous cases are excluded). At seed 42, update_norm was at least weakly genuinely correlated (ρ=+0.419); at the new seeds it is cited almost as heavily while carrying essentially no real signal at all.

### 4b — owed hand-check of Phase 4's trend-error heuristic

Phase 4 reported 45.00% of rolling-history trend claims ("increasing"/"decreasing"/"stable") factually wrong against the actual sequence, computed by a simple endpoint-comparison heuristic (5%-relative tolerance for "stable"), explicitly flagged as unvalidated. Reproduced the exact scoreable population from `results/inspection/phase4_gate_raw_a0.5_s42.json` (920 scoreable claims, 414 wrong, error rate 45.00% — **exact match to Phase 4's published figure**, confirming no drift in the extraction logic). Drew a random sample of 35 (seed=7, no new LLM calls) with full explanation text and sequence, and hand-checked each one independently — is the heuristic's own verdict (correct/wrong) itself correct, wrong, or genuinely ambiguous? Sample: `results/inspection/multiseed_citation_accuracy_sample.json`'s sibling data is inline in the analysis script output (35-row sample not separately persisted — reproducible via `scripts/sample_trend_claims.py`'s fixed seed=7).

**Result: 32/35 (91.4%) of the heuristic's verdicts are confidently validated by hand; 3/35 (8.6%) are genuinely ambiguous boundary cases (all on the "wrong" side, sequences whose net first-to-last change sits right at or just past the 5% tolerance line); 0/35 are confident disagreements with the heuristic.**

Breaking this down by the heuristic's own verdict:
- **21/21 "correct" verdicts in the sample were confirmed correct by hand** — when the heuristic says the model's trend claim matches the sequence, that holds up 100% of the time in this sample.
- **11/14 "wrong" verdicts were confirmed as genuine, unambiguous errors** — several are not close calls at all: e.g. a monotonically decreasing update_norm sequence (5.997→3.802, a 36.6% drop) described by the model as "increasing"; a monotonically decreasing cosine_to_global sequence (0.6225→0.5350) described as "stable"; a steeply falling train_loss sequence (0.0794→0.0194, a 75.6% drop over 2 steps) described as "stable." These are flat misreadings of a clearly monotonic sequence, not artifacts of the scoring rule.
- **3/14 "wrong" verdicts are genuinely ambiguous** — small, noisy, near-tolerance-boundary sequences (e.g. a train_loss sequence jittering in a tight ~0.0045–0.0052 band, called "stable" by the model, scored "decreasing" by the heuristic because the net change is 8.2% relative — barely over the 5% cutoff) where a lenient human reading would not confidently call the model wrong.

**Heuristic precision and adjusted error-rate range:** the heuristic's automated 45.00% is **confirmed fundamentally sound** — it is not an artifact of a broken extractor (0/35 confident disagreements), and its "correct" verdicts are fully reliable (100% in-sample). Its "wrong" verdicts carry a genuine ambiguous-boundary fraction of ~21.4% (3/14). Extrapolating that fraction to the full 414-claim "wrong" population and removing the ambiguous share from both numerator and denominator (same discipline as Phase 3's own strict/loose citation-accuracy split): **adjusted error rate range ≈ 35–45%**, point estimate **≈ 39%** if ambiguous cases are excluded entirely rather than counted as errors. Either the raw 45.00% (upper, conservative-strict bound) or the ~39% adjusted point estimate is defensible to report; both are far above what "the agent's trend claims are reliable" would look like, and neither changes Phase 4's Step 3 verdict (the canary-conjunction failure, which does not depend on this number at all).

Hand-check artifacts: `results/inspection/multiseed_trend_claim_sample.json` (the sampled 35 rows, reproducible via `scripts/sample_trend_claims.py --seed 7`), `results/inspection/multiseed_trend_claim_handcheck_verdicts.json` (per-row manual verdict + reasoning, same discipline as Phase 3's `phase3_citation_accuracy_sample.json`).

---

## What remains n=1, deliberately — scoping decisions, not oversights

Per the ground truth's explicit instruction, only three findings were multi-seeded in this session (the compositional-confound/canary finding, the explanation-fidelity audit, and the owed Phase 4 trend-error hand-check). Everything else in Phases 0–4 remains at seed 42 only. Restated here so their absence reads as a scoping decision, not a gap:

- **Phase 2's Krum/Multi-Krum/trimmed-mean baselines** — not re-run at new seeds. Phase 2's failure finding (all three strategies chronically exclude/trim the same large, Benign-heavy silos regardless of attack condition — confirmed via clean-control runs with zero malicious silos present) is a **mechanistic** finding, not a statistical one: the same two silos are excluded in literally every round of every condition tested, attack or not. More seeds cannot change a mechanistic explanation that already holds with zero variance across every condition Phase 2 ran.
- **Phase 4's full 6-cell matrix (3 conditions × 2 agent modes)** — not re-run at new seeds. Rolling-history's negative verdict rests on the canary conjunction (the never-malicious canary's lift equals or exceeds the real attackers' own lift), which is a qualitative failure mode, not a number sensitive to decimal-level precision. This session's Step 3/4a work only ever exercised current-round mode at the new seeds, exactly as scoped.
- **Gradual-mode attack runs** — not run at new seeds. Explicitly out of scope; the compositional-confound/canary question this session answers is orthogonal to sudden-vs-gradual onset.
- **Phase 5's eval harness (ByzAgent vs. Krum/trimmed-mean benchmarking)** — moot as originally scoped. Both baselines are already documented as failing for reasons (compositional-extremity confound, size/Benign-skew geometry sensitivity) a benchmarking harness would not add evidence to.
- **Phase 6 dashboard** — deferred until the React port exists, unrelated to this session's scope.

## Output-path bug fix — `federated/results/` vs. top-level `results/`

Diagnosed during Step 2 (both poisoned runs initially landed in the wrong directory): Flower's simulation backend pins the server thread's `cwd` to the app source directory (`federated/`) regardless of where `flwr run` itself is invoked from. `federated/xfed_federated/task.py`'s `load_yaml()` already avoided this trap for config loading via a hardcoded `_PROJECT_ROOT` absolute-path constant, but `server_app.py`'s output-directory computation used `configs/model.yaml`'s relative `"results/"` value directly (`Path(model_cfg["output"]["results_dir"]) / "federated" / tag`), which silently resolved against `federated/` instead of the project root — every affected run's artifacts landed in `federated/results/federated/{tag}/` instead of `results/federated/{tag}/`.

**Fixed** ([federated/xfed_federated/server_app.py:609](../../federated/xfed_federated/server_app.py)): imported `_PROJECT_ROOT` from `task.py` and changed the computation to `_PROJECT_ROOT / model_cfg["output"]["results_dir"] / "federated" / tag` — absolute, immune to whatever `cwd` Flower's backend pins.

**Verified** without a live training run (no GPU/Ollama time spent): reproduced the exact failure condition (`cwd` = `federated/`) and confirmed the old computation resolved to `federated\results\federated\...` while the fixed computation resolves to the correct top-level `C:\Pilli\Capstone\xfed-ids\results\federated\...`; confirmed `server_app.py` still imports cleanly (syntax + import check) after the change.

**Pre-existing orphaned directories from earlier sessions, investigated read-only, resolved as follows (01_Planning decision):**

| orphan (`federated/results/federated/...`) | top-level counterpart | resolution |
|---|---|---|
| `fedavg_a0.5_s42` | yes, byte-for-byte MD5-identical (`config.json`, `final_metrics.json`, `model_best.pt` all match) | **confirmed exact duplicate, left in place, not deleted** — safe for anyone who encounters it to ignore |
| `fedprox_mu0.0005_a0.1_s42` | yes, byte-for-byte MD5-identical | **confirmed exact duplicate, left in place, not deleted** — safe to ignore |
| `fedprox_mu0.0005_a0.5_s42` | yes, byte-for-byte MD5-identical | **confirmed exact duplicate, left in place, not deleted** — safe to ignore |
| `fedprox_mu0.01_a0.5_s42` | none (the only copy) | **RELOCATED** to `results/federated/fedprox_mu0.01_a0.5_s42/` — see below |

**Relocation, done this session:** moved `federated/results/federated/fedprox_mu0.01_a0.5_s42/` (5 files: `config.json`, `final_metrics.json`, `model_best.pt`, `model_last.pt`, `round_history.json`) to `results/federated/fedprox_mu0.01_a0.5_s42/` — the conventional top-level location every other run lives at. Reconfirmed immediately beforehand that no top-level directory of that name existed (not just trusting the earlier read-only check); verified by MD5 that all 5 files are byte-identical pre- and post-move. **Why:** this is the sole copy of the artifact behind a claim already cited in the closed Contribution A record — `results/chat03_claims.md:106` ("μ=0.01 ... 0.7119 ... Bot AND WebAttack both to 0.0000") and paraphrased in `docs/contribution_a_results.md:131` ("collapsed macro-F1 to 0.71 with Bot/WebAttack recall at 0.0") — sitting in a directory where 3 of 4 contents genuinely are stale duplicates a future cleanup would reasonably delete. Moving it changes no claim, no number, no prose in either document; `docs/contribution_a_results.md` was **not edited** (Contribution A is closed, and the existing paraphrased citation is sufficient — the relocation only makes the underlying artifact findable at the path the project's own convention expects, not a footnote added to a closed record). The claim itself (mu=0.01 collapse to macro-F1 0.7119, Bot and WebAttack recall both 0.0) is unaffected and remains **uncited-by-path in `contribution_a_results.md` by design** — this was a deliberate decision, not an oversight left for a future session to "fix."

This session's own two runs (seeds 1337/2024 poisoned) hit the same output-path bug before the fix landed — both were caught immediately, verified complete, and moved to the correct location by hand (see Step 2 above); nothing from this session was left behind in `federated/results/`.

## Artifact index (this session)

- `federated/xfed_federated/server_app.py` — output-path bug fix (`_PROJECT_ROOT`-anchored `out_dir`), see "Output-path bug fix" above
- `results/inspection/silo_family_composition_a0.5_{s1337,s2024}.csv` — per-silo family composition, train-only (val_mask-excluded), reproduced via the method verified against seed 42's on-disk file
- `results/inspection/frontier_{f3,f2}_a0.5_{s1337,s2024}.csv` — full C(10,3)/C(10,2) coverage frontier
- `results/federated/fedavg_a0.5_{s1337,s2024}/client_stats.jsonl` — replayed (zero retraining) from pre-existing Contribution A checkpoints
- `results/federated/fedavg_a0.5_{s1337,s2024}_poisoned_f3_sudden_silos0-3-5/` — new live poisoned runs, full artifacts
- `results/attacks/a0.5_{s1337,s2024}_f3_sudden_silos0-3-5/` — attack manifests + flip logs
- `results/inspection/attack_gate_a0.5_{s1337,s2024}_f3_sudden_silos0-3-5.log` — training run console logs
- `scripts/phase_multiseed_agent_replay.py` — Step 3, 4-cell current-round replay (mirrors `phase3_verification_gate.py`)
- `results/inspection/multiseed_agent_gate_raw.json` — Step 3 raw replay data (80 rounds)
- `results/federated/{tag}/agent_decisions_multiseed.jsonl` — Step 3 per-run decision logs
- `scripts/phase_multiseed_fidelity_audit.py` — Step 4a (mirrors `phase3_analysis.py`, citation frequency/accuracy/correlation)
- `results/inspection/multiseed_fidelity_audit.json` — Step 4a full output
- `results/inspection/multiseed_citation_accuracy_sample.json` — Step 4a citation-accuracy hand-check sample (30 rows)
- `scripts/sample_trend_claims.py` — Step 4b, reproduces Phase 4's scoreable trend-claim population and samples for hand-check
- `results/inspection/multiseed_trend_claim_sample.json` — Step 4b sampled 35 rows
- `results/inspection/multiseed_trend_claim_handcheck_verdicts.json` — Step 4b manual verdicts



