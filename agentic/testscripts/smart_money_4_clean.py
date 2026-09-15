from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
P2P_SRC = ROOT / "services" / "pine2python" / "src"
for path in (ROOT, P2P_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import settings as app_settings
from app.data import Bar, DataService
from app.pine_workbench import PineWorkbenchService
from app.storage import Repository
from pine2python.config import Settings as P2PSettings
from pine2python.models import AnalyzeRequest, ProofRequest
from pine2python.service import Pine2PythonService

SOURCE_PATH = (
    ROOT / "pre-strategies" / "smart-money-4" / "smart-money-4-clean-indicator.pine"
)
CONTRACT_PATH = ROOT / "agentic" / "design" / "smart-money-4-clean-contract.md"
FIFTEEN_DATASET_ID = "ds_207c4624f554"
ONE_DATASET_ID = "ds_1e4ab545aa12"
PIVOT_LEN = 2
EXTERNAL_PIVOT_LEN = 4
HTF_PIVOT_LEN = 2
PROFILE_MIN_ROWS = 32
PROFILE_MAX_ROWS = 72
PROFILE_LOOKBACK_BARS = 500
PROFILE_ATR_FRACTION = 0.20
POC_ROW_TOLERANCE = 2
SWEEP_LOOKBACK = 12
MAX_STRUCTURE_LEVELS = 96
MAX_SWEEP_CANDIDATES = 64


class DirectClient:
    def __init__(self, service: Pine2PythonService) -> None:
        self.service = service

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.analyze(AnalyzeRequest.model_validate(payload))

    def proof(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.proof(ProofRequest.model_validate(payload))


@dataclass
class Setup:
    direction: int
    ready: int
    entry: float
    stop: float
    target: float
    score: int
    missing: str
    state: int = 0
    fill: int | None = None
    exit: int | None = None


@dataclass(frozen=True)
class NativeHtfBar:
    """Provider-owned completed interval; shortened session bars are legal."""

    open_ms: int
    close_ms: int
    high: float
    low: float


def raw_pivots(bars: list[Bar], length: int = PIVOT_LEN) -> tuple[list[float | None], list[float | None]]:
    highs: list[float | None] = [None] * len(bars)
    lows: list[float | None] = [None] * len(bars)
    for center in range(length, len(bars) - length):
        older = bars[center - length : center]
        newer = bars[center + 1 : center + length + 1]
        high = bars[center].high
        low = bars[center].low
        if all(high >= bar.high for bar in older) and all(high > bar.high for bar in newer):
            highs[center + length] = high
        if all(low <= bar.low for bar in older) and all(low < bar.low for bar in newer):
            lows[center + length] = low
    return highs, lows


def completed_htf_context(
    bars: list[Bar],
    pivot_length: int = HTF_PIVOT_LEN,
    native: list[NativeHtfBar] | None = None,
) -> list[tuple[float | None, float | None]]:
    if pivot_length < 1:
        raise ValueError("HTF pivot length must be positive")
    times = [int(bar.ts.timestamp() * 1000) for bar in bars]
    if any(bar.ts.tzinfo is None for bar in bars) or any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("LTF timestamps must be timezone-aware, unique and increasing")
    if native is not None:
        for index, candle in enumerate(native):
            if (candle.close_ms <= candle.open_ms or candle.close_ms - candle.open_ms > 14_400_000
                    or not math.isfinite(candle.high) or not math.isfinite(candle.low)
                    or candle.high < candle.low
                    or (index and native[index - 1].close_ms > candle.open_ms)):
                raise ValueError("Invalid or overlapping provider-owned 4h intervals")
        # No offset guessing or sixteen-child requirement for native candles.
        complete_keys = [candle.close_ms for candle in native]
        complete = {candle.close_ms: (candle.high, candle.low) for candle in native}
        return _htf_pivot_context(times, complete_keys, complete, pivot_length)
    groups: dict[int, list[Bar]] = defaultdict(list)
    keys: list[int] = []
    for bar in bars:
        key = int(bar.ts.timestamp()) // 14_400
        if key not in groups:
            keys.append(key)
        groups[key].append(bar)
    complete: dict[int, tuple[float, float]] = {}
    for key in keys:
        group = groups[key]
        expected = [key * 14_400 + offset * 900 for offset in range(16)]
        if [int(x.ts.timestamp()) for x in group] == expected:
            complete[(key + 1) * 14_400_000] = (max(x.high for x in group), min(x.low for x in group))
    complete_keys = sorted(complete)
    return _htf_pivot_context(times, complete_keys, complete, pivot_length)


def _htf_pivot_context(
    times: list[int], complete_keys: list[int],
    complete: dict[int, tuple[float, float]], pivot_length: int,
) -> list[tuple[float | None, float | None]]:
    """Join using provider close time, never the source pivot's earlier time."""
    htf_highs = [complete[key][0] for key in complete_keys]
    htf_lows = [complete[key][1] for key in complete_keys]
    confirmed_high: list[float | None] = [None] * len(complete_keys)
    confirmed_low: list[float | None] = [None] * len(complete_keys)
    for center in range(pivot_length, len(complete_keys) - pivot_length):
        older_highs = htf_highs[center - pivot_length : center]
        newer_highs = htf_highs[center + 1 : center + pivot_length + 1]
        older_lows = htf_lows[center - pivot_length : center]
        newer_lows = htf_lows[center + 1 : center + pivot_length + 1]
        if all(htf_highs[center] >= value for value in older_highs) and all(
            htf_highs[center] > value for value in newer_highs
        ):
            confirmed_high[center + pivot_length] = htf_highs[center]
        if all(htf_lows[center] <= value for value in older_lows) and all(
            htf_lows[center] < value for value in newer_lows
        ):
            confirmed_low[center + pivot_length] = htf_lows[center]
    state_by_key: dict[int, tuple[float | None, float | None]] = {}
    swing_high: float | None = None
    swing_low: float | None = None
    for index, key in enumerate(complete_keys):
        if confirmed_high[index] is not None:
            swing_high = confirmed_high[index]
        if confirmed_low[index] is not None:
            swing_low = confirmed_low[index]
        state_by_key[key] = (swing_high, swing_low)

    result: list[tuple[float | None, float | None]] = []
    cursor = 0
    state: tuple[float | None, float | None] = (None, None)
    for time_ms in times:
        while cursor < len(complete_keys) and complete_keys[cursor] <= time_ms:
            state = state_by_key[complete_keys[cursor]]
            cursor += 1
        result.append(state)
    return result


def atr_rma(bars: list[Bar], length: int = 14) -> list[float | None]:
    values: list[float | None] = [None] * len(bars)
    true_ranges: list[float] = []
    running: float | None = None
    for index, bar in enumerate(bars):
        previous_close = bars[index - 1].close if index > 0 else bar.close
        tr = max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))
        true_ranges.append(tr)
        if index == length - 1:
            running = sum(true_ranges[-length:]) / length
        elif index >= length and running is not None:
            running = (running * (length - 1) + tr) / length
        values[index] = running
    return values


