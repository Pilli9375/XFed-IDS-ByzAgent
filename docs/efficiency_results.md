# Efficiency results

Branch `efficiency`, 2026-10-13. Kept separate from the explanation check
(`docs/contribution_a_results.md`) and the trust check
(`docs/contribution_b_results.md`); nothing here changes either of them.

**No test rows were read.** Part A replays existing agent logs. Part B uses
validation rows only (train_pool rows with `val_mask = True`, 143,513 rows).
Part C uses parameter counts, existing run logs and validation macro-F1 from
validation-only runs. All parameters are in `configs/efficiency.yaml`.

Every number below names its file. Each claim says what kind of evidence it
rests on: **replay** (offline, against one logged sample), **single run /
single session**, **N sessions**, or **3 seeds**.

**Summary (wording agreed in the planning chat, 2026-10-13).**

- **Serving (3 timing sessions):** 4× lower per-flow latency (p50 45.7 vs
  186.5 µs, batch 1); at batch 1024 PyTorch eager has higher throughput. The
  backend now serves the model through ONNX Runtime fp32 by default, behind a
  startup gate that requires identical predictions on all 143,513 validation
  rows. int8 is dropped.
- **Update compression (3 seeds):** fp16 −50% / int8 −74.9% uplink; mean
  best-by-val change −0.0007 / −0.0011, no detectable effect at n=3 (seed 2024
  −0.0068 / −0.0066, within round-to-round noise).
- **Agent pre-screen (replay):** a negative result. A per-round train_loss
  threshold chosen on seed 42 did not transfer (seed 1337 poisoned flag rate
  0.017 vs logged 0.483). No redesign is planned.

---

## Part A — train_loss pre-screen in front of ByzAgent (replay)

File: `results/efficiency/agent_prescreen_replay.json`
Script: `tools/efficiency_agent_prescreen.py`

### What was replayed

ByzAgent makes **one batched LLM call per round** covering all 10 orgs
(`src/agents/byz_agent.py`, `decide_round`), not one call per org. The
pre-screen therefore saves in two ways, reported separately:

- **LLM calls avoided**: rounds in which no org passes the screen, so no call
  is made (out of 20).
- **Org slots avoided**: (org, round) pairs not sent to the LLM (out of 200).
  A smaller prompt is cheaper, but the call still happens.

Rule: in each round, `ratio = train_loss / median(train_loss of all 10 orgs)`.
An org goes to the LLM only if `ratio > t`; every other org is auto-trusted.
An org that goes to the LLM keeps the decision the LLM logged for it.
"Flag" means downweight or quarantine, as in contribution B.

Inputs are the current-round (Phase 3 prompt) decision logs. The seed-42 logs
were checked 200/200 identical to `results/inspection/phase3_gate_raw_a0.5_s42.json`.
These decisions were made on statistics logged from undefended FedAvg runs,
so the agent's decisions never fed back into training. That is why replaying
them with a different decision rule is valid at all.

### Choosing t (seed 42 only)

The rule was fixed in `configs/efficiency.yaml` before any ratio distribution
was looked at. It picks the **largest t** in the grid that keeps every flag the
logged LLM placed on a poisoned org, in both seed-42 sudden attack runs (f=3
{0,3,5} and f=2 {0,3}).

Result: **t = 10.0**. At t = 15, retention falls to 0.95 in both runs
(`selection_table_seed42`).

### Results at t = 10 on the report seeds (replay)

| run | LLM calls avoided | org slots avoided | replayed = logged | flag rate, poisoned (replay / logged) | flag rate, clean orgs (replay / logged) |
|---|---|---|---|---|---|
| seed 1337 clean | 25.0% (15 of 20 calls made) | 90.0% | 0.685 | — | 0.100 / 0.415 |
| seed 1337 f3 sudden | 95.0% (1 of 20) | 99.5% | 0.450 | **0.017 / 0.483** | 0.000 / 0.586 |
| seed 2024 clean | 0.0% (20 of 20) | 90.0% | 0.560 | — | 0.100 / 0.540 |
| seed 2024 f3 sudden | 5.0% (19 of 20) | 64.5% | 0.765 | 0.733 / 0.767 | 0.100 / 0.421 |

