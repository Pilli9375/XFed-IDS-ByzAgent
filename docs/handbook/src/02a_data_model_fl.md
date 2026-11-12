# Part 2 — The system, stage by stage {#part-2}

Each chapter follows the same eight sections, so you always know where to look: **In one line · Why this exists · How it works · What we actually did · What we found · What this does NOT mean · Where it lives in the code · Questions an examiner might ask.**

## 2.1 Data {#ch-data}

### In one line

We took the corrected Distrinet CICIDS2017 V4 dataset, cleaned 2,099,976 raw flows down to 1,913,502, mapped 14 raw labels into 8 attack families plus Benign, split it once into train and test without letting duplicates leak across, and locked the federated partitions with SHA256 hashes (source: `data/README.md`).

### Why this exists

Every later number depends on the data being right. CICIDS2017 is one of the most used IDS datasets, and also one of the most criticised: published studies found mislabelled flows, broken flow construction and duplicated captures in the original release. A model trained on bad labels learns bad lessons, and a split that lets duplicate rows straddle train and test inflates every score. This stage exists to make the data trustworthy *and* to record every cleaning decision with its row count, so anyone can check it.

### How it works

![From raw flows to the cleaned dataset. Row counts at each stage.](img/fig19_funnel.svg)

1. **Load** the five per-day CSV files (Monday to Friday of the lab capture). 2,099,976 flows, 91 columns: 7 identifiers, `Label`, `Attempted Category`, and 82 candidate features (source: `data/README.md` §1).
2. **Drop identifiers** (`id`, `Flow ID`, `Src IP`, `Src Port`, `Dst IP`, `Dst Port`, `Timestamp`) so the model learns behaviour, not addresses.
3. **Map labels to families** (raw label → family), *before* any other cleaning step.
4. **Remove non-finite values** (infinities).
5. **Remove family conflicts**: groups of rows with identical features but different families.
6. **Remove cross-day duplicates**.
7. **Split** once, globally, group-aware, 75/25 train/test.
8. **Carve validation** out of the training pool (10%, also group-aware).
9. **Partition** the training pool into 10 silos with a Dirichlet draw, for each (α, seed), and store the row→silo assignment with a SHA256 hash.

**Analogy for the order of steps.** Sorting laundry: you first decide which pile each item belongs to (family mapping), *then* you look for items that are identical but in different piles (conflicts). If you looked for conflicts first, using the original tags, you'd wrongly treat a "navy sock" and a "dark-blue sock" as a conflict even though both go in the "socks" pile. That exact bug happened once and was fixed (see below).

### What we actually did

**Dataset: Distrinet CICIDS2017 V4, not the original.** The lineage has two papers, and both are cited (source: `data/README.md` §1):

- Engelen, Rimmer & Joosen (WTMC 2021) found errors in traffic generation, flow construction, feature extraction and labelling, fixed CICFlowMeter, and introduced the `X - Attempted` label convention.
- Liu, Engelen, Lynar, Essam & Joosen (IEEE CNS 2022) found further errors and released the refined version 4, which we use.
- *Rejected:* the original CIC release (known errors). *Not used:* a third correction branch by Lanvin et al. (CRiSIS 2022), which addresses different issues (source: `data/README.md` §1).

**"Attempted" flows join their parent family.** A flow labelled `X - Attempted` belongs to attack class X but carried no payload — the attack was launched but didn't land. The initial plan was to fold these into Benign, as Engelen et al.'s own benchmark does. The counts overturned it: for some families most flows are Attempted (Web Attack – XSS 97%, Web Attack – Brute Force 95%, Botnet 85%) (source: `data/README.md` §2). Folding them into Benign would have wiped out most of Bot and WebAttack. *Cost, stated:* the model learns to alert on failed attempts too, so per-family scores mix completed and attempted attacks.

**14 raw labels → 8 families + Benign** (source: `data/README.md` §3):

| Family | Raw labels folded in |
|---|---|
| Benign | BENIGN |
| DoS | DoS Hulk, DoS GoldenEye, DoS Slowloris, DoS Slowhttptest (+ Attempted) |
| DDoS | DDoS |
| PortScan | Portscan, Infiltration - Portscan |
| BruteForce | FTP-Patator, SSH-Patator (+ Attempted) |
| WebAttack | Web Attack Brute Force / XSS / SQL Injection (+ Attempted) |
| Bot | Botnet (+ Attempted) |
| Infiltration | Infiltration (+ Attempted) |
| Heartbleed | Heartbleed |

