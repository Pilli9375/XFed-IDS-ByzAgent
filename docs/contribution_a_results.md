# Explanation check — Results

**This is the canonical write-up of the explanation check (explanation parity under non-IID federation).** Every number below is read from a file already on disk, produced by the tools in `tools/`; nothing here is a new computation. Where a number is a derived statistic (a correlation, a median-of-medians) rather than a raw CSV cell, the file and method that produced it are cited inline. `PROJECT_INSTRUCTIONS.md`, `docs/measurement_protocol.md`, and the dashboard (`app_lib/sections.py`, "Methods & Limits") each carry a short note pointing back here — this document is the one to update when a number changes.

---

## 1. The claim

**Under realistic non-IID federation, accuracy parity between silos does not imply explanation parity.**

This is stated as **boundary conditions on Oki et al.** (IEEE Networking Letters, 2024), not as a first measurement — Oki et al. already measured distance between distributed and non-distributed IDS feature sets and reported that federated learning reduces explanation distance. This project does not dispute that finding; it characterizes *where it breaks down*: Oki's convergence result holds at moderate-to-low heterogeneity (α=0.5, α=5.0 here) and fails to hold — in the specific sense of dropping to a level indistinguishable from pure seed noise — at severe heterogeneity (α=0.1). Never framed as "first to measure."

The **null control is the headline methodological contribution**, not the federated numbers themselves: no prior work in this space reports a baseline for how much explanation ranking varies from random seed alone, as opposed to from federation or heterogeneity. Without that baseline, a number like "Jaccard@10 = 0.53" has no reference to be falsified against. §2 below reports that baseline (the centralized-seed instability floor) alongside the federated numbers, and §9 of `docs/measurement_protocol.md` is the full methodological specification.

Gholizade et al.'s June 2026 federated-XAI survey (arXiv 2607.13045) is the open-challenge citation for this gap: it names explanation consistency under non-IID data as unsolved and states explicitly that no standardized metrics exist for measuring it.

The LLM explanation layer built on top of these numbers (Phase 2 scope) is usability, never novelty, and is out of scope for this document.

---

## 2. Headline agreement numbers

| α | Jaccard@10 (median) | Weighted τ (median) |
|---|---|---|
| 0.1 | 0.333 | 0.592 |
| 0.5 | 0.538 | 0.787 |
| 5.0 | 0.667 | 0.844 |

Reference lines:

| Reference | Value |
|---|---|
| Chance-level Jaccard@10 (k=10, n=82 features) | 0.065 |
| Centralized-seed instability floor — Jaccard@10 | median 0.429, range [0.429, 0.484] across 3 seed-pairs |

**Source:** `results/inspection/agreement_metrics.csv`, median over `family_eligible==True` rows, grouped by α (the aggregation that reproduces these six-decimal values, confirmed in `app_lib/loaders.py::get_headline_agreement`). Chance baseline from `chance_jaccard()` in `tools/agreement_metrics.py:46-50`. Instability floor from `results/inspection/centralized_instability_floor.csv` (pairwise Jaccard/τ across centralized seeds 42, 1337, 2024, computed by `tools/centralized_shap_floor.py`).

**Reading:** at α=5.0 (near-IID), agreement sits 5.1×–10.3× the chance level and comfortably above the seed-noise floor — the federated signal is real. At α=0.1 (severe heterogeneity), Jaccard@10 (0.333) drops below the floor's lower bound (0.429) — silo-vs-global explanation agreement is not distinguishable from pure seed noise, even though accuracy at that α still reaches 0.516 ± 0.048 (`PROJECT_INSTRUCTIONS.md` headline table). This is the central finding. **It is directional, not statistically confirmed**: the cluster-bootstrap CI at α=0.1 ([0.250, 0.429]) overlaps the floor's range ([0.429, 0.484]) — never stated as significant.

---

## 3. Round-wise agreement

Computed at rounds 5, 10, 15, 20 (not just the best-by-validation round), to check whether explanation agreement converges at the same rate as accuracy or lags it.

**Mean Jaccard@10 by (α, round):**

