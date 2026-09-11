"""Label-flip poisoning attack. ByzAgent Contribution B, Phase 0.

PoisonedClient wraps the output of the EXISTING loader (load_silo() /
load_silo_for_client()) -- it does not fork or reimplement client training.

CANONICAL SOURCE. federated/xfed_federated/ runs inside Flower's isolated
simulation runtime, which cannot see this src/ tree (same reason
src/data/loaders.py, src/data/schema.py, src/models/mlp.py, and
src/train/metrics.py are vendored there). This file is therefore vendored
too, at federated/xfed_federated/_vendored/label_flip.py -- edit HERE, then
re-copy before your next `flwr run`, exactly like the other four modules.
See the header comment in that copy.

The actual federated harness that produced every locked result in
results/federated/ is federated/xfed_federated/ (via
`flwr run federated local-simulation`), NOT src/federated/ (root
pyproject.toml's target, which has no best-by-validation checkpoint
selection and is not what any reported number came from). The call site is
therefore federated/xfed_federated/client_app.py's train(), which inserts
one call between `load_silo_for_client()` and everything downstream of it:

    splits = load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)
    if attack_cfg.get("enabled", False):
        splits = poisoner.poison_and_log(splits, silo_id, server_round)
    model = build_model(...)                      # unchanged
    local_train_epochs(model, splits, ...)         # unchanged

Flipping touches splits.y_train ONLY. splits.y_val and splits.y_test are
never read or written here -- validation and test integrity are the caller's
responsibility to preserve by not passing them in, which client_app.py
already does not.

Reproducibility: which silos are malicious is read verbatim from
configs/attack.yaml (attack.malicious_silos) -- an explicit, logged list, not
re-derived per call. Within a malicious silo, which specific rows get
flipped is deterministic given (attack_seed, silo_id, server_round) via
numpy's SeedSequence-based Generator.

Place at: src/attacks/label_flip.py
"""

from __future__ import annotations

import csv
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..data.schema import load_label_vocabulary

LOG_COLUMNS = (
    "silo_id", "round", "is_malicious", "flip_fraction",
    "n_rows_flipped", "n_rows_total", "attack_seed",
    "partition_seed", "alpha", "mode",
)


# ---------------------------------------------------------------------------
# malicious silo selection
# ---------------------------------------------------------------------------

def resolve_malicious_silos(attack_cfg: dict, n_silos: int) -> list[int]:
    """The explicit list of record. Reads attack_cfg['malicious_silos'] if
    non-empty; only falls back to a seeded derivation for convenience.

    The fallback NEVER uses the data partition seed -- it uses attack_seed, a
    separate value. Reusing the partition seed would couple "which silos are
    attacked" to "which silos are big" (Dirichlet partitioning makes silo
    size a deterministic side effect of the seed that drew the label split),
    making a weak attack indistinguishable from an accidentally-small
    poisoned sample. See configs/attack.yaml for the full rationale.
    """
    f = int(attack_cfg["f"])
    explicit = attack_cfg.get("malicious_silos")

    if explicit:
        resolved = sorted(int(s) for s in explicit)
        if len(resolved) != f:
            raise ValueError(
                f"attack.yaml: malicious_silos has {len(resolved)} entries but f={f}"
            )
        if len(set(resolved)) != len(resolved):
            raise ValueError(f"attack.yaml: malicious_silos contains duplicates: {resolved}")
        if any(s < 0 or s >= n_silos for s in resolved):
            raise ValueError(
                f"attack.yaml: malicious_silos {resolved} out of range for n_silos={n_silos}"
            )
        return resolved

    attack_seed = int(attack_cfg["attack_seed"])
    return sorted(random.Random(attack_seed).sample(range(n_silos), f))


# ---------------------------------------------------------------------------
# round number
# ---------------------------------------------------------------------------

