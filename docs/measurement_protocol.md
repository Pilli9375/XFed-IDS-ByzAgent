# A Measurement Protocol for Cross-Silo Explanation Agreement

This document formalises the protocol used in this project to measure whether
model explanations stay consistent across silos in a federated learning
system — as a specification someone else could apply to a different
federated system, not as a report of this project's results.

**For this project's actual results** (headline numbers, round-wise agreement,
parity-monitor flags, the size/heterogeneity analysis, FedProx, and the full
consolidated limitations list), see `docs/contribution_a_results.md` — the
canonical write-up. §10 of this document is one of that file's cited
sources; it is not superseded, but the results themselves live there.

Every claim below was checked against the code that implements it
(`tools/agreement_metrics.py`, `tools/local_shap_pipeline.py`,
`tools/centralized_shap_floor.py`, `tools/deletion_curve.py`,
`tools/insertion_curve.py`, `tools/kernel_validation.py`,
`tools/common_background_ablation.py`, `tools/eval_set_config.py`,
`tools/parity_monitor.py`, `tools/parity_noise_floor.py`, `app_lib/loaders.py`)
as of 2026-08-25. Where the code does something different from how it is
commonly described in this project's own planning docs, or where an
incident in this project's own history changed what the protocol requires,
that is called out explicitly in the relevant section below rather than
smoothed over.

---

## 1. Why this protocol exists

Federated learning papers routinely report that per-silo accuracy tracks
centralized accuracy under moderate heterogeneity. Oki et al. (IEEE
Networking Letters, 2024) extended this to feature importance, reporting
that federated explanations converge toward centralized ones. Neither line
of work asks whether that convergence holds *uniformly* across the
heterogeneity spectrum, and neither reports what fraction of the measured
agreement is just noise.

Gholizade et al.'s June 2026 survey of federated XAI (arXiv 2607.13045)
names this gap directly: explanation consistency under non-IID data is
flagged as an open challenge, and the survey notes that **no standardized
metrics exist** for it. Every prior study picks its own eval set, its own
agreement statistic, and reports a bare number with nothing to compare it
against — no chance baseline, no noise floor.

This protocol is an attempt to close that specific gap: a fixed measurement
procedure, with two reference lines built in (chance and seed-noise), so
that a number like "Jaccard@10 = 0.53" is falsifiable rather than just
asserted. It doesn't propose a new agreement statistic — Jaccard@k and
weighted Kendall's τ both predate this project. What it standardizes is
*how* those statistics get computed and *what they get compared against*.

The following six sections (§2–§7) each cover one component of the core
measurement: what it measures, why it's needed, how it's computed, and
where it lives in this repo. §8 covers an extension for reusers who, like
this project, build an automated monitor on top of these measurements.

---

## 2. Fixed stratified evaluation set

**What it measures / controls:** Nothing directly — it's the shared input
that every other component depends on. Every model (global and every silo)
must be asked to explain the *same physical rows*. Without this, any
difference between two explanations is confounded: it could reflect a real
difference between the models, or it could just reflect that model A was
asked about a DDoS flow and model B was asked about a PortScan flow.

**Why it's needed:** Explanations are per-sample. To compare explanation A
against explanation B, both must be explanations *of the same input*, run
through each model's own preprocessing (its own fitted scaler).

**How it's computed:** 20 rows are targeted, split evenly across the 7
headline label classes (`Benign, Bot, BruteForce, DDoS, DoS, PortScan,
WebAttack` — this project's `headline_classes`, defined in
`configs/model.yaml`). `20 // 7 = 2` rows per class, giving **14 rows total**
in practice, not 20 — the target and the realized count diverge because the
per-class floor-division rounds down. Rows are drawn from the held-out test
set with a single fixed seed (`EVAL_SEED = 12345`), stored as **raw,
unscaled** feature values, and then rescaled per-model at explanation time
using that model's own fitted `StandardScaler` center/scale.

