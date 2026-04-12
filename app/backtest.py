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
    stop_initialized_on_index: int


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
) -> dict[str, Any]:
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
            "buy_hold_return": buy_hold_return,
            "outperformance": -buy_hold_return,
        }
    pnls = [trade["net_pnl"] for trade in trades]
    returns = [trade["return_on_equity_pct"] / 100 for trade in trades]
    wins = [trade for trade in trades if trade["net_pnl"] > 0]
    losses = [trade for trade in trades if trade["net_pnl"] < 0]
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
    return {
        "initial_capital": round(initial_capital, 2),
        "net_pnl": round(sum(pnls), 2),
        "return_pct": round((sum(pnls) / initial_capital) * 100, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else round(gross_profit, 4),
        "expected_payoff": round(sum(pnls) / len(pnls), 2),
        "sharpe": round((avg_return / math.sqrt(variance)) * math.sqrt(len(returns)), 4) if variance > 0 else 0.0,
        "sortino": round((avg_return / math.sqrt(downside_variance)) * math.sqrt(len(returns)), 4) if downside_variance > 0 else 0.0,
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
        "buy_hold_return": round(buy_hold_return, 2),
        "outperformance": round(sum(pnls) - buy_hold_return, 2),
    }


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
        quantity = float(parameters.get("quantity", 1.0))
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
            "time_exits": 0,
        }
        warmup = max(
            int(parameters["slow_len"]),
            int(parameters["atr_len"]),
            int(parameters["noise_lookback"]) + 1,
        )

        for index, bar in enumerate(bars):
            if index < warmup or fast[index] is None or slow[index] is None or atr_values[index] is None:
                equity_curve.append({"ts": bar.ts.isoformat(), "equity": round(equity, 2)})
                continue

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
            if parameters.get("allow_short", True) and short_signal:
                diagnostics["signals_short"] += 1
            else:
                short_signal = False

            entry_at_close = bar.close
            if position and position.direction == 1 and short_signal:
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
            elif position and position.direction == -1 and long_signal:
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
                if long_signal:
                    fill = entry_at_close + slippage
                    stop = fill - (float(atr_values[index]) * float(parameters["stop_mult"]))
                    commission = fill * quantity * commission_pct
                    position = Position(
                        direction=1,
                        entry_index=index,
                        entry_ts=bar.ts,
                        entry_price=fill,
                        stop_price=stop,
                        quantity=quantity,
                        entry_commission=commission,
                        stop_initialized_on_index=index,
                    )
                    diagnostics["entries"] += 1
                elif short_signal:
                    fill = max(entry_at_close - slippage, 0.0)
                    stop = fill + (float(atr_values[index]) * float(parameters["stop_mult"]))
                    commission = fill * quantity * commission_pct
                    position = Position(
                        direction=-1,
                        entry_index=index,
                        entry_ts=bar.ts,
                        entry_price=fill,
                        stop_price=stop,
                        quantity=quantity,
                        entry_commission=commission,
                        stop_initialized_on_index=index,
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

        buy_hold_return = (bars[-1].close - bars[warmup].close) * quantity if len(bars) > warmup else 0.0
        metrics = compute_metrics(
            initial_capital=float(parameters.get("initial_capital", 100_000.0)),
            trades=trades,
            equity_curve=equity_curve,
            buy_hold_return=buy_hold_return,
        )
        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "diagnostics": diagnostics,
        }

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
        return {
            "trade_id": f"tr_{uuid.uuid4().hex[:12]}",
            "direction": "long" if position.direction == 1 else "short",
            "entry_ts": position.entry_ts.isoformat(),
            "exit_ts": bar.ts.isoformat(),
            "entry_price": round(position.entry_price, 4),
            "exit_price": round(price, 4),
            "stop_price": round(position.stop_price, 4),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "bars_held": index - position.entry_index,
            "reason": reason,
            "return_on_equity_pct": round((net_pnl / equity_before) * 100, 4) if equity_before else 0.0,
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
