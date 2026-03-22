from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import groupby
from math import sqrt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    NY_TZ = ZoneInfo("America/New_York")
except ZoneInfoNotFoundError:  # pragma: no cover - depends on host tzdata availability
    NY_TZ = timezone.utc
TIMEFRAME_SECONDS = {"5m": 300, "1H": 3600, "4H": 14400}


@dataclass
class Position:
    direction: str
    entry_ts: int
    entry_price: float
    quantity: float
    stop: float
    target_one: float
    target_two: float
    tp1_hit: bool = False
    reentry_used: bool = False


def compute_rsi(candles: list[dict], period: int = 14) -> list[float]:
    values = [50.0] * len(candles)
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(candles)):
        delta = candles[index]["close"] - candles[index - 1]["close"]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))
        if index < period:
            continue
        avg_gain = sum(gains[index - period : index]) / period
        avg_loss = sum(losses[index - period : index]) / period
        if avg_loss == 0:
            values[index] = 100.0
        else:
            rs = avg_gain / avg_loss
            values[index] = 100 - (100 / (1 + rs))
    return values


def compute_atr(candles: list[dict], period: int = 14) -> list[float]:
    atr = [0.0] * len(candles)
    tr_values: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            tr = candle["high"] - candle["low"]
        else:
            previous_close = candles[index - 1]["close"]
            tr = max(
                candle["high"] - candle["low"],
                abs(candle["high"] - previous_close),
                abs(candle["low"] - previous_close),
            )
        tr_values.append(tr)
        if index >= period:
            atr[index] = sum(tr_values[index - period + 1 : index + 1]) / period
        else:
            atr[index] = sum(tr_values) / len(tr_values)
    return atr


def fractal_indices(candles: list[dict], side: str, depth: int = 2) -> set[int]:
    points: set[int] = set()
    for index in range(depth, len(candles) - depth):
        window = candles[index - depth : index + depth + 1]
        center = candles[index]
        if side == "high" and center["high"] == max(item["high"] for item in window):
            points.add(index)
        if side == "low" and center["low"] == min(item["low"] for item in window):
            points.add(index)
    return points


def annualization_factor(timeframe: str) -> float:
    periods = {"5m": 12 * 24 * 365, "1H": 24 * 365, "4H": 6 * 365}
    return sqrt(periods[timeframe])


