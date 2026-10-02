#!/usr/bin/env python
"""One-time offline script: pregenerates one analyst-readable sentence per
row of the dashboard's precomputed SHAP set (Step 8, LLM explanation layer).

Why offline, not live: this project is offline-capable end-to-end (verified,
network off, zero external requests) and the demo's GPU budget is already
committed -- ByzAgent (src/agents/byz_agent.py) holds ~4.8GB VRAM resident on
the 6GB card for llama3.1:8b-instruct-q4_K_M during live aggregation rounds.
A second concurrent model call at serve time would contend for that same
budget and risks visible swap latency mid-demo. The row set this covers is
closed (14 curated + 500 streamed -- exactly what GET /shap/{sample_id}
already serves and nothing else), so there is no live case this can't cover
by precomputing once. See PROJECT_INSTRUCTIONS.md: "The LLM explanation
layer is usability, never novelty" -- enforced here at generation time (see
_BANNED_WORDS below), not left to the served string alone.

Reuses backend.model_loader.load_and_verify() for the model + scaler --
NOT app_lib.loaders' Streamlit-cached copies -- so predicted_family and
confidence here are bit-identical to what POST /predict would return for
these exact raw feature values. Reads results/shap/<tag>/global_shap.npz +
eval_rows_sidecar.npz (14 curated rows) and streamed_pool.npz (500 rows,
Step 7) -- all three read-only, same posture as every other tools/build_*
script in this project.

Talks to Ollama over http://localhost:11434 -- loopback only, never the
internet; this is what "no network call at serve time" is protecting
against, not local inter-process calls.

Writes results/explanations/<tag>/sentences.json, keyed by sample_id
(string keys, JSON's only option -- backend/main.py casts back to int on
load, same pattern as the streamed pool's in-memory index).

Run as:
    python -m tools.build_explanations --tag fedavg_a0.5_s42 --limit 5   # sanity check first
    python -m tools.build_explanations --tag fedavg_a0.5_s42             # full 514-row run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.model_loader import load_and_verify  # noqa: E402

SHAP_ROOT = ROOT / "results" / "shap"
EXPLANATIONS_ROOT = ROOT / "results" / "explanations"

log = logging.getLogger("build_explanations")

DEFAULT_MODEL = "llama3.1:8b-instruct-q4_K_M"
DEFAULT_HOST = "http://localhost:11434"
TOP_K = 5

# Enforced at generation time, not just documented: PROJECT_INSTRUCTIONS.md's
# "usability, never novelty" framing must never leak into a served sentence.
# Substring, case-insensitive.
_BANNED_WORDS = (
    "first", "novel", "novelty", "discover", "breakthrough", "state-of-the-art",
    "state of the art", "cutting-edge", "cutting edge", "groundbreaking",
    "unprecedented", "pioneering", "revolutionary",
)

PROMPT_TEMPLATE = """You are writing a one-sentence explanation for a security analyst reviewing an intrusion-detection alert. This is a usability aid describing what the model already computed -- not a research claim, not a discovery.

The model classified this network flow as "{family}" with {confidence_pct:.1f}% confidence.

The features that contributed most to this classification (from SHAP, ranked by contribution magnitude, {top_k} shown):
{feature_lines}

