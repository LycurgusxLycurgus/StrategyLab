from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StrategyManifest(BaseModel):
    family_id: str
    title: str
    class_type: Literal["white_box", "hybrid", "black_box"]
    class_description: str = ""
    asset: str
    timeframe: str
    supported_timeframes: list[str] = Field(default_factory=list)
    min_bars_by_timeframe: dict[str, int] = Field(default_factory=dict)
    parameters: dict[str, float | int | bool | str] = Field(default_factory=dict)
    risk: dict[str, float | int] = Field(default_factory=dict)
    gates: dict[str, float] = Field(default_factory=dict)
    optimization_grid: dict[str, list[float | int | bool | str]] = Field(default_factory=dict)
    rules: dict[str, float | int | bool | str] = Field(default_factory=dict)
    notes_path: str


class StrategyDraftRequest(BaseModel):
    base_family_id: str
    new_family_id: str
    title: str
    asset: str
    timeframe: str
    parameter_overrides: dict[str, float | int | bool | str] = Field(default_factory=dict)
    notes: str = ""
