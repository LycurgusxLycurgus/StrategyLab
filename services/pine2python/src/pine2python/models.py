from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Candle(BaseModel):
    time: int = Field(description="Bar open time as a UNIX timestamp in milliseconds")
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class AnalyzeRequest(BaseModel):
    source: str = Field(min_length=1, max_length=1_000_000)
    name: str = "strategy.pine"
    provenance: dict[str, Any] = Field(default_factory=dict)


class ProofStreamExpression(BaseModel):
    name: str
    expression: str
    kind: Literal["bool", "int", "price", "float"] = "bool"
    scale: int = 1_000_000


class ProofRequest(BaseModel):
    source: str = Field(min_length=1, max_length=1_000_000)
    source_name: str = "strategy.pine"
    source_id: str | None = None
    dataset_sha256: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    profile: str = "basic_v1"
    instrumentation_version: Literal[
        "tv_table_v2_4", "tv_table_v2_5", "tv_table_v2_6", "tv_table_v2_7", "tv_table_v2_8", "tv_table_v2_9", "tv_table_v2_10", "tv_table_v2_11", "tv_table_v2_12"
    ] = (
        "tv_table_v2_12"
    )
    symbol: str
    timeframe: str
    start_ms: int
    end_ms: int
    mintick: float = Field(gt=0)
    candles: list[Candle] = Field(max_length=200_000)
    trace_rows: list[dict[str, Any]] = Field(default_factory=list, max_length=200_000)
    stream_expressions: dict[
        Literal["features", "states", "signals", "rejections", "orders"],
        list[ProofStreamExpression],
    ] = Field(default_factory=dict)
    declaration_kind: Literal["strategy", "indicator"] = "strategy"
    segments: int = Field(default=8, ge=1, le=16)
    local_runtime_policy: Literal[
        "attempt", "skip_static_blockers"
    ] = "attempt"
    local_runtime_blockers: list[dict[str, Any]] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_window(self) -> ProofRequest:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be earlier than end_ms")
        if (
            self.local_runtime_policy == "skip_static_blockers"
            and not self.local_runtime_blockers
        ):
            raise ValueError(
                "skip_static_blockers requires local_runtime_blockers"
            )
        return self


class TradingViewObservationRequest(BaseModel):
    expected: dict[str, Any]
    observed: dict[str, Any]
    screenshot_sha256: str | None = None
    user_verdict: Literal["accepted", "rejected", "pending"] = "pending"


class RuntimeRequest(BaseModel):
    source: str = Field(min_length=1, max_length=1_000_000)
    candles: list[Candle] = Field(max_length=200_000)
    symbol: str = "CUSTOM"
    timeframe: str = "1"
    timeout_seconds: float | None = Field(default=None, gt=0, le=120)


class ParityContract(BaseModel):
    key: str = "time"
    exact_fields: list[str] = Field(default_factory=list)
    tolerance_fields: dict[str, float] = Field(default_factory=dict)
    require_same_keys: bool = True


class ParityRequest(BaseModel):
    reference_rows: list[dict[str, Any]] = Field(max_length=200_000)
    candidate_rows: list[dict[str, Any]] = Field(max_length=200_000)
    contract: ParityContract


class GenerateRequest(BaseModel):
    parameters: dict[str, Any]
    title: str = "Pine2Python generated strategy"
    symbol: str = "BTCUSDT"
    timeframe: str = "15"
    mintick: float = Field(default=0.01, gt=0)
    start_ms: int
    end_ms: int
    profile: str = "basic_v1"