Write exactly ONE sentence (max 30 words) for the analyst, in plain prose, that explains the classification by referencing the actual feature names and values above. Rules:
- Output ONLY the sentence. No preamble, no quotation marks, no markdown, no bullet points.
- Do not use the words "first", "novel", "discover", "breakthrough", "state-of-the-art", "cutting-edge", "groundbreaking", "unprecedented", or "pioneering" -- this must never read as a novelty or research claim.
- Do not mention "SHAP", "the model", or add caveats/disclaimers -- just state what drove the classification.
"""


def _verify_feature_alignment(npz_feature_names: list[str], loaded_feature_cols: list[str], source: str) -> None:
    """Same discipline as tools/build_shap_streamed_pool.py's
    _verify_feature_order(): re-assert on every run rather than trust that a
    prior script's check still holds, because a silent mismatch here would
    misattribute every generated sentence to the wrong feature."""
    if npz_feature_names != loaded_feature_cols:
        first_mismatch = next(
            (i for i, (a, b) in enumerate(zip(npz_feature_names, loaded_feature_cols)) if a != b), None
        )
        raise RuntimeError(
            f"{source}'s feature_names does not match backend/model_loader.py's "
            f"feature_cols order (first mismatch at index {first_mismatch}). Refusing "
            f"to generate sentences that would reference the wrong feature."
        )


def _format_raw(v: float) -> str:
    return f"{v:.4g}"


def _top_k_features(shap_row: np.ndarray, raw_row: np.ndarray, feature_cols: list[str], k: int) -> list[dict]:
    """shap_row: (82,) SHAP contributions to the PREDICTED class only (not
    ground truth) -- an analyst sees the model's own reasoning for the
    label it actually output. Ranked by absolute contribution, sign kept so
    the prompt (and the served response) can say whether each feature
    pushed toward or away from the predicted class."""
    order = np.argsort(-np.abs(shap_row))[:k]
    return [
        {
            "name": feature_cols[j],
            "raw_value": float(raw_row[j]),
            "shap_value": float(shap_row[j]),
        }
        for j in order
    ]


def _build_prompt(family: str, confidence: float, top_features: list[dict]) -> str:
    lines = []
    for f in top_features:
        direction = "raises" if f["shap_value"] > 0 else "lowers"
        lines.append(
            f"- {f['name']} = {_format_raw(f['raw_value'])} "
            f"(SHAP {f['shap_value']:+.4f}, {direction} the likelihood of {family})"
        )
    return PROMPT_TEMPLATE.format(
        family=family, confidence_pct=confidence * 100, top_k=len(top_features),
        feature_lines="\n".join(lines),
    )


def _call_ollama(prompt: str, model: str, host: str, temperature: float, keep_alive: str, timeout: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{host}/api/generate", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("response", "")


def _clean_sentence(text: str) -> str:
    s = text.strip()
    # Model sometimes wraps in quotes or emits a stray leading/trailing newline
    # despite the prompt's instruction -- strip, never silently accept a
    # multi-line response as "one sentence".
    s = s.strip('"“”\'')
    s = " ".join(s.split())
    return s


def _violates_framing(sentence: str) -> str | None:
    lower = sentence.lower()
    for w in _BANNED_WORDS:
        if w in lower:
            return w
    return None


def _generate_one(
    prompt: str, model: str, host: str, temperature: float, keep_alive: str, timeout: int, max_retries: int
) -> tuple[str | None, str | None]:
    """Returns (sentence, exclusion_reason). Exactly one is None."""
    last_reason = None
    for attempt in range(max_retries + 1):
        try:
            raw = _call_ollama(prompt, model, host, temperature, keep_alive, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_reason = f"ollama call failed: {e}"
            continue
        sentence = _clean_sentence(raw)
        if not sentence:
            last_reason = "empty response"
            continue
        if "\n" in raw.strip():
            last_reason = f"multi-line response (not one sentence): {raw!r}"
            continue
        bad_word = _violates_framing(sentence)
        if bad_word:
            last_reason = f"banned word {bad_word!r} in generated sentence: {sentence!r}"
            continue
        return sentence, None
    return None, last_reason


def build_explanations(
    tag: str,
    model: str,
    host: str,
    top_k: int,
    temperature: float,
    keep_alive: str,
    timeout: int,
    max_retries: int,
    limit: int | None,
) -> Path:
    t0 = time.time()
    loaded = load_and_verify()
    if loaded.tag != tag:
        raise RuntimeError(
            f"--tag {tag!r} does not match configs/backend.yaml's configured model.tag "
            f"{loaded.tag!r}. load_and_verify() always loads the configured tag; point "
            f"configs/backend.yaml at {tag!r} first, or pass --tag {loaded.tag!r}."
        )
    log.info("loaded + verified model for tag=%s best_round=%d", loaded.tag, loaded.best_round)

    shap_dir = SHAP_ROOT / tag
    with np.load(shap_dir / "global_shap.npz") as npz:
        curated_shap = npz["shap_values"].copy()  # (14, 82, 9)
    with np.load(shap_dir / "eval_rows_sidecar.npz") as npz:
        curated_raw = npz["raw_values"].copy()  # (14, 82)
        curated_feature_names = list(npz["feature_names"])
    with np.load(shap_dir / "streamed_pool.npz") as npz:
        streamed_shap = npz["shap_values"].copy()  # (500, 82, 9)
        streamed_raw = npz["raw_values"].copy()
        streamed_sample_id = npz["sample_id"].copy()
        streamed_feature_names = list(npz["feature_names"])

    _verify_feature_alignment(curated_feature_names, loaded.feature_cols, "eval_rows_sidecar.npz")
    _verify_feature_alignment(streamed_feature_names, loaded.feature_cols, "streamed_pool.npz")
    log.info("feature order verified against backend/model_loader.py (%d features)", len(loaded.feature_cols))

    # (sample_id, raw_row, shap_row_all_classes, source) for all 514 rows,
    # same priority order as GET /shap/{sample_id}: curated [0,13] first.
    jobs: list[tuple[int, np.ndarray, np.ndarray, str]] = []
    for i in range(curated_raw.shape[0]):
        jobs.append((i, curated_raw[i], curated_shap[i], "curated"))
    for i in range(streamed_raw.shape[0]):
        jobs.append((int(streamed_sample_id[i]), streamed_raw[i], streamed_shap[i], "streamed"))

    if limit is not None:
        log.warning("--limit %d set: sanity-check run, NOT the full artifact", limit)
        jobs = jobs[:limit]

    scaler = loaded.scaler
    class_names = loaded.class_names
    prompt_template_sha256 = hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
    raw_concat = np.concatenate([curated_raw, streamed_raw], axis=0)
    raw_values_sha256 = hashlib.sha256(np.ascontiguousarray(raw_concat).tobytes()).hexdigest()

    log.info(
        "generating %d sentences | model=%s host=%s top_k=%d temperature=%.2f keep_alive=%s | "
        "prompt_template sha256=%s",
        len(jobs), model, host, top_k, temperature, keep_alive, prompt_template_sha256,
    )

    rows: dict[str, dict] = {}
    excluded: dict[str, str] = {}
    t_gen0 = time.time()
    for n, (sample_id, raw_row, shap_row_all, source) in enumerate(jobs):
        x_scaled = scaler.transform(raw_row.reshape(1, -1)).astype(np.float32)
        with torch.no_grad():
            loaded.model.eval()
            logits = loaded.model(torch.from_numpy(x_scaled).to(loaded.device))
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        pred_idx = int(np.argmax(probs))
        family = class_names[pred_idx]
        confidence = float(probs[pred_idx])

        top_features = _top_k_features(shap_row_all[:, pred_idx], raw_row, loaded.feature_cols, top_k)
        prompt = _build_prompt(family, confidence, top_features)

        sentence, reason = _generate_one(prompt, model, host, temperature, keep_alive, timeout, max_retries)
        if sentence is None:
            log.error("sample_id=%d EXCLUDED: %s", sample_id, reason)
            excluded[str(sample_id)] = reason
        else:
            rows[str(sample_id)] = {
                "sample_id": sample_id,
                "source": source,
                "predicted_family": family,
                "confidence": confidence,
                "top_features": top_features,
                "sentence": sentence,
            }

        if (n + 1) % 25 == 0 or (n + 1) == len(jobs):
            elapsed = time.time() - t_gen0
            rate = (n + 1) / elapsed
            log.info(
                "generated %d/%d (%d excluded) (%.2fs/row, elapsed=%.1fs, eta=%.1fs)",
                n + 1, len(jobs), len(excluded), elapsed / (n + 1), elapsed,
                (len(jobs) - n - 1) / rate if rate > 0 else float("nan"),
            )

    out_dir = EXPLANATIONS_ROOT / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sentences.json"
    payload = {
        "tag": tag,
        "model": model,
        "prompt_template_sha256": prompt_template_sha256,
        "raw_values_sha256": raw_values_sha256,
        "top_k": top_k,
        "temperature": temperature,
        "n_rows": len(rows),
        "n_excluded": len(excluded),
        "excluded": excluded,
        "rows": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2))

    elapsed = time.time() - t0
    log.info(
        "WROTE %s | tag=%s | model=%s | rows=%d excluded=%d | prompt_template sha256=%s | "
        "raw_values sha256=%s | elapsed=%.1fs (%.2fmin)",
        out_path, tag, model, len(rows), len(excluded), prompt_template_sha256,
        raw_values_sha256, elapsed, elapsed / 60,
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="e.g. fedavg_a0.5_s42")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--keep-alive", default="10m",
                         help="Ollama keep_alive for this batch run. Safe to keep the model resident "
                              "across all 514 calls here (offline, one-time, not running concurrently "
                              "with a live ByzAgent demo) -- see module docstring for why that's NOT "
                              "true at serve time.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None,
                         help="TEST ONLY: generate only the first N rows, for sanity-checking output "
                              "quality before committing to the full 514-row run.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    build_explanations(
        tag=args.tag, model=args.model, host=args.host, top_k=args.top_k,
        temperature=args.temperature, keep_alive=args.keep_alive, timeout=args.timeout,
        max_retries=args.max_retries, limit=args.limit,
    )


if __name__ == "__main__":
    main()
