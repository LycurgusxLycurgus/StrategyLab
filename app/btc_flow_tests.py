"""Independent fixtures for the executed-taker-pressure research boundary."""

from __future__ import annotations

import csv
import io
import json
import math
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from app import btc_flow as strategy
from app import btc_flow_broker as broker
from app import btc_flow_campaign as campaign
from app import btc_flow_data as flow_data
from app.btc_liquidity import Candle, Execution


MINUTE = 60_000
DAY = 86_400_000
UTC_DAY0 = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
CANDIDATE = "executed_taker_pressure_reversal_v1"
CONTROL = "price_shock_reversal_control_v1"


def _bar(
    index: int,
    *,
    minutes: int = 5,
    start: int = UTC_DAY0,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
    volume: float = 1.0,
) -> Candle:
    return Candle(start + index * minutes * MINUTE, open_, high, low, close, volume)


def _flat_bars(count: int, *, minutes: int = 5, start: int = UTC_DAY0) -> list[Candle]:
    return [_bar(i, minutes=minutes, start=start) for i in range(count)]


def _features(
    bars: list[Candle], minutes: int, *, atr: float | None = 1.0,
    pressure: float = 0.0, threshold: float | None = 0.0,
) -> list[dict]:
    return [
        {
            "known_at": bar.t + minutes * MINUTE,
            "atr": atr,
            "pressure": pressure,
            "pressure_q99": threshold,
        }
        for bar in bars
    ]


def _intent(
    index: int = 0, direction: int = 1, *, stop: float | None = None,
    anchor: float | None = None,
) -> strategy.Intent:
    return strategy.Intent(
        index=index,
        direction=direction,
        stop=(98.0 if direction == 1 else 102.0) if stop is None else stop,
        anchor=(103.0 if direction == 1 else 97.0) if anchor is None else anchor,
        hold_minutes=120,
        reason="fixture",
    )


def _run_broker(
    bars: list[Candle], signals: list[strategy.Intent], *, minutes: int = 5,
    approach: str = CANDIDATE, direction: str = "both",
    features: list[dict] | None = None, funding: list[dict] | None = None,
    execution: Execution | None = None,
) -> dict:
    return broker.simulate(
        bars,
        signals,
        features if features is not None else _features(bars, minutes),
        minutes,
        approach,
        direction,
        funding if funding is not None else [],
        execution if execution is not None else Execution(funding_mark_buffer_fraction=0.01),
    )


def _flow_row(pressure: float = 0.0, *, quote: float = 100.0) -> dict[str, float]:
    return {"quote": quote, "taker_buy_quote": (quote + pressure) / 2.0}


