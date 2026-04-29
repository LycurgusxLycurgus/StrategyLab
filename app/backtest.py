from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from fastapi import HTTPException

from app.data import Bar


@dataclass(slots=True)
class Position:
    direction: int
    entry_index: int
    entry_ts: datetime
    entry_price: float
    stop_price: float
    quantity: float
    entry_commission: float
    entry_equity: float
    entry_notional: float
    initial_risk_per_unit: float
    stop_initialized_on_index: int
    entry_features: dict[str, Any]
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0


def sma(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= length:
            running -= values[index - length]
        output.append((running / length) if index + 1 >= length else None)
    return output


def ema(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    alpha = 2 / (length + 1)
    current: float | None = None
    for index, value in enumerate(values):
        if index + 1 < length:
            output.append(None)
            continue
        if current is None:
            window = values[index + 1 - length : index + 1]
            current = sum(window) / length
        else:
            current = (value * alpha) + (current * (1 - alpha))
        output.append(current)
    return output


def atr(bars: list[Bar], length: int) -> list[float | None]:
    output: list[float | None] = []
    trs: list[float] = []
    previous_close = bars[0].close if bars else 0.0
    for index, bar in enumerate(bars):
        tr = max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))
        trs.append(tr)
        if index + 1 < length:
            output.append(None)
        else:
            window = trs[index + 1 - length : index + 1]
            output.append(sum(window) / length)
        previous_close = bar.close
    return output


