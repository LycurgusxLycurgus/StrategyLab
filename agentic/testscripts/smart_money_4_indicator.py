from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PINE2PYTHON_SRC = ROOT / "services" / "pine2python" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PINE2PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PINE2PYTHON_SRC))

from pine2python.config import Settings as Pine2PythonSettings
from pine2python.models import (
    AnalyzeRequest,
    ProofRequest,
    TradingViewObservationRequest,
)
from pine2python.service import Pine2PythonService

from app.config import settings as app_settings
from app.data import Bar, DataService
from app.pine_review import build_review_package
from app.pine_workbench import PineWorkbenchService
from app.storage import Repository

BASELINE_PATH = ROOT / "pre-strategies" / "smart-money-indicator-first.pine"
CANDIDATE_PATH = (
    ROOT / "pre-strategies" / "smart-money-4" / "smart-money-4-indicator-first.pine"
)
SOURCE_DOCUMENT_PATH = (
    ROOT
    / "pre-strategies"
    / "smart-money-4"
    / "The ONLY 15 Minute Trading Strategy You Need in 2026"
    / "Transcript con timestamps.txt"
)
CONTRACT_PATH = ROOT / "agentic" / "design" / "smart-money-4-video-contract.md"
FIDELITY_PATH = ROOT / "agentic" / "design" / "smart-money-4-fidelity.json"
DATASET_ID = "ds_f6f2d4ba05c4"
BASELINE_REVISION_ID = "pvr_28090860d3444b575353"
REPAIR_PARENT_REVISION_ID = BASELINE_REVISION_ID
TEMPORAL_LEDGER_PARENT_REVISION_ID = BASELINE_REVISION_ID

# These fields are useful for the event-funnel report, but their absolute values
# depend on how much chart history TradingView loaded before the proof window.
# Strategy-consumed state is proven separately below, so history-origin counters
# and display-only checklist codes must never contaminate strict parity.
HISTORY_ORIGIN_DIAGNOSTIC_FIELDS = {
    "features.checklist_event_id",
    "features.checklist_class_code",
    "features.checklist_status_code",
    "features.checklist_event_count",
    "features.checklist_continuation_count",
    "features.checklist_reversal_count",
    "features.checklist_fresh_sweep_count",
    "features.checklist_linked_fvg_count",
    "features.checklist_range_locked_count",
    "features.checklist_raw_fvg_count",
    "features.checklist_accepted_fvg_count",
    "features.checklist_atr_rejected_fvg_count",
    "features.setup_ready_time",
    "features.setup_outcome_time",
}