class FeatureContractTests(unittest.TestCase):
    def test_q99_is_nearest_rank_over_thirty_complete_prior_days_including_zeros(self) -> None:
        minutes = 15
        per_day = DAY // (minutes * MINUTE)
        days = 31
        bars = _flat_bars(days * per_day, minutes=minutes)
        flow = [_flow_row() for _ in bars]
        # Thirty nonzero observations among 2,880 prior bars make the 99th
        # nearest rank the second nonzero value: ceil(.99 * 2,880) == 2,852.
        for pressure in range(1, 31):
            flow[(pressure - 1) * per_day] = _flow_row(float(pressure))
        flow[-1] = _flow_row(1_000.0, quote=2_000.0)

        features = strategy.build_features(bars, flow, minutes)

        self.assertIsNone(features[29 * per_day]["pressure_q99"])
        day_30 = 30 * per_day
        self.assertEqual(features[day_30]["pressure_q99"], 2.0)
        self.assertEqual(features[-1]["pressure_q99"], 2.0)
        self.assertEqual(features[-1]["pressure"], 1_000.0)

    def test_feature_prefix_is_causal_for_every_field_and_detector_output(self) -> None:
        minutes = 15
        per_day = DAY // (minutes * MINUTE)
        count = 31 * per_day + 17
        bars = _flat_bars(count, minutes=minutes)
        flow = [_flow_row() for _ in bars]
        # Provide a deterministic signal-bearing bar after warmup, then make
        # future price and flow extreme without changing its known features.
        signal_index = 30 * per_day + 4
        bars[signal_index] = _bar(
            signal_index, minutes=minutes, open_=100, high=101, low=99.5, close=100.6
        )
        flow[signal_index] = _flow_row(4.0)
        cut = signal_index + 1
        later = cut + 4
        bars[later] = _bar(
            later, minutes=minutes, open_=100, high=500, low=50, close=400
        )
        flow[later] = _flow_row(1_000.0, quote=2_000.0)

        prefix_features = strategy.build_features(bars[:cut], flow[:cut], minutes)
        full_features = strategy.build_features(bars, flow, minutes)

        self.assertEqual(prefix_features, full_features[:cut])
        prefix_signals, prefix_events = strategy.detect(
            bars[:cut], prefix_features, minutes, CANDIDATE
        )
        full_signals, full_events = strategy.detect(bars, full_features, minutes, CANDIDATE)
        self.assertEqual(prefix_signals, [s for s in full_signals if s.index < cut])
        self.assertEqual(prefix_events, [e for e in full_events if e["index"] < cut])
        self.assertIn(signal_index, [s.index for s in prefix_signals])

    def test_hourly_atr_waits_for_twenty_completed_true_ranges_and_uses_newly_closed_hour(self) -> None:
        minutes = 5
        per_hour = 60 // minutes
        bars: list[Candle] = []
        for hour in range(21):
            for offset in range(per_hour):
                index = hour * per_hour + offset
                open_ = 100.0 + hour * 0.37 + offset * 0.025
                close = open_ + (0.04 if offset % 2 == 0 else -0.03)
                bars.append(
                    _bar(
                        index,
                        open_=open_,
                        high=max(open_, close) + 0.08 + (hour % 3) * 0.01,
                        low=min(open_, close) - 0.12 - (offset % 4) * 0.005,
                        close=close,
                    )
                )
        bars.extend(
            [
                _bar(21 * per_hour, open_=108, high=108.3, low=107.8, close=108.1),
                _bar(21 * per_hour + 1, open_=108.1, high=108.4, low=108.0, close=108.2),
            ]
        )
        flow = [_flow_row() for _ in bars]

        features = strategy.build_features(bars, flow, minutes)

        self.assertIsNone(features[20 * per_hour - 1]["atr"])
        grouped_ranges: list[float] = []
        previous_close: float | None = None
        for hour in range(21):
            group = bars[hour * per_hour : (hour + 1) * per_hour]
            high = max(bar.high for bar in group)
            low = min(bar.low for bar in group)
            if previous_close is not None:
                grouped_ranges.append(
                    max(high - low, abs(high - previous_close), abs(low - previous_close))
                )
            previous_close = group[-1].close
        expected_at_21h = sum(grouped_ranges[-20:]) / 20
        self.assertAlmostEqual(features[21 * per_hour - 1]["atr"], expected_at_21h)
        self.assertAlmostEqual(features[21 * per_hour]["atr"], expected_at_21h)
        self.assertAlmostEqual(features[21 * per_hour + 1]["atr"], expected_at_21h)

    def test_feature_input_rejects_missing_bars_bad_flow_length_and_nonfinite_flow(self) -> None:
        bars = _flat_bars(3)
        gap = [bars[0], bars[2]]
        with self.assertRaisesRegex(ValueError, "missing candle"):
            strategy.build_features(gap, [_flow_row(), _flow_row()], 5)
        with self.assertRaisesRegex(ValueError, "Flow count mismatch"):
            strategy.build_features(bars, [_flow_row()], 5)
        bad = [_flow_row(), {"quote": math.nan, "taker_buy_quote": 0.0}, _flow_row()]
        with self.assertRaisesRegex(ValueError, "Invalid flow"):
            strategy.build_features(bars, bad, 5)

    def test_feature_input_rejects_buy_quote_above_total_and_zero_volume_mismatch(self) -> None:
        bars = _flat_bars(2)
        with self.assertRaisesRegex(ValueError, "Invalid flow"):
            strategy.build_features(
                bars, [{"quote": 10.0, "taker_buy_quote": 11.0}, _flow_row()], 5
            )
        zero_volume = [_bar(0, volume=0.0), bars[1]]
        with self.assertRaisesRegex(ValueError, "Invalid flow"):
            strategy.build_features(zero_volume, [_flow_row(), _flow_row()], 5)

    def test_fifteen_minute_aggregation_sums_original_quote_components(self) -> None:
        component = [
            {"quote": 1_000.0, "taker_buy_quote": 550.0},
            {"quote": 2_000.0, "taker_buy_quote": 1_100.0},
            {"quote": 3_000.0, "taker_buy_quote": 1_650.0},
        ]

        aggregated = flow_data.aggregate_flow_15m(component)

        self.assertEqual(aggregated, [{"quote": 6_000.0, "taker_buy_quote": 3_300.0}])
        fifteen = _flat_bars(1, minutes=15)
        feature = strategy.build_features(fifteen, aggregated, 15)[0]
        self.assertEqual(feature["pressure"], 600.0)

    def test_fifteen_minute_aggregation_rejects_partial_bad_and_nonfinite_groups(self) -> None:
        valid = [_flow_row(), _flow_row(), _flow_row()]
        with self.assertRaisesRegex(ValueError, "Incomplete 15-minute flow triplet"):
            flow_data.aggregate_flow_15m(valid[:2])
        with self.assertRaisesRegex(ValueError, "Invalid flow"):
            flow_data.aggregate_flow_15m([valid[0], {"quote": 1.0}, valid[2]])
        bad = [valid[0], {"quote": math.inf, "taker_buy_quote": 0.0}, valid[2]]
        with self.assertRaisesRegex(ValueError, "Invalid flow"):
            flow_data.aggregate_flow_15m(bad)