**`Infiltration - Portscan` goes to PortScan.** 67,072 raw flows (source: `data/README.md` §3). By name it is part of the infiltration scenario; by feature signature (short flows, few bytes, many probes) it is a port scan. Routing it to Infiltration would make that family over 99.9% scan-shaped, and every "Infiltration" explanation would really explain a port scan. *Cost:* Infiltration drops to 66 flows, below the floor. Accepted deliberately.

**The 1,000-flow floor.** Families below 1,000 flows are **kept in the data**, **reported per class**, but **excluded from headline macro-F1**: Infiltration (66) and Heartbleed (11) (source: `data/README.md` §3). With 11 examples, a macro-F1 that includes Heartbleed would swing wildly from one flow being right or wrong.

**Cleaning, with every count** (source: `data/README.md` §4.5):

| Stage | Rows removed |
|---|---:|
| Start | 2,099,976 |
| Inf / NaN | −5 |
| Family conflicts | −44,005 |
| Cross-file duplicates | −142,464 |
| **Retained** | **1,913,502** (8.88% dropped) |

- **Inf/NaN:** exactly 5 flows with `Flow Duration == 0` produce infinite rates (both rate columns divide by duration). The ICMP columns hold −1 for non-ICMP flows; that's CICFlowMeter's "not applicable" code, not corruption, so it was left alone (source: `data/README.md` §4.1).
- **Family conflicts:** 43,890 rows in Benign|PortScan groups and 115 in Bot|Infiltration groups (source: `data/README.md` §4.2). Even in the corrected dataset, ~43,890 flows are feature-identical to traffic of another family once identifiers are removed. No model can separate identical inputs with different labels; this is a ceiling set by the 82-feature space, and it is reported as a limitation.
- **The conflict bug that was caught.** An earlier version checked conflicts on the *raw* label and destroyed 58,307 rows where `Infiltration - Portscan` and `Portscan` "conflicted," although both map to PortScan (source: `data/README.md` §4.2). It didn't crash; it produced plausible output for a full cycle. It was caught only by logging *which* combinations conflicted.
- **Duplicates: drop only across days.** The raw exact-duplicate rate is 18.3%, almost all in scans and bots (Portscan 99.2% of its rows sit in duplicate groups) (source: `data/README.md` §4.3). A port scan sends many identical probes that differ only in port number — a column we dropped. These are distinct events that *look* identical, not one event recorded twice. So duplicates are dropped only when a group spans **more than one day-file**, which matches the capture-overlap problems documented in the correction papers. The dedup key is the raw label (provenance), on purpose different from the conflict key (family).
- **Near-constant features kept.** 8 of 82 features have one value covering ≥99.9% of rows, but none is strictly constant; `ICMP Type`/`Code` are the only features that could describe an ICMP attack. **All 82 features retained** (source: `data/README.md` §4.4).

**Final family distribution** (source: `data/README.md` §5):

| Family | Flows | Below floor |
|---|---:|:---:|
| Benign | 1,440,899 | |
| PortScan | 186,160 | |
| DoS | 177,491 | |
| DDoS | 95,144 | |
| BruteForce | 6,972 | |
| Bot | 4,703 | |
| WebAttack | 2,056 | |
| Infiltration | 66 | ✓ |
| Heartbleed | 11 | ✓ |

**Group-aware, global split, before partitioning.** After cleaning, 213,752 rows still share a feature vector with at least one other row (1,714,074 distinct vectors among 1,913,502 rows) (source: `data/README.md` §6). A random split would put copies on both sides. Deleting them would strip most of PortScan. Instead, every distinct feature vector is a **group**, and `StratifiedGroupKFold` keeps each group on one side. The pipeline *verifies* this and raises an error if any vector appears on both sides. Result: 1,435,126 train / 478,376 test (25.0%), with every headline family at exactly 25.0% in test (source: `data/README.md` §6). The split is done **once, before federation**, so the centralized and federated models are scored on the identical test set.