"Replayed = logged" is the share of the 200 (org, round) decisions where the
replayed decision equals the logged one. The 3-way and trust-vs-flag
agreements are identical here, because the replay either keeps the logged
decision or replaces it with trust.

Poisoned-flag retention (logged flags on poisoned orgs that still reach the
LLM): **1 of 29 at seed 1337** (0.034); 44 of 46 at seed 2024 (0.957).

### Reading

- **The seed-42 threshold does not transfer.** At seed 1337 the pre-screen
  hides the attack: 59 of 60 poisoned (org, round) pairs never reach the LLM
  (`poisoned_exposure_at_t_selected`).
  - Poisoned silo 0 is 95.4% Benign at that seed. Its train_loss ratio under
    attack stays at 0.45–0.99, because flipping its few attack rows to Benign
    barely moves its loss.
  - Silos 3 and 5 sit at 3.3–7.5× and 5.1–10.8×.
  - Clean, compositionally extreme silos reach up to 11.2× (silo 2) and 24.6×
    (silo 4) in the clean run.

  So at seed 1337, train_loss ratio does not separate poisoned from clean orgs
  well enough for any single cut.
- **The "33.8×–154.3×" separation is a different quantity.** It is a seed-42
  Glass's-delta ratio (poisoned vs clean-control, `docs/contribution_b_results.md`),
  not a per-round train_loss ratio to the median. At seed 42 (f=3) the
  poisoned silos' ratio to the median is 10.2–100.7×; at seed 1337 it exceeds
  10 in one (org, round) pair out of 60.
- **Most saving comes from smaller prompts, not skipped calls.** In attack
  runs where the screen still catches the attack, a call happens almost every
  round (0% avoided at seed 42 f3, 5% at seed 2024 f3). The saving there is
  64.5–70% fewer org slots per prompt.
- **Clean-org flag rates drop a lot** (for example 0.540 → 0.100 at seed 2024
  clean). Many logged clean-org flags are the compositional confound
  contribution B documents. This replay cannot say whether removing them is
  good: the LLM was never asked about a 1–2 org prompt.
- For scale, the logged no-pre-screen calls took 41.1–47.6 s median per call
  (`logged_call_timing_no_prescreen`, 20 calls per condition, keep_alive 0).
  A skipped round saves roughly one such call. The effect of a smaller prompt
  on call time was not measured.

### Limits (state with any use of these numbers)

1. **This is a replay against one sample of a nondeterministic agent.**
   - Each logged decision is one draw at temperature 0.2.
   - The replay also assumes the LLM would give the same decision to an org
     when shown only the orgs that passed the screen. A live run shows it
     fewer orgs, which may change its answers.
2. **An attacker who keeps train_loss under t is never seen by the LLM.**
   - This is not hypothetical in these logs.
   - In the seed-42 gradual run (diagnostic, not used for selection), the
     poisoned orgs' ratio in round 20, at 100% flip fraction, is
     0.005 / 0.096 / 0.126. When every attack row is relabelled Benign, the
     labels are self-consistent and the loss collapses.
   - Retention in that run is 0.90 (6 of 60 poisoned pairs never sent).
   - A stronger label flip can produce a *lower* train_loss.
3. The selection used 2 attack runs at one seed and one attack family (label
   flip to Benign). Phase 2 baselines and the Phase 4 matrix are n=1 by design;
   so is this.

**Decision:** the optional live run (seed 1337, f3_sudden, pre-screen on) was
**not** done. The brief made it conditional on Part A looking good, and at
seed 1337 the pre-screen removes 28 of the 29 attack flags.

**Planning chat:** reported as a negative result; no redesign.

