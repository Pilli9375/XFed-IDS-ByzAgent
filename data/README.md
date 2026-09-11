# XFed-IDS — Data Pipeline

Decision record for the data stage. Every choice below was made deliberately,
with a reason, and every number was produced by the scripts in `src/data/` —
none are copied from the literature or estimated.

Last updated: 2026-08-06.

---

## 1. Dataset and lineage

**Distrinet-CIC-IDS2017**, Kaggle (`dhoogla/distrinetcicids2017`), **versions/4** —
the IEEE CNS 2022 update. Five per-day CSVs, ~1.15 GB, held outside the repo at
`C:\Pilli\Capstone\Dataset\`.

This is a *corrected* CICIDS2017, not the original CIC release. The lineage has
two stages and both must be cited:

| Stage | Work | Contribution |
|---|---|---|
| Foundational | Engelen, Rimmer & Joosen (2021), *Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study*, IEEE SPW (WTMC workshop) | Identified errors in traffic generation, flow construction, feature extraction and labelling; introduced the fixed CICFlowMeter and the `X - Attempted` label convention |
| **This dataset (V4)** | Liu, Engelen, Lynar, Essam & Joosen (2022), *Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018*, IEEE CNS, pp. 254–262 | Further errors across the dataset creation lifecycle; released the refined version used here. Best Paper, IEEE CNS 2022 |

> **Open item for 01_Planning.** Locked decision 1 currently names only
> "Engelen et al. corrected CICIDS2017 (WTMC-2021)". The files actually in use
> are the Liu et al. (2022) V4 CSVs. The decision text needs rewording and the
> paper needs both citations. Not a scope change — V4 is a more thorough
> correction of the same lineage.

A third correction branch exists (Lanvin et al., CRiSIS-2022) addressing
different issues — mislabelled port scans, duplicated captures. **Not used
here.** Worth one sentence in Related Work.

### Raw shape

- 2,099,976 flows across 5 day-files
- 91 columns: 7 identifiers, 1 `Label`, 1 `Attempted Category`, **82 candidate features**
- All five files column-identical; **zero** columns carry leading/trailing whitespace
  (checked explicitly — this is a known CICIDS trap, it just doesn't apply to V4)
- All 82 candidate features parsed as numeric; no `object`-dtype surprises

Identifiers dropped: `id`, `Flow ID`, `Src IP`, `Src Port`, `Dst IP`, `Dst Port`,
`Timestamp`. This matters more than it looks — see §4.

---

## 2. The `Attempted` convention

Engelen et al. label a flow `X - Attempted` when it belongs to payload-reliant
attack class *X* but carries no payload — the attack was launched but did not
land. V4 additionally exposes an `Attempted Category` column: a reason code,
not a boolean (7 distinct values observed: `-1`, `0`, `1`, `2`, `3`, `4`, `6`).

**Verified finding:** `Attempted Category != -1` agrees with the `- Attempted`
label suffix on **every one of the 2,099,976 rows**, with zero exceptions. The
suffix check alone is therefore sufficient, and the pipeline does not read the
category column. It is retained in the raw data as a diagnostic only.

### Decision: Attempted flows join their parent family

Not folded into Benign, not dropped.

Engelen et al.'s own benchmark assigns Attempted flows to Benign, and that was
the initial plan here. **The per-family counts overturned it.** For several
families, Attempted flows are the majority of the class:

| Family (raw) | Clean | Attempted | Attempted share |
|---|---:|---:|---:|
| Web Attack – XSS | 18 | 655 | 97% |
| Web Attack – Brute Force | 73 | 1,292 | 95% |
| Botnet | 736 | 4,067 | 85% |
| DoS Slowhttptest | 1,741 | 3,367 | 66% |
| Infiltration | 36 | 45 | 56% |
| DoS Slowloris | 3,998 | 1,708 | 30% |
| DoS Hulk | 158,449 | 581 | 0.4% |

Folding to Benign would remove 85–97% of the mass from Bot and both Web Attack
subtypes — families already close to the reporting floor. Assigning them to the
parent family is one uniform rule with no per-family exceptions, and is
justified on the grounds that a flow whose payload did not land is still an
instance of the attacker's behaviour class.

**Cost / defensibility:** the model is being taught to alert on failed attempts
as well as successful ones. For an IDS this is arguably correct behaviour, but
it does mean reported per-family performance mixes completed and attempted
attacks. Stated, not hidden.

---

## 3. Taxonomy — 14 raw labels → 8 families + Benign

Defined in `configs/data.yaml` under `family_map`. `src/data/mapping.py` raises
if any observed raw label has no mapping, rather than producing a silent `NaN`
family on a future re-run.

| Family | Raw labels folded in |
|---|---|
| Benign | BENIGN |
| DoS | DoS Hulk, DoS GoldenEye, DoS Slowloris, DoS Slowhttptest (+ Attempted variants) |
| DDoS | DDoS |
| PortScan | Portscan, **Infiltration - Portscan** |
| BruteForce | FTP-Patator, SSH-Patator (+ Attempted) |
| WebAttack | Web Attack Brute Force / XSS / SQL Injection (+ Attempted) |
| Bot | Botnet (+ Attempted) |
| Infiltration | Infiltration (+ Attempted) |
| Heartbleed | Heartbleed |

### Decision: `Infiltration - Portscan` → PortScan, not Infiltration

67,072 raw flows — larger than six other families combined, so where it goes
matters.

By name it belongs with Infiltration: it is the internal-scan phase of the
infiltration scenario. **By feature signature it is a port scan** — short flows,
low byte counts, many probes — and nothing like the ~80 genuinely stealthy
infiltration flows. Routing it to Infiltration would produce a family that is
>99.9% portscan-shaped, meaning every SHAP explanation for an "Infiltration"
alert would in practice be explaining a port scan.

Routed on feature-signature grounds. **Cost:** Infiltration drops to 66 flows and
falls under the reporting floor. Accepted deliberately — "we excluded
Infiltration, here is the count and the reason" is more defensible than a family
whose label does not describe its contents.

### Floor rule

Families below **1,000 flows** are reported but excluded from headline macro-F1,
with the reason stated. They are **not deleted** from the data.

Under the floor: **Infiltration (66)**, **Heartbleed (11)**.

**Headline metric:** macro-F1 over 6 attack families + Benign. Infiltration (66)
and Heartbleed (11) fall below the 1,000-flow floor — reported per-class,
excluded from headline macro-F1.

---

## 4. Cleaning

Order is load → **family mapping** → Inf/NaN → conflicts → dedup. The mapping
must come first; see §4.2.

### 4.1 Inf / NaN — 5 rows dropped

Four columns carry non-finite or sentinel values:

| Column | +Inf | NaN | Negative |
|---|---:|---:|---:|
| Flow Bytes/s | 5 | 0 | 0 |
| Flow Packets/s | 5 | 0 | 0 |
| ICMP Code | 0 | 0 | 2,099,373 |
| ICMP Type | 0 | 0 | 2,099,373 |

The Inf values trace to exactly 5 flows with `Flow Duration == 0` (both columns
divide by duration). Dropped — 0.0002% of the data.

The ICMP negatives are **not corruption**: `-1` is CICFlowMeter's
"not applicable" sentinel for non-ICMP flows, which is almost everything. No
action taken.

### 4.2 Family conflicts — 44,005 rows dropped

Groups of feature-identical rows carrying **more than one family** are dropped
entirely. No classifier can separate identical inputs mapped to different
targets; keeping any member injects label noise and caps achievable macro-F1.

| Conflicting families | Rows | Groups |
|---|---:|---:|
| Benign \| PortScan | 43,890 | 756 |
| Bot \| Infiltration | 115 | 15 |

> **Finding worth reporting.** Even in the corrected dataset, ~43,890 flows are
> feature-identical to benign traffic once identifier columns are removed. This
> is a ceiling imposed by the 82-feature space itself, not by any model. It
> belongs in the paper's limitations.

**Conflicts are evaluated on `family`, not on the raw label.** An earlier version
keyed this on the raw label and destroyed 58,307 rows where
`Infiltration - Portscan` and `Portscan` "conflicted" — despite both mapping to
PortScan and therefore being perfectly learnable at the granularity actually
trained on. The bug did not crash; it produced plausible output for a full
cycle. Caught only by logging *which* combinations conflicted.

### 4.3 Duplicates — 142,464 rows dropped, and a large deliberate non-removal

Raw exact-duplicate rate is **18.3%**, concentrated almost entirely in scan and
bot traffic:

| Label | Rows in duplicate groups | Share of that label |
|---|---:|---:|
| Portscan | 157,753 | 99.2% |
| Infiltration - Portscan | 63,747 | 95.0% |
| Botnet - Attempted | 3,645 | 89.6% |
| BENIGN | 222,500 | 14.0% |

**These are not repeated observations of one event.** A port scan probes many
destination ports with identical packet shape, duration and byte counts,
differing only in the port number — which is a dropped identifier column. Bot
C2 beacons are periodic and near-identical by design. Once identifiers are
removed, many genuinely distinct events collapse into identical rows.

**Rule applied:** drop duplicates only where a group spans **more than one
day-file**. Same-day repetition has the behavioural explanation above;
byte-identical flows across different capture days do not, and match the
capture-overlap problems documented in this dataset's correction literature.

**The dedup key is the raw `Label`, deliberately different from the conflict key
(`family`).** The two filters answer different questions:

- conflicts ask *is this learnable?* → keyed on the **target** (family)
- duplicates ask *is this one captured event, recorded twice?* → keyed on
  **provenance** (raw label)

Capture overlap would produce the same raw label both times. Two rows with
different raw labels on different days are different events that merely collapse
to identical features. Keying dedup on family wrongly deleted 58,228 such rows
in an earlier version.

### 4.4 Near-constant features — retained, deliberately

Eight of 82 features have one value covering ≥99.9% of rows (`Bwd URG Flags`,
`Subflow Bwd Packets`, `Fwd URG Flags`, `URG Flag Count`, `ICMP Type`,
`ICMP Code`, `ECE Flag Count`, `CWR Flag Count`). **None is strictly constant.**

Not dropped at this stage. Dropping on a variance heuristic before any
feature-importance evidence exists would foreclose signal — `ICMP Type`/`Code`
are the only features that could carry information about an ICMP-based attack.
Revisit in 03_Model_FL with baseline importances, not here.

**All 82 features retained.**

### 4.5 Cleaning summary

| Stage | Rows removed |
|---|---:|
| Start | 2,099,976 |
| Inf / NaN | −5 |
| Family conflicts | −44,005 |
| Cross-file duplicates | −142,464 |
| **Retained** | **1,913,502** (8.88% dropped) |

---

## 5. Final family distribution

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

Severe imbalance — Benign is 75% of the data and Heartbleed is 0.0006%. This is
why **macro-F1 is the headline metric and accuracy is never reported**, and why
per-class results accompany every aggregate.

**Imbalance handling: class-weighted loss, not SMOTE.** Three reasons specific to
this project: (a) SMOTE must be fit per-silo to respect the privacy premise, but
Dirichlet at α=0.1 leaves most silos with too few real minority samples for
*k*-neighbour interpolation to work; (b) flow features are correlated by
construction (rate = bytes ÷ duration) and linear interpolation does not respect
that; (c) synthetic minority points would contaminate the cross-silo explanation
agreement measurement, which is this project's central contribution. Implemented
in 03_Model_FL.

---

## 6. Train/test split — group-aware, global, before partitioning

**One global family-stratified 75/25 split**, performed before any Dirichlet
partitioning, so the centralized baseline and the federated global model are
evaluated on the identical held-out set. Per-silo local test shards come from
applying the same Dirichlet proportions to this test set — not from a second
independent split.

### Grouped, not random

After cleaning, **213,752 rows still share a feature vector with at least one
other row** (1,714,074 distinct vectors across 1,913,502 rows). A plain random
split would place copies of the same vector in both train and test, handing the
model free correct answers and inflating every reported metric.

Deleting them would have stripped most of PortScan. Instead, every distinct
feature vector is treated as a **group** (`StratifiedGroupKFold`), forcing all
copies onto the same side of the boundary. Zero leakage, zero data loss.

The pipeline **verifies** the guarantee rather than trusting the library, and
raises if any vector appears on both sides.

### Result

1,435,126 train / 478,376 test (25.0%).

| Family | Train | Test | Test % |
|---|---:|---:|---:|
| Benign | 1,080,674 | 360,225 | 25.0 |
| PortScan | 139,620 | 46,540 | 25.0 |
| DoS | 133,118 | 44,373 | 25.0 |
| DDoS | 71,358 | 23,786 | 25.0 |
| BruteForce | 5,229 | 1,743 | 25.0 |
| Bot | 3,527 | 1,176 | 25.0 |
| WebAttack | 1,542 | 514 | 25.0 |
| Infiltration | 50 | 16 | 24.2 |
| Heartbleed | 8 | 3 | 27.3 |

Grouping makes exact proportions impossible in principle; all seven headline
families nonetheless landed at exactly 25.0%. The two deviations are the
floor-excluded families, where single groups are a large share of the class.

---

## 7. Federated partitioning

**10 silos. Dirichlet over labels. α ∈ {0.1, 0.5, 5.0} × seeds {42, 1337, 2024}
= 9 configurations.**

For each family *k* independently, draw a proportion vector over the silos:

```
p_k ~ Dir(α · 1_N)
```

`p_k[i]` is the fraction of family *k*'s flows going to silo *i*. Proportions are
applied by splitting each family's shuffled indices at cumulative boundaries,
giving exact proportions rather than multinomial sampling noise — which matters
for the small families, where noise could swing a silo's share substantially.

| α | Regime |
|---|---|
| 0.1 | Pathological heterogeneity — a family lands almost entirely in one silo |
| 0.5 | Realistic heterogeneity |
| 5.0 | Near-IID **control** |

The control is not optional: without it, "federation costs accuracy" and
"non-IID costs accuracy" cannot be separated, and they are different claims.

### Measured heterogeneity

Empty (silo, family) cells, out of 90 per configuration:

| α | seed 42 | seed 1337 | seed 2024 |
|---|---:|---:|---:|
| 0.1 | 38 | 29 | 31 |
| 0.5 | 7 | 10 | 8 |
| 5.0 | 3 | 2 | 2 |

Clean monotonic separation. Mean maximum single-silo share of a family: 0.694 at
α=0.1, 0.372 at α=0.5, 0.177 at α=5.0 (uniform ideal = 0.100).

**Two consequences to expect in 03_Model_FL, not to be alarmed by:**

1. Silo sizes become extremely uneven at α=0.1 — smallest ~143 rows against
   largest ~636,676. FedAvg's sample-count weighting will nearly ignore the
   small silos, and a 143-row silo cannot train a meaningful local model.
2. Some (silo, family) cells are empty **even at α=5.0**. Heartbleed has 8
   training flows and cannot occupy 10 silos. Unavoidable; state it rather than
   let a reviewer find it.

### Storage: assignments, not copies

Materialising 90 full shards would cost several GB and be invalidated by any
upstream change. The pipeline writes the row → silo **assignment** (~2 MB per
config) and materialises silos on demand via `load_silo()`.

The manifest hashes the **assignment array itself**, not file contents. This is
strictly stronger: it catches a partitioning bug that produces different output
from identical config inputs. Verified to detect a single flipped value across
1.4M entries. `load_silo()` checks the hash before returning data and raises on
mismatch.

---

## 8. Leakage controls — summary

Every point where test information could reach training, and what prevents it:

| Failure mode | Control |
|---|---|
| Scaler fit on pooled data before split | Fit per-silo on that silo's **train** rows only (03_Model_FL) |
| Duplicates straddling train/test | Group-aware split, verified, not assumed |
| Duplicates scattered across silos | Dedup applied before partitioning, never after |
| Partition silently regenerated differently | Manifest hash over the assignment array, checked at load |
| SHAP background drawn from test | Background = seeded, class-stratified sample from that client's **train** partition (locked decision 4) |
| Floor exclusions recomputed per run | Decided once from pooled counts, recorded here, applied everywhere |

---

## 9. Reproducing

```bash
python src/data/clean.py        # raw CSVs  -> clean.parquet
python src/data/families.py     # -> train_pool.parquet, test_global.parquet
python src/data/partition.py    # -> partitions/ + manifest.json
```

All parameters live in `configs/data.yaml`. Nothing is hardcoded in the scripts.
Seed 42 throughout the data stage.

### Artifacts

| File | Contents |
|---|---|
| `clean.parquet` | Cleaned flows with `family`, `is_attempted` |
| `clean_log.json` | Row counts at every removal stage, conflict breakdown, leakage exposure |
| `train_pool.parquet` / `test_global.parquet` | The global split |
| `family_distribution.csv` | Flows per family, floor flags |
| `family_log.json` | Split sizes, per-family balance, starvation warnings |
| `partitions/assign_a{α}_s{seed}_{split}.parquet` | Row → silo assignments |
| `partitions/label_distribution_a{α}_s{seed}.csv` | Flows per family per silo |
| `partitions/manifest.json` | Hashes, drawn proportions, silo sizes, empty-cell counts |

---

## 10. Open items

- **01_Planning:** locked decision 1 names WTMC-2021; actual data is Liu et al.
  (2022) V4. Reword; cite both.
- **03_Model_FL:** revisit the 8 near-constant features with real importance
  evidence.
- **03_Model_FL:** α=0.1 produces silos too small to train locally. Decide
  whether to report them, exclude them, or set a minimum silo size — and say so
  before running, not after seeing results.
- **05_Paper:** the 43,890 Benign/PortScan feature-collision flows are a
  limitation finding, not just a cleaning step.