**Requirement — minimum rows per class.** The per-class row count
(`N_EVAL_ROWS // n_classes`) is not a free parameter to set casually low. With
only 2 eval rows per family, a silo's aggregated top-k ranking (built by
vote-counting each row's own top-k across just 2 rows) can only take a small
number of distinct values, so unrelated silos land on identical or
near-identical deviation scores by coincidence more often than a naive
reading of "14 samples" would suggest. On 2026-08-24 this produced a
concrete failure: a single-draw modified-z threshold flagged two silos in
`fedavg_a0.1_s1337` round 5 as fleet outliers, and both flags failed to
reproduce under independent re-explanation of the exact same checkpoints
(see §8's account of the same incident). The mechanism was a tie-heavy
cluster of deviation values crushing that round's MAD to 0.042 — an artifact
of coarse per-class sample counts feeding vote-based aggregation, not a
property of the silos being compared. No specific minimum is derived
analytically here — the incident is evidence that 2 rows/class is too coarse
for this feature count (82) and this fleet size (10 silos), not a validated
floor for what count is safe. A reuser choosing a per-class row count should
budget for tie-heavy collapse (§8) rather than assume more rows always
helps proportionally.

**Requirement — single source of truth.** `N_EVAL_ROWS` and `EVAL_SEED` must
be defined in exactly one place and imported everywhere the eval set is
constructed — never re-declared as literals. This was not the case for most
of this project's history: **seven files** independently re-derived this
same eval set — `tools/local_shap_pipeline.py`, `tools/centralized_shap_floor.py`,
`tools/deletion_curve.py`, `tools/insertion_curve.py`,
`tools/kernel_validation.py`, `tools/common_background_ablation.py`, and
`app_lib/loaders.py` (the dashboard) — including the centralized instability
floor (§5, the null control) and the kernel-vs-gradient validation. They
agreed only because the literals `20` and `12345` were duplicated correctly,
by hand, seven times. One copy (`tools/centralized_shap_floor.py`) hardcoded
the division's *result* (`n_per_class=2`) rather than the division itself
(`20 // 7`), so a literal search for `20 //` missed it entirely; it was only
caught by searching for the construction *pattern*
(`fam_df.sample(n=n, random_state=...)` per headline class) rather than for
either literal. All seven were verified byte-identical to each other and to
the on-disk `.npz` artifacts after consolidating them into
`tools/eval_set_config.py` — no previously reported number in this document
or this project changed as a result. This is recorded as a **latent defect
that did not fire**, not a correction to any result below: nothing currently
in this document was wrong, but nothing prevented a future edit to one copy
from silently detaching that script's eval set from the other six, and nothing
would have caught it until numbers stopped matching.

**Code reference:** `load_fixed_eval_rows()` in
[tools/local_shap_pipeline.py](../tools/local_shap_pipeline.py), and the
shared constants in [tools/eval_set_config.py](../tools/eval_set_config.py).

## 3. Ground-truth reference class for ranking

**What it measures:** Which class's SHAP attribution vector gets compared
across models, for a multi-class model where every sample has one
attribution vector per class.

**Why it's needed:** A model that is federated-averaged from heterogeneous
silos may *predict* a different class than the global model does on the
same row. If agreement were measured on each model's own predicted class,
disagreement in ranking and disagreement in prediction would be entangled —
a silo model could look "more different" from the global model simply
because it predicted a different label, not because it explained the same
label differently. Anchoring on the **true label** instead means both
models are always compared on "how does your output support the correct
answer," which stays well-defined and comparable regardless of whether
either model got the row right.

**How it's computed:** For each eval row, the true class index is read from
the stored label (`eval_y`), and both the global and silo attribution
vectors are sliced at that class index before any ranking statistic is
computed: `g_vec = global_sv[sample_idx, :, true_class]`.

**Code reference:**
[tools/agreement_metrics.py:107-108](../tools/agreement_metrics.py).

## 4. Chance-level baseline

**What it measures:** The Jaccard@k value two *independent random* top-k
feature subsets would produce, given no relationship between them at all.
This is the floor below which a measured agreement number is
indistinguishable from noise in the *ranking statistic itself*, independent
of the model.

**Why it's needed:** Jaccard@k is bounded in [0, 1], but its baseline is not
0 — two random k-subsets of an n-feature space overlap by chance, and that
chance overlap grows with k/n. Reporting "Jaccard@10 = 0.53" without this
reference invites the reader to compare it against 0 or 1, both wrong
anchors.

**How it's computed:** Closed-form expectation for two independent uniform
random k-subsets of an n-item universe:
`E[|A∩B|] = k²/n`, `E[|A∪B|] = 2k − k²/n`, chance Jaccard = their ratio.
For this project's feature space (n=82) at k=10, this evaluates to
**0.065**.

**Code reference:** `chance_jaccard()` in
[tools/agreement_metrics.py:46-50](../tools/agreement_metrics.py).

## 5. Centralized-seed null control (instability floor)

**What it measures:** How much explanation agreement varies from **random
seed alone**, with federation entirely removed from the picture. Three
independently-seeded *centralized* models (same architecture, same full
dataset, no partitioning) are each explained on the same 14 fixed rows, and
pairwise agreement is computed between all three seed pairs.

**Why it's needed:** This is the component the project's own planning docs
call "the headline methodological contribution" — no prior work in this
space reports a baseline for how much explanation ranking varies from seed
alone, as opposed to from federation/heterogeneity. Without it, any
federated agreement number could just be seed noise wearing a federation
costume. A federated silo's agreement with the global model has to beat
this floor before heterogeneity can be blamed for anything.

**How it's computed:** Three centralized baseline checkpoints (seeds 42,
1337, 2024) are each run through `GradientExplainer` with the same fixed
eval rows, same `nsamples=4000`, same class-stratified 200-row background
construction as the federated pipeline (only the scaler differs, since
centralized models never see per-silo data). Pairwise Jaccard@k and weighted
τ are computed across all 3 seed-pairs (42-1337, 42-2024, 1337-2024); the
median across all pairs is the reported floor.