**Validation.** A 10% group-aware validation mask is carved from the training pool (`val_fraction: 0.10`, seed 42; source: `configs/model.yaml`), giving the 143,513-row centralized validation set used for every model and round selection (source: `docs/efficiency_results.md`).

**Partitions on disk, with a SHA256 manifest.** For each of the 9 (α, seed) configurations the pipeline writes the **row → silo assignment** (about 2 MB) rather than 90 copies of the data. The manifest stores a SHA256 hash of the assignment array itself, and `load_silo()` recomputes and checks it every time a silo is loaded; it was verified to detect a single flipped value among 1.4M entries (source: `data/README.md` §7). Analogy: a tamper seal on a medicine bottle — if anything changed, you know before you use it.

**Leakage controls, summarised** (source: `data/README.md` §8): scalers fit per silo on that silo's train rows only; group-aware split, verified; dedup before partitioning; manifest hash checked at load; SHAP background drawn from training rows only; floor exclusions decided once from pooled counts.

### What we found

- 8.88% of raw rows were removed, each removal step with its own count (source: `data/README.md` §4.5).
- Benign is 75% of the data; Heartbleed is 0.0006% (source: `data/README.md` §5). This drives the choice of macro-F1 and class weights.
- The partitions behave as intended: empty (silo, family) cells at seed 42 fall from 38 (α=0.1) to 7 (α=0.5) to 3 (α=5.0), and the mean largest single-silo share of a family falls from 0.694 to 0.372 to 0.177, against a uniform ideal of 0.100 (source: `data/README.md` §7).
- At α=0.1, silo sizes range from about 143 rows to about 636,676 (source: `data/README.md` §7).

### What this does NOT mean

- It does not mean CICIDS2017 V4 is *perfect*. 43,890 Benign/PortScan flows were indistinguishable by features and had to be dropped; this is a limit of the feature space.
- It does not mean our results transfer to real enterprise traffic. CICIDS2017 is a lab capture over five days.
- Per-family scores mix completed and attempted attacks, by design.
- Even at α=5.0 some cells are empty: Heartbleed has 8 training flows and cannot occupy 10 silos (source: `data/README.md` §7).

### Where it lives in the code

| File | What it does |
|---|---|
| `configs/data.yaml` | Every data parameter, including `family_map` and the floor |
| `src/data/clean.py` | Load → map → Inf/NaN → conflicts → dedup → `clean.parquet` |
| `src/data/mapping.py` | Raw label → family; raises on any unmapped label |
| `src/data/families.py` | Global group-aware split → `train_pool.parquet`, `test_global.parquet` |
| `scripts/make_val_split.py` | Group-aware 10% validation mask |
| `src/data/partition.py` | Dirichlet partitioning, manifest, `load_silo()` with hash check |
| `scripts/check_partitions.py` | Pre-flight check for silos that would crash a round |
| `data/README.md` | The decision record this chapter is built from |

### Questions an examiner might ask

_Numbers in these model answers repeat numbers already given with their source earlier in this chapter; the source notes are not repeated here._

**Q: Why not use the original CICIDS2017 like most papers?**
A: The original release has documented errors in flow construction and labelling. Engelen et al. (WTMC 2021) and Liu et al. (IEEE CNS 2022) corrected them; we use the V4 release from the second paper and cite both.

**Q: Why did you put "Attempted" attacks in the attack families instead of Benign?**
A: Because for Web Attack – XSS, Web Attack – Brute Force and Botnet, 85–97% of the flows are Attempted. Folding them into Benign would have nearly erased those families. The cost is that per-family scores mix failed and successful attacks; we state it.

**Q: You dropped 142,464 duplicates. Isn't duplication normal for scans?**
A: Yes, so we did *not* drop same-day duplicates — a scan's identical probes are distinct events. We only dropped groups spanning more than one day-file, which match the capture-overlap problems the correction papers describe.

**Q: How do you know duplicates didn't leak between train and test?**
A: Every distinct feature vector is a group, and `StratifiedGroupKFold` keeps groups on one side. The script doesn't trust the library: it checks and raises if any vector appears on both sides.

**Q: Why exclude Infiltration and Heartbleed from the headline?**
A: They have 66 and 11 flows. One flow right or wrong would move a headline average noticeably. They stay in the data and are reported per class.

