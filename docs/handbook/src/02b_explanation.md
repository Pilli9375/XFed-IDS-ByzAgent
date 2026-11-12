## 2.4 Explanation check {#ch-expl}

### In one line

Each organization explains its own model with SHAP on its own machine, only the top-10 feature rankings go to the server, and we measure how well those rankings agree with the global model's — finding that agreement falls as data becomes more heterogeneous, down to a level at α=0.1 that sits below a seed-noise floor (directional, not significant).

### The plain version

Ten organizations each trained the same kind of detector on their own traffic. We asked every one of them the same question: which clues did you use to spot this attack? When their traffic is similar, they mostly point to the same clues — their top-10 lists overlap at 0.667. When their traffic is very different, the overlap falls to 0.333, which is even lower than two copies of one ordinary model, trained twice by chance, agree with each other (0.429) (source: `docs/contribution_a_results.md` §2). Treat that last drop as a strong hint, not a proven result: the uncertainty ranges of the two numbers touch.

### Why this exists

**The claim** this chapter tests, from the canonical results document: **"Under realistic non-IID federation, accuracy parity between silos does not imply explanation parity."** (source: `docs/contribution_a_results.md` §1)

Why should anyone care? An analyst who gets an alert wants to know *why*. If every organization's model raises the same alert for *different reasons*, then an explanation that convinces one analyst might be meaningless at another organization. A model can be accurate and still be "right for different reasons" across sites.

Oki et al. (IEEE Networking Letters, 2024) showed that federated training *reduces* explanation distance in a distributed IDS. We don't dispute that. We ask **where that reduction breaks down** as client data becomes more different (source: `docs/contribution_a_results.md` §1). And we add a reference line nobody in this space reports: how much explanations differ from **random seed alone**.

### How it works

![The explanation check, step by step. Only top-10 rankings cross from each organization to the server.](img/fig14_expl_pipeline.svg)

