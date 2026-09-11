# Chat 03 — Written Claims

Closes the two "Done when" items that were artifacts rather than runs:
a privacy claim that does not overreach, and a communication-cost figure.

Every number here is traceable to a file under `results/`. Nothing is estimated.

---

## 1. Privacy claim

**The claim, as it should appear in the paper:**

> XFed-IDS shares only model parameters between silos; raw flow records never
> leave the client. This is a **data-minimisation property, not a formal privacy
> guarantee.** No differential privacy and no secure aggregation are applied —
> both are explicitly out of scope — so the system offers no defence against
> gradient-inversion or membership-inference attacks mounted against the shared
> updates, and no such resistance is claimed.

**Two disclosures that weaken the claim, stated rather than hidden:**

1. **Global class weights.** Weights are computed once from the centralized
   training split and distributed identically to every silo
   (`configs/global_class_weights.json`). This assumes participants agree to
   disclose approximate class prevalence. That is a weaker disclosure than
   sharing data, but it is not zero. The alternative — per-silo weights — was
   rejected on correctness grounds, not privacy grounds: each silo would then
   minimise a different objective, and FedAvg would average models that were
   never optimising the same loss (worst at alpha=0.1, where a silo may hold
   only a handful of classes).

2. **Server-side evaluation set.** Round-by-round model selection uses a
   validation set held at the server. In a real deployment this implies either
   a trusted coordinator holding labelled data, or an agreed shared validation
   corpus. This is standard in the FL literature but is an assumption, not a
   property of the protocol.

**What IS defensible to claim:**

- Raw flows never cross the client boundary. Verified structurally: each client
  calls `load_silo()` on its own partition only, and only an `ArrayRecord` of
  model parameters is returned (`federated/xfed_federated/client_app.py`).
- Per-silo scaler fitting means no client's feature statistics are pooled with
  another's. A global scaler would have quietly violated the premise; this was
  caught and enforced in `loaders.py::load_silo`.

**Anticipated panel question:** *"Federated learning does not guarantee privacy —
gradients leak. How do you respond?"*
Concession answer, not a defence: that is correct and this work does not claim
otherwise. What can be claimed is data minimisation plus the specific
disclosures above. Adding DP or secure aggregation is the natural next step and
was scoped out deliberately, not overlooked.

---

## 2. Communication cost

Derived from the locked architecture: 19,849 parameters, float32.

| Quantity | Value |
|---|---|
| Model size | 77.5 KB (19,849 x 4 bytes) |
| Per silo, per round (down + up) | 155.1 KB |
| Per round, 10 silos, both directions | 1.51 MB |
| **Full 20-round run** | **30.3 MB** |

**Why this number is small, and why that is a result rather than a footnote:**

The architecture pilot found all six arms within 0.0008 val macro-F1 of each
other — inside the epoch-to-epoch noise of any single run. Capacity bought
nothing measurable, so selection fell to the tiebreaker that actually matters
for federation: parameter count. The alternatives would have cost, for the same
20-round budget:

| Architecture | Params | Total transferred | Ratio |
|---|---|---|---|
| **[128, 64] (selected)** | **19,849** | **30.3 MB** | **1.0x** |
| [256, 128] | 56,073 | 85.6 MB | 2.8x |
| [512, 256, 128] | 209,673 | 320.0 MB | 10.6x |

**Paper sentence:**

> At 19,849 parameters (77.5 KB per model), a full 20-round federated run
> transfers approximately 30.3 MB across all 10 silos, or 155 KB per silo per
> round. The 512-256-128 alternative would have transferred 10.6x more for no
> measured accuracy gain (all six architecture-pilot arms fell within 0.0008
> validation macro-F1 of one another).

**Honest boundary:** this counts parameter payload only. It excludes protocol
overhead, serialization, TLS, and any real network effects — this is a
single-machine simulation and makes no claim about wall-clock communication
time or straggler behaviour in a real deployment.

---

## 3. Scope note: FedProx is exploratory, not swept

**This must be labelled wherever FedProx appears.** The FedAvg results are
3 seeds x 3 alphas = 9 runs. The FedProx results are **3 single-seed runs**.
They are not equivalent evidence and must never be tabulated as though they are.

| Run | alpha | seed | mu | macro-F1 (7) | vs FedAvg |
|---|---|---|---|---|---|
| regression check | 0.5 | 42 | 0.0 | 0.9753 | exact match — confirms mu=0 IS FedAvg |
| over-regularized | 0.5 | 42 | 0.01 | 0.7119 | -0.264 (Bot AND WebAttack both to 0.0000) |
| best | 0.5 | 42 | 0.0005 | 0.9794 | **+0.004** (Bot F1 0.8825 -> 0.9205) |
| severe skew | 0.1 | 42 | 0.0005 | 0.5526 | **+0.010** (PortScan recall 0.000 -> 0.119; Bot unchanged at 0.000) |

**The finding, which is more useful than "FedProx wins":**

> FedProx at mu=0.0005 improved PortScan recall under severe skew
> (0.000 -> 0.119) but had no effect on Bot, which remained at zero. This
> asymmetry is explained by the near-duplicate audit: PortScan is the only
> headline family whose test flows sit substantially further from the training
> set than training flows sit from each other (23x), i.e. the only family
> requiring genuine cross-silo generalization — exactly what a proximal
> constraint toward consensus helps. Bot, by contrast, is 89.6% duplicated
> (Chat 02), so under alpha=0.1 individual silos may hold too few genuinely
> distinct examples for any drift-regularization strategy to recover. FedProx
> addresses client drift; Bot's failure mode is local data sparsity.

At mu=0.01 the round-1 training loss doubled (0.0338 -> 0.0679) before local
weights had meaningfully drifted, indicating the proximal penalty was already
comparable in magnitude to the classification loss. Because the penalty is
class-blind, it suppressed precisely the large local corrections that the rarest
classes require, driving both Bot and WebAttack to zero.

**Not run, and why:** alpha=5.0 (FedAvg already at 0.9898, statistically at the
centralized ceiling — no headroom for FedProx to demonstrate anything);
mu=0.1 (10x a value that already collapsed two classes; outcome predictable,
~25 min for no information).

---

## 4. Open item carried to Chat 04

**Per-silo metric logging does not exist.** FedAvg's `aggregate_evaluate`
returns only the fleet-wide weighted mean, and `silo_id` was removed from the
MetricRecord because averaging an identifier produces a meaningless number
(it was reporting 4.96 as the "average silo").

Chat 04's cross-silo explanation agreement is **per-silo by definition**, so
this must be built there — with each client writing its own line to a shared
file, bypassing FedAvg's averaging entirely. Deferred rather than guessed at,
because the right schema depends on what the agreement analysis needs.
