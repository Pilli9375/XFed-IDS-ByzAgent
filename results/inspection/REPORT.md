# XFed-IDS -- Raw Data Inspection Report
Dataset: Distrinet-CIC-IDS2017 v4 (Liu et al. 2022, IEEE CNS; extends Engelen et al. 2021, WTMC)

## 0. Files
| file                                 |   size_MB | sha256              |
|:-------------------------------------|----------:|:--------------------|
| Benign-Monday.csv                    |     222.7 | 71680844f9dfddd1... |
| Bruteforce-Tuesday.csv               |     191.3 | 50dc9ce221aaac87... |
| DoS-Wednesday.csv                    |     311.2 | 8158ca8cf307ec98... |
| Infiltration-Webattacks-Thursday.csv |     203.9 | 6789798e5b934d39... |
| Portscan-DDos-Botnet-Friday.csv      |     307.1 | 98d5268b2168600b... |
## 1. Headers
Reference file: `Benign-Monday.csv` -- **91 columns**
All five files are column-identical. Safe to concat.

Columns with leading/trailing whitespace: **0**

<details><summary>Full column list (repr)</summary>

```
  0  'id'
  1  'Flow ID'
  2  'Src IP'
  3  'Src Port'
  4  'Dst IP'
  5  'Dst Port'
  6  'Protocol'
  7  'Timestamp'
  8  'Flow Duration'
  9  'Total Fwd Packet'
 10  'Total Bwd packets'
 11  'Total Length of Fwd Packet'
 12  'Total Length of Bwd Packet'
 13  'Fwd Packet Length Max'
 14  'Fwd Packet Length Min'
 15  'Fwd Packet Length Mean'
 16  'Fwd Packet Length Std'
 17  'Bwd Packet Length Max'
 18  'Bwd Packet Length Min'
 19  'Bwd Packet Length Mean'
 20  'Bwd Packet Length Std'
 21  'Flow Bytes/s'
 22  'Flow Packets/s'
 23  'Flow IAT Mean'
 24  'Flow IAT Std'
 25  'Flow IAT Max'
 26  'Flow IAT Min'
 27  'Fwd IAT Total'
 28  'Fwd IAT Mean'
 29  'Fwd IAT Std'
 30  'Fwd IAT Max'
 31  'Fwd IAT Min'
 32  'Bwd IAT Total'
 33  'Bwd IAT Mean'
 34  'Bwd IAT Std'
 35  'Bwd IAT Max'
 36  'Bwd IAT Min'
 37  'Fwd PSH Flags'
 38  'Bwd PSH Flags'
 39  'Fwd URG Flags'
 40  'Bwd URG Flags'
 41  'Fwd RST Flags'
 42  'Bwd RST Flags'
 43  'Fwd Header Length'
 44  'Bwd Header Length'
 45  'Fwd Packets/s'
 46  'Bwd Packets/s'
 47  'Packet Length Min'
 48  'Packet Length Max'
 49  'Packet Length Mean'
 50  'Packet Length Std'
 51  'Packet Length Variance'
 52  'FIN Flag Count'
 53  'SYN Flag Count'
 54  'RST Flag Count'
 55  'PSH Flag Count'
 56  'ACK Flag Count'
 57  'URG Flag Count'
 58  'CWR Flag Count'
 59  'ECE Flag Count'
 60  'Down/Up Ratio'
 61  'Average Packet Size'
 62  'Fwd Segment Size Avg'
 63  'Bwd Segment Size Avg'
 64  'Fwd Bytes/Bulk Avg'
 65  'Fwd Packet/Bulk Avg'
 66  'Fwd Bulk Rate Avg'
 67  'Bwd Bytes/Bulk Avg'
 68  'Bwd Packet/Bulk Avg'
 69  'Bwd Bulk Rate Avg'
 70  'Subflow Fwd Packets'
 71  'Subflow Fwd Bytes'
 72  'Subflow Bwd Packets'
 73  'Subflow Bwd Bytes'
 74  'FWD Init Win Bytes'
 75  'Bwd Init Win Bytes'
 76  'Fwd Act Data Pkts'
 77  'Fwd Seg Size Min'
 78  'Active Mean'
 79  'Active Std'
 80  'Active Max'
 81  'Active Min'
 82  'Idle Mean'
 83  'Idle Std'
 84  'Idle Max'
 85  'Idle Min'
 86  'ICMP Code'
 87  'ICMP Type'
 88  'Total TCP Flow Time'
 89  'Label'
 90  'Attempted Category'
```
</details>

