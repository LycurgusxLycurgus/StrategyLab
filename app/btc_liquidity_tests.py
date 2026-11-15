"""Independent constructed cases for the BTC liquidity research boundary."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from app import btc_liquidity as strategy
from app import btc_liquidity_campaign as campaign
from app import btc_liquidity_data as data


STEP = 5 * 60_000


def _candle(index: int, open_: float, high: float, low: float, close: float, volume: float = 1.0) -> strategy.Candle:
    return strategy.Candle(index * STEP, open_, high, low, close, volume)


def _liquidity_case() -> list[strategy.Candle]:
    return [
        _candle(0, 100, 102, 98, 100),
        _candle(1, 100, 102, 98, 100),
        _candle(2, 100, 102, 98, 100),
        _candle(3, 100, 101, 97, 100),
        _candle(4, 100, 104, 98, 103),
    ]


def _small_parameters(**overrides: float | int) -> strategy.Parameters:
    values: dict[str, float | int] = {
        "lookback_minutes": 15,
        "atr_minutes": 10,
        "confirm_minutes": 10,
        "max_hold_minutes": 15,
    }
    values.update(overrides)
    return strategy.Parameters(**values)


def _bar_sequence(rows: list[tuple[float, float, float, float]]) -> list[strategy.Candle]:
    return [_candle(index, *row) for index, row in enumerate(rows)]


class SignalContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.p = _small_parameters()

    def test_reclaim_emits_at_sweep_close_with_prior_range_stop(self) -> None:
        bars = _liquidity_case()
        signals, events = strategy.detect(bars, 5, "reclaim", self.p)

        self.assertEqual(len(signals), 1)
        signal = signals[0]
        self.assertEqual((signal.index, signal.direction, signal.sweep_index), (3, 1, 3))
        self.assertEqual(signal.reason, "reclaim")
        self.assertAlmostEqual(signal.stop, 96.6)
        sweep = next(event for event in events if event["kind"] == "sweep")
        self.assertEqual(sweep["known_at"], bars[3].t + STEP)

    def test_confirmation_waits_for_a_closed_displacement_bar(self) -> None:
        bars = _liquidity_case()
        signals, events = strategy.detect(bars, 5, "confirm", self.p)

        self.assertEqual([(s.index, s.direction, s.sweep_index) for s in signals], [(4, 1, 3)])
        self.assertEqual(signals[0].reason, "confirm")
        confirmed = next(event for event in events if event["kind"] == "confirmed")
        self.assertEqual(confirmed["index"], 4)
        self.assertEqual(confirmed["known_at"], bars[4].t + STEP)
        early_signals, early_events = strategy.detect(bars[:4], 5, "confirm", self.p)
        self.assertEqual(early_signals, [])
        self.assertEqual(
            [event["kind"] for event in early_events], ["sweep", "pending_at_cutoff"]
        )

    def test_fvg_confirmation_uses_the_known_gap_and_preserves_prior_candidate(self) -> None:
        bars = _liquidity_case()
        # This close at 100 does not confirm the pending long; the later candle
        # crosses the sweep extreme with a bullish three-bar gap.
        bars[4] = _candle(4, 100, 102, 98, 100)
        bars.append(_candle(5, 103, 107, 103, 106))
        signals, events = strategy.detect(bars, 5, "confirm_fvg", self.p)

        self.assertEqual([(s.index, s.direction, s.sweep_index) for s in signals], [(5, 1, 3)])
        self.assertEqual(signals[0].reason, "confirm_fvg")
        self.assertTrue(any(event["kind"] == "confirmed" and event["index"] == 5 for event in events))

    def test_plain_confirmation_does_not_pass_the_stricter_fvg_approach(self) -> None:
        bars = _liquidity_case()
        plain, _ = strategy.detect(bars, 5, "confirm", self.p)
        fvg, _ = strategy.detect(bars, 5, "confirm_fvg", self.p)

        self.assertEqual([(signal.index, signal.sweep_index) for signal in plain], [(4, 3)])
        self.assertEqual(fvg, [])

    def test_opposite_sweep_replaces_single_pending_candidate(self) -> None:
        bars = _liquidity_case()
        bars[4] = _candle(4, 100, 104, 98, 100)
        bars.append(_candle(5, 103, 107, 103, 106))
        signals, events = strategy.detect(bars, 5, "confirm", self.p)

        self.assertEqual(signals, [])
        self.assertTrue(
            any(event["kind"] == "replaced" and event["index"] == 4 and event["sweep_index"] == 3 for event in events)
        )
        self.assertTrue(
            any(event["kind"] == "invalidated" and event["index"] == 5 and event["sweep_index"] == 4 for event in events)
        )

    def test_unconfirmed_candidate_expires_after_the_declared_window(self) -> None:
        bars = _liquidity_case()[:4] + [
            _candle(4, 100, 101, 99, 100),
            _candle(5, 100, 101, 99, 100),
            _candle(6, 100, 101, 99, 100),
        ]
        signals, events = strategy.detect(bars, 5, "confirm", self.p)

        self.assertEqual(signals, [])
        expiry = next(event for event in events if event["kind"] == "expired")
        self.assertEqual(expiry["index"], 6)
        self.assertEqual(expiry["sweep_index"], 3)

    def test_wick_breach_before_confirmation_invalidates_candidate(self) -> None:
        bars = _liquidity_case()[:4] + [
            _candle(4, 100, 101, 96, 97),
            _candle(5, 100, 101, 99, 100),
        ]
        signals, events = strategy.detect(bars, 5, "confirm", self.p)

        self.assertEqual(signals, [])
        invalidation = next(event for event in events if event["kind"] == "invalidated")
        self.assertEqual((invalidation["index"], invalidation["sweep_index"]), (4, 3))

    def test_dual_sweep_is_excluded_instead_of_choosing_a_side(self) -> None:
        bars = _liquidity_case()[:3] + [_candle(3, 100, 103, 97, 100)]
        signals, events = strategy.detect(bars, 5, "reclaim", self.p)

        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "dual_sweep_excluded" for event in events))

    def test_features_signals_and_mature_events_are_prefix_invariant(self) -> None:
        bars = _liquidity_case() + [
            _candle(5, 103, 107, 103, 106),
            _candle(6, 106, 108, 104, 107),
        ]
        full_features = strategy.indicators(bars, 5, self.p)
        full_signals, full_events = strategy.detect(bars, 5, "confirm", self.p)

        for length in range(3, len(bars) + 1):
            prefix = bars[:length]
            prefix_features = strategy.indicators(prefix, 5, self.p)
            prefix_signals, prefix_events = strategy.detect(prefix, 5, "confirm", self.p)
            self.assertEqual(prefix_features, full_features[:length])
            self.assertEqual(
                prefix_signals,
                [signal for signal in full_signals if signal.index < length],
            )
            self.assertEqual(
                [event for event in prefix_events if event["kind"] != "pending_at_cutoff"],
                [
                    event
                    for event in full_events
                    if event["kind"] != "pending_at_cutoff" and event["index"] < length
                ],
            )


class ExecutionContractTests(unittest.TestCase):
    def _signal(self, direction: int = 1, stop: float | None = None) -> strategy.Signal:
        return strategy.Signal(0, direction, stop if stop is not None else (90 if direction == 1 else 110), 0, "fixture")

    def _execution_bars(self, tail: list[tuple[float, float, float, float]]) -> list[strategy.Candle]:
        return _bar_sequence([(100, 101, 99, 100)] + tail)

    def _zero_cost_execution(self, **overrides: float) -> strategy.Execution:
        return strategy.Execution(fee_bps=0, slip_bps=0, **overrides)

    def test_signal_fills_only_at_the_following_open(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 101, 99, 100)])
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            self._zero_cost_execution(),
        )

        position = result["open_position"]
        self.assertEqual(position["entry_index"], 1)
        self.assertEqual(position["entry_at"], bars[1].t)
        self.assertEqual(position["known_at"], bars[0].t + STEP)
        self.assertEqual(position["entry"], bars[1].open)

    def test_both_stop_and_target_on_one_bar_take_the_adverse_stop_first(self) -> None:
        bars = self._execution_bars([(100, 121, 89, 100)])
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            self._zero_cost_execution(),
        )

        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["reason"], "ambiguous_stop_first")
        self.assertEqual(result["trades"][0]["exit"], 90)

    def test_gap_through_stop_fills_at_the_next_open(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (80, 85, 78, 82)])
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            self._zero_cost_execution(),
        )

        self.assertEqual(result["trades"][0]["reason"], "stop_gap")
        self.assertEqual(result["trades"][0]["exit"], 80)

    def test_gap_exit_omits_later_funding_but_keeps_funding_at_the_open(self) -> None:
        cases = (
            ("long", 1, 90, (80, 85, 78, 82), 80),
            ("short", -1, 110, (120, 122, 115, 121), 120),
        )
        for direction, sign, stop, gap_bar, mark in cases:
            bars = self._execution_bars([(100, 101, 99, 100), gap_bar])
            for rate in (0.01, -0.01):
                for offset, should_apply in ((0, True), (1, False)):
                    with self.subTest(direction=direction, rate=rate, offset=offset):
                        result = strategy.simulate(
                            bars,
                            [self._signal(sign, stop)],
                            5,
                            direction,
                            [{"ts": bars[2].t + offset, "rate": rate, "mark": mark}],
                            _small_parameters(),
                            self._zero_cost_execution(),
                        )

                        trade = result["trades"][0]
                        expected_funding = -sign * 25 * mark * rate if should_apply else 0
                        expected_net = -500 + expected_funding
                        self.assertEqual(trade["entry_at"], bars[1].t)
                        self.assertEqual(trade["quantity"], 25)
                        self.assertEqual(trade["reason"], "stop_gap")
                        self.assertEqual(trade["exit_at"], bars[2].t)
                        self.assertEqual(trade["exit"], gap_bar[0])
                        self.assertAlmostEqual(trade["funding"], expected_funding)
                        self.assertAlmostEqual(trade["net_pnl"], expected_net)
                        self.assertAlmostEqual(result["metrics"]["funding"], expected_funding)
                        self.assertAlmostEqual(result["metrics"]["closed_net_pnl"], expected_net)
                        self.assertAlmostEqual(
                            result["metrics"]["marked_equity"],
                            100000 + expected_net,
                        )

                        funding_events = [
                            (index, event)
                            for index, event in enumerate(result["ledger"])
                            if event["kind"] == "funding"
                        ]
                        if should_apply:
                            self.assertEqual(len(funding_events), 1)
                            funding_index, funding_event = funding_events[0]
                            exit_index = next(
                                index
                                for index, event in enumerate(result["ledger"])
                                if event["kind"] == "exit"
                            )
                            self.assertEqual(funding_event["at"], bars[2].t)
                            self.assertAlmostEqual(funding_event["amount"], expected_funding)
                            self.assertLess(funding_index, exit_index)
                        else:
                            self.assertEqual(funding_events, [])

    def test_maximum_hold_exits_at_the_open_after_fifteen_minutes(self) -> None:
        bars = self._execution_bars(
            [
                (100, 101, 99, 100),
                (100, 101, 99, 100),
                (100, 101, 99, 100),
                (100, 101, 49, 50),
            ]
        )
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(max_hold_minutes=15),
            self._zero_cost_execution(),
        )

        trade = result["trades"][0]
        self.assertEqual(trade["reason"], "time_exit")
        self.assertEqual(trade["entry_index"], 1)
        self.assertEqual(trade["exit_index"], 4)
        self.assertEqual(trade["exit"], bars[4].open)

    def test_short_mirror_stops_at_the_protective_level(self) -> None:
        bars = self._execution_bars([(100, 111, 79, 100)])
        result = strategy.simulate(
            bars,
            [self._signal(-1)],
            5,
            "short",
            [],
            _small_parameters(),
            self._zero_cost_execution(),
        )

        trade = result["trades"][0]
        self.assertEqual(trade["reason"], "ambiguous_stop_first")
        self.assertEqual(trade["exit"], 110)

    def test_fee_debits_match_entry_and_exit_notional(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 121, 99, 120)])
        execution = strategy.Execution(fee_bps=10, slip_bps=0)
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            execution,
        )

        trade = result["trades"][0]
        expected_entry_fee = trade["entry"] * trade["quantity"] * 0.001
        expected_exit_fee = trade["exit"] * trade["quantity"] * 0.001
        self.assertAlmostEqual(trade["entry_fee"], expected_entry_fee)
        self.assertAlmostEqual(trade["exit_fee"], expected_exit_fee)
        self.assertAlmostEqual(result["metrics"]["fees"], expected_entry_fee + expected_exit_fee)
        self.assertAlmostEqual(
            trade["net_pnl"],
            trade["gross_pnl"] - expected_entry_fee - expected_exit_fee,
        )

    def test_funding_applies_to_carried_position_and_signed_direction(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 101, 99, 100)])
        funding = [{"ts": bars[2].t, "rate": 0.01, "mark": 100.0}]
        p = _small_parameters()
        long_result = strategy.simulate(
            bars, [self._signal(1, 90)], 5, "long", funding, p, self._zero_cost_execution()
        )
        short_result = strategy.simulate(
            bars, [self._signal(-1, 110)], 5, "short", funding, p, self._zero_cost_execution()
        )

        long_quantity = long_result["open_position"]["quantity"]
        short_quantity = short_result["open_position"]["quantity"]
        self.assertAlmostEqual(long_result["metrics"]["funding"], -long_quantity)
        self.assertAlmostEqual(short_result["metrics"]["funding"], short_quantity)

    def test_funding_buffer_increases_debits_and_reduces_credits(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 101, 99, 100)])
        p = _small_parameters()
        execution = self._zero_cost_execution(funding_mark_buffer_fraction=0.01)
        long_result = strategy.simulate(
            bars,
            [self._signal(1, 90)],
            5,
            "long",
            [{"ts": bars[2].t, "rate": 0.01, "mark": 100.0}],
            p,
            execution,
        )
        short_result = strategy.simulate(
            bars,
            [self._signal(-1, 110)],
            5,
            "short",
            [{"ts": bars[2].t, "rate": 0.01, "mark": 100.0}],
            p,
            execution,
        )

        long_quantity = long_result["open_position"]["quantity"]
        short_quantity = short_result["open_position"]["quantity"]
        self.assertAlmostEqual(long_result["metrics"]["funding"], -1.01 * long_quantity)
        self.assertAlmostEqual(short_result["metrics"]["funding"], 0.99 * short_quantity)

    def test_funding_at_entry_open_is_not_charged_to_new_position(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100)])
        funding = [{"ts": bars[1].t, "rate": 0.01, "mark": 100.0}]
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            funding,
            _small_parameters(),
            self._zero_cost_execution(),
        )

        self.assertEqual(result["metrics"]["funding"], 0)
        self.assertFalse(any(event["kind"] == "funding" for event in result["ledger"]))

    def test_intrabar_ambiguous_funding_charges_debit_and_omits_credit(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 121, 99, 120)])
        p = _small_parameters()
        event_ts = bars[2].t + STEP // 2
        debit = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [{"ts": event_ts, "rate": 0.01, "mark": 100.0}],
            p,
            self._zero_cost_execution(),
        )
        credit = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [{"ts": event_ts, "rate": -0.01, "mark": 100.0}],
            p,
            self._zero_cost_execution(),
        )

        self.assertLess(debit["metrics"]["funding"], 0)
        self.assertEqual(credit["metrics"]["funding"], 0)
        debit_event = next(event for event in debit["ledger"] if event["kind"] == "funding")
        credit_event = next(event for event in credit["ledger"] if event["kind"] == "funding")
        self.assertTrue(debit_event["uncertain_exit_order"])
        self.assertTrue(credit_event["uncertain_exit_order"])

    def test_sizing_respects_risk_notional_quantity_and_step_limits(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 101, 99, 100)])
        execution = strategy.Execution()
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            execution,
        )

        position = result["open_position"]
        self.assertLessEqual(position["initial_risk"], execution.initial_capital * execution.risk_fraction)
        self.assertLessEqual(
            position["entry"] * position["quantity"] * (1 + execution.fee_bps / 10_000),
            execution.initial_capital * execution.max_notional_fraction,
        )
        self.assertLessEqual(position["quantity"], execution.max_quantity)
        self.assertGreaterEqual(position["quantity"], execution.min_quantity)
        self.assertGreaterEqual(position["entry"] * position["quantity"], execution.min_notional)
        self.assertAlmostEqual(position["quantity"] / execution.quantity_step, round(position["quantity"] / execution.quantity_step))

    def test_exchange_minimum_rejection_is_reported_without_a_fill(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100)])
        execution = strategy.Execution(initial_capital=100, risk_fraction=1e-6)
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            execution,
        )

        self.assertEqual(result["trades"], [])
        self.assertIsNone(result["open_position"])
        self.assertEqual(result["metrics"]["counts"]["venue_size_rejected"], 1)

    def test_only_one_position_can_be_open_and_direction_filter_is_execution_only(self) -> None:
        bars = self._execution_bars(
            [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)]
        )
        p = _small_parameters()
        signals, _ = strategy.detect(bars, 5, "reclaim", p)
        hand_signals = [self._signal(1), strategy.Signal(1, -1, 110, 1, "fixture")]
        result = strategy.simulate(
            bars,
            hand_signals,
            5,
            "long",
            [],
            p,
            self._zero_cost_execution(),
        )

        self.assertIsInstance(signals, list)
        self.assertEqual(result["metrics"]["counts"]["direction_excluded"], 1)
        self.assertEqual(result["metrics"]["counts"].get("position_concurrency", 0), 0)
        # The second signal is short and is filtered before position concurrency.
        both_result = strategy.simulate(
            bars,
            hand_signals,
            5,
            "both",
            [],
            p,
            self._zero_cost_execution(),
        )
        self.assertEqual(both_result["metrics"]["counts"]["position_concurrency"], 1)

    def test_censored_open_position_is_marked_with_entry_and_exit_costs(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100), (100, 111, 99, 110)])
        execution = strategy.Execution(fee_bps=10, slip_bps=0)
        result = strategy.simulate(
            bars,
            [self._signal()],
            5,
            "long",
            [],
            _small_parameters(),
            execution,
        )

        position = result["open_position"]
        last_close = bars[-1].close
        expected = (
            execution.initial_capital
            - position["entry_fee"]
            + position["quantity"] * (last_close - position["entry"])
            - last_close * position["quantity"] * execution.fee_bps / 10_000
        )
        self.assertEqual(result["trades"], [])
        self.assertAlmostEqual(result["metrics"]["marked_equity"], expected)
        self.assertEqual(result["metrics"]["counts"]["open_at_cutoff"], 1)
        self.assertEqual(result["equity"][-1]["quantity"], position["quantity"])

    def test_malformed_funding_and_invalid_candles_are_rejected(self) -> None:
        bars = self._execution_bars([(100, 101, 99, 100)])
        with self.assertRaises(ValueError):
            strategy.simulate(
                bars,
                [self._signal()],
                5,
                "long",
                [{"ts": bars[0].t, "rate": math.nan, "mark": 100}],
                _small_parameters(),
                self._zero_cost_execution(),
            )
        with self.assertRaises(ValueError):
            strategy.validate_bars([strategy.Candle(0, 100, 98, 99, 100, 1)], 5)


class RawDataContractTests(unittest.TestCase):
    @staticmethod
    def _fixture_rows(
        *, duplicate_at: int | None = None, non_finite_at: int | None = None
    ) -> list[tuple[int, float, float, float, float, float]]:
        count = 31 * 24 * 12
        rows: list[tuple[int, float, float, float, float, float]] = []
        for index in range(count):
            timestamp = data.START_MS + index * data.INTERVAL_MS
            if duplicate_at == index:
                timestamp = data.START_MS + (index - 1) * data.INTERVAL_MS
            high = math.nan if index == non_finite_at else 101.0
            rows.append((timestamp, 100.0, high, 99.0, 100.0, 1.0))
        return rows

    def _write_fixture(
        self,
        root: Path,
        *,
        duplicate_at: int | None = None,
        non_finite_at: int | None = None,
        header: bool = False,
    ) -> None:
        root.mkdir(parents=True, exist_ok=True)
        month = data._Month(2022, 1)
        content = io.StringIO(newline="")
        writer = csv.writer(content)
        if header:
            writer.writerow(["open_time", "open", "high", "low", "close", "volume"])
        writer.writerows(
            self._fixture_rows(duplicate_at=duplicate_at, non_finite_at=non_finite_at)
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{month.stem}.csv", content.getvalue().encode("utf-8"))
        archive_bytes = output.getvalue()
        archive_hash = hashlib.sha256(archive_bytes).hexdigest()
        checksum = f"{archive_hash}  {month.filename}\n".encode("ascii")
        checksum_hash = hashlib.sha256(checksum).hexdigest()
        (root / month.filename).write_bytes(archive_bytes)
        (root / (month.filename + ".CHECKSUM")).write_bytes(checksum)
        manifest = {
            "schema_version": "btc_liquidity_raw_v1",
            "symbol": data.SYMBOL,
            "venue": "Binance USD-M perpetual",
            "interval": data.INTERVAL,
            "requested_start_ms": data.START_MS,
            "requested_end_exclusive_ms": data.END_EXCLUSIVE_MS,
            "monthly_archives": {
                month.stem: {
                    "archive": {
                        "source_url": month.source_url,
                        "download_utc": "2026-10-23T00:00:00Z",
                        "sha256": archive_hash,
                        "bytes": len(archive_bytes),
                    },
                    "checksum": {
                        "source_url": month.checksum_url,
                        "download_utc": "2026-10-23T00:00:00Z",
                        "sha256": checksum_hash,
                        "bytes": len(checksum),
                    },
                }
            },
            "funding_pages": [],
            "sources": {},
        }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def _fixture_window(self):
        expected_rows = 31 * 24 * 12
        end = data.START_MS + expected_rows * data.INTERVAL_MS
        return (
            mock.patch.object(data, "END_EXCLUSIVE_MS", end),
            mock.patch.object(data, "_months", return_value=[data._Month(2022, 1)]),
        )

    def _write_funding_contract(
        self,
        root: Path,
        timestamps: list[int],
        api_marks: list[float | None],
        mark_rows: list[tuple[int, float, float, float, float]] | None = None,
        daily_mark_rows: list[tuple[int, float, float, float, float]] | None = None,
    ) -> tuple[list[dict[str, int | float]], dict[str, object]]:
        self.assertEqual(len(timestamps), len(api_marks))
        mark_rows = mark_rows or []
        mark_by_time = {row[0]: row[1] for row in mark_rows}
        page = [
            {
                "symbol": data.SYMBOL,
                "fundingTime": timestamp,
                "fundingRate": "0.0001",
                "markPrice": "" if mark is None else str(mark),
            }
            for timestamp, mark in zip(timestamps, api_marks)
        ]
        page_bytes = (json.dumps(page, separators=(",", ":")) + "\n").encode("utf-8")
        start = data.START_MS
        page_path = root / "funding_pages" / f"funding-0000-{start}.json"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_bytes(page_bytes)
        page_record = {
            "page_index": 0,
            "request_start_ms": start,
            "request_end_ms": data.FUNDING_END_MS,
            "source_url": data._funding_page_url(start),
            "download_utc": "2026-10-23T00:00:00Z",
            "sha256": hashlib.sha256(page_bytes).hexdigest(),
            "bytes": len(page_bytes),
        }

        mark_months: dict[str, data._Month] = {}
        for timestamp, mark in zip(timestamps, api_marks):
            if mark is None:
                candle_t = timestamp // data.INTERVAL_MS * data.INTERVAL_MS
                month_date = datetime.fromtimestamp(candle_t / 1000, timezone.utc)
                month = data._Month(month_date.year, month_date.month)
                mark_months[month.stem] = month

        archive_records: dict[str, dict] = {}
        grouped_rows: dict[str, list[tuple[int, float, float, float, float]]] = {
            stem: [] for stem in mark_months
        }
        for row in mark_rows:
            row_date = datetime.fromtimestamp(row[0] / 1000, timezone.utc)
            row_month = data._Month(row_date.year, row_date.month)
            if row_month.stem in grouped_rows:
                grouped_rows[row_month.stem].append(row)
        for stem, month in mark_months.items():
            rows = grouped_rows[stem]
            csv_text = io.StringIO(newline="")
            csv.writer(csv_text).writerows(rows)
            archive_bytes_io = io.BytesIO()
            with zipfile.ZipFile(archive_bytes_io, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(month.filename.removesuffix(".zip") + ".csv", csv_text.getvalue())
            archive_bytes = archive_bytes_io.getvalue()
            checksum = f"{hashlib.sha256(archive_bytes).hexdigest()}  {month.filename}\n".encode("ascii")
            checksum_digest = hashlib.sha256(checksum).hexdigest()
            directory = root / data.MARK_PRICE_SUBDIR
            directory.mkdir(parents=True, exist_ok=True)
            (directory / month.filename).write_bytes(archive_bytes)
            (directory / (month.filename + ".CHECKSUM")).write_bytes(checksum)
            archive_records[stem] = {
                "archive": {
                    "source_url": month.mark_price_source_url,
                    "download_utc": "2026-10-23T00:00:00Z",
                    "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                    "bytes": len(archive_bytes),
                },
                "checksum": {
                    "source_url": month.mark_price_checksum_url,
                    "download_utc": "2026-10-23T00:00:00Z",
                    "sha256": checksum_digest,
                    "bytes": len(checksum),
                },
            }

        missing_monthly: dict[str, set[int]] = {}
        for timestamp, api_mark in zip(timestamps, api_marks):
            if api_mark is None:
                candle_t = timestamp // data.INTERVAL_MS * data.INTERVAL_MS
                if candle_t not in mark_by_time:
                    date_value = datetime.fromtimestamp(candle_t / 1000, timezone.utc).strftime("%Y-%m-%d")
                    missing_monthly.setdefault(date_value, set()).add(candle_t)
        daily_open_by_time: dict[int, float] = {}
        daily_archive_records: dict[str, dict] = {}
        supplied_daily_by_time = {row[0]: row for row in daily_mark_rows or []}
        if daily_mark_rows is not None:
            for date_value in sorted(missing_monthly):
                daily = data._daily_mark_archive(date_value)
                day_rows = [
                    supplied_daily_by_time.get(t, (t, 100.0, 101.0, 99.0, 100.0))
                    for t in range(daily.first_ms, daily.end_exclusive_ms, data.INTERVAL_MS)
                ]
                daily_open_by_time.update({row[0]: row[1] for row in day_rows})
                csv_text = io.StringIO(newline="")
                csv.writer(csv_text).writerows(day_rows)
                archive_bytes_io = io.BytesIO()
                with zipfile.ZipFile(archive_bytes_io, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(daily.filename.removesuffix(".zip") + ".csv", csv_text.getvalue())
                archive_bytes = archive_bytes_io.getvalue()
                checksum = f"{hashlib.sha256(archive_bytes).hexdigest()}  {daily.filename}\n".encode("ascii")
                checksum_digest = hashlib.sha256(checksum).hexdigest()
                directory = root / data.MARK_PRICE_SUBDIR / "daily"
                directory.mkdir(parents=True, exist_ok=True)
                (directory / daily.filename).write_bytes(archive_bytes)
                (directory / (daily.filename + ".CHECKSUM")).write_bytes(checksum)
                daily_archive_records[date_value] = {
                    "archive": {
                        "source_url": daily.source_url,
                        "download_utc": "2026-10-23T00:00:00Z",
                        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                        "bytes": len(archive_bytes),
                    },
                    "checksum": {
                        "source_url": daily.checksum_url,
                        "download_utc": "2026-10-23T00:00:00Z",
                        "sha256": checksum_digest,
                        "bytes": len(checksum),
                    },
                    "date": date_value,
                    "expected_rows": daily.expected_rows,
                    "start_ms": daily.first_ms,
                    "end_exclusive_ms": daily.end_exclusive_ms,
                }

        normalized: list[dict[str, int | float]] = []
        provenance_rows: list[dict[str, object]] = []
        for timestamp, api_mark in zip(timestamps, api_marks):
            if api_mark is not None:
                mark = float(api_mark)
                provenance_rows.append(
                    {
                        "funding_ts": timestamp,
                        "source": "api_mark",
                        "mark": mark,
                        "mark_candle_open_ts": None,
                        "archive_type": None,
                        "archive_id": None,
                    }
                )
            else:
                candle_t = timestamp // data.INTERVAL_MS * data.INTERVAL_MS
                month_date = datetime.fromtimestamp(candle_t / 1000, timezone.utc)
                month = data._Month(month_date.year, month_date.month)
                if candle_t in mark_by_time:
                    mark = mark_by_time[candle_t]
                    source, archive_type, archive_id = "mark_price_open_proxy", "monthly", month.stem
                else:
                    date_value = month_date.strftime("%Y-%m-%d")
                    mark = daily_open_by_time.get(candle_t, 999.0)
                    source, archive_type, archive_id = "mark_price_daily_open_repair", "daily", date_value
                provenance_rows.append(
                    {
                        "funding_ts": timestamp,
                        "source": source,
                        "mark": mark,
                        "mark_candle_open_ts": candle_t,
                        "archive_type": archive_type,
                        "archive_id": archive_id,
                    }
                )
            normalized.append({"ts": timestamp, "rate": 0.0001, "mark": mark})
        provenance: dict[str, object] = {
            "schema_version": "btc_liquidity_funding_mark_provenance_v1",
            "rows": provenance_rows,
            "summary": {
                "rows": len(provenance_rows),
                "api_mark_rows": sum(row["source"] == "api_mark" for row in provenance_rows),
                "proxy_mark_rows": sum(
                    row["source"] in {"mark_price_open_proxy", "mark_price_daily_open_repair"}
                    for row in provenance_rows
                ),
                "monthly_proxy_rows": sum(row["source"] == "mark_price_open_proxy" for row in provenance_rows),
                "daily_repair_rows": sum(
                    row["source"] == "mark_price_daily_open_repair" for row in provenance_rows
                ),
                "proxy_archive_months": sorted(
                    {row["archive_id"] for row in provenance_rows if row["archive_type"] == "monthly"}
                ),
                "daily_repair_dates": sorted(missing_monthly),
            },
        }
        repairs = []
        for date_value, target_times in sorted(missing_monthly.items()):
            if date_value not in daily_archive_records:
                continue
            daily = data._daily_mark_archive(date_value)
            month_date = datetime.fromtimestamp(daily.first_ms / 1000, timezone.utc)
            month = data._Month(month_date.year, month_date.month)
            monthly_record = archive_records[month.stem]
            daily_record = daily_archive_records[date_value]
            repaired_rows = [
                {
                    "funding_ts": row["funding_ts"],
                    "mark_candle_open_ts": row["mark_candle_open_ts"],
                    "mark": row["mark"],
                    "source": row["source"],
                }
                for row in provenance_rows
                if row["archive_type"] == "daily" and row["archive_id"] == date_value
            ]
            repairs.append(
                {
                    "date": date_value,
                    "missing_funding_timestamps": sorted(row["funding_ts"] for row in repaired_rows),
                    "missing_candle_open_timestamps": sorted(target_times),
                    "monthly_archive": {
                        "source_url": month.mark_price_source_url,
                        "sha256": monthly_record["archive"]["sha256"],
                        "bytes": monthly_record["archive"]["bytes"],
                        "checksum_url": month.mark_price_checksum_url,
                        "checksum_sha256": monthly_record["checksum"]["sha256"],
                    },
                    "daily_archive": {
                        "source_url": daily.source_url,
                        "sha256": daily_record["archive"]["sha256"],
                        "bytes": daily_record["archive"]["bytes"],
                        "checksum_url": daily.checksum_url,
                        "checksum_sha256": daily_record["checksum"]["sha256"],
                    },
                    "row_provenance": repaired_rows,
                }
            )
        repair_log = {
            "schema_version": "btc_liquidity_mark_price_gap_repairs_v1",
            "repairs": repairs,
            "summary": {
                "dates": [item["date"] for item in repairs],
                "repaired_funding_rows": sum(len(item["row_provenance"]) for item in repairs),
                "repaired_candle_open_rows": sum(
                    len(item["missing_candle_open_timestamps"]) for item in repairs
                ),
            },
        }
        provenance_bytes = (
            json.dumps(provenance, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        normalized_bytes = (json.dumps(normalized, indent=2) + "\n").encode("utf-8")
        coverage = data._funding_coverage(normalized, provenance_rows)
        coverage_bytes = (json.dumps(coverage, indent=2, sort_keys=True) + "\n").encode("utf-8")
        repairs_bytes = (json.dumps(repair_log, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (root / "funding_mark_provenance.json").write_bytes(provenance_bytes)
        (root / "normalized_funding.json").write_bytes(normalized_bytes)
        (root / "funding_coverage.json").write_bytes(coverage_bytes)
        (root / "mark_price_gap_repairs.json").write_bytes(repairs_bytes)
        manifest = {
            "schema_version": "btc_liquidity_raw_v1",
            "symbol": data.SYMBOL,
            "venue": "Binance USD-M perpetual",
            "interval": data.INTERVAL,
            "requested_start_ms": data.START_MS,
            "requested_end_exclusive_ms": data.END_EXCLUSIVE_MS,
            "monthly_archives": {},
            "mark_price_archives": archive_records,
            "mark_price_daily_archives": daily_archive_records,
            "funding_pages": [page_record],
            "sources": {
                "funding_mark_provenance": {
                    "source_url": "derived from exact funding pages and checksum-verified mark-price archives",
                    "download_utc": None,
                    "sha256": hashlib.sha256(provenance_bytes).hexdigest(),
                    "bytes": len(provenance_bytes),
                    "api_mark_rows": provenance["summary"]["api_mark_rows"],
                    "proxy_mark_rows": provenance["summary"]["proxy_mark_rows"],
                    "monthly_proxy_rows": provenance["summary"]["monthly_proxy_rows"],
                    "daily_repair_rows": provenance["summary"]["daily_repair_rows"],
                    "proxy_archive_months": provenance["summary"]["proxy_archive_months"],
                    "daily_repair_dates": provenance["summary"]["daily_repair_dates"],
                },
                "normalized_funding": {
                    "source_url": "derived from exact funding pages and funding mark provenance",
                    "download_utc": None,
                    "sha256": hashlib.sha256(normalized_bytes).hexdigest(),
                    "bytes": len(normalized_bytes),
                },
                "funding_coverage": {
                    "source_url": "derived from exact funding timestamps and mark provenance",
                    "download_utc": None,
                    "sha256": hashlib.sha256(coverage_bytes).hexdigest(),
                    "bytes": len(coverage_bytes),
                },
                "mark_price_gap_repairs": {
                    "source_url": "derived from exact missing monthly marks and verified daily mark-price opens",
                    "download_utc": None,
                    "sha256": hashlib.sha256(repairs_bytes).hexdigest(),
                    "bytes": len(repairs_bytes),
                    "dates": repair_log["summary"]["dates"],
                    "repaired_funding_rows": repair_log["summary"]["repaired_funding_rows"],
                },
            },
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return normalized, provenance

    def test_checksum_format_and_hash_verification_precede_csv_parse(self) -> None:
        month = data._Month(2022, 1)
        digest = "a" * 64
        self.assertEqual(
            data._checksum_digest(f"{digest}  {month.filename}\n".encode(), month.filename), digest
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._fixture_window()[0], self._fixture_window()[1]:
                self._write_fixture(root)
                archive_path = root / month.filename
                archive_path.write_bytes(archive_path.read_bytes() + b"tampered")
                with mock.patch.object(
                    data.zipfile, "ZipFile", side_effect=AssertionError("parsed before hash")
                ):
                    with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                        data.load_candles(root)

    def test_raw_audit_accepts_optional_header_and_records_manifest_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._fixture_window()[0], self._fixture_window()[1]:
                self._write_fixture(root, header=True)
                candles = data.load_candles(root)

            self.assertEqual(len(candles), 31 * 24 * 12)
            report = json.loads((root / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["rows"], 31 * 24 * 12)
            self.assertEqual(report["bounds"]["first_t"], data.START_MS)
            self.assertEqual(report["bounds"]["last_t"], data.START_MS + (31 * 24 * 12 - 1) * data.INTERVAL_MS)
            manifest_digest = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
            self.assertEqual(report["manifest_digest"], manifest_digest)

    def test_audit_reports_duplicate_and_gap_without_silent_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._fixture_window()[0], self._fixture_window()[1]:
                self._write_fixture(root, duplicate_at=100)
                with self.assertRaisesRegex(ValueError, "raw-data audit failed"):
                    data.audit(root)

            report = json.loads((root / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["duplicates"]["count"], 1)
            self.assertEqual(report["gaps"]["count"], 1)
            self.assertEqual(report["rows"], 31 * 24 * 12)

    def test_raw_audit_rejects_non_finite_candle_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._fixture_window()[0], self._fixture_window()[1]:
                self._write_fixture(root, non_finite_at=100)
                with self.assertRaisesRegex(ValueError, "invalid"):
                    data.audit(root)

            report = json.loads((root / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(any(example["reason"] == "non_finite_value" for example in report["invalid_rows"]["examples"]))

    def test_load_funding_matches_the_exact_page_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            start = data.START_MS
            end_exclusive = start + 24 * 60 * 60_000
            timestamps = [start, start + data.FUNDING_DEFAULT_INTERVAL_MS, start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS]
            with mock.patch.object(data, "END_EXCLUSIVE_MS", end_exclusive), mock.patch.object(
                data, "FUNDING_END_MS", end_exclusive - 1
            ):
                expected, _ = self._write_funding_contract(root, timestamps, [100.0] * 3)
                self.assertEqual(data.load_funding(root), expected)
                (root / "normalized_funding.json").write_text("[]", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "identity"):
                    data.load_funding(root)

    def test_missing_api_mark_uses_only_the_matching_mark_candle_open(self) -> None:
        start = data.START_MS
        timestamps = [start, start + data.FUNDING_DEFAULT_INTERVAL_MS + 1234, start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS]
        missing_candle_t = timestamps[1] // data.INTERVAL_MS * data.INTERVAL_MS
        mark_rows = [(missing_candle_t, 101.25, 999.0, 1.0, 777.0)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            end_exclusive = start + 24 * 60 * 60_000
            with mock.patch.object(data, "END_EXCLUSIVE_MS", end_exclusive), mock.patch.object(
                data, "FUNDING_END_MS", end_exclusive - 1
            ):
                expected, provenance = self._write_funding_contract(
                    root, timestamps, [100.0, None, 102.0], mark_rows
                )
                self.assertEqual(data.load_funding(root), expected)

            self.assertEqual(expected[0]["mark"], 100.0)
            self.assertEqual(expected[1]["mark"], 101.25)
            self.assertEqual(expected[2]["mark"], 102.0)
            self.assertEqual(provenance["summary"]["api_mark_rows"], 2)
            self.assertEqual(provenance["summary"]["proxy_mark_rows"], 1)
            self.assertEqual(provenance["rows"][1]["mark_candle_open_ts"], missing_candle_t)
            self.assertEqual(provenance["rows"][1]["source"], "mark_price_open_proxy")

    def test_missing_monthly_and_daily_candle_open_blocks_funding_load(self) -> None:
        start = int(datetime(2022, 7, 31, tzinfo=timezone.utc).timestamp() * 1000)
        timestamps = [
            start,
            start + data.FUNDING_DEFAULT_INTERVAL_MS,
            start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS,
        ]
        missing_candle_t = timestamps[1] // data.INTERVAL_MS * data.INTERVAL_MS
        monthly_neighbors = [
            (missing_candle_t - data.INTERVAL_MS, 100.0, 102.0, 99.0, 101.0),
            (missing_candle_t + data.INTERVAL_MS, 102.0, 104.0, 101.0, 103.0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            end_exclusive = start + 24 * 60 * 60_000
            with mock.patch.object(data, "START_MS", start), mock.patch.object(
                data, "END_EXCLUSIVE_MS", end_exclusive
            ), mock.patch.object(data, "FUNDING_END_MS", end_exclusive - 1):
                self._write_funding_contract(
                    root, timestamps, [100.0, None, 102.0], monthly_neighbors
                )
                with self.assertRaisesRegex(ValueError, "Required checksum-verified daily mark-price archive is missing"):
                    data.load_funding(root)

    def test_daily_mark_repair_uses_only_the_matching_open_and_records_provenance(self) -> None:
        start = int(datetime(2022, 7, 31, tzinfo=timezone.utc).timestamp() * 1000)
        timestamps = [
            start,
            start + data.FUNDING_DEFAULT_INTERVAL_MS + 1234,
            start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS,
        ]
        target_open = timestamps[1] // data.INTERVAL_MS * data.INTERVAL_MS
        monthly_neighbors = [
            (target_open - data.INTERVAL_MS, 100.0, 102.0, 99.0, 101.0),
            (target_open + data.INTERVAL_MS, 102.0, 104.0, 101.0, 103.0),
        ]
        # Deliberately extreme but valid H/L/C values prove the repair consumes
        # the daily candle's open only.
        daily_row = (target_open, 101.25, 999.0, 1.0, 777.0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            end_exclusive = start + 24 * 60 * 60_000
            with mock.patch.object(data, "START_MS", start), mock.patch.object(
                data, "END_EXCLUSIVE_MS", end_exclusive
            ), mock.patch.object(data, "FUNDING_END_MS", end_exclusive - 1):
                expected, provenance = self._write_funding_contract(
                    root,
                    timestamps,
                    [100.0, None, 102.0],
                    monthly_neighbors,
                    [daily_row],
                )
                self.assertEqual(data.load_funding(root), expected)

            repaired = provenance["rows"][1]
            self.assertEqual(expected[1]["mark"], 101.25)
            self.assertEqual(repaired["source"], "mark_price_daily_open_repair")
            self.assertEqual(repaired["mark_candle_open_ts"], target_open)
            self.assertEqual(repaired["archive_id"], "2022-07-31")
            repair_log = json.loads(
                (root / "mark_price_gap_repairs.json").read_text(encoding="utf-8")
            )
            repair = repair_log["repairs"][0]
            self.assertEqual(repair["date"], "2022-07-31")
            self.assertEqual(repair["missing_funding_timestamps"], [timestamps[1]])
            self.assertEqual(repair["missing_candle_open_timestamps"], [target_open])
            self.assertEqual(repair["row_provenance"][0]["mark"], 101.25)
            self.assertTrue(repair["monthly_archive"]["sha256"])
            self.assertTrue(repair["daily_archive"]["sha256"])

    def test_tampered_daily_mark_archive_is_rejected_before_join(self) -> None:
        start = int(datetime(2022, 7, 31, tzinfo=timezone.utc).timestamp() * 1000)
        timestamps = [
            start,
            start + data.FUNDING_DEFAULT_INTERVAL_MS,
            start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS,
        ]
        target_open = timestamps[1] // data.INTERVAL_MS * data.INTERVAL_MS
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            end_exclusive = start + 24 * 60 * 60_000
            with mock.patch.object(data, "START_MS", start), mock.patch.object(
                data, "END_EXCLUSIVE_MS", end_exclusive
            ), mock.patch.object(data, "FUNDING_END_MS", end_exclusive - 1):
                self._write_funding_contract(
                    root,
                    timestamps,
                    [100.0, None, 102.0],
                    [],
                    [(target_open, 101.25, 102.0, 100.0, 101.5)],
                )
                archive = data._daily_mark_archive("2022-07-31")
                archive_path = root / data.MARK_PRICE_SUBDIR / "daily" / archive.filename
                archive_path.write_bytes(archive_path.read_bytes() + b"tampered")
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch for cached daily mark-price archive"):
                    data.load_funding(root)

    def test_funding_download_paginates_and_preserves_pages_before_mark_join(self) -> None:
        start = data.START_MS
        step = data.FUNDING_DEFAULT_INTERVAL_MS
        first_times = [start + index * step for index in range(1000)]
        second_times = [start + 1000 * step, start + 1001 * step]
        end_exclusive = start + 1002 * step
        first_page = [
            {
                "symbol": data.SYMBOL,
                "fundingTime": timestamp,
                "fundingRate": "0.0001",
                "markPrice": "" if index == 0 else "100.0",
            }
            for index, timestamp in enumerate(first_times)
        ]
        second_page = [
            {"symbol": data.SYMBOL, "fundingTime": timestamp, "fundingRate": "0.0001", "markPrice": "100.0"}
            for timestamp in second_times
        ]
        payloads = [
            (json.dumps(first_page, separators=(",", ":")).encode("utf-8"), "2026-10-23T00:00:00Z"),
            (json.dumps(second_page, separators=(",", ":")).encode("utf-8"), "2026-10-23T00:00:01Z"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(data, "END_EXCLUSIVE_MS", end_exclusive), mock.patch.object(
                data, "FUNDING_END_MS", end_exclusive - 1
            ), mock.patch.object(data, "_fetch_bytes", side_effect=payloads) as fetch:
                manifest = data._load_manifest(root)
                raw_rows = data._download_funding_pages(root, manifest)

            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(len(raw_rows), 1002)
            self.assertIsNone(raw_rows[0]["api_mark"])
            self.assertEqual(len(manifest["funding_pages"]), 2)
            first_record = manifest["funding_pages"][0]
            first_path = root / "funding_pages" / f"funding-0000-{start}.json"
            self.assertEqual(first_record["sha256"], hashlib.sha256(first_path.read_bytes()).hexdigest())

    def test_tampered_funding_mark_provenance_is_rejected(self) -> None:
        start = data.START_MS
        timestamps = [start, start + data.FUNDING_DEFAULT_INTERVAL_MS, start + 2 * data.FUNDING_DEFAULT_INTERVAL_MS]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            end_exclusive = start + 24 * 60 * 60_000
            with mock.patch.object(data, "END_EXCLUSIVE_MS", end_exclusive), mock.patch.object(
                data, "FUNDING_END_MS", end_exclusive - 1
            ):
                self._write_funding_contract(root, timestamps, [100.0] * 3)
                (root / "funding_mark_provenance.json").write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "identity"):
                    data.load_funding(root)

    def test_funding_coverage_reports_a_missing_default_interval(self) -> None:
        start = data.START_MS
        covered = [
            {"ts": start, "rate": 0.0, "mark": 100.0},
            {"ts": start + data.FUNDING_DEFAULT_INTERVAL_MS, "rate": 0.0, "mark": 100.0},
            {"ts": start + 3 * data.FUNDING_DEFAULT_INTERVAL_MS, "rate": 0.0, "mark": 100.0},
        ]
        provenance = [
            {"funding_ts": row["ts"], "source": "api_mark", "mark": row["mark"]}
            for row in covered
        ]
        end = start + 4 * data.FUNDING_DEFAULT_INTERVAL_MS

        with mock.patch.object(data, "END_EXCLUSIVE_MS", end):
            report = data._funding_coverage(covered, provenance)

        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["max_gap_ms"], 2 * data.FUNDING_DEFAULT_INTERVAL_MS)
        self.assertEqual(len(report["gaps_over_8h"]), 1)


class ResampleContractTests(unittest.TestCase):
    def test_resample_uses_complete_aligned_triplets_and_ohlcv_aggregation(self) -> None:
        bars = [
            strategy.Candle(0, 100, 103, 98, 101, 1),
            strategy.Candle(STEP, 101, 105, 99, 104, 2),
            strategy.Candle(2 * STEP, 104, 106, 100, 102, 3),
            strategy.Candle(3 * STEP, 102, 104, 101, 103, 4),
            strategy.Candle(4 * STEP, 103, 107, 102, 106, 5),
            strategy.Candle(5 * STEP, 106, 108, 104, 105, 6),
        ]

        result = data.resample_15m(bars)

        self.assertEqual(
            result,
            [
                strategy.Candle(0, 100, 106, 98, 102, 6),
                strategy.Candle(3 * STEP, 102, 108, 101, 105, 15),
            ],
        )

    def test_resample_drops_only_partial_edge_buckets(self) -> None:
        bars = [
            strategy.Candle(STEP, 100, 102, 99, 101, 1),
            strategy.Candle(2 * STEP, 101, 103, 100, 102, 1),
            strategy.Candle(3 * STEP, 102, 104, 101, 103, 1),
            strategy.Candle(4 * STEP, 103, 105, 102, 104, 1),
            strategy.Candle(5 * STEP, 104, 106, 103, 105, 1),
        ]

        result = data.resample_15m(bars)

        self.assertEqual(result, [strategy.Candle(3 * STEP, 102, 106, 101, 105, 3)])

    def test_resample_rejects_a_missing_bar_and_a_non_utc_boundary(self) -> None:
        missing = [
            strategy.Candle(0, 100, 101, 99, 100, 1),
            strategy.Candle(2 * STEP, 100, 101, 99, 100, 1),
        ]
        misaligned = [strategy.Candle(1, 100, 101, 99, 100, 1)]
        with self.assertRaisesRegex(ValueError, "missing"):
            data.resample_15m(missing)
        with self.assertRaisesRegex(ValueError, "Misaligned|aligned"):
            data.resample_15m(misaligned)


class CampaignSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        protocol_path = (
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "strategy-development"
            / "btc-liquidity-20261023"
            / "protocol.json"
        )
        cls.protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

    def _candidate(self) -> dict:
        return {
            "base": {
                "2022": {"net_return_pct": -2.0, "closed_trades": 25},
                "2023": {"net_return_pct": 1.0, "closed_trades": 26},
                "2024": {"net_return_pct": 2.0, "closed_trades": 28},
                "2025": {"net_return_pct": 1.0, "closed_trades": 30},
                "2026": {"net_return_pct": 1.0, "closed_trades": 70},
            },
            "stress": {"2025": {"net_return_pct": -0.2}, "2026": {"net_return_pct": 0.3}},
            "combined": {
                "profit_factor": 1.05,
                "max_fold_drawdown_pct": 10.0,
                "worst_fold_return_pct": -2.0,
                "mean_fold_return_pct": 0.4,
            },
        }

    def test_screen_accepts_inclusive_thresholds_and_reports_each_failed_gate(self) -> None:
        candidate = self._candidate()
        self.assertEqual(campaign.qualifies(candidate, self.protocol), (True, []))

        for year in ("2025", "2026"):
            with self.subTest(nonpositive_year=year):
                failed_year = self._candidate()
                failed_year["base"][year]["net_return_pct"] = 0.0
                qualified_year, year_failures = campaign.qualifies(failed_year, self.protocol)
                self.assertFalse(qualified_year)
                self.assertTrue(any(f"{year}: nonpositive" in failure for failure in year_failures))

        candidate["base"]["2025"]["net_return_pct"] = 0.0
        candidate["base"]["2026"]["closed_trades"] = 29
        candidate["combined"]["profit_factor"] = 1.049
        candidate["combined"]["max_fold_drawdown_pct"] = 10.01
        candidate["stress"]["2026"]["net_return_pct"] = -0.2
        qualified, failures = campaign.qualifies(candidate, self.protocol)

        self.assertFalse(qualified)
        self.assertTrue(any("2025: nonpositive" in failure for failure in failures))
        self.assertTrue(any("2026: insufficient" in failure for failure in failures))
        self.assertTrue(any("profit factor" in failure for failure in failures))
        self.assertTrue(any("drawdown" in failure for failure in failures))
        self.assertTrue(any("stress return" in failure for failure in failures))

    def test_rank_prioritizes_qualification_then_worst_then_mean_fold(self) -> None:
        rows = [
            {"qualified": False, "combined": {"worst_fold_return_pct": 50, "mean_fold_return_pct": 60}},
            {"qualified": True, "combined": {"worst_fold_return_pct": 1, "mean_fold_return_pct": 2}},
            {"qualified": True, "combined": {"worst_fold_return_pct": 2, "mean_fold_return_pct": -100}},
            {"qualified": True, "combined": {"worst_fold_return_pct": 2, "mean_fold_return_pct": 3}},
        ]

        self.assertEqual(sorted(rows, key=campaign.rank_key, reverse=True), [rows[3], rows[2], rows[1], rows[0]])

    def test_fold_aggregate_uses_profit_factor_and_worst_annual_drawdown(self) -> None:
        aggregate = campaign.combined(
            [
                {
                    "gross_profit": 100.0,
                    "gross_loss": 50.0,
                    "net_return_pct": 5.0,
                    "closed_trades": 10,
                    "max_drawdown_pct": 4.0,
                    "adverse_drawdown_pct": 8.0,
                    "fees": 20.0,
                    "funding": 3.0,
                },
                {
                    "gross_profit": 80.0,
                    "gross_loss": 40.0,
                    "net_return_pct": -2.0,
                    "closed_trades": 20,
                    "max_drawdown_pct": 10.0,
                    "adverse_drawdown_pct": 12.0,
                    "fees": 30.0,
                    "funding": -4.0,
                },
            ]
        )

        self.assertEqual(aggregate["sum_fold_return_pct"], 3.0)
        self.assertEqual(aggregate["mean_fold_return_pct"], 1.5)
        self.assertEqual(aggregate["worst_fold_return_pct"], -2.0)
        self.assertEqual(aggregate["closed_trades"], 30)
        self.assertAlmostEqual(aggregate["profit_factor"], 2.0)
        self.assertEqual(aggregate["max_fold_drawdown_pct"], 10.0)
        self.assertEqual(aggregate["max_fold_adverse_drawdown_pct"], 12.0)
        self.assertEqual(aggregate["fees"], 50.0)
        self.assertEqual(aggregate["funding"], -1.0)


if __name__ == "__main__":
    unittest.main()
