# Part 6 — Final-review preparation {#part-6}

## 6.1 Top 40 examiner questions {#top40}

Each model answer is under 80 words. Practise them out loud. Numbers and their sources are in the chapters cited.

### Questions an examiner might ask — the whole project

**1. What is your project, in one sentence?**
A federated IDS that doesn't just detect attacks, but checks whether its own explanations and its own participants can be trusted. Ten organizations train a shared detector without sharing traffic; we then test whether their models detect attacks for the same reasons, and whether an LLM agent can spot poisoned participants.

**2. What's novel here?**
Not the FL + IDS + XAI combination — several 2025–2026 papers cover it. Our contributions: a seed-noise null control for explanation agreement, which we didn't find in prior work in this space, inside a reusable measurement protocol; showing where Oki et al.'s explanation convergence breaks down as α falls; and an LLM trust agent whose decisions and rationales we audit, with its limits quantified.

**3. Isn't your federated accuracy worse than centralized?**
Only under heterogeneity. At α=5.0 FedAvg scores 0.990 ± 0.001, matching centralized 0.9900 ± 0.0022. At α=0.5 it's 0.941 ± 0.057; at α=0.1, 0.516 ± 0.048. The near-IID control shows the drop is caused by non-IID data, not federation itself. Our preregistered FedAvgM reaches 0.9852 ± 0.0005 at α=0.5.

**4. Did you touch the test set?**
Yes, in documented ways, and we publish the full audit. All selection used validation. The test set was also read for logging, display and 14 SHAP input rows, with nothing chosen from those; three early settings were recorded with test numbers as rationale, and all three are re-confirmed on validation. Since 2026-10-12, only one preregistered configuration may ever be scored on test.

**5. Why trust an LLM?**
We don't, blindly. We measure it: citation error 11.7% at seed 42 and 22.5% at other seeds; ≈35–45% of its trend claims under rolling history contradicted its data; repeat calls agree 27/30 exactly and 30/30 on trust-versus-flag. Hence our wording: it produces decisions plus a rationale of measured fidelity.

**6. Krum is standard. Why did it fail?**
Krum assumes honest updates cluster and attackers stand out. Under non-IID data, honest organizations with unusual traffic also stand out. Here selection was dominated by silo size and composition: Multi-Krum excluded the same large Benign-heavy silos every round, even with zero attackers, and excluded a malicious silo 0% of the time — despite being told the true number of attackers.

**7. Is 0.333 vs 0.429 significant?**
No. The cluster-bootstrap CI at α=0.1 is [0.250, 0.429] and the floor's range is [0.429, 0.484]; they overlap. We call it directional, not significant. What is robust: agreement rises with α, and every α is 5.1×–10.3× above chance.

**8. What's the seed-noise floor and why does it matter?**
Three centralized models differing only by random seed agree at a median Jaccard@10 of 0.429. That's how much explanations move from randomness alone. Without it, a federated agreement of, say, 0.53 has nothing to be compared against.

**9. Why Jaccard@10 and weighted Kendall's τ — why two metrics?**
Jaccard@10 asks whether the analyst sees the same top-10 features; it ignores order. Weighted τ compares the whole ranking, giving important features more weight. Two models can agree on one and not the other, so we report both.

**10. Why did you choose the Distrinet V4 dataset?**
The original CICIDS2017 has documented labelling and flow-construction errors. Engelen et al. (WTMC 2021) and Liu et al. (IEEE CNS 2022) corrected them; V4 is the release from the second paper. We cite both.

**11. How did you stop duplicates leaking into the test set?**
Every distinct feature vector is a group; `StratifiedGroupKFold` keeps each group on one side, and the pipeline verifies it and raises if any vector appears on both sides. 213,752 rows shared a vector with another row, so this mattered.

**12. Why macro-F1 and not accuracy?**
Benign is 75% of the data, so predicting "Benign" always would score about 75% accuracy and catch nothing. Macro-F1 averages per-class F1, so each of the 7 headline classes counts equally.

**13. What is Dirichlet α, simply?**
A slider for how different the organizations' data is. For each attack family we draw how its flows are split across 10 silos. Small α (0.1): one silo gets nearly all of a family. Large α (5.0): each gets about a tenth.

