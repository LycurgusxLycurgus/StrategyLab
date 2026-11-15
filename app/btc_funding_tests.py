"""Independent constructed tests for the frozen BTC funding-state contract."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from app import btc_funding as strategy
from app import btc_funding_broker as broker
from app import btc_funding_campaign as campaign
from app.btc_liquidity import Candle


MINUTE = 60_000
DAY = 86_400_000
SLOT = 8 * 60 * MINUTE
START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() * 1000)
CANDIDATE, STALE, CONTINUOUS = strategy.APPROACHES


def _bar(
    index: int,
    *,
    minutes: int = 5,
    start: int = START,
    open_: float = 100.0,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
) -> Candle:
    close = open_ if close is None else close
    return Candle(
        start + index * minutes * MINUTE,
        open_,
        max(open_, close) + 1.0 if high is None else high,
        min(open_, close) - 1.0 if low is None else low,
        close,
        1.0,
    )


def _bars(
    count: int,
    *,
    minutes: int = 5,
    start: int = START,
    open_: float = 100.0,
    close: float | None = None,
) -> list[Candle]:
    return [
        _bar(i, minutes=minutes, start=start, open_=open_, close=close)
        for i in range(count)
    ]


def _event(ts: int, rate: float = 0.0, mark: float = 100.0) -> dict:
    return {"ts": ts, "rate": rate, "mark": mark}


def _history(
    count: int,
    *,
    start: int = START,
    rate: float = 0.0002,
) -> list[dict]:
    return [_event(start + i * SLOT, rate) for i in range(count)]


def _intent(
    bars: list[Candle],
    index: int = 0,
    *,
    minutes: int = 5,
    approach: str = CANDIDATE,
    event_ts: int | None = None,
    source_event_ts: int | None = None,
) -> strategy.Intent:
    step = minutes * MINUTE
    if event_ts is None:
        event_ts = bars[index].t + 6
    observation = ((event_ts + 1) // step + 1) * step
    if source_event_ts is None:
        source_event_ts = event_ts
    return strategy.Intent(
        index=index,
        event_ts=event_ts,
        source_event_ts=source_event_ts,
        observation_at=observation,
        decision_at=observation + 1,
        fill_at=observation + step,
        hold_minutes=None if approach == CONTINUOUS else 1440,
        reason=approach,
    )


def _funding_for(signals: list[strategy.Intent], *extra: dict) -> list[dict]:
    rows = [*(_event(s.event_ts) for s in signals), *extra]
    return sorted(rows, key=lambda row: row["ts"])


def _features_for_detection(
    event_ts: int,
    *,
    low_state: bool | None = True,
    lag_low_state: bool | None = True,
    common_ready: bool = True,
    lag_event_ts: int | None = None,
) -> dict:
    return {
        "event_ts": event_ts,
        "slot": event_ts // SLOT,
        "prior_count": 540,
        "less_count": 40,
        "equal_count": 1,
        "percentile": 0.075,
        "low_state": low_state,
        "common_ready": common_ready,
        "lag_low_state": lag_low_state,
        "lag_event_ts": event_ts - 21 * SLOT if lag_event_ts is None else lag_event_ts,
    }


def _metrics(
    *,
    return_pct: float = 2.0,
    trades: int = 50,
    gross_profit: float = 110.0,
    gross_loss: float = 100.0,
    drawdown: float = 9.0,
    net_profit: float = 2_000.0,
    closed_net: float = 200.0,
    notional_days: float = 100_000.0,
    entry_weeks: dict[str, float] | None = None,
    status: str = "OK",
) -> dict:
    return {
        "status": status,
        "net_return_pct": return_pct,
        "net_profit": net_profit,
        "closed_trades": trades,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "closed_net_pnl": closed_net,
        "max_drawdown_pct": drawdown,
        "adverse_drawdown_pct": drawdown + 0.5,
        "fees": 10.0,
        "funding": 0.0,
        "notional_days": notional_days,
        "entry_week_net_pnl": entry_weeks or {"2025-01-06": closed_net},
    }


def _screen_fixture() -> list[dict]:
    rows = []
    for minutes in (5, 15):
        for approach in strategy.APPROACHES:
            recent_return = {CANDIDATE: 2.0, STALE: 1.0, CONTINUOUS: 0.5}[approach]
            base = {}
            stress = {}
            severe = {}
            for year in range(2022, 2027):
                recent = year in (2025, 2026)
                base[str(year)] = _metrics(
                    return_pct=recent_return if recent else 0.5,
                    trades=50 if recent else 5,
                    net_profit=2_000 if approach == CANDIDATE else 1_000,
                    closed_net=200,
                    entry_weeks=(
                        {"2025-01-06": 100.0, "2025-12-29": 100.0}
                        if year == 2025
                        else {"2025-12-29": 100.0, "2026-01-05": 100.0}
                    ),
                )
                stress[str(year)] = _metrics(
                    return_pct=0.5 if recent else 0.1,
                    trades=50 if recent else 5,
                    net_profit=500,
                    closed_net=200,
                )
                severe[str(year)] = _metrics(
                    return_pct=-1.0,
                    trades=50 if recent else 5,
                    net_profit=-1_000,
                    closed_net=-100,
                )
            rows.append(
                {
                    "id": f"{minutes}m-{approach}",
                    "minutes": minutes,
                    "approach": approach,
                    "base": base,
                    "stress": stress,
                    "severe_sensitivity": severe,
                }
            )
    return rows


def _tmp_campaign_authority(root: Path, project: Path) -> tuple[dict, dict]:
    """Build a temporary, correctly authenticated copy without running economics."""
    protocol_path = project / campaign.ROOT / "protocol.json"
    protocol_bytes = protocol_path.read_bytes()
    (root / "protocol.json").write_bytes(protocol_bytes)
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    raw = project / protocol["data_root"]
    identities = {
        p.relative_to(project).as_posix(): campaign.sha(p)
        for p in sorted(raw.glob("*.json"))
    }
    manifest = raw / "manifest.json"
    identities[manifest.relative_to(project).as_posix()] = campaign.sha(manifest)
    identity_path = root / "INPUT_IDENTITIES.json"
    identity_path.write_text(json.dumps(identities), encoding="utf-8")
    auth = {
        "protocol_sha256": campaign.sha(root / "protocol.json"),
        "input_identities_sha256": campaign.sha(identity_path),
    }
    (root / "AUTHORIZATION.json").write_text(json.dumps(auth), encoding="utf-8")
    return protocol, identities


class EventFeatureContractTests(unittest.TestCase):
    def test_midrank_ties_use_exact_integer_tenth_boundary(self) -> None:
        history = _history(563)
        # At event 561 the 180-day window is indices 21..560: 53 lower,
        # two equal, and 485 higher rates. Midrank is exactly 10%.
        for index in range(21, 74):
            history[index]["rate"] = 0.01
        history[74]["rate"] = 0.02
        history[75]["rate"] = 0.02
        for index in range(76, 561):
            history[index]["rate"] = 0.03
        history[561]["rate"] = 0.02

        features = strategy.build_event_features(history, START)
        exact = features[561]
        self.assertEqual((exact["prior_count"], exact["less_count"], exact["equal_count"]), (540, 53, 2))
        self.assertEqual(exact["percentile"], 0.1)
        self.assertTrue(exact["low_state"])

        history[561]["rate"] = 0.020001
        above = strategy.build_event_features(history, START)[561]
        self.assertEqual((above["less_count"], above["equal_count"]), (55, 0))
        self.assertFalse(above["low_state"])

    def test_positive_funding_rate_can_be_a_low_state(self) -> None:
        history = _history(562, rate=0.0002)
        history[561]["rate"] = 0.0001

        row = strategy.build_event_features(history, START)[561]

        self.assertGreater(history[561]["rate"], 0)
        self.assertTrue(row["low_state"])
        self.assertLessEqual(row["percentile"], 0.1)

    def test_lookback_includes_left_edge_excludes_current_and_evicts_expired_event(self) -> None:
        history = _history(542, rate=0.02)
        history[0]["rate"] = 0.01
        history[540]["rate"] = 0.02
        history[541]["rate"] = 0.02

        features = strategy.build_event_features(history, START)

        at_180_days = features[540]
        one_slot_later = features[541]
        self.assertEqual((at_180_days["prior_count"], at_180_days["less_count"], at_180_days["equal_count"]), (540, 1, 539))
        self.assertEqual((one_slot_later["prior_count"], one_slot_later["less_count"], one_slot_later["equal_count"]), (540, 0, 540))

    def test_full_lookback_and_common_187_day_warmup_start_on_their_exact_boundaries(self) -> None:
        features = strategy.build_event_features(_history(563), START)

        self.assertIsNone(features[539]["low_state"])
        self.assertEqual(features[540]["prior_count"], 540)
        self.assertIsNotNone(features[540]["low_state"])
        self.assertFalse(features[560]["common_ready"])
        self.assertTrue(features[561]["common_ready"])
        self.assertEqual(features[561]["lag_event_ts"], features[540]["event_ts"])

    def test_history_requires_the_first_slot_and_rejects_internal_gap_or_duplicate(self) -> None:
        history = _history(562)
        with self.assertRaisesRegex(ValueError, "coverage does not begin"):
            strategy.build_event_features(history[1:], START)

        missing = _history(562)
        del missing[100]
        with self.assertRaisesRegex(ValueError, "slots incomplete"):
            strategy.build_event_features(missing, START)

        duplicate = _history(562)
        duplicate[100] = dict(duplicate[99])
        with self.assertRaisesRegex(ValueError, "slots incomplete"):
            strategy.build_event_features(duplicate, START)

    def test_history_rejects_nonfinite_rates_invalid_marks_and_bad_schema(self) -> None:
        cases = []
        bad_rate = _history(2)
        bad_rate[1]["rate"] = math.nan
        cases.append((bad_rate, "Invalid funding event"))
        bad_mark = _history(2)
        bad_mark[1]["mark"] = math.inf
        cases.append((bad_mark, "Invalid funding event"))
        no_mark = _history(2)
        del no_mark[1]["mark"]
        cases.append((no_mark, "Invalid funding schema"))
        for rows, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    strategy.build_event_features(rows, START)

    def test_lagged_state_is_from_actual_slot_21_events_old_not_current_state(self) -> None:
        history = _history(563, rate=0.02)
        history[540]["rate"] = 0.001
        history[561]["rate"] = 0.02
        history[562]["rate"] = 0.001
        features = strategy.build_event_features(history, START)

        first = features[561]
        second = features[562]
        self.assertTrue(first["lag_low_state"])
        self.assertFalse(first["low_state"])
        self.assertEqual(first["lag_event_ts"], history[540]["ts"])
        self.assertTrue(second["low_state"])
        self.assertFalse(second["lag_low_state"])
        self.assertEqual(second["lag_event_ts"], history[541]["ts"])

    def test_feature_prefix_does_not_change_when_future_rates_change(self) -> None:
        history = _history(563, rate=0.02)
        history[540]["rate"] = 0.001
        cut = 562
        baseline = strategy.build_event_features(history, START)
        changed = [dict(row) for row in history]
        changed[-1]["rate"] = 9.0
        changed[-1]["mark"] = 10_000.0
        after = strategy.build_event_features(changed, START)

        self.assertEqual(baseline[:cut], after[:cut])


class DetectorContractTests(unittest.TestCase):
    def test_raw_timestamp_jitter_maps_to_expected_5m_and_15m_observation_and_fill(self) -> None:
        for minutes, expected_fill_minutes in ((5, 10), (15, 30)):
            with self.subTest(minutes=minutes):
                bars = _bars(4, minutes=minutes)
                event_ts = START + 6
                signals, events = strategy.detect(
                    bars, minutes, [_features_for_detection(event_ts)], CANDIDATE
                )
                signal = signals[0]
                self.assertEqual(signal.index, 0)
                self.assertEqual(signal.event_ts, event_ts)
                self.assertEqual(signal.observation_at, START + minutes * MINUTE)
                self.assertEqual(signal.decision_at, START + minutes * MINUTE + 1)
                self.assertEqual(signal.fill_at, START + expected_fill_minutes * MINUTE)
                self.assertEqual(events[0]["event_ts"], event_ts)

    def test_one_millisecond_boundary_is_strict_and_does_not_backdate_observation(self) -> None:
        minutes = 5
        bars = _bars(5, minutes=minutes)
        just_before_close = START + 5 * MINUTE - 2
        exact_after_plus_one = START + 5 * MINUTE - 1
        first, _ = strategy.detect(
            bars, minutes, [_features_for_detection(just_before_close)], CANDIDATE
        )
        second, _ = strategy.detect(
            bars, minutes, [_features_for_detection(exact_after_plus_one)], CANDIDATE
        )

        self.assertEqual((first[0].index, first[0].observation_at, first[0].fill_at), (0, START + 5 * MINUTE, START + 10 * MINUTE))
        self.assertEqual((second[0].index, second[0].observation_at, second[0].fill_at), (1, START + 10 * MINUTE, START + 15 * MINUTE))

    def test_candidate_and_stale_control_use_their_own_current_and_lagged_classes(self) -> None:
        event = START + 6
        features = _features_for_detection(event, low_state=False, lag_low_state=True)
        bars = _bars(4)

        candidate, _ = strategy.detect(bars, 5, [features], CANDIDATE)
        stale, stale_events = strategy.detect(bars, 5, [features], STALE)

        self.assertEqual(candidate, [])
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].source_event_ts, event - 21 * SLOT)
        self.assertEqual(stale_events[0]["source_event_ts"], event - 21 * SLOT)
        self.assertEqual(stale[0].reason, STALE)

    def test_real_feature_lag_is_used_when_current_and_21_slot_classes_disagree(self) -> None:
        funding = _history(563, rate=0.02)
        funding[540]["rate"] = 0.001
        funding[561]["rate"] = 0.02
        funding[562]["rate"] = 0.001
        features = strategy.build_event_features(funding, START)
        first_ts, second_ts = funding[561]["ts"], funding[562]["ts"]
        bars_start = first_ts - 5 * MINUTE
        bars = _bars(100, start=bars_start)
        window = [features[561], features[562]]

        candidate, _ = strategy.detect(bars, 5, window, CANDIDATE)
        stale, _ = strategy.detect(bars, 5, window, STALE)

        self.assertEqual([s.event_ts for s in candidate], [second_ts])
        self.assertEqual([s.event_ts for s in stale], [first_ts])
        self.assertEqual(stale[0].source_event_ts, funding[540]["ts"])

    def test_detector_prefix_outputs_are_unchanged_by_later_opportunities(self) -> None:
        funding = _history(563, rate=0.02)
        funding[540]["rate"] = 0.001
        funding[561]["rate"] = 0.02
        funding[562]["rate"] = 0.001
        features = strategy.build_event_features(funding, START)
        first_ts = funding[561]["ts"]
        bars = _bars(100, start=first_ts - 5 * MINUTE)
        prefix_bars = bars[:96]
        prefix_end = prefix_bars[-1].t + 5 * MINUTE

        prefix_signals, prefix_events = strategy.detect(
            prefix_bars, 5, features[561:562], CANDIDATE
        )
        full_signals, full_events = strategy.detect(
            bars, 5, features[561:563], CANDIDATE
        )

        self.assertEqual(prefix_signals, [s for s in full_signals if s.event_ts < prefix_end])
        self.assertEqual(prefix_events, [e for e in full_events if e["event_ts"] < prefix_end])

    def test_continuous_control_ignores_classification_and_has_no_time_exit(self) -> None:
        features = [
            _features_for_detection(START + 6, low_state=False, lag_low_state=False),
            _features_for_detection(START + SLOT + 6, low_state=None, lag_low_state=None),
        ]
        bars = _bars(100)

        signals, _ = strategy.detect(bars, 5, features, CONTINUOUS)

        self.assertEqual([s.event_ts for s in signals], [row["event_ts"] for row in features])
        self.assertTrue(all(s.hold_minutes is None for s in signals))

    def test_event_without_full_observation_bar_is_not_emitted(self) -> None:
        bars = _bars(1)
        features = [_features_for_detection(START + 5 * MINUTE + 6)]

        signals, events = strategy.detect(bars, 5, features, CANDIDATE)

        self.assertEqual(signals, [])
        self.assertEqual(events, [])


class BrokerContractTests(unittest.TestCase):
    def test_5m_entry_uses_two_index_offset_and_fee_inclusive_ten_percent_quantity(self) -> None:
        bars = _bars(4)
        signal = _intent(bars)
        execution = strategy.FundingExecution()

        result = broker.simulate(bars, [signal], 5, CANDIDATE, _funding_for([signal]), execution)

        position = result["open_position"]
        self.assertEqual(result["status"], "OK")
        self.assertEqual((position["signal_index"], position["entry_index"]), (0, 2))
        self.assertEqual((position["decision_at"], position["entry_at"]), (signal.decision_at, bars[2].t))
        entry = bars[2].open * (1 + execution.slip_bps / 10_000)
        expected = math.floor(
            min(
                execution.initial_capital * execution.entry_notional_fraction
                / (entry * (1 + execution.fee_bps / 10_000)),
                execution.max_quantity,
            )
            / execution.quantity_step
            + 1e-9
        ) * execution.quantity_step
        self.assertAlmostEqual(position["quantity"], expected)
        self.assertLessEqual(
            position["quantity"] * entry * (1 + execution.fee_bps / 10_000),
            execution.initial_capital * execution.entry_notional_fraction,
        )

    def test_15m_entry_keeps_raw_event_clock_and_waits_until_0830(self) -> None:
        bars = _bars(4, minutes=15)
        event_ts = START + 6
        signal = _intent(bars, minutes=15, event_ts=event_ts)

        result = broker.simulate(bars, [signal], 15, CANDIDATE, _funding_for([signal]))

        self.assertEqual(result["open_position"]["entry_at"], START + 30 * MINUTE)
        self.assertEqual(result["open_position"]["event_ts"], event_ts)
        self.assertEqual(result["open_position"]["observation_at"], START + 15 * MINUTE)

    def test_fixed_24_hour_hold_crosses_midnight_and_weekend_without_daily_flatten(self) -> None:
        friday_2350 = int(datetime(2022, 1, 7, 23, 50, tzinfo=UTC).timestamp() * 1000)
        bars = _bars(291, start=friday_2350)
        bars[290] = _bar(290, start=friday_2350, open_=101.0, close=101.0)
        signal = _intent(bars, event_ts=friday_2350 + 6)
        result = broker.simulate(bars, [signal], 5, CANDIDATE, _funding_for([signal]))

        trade = result["trades"][0]
        self.assertEqual(datetime.fromtimestamp(trade["entry_at"] / 1000, UTC).weekday(), 5)
        self.assertEqual(datetime.fromtimestamp(trade["exit_at"] / 1000, UTC).weekday(), 6)
        self.assertEqual(trade["exit_at"] - trade["entry_at"], 24 * 60 * MINUTE)
        self.assertEqual(trade["reason"], "time_exit")

    def test_exact_entry_open_does_not_receive_trigger_or_same_open_settlement(self) -> None:
        bars = _bars(4)
        signal = _intent(bars)
        same_entry_open = _event(bars[2].t, rate=0.01)
        funding = _funding_for([signal], same_entry_open)

        result = broker.simulate(bars, [signal], 5, CANDIDATE, funding)

        self.assertEqual(result["metrics"]["funding"], 0.0)
        self.assertEqual([row for row in result["ledger"] if row["kind"] == "funding"], [])

    def test_future_debit_credit_and_coincident_exit_funding_are_owned_and_buffered(self) -> None:
        bars = _bars(291)
        bars[290] = _bar(290, open_=100.0, close=100.0)
        signal = _intent(bars)
        exit_at = bars[290].t
        events = [
            _event(signal.event_ts),
            _event(bars[2].t, rate=0.01),
            _event(bars[98].t, rate=0.001),
            _event(bars[194].t, rate=-0.001),
            _event(exit_at, rate=0.001),
        ]

        result = broker.simulate(bars, [signal], 5, CANDIDATE, sorted(events, key=lambda r: r["ts"]))

        trade = result["trades"][0]
        quantity = trade["quantity"]
        expected = -quantity * 100.0 * 0.001 * 1.01 + quantity * 100.0 * 0.001 * 0.99 - quantity * 100.0 * 0.001 * 1.01
        self.assertAlmostEqual(trade["funding"], expected)
        self.assertEqual(trade["exit_at"], exit_at)
        self.assertEqual([row["at"] for row in result["ledger"] if row["kind"] == "funding"], [bars[98].t, bars[194].t, exit_at])

    def test_exact_open_funding_debit_precedes_time_exit_and_cannot_be_hidden_by_exit_profit(self) -> None:
        bars = _bars(291)
        bars[290] = _bar(290, open_=2_200.0, close=2_200.0)
        signal = _intent(bars)
        funding = _funding_for(
            [signal],
            _event(bars[290].t, rate=0.5, mark=2_200.0),
        )

        result = broker.simulate(bars, [signal], 5, CANDIDATE, funding)

        self.assertEqual(result["status"], "INVALID_EXECUTION")
        self.assertEqual(result["trades"], [])
        self.assertIsNotNone(result["open_position"])
        kinds = [row["kind"] for row in result["ledger"]]
        self.assertLess(kinds.index("funding"), kinds.index("invalid_execution"))
        self.assertNotIn("exit", kinds)

    def test_occupied_decision_is_suppressed_and_a_later_flat_decision_can_fill(self) -> None:
        bars = _bars(389)
        first = _intent(bars, 0)
        while_held = _intent(bars, 96)
        after_exit = _intent(bars, 384)
        signals = [first, while_held, after_exit]

        result = broker.simulate(bars, signals, 5, CANDIDATE, _funding_for(signals))

        counts = result["metrics"]["counts"]
        self.assertEqual(counts["occupied_at_decision"], 1)
        self.assertEqual(counts["filled"], 2)
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["open_position"]["signal_index"], after_exit.index)

        # A decision one bar before the scheduled exit is still occupied. A
        # decision at the exit open runs after the exit and can queue the next
        # strictly later open.
        edge_bars = _bars(292)
        initial = _intent(edge_bars, 0)
        before_exit = _intent(edge_bars, 288)
        at_exit = _intent(edge_bars, 289)
        edge_signals = [initial, before_exit, at_exit]
        edge = broker.simulate(
            edge_bars,
            edge_signals,
            5,
            CANDIDATE,
            _funding_for(edge_signals),
        )
        self.assertEqual(edge["metrics"]["counts"]["occupied_at_decision"], 1)
        self.assertEqual(edge["trades"][0]["exit_at"], edge_bars[290].t)
        self.assertEqual(edge["open_position"]["entry_at"], edge_bars[291].t)

    def test_competing_same_open_orders_are_not_retried_after_one_fills(self) -> None:
        bars = _bars(300)
        first = _intent(bars, 0, event_ts=START + 6)
        second = _intent(bars, 0, event_ts=START + 7)

        result = broker.simulate(
            bars, [first, second], 5, CANDIDATE, _funding_for([first, second])
        )

        counts = result["metrics"]["counts"]
        self.assertEqual(counts["filled"], 1)
        self.assertEqual(counts["occupied_at_open"], 1)
        self.assertEqual(result["metrics"]["counts"].get("queued", 0), 2)
        self.assertEqual(len(result["trades"]), 1)

    def test_minimum_quantity_and_notional_rejections_expire_without_retry(self) -> None:
        bars = _bars(6)
        signal = _intent(bars)
        too_small_cash = strategy.FundingExecution(initial_capital=400.0)

        result = broker.simulate(
            bars, [signal], 5, CANDIDATE, _funding_for([signal]), too_small_cash
        )

        self.assertEqual(result["metrics"]["counts"]["size_rejected"], 1)
        self.assertEqual(result["metrics"]["counts"].get("filled", 0), 0)
        self.assertIsNone(result["open_position"])

        below_min_quantity = strategy.FundingExecution(initial_capital=0.5)
        rejected = broker.simulate(
            bars, [signal], 5, CANDIDATE, _funding_for([signal]), below_min_quantity
        )
        self.assertEqual(rejected["metrics"]["counts"]["size_rejected"], 1)

    def test_maximum_quantity_caps_fee_inclusive_target(self) -> None:
        bars = _bars(4)
        signal = _intent(bars)
        execution = strategy.FundingExecution(
            initial_capital=1_000_000.0,
            entry_notional_fraction=0.5,
            max_quantity=2.0,
        )

        result = broker.simulate(
            bars, [signal], 5, CANDIDATE, _funding_for([signal]), execution
        )

        self.assertEqual(result["open_position"]["quantity"], 2.0)

    def test_close_and_adverse_marks_apply_exit_slippage_and_fee_without_closing(self) -> None:
        bars = _bars(4, close=101.0)
        signal = _intent(bars, approach=CONTINUOUS)
        execution = strategy.FundingExecution(fee_bps=6.0, slip_bps=2.0)
        result = broker.simulate(
            bars, [signal], 5, CONTINUOUS, _funding_for([signal]), execution
        )

        position = result["open_position"]
        final = result["equity"][-1]
        slipped_close = bars[-1].close * (1 - execution.slip_bps / 10_000)
        self.assertEqual(result["trades"], [])
        self.assertIsNone(result["metrics"]["profit_factor"])
        self.assertAlmostEqual(
            final["equity"],
            final["cash"] + position["quantity"] * (slipped_close - position["entry"])
            - slipped_close * position["quantity"] * execution.fee_bps / 10_000,
        )
        self.assertAlmostEqual(
            result["metrics"]["estimated_exit_fee"],
            slipped_close * position["quantity"] * execution.fee_bps / 10_000,
        )
        self.assertAlmostEqual(
            result["metrics"]["estimated_exit_slippage"],
            bars[-1].close * position["quantity"] * execution.slip_bps / 10_000,
        )
        self.assertAlmostEqual(result["metrics"]["fees"], position["entry_fee"])

    def test_positive_intrabar_funding_credit_cannot_mask_earlier_adverse_low(self) -> None:
        bars = _bars(4)
        bars[2] = _bar(2, low=90.0, high=101.0, close=100.0)
        signal = _intent(bars)
        funding = _funding_for(
            [signal], _event(bars[2].t + 1, rate=-0.001, mark=100.0)
        )

        result = broker.simulate(bars, [signal], 5, CANDIDATE, funding)

        position = result["open_position"]
        fill = next(row for row in result["ledger"] if row["kind"] == "filled")
        pre_credit_cash = 100_000.0 - fill["entry_fee"]
        low_mark = bars[2].low * (1 - 2 / 10_000)
        expected = pre_credit_cash + position["quantity"] * (low_mark - position["entry"]) - low_mark * position["quantity"] * 6 / 10_000
        bar = result["equity"][2]
        self.assertGreater(position["funding"], 0)
        self.assertAlmostEqual(bar["adverse_equity"], expected)
        self.assertLess(bar["adverse_equity"], bar["cash"] + position["funding"])

    def test_notional_days_use_quantity_after_open_and_zero_exposure_is_undefined(self) -> None:
        bars = _bars(4)
        signal = _intent(bars, approach=CONTINUOUS)
        open_result = broker.simulate(
            bars, [signal], 5, CONTINUOUS, _funding_for([signal])
        )
        quantity = open_result["open_position"]["quantity"]
        expected = quantity * 100.0 * (5 / 1440) * 2
        self.assertAlmostEqual(open_result["metrics"]["notional_days"], expected)
        self.assertAlmostEqual(
            open_result["metrics"]["net_bps_per_notional_day"],
            10_000 * open_result["metrics"]["net_profit"] / expected,
        )

        flat = broker.simulate(bars, [], 5, CANDIDATE, [])
        self.assertEqual(flat["metrics"]["notional_days"], 0.0)
        self.assertIsNone(flat["metrics"]["net_bps_per_notional_day"])

    def test_cutoff_censors_open_position_and_unfillable_tail_intent(self) -> None:
        bars = _bars(4)
        tail_signal = _intent(bars, 2)
        result = broker.simulate(
            bars, [tail_signal], 5, CANDIDATE, _funding_for([tail_signal])
        )
        self.assertIsNone(result["open_position"])
        self.assertEqual(result["metrics"]["counts"]["censored_intent"], 1)

        longer = _bars(4)
        signal = _intent(longer, approach=CONTINUOUS)
        open_result = broker.simulate(
            longer, [signal], 5, CONTINUOUS, _funding_for([signal])
        )
        self.assertIsNotNone(open_result["open_position"])
        self.assertEqual(open_result["metrics"]["counts"]["censored_position"], 1)
        self.assertEqual(open_result["trades"], [])

    def test_invalid_funding_order_or_mark_is_rejected_at_broker_boundary(self) -> None:
        bars = _bars(4)
        signal = _intent(bars)
        good = _funding_for([signal])
        bad_order = [good[0], _event(signal.event_ts - 1)]
        bad_mark = [_event(signal.event_ts, mark=0.0)]
        for funding in (bad_order, bad_mark):
            with self.subTest(funding=funding):
                with self.assertRaisesRegex(ValueError, "Invalid funding"):
                    broker.simulate(bars, [signal], 5, CANDIDATE, funding)

        with self.assertRaisesRegex(ValueError, "Invalid intent ownership"):
            broker.simulate(
                bars,
                [replace(signal, event_ts=signal.event_ts + 1)],
                5,
                CANDIDATE,
                good,
            )
        with self.assertRaisesRegex(ValueError, "Invalid intent clock"):
            broker.simulate(
                bars, [replace(signal, index=1)], 5, CANDIDATE, good
            )
        with self.assertRaisesRegex(ValueError, "Invalid source event"):
            broker.simulate(
                bars,
                [replace(signal, source_event_ts=signal.event_ts - SLOT)],
                5,
                CANDIDATE,
                good,
            )


class CampaignGateTests(unittest.TestCase):
    def _screen(self, rows: list[dict] | None = None) -> list[dict]:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads(
            (root / campaign.ROOT / "protocol.json").read_text(encoding="utf-8")
        )
        return campaign.screen_rows(_screen_fixture() if rows is None else rows, protocol)

    def test_frozen_protocol_validates_and_rejects_mutated_authority_or_matrix(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads(
            (root / campaign.ROOT / "protocol.json").read_text(encoding="utf-8")
        )
        self.assertTrue(campaign.validate_protocol(protocol))
        changed = dict(protocol)
        changed["phase2_execution_authorized"] = False
        with self.assertRaisesRegex(ValueError, "Protocol differs from frozen contract"):
            campaign.validate_protocol(changed)
        changed = dict(protocol)
        changed["candidate_contexts"] = []
        with self.assertRaisesRegex(ValueError, "Protocol differs from frozen contract"):
            campaign.validate_protocol(changed)

    def test_complete_screen_qualifies_candidate_only_and_keeps_controls_diagnostic(self) -> None:
        rows = self._screen()

        candidates = [row for row in rows if row["approach"] == CANDIDATE]
        controls = [row for row in rows if row["approach"] != CANDIDATE]
        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(row["qualified"] for row in candidates))
        self.assertTrue(all(not row["qualified"] for row in controls))
        self.assertTrue(all(row["control"] for row in controls))
        self.assertEqual(
            next(row for row in candidates if row["minutes"] == 5)["recent_entry_week_net_pnl"]["2025-12-29"],
            200.0,
        )

    def test_screen_rejects_missing_or_duplicate_context_matrix(self) -> None:
        rows = _screen_fixture()
        with self.assertRaisesRegex(ValueError, "Incomplete context matrix"):
            self._screen(rows[:-1])
        duplicate = list(rows)
        duplicate[-1] = dict(duplicate[0])
        with self.assertRaisesRegex(ValueError, "Incomplete context matrix"):
            self._screen(duplicate)

        rows = _screen_fixture()
        del rows[0]["severe_sensitivity"]["2026"]
        with self.assertRaisesRegex(ValueError, "Incomplete fold matrix"):
            self._screen(rows)

    def test_screen_enforces_recent_returns_trade_counts_and_combined_pf_drawdown(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CANDIDATE)
        candidate["base"]["2025"]["net_return_pct"] = 0.0
        candidate["base"]["2026"]["closed_trades"] = 29
        candidate["base"]["2024"]["gross_loss"] = 10_000.0
        candidate["base"]["2023"]["max_drawdown_pct"] = 10.1

        screened = self._screen(rows)
        result = next(row for row in screened if row["minutes"] == 5 and row["approach"] == CANDIDATE)

        self.assertFalse(result["qualified"])
        failures = " ".join(result["screen_failures"])
        self.assertIn("2025: nonpositive base return", failures)
        self.assertIn("2026: insufficient closed trades", failures)
        self.assertIn("profit factor", failures)
        self.assertIn("drawdown", failures)

    def test_recent_standard_stress_must_be_strictly_positive(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 15 and row["approach"] == CANDIDATE)
        candidate["stress"]["2025"]["net_return_pct"] = 0.0
        candidate["stress"]["2026"]["net_return_pct"] = 0.0

        result = next(
            row for row in self._screen(rows)
            if row["minutes"] == 15 and row["approach"] == CANDIDATE
        )

        self.assertFalse(result["qualified"])
        self.assertIn("recent stress return nonpositive", result["screen_failures"])

    def test_candidate_must_strictly_beat_same_grid_stale_control(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CANDIDATE)
        stale = next(row for row in rows if row["minutes"] == 5 and row["approach"] == STALE)
        candidate["base"]["2025"]["net_return_pct"] = 1.0
        candidate["base"]["2026"]["net_return_pct"] = 1.0
        stale["base"]["2025"]["net_return_pct"] = 1.0
        stale["base"]["2026"]["net_return_pct"] = 1.0

        result = next(
            row for row in self._screen(rows)
            if row["minutes"] == 5 and row["approach"] == CANDIDATE
        )

        self.assertFalse(result["qualified"])
        self.assertIn("recent base return does not exceed stale control", result["screen_failures"])

    def test_recent_efficiency_must_beat_continuous_and_have_both_denominators(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CANDIDATE)
        continuous = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CONTINUOUS)
        for year in ("2025", "2026"):
            candidate["base"][year]["net_profit"] = 1_000.0
            candidate["base"][year]["notional_days"] = 100_000.0
            continuous["base"][year]["net_profit"] = 1_000.0
            continuous["base"][year]["notional_days"] = 100_000.0

        equal = next(
            row for row in self._screen(rows)
            if row["minutes"] == 5 and row["approach"] == CANDIDATE
        )
        self.assertFalse(equal["qualified"])
        self.assertIn("recent return per notional-day does not exceed continuous control", equal["screen_failures"])

        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 15 and row["approach"] == CANDIDATE)
        candidate["base"]["2025"]["notional_days"] = 0.0
        candidate["base"]["2026"]["notional_days"] = 0.0
        undefined = next(
            row for row in self._screen(rows)
            if row["minutes"] == 15 and row["approach"] == CANDIDATE
        )
        self.assertFalse(undefined["qualified"])
        self.assertIn("notional-day", " ".join(undefined["screen_failures"]))

    def test_best_entry_week_is_merged_across_recent_fold_boundary(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CANDIDATE)
        candidate["base"]["2025"]["closed_net_pnl"] = 20.0
        candidate["base"]["2025"]["entry_week_net_pnl"] = {"2025-12-29": 100.0, "2025-01-06": -80.0}
        candidate["base"]["2026"]["closed_net_pnl"] = 20.0
        candidate["base"]["2026"]["entry_week_net_pnl"] = {"2025-12-29": 100.0, "2026-01-05": -80.0}

        result = next(
            row for row in self._screen(rows)
            if row["minutes"] == 5 and row["approach"] == CANDIDATE
        )

        self.assertEqual(result["recent_entry_week_net_pnl"]["2025-12-29"], 200.0)
        self.assertEqual(result["recent_closed_net_less_best_week"], -160.0)
        self.assertIn("best entry week", " ".join(result["screen_failures"]))

    def test_candidate_invalid_execution_blocks_qualification(self) -> None:
        rows = _screen_fixture()
        candidate = next(row for row in rows if row["minutes"] == 5 and row["approach"] == CANDIDATE)
        candidate["severe_sensitivity"]["2023"]["status"] = "INVALID_EXECUTION"

        result = next(
            row for row in self._screen(rows)
            if row["minutes"] == 5 and row["approach"] == CANDIDATE
        )

        self.assertFalse(result["qualified"])
        self.assertIn("invalid execution", result["screen_failures"])

    def test_invalid_execution_in_either_matched_control_blocks_candidate(self) -> None:
        for control in (STALE, CONTINUOUS):
            with self.subTest(control=control):
                rows = _screen_fixture()
                paired = next(row for row in rows if row["minutes"] == 15 and row["approach"] == control)
                paired["stress"]["2024"]["status"] = "INVALID_EXECUTION"

                result = next(
                    row for row in self._screen(rows)
                    if row["minutes"] == 15 and row["approach"] == CANDIDATE
                )

                self.assertFalse(result["qualified"])
                self.assertIn("paired control invalid execution", result["screen_failures"])

    def test_campaign_run_id_traversal_and_existing_output_are_rejected_before_economics(self) -> None:
        project = Path(__file__).resolve().parents[1]
        protocol_source = project / campaign.ROOT / "protocol.json"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _tmp_campaign_authority(root, project)
            protocol_sha = campaign.sha(root / "protocol.json")
            with mock.patch.object(campaign, "ROOT", root), mock.patch.object(
                campaign, "PROTOCOL_SHA256", protocol_sha
            ), mock.patch.object(campaign, "REQUIRED_SOURCES", set()), mock.patch.object(
                campaign, "load_candles", side_effect=AssertionError("economics must not run")
            ):
                with self.assertRaisesRegex(ValueError, "Invalid run id"):
                    campaign.comparison(root, "../escape")
                run = root / "runs" / "already-there"
                run.mkdir(parents=True)
                sentinel = run / "sentinel.txt"
                sentinel.write_text("preserve", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    campaign.comparison(root, "already-there")
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
            self.assertTrue(protocol_source.is_file())

    def test_campaign_preserves_partial_failure_status_without_loading_market_data(self) -> None:
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _tmp_campaign_authority(root, project)
            protocol_sha = campaign.sha(root / "protocol.json")
            with mock.patch.object(campaign, "ROOT", root), mock.patch.object(
                campaign, "PROTOCOL_SHA256", protocol_sha
            ), mock.patch.object(campaign, "REQUIRED_SOURCES", set()), mock.patch.object(
                campaign, "load_candles", side_effect=RuntimeError("fixture data failure")
            ):
                with self.assertRaisesRegex(RuntimeError, "fixture data failure"):
                    campaign.comparison(root, "partial-failure")

            run = root / "runs" / "partial-failure"
            progress = json.loads((run / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual(progress["status"], "FAILED")
            self.assertEqual(progress["completed"], 0)
            self.assertIn("fixture data failure", progress["error"])
            self.assertTrue((run / "identities_after_run.json").is_file())


if __name__ == "__main__":
    unittest.main()
