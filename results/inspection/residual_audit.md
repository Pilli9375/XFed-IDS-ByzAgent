# Additivity residual audit (read-only)

Produced by `python -m tools.residual_audit` (2026-10-14). The data is in
`residual_audit.csv`, one row per file, and the aggregates are in
`residual_audit_summary.json`. Only stored SHAP files are read: no model was
run and no test rows were read.
Silo rows also carry `n_flows` and `size_rank_in_config` (1 = smallest of the
10 silos), from `silo_sizes.csv`.

## Scope

The audit covers 594 SHAP files: FedAvg and FedProx μ=0.0005, every α × seed,
the global model and all 10 silos.

| Pass | Files |
|---|---|
| Final checkpoints, FedAvg | 99 |
| Final checkpoints, FedProx | 99 |
| Round-wise (rounds 5/10/15/20, nsamples=1000), FedAvg only | 396 |

## What the residual measures

Each file stores one scalar, `additivity_max_diff`: the largest
|ΣSHAP − (f(x) − E[f])| over that file's 14 fixed eval rows and 9 classes, in
logit units.

The reference value 3.336 is the largest **per-row** value in the 500-row
validation pool (`results/shap/fedavg_a0.5_s42/val_pool_summary.json`).
Because each file's scalar is a maximum over 14 rows, the comparison is a
coarse flag, not a like-for-like test.

## Files above 3.336

| Pass | Above 3.336 | By α (0.1 / 0.5 / 5.0) | Median | Max |
|---|---|---|---|---|
| FedAvg, final | 4 / 99 | 3 / 0 / 1 | 0.895 | 11.955 |
| FedProx, final | 1 / 99 | 1 / 0 / 0 | 0.562 | 4.258 |
| FedAvg, round-wise | 31 / 396 | 26 / 0 / 5 | 1.454 | 15.874 |

**The exceedances cluster by α.** None of them occur at α=0.5.

**Within α=0.1 they cluster by silo.** A silo here means a (seed, silo) pair:
silo indices name different partitions in different seeds.

- FedAvg final:
  - α=0.1 seed 42, silos 3 (4.193; 3,206 flows, 3rd smallest) and 9 (11.955; 143 flows, smallest)
  - α=0.1 seed 1337, silo 8 (6.576; 836 flows, smallest)
  - α=5.0 seed 1337, global model (3.500)
- FedProx final: α=0.1 seed 42, silo 9 (4.258)
- Round-wise: the same few silos recur across rounds.
  - α=0.1 seed 42: silos 3, 6 and 9
  - α=0.1 seed 1337: silos 1, 2 and 8

## Spearman correlation: silo residual vs silo Jaccard@10, within α

r and n only, no p-values.

Per-silo Jaccard@10 is the median over family-eligible rows, the same
aggregation as `per_silo_agreement.csv`. Re-applying it reproduces that file
(max difference 5.6e-17).

| | α=0.1 | α=0.5 | α=5.0 |
|---|---|---|---|
| FedAvg, final | r=−0.237, n=29 | r=+0.202, n=30 | r=+0.110, n=30 |
| FedProx, final | r=−0.207, n=29 | r=+0.431, n=30 | r=−0.078, n=30 |
| FedAvg round-wise, round 5 / 10 / 15 / 20 (n=29 at α=0.1, otherwise 30) | −0.441 / −0.428 / −0.222 / −0.200 | +0.135 / +0.285 / +0.025 / +0.334 | +0.167 / −0.425 / +0.036 / −0.100 |

No wording or results elsewhere were changed by this audit.