class SignalContractTests(unittest.TestCase):
    def test_price_impulse_is_inclusive_at_sixty_basis_points_and_fades(self) -> None:
        bars = _flat_bars(2)
        bars[0] = _bar(0, open_=100.0, high=101.0, low=99.0, close=100.6)
        features = _features(bars, 5, atr=2.0, pressure=3.0, threshold=2.0)

        signals, events = strategy.detect(bars, features, 5, CANDIDATE)

        self.assertEqual(len(signals), 1)
        signal = signals[0]
        self.assertEqual((signal.index, signal.direction, signal.anchor), (0, -1, 100.0))
        self.assertAlmostEqual(signal.stop, 104.6)
        raw = next(event for event in events if event["kind"] == "raw_signal")
        self.assertEqual(raw["known_at"], bars[0].t + 5 * MINUTE)
        self.assertEqual(raw["legal_after"], bars[0].t + 5 * MINUTE + 1)

        down = [_bar(0, open_=100.0, high=101.0, low=99.0, close=99.4)]
        down_signal, _ = strategy.detect(
            down, _features(down, 5, atr=2.0, pressure=-3.0, threshold=2.0), 5, CANDIDATE
        )
        self.assertEqual((down_signal[0].direction, down_signal[0].anchor), (1, 100.0))

    def test_below_impulse_threshold_and_wrong_pressure_sign_are_filtered(self) -> None:
        bars = _flat_bars(2)
        bars[0] = _bar(0, open_=100.0, high=101.0, low=99.0, close=100.59)
        features = _features(bars, 5, atr=1.0, pressure=5.0, threshold=1.0)
        signals, _ = strategy.detect(bars, features, 5, CANDIDATE)
        self.assertEqual(signals, [])

        bars[0] = _bar(0, open_=100.0, high=101.0, low=99.0, close=101.0)
        features = _features(bars, 5, atr=1.0, pressure=-5.0, threshold=1.0)
        signals, events = strategy.detect(bars, features, 5, CANDIDATE)
        self.assertEqual(signals, [])
        self.assertIn("pressure_filter", [event["kind"] for event in events])

    def test_candidate_uses_strict_pressure_quantile_while_control_omits_flow_filter(self) -> None:
        bars = _flat_bars(2)
        bars[0] = _bar(0, open_=100.0, high=101.0, low=99.0, close=101.0)
        exact = _features(bars, 5, atr=2.0, pressure=4.0, threshold=4.0)

        candidate_exact, _ = strategy.detect(bars, exact, 5, CANDIDATE)
        control_exact, _ = strategy.detect(bars, exact, 5, CONTROL)
        above = _features(bars, 5, atr=2.0, pressure=4.01, threshold=4.0)
        candidate_above, _ = strategy.detect(bars, above, 5, CANDIDATE)
        opposite = _features(bars, 5, atr=2.0, pressure=-5.0, threshold=4.0)
        candidate_opposite, _ = strategy.detect(bars, opposite, 5, CANDIDATE)
        control_opposite, _ = strategy.detect(bars, opposite, 5, CONTROL)

        self.assertEqual(candidate_exact, [])
        self.assertEqual(len(control_exact), 1)
        self.assertEqual(len(candidate_above), 1)
        self.assertEqual(candidate_opposite, [])
        self.assertEqual(len(control_opposite), 1)

    def test_control_shares_feature_warmup_atr_timing_stop_and_anchor(self) -> None:
        bars = _flat_bars(2)
        bars[0] = _bar(0, open_=100.0, high=101.0, low=99.0, close=101.0)
        unavailable = _features(bars, 5, atr=None, pressure=500.0, threshold=None)
        self.assertEqual(strategy.detect(bars, unavailable, 5, CONTROL)[0], [])

        ready = _features(bars, 5, atr=2.0, pressure=5.0, threshold=4.0)
        candidate, _ = strategy.detect(bars, ready, 5, CANDIDATE)
        control, events = strategy.detect(bars, ready, 5, CONTROL)
        self.assertEqual(
            (candidate[0].index, candidate[0].direction, candidate[0].stop,
             candidate[0].anchor, candidate[0].hold_minutes),
            (control[0].index, control[0].direction, control[0].stop,
             control[0].anchor, control[0].hold_minutes),
        )
        self.assertEqual(candidate[0].reason, CANDIDATE)
        self.assertEqual(control[0].reason, CONTROL)
        self.assertEqual(control[0], strategy.Intent(0, -1, 105.0, 100.0, 120, CONTROL))
        self.assertEqual(events[0]["known_at"], bars[0].t + 5 * MINUTE)

    def test_detector_rejects_feature_timing_and_bad_context(self) -> None:
        bars = _flat_bars(2)
        features = _features(bars, 5)
        features[1]["known_at"] += 1
        with self.assertRaisesRegex(ValueError, "Feature timing mismatch"):
            strategy.detect(bars, features, 5, CANDIDATE)
        with self.assertRaisesRegex(ValueError, "Invalid detector inputs"):
            strategy.detect(bars, _features(bars, 5), 5, "unregistered")


