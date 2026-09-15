from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ENGINE_VERSION = "tg_signal_management_v2"
IMPORTER_VERSION = "tg_snapshot_import_v4"
MODEL_VERSION = "tg_external_execution_v5"
SUPPORTED_ASSETS = ("XAUUSD", "EURUSD", "BTCUSD", "NASDAQ", "US30")
PROMOTION_STATES = {
    "INSUFFICIENT_EXACT_COVERAGE",
    "INSUFFICIENT_TRADES",
    "BASELINE_PARITY_FAILED",
    "RESEARCH_ONLY",
    "PROMOTION_CANDIDATE",
    "REJECTED",
}


@dataclass(frozen=True, slots=True)
class Tick:
    time_msc: int
    bid: float
    ask: float
    flags: int
    source_ordinal: int


@dataclass(frozen=True, slots=True)
class VenueTranslationMetadata:
    operational_migration: int
    provider_geometry_source: str
    execution_venue: str | None
    provider_entry_price: float | None
    provider_stop_loss: float | None
    provider_tp1: float | None
    provider_tp2: float | None
    provider_tp3: float | None
    venue_price_delta: float | None
    reference_quote_bid: float | None
    reference_quote_ask: float | None
    destination_quote_bid: float | None
    destination_quote_ask: float | None
    quote_skew_seconds: float | None
    quote_acquisition_seconds: float | None
    venue_order_id: str | None
    venue_position_key: str | None
    cohort_decision: str | None
    cohort_decided_at: str | None
    cohort_authority_execution_id: int | None
    cohort_authority_status: str | None
    cohort_authority_leg_count: int | None


@dataclass(frozen=True, slots=True)
class Leg:
    leg_id: str
    execution_id: str
    ordinal: int
    fraction: float
    requested_volume: float
    filled_volume: float
    native_target: str
    target_price: float | None
    order_ticket: str | None = None
    position_ticket: str | None = None
    actual_net_pnl: float | None = None
    venue_order_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExternalOperation:
    execution_id: str
    signal_id: str
    telegram_channel_id: str | None
    telegram_message_id: str | None
    published_at: str
    original_timezone: str | None
    broker_profile: str
    provider_symbol: str
    mt5_symbol: str
    side: Literal["BUY", "SELL"]
    timeframe: str
    strategy_lane: str
    signal_version: str
    parser_version: str
    statistics_schema_version: str
    execution_policy_version: str
    management_policy_version: str
    config_fingerprint: str
    provider_entry: float
    actual_fill: float
    entry_bid: float | None
    entry_ask: float | None
    spread: float | None
    initial_provider_sl: float
    tp1: float | None
    tp2: float | None
    tp3: float | None
    risk_amount: float
    risk_r: float
    requested_volume: float
    filled_volume: float
    volume_min: float | None
    volume_step: float | None
    opened_at: str
    closed_at: str | None
    broker_realized_net_pnl: float | None
    close_reason: str | None
    commission: float | None
    swap: float | None
    fees: float | None
    manual_intervention: bool
    anomalous_state: bool
    coverage_status: str
    coverage_start_at: str | None
    coverage_end_at: str | None
    coverage_gap_count: int
    checksum_status: str
    costs_complete: bool
    policy_resolved: bool
    symbol_spec_resolved: bool
    venue_translation: VenueTranslationMetadata
    legs: tuple[Leg, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ManagementPolicy:
    policy_id: str
    parent_policy_id: str | None
    management_policy_version: str
    partials: tuple[float, ...] = (0.5, 0.3, 0.2)
    tp1_action: str = "breakeven"
    breakeven_offset_price: float = 0.0
    breakeven_offset_points: float | None = None
    tp2_action: str = "stop_to_tp1"
    early_breakeven_activation_r: float | None = None
    early_breakeven_offset_r: float = 0.0
    early_breakeven_offset_price: float | None = None
    early_breakeven_offset_points: float | None = None
    trailing_activation_r: float | None = None
    trailing_distance_r: float | None = None
    trailing_distance_price: float | None = None
    trailing_distance_points: float | None = None
    trailing_step_r: float = 0.0
    trailing_after: str = "entry"
    time_stop_seconds: int | None = None
    mfe_protect_activation_r: float | None = None
    mfe_protect_fraction: float | None = None
    exit_slippage_price: float = 0.0
    latency_msc: int = 0
    stress_same_millisecond_stop_first: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ManagementPolicy":
        values = dict(payload)
        values["partials"] = tuple(float(value) for value in values.get("partials", (0.5, 0.3, 0.2)))
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["partials"] = list(self.partials)
        return payload


@dataclass(frozen=True, slots=True)
class TargetGeometryPolicy:
    geometry_id: str
    parent_geometry_id: str | None
    contract_version: str = "tg_target_geometry_v1"
    mode: Literal["PROVIDER_ORIGINAL", "FIXED_R"] = "PROVIDER_ORIGINAL"
    candidate_family: str = "BASELINE"
    tp1_r: float | None = None
    tp2_r: float | None = None
    tp3_r: float | None = None

    @classmethod
    def provider_original(cls) -> "TargetGeometryPolicy":
        return cls("provider_original", None)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetGeometryPolicy":
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExitFill:
    leg_id: str
    reason: str
    time_msc: int
    price: float
    volume: float
    gross_pnl: float
    net_pnl: float


@dataclass(frozen=True, slots=True)
class ReplayResult:
    execution_id: str
    policy_id: str
    status: str
    comparable: bool
    exclusions: tuple[str, ...]
    net_pnl: float | None
    result_r: float | None
    fills: tuple[ExitFill, ...]
    milestones: tuple[dict[str, Any], ...]
    final_remaining_volume: float
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_milliseconds(value: str) -> int:
    from datetime import UTC, datetime

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)
