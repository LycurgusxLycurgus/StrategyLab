from __future__ import annotations

from pydantic import BaseModel, Field


class ImportDatasetRequest(BaseModel):
    path: str
    symbol: str
    timeframe: str
    dataset_name: str = Field(min_length=3, max_length=80)


class DemoDatasetRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1H"
    dataset_name: str = "demo-btc-1h"
    bars: int = Field(default=240, ge=60, le=2000)


class BinanceDatasetRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1H"
    dataset_name: str = "binance-btc-1h"
    bars: int = Field(default=2500, ge=60, le=5000)


class DatasetSummary(BaseModel):
    dataset_id: str
    dataset_name: str
    symbol: str
    timeframe: str
    row_count: int
    start_ts: int
    end_ts: int
    source_path: str