class CostAdmissionTests(unittest.TestCase):
    def test_reference_friction_equality_passes_and_wrong_side_stops_fail(self) -> None:
        admitted = strategy.cost_admitted
        self.assertTrue(admitted(100.0, 99.2, 1))
        self.assertTrue(admitted(100.0, 100.8, -1))
        self.assertFalse(admitted(100.0, 100.01, 1))
        self.assertFalse(admitted(100.0, 99.99, -1))
        self.assertFalse(admitted(100.0, 99.0, 0))

    def test_initial_stop_rounds_away_from_entry_and_fill_guard_rejects_a_gap(self) -> None:
        bars = _flat_bars(4)
        rounded = _run_broker(
            bars, [_intent(stop=97.91, anchor=103.0)]
        )
        self.assertIsNotNone(rounded["open_position"])
        self.assertEqual(rounded["open_position"]["stop"], 97.9)

        gap_bars = list(bars)
        gap_bars[2] = _bar(2, open_=98.0, high=99.0, low=97.5, close=98.5)
        rejected = _run_broker(gap_bars, [_intent(stop=99.0, anchor=104.0)])
        self.assertIsNone(rejected["open_position"])
        self.assertIn("fill_cost_guard", rejected["metrics"]["counts"])


class BrokerContractTests(unittest.TestCase):
    def test_entry_waits_one_whole_bar_after_legal_after_and_records_actual_fill(self) -> None:
        bars = _flat_bars(4)
        result = _run_broker(bars, [_intent(anchor=103.0)])

        position = result["open_position"]
        self.assertIsNotNone(position)
        self.assertEqual(position["signal_index"], 0)
        self.assertEqual(position["known_at"], bars[0].t + 5 * MINUTE)
        self.assertEqual(position["legal_after"], bars[0].t + 5 * MINUTE + 1)
        self.assertEqual(position["entry_index"], 2)
        self.assertEqual(position["entry_at"], bars[2].t)
        self.assertAlmostEqual(position["entry"], bars[2].open * 1.0002)

    def test_fill_requires_six_tenths_percent_anchor_room_after_slippage(self) -> None:
        boundary = 100.02 * 1.006
        exact_bars = _flat_bars(4)
        exact_bars[0] = _bar(0, open_=boundary, high=101.0, low=99.0, close=100.0)
        exact_bars[2] = _bar(2, open_=100.0, high=100.5, low=99.0, close=100.0)
        exact = _run_broker(exact_bars, [_intent(anchor=boundary)])
        self.assertEqual(exact["metrics"]["counts"].get("filled"), 1)
        self.assertEqual(exact["trades"][0]["reason"], "anchor")

        below_bars = _flat_bars(4)
        below_anchor = boundary - 1e-8
        below_bars[0] = _bar(
            0, open_=below_anchor, high=101.0, low=99.0, close=100.0
        )
        below_bars[2] = _bar(2, open_=100.0, high=100.5, low=99.0, close=100.0)
        below = _run_broker(below_bars, [_intent(anchor=below_anchor)])
        self.assertEqual(below["metrics"]["counts"].get("anchor_room_reject"), 1)

        bars = _flat_bars(4)
        bars[2] = _bar(2, open_=102.5, high=103.0, low=102.0, close=102.5)
        result = _run_broker(bars, [_intent(anchor=103.0)])
        self.assertIsNone(result["open_position"])
        self.assertEqual(result["metrics"]["counts"].get("anchor_room_reject"), 1)

    def test_fifteen_minute_long_and_short_entries_preserve_known_fill_clock(self) -> None:
        bars = _flat_bars(4, minutes=15)
        for direction, anchor, stop in ((1, 103.0, 98.0), (-1, 97.0, 102.0)):
            result = _run_broker(
                bars,
                [_intent(0, direction=direction, stop=stop, anchor=anchor)],
                minutes=15,
            )
            position = result["open_position"]
            self.assertIsNotNone(position)
            self.assertEqual(position["direction"], direction)
            self.assertEqual(position["known_at"], bars[0].t + 15 * MINUTE)
            self.assertEqual(position["legal_after"], bars[0].t + 15 * MINUTE + 1)
            self.assertEqual(position["entry_index"], 2)
            self.assertEqual(position["entry_at"], bars[2].t)

    def test_quote_notional_sizing_and_entry_exit_fees_reconcile(self) -> None:
        bars = _flat_bars(4)
        bars[3] = _bar(3, open_=100, high=101, low=97, close=99)
        execution = Execution(funding_mark_buffer_fraction=0.01)
        result = _run_broker(
            bars, [_intent(stop=98.0, anchor=110.0)], execution=execution
        )
        trade = result["trades"][0]
        fee = execution.fee_bps / 10_000
        slip = execution.slip_bps / 10_000
        stopped = trade["initial_stop"] * (1 - slip)
        risk_per_unit = trade["entry"] - stopped + fee * (trade["entry"] + stopped)
        desired = min(
            trade["entry_equity"] * execution.risk_fraction / risk_per_unit,
            trade["entry_equity"] * execution.max_notional_fraction
            / (trade["entry"] * (1 + fee)),
            execution.max_quantity,
        )
        expected_quantity = math.floor(
            desired / execution.quantity_step + 1e-9
        ) * execution.quantity_step
        self.assertAlmostEqual(trade["quantity"], expected_quantity)
        self.assertAlmostEqual(trade["initial_risk"], expected_quantity * risk_per_unit)
        self.assertLessEqual(
            trade["initial_risk"], execution.initial_capital * execution.risk_fraction
        )

        expected_entry_fee = trade["entry"] * trade["quantity"] * fee
        expected_exit_fee = trade["exit"] * trade["quantity"] * fee
        expected_gross = trade["direction"] * trade["quantity"] * (
            trade["exit"] - trade["entry"]
        )
        self.assertAlmostEqual(trade["entry_fee"], expected_entry_fee)
        self.assertAlmostEqual(trade["exit_fee"], expected_exit_fee)
        self.assertAlmostEqual(trade["gross_pnl"], expected_gross)
        self.assertAlmostEqual(
            trade["net_pnl"], expected_gross - expected_entry_fee - expected_exit_fee
        )
        self.assertAlmostEqual(
            result["metrics"]["fees"], expected_entry_fee + expected_exit_fee
        )

    def test_both_intrabar_levels_stop_first_and_short_is_the_mirror(self) -> None:
        long_bars = _flat_bars(4)
        long_bars[3] = _bar(3, open_=100, high=104, low=97, close=101)
        long_result = _run_broker(
            long_bars, [_intent(direction=1, stop=98.0, anchor=103.0)]
        )
        self.assertEqual(long_result["trades"][0]["reason"], "stop")
        self.assertEqual(long_result["trades"][0]["raw_exit"], 98.0)

        short_bars = _flat_bars(4)
        short_bars[3] = _bar(3, open_=100, high=103, low=96, close=99)
        short_result = _run_broker(
            short_bars, [_intent(direction=-1, stop=102.0, anchor=97.0)]
        )
        self.assertEqual(short_result["trades"][0]["reason"], "stop")
        self.assertEqual(short_result["trades"][0]["raw_exit"], 102.0)

    def test_stop_gap_uses_adverse_open_and_anchor_gap_never_improves_target(self) -> None:
        gap = _flat_bars(4)
        gap[3] = _bar(3, open_=96.0, high=97.0, low=95.0, close=96.5)
        stopped = _run_broker(gap, [_intent(stop=98.0, anchor=103.0)])
        self.assertEqual(stopped["trades"][0]["reason"], "stop_gap")
        self.assertEqual(stopped["trades"][0]["raw_exit"], 96.0)
        self.assertLess(stopped["trades"][0]["exit"], 96.0)

        target_gap = _flat_bars(4)
        target_gap[3] = _bar(3, open_=105.0, high=106.0, low=104.0, close=105.5)
        targeted = _run_broker(target_gap, [_intent(stop=98.0, anchor=103.0)])
        self.assertEqual(targeted["trades"][0]["reason"], "anchor_gap")
        self.assertEqual(targeted["trades"][0]["raw_exit"], 103.0)
        self.assertLess(targeted["trades"][0]["exit"], 103.0)

    def test_deadline_is_the_earlier_of_two_hours_and_utc_2345_flat(self) -> None:
        bars = _flat_bars(27)
        result = _run_broker(bars, [_intent(anchor=110.0)])
        trade = result["trades"][0]
        self.assertEqual(trade["reason"], "time_exit")
        self.assertEqual(trade["exit_at"] - trade["entry_at"], 120 * MINUTE)

        start = UTC_DAY0 + (21 * 60 + 50) * MINUTE
        flat_bars = _flat_bars(24, start=start)
        flat = _run_broker(flat_bars, [_intent(anchor=110.0)])
        flat_trade = flat["trades"][0]
        self.assertEqual(flat_trade["entry_at"] % DAY, 22 * 60 * MINUTE)
        self.assertEqual(flat_trade["reason"], "flat_exit")
        self.assertEqual(flat_trade["exit_at"] % DAY, (23 * 60 + 45) * MINUTE)

    def test_last_entry_cutoff_allows_2200_and_rejects_later_fill(self) -> None:
        cutoff = UTC_DAY0 + (21 * 60 + 50) * MINUTE
        allowed_bars = _flat_bars(4, start=cutoff)
        allowed = _run_broker(allowed_bars, [_intent(anchor=110.0)])
        self.assertIsNotNone(allowed["open_position"])
        self.assertEqual(allowed["open_position"]["entry_at"] % DAY, 22 * 60 * MINUTE)

        later_start = UTC_DAY0 + (21 * 60 + 55) * MINUTE
        later_bars = _flat_bars(4, start=later_start)
        later = _run_broker(later_bars, [_intent(anchor=110.0)])
        self.assertIsNone(later["open_position"])
        self.assertEqual(later["metrics"]["counts"].get("entry_time_reject"), 1)

        midnight_start = UTC_DAY0 + (23 * 60 + 50) * MINUTE
        midnight_bars = _flat_bars(4, start=midnight_start)
        midnight = _run_broker(midnight_bars, [_intent(anchor=110.0)])
        self.assertIsNone(midnight["open_position"])
        self.assertEqual(midnight["metrics"]["counts"].get("entry_time_reject"), 1)

    def test_daily_cap_counts_filled_entries_and_open_position_cannot_be_replaced(self) -> None:
        bars = _flat_bars(12)
        for index in (2, 4, 6, 8, 10):
            bars[index] = _bar(index, open_=100, high=104, low=99, close=102)
        signals = [_intent(index, anchor=103.0) for index in (0, 2, 4, 6, 8)]
        capped = _run_broker(bars, signals)
        self.assertEqual(capped["metrics"]["counts"].get("filled"), 4)
        self.assertEqual(capped["metrics"]["counts"].get("daily_entry_cap"), 1)

        held_bars = _flat_bars(4)
        same_open = _run_broker(
            held_bars,
            [_intent(0, anchor=110.0), _intent(0, direction=-1, anchor=90.0)],
        )
        self.assertEqual(same_open["metrics"]["counts"].get("filled"), 1)
        self.assertEqual(same_open["metrics"]["counts"].get("occupied_at_open"), 1)

        carried_open = _run_broker(
            held_bars,
            [_intent(0, anchor=110.0), _intent(1, direction=-1, anchor=90.0)],
        )
        self.assertEqual(carried_open["metrics"]["counts"].get("filled"), 1)
        self.assertEqual(carried_open["metrics"]["counts"].get("occupied_at_open"), 1)

        gap_open_bars = _flat_bars(5)
        gap_open_bars[4] = _bar(4, open_=97, high=99, low=96, close=98)
        exited_at_open = _run_broker(
            gap_open_bars,
            [_intent(0, anchor=110.0), _intent(2, stop=96.0, anchor=110.0)],
        )
        self.assertEqual(exited_at_open["metrics"]["counts"].get("stop_gap"), 1)
        self.assertEqual(exited_at_open["metrics"]["counts"].get("occupied_at_open"), 1)
        self.assertIsNone(exited_at_open["open_position"])

    def test_direction_filter_runs_before_filled_entry_cap(self) -> None:
        bars = _flat_bars(4)
        result = _run_broker(
            bars,
            [_intent(0, direction=-1, anchor=97.0), _intent(0, direction=1, anchor=110.0)],
            direction="long",
        )
        self.assertEqual(result["metrics"]["counts"].get("direction_excluded"), 1)
        self.assertEqual(result["metrics"]["counts"].get("filled"), 1)
        self.assertEqual(result["open_position"]["direction"], 1)

    def test_exact_open_funding_belongs_to_carried_position_not_new_entry(self) -> None:
        bars = _flat_bars(5)
        funding = [
            {"ts": bars[2].t, "rate": 0.01, "mark": 100.0},
            {"ts": bars[3].t, "rate": 0.01, "mark": 100.0},
        ]
        result = _run_broker(bars, [_intent(anchor=110.0)], funding=funding)

        entries = [row for row in result["ledger"] if row["kind"] == "filled"]
        charges = [row for row in result["ledger"] if row["kind"] == "funding"]
        self.assertEqual(len(entries), 1)
        self.assertEqual([row["at"] for row in charges], [bars[3].t])
        self.assertLess(charges[0]["amount"], 0)

    def test_uncertain_intrabar_exit_charges_debit_and_discards_credit(self) -> None:
        bars = _flat_bars(4)
        bars[3] = _bar(3, open_=100, high=104, low=97, close=100)
        debit = _run_broker(
            bars,
            [_intent(stop=98.0, anchor=103.0)],
            funding=[{"ts": bars[3].t + MINUTE, "rate": 0.01, "mark": 100.0}],
        )
        credit = _run_broker(
            bars,
            [_intent(stop=98.0, anchor=103.0)],
            funding=[{"ts": bars[3].t + MINUTE, "rate": -0.01, "mark": 100.0}],
        )
        debit_row = next(row for row in debit["ledger"] if row["kind"] == "funding")
        credit_row = next(row for row in credit["ledger"] if row["kind"] == "funding")
        self.assertLess(debit_row["amount"], 0)
        self.assertTrue(debit_row["uncertain_exit_order"])
        self.assertEqual(credit_row["amount"], 0.0)
        self.assertTrue(credit_row["uncertain_exit_order"])

    def test_mark_to_market_open_position_and_last_two_intents_are_censored(self) -> None:
        bars = _flat_bars(4)
        bars[3] = _bar(3, open_=100, high=101, low=99, close=101)
        open_result = _run_broker(bars, [_intent(anchor=110.0)])
        position = open_result["open_position"]
        self.assertIsNotNone(position)
        final = open_result["equity"][-1]
        expected = (
            final["cash"]
            + position["direction"] * position["quantity"] * (bars[-1].close - position["entry"])
            - bars[-1].close * position["quantity"] * 0.0006
        )
        self.assertAlmostEqual(final["equity"], expected)
        self.assertGreater(final["notional"], 0)

        tail = _run_broker(
            _flat_bars(4),
            [_intent(2, anchor=110.0), _intent(3, direction=-1, anchor=90.0)],
        )
        self.assertEqual(tail["metrics"]["counts"].get("censored_intent"), 2)
        self.assertIsNone(tail["open_position"])