---

## Part B — inference speed of the served model (3 timing sessions)

Files: `results/efficiency/inference_speed_summary.json` (3 sessions),
`results/efficiency/inference_speed_sessions.jsonl` (one line per session),
`results/efficiency/inference_speed.json` (last full session: per-class F1,
op counts, hardware).
Scripts: `tools/efficiency_inference_speed.py`, `tools/efficiency_inference_summary.py`.

Model: `fedavg_a0.5_s42`, round 18. It is loaded through
`backend/model_loader.load_and_verify()`, which re-checks validation macro-F1
against `round_history.json` (0.9759668074, diff 0) and never reads
`test_global.parquet`.

**Hardware.**
- AMD Ryzen 7 7435HS (8 cores / 16 threads), Windows 11, CPU only.
- torch 2.6.0, onnxruntime 1.31.0, onnx 1.23.2.
- 8 intra-op threads for both torch and ONNX Runtime.

**Protocol (per session).**
- **Latency:** 500 warm-up single-row calls, then 3 repeats × 5,000 validation
  rows (seed 42 sample), one row per call.
- **Throughput:** 20 warm-up batches, then 5 full passes over the validation
  split at batch 1024 (140 full batches, 143,360 rows).
- **What is timed:** only the forward pass on already-scaled float32 rows. The
  StandardScaler is the same for every variant and is not timed.
- **Reported value:** the median over the 3 sessions, with [min, max].

| variant | val macro-F1 | Δ vs eager | p50 latency, batch 1 | p95 latency, batch 1 | throughput, batch 1024 | size on disk |
|---|---|---|---|---|---|---|
| PyTorch eager | 0.9760 | — | 186.5 µs [172.7, 193.2] | 322.1 µs [254.1, 369.4] | 1,482,368 rows/s [1,411,067, 1,493,469] | 83,557 B (`round_018.pt`) |
| ONNX Runtime fp32 | 0.9760 | +0.0000 | 45.7 µs [40.6, 46.9] | 83.6 µs [75.7, 88.5] | 1,071,700 rows/s [1,044,718, 1,124,598] | 80,704 B |
| ONNX Runtime int8 (dynamic) | **0.8332** | **−0.1428** | 47.9 µs [45.3, 57.9] | 98.1 µs [65.1, 99.2] | 1,256,956 rows/s [1,225,154, 1,260,406] | 25,957 B |

- **ONNX fp32** gives identical predictions to eager on all 143,513
  validation rows (agreement 1.000000). At batch 1 its p50 latency is about
  4× lower than eager. At batch 1024 it is *slower* than eager on this CPU
  (1.07M vs 1.48M rows/s).
- **int8 dynamic quantization is a stop-and-flag item.** Validation macro-F1
  moves by −0.1428, far beyond the 0.005 bound. Only 0.54% of predictions
  change (agreement 0.994593), but they fall on small classes:

  | class | eager F1 | int8 F1 |
  |---|---|---|
  | Bot | 0.8815 | 0.4509 |
  | WebAttack | 0.9671 | 0.4401 |
  | Infiltration (per class only, not headline) | 0.8889 | 0.3333 |

  Before quantizing, the int8 model was built by rewriting `Gemm` as
  `MatMul + Add`, because ONNX Runtime's dynamic quantizer does not handle
  `Gemm`. That rewrite alone, still fp32, matches eager on 100% of validation
  rows (`gemm_to_matmul_rewrite_check`). The drop therefore comes from
  quantization, not the rewrite. The quantized graph has 3 `MatMulInteger`
  nodes.

  **Planning chat:** int8 is dropped and not offered; no further
  quantization schemes are tried.
- **Size:** int8 is 31% of the fp32 ONNX file. Both ONNX files are about the
  size of the `.pt` checkpoint, because the model only has 19,849 parameters.
- **Timing spread:** timings varied between sessions (p95 eager 254–369 µs).
  Two earlier development sessions, run before the per-session log existed,
  are not reported.