| α | round 5 | round 10 | round 15 | round 20 |
|---|---|---|---|---|
| 0.1 | 0.359 | 0.350 | 0.334 | 0.336 |
| 0.5 | 0.560 | 0.542 | 0.548 | 0.531 |
| 5.0 | 0.640 | 0.641 | 0.642 | 0.644 |

**Mean weighted τ by (α, round):**

| α | round 5 | round 10 | round 15 | round 20 |
|---|---|---|---|---|
| 0.1 | 0.524 | 0.548 | 0.541 | 0.529 |
| 0.5 | 0.770 | 0.760 | 0.759 | 0.742 |
| 5.0 | 0.830 | 0.828 | 0.822 | 0.830 |

**Mean val macro-F1 (headline) by (α, round), for comparison:**

| α | round 5 | round 10 | round 15 | round 20 |
|---|---|---|---|---|
| 0.1 | 0.460 | 0.461 | 0.464 | 0.506 |
| 0.5 | 0.872 | 0.895 | 0.937 | 0.898 |
| 5.0 | 0.860 | 0.984 | 0.949 | 0.950 |

**Source:** `results/inspection/round_wise_agreement.csv` (agreement) and `results/federated/<tag>/round_history.json` (val macro-F1), aggregated by `tools/round_wise_agreement.py`. Metadata: `results/inspection/round_wise_agreement_metadata.json`.