**Code reference:** `tools/centralized_shap_floor.py`, full pairwise loop at
[lines 172-204](../tools/centralized_shap_floor.py).

## 6. Jaccard@k + weighted Kendall's τ (the dual metric)

**What it measures:** Two different, complementary notions of "agreement"
between two ranked attribution vectors:
- **Jaccard@k** — set overlap of the top-k most important features by
  |attribution|, ignoring order within that set and ignoring magnitude.
  Answers "do the two models point the analyst to the same features."
- **Weighted Kendall's τ** (`scipy.stats.weightedtau`) — a rank-correlation
  statistic over *all* features, weighted so that pairs involving
  high-magnitude attributions matter more than pairs of near-zero ones.
  Answers "do the two models agree on the full ordering, weighted by how
  much each feature actually mattered."

**Why it's needed:** Neither statistic alone is sufficient. Jaccard@k is
blind to ordering and magnitude within the top-k, and throws away everything
outside it; weighted τ is sensitive to the long tail of near-zero-importance
features that no analyst would ever look at, unless down-weighted. Reporting
both catches cases where the two would disagree — e.g., two models could
share the same top-10 features but rank them in a different order (high
Jaccard@10, imperfect τ), or largely agree on ordering across all 82
features while missing each other on the specific top-k an analyst reads
(imperfect Jaccard@10, high τ).

**How it's computed:** Both computed per eval-row, per silo, at k ∈ {5, 10,
20}, using the ground-truth-class attribution vectors from §3 sliced from
each model's raw SHAP output.

**Code reference:** `jaccard_topk()` and the `weightedtau` call in
[tools/agreement_metrics.py:36-43,110-114](../tools/agreement_metrics.py).

## 7. Faithfulness check (deletion/insertion AUC)

**What it measures:** Whether an explanation is actually faithful to the
model it explains — i.e., whether the features SHAP ranks as important are
features the model's output actually depends on — as opposed to two
explainers that are simply *consistent with each other* while both being
disconnected from what either model is doing.
- **Deletion AUC:** starting from the real input, progressively zero out
  (substitute with train-mean) the top-|SHAP| features first, and track how
  fast the model's confidence in the true class collapses. Lower AUC = more
  faithful (confidence collapses fast once truly important features are
  removed).
- **Insertion AUC:** the mirror — start fully masked, restore top-|SHAP|
  features first, track how fast confidence rises. Higher AUC = more
  faithful.

**Why it's needed:** Jaccard@k and τ (§6) only measure whether two
explanations *agree with each other*. They say nothing about whether either
explanation is *right*. Two badly-behaved explainers could produce
identical, high-agreement, meaningless rankings. This check is what licenses
the interpretation of an agreement number as "the models explain similarly"
rather than "two explainers are coincidentally the same kind of wrong."