class DirectClient:
    def __init__(self, service: Pine2PythonService) -> None:
        self.service = service

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.analyze(AnalyzeRequest.model_validate(payload))

    def proof(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.proof(ProofRequest.model_validate(payload))

    def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.observe(
            TradingViewObservationRequest.model_validate(payload)
        )


def _time_ms(bar: Bar) -> int:
    return int(bar.ts.timestamp() * 1_000)


def _raw_pivots(
    bars: list[Bar], length: int
) -> tuple[list[float | None], list[float | None]]:
    highs: list[float | None] = [None] * len(bars)
    lows: list[float | None] = [None] * len(bars)
    for center in range(length, len(bars) - length):
        confirm = center + length
        high = bars[center].high
        low = bars[center].low
        older = bars[center - length : center]
        newer = bars[center + 1 : center + length + 1]
        if all(high >= bar.high for bar in older) and all(
            high > bar.high for bar in newer
        ):
            highs[confirm] = high
        if all(low <= bar.low for bar in older) and all(low < bar.low for bar in newer):
            lows[confirm] = low
    return highs, lows


def evaluate_internal_structure(
    bars: list[Bar],
    *,
    length: int = 2,
    normalized: bool,
) -> list[dict[str, Any]]:
    raw_highs, raw_lows = _raw_pivots(bars, length)
    active_high: float | None = None
    active_low: float | None = None
    active_high_source: int | None = None
    active_low_source: int | None = None
    high_consumed = False
    low_consumed = False
    last_pivot_direction = 0
    bias = 0
    rows: list[dict[str, Any]] = []

    for index, bar in enumerate(bars):
        raw_high = raw_highs[index]
        raw_low = raw_lows[index]
        raw_high_event = raw_high is not None
        raw_low_event = raw_low is not None
        accepted_high = False
        accepted_low = False
        replaced = False
        rejected = False
        decision = 0

        candidates: list[tuple[int, float]] = []
        if normalized:
            if raw_high is not None and raw_low is not None:
                if last_pivot_direction == 1:
                    candidates = [(-1, raw_low)]
                elif last_pivot_direction == -1:
                    candidates = [(1, raw_high)]
                else:
                    pivot_close = bars[index - length].close
                    direction = (
                        1
                        if abs(raw_high - pivot_close) >= abs(pivot_close - raw_low)
                        else -1
                    )
                    candidates = [(direction, raw_high if direction == 1 else raw_low)]
            elif raw_high is not None:
                candidates = [(1, raw_high)]
            elif raw_low is not None:
                candidates = [(-1, raw_low)]
        else:
            if raw_high is not None:
                candidates.append((1, raw_high))
            if raw_low is not None:
                candidates.append((-1, raw_low))

        for direction, price in candidates:
            source_index = index - length
            same_side = direction == last_pivot_direction
            more_extreme = (
                active_high is None or price > active_high
                if direction == 1
                else active_low is None or price < active_low
            )
            accept = not normalized or not same_side or more_extreme
            if not accept:
                rejected = True
                decision = 3 if direction == 1 else -3
                continue
            if normalized and same_side:
                replaced = True
                decision = 2 if direction == 1 else -2
            else:
                decision = direction
            last_pivot_direction = direction
            if direction == 1:
                active_high = price
                active_high_source = _time_ms(bars[source_index])
                high_consumed = False
                accepted_high = True
            else:
                active_low = price
                active_low_source = _time_ms(bars[source_index])
                low_consumed = False
                accepted_low = True

        buy_sweep = (
            active_high is not None
            and not high_consumed
            and bar.high > active_high
            and bar.close <= active_high
        )
        sell_sweep = (
            active_low is not None
            and not low_consumed
            and bar.low < active_low
            and bar.close >= active_low
        )
        dual_sweep = buy_sweep and sell_sweep
        if normalized and dual_sweep:
            buy_sweep = False
            sell_sweep = False
        bull_break = (
            active_high is not None and not high_consumed and bar.close > active_high
        )
        bear_break = (
            active_low is not None and not low_consumed and bar.close < active_low
        )
        if bull_break:
            high_consumed = True
            bias = 1
        if bear_break:
            low_consumed = True
            bias = -1

        rows.append(
            {
                "time": _time_ms(bar),
                "features": {
                    "ltf_structure_high": active_high,
                    "ltf_structure_low": active_low,
                    "ltf_high_source_time": active_high_source,
                    "ltf_low_source_time": active_low_source,
                    "ltf_bias": bias,
                    "ltf_pivot_decision": decision,
                    "ltf_raw_high_price": raw_high,
                    "ltf_raw_low_price": raw_low,
                },
                "states": {
                    "ltf_high_consumed": int(high_consumed),
                    "ltf_low_consumed": int(low_consumed),
                },
                "signals": {
                    "ltf_raw_high_pivot": int(raw_high_event),
                    "ltf_raw_low_pivot": int(raw_low_event),
                    "ltf_high_pivot_accepted": int(accepted_high),
                    "ltf_low_pivot_accepted": int(accepted_low),
                    "ltf_pivot_replaced": int(replaced),
                    "ltf_bull_break": int(bull_break),
                    "ltf_bear_break": int(bear_break),
                    "ltf_buy_side_sweep": int(buy_sweep),
                    "ltf_sell_side_sweep": int(sell_sweep),
                },
                "rejections": {
                    "ltf_weaker_same_side_pivot": int(rejected),
                    "ltf_dual_side_sweep": int(dual_sweep),
                },
            }
        )
    return rows


def _atr_rma(bars: list[Bar], length: int = 14) -> list[float | None]:
    true_ranges: list[float] = []
    result: list[float | None] = [None] * len(bars)
    previous: float | None = None
    for index, bar in enumerate(bars):
        true_range = (
            bar.high - bar.low
            if index == 0
            else max(
                bar.high - bar.low,
                abs(bar.high - bars[index - 1].close),
                abs(bar.low - bars[index - 1].close),
            )
        )
        true_ranges.append(true_range)
        if index == length - 1:
            previous = sum(true_ranges[:length]) / length
            result[index] = previous
        elif index >= length and previous is not None:
            previous = previous + (true_range - previous) / length
            result[index] = previous
    return result


def _advance_setup_state(
    state: str,
    *,
    direction: int,
    entry: float,
    stop: float,
    target: float,
    bar: Bar,
) -> tuple[str, str | None, bool]:
    entry_hit = bar.low <= entry if direction == 1 else bar.high >= entry
    target_hit = bar.high >= target if direction == 1 else bar.low <= target
    stop_hit = bar.low <= stop if direction == 1 else bar.high >= stop
    stop_gap = bar.open <= stop if direction == 1 else bar.open >= stop
    if state == "ACTIVE":
        if stop_gap:
            return "INVALIDATED_BEFORE_FILL", "invalid", True
        if entry_hit and (target_hit or stop_hit):
            return "AMBIGUOUS", "ambiguous", True
        if target_hit and not entry_hit:
            return "MISSED_TP_BEFORE_FILL", "missed", True
        if stop_hit and not entry_hit:
            return "INVALIDATED_BEFORE_FILL", "invalid", True
        if entry_hit:
            return "FILLED", "filled", False
    elif state == "FILLED":
        if target_hit and stop_hit:
            return "AMBIGUOUS", "ambiguous", True
        if target_hit:
            return "TARGET", "target", True
        if stop_hit:
            return "STOP", "stop", True
    return state, None, False


def _setup_lifecycle_fixtures(template: Bar) -> dict[str, bool]:
    def candle(open_: float, high: float, low: float, close: float) -> Bar:
        return Bar(
            ts=template.ts,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=template.volume,
            symbol=template.symbol,
            timeframe=template.timeframe,
        )

    long_fill = _advance_setup_state(
        "ACTIVE",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(104.0, 106.0, 99.0, 102.0),
    )
    long_target = _advance_setup_state(
        "FILLED",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(103.0, 111.0, 101.0, 110.0),
    )
    long_stop = _advance_setup_state(
        "FILLED",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(101.0, 103.0, 94.0, 96.0),
    )
    long_missed = _advance_setup_state(
        "ACTIVE",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(105.0, 111.0, 102.0, 109.0),
    )
    long_gap_invalid = _advance_setup_state(
        "ACTIVE",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(94.0, 96.0, 92.0, 93.0),
    )
    long_ambiguous = _advance_setup_state(
        "ACTIVE",
        direction=1,
        entry=100.0,
        stop=95.0,
        target=110.0,
        bar=candle(104.0, 111.0, 99.0, 105.0),
    )
    short_fill = _advance_setup_state(
        "ACTIVE",
        direction=-1,
        entry=100.0,
        stop=105.0,
        target=90.0,
        bar=candle(96.0, 101.0, 94.0, 98.0),
    )
    return {
        "long_fill": long_fill == ("FILLED", "filled", False),
        "long_target": long_target == ("TARGET", "target", True),
        "long_stop": long_stop == ("STOP", "stop", True),
        "long_missed": long_missed == ("MISSED_TP_BEFORE_FILL", "missed", True),
        "long_gap_invalid": long_gap_invalid
        == ("INVALIDATED_BEFORE_FILL", "invalid", True),
        "long_ambiguous": long_ambiguous == ("AMBIGUOUS", "ambiguous", True),
        "short_fill": short_fill == ("FILLED", "filled", False),
    }


def _aggregate_4h(bars: list[Bar]) -> tuple[list[Bar], list[int]]:
    aggregated: list[Bar] = []
    keys: list[int] = []
    for bar in bars:
        key = int(bar.ts.timestamp()) // (4 * 60 * 60)
        if not keys or key != keys[-1]:
            keys.append(key)
            aggregated.append(
                Bar(
                    ts=bar.ts,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    symbol=bar.symbol,
                    timeframe="4h",
                )
            )
        else:
            current = aggregated[-1]
            current.high = max(current.high, bar.high)
            current.low = min(current.low, bar.low)
            current.close = bar.close
            current.volume += bar.volume
    return aggregated, keys


def _evaluate_confirmed_htf(bars: list[Bar]) -> dict[int, dict[str, Any]]:
    htf_bars, keys = _aggregate_4h(bars)
    raw_highs, raw_lows = _raw_pivots(htf_bars, 5)
    active_high: float | None = None
    active_low: float | None = None
    high_consumed = False
    low_consumed = False
    bias = 0
    range_direction = 0
    range_locked = False
    range_event_time: int | None = None
    range_high: float | None = None
    range_low: float | None = None
    buy_sweep_active = False
    sell_sweep_active = False
    states: dict[int, dict[str, Any]] = {}

    for index, bar in enumerate(htf_bars):
        pivot_high = raw_highs[index]
        pivot_low = raw_lows[index]
        pivot_high_time = (
            _time_ms(htf_bars[index - 5])
            if pivot_high is not None and index >= 5
            else None
        )
        pivot_low_time = (
            _time_ms(htf_bars[index - 5])
            if pivot_low is not None and index >= 5
            else None
        )
        buy_invalidated = False
        sell_invalidated = False
        buy_consumed = False
        sell_consumed = False

        if pivot_high is not None:
            if buy_sweep_active:
                buy_sweep_active = False
                buy_invalidated = True
            active_high = pivot_high
            high_consumed = False
        if pivot_low is not None:
            if sell_sweep_active:
                sell_sweep_active = False
                sell_invalidated = True
            active_low = pivot_low
            low_consumed = False

        buy_sweep = bool(
            active_high is not None
            and not high_consumed
            and not buy_sweep_active
            and bar.high > active_high
            and bar.close <= active_high
        )
        sell_sweep = bool(
            active_low is not None
            and not low_consumed
            and not sell_sweep_active
            and bar.low < active_low
            and bar.close >= active_low
        )
        if buy_sweep:
            buy_sweep_active = True
        if sell_sweep:
            sell_sweep_active = True

        bull_break = bool(
            active_high is not None and not high_consumed and bar.close > active_high
        )
        bear_break = bool(
            active_low is not None and not low_consumed and bar.close < active_low
        )
        if bull_break:
            if buy_sweep_active:
                buy_sweep_active = False
                buy_invalidated = True
            if sell_sweep_active:
                sell_sweep_active = False
                sell_consumed = True
            high_consumed = True
            bias = 1
            range_direction = 1
            range_locked = False
            range_event_time = _time_ms(bar)
            range_low = active_low
            range_high = bar.high
        if bear_break:
            if sell_sweep_active:
                sell_sweep_active = False
                sell_invalidated = True
            if buy_sweep_active:
                buy_sweep_active = False
                buy_consumed = True
            low_consumed = True
            bias = -1
            range_direction = -1
            range_locked = False
            range_event_time = _time_ms(bar)
            range_high = active_high
            range_low = bar.low

        if range_direction == 1 and not range_locked and range_event_time:
            range_high = bar.high if range_high is None else max(range_high, bar.high)
            if (
                pivot_high is not None
                and pivot_high_time is not None
                and pivot_high_time >= range_event_time
            ):
                range_high = pivot_high
                range_locked = True
        if range_direction == -1 and not range_locked and range_event_time:
            range_low = bar.low if range_low is None else min(range_low, bar.low)
            if (
                pivot_low is not None
                and pivot_low_time is not None
                and pivot_low_time >= range_event_time
            ):
                range_low = pivot_low
                range_locked = True

        midpoint = (
            (range_high + range_low) / 2.0
            if range_locked and range_high is not None and range_low is not None
            else None
        )
        states[keys[index]] = {
            "features": {
                "htf_structure_high": active_high,
                "htf_structure_low": active_low,
                "htf_bias": bias,
                "htf_range_high": range_high,
                "htf_range_low": range_low,
                "htf_range_midpoint": midpoint,
            },
            "states": {
                "htf_range_locked": int(range_locked),
                "htf_buy_sweep_active": int(buy_sweep_active),
                "htf_sell_sweep_active": int(sell_sweep_active),
            },
            "signals": {
                "htf_bull_break": int(bull_break),
                "htf_bear_break": int(bear_break),
                "htf_buy_side_sweep": int(buy_sweep),
                "htf_sell_side_sweep": int(sell_sweep),
                "htf_buy_sweep_consumed": int(buy_consumed),
                "htf_sell_sweep_consumed": int(sell_consumed),
            },
            "rejections": {
                "htf_buy_sweep_invalidated": int(buy_invalidated),
                "htf_sell_sweep_invalidated": int(sell_invalidated),
            },
        }
    return states


def evaluate_acceptance_contract(
    bars: list[Bar],
) -> list[dict[str, Any]]:
    rows = evaluate_internal_structure(bars, normalized=True)
    htf_states = _evaluate_confirmed_htf(bars)
    htf_keys = sorted(htf_states)
    key_position = {key: index for index, key in enumerate(htf_keys)}
    atr = _atr_rma(bars)

    buy_sweep_active = False
    sell_sweep_active = False
    next_sweep_id = 0
    buy_sweep_id: int | None = None
    sell_sweep_id: int | None = None
    buy_sweep_source_time: int | None = None
    sell_sweep_source_time: int | None = None
    event_direction = 0
    event_index: int | None = None
    event_has_sweep = False
    event_sweep_id: int | None = None
    event_sweep_source_time: int | None = None
    event_sweep_confirmation_time: int | None = None
    range_direction = 0
    range_locked = False
    range_event_time: int | None = None
    range_high: float | None = None
    range_low: float | None = None
    range_high_time: int | None = None
    range_low_time: int | None = None
    tracked_locked_range_event: int | None = None
    entry_touched_before_ready = False
    linked_fvg_id: int | None = None
    linked_fvg: dict[str, Any] | None = None
    next_fvg_id = 0
    active_fvgs: list[dict[str, Any]] = []
    latest_directional_fvg: dict[int, dict[str, Any]] = {}
    checklist_event_count = 0
    checklist_continuation_count = 0
    checklist_reversal_count = 0
    checklist_fresh_sweep_count = 0
    checklist_linked_fvg_count = 0
    checklist_range_locked_count = 0
    checklist_raw_fvg_count = 0
    checklist_accepted_fvg_count = 0
    checklist_atr_rejected_fvg_count = 0
    checklist_current_event_id: int | None = None
    checklist_current_class_code = 0
    checklist_current_fvg_counted = False
    checklist_current_range_counted = False
    previous_htf_key: int | None = None
    last_setup_key = ""
    next_setup_id = 0
    active_setups: list[dict[str, Any]] = []
    latest_setup: dict[str, Any] | None = None

    for index, (bar, row) in enumerate(zip(bars, rows, strict=True)):
        features = row.setdefault("features", {})
        states = row.setdefault("states", {})
        signals = row.setdefault("signals", {})
        rejections = row.setdefault("rejections", {})
        features.update(
            {
                "htf_structure_high": None,
                "htf_structure_low": None,
                "htf_bias": 0,
                "htf_range_high": None,
                "htf_range_low": None,
                "htf_range_midpoint": None,
                "ltf_range_high": range_high,
                "ltf_range_low": range_low,
                "ltf_fib_entry": None,
                "ltf_event_sweep_id": event_sweep_id,
                "ltf_event_sweep_source_time": event_sweep_source_time,
                "ltf_event_sweep_confirmation_time": (event_sweep_confirmation_time),
                "setup_id": None,
                "setup_direction": 0,
                "setup_entry": None,
                "setup_stop": None,
                "setup_target": None,
                "setup_ready_time": None,
                "setup_outcome_time": None,
                "setup_trade_score": None,
                "video_htf_alignment": 0,
                "video_bos": 0,
                "video_sweep": 0,
                "video_imbalance": 0,
                "video_trade_score": 0,
                "checklist_event_id": checklist_current_event_id,
                "checklist_class_code": checklist_current_class_code,
                "checklist_status_code": 0,
            }
        )
        states.update(
            {
                "htf_range_locked": 0,
                "htf_buy_sweep_active": 0,
                "htf_sell_sweep_active": 0,
                "ltf_range_locked": int(range_locked),
                "setup_pending": 0,
                "setup_active": 0,
                "setup_filled": 0,
                "setup_terminal": 0,
            }
        )
        signals.update(
            {
                "htf_bull_break": 0,
                "htf_bear_break": 0,
                "htf_buy_side_sweep": 0,
                "htf_sell_side_sweep": 0,
                "htf_buy_sweep_consumed": 0,
                "htf_sell_sweep_consumed": 0,
                "ltf_manipulation_confirmed": 0,
                "long_setup_ready": 0,
                "short_setup_ready": 0,
                "setup_filled": 0,
                "setup_target": 0,
                "setup_stop": 0,
                "setup_missed": 0,
                "setup_invalid": 0,
                "ltf_raw_fvg": 0,
                "ltf_fvg_accepted": 0,
            }
        )
        rejections.update(
            {
                "htf_buy_sweep_invalidated": 0,
                "htf_sell_sweep_invalidated": 0,
                "setup_entry_touched_before_ready": 0,
                "setup_rejected_active": 0,
                "setup_ambiguous": 0,
                "ltf_fvg_atr_rejected": 0,
            }
        )

        buy_consumed = False
        sell_consumed = False
        buy_invalidated = False
        sell_invalidated = False
        new_fvg_direction = 0
        prior_ltf_bias = (
            int(rows[index - 1].get("features", {}).get("ltf_bias") or 0)
            if index > 0
            else 0
        )

        if signals.get("ltf_high_pivot_accepted") and buy_sweep_active:
            buy_sweep_active = False
            buy_invalidated = True
            buy_sweep_id = None
            buy_sweep_source_time = None
        if signals.get("ltf_low_pivot_accepted") and sell_sweep_active:
            sell_sweep_active = False
            sell_invalidated = True
            sell_sweep_id = None
            sell_sweep_source_time = None

        if rejections.get("ltf_dual_side_sweep"):
            next_sweep_id += 2

        if signals.get("ltf_buy_side_sweep") and not buy_sweep_active:
            buy_sweep_active = True
            next_sweep_id += 1
            buy_sweep_id = next_sweep_id
            buy_sweep_source_time = _time_ms(bar)
        elif signals.get("ltf_buy_side_sweep") and buy_sweep_active:
            signals["ltf_buy_side_sweep"] = 0
        if signals.get("ltf_sell_side_sweep") and not sell_sweep_active:
            sell_sweep_active = True
            next_sweep_id += 1
            sell_sweep_id = next_sweep_id
            sell_sweep_source_time = _time_ms(bar)
        elif signals.get("ltf_sell_side_sweep") and sell_sweep_active:
            signals["ltf_sell_side_sweep"] = 0

        if signals.get("ltf_bull_break"):
            if buy_sweep_active:
                buy_sweep_active = False
                buy_invalidated = True
                buy_sweep_id = None
                buy_sweep_source_time = None
            if sell_sweep_active:
                sell_sweep_active = False
                sell_consumed = True
                event_sweep_id = sell_sweep_id
                event_sweep_source_time = sell_sweep_source_time
                event_sweep_confirmation_time = _time_ms(bar)
                sell_sweep_id = None
                sell_sweep_source_time = None
            event_direction = 1
            event_index = index
            event_has_sweep = sell_consumed
            if not sell_consumed:
                event_sweep_id = None
                event_sweep_source_time = None
                event_sweep_confirmation_time = None
            linked_fvg_id = None
            linked_fvg = None
            range_direction = 1
            range_locked = False
            range_event_time = _time_ms(bar)
            range_low = features.get("ltf_structure_low")
            range_low_time = features.get("ltf_low_source_time")
            range_high = bar.high
            range_high_time = _time_ms(bar)
            tracked_locked_range_event = None
            entry_touched_before_ready = False
            checklist_event_count += 1
            checklist_current_event_id = checklist_event_count
            checklist_current_class_code = 2 if prior_ltf_bias == -1 else 1
            checklist_continuation_count += int(checklist_current_class_code == 1)
            checklist_reversal_count += int(checklist_current_class_code == 2)
            checklist_fresh_sweep_count += int(sell_consumed)
            checklist_current_fvg_counted = False
            checklist_current_range_counted = False
        if signals.get("ltf_bear_break"):
            if sell_sweep_active:
                sell_sweep_active = False
                sell_invalidated = True
                sell_sweep_id = None
                sell_sweep_source_time = None
            if buy_sweep_active:
                buy_sweep_active = False
                buy_consumed = True
                event_sweep_id = buy_sweep_id
                event_sweep_source_time = buy_sweep_source_time
                event_sweep_confirmation_time = _time_ms(bar)
                buy_sweep_id = None
                buy_sweep_source_time = None
            event_direction = -1
            event_index = index
            event_has_sweep = buy_consumed
            if not buy_consumed:
                event_sweep_id = None
                event_sweep_source_time = None
                event_sweep_confirmation_time = None
            linked_fvg_id = None
            linked_fvg = None
            range_direction = -1
            range_locked = False
            range_event_time = _time_ms(bar)
            range_high = features.get("ltf_structure_high")
            range_high_time = features.get("ltf_high_source_time")
            range_low = bar.low
            range_low_time = _time_ms(bar)
            tracked_locked_range_event = None
            entry_touched_before_ready = False
            checklist_event_count += 1
            checklist_current_event_id = checklist_event_count
            checklist_current_class_code = 2 if prior_ltf_bias == 1 else 1
            checklist_continuation_count += int(checklist_current_class_code == 1)
            checklist_reversal_count += int(checklist_current_class_code == 2)
            checklist_fresh_sweep_count += int(buy_consumed)
            checklist_current_fvg_counted = False
            checklist_current_range_counted = False

        source_index = index - 2
        source_time = _time_ms(bars[source_index]) if source_index >= 0 else None
        if range_direction == 1 and range_event_time is not None:
            if not range_locked and (range_high is None or bar.high > range_high):
                range_high = bar.high
                range_high_time = _time_ms(bar)
            raw_high = features.get("ltf_raw_high_price")
            if (
                not range_locked
                and raw_high is not None
                and source_time is not None
                and source_time >= range_event_time
            ):
                range_high = float(raw_high)
                range_high_time = source_time
                range_locked = True
                if not checklist_current_range_counted:
                    checklist_range_locked_count += 1
                    checklist_current_range_counted = True
        if range_direction == -1 and range_event_time is not None:
            if not range_locked and (range_low is None or bar.low < range_low):
                range_low = bar.low
                range_low_time = _time_ms(bar)
            raw_low = features.get("ltf_raw_low_price")
            if (
                not range_locked
                and raw_low is not None
                and source_time is not None
                and source_time >= range_event_time
            ):
                range_low = float(raw_low)
                range_low_time = source_time
                range_locked = True
                if not checklist_current_range_counted:
                    checklist_range_locked_count += 1
                    checklist_current_range_counted = True

        for fvg in active_fvgs:
            if not fvg["active"]:
                continue
            liquidation = (fvg["top"] + fvg["bottom"]) / 2.0
            if (fvg["direction"] == 1 and bar.low <= liquidation) or (
                fvg["direction"] == -1 and bar.high >= liquidation
            ):
                fvg["active"] = False

        if index >= 2:
            body = abs(bars[index - 1].close - bars[index - 1].open)
            # SmartMoney-4 follows the video's raw three-candle imbalance.
            # ATR displacement remains an optional Pine audit input, off by default.
            valid = True
            bull = bar.low > bars[index - 2].high
            bear = bar.high < bars[index - 2].low
            if bull or bear:
                checklist_raw_fvg_count += 1
                signals["ltf_raw_fvg"] = 1
                if valid:
                    checklist_accepted_fvg_count += 1
                    signals["ltf_fvg_accepted"] = 1
                else:
                    checklist_atr_rejected_fvg_count += 1
                    rejections["ltf_fvg_atr_rejected"] = 1
            if valid and (bull or bear):
                direction = 1 if bull else -1
                next_fvg_id += 1
                fvg = {
                    "id": next_fvg_id,
                    "direction": direction,
                    "top": bar.low if bull else bars[index - 2].low,
                    "bottom": bars[index - 2].high if bull else bar.high,
                    "time": _time_ms(bar),
                    "index": index,
                    "active": True,
                }
                active_fvgs.append(fvg)
                latest_directional_fvg[direction] = fvg
                new_fvg_direction = direction

        if event_index is not None and event_direction and linked_fvg_id is None:
            latest = latest_directional_fvg.get(event_direction)
            origin_time = range_low_time if event_direction == 1 else range_high_time
            extreme_time = range_high_time if event_direction == 1 else range_low_time
            if (
                latest
                and origin_time is not None
                and int(latest["time"]) >= int(origin_time)
                and (
                    not range_locked
                    or extreme_time is not None
                    and int(latest["time"]) <= int(extreme_time)
                )
            ):
                linked_fvg_id = int(latest["id"])
                linked_fvg = latest
        if range_locked and linked_fvg is not None:
            extreme_time = range_high_time if event_direction == 1 else range_low_time
            if extreme_time is None or int(linked_fvg["time"]) > int(extreme_time):
                linked_fvg_id = None
                linked_fvg = None
        if linked_fvg_id is not None and not checklist_current_fvg_counted:
            checklist_linked_fvg_count += 1
            checklist_current_fvg_counted = True

        linked_active = any(
            fvg["id"] == linked_fvg_id and fvg["active"] for fvg in active_fvgs
        )
        any_directional_active = any(
            fvg["direction"] == event_direction and fvg["active"] for fvg in active_fvgs
        )

        ltf_entry: float | None = None
        ltf_stop: float | None = None
        ltf_target: float | None = None
        if range_high is not None and range_low is not None:
            width = range_high - range_low
            if range_direction == 1:
                ltf_entry = range_high - width * 0.75
                ltf_stop = range_low
                ltf_target = range_high
            elif range_direction == -1:
                ltf_entry = range_low + width * 0.75
                ltf_stop = range_high
                ltf_target = range_low
        ltf_fvg_entry_overlap = bool(
            linked_fvg is not None
            and ltf_entry is not None
            and float(linked_fvg["bottom"])
            <= float(ltf_entry)
            <= float(linked_fvg["top"])
        )
        if range_locked and ltf_entry is not None:
            if tracked_locked_range_event != range_event_time:
                tracked_locked_range_event = range_event_time
                lookback = bars[max(0, index - 2) : index + 1]
                entry_touched_before_ready = (
                    min(item.low for item in lookback) <= ltf_entry
                    if range_direction == 1
                    else max(item.high for item in lookback) >= ltf_entry
                )
            else:
                entry_touched_before_ready = entry_touched_before_ready or (
                    bar.low <= ltf_entry
                    if range_direction == 1
                    else bar.high >= ltf_entry
                )

        features.update(
            {
                "ltf_range_high": range_high,
                "ltf_range_low": range_low,
                "ltf_fib_entry": ltf_entry,
                "ltf_event_sweep_id": event_sweep_id,
                "ltf_event_sweep_source_time": event_sweep_source_time,
                "ltf_event_sweep_confirmation_time": (event_sweep_confirmation_time),
                "checklist_event_id": checklist_current_event_id,
                "checklist_class_code": checklist_current_class_code,
                "ltf_fvg_entry_overlap": int(ltf_fvg_entry_overlap),
            }
        )

        states.update(
            {
                "ltf_buy_sweep_active": int(buy_sweep_active),
                "ltf_sell_sweep_active": int(sell_sweep_active),
                "ltf_linked_fvg_active": int(linked_active),
                "ltf_range_locked": int(range_locked),
            }
        )
        features["ltf_linked_fvg_id"] = linked_fvg_id
        signals.update(
            {
                "ltf_buy_sweep_consumed": int(buy_consumed),
                "ltf_sell_sweep_consumed": int(sell_consumed),
                "ltf_sweep_consumed": int(buy_consumed or sell_consumed),
                "ltf_manipulation_confirmed": int(buy_consumed or sell_consumed),
            }
        )
        rejections.update(
            {
                "ltf_buy_sweep_invalidated": int(buy_invalidated),
                "ltf_sell_sweep_invalidated": int(sell_invalidated),
                "ltf_sweep_invalidated": int(buy_invalidated or sell_invalidated),
                "unrelated_fvg_for_latest_break": int(
                    event_index is not None
                    and (
                        bool(signals.get("ltf_bull_break"))
                        or bool(signals.get("ltf_bear_break"))
                        or new_fvg_direction == event_direction
                    )
                    and any_directional_active
                    and linked_fvg_id is None
                ),
            }
        )

        key = int(bar.ts.timestamp()) // (4 * 60 * 60)
        position = key_position.get(key)
        confirmed_key = (
            htf_keys[position - 1] if position is not None and position > 0 else None
        )
        confirmed = htf_states.get(confirmed_key or -1)
        source_update = confirmed_key is not None and key != previous_htf_key
        if confirmed:
            for category in ("features", "states", "signals", "rejections"):
                row.setdefault(category, {}).update(confirmed[category])
            midpoint = confirmed["features"]["htf_range_midpoint"]
            gate = (
                1
                if midpoint is not None and bar.close < midpoint
                else -1
                if midpoint is not None and bar.close > midpoint
                else 0
            )
            features["htf_direction_gate"] = gate
            signals["htf_discount_gate"] = int(gate == 1)
            signals["htf_premium_gate"] = int(gate == -1)
        else:
            features["htf_direction_gate"] = 0
            signals["htf_discount_gate"] = 0
            signals["htf_premium_gate"] = 0
        signals["htf_confirmed_source_update"] = int(source_update)
        if not source_update:
            for name in (
                "htf_bull_break",
                "htf_bear_break",
                "htf_buy_side_sweep",
                "htf_sell_side_sweep",
                "htf_buy_sweep_consumed",
                "htf_sell_sweep_consumed",
            ):
                signals[name] = 0
            for name in (
                "htf_buy_sweep_invalidated",
                "htf_sell_sweep_invalidated",
            ):
                rejections[name] = 0

        direction_gate = int(features.get("htf_direction_gate") or 0)
        video_htf_alignment = bool(
            states.get("htf_range_locked") and direction_gate == range_direction
        )
        video_bos = bool(range_locked and event_index is not None)
        video_sweep = bool(event_has_sweep)
        video_imbalance = linked_fvg_id is not None
        video_trade_score = 25 * sum(
            (video_htf_alignment, video_bos, video_sweep, video_imbalance)
        )
        checklist_status_code = (
            0
            if checklist_current_event_id is None
            else 1
            if not states.get("htf_range_locked")
            else 2
            if not range_locked
            else 5
            if ltf_entry is None or ltf_stop is None or ltf_target is None
            else 7
            if video_trade_score < 75
            else 6
            if entry_touched_before_ready
            else 8
        )
        features.update(
            {
                "checklist_status_code": checklist_status_code,
                "checklist_event_count": checklist_event_count,
                "checklist_continuation_count": checklist_continuation_count,
                "checklist_reversal_count": checklist_reversal_count,
                "checklist_fresh_sweep_count": checklist_fresh_sweep_count,
                "checklist_linked_fvg_count": checklist_linked_fvg_count,
                "checklist_range_locked_count": checklist_range_locked_count,
                "checklist_raw_fvg_count": checklist_raw_fvg_count,
                "checklist_accepted_fvg_count": checklist_accepted_fvg_count,
                "checklist_atr_rejected_fvg_count": (
                    checklist_atr_rejected_fvg_count
                ),
                "setup_entry_touched_before_ready": int(
                    entry_touched_before_ready
                ),
                "video_htf_alignment": int(video_htf_alignment),
                "video_bos": int(video_bos),
                "video_sweep": int(video_sweep),
                "video_imbalance": int(video_imbalance),
                "video_trade_score": video_trade_score,
            }
        )
        canonical_ready = bool(
            states.get("htf_range_locked")
            and range_locked
            and video_bos
            and video_trade_score >= 75
            and ltf_entry is not None
            and ltf_stop is not None
            and ltf_target is not None
        )
        setup_key = (
            f"{event_index}:{range_high_time}:{range_low_time}"
            if canonical_ready
            else ""
        )
        if canonical_ready and setup_key != last_setup_key:
            last_setup_key = setup_key
            touched = entry_touched_before_ready or (
                bar.low <= float(ltf_entry)
                if range_direction == 1
                else bar.high >= float(ltf_entry)
            )
            if touched:
                rejections["setup_entry_touched_before_ready"] = 1
            else:
                next_setup_id += 1
                new_setup = {
                    "id": next_setup_id,
                    "direction": range_direction,
                    "state": "PENDING",
                    "ready_time": _time_ms(bar),
                    "ready_index": index,
                    "outcome_time": None,
                    "entry": float(ltf_entry),
                    "stop": float(ltf_stop),
                    "target": float(ltf_target),
                    "sweep_id": event_sweep_id,
                    "sweep_source_time": event_sweep_source_time,
                    "sweep_confirmation_time": (event_sweep_confirmation_time),
                    "break_time": (
                        _time_ms(bars[event_index]) if event_index is not None else None
                    ),
                    "fvg_id": linked_fvg_id,
                    "fvg_entry_overlap": ltf_fvg_entry_overlap,
                    "range_high_time": range_high_time,
                    "range_low_time": range_low_time,
                    "trade_score": video_trade_score,
                    "htf_alignment": video_htf_alignment,
                    "bos": video_bos,
                    "sweep": video_sweep,
                    "imbalance": video_imbalance,
                }
                active_setups.append(new_setup)
                latest_setup = dict(new_setup)
                signals[
                    "long_setup_ready" if range_direction == 1 else "short_setup_ready"
                ] = 1

        for active_setup in list(active_setups):
            if index <= int(active_setup["ready_index"]):
                continue
            if active_setup["state"] == "PENDING":
                active_setup["state"] = "ACTIVE"
            next_state, lifecycle_event, terminal = _advance_setup_state(
                str(active_setup["state"]),
                direction=int(active_setup["direction"]),
                entry=float(active_setup["entry"]),
                stop=float(active_setup["stop"]),
                target=float(active_setup["target"]),
                bar=bar,
            )
            active_setup["state"] = next_state
            if lifecycle_event in {"filled", "target", "stop", "missed", "invalid"}:
                signals[f"setup_{lifecycle_event}"] = 1
            elif lifecycle_event == "ambiguous":
                rejections["setup_ambiguous"] = 1
            if terminal:
                active_setup["outcome_time"] = _time_ms(bar)
            if latest_setup is not None and int(active_setup["id"]) == int(
                latest_setup["id"]
            ):
                latest_setup = dict(active_setup)
            if terminal:
                active_setups.remove(active_setup)

        visible_setup = latest_setup
        if visible_setup:
            features.update(
                {
                    "setup_id": visible_setup["id"],
                    "setup_direction": visible_setup["direction"],
                    "setup_entry": visible_setup["entry"],
                    "setup_stop": visible_setup["stop"],
                    "setup_target": visible_setup["target"],
                    "setup_ready_time": visible_setup["ready_time"],
                    "setup_outcome_time": visible_setup["outcome_time"],
                    "setup_trade_score": visible_setup["trade_score"],
                }
            )
            setup_state = str(visible_setup["state"])
            states["setup_pending"] = int(
                any(setup["state"] == "PENDING" for setup in active_setups)
            )
            states["setup_active"] = int(
                any(setup["state"] == "ACTIVE" for setup in active_setups)
            )
            states["setup_filled"] = int(
                any(setup["state"] == "FILLED" for setup in active_setups)
            )
            states["setup_terminal"] = int(
                setup_state
                in {
                    "TARGET",
                    "STOP",
                    "MISSED_TP_BEFORE_FILL",
                    "INVALIDATED_BEFORE_FILL",
                    "AMBIGUOUS",
                }
            )
        previous_htf_key = key
    return rows


def event_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for category in ("signals", "rejections"):
            for name, value in row.get(category, {}).items():
                if value not in (None, 0, False):
                    counts[f"{category}.{name}"] += 1
    return dict(sorted(counts.items()))


def checklist_event_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the SmartMoney-4 event funnel from the four visible score fields."""
    events: dict[int, dict[str, Any]] = {}
    for row in rows:
        features = row.get("features", {})
        event_id = features.get("checklist_event_id")
        if event_id is None:
            continue
        event = events.setdefault(
            int(event_id),
            {
                "event_id": int(event_id),
                "time": row["time"],
                "class_code": int(features.get("checklist_class_code") or 0),
                "direction": int(features.get("ltf_bias") or 0),
                "htf_context": False,
                "htf_alignment": False,
                "bos": False,
                "sweep": False,
                "imbalance": False,
                "max_score": 0,
                "range_locked": False,
                "contract_reached": False,
                "entry_touched_at_contract": False,
                "contract_time": None,
                "implementation_ready": False,
                "active_suppressed": False,
            },
        )
        event["htf_context"] |= bool(row.get("states", {}).get("htf_range_locked"))
        event["htf_alignment"] |= bool(features.get("video_htf_alignment"))
        event["bos"] |= bool(features.get("video_bos"))
        event["sweep"] |= bool(features.get("video_sweep"))
        event["imbalance"] |= bool(features.get("video_imbalance"))
        event["max_score"] = max(
            int(event["max_score"]), int(features.get("video_trade_score") or 0)
        )
        event["range_locked"] |= bool(row.get("states", {}).get("ltf_range_locked"))
        entry_touched_now = bool(features.get("setup_entry_touched_before_ready"))
        current_contract = bool(
            row.get("states", {}).get("htf_range_locked")
            and row.get("states", {}).get("ltf_range_locked")
            and features.get("video_bos")
            and int(features.get("video_trade_score") or 0) >= 75
        )
        if current_contract and not event["contract_reached"]:
            event["contract_reached"] = True
            event["entry_touched_at_contract"] = entry_touched_now
            event["contract_time"] = row["time"]
        event["implementation_ready"] |= bool(
            row.get("signals", {}).get("long_setup_ready")
            or row.get("signals", {}).get("short_setup_ready")
        )
        event["active_suppressed"] |= bool(
            row.get("rejections", {}).get("setup_rejected_active")
        )

    failure_counts: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = {}
    transcript_ready = 0
    for event in events.values():
        transcript_pass = bool(
            event["contract_reached"] and not event["entry_touched_at_contract"]
        )
        transcript_ready += int(transcript_pass)
        if not event["htf_context"]:
            reason = "NO_LOCKED_HTF_CONTEXT"
        elif not event["range_locked"]:
            reason = "NO_LOCKED_15M_RANGE"
        elif not event["bos"]:
            reason = "NO_CONFIRMED_BOS"
        elif int(event["max_score"]) < 75:
            reason = "SCORE_BELOW_75"
        elif not event["contract_reached"]:
            reason = "SCORE_GATES_NEVER_COINCIDE"
        elif event["contract_reached"] and event["entry_touched_at_contract"]:
            reason = "ENTRY_TOUCHED_BEFORE_READY"
        elif event["active_suppressed"]:
            reason = "IMPLEMENTATION_ACTIVE_SETUP_SUPPRESSION"
        elif transcript_pass and not event["implementation_ready"]:
            reason = "IMPLEMENTATION_CHECKLIST_MISMATCH"
        else:
            reason = "READY"
        failure_counts[reason] += 1
        if len(samples.setdefault(reason, [])) < 3:
            samples[reason].append(
                {
                    "event_id": event["event_id"],
                    "time": event["time"],
                    "direction": event["direction"],
                    "score": event["max_score"],
                }
            )

    return {
        "event_count": len(events),
        "independent_pass_counts": {
            "htf_context": sum(int(event["htf_context"]) for event in events.values()),
            "htf_alignment": sum(int(event["htf_alignment"]) for event in events.values()),
            "bos": sum(int(event["bos"]) for event in events.values()),
            "sweep": sum(int(event["sweep"]) for event in events.values()),
            "imbalance": sum(int(event["imbalance"]) for event in events.values()),
            "range_locked": sum(int(event["range_locked"]) for event in events.values()),
            "entry_untouched_at_contract": sum(
                int(
                    event["contract_reached"]
                    and not event["entry_touched_at_contract"]
                )
                for event in events.values()
            ),
        },
        "transcript_ready_count": transcript_ready,
        "implementation_ready_count": sum(
            int(event["implementation_ready"]) for event in events.values()
        ),
        "maximum_score_distribution": dict(
            sorted(Counter(int(event["max_score"]) for event in events.values()).items())
        ),
        "first_failure_counts": dict(sorted(failure_counts.items())),
        "samples": samples,
    }


def stream_expressions() -> dict[str, list[dict[str, Any]]]:
    def fields(
        category: str, values: list[tuple[str, str, str]]
    ) -> list[dict[str, str]]:
        return [
            {
                "name": f"{category}.{name}",
                "expression": expression,
                "kind": kind,
            }
            for name, expression, kind in values
        ]

    return {
        "features": fields(
            "features",
            [
                (
                    "setup_entry_touched_before_ready",
                    "trackedEntryTouchedBeforeReady",
                    "bool",
                ),
                ("htf_structure_high", "swingLastHighPrice", "price"),
                ("htf_structure_low", "swingLastLowPrice", "price"),
                ("htf_bias", "swingBias", "int"),
                ("htf_range_high", "swingRangeHigh", "price"),
                ("htf_range_low", "swingRangeLow", "price"),
                ("htf_range_midpoint", "htfRangeMidpoint", "price"),
                ("htf_direction_gate", "htfDirectionGate", "int"),
                ("ltf_structure_high", "internalLastHighPrice", "price"),
                ("ltf_structure_low", "internalLastLowPrice", "price"),
                ("ltf_bias", "internalBias", "int"),
                (
                    "ltf_pivot_decision",
                    "internalPivotDecisionCode",
                    "int",
                ),
                ("ltf_range_high", "internalRangeHigh", "price"),
                ("ltf_range_low", "internalRangeLow", "price"),
                ("ltf_fib_entry", "ltfFibEntry", "price"),
                ("video_htf_alignment", "videoHtfAlignmentNow", "bool"),
                ("video_bos", "videoBosNow", "bool"),
                ("video_sweep", "videoSweepNow", "bool"),
                ("video_imbalance", "videoImbalanceNow", "bool"),
                ("video_trade_score", "videoTradeScoreNow", "int"),
                ("setup_trade_score", "latestVideoTradeScore", "int"),
                (
                    "ltf_fvg_entry_overlap",
                    "ltfFibFvgOverlap",
                    "bool",
                ),
                (
                    "ltf_event_sweep_source_time",
                    "internalLastEventSweepSourceTime",
                    "int",
                ),
                (
                    "ltf_event_sweep_confirmation_time",
                    "internalLastEventSweepConfirmationTime",
                    "int",
                ),
                ("setup_direction", "latestSetupDirection", "int"),
                ("setup_entry", "liveSetupEntry", "price"),
                ("setup_stop", "liveSetupStop", "price"),
                ("setup_target", "liveSetupTarget", "price"),
            ],
        ),
        "states": fields(
            "states",
            [
                (
                    "ltf_high_consumed",
                    "internalHighConsumed",
                    "bool",
                ),
                ("ltf_low_consumed", "internalLowConsumed", "bool"),
                ("htf_range_locked", "swingRangeLocked", "bool"),
                (
                    "ltf_buy_sweep_active",
                    "latestInternalBuySweepActive",
                    "bool",
                ),
                (
                    "ltf_sell_sweep_active",
                    "latestInternalSellSweepActive",
                    "bool",
                ),
                (
                    "ltf_linked_fvg_active",
                    "ltfDirectionFvgOk",
                    "bool",
                ),
                ("ltf_range_locked", "internalRangeLocked", "bool"),
                (
                    "setup_pending",
                    "anySetupPending",
                    "bool",
                ),
                (
                    "setup_active",
                    "anySetupActive",
                    "bool",
                ),
                (
                    "setup_filled",
                    "anySetupFilled",
                    "bool",
                ),
                (
                    "setup_terminal",
                    "latestSetupState == SETUP_TARGET or latestSetupState == SETUP_STOP or latestSetupState == SETUP_MISSED or latestSetupState == SETUP_INVALID or latestSetupState == SETUP_AMBIGUOUS",
                    "bool",
                ),
            ],
        ),
        "signals": fields(
            "signals",
            [
                (
                    "ltf_raw_high_pivot",
                    "internalRawHighPivot",
                    "bool",
                ),
                ("ltf_raw_low_pivot", "internalRawLowPivot", "bool"),
                (
                    "ltf_high_pivot_accepted",
                    "internalHighPivotAccepted",
                    "bool",
                ),
                (
                    "ltf_low_pivot_accepted",
                    "internalLowPivotAccepted",
                    "bool",
                ),
                (
                    "ltf_pivot_replaced",
                    "internalPivotReplaced",
                    "bool",
                ),
                ("ltf_bull_break", "internalBullBreak", "bool"),
                ("ltf_bear_break", "internalBearBreak", "bool"),
                (
                    "ltf_buy_side_sweep",
                    "internalBuySideSweep",
                    "bool",
                ),
                (
                    "ltf_sell_side_sweep",
                    "internalSellSideSweep",
                    "bool",
                ),
                (
                    "ltf_sweep_consumed",
                    "internalBuySweepConsumed or internalSellSweepConsumed",
                    "bool",
                ),
                (
                    "ltf_manipulation_confirmed",
                    "internalBuySweepConsumed or internalSellSweepConsumed",
                    "bool",
                ),
                (
                    "long_setup_ready",
                    "setupReadySignal and latestSetupDirection == 1",
                    "bool",
                ),
                (
                    "short_setup_ready",
                    "setupReadySignal and latestSetupDirection == -1",
                    "bool",
                ),
                ("setup_filled", "setupFilledSignal", "bool"),
                ("setup_target", "setupTargetSignal", "bool"),
                ("setup_stop", "setupStopSignal", "bool"),
                ("setup_missed", "setupMissedSignal", "bool"),
                ("setup_invalid", "setupInvalidSignal", "bool"),
                (
                    "htf_confirmed_source_update",
                    "confirmedSwingSourceUpdate",
                    "bool",
                ),
                (
                    "htf_discount_gate",
                    "htfDirectionGate == 1",
                    "bool",
                ),
                (
                    "htf_premium_gate",
                    "htfDirectionGate == -1",
                    "bool",
                ),
                ("htf_bull_break", "swingBullBreak", "bool"),
                ("htf_bear_break", "swingBearBreak", "bool"),
            ],
        ),
        "rejections": fields(
            "rejections",
            [
                (
                    "ltf_weaker_same_side_pivot",
                    "internalPivotRejected",
                    "bool",
                ),
                (
                    "ltf_sweep_invalidated",
                    "internalBuySweepInvalidated or internalSellSweepInvalidated",
                    "bool",
                ),
                (
                    "unrelated_fvg_for_latest_break",
                    "unrelatedFvgForLatestBreak",
                    "bool",
                ),
                (
                    "ltf_dual_side_sweep",
                    "internalDualSideSweep",
                    "bool",
                ),
                (
                    "setup_entry_touched_before_ready",
                    "setupRejectedLateSignal",
                    "bool",
                ),
                (
                    "setup_rejected_active",
                    "false",
                    "bool",
                ),
                (
                    "setup_ambiguous",
                    "setupAmbiguousSignal",
                    "bool",
                ),
            ],
        ),
    }


def ensure_revisions(
    workbench: PineWorkbenchService,
    *,
    baseline_source: str,
    candidate_source: str,
    fidelity: dict[str, Any],
    state_start_ms: int,
    parent_revision_id: str,
    semantic_change: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_revision = workbench.revision_detail(BASELINE_REVISION_ID)
    parent_revision = workbench.revision_detail(parent_revision_id)
    candidate_revision = workbench.create_revision(
        source_code=candidate_source,
        source_name=CANDIDATE_PATH.name,
        mode="indicator_first",
        settings_payload={
            "tradingview_symbol": "BINANCE:BTCUSDT",
            "tradingview_timeframe": "15",
            "review_timeframes": ["240", "15"],
            "dataset_id": DATASET_ID,
            "ltf_pivot_length": 2,
            "htf_pivot_length": 5,
            "swing_fib_retracement": 0.71,
            "day_fib_retracement": 0.75,
            "golden_zone_retracement": 0.71,
            "minimum_trade_score": 75,
            "execution": "confirmed_bar_close",
            "state_start_ms": state_start_ms,
            "repaint_policy": "previous_completed_4h_and_confirmed_15m",
            "direction_policy": "4h_premium_discount_is_one_25_point_score_item",
            "sweep_policy": "potential_then_opposite_break_confirmed_manipulation",
            "fvg_policy": "raw_three_candle_causal_imbalance_atr_audit_optional",
            "score_policy": "four_visible_boolean_items_times_25_minimum_75",
            "setup_policy": "confirmed_ready_close_actionable_next_bar",
        },
        provenance={
            "origin": "smart_money_4_video_fidelity_branch",
            "semantic_change": semantic_change,
            "contract": str(CONTRACT_PATH),
            "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
            "fidelity_contract": fidelity,
            "trace_contract": stream_expressions(),
        },
        workbench_id=parent_revision["workbench_id"],
        parent_revision_id=parent_revision_id,
    )
    return baseline_revision, candidate_revision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", type=int, default=1_500)
    parser.add_argument("--register", action="store_true")
    parser.add_argument(
        "--parent-revision-id",
        default=TEMPORAL_LEDGER_PARENT_REVISION_ID,
        help="Immutable parent for a newly registered source revision.",
    )
    parser.add_argument(
        "--semantic-change",
        default="event-level checklist funnel instrumentation only",
        help="Single reviewable semantic or diagnostic change for lineage.",
    )
    parser.add_argument(
        "--proof-revision-id",
        help="Regenerate evidence for an existing immutable candidate revision.",
    )
    args = parser.parse_args()
    if not 500 <= args.bars <= 5_000:
        parser.error("--bars must be between 500 and 5000")
    if args.proof_revision_id and not args.register:
        parser.error("--proof-revision-id requires --register")

    baseline_source = BASELINE_PATH.read_text(encoding="utf-8")
    candidate_source = CANDIDATE_PATH.read_text(encoding="utf-8")
    fidelity = json.loads(FIDELITY_PATH.read_text(encoding="utf-8"))
    repo = Repository()
    data_service = DataService(repo)
    dataset = repo.get_dataset(DATASET_ID)
    if dataset is None:
        raise RuntimeError(f"Dataset {DATASET_ID} is not registered.")
    bars = data_service.load_bars(DATASET_ID)[-args.bars :]
    baseline_rows = evaluate_internal_structure(bars, normalized=False)
    candidate_rows = evaluate_acceptance_contract(bars)

    with tempfile.TemporaryDirectory(prefix="smc-review-") as temporary:
        service = Pine2PythonService(
            Pine2PythonSettings(
                artifact_root=(
                    app_settings.pine_development_dir / "pine2python-artifacts"
                    if args.register
                    else Path(temporary) / "artifacts"
                ),
                work_root=(
                    app_settings.pine_development_dir / "pine2python-work"
                    if args.register
                    else Path(temporary) / "work"
                ),
                worker_timeout_seconds=120,
                max_worker_output_bytes=300_000_000,
            )
        )
        workbench: PineWorkbenchService | None = None
        baseline_revision: dict[str, Any] | None = None
        candidate_revision: dict[str, Any] | None = None
        if args.register:
            workbench = PineWorkbenchService(
                repo,
                data_service,
                DirectClient(service),  # type: ignore[arg-type]
            )
            if args.proof_revision_id:
                baseline_revision = workbench.revision_detail(BASELINE_REVISION_ID)
                candidate_revision = workbench.revision_detail(
                    args.proof_revision_id
                )
                if candidate_revision["source_sha256"] != hashlib.sha256(
                    candidate_source.encode("utf-8")
                ).hexdigest():
                    raise RuntimeError(
                        "Existing proof revision does not match candidate source bytes."
                    )
            else:
                baseline_revision, candidate_revision = ensure_revisions(
                    workbench,
                    baseline_source=baseline_source,
                    candidate_source=candidate_source,
                    fidelity=fidelity,
                    state_start_ms=_time_ms(bars[0]),
                    parent_revision_id=args.parent_revision_id,
                    semantic_change=args.semantic_change,
                )
            baseline_analysis = {
                "status": baseline_revision["status"],
                **baseline_revision["analysis"],
            }
            candidate_analysis = {
                "status": candidate_revision["status"],
                **candidate_revision["analysis"],
            }
        else:
            baseline_analysis = service.analyze(
                AnalyzeRequest(
                    source=baseline_source,
                    name=BASELINE_PATH.name,
                )
            )
            candidate_analysis = service.analyze(
                AnalyzeRequest(
                    source=candidate_source,
                    name=CANDIDATE_PATH.name,
                )
            )
        local_review = build_review_package(
            baseline_revision_id="unregistered_baseline",
            baseline_source=baseline_source,
            candidate_revision_id="unregistered_candidate",
            candidate_source=candidate_source,
            fidelity_contract=fidelity,
            trace_rows=candidate_rows,
        )

        candidate_counts = event_counts(candidate_rows)
        checklist_audit = checklist_event_audit(candidate_rows)
        window_weeks = max(
            (bars[-1].ts - bars[0].ts).total_seconds() / (7 * 24 * 60 * 60),
            1 / 7,
        )
        emitted_setup_count = (
            candidate_counts.get("signals.long_setup_ready", 0)
            + candidate_counts.get("signals.short_setup_ready", 0)
        )
        lifecycle_fixtures = _setup_lifecycle_fixtures(bars[0])
        plot_budget = candidate_analysis["inventory"]["plot_budget"]
        checks = {
            "baseline_parse_complete": "PARSE_COMPLETE" in baseline_analysis["status"],
            "candidate_parse_complete": "PARSE_COMPLETE"
            in candidate_analysis["status"],
            "request_runtime_routed_to_tradingview": (
                "TRADINGVIEW_REVIEW_REQUIRED" in candidate_analysis["status"]
                and bool(candidate_analysis["inventory"]["request_calls"])
            ),
            "protected_source_pass": "SOURCE_FIDELITY_PASS" in local_review["status"],
            "accepted_highs_exist": candidate_counts.get(
                "signals.ltf_high_pivot_accepted", 0
            )
            > 0,
            "accepted_lows_exist": candidate_counts.get(
                "signals.ltf_low_pivot_accepted", 0
            )
            > 0,
            "weaker_pivots_rejected": candidate_counts.get(
                "rejections.ltf_weaker_same_side_pivot", 0
            )
            > 0,
            "bull_and_bear_breaks_exist": (
                candidate_counts.get("signals.ltf_bull_break", 0) > 0
                and candidate_counts.get("signals.ltf_bear_break", 0) > 0
            ),
            "focused_fixtures_exist": bool(
                local_review["fixture_manifest"]["fixtures"]
            ),
            "confirmed_htf_updates_exist": candidate_counts.get(
                "signals.htf_confirmed_source_update", 0
            )
            > 0,
            "premium_and_discount_gates_exist": (
                candidate_counts.get("signals.htf_premium_gate", 0) > 0
                and candidate_counts.get("signals.htf_discount_gate", 0) > 0
            ),
            "sweep_lifecycle_exercised": (
                candidate_counts.get("signals.ltf_sweep_consumed", 0) > 0
                and candidate_counts.get("rejections.ltf_sweep_invalidated", 0) > 0
            ),
            "manipulation_confirmation_exercised": candidate_counts.get(
                "signals.ltf_manipulation_confirmed", 0
            )
            > 0,
            "entry_funnel_accounts_for_every_break": (
                checklist_audit["event_count"]
                == candidate_counts.get("signals.ltf_bull_break", 0)
                + candidate_counts.get("signals.ltf_bear_break", 0)
            ),
            "pine_contract_and_evaluator_ready_counts_match": (
                checklist_audit["transcript_ready_count"]
                == checklist_audit["implementation_ready_count"]
                == emitted_setup_count
            ),
            "video_score_formula_exact": all(
                int(row.get("features", {}).get("video_trade_score") or 0)
                == 25
                * sum(
                    bool(row.get("features", {}).get(name))
                    for name in (
                        "video_htf_alignment",
                        "video_bos",
                        "video_sweep",
                        "video_imbalance",
                    )
                )
                for row in candidate_rows
            ),
            "score_75_setup_exercised": any(
                int(row.get("features", {}).get("setup_trade_score") or 0) == 75
                and bool(
                    row.get("signals", {}).get("long_setup_ready")
                    or row.get("signals", {}).get("short_setup_ready")
                )
                for row in candidate_rows
            ),
            "no_hidden_legacy_veto_after_score": all(
                not bool(
                    row.get("signals", {}).get("long_setup_ready")
                    or row.get("signals", {}).get("short_setup_ready")
                )
                or (
                    int(row.get("features", {}).get("video_trade_score") or 0) >= 75
                    and bool(row.get("features", {}).get("video_bos"))
                    and bool(row.get("states", {}).get("ltf_range_locked"))
                )
                for row in candidate_rows
            ),
            "independent_setup_ledger_has_no_active_suppression": (
                candidate_counts.get("rejections.setup_rejected_active", 0) == 0
                and "array.push(activeSetupIds" in candidate_source
            ),
            "weekly_frequency_plausibility_floor_met": (
                emitted_setup_count / window_weeks >= 1.0
            ),
            "late_setup_rejection_exercised": candidate_counts.get(
                "rejections.setup_entry_touched_before_ready", 0
            )
            > 0,
            "setup_lifecycle_fixtures_pass": all(lifecycle_fixtures.values()),
            "linked_and_unrelated_fvg_exercised": (
                sum(
                    int(row.get("states", {}).get("ltf_linked_fvg_active", 0))
                    for row in candidate_rows
                )
                > 0
                and candidate_counts.get("rejections.unrelated_fvg_for_latest_break", 0)
                > 0
            ),
            "video_fib_defaults_declared": (
                'input.float(0.71, "Swing / 4H Fib entry"' in candidate_source
                and 'input.float(0.75, "Day / 15M execution Fib"' in candidate_source
                and 'input.float(0.71, "Golden-zone companion Fib"' in candidate_source
            ),
            "raw_video_imbalance_is_default": (
                'useFvgValidity = input.bool(false, "Use optional ATR validity filter"'
                in candidate_source
            ),
            "indicator_only_no_orders": (
                'indicator("SmartMoney-4 - 15m Video Checklist' in candidate_source
                and "strategy(" not in candidate_source
                and "strategy." not in candidate_source
            ),
            "confirmed_state_boundary_declared": (
                "bool confirmedEventBar = barstate.isconfirmed" in candidate_source
                and "confirmedEventBar and enableInternalStructure" in candidate_source
                and "confirmedEventBar and enableFvgLogic" in candidate_source
                and "confirmedEventBar and isEntryTf" in candidate_source
            ),
            "plot_budget_within_limit": (
                int(plot_budget["minimum_count"]) <= int(plot_budget["limit"])
                and int(plot_budget["minimum_count"]) == 62
            ),
            "bounded_drawing_ledgers_declared": (
                "maxHistoricalSetupsInput = input.int(25" in candidate_source
                and "maxHistoricalSweepsInput = input.int(25" in candidate_source
                and "MAX_ACTIVE_SETUP_DRAWINGS = 100" in candidate_source
                and "while array.size(historicalSetupMarkers)" in candidate_source
                and "while array.size(finalizedSweepLabels)" in candidate_source
            ),
            "terminal_setups_collapse_to_direction_markers": (
                'setupDirection == 1 ? "LONG" : "SHORT"' in candidate_source
                and "box.delete(setupTargetBox)" in candidate_source
                and "line.delete(setupEntryLine)" in candidate_source
            ),
            "compact_video_checklist_enabled": (
                'showVideoChecklistInput = input.bool(true, "Show real-time video checklist"'
                in candidate_source
                and '"HTF Alignment"' in candidate_source
                and '"Break of Structure"' in candidate_source
                and '"Liquidity Sweep"' in candidate_source
                and '"Trade Score"' in candidate_source
            ),
            "production_dashboard_opt_in": (
                'showDashboard = input.bool(false, "Show dashboard"'
                in candidate_source
            ),
            "history_origin_ids_excluded_from_parity": (
                all(
                    field["name"] not in HISTORY_ORIGIN_DIAGNOSTIC_FIELDS
                    and field["name"]
                    not in {"features.ltf_event_sweep_id", "features.setup_id"}
                    for fields in stream_expressions().values()
                    for field in fields
                )
            ),
        }
        registration: dict[str, Any] | None = None
        if args.register and all(checks.values()):
            assert workbench is not None
            assert baseline_revision is not None
            assert candidate_revision is not None
            review = workbench.prepare_review_package(
                candidate_revision["revision_id"],
                baseline_revision_id=baseline_revision["revision_id"],
                fidelity_contract=fidelity,
                trace_evidence_id=None,
                trace_rows=candidate_rows,
                max_fixtures=18,
            )
            warmup_count = min(4_000, max(0, len(bars) - 500))
            start_ms = _time_ms(bars[warmup_count])
            end_ms = _time_ms(bars[-1]) + 15 * 60 * 1_000
            proof = workbench.create_proof(
                candidate_revision["revision_id"],
                dataset_id=DATASET_ID,
                start_ms=start_ms,
                end_ms=end_ms,
                mintick=0.01,
                trace_rows=candidate_rows[warmup_count:],
                stream_expressions=stream_expressions(),
                profile="basic_v1",
            )
            registration = {
                "workbench_id": baseline_revision["workbench_id"],
                "baseline_revision_id": baseline_revision["revision_id"],
                "candidate_revision_id": candidate_revision["revision_id"],
                "baseline_source_sha256": baseline_revision["source_sha256"],
                "candidate_source_sha256": candidate_revision["source_sha256"],
                "review_evidence_id": review["evidence_id"],
                "review_status": review["status"],
                "proof_evidence_id": proof["evidence_id"],
                "proof_status": proof["status"],
                "local_runtime": proof["payload"]["local_runtime"],
                "instrumented_source_sha256": proof["payload"]["identity"][
                    "instrumented_source_sha256"
                ],
                "proof_artifact": proof["artifact"],
            }

    summary = {
        "checks": checks,
        "passed": all(checks.values()),
        "dataset_id": DATASET_ID,
        "bars": len(bars),
        "baseline_analysis_status": baseline_analysis["status"],
        "candidate_analysis_status": candidate_analysis["status"],
        "protected_source_status": local_review["source_fidelity"]["status"],
        "baseline_event_counts": event_counts(baseline_rows),
        "candidate_event_counts": candidate_counts,
        "checklist_event_audit": checklist_audit,
        "setup_frequency": {
            "window_weeks": round(window_weeks, 4),
            "setup_count": emitted_setup_count,
            "setups_per_week": round(emitted_setup_count / window_weeks, 4),
        },
        "focused_fixture_count": len(local_review["fixture_manifest"]["fixtures"]),
        "setup_lifecycle_fixtures": lifecycle_fixtures,
        "registration": registration,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
