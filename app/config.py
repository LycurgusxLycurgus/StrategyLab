from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def load_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


BASE_DIR = Path(__file__).resolve().parents[1]


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("APP_PORT", "8000"))
    timezone_name: str = os.getenv("APP_TIMEZONE", "America/Bogota")
    db_path: Path = Path(os.getenv("APP_DB_PATH", str(BASE_DIR / "artifacts" / "mutation_lab.sqlite3")))
    data_dir: Path = Path(os.getenv("APP_DATA_DIR", str(BASE_DIR / "artifacts" / "data")))
    run_dir: Path = Path(os.getenv("APP_RUN_DIR", str(BASE_DIR / "artifacts" / "runs")))
    report_dir: Path = Path(os.getenv("APP_REPORT_DIR", str(BASE_DIR / "artifacts" / "reports")))
    diagnostic_dir: Path = Path(os.getenv("APP_DIAGNOSTIC_DIR", str(BASE_DIR / "artifacts" / "diagnostics")))
    tg_snapshot_dir: Path = Path(os.getenv("APP_TG_SNAPSHOT_DIR", str(BASE_DIR / "artifacts" / "tg_snapshots")))
    tg_experiment_dir: Path = Path(os.getenv("APP_TG_EXPERIMENT_DIR", str(BASE_DIR / "artifacts" / "tg_experiments")))
    prompt_dir: Path = BASE_DIR / "agents" / "translation and generation" / "whitebox"
    strategy_specs_dir: Path = BASE_DIR / "strategies"
    seed_strategy_path: Path = BASE_DIR / "pre-strategies" / "BTC-intraday.txt"
    seed_spec_path: Path = BASE_DIR / "strategies" / "btc_intraday_parent.json"
    pine_development_dir: Path = Path(
        os.getenv(
            "PINE_DEVELOPMENT_DIR",
            str(BASE_DIR / "artifacts" / "strategy-development"),
        )
    )
    pine2python_url: str = os.getenv(
        "PINE2PYTHON_URL", "http://127.0.0.1:8080"
    ).rstrip("/")
    pine2python_enabled: bool = env_bool("PINE2PYTHON_ENABLED", True)
    pine2python_required: bool = env_bool("PINE2PYTHON_REQUIRED", False)
    pine2python_local_fallback: bool = env_bool(
        "PINE2PYTHON_LOCAL_FALLBACK", True
    )
    pine2python_timeout_seconds: float = float(
        os.getenv("PINE2PYTHON_TIMEOUT_SECONDS", "30")
    )

    @property
    def timezone(self) -> ZoneInfo:
        return load_timezone(self.timezone_name)

    def ensure_dirs(self) -> None:
        for path in (
            self.db_path.parent,
            self.data_dir,
            self.run_dir,
            self.report_dir,
            self.diagnostic_dir,
            self.tg_snapshot_dir,
            self.tg_experiment_dir,
            self.strategy_specs_dir,
            self.pine_development_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