class RawFlowAdapterTests(unittest.TestCase):
    @staticmethod
    def _archive_for_row(row: list[str]) -> zipfile.ZipFile:
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("month.csv", ",".join(row) + "\n")
        return zipfile.ZipFile(io.BytesIO(payload.getvalue()))

    def _load_fixture(self, bar: Candle, *, expected_rows: int = 1, row: list[str] | None = None) -> list[dict]:
        values = row or [
            str(bar.t), str(bar.open), str(bar.high), str(bar.low), str(bar.close), "10",
            "ignored", "1000", "ignored", "4", "400",
        ]
        archive = self._archive_for_row(values)
        month = type(
            "MonthFixture",
            (),
            {"filename": "fixture.zip", "expected_rows": expected_rows,
             "first_ms": bar.t, "next_month_ms": bar.t + 60 * MINUTE},
        )()
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            flow_data, "_months", return_value=[month]
        ), mock.patch.object(flow_data, "_load_manifest", return_value={}), mock.patch.object(
            flow_data, "_open_archive_member", return_value=(archive, archive.open("month.csv"))
        ):
            return flow_data.load_flow(temporary, [bar])

    def test_verified_archive_adapter_returns_aligned_quote_and_taker_buy_values(self) -> None:
        bar = _bar(0, open_=100, high=105, low=95, close=101, volume=10)
        self.assertEqual(self._load_fixture(bar), [{"quote": 1000.0, "taker_buy_quote": 400.0}])

    def test_archive_adapter_checks_average_price_alignment_and_monthly_count(self) -> None:
        bar = _bar(0, open_=100, high=105, low=95, close=101, volume=10)
        bad_average = [
            str(bar.t), str(bar.open), str(bar.high), str(bar.low), str(bar.close), "10",
            "ignored", "1000", "ignored", "4", "600",
        ]
        with self.assertRaisesRegex(ValueError, "Inconsistent quote/base flow"):
            self._load_fixture(bar, row=bad_average)

        bad_time = [
            str(bar.t + 5 * MINUTE), str(bar.open), str(bar.high), str(bar.low), str(bar.close), "10",
            "ignored", "1000", "ignored", "4", "400",
        ]
        with self.assertRaisesRegex(ValueError, "Flow candle alignment mismatch"):
            self._load_fixture(bar, row=bad_time)
        with self.assertRaisesRegex(ValueError, "Incomplete monthly flow archive"):
            self._load_fixture(bar, expected_rows=2)


