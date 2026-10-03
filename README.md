# xfed-ids

Explanation parity under non-IID federation for network intrusion detection
(explanation check), plus a demo dashboard (FastAPI backend + React frontend).
Canonical write-up: [`docs/contribution_a_results.md`](docs/contribution_a_results.md).

## Reproducing the demo data

`results/shap/<tag>/streamed_pool.npz` (500-row streamed SHAP pool) and
`results/shap/<tag>/eval_rows_sidecar.npz` (14-row eval sidecar) are **not
redistributed**. They are regenerated locally from the Distrinet CICIDS2017 V4
dataset, via `data/processed/test_global.parquet`. Each script is a one-time,
logged read of that file (see the "Test-set access note" in
`docs/contribution_a_results.md`); run from the repo root:

```bash
python -m tools.build_shap_eval_sidecar --tag fedavg_a0.5_s42
python -m tools.build_shap_streamed_pool --tag fedavg_a0.5_s42
```

`fedavg_a0.5_s42` is the served model tag (`configs/backend.yaml`, `model.tag`).
Both scripts need the trained federated checkpoint for that tag.

### Known limitations

- Manifest paths use Windows backslashes, so the backend as shipped is
  Windows-oriented.
- A fresh clone lacks `train_pool.parquet` and `val_mask.parquet` (`*.parquet`
  is git-ignored), which the backend needs at startup to refit the scaler. The
  backend only starts on a machine where the full data pipeline has been run.
- Both `.npz` files are git-ignored and were removed from tracking (`git rm
  --cached`) after being committed earlier. They remain in earlier history:
  `eval_rows_sidecar.npz` since commit `0d9a8aa`, `streamed_pool.npz` since
  commit `2823faf`. History was not rewritten, so cloning the repo still
  fetches those historical copies; the current tree does not contain them. The
  two commands above regenerate them locally.

## Dataset attribution

This project uses the Distrinet CICIDS2017 V4 dataset: Liu et al., IEEE CNS
2022, and Engelen et al., WTMC 2021. The dataset is not owned or redistributed
by this project; obtain it from its original authors. Derived data
(`*.parquet`, the demo `.npz` files) is likewise not committed.