### Column classification
| group      |   n | columns                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|:-----------|----:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| identifier |   7 | id, Flow ID, Src IP, Src Port, Dst IP, Dst Port, Timestamp                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| label      |   1 | Label                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| attempted  |   1 | Attempted Category                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| feature    |  82 | Protocol, Flow Duration, Total Fwd Packet, Total Bwd packets, Total Length of Fwd Packet, Total Length of Bwd Packet, Fwd Packet Length Max, Fwd Packet Length Min, Fwd Packet Length Mean, Fwd Packet Length Std, Bwd Packet Length Max, Bwd Packet Length Min, Bwd Packet Length Mean, Bwd Packet Length Std, Flow Bytes/s, Flow Packets/s, Flow IAT Mean, Flow IAT Std, Flow IAT Max, Flow IAT Min, Fwd IAT Total, Fwd IAT Mean, Fwd IAT Std, Fwd IAT Max, Fwd IAT Min, Bwd IAT Total, Bwd IAT Mean, Bwd IAT Std, Bwd IAT Max, Bwd IAT Min, Fwd PSH Flags, Bwd PSH Flags, Fwd URG Flags, Bwd URG Flags, Fwd RST Flags, Bwd RST Flags, Fwd Header Length, Bwd Header Length, Fwd Packets/s, Bwd Packets/s, Packet Length Min, Packet Length Max, Packet Length Mean, Packet Length Std, Packet Length Variance, FIN Flag Count, SYN Flag Count, RST Flag Count, PSH Flag Count, ACK Flag Count, URG Flag Count, CWR Flag Count, ECE Flag Count, Down/Up Ratio, Average Packet Size, Fwd Segment Size Avg, Bwd Segment Size Avg, Fwd Bytes/Bulk Avg, Fwd Packet/Bulk Avg, Fwd Bulk Rate Avg, Bwd Bytes/Bulk Avg, Bwd Packet/Bulk Avg, Bwd Bulk Rate Avg, Subflow Fwd Packets, Subflow Fwd Bytes, Subflow Bwd Packets, Subflow Bwd Bytes, FWD Init Win Bytes, Bwd Init Win Bytes, Fwd Act Data Pkts, Fwd Seg Size Min, Active Mean, Active Std, Active Max, Active Min, Idle Mean, Idle Std, Idle Max, Idle Min, ICMP Code, ICMP Type, Total TCP Flow Time |

## 2. Labels and Attempted Category
Total rows across all five files: **2,099,976**

