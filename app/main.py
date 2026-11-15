from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.data import DataService
from app.lab import MutationLabService
from app.pine2python_client import Pine2PythonClient
from app.pine_workbench import PineWorkbenchService
from app.storage import Repository
from app.tg_lab import TgManagementLabService


class DatasetDownloadRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT")
    timeframe: str = Field(default="15m")
    bars: int = Field(default=40000, ge=0, le=1_000_000)
    full_history: bool = False
    name: str | None = None


class DatasetImportRequest(BaseModel):
    source_path: str
    symbol: str = Field(default="XAUUSD")
    timeframe: str = Field(default="30m")
    name: str | None = None


class DatasetImportContentRequest(BaseModel):
    filename: str
    content: str
    symbol: str = Field(default="XAUUSD")
    timeframe: str = Field(default="30m")
    name: str | None = None


class RegisterBaselineRequest(BaseModel):
    family_id: str
    title: str
    asset: str
    venue: str
    timeframe: str
    version_name: str
    source_code: str
    spec_json: dict
    causal_story: str
    notes: str = ""
    workflow_version: str = "reference_v1"


class TunePreviewRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict


class SaveTuneRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict
    name: str | None = None
    notes: str = ""


class OptimizeLeverRequest(BaseModel):
    dataset_id: str
    lever: str
    parameter_overrides: dict = Field(default_factory=dict)
    optimization_mode: str = Field(default="production")


class OptimizeAllRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict = Field(default_factory=dict)
    passes: int = Field(default=2, ge=1, le=5)
    optimization_mode: str = Field(default="production")


class RobustnessRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict = Field(default_factory=dict)


class HybridEntryQualityRequest(BaseModel):
    veto_fraction: float = Field(default=0.15, ge=0.01, le=0.5)


class HybridEntrySizingRequest(BaseModel):
    reduced_fraction: float = Field(default=0.10, ge=0.05, le=0.25)
    risk_multiplier: float = Field(default=0.50, ge=0.10, le=0.90)


class HybridTimeDecayTriageRequest(BaseModel):
    exit_fraction: float = Field(default=0.15, ge=0.01, le=0.5)


class PineRevisionRequest(BaseModel):
    source_code: str = Field(min_length=1, max_length=1_000_000)
    source_name: str = "strategy.pine"
    mode: str = "greenfield_strategy"
    settings: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)
    workbench_id: str | None = None
    parent_revision_id: str | None = None


class PineGenerateRevisionRequest(BaseModel):
    parameters: dict = Field(default_factory=dict)
    title: str = "Pine2Python generated strategy"
    symbol: str = "BTCUSDT"
    timeframe: str = "15"
    mintick: float = Field(default=0.01, gt=0)
    start_ms: int
    end_ms: int
    profile: str = "basic_v1"
    workbench_id: str | None = None
    parent_revision_id: str | None = None


class PineProofRequest(BaseModel):
    dataset_id: str
    start_ms: int
    end_ms: int
    mintick: float = Field(gt=0)
    trace_rows: list[dict] = Field(default_factory=list, max_length=200_000)
    stream_expressions: dict[str, list[dict]] = Field(default_factory=dict)
    profile: str = "basic_v1"


class PineReviewPackageRequest(BaseModel):
    baseline_revision_id: str
    fidelity_contract: dict = Field(default_factory=dict)
    trace_evidence_id: str | None = None
    trace_rows: list[dict] | None = Field(default=None, max_length=200_000)
    max_fixtures: int = Field(default=18, ge=1, le=100)


class TradingViewObservationRequest(BaseModel):
    proof_evidence_id: str
    observed: dict
    screenshot_sha256: str | None = None
    user_verdict: str = "pending"


class PythonTraceRequest(BaseModel):
    dataset_id: str


class PineParityRequest(BaseModel):
    reference_rows: list[dict] = Field(max_length=200_000)
    candidate_rows: list[dict] = Field(max_length=200_000)
    contract: dict


class TgSnapshotImportRequest(BaseModel):
    package_path: str


