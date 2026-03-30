from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = BASE_DIR / "artifacts" / "data"
DEFAULT_RUN_DIR = BASE_DIR / "artifacts" / "runs"
DEFAULT_REPORT_DIR = BASE_DIR / "artifacts" / "reports"
DEFAULT_PAPER_DIR = BASE_DIR / "artifacts" / "paper"
DEFAULT_DB_PATH = BASE_DIR / "artifacts" / "strategy_lab.sqlite3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: Path = Field(default=DEFAULT_DB_PATH)
    data_dir: Path = Field(default=DEFAULT_DATA_DIR)
    run_dir: Path = Field(default=DEFAULT_RUN_DIR)
    report_dir: Path = Field(default=DEFAULT_REPORT_DIR)
    paper_dir: Path = Field(default=DEFAULT_PAPER_DIR)
    log_level: str = "INFO"
    timezone_name: str = "America/New_York"
    default_symbol: str = "XAU_USD"
    default_timeframe: str = "15m"
    hybrid_threshold: float = 0.65
    oanda_api_token: str = ""
    oanda_account_id: str = ""
    oanda_base_url: str = "https://api-fxpractice.oanda.com"

    @property
    def timezone(self) -> ZoneInfo:
        return load_tz(self.timezone_name)

    def ensure_dirs(self) -> None:
        for path in (
            self.db_path.parent,
            self.data_dir,
            self.run_dir,
            self.report_dir,
            self.paper_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
