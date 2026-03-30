from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatasetDownloadRequest(BaseModel):
    symbol: Literal["XAU_USD"] = "XAU_USD"
    timeframe: Literal["15m"] = "15m"
    lookback_days: Literal[30, 45, 60] = 60
    provider: Literal["auto", "oanda"] = "auto"
    name: str | None = Field(default=None, max_length=80)


class DatasetRecord(BaseModel):
    dataset_id: str
    name: str
    symbol: str
    timeframe: str
    rows_count: int
    path: str
    created_at: datetime


class DatasetImportRequest(BaseModel):
    symbol: str = "XAU_USD"
    timeframe: str = "15m"
    name: str | None = Field(default=None, max_length=80)