class TgExperimentRequest(BaseModel):
    snapshot_id: str
    asset: str
    seed: int = 0
    candidate_family: str = "all"


settings.ensure_dirs()
repo = Repository()
data_service = DataService(repo)
lab = MutationLabService(repo, data_service)
tg_lab = TgManagementLabService(repo)
lab.ensure_seeded()
pine2python_client = Pine2PythonClient()
pine_workbench = PineWorkbenchService(repo, data_service, pine2python_client)
optimization_executor = ThreadPoolExecutor(max_workers=1)
optimization_jobs: dict[str, dict] = {}
optimization_jobs_lock = Lock()
tg_jobs: dict[str, dict] = {}

app = FastAPI(title="Python2Pine StrategyLab", version="1.1.0")
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "ui"), name="ui")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(Path(__file__).parent / "ui" / "index.html")


@app.get("/health")
def health() -> dict:
    pine_status = pine_workbench.status()
    return {
        "status": (
            "degraded"
            if pine_status["status"] == "unavailable"
            else "ok"
        ),
        "app": "mutation-lab",
        "pine2python": {
            "status": pine_status["status"],
            "required": pine_status["required"],
            "transport": pine_status.get("transport"),
        },
    }


@app.get("/health/ready")
def health_ready() -> dict:
    payload = health()
    if (
        payload["pine2python"]["required"]
        and payload["pine2python"]["status"] != "ready"
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "PINE2PYTHON_REQUIRED_UNAVAILABLE",
                "health": payload,
            },
        )
    return payload


@app.get("/api/pine2python/status")
@app.get("/api/python2pine/status")
def pine2python_status() -> dict:
    return pine_workbench.status()


@app.get("/api/pine-workbench/revisions")
def list_pine_revisions(workbench_id: str | None = None) -> list[dict]:
    return pine_workbench.list_revisions(workbench_id)


@app.get("/api/pine-workbench/revisions/{revision_id}")
def pine_revision_detail(revision_id: str) -> dict:
    return pine_workbench.revision_detail(revision_id)


@app.post("/api/pine-workbench/revisions")
def create_pine_revision(request: PineRevisionRequest) -> dict:
    return pine_workbench.create_revision(
        source_code=request.source_code,
        source_name=request.source_name,
        mode=request.mode,
        settings_payload=request.settings,
        provenance=request.provenance,
        workbench_id=request.workbench_id,
        parent_revision_id=request.parent_revision_id,
    )


@app.post("/api/pine-workbench/generate/{adapter_id}")
def generate_pine_revision(
    adapter_id: str, request: PineGenerateRevisionRequest
) -> dict:
    generator_payload = request.model_dump(
        exclude={"workbench_id", "parent_revision_id"}
    )
    return pine_workbench.generate_revision(
        adapter_id,
        generator_payload=generator_payload,
        workbench_id=request.workbench_id,
        parent_revision_id=request.parent_revision_id,
    )


@app.post("/api/pine-workbench/revisions/{revision_id}/proofs")
def create_pine_proof(revision_id: str, request: PineProofRequest) -> dict:
    return pine_workbench.create_proof(
        revision_id,
        dataset_id=request.dataset_id,
        start_ms=request.start_ms,
        end_ms=request.end_ms,
        mintick=request.mintick,
        trace_rows=request.trace_rows,
        stream_expressions=request.stream_expressions,
        profile=request.profile,
    )


@app.post("/api/pine-workbench/revisions/{revision_id}/review-package")
def prepare_pine_review_package(
    revision_id: str, request: PineReviewPackageRequest
) -> dict:
    return pine_workbench.prepare_review_package(
        revision_id,
        baseline_revision_id=request.baseline_revision_id,
        fidelity_contract=request.fidelity_contract,
        trace_evidence_id=request.trace_evidence_id,
        trace_rows=request.trace_rows,
        max_fixtures=request.max_fixtures,
    )