def get_server_round(msg) -> int:
    """Defensive extraction of the current FL round.

    Flower's FedAvg/FedProx configure_train() always injects
    config["server-round"] into the training message (flwr/serverapp/
    strategy/fedavg.py). A missing key means this Message did not come from
    the normal strategy.start() path. Silently defaulting to round 0 or 1
    would pin a 'gradual' ramp at its start fraction for the entire run and
    present as a weak-attack failure at the verification gate -- fail loudly
    instead.
    """
    try:
        return int(msg.content["config"]["server-round"])
    except (KeyError, TypeError, AttributeError) as e:
        raise RuntimeError(
            "msg.content['config']['server-round'] is missing or unreadable -- "
            "cannot determine the current FL round. Refusing to default silently."
        ) from e


# ---------------------------------------------------------------------------
# flip fraction schedule
# ---------------------------------------------------------------------------

def compute_flip_fraction(attack_cfg: dict, server_round: int) -> float:
    if server_round < 1:
        raise ValueError(f"server_round must be >= 1, got {server_round}")

    mode = attack_cfg["mode"]
    if mode == "sudden":
        return float(attack_cfg["sudden"]["flip_fraction"])
    if mode == "gradual":
        g = attack_cfg["gradual"]
        start = float(g["start_fraction"])
        inc = float(g["increment_per_round"])
        cap = float(g.get("max_fraction", 1.0))
        return min(start + inc * (server_round - 1), cap)
    raise ValueError(f"unknown attack.mode {mode!r}")


# ---------------------------------------------------------------------------
# label flipping
# ---------------------------------------------------------------------------

def flip_labels(
    y_train: np.ndarray,
    vocab: dict[str, int],
    attack_cfg: dict,
    flip_fraction: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """Returns (flipped copy of y_train, n_rows_flipped). Never mutates the input.

    strategy == "targeted_to_benign": flip_fraction is a fraction of the
    ELIGIBLE rows (true label != target class), not of all rows -- flipping
    an already-Benign row to Benign is a no-op, and defining the fraction
    over all rows would make it mean a different thing in every silo
    depending on that silo's (Dirichlet-skewed) Benign share.

    strategy == "random_permutation": flip_fraction is a fraction of all
    rows; each selected row's label moves to a uniformly random class other
    than its own.
    """
    strategy = attack_cfg["strategy"]
    y_out = y_train.copy()
    n_classes = len(vocab)

    if strategy == "targeted_to_benign":
        target_name = attack_cfg["targeted_to_benign"]["target_class"]
        if target_name not in vocab:
            raise ValueError(f"attack.yaml: target_class {target_name!r} not in label vocabulary")
        target_idx = vocab[target_name]
        eligible = np.flatnonzero(y_out != target_idx)
    elif strategy == "random_permutation":
        eligible = np.arange(len(y_out))
    else:
        raise ValueError(f"unknown attack.strategy {strategy!r}")

    n_eligible = len(eligible)
    n_flip = min(int(round(flip_fraction * n_eligible)), n_eligible)
    if n_flip == 0:
        return y_out, 0

    chosen = rng.choice(eligible, size=n_flip, replace=False)

    if strategy == "targeted_to_benign":
        y_out[chosen] = target_idx
    else:
        # offset in [1, n_classes-1] guarantees the new label != the original
        offset = rng.integers(1, n_classes, size=n_flip)
        y_out[chosen] = (y_out[chosen] + offset) % n_classes

    return y_out, n_flip


# ---------------------------------------------------------------------------
# logging -- concurrency-safe append (Flower simulation may run silos as
# separate Ray worker processes)
# ---------------------------------------------------------------------------

def _acquire_lock(lock_path: Path, timeout: float = 30.0, poll: float = 0.05) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"could not acquire lock {lock_path} within {timeout}s")
            time.sleep(poll)


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def append_flip_log(row: dict, tag: str, results_dir: str | Path = "results/attacks") -> Path:
    """Append one row to results/attacks/{tag}/flip_log.csv, creating the file
    and header if needed. Locked so concurrent silo processes cannot
    interleave partial writes into the audit trail.
    """
    out_dir = Path(results_dir) / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "flip_log.csv"
    lock_path = out_dir / "flip_log.csv.lock"

    _acquire_lock(lock_path)
    try:
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(LOG_COLUMNS))
            if write_header:
                writer.writeheader()
            writer.writerow({k: row[k] for k in LOG_COLUMNS})
    finally:
        _release_lock(lock_path)
    return csv_path