**How it's computed:** Reuses already-computed SHAP values (no re-running
SHAP) and does per-sample forward passes only. Substitution value is each
model's own **train-set per-feature mean** in scaled space, not zero — 28 of
this project's 82 features are zero-inflated, so zero is itself a plausible,
on-manifold value, and using it would measure "response to a plausible
input" rather than "response to feature removal." AUC is trapezoidal,
normalized to feature-count so it's comparable regardless of dimensionality.

**Code reference:** `tools/deletion_curve.py` and `tools/insertion_curve.py`,
core loops at
[deletion_curve.py:79-107](../tools/deletion_curve.py) and
[insertion_curve.py:71-98](../tools/insertion_curve.py).

**Implementation status: a spot-check, not a gate — by allocation, not
oversight.** The protocol's recommended design is a **gate**: a hard
precondition that a config's deletion/insertion AUC must clear before its
agreement numbers (§6) are trusted, evaluated across the same configuration
space agreement is measured on. That is not what this project built. As
implemented:

- `deletion_curve.py` / `insertion_curve.py` run on **one single
  representative configuration** (`alpha=0.5, seed=42`) and **3 of the 10
  silos** (`SILO_IDS = [0, 1, 2]`), not the full 9-config × 10-silo sweep
  `agreement_metrics.py` covers.
- There is **no numeric threshold** anywhere in the code or in the dashboard
  (`app_lib/sections.py::render_faithfulness`) that a deletion/insertion AUC
  must clear. The dashboard renders the AUC table and curves labeled
  "lower = better" / "higher = better" for human judgment — it does not
  block, flag, or annotate the agreement figures based on these numbers.
- Nothing downstream — `agreement_metrics.py`, `plot_agreement_vs_alpha.py`,
  `round_wise_agreement.py`, or `parity_monitor.py` — reads the
  deletion/insertion AUC outputs or conditions on them in any way. It is a
  separate diagnostic artifact, not a runtime gate.

This is a **resource-allocation decision, not an oversight**. Promoting this
check to a real gate requires sweeping deletion/insertion curves across the
full 9 configs × 10 silos rather than one config's 3 silos — the same cost
structure as the headline SHAP sweep itself (one forward pass per feature
per sample per model, per config, per silo; see §10 limitation on this). That
compute budget was deliberately spent instead on the silo-size question at
low α — first attempting size-controlled partitions, then, once §10 item 5
showed size and heterogeneity cannot be independently varied by this
partitioner, on the size-conditioned (KL-from-global, partial-correlation)
analysis that replaced them. That question directly threatens the headline
claim (accuracy parity does not imply explanation parity) in a way a wider
faithfulness sweep does not. A single-slice spot
check that shows all four probed models' deletion AUCs comfortably below
their insertion AUCs (§9) was judged sufficient qualitative reassurance for
the current claim; a reuser with a different compute budget, a different
headline claim, or more reason to distrust the explainer on more of the
configuration space should weigh that trade differently and spend the
compute here instead. The gate described above remains the correct target
design — it is unimplemented in this instantiation, not wrong as a
recommendation.

---

## 8. Extension: thresholding derived deviations for drift detection

The six components above (§2–§7) measure agreement; they do not, by
themselves, decide whether a specific silo should be automatically flagged
as anomalous. A reuser building a monitor on top of this protocol — as this
project did in `tools/parity_monitor.py`, which turns per-silo top-k
rankings into a fleet-wide drift flag using only information that would
cross a real client→server trust boundary — needs two additional pieces of
discipline the six components alone do not provide.