**Q: What does the SHA256 manifest protect against?**
A: Silently training on a different partition than the one reported — for example, if a code change regenerated it. The hash is over the assignment array, checked every time a silo loads, and was verified to catch one flipped value in 1.4M.

**Q: Did any cleaning bug affect results?**
A: Two were caught *before* results: conflict detection on raw labels (would have destroyed 58,307 learnable rows) and dedup keyed on family (would have deleted 58,228 rows). Both are recorded in `data/README.md`.

---

## 2.2 Model and training {#ch-model}

### In one line

A small MLP ([128, 64], 19,849 parameters, LayerNorm, dropout 0.1) with StandardScaler inputs and effective-number class weights (β=0.999), trained with AdamW, where the reported version of every federated run is the round with the best *validation* score (source: `configs/model.yaml`).

### Why this exists

The explanation check and trust check both need one trustworthy model to study. If the model were poorly configured, every later finding could be blamed on it. So each setting was chosen by a small experiment (a "pilot") rather than by habit, and the reason for each is written in `configs/model.yaml` next to the value.

### How it works

- **Input:** 82 features, each standardised (mean 0, standard deviation 1) using a scaler fitted on the silo's own training rows.
- **Network:** 82 → 128 → 64 → 9, ReLU activations, LayerNorm, dropout 0.1.
- **Loss:** cross-entropy weighted by effective-number class weights (β=0.999), the *same* 9 weights for every silo.
- **Optimizer:** AdamW, learning rate 1.0e-3, weight decay 1.0e-4, batch size 1024 (source: `configs/model.yaml`).
- **Labels:** a **frozen 9-wide vocabulary** (Benign=0 … WebAttack=8), never derived from a silo's own rows (source: `configs/model.yaml`). If a silo has no Heartbleed flows, its model still has a Heartbleed output; otherwise silos' outputs wouldn't line up and couldn't be averaged.

### What we actually did

| Choice | Why | Rejected alternative, and why |
|---|---|---|
| **StandardScaler** | RobustScaler degenerates on 28 of 82 zero-inflated features (their IQR is 0, so it only centres them and leaves them unscaled); StandardScaler degenerates on just 1 (`Bwd URG Flags`, all zero) (source: `configs/model.yaml`) | RobustScaler, robust-with-clipping |
| **Effective-number class weights, β=0.999** | Best on validation macro-F1 (0.9941) in the weights pilot (source: `configs/model.yaml`) | none, inverse-sqrt, β=0.9999, β=0.99999. Larger β over-corrected: Infiltration precision fell from 0.92 to 0.12 between β=0.999 and 0.99999 (source: `configs/model.yaml`) |
| **MLP [128, 64]** | The top 4 architectures were within 0.0008 validation macro-F1 of each other, less than epoch-to-epoch noise. So the tie-breaker was size: 19,849 parameters vs 56,073 ([256,128]) vs 209,673 ([512,256,128]) — 3.7× and 10.6× less to send every round (source: `configs/model.yaml`) | Bigger models: no measurable gain; the largest also showed a one-epoch instability (validation macro-F1 0.988 → 0.881) |
| **Dropout 0.1** | Direction vs 0.3 flips with model size; inside noise (source: `configs/model.yaml`) | 0.3 |
| **LayerNorm, not BatchNorm** | BatchNorm stores running statistics of the data it saw. In FL those statistics come from incompatible per-silo distributions, and FedAvg would average them meaninglessly (source: `configs/model.yaml`) | BatchNorm |
| **3 local epochs** | Re-checked on validation: 3 epochs beat 1 at α=0.5 in all three seeds, mean best-by-validation macro-F1 0.9425 vs 0.8602 (source: `results/federated/epochs_provenance_val.json`, `docs/test_set_exposure_audit.md` §2) | 1 epoch |
| **Frozen 9-wide label vocabulary** | Every silo's output layer means the same thing | Per-silo label sets |
| **Global fixed class weights** | If each silo computed its own weights, each would minimise a different loss, and FedAvg would average models optimising different objectives (source: `scripts/export_class_weights.py` docstring) | Per-silo weights |
| **Best-by-validation round selection** | See "the round lottery" below | Reporting round 20 |

