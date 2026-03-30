from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.features.backtests.schema import HybridRunRequest, WhiteBoxRunRequest
from app.features.backtests.service import BacktestService
from app.features.data.schema import DatasetDownloadRequest
from app.features.data.service import DataService
from app.features.paper.service import PaperService
from app.features.strategies.service import StrategyService
from app.features.webhooks.schema import WebhookSignalRequest
from app.features.webhooks.service import WebhookService
from app.storage import Repository


settings.ensure_dirs()
repo = Repository()
data_service = DataService(repo)
strategy_service = StrategyService()
backtest_service = BacktestService(repo, data_service, strategy_service)
paper_service = PaperService(repo, data_service, strategy_service, backtest_service)
webhook_service = WebhookService(repo, backtest_service)

app = FastAPI(title="Project Aurum", version="1.0.0")
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "ui"), name="ui")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(Path(__file__).parent / "ui" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "project-aurum"}


@app.get("/api/strategies/current")
def current_strategy() -> dict:
    return strategy_service.current()


@app.get("/api/data/datasets")
def list_datasets() -> list[dict]:
    return data_service.list_datasets()


@app.post("/api/data/download")
def download_dataset(request: DatasetDownloadRequest) -> dict:
    return data_service.download_market_dataset(
        symbol=request.symbol,
        timeframe=request.timeframe,
        lookback_days=request.lookback_days,
        provider=request.provider,
        name=request.name,
    )


@app.post("/api/data/import-csv")
async def import_csv_dataset(
    file: UploadFile = File(...),
    symbol: str = Form("XAU_USD"),
    timeframe: str = Form("15m"),
    name: str | None = Form(None),
) -> dict:
    content = await file.read()
    return data_service.import_csv_dataset(
        content=content,
        filename=file.filename or "import.csv",
        symbol=symbol,
        timeframe=timeframe,
        name=name,
    )


@app.delete("/api/data/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    data_service.delete_dataset(dataset_id)
    return {"status": "deleted"}


@app.get("/api/backtests/runs")
def list_runs() -> list[dict]:
    return backtest_service.list_runs()


@app.post("/api/backtests/whitebox")
def run_whitebox(request: WhiteBoxRunRequest) -> dict:
    return backtest_service.run_whitebox(request.dataset_id, request.profile)


@app.post("/api/backtests/hybrid")
def run_hybrid(request: HybridRunRequest) -> dict:
    return backtest_service.run_hybrid(request.dataset_id, request.profile, request.threshold)


@app.delete("/api/backtests/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, str]:
    backtest_service.delete_run(run_id)
    return {"status": "deleted"}


@app.post("/api/backtests/runs/{run_id}/tv-debug")
def build_tv_debug(run_id: str) -> dict:
    return backtest_service.build_tradingview_debug(run_id)


@app.post("/api/backtests/runs/{run_id}/debug-trace")
def build_debug_trace(run_id: str) -> dict:
    return backtest_service.build_debug_trace(run_id)


@app.get("/api/paper/runs")
def list_paper_runs() -> list[dict]:
    return paper_service.list_runs()


@app.post("/api/paper/run")
def run_paper(request: WhiteBoxRunRequest) -> dict:
    return paper_service.run_week(request.dataset_id, request.profile, use_hybrid=True)


@app.post("/api/webhooks/tradingview")
def evaluate_webhook(request: WebhookSignalRequest) -> dict:
    return webhook_service.evaluate_signal(request.model_dump(mode="json"))


@app.get("/api/artifacts/{kind}/{artifact_name}")
def get_artifact(kind: str, artifact_name: str) -> FileResponse:
    roots = {
        "runs": settings.run_dir,
        "reports": settings.report_dir,
        "paper": settings.paper_dir,
        "data": settings.data_dir,
    }
    if kind not in roots:
        raise HTTPException(status_code=404, detail="Artifact group not found.")
    path = roots[kind] / artifact_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(path)