def run_a_zero(candles: list[dict], timeframe: str, parameters: dict, risk: dict, rules: dict, fees: float, slippage: float) -> dict:
    lookback_days = int(parameters.get("lookback_days", 90))
    range_multiplier = float(parameters.get("range_multiplier", 1.18))
    age_threshold_bars = int(parameters.get("age_threshold_bars", 28 * 24))
    periods_per_day = max(1, 86400 // TIMEFRAME_SECONDS[timeframe])
    lookback = lookback_days * periods_per_day
    execution_lookback = max(periods_per_day * 14, lookback // 3)
    rsi_values = compute_rsi(candles)
    start_equity = 10000.0
    equity = start_equity
    equity_curve = [{"ts": candles[0]["ts"], "equity": equity, "drawdown": 0.0}]
    peak_equity = equity
    trades: list[dict] = []
    position: Position | None = None
    pending_entry: dict | None = None
    recent_stop: dict | None = None
    max_hold_bars = max(24, lookback // 6)

    for index in range(1, len(candles)):
        candle = candles[index]
        previous = candles[index - 1]
        if pending_entry and position is None:
            entry_price = candle["open"] * (1 + slippage if pending_entry["direction"] == "long" else 1 - slippage)
            stop = pending_entry["stop"]
            risk_amount = equity * float(risk.get("risk_per_trade", 0.01))
            stop_distance = abs(entry_price - stop) or entry_price * 0.01
            quantity = risk_amount / stop_distance
            position = Position(
                direction=pending_entry["direction"],
                entry_ts=candle["ts"],
                entry_price=entry_price,
                quantity=quantity,
                stop=stop,
                target_one=pending_entry["target_one"],
                target_two=pending_entry["target_two"],
                reentry_used=pending_entry.get("reentry_used", False),
            )
            equity -= entry_price * quantity * fees
            pending_entry = None

        if position is not None:
            exit_trade = _manage_position(position, candle, fees, "a_zero")
            if exit_trade:
                equity += exit_trade["pnl"]
                trades.append(exit_trade)
                if exit_trade["reason"] == "stop":
                    recent_stop = {"direction": position.direction, "bars_left": 2}
                position = None
            elif index - _bar_index_for_timestamp(candles, position.entry_ts) >= max_hold_bars:
                exit_trade = _force_exit(position, candle, fees, "a_zero", "time_exit")
                equity += exit_trade["pnl"]
                trades.append(exit_trade)
                position = None

        if index < lookback:
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            peak_equity = max(peak_equity, equity)
            continue

        macro_window = candles[index - lookback : index]
        rolling = candles[max(0, index - execution_lookback) : index]
        if not rolling or not macro_window:
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            peak_equity = max(peak_equity, equity)
            continue

        rolling_low = min(item["low"] for item in rolling)
        rolling_high = max(item["high"] for item in rolling)
        macro_low = min(item["low"] for item in macro_window)
        macro_high = max(item["high"] for item in macro_window)
        range_high = max(rolling_high, rolling_low * range_multiplier)
        range_span = max(range_high - rolling_low, candle["close"] * 0.01)
        width = range_span / rolling_low if rolling_low else 0.0
        if width < 0.015 or width > 0.60:
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            peak_equity = max(peak_equity, equity)
            continue

        low_anchor = max(pos for pos, item in enumerate(rolling) if item["low"] == rolling_low)
        high_anchor = max(pos for pos, item in enumerate(rolling) if item["high"] == rolling_high)
        age_from_low = len(rolling) - 1 - low_anchor
        age_from_high = len(rolling) - 1 - high_anchor
        range_low = rolling_low
        zone_pct = min(0.40, max(0.18, 0.12 + (range_multiplier - 1.0)))
        lower_zone = rolling_low + range_span * zone_pct
        upper_zone = range_high - range_span * zone_pct
        macro_mid = macro_low + (macro_high - macro_low) * 0.50
        bullish_bias = previous["close"] >= macro_mid or age_from_low >= age_threshold_bars // 3
        bearish_bias = previous["close"] <= macro_mid or age_from_high >= age_threshold_bars // 3
        breakout_up = candle["close"] > rolling_high * (1 + (range_multiplier - 1.0) * 0.05) and previous["close"] <= rolling_high
        breakout_down = candle["close"] < rolling_low * (1 - (range_multiplier - 1.0) * 0.05) and previous["close"] >= rolling_low
        pullback_long = candle["low"] <= lower_zone and candle["close"] >= previous["close"]
        rejection_short = candle["high"] >= upper_zone and candle["close"] <= previous["close"]
        continuation_short = candle["close"] <= lower_zone and candle["close"] < candle["open"] and rsi_values[index] <= 48

        if recent_stop:
            recent_stop["bars_left"] -= 1
            if recent_stop["bars_left"] < 0:
                recent_stop = None

        if position is None and pending_entry is None and bullish_bias:
            long_confirm = candle["close"] > candle["open"] or rsi_values[index] <= 58
            breakout = age_from_high >= max(4, age_threshold_bars // 6) and breakout_up
            reentry_ready = recent_stop and recent_stop["direction"] == "long" and range_low <= candle["close"] <= range_high
            if pullback_long and (long_confirm or reentry_ready):
                stop = min(candle["close"] * 0.98, range_low * 0.985)
                pending_entry = {
                    "direction": "long",
                    "stop": stop,
                    "target_one": range_low + range_span * 0.5,
                    "target_two": range_high,
                    "reentry_used": bool(reentry_ready),
                }
            elif breakout:
                pending_entry = {
                    "direction": "long",
                    "stop": candle["close"] * 0.98,
                    "target_one": candle["close"] + range_span * 0.5,
                    "target_two": candle["close"] + range_span,
                }
        if position is None and pending_entry is None and bearish_bias:
            short_confirm = candle["close"] < candle["open"] or rsi_values[index] >= 42
            if (rejection_short or continuation_short) and short_confirm:
                pending_entry = {
                    "direction": "short",
                    "stop": max(candle["close"] * 1.02, range_high * 1.02),
                    "target_one": range_high - range_span * 0.5,
                    "target_two": rolling_low,
                }
            elif age_from_low >= max(4, age_threshold_bars // 6) and breakout_down:
                pending_entry = {
                    "direction": "short",
                    "stop": candle["close"] * 1.02,
                    "target_one": candle["close"] - range_span * 0.5,
                    "target_two": candle["close"] - range_span,
                }

        peak_equity = max(peak_equity, equity)
        equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))

    if position is not None:
        exit_trade = _force_exit(position, candles[-1], fees, "a_zero", "end_of_data")
        equity += exit_trade["pnl"]
        trades.append(exit_trade)
        equity_curve[-1] = _equity_point(candles[-1]["ts"], equity, max(peak_equity, equity))

    return {"equity_curve": equity_curve, "trades": trades, "final_equity": equity}


def run_smart_money(candles: list[dict], timeframe: str, parameters: dict, risk: dict, rules: dict, fees: float, slippage: float) -> dict:
    atr = compute_atr(candles)
    start_equity = 10000.0
    equity = start_equity
    peak_equity = equity
    equity_curve = [{"ts": candles[0]["ts"], "equity": equity, "drawdown": 0.0}]
    trades: list[dict] = []
    position: Position | None = None
    pending_order: dict | None = None
    sweep_state: dict | None = None
    daily_realized: dict[str, float] = {}
    consecutive_losses = 0
    trading_locked_day: str | None = None
    hourly = _aggregate_to_hourly(candles)
    htf_fractal_depth = int(parameters.get("htf_fractal_depth", 5))
    htf_depth_span = max(1, (htf_fractal_depth - 1) // 2)
    hourly_zones = _build_hourly_zones(hourly)
    sweep_window = max(12, int(12 + float(parameters.get("sweep_min_atr", parameters.get("sweep_multiplier", 0.2))) * 18))
    confirmation_window = max(3, int(3 + float(parameters.get("displacement_requirement_atr", parameters.get("displacement_requirement", 1.0))) * 2))
    lookback_htf = int(parameters.get("lookback_htf", 48))
    entry_retrace_level = float(parameters.get("entry_retrace_level", 0.5))
    confirmation_type = str(parameters.get("mss_confirmation_type", "strict"))
    displacement_requirement = float(parameters.get("displacement_requirement_atr", parameters.get("displacement_requirement", 1.2)))
    htf_pd_filter = bool(parameters.get("htf_pd_filter", False))
    min_rr_target = float(parameters.get("min_rr_target", 2.5))
    take_profit_logic = str(parameters.get("take_profit_logic", "opposing_liquidity_pool"))
    sweep_min_atr = float(parameters.get("sweep_min_atr", parameters.get("sweep_multiplier", 0.2)))
    stop_loss_padding_atr = float(parameters.get("stop_loss_padding_atr", 0.2))
    killzone_buffer_minutes = int(rules.get("killzone_buffer_minutes", 15))
    killzone_profile = str(rules.get("killzone_profile", "fx"))
    trade_min_duration_bars = int(rules.get("trade_min_duration_bars", 1))
    diagnostics = {
        "zone_hits": 0,
        "sweeps": 0,
        "near_miss_no_mss": 0,
        "mss_confirmations": 0,
        "fvg_confirmations": 0,
        "blocked_no_fvg": 0,
        "pending_orders": 0,
        "expired_orders": 0,
        "voided_orders": 0,
        "filled_orders": 0,
        "gate_no_zone": 0,
        "gate_no_sweep": 0,
        "gate_no_mss": 0,
        "gate_no_displacement": 0,
    }

    for index in range(2, len(candles)):
        candle = candles[index]
        date_key = datetime.fromtimestamp(candle["ts"], timezone.utc).astimezone(NY_TZ).date().isoformat()
        if trading_locked_day != date_key:
            consecutive_losses = 0
            if trading_locked_day and trading_locked_day != date_key:
                trading_locked_day = None
        if pending_order and position is None:
            order_expired = candle["ts"] > pending_order["expires_at"] or not _is_killzone(candle["ts"], killzone_buffer_minutes, killzone_profile)
            opposing_target_hit = (
                candle["high"] >= pending_order["target_two"] if pending_order["direction"] == "long" else candle["low"] <= pending_order["target_two"]
            )
            if order_expired or opposing_target_hit:
                diagnostics["expired_orders" if order_expired else "voided_orders"] += 1
                pending_order = None
            else:
                touched_entry = (
                    candle["low"] <= pending_order["entry_price"] <= candle["high"]
                    if pending_order["direction"] == "long"
                    else candle["low"] <= pending_order["entry_price"] <= candle["high"]
                )
                if touched_entry:
                    entry_price = pending_order["entry_price"] * (1 + slippage if pending_order["direction"] == "long" else 1 - slippage)
                    stop = pending_order["stop"]
                    risk_amount = equity * float(risk.get("risk_per_trade", 0.01))
                    stop_distance = abs(entry_price - stop) or entry_price * 0.01
                    position = Position(
                        direction=pending_order["direction"],
                        entry_ts=candle["ts"],
                        entry_price=entry_price,
                        quantity=risk_amount / stop_distance,
                        stop=stop,
                        target_one=pending_order["target_one"],
                        target_two=pending_order["target_two"],
                    )
                    equity -= entry_price * position.quantity * fees
                    diagnostics["filled_orders"] += 1
                    pending_order = None
        if position is not None:
            held_bars = index - _bar_index_for_timestamp(candles, position.entry_ts)
            if held_bars < trade_min_duration_bars:
                peak_equity = max(peak_equity, equity)
                equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
                continue

        if position is not None:
            exit_trade = _manage_position(position, candle, fees, "smart_money")
            if exit_trade:
                equity += exit_trade["pnl"]
                trades.append(exit_trade)
                daily_realized[date_key] = daily_realized.get(date_key, 0.0) + exit_trade["pnl"]
                consecutive_losses = consecutive_losses + 1 if exit_trade["pnl"] < 0 else 0
                if daily_realized[date_key] <= -0.02 * start_equity or consecutive_losses >= 2:
                    trading_locked_day = date_key
                position = None

        if trading_locked_day == date_key or position is not None or pending_order is not None or timeframe != "5m":
            peak_equity = max(peak_equity, equity)
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            continue

        if not _is_killzone(candle["ts"], killzone_buffer_minutes, killzone_profile):
            peak_equity = max(peak_equity, equity)
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            continue

        htf_range = _latest_structural_range(hourly, candle["ts"], htf_depth_span, lookback_htf)
        active_zone = _active_zone(hourly_zones, candle["ts"], candle["close"], lookback_htf, atr[index] * 0.5)
        if not active_zone or not htf_range:
            diagnostics["gate_no_zone"] += 1
            peak_equity = max(peak_equity, equity)
            equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))
            continue
        diagnostics["zone_hits"] += 1

        tolerance = max(candle["close"] * 0.00002, atr[index] * max(0.05, sweep_min_atr))
        prior_window = candles[max(0, index - sweep_window) : index]
        prior_low = min(item["low"] for item in prior_window)
        prior_high = max(item["high"] for item in prior_window)
        body_size = abs(candle["close"] - candle["open"])
        body_threshold = atr[index] * max(0.08, displacement_requirement * 0.35)
        if candle["low"] <= prior_low - tolerance and candle["close"] >= prior_low + body_threshold * 0.15:
            local_pivot_high = max(item["high"] for item in candles[max(0, index - 3) : index])
            sweep_state = {
                "direction": "long",
                "index": index,
                "pivot": local_pivot_high,
                "sweep_depth": max(0.0, prior_low - candle["low"]),
                "sweep_extreme": candle["low"],
            }
            diagnostics["sweeps"] += 1
        if candle["high"] >= prior_high + tolerance and candle["close"] <= prior_high - body_threshold * 0.15:
            local_pivot_low = min(item["low"] for item in candles[max(0, index - 3) : index])
            sweep_state = {
                "direction": "short",
                "index": index,
                "pivot": local_pivot_low,
                "sweep_depth": max(0.0, candle["high"] - prior_high),
                "sweep_extreme": candle["high"],
            }
            diagnostics["sweeps"] += 1

        minimum_sweep_depth = atr[index] * max(0.05, sweep_min_atr)
        displacement_threshold = atr[index] * max(0.12, displacement_requirement)
        bullish_fvg = candles[index - 2]["high"] < candle["low"]
        bearish_fvg = candles[index - 2]["low"] > candle["high"]
        relaxed_bullish_displacement = body_size >= displacement_threshold * displacement_requirement and candle["high"] > candles[index - 1]["high"]
        relaxed_bearish_displacement = body_size >= displacement_threshold * displacement_requirement and candle["low"] < candles[index - 1]["low"]
        strict_bullish_mss = bool(
            sweep_state
            and sweep_state["direction"] == "long"
            and index - sweep_state["index"] <= confirmation_window
            and candle["close"] > candle["open"]
            and body_size >= body_threshold
            and candle["close"] > sweep_state["pivot"]
            and sweep_state["sweep_depth"] >= minimum_sweep_depth
        )
        strict_bearish_mss = bool(
            sweep_state
            and sweep_state["direction"] == "short"
            and index - sweep_state["index"] <= confirmation_window
            and candle["close"] < candle["open"]
            and body_size >= body_threshold
            and candle["close"] < sweep_state["pivot"]
            and sweep_state["sweep_depth"] >= minimum_sweep_depth
        )
        relaxed_bullish_mss = bool(
            sweep_state
            and sweep_state["direction"] == "long"
            and index - sweep_state["index"] <= confirmation_window + 1
            and candle["high"] > min(sweep_state["pivot"], candles[index - 1]["high"])
            and candle["close"] >= candle["open"] + body_threshold * 0.25
            and sweep_state["sweep_depth"] >= minimum_sweep_depth * 0.75
            and relaxed_bullish_displacement
        )
        relaxed_bearish_mss = bool(
            sweep_state
            and sweep_state["direction"] == "short"
            and index - sweep_state["index"] <= confirmation_window + 1
            and candle["low"] < max(sweep_state["pivot"], candles[index - 1]["low"])
            and candle["close"] <= candle["open"] - body_threshold * 0.25
            and sweep_state["sweep_depth"] >= minimum_sweep_depth * 0.75
            and relaxed_bearish_displacement
        )
        bullish_mss = strict_bullish_mss if confirmation_type == "strict" else strict_bullish_mss or relaxed_bullish_mss
        bearish_mss = strict_bearish_mss if confirmation_type == "strict" else strict_bearish_mss or relaxed_bearish_mss
        if htf_pd_filter:
            if bullish_mss and candle["close"] > htf_range["mid"]:
                bullish_mss = False
            if bearish_mss and candle["close"] < htf_range["mid"]:
                bearish_mss = False
        if not sweep_state or index - sweep_state["index"] > confirmation_window + 1:
            diagnostics["gate_no_sweep"] += 1
        elif not bullish_mss and not bearish_mss:
            diagnostics["near_miss_no_mss"] += 1
            diagnostics["gate_no_mss"] += 1
        has_bullish_displacement = bullish_fvg or (confirmation_type == "relaxed" and relaxed_bullish_displacement)
        has_bearish_displacement = bearish_fvg or (confirmation_type == "relaxed" and relaxed_bearish_displacement)
        if active_zone["direction"] == "long" and bullish_mss and has_bullish_displacement:
            diagnostics["mss_confirmations"] += 1
            diagnostics["fvg_confirmations"] += 1
            fvg_bottom = candles[index - 2]["high"] if bullish_fvg else min(candles[index - 1]["open"], candles[index - 1]["close"])
            fvg_top = candle["low"] if bullish_fvg else max(candles[index - 1]["open"], candles[index - 1]["close"])
            entry_price = fvg_bottom + max(0.0, fvg_top - fvg_bottom) * entry_retrace_level
            stop = sweep_state["sweep_extreme"] - atr[index] * stop_loss_padding_atr
            risk_span = max(entry_price - stop, atr[index] * 0.2)
            opposing_liquidity = max(prior_high, htf_range["top"])
            target_two = max(entry_price + risk_span * min_rr_target, opposing_liquidity) if take_profit_logic == "opposing_liquidity_pool" else entry_price + risk_span * min_rr_target
            pending_order = {
                "direction": "long",
                "entry_price": entry_price,
                "stop": stop,
                "target_one": entry_price + (target_two - entry_price) * 0.5,
                "target_two": target_two,
                "expires_at": _killzone_end_ts(candle["ts"], killzone_buffer_minutes, killzone_profile),
            }
            diagnostics["pending_orders"] += 1
        elif active_zone["direction"] == "long" and bullish_mss:
            diagnostics["blocked_no_fvg"] += 1
            diagnostics["gate_no_displacement"] += 1
        if active_zone["direction"] == "short" and bearish_mss and has_bearish_displacement:
            diagnostics["mss_confirmations"] += 1
            diagnostics["fvg_confirmations"] += 1
            fvg_top = candles[index - 2]["low"] if bearish_fvg else max(candles[index - 1]["open"], candles[index - 1]["close"])
            fvg_bottom = candle["high"] if bearish_fvg else min(candles[index - 1]["open"], candles[index - 1]["close"])
            entry_price = fvg_top - max(0.0, fvg_top - fvg_bottom) * entry_retrace_level
            stop = sweep_state["sweep_extreme"] + atr[index] * stop_loss_padding_atr
            risk_span = max(stop - entry_price, atr[index] * 0.2)
            opposing_liquidity = min(prior_low, htf_range["bottom"])
            target_two = min(entry_price - risk_span * min_rr_target, opposing_liquidity) if take_profit_logic == "opposing_liquidity_pool" else entry_price - risk_span * min_rr_target
            pending_order = {
                "direction": "short",
                "entry_price": entry_price,
                "stop": stop,
                "target_one": entry_price - (entry_price - target_two) * 0.5,
                "target_two": target_two,
                "expires_at": _killzone_end_ts(candle["ts"], killzone_buffer_minutes, killzone_profile),
            }
            diagnostics["pending_orders"] += 1
        elif active_zone["direction"] == "short" and bearish_mss:
            diagnostics["blocked_no_fvg"] += 1
            diagnostics["gate_no_displacement"] += 1

        peak_equity = max(peak_equity, equity)
        equity_curve.append(_equity_point(candle["ts"], equity, peak_equity))

    if position is not None:
        exit_trade = _force_exit(position, candles[-1], fees, "smart_money", "end_of_data")
        equity += exit_trade["pnl"]
        trades.append(exit_trade)
        equity_curve[-1] = _equity_point(candles[-1]["ts"], equity, max(peak_equity, equity))

    return {"equity_curve": equity_curve, "trades": trades, "final_equity": equity, "diagnostics": diagnostics}


def _manage_position(position: Position, candle: dict, fees: float, strategy_name: str) -> dict | None:
    sign = 1 if position.direction == "long" else -1
    stop_hit = candle["low"] <= position.stop if position.direction == "long" else candle["high"] >= position.stop
    target_one_hit = candle["high"] >= position.target_one if position.direction == "long" else candle["low"] <= position.target_one
    target_two_hit = candle["high"] >= position.target_two if position.direction == "long" else candle["low"] <= position.target_two

    if stop_hit:
        pnl = sign * (position.stop - position.entry_price) * position.quantity - position.stop * position.quantity * fees
        return _trade(position, candle["ts"], position.stop, pnl, "stop", strategy_name)

    if target_one_hit and not position.tp1_hit:
        partial_qty = position.quantity * 0.33
        pnl = sign * (position.target_one - position.entry_price) * partial_qty - position.target_one * partial_qty * fees
        position.quantity -= partial_qty
        position.tp1_hit = True
        position.stop = position.entry_price
        if target_two_hit:
            pnl += sign * (position.target_two - position.entry_price) * position.quantity - position.target_two * position.quantity * fees
            return _trade(position, candle["ts"], position.target_two, pnl, "tp2_after_tp1", strategy_name)
        return None

    if target_two_hit:
        pnl = sign * (position.target_two - position.entry_price) * position.quantity - position.target_two * position.quantity * fees
        return _trade(position, candle["ts"], position.target_two, pnl, "tp2", strategy_name)
    return None


def _trade(position: Position, exit_ts: int, exit_price: float, pnl: float, reason: str, strategy_name: str) -> dict:
    return {
        "strategy": strategy_name,
        "direction": position.direction,
        "entry_ts": position.entry_ts,
        "exit_ts": exit_ts,
        "entry_price": round(position.entry_price, 6),
        "exit_price": round(exit_price, 6),
        "quantity": round(position.quantity, 6),
        "pnl": round(pnl, 6),
        "return_pct": round(pnl / 10000.0, 6),
        "reason": reason,
    }


def _force_exit(position: Position, candle: dict, fees: float, strategy_name: str, reason: str) -> dict:
    sign = 1 if position.direction == "long" else -1
    exit_price = candle["close"]
    pnl = sign * (exit_price - position.entry_price) * position.quantity - exit_price * position.quantity * fees
    return _trade(position, candle["ts"], exit_price, pnl, reason, strategy_name)


def _equity_point(ts: int, equity: float, peak_equity: float) -> dict:
    drawdown = 0.0 if peak_equity == 0 else max(0.0, (peak_equity - equity) / peak_equity)
    return {"ts": ts, "equity": round(equity, 6), "drawdown": round(drawdown, 6)}


def _bar_index_for_timestamp(candles: list[dict], ts: int) -> int:
    for index, candle in enumerate(candles):
        if candle["ts"] == ts:
            return index
    return len(candles) - 1


def _killzone_windows(profile: str) -> list[tuple[int, int]]:
    if profile == "crypto":
        return [(0, 240), (420, 660), (1140, 1380)]
    return [(120, 300), (420, 600)]


def _is_killzone(ts: int, buffer_minutes: int = 0, profile: str = "fx") -> bool:
    local = datetime.fromtimestamp(ts, timezone.utc).astimezone(NY_TZ)
    minutes = local.hour * 60 + local.minute
    return any((start - buffer_minutes) <= minutes <= (end + buffer_minutes) for start, end in _killzone_windows(profile))


def _killzone_end_ts(ts: int, buffer_minutes: int = 0, profile: str = "fx") -> int:
    local = datetime.fromtimestamp(ts, timezone.utc).astimezone(NY_TZ)
    minutes = local.hour * 60 + local.minute
    matching_window = next(
        ((start, end) for start, end in _killzone_windows(profile) if (start - buffer_minutes) <= minutes <= (end + buffer_minutes)),
        None,
    )
    if not matching_window:
        return ts
    _, end = matching_window
    end_minutes = end + buffer_minutes
    local_end = local.replace(hour=end_minutes // 60, minute=end_minutes % 60, second=0, microsecond=0)
    return int(local_end.astimezone(timezone.utc).timestamp())


def _aggregate_to_hourly(candles: list[dict]) -> list[dict]:
    grouped: list[dict] = []
    for _, items in groupby(candles, key=lambda item: datetime.fromtimestamp(item["ts"], timezone.utc).astimezone(NY_TZ).replace(minute=0, second=0, microsecond=0)):
        bucket = list(items)
        grouped.append(
            {
                "ts": bucket[-1]["ts"],
                "open": bucket[0]["open"],
                "high": max(item["high"] for item in bucket),
                "low": min(item["low"] for item in bucket),
                "close": bucket[-1]["close"],
            }
        )
    return grouped


def _build_hourly_zones(candles: list[dict]) -> list[dict]:
    atr = compute_atr(candles)
    zones: list[dict] = []
    for index in range(2, len(candles)):
        current = candles[index]
        prev = candles[index - 1]
        prior = candles[index - 2]
        if current["low"] > prior["high"]:
            zones.append({"direction": "long", "start_ts": current["ts"], "bottom": prior["high"], "top": current["low"], "expires_at": current["ts"] + 6 * 3600})
        displacement = current["high"] - current["low"]
        if current["high"] < prior["low"]:
            zones.append({"direction": "short", "start_ts": current["ts"], "bottom": current["high"], "top": prior["low"], "expires_at": current["ts"] + 6 * 3600})
        if displacement > atr[index] * 1.5:
            if current["close"] > prev["high"]:
                zones.append({"direction": "long", "start_ts": current["ts"], "bottom": prev["low"], "top": prev["high"], "expires_at": current["ts"] + 6 * 3600})
            if current["close"] < prev["low"]:
                zones.append({"direction": "short", "start_ts": current["ts"], "bottom": prev["low"], "top": prev["high"], "expires_at": current["ts"] + 6 * 3600})
    return zones


def _latest_structural_range(candles: list[dict], ts: int, depth: int, lookback_hours: int) -> dict | None:
    high_points = sorted(fractal_indices(candles, "high", depth))
    low_points = sorted(fractal_indices(candles, "low", depth))
    recent_high = next((candles[index] for index in reversed(high_points) if candles[index]["ts"] <= ts and ts - candles[index]["ts"] <= lookback_hours * 3600), None)
    recent_low = next((candles[index] for index in reversed(low_points) if candles[index]["ts"] <= ts and ts - candles[index]["ts"] <= lookback_hours * 3600), None)
    if not recent_high or not recent_low:
        return None
    top = recent_high["high"]
    bottom = recent_low["low"]
    if bottom >= top:
        return None
    return {"top": top, "bottom": bottom, "mid": bottom + (top - bottom) * 0.5}


def _active_zone(zones: list[dict], ts: int, price: float, lookback_htf: int = 24, tolerance: float = 0.0) -> dict | None:
    valid = [
        zone
        for zone in zones
        if zone["start_ts"] <= ts <= zone["expires_at"]
        and ts - zone["start_ts"] <= lookback_htf * 3600
        and (zone["bottom"] - tolerance) <= price <= (zone["top"] + tolerance)
    ]
    return valid[-1] if valid else None