**Backend wiring.** ONNX fp32 is the only variant whose validation macro-F1
equals eager's to 3 decimals, so it is wired into `backend/` behind
`configs/efficiency.yaml` `serving.engine`. Per the planning chat the default
is now `onnx_fp32`; `torch` remains available.
- With `onnx_fp32`, startup exports the verified model in memory and refuses
  to start unless every validation prediction equals torch's.
- Checked once: the startup gate passed (0 differences on 143,513 rows), and
  50/50 sampled `/predict` calls returned the same family and confidence as
  the torch engine.
- A hot-swapped model always uses torch.
- int8 is not offered.

---

## Part C — communication and compute

### C1. Bytes per round (computed + cross-checked)

File: `results/efficiency/communication.json`
Script: `tools/efficiency_communication.py`

| quantity | bytes |
|---|---|
| parameters (served checkpoint) | 19,849 |
| one model, fp32 tensors | 79,396 |
| per round, down (10 orgs) | 793,960 |
| per round, up (10 orgs) | 793,960 |
| **per round, both directions** | **1,587,920** |
| one model as Flower `Array` payloads (.npy blobs) | 80,676 (+1,280 header bytes) |
| one model as serialized `ArrayRecord` protobuf | 81,180 |
| per round as protobuf, both directions | 1,623,600 |

- **Cross-check against the harness.** The harness logs tensor bytes per
  round (`arrayrecord_nbytes`). Over 500 logged rounds from 25 three-epoch
  method runs, the logs match the parameter-count arithmetic exactly for
  FedAvg, FedAvgM and FedYogi in both directions.[^fedadam]
- **Out of scope.** These counts exclude message metadata, metric and config
  records, and gRPC/TLS framing. The simulation runs on one machine, so no
  real network is involved.

### C2. Wall time per round (existing logs, 25 runs)

Same file, `wall_time_per_round`.
- Taken from `results/federated_methods/{runs,regression}/*/round_timing_comm.jsonl`.
- 25 runs × 20 rounds: FedAvgM, FedAdam, FedYogi at α ∈ {0.1, 0.5} × 3
  seeds, plus the FedAvg regression run.
- Each round covers 10 simulated orgs × 3 local epochs on CPU, plus the
  server's validation pass.

| | seconds |
|---|---|
| median, all 500 rounds | 51.4 |
| range | 26.8 – 98.7 |
| round 1 median (includes start-up) | 84.2 |
| rounds 2–20 median | 51.3 |
| α=0.1 / α=0.5 median | 51.4 / 51.4 |