### 2a. Raw label counts (pooled)
| Label                                  |            flows |     pct |
|:---------------------------------------|-----------------:|--------:|
| BENIGN                                 |      1.58728e+06 | 75.5856 |
| Portscan                               | 159066           |  7.5747 |
| DoS Hulk                               | 158449           |  7.5453 |
| DDoS                                   |  95144           |  4.5307 |
| Infiltration - Portscan                |  67072           |  3.1939 |
| DoS GoldenEye                          |   7567           |  0.3603 |
| Botnet - Attempted                     |   4067           |  0.1937 |
| DoS Slowloris                          |   3998           |  0.1904 |
| FTP-Patator                            |   3972           |  0.1891 |
| DoS Slowhttptest - Attempted           |   3367           |  0.1603 |
| SSH-Patator                            |   2961           |  0.141  |
| DoS Slowhttptest                       |   1741           |  0.0829 |
| DoS Slowloris - Attempted              |   1708           |  0.0813 |
| Web Attack - Brute Force - Attempted   |   1292           |  0.0615 |
| Botnet                                 |    736           |  0.035  |
| Web Attack - XSS - Attempted           |    655           |  0.0312 |
| DoS Hulk - Attempted                   |    581           |  0.0277 |
| DoS GoldenEye - Attempted              |     80           |  0.0038 |
| Web Attack - Brute Force               |     73           |  0.0035 |
| Infiltration - Attempted               |     45           |  0.0021 |
| Infiltration                           |     36           |  0.0017 |
| SSH-Patator - Attempted                |     27           |  0.0013 |
| Web Attack - XSS                       |     18           |  0.0009 |
| Web Attack - SQL Injection             |     13           |  0.0006 |
| FTP-Patator - Attempted                |     12           |  0.0006 |
| Heartbleed                             |     11           |  0.0005 |
| Web Attack - SQL Injection - Attempted |      5           |  0.0002 |

Exact label strings (repr):
```
'BENIGN'
'Portscan'
'DoS Hulk'
'DDoS'
'Infiltration - Portscan'
'DoS GoldenEye'
'Botnet - Attempted'
'DoS Slowloris'
'FTP-Patator'
'DoS Slowhttptest - Attempted'
'SSH-Patator'
'DoS Slowhttptest'
'DoS Slowloris - Attempted'
'Web Attack - Brute Force - Attempted'
'Botnet'
'Web Attack - XSS - Attempted'
'DoS Hulk - Attempted'
'DoS GoldenEye - Attempted'
'Web Attack - Brute Force'
'Infiltration - Attempted'
'Infiltration'
'SSH-Patator - Attempted'
'Web Attack - XSS'
'Web Attack - SQL Injection'
'FTP-Patator - Attempted'
'Heartbleed'
'Web Attack - SQL Injection - Attempted'
```

### 2b. Labels present per day-file
_Relevant later: this dataset is already non-IID by day before Dirichlet partitioning touches it._

| Label                                  |   Benign-Monday.csv |   Bruteforce-Tuesday.csv |   DoS-Wednesday.csv |   Infiltration-Webattacks-Thursday.csv |   Portscan-DDos-Botnet-Friday.csv |
|:---------------------------------------|--------------------:|-------------------------:|--------------------:|---------------------------------------:|----------------------------------:|
| BENIGN                                 |              371624 |                   315106 |              319139 |                                 292867 |                            288544 |
| Botnet                                 |                   0 |                        0 |                   0 |                                      0 |                               736 |
| Botnet - Attempted                     |                   0 |                        0 |                   0 |                                      0 |                              4067 |
| DDoS                                   |                   0 |                        0 |                   0 |                                      0 |                             95144 |
| DoS GoldenEye                          |                   0 |                        0 |                7567 |                                      0 |                                 0 |
| DoS GoldenEye - Attempted              |                   0 |                        0 |                  80 |                                      0 |                                 0 |
| DoS Hulk                               |                   0 |                        0 |              158449 |                                      0 |                                 0 |
| DoS Hulk - Attempted                   |                   0 |                        0 |                 581 |                                      0 |                                 0 |
| DoS Slowhttptest                       |                   0 |                        0 |                1741 |                                      0 |                                 0 |
| DoS Slowhttptest - Attempted           |                   0 |                        0 |                3367 |                                      0 |                                 0 |
| DoS Slowloris                          |                   0 |                        0 |                3998 |                                      0 |                                 0 |
| DoS Slowloris - Attempted              |                   0 |                        0 |                1708 |                                      0 |                                 0 |
| FTP-Patator                            |                   0 |                     3972 |                   0 |                                      0 |                                 0 |
| FTP-Patator - Attempted                |                   0 |                       12 |                   0 |                                      0 |                                 0 |
| Heartbleed                             |                   0 |                        0 |                  11 |                                      0 |                                 0 |
| Infiltration                           |                   0 |                        0 |                   0 |                                     36 |                                 0 |
| Infiltration - Attempted               |                   0 |                        0 |                   0 |                                     45 |                                 0 |
| Infiltration - Portscan                |                   0 |                        0 |                   0 |                                  67072 |                                 0 |
| Portscan                               |                   0 |                        0 |                   0 |                                      0 |                            159066 |
| SSH-Patator                            |                   0 |                     2961 |                   0 |                                      0 |                                 0 |
| SSH-Patator - Attempted                |                   0 |                       27 |                   0 |                                      0 |                                 0 |
| Web Attack - Brute Force               |                   0 |                        0 |                   0 |                                     73 |                                 0 |
| Web Attack - Brute Force - Attempted   |                   0 |                        0 |                   0 |                                   1292 |                                 0 |
| Web Attack - SQL Injection             |                   0 |                        0 |                   0 |                                     13 |                                 0 |
| Web Attack - SQL Injection - Attempted |                   0 |                        0 |                   0 |                                      5 |                                 0 |
| Web Attack - XSS                       |                   0 |                        0 |                   0 |                                     18 |                                 0 |
| Web Attack - XSS - Attempted           |                   0 |                        0 |                   0 |                                    655 |                                 0 |