**Honest note on three of these choices.** Three early choices were *recorded* with test-set numbers as their justification: 3 local epochs, FedProx μ=0.0005 and StandardScaler. Re-checked on validation, the same μ and scaler are selected; for local epochs, validation also selects 3 over 1 at α=0.5 in all three seeds (source: `CLAUDE.md`, "Test-set use"). Part 3 tells the full story.

**Honest note on the class weights.** The 9 global weights are computed once from the pooled (centralized) training counts and given to every silo (source: `scripts/export_class_weights.py`). In a real deployment those counts would need to be shared or estimated; in our simulation it is a simplification we state.

**Best-by-validation round selection and the round lottery.** A federated run lasts 20 rounds. The global model's quality jumps around from round to round under non-IID data, because each round's average is pulled by very different clients. If you report "whatever round 20 happened to be," you are entering a lottery.

![The round lottery, real data: validation macro-F1 per round for FedAvg at α=5.0, seed 42. Best round 18; round 20 is 0.118 lower.](img/fig13_round_lottery.svg)

The largest gap between the best-by-validation round and round 20 is **0.118** (α=5.0, seed 42, validation macro-F1: best 0.9898 at round 18 vs 0.8713 at round 20) (source: `results/federated/round_lottery_val.csv`). So **every reported number uses the validation-selected round.** Analogy: if you're picking a player for the final, you choose on their best form in practice matches, not on whatever the last practice happened to be.

