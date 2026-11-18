# Appendix

This chapter holds the full detail behind Chapters 2 to 5. Each section opens by saying what it contains and which chapter it supports. Numbers in this chapter come from the same results files as the rest of the report, and every table and figure is listed in the front matter.

## Dataset and Cleaning {#sec:app-data}

This section records each step of data preparation and how many rows each step kept or removed. It supports Section 2.2.1 and the accuracy results of Section 4.1.

### Dataset lineage: the Distrinet release against the original

The project uses the Distrinet release of CICIDS2017, version 4, downloaded as five per-day CSV files and kept outside the repository. This is a corrected dataset, not the original release from the Canadian Institute for Cybersecurity [@sharafaldin2018]. Its lineage has two stages, and both are cited (@tab:lineage).
<!-- src: data/README.md -->

Table: The two correction stages behind the dataset used {#tab:lineage}
| Stage | Work | What it changed |
|---|---|---|
| Foundational correction | Engelen, Rimmer and Joosen [@engelen2021] | Found errors in traffic generation, flow construction, feature extraction and labelling; fixed the flow-meter tool; introduced the "Attempted" label for attack flows that carry no payload |
| This dataset (version 4) | Liu, Engelen, Lynar, Essam and Joosen [@liu2022] | Traced further errors across the dataset's creation lifecycle and released the refined version used here |
<!-- src: data/README.md -->

A third, separate correction branch [@lanvin2023] addresses other issues, such as mislabelled port scans and duplicated captures. It was not used.

Before cleaning there are 2,099,976 flows, one file per capture day, five files in all. The files share an identical set of 91 columns. Of these, 82 are numeric features; the remaining nine are seven identifier columns, the label and a code for attempted attacks. No column name carries stray whitespace, a known trap in the original release, and every candidate feature parsed as numeric. The identifiers dropped are the row id, flow id, source and destination addresses, source and destination ports, and the timestamp.
<!-- src: data/README.md -->

### The "Attempted" convention

Engelen et al. label a flow "X – Attempted" when it belongs to an attack class X that needs a payload but carries none: the attack was launched but did not land. Version 4 also has an attempted-category column, a reason code with 7 distinct values. We verified that a non-default category agrees with the "Attempted" label suffix on every one of the 2,099,976 rows, so the pipeline reads only the suffix.
<!-- src: data/README.md -->

The authors' own benchmark folds attempted flows into Benign, and that was our first plan. @tab:attempted shows why we dropped it: for several families, attempts are most of the class, and folding them away would have removed most of Bot and both web-attack subtypes. Attempted flows therefore join their parent family under one uniform rule. We accept one cost and say so: each family's score blends successful attacks with ones that failed to land.

Table: Share of attempted flows in raw families {#tab:attempted}
| Raw family | Completed | Attempted | Attempted share |
|---|---:|---:|---:|
| Web Attack – XSS | 18 | 655 | 97% |
| Web Attack – Brute Force | 73 | 1,292 | 95% |
| Botnet | 736 | 4,067 | 85% |
| DoS Slowhttptest | 1,741 | 3,367 | 66% |
| Infiltration | 36 | 45 | 56% |
| DoS Slowloris | 3,998 | 1,708 | 30% |
| DoS Hulk | 158,449 | 581 | 0.4% |
<!-- src: data/README.md -->

### Family mapping and the reporting floor

The 14 raw labels map to nine classes (@tab:family-map). The mapping lives in `configs/data.yaml`, and the mapping code raises an error if any raw label has no mapping, so a future re-run cannot silently produce an empty family.
<!-- src: data/README.md -->

Table: Raw labels folded into each family (attempted variants included) {#tab:family-map}
| Family | Raw labels |
|---|---|
| Benign | BENIGN |
| DoS | DoS Hulk, DoS GoldenEye, DoS Slowloris, DoS Slowhttptest |
| DDoS | DDoS |
| PortScan | Portscan, Infiltration – Portscan |
| BruteForce | FTP-Patator, SSH-Patator |
| WebAttack | Web Attack Brute Force, XSS, SQL Injection |
| Bot | Botnet |
| Infiltration | Infiltration |
| Heartbleed | Heartbleed |

The 67,072 "Infiltration – Portscan" flows needed a decision, because there are more of them than in six other families combined. Their name points to Infiltration, because they come from the scanning step inside that scenario. By their features they are a port scan: short flows, low byte counts, many probes. Routing them to Infiltration would have built a class almost entirely shaped like port scans, and every Infiltration explanation would really have explained a scan. They were routed to PortScan. As a result, only 66 flows are left in Infiltration.
<!-- src: data/README.md -->

A family with under 1,000 flows stays in the dataset, but it is left out of the headline macro-F1 and reported on its own, with its count. Two families fall below the floor: Infiltration (66) and Heartbleed (11). The headline metric therefore averages six attack families and Benign.
<!-- src: data/README.md -->

### Cleaning

The cleaning steps ran in a fixed sequence: loading, mapping to families, removing non-finite values, removing conflicts and, last, removing duplicates. The mapping has to come first, because conflicts are judged on the family.

**Non-finite values.** Four columns carry non-finite or sentinel values (@tab:nonfinite). The infinite values come from exactly 5 flows with zero duration, since both rate columns divide by duration; those 5 rows were dropped. The negative values in the two ICMP columns are not corruption: −1 is the flow meter's "not applicable" marker for non-ICMP flows, which is almost every flow. No action was taken on them.
<!-- src: data/README.md -->

Table: Columns with non-finite or sentinel values in the raw data {#tab:nonfinite}
| Column | +Inf | NaN | Negative |
|---|---:|---:|---:|
| Flow Bytes/s | 5 | 0 | 0 |
| Flow Packets/s | 5 | 0 | 0 |
| ICMP Code | 0 | 0 | 2,099,373 |
| ICMP Type | 0 | 0 | 2,099,373 |
<!-- src: data/README.md -->

**Family conflicts.** If one feature vector appears with two different families, no model can learn to tell them apart: no classifier separates identical inputs mapped to different targets. Such groups were dropped whole (@tab:conflicts). Even in the corrected data, then, about forty-four thousand flows look exactly like benign traffic once identifiers are removed. That is a ceiling set by the feature space itself, not by any model. Conflicts are keyed on the family. Our first version compared raw labels instead, and it quietly threw away 58,307 rows that could be learned: "Infiltration – Portscan" and "Portscan" looked like a conflict although both end up in PortScan. The bug was caught only by logging which label pairs conflicted.
<!-- src: data/README.md -->

Table: Family conflicts removed {#tab:conflicts}
| Conflicting families | Rows | Groups |
|---|---:|---:|
| Benign and PortScan | 43,890 | 756 |
| Bot and Infiltration | 115 | 15 |
<!-- src: data/README.md -->

**Duplicates.** In the raw data, 18.3% of rows duplicate some other row exactly, and these copies come almost only from scanning and botnet traffic (@tab:dups). These are mostly not repeated records of one event. A port scan probes many ports with packets of the same shape, which differ only in the port number, a column we drop. Bot beacons are periodic and nearly identical by design. Once identifiers are removed, many distinct events collapse into identical rows. So a group of duplicates is removed only if its copies come from different capture days, the pattern expected from the overlapping captures documented for this dataset. Duplicates are keyed on the raw label, which records provenance, while conflicts are keyed on the family, which is the training target. When an earlier version matched duplicates by family instead, it removed 58,228 rows that were in fact separate events.
<!-- src: data/README.md -->

Table: Labels with the largest share of rows in duplicate groups (raw data) {#tab:dups}
| Raw label | Rows in duplicate groups | Share of the label |
|---|---:|---:|
| Portscan | 157,753 | 99.2% |
| Infiltration – Portscan | 63,747 | 95.0% |
| Botnet – Attempted | 3,645 | 89.6% |
| BENIGN | 222,500 | 14.0% |
<!-- src: data/README.md -->

**Near-constant features.** For 8 features out of 82, a single value covers at least 99.9% of rows: Bwd URG Flags, Subflow Bwd Packets, Fwd URG Flags, URG Flag Count, ICMP Type, ICMP Code, ECE Flag Count and CWR Flag Count. None is strictly constant. All 82 were kept, since dropping features on a variance rule before any importance evidence would discard signal; the ICMP columns, for instance, are the only ones that could describe an ICMP-based attack.
<!-- src: data/README.md -->

@tab:clean-steps summarises the cleaning.

Table: Cleaning steps and rows removed {#tab:clean-steps}
| Stage | Rows |
|---|---:|
| Raw flows | 2,099,976 |
| Non-finite values removed | −5 |
| Family conflicts removed | −44,005 |
| Cross-day duplicates removed | −142,464 |
| Retained (8.88% dropped) | 1,913,502 |
<!-- src: data/README.md -->

### Final distribution and the group-aware split

The cleaned data are heavily imbalanced: Benign is 75% of all flows. This is why macro-F1 is the headline metric and why every aggregate is reported with per-class results. Imbalance is handled with a class-weighted loss rather than SMOTE, for three reasons. SMOTE would have to run inside each silo to respect the privacy premise, and at α=0.1 most silos hold too few minority examples for neighbour interpolation to work. Flow features are linked by construction (a rate is bytes divided by duration), and straight-line interpolation breaks those links. Finally, made-up rows would feed into the very explanation comparison this project sets out to measure.
<!-- src: data/README.md -->

Even after cleaning, 213,752 rows have a twin with the same feature vector; the 1,913,502 cleaned rows hold just 1,714,074 different vectors. A random split would put copies of one vector on both sides of the split and hand the model free correct answers. Deleting the copies would have stripped most of PortScan. Instead, every distinct vector is treated as a group, using a stratified group k-fold split, and the pipeline verifies afterwards that no vector appears on both sides, raising an error if one does. The split is a single global 75/25 split made before any partitioning, so the centralized and federated models are tested on the identical held-out set. @tab:split gives the result.
<!-- src: data/README.md -->

Table: Family counts after cleaning, and their division by the grouped split {#tab:split}
| Family | Flows | Training pool | Test | Test share (%) |
|---|---:|---:|---:|---:|
| Benign | 1,440,899 | 1,080,674 | 360,225 | 25.0 |
| PortScan | 186,160 | 139,620 | 46,540 | 25.0 |
| DoS | 177,491 | 133,118 | 44,373 | 25.0 |
| DDoS | 95,144 | 71,358 | 23,786 | 25.0 |
| BruteForce | 6,972 | 5,229 | 1,743 | 25.0 |
| Bot | 4,703 | 3,527 | 1,176 | 25.0 |
| WebAttack | 2,056 | 1,542 | 514 | 25.0 |
| Infiltration (below floor) | 66 | 50 | 16 | 24.2 |
| Heartbleed (below floor) | 11 | 8 | 3 | 27.3 |
| Total | 1,913,502 | 1,435,126 | 478,376 | 25.0 |
<!-- src: data/README.md -->

Grouping makes exact proportions impossible in principle, yet all seven headline families landed at exactly 25.0%. The two deviations are the below-floor families, where a single group is a large share of the class.
<!-- src: data/README.md -->

### The validation set

A centralized validation set is drawn from the training pool and held out of every silo. It uses the same grouping rule, so no feature vector is shared between the validation set and the rows used for training. @tab:val-split gives its size and composition.
<!-- src: results/val_split_report.json; configs/model.yaml -->

Table: Training/validation split of the training pool (seed 42, 10 group folds, one held out) {#tab:val-split}
| Family | Training rows | Validation rows |
|---|---:|---:|
| Benign | 972,607 | 108,067 |
| PortScan | 125,658 | 13,962 |
| DoS | 119,806 | 13,312 |
| DDoS | 64,222 | 7,136 |
| BruteForce | 4,706 | 523 |
| Bot | 3,174 | 353 |
| WebAttack | 1,388 | 154 |
| Infiltration | 45 | 5 |
| Heartbleed | 7 | 1 |
| Total | 1,291,613 | 143,513 |
<!-- src: results/val_split_report.json -->

The training pool of 1,435,126 rows has 1,285,553 distinct feature vectors. The validation mask is stored with its own SHA-256 hash.
<!-- src: results/val_split_report.json -->

### Leakage controls

@tab:leakage lists every point where test information could reach training and what prevents it.

Table: Leakage controls in the data stage {#tab:leakage}
| Failure mode | Control |
|---|---|
| Scaler fit on pooled data before the split | Fit in each silo on that silo's training rows only |
| Duplicates straddling the train/test boundary | Group-aware split, verified rather than assumed |
| Duplicates scattered across silos | Deduplication before partitioning, never after |
| A partition silently regenerated differently | SHA256 manifest over the assignment array, checked at load |
| SHAP background drawn from the test set | Background is a seeded, class-stratified sample of the silo's own training partition |
| Floor exclusions recomputed per run | Decided once from pooled counts and applied everywhere |

## Federated Partitions {#sec:app-partitions}

This section describes how the training pool was divided among the ten silos and gives the label counts of every silo in all nine partitions. It supports Sections 2.2.2 and 4.2.

### Method and measured heterogeneity

For each family k separately, a vector of silo shares is drawn as p_k ~ Dir(α·1). The share p_k[i] is the fraction of family k that goes to silo i. Each family's rows are shuffled and divided at the running totals of the shares. The proportions are therefore exact, with no sampling noise, which matters most for the small families. At α=0.1 the skew is extreme, and a family usually ends up nearly whole in a single silo. α=0.5 gives skew of a realistic size, and α=5.0 acts as a control close to IID. The control is needed to tell "federation costs accuracy" apart from "non-IID data costs accuracy", which are different claims.
<!-- src: data/README.md -->

@tab:empty-cells counts the (silo, family) cells that receive no flows. The counts fall cleanly as α grows. Even at α=5.0 a few cells stay empty, because Heartbleed has only 8 training flows and cannot fill ten silos. The largest single-silo share of a family, averaged across families, is 0.694 at α=0.1, 0.372 at α=0.5 and 0.177 at α=5.0; a perfectly even split would make it 0.100.
<!-- src: data/README.md -->

Table: Number of empty (silo, family) cells in each partition, of 90 possible {#tab:empty-cells}
| α | Seed 42 | Seed 1337 | Seed 2024 |
|:-:|:-:|:-:|:-:|
| 0.1 | 38 | 29 | 31 |
| 0.5 | 7 | 10 | 8 |
| 5.0 | 3 | 2 | 2 |
<!-- src: data/README.md -->

At α=0.1 silo sizes are extreme: in the seed-42 partition, the smallest silo has 143 rows and the largest 636,676. FedAvg weights updates by sample count, so it nearly ignores the smallest silos, and a 143-row silo cannot train a meaningful local model on its own. All silos still train in every round; the size floor applies only to explanation eligibility.
<!-- src: data/README.md; results/partition_check.json -->

### Storage and the SHA256 manifest

Writing 90 full silo shards to disk would cost several gigabytes and would be invalidated by any upstream change. The pipeline instead writes the row-to-silo assignment for each partition and builds a silo on demand. The manifest records a SHA256 hash of each assignment array, the drawn proportions, the silo sizes and the empty-cell counts. Hashing the assignment array itself, rather than file contents, also catches a partitioning bug that produces different output from the same configuration. A test confirmed that the check detects a single flipped value among 1.4 million entries, and the loader raises an error on any mismatch.
<!-- src: data/README.md -->

### Per-silo label counts

The nine tables give the number of training-pool flows of each family in each silo: @tab:silo-a01-s42, @tab:silo-a01-s1337 and @tab:silo-a01-s2024 for α=0.1; @tab:silo-a05-s42, @tab:silo-a05-s1337 and @tab:silo-a05-s2024 for α=0.5; and @tab:silo-a50-s42, @tab:silo-a50-s1337 and @tab:silo-a50-s2024 for α=5.0. The total column is the silo's size; the counts include rows that are later held out for validation, which are masked at load time. The counts make the skew concrete. At α=0.1, nearly all of a typical silo's flows come from just two families, while at α=5.0 every silo holds every family, apart from a few silos that receive no Heartbleed flows.
<!-- src: data/README.md -->

Table: Training-pool flows per silo and family, α=0.1, seed 42 {#tab:silo-a01-s42 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 361 | 10 | 31,541 | 0 | 0 | 0 | 133,559 | 0 | 165,471 |
| 1 | 446 | 176 | 847 | 0 | 285 | 0 | 0 | 501 | 0 | 2,255 |
| 2 | 606,828 | 0 | 0 | 2,141 | 27,511 | 0 | 0 | 0 | 196 | 636,676 |
| 3 | 0 | 1,952 | 15 | 0 | 20 | 0 | 0 | 2 | 1,217 | 3,206 |
| 4 | 877 | 30 | 806 | 219 | 0 | 0 | 48 | 5,430 | 21 | 7,431 |
| 5 | 19,313 | 998 | 0 | 0 | 21,640 | 0 | 0 | 126 | 0 | 42,077 |
| 6 | 0 | 0 | 72 | 37,418 | 0 | 0 | 0 | 1 | 0 | 37,491 |
| 7 | 59,511 | 9 | 3,463 | 0 | 35,403 | 7 | 1 | 0 | 0 | 98,394 |
| 8 | 393,698 | 0 | 15 | 11 | 48,255 | 0 | 0 | 0 | 3 | 441,982 |
| 9 | 1 | 1 | 1 | 28 | 4 | 1 | 1 | 1 | 105 | 143 |
<!-- src: data/processed/partitions/label_distribution_a0.1_s42.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=0.1, seed 1337 {#tab:silo-a01-s1337 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1,056,872 | 9 | 0 | 10,114 | 2 | 0 | 0 | 62 | 0 | 1,067,059 |
| 1 | 39 | 3 | 0 | 2,478 | 259 | 0 | 0 | 0 | 4 | 2,783 |
| 2 | 0 | 0 | 0 | 259 | 12 | 4 | 0 | 2,425 | 0 | 2,700 |
| 3 | 4,226 | 29 | 1,151 | 1 | 1,818 | 1 | 1 | 655 | 0 | 7,882 |
| 4 | 10,615 | 1,923 | 3,494 | 289 | 303 | 2 | 0 | 0 | 7 | 16,633 |
| 5 | 0 | 0 | 288 | 22 | 10 | 0 | 5 | 25,292 | 136 | 25,753 |
| 6 | 47 | 304 | 0 | 56,464 | 0 | 0 | 2 | 39,051 | 1,393 | 97,261 |
| 7 | 388 | 233 | 1 | 1,541 | 14,424 | 0 | 18 | 0 | 1 | 16,606 |
| 8 | 0 | 16 | 0 | 0 | 8 | 0 | 23 | 789 | 0 | 836 |
| 9 | 8,487 | 1,010 | 295 | 190 | 116,282 | 1 | 1 | 71,346 | 1 | 197,613 |
<!-- src: data/processed/partitions/label_distribution_a0.1_s1337.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=0.1, seed 2024 {#tab:silo-a01-s2024 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 4,392 | 3 | 0 | 60 | 41,074 | 0 | 0 | 346 | 0 | 45,875 |
| 1 | 28,871 | 1 | 2,130 | 9,179 | 1,796 | 3 | 0 | 0 | 19 | 41,999 |
| 2 | 1,730 | 8 | 0 | 3,172 | 65 | 0 | 0 | 43,211 | 98 | 48,284 |
| 3 | 122 | 0 | 365 | 0 | 0 | 0 | 0 | 88,315 | 0 | 88,802 |
| 4 | 10,274 | 1,404 | 0 | 58,785 | 2,170 | 2 | 10 | 254 | 460 | 73,359 |
| 5 | 250 | 1,300 | 0 | 0 | 65 | 0 | 0 | 7,477 | 0 | 9,092 |
| 6 | 1,004,282 | 9 | 833 | 149 | 34,140 | 2 | 0 | 0 | 0 | 1,039,415 |
| 7 | 27,420 | 799 | 162 | 0 | 5,471 | 0 | 3 | 1 | 964 | 34,820 |
| 8 | 976 | 2 | 47 | 0 | 0 | 0 | 22 | 0 | 0 | 1,047 |
| 9 | 2,357 | 1 | 1,692 | 13 | 48,337 | 1 | 15 | 16 | 1 | 52,433 |
<!-- src: data/processed/partitions/label_distribution_a0.1_s2024.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=0.5, seed 42 {#tab:silo-a05-s42 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 9,032 | 175 | 884 | 20,008 | 10,459 | 3 | 0 | 57,326 | 59 | 97,946 |
| 1 | 43,700 | 8 | 58 | 741 | 3,464 | 0 | 25 | 93 | 31 | 48,120 |
| 2 | 392,376 | 111 | 329 | 5,985 | 24,426 | 1 | 3 | 10,657 | 211 | 434,099 |
| 3 | 122 | 425 | 870 | 192 | 37,044 | 0 | 0 | 3,967 | 567 | 43,187 |
| 4 | 50,019 | 41 | 40 | 3,305 | 3,541 | 0 | 1 | 1,528 | 357 | 58,832 |
| 5 | 19 | 1,436 | 459 | 16,782 | 3,894 | 0 | 3 | 1,165 | 129 | 23,887 |
| 6 | 138,718 | 1 | 1,510 | 36 | 166 | 2 | 4 | 1,025 | 62 | 141,524 |
| 7 | 300,494 | 32 | 9 | 22,363 | 6,958 | 1 | 1 | 341 | 33 | 330,232 |
| 8 | 11,224 | 1,260 | 21 | 153 | 42,739 | 0 | 6 | 36,368 | 8 | 91,779 |
| 9 | 134,970 | 38 | 1,049 | 1,793 | 427 | 1 | 7 | 27,150 | 85 | 165,520 |
<!-- src: data/processed/partitions/label_distribution_a0.5_s42.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=0.5, seed 1337 {#tab:silo-a05-s1337 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 446,187 | 268 | 134 | 9,671 | 4,913 | 0 | 0 | 5,846 | 468 | 467,487 |
| 1 | 29,347 | 955 | 439 | 6,294 | 12,773 | 0 | 20 | 394 | 4 | 50,226 |
| 2 | 8,564 | 426 | 0 | 970 | 6,527 | 2 | 12 | 12,780 | 150 | 29,431 |
| 3 | 91,629 | 60 | 1,961 | 21,453 | 22,474 | 1 | 10 | 9,418 | 11 | 147,017 |
| 4 | 0 | 38 | 1,047 | 3,784 | 13,293 | 2 | 0 | 574 | 165 | 18,903 |
| 5 | 30,646 | 368 | 267 | 2,257 | 6,337 | 0 | 1 | 26,258 | 451 | 66,585 |
| 6 | 46,616 | 106 | 250 | 20,913 | 384 | 0 | 0 | 31,356 | 113 | 99,738 |
| 7 | 2,634 | 352 | 19 | 5,557 | 60,150 | 1 | 0 | 1,210 | 92 | 70,015 |
| 8 | 133,899 | 130 | 78 | 63 | 5,940 | 1 | 6 | 9,805 | 33 | 149,955 |
| 9 | 291,152 | 824 | 1,034 | 396 | 327 | 1 | 1 | 41,979 | 55 | 335,769 |
<!-- src: data/processed/partitions/label_distribution_a0.5_s1337.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=0.5, seed 2024 {#tab:silo-a05-s2024 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 96,295 | 157 | 2 | 17,854 | 23,904 | 0 | 3 | 11,740 | 12 | 149,967 |
| 1 | 167,756 | 111 | 1,453 | 2,131 | 454 | 3 | 1 | 359 | 237 | 172,505 |
| 2 | 77,025 | 183 | 95 | 6,741 | 8,267 | 0 | 4 | 36,866 | 34 | 129,215 |
| 3 | 44,678 | 22 | 617 | 5,000 | 3,820 | 0 | 6 | 47,262 | 442 | 101,847 |
| 4 | 121,114 | 1,009 | 114 | 76 | 21,741 | 1 | 4 | 11,035 | 0 | 155,094 |
| 5 | 51,556 | 962 | 31 | 22,666 | 10,781 | 0 | 0 | 22,565 | 33 | 108,594 |
| 6 | 164,788 | 190 | 862 | 13,612 | 505 | 1 | 4 | 2,299 | 692 | 182,953 |
| 7 | 67,949 | 740 | 472 | 173 | 26,156 | 2 | 20 | 4,080 | 8 | 99,600 |
| 8 | 285,820 | 143 | 334 | 2,555 | 36,535 | 0 | 1 | 0 | 54 | 325,442 |
| 9 | 3,693 | 10 | 1,249 | 550 | 955 | 1 | 7 | 3,414 | 30 | 9,909 |
<!-- src: data/processed/partitions/label_distribution_a0.5_s2024.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=5.0, seed 42 {#tab:silo-a50-s42 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 77,153 | 566 | 929 | 8,316 | 17,158 | 0 | 3 | 4,039 | 73 | 108,237 |
| 1 | 73,649 | 514 | 736 | 8,781 | 6,731 | 1 | 3 | 23,115 | 180 | 113,710 |
| 2 | 83,598 | 262 | 353 | 5,620 | 20,996 | 0 | 4 | 18,341 | 223 | 129,397 |
| 3 | 103,623 | 342 | 327 | 4,826 | 10,118 | 1 | 4 | 22,972 | 132 | 142,345 |
| 4 | 233,189 | 186 | 635 | 5,772 | 8,030 | 1 | 4 | 12,878 | 131 | 260,826 |
| 5 | 91,254 | 294 | 769 | 9,621 | 22,890 | 1 | 8 | 7,859 | 92 | 132,788 |
| 6 | 100,203 | 455 | 176 | 5,635 | 21,042 | 1 | 8 | 14,521 | 209 | 142,250 |
| 7 | 53,208 | 292 | 344 | 7,879 | 8,901 | 0 | 4 | 11,260 | 241 | 82,129 |
| 8 | 199,591 | 227 | 633 | 7,130 | 8,649 | 2 | 4 | 14,007 | 96 | 230,339 |
| 9 | 65,206 | 389 | 327 | 7,778 | 8,603 | 1 | 8 | 10,628 | 165 | 93,105 |
<!-- src: data/processed/partitions/label_distribution_a5.0_s42.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=5.0, seed 1337 {#tab:silo-a50-s1337 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 108,587 | 283 | 388 | 2,877 | 18,808 | 1 | 4 | 13,459 | 218 | 144,625 |
| 1 | 81,967 | 380 | 598 | 4,893 | 11,637 | 1 | 5 | 6,091 | 156 | 105,728 |
| 2 | 104,949 | 172 | 983 | 7,259 | 14,232 | 0 | 3 | 20,042 | 111 | 147,751 |
| 3 | 111,996 | 417 | 491 | 16,736 | 13,147 | 1 | 6 | 17,285 | 111 | 160,190 |
| 4 | 167,248 | 247 | 618 | 6,673 | 13,111 | 1 | 5 | 10,635 | 131 | 198,669 |
| 5 | 115,400 | 360 | 511 | 6,785 | 11,597 | 0 | 3 | 12,581 | 62 | 147,299 |
| 6 | 91,448 | 96 | 275 | 8,034 | 10,871 | 1 | 6 | 14,385 | 80 | 125,196 |
| 7 | 127,037 | 468 | 347 | 7,522 | 13,589 | 1 | 8 | 13,405 | 176 | 162,553 |
| 8 | 67,488 | 322 | 615 | 8,588 | 18,512 | 1 | 3 | 17,476 | 203 | 113,208 |
| 9 | 104,554 | 782 | 403 | 1,991 | 7,614 | 1 | 7 | 14,261 | 294 | 129,907 |
<!-- src: data/processed/partitions/label_distribution_a5.0_s1337.csv; results/partition_check.json -->

Table: Training-pool flows per silo and family, α=5.0, seed 2024 {#tab:silo-a50-s2024 size=9}
| Silo | Benign | Bot | BruteForce | DDoS | DoS | Heartbleed | Infiltration | PortScan | WebAttack | Total |
|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 277,111 | 653 | 746 | 8,085 | 4,996 | 0 | 10 | 9,938 | 147 | 301,686 |
| 1 | 125,504 | 289 | 428 | 5,938 | 16,455 | 1 | 2 | 11,232 | 107 | 159,956 |
| 2 | 122,458 | 376 | 406 | 13,133 | 9,907 | 1 | 2 | 6,705 | 157 | 153,145 |
| 3 | 114,304 | 284 | 473 | 7,752 | 12,424 | 1 | 4 | 11,088 | 254 | 146,584 |
| 4 | 45,869 | 313 | 802 | 5,101 | 30,981 | 1 | 7 | 14,797 | 153 | 98,024 |
| 5 | 56,792 | 339 | 726 | 9,736 | 18,513 | 0 | 6 | 11,695 | 292 | 98,099 |
| 6 | 128,261 | 300 | 296 | 8,772 | 10,470 | 1 | 4 | 8,956 | 121 | 157,181 |
| 7 | 111,739 | 190 | 596 | 5,876 | 8,727 | 1 | 4 | 25,068 | 108 | 152,309 |
| 8 | 59,177 | 199 | 283 | 2,836 | 9,565 | 1 | 7 | 16,908 | 71 | 89,047 |
| 9 | 39,459 | 584 | 473 | 4,129 | 11,080 | 1 | 4 | 23,233 | 132 | 79,095 |
<!-- src: data/processed/partitions/label_distribution_a5.0_s2024.csv; results/partition_check.json -->
