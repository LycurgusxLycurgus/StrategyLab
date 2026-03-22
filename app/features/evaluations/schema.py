from __future__ import annotations

from pydantic import BaseModel, Field


class MetricSet(BaseModel):
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    win_rate: float = 0.0
    trades: int = 0
    total_return: float = 0.0


class EvaluationSummary(BaseModel):
    overall: MetricSet
    out_of_sample: MetricSet
    fold_sharpes: list[float] = Field(default_factory=list)
    stable_walk_forward: bool = False
    verdict: str
