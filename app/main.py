from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.data import DataService
from app.lab import MutationLabService
from app.storage import Repository


class DatasetDownloadRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT")
    timeframe: str = Field(default="15m")
    bars: int = Field(default=40000, ge=0, le=1_000_000)
    full_history: bool = False
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


class OptimizeAllRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict = Field(default_factory=dict)
    passes: int = Field(default=2, ge=1, le=5)


class RobustnessRequest(BaseModel):
    dataset_id: str
    parameter_overrides: dict = Field(default_factory=dict)


class HybridEntryQualityRequest(BaseModel):
    veto_fraction: float = Field(default=0.15, ge=0.01, le=0.5)


class HybridTimeDecayTriageRequest(BaseModel):
    exit_fraction: float = Field(default=0.15, ge=0.01, le=0.5)


settings.ensure_dirs()
repo = Repository()
data_service = DataService(repo)
lab = MutationLabService(repo, data_service)
lab.ensure_seeded()

app = FastAPI(title="Mutation Lab", version="1.0.0")
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "ui"), name="ui")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(Path(__file__).parent / "ui" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "mutation-lab"}


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


@app.post("/api/families/register")
def register_family(request: RegisterBaselineRequest) -> dict:
    return lab.register_baseline(
        family_id=request.family_id,
        title=request.title,
        asset=request.asset,
        venue=request.venue,
        timeframe=request.timeframe,
        version_name=request.version_name,
        source_code=request.source_code,
        spec_json=request.spec_json,
        causal_story=request.causal_story,
        notes=request.notes,
    )


@app.post("/api/families/{family_id}/promote/{version_id}")
def promote_version(family_id: str, version_id: str) -> dict:
    return lab.promote_version(family_id, version_id)


@app.get("/api/datasets")
def list_datasets() -> list[dict]:
    return data_service.list_datasets()


@app.post("/api/datasets/download")
def download_dataset(request: DatasetDownloadRequest) -> dict:
    return data_service.download_binance_dataset(
        symbol=request.symbol,
        timeframe=request.timeframe,
        bars=request.bars,
        full_history=request.full_history,
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
    )


@app.post("/api/versions/{version_id}/optimize-all")
def optimize_all(version_id: str, request: OptimizeAllRequest) -> dict:
    return lab.optimize_all(
        version_id=version_id,
        dataset_id=request.dataset_id,
        parameter_overrides=request.parameter_overrides,
        passes=request.passes,
    )


@app.post("/api/versions/{version_id}/robustness")
def robustness_check(version_id: str, request: RobustnessRequest) -> dict:
    return lab.robustness_check(
        version_id=version_id,
        dataset_id=request.dataset_id,
        parameter_overrides=request.parameter_overrides,
    )


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