@app.post(
    "/api/pine-workbench/revisions/{revision_id}/tradingview-observations"
)
def observe_tradingview(
    revision_id: str, request: TradingViewObservationRequest
) -> dict:
    return pine_workbench.observe_tradingview(
        revision_id,
        proof_evidence_id=request.proof_evidence_id,
        observed=request.observed,
        screenshot_sha256=request.screenshot_sha256,
        user_verdict=request.user_verdict,
    )


@app.post("/api/versions/{version_id}/python-trace")
def create_python_trace(version_id: str, request: PythonTraceRequest) -> dict:
    return pine_workbench.python_trace(version_id, request.dataset_id)


@app.get("/api/versions/{version_id}/pine-evidence")
def list_version_pine_evidence(version_id: str) -> list[dict]:
    return pine_workbench.list_version_evidence(version_id)


@app.post("/api/pine2python/parity-comparisons")
def create_pine_parity(request: PineParityRequest) -> dict:
    return pine_workbench.compare_parity(request.model_dump())


@app.get("/api/prompts")
def prompt_catalog() -> list[dict]:
    return lab.list_prompts()


@app.get("/api/families")
def list_families() -> list[dict]:
    return lab.list_families()


@app.get("/api/families/{family_id}")
def family_detail(family_id: str) -> dict:
    return lab.family_detail(family_id)


@app.get("/api/versions/{version_id}/tuning")
def tuning_edges(version_id: str, include_hybrid: bool = True) -> list[dict]:
    return lab.list_tuning_edges(version_id, include_hybrid=include_hybrid)


class ReferenceValidationRequest(BaseModel):
    dataset_id: str
    cases: list[dict] = Field(min_length=1, max_length=100)


class SearchAuthorizationRequest(BaseModel):
    dataset_id: str
    authorization: dict


class ReferenceChildRequest(BaseModel):
    dataset_id: str
    spec: dict
    name: str
    source_code: str | None = None


@app.get("/api/versions/{version_id}/workflow")
def workflow_status(version_id: str, dataset_id: str | None = None) -> dict:
    return lab.reference_evidence.status(version_id, dataset_id)


@app.get("/api/versions/{version_id}/reference-casebook")
def reference_casebook(version_id: str, dataset_id: str) -> FileResponse:
    return FileResponse(lab.reference_evidence.casebook_path(version_id, dataset_id))


@app.post("/api/versions/{version_id}/reference-validation")
def validate_reference(version_id: str, request: ReferenceValidationRequest) -> dict:
    return lab.reference_evidence.validate(version_id, request.dataset_id, request.cases)


@app.post("/api/versions/{version_id}/search-authorization")
def authorize_reference_search(version_id: str, request: SearchAuthorizationRequest) -> dict:
    return lab.reference_evidence.authorize(version_id, request.dataset_id, request.authorization)


@app.post("/api/versions/{version_id}/reference-children")
def create_reference_child(version_id: str, request: ReferenceChildRequest) -> dict:
    return lab.create_reference_child(version_id, request.dataset_id, request.spec, request.name, request.source_code)


@app.post("/api/versions/{version_id}/pine-target")
def prepare_reference_pine_target(version_id: str, request: PythonTraceRequest) -> dict:
    return lab.reference_evidence.prepare_pine_target(version_id, request.dataset_id, pine_workbench)


@app.get("/api/optimization-progress")
def optimization_progress() -> dict:
    return lab.optimization_progress()


@app.get("/api/optimization-result")
def optimization_result() -> dict:
    return lab.optimization_result()


@app.post("/api/families/register")
def register_family(request: RegisterBaselineRequest) -> dict:
    spec = {**request.spec_json, "workflow_version": request.workflow_version}
    return lab.register_baseline(
        family_id=request.family_id,
        title=request.title,
        asset=request.asset,
        venue=request.venue,
        timeframe=request.timeframe,
        version_name=request.version_name,
        source_code=request.source_code,
        spec_json=spec,
        causal_story=request.causal_story,
        notes=request.notes,
    )


@app.post("/api/families/{family_id}/promote/{version_id}")
def promote_version(family_id: str, version_id: str) -> dict:
    return lab.promote_version(family_id, version_id)


