# Part 1 — Background from scratch {#part-1}

This part explains every idea the project uses, *before* the project uses it. Nothing here is specific to our results. Where we use a number, it is either a made-up teaching example (and says so) or it cites a file.

## 1.1 Network traffic, flows and features {#bg-flows}

**In one line:** a *flow* is a summary of one conversation between two computers, and each row of our dataset is one flow described by 82 numbers.

**Everyday analogy.** Think of a phone bill. It doesn't record what you said. It records *who* you called, *when*, *for how long*, and *how much data* was used. A network flow is the same idea for computer traffic: a tool watches packets go by and, for each conversation (same source, destination, ports and protocol), writes one summary line.

**What's in a flow.** The tool used for CICIDS2017 is called CICFlowMeter. For each flow it measures things like:

- how long the flow lasted (`Flow Duration`);
- how many packets went forward and backward;
- how many bytes per second (`Flow Bytes/s`) and packets per second (`Flow Packets/s`);
- statistics of packet sizes (mean, max, standard deviation);
- the time gaps between packets ("inter-arrival times");
- how many packets carried each TCP flag (SYN, ACK, URG and so on).

Each of these is a **feature**: one number describing the flow. Our cleaned data keeps **82 candidate features** per flow (source: `data/README.md`). The raw files also have identifier columns — IP addresses, ports, a timestamp, a flow ID — but we **drop them**, because a model that learns "this IP address is the attacker" has learned the lab, not the attack. That would not work on anyone else's network.

**What one row of CICIDS2017 looks like** (shape only, values left out):

| Flow Duration | Total Fwd Packets | Flow Bytes/s | … 79 more features … | Label |
|---|---|---|---|---|
| a number | a number | a number | … | e.g. `DoS Hulk` or `BENIGN` |

The **label** is the answer: was this flow normal traffic (`BENIGN`) or part of a known attack (`DoS Hulk`, `Portscan`, `SSH-Patator`, …)? The dataset's authors created the attacks themselves in a lab over five working days, so they know which flows were attacks.

