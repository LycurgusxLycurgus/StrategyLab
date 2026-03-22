from __future__ import annotations

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    family_id: str
    dataset_id: str
    parameter_overrides: dict[str, float | int | bool | str] = Field(default_factory=dict)


class FamilySweepRequest(BaseModel):
    family_id: str
    dataset_id: str


class BacktestSummary(BaseModel):
    run_id: str
    family_id: str
    dataset_id: str
    timeframe: str
    status: str
    verdict: str
    parameters: dict[str, float | int | bool | str]
    metrics: dict
    artifact_path: str
    report_path: str | None = None


class FamilySweepSummary(BaseModel):
    family_id: str
    dataset_id: str
    total_variants: int
    rejected: int
    research_survivors: int
    paper_candidates: int
    best_run_id: str | None = None
    best_oos_sharpe: float | None = None
    runs: list[dict]
