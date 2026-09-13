"""FastAPI app skeleton for the Phase 2 dashboard backend.

Read-only, serving endpoints plus the in-memory alert buffer that
backend/simulator.py feeds over HTTP, plus the read-only ByzAgent trust
panel (GET /trust). Still no hot-swap, no LLM layer here -- those come
after the React port.

Every path this module reads lives in configs/backend.yaml (via
backend.model_loader.load_backend_config / resolve_path). If startup
verification fails, the app does not serve -- see lifespan() below.

Place at: backend/main.py
Run as:   uvicorn backend.main:app --reload
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from backend.model_loader import LoadedModel, load_and_verify, load_backend_config, resolve_path
from backend.trust import build_trust_snapshot
from backend.federation import build_federation_snapshot
from backend.faithfulness import build_faithfulness_snapshot, load_faithfulness_figures
from backend.hotswap_service import HotSwapState, new_state, poll, revert, trigger

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# response/request models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    scaler_sha256: str
    uptime_seconds: float


class HotSwapInfo(BaseModel):
    """Additive to ConfigResponse -- see that model. Every field here
    describes whether the model actually answering /predict right now
    differs from the base_tag/alpha/seed/best_round reported above it,
    which never change regardless of hot-swap state."""

    active: bool
    event_id: str | None
    swap_depth: int
    base_tag: str
    job_status: str | None = Field(
        default=None,
        description="Last known worker status: running / accepted / rejected / error / crashed / null (no job ever run).",
    )
    job_detail: str | None = None


class ConfigResponse(BaseModel):
    # Unchanged by hot-swap state -- always describes the base model
    # loaded at startup (backend/model_loader.py::load_and_verify()),
    # exactly as before Step 2B. This is deliberate: every number already
    # rendered elsewhere on the dashboard (agreement, parity, faithfulness,
    # federation) was computed against THIS model, not whatever /predict
    # might currently be routing to -- see `hotswap` below for that.
    alpha: str
    seed: int
    tag: str
    best_round: int
    n_features: int
    n_classes: int
    hotswap: HotSwapInfo


class HotSwapTriggerRequest(BaseModel):
    family: str = Field(
        ...,
        description="A family label only -- confirming or correcting an alert's predicted_family. "
                    "Never a feature vector; see backend/hotswap_service.py's module docstring for why.",
    )


class HotSwapTriggerResponse(BaseModel):
    job_id: str
    status: str
    family: str
    seed: int


class HotSwapStatusResponse(BaseModel):
    job_id: str | None
    status: str | None
    detail: str | None
    family: str | None = Field(default=None, description="Family label the current/last job was triggered with.")
    hotswap: HotSwapInfo


class PredictRequest(BaseModel):
    # Keyed by feature name, not position -- the 82-wide ordering is an
    # internal implementation detail (schema.derive_feature_cols), not
    # something a caller should have to know or get silently wrong.
    features: dict[str, float] = Field(..., description="Exactly the 82 feature names from GET /config's model, each mapped to its raw (unscaled) value.")
    # Not a model input -- never touches the scaler or the forward pass.
    # backend/simulator.py has this from the test_global.parquet row it read
    # (the model does not); carried through only so the alert this call
    # produces can show ground truth. Any caller without it just gets a
    # true_family=null alert.
    true_family: str | None = Field(
        default=None,
        description="Ground truth family for the source row, if the caller has it (e.g. the traffic simulator). Ignored by the model.",
    )
    # Opt-in, default False. Every /predict caller -- the React frontend,
    # manual debugging calls, the future hot-swap flow -- hits this same
    # endpoint, and only backend/simulator.py's replayed rows are real
    # traffic with a source row behind them. Defaulting True would put a
    # phantom alert on screen (true_family: null) for every incidental
    # call, which reads as a fabricated number during a live demo even
    # though it isn't one.
    record_alert: bool = Field(
        default=False,
        description="Set True only by the traffic simulator. Any other caller leaves this False so an incidental /predict call does not appear in GET /alerts.",
    )


class PredictResponse(BaseModel):
    family: str
    confidence: float
    # All 9 classes, keyed by family name (not a positional array) -- same
    # reasoning as PredictRequest.features: the caller shouldn't have to
    # know or get an implicit class-index order right. Keys are exactly
    # loaded.class_names, i.e. the frozen vocab from configs/model.yaml via
    # src.data.schema, same source /predict already used for `family`.
    probabilities: dict[str, float]


class Alert(BaseModel):
    timestamp: str
    predicted_family: str
    confidence: float
    true_family: str | None
    # Always False here: the only precomputed SHAP artifact is a fixed
    # 14-row curated set (see GET /shap/{sample_id}) that carries no link
    # back to test_global.parquet rows -- confirmed in Step 0, and this is
    # exactly the scope collision that was routed to planning rather than
    # papered over with a fake link, a sample drawn from the 14, or a live
    # SHAP computation (forbidden -- /shap never computes). Every alert this
    # buffer ever holds will have shap_available=False until that collision
    # is actually resolved upstream.
    shap_available: bool


class ShapResponse(BaseModel):
    sample_id: int
    tag: str
    eval_family: str
    feature_names: list[str]
    class_names: list[str]
    shap_values: list[list[float]]  # [feature][class]
    # One value for the whole tag's global SHAP computation (not per-sample
    # -- the .npz stores exactly one), attached to every sample_id's
    # response as-is. From global_shap.npz, loaded at startup; never
    # recomputed here.
    additivity_max_diff: float
    # From results/shap/<tag>/eval_rows_sidecar.npz (tools/build_shap_eval_sidecar.py,
    # run offline, once -- see that script for why: the raw feature values
    # and base_values are not in global_shap.npz and were never persisted
    # anywhere else). Positional, aligned to feature_names/class_names
    # exactly like shap_values above, not name-keyed. raw_values is
    # UNSCALED -- verified to round-trip through POST /predict to the same
    # family eval_y says this row is, for all 14 rows, before this field
    # was wired up.
    raw_values: list[float]  # length 82, aligned to feature_names
    base_values: list[float]  # length 9, aligned to class_names


# ---------------------------------------------------------------------------
# startup
# ---------------------------------------------------------------------------

def _load_shap_arrays(loaded: LoadedModel, cfg_paths: dict) -> dict[str, np.ndarray]:
    """Loads results/shap/<tag>/<shap_filename>.npz AND its sidecar
    (<shap_sidecar_filename>.npz, built offline by
    tools/build_shap_eval_sidecar.py) fully into memory, merges them into
    one dict, and closes both files -- neither handle is kept open, and
    /shap never touches disk again after startup. The sidecar is required,
    not optional: if it's missing, run that script by hand first rather
    than silently serving /shap without raw_values/base_values."""
    shap_dir = resolve_path(cfg_paths, "shap_dir")
    shap_path = shap_dir / loaded.tag / cfg_paths["shap_filename"]
    if not shap_path.exists():
        raise RuntimeError(f"SHAP artifact {shap_path} does not exist for tag={loaded.tag}.")
    with np.load(shap_path) as npz:
        arrays = {k: npz[k].copy() for k in npz.files}
    required = {"shap_values", "eval_y", "eval_families"}
    missing = required - arrays.keys()
    if missing:
        raise RuntimeError(f"{shap_path} is missing expected array(s) {missing}.")
    log.info("loaded SHAP artifact %s: shap_values.shape=%s", shap_path, arrays["shap_values"].shape)

    sidecar_path = shap_dir / loaded.tag / cfg_paths["shap_sidecar_filename"]
    if not sidecar_path.exists():
        raise RuntimeError(
            f"SHAP eval-rows sidecar {sidecar_path} does not exist for tag={loaded.tag}. "
            f"Run `python -m tools.build_shap_eval_sidecar --tag {loaded.tag}` first -- "
            f"this backend never computes raw_values/base_values itself."
        )
    with np.load(sidecar_path) as npz:
        sidecar = {k: npz[k].copy() for k in npz.files}
    sidecar_required = {"raw_values", "base_values"}
    sidecar_missing = sidecar_required - sidecar.keys()
    if sidecar_missing:
        raise RuntimeError(f"{sidecar_path} is missing expected array(s) {sidecar_missing}.")
    if not np.array_equal(sidecar["eval_y"], arrays["eval_y"]):
        raise RuntimeError(
            f"{sidecar_path}'s eval_y does not match {shap_path}'s eval_y -- the sidecar was "
            f"built against a different eval-row selection than this global_shap.npz. Refusing "
            f"to serve raw_values/base_values that may not correspond to the right rows."
        )
    log.info("loaded SHAP sidecar %s: raw_values.shape=%s base_values.shape=%s (eval_y cross-checked)",
              sidecar_path, sidecar["raw_values"].shape, sidecar["base_values"].shape)

    arrays["raw_values"] = sidecar["raw_values"]
    arrays["base_values"] = sidecar["base_values"]
    return arrays


def _csv_records_json(path) -> list:
    """Read once, normalize to JSON-native types via pandas' own encoder
    (handles numpy dtypes and NaN->null), return already-parsed records."""
    df = pd.read_csv(path)
    return json.loads(df.to_json(orient="records"))


def _load_cached_endpoints(cfg_paths: dict) -> tuple[str, str]:
    """Reads the five results/inspection/*.csv files once and renders the
    final response bodies for /agreement and /parity as strings, so a
    request never re-reads a CSV or re-serializes JSON."""
    agreement = {
        "agreement_metrics": _csv_records_json(resolve_path(cfg_paths, "agreement_metrics")),
        "per_silo_agreement": _csv_records_json(resolve_path(cfg_paths, "per_silo_agreement")),
        "round_wise_agreement": _csv_records_json(resolve_path(cfg_paths, "round_wise_agreement")),
        "centralized_instability_floor": _csv_records_json(
            resolve_path(cfg_paths, "centralized_instability_floor")
        ),
    }
    parity = {"parity_monitor": _csv_records_json(resolve_path(cfg_paths, "parity_monitor"))}
    return json.dumps(agreement), json.dumps(parity)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Fail loudly: load_and_verify() raises RuntimeError on any mismatch
    # (architecture, scaler scope, macro-F1 reproduction). An exception here
    # aborts FastAPI/uvicorn startup -- the app never reaches a state where
    # it accepts requests.
    loaded = load_and_verify()
    cfg = load_backend_config()
    cfg_paths = cfg["paths"]

    app.state.loaded = loaded
    app.state.shap_arrays = _load_shap_arrays(loaded, cfg_paths)
    app.state.agreement_json, app.state.parity_json = _load_cached_endpoints(cfg_paths)

    # Contribution B: ByzAgent trust panel. Built once here, cached as a
    # rendered JSON string exactly like agreement/parity above -- GET /trust
    # does zero I/O and zero recomputation per request.
    app.state.trust_json = json.dumps(build_trust_snapshot(cfg_paths, resolve_path))

    # GET /federation -- ALL 9 configs, unlike everything above.
    app.state.federation_json = json.dumps(build_federation_snapshot())

    # GET /faithfulness -- AUC table cached as JSON; both curve PNGs read
    # fully into memory once and served from there, never re-read per request.
    app.state.faithfulness_json = json.dumps(build_faithfulness_snapshot())
    app.state.faithfulness_figures = load_faithfulness_figures()

    app.state.start_time = time.time()

    # In-memory only -- lost on restart, never written to results/. A
    # deque(maxlen=...) drops the oldest entry once full, which is the ring
    # buffer behavior; the lock guards it against concurrent /predict calls
    # (FastAPI runs sync def endpoints in a threadpool, so more than one
    # request can be appending at once).
    buffer_size = int(cfg["alerts"]["buffer_size"])
    app.state.alert_buffer = deque(maxlen=buffer_size)
    app.state.alert_lock = threading.Lock()

    # Step 2B: always starts inactive, serving the base model -- see
    # HotSwapState's own docstring for why a restart never resumes a prior
    # swap. The retraining path itself is never imported here (see
    # backend/hotswap_service.py's docstring); it only ever runs in the
    # subprocess spawned by trigger().
    app.state.hotswap = new_state(loaded.tag)

    log.info("startup complete: tag=%s best_round=%d device=%s", loaded.tag, loaded.best_round, loaded.device)
    yield
    # No teardown: nothing here holds an open file handle or external connection.


app = FastAPI(title="XFed-IDS Dashboard Backend", lifespan=lifespan)


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    loaded: LoadedModel = app.state.loaded
    return HealthResponse(
        status="ok",
        model_loaded=loaded.model is not None,
        scaler_sha256=loaded.scaler_sha256,
        uptime_seconds=time.time() - app.state.start_time,
    )


def _hotswap_info() -> HotSwapInfo:
    """Polls the current job (cheap, non-blocking) then reports state --
    called from both GET /config and GET /hotswap/status so neither one
    can show a stale "running" after the worker has actually finished."""
    state: HotSwapState = app.state.hotswap
    loaded: LoadedModel = app.state.loaded
    poll(state, loaded.model_cfg, loaded.device)
    return HotSwapInfo(
        active=state.active,
        event_id=state.event_id,
        swap_depth=state.swap_depth,
        base_tag=state.base_tag,
        job_status=state.job_status,
        job_detail=state.job_detail,
    )


@app.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    loaded: LoadedModel = app.state.loaded
    return ConfigResponse(
        alpha=loaded.alpha,
        seed=loaded.seed,
        tag=loaded.tag,
        best_round=loaded.best_round,
        n_features=len(loaded.feature_cols),
        n_classes=int(loaded.model_cfg["labels"]["n_classes"]),
        hotswap=_hotswap_info(),
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    loaded: LoadedModel = app.state.loaded
    expected = set(loaded.feature_cols)
    got = set(request.features)

    missing = expected - got
    extra = got - expected
    if missing or extra:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "features must match the model's frozen 82-column feature set exactly",
                "missing": sorted(missing),
                "unexpected": sorted(extra),
            },
        )

    x_raw = np.array([[request.features[c] for c in loaded.feature_cols]], dtype=np.float32)
    x_scaled = loaded.scaler.transform(x_raw).astype(np.float32)

    # Hot-swap only ever replaces the MODEL WEIGHTS -- scaler, feature_cols,
    # class_names above are untouched (the swapped-in checkpoint was
    # evaluated against this exact scaler; see src/hotswap/retrain.py's
    # _pooled_val_split()). state.active_model is None until a swap is
    # accepted, so this is a no-op change of behavior until then.
    hotswap_state: HotSwapState = app.state.hotswap
    active_model = hotswap_state.active_model if hotswap_state.active else None
    model = active_model if active_model is not None else loaded.model

    with torch.no_grad():
        model.eval()
        logits = model(torch.from_numpy(x_scaled).to(loaded.device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

    class_idx = int(np.argmax(probs))
    # Frozen 9-wide vocab, ordered by class index -- src.data.schema builds
    # this from configs/model.yaml's labels.vocabulary, never a literal list
    # of family names in backend code.
    family = loaded.class_names[class_idx]
    confidence = float(probs[class_idx])
    probabilities = {name: float(p) for name, p in zip(loaded.class_names, probs)}

    # Opt-in: only a caller that explicitly asks (the simulator) produces an
    # alert -- Benign included, per the 9-class family requirement (never a
    # binary attack/no-attack flag). The React frontend, manual debugging
    # calls, and the future hot-swap flow all hit this same endpoint and
    # must NOT show up in GET /alerts by default; see PredictRequest.record_alert.
    if request.record_alert:
        alert = Alert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            predicted_family=family,
            confidence=confidence,
            true_family=request.true_family,
            shap_available=False,
        )
        with app.state.alert_lock:
            app.state.alert_buffer.append(alert)

    return PredictResponse(family=family, confidence=confidence, probabilities=probabilities)


@app.post("/hotswap/trigger", response_model=HotSwapTriggerResponse)
def hotswap_trigger(request: HotSwapTriggerRequest) -> HotSwapTriggerResponse:
    """An analyst confirming or rejecting an alert calls this with the
    resulting family label -- confirm passes the alert's own
    predicted_family through unchanged, reject passes the analyst's
    corrected family. Either way this endpoint only ever sees a family
    name: see backend/hotswap_service.py and src/hotswap/retrain.py's
    module docstrings for why a feature vector can never reach this path.

    Returns immediately with status="running" -- this does not wait for
    the subprocess. Poll GET /hotswap/status (or GET /config) for the
    outcome.
    """
    state: HotSwapState = app.state.hotswap
    try:
        result = trigger(state, request.family)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return HotSwapTriggerResponse(**result)


@app.get("/hotswap/status", response_model=HotSwapStatusResponse)
def hotswap_status() -> HotSwapStatusResponse:
    state: HotSwapState = app.state.hotswap
    info = _hotswap_info()  # polls first
    return HotSwapStatusResponse(
        job_id=state.job_id, status=state.job_status, detail=state.job_detail,
        family=state.job_family, hotswap=info,
    )


@app.post("/hotswap/revert", response_model=HotSwapInfo)
def hotswap_revert() -> HotSwapInfo:
    """One call, one click from the frontend -- reloads nothing from disk
    (the base model was never touched by a swap in the first place, see
    /predict), just stops routing to the swapped-in model."""
    state: HotSwapState = app.state.hotswap
    revert(state)
    return _hotswap_info()


@app.get("/shap/{sample_id}", response_model=ShapResponse)
def shap(sample_id: int) -> ShapResponse:
    loaded: LoadedModel = app.state.loaded
    arrays = app.state.shap_arrays
    n_samples = arrays["shap_values"].shape[0]

    if sample_id < 0 or sample_id >= n_samples:
        raise HTTPException(
            status_code=404,
            detail=f"sample_id must be in [0, {n_samples - 1}], got {sample_id}.",
        )

    return ShapResponse(
        sample_id=sample_id,
        tag=loaded.tag,
        eval_family=str(arrays["eval_families"][sample_id]),
        feature_names=loaded.feature_cols,
        class_names=loaded.class_names,
        shap_values=arrays["shap_values"][sample_id].tolist(),
        additivity_max_diff=float(arrays["additivity_max_diff"]),
        raw_values=arrays["raw_values"][sample_id].tolist(),
        base_values=arrays["base_values"].tolist(),
    )


@app.get("/agreement")
def agreement() -> Response:
    return Response(content=app.state.agreement_json, media_type="application/json")


@app.get("/parity")
def parity() -> Response:
    return Response(content=app.state.parity_json, media_type="application/json")


@app.get("/alerts", response_model=list[Alert])
def alerts() -> list[Alert]:
    """Current ring buffer contents, newest-first. Empty if the simulator
    (or nothing) has posted to /predict since startup -- that is a normal
    state, not an error."""
    with app.state.alert_lock:
        return list(reversed(app.state.alert_buffer))


@app.get("/trust")
def trust() -> Response:
    """ByzAgent trust panel (Contribution B). See backend/trust.py for the
    pairing rule (every condition is clean+attack together or not rendered
    at all) and the decision-variance / nondeterminism-notice sourcing."""
    return Response(content=app.state.trust_json, media_type="application/json")


@app.get("/federation")
def federation() -> Response:
    """Serves ALL 9 (alpha, seed) configs -- unlike every other endpoint in
    this backend. GET /config is unaffected and stays loaded-model identity
    only; see backend/federation.py."""
    return Response(content=app.state.federation_json, media_type="application/json")


@app.get("/faithfulness")
def faithfulness() -> Response:
    """AUC table only (config_label + auc). The curve images themselves are
    GET /faithfulness/deletion_curve.png and /insertion_curve.png below."""
    return Response(content=app.state.faithfulness_json, media_type="application/json")


@app.get("/faithfulness/deletion_curve.png")
def faithfulness_deletion_curve() -> Response:
    return Response(content=app.state.faithfulness_figures["deletion"], media_type="image/png")


@app.get("/faithfulness/insertion_curve.png")
def faithfulness_insertion_curve() -> Response:
    return Response(content=app.state.faithfulness_figures["insertion"], media_type="image/png")