### 2c. Attempted Category value counts
|   Attempted Category |   flows |
|---------------------:|--------:|
|                   -1 | 2088137 |
|                    0 |    4845 |
|                    1 |    4067 |
|                    6 |    2804 |
|                    4 |      71 |
|                    3 |      27 |
|                    2 |      25 |

Distinct values (incl. null): **7** -- if this is >2, the field is a reason code, not a boolean flag.

### 2d. Label x Attempted Category crosstab
| Label                                  |      -1 |    0 |    1 |   2 |   3 |   4 |    6 |
|:---------------------------------------|--------:|-----:|-----:|----:|----:|----:|-----:|
| BENIGN                                 | 1587280 |    0 |    0 |   0 |   0 |   0 |    0 |
| Botnet                                 |     736 |    0 |    0 |   0 |   0 |   0 |    0 |
| Botnet - Attempted                     |       0 |    0 | 4067 |   0 |   0 |   0 |    0 |
| DDoS                                   |   95144 |    0 |    0 |   0 |   0 |   0 |    0 |
| DoS GoldenEye                          |    7567 |    0 |    0 |   0 |   0 |   0 |    0 |
| DoS GoldenEye - Attempted              |       0 |   80 |    0 |   0 |   0 |   0 |    0 |
| DoS Hulk                               |  158449 |    0 |    0 |   0 |   0 |   0 |    0 |
| DoS Hulk - Attempted                   |       0 |  579 |    0 |   2 |   0 |   0 |    0 |
| DoS Slowhttptest                       |    1741 |    0 |    0 |   0 |   0 |   0 |    0 |
| DoS Slowhttptest - Attempted           |       0 |  563 |    0 |   0 |   0 |   0 | 2804 |
| DoS Slowloris                          |    3998 |    0 |    0 |   0 |   0 |   0 |    0 |
| DoS Slowloris - Attempted              |       0 | 1705 |    0 |   3 |   0 |   0 |    0 |
| FTP-Patator                            |    3972 |    0 |    0 |   0 |   0 |   0 |    0 |
| FTP-Patator - Attempted                |       0 |   10 |    0 |   2 |   0 |   0 |    0 |
| Heartbleed                             |      11 |    0 |    0 |   0 |   0 |   0 |    0 |
| Infiltration                           |      36 |    0 |    0 |   0 |   0 |   0 |    0 |
| Infiltration - Attempted               |       0 |   42 |    0 |   3 |   0 |   0 |    0 |
| Infiltration - Portscan                |   67072 |    0 |    0 |   0 |   0 |   0 |    0 |
| Portscan                               |  159066 |    0 |    0 |   0 |   0 |   0 |    0 |
| SSH-Patator                            |    2961 |    0 |    0 |   0 |   0 |   0 |    0 |
| SSH-Patator - Attempted                |       0 |    0 |    0 |   0 |  27 |   0 |    0 |
| Web Attack - Brute Force               |      73 |    0 |    0 |   0 |   0 |   0 |    0 |
| Web Attack - Brute Force - Attempted   |       0 | 1214 |    0 |   7 |   0 |  71 |    0 |
| Web Attack - SQL Injection             |      13 |    0 |    0 |   0 |   0 |   0 |    0 |
| Web Attack - SQL Injection - Attempted |       0 |    1 |    0 |   4 |   0 |   0 |    0 |
| Web Attack - XSS                       |      18 |    0 |    0 |   0 |   0 |   0 |    0 |
| Web Attack - XSS - Attempted           |       0 |  651 |    0 |   4 |   0 |   0 |    0 |

