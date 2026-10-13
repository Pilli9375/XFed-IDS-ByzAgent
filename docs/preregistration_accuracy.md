# Preregistration: federated optimizer comparison

**Date:** 2026-10-12
**Branch:** `accuracy-prereg`
**Rule this relies on:** the test-set rule as amended on 2026-10-12 (commit
`b2b9bee`, "record decision to re-run the test set once for a preregistered
config"): the test set is evaluated one further time, once, for a single
federated configuration selected beforehand on validation data only. No other
configuration is ever scored on the test set.

This file is committed in two parts. **Part 1** (selection rule, candidates,
baseline) is committed before any candidate run exists. **Part 2** (the chosen
configuration, its sealed checkpoints and the test protocol) is filled in
after the validation grid and committed on its own before the single test
evaluation. If the outcome is "no improvement", Part 2 records that and the
test set is not touched.

---

## Part 1 — written before any candidate run

### Question

Under non-IID data (Dirichlet α), does a different federated optimizer
improve the global model's macro-F1 over FedAvg, chiefly at α=0.1 where FedAvg
is weakest?

### Candidates (exact parameters in `configs/federated_methods.yaml`)

| Name | Server aggregation (Flower 1.33) | Server parameters | Client μ |
|---|---|---|---|
| fedavg (baseline) | FedAvg | — | 0 |
| fedprox_mu0.001 | FedAvg | — | 0.001 |
| fedprox_mu0.01 | FedAvg | — | 0.01 |
| fedprox_mu0.1 | FedAvg | — | 0.1 |
| fedavgm_m0.5 | FedAvgM | server lr 1.0, momentum 0.5 | 0 |
| fedavgm_m0.9 | FedAvgM | server lr 1.0, momentum 0.9 | 0 |
| fedadam_lr0.01 | FedAdam | η=0.01, β1=0.9, β2=0.99, τ=0.001 | 0 |
| fedadam_lr0.001 | FedAdam | η=0.001, β1=0.9, β2=0.99, τ=0.001 | 0 |
| fedyogi_lr0.01 | FedYogi | η=0.01, β1=0.9, β2=0.99, τ=0.001 | 0 |
| fedyogi_lr0.001 | FedYogi | η=0.001, β1=0.9, β2=0.99, τ=0.001 | 0 |

**Budget cut (decided before any candidate run).** One timed round
(`results/federated_methods/budget_estimate.json`) gave 62.2 s/round plus
53.6 s startup, i.e. 21.6 min per 20-round run; the full plan (58 runs) is
20.9 h against a 12 h budget. Only these four candidates are run:
**fedavgm_m0.5, fedavgm_m0.9, fedadam_lr0.01, fedyogi_lr0.01** (24 runs, plus
3 α=5.0 runs for the chosen config and 1 FedAvg regression run: 28 runs,
~10.1 h). Cut, with reasons in `configs/federated_methods.yaml` under `cut:`:
fedprox_mu0.001 (existing μ=0.0005 runs gave +0.0007 at α=0.1), fedprox_mu0.01
(its earlier α=0.5 run scored 0.7114 vs FedAvg 0.9760, so it would fail the
guard), fedprox_mu0.1 (stronger than μ=0.01), fedadam_lr0.001 and
fedyogi_lr0.001 (a step of ~η per weight per round cannot move far in 20
rounds). The cut candidates are not part of the selection; nothing is claimed
about them.

**Revision of the cut, 2026-10-12, committed before any candidate run had
finished.** The one timed round above was inflated (first-round warm-up, plus
an unrelated `conda env create` running at the same time). The full 20-round
FedAvg regression run then measured 34.7 s/round, 12.7 min per run end to end
(`results/federated_methods/run_log.jsonl`). Revised estimate: 58 runs × 12.7
min = 12.3 h, still over 12 h, by about one candidate. Revised cut: only
**fedprox_mu0.1** is dropped (strongest proximal pull; μ=0.01 already
collapsed α=0.5 once). The candidate set for selection is therefore
**fedavgm_m0.5, fedavgm_m0.9, fedadam_lr0.01, fedyogi_lr0.01,
fedprox_mu0.001, fedprox_mu0.01, fedadam_lr0.001, fedyogi_lr0.001**
(48 runs + 3 α=5.0 runs ≈ 11.0 h with the two runs already done). The first
four run first, the other four after; the order does not depend on any result.

**Budget guard, added 2026-10-12 ~17:00, timing-only.** Candidate runs have
taken 10.2–18.6 min (mean above the 12.7 min of the regression run), which
projects past 12 h. Rule, applied mechanically by
`tools/run_federated_methods.py::budget_allows` before each candidate starts:
if the elapsed wall time of all logged runs plus the mean candidate-run time ×
(runs still needed for this and every later candidate + the 3 α=5.0 runs)
exceeds 12 h, that candidate and every later one in grid order are dropped,
whole. It reads only wall times from `run_log.jsonl`, never a score; a
candidate that has started is never dropped. Each check is logged to
`results/federated_methods/budget_guard.jsonl`. When this was added, five
runs of fedavgm_m0.5 had finished (one of their scores, α=0.1 seed 42, had
been seen); none of the four candidates the guard can drop had started.

**Regression check result.** The FedAvg re-run on the new path
(`results/federated_methods/regression/fedavg_a0.1_s42/round_history.json`) is
identical to the published curve at all 21 rounds (max absolute difference
0.0). The published FedAvg runs are therefore a like-for-like baseline.

β1, β2 and τ are Flower 1.33's defaults for FedAdam/FedYogi, written out
explicitly. SCAFFOLD is not run; the reason is recorded under `skipped:` in
the YAML (no Flower strategy, needs persistent client state, and its
correction is derived for local SGD while the locked local optimizer is
AdamW).

Prior exposure, disclosed: FedProx μ=0.01 was run once before, at α=0.5
seed 42 (`results/federated/fedprox_mu0.01_a0.5_s42/`), and that run was
scored on the test set under the old harness. It collapsed (val macro-F1
0.7114). It is cut below, so this earlier test touch cannot overlap with the
preregistered evaluation.

Environment, disclosed: Flower builds an isolated runtime env per run with
`uv`. The published runs' envs used **torch 2.13.0+cpu**, so all federated
training (published and new) runs on CPU, not the RTX 4050. Unpinned, `uv`
would now resolve newer packages, so `federated/pyproject.toml` pins the
versions read from the August envs (torch 2.13.0, numpy 2.4.6, pandas 3.0.5,
pyarrow 25.0.1, scikit-learn 1.9.0, pyyaml 6.0.3). Check: the one-round
timing run on the new path reproduced the published FedAvg α=0.1 seed 42
validation scores at rounds 0 and 1 (0.1303, 0.2452). A full 20-round FedAvg
re-run on the new path (`results/federated_methods/regression/`) is compared
against the published curve before the baseline numbers below are relied on.

### Fixed settings (all candidates)

α ∈ {0.1, 0.5}; seeds 42, 1337, 2024; the same partitions, SHA256-checked
against `data/processed/partitions/manifest.json` before every run; locked
model and class weights (`configs/model.yaml`); 3 local epochs; 20 rounds;
all 10 silos train every round; best-by-validation round selection over
rounds 0–20. Harness: `federated/xfed_federated/`, launched as
`flwr run federated local-simulation` by `tools/run_federated_methods.py`.

Method runs are validation-only by construction: the server path has no test
evaluation, client-side evaluation (which in the legacy path scores each
silo's own test rows) is switched off, and `client_app.evaluate` refuses
method runs.

### Baseline (existing published FedAvg runs, validation only)

From `results/federated/fedavg_a{α}_s{seed}/round_history.json`, best round
by `val_macro_f1_headline`:

| α | seed 42 | seed 1337 | seed 2024 | mean |
|---|---|---|---|---|
| 0.1 | 0.5440 (r20) | 0.4551 (r16) | 0.5694 (r16) | 0.5228 |
| 0.5 | 0.9760 (r18) | 0.9871 (r11) | 0.8644 (r17) | 0.9425 |

(Four decimals for display; the selection script uses the unrounded values.)

### Selection rule

Metric: `val_macro_f1_headline` — unweighted mean of per-class F1 over the 7
headline families (Benign, Bot, BruteForce, DDoS, DoS, PortScan, WebAttack),
computed by `compute_metrics` in `federated/xfed_federated/_vendored/metrics.py`
on the centralized validation split. Infiltration and Heartbleed are excluded.
Per run, the best round by this metric is taken; per (candidate, α), the mean
over the 3 seeds.

1. **Guard.** A candidate is eligible only if its α=0.5 mean is at least
   FedAvg's α=0.5 mean − 0.01.
2. **Pick.** Among eligible candidates, choose the one with the highest α=0.1
   mean.
3. **Threshold.** If the chosen candidate's α=0.1 mean is less than FedAvg's
   α=0.1 mean + 0.02, the outcome is **"no improvement"**: stop, report, and
   do not evaluate anything on the test set.
4. **Ties** (equal α=0.1 means to the 4th decimal): the higher α=0.5 mean
   wins; if still tied, the candidate listed earlier in the table above.

Interpretation recorded before results: the guard is applied as an
eligibility filter before picking (constrained maximum), not as a pass/fail
check on the unconstrained maximum only.

### Stop and flag

- Any candidate run at α=0.1 whose best validation macro-F1 exceeds 0.990
  (the centralized MLP's macro-F1).
- Any partition manifest mismatch.
- Anything that would score a second configuration on the test set.

### If a configuration is chosen

It is then trained (validation-only, same harness) at α=5.0 for seeds 42,
1337 and 2024, so it can be tested at all three published α values. Its
best-by-validation checkpoints at α ∈ {0.1, 0.5, 5.0} × 3 seeds are sealed by
SHA256 in Part 2, and only those 9 checkpoints are evaluated on the test set,
once.

---

## Part 2 — sealed configuration

**Date sealed:** 2026-10-12 (written after the validation grid, committed on
its own before any test evaluation).

### Validation outcome (rule applied by `tools/select_federated_method.py`)

Candidates actually compared: fedavgm_m0.5, fedavgm_m0.9, fedadam_lr0.01,
fedyogi_lr0.01. The timing-only budget guard dropped fedprox_mu0.001,
fedprox_mu0.01, fedadam_lr0.001 and fedyogi_lr0.001 before any of them
started (7.40 h elapsed, 17.8 min mean run, 15.4 h projected;
`results/federated_methods/budget_guard.jsonl`).

| Candidate | α=0.1 val mean | α=0.5 val mean | Guard (≥ 0.9325) |
|---|---|---|---|
| FedAvg (baseline) | 0.5228 | 0.9425 | — |
| fedavgm_m0.5 | 0.5386 | 0.9502 | pass |
| **fedavgm_m0.9** | **0.6068** | **0.9861** | pass |
| fedadam_lr0.01 | 0.4583 | 0.8482 | fail |
| fedyogi_lr0.01 | 0.4627 | 0.9004 | fail |

Threshold at α=0.1: 0.5228 + 0.02 = 0.5428. **Outcome: selected,
fedavgm_m0.9** (`results/federated_methods/selection.json`). No α=0.1 run
exceeded 0.990.

Recorded before the test, so it cannot be explained away afterwards:
fedavgm_m0.9's validation curves oscillate strongly at α=0.1, and its
best-by-validation rounds are often spikes. Its final-round α=0.1 val mean
is 0.5248 against FedAvg's 0.5062. Taking the maximum over 21 noisy rounds
inflates validation more for a jumpier method, so some of the +0.084
validation gain at α=0.1 is expected to shrink on test.

### Chosen configuration (exact YAML, `configs/federated_methods.yaml`)

```yaml
fedavgm_m0.9:
  server: fedavgm
  server_params: {server_learning_rate: 1.0, server_momentum: 0.9}
  client: {mu: 0.0}
```

Flower 1.33 `FedAvgM` (Hsu et al., 2019): weighted FedAvg mean, then
`v ← 0.9·v + (w_old − w_avg)`, `w_new = w_old − 1.0·v`. Everything else is
the locked configuration: `configs/model.yaml`, 3 local epochs, 20 rounds,
10 silos all training each round, best-by-validation round selection.

### What is tested

α ∈ {0.1, 0.5, 5.0} × seeds {42, 1337, 2024}: exactly these 9 checkpoints,
each the best-by-validation round of its run, and nothing else. Final-round
checkpoints are not scored on test.

| α | seed | round | val macro-F1 | file | file SHA256 | tensor-content SHA256 |
|---|---|---|---|---|---|---|
| 0.1 | 42 | 16 | 0.6568 | `results/federated_methods/runs/fedavgm_m0.9_a0.1_s42/model_best.pt` | `ad4c65a92b5a393f9731ffbcacd60e221e4046354932fd4557c0bf48288377f9` | `5a605bcee19e79f42e5df88deeb4955c2cd0827512d3d97a949c0903751a516a` |
| 0.1 | 1337 | 15 | 0.5263 | `results/federated_methods/runs/fedavgm_m0.9_a0.1_s1337/model_best.pt` | `6bc2fde99eb11a689443623268518696378356c06a37f0f8dea5cb6d4b495cf9` | `59c4839490d28579526b23287f7f2c7dc21559a2441c08178a2249d1b2416870` |
| 0.1 | 2024 | 13 | 0.6372 | `results/federated_methods/runs/fedavgm_m0.9_a0.1_s2024/model_best.pt` | `2d216e92624a86db1c9850b5aa8a2b5a6a513b92e22bdcf2db49270e7eafc576` | `461cf024f22a20cdf87ec8d2480007dfd98184aa8785346fe37b93c511cd845c` |
| 0.5 | 42 | 17 | 0.9870 | `results/federated_methods/runs/fedavgm_m0.9_a0.5_s42/model_best.pt` | `51f7b7bfaf93e2c4802799a975fb24ed2c12f75f7d6cd1b220ce01820f31b0a0` | `b1c8aaf95b540d7d3a625354e49fcb6964a2c4efdcf35e93091403d1272ab4ee` |
| 0.5 | 1337 | 17 | 0.9896 | `results/federated_methods/runs/fedavgm_m0.9_a0.5_s1337/model_best.pt` | `64f06026a385151bdfefc9109d15407027b7918373c2cfed4fdc52a2dbe540fc` | `d879dca0e9ba4feb338251a1b748ad882e9931502b67bbb8b0321c78251234ac` |
| 0.5 | 2024 | 11 | 0.9816 | `results/federated_methods/runs/fedavgm_m0.9_a0.5_s2024/model_best.pt` | `2a9f22639b996c4760663ae097a11827ce3eff4a2abaffe982fabaa46f156d01` | `fae1e98202733b8ea01c5ebb657a070fd6e0f56a5837e338cff31f3fa31f8875` |
| 5.0 | 42 | 17 | 0.9913 | `results/federated_methods/chosen/fedavgm_m0.9_a5.0_s42/model_best.pt` | `55d227dbbb4885468326957df878063a7074601d0574c09d06c739befff0f8e5` | `0cb72b9e1e29507fa515a0d70dd02aeb8498c6edf3abe955c6c698bb31f7ae00` |
| 5.0 | 1337 | 18 | 0.9910 | `results/federated_methods/chosen/fedavgm_m0.9_a5.0_s1337/model_best.pt` | `91acdeb5f0ad7f0810496104395c2121ab8d31ba1145e85099815fc5e613ed16` | `23b5e8031cc8cd219d2851fca371fc34db80952400aa15d5ca842072bb007935` |
| 5.0 | 2024 | 17 | 0.9932 | `results/federated_methods/chosen/fedavgm_m0.9_a5.0_s2024/model_best.pt` | `61678029c5b1f11e26298d875f42a87422ff2125eacc0cbcd554510d6eae0524` | `b57f5a28fd12e9faadae64b36737bba9b6c74b88e153434e01b1072f14569115` |

Same list, machine-readable: `results/federated_methods/sealed_checkpoints.json`.
`.pt` files are git-ignored; the hashes above are the record.

### Metric

Headline: macro-F1 over the 7 headline families (Benign, Bot, BruteForce,
DDoS, DoS, PortScan, WebAttack) on `data/processed/test_global.parquet`
(478,376 rows), computed by `compute_metrics` in
`federated/xfed_federated/_vendored/metrics.py` (scikit-learn
`precision_recall_fscore_support`, `zero_division=0`), preprocessing by the
same vendored `load_centralized` the harness uses. Reported per α as mean ±
std over the 3 seeds, std = population (ddof=0), the convention of the
published table. Per-class F1 is reported for all 9 classes; Infiltration and
Heartbleed appear per class only, never in the headline.

### Procedure

`tools/federated_method_test_once.py`, run once. Before touching test it
checks this file is committed and clean and contains every hash above,
re-hashes every checkpoint, and recomputes each checkpoint's validation
macro-F1 (it must equal the logged value exactly). It then writes a LOCK file
and scores the 9 checkpoints. The result JSON records this file's git commit.
Nothing is tuned after the result; the script is never re-run.

**This configuration will be reported whatever its test result.**