**Requirement — average deviation over N≥3 independent explainer draws
before flagging.** A per-silo deviation score computed from a single
`GradientExplainer` draw is not safe to threshold directly, especially
against a small eval set (§2) with coarse top-k vote aggregation. On
2026-08-24, a single-draw modified-z threshold (median/MAD, cutoff 3.5,
Iglewicz & Hoaglin 1993) flagged two silos in `fedavg_a0.1_s1337` round 5
(deviations 0.947 and 0.889) that did not reproduce under independent
re-explanation of the exact same checkpoints, same background, same eval
rows. One silo's deviation was *identical* (0.889) across two fresh draws,
yet it was flagged only in the original cached draw. The cause was traced,
not just observed: the original draw happened to produce an unusually tight
cluster of tied deviation values across the fleet — a byproduct of coarse
top-k vote-tie-breaking over only 14 eval rows (§2) — which crushed that
round's MAD to 0.042; fresh draws had roughly 3× the natural MAD (~0.13),
and the same 0.889 no longer cleared the threshold. The threshold formula
was never wrong; judging it against a single uncontrolled draw was. The
fix, verified in `tools/parity_monitor.py`: run the explainer N≥3 times
with distinct fixed seeds on the same checkpoint/background/eval rows,
compute each draw's leave-one-out deviation independently (never mixing
feature indices from different draws into one consensus set), and average
the N deviations per silo *before* computing median/MAD/threshold on them.
This changes what feeds the threshold, not the threshold formula itself.
See `tools/parity_noise_floor.py` for the diagnostic that isolated this and
`tools/parity_monitor.py`'s module docstring for the fix and its
before/after numbers.

**Interpretation — zero flags does not mean healthy.** The modified-z
threshold flags a silo relative to *its own fleet's spread that round*, not
relative to any absolute agreement level. At severe heterogeneity, every
silo tends to diverge from consensus roughly uniformly — there is no strong
consensus to converge to — so nothing stands out as a statistical outlier
even when the whole fleet's absolute agreement is poor. In this project's
full sweep, α=0.1 round 5 had a median per-silo deviation of 0.69 — worse
than any of the three deviations that *did* flag at α=0.5 — yet produced
zero flags, while α=0.5 (moderate heterogeneity, where most silos agree well
except a genuine few) produced all 3 flags in the entire 356-row sweep. A
reuser should read absolute agreement off the fleet-parity trend (§6's
Jaccard@k / τ, tracked across rounds or configs), not off the flag count —
the flag count answers "is any one silo unusual today," not "is agreement
good."

---

## 9. Worked example (this project's own reference instantiation)

Using CICIDS2017 (Distrinet V4), 82 features, 9 label classes (7 headline +
2 below-floor), 10 silos, Dirichlet α ∈ {0.1, 0.5, 5.0}, 3 seeds each:

| Step | Value |
|---|---|
| Eval set | 14 rows (2 per headline family × 7 families), `EVAL_SEED=12345` |
| Reference class | true family label per row, not each model's prediction |
| Chance-level Jaccard@10 | 0.065 (k=10 of n=82 features) |
| Centralized-seed instability floor | median 0.429, range [0.429, 0.484] across 3 seed-pairs |
| Federated Jaccard@10, α=0.1 → 0.5 → 5.0 | 0.333 → 0.538 → 0.667 |
| Federated weighted τ, α=0.1 → 0.5 → 5.0 | 0.592 → 0.787 → 0.844 |
| Deletion AUC (α=0.5, s42; lower=better) | global 0.167, silo_0 0.274, silo_1 0.166, silo_2 0.179 |
| Insertion AUC (α=0.5, s42; higher=better) | global 0.696, silo_0 0.800, silo_1 0.628, silo_2 0.655 |

