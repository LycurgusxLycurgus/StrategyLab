"""Independent contract tests for the fixed BTC SMC-inspired detectors."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from app import btc_liquidity as broker
from app import btc_smc as strategy
from app import btc_smc_campaign as campaign


STEP_5M = 5 * 60_000
NY = ZoneInfo("America/New_York")


def _candle(index: int, row: tuple[float, float, float, float], *, minutes: int = 5,
            start: int = 0) -> broker.Candle:
    return broker.Candle(start + index * minutes * 60_000, *row)


def _bars(rows: list[tuple[float, float, float, float]], *, minutes: int = 5,
          start: int = 0) -> list[broker.Candle]:
    return [_candle(i, row, minutes=minutes, start=start) for i, row in enumerate(rows)]


def _normal(price: float = 100.0) -> tuple[float, float, float, float]:
    return price, price + 1, price - 1, price


def _small_parameters(**overrides: float | int) -> strategy.SmcParameters:
    values: dict[str, float | int] = {
        "atr_minutes": 10,
        "pivot_span": 2,
        "block_search_bars": 12,
        "setup_minutes": 60,
        "displacement_atr": 0.5,
        "stop_buffer_atr": 0.1,
        "silver_expiry_minutes": 30,
        "turtle_lookback": 20,
        "turtle_min_age": 4,
    }
    values.update(overrides)
    return strategy.SmcParameters(**values)


def _bos_bars(*, short: bool = False, retest: bool = True,
              minutes: int = 5) -> list[broker.Candle]:
    rows = [_normal() for _ in range(4)]
    rows += [
        (100, 105, 99, 100),  # strict pivot high, confirmed two bars later
        (101, 104, 98, 100),  # earlier opposing candle
        (101, 104, 99, 100),  # latest opposing candle; selected block
        (104, 109, 103, 108),  # bullish BOS; also crosses the new block
    ]
    if retest:
        rows.append((105, 107, 103, 106))
    if short:
        rows = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in rows]
    return _bars(rows, minutes=minutes)


def _turtle_bars(*, short: bool = False, tied_latest: bool = False,
                 reclaim_close: float | None = None,
                 minutes: int = 5) -> list[broker.Candle]:
    rows = [_normal() for _ in range(20)]
    rows[16] = (100, 101, 90, 100)  # most recent channel low, exactly four bars old
    if tied_latest:
        rows[18] = (100, 101, 90, 100)  # latest tie is only two bars old
    rows += [(89, 90, 87, 88)]  # close below the prior 20-bar low; no same-bar reclaim
    rows += [(90, 92, 89, 91 if reclaim_close is None else reclaim_close)]
    if short:
        rows = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in rows]
    return _bars(rows, minutes=minutes)


def _local_ms(date: tuple[int, int, int], hour: int, minute: int) -> int:
    local = datetime(*date, hour, minute, tzinfo=NY)
    return int(local.astimezone(timezone.utc).timestamp() * 1000)


def _silver_bars(*, date: tuple[int, int, int] = (2026, 1, 15),
                 start_hour: int = 7,
                 sweep_at: str = "10:00", confirm_at: str | None = "10:05",
                 retest_at: str | None = "10:10", direction: int = 1,
                 dual_sweep: bool = False,
                 extra_second_setup: bool = False) -> list[broker.Candle]:
    start = _local_ms(date, start_hour, 0)
    stop = _local_ms(date, 11, 0)
    count = (stop - start) // STEP_5M + 1
    rows = [_normal() for _ in range(count)]
    for i in range(count):
        local = datetime.fromtimestamp((start + i * STEP_5M) / 1000, timezone.utc).astimezone(NY)
        if local.hour == 9:
            rows[i] = (100, 102, 98, 100)

    def index_at(clock: str) -> int:
        hour, minute = (int(part) for part in clock.split(":"))
        timestamp = _local_ms(date, hour, minute)
        return (timestamp - start) // STEP_5M

    if dual_sweep:
        rows[index_at(sweep_at)] = (100, 103, 97, 100)
    elif direction == 1:
        rows[index_at(sweep_at)] = (100, 101, 97, 99)
        if confirm_at is not None:
            confirm_i = index_at(confirm_at)
            previous_two = rows[confirm_i - 2][1]
            low = max(104.0, previous_two + 1)
            rows[confirm_i] = (low, low + 3, low, low + 2)
        if retest_at is not None:
            rows[index_at(retest_at)] = (104, 106, 103, 105)
    else:
        rows[index_at(sweep_at)] = (100, 103, 99, 101)
        if confirm_at is not None:
            confirm_i = index_at(confirm_at)
            previous_two = rows[confirm_i - 2][2]
            high = min(96.0, previous_two - 1)
            rows[confirm_i] = (high, high, high - 3, high - 2)
        if retest_at is not None:
            rows[index_at(retest_at)] = (96, 99, 94, 95)

    if extra_second_setup and direction == 1:
        # A second complete pattern follows the first eligible signal. The day
        # allowance is already consumed, so these candles cannot emit again.
        rows[index_at("10:15")] = (100, 101, 97, 99)
        rows[index_at("10:20")] = (109, 112, 108, 111)
        rows[index_at("10:25")] = (109, 112, 108, 111)
    if confirm_at is not None and retest_at is not None:
        confirm_hour, confirm_minute = (int(part) for part in confirm_at.split(":"))
        retest_hour, retest_minute = (int(part) for part in retest_at.split(":"))
        cursor = datetime(*date, confirm_hour, confirm_minute, tzinfo=NY) + timedelta(minutes=5)
        final = datetime(*date, retest_hour, retest_minute, tzinfo=NY)
        while cursor < final:
            index = index_at(cursor.strftime("%H:%M"))
            rows[index] = (106, 107, 105, 106) if direction == 1 else (94, 95, 93, 94)
            cursor += timedelta(minutes=5)
    return _bars(rows, start=start)


def _strip_cutoff(events: list[dict], length: int | None = None) -> list[dict]:
    return [event for event in events
            if event["kind"] != "pending_at_cutoff"
            and (length is None or event["index"] < length)]


class BosOrderBlockContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.p = _small_parameters()

    def test_pivot_is_confirmed_two_bars_later_then_block_retests_after_creation(self) -> None:
        bars = _bos_bars()
        signals, events = strategy.detect(bars, 5, "bos_order_block", self.p)

        pivot = next(event for event in events if event["kind"] == "pivot" and event["direction"] == 1)
        self.assertEqual((pivot["index"], pivot["source_index"], pivot["level"]), (6, 4, 105))
        self.assertEqual(pivot["known_at"], bars[6].t + STEP_5M)
        bos = next(event for event in events if event["kind"] == "bos" and event["source_index"] == 4)
        block = next(event for event in events if event["kind"] == "block")
        self.assertEqual((bos["index"], bos["known_at"]), (7, bars[7].t + STEP_5M))
        self.assertEqual((block["index"], block["source_index"], block["low"], block["high"]),
                         (7, 6, 99, 104))
        # Prior ATR at the BOS is (TR[5] + TR[6]) / 2 = (6 + 5) / 2.
        self.assertAlmostEqual(block["stop"], 99 - 0.1 * 5.5)
        self.assertEqual([(s.index, s.direction, s.sweep_index, s.reason) for s in signals],
                         [(8, 1, 6, "bos_order_block")])
        emitted = next(event for event in events if event["kind"] == "signal")
        self.assertEqual(emitted["known_at"], bars[8].t + STEP_5M)

    def test_short_rules_are_the_price_reflection_of_long_rules(self) -> None:
        bars = _bos_bars(short=True)
        signals, events = strategy.detect(bars, 5, "bos_order_block", self.p)

        self.assertEqual([(s.index, s.direction, s.sweep_index) for s in signals], [(8, -1, 6)])
        block = next(event for event in events if event["kind"] == "block")
        self.assertEqual((block["low"], block["high"]), (96, 101))
        self.assertAlmostEqual(block["stop"], 101 + 0.1 * 5.5)

    def test_bos_detector_accepts_the_supported_fifteen_minute_timeframe(self) -> None:
        bars = _bos_bars(minutes=15)
        signals, _ = strategy.detect(bars, 15, "bos_order_block", _small_parameters(atr_minutes=30))
        self.assertEqual([(signal.index, signal.direction) for signal in signals], [(8, 1)])

    def test_bos_bar_cannot_retest_its_new_block_and_invalidation_precedes_acceptance(self) -> None:
        bars = _bos_bars(retest=False)
        bars.append(_candle(8, (105, 107, 98, 106)))  # touches, breaches, and closes favorably
        signals, events = strategy.detect(bars, 5, "bos_order_block", self.p)

        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "invalidated" and event["index"] == 8 for event in events))

    def test_setup_survives_unsuccessful_touches_and_expires_at_sixty_minutes_inclusively(self) -> None:
        rows = [bar for bar in _bos_bars(retest=False)]
        for index in range(8, 19):
            rows.append(_candle(index, (102, 103, 100, 102)))
        rows.append(_candle(19, (104, 106, 103, 105)))
        signals, _ = strategy.detect(rows, 5, "bos_order_block", self.p)

        self.assertEqual([(signal.index, signal.sweep_index) for signal in signals], [(19, 6)])

    def test_failed_bos_consumes_pivot_and_does_not_replace_an_older_pending_block(self) -> None:
        rows = [bar for bar in _bos_bars(retest=False)]
        # Form and confirm a later strict high pivot while the first block is
        # pending. The next BOS has no opposing candle in its bounded search.
        rows += [
            _candle(8, (102, 103, 100, 102)),
            _candle(9, (102, 103, 100, 102)),
            _candle(10, (100, 120, 100, 102)),
            _candle(11, (102, 104, 100, 103)),
            _candle(12, (103, 105, 101, 104)),
            _candle(13, (118.5, 122, 118, 121)),
            _candle(14, (104, 106, 103, 105)),
        ]
        signals, events = strategy.detect(rows, 5, "bos_order_block", self.p)

        self.assertEqual([(signal.index, signal.sweep_index) for signal in signals], [(14, 6)])
        second_bos = [event for event in events if event["kind"] == "bos" and event["index"] == 13]
        self.assertEqual(len(second_bos), 1)
        self.assertFalse(any(event["kind"] == "block" and event["index"] == 13 for event in events))
        self.assertFalse(any(event["kind"] == "replaced" for event in events))

    def test_equal_pivot_extrema_are_rejected_and_a_failed_break_cannot_repeat(self) -> None:
        rows = [_normal() for _ in range(4)]
        rows += [
            (100, 105, 99, 100),
            (101, 104, 98, 100),
            (101, 104, 99, 100),
            (104.9, 105.2, 104.8, 105.1),  # strict break, body below displacement
            (104, 104.5, 103, 104),
            (104, 107, 104, 106),  # same pivot is already consumed
        ]
        signals, events = strategy.detect(_bars(rows), 5, "bos_order_block", self.p)
        source_four_bos = [event for event in events
                           if event["kind"] == "bos" and event["source_index"] == 4]

        self.assertEqual(len(source_four_bos), 1)
        self.assertFalse(any(event["kind"] == "block" for event in events))
        self.assertEqual(signals, [])

        tied = [_normal() for _ in range(7)]
        tied[2] = (100, 105, 99, 100)
        tied[4] = (100, 105, 99, 100)
        _, tied_events = strategy.detect(_bars(tied), 5, "bos_order_block", self.p)
        self.assertFalse(any(event["kind"] == "pivot" and event["source_index"] == 4
                             and event["direction"] == 1 for event in tied_events))


class SilverBulletContractTests(unittest.TestCase):
    def test_complete_new_york_range_sweep_gap_and_later_retest(self) -> None:
        bars = _silver_bars()
        signals, events = strategy.detect(bars, 5, "silver_bullet")

        signal_index = next(i for i, bar in enumerate(bars) if datetime.fromtimestamp(
            bar.t / 1000, timezone.utc).astimezone(NY).strftime("%H:%M") == "10:10")
        sweep_index = next(event["index"] for event in events if event["kind"] == "sweep")
        self.assertEqual([(signal.index, signal.direction, signal.sweep_index) for signal in signals],
                         [(signal_index, 1, sweep_index)])
        sweep = next(event for event in events if event["kind"] == "sweep")
        gap = next(event for event in events if event["kind"] == "gap")
        signal_event = next(event for event in events if event["kind"] == "signal")
        self.assertEqual(sweep["stop"], 97 - 0.1 * 3)
        self.assertEqual(signals[0].stop, sweep["stop"])
        self.assertEqual((gap["low"], gap["high"]), (102, 104))
        self.assertEqual(signal_event["known_at"], bars[signals[0].index].t + STEP_5M)
        self.assertLess(datetime.fromtimestamp(signal_event["known_at"] / 1000, timezone.utc).astimezone(NY).hour * 60
                        + datetime.fromtimestamp(signal_event["known_at"] / 1000, timezone.utc).astimezone(NY).minute,
                        11 * 60)

    def test_short_fvg_reversal_mirrors_the_long_setup(self) -> None:
        bars = _silver_bars(direction=-1)
        signals, events = strategy.detect(bars, 5, "silver_bullet")

        sweep_index = next(event["index"] for event in events if event["kind"] == "sweep")
        self.assertEqual([(signal.direction, signal.sweep_index) for signal in signals], [(-1, sweep_index)])
        gap = next(event for event in events if event["kind"] == "gap")
        self.assertEqual((gap["low"], gap["high"]), (96, 98))
        self.assertAlmostEqual(signals[0].stop, 103 + 0.1 * 3)

    def test_sweep_to_gap_and_gap_to_retest_expiry_are_inclusive_at_thirty_minutes(self) -> None:
        sweep_boundary = _silver_bars(confirm_at="10:30", retest_at="10:35")
        signals, _ = strategy.detect(sweep_boundary, 5, "silver_bullet")
        self.assertEqual(len(signals), 1)
        self.assertEqual(datetime.fromtimestamp(sweep_boundary[signals[0].index].t / 1000,
                                                timezone.utc).astimezone(NY).strftime("%H:%M"), "10:35")

        gap_boundary = _silver_bars(confirm_at="10:20", retest_at="10:50")
        signals, _ = strategy.detect(gap_boundary, 5, "silver_bullet")
        self.assertEqual(len(signals), 1)
        self.assertEqual(datetime.fromtimestamp(gap_boundary[signals[0].index].t / 1000,
                                                timezone.utc).astimezone(NY).strftime("%H:%M"), "10:50")

    def test_sweep_expiry_after_thirty_minutes_discards_the_setup(self) -> None:
        bars = _silver_bars(confirm_at="10:35", retest_at=None)
        signals, events = strategy.detect(bars, 5, "silver_bullet")

        self.assertEqual(signals, [])
        expired = next(event for event in events if event["kind"] == "expired")
        self.assertEqual(datetime.fromtimestamp(bars[expired["index"]].t / 1000,
                                                timezone.utc).astimezone(NY).strftime("%H:%M"), "10:35")

    def test_dst_winter_summer_sessions_use_local_clock_and_date(self) -> None:
        for date, expected_utc_hour in (((2026, 1, 15), 15), ((2026, 7, 15), 14)):
            with self.subTest(date=date):
                bars = _silver_bars(date=date)
                signals, events = strategy.detect(bars, 5, "silver_bullet")
                self.assertEqual(len(signals), 1)
                event = next(event for event in events if event["kind"] == "signal")
                local = datetime.fromtimestamp(event["known_at"] / 1000, timezone.utc).astimezone(NY)
                utc = datetime.fromtimestamp(event["known_at"] / 1000, timezone.utc)
                self.assertEqual(local.strftime("%H:%M"), "10:15")
                self.assertEqual(utc.hour, expected_utc_hour)

    def test_partial_range_and_dual_sweep_never_arm_a_trade(self) -> None:
        full = _silver_bars()
        first_905 = _local_ms((2026, 1, 15), 9, 5)
        partial_rows = [(bar.open, bar.high, bar.low, bar.close) for bar in full if bar.t >= first_905]
        partial = _bars(partial_rows, start=first_905)
        signals, events = strategy.detect(partial, 5, "silver_bullet", _small_parameters())
        self.assertEqual(signals, [])
        self.assertFalse(any(event["kind"] == "sweep" for event in events))

        dual = _silver_bars(dual_sweep=True, confirm_at=None, retest_at=None)
        signals, events = strategy.detect(dual, 5, "silver_bullet")
        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "dual_sweep_excluded" for event in events))

    def test_adverse_extremes_and_gap_close_invalidate_before_acceptance(self) -> None:
        bars = _silver_bars(confirm_at=None, retest_at=None)
        sweep_index = next(i for i, bar in enumerate(bars)
                           if datetime.fromtimestamp(bar.t / 1000, timezone.utc).astimezone(NY).strftime("%H:%M") == "10:00")
        bars[sweep_index + 1] = _candle(sweep_index + 1, (99, 100, 96, 99), start=bars[0].t)
        signals, events = strategy.detect(bars, 5, "silver_bullet")
        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "invalidated" and event["index"] == sweep_index + 1
                            for event in events))

        gap_case = _silver_bars(retest_at=None)
        gap_case[sweep_index + 2] = _candle(sweep_index + 2, (102, 103, 100, 101), start=gap_case[0].t)
        signals, events = strategy.detect(gap_case, 5, "silver_bullet")
        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "invalidated" and event["index"] == sweep_index + 2
                            for event in events))

    def test_new_sweep_replaces_old_state_and_one_signal_is_allowed_per_date(self) -> None:
        replaced = _silver_bars(direction=-1, sweep_at="10:05", confirm_at="10:10", retest_at="10:15")
        # A bullish sweep is the old state at 10:00, then the short sweep at
        # 10:05 replaces it. The short gap uses the 10:00 candle as its third bar.
        replaced[replaced.index(next(bar for bar in replaced if datetime.fromtimestamp(
            bar.t / 1000, timezone.utc).astimezone(NY).strftime("%H:%M") == "10:00"))] = _candle(
                next(i for i, bar in enumerate(replaced) if datetime.fromtimestamp(
                    bar.t / 1000, timezone.utc).astimezone(NY).strftime("%H:%M") == "10:00"),
                (100, 101, 97, 99), start=replaced[0].t)
        signals, events = strategy.detect(replaced, 5, "silver_bullet")
        self.assertEqual([signal.direction for signal in signals], [-1])
        self.assertTrue(any(event["kind"] == "replaced" for event in events))

        one_day = _silver_bars(extra_second_setup=True)
        signals, _ = strategy.detect(one_day, 5, "silver_bullet")
        self.assertEqual(len(signals), 1)

    def test_date_reset_allows_a_fresh_setup_on_the_next_local_day(self) -> None:
        first = _silver_bars(date=(2026, 1, 14))
        second = _silver_bars(date=(2026, 1, 15))
        rows = [(bar.open, bar.high, bar.low, bar.close) for bar in first]
        rows.extend(_normal() for _ in range(239))
        rows.extend((bar.open, bar.high, bar.low, bar.close) for bar in second)
        combined = _bars(rows, start=first[0].t)
        signals, _ = strategy.detect(combined, 5, "silver_bullet")

        signal_dates = [datetime.fromtimestamp(combined[signal.index].t / 1000, timezone.utc)
                        .astimezone(NY).date().isoformat() for signal in signals]
        self.assertEqual(signal_dates, ["2026-01-14", "2026-01-15"])

    def test_no_signal_can_be_known_at_or_after_the_eleven_oclock_next_open(self) -> None:
        bars = _silver_bars(sweep_at="10:20", confirm_at="10:50", retest_at="10:55")
        signals, events = strategy.detect(bars, 5, "silver_bullet")

        self.assertEqual(signals, [])
        self.assertFalse(any(event["kind"] == "signal" and event["known_at"] >= _local_ms((2026, 1, 15), 11, 0)
                             for event in events))


class TurtleSoupContractTests(unittest.TestCase):
    def test_prior_twenty_excludes_breakout_bar_and_exactly_next_strict_reclaim_emits(self) -> None:
        bars = _turtle_bars()
        signals, events = strategy.detect(bars, 5, "turtle_soup_plus1", _small_parameters())

        self.assertEqual([(signal.index, signal.direction, signal.sweep_index) for signal in signals],
                         [(21, 1, 20)])
        self.assertAlmostEqual(signals[0].stop, 87 - 0.1 * 7.5)
        breakout = next(event for event in events if event["kind"] == "breakout")
        self.assertEqual((breakout["index"], breakout["source_index"], breakout["level"]), (20, 16, 90))
        signal_event = next(event for event in events if event["kind"] == "signal")
        self.assertEqual(signal_event["known_at"], bars[21].t + STEP_5M)

        short_bars = _turtle_bars(short=True)
        short_signals, _ = strategy.detect(short_bars, 5, "turtle_soup_plus1", _small_parameters())
        self.assertEqual([(signal.index, signal.direction) for signal in short_signals], [(21, -1)])
        self.assertAlmostEqual(short_signals[0].stop, 113 + 0.1 * 7.5)

    def test_breakout_waits_for_next_bar_equality_fails_and_failed_reclaim_is_consumed(self) -> None:
        bars = _turtle_bars()
        prefix_signals, prefix_events = strategy.detect(bars[:21], 5, "turtle_soup_plus1", _small_parameters())
        self.assertEqual(prefix_signals, [])
        self.assertTrue(any(event["kind"] == "breakout" and event["index"] == 20 for event in prefix_events))

        equal = _turtle_bars(reclaim_close=90)
        equal.append(_candle(22, (90, 92, 89, 91)))
        signals, events = strategy.detect(equal, 5, "turtle_soup_plus1", _small_parameters())
        self.assertEqual(signals, [])
        self.assertTrue(any(event["kind"] == "reclaim_failed" and event["index"] == 21 for event in events))

    def test_most_recent_tied_extreme_controls_the_minimum_age(self) -> None:
        signals, events = strategy.detect(_turtle_bars(tied_latest=True), 5,
                                          "turtle_soup_plus1", _small_parameters())
        self.assertEqual(signals, [])
        self.assertFalse(any(event["kind"] == "breakout" for event in events))

    def test_default_two_hour_atr_must_be_available_and_positive_before_any_signal(self) -> None:
        short_history = _turtle_bars()[:21]
        signals, events = strategy.detect(short_history, 5, "turtle_soup_plus1")
        self.assertEqual(signals, [])
        self.assertFalse(any(event["kind"] == "breakout" for event in events))

        flat = [broker.Candle(i * STEP_5M, 100, 100, 100, 100) for i in range(25)]
        flat.append(broker.Candle(25 * STEP_5M, 100, 101, 99, 99))
        signals, events = strategy.detect(flat, 5, "turtle_soup_plus1")
        self.assertEqual(signals, [])
        self.assertFalse(any(event["kind"] in ("breakout", "signal") for event in events))

    def test_turtle_soup_supports_fifteen_minute_bars(self) -> None:
        bars = _turtle_bars(minutes=15)
        signals, _ = strategy.detect(bars, 15, "turtle_soup_plus1", _small_parameters(atr_minutes=30))
        self.assertEqual([(signal.index, signal.direction) for signal in signals], [(21, 1)])


class DetectorBoundaryTests(unittest.TestCase):
    def test_invalid_approach_timeframe_settings_ohlc_and_gaps_are_rejected(self) -> None:
        valid = _bars([_normal(), _normal()])
        for minutes, approach in ((30, "bos_order_block"), (15, "silver_bullet"), (5, "unknown")):
            with self.subTest(minutes=minutes, approach=approach), self.assertRaises(ValueError):
                strategy.detect(valid, minutes, approach)

        for p in (_small_parameters(atr_minutes=0), _small_parameters(atr_minutes=10.0),
                  _small_parameters(setup_minutes=7), _small_parameters(turtle_min_age=21),
                  _small_parameters(displacement_atr=float("nan")),
                  _small_parameters(stop_buffer_atr=-0.1)):
            with self.subTest(parameters=p), self.assertRaises(ValueError):
                strategy.detect(valid, 5, "turtle_soup_plus1", p)

        malformed = [
            [broker.Candle(0, 100, 99, 98, 100)],
            [broker.Candle(0, float("nan"), 101, 99, 100)],
            [broker.Candle(0, 100, 101, 99, 100), broker.Candle(2 * STEP_5M, 100, 101, 99, 100)],
            [broker.Candle(1, 100, 101, 99, 100)],
        ]
        for bars in malformed:
            with self.subTest(bars=bars), self.assertRaises(ValueError):
                strategy.detect(bars, 5, "bos_order_block", _small_parameters())

    def test_event_clocks_are_closed_bar_times_and_broker_fills_next_open(self) -> None:
        bars = _bos_bars()
        signals, events = strategy.detect(bars, 5, "bos_order_block", _small_parameters())
        signal = signals[0]
        sim_bars = bars + [_candle(9, _normal())]
        result = broker.simulate(
            sim_bars, signals, 5, "both", [],
            broker.Parameters(max_hold_minutes=180),
            broker.Execution(fee_bps=0, slip_bps=0),
        )

        signal_event = next(event for event in events if event["kind"] == "signal")
        position = result["open_position"]
        self.assertEqual(signal_event["known_at"], bars[signal.index].t + STEP_5M)
        self.assertEqual(position["known_at"], signal_event["known_at"])
        self.assertEqual(position["entry_index"], signal.index + 1)
        self.assertEqual(position["entry_at"], sim_bars[signal.index + 1].t)
        self.assertEqual(position["entry"], sim_bars[signal.index + 1].open)

    def test_prefix_causality_survives_future_bar_mutation_for_all_approaches(self) -> None:
        fixtures = {
            "bos_order_block": (_bos_bars(), 5, _small_parameters()),
            "silver_bullet": (_silver_bars(), 5, strategy.SmcParameters()),
            "turtle_soup_plus1": (_turtle_bars(), 5, _small_parameters()),
        }
        for approach, (bars, minutes, p) in fixtures.items():
            with self.subTest(approach=approach):
                complete_signals, complete_events = strategy.detect(bars, minutes, approach, p)
                for length in range(1, len(bars)):
                    prefix = bars[:length]
                    prefix_signals, prefix_events = strategy.detect(prefix, minutes, approach, p)
                    self.assertEqual(prefix_signals,
                                     [signal for signal in complete_signals if signal.index < length])
                    self.assertEqual(_strip_cutoff(prefix_events),
                                     _strip_cutoff(complete_events, length))

                    changed_future = list(bars)
                    for index in range(length, len(changed_future)):
                        price = 1_000_000.0 + index
                        changed_future[index] = _candle(index, (price, price + 2, price - 2, price + 1),
                                                        minutes=minutes, start=bars[0].t)
                    changed_signals, changed_events = strategy.detect(changed_future, minutes, approach, p)
                    self.assertEqual(prefix_signals,
                                     [signal for signal in changed_signals if signal.index < length])
                    self.assertEqual(_strip_cutoff(prefix_events),
                                     _strip_cutoff(changed_events, length))


class CampaignContractTests(unittest.TestCase):
    @staticmethod
    def _metrics() -> dict:
        return {
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_return_pct": 0.0,
            "closed_trades": 0,
            "max_drawdown_pct": 0.0,
            "adverse_drawdown_pct": 0.0,
            "fees": 0.0,
            "funding": 0.0,
        }

    def _run_mocked_comparison(self, root: Path) -> tuple[Path, mock.Mock]:
        root.mkdir(parents=True, exist_ok=True)
        source_root = Path(__file__).resolve().parents[1] / "artifacts" / "strategy-development" / "btc-smc-20261028"
        (root / "protocol.json").write_bytes((source_root / "protocol.json").read_bytes())
        (root / "STRATEGY.md").write_bytes((source_root / "STRATEGY.md").read_bytes())
        start = campaign.timestamp(2022)
        end = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
        bars5 = [broker.Candle(start, 100, 101, 99, 100), broker.Candle(end - STEP_5M, 100, 101, 99, 100)]
        bars15 = [broker.Candle(start, 100, 101, 99, 100), broker.Candle(end - 3 * STEP_5M, 100, 101, 99, 100)]
        simulation = mock.Mock(return_value={"metrics": self._metrics(), "trades": []})
        with contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(campaign, "load_candles", return_value=bars5), \
                mock.patch.object(campaign, "resample_15m", return_value=bars15), \
                mock.patch.object(campaign, "load_funding", return_value=[]), \
                mock.patch.object(campaign, "detect", return_value=([], [])) as detect, \
                mock.patch.object(campaign, "control_detect", return_value=([], [])), \
                mock.patch.object(campaign, "simulate", simulation):
            output = campaign.comparison(root, "unit-contract")
        return output, simulation

    def test_mocked_campaign_accounts_for_all_210_evaluations_and_returns_no_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, simulation = self._run_mocked_comparison(root)
            summary = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
            progress = json.loads((output / "progress.json").read_text(encoding="utf-8"))
            trials = (output / "trials.jsonl").read_text(encoding="utf-8").splitlines()
            cumulative = (root / "cumulative_trials.jsonl").read_text(encoding="utf-8").splitlines()
            identities_before = json.loads((output / "identities_before_run.json").read_text(encoding="utf-8"))
            identities_after = json.loads((output / "identities_after_run.json").read_text(encoding="utf-8"))

            self.assertEqual(simulation.call_count, 210)
            self.assertEqual(summary["completed_annual_runs"], 210)
            self.assertEqual(progress, {"completed": 210, "expected": 210, "status": "COMPLETE"})
            self.assertEqual(len(summary["candidates"]), 15)
            self.assertEqual(len(summary["controls"]), 6)
            self.assertEqual(len(trials), 210)
            self.assertEqual(len(cumulative), 210)
            self.assertTrue(all(json.loads(line)["condition"] in ("base", "stress") for line in trials))
            self.assertTrue(all(json.loads(line)["campaign_id"] == "btc-smc-20261028" for line in cumulative))
            self.assertEqual(identities_before, identities_after)
            self.assertEqual(summary["identities"], identities_before)
            self.assertIsNone(summary["selected"])
            self.assertEqual(summary["status"], "RETURN_TO_PHASE_1")

    def test_invalid_run_id_and_existing_run_directory_cannot_be_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for run_id in ("", "..", "../escape", "a/b", "C:\\escape"):
                with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                    campaign.comparison(root, run_id)

            source_root = Path(__file__).resolve().parents[1] / "artifacts" / "strategy-development" / "btc-smc-20261028"
            (root / "protocol.json").write_bytes((source_root / "protocol.json").read_bytes())
            (root / "STRATEGY.md").write_bytes((source_root / "STRATEGY.md").read_bytes())
            existing = root / "runs" / "unit-contract"
            existing.mkdir(parents=True)
            marker = existing / "keep.txt"
            marker.write_text("existing evidence", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                campaign.comparison(root, "unit-contract")
            self.assertEqual(marker.read_text(encoding="utf-8"), "existing evidence")


if __name__ == "__main__":
    unittest.main()
