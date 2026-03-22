from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]


class AppConfig(BaseModel):
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_db_path: Path = Field(default=ROOT_DIR / "artifacts" / "strategy_lab.duckdb")
    app_data_dir: Path = Field(default=ROOT_DIR / "artifacts" / "data")
    app_run_dir: Path = Field(default=ROOT_DIR / "artifacts" / "runs")
    app_report_dir: Path = Field(default=ROOT_DIR / "artifacts" / "reports")
    app_graveyard_dir: Path = Field(default=ROOT_DIR / "artifacts" / "graveyard")
    app_log_level: str = "INFO"
    app_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"
    root_dir: Path = ROOT_DIR
    strategies_dir: Path = ROOT_DIR / "strategies" / "families"
    ui_dir: Path = ROOT_DIR / "app" / "ui"

    def ensure_directories(self) -> None:
        self.app_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.app_run_dir.mkdir(parents=True, exist_ok=True)
        self.app_report_dir.mkdir(parents=True, exist_ok=True)
        self.app_graveyard_dir.mkdir(parents=True, exist_ok=True)
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
        self.ui_dir.mkdir(parents=True, exist_ok=True)


def _value(name: str, default: str) -> str:
    return os.getenv(name, default)


def build_config(overrides: dict[str, object] | None = None) -> AppConfig:
    raw = {
        "app_env": _value("APP_ENV", "development"),
        "app_host": _value("APP_HOST", "127.0.0.1"),
        "app_port": int(_value("APP_PORT", "8000")),
        "app_db_path": ROOT_DIR / _value("APP_DB_PATH", "artifacts/strategy_lab.duckdb"),
        "app_data_dir": ROOT_DIR / _value("APP_DATA_DIR", "artifacts/data"),
        "app_run_dir": ROOT_DIR / _value("APP_RUN_DIR", "artifacts/runs"),
        "app_report_dir": ROOT_DIR / _value("APP_REPORT_DIR", "artifacts/reports"),
        "app_graveyard_dir": ROOT_DIR / _value("APP_GRAVEYARD_DIR", "artifacts/graveyard"),
        "app_log_level": _value("APP_LOG_LEVEL", "INFO").upper(),
        "app_api_key": _value("APP_API_KEY", ""),
        "gemini_api_key": _value("GEMINI_API_KEY", ""),
        "gemini_model": _value("GEMINI_MODEL", "gemini-3-flash-preview"),
    }
    if overrides:
        raw.update(overrides)
    config = AppConfig(**raw)
    config.ensure_directories()
    return config


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    return build_config()
