from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.features.backtests.api import router as backtest_router
from app.features.backtests.service import BacktestService
from app.features.data.api import router as data_router
from app.features.data.service import DataService
from app.features.evaluations.api import router as evaluations_router
from app.features.evaluations.service import EvaluationService
from app.features.lab.api import router as lab_router
from app.features.lab.service import LabService
from app.features.strategies.api import router as strategies_router
from app.features.strategies.service import StrategyService
from app.infra.config import AppConfig, load_config
from app.infra.db import Database
from app.infra.logging import configure_logging
from app.shared.http import attach_http_runtime


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()
    configure_logging(config.app_log_level)
    db = Database(config)
    strategy_service = StrategyService(config)
    data_service = DataService(config, db)
    evaluation_service = EvaluationService(db)
    backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
    lab_service = LabService(config, db, strategy_service, backtest_service)
    app = FastAPI(title="StrategyLab", version="0.1.0")
    app.state.config = config
    app.state.db = db
    app.state.strategy_service = strategy_service
    app.state.data_service = data_service
    app.state.evaluation_service = evaluation_service
    app.state.backtest_service = backtest_service
    app.state.lab_service = lab_service
    attach_http_runtime(app)
    app.include_router(data_router)
    app.include_router(strategies_router)
    app.include_router(backtest_router)
    app.include_router(evaluations_router)
    app.include_router(lab_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(Path(config.ui_dir) / "index.html")

    @app.get("/app.js")
    def app_js() -> FileResponse:
        return FileResponse(Path(config.ui_dir) / "app.js", media_type="application/javascript")

    return app


app = create_app()