_Full frame in memory: 1.57 GB, 2,099,976 rows._

## 3. Dtypes
Candidate feature columns: **82**
Non-numeric feature columns: **0**

All candidate features parsed as numeric.

## 4. Inf / NaN / zero-duration
**4 of 82** numeric features have at least one Inf, NaN, or negative value.

| column         |   +Inf |   -Inf |   NaN |   negative | suspicious_negative   |
|:---------------|-------:|-------:|------:|-----------:|:----------------------|
| Flow Bytes/s   |      5 |      0 |     0 |          0 | False                 |
| Flow Packets/s |      5 |      0 |     0 |          0 | False                 |
| ICMP Code      |      0 |      0 |     0 |    2099373 | False                 |
| ICMP Type      |      0 |      0 |     0 |    2099373 | False                 |

Rows with at least one Inf or NaN: **5** (0.0002%)

`Flow Duration` == 0: **5** rows (direct cause of rate-column Inf)

## 5. Duplicates
- Exact duplicate rows (features + label): **384,258** (18.2982%)
- Feature-identical rows (label ignored): **385,130**
- Implied feature-identical but label-CONFLICTING: **872**

### 5a. Which labels carry duplicate mass
| Label                     |   rows_in_dup_groups |
|:--------------------------|---------------------:|
| BENIGN                    |               222500 |
| Portscan                  |               157753 |
| Infiltration - Portscan   |                63747 |
| Botnet - Attempted        |                 3645 |
| DoS Slowloris - Attempted |                    6 |
| DoS Hulk - Attempted      |                    2 |

Duplicate groups spanning MORE THAN ONE day-file: **47,940**
_Cross-file duplicates suggest capture overlap, not just repeated traffic._

**Conflicting labels exist.** These cap achievable macro-F1 and need an explicit resolution rule (drop all, majority vote, or keep-first) recorded in data/README.md.

## 6. Constant / near-constant features
**0** strictly constant, **8** near-constant (top value covers >= 99.9% of rows).

| column              |   n_unique |   top_value |   top_value_frac | constant   |
|:--------------------|-----------:|------------:|-----------------:|:-----------|
| Bwd URG Flags       |          2 |           0 |         1        | False      |
| Subflow Bwd Packets |          2 |           0 |         0.999984 | False      |
| Fwd URG Flags       |          5 |           0 |         0.999956 | False      |
| URG Flag Count      |          5 |           0 |         0.999955 | False      |
| ICMP Type           |          5 |          -1 |         0.999713 | False      |
| ICMP Code           |          6 |          -1 |         0.999713 | False      |
| ECE Flag Count      |          5 |           0 |         0.999673 | False      |
| CWR Flag Count      |          9 |           0 |         0.999636 | False      |

Candidate features surviving this check: **74** of 82

---

**Nothing was decided or written by this script.** Attempted handling, dedup rule, 14->8 mapping, floor exclusions, and the final feature list are all still open.
