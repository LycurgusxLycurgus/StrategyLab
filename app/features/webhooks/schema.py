from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WebhookSignalRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "15m"
    timestamp: datetime
    direction: str
    entry: float
    stop: float
    target: float
    session_ny: int = Field(default=0, ge=0, le=1)
    sweep_depth_atr: float
    body_atr: float
    fvg_size_atr: float
    bias: int
    distance_to_prev_day_atr: float