def write_attack_manifest(attack_cfg: dict, malicious_silos: list[int], tag: str,
                           alpha: str, partition_seed: int,
                           results_dir: str | Path = "results/attacks") -> Path:
    """Writes the RESOLVED explicit attack configuration for this run.
    Derivation (resolve_malicious_silos' seeded fallback) is for convenience;
    this file is the record. Atomic write (temp + os.replace) so concurrent
    silo processes never observe a torn file.
    """
    out_dir = Path(results_dir) / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "attack_config.json"
    tmp_path = out_dir / f"attack_config.json.tmp.{os.getpid()}"

    payload = {
        "tag": tag,
        "alpha": alpha,
        "partition_seed": partition_seed,
        "f": int(attack_cfg["f"]),
        "attack_seed": int(attack_cfg["attack_seed"]),
        "malicious_silos": malicious_silos,
        "mode": attack_cfg["mode"],
        "strategy": attack_cfg["strategy"],
        "sudden": attack_cfg.get("sudden"),
        "gradual": attack_cfg.get("gradual"),
        # Self-documenting adversary framing -- survives independently of
        # whatever comment sits in configs/attack.yaml at read time. See
        # PROJECT_INSTRUCTIONS.md: never present a full-global-knowledge
        # silo selection as a realistic/naturalistic attacker.
        "selection_note": attack_cfg.get("selection_note"),
    }
    tmp_path.write_text(json.dumps(payload, indent=2))
    os.replace(tmp_path, manifest_path)
    return manifest_path


# ---------------------------------------------------------------------------
# PoisonedClient
# ---------------------------------------------------------------------------

@dataclass
class PoisonedClient:
    """Wraps a silo's already-loaded Splits, flipping local training labels
    if this silo is designated malicious for this run. Constructed fresh per
    call in client_app.py, consistent with that module's stated invariant
    that ClientApp functions carry no state across Messages.
    """

    attack_cfg: dict
    model_cfg: dict
    n_silos: int
    alpha: str
    partition_seed: int
    tag: str

    def __post_init__(self) -> None:
        self._vocab = load_label_vocabulary(self.model_cfg)
        self._malicious_silos = resolve_malicious_silos(self.attack_cfg, self.n_silos)
        write_attack_manifest(
            self.attack_cfg, self._malicious_silos, self.tag,
            self.alpha, self.partition_seed,
            results_dir=self.attack_cfg.get("log", {}).get("results_dir", "results/attacks"),
        )

    @property
    def malicious_silos(self) -> list[int]:
        return list(self._malicious_silos)

    def poison_and_log(self, splits, silo_id: int, server_round: int):
        """Mutates splits.y_train in place if silo_id is malicious, and
        appends exactly one audit row per (silo_id, round) either way. A
        clean silo's row has flip_fraction=0.0 / n_rows_flipped=0 --
        absence of a row and a zero row are different things; this never
        leaves a malicious-eligible-but-clean silo unlogged.
        """
        is_malicious = silo_id in self._malicious_silos
        n_total = int(len(splits.y_train))

        if is_malicious:
            flip_fraction = compute_flip_fraction(self.attack_cfg, server_round)
            rng = np.random.default_rng([int(self.attack_cfg["attack_seed"]), silo_id, server_round])
            y_flipped, n_flipped = flip_labels(
                splits.y_train, self._vocab, self.attack_cfg, flip_fraction, rng
            )
            splits.y_train = y_flipped
        else:
            flip_fraction = 0.0
            n_flipped = 0

        row = {
            "silo_id": silo_id,
            "round": server_round,
            "is_malicious": is_malicious,
            "flip_fraction": flip_fraction,
            "n_rows_flipped": n_flipped,
            "n_rows_total": n_total,
            "attack_seed": int(self.attack_cfg["attack_seed"]),
            "partition_seed": self.partition_seed,
            "alpha": self.alpha,
            "mode": self.attack_cfg["mode"],
        }
        append_flip_log(row, self.tag, self.attack_cfg.get("log", {}).get("results_dir", "results/attacks"))
        return splits