All runs come from one laptop, one at a time. The note in CLAUDE.md applies:
federated training ran on CPU (Flower's runtime torch CPU build), not the GPU.

### C3. Update compression (α=0.5, 3 seeds)

File: `results/efficiency/update_compression.json`
Run log: `results/efficiency/compression_run_log.jsonl`
Runs: `results/federated_methods/efficiency/`
Scripts: `tools/efficiency_compression_runs.py`, `tools/efficiency_compression_summary.py`

**Method.**
- **Path:** FedAvg on the validation-only method path. No test evaluation
  exists on this path, client `evaluate()` is off, and no
  `final_metrics.json` was written by any run.
- **What is compressed:** the client→server update (local − received
  global), in two schemes:
  - **fp16:** the delta cast to float16.
  - **int8:** symmetric per-tensor int8 with a float32 abs-max scale per
    tensor, so 10 extra scalars.
- **Server side:** adds the dequantized delta back to the global it sent,
  then runs the unchanged Flower FedAvg aggregation.
- **Broadcast:** server→client stays float32.
- **Comparison:** each seed's published FedAvg run (`results/federated/fedavg_a0.5_s*`).

**Regression check (single run).** An uncompressed FedAvg run on the edited
harness (seed 42) reproduces the published validation curve **exactly**:
21/21 rounds identical, max diff 0.0, best 0.9760 at round 18. The default
path is unchanged by the compression hook.

**Bytes (harness-logged, every round of every run).**

| | uplink per round | saved vs fp32 uplink | saved vs fp32 total (up + down) |
|---|---|---|---|
| fp32 (reference) | 793,960 B | — | — |
| fp16 | 396,980 B | 50.0% | 25.0% |
| int8 per-tensor | 198,890 B | 74.9% | 37.5% |

**Validation macro-F1 (3 seeds, one run each).** Compressed − uncompressed;
all four statistics as required for trust-check comparisons:

| scheme | best-by-validation | final round (20) | final-5 mean (16–20) | mean of rounds 1–20 |
|---|---|---|---|---|
| fp16, per seed 42 / 1337 / 2024 | +0.0036 / +0.0011 / **−0.0068** | +0.0037 / −0.0016 / +0.0083 | −0.0465 / +0.0223 / −0.0037 | −0.0029 / +0.0168 / −0.0011 |
| fp16, mean ± sd | −0.0007 ± 0.0054 | +0.0035 ± 0.0050 | −0.0093 ± 0.0347 | +0.0043 ± 0.0109 |
| int8, per seed 42 / 1337 / 2024 | +0.0020 / +0.0013 / **−0.0066** | −0.0876 / +0.1173 / +0.0083 | −0.0169 / +0.0436 / −0.0023 | +0.0034 / +0.0068 / −0.0001 |
| int8, mean ± sd | −0.0011 ± 0.0048 | +0.0127 ± 0.1025 | +0.0081 ± 0.0316 | +0.0034 ± 0.0034 |

Absolute best-by-validation, compressed vs uncompressed: seed 42 fp16 0.9796
vs 0.9760 (int8 0.9780), seed 1337 0.9883 vs 0.9871 (int8 0.9884), seed
2024 0.8576 vs 0.8644 (int8 0.8578).

**Reported as (planning chat):** fp16 −50% / int8 −74.9% uplink; mean
best-by-val change −0.0007 / −0.0011, no detectable effect at n=3 (seed 2024
−0.0068 / −0.0066, within round-to-round noise). No more seeds are run now.

Seed 2024 crossed the session's 0.005 stop-and-flag bound for both schemes;
it was flagged and is reported, not tuned. What the numbers support:
- The 3-seed mean change in best-by-validation macro-F1 is small (−0.0007
  fp16, −0.0011 int8), and its sign is not consistent across seeds (+, +, −).
- Per-round validation F1 in these runs swings far more than any of these
  deltas:
  - int8 final-round deltas reach −0.0876 and +0.1173.
  - The documented round lottery is up to 0.118.
  - A float16 rounding of the update is enough to move the trajectory onto a
    different path.
- So at n=3 a compression effect of this size cannot be told apart from
  trajectory noise. The data do not show that compression is harmless within
  0.005. They do not show that it is harmful either.
- The bytes saving is exact and deterministic. The accuracy effect is
  unresolved at this n.

**Wall time.** Rounds 2–20 median per run:
- uncompressed regression: 51.7 s;
- fp16: 51.7 / 27.8 / 50.1 s;
- int8: 51.5 / 50.9 / 50.7 s.

The 27.8 s run (fp16, seed 1337) is an outlier on the fast side; C2 also saw
rounds as short as 26.8 s on this laptop. Compression has no measurable
wall-time cost or benefit here. The simulation moves bytes within one
machine, so a smaller payload cannot show up as a network saving.

[^fedadam]: FedAdam is the one exception: its downlink from round 2 on is
    1,587,920 B, twice the fp32 size, because Flower's FedAdam
    (`flwr/serverapp/strategy/fedadam.py`, flwr 1.33.0) scales the update by
    `eta_norm`, a numpy float64 scalar, which makes the broadcast global
    weights float64. Clients load them into a float32 model, so training is
    unaffected; FedAvg and the served model are not affected.