def _metrics(return_pct: float, trades: int) -> dict:
    return {
        "net_return_pct": return_pct,
        "closed_trades": trades,
        "gross_profit": 110.0,
        "gross_loss": 100.0,
        "max_drawdown_pct": 9.0,
        "adverse_drawdown_pct": 9.5,
        "fees": 10.0,
        "funding": 0.0,
    }


def _screen_fixture(candidate_recent: float = 2.0, control_recent: float = 1.0) -> list[dict]:
    rows = []
    for minutes in (5, 15):
        for approach in (CANDIDATE, CONTROL):
            for direction in ("long", "short", "both"):
                is_control = approach == CONTROL
                recent = control_recent if is_control else candidate_recent
                base = {
                    year: _metrics(recent if year in (2025, 2026) else 0.5,
                                   50 if year in (2025, 2026) else 2)
                    for year in range(2022, 2027)
                }
                stress = {
                    year: _metrics(0.25 if year in (2025, 2026) else -0.25,
                                   50 if year in (2025, 2026) else 2)
                    for year in range(2022, 2027)
                }
                rows.append(
                    {"minutes": minutes, "approach": approach, "direction": direction,
                     "base": {str(y): value for y, value in base.items()},
                     "stress": {str(y): value for y, value in stress.items()}}
                )
    return rows


