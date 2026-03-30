from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str


@dataclass(slots=True)
class Candidate:
    candidate_id: str
    ts: datetime
    direction: str
    sweep_level: str
    poi_type: str
    entry: float
    stop: float
    target: float
    atr: float
    reason: str
    features: dict[str, float | int | str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ts"] = self.ts.isoformat()
        return payload


@dataclass(slots=True)
class Trade:
    trade_id: str
    candidate_id: str
    direction: str
    entry_ts: datetime
    exit_ts: datetime
    entry: float
    exit: float
    stop: float
    target: float
    risk_r: float
    outcome_r: float
    exit_reason: str
    approved: bool = True
    model_score: float | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entry_ts"] = self.entry_ts.isoformat()
        payload["exit_ts"] = self.exit_ts.isoformat()
        return payload