**14. What is the round lottery?**
Under non-IID data the global model's quality jumps between rounds. At α=5.0, seed 42, round 20 was 0.118 lower on validation than the best round. So every reported model is its best-by-validation round.

**15. Why LayerNorm instead of BatchNorm?**
BatchNorm stores running statistics of its training data; in FL those come from incompatible per-silo distributions and averaging them is meaningless. LayerNorm normalises each example by itself and has no such state.

**16. Why GradientExplainer?**
We tested DeepExplainer first: it fails on LayerNorm, with additivity error 2.43 against a 0.01 tolerance. GradientExplainer handles any differentiable layer. A KernelExplainer cross-check gave median τ 0.730.

**17. Your SHAP values don't sum exactly. Is that a problem?**
We measured it: on 500 validation rows, median relative residual 3.2%, p95 7.7%, max 21.2%. Large residuals cluster in small α=0.1 silos. A pre-specified rule excluding them leaves α=0.1 Jaccard@10 at 0.333, τ 0.592 → 0.597.

**18. Doesn't SHAP leak private data from each organization?**
Only top-k feature rankings leave each organization, never SHAP magnitudes or raw rows (locked decision 4). That protects the privacy premise, but it also means the server only ever sees a compressed summary.

**19. Why no p-values?**
Silos in one run share one training trajectory, so they aren't independent; effective sample size is closer to 3 seeds than 30 silos. A p-value assuming independence would overstate the evidence. We report r and n.

**20. You switched from entropy to KL. Isn't that p-hacking?**
We disclose the order: entropy was pre-specified and failed — after controlling for silo size its sign flipped. KL was tested afterwards and survived (partial r −0.57 at α=0.1, −0.82/−0.87 at α=0.5). That's why we call it observational.

**21. Why couldn't you control silo size directly?**
Under the Dirichlet partitioner a silo's size is determined by the same draw that creates its skew; size-controlled partitions were proven impossible with it. Partial correlation on log(size) replaced them.

**22. Does FedProx help explanations?**
At μ=0.0005 only: at α=0.5, Jaccard@10 rose in all 3 seeds with flat accuracy; at α=0.1 inconclusive; at α=5.0 nothing. μ wasn't swept — μ=0.01 collapsed macro-F1 to 0.71.

**23. What does the parity monitor do, and did it work?**
It flags a silo whose top-10 list deviates unusually from the fleet, using only rankings. 3 flags in 356 rows, all at α=0.5. An early single-draw version raised false flags; averaging N≥3 explainer draws fixed it.

**24. Zero parity flags at α=0.1 — so α=0.1 is fine?**
No. When every silo disagrees, nobody stands out as an outlier. α=0.1's median deviation (0.694) was worse than any flagged α=0.5 silo. Read absolute agreement from Jaccard and τ, not flag counts.

**25. Is your attack realistic?**
No, and we say so everywhere. It's a worst-case, full-knowledge adversary: we searched all 120 possible attacker triples for the one covering the most attack traffic. No real attacker has that global view.

**26. Which statistic actually detects attackers?**
Only train_loss: 33.8× (f=3) and 154.3× (f=2) as seed-42 effect-size ratios. Geometry statistics are weak to null, and val_accuracy inverts. But a per-round threshold tuned on seed 42 didn't transfer to seed 1337.

**27. Why does val_accuracy invert?**
The attack relabels attack flows as Benign, and the validation set is mostly Benign. So a poisoned model gets *better* at validation. A naive reader — or LLM — would trust attackers more; our prompt warns against exactly that.

**28. ByzAgent flagged attackers 100% of the time. Isn't that great?**
It also flagged them 95–100% with no attack, and flagged never-malicious silo 8 just as often. That's the compositional confound. Where silos weren't saturated (seeds 1337, 2024), real lifts of +0.40 to +0.95 appeared.

**29. State your ByzAgent claim exactly.**
"Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition."

**30. Why didn't you just choose ordinary-looking attackers?**
Because in this partition a silo with enough attack traffic to poison meaningfully is necessarily unusual. The Benign-heavy silos hold only 6.65% of Bot rows; the best attacker triple from them is 7.1× weaker. A matched control isn't constructible.

**31. Wasn't giving the baselines the true f unfair?**
Unfair in their favour, deliberately. Krum, Multi-Krum and trimmed mean were told the true number of attackers; ByzAgent wasn't. They still failed, so the failure isn't from guessing f wrong.