def one_minute_map(bars: list[Bar]) -> dict[int, list[Bar]]:
    result: dict[int, list[Bar]] = defaultdict(list)
    for bar in bars:
        result[int(bar.ts.timestamp()) // 900].append(bar)
    return result


def volume_profile(
    fifteen: list[Bar],
    one_map: dict[int, list[Bar]],
    start: int,
    end: int,
    low: float,
    high: float,
    rows: int,
) -> tuple[list[float], float, int]:
    values = [0.0] * rows
    size = high - low
    row_height = size / rows
    for index in range(max(0, start), min(end + 1, len(fifteen))):
        key = int(fifteen[index].ts.timestamp()) // 900
        for bar in one_map.get(key, []):
            clipped_high = min(bar.high, high)
            clipped_low = max(bar.low, low)
            if clipped_high < clipped_low or bar.volume <= 0:
                continue
            first = max(0, min(rows - 1, int((clipped_low - low) // row_height)))
            last = max(0, min(rows - 1, int((clipped_high - low) // row_height)))
            share = bar.volume / max(1, last - first + 1)
            for row in range(first, last + 1):
                values[row] += share
    poc_row = max(range(rows), key=values.__getitem__)
    return values, low + (poc_row + 0.5) * row_height, poc_row


def missing_text(values: list[tuple[str, bool]]) -> str:
    failed = [name for name, value in values if not value]
    return ", ".join(failed) if failed else "NONE"


def evaluate(
    bars: list[Bar],
    one: list[Bar],
    *,
    fib_pct: float = 0.71,
    include_poc: bool = False,
    quality: str = "Standard",
    poc_tolerance: int = POC_ROW_TOLERANCE,
    structure_mode: str = "v6_sweep",
    pivot_length: int = PIVOT_LEN,
    native_htf: list[NativeHtfBar] | None = None,
    event_audit: list[dict[str, Any]] | None = None,
    sweep_audit: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[Setup]]:
    raw_highs, raw_lows = raw_pivots(bars, pivot_length)
    protected_owner = structure_mode == "protected_owner"
    bias_guard = structure_mode == "v6_bias"
    hierarchical = structure_mode in {"hierarchical", "protected", "protected_owner"}
    structure_highs, structure_lows = (
        raw_pivots(bars, EXTERNAL_PIVOT_LEN)
        if hierarchical
        else (raw_highs, raw_lows)
    )
    htf = completed_htf_context(bars, EXTERNAL_PIVOT_LEN if hierarchical else HTF_PIVOT_LEN, native_htf)
    atr = atr_rma(bars)
    one_map = one_minute_map(one)
    required = 100 if quality == "Perfect" else 80 if include_poc else 75
    array_structure = structure_mode in {
        "v6_endpoint", "v6_sweep", "v6_bias",
        "arrays",
        "latest",
        "hierarchical",
        "protected",
        "protected_owner",
    }

    active_high: float | None = None
    active_low: float | None = None
    active_high_index: int | None = None
    active_low_index: int | None = None
    high_consumed = False
    low_consumed = False
    last_pivot_type = 0
    buy_sweep: dict[str, Any] | None = None
    sell_sweep: dict[str, Any] | None = None
    high_levels: list[dict[str, Any]] = []
    low_levels: list[dict[str, Any]] = []
    sweep_candidates: list[dict[str, Any]] = []
    latest_confirmed_high: dict[str, Any] | None = None
    latest_confirmed_low: dict[str, Any] | None = None
    latest_external_high: dict[str, Any] | None = None
    latest_external_low: dict[str, Any] | None = None
    pending_bull_high: dict[str, Any] | None = None
    pending_bear_low: dict[str, Any] | None = None
    protected_bear_high: dict[str, Any] | None = None
    protected_bull_low: dict[str, Any] | None = None
    structure_trend = 0
    open_fvgs: list[dict[str, Any]] = []
    leg: dict[str, Any] | None = None
    latest: dict[str, Any] = {
        "direction": 0,
        "score": 0,
        "entry": None,
        "stop": None,
        "target": None,
        "bos_level": None,
        "sweep_level": None,
        "poc": None,
        "poc_distance_rows": None,
        "profile_rows": None,
        "fib_node_ratio": None,
        "htf_high": None,
        "htf_low": None,
        "htf_mid": None,
        "htf": False,
        "bos": False,
        "sweep": False,
        "imbalance": False,
        "poc_pass": False,
        "late": False,
        "eligible": False,
        "missing": "",
        "fvg_count": 0,
        "fvg_pass_count": 0,
        "break_fvg": False,
        "narrative_ready": False,
        "bos_kind": 0,
        "owner_role": 0,
        "owner_source": None,
        "owner_known": None,
        "sweep_bar": None,
        "sweep_level_bar": None,
        "bos_bar": None,
        "range_start": None,
        "range_end": None,
    }
    setups: list[Setup] = []
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    events_by_bar: dict[int, dict[str, Any]] = {}

    def finish_event(bos: int, status: str, at: int) -> None:
        record = events_by_bar[bos]
        if record["terminal"] != "AWAITING_RANGE":
            raise AssertionError("Structural event classified more than once")
        record.update(terminal=status, terminal_bar=at,
                      terminal_known_ms=int(bars[at].ts.timestamp() * 1000) + 900_000)

    def record_event(at: int, direction: int, owner: dict[str, Any] | None, starts_leg: bool) -> None:
        if starts_leg and leg is not None:
            finish_event(leg["bos"], "SUPERSEDED_BEFORE_LOCK", at)
        source = owner["source"] if owner else None
        known = owner["known"] if owner else None
        open_ms = int(bars[at].ts.timestamp() * 1000)
        source_ms = int(bars[source].ts.timestamp() * 1000) if source is not None else None
        known_ms = int(bars[known].ts.timestamp() * 1000) + 900_000 if known is not None else None
        level = owner["price"] if owner else None
        identity = [bars[at].symbol, bars[at].timeframe, open_ms, direction, source_ms, known_ms, level]
        record = dict(event_id=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20],
                      event_bar=at, event_open_ms=open_ms, event_known_ms=open_ms + 900_000,
                      direction=direction, owner_source_ms=source_ms, owner_known_ms=known_ms,
                      broken_level=level, bos_kind=bos_kind, owner_role=owner_role,
                      terminal="AWAITING_RANGE" if starts_leg else "LEG_ALREADY_OWNED",
                      terminal_bar=None if starts_leg else at,
                      terminal_known_ms=None if starts_leg else open_ms + 900_000)
        audit.append(record)
        events_by_bar[at] = record

    def record_sweep(kind: str, sweep: dict[str, Any], at: int) -> None:
        if sweep_audit is not None:
            sweep_audit.append(dict(kind=kind, at=at, **sweep))

    def preferred_sweeps(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if structure_mode not in {"v6_sweep", "v6_bias"} or not candidates:
            return candidates
        fresh = [s for s in candidates if s.get("linked_bar") is None]
        if fresh:
            return fresh
        latest_link = max(s["linked_bar"] for s in candidates)
        return [s for s in candidates if s["linked_bar"] == latest_link]

    for index, bar in enumerate(bars):
        signals = {
            "raw_high_pivot": False,
            "raw_low_pivot": False,
            "sweep_candidate": False,
            "sweep_linked": False,
            "sweep_invalidated": 0,
            "bull_break": False,
            "bear_break": False,
            "setup_ready": False,
            "long_ready": False,
            "short_ready": False,
            "fill": False,
            "target": False,
            "stop": False,
            "ambiguous": False,
            "candidate_updated": False,
        }
        rejection = ""
        bos_kind = 0  # 1 BOS, 2 CHoCH
        owner_role = 0  # 1 pending continuation, 2 protected opposite
        event_owner: dict[str, Any] | None = None

        confirmed_high = raw_highs[index] is not None
        confirmed_low = raw_lows[index] is not None
        structure_confirmed_high = structure_highs[index] is not None
        structure_confirmed_low = structure_lows[index] is not None
        signals["raw_high_pivot"] = confirmed_high
        signals["raw_low_pivot"] = confirmed_low
        # The hierarchical detector lets confirmed 4/4 external swings own
        # liquidity and BOS, while confirmed 2/2 internal swings only provide
        # the post-break endpoint and fallback range origin.
        if hierarchical and confirmed_high:
            latest_confirmed_high = {
                "id": f"IH{index - pivot_length}",
                "price": raw_highs[index],
                "source": index - pivot_length,
                "known": index,
                "active": True,
            }
        if hierarchical and confirmed_low:
            latest_confirmed_low = {
                "id": f"IL{index - pivot_length}",
                "price": raw_lows[index],
                "source": index - pivot_length,
                "known": index,
                "active": True,
            }
        if array_structure:
            accept_high = structure_confirmed_high
            accept_low = structure_confirmed_low
        else:
            accept_high = confirmed_high and (not confirmed_low or last_pivot_type <= 0)
            accept_low = confirmed_low and (not confirmed_high or last_pivot_type > 0)
        pivot_high_accepted = hierarchical and confirmed_high
        pivot_low_accepted = hierarchical and confirmed_low
        if accept_high and (
            array_structure
            or last_pivot_type != 1
            or active_high is None
            or structure_highs[index] > active_high  # type: ignore[operator]
        ):
            source = index - (EXTERNAL_PIVOT_LEN if hierarchical else pivot_length)
            accepted_high = structure_highs[index]
            if protected_owner:
                level = {
                    "id": f"H{source}",
                    "price": accepted_high,
                    "source": source,
                    "known": index,
                    "active": True,
                }
                latest_external_high = level
                if pending_bull_high is None or accepted_high > pending_bull_high["price"]:
                    pending_bull_high = level
            elif array_structure:
                if structure_mode in {"latest", "protected"}:
                    for level in high_levels:
                        level["active"] = False
                level = {
                    "id": f"H{source}",
                    "price": accepted_high,
                    "source": source,
                    "known": index,
                    "active": True,
                }
                high_levels.append(level)
                if not hierarchical:
                    latest_confirmed_high = level
                while len(high_levels) > MAX_STRUCTURE_LEVELS:
                    inactive = next((i for i, level in enumerate(high_levels) if not level["active"]), 0)
                    high_levels.pop(inactive)
            else:
                active_high = accepted_high
                active_high_index = source
                high_consumed = False
                if buy_sweep is not None and source > buy_sweep["bar"]:
                    buy_sweep = None
                last_pivot_type = 1
            if not hierarchical:
                pivot_high_accepted = True
        if accept_low and (
            array_structure
            or last_pivot_type != -1
            or active_low is None
            or structure_lows[index] < active_low  # type: ignore[operator]
        ):
            source = index - (EXTERNAL_PIVOT_LEN if hierarchical else pivot_length)
            accepted_low = structure_lows[index]
            if protected_owner:
                level = {
                    "id": f"L{source}",
                    "price": accepted_low,
                    "source": source,
                    "known": index,
                    "active": True,
                }
                latest_external_low = level
                if pending_bear_low is None or accepted_low < pending_bear_low["price"]:
                    pending_bear_low = level
            elif array_structure:
                if structure_mode in {"latest", "protected"}:
                    for level in low_levels:
                        level["active"] = False
                level = {
                    "id": f"L{source}",
                    "price": accepted_low,
                    "source": source,
                    "known": index,
                    "active": True,
                }
                low_levels.append(level)
                if not hierarchical:
                    latest_confirmed_low = level
                while len(low_levels) > MAX_STRUCTURE_LEVELS:
                    inactive = next((i for i, level in enumerate(low_levels) if not level["active"]), 0)
                    low_levels.pop(inactive)
            else:
                active_low = accepted_low
                active_low_index = source
                low_consumed = False
                if sell_sweep is not None and source > sell_sweep["bar"]:
                    sell_sweep = None
                last_pivot_type = -1
            if not hierarchical:
                pivot_low_accepted = True

        if protected_owner:
            eligible_high = pending_bull_high
            eligible_low = pending_bear_low
            for sweep in sweep_candidates:
                if sweep["valid"] and (
                    (sweep["direction"] == -1 and bar.close > sweep["level"])
                    or (sweep["direction"] == 1 and bar.close < sweep["level"])
                ):
                    sweep["valid"] = False
            swept_high = bool(
                eligible_high is not None
                and eligible_high["known"] < index
                and bar.high > eligible_high["price"]
                and bar.close <= eligible_high["price"]
            )
            swept_low = bool(
                eligible_low is not None
                and eligible_low["known"] < index
                and bar.low < eligible_low["price"]
                and bar.close >= eligible_low["price"]
            )
            if swept_high != swept_low:
                direction = -1 if swept_high else 1
                owner = eligible_high if swept_high else eligible_low
                assert owner is not None
                existing = next(
                    (
                        sweep
                        for sweep in sweep_candidates
                        if sweep["valid"]
                        and sweep["direction"] == direction
                        and sweep["level_index"] == owner["source"]
                    ),
                    None,
                )
                extreme = bar.high if direction == -1 else bar.low
                if existing is None:
                    sweep_candidates.append(
                        {
                            "direction": direction,
                            "bar": index,
                            "level_index": owner["source"],
                            "level": owner["price"],
                            "extreme": extreme,
                            "valid": True,
                        }
                    )
                else:
                    existing["bar"] = index
                    existing["extreme"] = (
                        max(existing["extreme"], extreme)
                        if direction == -1
                        else min(existing["extreme"], extreme)
                    )
                signals["sweep_candidate"] = True
            sweep_candidates = [sweep for sweep in sweep_candidates if sweep["valid"]][
                -MAX_SWEEP_CANDIDATES:
            ]
        elif array_structure:
            for sweep in sweep_candidates:
                if sweep["valid"] and (
                    (sweep["direction"] == -1 and bar.close > sweep["level"])
                    or (sweep["direction"] == 1 and bar.close < sweep["level"])
                ):
                    sweep["valid"] = False
                    signals["sweep_invalidated"] += 1
                    record_sweep("INVALIDATED", sweep, index)
            swept_highs = [
                level
                for level in high_levels
                if level["active"]
                and level["known"] < index
                and bar.high > level["price"]
                and bar.close <= level["price"]
            ]
            swept_lows = [
                level
                for level in low_levels
                if level["active"]
                and level["known"] < index
                and bar.low < level["price"]
                and bar.close >= level["price"]
            ]
            if bool(swept_highs) != bool(swept_lows):
                direction = -1 if swept_highs else 1
                levels = swept_highs if swept_highs else swept_lows
                for level in levels:
                    existing = next(
                        (
                            sweep
                            for sweep in sweep_candidates
                            if sweep["valid"]
                            and sweep["direction"] == direction
                            and sweep["level_index"] == level["source"]
                            and (structure_mode != "v6_sweep" or sweep.get("linked_bar") is None)
                        ),
                        None,
                    )
                    extreme = bar.high if direction == -1 else bar.low
                    if existing is None:
                        sweep_candidates.append(
                            {
                                "direction": direction,
                                "bar": index,
                                "level_index": level["source"],
                                "level": level["price"],
                                "extreme": extreme,
                                "valid": True,
                            }
                        )
                    else:
                        existing["bar"] = index
                        existing["extreme"] = (
                            max(existing["extreme"], extreme)
                            if direction == -1
                            else min(existing["extreme"], extreme)
                        )
                    signals["sweep_candidate"] = True
                    record_sweep("CREATED" if existing is None else "REFRESHED", sweep_candidates[-1] if existing is None else existing, index)
            sweep_candidates = [sweep for sweep in sweep_candidates if sweep["valid"]][
                -MAX_SWEEP_CANDIDATES:
            ]
        else:
            if buy_sweep is not None and (
                index - buy_sweep["bar"] > SWEEP_LOOKBACK
                or bar.close > buy_sweep["level"]
            ):
                buy_sweep = None
            if sell_sweep is not None and (
                index - sell_sweep["bar"] > SWEEP_LOOKBACK
                or bar.close < sell_sweep["level"]
            ):
                sell_sweep = None

            buy_now = active_high is not None and not high_consumed and bar.high > active_high and bar.close <= active_high
            sell_now = active_low is not None and not low_consumed and bar.low < active_low and bar.close >= active_low
            if buy_now and not sell_now:
                buy_sweep = {
                    "bar": index,
                    "level_index": active_high_index,
                    "level": active_high,
                    "extreme": bar.high,
                }
                signals["sweep_candidate"] = True
            if sell_now and not buy_now:
                sell_sweep = {
                    "bar": index,
                    "level_index": active_low_index,
                    "level": active_low,
                    "extreme": bar.low,
                }
                signals["sweep_candidate"] = True

        for fvg in open_fvgs:
            if fvg["valid"] and index > fvg["detect"]:
                mitigated = bar.low <= fvg["bottom"] if fvg["direction"] == 1 else bar.high >= fvg["top"]
                if mitigated:
                    fvg["valid"] = False
        if leg is not None:
            for fvg in leg["fvgs"]:
                if fvg["valid"] and index > fvg["source"] + 2:
                    mitigated = bar.low <= fvg["bottom"] if leg["direction"] == 1 else bar.high >= fvg["top"]
                    if mitigated:
                        fvg["valid"] = False

        new_fvg: dict[str, Any] | None = None
        if index >= 2 and bar.low > bars[index - 2].high:
            new_fvg = {
                "direction": 1,
                "bottom": bars[index - 2].high,
                "top": bar.low,
                "source": index - 2,
                "detect": index,
                "valid": True,
            }
        elif index >= 2 and bar.high < bars[index - 2].low:
            new_fvg = {
                "direction": -1,
                "bottom": bar.high,
                "top": bars[index - 2].low,
                "source": index - 2,
                "detect": index,
                "valid": True,
            }
        if new_fvg is not None:
            open_fvgs.append(dict(new_fvg))
            if leg is not None and leg["direction"] == new_fvg["direction"] and index > leg["bos"]:
                leg["fvgs"].append(dict(new_fvg))
        open_fvgs = open_fvgs[-96:]

        bull_level: dict[str, Any] | None = None
        bear_level: dict[str, Any] | None = None
        if protected_owner:
            previous_close = bars[index - 1].close if index > 0 else bar.close
            bullish_choch = bool(
                structure_trend == -1
                and protected_bear_high is not None
                and previous_close <= protected_bear_high["price"]
                and bar.close > protected_bear_high["price"]
            )
            bearish_choch = bool(
                structure_trend == 1
                and protected_bull_low is not None
                and previous_close >= protected_bull_low["price"]
                and bar.close < protected_bull_low["price"]
            )
            bullish_bos = bool(
                structure_trend != -1
                and pending_bull_high is not None
                and previous_close <= pending_bull_high["price"]
                and bar.close > pending_bull_high["price"]
            )
            bearish_bos = bool(
                structure_trend != 1
                and pending_bear_low is not None
                and previous_close >= pending_bear_low["price"]
                and bar.close < pending_bear_low["price"]
            )
            bull_break = bullish_choch or (bullish_bos and not bearish_choch)
            bear_break = bearish_choch or (bearish_bos and not bullish_choch)
            if bull_break and not bear_break:
                event_owner = protected_bear_high if bullish_choch else pending_bull_high
                bull_level = event_owner
                bos_kind = 2 if bullish_choch else 1
                owner_role = 2 if bullish_choch else 1
            elif bear_break and not bull_break:
                event_owner = protected_bull_low if bearish_choch else pending_bear_low
                bear_level = event_owner
                bos_kind = 2 if bearish_choch else 1
                owner_role = 2 if bearish_choch else 1
        elif array_structure:
            crossed_highs = [
                level
                for level in high_levels
                if level["active"] and level["known"] <= index and bar.close > level["price"]
            ]
            crossed_lows = [
                level
                for level in low_levels
                if level["active"] and level["known"] <= index and bar.close < level["price"]
            ]
            bull_level = (
                max(crossed_highs, key=lambda level: (level["price"], level["source"]))
                if crossed_highs
                else None
            )
            bear_level = (
                min(crossed_lows, key=lambda level: (level["price"], -level["source"]))
                if crossed_lows
                else None
            )
            bull_break = bull_level is not None
            bear_break = bear_level is not None
        else:
            bull_break = active_high is not None and not high_consumed and bar.close > active_high
            bear_break = active_low is not None and not low_consumed and bar.close < active_low

        # Preserve the permissive v6 raw event census, but do not promote an
        # internal opposing break to a new directional leg while the current
        # leg's protected extreme remains intact. A body close through that
        # extreme is still allowed to reverse the leg. This is deliberately a
        # narrow directional-role repair, not a 4/4 pivot owner filter.
        bull_guard_level = (
            latest_confirmed_high["price"]
            if bias_guard and latest_confirmed_high is not None
            else leg["stop"] if leg is not None else None
        )
        bear_guard_level = (
            latest_confirmed_low["price"]
            if bias_guard and latest_confirmed_low is not None
            else leg["stop"] if leg is not None else None
        )
        internal_bull_break = bool(
            bias_guard
            and bull_break
            and leg is not None
            and leg["direction"] == -1
            and bull_guard_level is not None
            and bar.close <= bull_guard_level
        )
        internal_bear_break = bool(
            bias_guard
            and bear_break
            and leg is not None
            and leg["direction"] == 1
            and bear_guard_level is not None
            and bar.close >= bear_guard_level
        )
        if internal_bull_break:
            bull_break = False
        if internal_bear_break:
            bear_break = False
        if bull_break and not bear_break:
            if protected_owner:
                assert bull_level is not None
                valid_sweeps = [
                    sweep
                    for sweep in sweep_candidates
                    if sweep["valid"]
                    and sweep["direction"] == 1
                    and bull_level["source"] < sweep["bar"] < index
                ]
                selected_sweep = (
                    min(preferred_sweeps(valid_sweeps), key=lambda sweep: (sweep["extreme"], -sweep["bar"]))
                    if valid_sweeps
                    else None
                )
                linked = selected_sweep is not None
                fallback = latest_confirmed_low
                start = selected_sweep["bar"] if linked else fallback["source"] if fallback else None
                stop = selected_sweep["extreme"] if linked else fallback["price"] if fallback else None
                bos_level_index = bull_level["source"]
                bos_level = bull_level["price"]
            elif array_structure:
                valid_sweeps = [
                    sweep
                    for sweep in sweep_candidates
                    if sweep["valid"]
                    and sweep["direction"] == 1
                    and bull_level is not None
                    and bull_level["source"] < sweep["bar"] < index
                ]
                selected_sweep = (
                    min(preferred_sweeps(valid_sweeps), key=lambda sweep: (sweep["extreme"], -sweep["bar"]))
                    if valid_sweeps
                    else None
                )
                linked = selected_sweep is not None
                fallback = latest_confirmed_low
                start = selected_sweep["bar"] if linked else fallback["source"] if fallback else None
                stop = selected_sweep["extreme"] if linked else fallback["price"] if fallback else None
                bos_level_index = bull_level["source"] if bull_level else None
                bos_level = bull_level["price"] if bull_level else None
            else:
                selected_sweep = sell_sweep
                linked = (
                    selected_sweep is not None
                    and selected_sweep["bar"] < index
                    and index - selected_sweep["bar"] <= SWEEP_LOOKBACK
                )
                fallback = None
                start = selected_sweep["bar"] if linked else active_low_index
                stop = selected_sweep["extreme"] if linked else active_low
                bos_level_index = active_high_index
                bos_level = active_high
            start_new_leg = protected_owner or not array_structure or leg is None or leg["direction"] != 1
            record_event(index, 1, bull_level, start_new_leg)
            if start_new_leg:
                leg = {
                    "direction": 1,
                    "bos": index,
                    "bos_level_index": bos_level_index,
                    "bos_level": bos_level,
                    "bos_kind": bos_kind,
                    "owner_role": owner_role,
                    "owner_known": event_owner["known"] if event_owner else None,
                    "sweep": linked,
                    "sweep_data": dict(selected_sweep) if linked else None,
                    "start": start,
                    "stop": stop,
                    "fvgs": [
                        dict(fvg)
                        for fvg in open_fvgs
                        if start is not None
                        and fvg["direction"] == 1
                        and fvg["valid"]
                        and start <= fvg["detect"] <= index
                    ],
                }
            if protected_owner:
                structure_trend = 1
                protected_bull_low = latest_external_low
                protected_bear_high = None
                pending_bull_high = None
                pending_bear_low = None
                for sweep in sweep_candidates:
                    sweep["valid"] = False
            elif array_structure:
                for level in crossed_highs:
                    level["active"] = False
                if start_new_leg and selected_sweep is not None:
                    signals["sweep_linked"] = True
                    record_sweep("LINKED", selected_sweep, index)
                    selected_sweep["linked_bar"] = index
                    if structure_mode not in {"v6_sweep", "v6_bias"}:
                        selected_sweep["valid"] = False
                        record_sweep("CONSUMED", selected_sweep, index)
            else:
                high_consumed = True
            signals["bull_break"] = True
            if not array_structure and linked:
                sell_sweep = None
        elif bear_break and not bull_break:
            if protected_owner:
                assert bear_level is not None
                valid_sweeps = [
                    sweep
                    for sweep in sweep_candidates
                    if sweep["valid"]
                    and sweep["direction"] == -1
                    and bear_level["source"] < sweep["bar"] < index
                ]
                selected_sweep = (
                    max(preferred_sweeps(valid_sweeps), key=lambda sweep: (sweep["extreme"], sweep["bar"]))
                    if valid_sweeps
                    else None
                )
                linked = selected_sweep is not None
                fallback = latest_confirmed_high
                start = selected_sweep["bar"] if linked else fallback["source"] if fallback else None
                stop = selected_sweep["extreme"] if linked else fallback["price"] if fallback else None
                bos_level_index = bear_level["source"]
                bos_level = bear_level["price"]
            elif array_structure:
                valid_sweeps = [
                    sweep
                    for sweep in sweep_candidates
                    if sweep["valid"]
                    and sweep["direction"] == -1
                    and bear_level is not None
                    and bear_level["source"] < sweep["bar"] < index
                ]
                selected_sweep = (
                    max(preferred_sweeps(valid_sweeps), key=lambda sweep: (sweep["extreme"], sweep["bar"]))
                    if valid_sweeps
                    else None
                )
                linked = selected_sweep is not None
                fallback = latest_confirmed_high
                start = selected_sweep["bar"] if linked else fallback["source"] if fallback else None
                stop = selected_sweep["extreme"] if linked else fallback["price"] if fallback else None
                bos_level_index = bear_level["source"] if bear_level else None
                bos_level = bear_level["price"] if bear_level else None
            else:
                selected_sweep = buy_sweep
                linked = (
                    selected_sweep is not None
                    and selected_sweep["bar"] < index
                    and index - selected_sweep["bar"] <= SWEEP_LOOKBACK
                )
                fallback = None
                start = selected_sweep["bar"] if linked else active_high_index
                stop = selected_sweep["extreme"] if linked else active_high
                bos_level_index = active_low_index
                bos_level = active_low
            start_new_leg = protected_owner or not array_structure or leg is None or leg["direction"] != -1
            record_event(index, -1, bear_level, start_new_leg)
            if start_new_leg:
                leg = {
                    "direction": -1,
                    "bos": index,
                    "bos_level_index": bos_level_index,
                    "bos_level": bos_level,
                    "bos_kind": bos_kind,
                    "owner_role": owner_role,
                    "owner_known": event_owner["known"] if event_owner else None,
                    "sweep": linked,
                    "sweep_data": dict(selected_sweep) if linked else None,
                    "start": start,
                    "stop": stop,
                    "fvgs": [
                        dict(fvg)
                        for fvg in open_fvgs
                        if start is not None
                        and fvg["direction"] == -1
                        and fvg["valid"]
                        and start <= fvg["detect"] <= index
                    ],
                }
            if protected_owner:
                structure_trend = -1
                protected_bear_high = latest_external_high
                protected_bull_low = None
                pending_bull_high = None
                pending_bear_low = None
                for sweep in sweep_candidates:
                    sweep["valid"] = False
            elif array_structure:
                for level in crossed_lows:
                    level["active"] = False
                if start_new_leg and selected_sweep is not None:
                    signals["sweep_linked"] = True
                    record_sweep("LINKED", selected_sweep, index)
                    selected_sweep["linked_bar"] = index
                    if structure_mode not in {"v6_sweep", "v6_bias"}:
                        selected_sweep["valid"] = False
                        record_sweep("CONSUMED", selected_sweep, index)
            else:
                low_consumed = True
            signals["bear_break"] = True
            if not array_structure and linked:
                buy_sweep = None

        # v6.1 accepts a confirmed pivot whose source is the BOS candle itself.
        # Explicit historical modes retain their original strict-after rule.
        endpoint_after = leg is not None and index - pivot_length > leg["bos"]
        endpoint_on_bos = leg is not None and structure_mode in {"v6_endpoint", "v6_sweep", "v6_bias"} and index - pivot_length == leg["bos"]
        lock_long = leg is not None and leg["direction"] == 1 and pivot_high_accepted and (endpoint_after or endpoint_on_bos)
        lock_short = leg is not None and leg["direction"] == -1 and pivot_low_accepted and (endpoint_after or endpoint_on_bos)
        if lock_long or lock_short:
            assert leg is not None
            direction = 1 if lock_long else -1
            endpoint_index = index - pivot_length
            endpoint = raw_highs[index] if lock_long else raw_lows[index]
            assert endpoint is not None
            range_low = leg["stop"] if direction == 1 else endpoint
            range_high = endpoint if direction == 1 else leg["stop"]
            valid = (
                range_low is not None
                and range_high is not None
                and range_high > range_low
                and leg["start"] is not None
            )
            if valid:
                size = range_high - range_low
                entry = range_high - fib_pct * size if direction == 1 else range_low + fib_pct * size
                stop = range_low if direction == 1 else range_high
                target = range_high if direction == 1 else range_low
                valid_fvgs = [fvg for fvg in leg["fvgs"] if fvg["valid"]][-8:]
                matching = [
                    fvg
                    for fvg in valid_fvgs
                    if fvg["bottom"] <= entry <= fvg["top"]
                ]
                imbalance = bool(matching)
                # Pine's rolling lower-timeframe arrays retain only the latest
                # PROFILE_LOOKBACK_BARS at the bar where the range is locked.
                # Mirror that ownership boundary exactly for raw POC parity.
                target_row_height = max(0.01, (atr[index] or size / PROFILE_MIN_ROWS) * PROFILE_ATR_FRACTION)
                profile_rows = max(
                    PROFILE_MIN_ROWS,
                    min(PROFILE_MAX_ROWS, math.ceil(size / target_row_height)),
                )
                profile_start = max(leg["start"], index - PROFILE_LOOKBACK_BARS)
                profile, poc, poc_row = volume_profile(
                    bars,
                    one_map,
                    profile_start,
                    endpoint_index,
                    range_low,
                    range_high,
                    profile_rows,
                )
                row_height = size / profile_rows
                fib_row = max(0, min(profile_rows - 1, int((entry - range_low) // row_height)))
                poc_distance_rows = abs(poc_row - fib_row)
                poc_pass = poc_distance_rows <= poc_tolerance and max(profile) > 0
                golden_a = range_high - 0.71 * size if direction == 1 else range_low + 0.71 * size
                golden_b = range_high - 0.75 * size if direction == 1 else range_low + 0.75 * size
                golden_low, golden_high = sorted((golden_a, golden_b))
                golden_first = max(0, min(profile_rows - 1, int((golden_low - range_low) // row_height)))
                golden_last = max(0, min(profile_rows - 1, int((golden_high - range_low) // row_height)))
                fib_node_volume = max(profile[golden_first : golden_last + 1], default=0.0)
                fib_node_ratio = fib_node_volume / max(profile) if max(profile) > 0 else None
                htf_high, htf_low = htf[index]
                midpoint = (htf_high + htf_low) / 2 if htf_high is not None and htf_low is not None else None
                htf_pass = midpoint is not None and (bar.close <= midpoint if direction == 1 else bar.close >= midpoint)
                bos_pass = all(
                    leg.get(name) is not None
                    for name in ("bos", "bos_level_index", "bos_level")
                )
                count = int(htf_pass) + int(bos_pass) + int(leg["sweep"]) + int(imbalance) + (int(poc_pass) if include_poc else 0)
                score = count * (20 if include_poc else 25)
                late = any(
                    bars[offset].low <= entry if direction == 1 else bars[offset].high >= entry
                    for offset in range(endpoint_index + 1, index + 1)
                )
                eligible = score >= required and not late
                missing = missing_text(
                    [
                        ("HTF", htf_pass),
                        ("BOS", bos_pass),
                        ("LQ", leg["sweep"]),
                        ("FVG", imbalance),
                        *(([("POC", poc_pass)]) if include_poc else []),
                    ]
                )
                latest = {
                    "direction": direction,
                    "score": score,
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "bos_level": leg["bos_level"],
                    "sweep_level": leg["sweep_data"]["level"] if leg["sweep_data"] else None,
                    "poc": poc,
                    "poc_distance_rows": poc_distance_rows,
                    "profile_rows": profile_rows,
                    "fib_node_ratio": fib_node_ratio,
                    "htf_high": htf_high,
                    "htf_low": htf_low,
                    "htf_mid": midpoint,
                    "htf": htf_pass,
                    "bos": bos_pass,
                    "sweep": leg["sweep"],
                    "imbalance": imbalance,
                    "poc_pass": poc_pass,
                    "late": late,
                    "eligible": eligible,
                    "missing": missing,
                    "profile_volume": sum(profile),
                    "fvg_count": len(valid_fvgs),
                    "fvg_pass_count": len(matching),
                    "break_fvg": any(fvg["detect"] <= leg["bos"] for fvg in valid_fvgs),
                    "narrative_ready": True,
                    "sweep_bar": leg["sweep_data"]["bar"] if leg["sweep_data"] else None,
                    "sweep_level_bar": leg["sweep_data"]["level_index"] if leg["sweep_data"] else None,
                    "bos_bar": leg["bos"],
                    "range_start": leg["start"],
                    "range_end": endpoint_index,
                    "bos_kind": leg.get("bos_kind", 0),
                    "owner_role": leg.get("owner_role", 0),
                    "owner_source": leg["bos_level_index"],
                    "owner_known": leg.get("owner_known"),
                }
                signals["candidate_updated"] = True
                events_by_bar[leg["bos"]].update(
                    candidate_bar=index, range_start_ms=int(bars[leg["start"]].ts.timestamp() * 1000),
                    range_end_ms=int(bars[endpoint_index].ts.timestamp() * 1000),
                    score=score, missing=missing, late=late, sweep=bool(leg["sweep"]),
                    entry=entry, stop=stop, target=target,
                    sweep_snapshot=dict(leg["sweep_data"]) if leg["sweep_data"] else None)
                finish_event(leg["bos"], "SETUP_READY" if eligible else "LATE" if late else "SCORE", index)
                if eligible:
                    setups.append(Setup(direction, index, entry, stop, target, score, missing))
                    signals["setup_ready"] = True
                    signals["long_ready"] = direction == 1
                    signals["short_ready"] = direction == -1
                else:
                    rejection = "LATE" if late else "SCORE"
            else:
                finish_event(leg["bos"], "INVALID_RANGE", index)
            leg = None

        for setup in setups:
            if index <= setup.ready or setup.state > 1:
                continue
            entry_touch = bar.low <= setup.entry if setup.direction == 1 else bar.high >= setup.entry
            stop_touch = bar.low <= setup.stop if setup.direction == 1 else bar.high >= setup.stop
            target_touch = bar.high >= setup.target if setup.direction == 1 else bar.low <= setup.target
            gap_past_stop = bar.open <= setup.stop if setup.direction == 1 else bar.open >= setup.stop
            if setup.state == 0:
                if entry_touch:
                    setup.fill = index
                    signals["fill"] = True
                    if target_touch or (stop_touch and gap_past_stop):
                        setup.state = 5
                        setup.exit = index
                        signals["ambiguous"] = True
                    elif stop_touch:
                        setup.state = 3
                        setup.exit = index
                        signals["stop"] = True
                    else:
                        setup.state = 1
                elif stop_touch or target_touch:
                    setup.state = 4
                    setup.exit = index
            elif setup.state == 1:
                if stop_touch and target_touch:
                    setup.state = 5
                    setup.exit = index
                    signals["ambiguous"] = True
                elif target_touch:
                    setup.state = 2
                    setup.exit = index
                    signals["target"] = True
                elif stop_touch:
                    setup.state = 3
                    setup.exit = index
                    signals["stop"] = True

        rows.append(
            {
                "time": int(bar.ts.timestamp() * 1000),
                "features": {
                    "direction": latest["direction"],
                    "score": latest["score"],
                    "entry": latest["entry"],
                    "stop": latest["stop"],
                    "target": latest["target"],
                    "bos_level": latest["bos_level"],
                    "sweep_level": latest["sweep_level"],
                    "poc": latest["poc"],
                    "poc_distance_rows": latest["poc_distance_rows"],
                    "profile_rows": latest["profile_rows"],
                    "fib_node_ratio": latest["fib_node_ratio"],
                    "htf_high": latest["htf_high"],
                    "htf_low": latest["htf_low"],
                    "htf_mid": latest["htf_mid"],
                    "htf": latest["htf"],
                    "bos": latest["bos"],
                    "sweep": latest["sweep"],
                    "imbalance": latest["imbalance"],
                    "poc_pass": latest["poc_pass"],
                    "late": latest["late"],
                    "eligible": latest["eligible"],
                    "missing": latest["missing"],
                    "fvg_count": latest["fvg_count"],
                    "fvg_pass_count": latest["fvg_pass_count"],
                    "break_fvg": latest["break_fvg"],
                    "narrative_ready": latest["narrative_ready"],
                    "bos_kind": latest["bos_kind"],
                    "owner_role": latest["owner_role"],
                    "owner_source": latest["owner_source"],
                    "owner_known": latest["owner_known"],
                    "sweep_bar": latest["sweep_bar"],
                    "sweep_time": int(bars[latest["sweep_bar"]].ts.timestamp() * 1000) if latest["sweep_bar"] is not None else None,
                    "sweep_level_time": int(bars[latest["sweep_level_bar"]].ts.timestamp() * 1000) if latest["sweep_level_bar"] is not None else None,
                    "bos_time": int(bars[latest["bos_bar"]].ts.timestamp() * 1000) if latest["bos_bar"] is not None else None,
                    "bos_bar": latest["bos_bar"],
                    "range_start": latest["range_start"],
                    "range_end": latest["range_end"],
                },
                "signals": signals,
                "structure": {
                    "trend": structure_trend if protected_owner else 0,
                    "bos_kind": bos_kind,
                    "owner_role": owner_role,
                    "owner_source": (bull_level or bear_level or {}).get("source"),
                    "owner_known": (bull_level or bear_level or {}).get("known"),
                    "owner_price": (bull_level or bear_level or {}).get("price"),
                    "pending_high_source": pending_bull_high["source"] if pending_bull_high else None,
                    "pending_low_source": pending_bear_low["source"] if pending_bear_low else None,
                    "protected_high_source": protected_bear_high["source"] if protected_bear_high else None,
                    "protected_low_source": protected_bull_low["source"] if protected_bull_low else None,
                },
                "rejections": {"code": rejection},
            }
        )
    if leg is not None:
        # Censored at this supplied window, not an invented historical rejection.
        events_by_bar[leg["bos"]]["terminal"] = "WINDOW_END_UNRESOLVED"
    if event_audit is not None:
        event_audit.extend(audit)
    return rows, setups


def contract_fixtures() -> dict[str, bool]:
    """Deterministic bearish narrative with its causal FVG formed on BOS."""
    prices = [
        (100, 101, 99, 100),
        (101, 102, 100, 101),
        (103, 105, 101, 104),  # owned swing high
        (102, 103, 100, 101),
        (100, 102, 98, 99),    # owned swing low
        (101, 104, 99, 103),
        (104, 106, 103, 104),  # buy-side wick/reclaim sweep
        (101, 104, 99, 100),
        (97, 97, 94, 96),      # bearish BOS and bearish FVG vs bar 6
        (96, 97, 93, 94),
        (94, 96, 90, 92),      # post-break endpoint
        (93, 95, 92, 94),
        (94, 95, 93, 94),      # endpoint becomes knowable here
        (94, 96, 93, 95),
    ]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    fifteen = [
        Bar(start + timedelta(minutes=15 * i), o, h, l, c, 100 + i, "FIXTURE", "15m")
        for i, (o, h, l, c) in enumerate(prices)
    ]
    one = [
        Bar(bar.ts, bar.open, bar.high, bar.low, bar.close, bar.volume, "FIXTURE", "1m")
        for bar in fifteen
    ]
    # This compact fixture isolates sweep -> BOS -> FVG -> range semantics.
    # External/internal hierarchy is exercised separately on the full mirror
    # census because a 4/4 swing needs substantially more surrounding bars.
    rows, setups = evaluate(fifteen, one, include_poc=False, structure_mode="arrays")
    mirror_axis = 200.0
    mirrored = [
        Bar(
            bar.ts,
            mirror_axis - bar.open,
            mirror_axis - bar.low,
            mirror_axis - bar.high,
            mirror_axis - bar.close,
            bar.volume,
            "FIXTURE_MIRROR",
            "15m",
        )
        for bar in fifteen
    ]
    mirrored_one = [
        Bar(bar.ts, bar.open, bar.high, bar.low, bar.close, bar.volume, "FIXTURE_MIRROR", "1m")
        for bar in mirrored
    ]
    mirror_rows, mirror_setups = evaluate(
        mirrored,
        mirrored_one,
        include_poc=False,
        structure_mode="arrays",
    )
    narratives = [row for row in rows if row["signals"]["candidate_updated"]]
    narrative = narratives[-1] if narratives else None
    mirror_structure_symmetry = all(
        row["signals"]["raw_high_pivot"] == mirror["signals"]["raw_low_pivot"]
        and row["signals"]["raw_low_pivot"] == mirror["signals"]["raw_high_pivot"]
        and row["signals"]["bull_break"] == mirror["signals"]["bear_break"]
        and row["signals"]["bear_break"] == mirror["signals"]["bull_break"]
        and row["signals"]["candidate_updated"] == mirror["signals"]["candidate_updated"]
        and (
            not row["signals"]["candidate_updated"]
            or row["features"]["direction"] == -mirror["features"]["direction"]
        )
        for row, mirror in zip(rows, mirror_rows, strict=True)
    )
    boundary = list(fifteen[:11])
    boundary[8] = Bar(fifteen[8].ts, 97, 97, 90, 92, 108, "FIXTURE", "15m")
    boundary[9] = Bar(fifteen[9].ts, 93, 96, 92, 94, 109, "FIXTURE", "15m")
    boundary[10] = Bar(fifteen[10].ts, 94, 96, 93, 95, 110, "FIXTURE", "15m")
    boundary_rows, boundary_setups = evaluate(boundary, [])
    _, old_boundary = evaluate(boundary, [], structure_mode="arrays")
    mirror_boundary = [Bar(b.ts, 200-b.open, 200-b.low, 200-b.high, 200-b.close, b.volume, "FIXTURE", "15m") for b in boundary]
    _, mirror_boundary_setups = evaluate(mirror_boundary, [])
    return {
        "bos_endpoint_waits_for_confirmation": not any(r["signals"]["candidate_updated"] for r in boundary_rows[:10]),
        "bos_endpoint_recovers_short": len(boundary_setups) == 1 and boundary_setups[0].ready == 10 and boundary_setups[0].direction == -1,
        "bos_endpoint_recovers_long": len(mirror_boundary_setups) == 1 and mirror_boundary_setups[0].ready == 10 and mirror_boundary_setups[0].direction == 1,
        "bos_endpoint_was_missed_by_v6": not old_boundary,
        "bos_candle_fvg_retained": bool(narrative and narrative["features"]["break_fvg"]),
        "linked_sweep_retained": bool(narrative and narrative["features"]["sweep"]),
        "fib_overlaps_causal_fvg": bool(narrative and narrative["features"]["imbalance"]),
        "core_75_ready": len(setups) == 1 and setups[0].score == 75,
        "narrative_visible_when_scored": bool(narrative and narrative["features"]["narrative_ready"]),
        "long_short_structure_mirror": mirror_structure_symmetry,
        "long_short_setup_count_mirror": len(setups) == len(mirror_setups),
    }


def stream_expressions() -> dict[str, list[dict[str, str]]]:
    def field(category: str, name: str, expression: str, kind: str) -> dict[str, str]:
        return {"name": f"{category}.{name}", "expression": expression, "kind": kind}

    return {
        "features": [
            field("features", "direction", "candidateDirection", "int"),
            field("features", "score", "candidateScore", "int"),
            field("features", "entry", "candidateEntry", "price"),
            field("features", "stop", "candidateStop", "price"),
            field("features", "target", "candidateTarget", "price"),
            field("features", "bos_level", "candidateBosLevel", "price"),
            field("features", "sweep_level", "candidateSweepLevel", "price"),
            field("features", "poc", "candidatePoc", "price"),
            field("features", "poc_distance_rows", "candidatePocDistanceRows", "int"),
            field("features", "profile_rows", "candidateProfileRows", "int"),
            field("features", "fib_node_ratio", "candidateFibNodeRatio", "float"),
            field("features", "htf_high", "candidateHtfHigh", "price"),
            field("features", "htf_low", "candidateHtfLow", "price"),
            field("features", "htf_mid", "candidateHtfMid", "price"),
            field("features", "htf", "candidateHtf", "bool"),
            field("features", "bos", "candidateBos", "bool"),
            field("features", "sweep", "candidateSweep", "bool"),
            field("features", "imbalance", "candidateImbalance", "bool"),
            field("features", "poc_pass", "candidatePocPass", "bool"),
            field("features", "fvg_count", "candidateFvgCount", "int"),
            field("features", "fvg_pass_count", "candidateFvgPassCount", "int"),
            field("features", "break_fvg", "candidateBreakFvg", "bool"),
            field("features", "narrative_ready", "not na(candidateReadyBar)", "bool"),
            field("features", "sweep_time", "f_time_at(candidateSweepBar)", "int"),
            field("features", "sweep_level_time", "f_time_at(candidateSweepLevelBar)", "int"),
            field("features", "bos_time", "f_time_at(candidateBosBar)", "int"),
        ],
        "signals": [
            field("signals", "bull_break", "bullBreakSignal", "bool"),
            field("signals", "bear_break", "bearBreakSignal", "bool"),
            field("signals", "raw_high_pivot", "rawHighPivotSignal", "bool"),
            field("signals", "raw_low_pivot", "rawLowPivotSignal", "bool"),
            field("signals", "sweep_candidate", "sweepCandidateSignal", "bool"),
            field("signals", "sweep_linked", "sweepLinkedSignal", "bool"),
            field("signals", "sweep_invalidated", "sweepInvalidatedCount", "int"),
            field("signals", "candidate_updated", "candidateUpdatedSignal", "bool"),
            field("signals", "setup_ready", "setupReadySignal", "bool"),
            field("signals", "long_ready", "longReadySignal", "bool"),
            field("signals", "short_ready", "shortReadySignal", "bool"),
            field("signals", "fill", "fillSignal", "bool"),
            field("signals", "target", "targetSignal", "bool"),
            field("signals", "stop", "stopSignal", "bool"),
            field("signals", "ambiguous", "ambiguousSignal", "bool"),
        ],
    }


def event_accounting(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(event["terminal"] for event in events)
    expected = sum(bool(row["signals"]["bull_break"] or row["signals"]["bear_break"]) for row in rows)
    allowed = {"SUPERSEDED_BEFORE_LOCK", "LEG_ALREADY_OWNED", "INVALID_RANGE", "SCORE", "LATE", "SETUP_READY", "WINDOW_END_UNRESOLVED"}
    return {
        "structural_events": expected,
        "accounted_events": len(events),
        "terminal_counts": dict(statuses),
        "complete": (len(events) == expected == len({event["event_id"] for event in events})
                     and set(statuses) <= allowed
                     and statuses["SETUP_READY"] == sum(row["signals"]["setup_ready"] for row in rows)),
        "by_direction": {str(direction): dict(Counter(event["terminal"] for event in events if event["direction"] == direction)) for direction in (1, -1)},
    }


def counts(rows: list[dict[str, Any]], setups: list[Setup]) -> dict[str, Any]:
    signal_counts = Counter(
        name
        for row in rows
        for name, value in row["signals"].items()
        if value
    )
    score_counts = Counter(
        int(row["features"]["score"])
        for row in rows
        if row["signals"]["setup_ready"]
    )
    state_counts = Counter(setup.state for setup in setups)
    rejection_counts = Counter(
        row["rejections"]["code"] for row in rows if row["rejections"]["code"]
    )
    return {
        "signals": dict(signal_counts),
        "ready_scores": dict(score_counts),
        "states": dict(state_counts),
        "rejections": dict(rejection_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", type=int, default=5_000)
    parser.add_argument("--register", action="store_true")
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Run the deterministic Python detector without Pine parsing or registration.",
    )
    parser.add_argument(
        "--diagnose-feature-groups",
        action="store_true",
        help="Register contiguous feature-only proof dashboards for Pine/TradingView mismatch localization.",
    )
    args = parser.parse_args()

    repo = Repository()
    data = DataService(repo)
    bars = data.load_bars(FIFTEEN_DATASET_ID)[-args.bars :]
    one = data.load_bars(ONE_DATASET_ID)
    start = bars[0].ts
    one = [bar for bar in one if bar.ts >= start]
    audit_events: list[dict[str, Any]] = []
    rows, setups = evaluate(bars, one, event_audit=audit_events)
    fixtures = contract_fixtures()
    weeks = max((bars[-1].ts - bars[0].ts).total_seconds() / 604_800, 1 / 7)
    variants: dict[str, Any] = {}
    for variant_name, variant_poc, variant_quality in (
        ("video_standard_75", False, "Standard"),
        ("poc_extended_standard_80", True, "Standard"),
        ("video_perfect_100", False, "Perfect"),
        ("poc_extended_perfect_100", True, "Perfect"),
    ):
        variant_rows, variant_setups = (
            (rows, setups)
            if variant_name == "video_standard_75"
            else evaluate(bars, one, include_poc=variant_poc, quality=variant_quality)
        )
        variants[variant_name] = {
            "setups": len(variant_setups),
            "per_week": round(len(variant_setups) / weeks, 3),
            "long": sum(setup.direction == 1 for setup in variant_setups),
            "short": sum(setup.direction == -1 for setup in variant_setups),
            "states": dict(Counter(setup.state for setup in variant_setups)),
            "candidates": sum(row["signals"]["candidate_updated"] for row in variant_rows),
        }
    poc_tolerance_variants: dict[str, Any] = {}
    for tolerance in (0, 1, 2):
        tolerance_rows, tolerance_setups = evaluate(
            bars,
            one,
            include_poc=True,
            quality="Standard",
            poc_tolerance=tolerance,
        )
        poc_tolerance_variants[str(tolerance)] = {
            "poc_positive_candidates": sum(
                row["signals"]["candidate_updated"] and row["features"]["poc_distance_rows"] <= tolerance
                for row in tolerance_rows
            ),
            "setups": len(tolerance_setups),
            "per_week": round(len(tolerance_setups) / weeks, 3),
            "long": sum(setup.direction == 1 for setup in tolerance_setups),
            "short": sum(setup.direction == -1 for setup in tolerance_setups),
        }
    candidate_rows = [row for row in rows if row["signals"]["candidate_updated"]]
    checklist_funnel = {
        "candidates": len(candidate_rows),
        "htf_pass": sum(row["features"]["htf"] for row in candidate_rows),
        "bos_pass": sum(row["features"]["bos"] for row in candidate_rows),
        "sweep_pass": sum(row["features"]["sweep"] for row in candidate_rows),
        "imbalance_pass": sum(row["features"]["imbalance"] for row in candidate_rows),
        "poc_pass": sum(row["features"]["poc_pass"] for row in candidate_rows),
        "profile_rows": dict(Counter(int(row["features"]["profile_rows"]) for row in candidate_rows)),
    }
    setup_checklist_distribution = dict(Counter(setup.missing for setup in setups))
    setup_sweep_pass = sum(bool(rows[setup.ready]["features"]["sweep"]) for setup in setups)
    ambiguous_examples: list[dict[str, Any]] = []
    for setup in setups:
        if setup.state != 5 or setup.exit is None:
            continue
        exit_bar = bars[setup.exit]
        stop_touch = exit_bar.low <= setup.stop if setup.direction == 1 else exit_bar.high >= setup.stop
        target_touch = exit_bar.high >= setup.target if setup.direction == 1 else exit_bar.low <= setup.target
        same_as_fill = setup.fill == setup.exit
        gap_past_stop = exit_bar.open <= setup.stop if setup.direction == 1 else exit_bar.open >= setup.stop
        if not same_as_fill:
            reason = "OPEN_STOP_TARGET_SAME_BAR"
        elif stop_touch and target_touch:
            reason = "ENTRY_STOP_TARGET_SAME_BAR"
        elif target_touch:
            reason = "ENTRY_TARGET_SAME_BAR"
        elif gap_past_stop:
            reason = "ENTRY_STOP_GAP_SAME_BAR"
        else:
            reason = "ENTRY_STOP_ORDERED_SAME_BAR"
        ambiguous_examples.append(
            {
                "direction": "LONG" if setup.direction == 1 else "SHORT",
                "ready": bars[setup.ready].ts.isoformat(),
                "fill_exit": exit_bar.ts.isoformat(),
                "reason": reason,
                "open": exit_bar.open,
                "high": exit_bar.high,
                "low": exit_bar.low,
                "close": exit_bar.close,
            }
        )
    ambiguous_reason_counts = dict(Counter(item["reason"] for item in ambiguous_examples))
    sweep_setup_examples = [
        {
            "direction": "LONG" if setup.direction == 1 else "SHORT",
            "ready": bars[setup.ready].ts.isoformat(),
            "score": setup.score,
            "missing": setup.missing,
            "state": setup.state,
        }
        for setup in setups
        if rows[setup.ready]["features"]["sweep"]
    ][-10:]
    no_sweep_setup_examples = [
        {
            "direction": "LONG" if setup.direction == 1 else "SHORT",
            "ready": bars[setup.ready].ts.isoformat(),
            "score": setup.score,
            "missing": setup.missing,
            "state": setup.state,
        }
        for setup in setups
        if not rows[setup.ready]["features"]["sweep"]
    ][-10:]
    if args.evaluate_only:
        shadow_detectors: dict[str, Any] = {}
        for detector, detector_mode, detector_pivot in (
            ("v6_endpoint_2", "v6_endpoint", 2),
            ("legacy_2", "legacy", 2),
            ("latest_2", "latest", 2),
            ("arrays_2", "arrays", 2),
            ("arrays_4", "arrays", 4),
            ("hierarchical_4_2", "hierarchical", 2),
            ("latest_external_4_2", "protected", 2),
            ("protected_owner_4_2", "protected_owner", 2),
        ):
            detector_rows, detector_setups = (
                (rows, setups)
                if detector == "v6_endpoint_2"
                else evaluate(
                    bars,
                    one,
                    structure_mode=detector_mode,
                    pivot_length=detector_pivot,
                )
            )
            shadow_detectors[detector] = {
                "raw_high_pivots": sum(row["signals"]["raw_high_pivot"] for row in detector_rows),
                "raw_low_pivots": sum(row["signals"]["raw_low_pivot"] for row in detector_rows),
                "sweep_candidate_bars": sum(row["signals"]["sweep_candidate"] for row in detector_rows),
                "bull_bos": sum(row["signals"]["bull_break"] for row in detector_rows),
                "bear_bos": sum(row["signals"]["bear_break"] for row in detector_rows),
                "candidates": sum(row["signals"]["candidate_updated"] for row in detector_rows),
                "setups": len(detector_setups),
                "long": sum(setup.direction == 1 for setup in detector_setups),
                "short": sum(setup.direction == -1 for setup in detector_setups),
            }
        print(
            json.dumps(
                {
                    "bars": len(bars),
                    "candidates": len(candidate_rows),
                    "setups": len(setups),
                    "long": sum(setup.direction == 1 for setup in setups),
                    "short": sum(setup.direction == -1 for setup in setups),
                    "checklist_funnel": checklist_funnel,
                    "event_accounting": event_accounting(audit_events, rows),
                    "counts": counts(rows, setups),
                    "fixtures": fixtures,
                    "shadow_detectors": shadow_detectors,
                    "setup_checklist_distribution": setup_checklist_distribution,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    source = SOURCE_PATH.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="sm4-clean-") as temporary:
        service = Pine2PythonService(
            P2PSettings(
                artifact_root=app_settings.pine_development_dir / "pine2python-artifacts" if args.register else Path(temporary) / "artifacts",
                work_root=app_settings.pine_development_dir / "pine2python-work" if args.register else Path(temporary) / "work",
                worker_timeout_seconds=180,
                max_worker_output_bytes=300_000_000,
            )
        )
        analysis = service.analyze(AnalyzeRequest(source=source, name=SOURCE_PATH.name))
        checks = {
            "event_accounting_complete": event_accounting(audit_events, rows)["complete"],
            "parse_complete": "PARSE_COMPLETE" in analysis["status"],
            "indicator_only": analysis["inventory"]["declaration"] == "indicator" and not analysis["inventory"]["strategy_calls"],
            "nine_essential_inputs": len(analysis["inventory"]["inputs"]) == 9,
            "plot_budget_safe": analysis["inventory"]["plot_budget"]["minimum_count"] <= 64,
            "one_minute_request_declared": "request.security_lower_tf" in analysis["inventory"]["request_calls"],
            "all_ready_scores_valid": all(setup.score in {75, 100} for setup in setups),
            "both_directions": any(s.direction == 1 for s in setups) and any(s.direction == -1 for s in setups),
            "profile_volume_present": any((row["features"]["poc"] or 0) > 0 for row in rows),
            "narratives_persist_independent_of_score": any(
                row["signals"]["candidate_updated"]
                and row["features"]["narrative_ready"]
                and not row["signals"]["setup_ready"]
                for row in rows
            ),
            "bos_candle_or_pre_bos_fvg_exercised": any(
                row["signals"]["candidate_updated"] and row["features"]["break_fvg"]
                for row in rows
            ),
            "lifecycle_exercised": any(s.fill is not None for s in setups) and any(s.state in {2, 3, 5} for s in setups),
            "closed_bar_rows": len(rows) == len(bars),
            "deterministic_contract_fixtures": all(fixtures.values()),
            "reviewer_mode_present": all(token in source for token in ("Reviewer", "Review source", "Review offset")),
            "history_count_removed": "Completed trades" not in source and "historyCountInput" not in source,
            "persistent_full_history_present": all(
                token in source
                for token in (
                    "f_draw_history_setup",
                    "const int MAX_ARCHIVED_FULL_SETUPS = 45",
                    "xloc=xloc.bar_time",
                    "materialized from the ledger once",
                )
            ),
            "history_viewport_independent": "chart.left_visible_bar_time" not in source
            and "chart.right_visible_bar_time" not in source,
            "history_initial_redraw_safe": "na(renderedHistoryKey)" in source,
            "history_labels_collision_aware": all(
                token in source
                for token in (
                    "bosLabelTime",
                    "sweepLabelTime",
                    "cardPrice",
                    "AMB · ORDER",
                )
            ),
            "detached_history_markers_removed": all(
                token not in source
                for token in (
                    '"Historical LONG fill"',
                    '"Historical SHORT fill"',
                    '"Historical TP"',
                    '"Historical SL"',
                )
            ),
            "setup_sweep_distribution_exercised": 0 < setup_sweep_pass < len(setups),
            "ambiguous_events_audited": len(ambiguous_examples) == sum(setup.state == 5 for setup in setups),
            "ambiguous_semantics_strict": all(
                item["reason"]
                in {
                    "OPEN_STOP_TARGET_SAME_BAR",
                    "ENTRY_STOP_TARGET_SAME_BAR",
                    "ENTRY_TARGET_SAME_BAR",
                    "ENTRY_STOP_GAP_SAME_BAR",
                }
                for item in ambiguous_examples
            ),
            "dynamic_profile_present": all(token in source for token in ("PROFILE_MIN_ROWS", "PROFILE_MAX_ROWS", "candidatePocDistanceRows")),
            "v6_structural_memory_and_bos_endpoint_present": all(
                token in source
                for token in (
                    "PIVOT_LEN = 2",
                    "HTF_PIVOT_LEN = 2",
                    "MAX_STRUCTURE_LEVELS = 96",
                    "bar_index - PIVOT_LEN >= legBosBar",
                    "MAX_SWEEP_CANDIDATES = 64",
                    "sweepCandidateSignal",
                )
            ),
            "legacy_structural_suppression_removed": all(
                token not in source
                for token in (
                    "SWEEP_LOOKBACK_BARS",
                    "lastPivotType",
                    "highConsumed",
                    "lowConsumed",
                )
            ),
        }
        registration = None
        diagnostic_proofs: dict[str, Any] = {}
        if args.register and all(checks.values()):
            client = DirectClient(service)
            workbench = PineWorkbenchService(repo, data, client)  # type: ignore[arg-type]
            revision = workbench.create_revision(
                source_code=source,
                source_name=SOURCE_PATH.name,
                mode="indicator_first",
                settings_payload={
                    "tradingview_symbol": "BINANCE:BTCUSDT",
                    "tradingview_timeframe": "15",
                    "dataset_15m": FIFTEEN_DATASET_ID,
                    "dataset_1m": ONE_DATASET_ID,
                    "fib_entry": 0.71,
                    "view": "trader",
                    "checklist": "video_four_check",
                    "quality": "standard_75",
                    "poc_extended_tolerance_rows": 2,
                    "profile_rows": "dynamic_32_72_atr_0.20",
                    "risk_budget": 2000,
                    "risk_currency": "USD",
                    "position_unit": "base_asset_default_lots_with_explicit_multiplier",
                    "history_rendering": "latest_45_eligible_setups_including_pending_missed_open_persistent_timestamp_owned_object_budgeted",
                    "same_bar_policy": "ordered_entry_plus_stop_is_sl_target_or_gap_order_is_ambiguous",
                    "structural_detector": "v6_independent_2_2_levels_confirmed_endpoint_on_or_after_bos",
                    "structure_owner_state": "retained_independent_levels_v6",
                    "sweep_candidate_budget": MAX_SWEEP_CANDIDATES,
                    "sweep_linkage": "fresh_priority_then_latest_valid_linked_context_score_independent",
                    "execution": "confirmed_close_actionable_next_bar",
                    "state_start_ms": int(bars[0].ts.timestamp() * 1000),
                    "intrabar_dataset_sha256": data.dataset_content_hash(ONE_DATASET_ID)["sha256"],
                },
                provenance={
                    "origin": "smart_money_4_v6_3_coverage_non_consuming_sweep_linkage",
                    "authority": "timestamped transcript plus mandatory frames",
                    "contract": str(CONTRACT_PATH),
                    "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
                    "trace_contract": stream_expressions(),
                    "supersedes_without_inheriting": [
                        "smart-money-3",
                        "smart-money-4-video-checklist-v1",
                        "pvr_04ff2cab409e735251f6",
                    ],
                },
                workbench_id="pwb_f89ea6f3774a",
                parent_revision_id="pvr_122d076db526ae8f9628",
            )
            proof_start = max(0, len(bars) - 1_000)
            proof = workbench.create_proof(
                revision["revision_id"],
                dataset_id=FIFTEEN_DATASET_ID,
                start_ms=int(bars[proof_start].ts.timestamp() * 1000),
                end_ms=int(bars[-1].ts.timestamp() * 1000) + 900_000,
                mintick=0.01,
                trace_rows=rows[proof_start:],
                stream_expressions=stream_expressions(),
                profile="basic_v1",
            )
            if args.diagnose_feature_groups:
                feature_contract = stream_expressions()["features"]
                feature_groups = {
                    "core_levels": slice(0, 5),
                    "structural_levels": slice(5, 7),
                    "profile_levels": slice(7, 11),
                    "htf_levels": slice(11, 15),
                    "poc_value": slice(7, 8),
                    "structure_checks": slice(15, 19),
                    "fvg_and_narrative": slice(19, 23),
                    "event_timestamps": slice(23, 26),
                }
                contiguous = [i for name, group in feature_groups.items() if name != "poc_value"
                              for i in range(group.start or 0, group.stop)]
                if sorted(contiguous) != list(range(len(feature_contract))):
                    raise AssertionError("diagnostic feature groups do not cover the 26-field contract")
                for group_name, group_slice in feature_groups.items():
                    group_proof = workbench.create_proof(
                        revision["revision_id"],
                        dataset_id=FIFTEEN_DATASET_ID,
                        start_ms=int(bars[proof_start].ts.timestamp() * 1000),
                        end_ms=int(bars[-1].ts.timestamp() * 1000) + 900_000,
                        mintick=0.01,
                        trace_rows=rows[proof_start:],
                        stream_expressions={"features": feature_contract[group_slice]},
                        profile="basic_v1",
                    )
                    diagnostic_proofs[group_name] = {
                        "evidence_id": group_proof["evidence_id"],
                        "path": group_proof["artifact"]["strategy_path"],
                        "dashboard": group_proof["payload"]["dashboard_values"],
                        "instrumented_source_sha256": group_proof["payload"]["identity"]["instrumented_source_sha256"],
                    }
                volume_rows = [
                    {
                        "time": row["time"],
                        "features": {"lower_tf_volume": bar.volume},
                    }
                    for row, bar in zip(rows[proof_start:], bars[proof_start:], strict=True)
                ]
                volume_proof = workbench.create_proof(
                    revision["revision_id"],
                    dataset_id=FIFTEEN_DATASET_ID,
                    start_ms=int(bars[proof_start].ts.timestamp() * 1000),
                    end_ms=int(bars[-1].ts.timestamp() * 1000) + 900_000,
                    mintick=0.01,
                    trace_rows=volume_rows,
                    stream_expressions={
                        "features": [
                            {
                                "name": "features.lower_tf_volume",
                                "expression": "array.sum(oneVolume)",
                                "kind": "float",
                            }
                        ]
                    },
                    profile="basic_v1",
                )
                diagnostic_proofs["lower_tf_volume_feed"] = {
                    "evidence_id": volume_proof["evidence_id"],
                    "path": volume_proof["artifact"]["strategy_path"],
                    "dashboard": volume_proof["payload"]["dashboard_values"],
                    "instrumented_source_sha256": volume_proof["payload"]["identity"]["instrumented_source_sha256"],
                }
            registration = {
                "workbench_id": revision["workbench_id"],
                "revision_id": revision["revision_id"],
                "source_sha256": revision["source_sha256"],
                "status": revision["status"],
                "proof_evidence_id": proof["evidence_id"],
                "proof_status": proof["status"],
                "instrumented_source_sha256": proof["payload"]["identity"]["instrumented_source_sha256"],
                "proof_path": proof["artifact"]["strategy_path"],
                "diagnostic_proofs": diagnostic_proofs,
            }

    summary = {
        "passed": all(checks.values()),
        "checks": checks,
        "source_sha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
        "datasets": {"15m": FIFTEEN_DATASET_ID, "1m": ONE_DATASET_ID},
        "bars": len(bars),
        "one_minute_bars": len(one),
        "counts": counts(rows, setups),
        "fixtures": fixtures,
        "variants": variants,
        "poc_tolerance_variants": poc_tolerance_variants,
        "checklist_funnel": checklist_funnel,
        "event_accounting": event_accounting(audit_events, rows),
        "setup_checklist_distribution": setup_checklist_distribution,
        "setup_sweep_pass": setup_sweep_pass,
        "setup_sweep_fail": len(setups) - setup_sweep_pass,
        "ambiguous_reason_counts": ambiguous_reason_counts,
        "ambiguous_examples": ambiguous_examples,
        "sweep_setup_examples": sweep_setup_examples,
        "no_sweep_setup_examples": no_sweep_setup_examples,
        "setups": len(setups),
        "registration": registration,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