1. **A fixed evaluation set.** Every model explains the *same physical rows*: 14 rows, 2 per headline family, drawn once with `EVAL_SEED = 12345`. (The target was 20 rows; 20 // 7 = 2 per class gives 14.) Each model rescales the raw rows with its own scaler (source: `docs/measurement_protocol.md` §2).
2. **Client-side SHAP.** Each silo runs `GradientExplainer` (`nsamples=4000`) on its own model, with a fixed, seeded, class-stratified background of 200 rows from its *own* training data (source: `docs/measurement_protocol.md` §5; locked decision 4 in `CLAUDE.md`).
3. **Anchor on the true class.** For each row, take the SHAP vector of the row's true family, so models are compared on how they support the correct answer, not on what each happened to predict (source: `docs/measurement_protocol.md` §3).
4. **Only rankings leave.** Each silo turns its SHAP vector into a top-k ranking. **Only the top-k ranking crosses the client → server boundary** — no SHAP magnitudes, no raw data (locked decision 4; source: `CLAUDE.md`).
5. **Compare with the global model.** For each (silo, row), compute Jaccard@k (k ∈ {5, 10, 20}; headline k=10) and weighted Kendall's τ between the silo's ranking and the global model's (source: `docs/measurement_protocol.md` §6).
6. **Eligibility.** A (silo, row) pair counts only if the silo is big enough (T_SILO = 400 flows) and holds enough of that row's family (M_FAMILY = 20) (source: `docs/contribution_a_results.md` §6). A silo with no Bot traffic can't be expected to explain Bot.
7. **Reference lines.** Compare with chance (0.065) and with the centralized-seed instability floor.

**Analogy for the whole check.** Ten doctors in ten hospitals each diagnose the same 14 patient files. We don't ask only "did they reach the same diagnosis?" (accuracy) but "did they cite the same symptoms?" (explanations). And before blaming the hospitals for disagreeing, we measure how much *one* doctor disagrees with *themself* on different days (the seed-noise floor).

### What we actually did

| Choice | Why | Alternative rejected |
|---|---|---|
| **GradientExplainer** | DeepExplainer fails on LayerNorm (additivity error 2.43 vs 0.01 tolerance) (source: `CLAUDE.md`) | DeepExplainer |
| **CPU for SHAP** | Measured: GPU ran about 3× slower, because kernel-launch overhead dominates on a ~19.5k-parameter model (source: `docs/contribution_a_results.md`, Limitations #7) | GPU |
| **Ground-truth class anchoring** | Separates "explains the same label differently" from "predicts a different label" (source: `docs/measurement_protocol.md` §3) | Each model's predicted class (answers a different question) |
| **Two metrics** (Jaccard@10 and weighted τ) | Each misses things the other catches (source: `docs/measurement_protocol.md` §6) | One metric only |
| **Median** as the headline aggregate | Per-row values are lumpy; median is robust (source: `docs/contribution_a_results.md` §2) | Mean |
| **Null control** (3 centralized seeds) | Without it, no number can be told apart from seed noise (source: `docs/contribution_a_results.md` §1) | No reference line (what prior work does) |
| **Top-k only crosses the boundary** | Keeps the privacy premise: raw SHAP vectors can reveal information about the local data (locked decision 4) | Sending full SHAP vectors |

**Three validation checks** that the agreement signal reflects real model behaviour, not a measurement artifact (source: `docs/contribution_a_results.md` §3):

1. **Explainer cross-check.** KernelExplainer vs GradientExplainer on the same models: median weighted τ 0.730, median Jaccard@10 0.538 (n=14) (source: `results/inspection/kernel_vs_gradient_validation.csv`).
2. **Background ablation.** A common background vs per-silo backgrounds: median weighted τ 0.807, median Jaccard@10 0.603 (n=42) (source: `results/inspection/common_background_ablation.csv`). Cross-silo disagreement is not a background-sampling artifact.
3. **Faithfulness spot-check** (α=0.5, seed 42). *Deletion*: remove the top-ranked features first (replace with the training mean) and watch confidence fall — lower area under the curve (AUC) is better. *Insertion*: start fully masked and restore top features first — higher AUC is better. All four probed models have deletion AUC below insertion AUC: global 0.167/0.696, silo_0 0.274/0.800, silo_1 0.166/0.628, silo_2 0.179/0.655 (source: `results/inspection/deletion_auc.csv`, `insertion_auc.csv`).

![Deletion curve (α=0.5, seed 42): confidence in the true class as the top-SHAP features are removed first.](img/deletion_curve.png)

![Insertion curve (α=0.5, seed 42): confidence as the top-SHAP features are restored first.](img/insertion_curve.png)

### What we found

**1. Headline agreement** (median over eligible rows) (source: `results/inspection/agreement_metrics.csv`; `docs/contribution_a_results.md` §2):

| α | Jaccard@10 | Weighted τ |
|---|---|---|
| 0.1 | **0.333** | **0.592** |
| 0.5 | **0.538** | **0.787** |
| 5.0 | **0.667** | **0.844** |

| Reference | Value |
|---|---|
| Chance-level Jaccard@10 (k=10, n=82) | 0.065 (source: `tools/agreement_metrics.py`, `chance_jaccard()`) |
| Centralized-seed instability floor (Jaccard@10) | median 0.429, range [0.429, 0.484] across 3 seed pairs (source: `results/inspection/centralized_instability_floor.csv`) |

![Agreement vs α. Left: Jaccard@10 with the seed-noise floor (red dashed) and chance (grey dotted). Right: weighted τ. Shaded band = IQR across eligible silo-samples.](img/agreement_vs_alpha.png)

**Reading.** Agreement rises with α. The medians sit 5.1×–10.3× above chance (source: `docs/contribution_a_results.md` §2), so the federated signal is real. At α=5.0 agreement is comfortably above the seed-noise floor. At **α=0.1, Jaccard@10 (0.333) falls below the floor's lower bound (0.429)**: silo-vs-global agreement is not distinguishable from pure seed noise, **even though accuracy at that α still reaches 0.516 ± 0.048** (source: `docs/contribution_a_results.md` §2).

**It is directional, not significant.** The cluster-bootstrap CI at α=0.1 is [0.250, 0.429]; the floor's range is [0.429, 0.484]. They overlap, so we **never** state the below-floor result as confirmed (source: `docs/contribution_a_results.md` §2).

![The seed-noise floor compared with federated agreement across α (from the project's figures).](img/instability_floor_vs_alpha.png)

![The number line every examiner question about agreement comes back to. α=0.1 is shown with its cluster-bootstrap CI; it touches the floor's range.](img/fig10_numberline.svg)

![Accuracy and agreement do not move together across α (from the project's figures).](img/accuracy_agreement_decoupling.png)

**2. Round-wise agreement.** Measured at rounds 5, 10, 15 and 20 (source: `results/inspection/round_wise_agreement.csv`; `docs/contribution_a_results.md` §3):

| α | Jaccard@10, round 5 → 20 | Val macro-F1, round 5 → 20 |
|---|---|---|
| 0.1 | 0.359 → 0.336 | 0.460 → 0.506 |
| 0.5 | 0.560 → 0.531 | 0.872 → 0.898 |
| 5.0 | 0.640 → 0.644 (range 0.640–0.644) | 0.860 → 0.950 |

At α=0.1 and α=0.5, agreement *declines* from round 5 to round 20 while validation accuracy *rises*; at α=5.0 agreement is flat. This is **directional, not formally tested**, and was computed at reduced SHAP fidelity (`nsamples=1000`), so its magnitudes are not comparable to the headline table (source: `docs/contribution_a_results.md` §3).

![Agreement by round, from the project's figures.](img/agreement_vs_round.png)

**3. Size and heterogeneity are tangled.** Under the Dirichlet partitioner, a silo's size is a *deterministic output* of the same label-skew draw that creates heterogeneity: size_i = Σ_family available_family × p_family[i] (source: `docs/contribution_a_results.md` §5). So "small silos agree less" could just be "skewed silos agree less" in disguise. Size-controlled partitions were proven impossible under this partitioner (source: `CLAUDE.md`). We used partial correlation instead.

- **Order matters, and we state it: entropy first, then KL.** Label entropy was the *pre-specified* heterogeneity measure. At α=0.5 its correlation with agreement (r=−0.12 to −0.15) did not survive conditioning on log(size): the partial correlation weakened and **flipped sign** (to +0.23/+0.13 for Jaccard@10/τ, n=30) (source: `docs/contribution_a_results.md` §5). Entropy was abandoned for that reason. **KL divergence from the global family distribution** was tried after, and it does survive:

| α | Jaccard@10 partial r | Weighted τ partial r | n |
|---|---|---|---|
| 0.1 | −0.57 | (not separately reported) | 29 |
| 0.5 | −0.82 | −0.87 | 30 |

(source: `results/inspection/size_matched_heterogeneity.csv`; `docs/contribution_a_results.md` §5; r and n only, no p-values)

![Entropy's apparent effect is carried by silo size; KL's is not (from the project's figures).](img/entropy_kl_partial_correlation.png)

Analogy for KL: entropy asks "how evenly mixed is this silo?"; KL asks "how far is this silo's mix from the overall mix, and in which direction?" A silo that is 100% PortScan and one that is 100% Benign can have the same entropy (zero) but very different KL.

**4. FedProx at μ=0.0005** (one value, not swept; source: `docs/contribution_a_results.md` §6):

- **α=0.5:** Jaccard@10 up in all 3 seeds (+0.0263, +0.0173, +0.0042) while test macro-F1 is flat and sign-mixed (+0.0041, −0.0020, −0.0014). Agreement improves with flat accuracy.
- **α=0.1:** inconclusive at n=3 — agreement and accuracy move together in every seed, so an explanation-specific effect can't be separated from an accuracy effect.
- **α=5.0:** no effect.
- μ=0.01 was tried once (α=0.5, seed 42) and collapsed macro-F1 to 0.71 with Bot/WebAttack recall 0.0 (source: `docs/contribution_a_results.md` §6).

![FedProx vs FedAvg per seed (from the project's figures).](img/fedprox_vs_fedavg_per_seed.png)

**5. Parity monitor.** A server-side drift alarm that uses only what crosses the trust boundary (top-10 lists). It flags a silo whose deviation from the fleet is an outlier by a modified z-score (median/MAD, cutoff 3.5, Iglewicz & Hoaglin 1993) (source: `results/inspection/parity_monitor_metadata.json`). **Result: 3 flags out of 356 rows, all at α=0.5, round 5** (source: `results/inspection/parity_monitor.csv`).

- **Zero flags at α=0.1 does not mean α=0.1 is healthy.** Its median per-silo deviation at round 5 was 0.694 — worse than every flagged α=0.5 silo — but when *everyone* disagrees, nobody stands out (source: `docs/contribution_a_results.md` §4).
- **The multi-draw bug that was caught.** An earlier single-draw version flagged two α=0.1 silos that did not reproduce on fresh explainer draws of the same checkpoints. Cause: a tie-heavy cluster of deviation values crushed that round's MAD to 0.042 (fresh draws had ~0.13). Fix, now in production: run the explainer N≥3 times with fixed seeds and average the deviations *before* thresholding (source: `docs/contribution_a_results.md` §4). That's why the locked rule says parity flags need N≥3 draws.

![Parity monitor results (from the project's figures).](img/parity_monitor.png)

**6. The residual audit and sensitivity check.** SHAP's additivity is never perfect ([1.5.3](#bg-additivity)). We measured it and asked whether it moves the headline.

- On 500 validation rows for the served model, the largest absolute residual per row (logit space) has median 0.472, p95 1.105, max 3.336. Relative to the size of the output (max over classes of |ΣSHAP − (f(x) − E[f])| ÷ max over classes of |f(x) − E[f]|): median 3.2%, p95 7.7%, max 21.2% (one Infiltration row); 18 rows above 8%, mostly Bot (7), Benign (4) and WebAttack (4) (source: `results/shap/fedavg_a0.5_s42/val_pool_summary.json`; `CLAUDE.md`).
- **An earlier "~3–8%" figure had no backing file and was dropped.** It can't be recomputed for the 14 test rows, because their stored SHAP files hold no model outputs (source: `CLAUDE.md`).
- **Audit over 594 stored SHAP files** (source: `results/inspection/residual_audit.md`): residuals above the validation-pool maximum (3.336) occur in 4 of 99 final-round FedAvg files — three α=0.1 silos (two of them the smallest silo in their configuration) and the α=5.0 seed-1337 global model (3.500). None at α=0.5.
- Within α=0.1, silo residual and Jaccard@10 correlate at Spearman r=−0.237 (n=29, final round) (source: `results/inspection/residual_audit.md`).
- **Pre-specified sensitivity rule**: exclude silos whose final residual exceeds 3.336. This removes 2 silos with eligible rows (8 of 220 rows). The α=0.1 headline is **unchanged**: Jaccard@10 0.333 → 0.333; weighted τ 0.592 → 0.597 (source: `results/inspection/residual_sensitivity.json`).
- **Post-hoc, not part of the rule:** dropping the whole α=5.0 seed-1337 run leaves Jaccard@10 at 0.667 and τ at 0.844 (source: `results/inspection/residual_sensitivity.json`; `CLAUDE.md`).
- Caveat: each stored file's residual is a maximum over 14 rows, so comparing it with a per-row maximum is coarse (source: `docs/contribution_a_results.md`, Limitations #21).

**7. A recurring α=0.5 pattern, with no mechanism proposed.** Three separate analyses single out α=0.5: all 3 parity flags, the strongest KL partial correlation, and the cleanest FedProx effect. The canonical document deliberately refuses to invent a story for it and leaves it open (source: `docs/contribution_a_results.md` §7).

### What this does NOT mean

- **Not "first to measure"** explanation agreement in federated IDS. Oki et al. measured it; we characterise where their finding breaks down.
- **Not significant** at α=0.1: directional only, CIs overlap.
- **Not causal** for heterogeneity: the KL partial correlation is observational, on silos whose size and skew came from the same draw.
- **Not a full faithfulness guarantee**: one configuration (α=0.5, seed 42), 3 of 10 silos, no agreed threshold; nothing downstream depends on it (source: `docs/measurement_protocol.md` §7).
- **The floor is only 3 points** (3 seed pairs): enough for a median, not a reliable interval (source: `docs/measurement_protocol.md` §10).
- **Chance (0.065) assumes uniform, independent features**; real rankings aren't uniform. No permutation baseline was computed (source: `docs/measurement_protocol.md` §10).
- **SHAP's Monte Carlo sampling is unseeded**: re-running SHAP on identical inputs changed values (mean absolute difference 0.0188, max 0.403). Each headline number reflects one draw per (config, silo) (source: `docs/contribution_a_results.md`, Limitations #17).
- **Silos in one run aren't independent**; effective n is closer to the 3 seeds (source: `docs/contribution_a_results.md`, Limitations #18).
- **Explanations never leave in raw form**, so all server-side analysis sees only a compressed summary (source: `docs/contribution_a_results.md`, Limitations #10).
- **Background substitution is off-manifold**: SHAP's "missing feature" baseline is not a real flow — a general limit of perturbation-based explanation (source: `docs/contribution_a_results.md`, Limitations #11).
- The 14 explained rows come from the test set as **inputs only**, never as a selection score (source: `docs/test_set_exposure_audit.md`, row 6).
- Bot/WebAttack near-duplication was **tested and not confirmed** as an inflation source; thin support (Bot 3,527 and WebAttack 1,542 training rows) is the likelier explanation (source: `docs/contribution_a_results.md`, Limitations #2).
- PortScan is the genuine generalisation family (23× further test nearest-neighbour distance) (source: `CLAUDE.md`).
- **Whether FedAvgM changes explanation agreement is untested** — every number here is FedAvg (or FedProx μ=0.0005) (source: `docs/contribution_a_results.md`, optimizer section).

### Where it lives in the code

| File | What it does |
|---|---|
| `tools/eval_set_config.py` | Single source of `N_EVAL_ROWS`, `EVAL_SEED` (consolidated from seven duplicated copies) |
| `tools/extract_best_rounds.py` | Best-by-validation checkpoint manifest |
| `tools/local_shap_pipeline.py` | Client-side SHAP for every silo and the global model |
| `tools/agreement_metrics.py` | Jaccard@k, weighted τ, `chance_jaccard()` |
| `tools/centralized_shap_floor.py` | The seed-noise floor |
| `tools/round_wise_shap.py`, `tools/round_wise_agreement.py` | Rounds 5/10/15/20 |
| `tools/parity_monitor.py`, `tools/parity_noise_floor.py` | Multi-draw drift monitor and the diagnostic that found the bug |
| `tools/deletion_curve.py`, `tools/insertion_curve.py` | Faithfulness spot-check |
| `tools/kernel_validation.py`, `tools/common_background_ablation.py` | Validation checks |
| `tools/residual_audit.py` | Read-only residual audit |
| `results/inspection/` | All CSV/JSON outputs cited above |
| `docs/contribution_a_results.md` | Canonical results |
| `docs/measurement_protocol.md` | The reusable protocol |

### Questions an examiner might ask

_Numbers in these model answers repeat numbers already given with their source earlier in this chapter; the source notes are not repeated here._

**Q: Is 0.333 vs 0.429 significant?**
A: No, and we never say it is. The cluster-bootstrap CI at α=0.1 is [0.250, 0.429]; the floor's range is [0.429, 0.484]. They overlap, so the result is directional, not significant. What *is* solid is the trend across α and that every α sits well above chance.

**Q: Why should I care whether explanations agree, if the model is accurate?**
A: Because analysts act on explanations. If ten organizations' models flag the same attack for different reasons, an explanation shown to one analyst may not hold at another site. Our point is that accuracy parity doesn't guarantee explanation parity.

**Q: Isn't the disagreement just random noise?**
A: That's exactly what the null control answers. Three centralized models differing only by seed agree at a median Jaccard@10 of 0.429. At α=5.0 federated agreement (0.667) is well above that; at α=0.1 (0.333) it's below.

**Q: Why GradientExplainer and not DeepExplainer?**
A: We tested DeepExplainer: it fails on our LayerNorm layers, additivity error 2.43 against a 0.01 tolerance. GradientExplainer handles LayerNorm.

**Q: Your SHAP values don't add up exactly. Doesn't that break everything?**
A: We measured it: median relative residual 3.2%, p95 7.7% on 500 validation rows. The large residuals cluster in small α=0.1 silos, and a pre-specified rule excluding them leaves the α=0.1 headline at 0.333 (τ 0.592 → 0.597).

**Q: Why did you switch from entropy to KL? Isn't that p-hacking?**
A: We report the order openly: entropy was pre-specified and failed the size conditioning — its sign flipped. KL was tried after. That is why we call the KL result observational and report r and n only.

**Q: Why no p-values?**
A: The 10 silos in one run share one training trajectory, so they aren't independent observations. A p-value treating n=30 as independent would overstate the evidence. We report r and n.

**Q: What's the chance level and why does it matter?**
A: Two random top-10 lists from 82 features overlap with Jaccard 0.065 on average. Without it, readers compare against 0, which is the wrong anchor. Our medians are 5.1×–10.3× chance.

**Q: Did the parity monitor ever raise a false alarm?**
A: Yes — an earlier single-draw version flagged two silos that didn't reproduce. We traced it to a tie-heavy draw that crushed the MAD to 0.042, and fixed it by averaging N≥3 explainer draws before thresholding.

**Q: Does FedProx fix explanation disagreement?**
A: At μ=0.0005 only, and only clearly at α=0.5: Jaccard@10 rose in all 3 seeds with flat accuracy. At α=0.1 it's inconclusive at n=3; at α=5.0 there's no effect. We didn't sweep μ.
