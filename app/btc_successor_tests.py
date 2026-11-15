"""Independent constructed cases for the frozen BTC successor contracts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from app import btc_liquidity as legacy
from app import btc_liquidity_campaign as legacy_campaign
from app import btc_liquidity_data as legacy_data
from app import btc_successor as successor
from app import btc_successor_broker as broker
from app import btc_successor_campaign as campaign
from app import btc_successor_data as successor_data


STEP_5M = 5 * 60_000
STEP_15M = 15 * 60_000
HOUR = 60 * 60_000
DAY = 24 * HOUR
PHASE2_ROOT = Path("artifacts/strategy-development/btc-successor-phase2-20261028")


def _candle(index: int, row: tuple[float, float, float, float], *,
            minutes: int = 15, start: int = 0, volume: float = 1.0) -> legacy.Candle:
    return legacy.Candle(start + index * minutes * 60_000, *row, volume)


def _flat_bars(count: int, *, price: float = 100.0, start: int = 0,
               minutes: int = 15, wick: float = 0.5,
               volume: float = 1.0) -> list[legacy.Candle]:
    return [
        _candle(i, (price, price + wick, price - wick, price),
                minutes=minutes, start=start, volume=volume)
        for i in range(count)
    ]


def _quote_values(bars: list[legacy.Candle]) -> list[float]:
    return [bar.close * bar.volume for bar in bars]


def _features(bars: list[legacy.Candle], **updates: dict[str, dict]) -> list[dict]:
    result = []
    for index, bar in enumerate(bars):
        result.append({
            "known_at": bar.t + STEP_15M,
            "atr": None,
            "hour_close": False,
            "two_hour_close": False,
            "shock_return": None,
            "shock_sigma": None,
            "channel_upper": None,
            "channel_lower": None,
            "channel_midpoint": None,
            "trail_midpoint": None,
            "noise_upper": None,
            "noise_lower": None,
            "vwap": None,
            "noise_check": False,
        })
        if str(index) in updates:
            result[-1].update(updates[str(index)])
    return result


def _intent(index: int = 0, direction: int = 1, stop: float = 95.0,
            hold: int = 120, reason: str = "fixture") -> successor.Intent:
    return successor.Intent(index, direction, stop, hold, reason)


def _execution(**overrides: float) -> legacy.Execution:
    values = {"fee_bps": 0.0, "slip_bps": 0.0,
              "funding_mark_buffer_fraction": 0.01}
    values.update(overrides)
    return legacy.Execution(**values)


def _noise_history(day_count: int = 16, *, start_partial: bool = False,
                   current_open: float = 100.0,
                   current_close: float = 103.0) -> list[legacy.Candle]:
    """Daily fixture with seven 1% and seven 5% same-clock moves."""
    bars = []
    for day in range(day_count):
        for offset in range(96):
            if start_partial and day == 0 and offset == 0:
                continue
            t = day * DAY + offset * STEP_15M
            opening = current_open if day == day_count - 1 and offset == 0 else 100.0
            close = 100.0
            if offset == 1 and day == day_count - 1:
                close = current_close
            elif offset == 1:
                if day == 0:
                    close = 150.0  # must fall outside the immediately preceding 14 days
                elif 1 <= day <= 7:
                    close = 101.0
                elif 8 <= day <= 14:
                    close = 105.0
            bars.append(legacy.Candle(t, opening, max(opening, close) + 0.25,
                                      min(opening, close) - 0.25, close, 1.0))
    return bars


def _small_parameters(**overrides: float | int) -> successor.ModelParameters:
    values: dict[str, float | int] = {
        "atr_hours": 1,
        "shock_returns": 2,
        "shock_multiple": 3.0,
        "noise_days": 14,
        "channel_hours": 2,
    }
    values.update(overrides)
    return successor.ModelParameters(**values)


class AggregationAndFeatureTests(unittest.TestCase):
    def test_production_model_defaults_are_frozen_and_bad_windows_reject(self) -> None:
        self.assertEqual(successor.ModelParameters(), successor.ModelParameters(20, 240, 3.0, 14, 24))
        for values in (
                {"atr_hours": 0}, {"shock_returns": 1}, {"shock_multiple": 0.0},
                {"noise_days": -1}, {"channel_hours": 1},
                {"shock_multiple": float("nan")}):
            with self.subTest(parameters=values):
                with self.assertRaises(ValueError):
                    successor.ModelParameters(**values)

    def test_known_ohlcv_aggregation_uses_complete_utc_triplets_only(self) -> None:
        bars5 = [
            legacy.Candle(0, 100, 103, 99, 101, 1),
            legacy.Candle(STEP_5M, 101, 104, 100, 103, 2),
            legacy.Candle(2 * STEP_5M, 103, 105, 102, 104, 3),
            legacy.Candle(3 * STEP_5M, 104, 108, 103, 107, 4),
            legacy.Candle(4 * STEP_5M, 107, 109, 106, 108, 5),
        ]

        self.assertEqual(
            legacy_data.resample_15m(bars5),
            [legacy.Candle(0, 100, 105, 99, 104, 6)],
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            legacy_data.resample_15m([bars5[0], bars5[2], bars5[3]])

    def test_epoch_aligned_hour_and_two_hour_availability_and_atr(self) -> None:
        bars = []
        for i in range(8):
            high, low = (102, 98) if i < 4 else (104, 99)
            bars.append(_candle(i, (100, high, low, 100)))

        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())

        self.assertEqual([i for i, f in enumerate(frames) if f["hour_close"]], [3, 7])
        self.assertEqual([i for i, f in enumerate(frames) if f["two_hour_close"]], [7])
        self.assertEqual([f["known_at"] for f in frames], [b.t + STEP_15M for b in bars])
        self.assertIsNone(frames[3]["atr"], "the first completed hour has no preceding hourly close")
        self.assertEqual(frames[7]["atr"], 5.0,
                         "second-hour TR is max(104-99, 104-100, 100-99)")

    def test_prefixes_preserve_all_existing_features_and_allow_partial_tail(self) -> None:
        bars = _flat_bars(11)
        p = _small_parameters()
        complete = successor.build_features(bars, _quote_values(bars), p)

        for length in range(1, len(bars)):
            with self.subTest(prefix=length):
                prefix = successor.build_features(bars[:length], _quote_values(bars[:length]), p)
                self.assertEqual(prefix, complete[:length])
        self.assertFalse(complete[10]["hour_close"])
        self.assertEqual(complete[10]["atr"], complete[7]["atr"],
                         "an unfinished hour keeps the latest completed ATR")

    def test_2h_shock_sigma_is_sample_sd_of_prior_returns_only(self) -> None:
        endpoints = [100.0, 102.0, 101.0, 104.0]
        bars = []
        previous = endpoints[0]
        endpoint_by_bar = {}
        for two_hour, close in enumerate(endpoints):
            if two_hour == 0:
                close = endpoints[0]
            for quarter in range(8):
                i = len(bars)
                target = close if quarter == 7 else previous
                op = previous if quarter == 7 else previous
                bars.append(_candle(i, (op, max(op, target) + 0.5,
                                        min(op, target) - 0.5, target)))
            previous = close
            endpoint_by_bar[len(bars) - 1] = close

        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())
        last = frames[31]
        prior = [102.0 / 100.0 - 1.0, 101.0 / 102.0 - 1.0]
        expected_sample_sd = math.sqrt(sum((x - sum(prior) / 2) ** 2 for x in prior))

        self.assertEqual(last["shock_return"], 104.0 / 101.0 - 1.0)
        self.assertAlmostEqual(last["shock_sigma"], expected_sample_sd, places=12)
        self.assertNotAlmostEqual(last["shock_sigma"], expected_sample_sd / math.sqrt(2), places=5,
                                  msg="ddof=0 would produce the smaller population deviation")

    def test_partial_initial_day_does_not_claim_midnight_vwap_ownership(self) -> None:
        bars = _flat_bars(5, start=STEP_15M)
        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())

        self.assertTrue(all(frame["vwap"] is None for frame in frames),
                        "without the UTC midnight open, this partial session has no known VWAP")

    def test_features_reject_missing_nonfinite_negative_and_wrong_unit_turnover(self) -> None:
        bars = _flat_bars(2)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            successor.build_features(bars, [100.0], _small_parameters())
        for quotes in ([100.0, float("nan")], [100.0, -1.0], [100.0, 1000.0]):
            with self.subTest(quotes=quotes):
                with self.assertRaisesRegex(ValueError, "quote turnover"):
                    successor.build_features(bars, quotes, _small_parameters())

    def test_noise_uses_exact_fourteen_prior_days_mean_absolute_move(self) -> None:
        bars = _noise_history()
        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())
        current_index = 15 * 96 + 1
        frame = frames[current_index]

        self.assertEqual((frame["noise_upper"], frame["noise_lower"]), (103.0, 97.0))
        self.assertAlmostEqual(frame["vwap"], 101.5)
        self.assertTrue(frame["noise_check"])
        equal_signals, _ = successor.detect(bars[:current_index + 1],
                                            frames[:current_index + 1],
                                            "utc_noise_momentum", _small_parameters())
        self.assertNotIn(current_index, [signal.index for signal in equal_signals],
                         "equality with the upper band is not outside")

        above = _noise_history(current_close=103.01)
        above_frames = successor.build_features(above, _quote_values(above), _small_parameters())
        signals, _ = successor.detect(above[:current_index + 1],
                                      above_frames[:current_index + 1],
                                      "utc_noise_momentum", _small_parameters())
        self.assertEqual([(signal.index, signal.direction) for signal in signals],
                         [(current_index, 1)])

    def test_noise_requires_fourteen_complete_prior_days_and_midnight_owns_previous_day(self) -> None:
        partial = _noise_history(day_count=15, start_partial=True)
        partial_frames = successor.build_features(partial, _quote_values(partial), _small_parameters())
        current_index = next(i for i, bar in enumerate(partial) if bar.t == 14 * DAY + STEP_15M)
        self.assertIsNone(partial_frames[current_index]["noise_upper"],
                          "the initial partial calendar day cannot count as one of 14 complete days")

        midnight = _noise_history(current_open=110.0)
        midnight_frames = successor.build_features(midnight, _quote_values(midnight), _small_parameters())
        prior_day_close_index = 15 * 96 - 1
        current_day_check_index = 15 * 96 + 1
        self.assertIsNone(midnight_frames[prior_day_close_index]["noise_upper"],
                          "the 23:45 observation ending at midnight still belongs to the prior day")
        self.assertEqual(midnight_frames[current_day_check_index]["noise_upper"], 113.3)

    def test_cost_admission_equality_both_directions_and_invalid_geometry(self) -> None:
        self.assertTrue(successor.cost_admitted(100.0, 99.2, 1))
        self.assertTrue(successor.cost_admitted(100.0, 100.8, -1))
        self.assertFalse(successor.cost_admitted(100.0, 99.2001, 1))
        self.assertFalse(successor.cost_admitted(100.0, 100.7999, -1))
        self.assertFalse(successor.cost_admitted(100.0, 101.0, 1))
        self.assertFalse(successor.cost_admitted(100.0, 99.0, -1))
        self.assertFalse(successor.cost_admitted(float("nan"), 99.2, 1))


class TurnoverAdapterTests(unittest.TestCase):
    def _raw_fixture(self, root: Path, rows: list[list[str]]) -> tuple[SimpleNamespace, list[legacy.Candle]]:
        month = SimpleNamespace(
            stem="BTCUSDT-5m-2022-01",
            filename="BTCUSDT-5m-2022-01.zip",
            source_url=legacy_data.ARCHIVE_BASE_URL + "BTCUSDT-5m-2022-01.zip",
            checksum_url=legacy_data.ARCHIVE_BASE_URL + "BTCUSDT-5m-2022-01.zip.CHECKSUM",
            first_ms=legacy_data.START_MS,
            next_month_ms=legacy_data.START_MS + len(rows) * STEP_5M,
            expected_rows=len(rows),
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            text = io.StringIO(newline="")
            writer = csv.writer(text)
            writer.writerow(["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"])
            writer.writerows(rows)
            archive.writestr(month.stem + ".csv", text.getvalue().encode("utf-8"))
        archive_bytes = output.getvalue()
        checksum_bytes = f"{hashlib.sha256(archive_bytes).hexdigest()}  {month.filename}\n".encode("ascii")
        (root / month.filename).write_bytes(archive_bytes)
        (root / (month.filename + ".CHECKSUM")).write_bytes(checksum_bytes)
        manifest = {
            "schema_version": "btc_liquidity_raw_v1",
            "symbol": legacy_data.SYMBOL,
            "venue": "Binance USD-M perpetual",
            "interval": legacy_data.INTERVAL,
            "requested_start_ms": legacy_data.START_MS,
            "requested_end_exclusive_ms": legacy_data.END_EXCLUSIVE_MS,
            "monthly_archives": {
                month.stem: {
                    "archive": {"source_url": month.source_url,
                                "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                                "bytes": len(archive_bytes)},
                    "checksum": {"source_url": month.checksum_url,
                                 "sha256": hashlib.sha256(checksum_bytes).hexdigest(),
                                 "bytes": len(checksum_bytes)},
                }
            },
            "funding_pages": [],
            "sources": {},
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        bars = [
            legacy.Candle(int(row[0]), float(row[1]), float(row[2]), float(row[3]),
                          float(row[4]), float(row[5]))
            for row in rows
        ]
        return month, bars

    @staticmethod
    def _valid_rows() -> list[list[str]]:
        start = legacy_data.START_MS
        return [
            [str(start), "100", "101", "99", "100", "2", "", "200"],
            [str(start + STEP_5M), "100", "102", "99", "101", "0", "", "0"],
            [str(start + 2 * STEP_5M), "101", "103", "100", "102", "4", "", "408"],
        ]

    def test_verified_quote_field_zero_rows_and_exact_session_vwap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, bars = self._raw_fixture(root, self._valid_rows())
            with mock.patch.object(successor_data, "_months", return_value=[self._raw_fixture_month(root)]):
                quotes = successor_data.load_quote_turnover(root, bars)

        self.assertEqual(quotes, [200.0, 0.0, 408.0])
        self.assertEqual(sum(quotes) / sum(bar.volume for bar in bars), 608.0 / 6.0)

    def _raw_fixture_month(self, root: Path) -> SimpleNamespace:
        # Reconstruct the one-month identity from the names and manifest used above.
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        record = manifest["monthly_archives"]["BTCUSDT-5m-2022-01"]
        return SimpleNamespace(
            stem="BTCUSDT-5m-2022-01",
            filename="BTCUSDT-5m-2022-01.zip",
            source_url=record["archive"]["source_url"],
            checksum_url=record["checksum"]["source_url"],
            first_ms=legacy_data.START_MS,
            next_month_ms=legacy_data.START_MS + 3 * STEP_5M,
            expected_rows=3,
        )

    def test_checksum_tamper_is_rejected_before_turnover_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, bars = self._raw_fixture(root, self._valid_rows())
            archive_path = root / "BTCUSDT-5m-2022-01.zip"
            archive_path.write_bytes(archive_path.read_bytes() + b"tampered")
            with mock.patch.object(successor_data, "_months", return_value=[self._raw_fixture_month(root)]):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    successor_data.load_quote_turnover(root, bars)

    def test_turnover_rejects_timestamp_base_unit_zero_and_row_count_mismatches(self) -> None:
        valid = self._valid_rows()
        malformed = []
        wrong_time = [row[:] for row in valid]
        wrong_time[1][0] = str(int(wrong_time[1][0]) + STEP_5M)
        malformed.append((wrong_time, "alignment or value"))
        wrong_base = [row[:] for row in valid]
        wrong_base[0][5] = "3"
        malformed.append((wrong_base, "alignment or value"))
        wrong_units = [row[:] for row in valid]
        wrong_units[0][7] = "20000"
        malformed.append((wrong_units, "alignment or value"))
        zero_mismatch = [row[:] for row in valid]
        zero_mismatch[1][7] = "100"
        malformed.append((zero_mismatch, "alignment or value"))
        negative = [row[:] for row in valid]
        negative[0][7] = "-1"
        malformed.append((negative, "alignment or value"))
        nonfinite = [row[:] for row in valid]
        nonfinite[0][7] = "nan"
        malformed.append((nonfinite, "alignment or value"))
        incomplete = (valid[:-1], "Incomplete monthly turnover archive")

        for rows, message in [*malformed, incomplete]:
            with self.subTest(message=message, rows=len(rows)):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _, bars = self._raw_fixture(root, rows)
                    # The archive declares its actual row extent, while the bars
                    # retain the expected complete three-row source interval.
                    bars = [
                        legacy.Candle(legacy_data.START_MS + i * STEP_5M,
                                      100, 103, 99, 100, 2 if i == 0 else 0 if i == 1 else 4)
                        for i in range(3)
                    ]
                    month = self._raw_fixture_month(root)
                    with mock.patch.object(successor_data, "_months", return_value=[month]):
                        with self.assertRaisesRegex(ValueError, message):
                            successor_data.load_quote_turnover(root, bars)


class DetectorBoundaryTests(unittest.TestCase):
    def test_shock_equality_emits_both_reversal_directions_and_zero_sigma_does_not(self) -> None:
        bars = _flat_bars(16)
        p = _small_parameters()
        for current_return, expected_direction in ((0.06, -1), (-0.06, 1)):
            with self.subTest(return_value=current_return):
                frames = _features(bars, **{"7": {
                    "two_hour_close": True,
                    "shock_return": current_return,
                    "shock_sigma": 0.02,
                    "atr": 1.0,
                }})
                signals, _ = successor.detect(bars, frames, "shock_reversal_2h", p)
                self.assertEqual([(s.index, s.direction, s.stop) for s in signals],
                                 [(7, expected_direction, 100.0 - expected_direction * 2.0)])
        zero_frames = _features(bars, **{"7": {
            "two_hour_close": True, "shock_return": 0.06,
            "shock_sigma": 0.0, "atr": 1.0,
        }})
        signals, _ = successor.detect(bars, zero_frames, "shock_reversal_2h", p)
        self.assertEqual(signals, [])

    def test_shock_without_atr_is_diagnostic_only_and_controls_use_prior_close(self) -> None:
        bars = _flat_bars(4)
        unavailable = _features(bars, **{"1": {
            "two_hour_close": True, "shock_return": -0.2,
            "shock_sigma": 0.01, "atr": None,
        }})
        signals, events = successor.detect(bars, unavailable, "shock_reversal_2h", _small_parameters())
        self.assertEqual(signals, [])
        self.assertTrue(any(e.get("kind") == "unavailable_feature" and e.get("feature") == "atr"
                            for e in events))

        clock_bars = _flat_bars(74)
        frames = _features(clock_bars, **{
            "0": {"known_at": 15 * 60_000, "hour_close": False, "atr": 1.0},
            "23": {"known_at": 6 * HOUR, "atr": 1.0},
            "47": {"known_at": 12 * HOUR, "atr": 1.0},
            "71": {"known_at": 18 * HOUR, "atr": 1.0},
        })
        # These are raw benchmark directions; alternating uses long at 00/12,
        # short at 06/18 UTC. There is no implied intent before its first clock.
        frames[23]["known_at"] = clock_bars[23].t + STEP_15M
        signals, _ = successor.detect(clock_bars, frames, "clock_6h_alternating", _small_parameters())
        self.assertEqual([(s.index, s.direction, s.stop) for s in signals],
                         [(23, -1, 102.0), (47, 1, 98.0), (71, -1, 102.0)])

    def test_raw_shock_signal_is_retained_when_cost_admission_fails(self) -> None:
        bars = _flat_bars(8)
        frames = _features(bars, **{"7": {
            "two_hour_close": True, "shock_return": -0.06,
            "shock_sigma": 0.02, "atr": 0.1,
        }})
        signals, events = successor.detect(bars, frames, "shock_reversal_2h", _small_parameters())

        self.assertEqual([(signal.index, signal.direction, signal.stop) for signal in signals],
                         [(7, 1, 99.8)])
        raw = next(event for event in events if event["kind"] == "raw_signal")
        self.assertFalse(raw["cost_admitted"], "detector output stays independent of order admission")

    def test_noise_check_entry_window_includes_0030_and_1800_but_not_1815(self) -> None:
        bars = _flat_bars(73)
        frames = _features(bars, **{
            "1": {"noise_check": True, "noise_upper": 101.0, "noise_lower": 99.0,
                "vwap": 100.0, "atr": 1.0},
            "71": {"noise_check": True, "noise_upper": 101.0, "noise_lower": 99.0,
                 "vwap": 100.0, "atr": 1.0},
            "72": {"noise_check": True, "noise_upper": 101.0, "noise_lower": 99.0,
                 "vwap": 100.0, "atr": 1.0},
        })
        for index in (1, 71, 72):
            bars[index] = _candle(index, (102.0, 103.0, 101.0, 102.0))
        for index in (1, 71, 72):
            frames[index]["known_at"] = bars[index].t + STEP_15M

        signals, _ = successor.detect(bars, frames, "utc_noise_momentum", _small_parameters())

        self.assertEqual([s.index for s in signals], [1, 71])
        self.assertTrue(all(s.direction == 1 and s.hold_minutes == 360 for s in signals))

    def test_channel_uses_prior_close_extrema_and_current_close_only_for_trail(self) -> None:
        hourly_closes = [100.0, 102.0, 103.0]
        bars = []
        previous = hourly_closes[0]
        for hour_index, close in enumerate(hourly_closes):
            for quarter in range(4):
                op = previous
                target = close if quarter == 3 else previous
                bars.append(_candle(len(bars), (op, max(op, target) + 20,
                                                min(op, target) - 20, target)))
            previous = close
        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())
        frame = frames[11]

        self.assertEqual((frame["channel_upper"], frame["channel_lower"],
                          frame["channel_midpoint"]), (102.0, 100.0, 101.0))
        self.assertEqual(frame["trail_midpoint"], 102.5)
        self.assertEqual((max(bar.high for bar in bars[:8]), min(bar.low for bar in bars[:8])),
                         (122.0, 80.0), "wick extrema are deliberately unrelated to close channel")

    def test_channel_breakout_is_strict_and_has_no_target_or_atr_dependency(self) -> None:
        bars = _flat_bars(3)
        frames = _features(bars, **{
            "1": {"hour_close": True, "channel_upper": 100.0, "channel_lower": 90.0,
                "channel_midpoint": 95.0},
            "2": {"hour_close": True, "channel_upper": 100.0, "channel_lower": 90.0,
                "channel_midpoint": 95.0},
        })
        bars[1] = _candle(1, (100, 101, 99, 100))
        bars[2] = _candle(2, (100, 102, 100, 101))
        frames[1]["known_at"] = bars[1].t + STEP_15M
        frames[2]["known_at"] = bars[2].t + STEP_15M

        signals, _ = successor.detect(bars, frames, "close_channel_24h", _small_parameters())

        self.assertEqual([(s.index, s.direction, s.stop) for s in signals], [(2, 1, 95.0)])

    def test_flat_channel_does_not_publish_an_unusable_midpoint(self) -> None:
        bars = _flat_bars(12)
        frames = successor.build_features(bars, _quote_values(bars), _small_parameters())

        self.assertIsNone(frames[11]["channel_upper"])
        self.assertIsNone(frames[11]["channel_midpoint"])
        self.assertEqual(frames[11]["trail_midpoint"], 100.0,
                         "a flat latest close channel still has a defined trailing midpoint")

    def test_clock_controls_have_no_implicit_first_decision(self) -> None:
        bars = _flat_bars(4)
        frames = _features(bars)
        for index, known in ((0, 15 * 60_000), (1, 30 * 60_000),
                             (2, 45 * 60_000), (3, 60 * 60_000)):
            frames[index].update(known_at=known, atr=1.0)
        signals, _ = successor.detect(bars, frames, "clock_6h_long", _small_parameters())
        self.assertEqual(signals, [])


class BrokerExecutionTests(unittest.TestCase):
    def _run(self, bars: list[legacy.Candle], signals: list[successor.Intent], *,
             features: list[dict] | None = None,
             approach: str = "shock_reversal_2h", direction: str = "both",
             funding: list[dict] | None = None,
             execution: legacy.Execution | None = None) -> dict:
        return broker.simulate(
            bars, signals, features or _features(bars), approach, direction,
            funding or [], execution or _execution(),
        )

    def test_signal_and_fill_cost_guards_reject_without_widening(self) -> None:
        self.assertTrue(successor.cost_admitted(100.0, 99.2, 1))
        self.assertTrue(successor.cost_admitted(100.0, 100.8, -1))
        bars = [
            _candle(0, (100.0, 101.0, 99.0, 100.0)),
            _candle(1, (98.8, 99.0, 98.0, 98.7)),
        ]
        result = self._run(bars, [_intent(stop=99.2)], direction="long")

        self.assertIsNone(result["open_position"])
        rejected = [event for event in result["ledger"] if event["kind"] == "entry_rejected"]
        self.assertEqual([(event["reason"], event["signal_index"]) for event in rejected],
                         [("fill_cost_guard", 0)])
        self.assertEqual(result["metrics"]["counts"].get("fill_cost_guard"), 1)

    def test_risk_sizing_includes_entry_stop_fees_slippage_and_quantity_step(self) -> None:
        bars = _flat_bars(2)
        execution = _execution(fee_bps=6.0, slip_bps=2.0)
        result = self._run(bars, [_intent(stop=95.0)], direction="long", execution=execution)
        position = result["open_position"]
        self.assertIsNotNone(position)

        expected_entry = 100.0 * 1.0002
        expected_stop = 95.0
        stopped_exit = expected_stop * 0.9998
        risk_per_unit = expected_entry - stopped_exit + 0.0006 * (expected_entry + stopped_exit)
        expected_quantity = math.floor((execution.initial_capital * execution.risk_fraction /
                                        risk_per_unit) / execution.quantity_step + 1e-9) * execution.quantity_step
        self.assertAlmostEqual(position["entry"], expected_entry)
        self.assertAlmostEqual(position["quantity"], expected_quantity)
        self.assertAlmostEqual(position["initial_risk"], expected_quantity * risk_per_unit)
        self.assertLessEqual(position["initial_risk"], execution.initial_capital * execution.risk_fraction)
        self.assertAlmostEqual(position["quantity"] / execution.quantity_step,
                               round(position["quantity"] / execution.quantity_step))

    def test_notional_limit_includes_entry_fee(self) -> None:
        bars = _flat_bars(2)
        execution = _execution(fee_bps=6.0, slip_bps=2.0,
                               risk_fraction=0.5, max_notional_fraction=0.05)
        result = self._run(bars, [_intent(stop=95.0)], direction="long", execution=execution)
        position = result["open_position"]
        self.assertIsNotNone(position)
        self.assertLessEqual(position["quantity"] * position["entry"] * 1.0006,
                             execution.initial_capital * execution.max_notional_fraction)

    def test_direction_filter_precedes_daily_cap_and_excluded_intents_use_no_slot(self) -> None:
        bars = _flat_bars(16)
        signals = [_intent(i, -1, 105.0, 15, "excluded") for i in (0, 3, 6, 9)]
        signals.append(_intent(12, 1, 95.0, 15, "allowed"))
        result = self._run(bars, signals, direction="long")

        counts = result["metrics"]["counts"]
        self.assertEqual(counts.get("direction_excluded"), 4)
        self.assertEqual(counts.get("filled"), 1)
        self.assertNotIn("daily_entry_cap", counts)

    def test_four_filled_entries_cap_applies_per_utc_day(self) -> None:
        bars = _flat_bars(16)
        signals = [_intent(i, 1, 95.0, 15) for i in (0, 3, 6, 9, 12)]
        result = self._run(bars, signals, direction="long")

        self.assertEqual(result["metrics"]["counts"].get("filled"), 4)
        self.assertEqual(result["metrics"]["counts"].get("daily_entry_cap"), 1)
        self.assertEqual(len(result["trades"]), 4)

    def test_exit_at_open_cannot_be_replaced_at_that_same_open(self) -> None:
        bars = _flat_bars(4)
        signals = [_intent(0, 1, 95.0, 15), _intent(1, 1, 95.0, 15, "replacement")]
        result = self._run(bars, signals, direction="long")

        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["reason"], "time_exit")
        self.assertEqual(result["metrics"]["counts"].get("filled"), 1)
        self.assertEqual(result["metrics"]["counts"].get("occupied_at_open"), 1)

    def test_fixed_holds_exit_at_exact_120_and_360_minute_opens_without_targets(self) -> None:
        for hold, exit_index in ((120, 9), (360, 25)):
            with self.subTest(hold=hold):
                bars = [
                    _candle(i, (100.0, 160.0, 99.0, 100.0))
                    for i in range(exit_index + 1)
                ]
                result = self._run(bars, [_intent(0, 1, 95.0, hold)], direction="long")
                trade = result["trades"][0]
                self.assertEqual(trade["reason"], "time_exit")
                self.assertEqual(trade["exit_index"], exit_index)
                self.assertEqual(trade["exit_at"], bars[exit_index].t)
                self.assertNotIn("target", trade)

    def test_noise_deadline_is_capped_at_next_midnight(self) -> None:
        start = 18 * HOUR - STEP_15M
        bars = [
            _candle(i, (100.0, 101.0, 99.0, 100.0), start=start)
            for i in range(26)
        ]
        result = self._run(bars, [_intent(0, 1, 95.0, 360)],
                           approach="utc_noise_momentum", direction="long")
        trade = result["trades"][0]
        next_midnight = DAY

        self.assertEqual(trade["deadline"], next_midnight)
        self.assertEqual(trade["exit_at"], next_midnight)
        self.assertNotIn("target", trade)

    def test_noise_exit_uses_current_band_vwap_and_suppresses_same_check_entry(self) -> None:
        cases = (
            (1, 101.0, 101.0, 100.0),
            (-1, 99.0, 101.0, 99.0),
        )
        for direction, close, upper, lower in cases:
            with self.subTest(direction=direction):
                bars = _flat_bars(5)
                bar = bars[3]
                bars[3] = _candle(3, (100.0, max(101.0, close), min(99.0, close), close))
                frames = _features(bars, **{"3": {
                    "noise_check": True, "noise_upper": upper,
                    "noise_lower": lower, "vwap": 100.0,
                }})
                signals = [_intent(0, direction, 95.0 if direction == 1 else 105.0, 360),
                           _intent(3, direction, 95.0 if direction == 1 else 105.0, 360,
                                   "same_check")]
                result = self._run(bars, signals, features=frames,
                                   approach="utc_noise_momentum", direction="both")

                self.assertEqual(result["trades"][0]["reason"], "noise_exit")
                self.assertEqual(result["trades"][0]["exit_at"], bars[4].t)
                self.assertEqual(result["metrics"]["counts"].get("filled"), 1)
                self.assertEqual(result["metrics"]["counts"].get("occupied_at_open"), 1)
                self.assertTrue(any(event["kind"] == "same_check_exit_suppression"
                                    for event in result["ledger"]))

    def test_channel_amendments_round_away_activate_next_open_and_never_loosen(self) -> None:
        cases = ((1, 95.0, 96.07, 96.0, 94.0),
                 (-1, 105.0, 104.03, 104.1, 106.0))
        for direction, initial_stop, proposed, rounded, loosening in cases:
            with self.subTest(direction=direction):
                bars = _flat_bars(8)
                frames = _features(bars, **{
                    "3": {"hour_close": True, "trail_midpoint": proposed},
                    "7": {"hour_close": True, "trail_midpoint": loosening},
                })
                result = self._run(bars, [_intent(0, direction, initial_stop, 360)],
                                   features=frames, approach="close_channel_24h",
                                   direction="both")
                proposed_events = [e for e in result["ledger"] if e["kind"] == "amendment_proposed"]
                active = [e for e in result["ledger"] if e["kind"] == "amendment_activated"]

                self.assertEqual(len(proposed_events), 1)
                self.assertEqual(proposed_events[0]["bar_index"], 3)
                self.assertAlmostEqual(proposed_events[0]["rounded_stop"], rounded)
                self.assertEqual(len(active), 1)
                self.assertEqual(active[0]["bar_index"], 4)
                self.assertAlmostEqual(result["open_position"]["stop"], rounded)

    def test_close_beyond_unrounded_trail_queues_next_open_exit_not_stop_fill(self) -> None:
        bars = _flat_bars(5)
        bars[3] = _candle(3, (99.5, 100.0, 99.1, 99.23))
        bars[4] = _candle(4, (100.0, 101.0, 99.0, 100.0))
        frames = _features(bars, **{"3": {"hour_close": True, "trail_midpoint": 99.26}})
        result = self._run(bars, [_intent(0, 1, 95.0, 360)], features=frames,
                           approach="close_channel_24h", direction="long")

        exit_event = next(event for event in result["ledger"] if event["kind"] == "exit_decision")
        trade = result["trades"][0]
        self.assertEqual(exit_event["rounded_stop"], 99.2)
        self.assertEqual(exit_event["proposed_stop"], 99.26)
        self.assertEqual(trade["reason"], "trail_exit")
        self.assertEqual(trade["raw_exit"], bars[4].open)
        self.assertNotEqual(trade["raw_exit"], 99.2)

    def test_opening_hard_stop_gap_has_priority_over_queued_channel_exit(self) -> None:
        bars = _flat_bars(5)
        bars[3] = _candle(3, (99.5, 100.0, 99.1, 99.23))
        bars[4] = _candle(4, (94.0, 95.0, 93.5, 94.5))
        frames = _features(bars, **{"3": {"hour_close": True, "trail_midpoint": 99.26}})
        result = self._run(bars, [_intent(0, 1, 95.0, 360)], features=frames,
                           approach="close_channel_24h", direction="long")

        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["reason"], "stop_gap")
        self.assertEqual(result["trades"][0]["raw_exit"], 94.0)
        self.assertFalse(any(event.get("reason") == "trail_exit" and event["kind"] == "exit"
                             for event in result["ledger"]))

    def test_exact_open_funding_belongs_to_carried_position_not_new_entry(self) -> None:
        bars = _flat_bars(4)
        signal = _intent(0, 1, 95.0, 120)
        funding = [
            {"ts": bars[1].t, "rate": 0.01, "mark": 100.0},
            {"ts": bars[2].t, "rate": 0.01, "mark": 100.0},
        ]
        result = self._run(bars, [signal], direction="long", funding=funding)
        position = result["open_position"]
        expected = -position["quantity"] * 100.0 * 0.01 * 1.01

        self.assertAlmostEqual(position["funding"], expected)
        funding_events = [event for event in result["ledger"] if event["kind"] == "funding"]
        self.assertEqual([event["at"] for event in funding_events], [bars[2].t])

    def test_intrabar_uncertain_funding_keeps_debits_and_omits_credits(self) -> None:
        for direction, stop, row, expected_sign in (
                (1, 95.0, (100.0, 101.0, 94.0, 96.0), -1),
                (-1, 105.0, (100.0, 106.0, 99.0, 104.0), 0)):
            with self.subTest(direction=direction):
                bars = _flat_bars(3)
                bars[2] = _candle(2, row)
                funding = [{"ts": bars[2].t + 60_000, "rate": 0.01, "mark": 100.0}]
                result = self._run(bars, [_intent(0, direction, stop, 120)],
                                   direction="both", funding=funding)
                trade = result["trades"][0]
                self.assertEqual(trade["reason"], "stop")
                if expected_sign < 0:
                    self.assertLess(trade["funding"], 0)
                else:
                    self.assertEqual(trade["funding"], 0.0)
                event = next(event for event in result["ledger"] if event["kind"] == "funding")
                self.assertTrue(event["uncertain_exit_order"])

    def test_open_gap_charges_exact_open_funding_but_ignores_later_intrabar_funding(self) -> None:
        bars = _flat_bars(3)
        bars[2] = _candle(2, (94.0, 96.0, 93.5, 95.0))
        funding = [
            {"ts": bars[2].t, "rate": 0.01, "mark": 100.0},
            {"ts": bars[2].t + 60_000, "rate": 0.01, "mark": 100.0},
        ]
        result = self._run(bars, [_intent(0, 1, 95.0, 120)],
                           direction="long", funding=funding)
        trade = result["trades"][0]
        expected = -trade["quantity"] * 100.0 * 0.01 * 1.01

        self.assertEqual(trade["reason"], "stop_gap")
        self.assertAlmostEqual(trade["funding"], expected)
        self.assertEqual([event["at"] for event in result["ledger"] if event["kind"] == "funding"],
                         [bars[2].t])

    def test_cutoff_marks_open_position_and_censors_last_bar_intent(self) -> None:
        bars = [
            _candle(0, (100.0, 101.0, 99.0, 100.0)),
            _candle(1, (100.0, 102.0, 99.0, 101.0)),
        ]
        result = self._run(bars, [_intent(0, 1, 95.0, 360),
                                   _intent(1, 1, 95.0, 360, "cutoff")],
                           direction="long")

        position = result["open_position"]
        self.assertIsNotNone(position)
        self.assertEqual(result["trades"], [])
        self.assertAlmostEqual(result["equity"][-1]["equity"],
                               result["equity"][-1]["cash"] + position["quantity"] * 1.0)
        censored = [event for event in result["ledger"] if event["kind"] == "censored_intent"]
        self.assertEqual([(event["signal_index"], event["expected_fill_at"]) for event in censored],
                         [(1, bars[-1].t + STEP_15M)])
        self.assertNotIn("target", position)

    def test_annual_fold_last_close_intent_cannot_fill_in_next_fold(self) -> None:
        year_start = legacy_campaign.timestamp(2023)
        prior_fold = [legacy.Candle(year_start - STEP_15M, 100, 101, 99, 100, 1)]
        last_intent = _intent(0, 1, 95.0, 120, "prior_fold_last_close")
        prior_result = self._run(prior_fold, [last_intent], direction="long")
        next_fold = [legacy.Candle(year_start, 100, 101, 99, 100, 1),
                     legacy.Candle(year_start + STEP_15M, 100, 101, 99, 100, 1)]
        next_result = self._run(next_fold, [], direction="long")

        self.assertIsNone(prior_result["open_position"])
        self.assertEqual(prior_result["metrics"]["counts"].get("censored_intent"), 1)
        self.assertEqual(next_result["metrics"]["counts"].get("filled", 0), 0)
        self.assertEqual(next_result["trades"], [])


class CampaignBoundaryTests(unittest.TestCase):
    def _copy_admin(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for name in ("protocol.json", "AUTHORIZATION.json", "INPUT_IDENTITIES.json"):
            (root / name).write_bytes((PHASE2_ROOT / name).read_bytes())

    @staticmethod
    def _qualifying_row(protocol: dict) -> dict:
        base = {
            str(year): {
                "net_return_pct": 1.0 if year in (2025, 2026) else 0.0,
                "closed_trades": 50 if year in (2025, 2026) else 0,
            }
            for year in range(2022, 2027)
        }
        stress = {"2025": {"net_return_pct": 0.2},
                  "2026": {"net_return_pct": 0.2}}
        return {
            "base": base,
            "stress": stress,
            "combined": {
                "profit_factor": 1.05,
                "max_fold_drawdown_pct": 10.0,
                "worst_fold_return_pct": -2.0,
                "mean_fold_return_pct": 0.4,
            },
        }

    def test_all_frozen_screen_gates_apply_at_boundaries_and_fail_independently(self) -> None:
        protocol = json.loads((PHASE2_ROOT / "protocol.json").read_text(encoding="utf-8"))
        baseline = self._qualifying_row(protocol)
        self.assertEqual(legacy_campaign.qualifies(baseline, protocol), (True, []))

        cases = (
            ("2025: nonpositive", lambda row: row["base"]["2025"].update(net_return_pct=0.0)),
            ("2026: insufficient", lambda row: row["base"]["2026"].update(closed_trades=29)),
            ("insufficient recent total", lambda row: row["base"]["2025"].update(closed_trades=30)),
            ("profit factor", lambda row: row["combined"].update(profit_factor=1.049)),
            ("drawdown", lambda row: row["combined"].update(max_fold_drawdown_pct=10.01)),
            ("stress return", lambda row: row["stress"]["2026"].update(net_return_pct=-0.2)),
        )
        for expected, mutate in cases:
            with self.subTest(gate=expected):
                row = json.loads(json.dumps(baseline))
                mutate(row)
                qualified, failures = legacy_campaign.qualifies(row, protocol)
                self.assertFalse(qualified)
                self.assertTrue(any(expected in failure.lower() for failure in failures), failures)

    def test_changed_preregistered_settings_are_rejected_by_frozen_admin_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "phase2"
            self._copy_admin(root)
            protocol_path = root / "protocol.json"
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
            protocol["execution"]["risk_fraction"] = 0.003
            protocol_path.write_text(json.dumps(protocol), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Changed administrative identity: protocol.json"):
                campaign.comparison(root, "tampered")
            self.assertFalse((root / "runs").exists())

    def test_invalid_or_existing_run_id_cannot_overwrite_saved_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "phase2"
            self._copy_admin(root)
            for bad_id in ("", "..", "../escape", "run/child"):
                with self.subTest(run_id=bad_id):
                    with self.assertRaisesRegex(ValueError, "Invalid run id"):
                        campaign.comparison(root, bad_id)

            existing = root / "runs" / "kept"
            existing.mkdir(parents=True)
            sentinel = existing / "evidence.txt"
            sentinel.write_text("immutable", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                campaign.comparison(root, "kept")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "immutable")

    def test_mocked_runner_completes_unique_matrix_excludes_controls_and_breaks_ties_by_id(self) -> None:
        class SparseCandles:
            def __init__(self, start: int, step: int, count: int):
                self.start, self.step, self.count = start, step, count

            def __len__(self) -> int:
                return self.count

            def __iter__(self):
                # Data traversal is owned by the scoped resampler and simulator spies.
                return iter(())

            def __getitem__(self, item):
                if isinstance(item, slice):
                    first, stop, stride = item.indices(self.count)
                    if stride != 1:
                        raise AssertionError("campaign must preserve contiguous fold slices")
                    return SparseCandles(self.start + first * self.step, self.step, stop - first)
                if item < 0:
                    item += self.count
                if not 0 <= item < self.count:
                    raise IndexError(item)
                return legacy.Candle(self.start + item * self.step,
                                     100.0, 101.0, 99.0, 100.0, 1.0)

        class SparseQuotes:
            def __init__(self, count: int):
                self.count = count

            def __len__(self) -> int:
                return self.count

            def __getitem__(self, item):
                if isinstance(item, slice):
                    first, stop, stride = item.indices(self.count)
                    return [0.0] * len(range(first, stop, stride))
                return 0.0

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name) / "phase2"

        def run_spy():
            self._copy_admin(root)
            start = legacy_campaign.timestamp(2022)
            end = legacy_campaign.timestamp(2026) + 243 * DAY
            count15 = (end - start) // STEP_15M
            count5 = count15 * 3
            bars5 = SparseCandles(start, STEP_5M, count5)
            bars15 = SparseCandles(start, STEP_15M, count15)
            quote_rows = SparseQuotes(count5)
            boundary_indices = [0]
            for year in range(2022, 2027):
                fold_start = legacy_campaign.timestamp(year)
                fold_end = min(legacy_campaign.timestamp(year + 1), end) if year < 2026 else end
                left = (fold_start - start) // STEP_15M
                right = (fold_end - start) // STEP_15M
                boundary_indices.extend((left, right - 1))
            intents = [successor.Intent(index, 1, 95.0, 120, "independent_fold_edge")
                       for index in sorted(set(boundary_indices)) if index < count15]
            simulation_calls = []
            year_by_start = {legacy_campaign.timestamp(year): year for year in range(2022, 2027)}

            def simulate_spy(part, signals, features, approach, direction, funding, execution):
                year = year_by_start[part[0].t]
                condition = "stress" if execution.slip_bps == 4.0 else "base"
                indices = [signal.index for signal in signals]
                simulation_calls.append((approach, direction, year, condition, indices, len(part)))
                metrics = {
                    "net_return_pct": 1.0,
                    "closed_trades": 50 if year in (2025, 2026) else 10,
                    "gross_profit": 105.0,
                    "gross_loss": 100.0,
                    "fees": 5.0,
                    "funding": 0.0,
                    "max_drawdown_pct": 5.0,
                    "adverse_drawdown_pct": 6.0,
                }
                return {"metrics": metrics, "trades": [], "equity": [],
                        "ledger": [], "open_position": None}

            with mock.patch.object(campaign, "load_candles", return_value=bars5), \
                 mock.patch.object(campaign, "load_quote_turnover", return_value=quote_rows), \
                 mock.patch.object(campaign, "resample_15m", return_value=bars15), \
                 mock.patch.object(campaign, "load_funding", return_value=[
                     {"ts": start + i * 8 * HOUR, "rate": 0.0, "mark": 100.0}
                     for i in range(5112)]), \
                 mock.patch.object(campaign, "build_features", return_value=[]), \
                 mock.patch.object(campaign, "detect", side_effect=lambda *_: (intents, [])), \
                 mock.patch.object(campaign, "simulate", side_effect=simulate_spy):
                output = campaign.comparison(root, "spy-run")
            return output, simulation_calls

        output, simulation_calls = run_spy()
        summary = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["completed_annual_runs"], 120)
        self.assertEqual(len(summary["candidates"]), 9)
        self.assertEqual(len(summary["controls"]), 3)
        self.assertEqual(summary["selected"], "close_channel_24h-both",
                         "equal eligible rows resolve to the lexicographically first context id")
        self.assertTrue(all(not row["qualified"] for row in summary["controls"]))
        self.assertTrue(all("benchmark only" in " ".join(row["screen_failures"])
                            for row in summary["controls"]))
        self.assertEqual(len(simulation_calls), 120)
        keys = [(a, d, y, c) for a, d, y, c, _, _ in simulation_calls]
        self.assertEqual(len(set(keys)), 120)
        for approach, direction, year, condition, indices, part_length in simulation_calls:
            with self.subTest(approach=approach, direction=direction, year=year,
                              condition=condition):
                self.assertEqual(indices, [0, part_length - 1],
                                 "the fold start and last in-fold observing bar belong to that fold")
        before = json.loads((output / "identities_before_run.json").read_text(encoding="utf-8"))
        after = json.loads((output / "identities_after_run.json").read_text(encoding="utf-8"))
        self.assertEqual(before, after)
        trials = [json.loads(line) for line in (output / "trials.jsonl").read_text(encoding="utf-8").splitlines()]
        cumulative = [json.loads(line) for line in (root / "cumulative_trials.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(trials), 120)
        self.assertEqual(len(cumulative), 120)
        self.assertEqual(len({(row["trial_id"], row["year"], row["condition"]) for row in trials}), 120)