@app.get("/api/datasets")
def list_datasets() -> list[dict]:
    return data_service.list_datasets()


@app.get("/api/datasets/{dataset_id}/pine-proof-window")
def pine_proof_window(dataset_id: str, max_bars: int = 5_000) -> dict:
    return data_service.pine_proof_window(dataset_id, max_bars=max_bars)


@app.post("/api/datasets/download")
def download_dataset(request: DatasetDownloadRequest) -> dict:
    return data_service.download_binance_dataset(
        symbol=request.symbol,
        timeframe=request.timeframe,
        bars=request.bars,
        full_history=request.full_history,
        name=request.name,
    )


@app.post("/api/datasets/import-mt5")
def import_mt5_dataset(request: DatasetImportRequest) -> dict:
    return data_service.import_mt5_csv_dataset(
        source_path=request.source_path,
        symbol=request.symbol,
        timeframe=request.timeframe,
        name=request.name,
    )


@app.post("/api/datasets/import-mt5-content")
def import_mt5_dataset_content(request: DatasetImportContentRequest) -> dict:
    return data_service.import_mt5_csv_content(
        filename=request.filename,
        content=request.content,
        symbol=request.symbol,
        timeframe=request.timeframe,
        name=request.name,
    )


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    data_service.delete_dataset(dataset_id)
    return {"status": "deleted"}


@app.get("/api/runs")
def list_runs(family_id: str | None = None) -> list[dict]:
    return lab.list_runs(family_id=family_id)


@app.post("/api/versions/{version_id}/run")
def run_version(version_id: str, dataset_id: str) -> dict:
    return lab.run_version(version_id, dataset_id)


@app.post("/api/versions/{version_id}/preview")
def preview_tuned_version(version_id: str, request: TunePreviewRequest) -> dict:
    return lab.preview_tuned_version(version_id, request.dataset_id, request.parameter_overrides)


@app.post("/api/versions/{version_id}/save-tuned")
def save_tuned_version(version_id: str, request: SaveTuneRequest) -> dict:
    return lab.save_tuned_version(
        version_id=version_id,
        dataset_id=request.dataset_id,
        parameter_overrides=request.parameter_overrides,
        name=request.name,
        notes=request.notes,
    )


@app.post("/api/versions/{version_id}/optimize-lever")
def optimize_lever(version_id: str, request: OptimizeLeverRequest) -> dict:
    return lab.optimize_lever(
        version_id=version_id,
        dataset_id=request.dataset_id,
        lever=request.lever,
        parameter_overrides=request.parameter_overrides,
        optimization_mode=request.optimization_mode,
    )


@app.post("/api/versions/{version_id}/optimize-all")
def optimize_all(version_id: str, request: OptimizeAllRequest) -> dict:
    return lab.optimize_all(
        version_id=version_id,
        dataset_id=request.dataset_id,
        parameter_overrides=request.parameter_overrides,
        passes=request.passes,
        optimization_mode=request.optimization_mode,
    )


@app.post("/api/versions/{version_id}/optimize-all/jobs")
def start_optimize_all_job(version_id: str, request: OptimizeAllRequest) -> dict:
    version = lab._get_upgraded_version(version_id)
    if not version:
        raise HTTPException(404, "Version not found.")
    lab.reference_evidence.require(version, request.dataset_id, "search")
    job_id = f"opt_{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    with optimization_jobs_lock:
        optimization_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "version_id": version_id,
            "dataset_id": request.dataset_id,
            "progress": None,
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }
    optimization_executor.submit(
        _run_optimize_all_job,
        job_id,
        version_id,
        request.dataset_id,
        request.parameter_overrides,
        request.passes,
        request.optimization_mode,
    )
    return _optimization_job_snapshot(job_id)


@app.get("/api/optimization-jobs/{job_id}")
def optimization_job_status(job_id: str) -> dict:
    return _optimization_job_snapshot(job_id)