*Kept as a record:* the lottery was first measured with test scores (a round-20 test score of the unselected checkpoint), with a maximum of 0.1199 (α=0.5, seed 1337); that test-based version is superseded by the validation-only one (source: `docs/contribution_a_results.md`, Limitations #1).

### What we found

- Centralized MLP macro-F1: **0.9900 ± 0.0022** over 3 seeds (source: `results/aggregated/centralized_headline.csv`).
- XGBoost (a strong non-neural reference): **0.9946 ± 0.0001** (source: `results/aggregated/xgboost_headline.csv`).
- The served demo model, `fedavg_a0.5_s42`, is round 18 with validation macro-F1 **0.9760** (source: `results/federated/fedavg_a0.5_s42/final_metrics.json`).

### What this does NOT mean

- The pilots were small: a handful of arms each, centralized, on one seed family. They show the chosen settings are reasonable, not optimal.
- XGBoost being slightly higher does not make it the right model here: tree ensembles don't average across clients the way neural network weights do, and SHAP on an MLP is what the explanation check needs. XGBoost is a reference line, not a competitor.
- The round lottery means a single federated run's "last round" number is unreliable; it does not mean federated training is broken.

### Where it lives in the code

| File | What it does |
|---|---|
| `configs/model.yaml` | Every model and training setting, with the reason next to each lock |
| `src/models/` | The MLP definition |
| `src/train/centralized.py` | Centralized training (baselines, pilots) |
| `src/train/xgboost_baseline.py`, `scripts/tune_xgboost.py` | XGBoost reference (tuning early-stops on validation) |
| `scripts/run_pilots.py` | Scaler, class-weight and architecture pilots |
| `scripts/export_class_weights.py` | Writes `configs/global_class_weights.json` once |
| `results/aggregated/*_headline.csv` | Headline tables |
| `results/federated/round_lottery_val.csv` | The validation-only round lottery |

### Questions an examiner might ask

_Numbers in these model answers repeat numbers already given with their source earlier in this chapter; the source notes are not repeated here._

**Q: Why such a small model?**
A: The top four architectures scored within 0.0008 of each other on validation, so extra capacity bought nothing measurable. The smallest has 19,849 parameters, 3.7× and 10.6× fewer than the next two — and every parameter travels every round.

**Q: Why LayerNorm instead of BatchNorm?**
A: BatchNorm keeps running statistics of its input data. Averaging those across organizations with very different traffic is meaningless. LayerNorm normalises each example on its own and has no such state.

**Q: Why not just report the final round?**
A: Because of the round lottery: at α=5.0, seed 42, round 20 was 0.118 lower than the best round on validation. Choosing by validation is the standard, fair fix, and it never looks at test data.

**Q: Isn't choosing the best round on validation a form of cheating?**
A: No — that's what validation is for. Cheating would be choosing it on the test set. The test set scores only the already-chosen checkpoint.

**Q: Why StandardScaler rather than RobustScaler, which handles outliers better?**
A: RobustScaler divides by the IQR, which is zero for 28 of our 82 zero-inflated features, so those were left unscaled. StandardScaler fails on only one all-zero feature. Validation also picked it.

**Q: Why effective-number weights and not plain inverse-frequency?**
A: The pilot showed stronger correction hurts: from β=0.999 to β=0.99999, Infiltration precision fell from 0.92 to 0.12. β=0.999 scored best on validation.

---

## 2.3 Federated training {#ch-fl}

### In one line

Ten simulated organizations train the MLP together with Flower and FedAvg for 20 rounds of 3 local epochs each, at α ∈ {0.1, 0.5, 5.0} × seeds {42, 1337, 2024}, on CPU, with partitions checked by hash every time they load.

### Why this exists

This is the "federated" in federated IDS. It produces the trained models that both the explanation check and the trust check study, and it answers the first question an examiner asks: how much accuracy does federation cost, and when?

### How it works

![One run: 20 rounds; in each, all 10 silos train 3 local epochs, the server averages, scores the new global model on validation, and keeps a checkpoint.](img/fig02_rounds.svg)

1. Flower's simulation engine starts one server and 10 client processes on one laptop.
2. Each round, the server sends the global weights to **all 10** silos (`fraction-train = 1.0`; source: `federated/pyproject.toml`).
3. Each silo loads its partition (hash-checked), scales its own data with its own scaler, and trains 3 local epochs.
4. The server averages the updates with FedAvg (sample-count weighted), scores the new global model on the centralized validation split, and saves a checkpoint for that round.
5. After 20 rounds, the round with the highest validation macro-F1 is the run's model.

**Locked decision 5: all 10 silos train, regardless of size.** Even the 143-row silo at α=0.1 trains. The size floor (T_SILO=400) applies only later, to decide which silos are *eligible for explanation analysis* (source: `CLAUDE.md`; `docs/contribution_a_results.md` §6). Dropping small silos from training would change the federation we're studying.

### What we actually did

- **Framework: Flower (flwr) 1.33.0** (source: `README.md`, tech stack).
- **The authoritative harness is `federated/xfed_federated/`**, invoked as `flwr run federated local-simulation`. A bare `flwr run` from the repo root **fails on purpose**: an older prototype in `src/federated/` never implemented best-by-validation selection, so the root `pyproject.toml` had its Flower app section removed to make it impossible to train against the wrong harness by accident (source: `docs/contribution_b_results.md` §10).
- **9 configurations:** α ∈ {0.1, 0.5, 5.0} × seeds {42, 1337, 2024}.
- **20 rounds, 3 local epochs** (source: `federated/pyproject.toml`).
- **CPU, not GPU.** Flower builds an isolated environment for each run, and that environment used **torch 2.13.0+cpu**. This was verified for the August environments and all runs from 2026-10-12 on, so the published federated runs most likely trained on CPU (source: `docs/preregistration_accuracy.md`; `docs/contribution_a_results.md`, optimizer section). The GPU ran the centralized MLP, XGBoost and Ollama (source: `CLAUDE.md`, Environment). We disclose this because an earlier description said the federated runs used the GPU.
- **Partitions on disk** with the SHA256 manifest from [2.1](#ch-data).
- **Server-side validation** on the centralized 143,513-row validation split. In a real deployment the server wouldn't hold a centralized validation set; this is a simulation simplification.
- **Legacy client-side test scoring.** The published runs also scored each silo on its own local test shard every round (`fraction-evaluate = 1.0`). Nothing reads those scores; the flag is now off by default (`legacy-client-test-eval = false`) (source: `README.md`, step 4; `docs/test_set_exposure_audit.md` row 3). Part 3 covers it.

### What we found

| α | FedAvg macro-F1 (mean ± sd, 3 seeds) | Per seed (42 / 1337 / 2024) |
|---|---|---|
| 0.1 | **0.516 ± 0.048** | 0.5426 / 0.4481 / 0.5572 |
| 0.5 | **0.941 ± 0.057** | 0.9753 / 0.9866 / 0.8605 |
| 5.0 | **0.990 ± 0.001** | 0.9900 / 0.9905 / 0.9889 |

(source: `results/aggregated/federated_headline.csv`; per-seed values from `docs/contribution_a_results.md`, optimizer section)

Compare: centralized MLP 0.9900 ± 0.0022 (source: `results/aggregated/centralized_headline.csv`).

**Reading.**

- **At α=5.0 (near-IID), federation costs nothing**: 0.990 vs 0.990 centralized.
- **At α=0.5, it mostly works**, but one seed (2024) is much worse (0.8605), which inflates the spread.
- **At α=0.1, accuracy collapses** to 0.516. Many silos hold only one or two families; averaging their very different models produces a global model that misses whole families.

So the near-IID control does its job: the drop is caused by **non-IID data**, not by federation as such.

**Time and bytes.** One round over 25 logged method runs had a median of 51.4 seconds on the laptop's CPU (source: `results/efficiency/communication.json`). Each round moves 1,587,920 bytes of fp32 weights in total (793,960 each way) (source: `results/efficiency/communication.json`).

### What this does NOT mean

- It does not mean "federated learning is worse than centralized." At α=5.0 they tie. The cost depends on heterogeneity.
- It does not mean α=0.1 is realistic. It is a deliberately pathological stress test.
- n=3 seeds per α: the ± values are rough.
- Ten processes on one laptop is a simulation; there is no real network, no dropped clients and no stragglers.
- These are not GPU results.

### Where it lives in the code

| File | What it does |
|---|---|
| `federated/xfed_federated/server_app.py` | Server strategy, validation scoring, checkpointing, logging strategies (`LoggingFedAvg`, Krum, trimmed mean, ByzAgent) |
| `federated/xfed_federated/client_app.py` | Local training on one silo |
| `federated/xfed_federated/_vendored/` | Vendored copies of data loading, metrics, attacks, agent (Flower isolates the app) |
| `federated/pyproject.toml` | Rounds, local epochs, fractions, pinned versions |
| `federated/flwr_config.example.toml` | Example user-level Flower simulation config |
| `tools/run_sweep.ps1`, `tools/run_sweep_fedprox.ps1` | The 9-configuration sweeps |
| `scripts/aggregate_federated.py` | Builds `results/aggregated/federated_headline.csv` |
| `results/federated/<tag>/` | Per-run `round_history.json`, `final_metrics.json`, checkpoints |
| `src/federated/` | Early prototype, **unused**, kept as it was |

### Questions an examiner might ask

_Numbers in these model answers repeat numbers already given with their source earlier in this chapter; the source notes are not repeated here._

**Q: Isn't your federated accuracy worse than centralized?**
A: Only under heterogeneity. At α=5.0 FedAvg scores 0.990 ± 0.001, the same as centralized 0.9900 ± 0.0022. At α=0.5 it's 0.941 ± 0.057 and at α=0.1 0.516 ± 0.048. The near-IID control shows the drop comes from non-IID data, not federation itself.

**Q: Why train tiny silos that can't learn anything?**
A: Locked decision 5: all 10 silos train regardless of size, because that's the federation we're studying. Small silos are only excluded later from the *explanation* analysis, by a stated size floor.

**Q: Did you use the GPU for federated training?**
A: No. Flower's isolated runtime installed torch 2.13.0+cpu, verified for the August environments and every run from 2026-10-12 on. The GPU trained the centralized MLP and XGBoost and ran Ollama.

**Q: What stops someone from accidentally running the wrong harness?**
A: The root `pyproject.toml` has no Flower app section, so a bare `flwr run` fails immediately. Every reported number came from `flwr run federated local-simulation`.

**Q: Why is α=0.5 seed 2024 so much worse?**
A: That seed's partition happens to be harder: its best-by-validation macro-F1 was 0.8644 against 0.9760 and 0.9871 for the other seeds (source: `docs/preregistration_accuracy.md`, baseline table). It's why we run three seeds and report the spread.

**Q: Is a centralized validation set realistic in FL?**
A: No; it's a simulation simplification that lets us pick rounds fairly and compare methods on identical terms. A deployment would need held-out validation data agreed by the participants.