**32. What does it cost to defend when nobody attacks?**
Compared with clean FedAvg's test macro-F1: Krum −22.7 points, Multi-Krum −4.9, trimmed mean −1.6. Robust aggregation isn't free under non-IID data.

**33. Why did rolling history fail?**
Our pre-registered rule: it fails if the never-malicious canary rises with the attackers. The canary's lift was +0.60 (sudden) and +0.45 (gradual), matching or exceeding every attacker. The agent's reasoning also degraded on longer prompts.

**34. LLMs are random. How can you report its decisions?**
We report stability with them: three repeat calls on the same round agreed exactly 27/30 times, and 30/30 on the trust-versus-flag boundary. Temperature is 0.2. Rolling-history mode was less stable (70–80%).

**35. Why run the LLM locally?**
Privacy — sending organizations' behaviour statistics to a cloud API would undercut FL's premise — plus fixed model versions and no cost. llama3.1:8b (4-bit) fits our 6 GB GPU; it beat qwen2.5 and phi3.5 on valid IDs and grounded explanations.

**36. Why only 4 of 9 optimizer candidates?**
Wall time. A timing-only guard, which never reads scores, dropped later candidates before they started, each recorded in the preregistration. We disclose that the guard was added after one validation score was seen. Our claim is "best of these four."

**37. What did FedAvgM actually improve?**
At α=0.5, stability: mean 0.941 → 0.985, spread 0.057 → 0.0005, mainly by fixing seed 2024. At α=0.1, modest: +0.113, +0.058, +0.060 per seed. At α=5.0, parity. One test evaluation, n=3.

**38. Did federated training use your GPU?**
No. Flower's isolated runtime installed torch 2.13.0+cpu. The GPU trained the centralized MLP and XGBoost and ran Ollama. We disclose this because an earlier description said otherwise.

**39. Why ONNX, and why not int8?**
ONNX fp32 gives identical predictions and cuts per-flow latency from 186.5 to 45.7 µs. int8 lost 0.1428 validation macro-F1 because errors hit small classes (WebAttack F1 0.9671 → 0.4401), so we dropped it.

**40. If you had three more months, what would you do?**
More seeds for the floor and the trust baselines; seed SHAP sampling and average draws for the headline; a permutation-based chance baseline; a full faithfulness gate; test whether FedAvgM changes explanation agreement; and a design that separates attack strength from compositional extremity. (Scope changes go to the planning chat first.)

## 6.2 Who explains what {#speakers}

A suggested 15–20 minute split. Each speaker owns the questions for their section.

| Speaker | Sections | Handbook chapters to master | Must-say lines |
|---|---|---|---|
| **[Member 1]** | Problem, pitch, data, model, federated accuracy | 0, 1.1–1.4, 2.1–2.3 | One-line pitch; FedAvg 0.516 / 0.941 / 0.990 vs centralized 0.9900 |
| **[Member 2]** | Explanation check | 1.5–1.6, 1.9, 2.4 | "Accuracy parity does not imply explanation parity"; floor 0.429; "directional, not significant" |
| **[Member 3]** | Trust check (ByzAgent) | 1.7–1.8, 2.5 | Multi-Krum 0%; the locked claim verbatim; "a rationale of measured fidelity" |
| **[Member 4]** | Prereg, efficiency, honesty, live demo | 1.9.7, 2.6–2.8, Part 3, Part 5 | Sealed-envelope story; test-set disclosure; demo script |

**Hand-off lines:**

- **[Member 1] → [Member 2]:** "So the organizations can train an accurate model together — when their data isn't too different. But accurate for the *same reasons*? [Member 2] will show you."
- **[Member 2] → [Member 3]:** "That was the explanation check. The trust check is a separate experiment with its own evidence: what if one of the organizations is lying? [Member 3]."
- **[Member 3] → [Member 4]:** "Those are the two checks, reported separately. [Member 4] will show how we improved accuracy without peeking at the test set, what it costs to run, and the system live."
- **[Member 4] closing:** "Detect the attack, then check the detector. And every number you saw links to the file it came from. We're happy to take questions."

**Rules for the Q&A:** whoever owns the section answers first; anyone may add "and the limitation is…"; nobody combines the two checks into one claim; if you don't know, say "we didn't measure that" rather than guess.