**Reading:** at both non-IID settings (α=0.1, α=0.5), agreement net-declines from round 5 to round 20 (Jaccard@10: −0.023 and −0.029 respectively) while validation accuracy improves over the same window (+0.046 and +0.026). At α=5.0, agreement is flat (Jaccard@10 range across all four rounds: 0.640–0.644, a 0.004 spread). **Labeled directional, not formally tested** — no significance test has been run on this trend, and the underlying SHAP values were computed at reduced fidelity (`nsamples=1000`, vs. the headline pipeline's `nsamples=4000`), so these numbers are a convergence-shape check, not a substitute for §2's headline numbers, and are not directly comparable to them in magnitude.

**Three validation checks supporting that this reflects real model behavior, not a measurement artifact:**

1. **Kernel-vs-gradient explainer check** — `results/inspection/kernel_vs_gradient_validation.csv`: median weighted τ = 0.730, median Jaccard@10 = 0.538 (n=14) between `KernelExplainer` and `GradientExplainer` on the same models. Confirms the ranking signal isn't an artifact of the explainer choice.
2. **Common vs. per-silo background ablation** — `results/inspection/common_background_ablation.csv`: median weighted τ = 0.807, median Jaccard@10 = 0.603 (n=42). Confirms cross-silo disagreement isn't a background-sampling artifact.
3. **Deletion/insertion faithfulness spot-check** (α=0.5, seed=42; `results/inspection/deletion_auc.csv`, `insertion_auc.csv`) — all four probed models' deletion AUC sits below their insertion AUC (global 0.167/0.696, silo_0 0.274/0.800, silo_1 0.166/0.628, silo_2 0.179/0.655), consistent with attributions that track real model behavior. This is a single-slice diagnostic (one config, 3 of 10 silos), not a swept precondition — see the limitations table.

---

## 4. Parity monitoring

`tools/parity_monitor.py` turns per-silo top-k rankings into a fleet-wide drift flag, using only information that would cross a real client→server trust boundary (top-10 feature-index lists only — no SHAP magnitude, no raw data).

**Result: 3 flags out of 356 rows, all at α=0.5, round 5.**

| tag | seed | silo | silo_deviation | flagged |
|---|---|---|---|---|
| fedavg_a0.5_s1337 | 1337 | 7 | 0.775 | True |
| fedavg_a0.5_s2024 | 2024 | 3 | 0.530 | True |
| fedavg_a0.5_s2024 | 2024 | 6 | 0.535 | True |

**Source:** `results/inspection/parity_monitor.csv` (356 rows total, `flagged` column), metadata `results/inspection/parity_monitor_metadata.json` (threshold: modified z-score on median/MAD, cutoff 3.5, Iglewicz & Hoaglin 1993; full sweep, 9 configs × 4 rounds; elapsed 392.0 min).

**"Zero flags at α=0.1 does not mean α=0.1 is healthy."** The modified-z threshold flags a silo relative to *its own fleet's spread that round*, not relative to any absolute agreement level. At α=0.1, round 5, the **median** per-silo deviation across 29 eligible silos was **0.694** — worse than every one of the three deviations that *did* flag at α=0.5 (0.775, 0.530, 0.535) — yet produced **zero** flags, because at severe heterogeneity every silo diverges from consensus roughly uniformly, so nothing stands out as a statistical outlier even though the whole fleet's absolute agreement is poor. Absolute agreement should be read off §2/§3's Jaccard@k and τ trends, not off the flag count.

**The multi-draw bug that was caught.** An earlier single-draw version of this monitor flagged two silos in `fedavg_a0.1_s1337` round 5 (deviations 0.947 and 0.889) that did not reproduce under independent re-explanation of the exact same checkpoints, background, and eval rows — one silo's deviation was identical (0.889) across two fresh draws yet was flagged only in the original cached draw. Traced, not just observed: the original draw happened to produce an unusually tight cluster of tied deviation values (a byproduct of coarse top-k vote-tie-breaking over only 14 eval rows), crushing that round's MAD to 0.042; fresh draws had roughly 3× the natural MAD (~0.13), and the same 0.889 no longer cleared the threshold. The threshold formula itself was never wrong — judging it against a single uncontrolled explainer draw was. **Fix, verified and now in production** (`tools/parity_monitor.py`, "v2" in its module docstring): run the explainer N≥3 times with distinct fixed seeds on the same checkpoint/background/eval rows, compute each draw's leave-one-out deviation independently (never mixing feature indices from different draws into one consensus set), and average the N deviations per silo *before* computing median/MAD/threshold. The numbers reported in the table above are from this fixed, multi-draw version (`n_draws: 3`, `rseeds: [1001, 2002, 3003]` in the metadata). See `tools/parity_noise_floor.py` for the diagnostic that isolated the bug and `docs/measurement_protocol.md` §8 for the full account.

---

## 5. Size and heterogeneity are not independently varied by this partitioner

**The derivation.** Under `dirichlet_assign()` (`src/data/partition.py:64`), each family's per-silo proportions are drawn from `Dir(α,...,α)` over the 10 silos and sum to 1 by construction. A silo's total size is therefore

```
size_i = Σ_family available_family × p_family[i]
```

— a **deterministic output of the same label-skew draw** that produces heterogeneity, not an independent quantity that happens to correlate with it. This means a raw correlation between silo size and agreement cannot, on its own, distinguish "heterogeneity affects agreement" from "this is just restating the label-skew draw."

**Zero-order correlation confirms the confound is real, not hypothetical.** Silo size correlates with Jaccard@10 at α=0.1 (r=+0.46, p=0.011) but not at α=5.0 (r=+0.07) — consistent with size itself carrying signal that is really the label-skew effect, since heterogeneity (and therefore size variance) is largest at α=0.1 and smallest at α=5.0.

**Substitution ordering: entropy first, then KL — not chosen after the fact.** Label entropy over the 9-family vocabulary was the *pre-specified* heterogeneity covariate. Its zero-order correlation with agreement at α=0.5 (r=−0.12 to −0.15) **did not survive conditioning on log(silo size)**: the partial correlation weakens and **flips sign** (to +0.23/+0.13 for Jaccard@10/weighted τ, n=30) — the signature of a covariate whose apparent effect was actually carried by size. Entropy was abandoned as the covariate for this reason, not swapped preemptively. KL divergence from the global family distribution was tested in its place — a *directional* divergence measure rather than a mere-evenness one — and **retains a strong partial correlation with agreement after the same conditioning**:

| α | Jaccard@10 partial r | Weighted τ partial r | n |
|---|---|---|---|
| 0.1 | −0.57 | (not separately reported) | 29 |
| 0.5 | −0.82 | −0.87 | 30 |

(Partial correlations control for log(silo size); no p-values reported, per the project's own convention for these three-seed-scale correlations.)

**Source:** per-silo values in `results/inspection/size_matched_heterogeneity.csv` (columns: `log_size`, `entropy`, `kl_from_global`, `jaccard_at_10`, `kendall_weighted_tau`); zero-order size correlation in `results/inspection/silo_size_vs_agreement.csv`; full derivation and numbers in `docs/measurement_protocol.md` §10 item 5.

**What this does and doesn't show.** Conditioning on log(size), KL-from-global still predicts agreement — heterogeneity's effect holds up, size alone doesn't explain it away. This narrows the limitation; it does not remove it. The partial correlation is still observational, computed on silos whose size and heterogeneity were jointly determined by the same draw, not on a design where the two were manipulated independently. Disentangling them causally would require a separate experimental control (size-equalized partitions), not a change to this measurement.

---

## 6. FedProx at μ=0.0005

μ=0.0005 was the value carried forward from the Chat 03 exploratory run — not swept, and not the only value tried exploratorily (μ=0.01 was also tried once at α=0.5, seed=42, and collapsed macro-F1 to 0.71 with Bot/WebAttack recall at 0.0; μ=0.0005 was the value that preserved accuracy). Every FedProx number in this section is at **μ=0.0005** specifically; it is not swept, and should not be read as an optimum.

**α=0.5, μ=0.0005: agreement gain, independent of a flat accuracy signal, across all 3 seeds on Jaccard@10.**

| seed | FedAvg J@10 | FedProx J@10 (μ=0.0005) | Δ | FedAvg τ_w | FedProx τ_w (μ=0.0005) | Δ | FedAvg test-F1 | FedProx test-F1 (μ=0.0005) | Δ |
|---|---|---|---|---|---|---|---|---|---|
| 42 | 0.5444 | 0.5707 | +0.0263 | 0.7545 | 0.7647 | +0.0102 | 0.9753 | 0.9794 | +0.0041 |
| 1337 | 0.5096 | 0.5269 | +0.0173 | 0.7318 | 0.7565 | +0.0247 | 0.9866 | 0.9846 | −0.0020 |
| 2024 | 0.6167 | 0.6209 | +0.0042 | 0.7913 | 0.7904 | −0.0009 | 0.8605 | 0.8591 | −0.0014 |

Jaccard@10 (μ=0.0005) is up in all 3 seeds, shrinking from +0.0263 to +0.0042 across the table. Weighted τ (μ=0.0005) is up in 2 of 3 seeds and negligibly down in the third (seed 2024, −0.0009 — noise-level). Test-F1 is small and sign-mixed across all 3 seeds (+0.0041, −0.0020, −0.0014) — accuracy is flat while agreement moves consistently in one direction on Jaccard@10.

**α=0.1, μ=0.0005: inconclusive at n=3 — agreement and accuracy move together, per seed.**

| seed | FedAvg J@10 | FedProx J@10 (μ=0.0005) | Δ | FedAvg τ_w | FedProx τ_w (μ=0.0005) | Δ | FedAvg test-F1 | FedProx test-F1 (μ=0.0005) | Δ |
|---|---|---|---|---|---|---|---|---|---|
| 42 | 0.3257 | 0.3917 | +0.0660 | 0.5078 | 0.6176 | +0.1098 | 0.5426 | 0.5526 | +0.0100 |
| 1337 | 0.3979 | 0.3312 | −0.0667 | 0.6147 | 0.5689 | −0.0458 | 0.4481 | 0.4202 | −0.0279 |
| 2024 | 0.3301 | 0.4109 | +0.0808 | 0.5331 | 0.6265 | +0.0934 | 0.5572 | 0.6265 | +0.0693 |

At every one of the 3 seeds, agreement and accuracy point the same direction under μ=0.0005 (both up at seeds 42 and 2024, both down at seed 1337). With agreement and accuracy confounded together at this α, n=3 does not let this analysis separate an explanation-specific FedProx effect from an accuracy-driven one — unlike α=0.5, where accuracy stayed flat while agreement moved. Not stated as a finding either way.

**α=5.0, μ=0.0005: nothing.**

| seed | FedAvg J@10 | FedProx J@10 (μ=0.0005) | Δ | FedAvg τ_w | FedProx τ_w (μ=0.0005) | Δ | FedAvg test-F1 | FedProx test-F1 (μ=0.0005) | Δ |
|---|---|---|---|---|---|---|---|---|---|
| 42 | 0.6406 | 0.6441 | +0.0035 | 0.8415 | 0.8396 | −0.0018 | 0.9900 | 0.9889 | −0.0011 |
| 1337 | 0.6688 | 0.6593 | −0.0095 | 0.8385 | 0.8330 | −0.0055 | 0.9905 | 0.9890 | −0.0015 |
| 2024 | 0.6269 | 0.6732 | +0.0463 | 0.8373 | 0.8391 | +0.0018 | 0.9889 | 0.9919 | +0.0029 |

Small, sign-inconsistent movement across seeds on every metric, within the range already seen as run-to-run noise elsewhere in this project — no directional signal to report at μ=0.0005, α=5.0.

**Source:** `results/inspection/agreement_metrics.csv` and `results/inspection/agreement_metrics_fedprox_mu0.0005.csv` (mean Jaccard@10 / weighted τ over `family_eligible==True` rows, per α/seed — **mean**, not the median convention used in §2, stated explicitly here to avoid conflation); `results/inspection/best_rounds_manifest.json` and `results/inspection/best_rounds_manifest_fedprox_mu0.0005.json` for `test_macro_f1_headline`. Row counts match exactly between FedAvg and FedProx at every (α, seed) pair, confirming the same eligibility filter (T_SILO=400, M_FAMILY=20) was applied identically to both.

---

## 7. The recurring α=0.5 pattern

Three independent analyses in this document each single out **α=0.5** (moderate heterogeneity) as the point where something distinct happens, without a shared mechanism connecting them:

- **§4 parity monitoring** — all 3 real flags in the entire 356-row sweep occurred at α=0.5, despite α=0.1 having *worse* absolute per-silo deviation (median 0.694 vs. the flagged α=0.5 deviations of 0.530–0.775). α=0.1's uniform divergence produces no statistical outliers; α=0.5 does.
- **§5 size/heterogeneity** — the KL-from-global partial correlation with agreement is stronger at α=0.5 (−0.82/−0.87) than at α=0.1 (−0.57).
- **§6 FedProx** — the agreement gain at μ=0.0005 is consistent and directionally clean across all 3 seeds at α=0.5, while it is confounded with accuracy at α=0.1 (inconclusive) and absent at α=5.0 (nothing).

This is stated as an **open pattern, with no mechanism proposed**. Three analyses converging on the same α is worth flagging precisely because it is not yet explained — the temptation to retrofit a story (e.g., "α=0.5 is where per-silo models are similar enough for outliers to be detectable but different enough for the proximal term to matter") is explicitly resisted here. It is left as an open question for future work.

---

## Test-set access note

**Test-set access note.** The test set was evaluated exactly once, for model evaluation. Separately, raw feature values for 514 rows (a 14-row eval sidecar and a 500-row streamed SHAP pool) were read from `test_global.parquet` for display in the demo dashboard only, because SHAP values for those rows had already been computed. No metric was recomputed, no model was selected, and no reported number derives from these reads. Both reads were one-time and logged.

---

## Limitations

Consolidated from `PROJECT_INSTRUCTIONS.md` ("Findings that limit what can be claimed", for the findings it still lists), `data/README.md` and `configs/hotswap.yaml` (for the two data-preparation/compute findings it no longer lists), the dashboard (`app_lib/sections.py`, "Known limitations"), `docs/measurement_protocol.md` §10, and new limitations surfaced in the FedProx/verification work (§6 above and its supporting conversation). Entries stated in more than one source are merged into one row citing all sources; nothing is dropped silently.

| # | Limitation | Source(s) |
|---|---|---|
| 1 | **Round lottery is real** — FedAvg's global macro-F1 can swing up to 0.118 between best-by-validation and the final-round (unselected) test number under non-IID partitioning. Validation-round selection is not optional; every reported number in this project uses it. | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed"; dashboard "Round-lottery gap" (computed live from `final_metrics.json` across all 9 configs) |
| 2 | **Bot/WebAttack near-duplication was tested, not confirmed.** A nearest-neighbor audit found train/test rows for these families are nearly identical (test-NN ≈ 0.0), raising a pre-registered inflation caveat for their agreement numbers — but the caveat was tested and **not confirmed**; thin dataset support (Bot=3,527, WebAttack=1,542 rows) is the likelier explanation for their behavior. State as tested-and-not-confirmed, not as a live caveat. | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed"; dashboard "Known limitations" |
| 3 | **α=0.1 below-floor reading is directional, not significant.** Cluster-bootstrap CIs overlap: α=0.1 [0.250, 0.429] vs. floor range [0.429, 0.484]. Never state the below-floor result as confirmed. | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed"; dashboard "Is the α=0.1 agreement drop real, or seed noise?" callout |
| 4 | **Silo size and heterogeneity cannot be independently varied by this partitioner** — size is a deterministic output of the same Dirichlet label-skew draw that produces heterogeneity (`dirichlet_assign()`). A raw size correlation restates the label-skew effect; the KL-from-global partial correlation (conditioned on log-size) is the recommended covariate, and it survives conditioning, but the underlying draw still jointly determines both — no covariate check substitutes for an experimental control (e.g. size-equalized partitions). | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed"; dashboard "Known limitations"; `docs/measurement_protocol.md` §10 item 5 (fullest account); §5 above |
| 5 | **PortScan is the genuine generalization family**, not an artifact — 23× further test-NN distance than other families, with bimodal recall (0.9505 / 0.9506 / 0.9995) across seeds. Relevant when reading per-family agreement breakdowns. | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed" |
| 6 | **GradientExplainer was chosen over DeepExplainer by a confirmed probe, not by default** — DeepExplainer fails on this model's LayerNorm layers (additivity error 2.43 vs. a 0.01 tolerance). | `PROJECT_INSTRUCTIONS.md` "Findings that limit what can be claimed" |
| 7 | **CPU beats GPU for this SHAP workload** (measured, not assumed) — GPU ran ~3× slower; kernel-launch overhead dominates on a 19.5k-parameter model. All SHAP computation in this project runs on CPU as a result. | `configs/hotswap.yaml` (`device: cpu` comment, citing the SHAP GPU-vs-CPU probe); dashboard "Known limitations" |
| 8 | **Family-level conflict detection was required over raw-label conflict detection** — the raw-label approach silently destroyed 58,307 learnable rows during data preparation. | `data/README.md` ("Conflicts are evaluated on `family`"); `src/data/clean.py` docstring |
| 9 | **GradientExplainer's additivity residual is nonzero** — typically 0.67–1.31 in logit space for this model; SHAP values plus the base value don't perfectly reconstruct the model's output. Disclosed, not hidden, and not gated on (see #14 below). | dashboard "Known limitations" |
| 10 | **Explanations never leave the client in raw form.** Per locked decision 4, only top-k rankings (and, in the parity monitor, leave-one-out deviation scores) cross the client→server boundary. This protects the project's privacy premise, but it also means every server-side agreement/monitoring analysis in this document only ever sees a compressed summary of each silo's explanation, never the full SHAP vector. | dashboard "Known limitations" |
| 11 | **Background substitution is off-manifold** — SHAP's "missing feature" baseline (the class-stratified background mean) is not a real network flow. A standard, disclosed limitation of perturbation-based explainability generally, not specific to this project. | dashboard "Known limitations" |
| 12 | **The faithfulness check (§3, §7 of the protocol) is a single-slice spot-check, not a swept precondition.** It runs on one config (α=0.5, seed=42) and 3 of 10 silos, and nothing downstream (`agreement_metrics.py`, `round_wise_agreement.py`, `parity_monitor.py`) reads or conditions on its output. This is a resource-allocation decision — the compute budget was spent on the size/heterogeneity question (§5) instead — not an oversight. | `docs/measurement_protocol.md` §10 item 1 (and §7's allocation discussion) |
| 13 | **The centralized-seed instability floor (§2) is itself only 3 points** — three seeds gives three pairwise comparisons, enough to report a median, not enough to report a reliable interval. A tighter or looser floor from a different seed triple can't be ruled out without more seeds, each of which is a full centralized training run. | `docs/measurement_protocol.md` §10 item 2 |
| 14 | **Ground-truth-class anchoring (§3 of the protocol) is a choice, not the only valid one.** Anchoring every ranking comparison on the true label (rather than each model's own predicted class) deliberately excludes prediction disagreement from what "agreement" measures here. A predicted-class variant would answer a different, also-valid question and would need its own eligibility scheme. | `docs/measurement_protocol.md` §10 item 3 |
| 15 | **The chance-level baseline (0.065, §2) assumes independence and uniformity** among features — real feature-importance rankings are not uniform, so the true "uninformative" baseline for this dataset could sit above or below 0.065. No empirical (permutation-based) chance baseline is computed as a cross-check. | `docs/measurement_protocol.md` §10 item 4 |
| 16 | **Faithfulness AUC (§3's three checks) has no agreed absolute threshold.** Deletion/insertion AUC is reported as a relative, eyeballed diagnostic ("lower/higher is better") — no literature-backed threshold exists for what constitutes "faithful enough." A genuine open point, not an oversight. | `docs/measurement_protocol.md` §10 item 6 |
| 17 | **SHAP's Monte Carlo sampling is unseeded.** `shap.GradientExplainer(...).shap_values(..., nsamples=4000)` (and the reduced-fidelity `nsamples=1000` round-wise pass) is never seeded anywhere in `tools/local_shap_pipeline.py` or `tools/round_wise_shap.py`. Confirmed empirically during FedProx verification: re-running SHAP on the identical checkpoint, identical background, identical eval rows (`fedavg_a0.5_s42`, global model) produced different SHAP values on the second draw — mean absolute difference 0.0188, max 0.403, on a stack with values typically in the low single digits — while `eval_y`, `eval_families`, and `background_size` were all exactly reproduced (confirming the deterministic parts of the pipeline are not the source). Every Jaccard@k / τ number in this document reflects one unseeded draw per (config, silo); the parity monitor (§4) is the only component in this document that already addresses this, by averaging N=3 draws before thresholding. Ranking-level noise from this (e.g. how often a feature crosses the top-10 boundary between draws) has not been characterized for the headline agreement pipeline. | New — this document, per the FedProx-verification conversation |
| 18 | **Silos within one federated run are not independent draws.** Every silo in a given (α, seed) config shares the same global-model aggregation trajectory — the same sequence of FedAvg/FedProx rounds, the same random client sampling, the same global initialization. Treating the 10 silos in one config as 10 independent observations (as the raw row counts in §2–§6's tables implicitly do) overstates the effective sample size; the number of genuinely independent units in this project's design is closer to the number of seeds (3 per α) than the number of (silo × seed) rows. | New — this document |
| 19 | **n=3 seeds is a ceiling, not a choice made freely.** Every seed is a full centralized or federated training run; adding a seed multiplies training cost directly. This caps statistical power everywhere a per-seed pattern is reported in this document — §5's partial correlations (n=29/30, silo-level within 3 seeds), §6's FedProx per-seed breakdown (n=3 per α), and §2's instability floor (item 13 above) all inherit this ceiling. | New — this document (generalizes `docs/measurement_protocol.md` §10 item 2 beyond just the instability floor) |
| 20 | **μ=0.0005 is a single point, not a swept optimum.** §6's FedProx numbers reflect exactly one μ value, carried forward from Chat 03's exploratory run (where μ=0.01 was also tried once and collapsed accuracy). No systematic sweep over μ was performed; "FedProx helps at α=0.5" in this document means "FedProx at μ=0.0005 helps at α=0.5, in this one exploratory-then-confirmed setting," not that μ=0.0005 is a validated optimum or that other μ values would show the same pattern. | New — this document |

**Excluded from this table:** the Phase 1 Streamlit app's practical performance ceiling is an engineering note about the old Streamlit dashboard, not a limitation of the explanation check's measurement or claims. It was previously cited from `PROJECT_INSTRUCTIONS.md`, which no longer lists it, and no other file on disk records it, so it is omitted here for topical fit, not overlooked.

---

*Numbers in this document were current as of the FedProx μ=0.0005 sweep (2026-08-25). If any upstream CSV, manifest, or script referenced above changes, this document is the one to re-derive from and update — the other three locations defer to it.*