def _run_optimize_all_job(
    job_id: str,
    version_id: str,
    dataset_id: str,
    parameter_overrides: dict,
    passes: int,
    optimization_mode: str,
) -> None:
    _update_optimization_job(job_id, status="running")
    try:
        result = lab.optimize_all(
            version_id=version_id,
            dataset_id=dataset_id,
            parameter_overrides=parameter_overrides,
            passes=passes,
            optimization_mode=optimization_mode,
            progress_callback=lambda progress: _update_optimization_job(job_id, progress=progress),
        )
    except HTTPException as exc:
        _update_optimization_job(job_id, status="failed", error=str(exc.detail))
    except Exception as exc:  # pragma: no cover - defensive boundary for long-running operator jobs.
        _update_optimization_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
    else:
        _update_optimization_job(job_id, status="completed", result=result, progress=None)


def _update_optimization_job(job_id: str, **updates: object) -> None:
    with optimization_jobs_lock:
        job = optimization_jobs.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updated_at"] = datetime.now(UTC).isoformat()


def _optimization_job_snapshot(job_id: str) -> dict:
    with optimization_jobs_lock:
        job = optimization_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Optimization job not found.")
        return dict(job)


@app.post("/api/versions/{version_id}/robustness")
def robustness_check(version_id: str, request: RobustnessRequest) -> dict:
    return lab.robustness_check(
        version_id=version_id,
        dataset_id=request.dataset_id,
        parameter_overrides=request.parameter_overrides,
    )


@app.post("/api/runs/{run_id}/execution-audit")
def execution_feasibility_audit(run_id: str) -> dict:
    return lab.execution_feasibility_audit(run_id)


@app.post("/api/versions/{version_id}/proposals/generate")
def generate_proposals(version_id: str, include_hybrid: bool = False) -> list[dict]:
    return lab.generate_proposals(version_id, include_hybrid=include_hybrid)


@app.post("/api/versions/{version_id}/proposals/run-all")
def run_proposals(version_id: str, dataset_id: str, include_hybrid: bool = False) -> dict:
    return lab.run_proposal_pack(version_id, dataset_id, include_hybrid=include_hybrid)


@app.post("/api/proposals/{proposal_id}/run")
def run_proposal(proposal_id: str, dataset_id: str) -> dict:
    return lab.run_proposal(proposal_id, dataset_id)


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, str]:
    lab.delete_run(run_id)
    return {"status": "deleted"}


@app.post("/api/runs/{run_id}/hybrid-entry-quality")
def run_hybrid_entry_quality(run_id: str, request: HybridEntryQualityRequest) -> dict:
    return lab.run_hybrid_entry_quality_experiment(run_id, veto_fraction=request.veto_fraction)


@app.post("/api/runs/{run_id}/hybrid-entry-sizing")
def run_hybrid_entry_sizing(run_id: str, request: HybridEntrySizingRequest) -> dict:
    return lab.run_hybrid_entry_sizing_experiment(
        run_id,
        reduced_fraction=request.reduced_fraction,
        risk_multiplier=request.risk_multiplier,
    )


@app.post("/api/runs/{run_id}/hybrid-time-decay-triage")
def run_hybrid_time_decay_triage(run_id: str, request: HybridTimeDecayTriageRequest) -> dict:
    return lab.run_hybrid_time_decay_triage_experiment(run_id, exit_fraction=request.exit_fraction)


@app.delete("/api/versions/{version_id}")
def delete_version(version_id: str) -> dict[str, str]:
    lab.delete_version(version_id)
    return {"status": "deleted"}


@app.get("/api/artifacts/{kind}/{artifact_name}")
def get_artifact(kind: str, artifact_name: str) -> FileResponse:
    roots = {
        "runs": settings.run_dir,
        "reports": settings.report_dir,
        "diagnostics": settings.diagnostic_dir,
        "data": settings.data_dir,
    }
    root = roots.get(kind)
    if root is None:
        raise HTTPException(status_code=404, detail="Artifact group not found.")
    path = root / artifact_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(path)


@app.get("/api/tg-management/snapshots")
def list_tg_snapshots() -> list[dict]:
    return tg_lab.list_snapshots()