Reading this together: at α=5.0 (near-IID), agreement sits at 5.1×–10.3×
the chance level and comfortably above the seed-noise floor — the federated
signal is real, not noise. At α=0.1 (severe heterogeneity), Jaccard@10
(0.333) drops *below* the instability floor's lower bound (0.429), which is
the project's central finding: under severe non-IID skew, silo-vs-global
explanation agreement is not distinguishable from pure seed noise, even
though accuracy at that α still reaches 0.516 ± 0.048 — i.e. **accuracy
parity does not imply explanation parity.** (This directional reading at
α=0.1 does not clear a cluster-bootstrap significance test in this
project's own results — see §10.) The faithfulness spot-check on the α=0.5
slice shows all four models' deletion AUCs well below their insertion AUCs,
consistent with attributions that track real model behavior rather than
each other's noise — supporting, though not proving across the full sweep
(§7), that the agreement numbers above reflect real explanations and not
two similarly-broken explainers.

---

## 10. Limitations of the protocol itself

These are limits of the *measurement procedure*, independent of what this
project's data happened to show.

1. **Faithfulness check does not cover the full configuration space
   (§7).** As implemented, it is a single-slice diagnostic, not a swept
   precondition — deliberately, per §7's allocation discussion, not by
   oversight. A reuser who wants faithfulness confirmed at every
   (α, seed, silo) combination the agreement metric is computed on would
   need to extend this, and would pay the corresponding compute cost —
   deletion/insertion curves require one forward pass per feature per
   sample per model, which does not scale free of charge across a full
   sweep.

2. **The instability floor is itself only 3 points.** Three seeds gives
   three pairwise comparisons — enough to report a median, not enough to
   report a reliable interval. A tighter or looser floor from a different
   seed triple can't be ruled out without more seeds, which directly
   multiplies training cost (each seed is a full centralized training run).

3. **Ground-truth-class anchoring (§3) is a choice, not the only valid
   one.** Anchoring on the true label is defensible and stated explicitly,
   but it is not neutral: it means disagreement in *prediction* is
   deliberately excluded from what "agreement" measures. A protocol variant
   anchored on each model's own predicted class would answer a different,
   also-valid question ("do these models justify their own decisions
   similarly") and would need a different eligibility scheme, since the
   predicted class is not guaranteed to have a stable, comparable ground
   truth across models.

4. **The chance-level baseline (§4) assumes independence and uniformity**
   — it is the expected overlap of two *independent, uniformly random*
   k-subsets. Real feature-importance rankings are not uniform (some
   features are near-constant, some are always near the top for structural
   reasons unrelated to the model), so the true "uninformative" baseline for
   a specific dataset could sit above or below the analytical 0.065 used
   here. The protocol does not include an empirical (permutation-based)
   chance baseline as a cross-check.

5. **Size and heterogeneity cannot be independently varied by this
   partitioner, which limits what a raw correlation with size can show.**
   Under `dirichlet_assign()` (`src/data/partition.py`), each family's
   per-silo proportions are drawn from a Dirichlet over the 10 silos and
   sum to 1 by construction, so a silo's total size
   (`size_i = Σ_family available_family × p_family[i]`) is a deterministic
   output of the same label-skew draw that produces heterogeneity, not an
   independent quantity that happens to correlate with it. A naive
   zero-order correlation reflects exactly this: silo size correlated with
   Jaccard@10 at α=0.1 (r=+0.46, p=0.011) but not at α=5.0 (r=+0.07) — on
   its own, that number restates the label-skew effect rather than
   isolating heterogeneity as a distinct cause, and it cannot rule out that
   the low-α agreement drop is *merely* a size artifact.

   **Recommended covariate: KL divergence from the global label
   distribution, conditioned on log(size).** Report it alongside any
   agreement number, via a partial correlation controlling for log(silo
   size) — not a zero-order correlation with size or with a simpler
   heterogeneity measure like entropy, since both are easy to conflate
   with a size effect in a way that looks like a real, independent
   relationship until checked. Worked justification from this project:
   label entropy over the 9-family vocab was the pre-specified
   heterogeneity covariate, but its zero-order correlation with agreement
   at α=0.5 (r=−0.12 to −0.15) did not survive conditioning on log(size) —
   the partial correlation weakens and *flips sign* (to +0.23/+0.13 for
   Jaccard@10/weighted τ, n=30), the signature of a covariate whose
   apparent effect was actually carried by size. KL divergence from the
   global family distribution, tested in its place, retains a strong
   partial correlation with agreement after the same conditioning (partial
   r=−0.57 to −0.87 across α=0.1/0.5, n=29/30) — evidence that
   heterogeneity, specifically *directional* divergence from the global
   mix rather than mere evenness, rules out the "merely restating size"
   reading that the raw r=+0.46 could not rule out on its own. See
   `results/inspection/size_matched_heterogeneity.csv` for the per-silo
   values.

   This narrows the limitation; it does not remove it. The partial
   correlation is still observational, computed on silos whose size and
   heterogeneity were jointly determined by the same draw, not on a design
   where the two were manipulated independently — no covariate check
   substitutes for that. Disentangling them causally still requires a
   separate experimental control (e.g. size-equalized partitions), not a
   change to the measurement itself.

6. **Faithfulness AUC has no agreed absolute threshold.** The protocol
   reports deletion/insertion AUC as a relative, eyeballed diagnostic
   ("lower/higher is better," compared across models in the same run) — it
   does not define what AUC value constitutes "faithful enough," because no
   such threshold is established in the literature this protocol draws on.
   This is a genuine open point, not an oversight specific to this
   implementation.
