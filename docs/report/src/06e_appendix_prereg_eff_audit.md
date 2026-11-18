## Preregistered Accuracy Study {#sec:app-prereg}

This section gives the full preregistered optimizer comparison: the question, the candidates, the selection rule, the budget decisions, the validation results, the sealed checkpoints and the single test result. It supports Sections 2.2.6 and 4.1. The protocol, `docs/preregistration_accuracy.md`, was committed in two parts: first the candidates and the rule for choosing among them, before any candidate had run; then the winner and the hashes of its checkpoints, before the test set was touched.

### Question and candidates

The question was: under non-IID data, does a different federated optimizer raise the global model's macro-F1 over FedAvg, mainly at α=0.1, where FedAvg is weakest? @tab:prereg-grid lists the ten configurations in the protocol and what happened to each. FedAdam and FedYogi use Flower's default values β1=0.9, β2=0.99 and τ=0.001, written out explicitly. SCAFFOLD was not run: Flower offers no implementation of it, it requires each client to keep state from round to round, and its correction term assumes plain SGD on the clients, whereas ours use AdamW.
<!-- src: docs/preregistration_accuracy.md -->

Table: Preregistered candidate grid and the status of each candidate {#tab:prereg-grid}
| Candidate | Server rule | Parameters | Client μ | Status |
|---|---|---|:-:|---|
| fedavg | FedAvg | none | 0 | Baseline (published runs) |
| fedprox_mu0.001 | FedAvg | none | 0.001 | Dropped by the budget guard |
| fedprox_mu0.01 | FedAvg | none | 0.01 | Dropped by the budget guard |
| fedprox_mu0.1 | FedAvg | none | 0.1 | Cut by the revised budget estimate |
| fedavgm_m0.5 | FedAvgM | server lr 1.0, momentum 0.5 | 0 | Run |
| fedavgm_m0.9 | FedAvgM | server lr 1.0, momentum 0.9 | 0 | Run; selected |
| fedadam_lr0.01 | FedAdam | η=0.01 | 0 | Run |
| fedadam_lr0.001 | FedAdam | η=0.001 | 0 | Dropped by the budget guard |
| fedyogi_lr0.01 | FedYogi | η=0.01 | 0 | Run |
| fedyogi_lr0.001 | FedYogi | η=0.001 | 0 | Dropped by the budget guard |
<!-- src: docs/preregistration_accuracy.md -->

**Fixed settings.** All candidates used α ∈ {0.1, 0.5}, seeds 42, 1337 and 2024, the same partitions checked against the SHA256 manifest before every run, the locked model and class weights, 3 local epochs, 20 rounds, all 10 silos training every round, and best-by-validation round selection over rounds 0 to 20. The method runs are validation-only by construction: the server path has no test evaluation, client-side evaluation is switched off, and the client refuses to evaluate a method run.
<!-- src: docs/preregistration_accuracy.md -->

### The selection rule

The metric was computed with scikit-learn's precision, recall and F1 routine, counting a class with no predictions as zero, and standard deviations over seeds are population values, as in the published table. Candidates were scored by the macro-F1 of their best validated round on the seven headline classes, with the three seeds averaged for each candidate and α. The rule, applied by `tools/select_federated_method.py`:

1. **Guard.** To be eligible, a candidate's mean at α=0.5 may fall at most 0.01 short of FedAvg's, so it must reach 0.9325.
2. **Pick.** Among eligible candidates, choose the highest α=0.1 mean.
3. **Threshold.** If that mean is below FedAvg's α=0.1 mean plus 0.02 (0.5428), stop, report "no improvement" and do not touch the test set.
4. **Ties.** Equal α=0.1 means to the fourth decimal go to the higher α=0.5 mean.
<!-- src: docs/preregistration_accuracy.md -->

The protocol also listed stop-and-flag conditions: any α=0.1 run with validation macro-F1 above the centralized model's 0.990, any partition manifest mismatch, and anything that would score a second configuration on the test set. None was triggered.
<!-- src: docs/preregistration_accuracy.md -->

### Budget decisions and the four-of-nine disclosure

The budget was 12 hours of compute. @tab:prereg-budget records each budget decision in order. The guard reads only wall times, never a score. At the moment the guard was introduced, fedavgm_m0.5 had completed five runs and one of its scores, for α=0.1 and seed 42, had been looked at. The four candidates that the guard was able to remove had not begun. Of the 9 candidates originally requested, 4 were finally run.
<!-- src: docs/preregistration_accuracy.md; docs/contribution_a_results.md -->

Table: Budget decisions in the preregistered study {#tab:prereg-budget size=9.5}
| Step | Measurement | Decision |
|---|---|---|
| Initial estimate, before any candidate | One timed round: 62.2 s per round plus 53.6 s start-up, 21.6 min per run; 20.9 h for 58 runs | Keep four candidates only |
| Revised estimate, before any candidate finished | Full FedAvg regression run: 34.7 s per round, 12.7 min per run; 12.3 h for 58 runs | Drop only fedprox_mu0.1 |
| Timing-only guard, added during the runs | Candidate runs took 10.2 to 18.6 min; at 7.40 h elapsed, mean run 17.8 min, projected 15.4 h | Drop the four later candidates |
<!-- src: docs/preregistration_accuracy.md -->

**Regression check.** FedAvg was run again through the new code. For α=0.1 and seed 42 its validation curve matched the published one in all 21 rounds, and the biggest difference was 0.0. Even the one-round timing run had already reproduced the published validation scores of rounds 0 and 1 (0.1303 and 0.2452). The Flower runtime for these runs uses the CPU build of PyTorch, with package versions pinned to those of the published runs.
<!-- src: docs/preregistration_accuracy.md -->

**Earlier exposure, disclosed.** FedProx with μ=0.01 had been run once before, at α=0.5 and seed 42, and that run had been scored on the test set under the old harness; it collapsed, with validation macro-F1 0.7114. Because that candidate was among those dropped, its earlier test score cannot overlap with the preregistered evaluation. The published FedAvg runs are therefore a like-for-like baseline.
<!-- src: docs/preregistration_accuracy.md -->

### Validation results and selection

@tab:prereg-val gives the validation means of every candidate that ran. FedAvgM with momentum 0.9 was selected, clearing the α=0.1 threshold of 0.5428. FedAdam and FedYogi failed the α=0.5 guard.
<!-- src: docs/preregistration_accuracy.md -->

Table: Validation selection: mean best-by-validation macro-F1 per candidate {#tab:prereg-val}
| Candidate | α=0.1 mean | α=0.5 mean | Guard (at least 0.9325) |
|---|:-:|:-:|:-:|
| FedAvg (published baseline) | 0.5228 | 0.9425 | n/a |
| FedAvgM, momentum 0.5 | 0.5386 | 0.9502 | Pass |
| FedAvgM, momentum 0.9 | 0.6068 | 0.9861 | Pass; selected |
| FedAdam, η=0.01 | 0.4583 | 0.8482 | Fail |
| FedYogi, η=0.01 | 0.4627 | 0.9004 | Fail |
<!-- src: docs/preregistration_accuracy.md -->

Before the test, the protocol recorded a warning that could not be explained away afterwards. At α=0.1 FedAvgM's validation curves swing up and down sharply, so the round it picks is often a peak; at the last round its mean is 0.5248, not far from FedAvg's 0.5062. Picking the highest of 21 noisy rounds flatters an unsteady method more, so we expected some of its validation advantage to disappear on the test set.
<!-- src: docs/preregistration_accuracy.md -->

### Sealing and the single test evaluation

FedAvgM was also trained at α=5.0, after which the SHA256 hashes of all nine selected checkpoints were committed (@tab:sealed). The test script then checked that the protocol file was committed and contained every hash, re-hashed every checkpoint, recomputed each validation score (each had to equal the logged value exactly), created a lock file and only then evaluated the nine checkpoints, a single time, on the 478,376 test rows. The script is never run again, and nothing was tuned after the result.
<!-- src: docs/preregistration_accuracy.md -->

Table: Sealed checkpoints of FedAvgM (momentum 0.9): best round, validation macro-F1 and file SHA256 prefix {#tab:sealed}
| α | Seed | Round | Validation | SHA256 (first 12 hex digits) |
|:-:|:-:|:-:|:-:|---|
| 0.1 | 42 | 16 | 0.6568 | `ad4c65a92b5a` |
| 0.1 | 1337 | 15 | 0.5263 | `6bc2fde99eb1` |
| 0.1 | 2024 | 13 | 0.6372 | `2d216e92624a` |
| 0.5 | 42 | 17 | 0.9870 | `51f7b7bfaf93` |
| 0.5 | 1337 | 17 | 0.9896 | `64f06026a385` |
| 0.5 | 2024 | 11 | 0.9816 | `2a9f22639b99` |
| 5.0 | 42 | 17 | 0.9913 | `55d227dbbb48` |
| 5.0 | 1337 | 18 | 0.9910 | `91acdeb5f0ad` |
| 5.0 | 2024 | 17 | 0.9932 | `61678029c5b1` |
<!-- src: docs/preregistration_accuracy.md -->

@tab:prereg-test gives the single test result per seed, against the published FedAvg runs. @tab:prereg-class gives per-class F1 for the chosen configuration.

Table: The single preregistered test evaluation: macro-F1 over 7 classes, FedAvg (published) against FedAvgM {#tab:prereg-test size=9.5}
| α | FedAvg | FedAvgM, momentum 0.9 | Seed 42 | Seed 1337 | Seed 2024 |
|:-:|:-:|:-:|:-:|:-:|:-:|
| 0.1 | 0.516 ± 0.048 | 0.5930 ± 0.0632 | 0.5426 → 0.6558 | 0.4481 → 0.5065 | 0.5572 → 0.6167 |
| 0.5 | 0.941 ± 0.057 | 0.9852 ± 0.0005 | 0.9753 → 0.9846 | 0.9866 → 0.9856 | 0.8605 → 0.9856 |
| 5.0 | 0.990 ± 0.001 | 0.9911 ± 0.0005 | 0.9900 → 0.9918 | 0.9905 → 0.9906 | 0.9889 → 0.9910 |
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

Table: Test F1 for each class under FedAvgM with momentum 0.9, averaged across 3 seeds {#tab:prereg-class}
| Class | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Benign | 0.9417 | 0.9988 | 0.9993 |
| Bot | 0.3949 | 0.9646 | 0.9705 |
| BruteForce | 0.5708 | 0.9947 | 0.9964 |
| DDoS | 0.9897 | 0.9999 | 0.9999 |
| DoS | 0.6487 | 0.9946 | 0.9979 |
| PortScan | 0.2964 | 0.9967 | 0.9977 |
| WebAttack | 0.3088 | 0.9475 | 0.9762 |
| Heartbleed (per class only) | 0.0000 | 0.6000 | 0.9333 |
| Infiltration (per class only) | 0.0000 | 0.4843 | 0.6239 |
<!-- src: docs/contribution_a_results.md -->

### Reading and limits

At α=0.5 the change is stability: the mean rose from 0.941 to 0.985 and the seed spread shrank from 0.057 to 0.0005. The change comes mainly from seed 2024, where FedAvg had done poorly (0.8605, now 0.9856); seed 1337 changed by −0.001. At α=0.1 each seed improves, by +0.113, +0.058 and +0.060, yet in some seeds entire families are still close to zero; for five families (Bot, BruteForce, DoS, PortScan and WebAttack) the standard deviation of per-class F1 across seeds lies between 0.31 and 0.46. As the warning recorded before the test predicted, the gain on validation (+0.084) exceeded the gain on test (+0.077). At α=5.0 the seeds move by between +0.0001 and +0.0021, no more than the centralized model varies across its own seeds.
<!-- src: docs/contribution_a_results.md -->

The limits are stated with the result. Three seeds give no significance test. Only 4 of the 9 requested candidates were compared, so this is "the best of these four", not a tuned optimum: only two momentum values, 0.5 and 0.9, were tried, and the server learning rate was never changed from 1.0. These runs trained on the CPU through Flower's isolated runtime. Finally, both checks were carried out on FedAvg; nobody has yet tested what server momentum does to explanation agreement.
<!-- src: docs/contribution_a_results.md -->

## Efficiency, Full Results {#sec:app-efficiency}

This section gives the full serving, communication, compression and agent pre-screen measurements. It supports Sections 3.3 and 4.4. No test rows were read: the serving part uses the 143,513 validation rows, and the other parts use existing logs and validation-only runs. All parameters are in `configs/efficiency.yaml`.
<!-- src: docs/efficiency_results.md -->

### Serving speed and the int8 decision

The deployed checkpoint (`fedavg_a0.5_s42`, round 18, 19,849 parameters) was timed on the AMD Ryzen 7 7435HS CPU (8 cores, 16 threads) with 8 intra-op threads for both engines. The loader re-checks validation macro-F1 against the training log before timing, and never reads the test file. Three timing sessions were run. Each began with 500 single-row warm-up calls, followed by 5,000 single-row calls on validation rows, done 3 times, and finished with 5 complete passes over the validation set in batches of 1024 (140 full batches, 143,360 rows). Only the forward pass on already-scaled rows is timed. @tab:serving-latency and @tab:serving-size give the median of the three sessions with [minimum, maximum].
<!-- src: docs/efficiency_results.md -->

Table: Serving variants: validation macro-F1 and per-flow latency (median of 3 sessions [min, max]) {#tab:serving-latency size=9.5}
| Variant | Validation macro-F1 | p50 latency, batch 1 | p95 latency, batch 1 |
|---|:-:|:-:|:-:|
| PyTorch eager | 0.9760 | 186.5 µs [172.7, 193.2] | 322.1 µs [254.1, 369.4] |
| ONNX Runtime fp32 | 0.9760 | 45.7 µs [40.6, 46.9] | 83.6 µs [75.7, 88.5] |
| ONNX Runtime int8 (dynamic) | 0.8332 | 47.9 µs [45.3, 57.9] | 98.1 µs [65.1, 99.2] |
<!-- src: docs/efficiency_results.md -->

Table: Serving variants: throughput and size on disk {#tab:serving-size}
| Variant | Throughput at batch 1024 (rows/s) | Size (bytes) |
|---|:-:|:-:|
| PyTorch eager | 1,482,368 [1,411,067, 1,493,469] | 83,557 |
| ONNX Runtime fp32 | 1,071,700 [1,044,718, 1,124,598] | 80,704 |
| ONNX Runtime int8 (dynamic) | 1,256,956 [1,225,154, 1,260,406] | 25,957 |
<!-- src: docs/efficiency_results.md -->

ONNX Runtime fp32 gives identical predictions to PyTorch on all 143,513 validation rows. At batch 1 its p50 latency is about four times lower, while at batch 1024 it is slower than PyTorch on this CPU. It is the only variant whose validation macro-F1 equals PyTorch's to three decimals, so it became the backend's default engine. When it starts, the backend converts the checked model to ONNX in memory and compares the two engines on every validation row, stopping if any prediction differs; this check passed with 0 differences, and 50 of 50 sampled prediction requests returned the same family and confidence from both engines. A hot-swapped model always uses PyTorch.
<!-- src: docs/efficiency_results.md -->

Dynamic int8 quantization changed only 0.54% of predictions (agreement 0.994593), but those changes fell on small classes (@tab:int8), and validation macro-F1 fell by 0.1428, far beyond the 0.005 bound the session had set. Before quantizing, the model's Gemm operations had to be rewritten as a matrix multiply and an add, because the dynamic quantizer does not handle Gemm. That rewrite alone, still in fp32, matches PyTorch on 100% of validation rows, so the drop comes from quantization itself. int8 was dropped and is not offered.
<!-- src: docs/efficiency_results.md -->

Table: Validation F1 of the classes hurt by int8 quantization {#tab:int8}
| Class | PyTorch F1 | int8 F1 |
|---|:-:|:-:|
| Bot | 0.8815 | 0.4509 |
| WebAttack | 0.9671 | 0.4401 |
| Infiltration (per class only) | 0.8889 | 0.3333 |
<!-- src: docs/efficiency_results.md -->

### Communication per round

@tab:comm gives the bytes moved per federated round, computed from the parameter count and cross-checked against the harness logs. In 500 rounds logged by 25 runs with three local epochs, the recorded byte counts equal the calculated ones in both directions for FedAvg, FedAvgM and FedYogi. These counts exclude message metadata, configuration records and network framing; the simulation runs on one machine, so no real network is involved.
<!-- src: docs/efficiency_results.md -->

Table: Bytes moved per federated round (served model, 10 silos) {#tab:comm}
| Quantity | Bytes |
|---|:-:|
| Parameters | 19,849 |
| One model as fp32 tensors | 79,396 |
| Per round, server to silos | 793,960 |
| Per round, silos to server | 793,960 |
| Per round, both directions | 1,587,920 |
| One model as Flower array payloads | 80,676 |
| One model as a serialized Flower record | 81,180 |
| Per round as serialized records, both directions | 1,623,600 |
<!-- src: docs/efficiency_results.md -->

**The FedAdam float64 note.** FedAdam is the one exception. In Flower 1.33 it scales the update by a 64-bit scalar, which turns the broadcast weights into float64 from round 2 on. Its traffic is therefore 2,381,880 bytes per round, 1.5 times the 1,587,920 of every other method. Clients load the weights into a float32 model, so training is unaffected, and FedAdam was not selected; the note is for anyone who reuses it.
<!-- src: docs/efficiency_results.md; docs/contribution_a_results.md -->

### Wall time per round

@tab:walltime gives wall time per round from 25 existing method runs of 20 rounds each (FedAvgM, FedAdam and FedYogi at α ∈ {0.1, 0.5} with three seeds, plus the FedAvg regression run). Each round covers 10 simulated silos training for 3 local epochs on the CPU, plus the server's validation pass. All runs came from one laptop, one at a time.
<!-- src: docs/efficiency_results.md -->

Table: Wall time per round over 500 logged rounds {#tab:walltime}
| Quantity | Seconds |
|---|:-:|
| Median, all rounds | 51.4 |
| Range | 26.8 to 98.7 |
| Median, round 1 (includes start-up) | 84.2 |
| Median, rounds 2 to 20 | 51.3 |
| Median at α=0.1 / α=0.5 | 51.4 / 51.4 |
<!-- src: docs/efficiency_results.md -->

### Update compression

Two schemes compress the silo-to-server update, the difference between the trained local weights and the received global weights: fp16, a cast to 16-bit floats; and int8, a symmetric per-tensor 8-bit quantization with one float32 scale per tensor. The server adds the decompressed update back to the global model it sent and then runs the unchanged FedAvg aggregation; the broadcast stays fp32. Runs used FedAvg on the validation-only path at α=0.5 with three seeds and were compared with each seed's published FedAvg run. Before comparing, an uncompressed run through the modified code was checked against the published seed-42 run; all 21 rounds were identical, with the best score again 0.9760 at round 18. @tab:comp-bytes gives the bytes, which are exact.
<!-- src: docs/efficiency_results.md -->

Table: Uplink bytes per round under update compression {#tab:comp-bytes}
| Scheme | Uplink per round (bytes) | Saved against fp32 uplink | Saved against fp32 total |
|---|:-:|:-:|:-:|
| fp32 (reference) | 793,960 | n/a | n/a |
| fp16 | 396,980 | 50.0% | 25.0% |
| int8 per tensor | 198,890 | 74.9% | 37.5% |
<!-- src: docs/efficiency_results.md -->

@tab:comp-f1 reports the effect on validation macro-F1 with all four statistics, per seed and as mean ± standard deviation.

Table: Change in validation macro-F1 caused by compression at α=0.5, listed for seeds 42, 1337 and 2024 and then as mean ± sd {#tab:comp-f1 size=9}
| Scheme | Best-by-validation | Final round (20) | Final-5 mean | Mean of rounds 1–20 |
|---|:-:|:-:|:-:|:-:|
| fp16, per seed | +0.0036 / +0.0011 / −0.0068 | +0.0037 / −0.0016 / +0.0083 | −0.0465 / +0.0223 / −0.0037 | −0.0029 / +0.0168 / −0.0011 |
| fp16, mean ± sd | −0.0007 ± 0.0054 | +0.0035 ± 0.0050 | −0.0093 ± 0.0347 | +0.0043 ± 0.0109 |
| int8, per seed | +0.0020 / +0.0013 / −0.0066 | −0.0876 / +0.1173 / +0.0083 | −0.0169 / +0.0436 / −0.0023 | +0.0034 / +0.0068 / −0.0001 |
| int8, mean ± sd | −0.0011 ± 0.0048 | +0.0127 ± 0.1025 | +0.0081 ± 0.0316 | +0.0034 ± 0.0034 |
<!-- src: docs/efficiency_results.md -->

In absolute terms, best-by-validation macro-F1 moved from 0.9760 to 0.9796 (fp16) and 0.9780 (int8) at seed 42, from 0.9871 to 0.9883 and 0.9884 at seed 1337, and from 0.8644 to 0.8576 and 0.8578 at seed 2024. For both schemes, seed 2024 went past the 0.005 limit set for this session. We report it as it is and did not tune anything in response. The three-seed mean change is small and its sign is not consistent across seeds, while per-round validation F1 in these same runs swings far more than any of these changes: a 16-bit rounding of the update is enough to move training onto a different path. At three seeds, therefore, a compression effect of this size cannot be told apart from trajectory noise. The data show neither that compression is harmless within 0.005 nor that it is harmful. Compression also showed no measurable wall-time effect (rounds 2 to 20 median: 51.7 s uncompressed; 51.7, 27.8 and 50.1 s for fp16; 51.5, 50.9 and 50.7 s for int8), because the simulation moves bytes within one machine.
<!-- src: docs/efficiency_results.md -->

### A training-loss pre-screen in front of ByzAgent

ByzAgent makes one batched LLM call per round for all ten silos. The idea of a pre-screen is to pass to the agent only those silos whose training loss is above t times the median for that round, and to trust all the others without asking. It saves in two ways: whole calls avoided, in rounds where no silo passes the screen, and silo slots avoided within a call. The rule for choosing t was fixed before any loss ratio was looked at: take the largest t in the grid that keeps every flag the agent had placed on a poisoned silo, in both seed-42 sudden attack runs. That gave t=10; at t=15, retention falls to 0.95. @tab:prescreen replays the rule on the other seeds against the logged agent decisions.
<!-- src: docs/efficiency_results.md -->

Table: Pre-screen replay at t=10 (flag rates: replay / logged) {#tab:prescreen size=9.5}
| Run | Calls avoided | Silo slots avoided | Replay equals logged | Flag rate, poisoned | Flag rate, clean |
|---|:-:|:-:|:-:|:-:|:-:|
| Seed 1337, clean | 25.0% | 90.0% | 0.685 | n/a | 0.100 / 0.415 |
| Seed 1337, f=3 sudden | 95.0% | 99.5% | 0.450 | 0.017 / 0.483 | 0.000 / 0.586 |
| Seed 2024, clean | 0.0% | 90.0% | 0.560 | n/a | 0.100 / 0.540 |
| Seed 2024, f=3 sudden | 5.0% | 64.5% | 0.765 | 0.733 / 0.767 | 0.100 / 0.421 |
<!-- src: docs/efficiency_results.md -->

The seed-42 threshold does not transfer. At seed 1337 the pre-screen hides the attack: only 1 of the 60 poisoned silo-rounds is sent to the agent, and of the 29 flags the agent had placed on poisoned silos, just 1 remains; at seed 2024, by contrast, 44 of 46 such flags survive. Poisoned silo 0 is 95.4% Benign at that seed, so flipping the handful of attack rows it holds hardly changes its loss (ratio 0.45 to 0.99), while clean extreme silos reach 11.2 times (silo 2) and 24.6 times (silo 4) the median in the clean run. Flipping more can actually reduce the loss. In the seed-42 gradual run, once every eligible row is flipped, the attackers' ratios drop to 0.005, 0.096 and 0.126: labels that are all Benign agree with each other, so the model fits them easily. For scale, logged agent calls without a pre-screen took a median of 41.1 to 47.6 seconds each. The replay relies on a single run of an agent whose answers vary, and it supposes that the agent would answer the same way if shown fewer silos. The planned live run was not done, and the result is reported as a negative one with no redesign planned.
<!-- src: docs/efficiency_results.md -->

## Test-Set Exposure Audit {#sec:app-testaudit}

This section restates, in our own words, the audit of every way the 478,376-row test set was read, and the provenance of the choices made along the way. It supports Section 2.2.7. In these tables, "selected" means that some decision was based on the result of that read.
<!-- src: docs/test_set_exposure_audit.md -->

### Every read of the test set

@tab:exposure lists the nine kinds of read found by the audit on 2026-10-13.

Table: Every way the test set was read {#tab:exposure size=9.5}
| # | Read | Anything selected from it? | Note |
|:-:|---|---|---|
| 1 | Headline numbers: one test pass over the checkpoint each run had already picked on validation (FedAvg, FedProx, clean defence runs, exploratory runs, centralized and XGBoost) | No | The checkpoint was fixed on validation first |
| 2 | Centralized pilots: every arm scored on test (14 arms plus a smoke run) | Partly | Arms were ranked on validation, but three written rationales quote test scores (@tab:provenance) |
| 3 | Legacy client-side scoring: each silo scored on its own test share every round, in 35 runs | No | No analysis reads these rows |
| 4 | The round-20, unselected checkpoint scored once per run | No | Fed an earlier round-lottery figure, since replaced by a validation version |
| 5 | A round-20 field exported to the public site but never displayed | No | Removed from the export |
| 6 | 14 fixed test rows used as SHAP inputs, two per headline family | No | Inputs only, never a score |
| 7 | Display extractions for the demo: 514 rows | No | Feature values of rows already explained |
| 8 | The dashboard simulator before 2026-10-13 replayed test rows with a per-alert match mark | No | Not logged; no aggregate ever computed |
| 9 | One preregistered evaluation of nine sealed checkpoints | No | Selection and sealing came first (Section 6.H) |
<!-- src: docs/test_set_exposure_audit.md -->

The audit also confirmed that the following code paths never read the test set: hot-swap retraining, model loading in the backend (validation only), XGBoost tuning (early-stopped on validation), every statistic given to ByzAgent, the preregistered method runs, and three checkpoint-only folders.

### Provenance of the locked choices

@tab:provenance-full lists which data split chose each locked setting.

Table: Which split chose each locked setting {#tab:provenance-full size=9.5}
| Choice | What the recorded decision cites | Validation-best value | Test score used? |
|---|---|---|---|
| 3 local epochs | The round-20 test score of `fedavg_a0.5_s42` | 3 epochs, re-checked on 2026-10-13 in all three seeds | Yes, as first recorded |
| FedProx μ=0.0005 | Test macro-F1 at α=0.5, seed 42 | μ=0.0005 is also best on validation | Yes, as recorded; validation agrees |
| StandardScaler | Test macro-F1 of the three scaler arms | StandardScaler (validation 0.9941) | Yes, as recorded; validation agrees |
| Class weights β=0.999 | Both validation and test | β=0.999 (validation 0.9941) | Mixed; validation agrees |
| Architecture [128, 64] | Validation (top four arms within 0.0008) and parameter count | [128, 64], dropout 0.1 (validation 0.9939) | No |
| Dropout 0.1 | Within noise; the validation-best arm | Same arm | No |
| Stopping epoch and best round | Validation | n/a | No |
<!-- src: docs/test_set_exposure_audit.md -->

The audit's outcome was that two locked choices (3 local epochs and FedProx μ=0.0005) and the scaler's written rationale rest on test scores as recorded. Re-checked on validation, all three are the values validation prefers. A blanket statement that no choice of any kind ever used a test score would therefore have been false. The project instead uses the disclosure given in Section 2.2.7, which lists the three choices by name.
<!-- src: docs/test_set_exposure_audit.md -->

### The rule going forward

The team's decision of 2026-10-12 allows exactly one more use of the test set: a single evaluation of one federated configuration, chosen in advance using validation data alone. Every other configuration stays off the test set for good. That evaluation is the preregistered study in Section 6.H. Since 2026-10-13 the dashboard simulator replays validation rows and computes no aggregate. The public site's replay uses 500 stored outputs for test rows that were extracted for display before the rule.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->