def compute_metrics(
    initial_capital: float,
    trades: list[dict[str, Any]],
    equity_curve: list[dict[str, Any]],
    buy_hold_return: float,
    buy_hold_return_pct: float,
    buy_hold_start_price: float = 0.0,
    buy_hold_end_price: float = 0.0,
    buy_hold_max_drawdown_pct: float = 0.0,
) -> dict[str, Any]:
    periodic = periodic_equity_metrics(equity_curve, initial_capital)
    if not trades:
        return {
            "initial_capital": initial_capital,
            "net_pnl": 0.0,
            "return_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "expected_payoff": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "daily_sharpe": periodic["daily_sharpe"],
            "daily_sortino": periodic["daily_sortino"],
            "daily_volatility_pct": periodic["daily_volatility_pct"],
            "worst_daily_return_pct": periodic["worst_daily_return_pct"],
            "positive_day_pct": periodic["positive_day_pct"],
            "daily_return_count": periodic["daily_return_count"],
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "percent_profitable": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "ratio_avg_win_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "avg_bars_in_trade": 0.0,
            "avg_bars_winning": 0.0,
            "avg_bars_losing": 0.0,
            "max_equity_drawdown": 0.0,
            "max_equity_drawdown_pct": 0.0,
            "max_equity_runup": 0.0,
            "avg_entry_exposure_pct": 0.0,
            "max_entry_exposure_pct": 0.0,
            "avg_initial_risk_pct": 0.0,
            "max_initial_risk_pct": 0.0,
            "buy_hold_return": buy_hold_return,
            "buy_hold_return_pct": buy_hold_return_pct,
            "buy_hold_start_price": buy_hold_start_price,
            "buy_hold_end_price": buy_hold_end_price,
            "buy_hold_max_drawdown_pct": buy_hold_max_drawdown_pct,
            "calmar": 0.0,
            "buy_hold_calmar": 0.0,
            "calmar_delta": 0.0,
            "outperformance": -buy_hold_return,
            "outperformance_pct": -buy_hold_return_pct,
        }
    pnls = [trade["net_pnl"] for trade in trades]
    returns = [trade["return_on_equity_pct"] / 100 for trade in trades]
    wins = [trade for trade in trades if trade["net_pnl"] > 0]
    losses = [trade for trade in trades if trade["net_pnl"] < 0]
    exposures = [float(trade.get("entry_exposure_pct", 0.0)) for trade in trades]
    risk_pcts = [float(trade.get("initial_risk_pct", 0.0)) for trade in trades]
    gross_profit = sum(trade["net_pnl"] for trade in wins)
    gross_loss = abs(sum(trade["net_pnl"] for trade in losses))
    avg_return = sum(returns) / len(returns)
    variance = sum((item - avg_return) ** 2 for item in returns) / len(returns)
    downside = [item for item in returns if item < 0]
    downside_variance = sum(item**2 for item in downside) / len(downside) if downside else 0.0
    largest_win = max(pnls)
    largest_loss = min(pnls)
    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = sum(trade["net_pnl"] for trade in losses) / len(losses) if losses else 0.0
    drawdown = 0.0
    drawdown_pct = 0.0
    runup = 0.0
    peak = initial_capital
    trough = initial_capital
    for point in equity_curve:
        peak = max(peak, point["equity"])
        trough = min(trough, point["equity"])
        drawdown = max(drawdown, peak - point["equity"])
        drawdown_pct = max(drawdown_pct, ((peak - point["equity"]) / peak) * 100 if peak else 0.0)
        runup = max(runup, point["equity"] - trough)
    return_pct = (sum(pnls) / initial_capital) * 100
    calmar = return_pct / drawdown_pct if drawdown_pct > 0 else (return_pct if return_pct > 0 else 0.0)
    buy_hold_calmar = (
        buy_hold_return_pct / buy_hold_max_drawdown_pct
        if buy_hold_max_drawdown_pct > 0
        else (buy_hold_return_pct if buy_hold_return_pct > 0 else 0.0)
    )
    return {
        "initial_capital": round(initial_capital, 2),
        "net_pnl": round(sum(pnls), 2),
        "return_pct": round(return_pct, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else round(gross_profit, 4),
        "expected_payoff": round(sum(pnls) / len(pnls), 2),
        "sharpe": round((avg_return / math.sqrt(variance)) * math.sqrt(len(returns)), 4) if variance > 0 else 0.0,
        "sortino": round((avg_return / math.sqrt(downside_variance)) * math.sqrt(len(returns)), 4) if downside_variance > 0 else 0.0,
        "daily_sharpe": periodic["daily_sharpe"],
        "daily_sortino": periodic["daily_sortino"],
        "daily_volatility_pct": periodic["daily_volatility_pct"],
        "worst_daily_return_pct": periodic["worst_daily_return_pct"],
        "positive_day_pct": periodic["positive_day_pct"],
        "daily_return_count": periodic["daily_return_count"],
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "percent_profitable": round((len(wins) / len(trades)) * 100, 2),
        "avg_pnl": round(sum(pnls) / len(pnls), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "ratio_avg_win_loss": round(abs(avg_win / avg_loss), 4) if avg_loss else 0.0,
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "avg_bars_in_trade": round(sum(trade["bars_held"] for trade in trades) / len(trades), 2),
        "avg_bars_winning": round(sum(trade["bars_held"] for trade in wins) / len(wins), 2) if wins else 0.0,
        "avg_bars_losing": round(sum(trade["bars_held"] for trade in losses) / len(losses), 2) if losses else 0.0,
        "max_equity_drawdown": round(drawdown, 2),
        "max_equity_drawdown_pct": round(drawdown_pct, 2),
        "max_equity_runup": round(runup, 2),
        "avg_entry_exposure_pct": round(sum(exposures) / len(exposures), 2) if exposures else 0.0,
        "max_entry_exposure_pct": round(max(exposures), 2) if exposures else 0.0,
        "avg_initial_risk_pct": round(sum(risk_pcts) / len(risk_pcts), 4) if risk_pcts else 0.0,
        "max_initial_risk_pct": round(max(risk_pcts), 4) if risk_pcts else 0.0,
        "buy_hold_return": round(buy_hold_return, 2),
        "buy_hold_return_pct": round(buy_hold_return_pct, 2),
        "buy_hold_start_price": round(buy_hold_start_price, 4),
        "buy_hold_end_price": round(buy_hold_end_price, 4),
        "buy_hold_max_drawdown_pct": round(buy_hold_max_drawdown_pct, 2),
        "calmar": round(calmar, 4),
        "buy_hold_calmar": round(buy_hold_calmar, 4),
        "calmar_delta": round(calmar - buy_hold_calmar, 4),
        "outperformance": round(sum(pnls) - buy_hold_return, 2),
        "outperformance_pct": round(return_pct - buy_hold_return_pct, 2),
    }


def periodic_equity_metrics(equity_curve: list[dict[str, Any]], initial_capital: float) -> dict[str, float]:
    daily_closes: dict[str, float] = {}
    for point in equity_curve:
        ts = str(point.get("ts", ""))
        if not ts:
            continue
        day = ts[:10]
        daily_closes[day] = float(point.get("equity", initial_capital))
    returns: list[float] = []
    previous = initial_capital
    for day in sorted(daily_closes):
        close = daily_closes[day]
        if previous > 0:
            returns.append((close - previous) / previous)
        previous = close
    if not returns:
        return {
            "daily_sharpe": 0.0,
            "daily_sortino": 0.0,
            "daily_volatility_pct": 0.0,
            "worst_daily_return_pct": 0.0,
            "positive_day_pct": 0.0,
            "daily_return_count": 0,
        }
    avg_return = sum(returns) / len(returns)
    variance = sum((item - avg_return) ** 2 for item in returns) / len(returns)
    downside = [item for item in returns if item < 0]
    downside_variance = sum(item**2 for item in downside) / len(downside) if downside else 0.0
    annualizer = math.sqrt(365)
    return {
        "daily_sharpe": round((avg_return / math.sqrt(variance)) * annualizer, 4) if variance > 0 else 0.0,
        "daily_sortino": round((avg_return / math.sqrt(downside_variance)) * annualizer, 4) if downside_variance > 0 else 0.0,
        "daily_volatility_pct": round(math.sqrt(variance) * annualizer * 100, 2) if variance > 0 else 0.0,
        "worst_daily_return_pct": round(min(returns) * 100, 2),
        "positive_day_pct": round((sum(1 for item in returns if item > 0) / len(returns)) * 100, 2),
        "daily_return_count": len(returns),
    }


def buy_hold_drawdown_pct(bars: list[Bar], start_index: int) -> float:
    if not bars or start_index >= len(bars):
        return 0.0
    peak = bars[start_index].close
    max_drawdown = 0.0
    for bar in bars[start_index:]:
        peak = max(peak, bar.close)
        if peak:
            max_drawdown = max(max_drawdown, ((peak - bar.close) / peak) * 100)
    return max_drawdown


def benchmark_warmup_index(parameters: dict[str, Any], bar_count: int) -> int:
    if bar_count <= 1:
        return 0
    warmup = max(
        int(parameters["fast_len"]),
        int(parameters["slow_len"]),
        int(parameters["atr_len"]),
        int(parameters["noise_lookback"]) + 1,
    )
    return min(warmup, bar_count - 1)


class BacktestEngine:
    def run(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        engine_id = spec.get("engine_id")
        if engine_id != "ma_cross_atr_stop_v1":
            raise HTTPException(status_code=400, detail=f"Unsupported engine: {engine_id}")
        return self._run_ma_cross_atr_stop(spec, bars)

    def _run_ma_cross_atr_stop(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters = spec["parameters"]
        closes = [bar.close for bar in bars]
        ma_kind = parameters.get("ma_kind", "sma").lower()
        ma_fn = sma if ma_kind == "sma" else ema
        fast = ma_fn(closes, int(parameters["fast_len"]))
        slow = ma_fn(closes, int(parameters["slow_len"]))
        atr_values = atr(bars, int(parameters["atr_len"]))
        short_quality_gate_enabled = bool(parameters.get("short_quality_gate_enabled", False))
        short_quality_gate_values = (
            sma(closes, int(parameters.get("short_quality_gate_len_bars", 0)))
            if short_quality_gate_enabled
            else []
        )

        price_cross_fast: list[bool] = []
        for index, bar in enumerate(bars):
            if index == 0 or fast[index] is None or fast[index - 1] is None:
                price_cross_fast.append(False)
                continue
            previous_relation = closes[index - 1] - float(fast[index - 1])
            current_relation = closes[index] - float(fast[index])
            crossed = (previous_relation <= 0 < current_relation) or (previous_relation >= 0 > current_relation)
            price_cross_fast.append(crossed)

        position: Position | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        equity = float(parameters.get("initial_capital", 100_000.0))
        tick_size = float(parameters.get("tick_size", 0.01))
        slippage = int(parameters.get("slippage_ticks", 0)) * tick_size
        commission_pct = float(parameters.get("commission_pct", 0.0)) / 100
        diagnostics = {
            "bars": len(bars),
            "signals_long": 0,
            "signals_short": 0,
            "entries": 0,
            "stop_exits": 0,
            "reverse_exits": 0,
            "breakeven_stop_moves": 0,
            "short_quality_gate_blocks": 0,
            "time_risk_filter_blocks": 0,
            "hybrid_time_decay_triage_exits": 0,
            "hybrid_reverse_exit_blocks": 0,
            "time_decay_exits": 0,
            "time_exits": 0,
        }
        warmup = max(
            int(parameters["fast_len"]),
            int(parameters["slow_len"]),
            int(parameters["atr_len"]),
            int(parameters["noise_lookback"]) + 1,
        )

        for index, bar in enumerate(bars):
            if index < warmup or fast[index] is None or slow[index] is None or atr_values[index] is None:
                equity_curve.append({"ts": bar.ts.isoformat(), "equity": round(equity, 2)})
                continue

            if position:
                self._update_excursion(position, bar)

            if position and index > position.stop_initialized_on_index:
                if position.direction == 1 and bar.low <= position.stop_price:
                    trade = self._close_trade(
                        position=position,
                        bar=bar,
                        index=index,
                        price=max(position.stop_price - slippage, 0.0),
                        reason="stop",
                        commission_pct=commission_pct,
                        equity_before=equity,
                    )
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["stop_exits"] += 1
                    position = None
                elif position.direction == -1 and bar.high >= position.stop_price:
                    trade = self._close_trade(
                        position=position,
                        bar=bar,
                        index=index,
                        price=position.stop_price + slippage,
                        reason="stop",
                        commission_pct=commission_pct,
                        equity_before=equity,
                    )
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["stop_exits"] += 1
                    position = None

            if position and parameters.get("breakeven_stop_enabled", False):
                initial_risk = abs(position.entry_price - position.stop_price)
                if initial_risk:
                    trigger_r = float(parameters.get("breakeven_trigger_mfe_r", 1.0))
                    lock_r = float(parameters.get("breakeven_lock_r", 0.0))
                    mfe_r = position.max_favorable_excursion / initial_risk
                    if mfe_r >= trigger_r:
                        if position.direction == 1:
                            new_stop = position.entry_price + (initial_risk * lock_r)
                            if new_stop > position.stop_price:
                                position.stop_price = new_stop
                                diagnostics["breakeven_stop_moves"] += 1
                        else:
                            new_stop = position.entry_price - (initial_risk * lock_r)
                            if new_stop < position.stop_price:
                                position.stop_price = new_stop
                                diagnostics["breakeven_stop_moves"] += 1

            if position and parameters.get("hybrid_time_decay_triage_enabled", False):
                bars_held = index - position.entry_index
                checkpoints = parameters.get("hybrid_time_decay_triage_checkpoints", [10, 20, 30])
                if isinstance(checkpoints, (int, float)):
                    checkpoint_set = {int(checkpoints)}
                else:
                    checkpoint_set = {int(item) for item in checkpoints}
                initial_risk = abs(position.entry_price - position.stop_price)
                if initial_risk and bars_held in checkpoint_set:
                    if position.direction == 1:
                        unrealized = bar.close - position.entry_price
                    else:
                        unrealized = position.entry_price - bar.close
                    unrealized_r = unrealized / initial_risk
                    mfe_r = position.max_favorable_excursion / initial_risk
                    max_unrealized_r = float(parameters.get("hybrid_time_decay_triage_max_unrealized_r", 0.10))
                    max_mfe_r = float(parameters.get("hybrid_time_decay_triage_max_mfe_r", 0.25))
                    if unrealized_r <= max_unrealized_r and mfe_r <= max_mfe_r:
                        exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                        trade = self._close_trade(
                            position=position,
                            bar=bar,
                            index=index,
                            price=exit_price,
                            reason="hybrid_time_decay_triage",
                            commission_pct=commission_pct,
                            equity_before=equity,
                        )
                        trades.append(trade)
                        equity += trade["net_pnl"]
                        diagnostics["hybrid_time_decay_triage_exits"] += 1
                        position = None

            if position and parameters.get("time_decay_exit_enabled", False):
                bars_held = index - position.entry_index
                decay_bars = int(parameters.get("time_decay_bars", 0))
                initial_risk = abs(position.entry_price - position.stop_price)
                mfe_r = position.max_favorable_excursion / initial_risk if initial_risk else 0.0
                if decay_bars > 0 and bars_held >= decay_bars and mfe_r < float(parameters.get("time_decay_min_mfe_r", 0.0)):
                    exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                    trade = self._close_trade(
                        position=position,
                        bar=bar,
                        index=index,
                        price=exit_price,
                        reason="time_decay",
                        commission_pct=commission_pct,
                        equity_before=equity,
                    )
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["time_decay_exits"] += 1
                    position = None

            noise_lookback = int(parameters["noise_lookback"])
            cross_count = sum(1 for item in price_cross_fast[max(0, index - noise_lookback + 1) : index + 1] if item)
            cross_count_ok = cross_count <= int(parameters["max_no_cross"])
            prev_fast = float(fast[index - 1])
            prev_slow = float(slow[index - 1])
            curr_fast = float(fast[index])
            curr_slow = float(slow[index])

            crossover = prev_fast <= prev_slow and curr_fast > curr_slow
            crossunder = prev_fast >= prev_slow and curr_fast < curr_slow
            pullback_long = (
                bar.close < curr_fast
                and bar.close > curr_slow
                and curr_fast > curr_slow
                and cross_count_ok
            )
            pullback_short = (
                bar.close > curr_fast
                and bar.close < curr_slow
                and curr_fast < curr_slow
                and cross_count_ok
            )

            entry_mode = parameters.get("entry_mode", "crossover_only")
            long_signal = crossover and cross_count_ok
            short_signal = crossunder and cross_count_ok
            if entry_mode == "crossover_plus_pullback":
                long_signal = long_signal or pullback_long
                short_signal = short_signal or pullback_short

            if parameters.get("allow_long", True) and long_signal:
                diagnostics["signals_long"] += 1
            else:
                long_signal = False

            if short_signal and short_quality_gate_enabled:
                rule = parameters.get("short_quality_gate_rule", "block_below_sma")
                context_value = short_quality_gate_values[index]
                block_short = context_value is None
                if context_value is not None and rule == "block_below_sma":
                    block_short = bar.close < float(context_value)
                elif context_value is not None and rule == "block_above_sma":
                    block_short = bar.close > float(context_value)
                if block_short:
                    diagnostics["short_quality_gate_blocks"] += 1
                    short_signal = False

            if parameters.get("allow_short", True) and short_signal:
                diagnostics["signals_short"] += 1
            else:
                short_signal = False

            entry_long_signal = long_signal
            entry_short_signal = short_signal
            if parameters.get("time_risk_filter_enabled", False) and (entry_long_signal or entry_short_signal):
                blocked_weekdays = {int(item) for item in parameters.get("time_risk_block_weekdays", [])}
                blocked_hours = {int(item) for item in parameters.get("time_risk_block_utc_hours", [])}
                if bar.ts.weekday() in blocked_weekdays or bar.ts.hour in blocked_hours:
                    diagnostics["time_risk_filter_blocks"] += int(entry_long_signal) + int(entry_short_signal)
                    entry_long_signal = False
                    entry_short_signal = False

            entry_at_close = bar.close
            reverse_exit_blocked = False
            if position and parameters.get("hybrid_reverse_exit_triage_enabled", False):
                initial_risk = abs(position.entry_price - position.stop_price)
                mfe_r = position.max_favorable_excursion / initial_risk if initial_risk else 0.0
                min_mfe_r = float(parameters.get("hybrid_reverse_exit_min_mfe_r", 0.25))
                if (
                    (position.direction == 1 and short_signal)
                    or (position.direction == -1 and long_signal)
                ) and mfe_r < min_mfe_r:
                    diagnostics["hybrid_reverse_exit_blocks"] += 1
                    reverse_exit_blocked = True
                    entry_long_signal = False
                    entry_short_signal = False

            if position and position.direction == 1 and short_signal and not reverse_exit_blocked:
                trade = self._close_trade(
                    position=position,
                    bar=bar,
                    index=index,
                    price=max(entry_at_close - slippage, 0.0),
                    reason="reverse",
                    commission_pct=commission_pct,
                    equity_before=equity,
                )
                trades.append(trade)
                equity += trade["net_pnl"]
                diagnostics["reverse_exits"] += 1
                position = None
            elif position and position.direction == -1 and long_signal and not reverse_exit_blocked:
                trade = self._close_trade(
                    position=position,
                    bar=bar,
                    index=index,
                    price=entry_at_close + slippage,
                    reason="reverse",
                    commission_pct=commission_pct,
                    equity_before=equity,
                )
                trades.append(trade)
                equity += trade["net_pnl"]
                diagnostics["reverse_exits"] += 1
                position = None

            if position is None:
                if entry_long_signal:
                    fill = entry_at_close + slippage
                    stop = fill - (float(atr_values[index]) * float(parameters["stop_mult"]))
                    quantity = self._position_quantity(parameters, equity, fill, stop)
                    commission = fill * quantity * commission_pct
                    entry_notional = fill * quantity
                    initial_risk_per_unit = abs(fill - stop)
                    entry_features = self._entry_features(
                        bars=bars,
                        index=index,
                        direction=1,
                        fast=fast,
                        slow=slow,
                        atr_values=atr_values,
                        cross_count=cross_count,
                        stop_price=stop,
                        entry_price=fill,
                    )
                    position = Position(
                        direction=1,
                        entry_index=index,
                        entry_ts=bar.ts,
                        entry_price=fill,
                        stop_price=stop,
                        quantity=quantity,
                        entry_commission=commission,
                        entry_equity=equity,
                        entry_notional=entry_notional,
                        initial_risk_per_unit=initial_risk_per_unit,
                        stop_initialized_on_index=index,
                        entry_features=entry_features,
                    )
                    diagnostics["entries"] += 1
                elif entry_short_signal:
                    fill = max(entry_at_close - slippage, 0.0)
                    stop = fill + (float(atr_values[index]) * float(parameters["stop_mult"]))
                    quantity = self._position_quantity(parameters, equity, fill, stop)
                    commission = fill * quantity * commission_pct
                    entry_notional = fill * quantity
                    initial_risk_per_unit = abs(fill - stop)
                    entry_features = self._entry_features(
                        bars=bars,
                        index=index,
                        direction=-1,
                        fast=fast,
                        slow=slow,
                        atr_values=atr_values,
                        cross_count=cross_count,
                        stop_price=stop,
                        entry_price=fill,
                    )
                    position = Position(
                        direction=-1,
                        entry_index=index,
                        entry_ts=bar.ts,
                        entry_price=fill,
                        stop_price=stop,
                        quantity=quantity,
                        entry_commission=commission,
                        entry_equity=equity,
                        entry_notional=entry_notional,
                        initial_risk_per_unit=initial_risk_per_unit,
                        stop_initialized_on_index=index,
                        entry_features=entry_features,
                    )
                    diagnostics["entries"] += 1

            equity_curve.append({"ts": bar.ts.isoformat(), "equity": round(equity, 2)})

        if position:
            last_bar = bars[-1]
            exit_price = max(last_bar.close - slippage, 0.0) if position.direction == 1 else last_bar.close + slippage
            trade = self._close_trade(
                position=position,
                bar=last_bar,
                index=len(bars) - 1,
                price=exit_price,
                reason="time_exit",
                commission_pct=commission_pct,
                equity_before=equity,
            )
            trades.append(trade)
            equity += trade["net_pnl"]
            diagnostics["time_exits"] += 1
            equity_curve[-1] = {"ts": last_bar.ts.isoformat(), "equity": round(equity, 2)}

        initial_capital = float(parameters.get("initial_capital", 100_000.0))
        buy_hold_start_price = bars[warmup].close if len(bars) > warmup else bars[0].close
        buy_hold_end_price = bars[-1].close
        buy_hold_return_pct = (
            ((buy_hold_end_price - buy_hold_start_price) / buy_hold_start_price) * 100
            if buy_hold_start_price
            else 0.0
        )
        buy_hold_return = initial_capital * (buy_hold_return_pct / 100)
        buy_hold_max_drawdown_pct = buy_hold_drawdown_pct(bars, warmup)
        metrics = compute_metrics(
            initial_capital=initial_capital,
            trades=trades,
            equity_curve=equity_curve,
            buy_hold_return=buy_hold_return,
            buy_hold_return_pct=buy_hold_return_pct,
            buy_hold_start_price=buy_hold_start_price,
            buy_hold_end_price=buy_hold_end_price,
            buy_hold_max_drawdown_pct=buy_hold_max_drawdown_pct,
        )
        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "diagnostics": diagnostics,
        }

    @staticmethod
    def _position_quantity(parameters: dict[str, Any], equity: float, entry_price: float, stop_price: float) -> float:
        if entry_price <= 0 or equity <= 0:
            return 0.0
        mode = parameters.get("sizing_mode", "fixed_quantity")
        max_leverage = max(0.0, float(parameters.get("max_leverage", 1.0)))
        max_notional = equity * max_leverage if max_leverage else float("inf")
        if mode == "fixed_notional_pct":
            target_pct = max(0.0, float(parameters.get("notional_pct", 1.0)))
            target_notional = min(equity * target_pct, max_notional)
            return target_notional / entry_price
        if mode == "fixed_risk_pct":
            risk_per_unit = abs(entry_price - stop_price)
            if risk_per_unit <= 0:
                return 0.0
            risk_pct = max(0.0, float(parameters.get("risk_pct", 0.005)))
            risk_quantity = (equity * risk_pct) / risk_per_unit
            leverage_quantity = max_notional / entry_price
            return min(risk_quantity, leverage_quantity)
        return max(0.0, float(parameters.get("quantity", 1.0)))

    @staticmethod
    def _entry_features(
        bars: list[Bar],
        index: int,
        direction: int,
        fast: list[float | None],
        slow: list[float | None],
        atr_values: list[float | None],
        cross_count: int,
        stop_price: float,
        entry_price: float,
    ) -> dict[str, Any]:
        bar = bars[index]
        lookback = min(index, 20)
        prior = bars[index - lookback : index + 1]
        prior_close = bars[index - lookback].close if lookback else bar.close
        prior_high = max(item.high for item in prior)
        prior_low = min(item.low for item in prior)
        prior_returns = [
            (bars[item].close - bars[item - 1].close) / bars[item - 1].close
            for item in range(max(1, index - lookback + 1), index + 1)
            if bars[item - 1].close
        ]
        current_fast = float(fast[index] or 0.0)
        current_slow = float(slow[index] or 0.0)
        previous_fast = float(fast[index - 1] or current_fast)
        previous_slow = float(slow[index - 1] or current_slow)
        current_atr = float(atr_values[index] or 0.0)
        stop_distance = abs(entry_price - stop_price)
        return {
            "side": "long" if direction == 1 else "short",
            "weekday": bar.ts.weekday(),
            "utc_hour": bar.ts.hour,
            "month": bar.ts.month,
            "fast_sma": round(current_fast, 6),
            "slow_sma": round(current_slow, 6),
            "fast_minus_slow": round(current_fast - current_slow, 6),
            "normalized_ma_distance": round((current_fast - current_slow) / bar.close, 8) if bar.close else 0.0,
            "fast_slope": round(current_fast - previous_fast, 6),
            "slow_slope": round(current_slow - previous_slow, 6),
            "atr": round(current_atr, 6),
            "atr_pct": round(current_atr / bar.close, 8) if bar.close else 0.0,
            "recent_return_20": round((bar.close - prior_close) / prior_close, 8) if prior_close else 0.0,
            "recent_range_20": round((prior_high - prior_low) / bar.close, 8) if bar.close else 0.0,
            "recent_volatility_20": round(math.sqrt(sum(item * item for item in prior_returns) / len(prior_returns)), 8)
            if prior_returns
            else 0.0,
            "recent_cross_count": cross_count,
            "stop_distance": round(stop_distance, 6),
            "stop_distance_atr": round(stop_distance / current_atr, 6) if current_atr else 0.0,
            "stop_distance_pct": round(stop_distance / entry_price, 8) if entry_price else 0.0,
        }

    @staticmethod
    def _update_excursion(position: Position, bar: Bar) -> None:
        if position.direction == 1:
            favorable = bar.high - position.entry_price
            adverse = bar.low - position.entry_price
        else:
            favorable = position.entry_price - bar.low
            adverse = position.entry_price - bar.high
        position.max_favorable_excursion = max(position.max_favorable_excursion, favorable)
        position.max_adverse_excursion = min(position.max_adverse_excursion, adverse)

    def _close_trade(
        self,
        position: Position,
        bar: Bar,
        index: int,
        price: float,
        reason: str,
        commission_pct: float,
        equity_before: float,
    ) -> dict[str, Any]:
        exit_commission = price * position.quantity * commission_pct
        if position.direction == 1:
            gross_pnl = (price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - price) * position.quantity
        net_pnl = gross_pnl - position.entry_commission - exit_commission
        initial_risk = position.initial_risk_per_unit
        initial_risk_amount = initial_risk * position.quantity
        return {
            "trade_id": f"tr_{uuid.uuid4().hex[:12]}",
            "direction": "long" if position.direction == 1 else "short",
            "entry_ts": position.entry_ts.isoformat(),
            "exit_ts": bar.ts.isoformat(),
            "entry_price": round(position.entry_price, 4),
            "exit_price": round(price, 4),
            "stop_price": round(position.stop_price, 4),
            "quantity": round(position.quantity, 8),
            "entry_notional": round(position.entry_notional, 2),
            "entry_exposure_pct": round((position.entry_notional / position.entry_equity) * 100, 4)
            if position.entry_equity
            else 0.0,
            "initial_risk_amount": round(initial_risk_amount, 2),
            "initial_risk_pct": round((initial_risk_amount / position.entry_equity) * 100, 4)
            if position.entry_equity
            else 0.0,
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "bars_held": index - position.entry_index,
            "reason": reason,
            "mfe": round(position.max_favorable_excursion * position.quantity, 2),
            "mae": round(position.max_adverse_excursion * position.quantity, 2),
            "mfe_r": round(position.max_favorable_excursion / initial_risk, 4) if initial_risk else 0.0,
            "mae_r": round(position.max_adverse_excursion / initial_risk, 4) if initial_risk else 0.0,
            "return_on_equity_pct": round((net_pnl / equity_before) * 100, 4) if equity_before else 0.0,
            "entry_features": position.entry_features,
        }


def apply_patch_to_spec(spec: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(spec)
    path = patch["path"].split(".")
    cursor: dict[str, Any] = result
    for step in path[:-1]:
        next_value = cursor.get(step)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[step] = next_value
        cursor = next_value
    cursor[path[-1]] = patch["value"]
    return result