class CampaignGateTests(unittest.TestCase):
    def test_frozen_protocol_validates_and_rejects_authority_or_matrix_changes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads(
            (root / "artifacts/strategy-development/btc-flow-phase2-20261028/protocol.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(campaign.validate_protocol(protocol))
        changed = dict(protocol)
        changed["phase2_execution_authorized"] = False
        with self.assertRaisesRegex(ValueError, "Protocol differs from frozen contract"):
            campaign.validate_protocol(changed)

        valid_rows = _screen_fixture()
        screen_rows = campaign.screen_rows(valid_rows, protocol)
        candidates = [row for row in screen_rows if row["approach"] == CANDIDATE]
        controls = [row for row in screen_rows if row["approach"] == CONTROL]
        self.assertEqual(len(candidates), 6)
        self.assertTrue(all(row["qualified"] for row in candidates))
        self.assertTrue(all(not row["qualified"] for row in controls))
        self.assertTrue(all(row["recent_base_return_pct"] > row["matched_control_recent_base_return_pct"] for row in candidates))

        with self.assertRaisesRegex(ValueError, "Incomplete matrix"):
            campaign.screen_rows(valid_rows[:-1], protocol)

    def test_matched_control_gate_requires_strict_incremental_recent_return(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads(
            (root / "artifacts/strategy-development/btc-flow-phase2-20261028/protocol.json").read_text(
                encoding="utf-8"
            )
        )
        rows = campaign.screen_rows(_screen_fixture(candidate_recent=1.0, control_recent=1.0), protocol)
        candidate = next(row for row in rows if row["minutes"] == 5 and row["direction"] == "long" and row["approach"] == CANDIDATE)
        self.assertFalse(candidate["qualified"])
        self.assertIn("recent base return does not exceed matched price control", candidate["screen_failures"])

    def test_campaign_authentication_and_existing_run_guard_precede_data_loading(self) -> None:
        project = Path(__file__).resolve().parents[1]
        protocol_bytes = (
            project / "artifacts/strategy-development/btc-flow-phase2-20261028/protocol.json"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "protocol.json").write_bytes(protocol_bytes)
            identities = {
                name: campaign.sha(project / name) for name in campaign.REQUIRED_SOURCES
            }
            raw = Path(
                json.loads(protocol_bytes.decode("utf-8"))["data_root"]
            )
            identities.update({path.as_posix(): campaign.sha(path) for path in raw.glob("*.json")})
            identities[(raw / "manifest.json").as_posix()] = campaign.sha(raw / "manifest.json")
            identity_path = root / "INPUT_IDENTITIES.json"
            identity_path.write_text(json.dumps(identities), encoding="utf-8")
            authorization = {
                "protocol_sha256": campaign.sha(root / "protocol.json"),
                "input_identities_sha256": campaign.sha(identity_path),
            }
            (root / "AUTHORIZATION.json").write_text(json.dumps(authorization), encoding="utf-8")
            run = root / "runs" / "preserve-me"
            run.mkdir(parents=True)
            sentinel = run / "sentinel.txt"
            sentinel.write_text("original", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                campaign.comparison(root, "preserve-me")

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "original")
            self.assertFalse((root / "cumulative_trials.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