@app.post("/api/tg-management/snapshots/import")
def import_tg_snapshot(request: TgSnapshotImportRequest) -> dict:
    return tg_lab.import_snapshot(request.package_path)


@app.get("/api/tg-management/snapshots/{snapshot_id}")
def tg_snapshot_detail(snapshot_id: str) -> dict:
    return tg_lab.snapshot_detail(snapshot_id)


@app.get("/api/tg-management/snapshots/{snapshot_id}/coverage")
def tg_snapshot_coverage(snapshot_id: str) -> dict:
    return tg_lab.coverage(snapshot_id)


@app.post("/api/tg-management/baseline")
def run_tg_baseline(request: TgExperimentRequest) -> dict:
    return tg_lab.run_baseline(request.snapshot_id, request.asset)


@app.post("/api/tg-management/optimize")
def run_tg_optimization(request: TgExperimentRequest) -> dict:
    return tg_lab.optimize_asset(request.snapshot_id, request.asset, request.seed, request.candidate_family)


@app.post("/api/tg-management/optimization-jobs")
def start_tg_optimization(request: TgExperimentRequest) -> dict:
    job_id = f"tgopt_{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    with optimization_jobs_lock:
        tg_jobs[job_id] = {"job_id": job_id, "status": "queued", "progress": {"percent": 0, "stage": "queued"}, "result": None, "error": None, "created_at": now, "updated_at": now}
    optimization_executor.submit(_run_tg_job, job_id, request.snapshot_id, request.asset, request.seed, request.candidate_family)
    return _tg_job(job_id)


def _run_tg_job(job_id: str, snapshot_id: str, asset: str, seed: int, candidate_family: str) -> None:
    with optimization_jobs_lock:
        tg_jobs[job_id].update(status="running", progress={"percent": 0, "stage": "search"}, updated_at=datetime.now(UTC).isoformat())
    def update_progress(progress: dict) -> None:
        with optimization_jobs_lock:
            tg_jobs[job_id].update(progress=progress, updated_at=datetime.now(UTC).isoformat())
    try:
        result = tg_lab.optimize_asset(snapshot_id, asset, seed, candidate_family, update_progress)
    except Exception as exc:  # pragma: no cover - defensive API job boundary
        with optimization_jobs_lock:
            tg_jobs[job_id].update(status="failed", error=f"{type(exc).__name__}: {exc}", updated_at=datetime.now(UTC).isoformat())
    else:
        with optimization_jobs_lock:
            tg_jobs[job_id].update(status="completed", progress={"percent": 100, "stage": "completed"}, result=result, updated_at=datetime.now(UTC).isoformat())


def _tg_job(job_id: str) -> dict:
    with optimization_jobs_lock:
        if job_id not in tg_jobs:
            raise HTTPException(404, "TgSignalSniper optimization job not found")
        return dict(tg_jobs[job_id])


@app.get("/api/tg-management/optimization-jobs/{job_id}")
def tg_optimization_progress(job_id: str) -> dict:
    return _tg_job(job_id)


@app.get("/api/tg-management/experiments")
def list_tg_experiments(snapshot_id: str | None = None, asset: str | None = None) -> list[dict]:
    return tg_lab.list_experiments(snapshot_id, asset)


@app.get("/api/tg-management/experiments/{experiment_id}")
def tg_experiment_detail(experiment_id: str) -> dict:
    return tg_lab.experiment(experiment_id)


@app.get("/api/tg-management/experiments/{experiment_id}/download/{format_name}")
def download_tg_experiment(experiment_id: str, format_name: str) -> FileResponse:
    experiment = tg_lab.experiment(experiment_id)
    suffixes = {"json": ".json", "csv": ".csv", "markdown": ".md"}
    suffix = suffixes.get(format_name)
    if not suffix:
        raise HTTPException(404, "Unknown experiment format")
    path = settings.tg_experiment_dir / f"{experiment_id}{suffix}"
    if not path.is_file():
        raise HTTPException(404, "Experiment artifact not found")
    return FileResponse(path)