**Why a "corrected" version matters.** The original CICIDS2017 release has known errors in how flows were built and labelled. Researchers at Distrinet (KU Leuven) found and fixed many of them. We use their corrected version 4. Chapter [2.1](#ch-data) explains this.

## 1.2 What an intrusion detection system is {#bg-ids}

**In one line:** an IDS watches network traffic and raises an alert when something looks like an attack.

**Analogy.** A security guard at a building entrance. There are two styles of guard:

- A **signature-based** guard has a list of photos of known troublemakers and checks each visitor against the list. Precise, but useless against someone new.
- An **anomaly- or learning-based** guard has watched thousands of normal visitors and notices behaviour that doesn't fit. More flexible, but it can raise false alarms.

Our IDS is a **learning-based** detector: a neural network that has seen labelled examples of each attack family and of normal traffic, and learns to classify new flows. For every flow it outputs one of 9 classes: Benign or one of 8 attack families.

**Two kinds of mistake.** A *false positive* is an alarm on normal traffic (the guard stops an innocent visitor). A *false negative* is a missed attack (the guard waves a thief through). A useful IDS needs both to be rare, and it must not ignore rare attack types just because they are rare. That is why we use macro-F1 ([1.3.5](#bg-macro-f1)).

## 1.3 Basic machine learning ideas {#bg-ml}

### 1.3.1 Train, validation and test — and why the test set is sacred {#bg-splits}

**Analogy: preparing for an exam.**

- The **training set** is your textbook and homework. You learn from it.
- The **validation set** is a set of mock exams. You use them to *decide things*: which study method works, when to stop revising, which of your practice answers is best.
- The **test set** is the real final exam. You sit it **once**, at the end, and the score is what you report.

If you peek at the final exam paper while revising, your final score no longer measures what you know; it measures how well you memorised that paper. In ML, any decision made by looking at test scores — which model, which setting, which training round — quietly "leaks" the test set into the model, and the reported score becomes optimistic. That is why the test set is sacred: **every choice is made on validation; the test set is only for the final, one-time measurement.**

![How the data is split. One global group-aware train/test split comes first; validation is carved out of the training pool; federated silos are then drawn from the training pool.](img/fig04_splits.svg)

Our project takes this rule very seriously, and Part 3 tells the full, honest story of every time the test set was read.

**Group-aware splitting.** Some flows are exact copies of each other (a port scan sends many identical probes). If one copy lands in training and another in test, the model gets "free" correct answers on test. A *group-aware* split puts all copies of the same feature vector on the same side. We used scikit-learn's `StratifiedGroupKFold` for this (source: `data/README.md`).

### 1.3.2 Overfitting {#bg-overfit}

**Analogy.** A student who memorises the answers to last year's paper word for word scores 100% on that paper and fails a new one. They learned the *paper*, not the *subject*.

A model **overfits** when it fits the quirks and noise of its training data so closely that it does worse on new data. Signs: training score keeps rising while validation score stalls or falls. Ways to fight it that we use: **dropout** (randomly switching off some neurons during training, so the model can't rely on any single one), **weight decay** (a small penalty for large weights), and **early stopping / best-by-validation selection** (keep the version that scored best on validation, not the last one).

### 1.3.3 What an MLP is {#bg-mlp}

**Analogy: a committee of committees.** Imagine 82 measurements of a flow are handed to a first committee of 128 people. Each person looks at all 82 numbers, weighs them in their own way, and writes down one opinion. Those 128 opinions go to a second committee of 64 people, who do the same. The 64 opinions go to a final panel of 9 judges, one per class, who each give a score for "this flow is my class."

That is a **multilayer perceptron (MLP)**: layers of "neurons", where each neuron computes a weighted sum of the previous layer's outputs and passes it through a simple bend (an *activation function*; we use ReLU, which just replaces negative numbers with zero). Training adjusts all the weights so the final scores point at the right class.

![Our MLP: 82 input features, hidden layers of 128 and 64 neurons, 9 output scores (one per class).](img/fig05_mlp.svg)

Our model's shape is **[128, 64]** with **19,849 parameters** in total (source: `configs/model.yaml`). That is tiny by modern standards, on purpose: every parameter has to travel between organizations and the server every round.

**Two extra pieces inside our MLP:**

- **Dropout 0.1**: during training, each neuron is switched off with probability 0.1 (source: `configs/model.yaml`).
- **LayerNorm**: rescales each layer's outputs to a standard range, computed fresh for each single example. We chose it over the more common BatchNorm because BatchNorm keeps running averages of the data it has seen; in federated learning those averages would come from very different organizations and averaging them makes no sense (source: `configs/model.yaml`). Chapter [2.2](#ch-model) has the details.

### 1.3.4 Softmax and confidence {#bg-softmax}

The final 9 scores the MLP produces are called **logits**. They can be any number, positive or negative. To turn them into something readable, we apply **softmax**:

**Plain version first.** Softmax turns a list of scores into a list of percentages that add up to 100%, where bigger scores get a much bigger share. It's like converting raw vote counts into vote shares, except softmax exaggerates the leader.

**Formula (after the plain version).** For logits z₁ … z₉, the probability of class i is

  p_i = e^(z_i) / (e^(z₁) + e^(z₂) + … + e^(z₉))

The predicted class is the one with the largest p_i, and that p_i is often called the model's **confidence**.

![Softmax turns 9 raw scores (logits) into 9 probabilities that sum to 1. Illustrative values, not from any model.](img/fig06_softmax.svg)

**A warning about confidence.** A softmax probability of 0.99 does *not* mean "right 99% of the time." Neural networks are often over-confident. On the dashboard we show confidence because analysts find it useful, not as a guarantee.

### 1.3.5 Macro-F1, and why we use it instead of accuracy {#bg-macro-f1}

**Why accuracy is misleading here.** In our cleaned data, Benign is about 75% of all flows (source: `data/README.md`). A "detector" that labels *everything* Benign is right about 75% of the time — and catches zero attacks. Accuracy rewards ignoring rare classes.

![Flows per family after cleaning. Benign dominates; Heartbleed and Infiltration are below the 1,000-flow floor. Log scale.](img/fig07_imbalance.svg)

**Precision, recall and F1, with a fishing analogy.** You cast a net to catch only salmon.

- **Precision** = of the fish you caught, what fraction are salmon? (Are your alarms trustworthy?)
- **Recall** = of all the salmon in the lake, what fraction did you catch? (Do you miss attacks?)
- **F1** = the *harmonic mean* of the two: F1 = 2 × precision × recall / (precision + recall). It is high only if *both* are high.

**Macro-F1** computes F1 separately for each class, then takes the plain average, so every class counts equally regardless of size. A model that ignores WebAttack (a small class) loses a whole 1/7 of its macro-F1 score, even though WebAttack is a tiny fraction of the flows.

**Our headline metric** is macro-F1 over the **7 headline classes** (Benign plus 6 attack families: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack). Infiltration and Heartbleed are below the 1,000-flow floor and are reported per class only (source: `configs/model.yaml`, `data/README.md`). The data record states it plainly: macro-F1 is the headline metric "and accuracy is never reported" (source: `data/README.md`).

### 1.3.6 Class imbalance and class weights {#bg-weights}

**Analogy.** A teacher marking a class of 100 where 75 students wrote about one topic and 1 student wrote about another. If every mistake costs the same, the teacher's marking scheme will be tuned to the 75. To be fair to the 1, you make their mistakes "cost more."

**Class weights** do exactly this: in the training loss, mistakes on rare classes are multiplied by a bigger weight. We use **effective-number** class weights with **β = 0.999** (source: `configs/model.yaml`). The idea (the "effective number of samples" idea, Cui et al. [to verify in lit review]) is that adding more examples of a class gives diminishing returns, so the weight of a class with n examples is proportional to (1 − β) / (1 − βⁿ). With β = 0.999, a class with very many examples is down-weighted heavily, and a class with few is not.

**Why not SMOTE (making synthetic minority examples)?** Our data record gives three reasons (source: `data/README.md`): SMOTE would have to run inside each organization, and at α=0.1 many organizations have too few minority examples to interpolate between; flow features are linked (rate = bytes ÷ duration) and interpolation breaks those links; and synthetic points would contaminate the explanation check, which is the project's central measurement.

## 1.4 Federated learning {#bg-fl}

### 1.4.1 The problem it solves {#bg-fl-problem}

**Analogy: a recipe club that can't share kitchens.** Ten restaurants want to create the best soup recipe together, but none will let the others into its kitchen or reveal its customers. So each restaurant tries the current recipe in its own kitchen, tweaks it, and sends *only the tweaked recipe* to a club coordinator. The coordinator blends the ten tweaked recipes into one new recipe and sends it back. Repeat. Nobody ever sees anyone else's ingredients or customers, but the club ends up with a recipe informed by all ten kitchens.

In federated learning (FL), the "recipe" is the model's weights, the "kitchens" are organizations with private data, and the "coordinator" is a server. Network traffic is sensitive (it reveals who talks to whom inside an organization), so it is a natural fit.

### 1.4.2 Clients and server {#bg-clients}

- **Clients** (we also say **silos** or **organizations**, "orgs" on the dashboard): each holds its own private data and trains a local copy of the model. We have **10**.
- **Server**: holds the global model, sends it out, collects updates, combines them. It never sees raw data.

"Cross-silo" FL means a small number of fairly reliable organizations (like ours), as opposed to "cross-device" FL with millions of phones.

### 1.4.3 Rounds and FedAvg {#bg-fedavg}

One **round** of training:

1. The server sends the current global model to every client.
2. Each client trains it on its own data for a few passes (we use **3 local epochs**).
3. Each client sends its updated weights back.
4. The server combines them into a new global model.

![One federated round. Only model weights travel; raw traffic never leaves an organization.](img/fig02_rounds.svg)

**FedAvg** (federated averaging, McMahan et al. [to verify in lit review]) is the standard way to combine: a **weighted average** of the clients' weights, where each client's weight is proportional to how many training examples it has. A client with twice the data counts twice as much.

Formula, after the plain version: if client k has n_k examples and weights w_k, the new global weights are

  w_new = Σ_k (n_k / N) · w_k, where N = Σ_k n_k.

We run **20 rounds** per training run, and keep the round whose global model scores best on validation ("best-by-validation round selection"), not simply the last one. [2.2](#ch-model) explains why that matters (the "round lottery").

### 1.4.4 What "non-IID" means {#bg-noniid}

**IID** means "independent and identically distributed": every client's data looks like a random sample of the same overall mix. **Non-IID** means the clients' data differ.

**Everyday example.** Ten hospitals train a shared disease detector. A children's hospital sees mostly childhood illnesses; a cancer centre sees mostly tumours; a rural clinic sees mostly injuries. Each hospital's local model becomes an expert in *its* patients. When you average them, the experts pull in different directions, and the average can be worse than any of them.

For network traffic this is realistic: a university network sees lots of port scans; a bank's network sees brute-force login attempts; a small company may see almost only normal traffic.

### 1.4.5 The Dirichlet α slider {#bg-alpha}

We need a *controlled* way to make clients more or less different. The standard tool is the **Dirichlet distribution**, controlled by one number, **α** (alpha).

**Plain version.** For each attack family (say, DDoS), we roll a special die that decides what share of the DDoS flows each of the 10 organizations gets. With a **small α**, the die is "lumpy": one or two organizations get almost all the DDoS flows and the rest get almost none. With a **large α**, the die is "smooth": every organization gets roughly 10%. We do this separately for every family.

- **α = 0.1**: pathological heterogeneity — a family lands almost entirely in one silo.
- **α = 0.5**: realistic heterogeneity.
- **α = 5.0**: near-IID control.

(source: `data/README.md`, §7)

![Real silo compositions for seed 42 at α=0.1 (top) and α=5.0 (bottom): flows per family in each of the 10 silos, shown as each silo's share. At α=0.1 most silos hold one or two families; at α=5.0 every silo looks like the global mix.](img/fig03_alpha.svg)

The **near-IID control** matters: without it, we couldn't tell whether a drop in accuracy is caused by *federation itself* or by *non-IID data*. Those are different claims (source: `data/README.md`).

How lumpy does it get? Out of 90 (silo, family) cells per configuration, the number left completely **empty** at seed 42 is 38 at α=0.1, 7 at α=0.5 and 3 at α=5.0 (source: `data/README.md`, §7).

**Formula (after the plain version).** For each family k, draw a proportion vector over the N=10 silos, p_k ~ Dir(α · 1_N); then p_k[i] is the fraction of family k's flows sent to silo i (source: `data/README.md`, §7).

### 1.4.6 FedProx and FedAvgM (server momentum) {#bg-fedprox}

Two well-known fixes for non-IID trouble appear in this project:

- **FedProx** (Li et al. [to verify in lit review]) adds a "leash" to local training: each client is penalised for drifting too far from the global model it received. The leash strength is **μ** (mu). Formula: the client minimises its usual loss + (μ/2)·‖w − w_global‖². Too strong a leash and nobody learns anything local; too weak and it does nothing. We test **μ = 0.0005** in the explanation check ([2.4](#ch-expl)).
- **FedAvgM** (Hsu et al., 2019) adds **momentum on the server**. Analogy: a heavy shopping trolley. Small pushes in random directions don't change its course much; consistent pushes build up speed. The server keeps a running "velocity" of how the global model has been moving, so noisy, conflicting updates from very different clients get smoothed. With momentum 0.9, the update rule is v ← 0.9·v + (w_old − w_avg), w_new = w_old − 1.0·v (source: `docs/preregistration_accuracy.md`, Part 2). This is the method our preregistered comparison selected ([2.6](#ch-prereg)). Note: the headline table writes it as "FedAvgM β=0.9"; β here is the same momentum value 0.9.

## 1.5 Explainable AI {#bg-xai}

### 1.5.1 What SHAP is — "sharing the bill" {#bg-shap}

**The question.** Our model says "this flow is DDoS." *Why?* Which of the 82 features pushed it there?

**Analogy: splitting a restaurant bill fairly.** Four friends share a meal and the bill is higher than the usual price of an empty table. How much of the *extra* did each person cause? It's tricky because orders interact (sharing a bottle of wine, a starter for two). The fair answer, proven by economist Lloyd Shapley, is: imagine the friends arriving in every possible order, see how much the bill goes up when each person sits down, and average that over all orders. Each person's average contribution is their **Shapley value**. The Shapley values always add up exactly to the extra amount on the bill.

**SHAP** (SHapley Additive exPlanations, Lundberg & Lee [to verify in lit review]) applies this to a model's prediction:

- the "bill" is the model's output for this flow;
- the "empty table price" is the model's average output (the **base value**);
- each "friend" is a feature;
- each feature's SHAP value is how much it pushed this prediction up or down from the average.

![The SHAP "bill" for one prediction: start at the base value, each feature adds or subtracts, and the total lands on the model's output. Illustrative values, not from any model.](img/fig08_shap_bill.svg)

A large positive SHAP value for `Flow Packets/s` means "this feature pushed the model strongly towards DDoS for this flow." Ranking features by the *size* (absolute value) of their SHAP values gives a **top-k list**: the k features that mattered most.

### 1.5.2 Base value and logits {#bg-base}

- The **base value** (also written E[f]) is the model's average output over a **background** set of example rows. It's the "starting point" before we know anything about this particular flow. We use a fixed, seeded background of rows drawn from each silo's own training data (locked decision 4: 100–200 rows per silo; source: `CLAUDE.md`).
- We explain the model's **logits** (the raw scores before softmax, [1.3.4](#bg-softmax)), one set of SHAP values per class. Logits are used because they add up cleanly; probabilities after softmax don't.
- For comparing explanations we use the SHAP vector of the **true class** of each row ("ground-truth anchoring"), so two models are always compared on "how does your output support the correct answer" (source: `docs/measurement_protocol.md` §3).

### 1.5.3 Additivity and the residual {#bg-additivity}

**Additivity** is SHAP's promise that the pieces add up: base value + sum of all SHAP values = the model's actual output. In formula form, for class c: Σ_f SHAP[f, c] = f(x)_c − E[f]_c.

In practice the SHAP software *estimates* the values by sampling, so the sum is a little off. The gap is the **additivity residual**:

  residual = | Σ SHAP − (f(x) − E[f]) |

Think of it as a rounding error in the bill-splitting: the shares add up to almost, but not exactly, the bill. A small residual means the explanation is internally consistent; a large residual means the explanation for that row should be treated with caution. We measured and disclosed it ([2.4](#ch-expl), [3.2](#audits)).

### 1.5.4 GradientExplainer vs DeepExplainer {#bg-explainers}

The SHAP library offers several ways to estimate SHAP values for neural networks:

- **DeepExplainer** uses a fast rule-based shortcut (DeepLIFT). It is exact for some layer types but not for all. On our model it **failed on the LayerNorm layers**: additivity error 2.43 against a 0.01 tolerance (source: `CLAUDE.md`, "Findings that limit what can be claimed").
- **GradientExplainer** (expected gradients) averages gradients along paths between background rows and the input. It works with any differentiable layer, including LayerNorm, at the cost of sampling noise. We use it with `nsamples=4000` for headline numbers (source: `docs/contribution_a_results.md` §3).
- **KernelExplainer** is model-agnostic and slow; we used it only as a cross-check ([2.4](#ch-expl)).

So GradientExplainer was chosen because a test showed DeepExplainer fails on our architecture — not by default.

## 1.6 Comparing explanations {#bg-compare}

### 1.6.1 Top-k lists {#bg-topk}

After SHAP, each model has a ranking of 82 features for each explained flow. We keep the **top 10** (k = 10) by absolute SHAP value. The question becomes: do two models put the same features in their top 10?

### 1.6.2 Jaccard@10 {#bg-jaccard}

**Plain version.** Put the two top-10 lists side by side. Count the features that appear in both (the overlap). Divide by the number of different features that appear in at least one list (the union). 1 means identical sets; 0 means nothing in common. Order inside the top 10 doesn't matter.

**Worked example (made-up lists).** If 7 features are in both lists, the overlap is 7 and the union is 10 + 10 − 7 = 13, so Jaccard@10 = 7/13 ≈ 0.538.

![Two made-up top-10 lists. 7 features are shared; the union has 13; Jaccard@10 = 7/13.](img/fig09_jaccard.svg)

**Formula.** J(A, B) = |A ∩ B| / |A ∪ B|.

Notice how unforgiving it is: sharing 5 of 10 features gives only 5/15 ≈ 0.333.

### 1.6.3 Weighted Kendall's τ {#bg-tau}

Jaccard ignores order and everything outside the top 10. **Kendall's τ** (tau) looks at the *whole* ranking. Plain version: take every pair of features and ask "do both models put these two in the same order?" τ is (agreeing pairs − disagreeing pairs) / all pairs, so +1 is identical order, 0 is unrelated, −1 is reversed.

**Weighted** τ (we use `scipy.stats.weightedtau`) gives more weight to pairs involving important features, so disagreements among the 60 features that nobody cares about don't swamp agreement on the ones that matter (source: `docs/measurement_protocol.md` §6).

**Why both?** Two models can share the same top 10 in a different order (high Jaccard, lower τ), or agree on the overall order but differ on the exact top 10 (lower Jaccard, high τ). Reporting both catches both cases (source: `docs/measurement_protocol.md` §6).

### 1.6.4 Chance level {#bg-chance}

**Plain version.** If two "models" picked their top 10 *completely at random* from 82 features, how much would they overlap by luck? Not zero — on average k²/n features (k = 10, n = 82) land in both lists by luck. Turned into a Jaccard value, that is **0.065** (source: `docs/measurement_protocol.md` §4). Any real agreement must be compared with this, not with 0.

**Formula.** E[|A∩B|] = k²/n and E[|A∪B|] = 2k − k²/n; chance Jaccard is their ratio, with k = 10 and n = 82 (source: `docs/measurement_protocol.md` §4).

### 1.6.5 A "null control" / seed-noise floor, and why it matters {#bg-floor}

**The problem.** Neural network training is random: the starting weights and the order of examples depend on a **random seed**. Train the *same* model on the *same* data twice with different seeds, and you get two slightly different models — and their SHAP top-10 lists will differ a bit too. So when a federated silo's explanation differs from the global model's, how much of that difference is caused by federation and heterogeneity, and how much would have happened anyway, just from the seed?

**Analogy.** Two judges at a talent show give different scores. Before concluding "they have different taste," check how much *the same judge* varies when shown the same act twice. That self-variation is the noise floor.

**Our null control.** Train three centralized models (no federation at all), identical except for seed (42, 1337, 2024). Explain the same 14 rows with each. Measure Jaccard@10 between every pair. The median is the **centralized-seed instability floor**: the agreement you get from seed noise alone. Ours is median 0.429, range [0.429, 0.484] (source: `results/inspection/centralized_instability_floor.csv`).

A federated agreement number above the floor shows something beyond seed noise. A number *below* the floor means the silos agree with the global model *less* than two re-runs of the same centralized model agree with each other. Without this floor, a number like "Jaccard@10 = 0.53" has nothing to be compared against. The project treats this null control as its **headline methodological contribution** (source: `docs/contribution_a_results.md` §1).

![The two reference lines: chance level (0.065) and the seed-noise floor (median 0.429, range [0.429, 0.484]).](img/fig10_numberline.svg)

## 1.7 Poisoning and Byzantine attacks {#bg-poison}

### 1.7.1 Label flipping {#bg-labelflip}

In FL the server can't see clients' data, so a dishonest client can train on bad data and send a harmful update. This is **data poisoning**. The simplest form is **label flipping**: the client keeps its traffic but changes some labels.

Our attack is **targeted to Benign**: a malicious silo relabels a fraction of its *attack* flows as "Benign" before training. The goal of such an attacker is a shared model that waves attacks through. We flip **40%** of eligible rows (`flip_fraction: 0.40`) (source: `docs/contribution_b_results.md` §2). Only non-Benign rows can be flipped, so a silo with very little attack traffic is mechanically a weak attacker — this detail matters later.

Two timing modes: **sudden** (40% from round 1) and **gradual** (starts at 5% and ramps up by 5 points per round, reaching 100% at round 20) (source: `docs/contribution_b_results.md` §2).

### 1.7.2 "Byzantine" clients and "f" attackers {#bg-byzantine}

The name comes from the "Byzantine generals" problem in computer science: some generals may be traitors sending false messages, and the loyal ones must still agree. A **Byzantine client** is one that may send *any* update, possibly malicious. **f** is the number of attackers. We test **f = 3** (silos {0, 3, 5}) and **f = 2** (silos {0, 3}) out of 10 (source: `docs/contribution_b_results.md` §2).

### 1.7.3 Krum, Multi-Krum and trimmed mean {#bg-krum}

These are classic **robust aggregation** rules — replacements for FedAvg designed to resist bad updates.

**Krum** (Blanchard et al.; the year is not recorded in our docs [to verify in lit review]). Plain version: each update is a point in a huge space. Honest updates should cluster together; attackers should sit apart. For each update, add up its squared distances to its *n − f − 2* nearest neighbours. The update with the smallest total is the most "central"; **Krum ships that one update alone** as the next global model.

![How Krum picks: each client's update is a point; Krum scores each by distance to its nearest neighbours and keeps the single most central one. Schematic.](img/fig11_krum.svg)

**Multi-Krum** repeats the Krum selection to keep the **n − f** most central updates and averages them. So it drops exactly f updates per round.

**Coordinate-wise trimmed mean** (Yin et al. [to verify in lit review]). Plain version: for every single weight, line up the 10 clients' values, throw away the highest and lowest few, and average the rest. Like Olympic judging, where the highest and lowest scores are discarded. The trim fraction is **β** (beta); we set β = f / n (0.3 at f=3, 0.2 at f=2) (source: `docs/contribution_b_results.md` §4).

![Multi-Krum drops whole clients; trimmed mean drops extreme values one coordinate at a time. Schematic.](img/fig12_multikrum_trim.svg)

**A trap for non-IID data.** All three rules assume "unusual = malicious." But under non-IID data, an honest organization with an unusual mix of traffic *also* looks unusual. That is exactly the problem our trust check runs into ([2.5](#ch-trust)).

### 1.7.4 What an "oracle attacker count" means {#bg-oracle}

Krum, Multi-Krum and trimmed mean all need to be told **f**, the number of attackers, in advance. In real life nobody knows that. We gave these baselines the **true f** — an "oracle," as if someone whispered the answer. This is a **deliberate advantage** for the baselines. ByzAgent was given neither f nor anything else privileged (source: `docs/contribution_b_results.md` §1). Every ByzAgent-vs-baseline comparison must say this.

## 1.8 LLM agents {#bg-llm}

**What an LLM is.** A large language model is a neural network trained on huge amounts of text to predict the next word. Given a prompt, it writes a continuation. Instruction-tuned models (like ours) have been further trained to follow instructions and produce structured answers such as JSON.

**What an "agent" means here.** Our use is modest: each round, the server writes a prompt containing five numbers per organization, the LLM returns a JSON decision (trust / downweight / quarantine) plus a short written rationale per organization. That is all. It does not browse, plan, or take other actions.

**Why local (Ollama, llama3.1:8b).** We run **`llama3.1:8b-instruct-q4_K_M`** through **Ollama** on our own laptop (source: `configs/agent.yaml`). Reasons:

- *Privacy*: the whole point of FL is that organizations' information stays put; sending their behaviour statistics to a cloud API would undercut that.
- *Hardware*: "8b" means 8 billion parameters; "q4_K_M" means 4-bit quantized, so it fits the 6 GB GPU (~4.8 GB resident, source: `configs/agent.yaml`).
- *Reproducibility and cost*: a fixed local model version, no API changes, no fees.
- *Chosen by test*: three local models were compared; only llama3.1 combined valid JSON, correct client IDs and explanations citing real numbers ([2.5](#ch-trust)).

**Nondeterminism.** An LLM picks each next word by sampling from probabilities. With **temperature 0.2** (source: `configs/agent.yaml`) it is fairly but not fully predictable: send the same prompt twice and you may get a slightly different answer. So we never report one LLM decision as "the" answer; we report **decision stability** — how often repeated calls agree ([2.5](#ch-trust)).

**Why trust an LLM at all?** We don't, blindly. We audit it: we check whether the numbers it cites are real and correctly described, and whether its decisions actually track the statistics. That audit is why our locked wording is that ByzAgent **"produces decisions plus a rationale of measured fidelity"** — never that it "understands" or reasons reliably.

## 1.9 Statistics we used {#bg-stats}

### 1.9.1 Mean ± sd over seeds {#bg-meansd}

We repeat every federated configuration with 3 seeds. We report the **mean** and the **standard deviation (sd)** across those 3 runs, e.g. 0.941 ± 0.057 (source: `results/aggregated/federated_headline.csv`). The sd tells you how much results swing just from randomness. Our headline tables use the *population* sd (dividing by n, not n − 1) (source: `docs/preregistration_accuracy.md`, Part 2). With n = 3, treat the sd as a rough indication, not a precise number.

### 1.9.2 Median and IQR {#bg-median}

The **median** is the middle value when sorted; unlike the mean, one extreme value can't drag it around. The **IQR** (interquartile range) is the spread of the middle half of the data (75th percentile minus 25th). We use medians for the headline agreement numbers because per-row Jaccard values are lumpy and skewed (source: `docs/contribution_a_results.md` §2).

### 1.9.3 Cluster bootstrap confidence intervals {#bg-bootstrap}

**Bootstrap, plain version.** You have one sample and want to know how much a statistic would wobble if you had collected a different sample. Trick: create many fake samples by drawing from your own data *with replacement*, recompute the statistic each time, and look at the spread. The middle 95% of those values is a **95% confidence interval (CI)**.

**Cluster bootstrap.** Our rows are not independent: many rows come from the same silo and the same run. Resampling individual rows would pretend we have more independent evidence than we do. A **cluster** bootstrap resamples whole groups (clusters) instead of single rows, which gives wider, more honest intervals. Our α=0.1 interval is [0.250, 0.429] against the floor range [0.429, 0.484] (source: `CLAUDE.md`, "Findings that limit what can be claimed"). Because they touch at 0.429, we say the below-floor result is **directional, not significant**.

### 1.9.4 Spearman and partial correlation {#bg-corr}

- **Correlation (r)** measures how strongly two quantities move together, from −1 to +1.
- **Spearman** correlation works on *ranks* rather than raw values, so it captures any consistently increasing or decreasing relationship and isn't thrown off by outliers.
- **Partial correlation** asks: do X and Y still move together *after removing the part of both that is explained by Z*? Analogy: ice-cream sales and drownings are correlated, but both are driven by hot weather. Control for temperature and the correlation disappears. We use partial correlation to ask whether label skew predicts explanation agreement *after controlling for silo size* ([2.4](#ch-expl)).

### 1.9.5 Effect size {#bg-effect}

A **p-value** says how surprising a result would be if nothing were going on; an **effect size** says *how big* the difference is. For the trust check we use **Glass's delta**: (mean of malicious silos − mean of clean silos) ÷ (standard deviation of the clean silos) (source: `docs/contribution_b_results.md` §3). "Big" here means "many clean-silo standard deviations apart."

### 1.9.6 Why we report r and n, with no p-values {#bg-nopvalue}

A p-value assumes every data point is an independent observation. Our silos are **not independent**: all 10 silos in one run share the same global model trajectory. Treating 30 silos as 30 independent points would overstate the evidence; the number of truly independent units is closer to the number of seeds (3) (source: `docs/contribution_a_results.md`, Limitations #18). A p-value computed as if n were 30 would look more convincing than the evidence deserves. So we report the correlation **r** and the count **n**, and let readers judge. This is a deliberate project rule (source: `CLAUDE.md`).

### 1.9.7 Pre-registration {#bg-prereg}

**Analogy: the sealed envelope.** Before a match, you write your prediction and the rule for judging it, seal it in an envelope, and hand it to a friend. After the match, you open it. Nobody can accuse you of changing your story after seeing the result.

**Pre-registration** in research means writing down, *before* looking at the data, exactly what you will compare, how you will decide, and what counts as success — and committing it publicly (for us, to git, with a timestamp). We used it twice: for the rolling-history test in the trust check ([2.5](#ch-trust)) and for the accuracy-improvement experiment ([2.6](#ch-prereg)). It protects against the most common way honest people fool themselves: choosing the analysis after seeing which one looks best.

## 1.10 Self-check: could a non-ML friend follow this? {#bg-check}

We re-read Part 1 asking one question per section: could a friend who has never studied ML explain it back? The rewrites made after that check:

- Every term now has an everyday analogy *before* its formula (exam paper, committee, fishing net, recipe club, restaurant bill, talent-show judge, Olympic judging, sealed envelope).
- The Jaccard example uses a picture with countable features, so the 7/13 can be checked by eye.
- "Logit", "base value" and "residual" are each introduced with the bill analogy, rather than with symbols.
- Dirichlet α is explained as a "lumpy vs smooth die," with a picture made from our real partition files.
- Remaining hard spots, flagged honestly: weighted Kendall's τ and the cluster bootstrap are the two ideas that need a second read. For an exam answer, the one-sentence versions are enough: "τ asks whether two rankings put pairs of features in the same order, giving more weight to important features," and "a cluster bootstrap estimates uncertainty by resampling whole silos rather than single rows, because rows from one silo are not independent."
