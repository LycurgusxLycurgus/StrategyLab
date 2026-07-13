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
    stop_moved_to_breakeven: bool = False
    time_decay_confirmation_suppressed: int = 0
    reverse_confirmation_suppressed: int = 0
    gann_exit_confirmation_suppressed: int = 0
    account_conversion_mode: str = "identity"
    contract_size: float = 0.0
    commission_per_lot_side: float = 0.0


@dataclass(slots=True)
class Pivot:
    index: int
    price: float
    kind: str


@dataclass(slots=True)
class FairValueGap:
    direction: int
    created_index: int
    top: float
    bottom: float
    gap_atr_multiple: float


@dataclass(slots=True)
class AsmSetup:
    direction: int
    created_index: int
    setup_type: str
    origin_index: int
    origin_price: float
    extreme_index: int
    extreme_price: float
    range_size: float
    range_atr_multiple: float
    entry_price: float
    stop_price: float
    target_price: float
    discount_premium_passed: bool
    fvg: FairValueGap | None = None
    retracement_index: int | None = None
    sweep_index: int | None = None
    sweep_price: float | None = None
    internal_confirmation_index: int | None = None
    internal_confirmation_type: str | None = None
    context_bias: str | None = None
    context_bias_event: str | None = None
    context_bias_index: int | None = None
    context_bias_ts: datetime | None = None
    context_bias_age: int | None = None


@dataclass(slots=True)
class QuantSmcZone:
    direction: int
    created_index: int
    top: float
    bottom: float
    score: float
    source: str
    mitigated: bool = False


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


def rolling_high(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < length:
            output.append(None)
            continue
        output.append(max(values[index + 1 - length : index + 1]))
    return output


def rolling_low(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < length:
            output.append(None)
            continue
        output.append(min(values[index + 1 - length : index + 1]))
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
    empty_exit_metrics = {
        "stop_exit_net_pnl": 0.0,
        "stop_exit_profit_factor": 0.0,
        "stop_exit_win_rate_pct": 0.0,
        "stop_exit_pnl_share_pct": 0.0,
        "reverse_exit_net_pnl": 0.0,
        "reverse_exit_profit_factor": 0.0,
        "reverse_exit_win_rate_pct": 0.0,
    }
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
            **empty_exit_metrics,
        }
    pnls = [trade["net_pnl"] for trade in trades]
    returns = [trade["return_on_equity_pct"] / 100 for trade in trades]
    wins = [trade for trade in trades if trade["net_pnl"] > 0]
    losses = [trade for trade in trades if trade["net_pnl"] < 0]
    exposures = [float(trade.get("entry_exposure_pct", 0.0)) for trade in trades]
    risk_pcts = [float(trade.get("initial_risk_pct", 0.0)) for trade in trades]
    gross_profit = sum(trade["net_pnl"] for trade in wins)
    gross_loss = abs(sum(trade["net_pnl"] for trade in losses))
    exit_metrics = exit_reason_risk_metrics(trades)
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
        point_equity = equity_point_value(point, initial_capital)
        peak = max(peak, point_equity)
        trough = min(trough, point_equity)
        drawdown = max(drawdown, peak - point_equity)
        drawdown_pct = max(drawdown_pct, ((peak - point_equity) / peak) * 100 if peak else 0.0)
        runup = max(runup, point_equity - trough)
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
        **exit_metrics,
    }


def exit_reason_risk_metrics(trades: list[dict[str, Any]]) -> dict[str, float]:
    output: dict[str, float] = {}
    total_net = sum(float(trade.get("net_pnl", 0.0)) for trade in trades)
    for reason in ("stop", "reverse"):
        segment = [trade for trade in trades if trade.get("reason") == reason]
        wins = [trade for trade in segment if float(trade.get("net_pnl", 0.0)) > 0]
        losses = [trade for trade in segment if float(trade.get("net_pnl", 0.0)) < 0]
        gross_profit = sum(float(trade.get("net_pnl", 0.0)) for trade in wins)
        gross_loss = abs(sum(float(trade.get("net_pnl", 0.0)) for trade in losses))
        net_pnl = gross_profit - gross_loss
        output[f"{reason}_exit_net_pnl"] = round(net_pnl, 2)
        output[f"{reason}_exit_profit_factor"] = round(gross_profit / gross_loss, 4) if gross_loss else round(gross_profit, 4)
        output[f"{reason}_exit_win_rate_pct"] = round((len(wins) / len(segment)) * 100, 2) if segment else 0.0
    output["stop_exit_pnl_share_pct"] = round((output["stop_exit_net_pnl"] / total_net) * 100, 2) if total_net > 0 else 0.0
    return output


def periodic_equity_metrics(equity_curve: list[dict[str, Any]], initial_capital: float) -> dict[str, float]:
    daily_closes: dict[str, float] = {}
    for point in equity_curve:
        ts = str(point.get("ts", ""))
        if not ts:
            continue
        day = ts[:10]
        daily_closes[day] = equity_point_value(point, initial_capital)
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


def equity_point_value(point: dict[str, Any], initial_capital: float) -> float:
    return float(point.get("equity", point.get("mark_to_market_equity", point.get("realized_equity", initial_capital))))


def mark_to_market_equity(realized_equity: float, position: Position | None, close_price: float, commission_pct: float) -> float:
    if position is None:
        return realized_equity
    if position.direction == 1:
        unrealized = (close_price - position.entry_price) * position.quantity
    else:
        unrealized = (position.entry_price - close_price) * position.quantity
    if position.account_conversion_mode == "quote_divide_price" and close_price > 0:
        unrealized /= close_price
    lots = position.quantity / position.contract_size if position.contract_size > 0 else 0.0
    exit_commission = (
        lots * position.commission_per_lot_side
        if position.commission_per_lot_side > 0
        else close_price * position.quantity * commission_pct
    )
    return realized_equity + unrealized - position.entry_commission - exit_commission


def benchmark_warmup_index(parameters: dict[str, Any], bar_count: int) -> int:
    if bar_count <= 1:
        return 0
    if "gann_high_period" in parameters or "donchian_length" in parameters:
        warmup = max(
            int(parameters.get("gann_high_period", 13)),
            int(parameters.get("gann_low_period", 21)),
            int(parameters.get("donchian_length", 55)),
            int(parameters.get("atr_len", 14)),
        )
        return min(warmup, bar_count - 1)
    if "pivot_len" in parameters:
        warmup = max(
            int(parameters.get("pivot_len", 5)) * 2 + 2,
            int(parameters.get("atr_len", 14)),
            int(parameters.get("ema_len", 100)),
        )
        return min(warmup, bar_count - 1)
    if "fast_len" not in parameters:
        return min(max(int(parameters.get("displacement_atr_len", 14)), int(parameters.get("external_pivot_period", 4)) * 2 + 2), bar_count - 1)
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
        if engine_id == "ma_cross_atr_stop_v1":
            return self._run_ma_cross_atr_stop(spec, bars)
        if engine_id == "ghl_dc_breakout_v1":
            return self._run_ghl_dc_breakout(spec, bars)
        if engine_id == "bos_demand_pullback_v1":
            return self._run_bos_demand_pullback(spec, bars)
        if engine_id == "asm_fib_liquidity_fvg_v1":
            return self._run_asm_fib_liquidity_fvg(spec, bars)
        if engine_id == "quant_smc_strategy_v1":
            return self._run_quant_smc_strategy(spec, bars)
        raise HTTPException(status_code=400, detail=f"Unsupported engine: {engine_id}")

    def _run_bos_demand_pullback(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters = spec["parameters"]
        execution_model = str(parameters.get("execution_model", "mt5_bar_proxy"))
        if execution_model not in {"next_bar_open", "research_same_close", "mt5_bar_proxy"}:
            raise HTTPException(status_code=400, detail="execution_model must be `next_bar_open`, `research_same_close`, or `mt5_bar_proxy`.")
        if len(bars) < 20:
            raise HTTPException(status_code=400, detail="BOS demand pullback engine requires at least 20 bars.")
        if bars[0].timeframe != spec.get("timeframe", bars[0].timeframe):
            raise HTTPException(
                status_code=400,
                detail=f"Dataset timeframe `{bars[0].timeframe}` does not match strategy timeframe `{spec.get('timeframe')}`.",
            )

        closes = [bar.close for bar in bars]
        atr_values = atr(bars, int(parameters.get("atr_len", 14)))
        ema_values = ema(closes, int(parameters.get("ema_len", 100)))
        tick_size = float(parameters.get("tick_size", 0.01))
        slippage = int(parameters.get("slippage_ticks", 0)) * tick_size
        commission_pct = float(parameters.get("commission_pct", 0.0)) / 100
        equity = float(parameters.get("initial_capital", 100_000.0))
        initial_capital = equity
        pivot_len = int(parameters.get("pivot_len", 5))
        min_green = int(parameters.get("min_green", 1))
        atr_mult = float(parameters.get("atr_mult", 2.0))
        max_zone_age = int(parameters.get("max_zone_age", 20))
        demand_lookback = int(parameters.get("demand_lookback_bars", 10))
        tp_r = float(parameters.get("tp_r", 1.5))
        variant = str(parameters.get("variant", "v0_exact_pine"))
        bos_break_mode = str(parameters.get("bos_break_mode", "wick"))
        ema_filter_enabled = bool(parameters.get("ema_filter_enabled", True))
        if variant == "v0_exact_pine":
            bos_break_mode = "wick"
            ema_filter_enabled = True
        elif variant == "v0_integrity_close_bos":
            bos_break_mode = "close"
            ema_filter_enabled = True
        elif variant == "v0_no_ema_diagnostic":
            bos_break_mode = "wick"
            ema_filter_enabled = False
        elif variant != "custom_controls":
            raise HTTPException(status_code=400, detail=f"Unsupported BOS demand variant: {variant}")
        if bos_break_mode not in {"wick", "close"}:
            raise HTTPException(status_code=400, detail="bos_break_mode must be `wick` or `close`.")
        same_bar_exit_policy = str(parameters.get("same_bar_exit_policy", "stop_first"))

        diagnostics = {
            "bars": len(bars),
            "signals_long": 0,
            "signals_short": 0,
            "entries": 0,
            "stop_exits": 0,
            "target_exits": 0,
            "reverse_exits": 0,
            "time_exits": 0,
            "same_bar_stop_first_exits": 0,
            "pending_entry_orders": 0,
            "pending_order_fills": 0,
            "dropped_pending_orders_eod": 0,
            "execution_model": execution_model,
            "confirmed_pivot_highs": 0,
            "bos_events": 0,
            "strong_impulses": 0,
            "demand_zones_created": 0,
            "zone_pullbacks": 0,
            "blocked_no_zone": 0,
            "blocked_no_bullish_candle": 0,
            "blocked_ema_filter": 0,
            "wick_bos_events": 0,
            "close_bos_events": 0,
            "ema_filter_enabled": int(ema_filter_enabled),
        }
        position: Position | None = None
        pending_order: dict[str, Any] | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        last_high: float | None = None
        high_broken = False
        green_count = 0
        first_green_open: float | None = None
        zone_top: float | None = None
        zone_bottom: float | None = None
        zone_bar: int | None = None

        def append_equity_point(current_bar: Bar) -> None:
            mtm = mark_to_market_equity(equity, position, current_bar.close, commission_pct)
            equity_curve.append(
                {
                    "ts": current_bar.ts.isoformat(),
                    "equity": round(mtm, 2),
                    "mark_to_market_equity": round(mtm, 2),
                    "realized_equity": round(equity, 2),
                }
            )

        def open_position(entry_bar: Bar, entry_index: int, signal: dict[str, Any]) -> Position:
            reference = entry_bar.close if execution_model == "research_same_close" else entry_bar.open
            fill = reference + slippage
            stop = float(signal["zone_bottom"])
            risk = max(fill - stop, tick_size)
            target = fill + (risk * tp_r)
            quantity = self._position_quantity(parameters, equity, fill, stop)
            entry_features = {
                "side": "long",
                "source_parent": "bos_demand_pullback",
                "variant": variant,
                "bos_break_mode": bos_break_mode,
                "ema_filter_enabled": ema_filter_enabled,
                "pivot_len": pivot_len,
                "atr_len": int(parameters.get("atr_len", 14)),
                "atr_mult": atr_mult,
                "min_green": min_green,
                "max_zone_age": max_zone_age,
                "demand_lookback_bars": demand_lookback,
                "tp_r": tp_r,
                "zone_top": round(float(signal["zone_top"]), 6),
                "zone_bottom": round(stop, 6),
                "zone_age": entry_index - int(signal["zone_bar"]),
                "last_high": round(float(signal["last_high"]), 6),
                "impulse_range": round(float(signal["impulse_range"]), 6),
                "impulse_atr_multiple": round(float(signal["impulse_range"]) / float(signal["atr_value"]), 6)
                if signal["atr_value"]
                else 0.0,
                "bullish_pattern": signal["bullish_pattern"],
                "ema_value": round(float(signal["ema_value"] or 0.0), 6),
                "target_price": round(target, 6),
                "same_bar_exit_policy": same_bar_exit_policy,
                "execution_model": execution_model,
                "signal_ts": bars[int(signal["signal_index"])].ts.isoformat(),
                "fill_ts": entry_bar.ts.isoformat(),
            }
            return Position(
                direction=1,
                entry_index=entry_index,
                entry_ts=entry_bar.ts,
                entry_price=fill,
                stop_price=stop,
                quantity=quantity,
                entry_commission=fill * quantity * commission_pct,
                entry_equity=equity,
                entry_notional=fill * quantity,
                initial_risk_per_unit=abs(fill - stop),
                stop_initialized_on_index=entry_index if execution_model in {"research_same_close", "mt5_bar_proxy"} else entry_index - 1,
                entry_features=entry_features,
            )

        for index, bar in enumerate(bars):
            current_atr = atr_values[index]
            if pending_order and execution_model in {"next_bar_open", "mt5_bar_proxy"} and position is None:
                position = open_position(bar, index, pending_order)
                diagnostics["entries"] += 1
                diagnostics["pending_order_fills"] += 1
                pending_order = None

            if position:
                self._update_excursion(position, bar)
                target = float(position.entry_features["target_price"])
                stop_can_trigger = index >= position.stop_initialized_on_index if execution_model == "mt5_bar_proxy" else index > position.stop_initialized_on_index
                stop_hit = stop_can_trigger and bar.low <= position.stop_price
                target_hit = stop_can_trigger and bar.high >= target
                if stop_hit and target_hit:
                    if same_bar_exit_policy == "target_first":
                        trade = self._close_trade(position, bar, index, max(target - slippage, 0.0), "target", commission_pct, equity)
                        diagnostics["target_exits"] += 1
                    else:
                        trade = self._close_trade(position, bar, index, max(position.stop_price - slippage, 0.0), "stop", commission_pct, equity)
                        diagnostics["same_bar_stop_first_exits"] += 1
                        diagnostics["stop_exits"] += 1
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    position = None
                elif stop_hit:
                    trade = self._close_trade(position, bar, index, max(position.stop_price - slippage, 0.0), "stop", commission_pct, equity)
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["stop_exits"] += 1
                    position = None
                elif target_hit:
                    trade = self._close_trade(position, bar, index, max(target - slippage, 0.0), "target", commission_pct, equity)
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["target_exits"] += 1
                    position = None

            confirmed = self._confirmed_pivot(bars, index, pivot_len)
            if confirmed and confirmed.kind == "high":
                last_high = confirmed.price
                high_broken = False
                diagnostics["confirmed_pivot_highs"] += 1

            if bar.close > bar.open:
                if green_count == 0:
                    first_green_open = bar.open
                green_count += 1
            else:
                green_count = 0
                first_green_open = None

            if index == 0 or current_atr is None or ema_values[index] is None:
                append_equity_point(bar)
                continue

            wick_bos = last_high is not None and not high_broken and bar.high > last_high and bars[index - 1].close <= last_high
            close_bos = last_high is not None and not high_broken and bar.close > last_high and bars[index - 1].close <= last_high
            bos = close_bos if bos_break_mode == "close" else wick_bos
            if bos:
                high_broken = True
                diagnostics["bos_events"] += 1
                if wick_bos:
                    diagnostics["wick_bos_events"] += 1
                if close_bos:
                    diagnostics["close_bos_events"] += 1

            impulse_range = (bar.close - first_green_open) if first_green_open is not None else 0.0
            strong_impulse = green_count >= min_green and impulse_range >= atr_mult * float(current_atr) and bos
            if strong_impulse:
                diagnostics["strong_impulses"] += 1
                for offset in range(1, min(demand_lookback, index) + 1):
                    prior = bars[index - offset]
                    if prior.close < prior.open:
                        zone_top = prior.high
                        zone_bottom = prior.low
                        zone_bar = index
                        diagnostics["demand_zones_created"] += 1
                        break

            zone_valid = zone_top is not None and zone_bottom is not None and zone_bar is not None and index > zone_bar and index - zone_bar <= max_zone_age
            pullback_into_zone = zone_valid and bar.low <= zone_top and bar.low >= zone_bottom and bar.close >= zone_top
            pattern = self._bos_bullish_pattern(bars, index)
            trend_ok = not ema_filter_enabled or bar.close > float(ema_values[index])
            if pullback_into_zone:
                diagnostics["zone_pullbacks"] += 1
            elif zone_top is None:
                diagnostics["blocked_no_zone"] += 1
            if pullback_into_zone and not pattern:
                diagnostics["blocked_no_bullish_candle"] += 1
            if pullback_into_zone and pattern and not trend_ok:
                diagnostics["blocked_ema_filter"] += 1

            if pullback_into_zone and pattern and trend_ok and position is None and pending_order is None:
                signal = {
                    "signal_index": index,
                    "zone_top": zone_top,
                    "zone_bottom": zone_bottom,
                    "zone_bar": zone_bar,
                    "last_high": last_high or 0.0,
                    "impulse_range": impulse_range,
                    "atr_value": float(current_atr),
                    "bullish_pattern": pattern,
                    "ema_value": ema_values[index],
                }
                diagnostics["signals_long"] += 1
                if execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                    pending_order = signal
                    diagnostics["pending_entry_orders"] += 1
                else:
                    position = open_position(bar, index, signal)
                    diagnostics["entries"] += 1
                    self._update_excursion(position, bar)

            append_equity_point(bar)

        if pending_order:
            diagnostics["dropped_pending_orders_eod"] += 1
        if position:
            last_bar = bars[-1]
            trade = self._close_trade(position, last_bar, len(bars) - 1, max(last_bar.close - slippage, 0.0), "time", commission_pct, equity)
            trades.append(trade)
            equity += trade["net_pnl"]
            diagnostics["time_exits"] += 1
            equity_curve[-1]["equity"] = round(equity, 2)
            equity_curve[-1]["mark_to_market_equity"] = round(equity, 2)
            equity_curve[-1]["realized_equity"] = round(equity, 2)

        warmup_index = benchmark_warmup_index(parameters, len(bars))
        buy_hold_start = bars[warmup_index].close
        buy_hold_end = bars[-1].close
        buy_hold_return_pct = ((buy_hold_end - buy_hold_start) / buy_hold_start) * 100 if buy_hold_start else 0.0
        buy_hold_return = initial_capital * (buy_hold_return_pct / 100)
        metrics = compute_metrics(
            initial_capital,
            trades,
            equity_curve,
            buy_hold_return,
            buy_hold_return_pct,
            buy_hold_start,
            buy_hold_end,
            buy_hold_drawdown_pct(bars, warmup_index),
        )
        return {"metrics": metrics, "trades": trades, "equity_curve": equity_curve, "diagnostics": diagnostics}

    def _run_asm_fib_liquidity_fvg(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters, profile_override_applied = self._resolve_asm_parameters(spec["parameters"])
        execution_model = str(parameters.get("execution_model", "mt5_bar_proxy"))
        if execution_model not in {"next_bar_open", "research_same_close", "mt5_bar_proxy"}:
            raise HTTPException(status_code=400, detail="execution_model must be `next_bar_open`, `research_same_close`, or `mt5_bar_proxy`.")
        if len(bars) < 10:
            raise HTTPException(status_code=400, detail="ASM engine requires at least 10 bars.")
        dataset_timeframe = bars[0].timeframe if bars else parameters.get("execution_timeframe", spec.get("timeframe", ""))
        if dataset_timeframe != parameters.get("execution_timeframe", spec.get("timeframe")):
            raise HTTPException(
                status_code=400,
                detail=f"Dataset timeframe `{dataset_timeframe}` does not match ASM execution timeframe `{parameters.get('execution_timeframe')}`.",
            )
        context_bars = (
            self._resample_bars(bars, str(parameters.get("execution_timeframe", dataset_timeframe)), str(parameters.get("context_timeframe", dataset_timeframe)))
            if parameters.get("resample_context_from_execution_bars", False)
            else []
        )
        higher_context_bars = (
            self._resample_bars(
                bars,
                str(parameters.get("execution_timeframe", dataset_timeframe)),
                str(parameters.get("higher_context_timeframe", parameters.get("context_timeframe", dataset_timeframe))),
            )
            if parameters.get("resample_context_from_execution_bars", False)
            else []
        )
        context_bias_by_index = self._context_bias_series(parameters, bars, context_bars)
        atr_len = int(parameters.get("displacement_atr_len", 14))
        atr_values = atr(bars, atr_len)
        pivot_period = int(parameters.get("external_pivot_period", 4))
        internal_pivot_period = int(parameters.get("internal_pivot_period", 2))
        warmup = max(atr_len, (pivot_period * 2) + 2, (internal_pivot_period * 2) + 2)
        tick_size = float(parameters.get("tick_size", 0.01))
        slippage = int(parameters.get("slippage_ticks", 0)) * tick_size
        commission_pct = float(parameters.get("commission_pct", 0.0)) / 100
        initial_capital = float(parameters.get("initial_capital", 100_000.0))
        equity = initial_capital
        position: Position | None = None
        active_setup: AsmSetup | None = None
        pending_setup: AsmSetup | None = None
        latest_high: Pivot | None = None
        latest_low: Pivot | None = None
        latest_internal_high: Pivot | None = None
        latest_internal_low: Pivot | None = None
        active_fvgs: list[FairValueGap] = []
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        diagnostics = {
            "bars": len(bars),
            "active_timeframe_profile": parameters.get("active_timeframe_profile", "none"),
            "context_bars_built": len(context_bars),
            "higher_context_bars_built": len(higher_context_bars),
            "context_bias_bullish_events": 0,
            "context_bias_bearish_events": 0,
            "blocked_no_context_bias": 0,
            "blocked_context_bias_mismatch": 0,
            "blocked_incomplete_context_bar": 0,
            "profile_override_applied": int(profile_override_applied),
            "dataset_timeframe_mismatch": 0,
            "setups_bullish": 0,
            "setups_bearish": 0,
            "external_setups_bullish": 0,
            "external_setups_bearish": 0,
            "internal_confirmations_bullish": 0,
            "internal_confirmations_bearish": 0,
            "setups_expired": 0,
            "signals_long": 0,
            "signals_short": 0,
            "entries": 0,
            "entries_after_internal_confirmation": 0,
            "blocked_no_fvg": 0,
            "blocked_no_sweep": 0,
            "blocked_no_internal_confirmation": 0,
            "blocked_internal_against_external_bias": 0,
            "blocked_not_discount_or_premium": 0,
            "blocked_time_risk": 0,
            "stop_exits": 0,
            "reverse_exits": 0,
            "time_decay_exits": 0,
            "breakeven_stop_moves": 0,
            "short_quality_gate_blocks": 0,
            "hybrid_time_decay_triage_exits": 0,
            "mfe_giveback_exits": 0,
            "hybrid_reverse_exit_blocks": 0,
            "target_exits": 0,
            "time_stop_exits": 0,
            "time_exits": 0,
            "same_bar_stop_first_exits": 0,
            "execution_model": execution_model,
            "pending_entry_orders": 0,
            "pending_order_fills": 0,
            "pending_orders_expired": 0,
        }
        last_context_bias_key: tuple[str | None, int | None] = (None, None)

        def append_equity_point(current_bar: Bar) -> None:
            mtm = mark_to_market_equity(equity, position, current_bar.close, commission_pct)
            equity_curve.append(
                {
                    "ts": current_bar.ts.isoformat(),
                    "equity": round(mtm, 2),
                    "mark_to_market_equity": round(mtm, 2),
                    "realized_equity": round(equity, 2),
                }
            )

        def open_asm_position(setup: AsmSetup, fill: float, entry_bar: Bar, entry_index: int) -> Position:
            quantity = self._position_quantity(parameters, equity, fill, setup.stop_price)
            entry_features = self._asm_entry_features(parameters, setup, entry_bar, entry_index)
            entry_features["execution_model"] = execution_model
            entry_features["signal_ts"] = bars[setup.internal_confirmation_index or setup.created_index].ts.isoformat()
            entry_features["fill_ts"] = entry_bar.ts.isoformat()
            return Position(
                direction=setup.direction,
                entry_index=entry_index,
                entry_ts=entry_bar.ts,
                entry_price=fill,
                stop_price=setup.stop_price,
                quantity=quantity,
                entry_commission=fill * quantity * commission_pct,
                entry_equity=equity,
                entry_notional=fill * quantity,
                initial_risk_per_unit=abs(fill - setup.stop_price),
                stop_initialized_on_index=entry_index if execution_model in {"research_same_close", "mt5_bar_proxy"} else entry_index - 1,
                entry_features=entry_features,
            )

        for index, bar in enumerate(bars):
            current_atr = atr_values[index]
            self._register_asm_fvg(parameters, bars, atr_values, active_fvgs, index)
            self._expire_asm_fvgs(parameters, bars, active_fvgs, index)

            confirmed_pivot = self._confirmed_pivot(bars, index, pivot_period)
            if confirmed_pivot:
                if confirmed_pivot.kind == "high":
                    latest_high = confirmed_pivot
                else:
                    latest_low = confirmed_pivot
            confirmed_internal_pivot = self._confirmed_pivot(bars, index, internal_pivot_period)
            if confirmed_internal_pivot:
                if confirmed_internal_pivot.kind == "high":
                    latest_internal_high = confirmed_internal_pivot
                else:
                    latest_internal_low = confirmed_internal_pivot

            if not position and pending_setup and execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                if index - pending_setup.created_index > int(parameters.get("max_setup_age_bars", 96)):
                    diagnostics["pending_orders_expired"] += 1
                    pending_setup = None
                elif parameters.get("entry_order_type", "limit_touch") == "limit_touch":
                    if self._asm_entry_touched(bar, pending_setup.entry_price):
                        fill = pending_setup.entry_price + slippage if pending_setup.direction == 1 else max(pending_setup.entry_price - slippage, 0.0)
                        position = open_asm_position(pending_setup, fill, bar, index)
                        diagnostics["entries"] += 1
                        diagnostics["pending_order_fills"] += 1
                        if pending_setup.internal_confirmation_index is not None:
                            diagnostics["entries_after_internal_confirmation"] += 1
                        pending_setup = None
                else:
                    fill = bar.open + slippage if pending_setup.direction == 1 else max(bar.open - slippage, 0.0)
                    position = open_asm_position(pending_setup, fill, bar, index)
                    diagnostics["entries"] += 1
                    diagnostics["pending_order_fills"] += 1
                    if pending_setup.internal_confirmation_index is not None:
                        diagnostics["entries_after_internal_confirmation"] += 1
                    pending_setup = None

            if position:
                self._update_excursion(position, bar)
                exit_result = self._asm_exit_position(
                    position=position,
                    bar=bar,
                    index=index,
                    slippage=slippage,
                    commission_pct=commission_pct,
                    equity=equity,
                    diagnostics=diagnostics,
                    allow_same_bar=True,
                )
                if exit_result:
                    trade, reason = exit_result
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics[reason] += 1
                    position = None

            if active_setup and index - active_setup.created_index > int(parameters.get("max_setup_age_bars", 96)):
                diagnostics["setups_expired"] += 1
                active_setup = None

            if not position and pending_setup is None and active_setup is None and index >= warmup and current_atr:
                context_bias = context_bias_by_index[index]
                context_bias_key = (context_bias.get("bias"), context_bias.get("bar_index"))
                if context_bias_key != last_context_bias_key:
                    if context_bias.get("bias") == "bullish":
                        diagnostics["context_bias_bullish_events"] += 1
                    elif context_bias.get("bias") == "bearish":
                        diagnostics["context_bias_bearish_events"] += 1
                    last_context_bias_key = context_bias_key
                new_setup = self._maybe_create_asm_setup(
                    parameters=parameters,
                    bars=bars,
                    atr_value=float(current_atr),
                    active_fvgs=active_fvgs,
                    latest_high=latest_high,
                    latest_low=latest_low,
                    index=index,
                    context_bias=context_bias,
                )
                if new_setup:
                    active_setup = new_setup
                    if new_setup.direction == 1:
                        diagnostics["setups_bullish"] += 1
                        diagnostics["external_setups_bullish"] += 1
                    else:
                        diagnostics["setups_bearish"] += 1
                        diagnostics["external_setups_bearish"] += 1

            if not position and active_setup:
                self._update_asm_setup_retracement(bars, active_setup, index)
                self._update_asm_setup_sweep(parameters, bars, active_setup, index)
                confirmation = self._asm_internal_confirmation(
                    parameters=parameters,
                    bars=bars,
                    setup=active_setup,
                    latest_internal_high=latest_internal_high,
                    latest_internal_low=latest_internal_low,
                    index=index,
                )
                if confirmation:
                    active_setup.internal_confirmation_index = index
                    active_setup.internal_confirmation_type = confirmation
                    if active_setup.direction == 1:
                        diagnostics["internal_confirmations_bullish"] += 1
                    else:
                        diagnostics["internal_confirmations_bearish"] += 1
                block_reason = self._asm_setup_block_reason(parameters, bars, active_setup, active_fvgs, index)
                if block_reason:
                    diagnostics[block_reason] += 1
                elif self._asm_entry_ready(parameters, active_setup):
                    if active_setup.direction == 1:
                        diagnostics["signals_long"] += 1
                    else:
                        diagnostics["signals_short"] += 1
                    if execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                        pending_setup = active_setup
                        diagnostics["pending_entry_orders"] += 1
                        active_setup = None
                    else:
                        entry_reference = bar.close if self._asm_internal_required(parameters) else active_setup.entry_price
                        fill = entry_reference + slippage if active_setup.direction == 1 else max(entry_reference - slippage, 0.0)
                        position = open_asm_position(active_setup, fill, bar, index)
                        diagnostics["entries"] += 1
                        if active_setup.internal_confirmation_index is not None:
                            diagnostics["entries_after_internal_confirmation"] += 1
                        active_setup = None
                        self._update_excursion(position, bar)
                        exit_result = self._asm_exit_position(
                            position=position,
                            bar=bar,
                            index=index,
                            slippage=slippage,
                            commission_pct=commission_pct,
                            equity=equity,
                            diagnostics=diagnostics,
                            allow_same_bar=True,
                        )
                        if exit_result:
                            trade, reason = exit_result
                            trades.append(trade)
                            equity += trade["net_pnl"]
                            diagnostics[reason] += 1
                            position = None

            append_equity_point(bar)

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
            equity_curve[-1] = {
                "ts": last_bar.ts.isoformat(),
                "equity": round(equity, 2),
                "mark_to_market_equity": round(equity, 2),
                "realized_equity": round(equity, 2),
            }

        buy_hold_start_price = bars[warmup].close if len(bars) > warmup else bars[0].close
        buy_hold_end_price = bars[-1].close
        buy_hold_return_pct = (
            ((buy_hold_end_price - buy_hold_start_price) / buy_hold_start_price) * 100
            if buy_hold_start_price
            else 0.0
        )
        buy_hold_return = initial_capital * (buy_hold_return_pct / 100)
        metrics = compute_metrics(
            initial_capital=initial_capital,
            trades=trades,
            equity_curve=equity_curve,
            buy_hold_return=buy_hold_return,
            buy_hold_return_pct=buy_hold_return_pct,
            buy_hold_start_price=buy_hold_start_price,
            buy_hold_end_price=buy_hold_end_price,
            buy_hold_max_drawdown_pct=buy_hold_drawdown_pct(bars, warmup),
        )
        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "diagnostics": diagnostics,
            "resolved_parameters": parameters,
        }

    def _run_ma_cross_atr_stop(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters = spec["parameters"]
        execution_model = str(parameters.get("execution_model", "mt5_bar_proxy"))
        if execution_model not in {"next_bar_open", "research_same_close", "mt5_bar_proxy"}:
            raise HTTPException(status_code=400, detail="execution_model must be `next_bar_open`, `research_same_close`, or `mt5_bar_proxy`.")
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
        mt5_bar_proxy = execution_model == "mt5_bar_proxy"
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
            "short_time_risk_filter_blocks": 0,
            "hybrid_time_decay_triage_exits": 0,
            "mfe_giveback_exits": 0,
            "hybrid_reverse_exit_blocks": 0,
            "reverse_confirmation_candidates": 0,
            "reverse_confirmation_exits_allowed": 0,
            "reverse_confirmation_suppressed": 0,
            "reverse_confirmation_adverse_escape_allowed": 0,
            "reverse_confirmation_suppressed_net_pnl": 0.0,
            "time_decay_exits": 0,
            "time_decay_confirmation_candidates": 0,
            "time_decay_confirmation_exits": 0,
            "time_decay_confirmation_suppressed": 0,
            "time_decay_confirmation_suppressed_net_pnl": 0.0,
            "time_exits": 0,
            "mt5_stop_modify_rejects": 0,
            "entry_exposure_gate_blocks": 0,
            "entry_exposure_gate_long_blocks": 0,
            "entry_exposure_gate_short_blocks": 0,
            "entry_blackbox_veto_blocks": 0,
            "entry_blackbox_veto_long_blocks": 0,
            "entry_blackbox_veto_short_blocks": 0,
            "execution_model": execution_model,
            "pending_entry_orders": 0,
            "pending_reverse_orders": 0,
            "pending_order_fills": 0,
            "dropped_pending_orders_eod": 0,
        }
        warmup = max(
            int(parameters["fast_len"]),
            int(parameters["slow_len"]),
            int(parameters["atr_len"]),
            int(parameters["noise_lookback"]) + 1,
        )
        pending_order: dict[str, Any] | None = None

        def append_equity_point(current_bar: Bar) -> None:
            mtm = mark_to_market_equity(equity, position, current_bar.close, commission_pct)
            equity_curve.append(
                {
                    "ts": current_bar.ts.isoformat(),
                    "equity": round(mtm, 2),
                    "mark_to_market_equity": round(mtm, 2),
                    "realized_equity": round(equity, 2),
                }
            )

        def open_position(
            direction: int,
            entry_bar: Bar,
            entry_index: int,
            signal_index: int,
            signal_atr: float,
            signal_cross_count: int,
        ) -> Position:
            if direction == 1:
                fill = entry_bar.close + slippage if execution_model == "research_same_close" else entry_bar.open + slippage
                stop = fill - (signal_atr * float(parameters["stop_mult"]))
            else:
                reference = entry_bar.close if execution_model == "research_same_close" else entry_bar.open
                fill = max(reference - slippage, 0.0)
                stop = fill + (signal_atr * float(parameters["stop_mult"]))
            quantity = self._position_quantity(parameters, equity, fill, stop)
            entry_features = self._entry_features(
                bars=bars,
                index=signal_index,
                direction=direction,
                fast=fast,
                slow=slow,
                atr_values=atr_values,
                cross_count=signal_cross_count,
                stop_price=stop,
                entry_price=fill,
            )
            entry_features["execution_model"] = execution_model
            entry_features["signal_ts"] = bars[signal_index].ts.isoformat()
            entry_features["fill_ts"] = entry_bar.ts.isoformat()
            entry_notional = fill * quantity
            if not self._entry_blackbox_veto_allows_entry(
                parameters=parameters,
                direction=direction,
                entry_ts=entry_bar.ts,
                diagnostics=diagnostics,
            ):
                raise ValueError("entry_blackbox_veto_blocked")
            if not self._entry_exposure_gate_allows_entry(
                parameters=parameters,
                direction=direction,
                equity=equity,
                entry_notional=entry_notional,
                diagnostics=diagnostics,
            ):
                raise ValueError("entry_exposure_gate_blocked")
            return Position(
                direction=direction,
                entry_index=entry_index,
                entry_ts=entry_bar.ts,
                entry_price=fill,
                stop_price=stop,
                quantity=quantity,
                entry_commission=fill * quantity * commission_pct,
                entry_equity=equity,
                entry_notional=entry_notional,
                initial_risk_per_unit=abs(fill - stop),
                stop_initialized_on_index=entry_index if execution_model in {"research_same_close", "mt5_bar_proxy"} else entry_index - 1,
                entry_features=entry_features,
            )

        for index, bar in enumerate(bars):
            if index < warmup or fast[index] is None or slow[index] is None or atr_values[index] is None:
                append_equity_point(bar)
                continue

            if pending_order and execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                if pending_order.get("close_existing") and position:
                    exit_price = max(bar.open - slippage, 0.0) if position.direction == 1 else bar.open + slippage
                    trade = self._close_trade(
                        position=position,
                        bar=bar,
                        index=index,
                        price=exit_price,
                        reason="reverse",
                        commission_pct=commission_pct,
                        equity_before=equity,
                    )
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["reverse_exits"] += 1
                    position = None
                if position is None and pending_order.get("direction"):
                    try:
                        position = open_position(
                            direction=int(pending_order["direction"]),
                            entry_bar=bar,
                            entry_index=index,
                            signal_index=int(pending_order["signal_index"]),
                            signal_atr=float(pending_order["atr_value"]),
                            signal_cross_count=int(pending_order.get("cross_count", 0)),
                        )
                        diagnostics["entries"] += 1
                        diagnostics["pending_order_fills"] += 1
                    except ValueError:
                        pass
                pending_order = None

            if position:
                self._update_excursion(position, bar)

            stop_can_trigger = (
                position is not None
                and (index >= position.stop_initialized_on_index if mt5_bar_proxy else index > position.stop_initialized_on_index)
            )
            if position and stop_can_trigger:
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
                            if mt5_bar_proxy and new_stop >= bar.close:
                                diagnostics["mt5_stop_modify_rejects"] += 1
                                new_stop = position.stop_price
                            if new_stop > position.stop_price:
                                position.stop_price = new_stop
                                position.stop_moved_to_breakeven = True
                                diagnostics["breakeven_stop_moves"] += 1
                        else:
                            new_stop = position.entry_price - (initial_risk * lock_r)
                            if mt5_bar_proxy and new_stop <= bar.close:
                                diagnostics["mt5_stop_modify_rejects"] += 1
                                new_stop = position.stop_price
                            if new_stop < position.stop_price:
                                position.stop_price = new_stop
                                position.stop_moved_to_breakeven = True
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
                        if not self._time_decay_confirmation_allows_exit(
                            parameters=parameters,
                            position=position,
                            unrealized_r=unrealized_r,
                            mfe_r=mfe_r,
                            diagnostics=diagnostics,
                        ):
                            append_equity_point(bar)
                            continue
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
                    if position.direction == 1:
                        unrealized = bar.close - position.entry_price
                    else:
                        unrealized = position.entry_price - bar.close
                    unrealized_r = unrealized / initial_risk if initial_risk else 0.0
                    if not self._time_decay_confirmation_allows_exit(
                        parameters=parameters,
                        position=position,
                        unrealized_r=unrealized_r,
                        mfe_r=mfe_r,
                        diagnostics=diagnostics,
                    ):
                        append_equity_point(bar)
                        continue
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

            if position and parameters.get("mfe_giveback_exit_enabled", False):
                initial_risk = abs(position.entry_price - position.stop_price)
                if initial_risk:
                    if position.direction == 1:
                        unrealized = bar.close - position.entry_price
                    else:
                        unrealized = position.entry_price - bar.close
                    unrealized_r = unrealized / initial_risk
                    mfe_r = position.max_favorable_excursion / initial_risk
                    trigger_r = float(parameters.get("mfe_giveback_trigger_r", 1.0))
                    floor_r = float(parameters.get("mfe_giveback_floor_r", 0.0))
                    if mfe_r >= trigger_r and unrealized_r <= floor_r:
                        exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                        trade = self._close_trade(
                            position=position,
                            bar=bar,
                            index=index,
                            price=exit_price,
                            reason="mfe_giveback",
                            commission_pct=commission_pct,
                            equity_before=equity,
                        )
                        trades.append(trade)
                        equity += trade["net_pnl"]
                        diagnostics["mfe_giveback_exits"] += 1
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

            if short_signal and parameters.get("short_time_risk_filter_enabled", False):
                blocked_weekdays = {int(item) for item in parameters.get("short_time_risk_block_weekdays", [])}
                blocked_hours = {int(item) for item in parameters.get("short_time_risk_block_utc_hours", [])}
                if bar.ts.weekday() in blocked_weekdays or bar.ts.hour in blocked_hours:
                    diagnostics["short_time_risk_filter_blocks"] += 1
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

            if position and not reverse_exit_blocked:
                if not self._reverse_confirmation_allows_exit(
                    parameters=parameters,
                    position=position,
                    index=index,
                    current_close=bar.close,
                    long_signal=long_signal,
                    short_signal=short_signal,
                    diagnostics=diagnostics,
                ):
                    reverse_exit_blocked = True
                    entry_long_signal = False
                    entry_short_signal = False

            if execution_model in {"next_bar_open", "mt5_bar_proxy"} and position and not reverse_exit_blocked:
                if position.direction == 1 and short_signal:
                    pending_order = {
                        "direction": -1,
                        "close_existing": True,
                        "signal_index": index,
                        "atr_value": float(atr_values[index]),
                        "cross_count": cross_count,
                    }
                    diagnostics["pending_reverse_orders"] += 1
                    entry_long_signal = False
                    entry_short_signal = False
                elif position.direction == -1 and long_signal:
                    pending_order = {
                        "direction": 1,
                        "close_existing": True,
                        "signal_index": index,
                        "atr_value": float(atr_values[index]),
                        "cross_count": cross_count,
                    }
                    diagnostics["pending_reverse_orders"] += 1
                    entry_long_signal = False
                    entry_short_signal = False

            if execution_model == "research_same_close" and position and position.direction == 1 and short_signal and not reverse_exit_blocked:
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
            elif execution_model == "research_same_close" and position and position.direction == -1 and long_signal and not reverse_exit_blocked:
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

            if mt5_bar_proxy:
                if entry_long_signal:
                    pending_order = {
                        "direction": 1,
                        "close_existing": False,
                        "atr_value": float(atr_values[index]),
                        "signal_index": index,
                        "cross_count": cross_count,
                    }
                    diagnostics["pending_entry_orders"] += 1
                elif entry_short_signal:
                    pending_order = {
                        "direction": -1,
                        "close_existing": False,
                        "atr_value": float(atr_values[index]),
                        "signal_index": index,
                        "cross_count": cross_count,
                    }
                    diagnostics["pending_entry_orders"] += 1
            elif position is None:
                if entry_long_signal:
                    if execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                        pending_order = {
                            "direction": 1,
                            "close_existing": False,
                            "signal_index": index,
                            "atr_value": float(atr_values[index]),
                            "cross_count": cross_count,
                        }
                        diagnostics["pending_entry_orders"] += 1
                    else:
                        try:
                            position = open_position(1, bar, index, index, float(atr_values[index]), cross_count)
                            diagnostics["entries"] += 1
                        except ValueError:
                            pass
                elif entry_short_signal:
                    if execution_model in {"next_bar_open", "mt5_bar_proxy"}:
                        pending_order = {
                            "direction": -1,
                            "close_existing": False,
                            "signal_index": index,
                            "atr_value": float(atr_values[index]),
                            "cross_count": cross_count,
                        }
                        diagnostics["pending_entry_orders"] += 1
                    else:
                        try:
                            position = open_position(-1, bar, index, index, float(atr_values[index]), cross_count)
                            diagnostics["entries"] += 1
                        except ValueError:
                            pass

            append_equity_point(bar)

        if pending_order:
            diagnostics["dropped_pending_orders_eod"] += 1
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
            equity_curve[-1] = {
                "ts": last_bar.ts.isoformat(),
                "equity": round(equity, 2),
                "mark_to_market_equity": round(equity, 2),
                "realized_equity": round(equity, 2),
            }

        diagnostics["time_decay_confirmation_suppressed_net_pnl"] = round(
            sum(trade["net_pnl"] for trade in trades if int(trade.get("time_decay_confirmation_suppressed", 0)) > 0),
            2,
        )
        diagnostics["reverse_confirmation_suppressed_net_pnl"] = round(
            sum(trade["net_pnl"] for trade in trades if int(trade.get("reverse_confirmation_suppressed", 0)) > 0),
            2,
        )

        diagnostics["time_decay_confirmation_suppressed_net_pnl"] = round(
            sum(
                trade["net_pnl"]
                for trade in trades
                if int(trade.get("time_decay_confirmation_suppressed", 0)) > 0
            ),
            2,
        )
        diagnostics["reverse_confirmation_suppressed_net_pnl"] = round(
            sum(
                trade["net_pnl"]
                for trade in trades
                if int(trade.get("reverse_confirmation_suppressed", 0)) > 0
            ),
            2,
        )
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
    def _time_decay_confirmation_allows_exit(
        *,
        parameters: dict[str, Any],
        position: Position,
        unrealized_r: float,
        mfe_r: float,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not parameters.get("time_decay_triage_confirmation_enabled", False):
            return True
        diagnostics["time_decay_confirmation_candidates"] += 1
        max_unrealized_r = float(parameters.get("time_decay_confirm_max_unrealized_r", 0.0))
        max_mfe_r = float(parameters.get("time_decay_confirm_max_mfe_r", 0.35))
        require_no_breakeven = bool(parameters.get("time_decay_confirm_require_no_breakeven_move", False))
        confirmed = unrealized_r <= max_unrealized_r and mfe_r <= max_mfe_r
        if require_no_breakeven and position.stop_moved_to_breakeven:
            confirmed = False
        if confirmed:
            diagnostics["time_decay_confirmation_exits"] += 1
            return True
        diagnostics["time_decay_confirmation_suppressed"] += 1
        position.time_decay_confirmation_suppressed += 1
        return False

    @staticmethod
    def _reverse_confirmation_allows_exit(
        *,
        parameters: dict[str, Any],
        position: Position,
        index: int,
        current_close: float,
        long_signal: bool,
        short_signal: bool,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not parameters.get("reverse_confirmation_enabled", False):
            return True
        opposite_signal = (position.direction == 1 and short_signal) or (position.direction == -1 and long_signal)
        if not opposite_signal:
            return True
        diagnostics["reverse_confirmation_candidates"] += 1
        initial_risk = abs(position.entry_price - position.stop_price)
        if not initial_risk:
            diagnostics["reverse_confirmation_exits_allowed"] += 1
            return True
        bars_held = index - position.entry_index
        mfe_r = position.max_favorable_excursion / initial_risk
        unrealized = current_close - position.entry_price if position.direction == 1 else position.entry_price - current_close
        unrealized_r = unrealized / initial_risk

        max_bars = int(parameters.get("reverse_confirm_max_bars", 2))
        min_mfe_r = float(parameters.get("reverse_confirm_min_mfe_r", 0.20))
        adverse_escape_r = float(parameters.get("reverse_confirm_allow_if_unrealized_r_lte", -0.35))
        require_no_breakeven = bool(parameters.get("reverse_confirm_require_no_breakeven_move", False))

        is_young = bars_held <= max_bars
        weak_excursion = mfe_r < min_mfe_r
        adverse_escape = unrealized_r <= adverse_escape_r
        suppress_reverse = is_young and weak_excursion and not adverse_escape
        if require_no_breakeven and position.stop_moved_to_breakeven:
            suppress_reverse = False

        if suppress_reverse:
            diagnostics["reverse_confirmation_suppressed"] += 1
            position.reverse_confirmation_suppressed += 1
            return False
        if adverse_escape:
            diagnostics["reverse_confirmation_adverse_escape_allowed"] += 1
        diagnostics["reverse_confirmation_exits_allowed"] += 1
        return True

    @staticmethod
    def _entry_exposure_gate_allows_entry(
        *,
        parameters: dict[str, Any],
        direction: int,
        equity: float,
        entry_notional: float,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not parameters.get("entry_exposure_gate_enabled", False):
            return True
        exposure_pct = (entry_notional / equity) * 100 if equity > 0 else float("inf")
        max_exposure_pct = float(parameters.get("entry_exposure_gate_max_pct", 75.0))
        if exposure_pct <= max_exposure_pct:
            return True
        diagnostics["entry_exposure_gate_blocks"] += 1
        if direction == 1:
            diagnostics["entry_exposure_gate_long_blocks"] += 1
        else:
            diagnostics["entry_exposure_gate_short_blocks"] += 1
        return False

    @staticmethod
    def _entry_blackbox_veto_allows_entry(
        *,
        parameters: dict[str, Any],
        direction: int,
        entry_ts: datetime,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not parameters.get("entry_blackbox_veto_enabled", False):
            return True
        blocked_hours = {int(item) for item in parameters.get("entry_blackbox_veto_utc_hours", [])}
        side = "long" if direction == 1 else "short"
        side_months = {str(item).strip().lower() for item in parameters.get("entry_blackbox_veto_side_months", [])}
        blocked = entry_ts.hour in blocked_hours or f"{side}:{entry_ts.month}" in side_months
        if not blocked:
            return True
        diagnostics["entry_blackbox_veto_blocks"] += 1
        if direction == 1:
            diagnostics["entry_blackbox_veto_long_blocks"] += 1
        else:
            diagnostics["entry_blackbox_veto_short_blocks"] += 1
        return False

    @staticmethod
    def _bos_bullish_pattern(bars: list[Bar], index: int) -> str | None:
        bar = bars[index]
        previous = bars[index - 1] if index > 0 else bar
        body = abs(bar.close - bar.open)
        range_size = bar.high - bar.low
        if range_size <= 0:
            return None
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low
        marubozu = bar.close > bar.open and upper_wick <= range_size * 0.1 and lower_wick <= range_size * 0.1
        engulfing = bar.close > bar.open and previous.close < previous.open and bar.close > previous.open and bar.open <= previous.close
        pinbar = bar.close > bar.open and lower_wick >= body * 2 and upper_wick <= body
        if marubozu:
            return "marubozu"
        if engulfing:
            return "engulfing"
        if pinbar:
            return "pinbar"
        return None

    @staticmethod
    def _confirmed_pivot(bars: list[Bar], index: int, period: int) -> Pivot | None:
        center = index - period
        if center < period:
            return None
        window = bars[center - period : center + period + 1]
        center_bar = bars[center]
        if center_bar.high == max(item.high for item in window):
            return Pivot(index=center, price=center_bar.high, kind="high")
        if center_bar.low == min(item.low for item in window):
            return Pivot(index=center, price=center_bar.low, kind="low")
        return None

    @staticmethod
    def _resolve_asm_parameters(parameters: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        resolved = copy.deepcopy(parameters)
        profile_name = resolved.get("active_timeframe_profile")
        profiles = resolved.get("timeframe_profiles", {})
        applied = False
        if resolved.get("use_timeframe_profile_overrides", False) and profile_name and isinstance(profiles, dict):
            profile = profiles.get(profile_name, {})
            if isinstance(profile, dict):
                for key, value in profile.items():
                    resolved[key] = copy.deepcopy(value)
                applied = True
        return resolved, applied

    @staticmethod
    def _timeframe_minutes(timeframe: str) -> int:
        normalized = timeframe.strip().lower()
        if normalized.endswith("m"):
            return int(normalized[:-1])
        if normalized.endswith("h"):
            return int(normalized[:-1]) * 60
        if normalized.endswith("d"):
            return int(normalized[:-1]) * 1440
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe for ASM resampling: {timeframe}")

    def _resample_bars(self, bars: list[Bar], source_timeframe: str, target_timeframe: str) -> list[Bar]:
        source_minutes = self._timeframe_minutes(source_timeframe)
        target_minutes = self._timeframe_minutes(target_timeframe)
        if target_minutes == source_minutes:
            return list(bars)
        if target_minutes < source_minutes or target_minutes % source_minutes:
            raise HTTPException(status_code=400, detail=f"Cannot resample {source_timeframe} bars into {target_timeframe} context.")
        factor = target_minutes // source_minutes
        output: list[Bar] = []
        for start in range(0, len(bars) - factor + 1, factor):
            chunk = bars[start : start + factor]
            if len(chunk) < factor:
                break
            output.append(
                Bar(
                    ts=chunk[-1].ts,
                    open=chunk[0].open,
                    high=max(item.high for item in chunk),
                    low=min(item.low for item in chunk),
                    close=chunk[-1].close,
                    volume=sum(item.volume for item in chunk),
                    symbol=chunk[-1].symbol,
                    timeframe=target_timeframe,
                )
            )
        return output

    def _context_bias_for_index(
        self,
        parameters: dict[str, Any],
        execution_bars: list[Bar],
        context_bars: list[Bar],
        execution_index: int,
    ) -> dict[str, Any]:
        if not parameters.get("context_bias_required", False):
            return {"bias": None, "event": "not_required", "bar_index": None, "bar_ts": None, "age": None}
        if not context_bars:
            return {"bias": None, "event": None, "bar_index": None, "bar_ts": None, "age": None}
        execution_tf = str(parameters.get("execution_timeframe", execution_bars[0].timeframe))
        context_tf = str(parameters.get("context_timeframe", execution_tf))
        factor = self._timeframe_minutes(context_tf) // self._timeframe_minutes(execution_tf)
        completed_count = (execution_index + 1) // factor
        usable = context_bars[:completed_count]
        if len(usable) < (int(parameters.get("external_pivot_period", 4)) * 2) + 2:
            return {"bias": None, "event": None, "bar_index": None, "bar_ts": None, "age": None}
        event = self._latest_structure_event(usable, int(parameters.get("external_pivot_period", 4)), str(parameters.get("context_bias_event", "bos_or_choch")))
        if not event:
            return {"bias": None, "event": None, "bar_index": None, "bar_ts": None, "age": None}
        return {
            "bias": event["bias"],
            "event": event["event"],
            "bar_index": event["bar_index"],
            "bar_ts": usable[event["bar_index"]].ts,
            "age": len(usable) - 1 - event["bar_index"],
        }

    def _context_bias_series(
        self,
        parameters: dict[str, Any],
        execution_bars: list[Bar],
        context_bars: list[Bar],
    ) -> list[dict[str, Any]]:
        empty = {"bias": None, "event": None, "bar_index": None, "bar_ts": None, "age": None}
        if not execution_bars:
            return []
        if not parameters.get("context_bias_required", False):
            return [{"bias": None, "event": "not_required", "bar_index": None, "bar_ts": None, "age": None} for _ in execution_bars]
        if not context_bars:
            return [dict(empty) for _ in execution_bars]
        execution_tf = str(parameters.get("execution_timeframe", execution_bars[0].timeframe))
        context_tf = str(parameters.get("context_timeframe", execution_tf))
        factor = self._timeframe_minutes(context_tf) // self._timeframe_minutes(execution_tf)
        pivot_period = int(parameters.get("external_pivot_period", 4))
        event_mode = str(parameters.get("context_bias_event", "bos_or_choch"))
        context_events = self._context_structure_events(context_bars, pivot_period, event_mode)
        series: list[dict[str, Any]] = []
        for execution_index in range(len(execution_bars)):
            completed_count = (execution_index + 1) // factor
            context_index = completed_count - 1
            if context_index < 0 or context_index >= len(context_events):
                series.append(dict(empty))
                continue
            series.append(dict(context_events[context_index]))
        return series

    def _context_structure_events(self, bars: list[Bar], pivot_period: int, event_mode: str) -> list[dict[str, Any]]:
        latest_high: Pivot | None = None
        latest_low: Pivot | None = None
        latest_event: dict[str, Any] | None = None
        events: list[dict[str, Any]] = []
        for index, bar in enumerate(bars):
            pivot = self._confirmed_pivot(bars, index, pivot_period)
            if pivot:
                if pivot.kind == "high":
                    latest_high = pivot
                else:
                    latest_low = pivot
            if latest_high and bar.close > latest_high.price and event_mode in {"bos_or_choch", "bos_only", "choch_only"}:
                latest_event = {"bias": "bullish", "event": "bullish_bos", "bar_index": index, "bar_ts": bar.ts}
            if latest_low and bar.close < latest_low.price and event_mode in {"bos_or_choch", "bos_only", "choch_only"}:
                latest_event = {"bias": "bearish", "event": "bearish_bos", "bar_index": index, "bar_ts": bar.ts}
            if latest_event:
                event = dict(latest_event)
                event["age"] = index - int(event["bar_index"])
                events.append(event)
            else:
                events.append({"bias": None, "event": None, "bar_index": None, "bar_ts": None, "age": None})
        return events

    def _latest_structure_event(self, bars: list[Bar], pivot_period: int, event_mode: str) -> dict[str, Any] | None:
        latest_high: Pivot | None = None
        latest_low: Pivot | None = None
        latest_event: dict[str, Any] | None = None
        for index, bar in enumerate(bars):
            pivot = self._confirmed_pivot(bars, index, pivot_period)
            if pivot:
                if pivot.kind == "high":
                    latest_high = pivot
                else:
                    latest_low = pivot
            if latest_high and bar.close > latest_high.price and event_mode in {"bos_or_choch", "bos_only", "choch_only"}:
                latest_event = {"bias": "bullish", "event": "bullish_bos", "bar_index": index}
            if latest_low and bar.close < latest_low.price and event_mode in {"bos_or_choch", "bos_only", "choch_only"}:
                latest_event = {"bias": "bearish", "event": "bearish_bos", "bar_index": index}
        return latest_event

    @staticmethod
    def _register_asm_fvg(
        parameters: dict[str, Any],
        bars: list[Bar],
        atr_values: list[float | None],
        active_fvgs: list[FairValueGap],
        index: int,
    ) -> None:
        if not parameters.get("fvg_enabled", True) or index < 2 or not atr_values[index]:
            return
        min_gap = float(parameters.get("fvg_min_gap_atr", 0.05)) * float(atr_values[index])
        older = bars[index - 2]
        current = bars[index]
        if current.low > older.high and current.low - older.high >= min_gap:
            active_fvgs.append(
                FairValueGap(
                    direction=1,
                    created_index=index,
                    bottom=older.high,
                    top=current.low,
                    gap_atr_multiple=round((current.low - older.high) / float(atr_values[index]), 6),
                )
            )
        if current.high < older.low and older.low - current.high >= min_gap:
            active_fvgs.append(
                FairValueGap(
                    direction=-1,
                    created_index=index,
                    bottom=current.high,
                    top=older.low,
                    gap_atr_multiple=round((older.low - current.high) / float(atr_values[index]), 6),
                )
            )

    @staticmethod
    def _expire_asm_fvgs(parameters: dict[str, Any], bars: list[Bar], active_fvgs: list[FairValueGap], index: int) -> None:
        max_age = int(parameters.get("fvg_max_age_bars", 96))
        mitigation_rule = parameters.get("fvg_mitigation_rule", "touch_through_far_edge")
        current = bars[index]
        retained: list[FairValueGap] = []
        for fvg in active_fvgs:
            if index - fvg.created_index > max_age:
                continue
            mitigated = False
            if mitigation_rule == "touch_through_far_edge" and index > fvg.created_index:
                if fvg.direction == 1:
                    mitigated = current.low <= fvg.bottom
                else:
                    mitigated = current.high >= fvg.top
            if not mitigated:
                retained.append(fvg)
        active_fvgs[:] = retained

    def _maybe_create_asm_setup(
        self,
        parameters: dict[str, Any],
        bars: list[Bar],
        atr_value: float,
        active_fvgs: list[FairValueGap],
        latest_high: Pivot | None,
        latest_low: Pivot | None,
        index: int,
        context_bias: dict[str, Any] | None = None,
    ) -> AsmSetup | None:
        bar = bars[index]
        allow_long = bool(parameters.get("allow_long", True))
        allow_short = bool(parameters.get("allow_short", True))
        if allow_long and latest_high and latest_low and latest_low.index < index and bar.close > latest_high.price:
            return self._build_asm_setup(
                parameters=parameters,
                bars=bars,
                atr_value=atr_value,
                active_fvgs=active_fvgs,
                direction=1,
                index=index,
                origin=latest_low,
                broken=latest_high,
                context_bias=context_bias,
            )
        if allow_short and latest_high and latest_low and latest_high.index < index and bar.close < latest_low.price:
            return self._build_asm_setup(
                parameters=parameters,
                bars=bars,
                atr_value=atr_value,
                active_fvgs=active_fvgs,
                direction=-1,
                index=index,
                origin=latest_high,
                broken=latest_low,
                context_bias=context_bias,
            )
        return None

    def _build_asm_setup(
        self,
        parameters: dict[str, Any],
        bars: list[Bar],
        atr_value: float,
        active_fvgs: list[FairValueGap],
        direction: int,
        index: int,
        origin: Pivot,
        broken: Pivot,
        context_bias: dict[str, Any] | None = None,
    ) -> AsmSetup | None:
        bar = bars[index]
        fib_entry = float(parameters.get("fib_entry_retracement", 0.67))
        stop_retrace = float(parameters.get("fib_stop_retracement", 1.0))
        target_retrace = float(parameters.get("fib_target_retracement", 0.0))
        buffer = float(parameters.get("stop_buffer_atr_mult", 0.0)) * atr_value
        if direction == 1:
            extreme_price = max(bar.high, broken.price)
            origin_price = origin.price
            range_size = extreme_price - origin_price
            displacement = bar.close - broken.price
            entry_price = extreme_price - (range_size * fib_entry)
            stop_price = extreme_price - (range_size * stop_retrace) - buffer
            target_price = extreme_price - (range_size * target_retrace)
            midpoint = origin_price + (range_size * float(parameters.get("premium_discount_midpoint", 0.5)))
            discount_premium_passed = (not parameters.get("require_discount_for_longs", True)) or entry_price <= midpoint
        else:
            extreme_price = min(bar.low, broken.price)
            origin_price = origin.price
            range_size = origin_price - extreme_price
            displacement = broken.price - bar.close
            entry_price = extreme_price + (range_size * fib_entry)
            stop_price = extreme_price + (range_size * stop_retrace) + buffer
            target_price = extreme_price + (range_size * target_retrace)
            midpoint = extreme_price + (range_size * float(parameters.get("premium_discount_midpoint", 0.5)))
            discount_premium_passed = (not parameters.get("require_premium_for_shorts", True)) or entry_price >= midpoint
        if range_size <= 0:
            return None
        range_atr = range_size / atr_value if atr_value else 0.0
        if range_atr < float(parameters.get("range_min_atr", 1.0)):
            return None
        if range_atr > float(parameters.get("range_max_atr", 12.0)):
            return None
        if displacement < float(parameters.get("min_displacement_atr", 0.8)) * atr_value:
            return None
        fvg = self._select_asm_fvg(parameters, active_fvgs, direction, entry_price, atr_value, index)
        return AsmSetup(
            direction=direction,
            created_index=index,
            setup_type="BOS",
            origin_index=origin.index,
            origin_price=origin_price,
            extreme_index=index,
            extreme_price=extreme_price,
            range_size=range_size,
            range_atr_multiple=round(range_atr, 6),
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            discount_premium_passed=discount_premium_passed,
            fvg=fvg,
            context_bias=context_bias.get("bias") if context_bias else None,
            context_bias_event=context_bias.get("event") if context_bias else None,
            context_bias_index=context_bias.get("bar_index") if context_bias else None,
            context_bias_ts=context_bias.get("bar_ts") if context_bias else None,
            context_bias_age=context_bias.get("age") if context_bias else None,
        )

    @staticmethod
    def _select_asm_fvg(
        parameters: dict[str, Any],
        active_fvgs: list[FairValueGap],
        direction: int,
        entry_price: float,
        atr_value: float,
        index: int,
    ) -> FairValueGap | None:
        tolerance = float(parameters.get("fvg_overlap_tolerance_atr", 0.1)) * atr_value
        candidates = [
            fvg
            for fvg in active_fvgs
            if fvg.direction == direction and fvg.bottom - tolerance <= entry_price <= fvg.top + tolerance
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: index - item.created_index)

    @staticmethod
    def _update_asm_setup_sweep(parameters: dict[str, Any], bars: list[Bar], setup: AsmSetup, index: int) -> None:
        if setup.sweep_index is not None or index <= setup.created_index:
            return
        lookback = int(parameters.get("sweep_lookback_bars", 20))
        start = max(0, index - lookback)
        if start >= index:
            return
        prior = bars[start:index]
        bar = bars[index]
        close_back_inside = bool(parameters.get("sweep_close_back_inside", True))
        if setup.direction == 1:
            prior_low = min(item.low for item in prior)
            if bar.low < prior_low and (not close_back_inside or bar.close > prior_low):
                setup.sweep_index = index
                setup.sweep_price = bar.low
        else:
            prior_high = max(item.high for item in prior)
            if bar.high > prior_high and (not close_back_inside or bar.close < prior_high):
                setup.sweep_index = index
                setup.sweep_price = bar.high

    @staticmethod
    def _update_asm_setup_retracement(bars: list[Bar], setup: AsmSetup, index: int) -> None:
        if setup.retracement_index is not None or index <= setup.created_index:
            return
        if bars[index].low <= setup.entry_price <= bars[index].high:
            setup.retracement_index = index

    @staticmethod
    def _asm_internal_confirmation(
        parameters: dict[str, Any],
        bars: list[Bar],
        setup: AsmSetup,
        latest_internal_high: Pivot | None,
        latest_internal_low: Pivot | None,
        index: int,
    ) -> str | None:
        if not BacktestEngine._asm_internal_required(parameters):
            return "not_required"
        if setup.retracement_index is None or setup.sweep_index is None:
            return None
        if index <= setup.retracement_index or index <= setup.sweep_index:
            return None
        event_mode = parameters.get("internal_confirmation_event", "bos_or_choch")
        bar = bars[index]
        if setup.direction == 1:
            if latest_internal_high is None:
                return None
            if latest_internal_high.index <= max(setup.retracement_index, setup.sweep_index):
                return None
            if bar.close > latest_internal_high.price and event_mode in {"bos_or_choch", "bos_only"}:
                return "bullish_bos"
            if bar.close > latest_internal_high.price and event_mode == "choch_only":
                return "bullish_choch"
        else:
            if latest_internal_low is None:
                return None
            if latest_internal_low.index <= max(setup.retracement_index, setup.sweep_index):
                return None
            if bar.close < latest_internal_low.price and event_mode in {"bos_or_choch", "bos_only"}:
                return "bearish_bos"
            if bar.close < latest_internal_low.price and event_mode == "choch_only":
                return "bearish_choch"
        return None

    def _asm_setup_block_reason(
        self,
        parameters: dict[str, Any],
        bars: list[Bar],
        setup: AsmSetup,
        active_fvgs: list[FairValueGap],
        index: int,
    ) -> str | None:
        if parameters.get("time_risk_filter_enabled", False):
            blocked_weekdays = {int(item) for item in parameters.get("time_risk_block_weekdays", [])}
            blocked_hours = {int(item) for item in parameters.get("time_risk_block_utc_hours", [])}
            if bars[index].ts.weekday() in blocked_weekdays or bars[index].ts.hour in blocked_hours:
                return "blocked_time_risk"
        if not setup.discount_premium_passed:
            return "blocked_not_discount_or_premium"
        if parameters.get("context_bias_required", False):
            if setup.context_bias is None:
                return "blocked_no_context_bias"
            expected_bias = "bullish" if setup.direction == 1 else "bearish"
            max_age = int(parameters.get("context_bias_max_age_bars", 96))
            if setup.context_bias_index is None or setup.context_bias_age is None or setup.context_bias_age > max_age:
                return "blocked_no_context_bias"
            if parameters.get("context_bias_must_align_with_external_bias", True) and setup.context_bias != expected_bias:
                return "blocked_context_bias_mismatch"
        if parameters.get("fvg_overlap_required", True):
            atr_value = max(setup.range_size / max(setup.range_atr_multiple, 0.000001), 0.000001)
            setup.fvg = setup.fvg or self._select_asm_fvg(parameters, active_fvgs, setup.direction, setup.entry_price, atr_value, index)
            if setup.fvg is None:
                return "blocked_no_fvg"
        if setup.retracement_index is None:
            return "blocked_not_discount_or_premium"
        if parameters.get("liquidity_sweep_required", True):
            if setup.sweep_index is None:
                return "blocked_no_sweep"
            if index - setup.sweep_index > int(parameters.get("sweep_window_bars", 48)):
                return "blocked_no_sweep"
        if self._asm_internal_required(parameters):
            if setup.internal_confirmation_index is None:
                return "blocked_no_internal_confirmation"
            max_age = int(parameters.get("internal_confirmation_max_age_bars", 24))
            if index - setup.internal_confirmation_index > max_age:
                return "blocked_no_internal_confirmation"
            if parameters.get("internal_must_align_with_external_bias", True):
                expected_prefix = "bullish" if setup.direction == 1 else "bearish"
                if not str(setup.internal_confirmation_type).startswith(expected_prefix):
                    return "blocked_internal_against_external_bias"
        return None

    @staticmethod
    def _asm_entry_touched(bar: Bar, entry_price: float) -> bool:
        return bar.low <= entry_price <= bar.high

    @staticmethod
    def _asm_entry_ready(parameters: dict[str, Any], setup: AsmSetup) -> bool:
        sweep_ready = setup.sweep_index is not None or not parameters.get("liquidity_sweep_required", True)
        internal_ready = setup.internal_confirmation_index is not None or not BacktestEngine._asm_internal_required(parameters)
        return setup.retracement_index is not None and sweep_ready and internal_ready

    @staticmethod
    def _asm_internal_required(parameters: dict[str, Any]) -> bool:
        return bool(parameters.get("internal_confirmation_required", False)) or parameters.get("structure_stream") == "external_and_internal_intraday"

    def _asm_exit_position(
        self,
        position: Position,
        bar: Bar,
        index: int,
        slippage: float,
        commission_pct: float,
        equity: float,
        diagnostics: dict[str, int],
        allow_same_bar: bool,
    ) -> tuple[dict[str, Any], str] | None:
        target = float(position.entry_features.get("target_price", position.entry_price))
        stop_hit = False
        target_hit = False
        if position.direction == 1:
            stop_hit = bar.low <= position.stop_price
            target_hit = bar.high >= target
            stop_price = max(position.stop_price - slippage, 0.0)
            target_price = max(target - slippage, 0.0)
        else:
            stop_hit = bar.high >= position.stop_price
            target_hit = bar.low <= target
            stop_price = position.stop_price + slippage
            target_price = target + slippage
        if index == position.entry_index and not allow_same_bar:
            return None
        if stop_hit and target_hit:
            if position.entry_features.get("same_bar_exit_policy", "stop_first") == "target_first":
                trade = self._close_trade(position, bar, index, target_price, "target", commission_pct, equity)
                return trade, "target_exits"
            diagnostics["same_bar_stop_first_exits"] += 1
            trade = self._close_trade(position, bar, index, stop_price, "stop", commission_pct, equity)
            return trade, "stop_exits"
        if stop_hit:
            trade = self._close_trade(position, bar, index, stop_price, "stop", commission_pct, equity)
            return trade, "stop_exits"
        if target_hit:
            trade = self._close_trade(position, bar, index, target_price, "target", commission_pct, equity)
            return trade, "target_exits"
        time_stop_enabled = bool(position.entry_features.get("time_stop_enabled", False))
        if time_stop_enabled and index - position.entry_index >= int(position.entry_features.get("time_stop_bars", 0)):
            initial_risk = abs(position.entry_price - position.stop_price)
            mfe_r = position.max_favorable_excursion / initial_risk if initial_risk else 0.0
            if mfe_r < float(position.entry_features.get("time_stop_min_mfe_r", 0.0)):
                exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                trade = self._close_trade(position, bar, index, exit_price, "time_stop", commission_pct, equity)
                return trade, "time_stop_exits"
        return None

    @staticmethod
    def _asm_entry_features(parameters: dict[str, Any], setup: AsmSetup, bar: Bar, index: int) -> dict[str, Any]:
        fvg = setup.fvg
        return {
            "side": "long" if setup.direction == 1 else "short",
            "direction": "long" if setup.direction == 1 else "short",
            "setup_type": setup.setup_type,
            "external_setup_type": setup.setup_type,
            "weekday": bar.ts.weekday(),
            "utc_hour": bar.ts.hour,
            "month": bar.ts.month,
            "fib_entry_retracement": round(abs(setup.extreme_price - setup.entry_price) / setup.range_size, 6)
            if setup.range_size
            else 0.0,
            "swing_origin": round(setup.origin_price, 6),
            "swing_extreme": round(setup.extreme_price, 6),
            "external_range_origin": round(setup.origin_price, 6),
            "external_range_extreme": round(setup.extreme_price, 6),
            "external_range_midpoint": round((setup.origin_price + setup.extreme_price) / 2, 6),
            "external_bias": "bullish" if setup.direction == 1 else "bearish",
            "execution_external_bias": "bullish" if setup.direction == 1 else "bearish",
            "range_size": round(setup.range_size, 6),
            "range_atr_multiple": round(setup.range_atr_multiple, 6),
            "fvg_top": round(fvg.top, 6) if fvg else None,
            "fvg_bottom": round(fvg.bottom, 6) if fvg else None,
            "fvg_age": index - fvg.created_index if fvg else None,
            "fvg_gap_atr_multiple": fvg.gap_atr_multiple if fvg else None,
            "sweep_age": index - setup.sweep_index if setup.sweep_index is not None else None,
            "sweep_price": round(setup.sweep_price, 6) if setup.sweep_price is not None else None,
            "sweep_passed": setup.sweep_index is not None or not parameters.get("liquidity_sweep_required", True),
            "internal_confirmation_type": setup.internal_confirmation_type,
            "execution_internal_confirmation_type": setup.internal_confirmation_type,
            "internal_confirmation_bar_index": setup.internal_confirmation_index,
            "internal_confirmation_age_bars": index - setup.internal_confirmation_index
            if setup.internal_confirmation_index is not None
            else None,
            "internal_pivot_period": int(parameters.get("internal_pivot_period", 2)),
            "external_pivot_period": int(parameters.get("external_pivot_period", 4)),
            "active_timeframe_profile": parameters.get("active_timeframe_profile"),
            "execution_timeframe": parameters.get("execution_timeframe"),
            "context_timeframe": parameters.get("context_timeframe"),
            "higher_context_timeframe": parameters.get("higher_context_timeframe"),
            "context_bias": setup.context_bias,
            "context_bias_event": setup.context_bias_event,
            "context_bias_age_bars": setup.context_bias_age,
            "context_bias_bar_time": setup.context_bias_ts.isoformat() if setup.context_bias_ts else None,
            "fib_entry_retracement_resolved": round(abs(setup.extreme_price - setup.entry_price) / setup.range_size, 6)
            if setup.range_size
            else 0.0,
            "profile_override_applied": bool(parameters.get("use_timeframe_profile_overrides", False)),
            "entry_r": 0.0,
            "discount_premium_passed": setup.discount_premium_passed,
            "discount_or_premium_passed": setup.discount_premium_passed,
            "fvg_overlap_passed": fvg is not None or not parameters.get("fvg_overlap_required", True),
            "entry_price": round(setup.entry_price, 6),
            "stop_price": round(setup.stop_price, 6),
            "target_price": round(setup.target_price, 6),
            "same_bar_exit_policy": parameters.get("same_bar_exit_policy", "stop_first"),
            "time_stop_enabled": bool(parameters.get("time_stop_enabled", False)),
            "time_stop_bars": int(parameters.get("time_stop_bars", 0)),
            "time_stop_min_mfe_r": float(parameters.get("time_stop_min_mfe_r", 0.0)),
        }

    def _run_quant_smc_strategy(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters = spec["parameters"]
        if len(bars) < 100:
            raise HTTPException(status_code=400, detail="Quant SMC engine requires at least 100 bars.")
        execution_model = str(parameters.get("execution_model", "mt5_bar_proxy"))
        if execution_model not in {"research_same_close", "mt5_bar_proxy"}:
            raise HTTPException(status_code=400, detail="execution_model must be `research_same_close` or `mt5_bar_proxy`.")

        atr_len = int(parameters.get("atr_len", 14))
        atr_values = atr(bars, atr_len)
        volumes = [bar.volume for bar in bars]
        vol_avg = sma(volumes, int(parameters.get("volume_sma_len", 20)))
        context_bars = (
            self._resample_bars(
                bars,
                str(parameters.get("execution_timeframe", bars[0].timeframe)),
                str(parameters.get("context_timeframe", bars[0].timeframe)),
            )
            if parameters.get("resample_context_from_execution_bars", False)
            else []
        )
        context_bias_by_index = self._context_bias_series(parameters, bars, context_bars)
        equity = float(parameters.get("initial_capital", 100_000.0))
        initial_capital = equity
        tick_size = float(parameters.get("tick_size", 0.01))
        slippage = int(parameters.get("slippage_ticks", 0)) * tick_size
        commission_pct = float(parameters.get("commission_pct", 0.0)) / 100
        mt5_bar_proxy = execution_model == "mt5_bar_proxy"
        warmup = max(atr_len, int(parameters.get("fixed_pivot_window", 25)) * 2 + 2, int(parameters.get("minor_pivot_window", 4)) * 2 + 2, 50)

        major_pivots: list[Pivot] = []
        minor_pivots: list[Pivot] = []
        bull_fvgs: list[QuantSmcZone] = []
        bear_fvgs: list[QuantSmcZone] = []
        bull_obs: list[QuantSmcZone] = []
        bear_obs: list[QuantSmcZone] = []
        major_state = 0
        minor_state = 0
        anchor_index = 0
        avwap_num = 0.0
        avwap_den = 0.0
        rc_high = bars[0].high
        rc_high_index = 0
        rc_low = bars[0].low
        rc_low_index = 0
        last_confirmed_direction = 0
        pending_high: Pivot | None = None
        pending_low: Pivot | None = None
        pending_minor_high: Pivot | None = None
        pending_minor_low: Pivot | None = None
        last_bull_sweep = -10_000
        last_bear_sweep = -10_000
        latest_bull_sweep_index: int | None = None
        latest_bear_sweep_index: int | None = None
        active_setup: dict[str, Any] | None = None
        pending_setup: dict[str, Any] | None = None
        position: Position | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        diagnostics = {
            "bars": len(bars),
            "major_pivots": 0,
            "minor_pivots": 0,
            "bull_major_breaks": 0,
            "bear_major_breaks": 0,
            "bull_minor_breaks": 0,
            "bear_minor_breaks": 0,
            "mss_breaks": 0,
            "choch_breaks": 0,
            "bos_breaks": 0,
            "bull_fvgs": 0,
            "bear_fvgs": 0,
            "bull_sweeps": 0,
            "bear_sweeps": 0,
            "bull_obs": 0,
            "bear_obs": 0,
            "blocked_no_sweep": 0,
            "blocked_no_fvg_overlap": 0,
            "blocked_pd_zone": 0,
            "blocked_low_score": 0,
            "context_bars_built": len(context_bars),
            "context_bias_bullish_events": 0,
            "context_bias_bearish_events": 0,
            "blocked_no_context_bias": 0,
            "blocked_context_bias_mismatch": 0,
            "blocked_no_internal_confirmation": 0,
            "entries_after_internal_confirmation": 0,
            "signals_long": 0,
            "signals_short": 0,
            "entries": 0,
            "pending_entry_orders": 0,
            "pending_order_fills": 0,
            "pending_orders_expired": 0,
            "target_exits": 0,
            "stop_exits": 0,
            "time_exits": 0,
            "same_bar_stop_first_exits": 0,
            "execution_model": execution_model,
        }

        def append_equity_point(current_bar: Bar) -> None:
            mtm = mark_to_market_equity(equity, position, current_bar.close, commission_pct)
            equity_curve.append({"ts": current_bar.ts.isoformat(), "equity": round(mtm, 2), "mark_to_market_equity": round(mtm, 2), "realized_equity": round(equity, 2)})

        def add_fvg(index: int, current_atr: float) -> None:
            if not parameters.get("show_fvg", True) or index < 2:
                return
            older = bars[index - 2]
            middle = bars[index - 1]
            current = bars[index]
            min_gap = current_atr * float(parameters.get("fvg_min_atr", 0.20))
            if current.low > older.high and middle.close > older.high and current.low - older.high >= min_gap:
                bull_fvgs.append(QuantSmcZone(1, index, current.low, older.high, 0.0, "fvg"))
                diagnostics["bull_fvgs"] += 1
            if current.high < older.low and middle.close < older.low and older.low - current.high >= min_gap:
                bear_fvgs.append(QuantSmcZone(-1, index, older.low, current.high, 0.0, "fvg"))
                diagnostics["bear_fvgs"] += 1
            max_fvgs = int(parameters.get("fvg_max", 30))
            del bull_fvgs[:-max_fvgs]
            del bear_fvgs[:-max_fvgs]

        def mitigate_zones(zones: list[QuantSmcZone], index: int) -> None:
            bar = bars[index]
            retained: list[QuantSmcZone] = []
            for zone in zones:
                if zone.direction == 1:
                    mitigated = bar.low < zone.bottom
                else:
                    mitigated = bar.high > zone.top
                if not mitigated:
                    retained.append(zone)
            zones[:] = retained

        def fvg_overlap(direction: int, top: float, bottom: float) -> bool:
            zones = bull_fvgs if direction == 1 else bear_fvgs
            return any(zone.top >= bottom and zone.bottom <= top for zone in zones)

        def fvg_entry_overlap(direction: int, entry_price: float, current_atr: float) -> bool:
            tolerance = float(parameters.get("fvg_overlap_tolerance_atr", 0.1)) * current_atr
            zones = bull_fvgs if direction == 1 else bear_fvgs
            return any(zone.bottom - tolerance <= entry_price <= zone.top + tolerance for zone in zones)

        def compute_ob_score(top: float, bottom: float, direction: int, index: int, current_atr: float) -> float:
            size_score = min(((top - bottom) / max(current_atr, 0.000001)) / 2.0, 1.0) * 30.0
            disp_body = abs(bars[index].close - bars[index].open)
            disp_score = min(disp_body / max(current_atr * 1.5, 0.000001), 1.0) * 30.0
            volume_score = 20.0 if vol_avg[index] is not None and bars[index].volume > float(vol_avg[index]) else 10.0
            confluence_score = 20.0 if fvg_overlap(direction, top, bottom) else 0.0
            return size_score + disp_score + volume_score + confluence_score

        def find_origin(direction: int, index: int, current_atr: float) -> QuantSmcZone | None:
            selected: QuantSmcZone | None = None
            for offset in range(1, min(int(parameters.get("ob_scan_bars", 30)), index) + 1):
                source = bars[index - offset]
                rng = source.high - source.low
                body = abs(source.close - source.open)
                body_ratio = body / rng if rng > 0 else 0.0
                vol_ok = True
                if parameters.get("ob_volume_required", True) and vol_avg[index - offset] is not None:
                    vol_ok = source.volume >= float(vol_avg[index - offset]) * float(parameters.get("ob_volume_mult", 1.25))
                not_volatile = rng < current_atr * float(parameters.get("ob_max_range_atr", 2.5))
                quality_ok = body_ratio >= float(parameters.get("ob_min_body_ratio", 0.25))
                opposite = source.close < source.open if direction == 1 else source.close > source.open
                if not (opposite and not_volatile and vol_ok and quality_ok):
                    continue
                score = compute_ob_score(source.high, source.low, direction, index, current_atr)
                candidate = QuantSmcZone(direction, index, source.high, source.low, score, "order_block")
                if selected is None:
                    selected = candidate
                elif direction == 1 and candidate.bottom < selected.bottom:
                    selected = candidate
                elif direction == -1 and candidate.top > selected.top:
                    selected = candidate
            return selected

        def premium_discount_pass(
            direction: int,
            index: int,
            entry_price: float,
            range_origin: float | None = None,
            range_extreme: float | None = None,
        ) -> bool:
            if not parameters.get("require_pd_zone", True):
                return True
            pd_method = str(parameters.get("pd_method", "avwap"))
            if pd_method == "external_range_midpoint" and range_origin is not None and range_extreme is not None:
                equilibrium = (range_origin + range_extreme) / 2
            else:
                lookback = max(1, min(index - anchor_index, int(parameters.get("pd_lookback_cap", 500))))
                window = bars[index - lookback + 1 : index + 1]
                hh = max(item.high for item in window)
                ll = min(item.low for item in window)
                equilibrium = avwap_num / avwap_den if pd_method == "avwap" and avwap_den > 0 else (hh + ll) / 2
            return entry_price <= equilibrium if direction == 1 else entry_price >= equilibrium

        def latest_sweep_ok(direction: int, index: int) -> bool:
            if not parameters.get("require_sweep", True):
                return True
            sweep_index = latest_bull_sweep_index if direction == 1 else latest_bear_sweep_index
            return sweep_index is not None and 0 <= index - sweep_index <= int(parameters.get("sweep_max_age_bars", 48))

        def latest_major_pivot(kind: str, before_index: int) -> Pivot | None:
            return next((pivot for pivot in reversed(major_pivots) if pivot.kind == kind and pivot.index < before_index), None)

        def build_setup(direction: int, index: int, kind: str, current_atr: float) -> dict[str, Any] | None:
            zone = find_origin(direction, index, current_atr)
            if zone is None:
                return None
            if zone.score < float(parameters.get("min_ob_score", 0)):
                diagnostics["blocked_low_score"] += 1
                return None
            entry_source = str(parameters.get("entry_price_source", "ob_midpoint"))
            if entry_source != "asm_external_fib" and parameters.get("require_fvg_overlap", True) and not fvg_overlap(direction, zone.top, zone.bottom):
                diagnostics["blocked_no_fvg_overlap"] += 1
                return None
            origin_pivot: Pivot | None = None
            broken_pivot: Pivot | None = None
            range_origin: float | None = None
            range_extreme: float | None = None
            if entry_source == "asm_external_fib":
                fib = float(parameters.get("fib_entry_retracement", 0.67))
                if direction == 1:
                    broken_pivot = pending_high
                    origin_pivot = latest_major_pivot("low", index)
                    if origin_pivot is None or broken_pivot is None:
                        return None
                    range_origin = origin_pivot.price
                    range_extreme = max(bar.high, broken_pivot.price)
                    range_size = range_extreme - range_origin
                    if range_size <= 0:
                        return None
                    entry = range_extreme - (range_size * fib)
                else:
                    broken_pivot = pending_low
                    origin_pivot = latest_major_pivot("high", index)
                    if origin_pivot is None or broken_pivot is None:
                        return None
                    range_origin = origin_pivot.price
                    range_extreme = min(bar.low, broken_pivot.price)
                    range_size = range_origin - range_extreme
                    if range_size <= 0:
                        return None
                    entry = range_extreme + (range_size * fib)
            elif entry_source == "ob_near_edge":
                entry = zone.top if direction == 1 else zone.bottom
            else:
                entry = (zone.top + zone.bottom) / 2
            if entry_source == "asm_external_fib" and parameters.get("require_fvg_overlap", True) and not fvg_entry_overlap(direction, entry, current_atr):
                diagnostics["blocked_no_fvg_overlap"] += 1
                return None
            if not premium_discount_pass(direction, index, entry, range_origin, range_extreme):
                diagnostics["blocked_pd_zone"] += 1
                return None
            timing_mode = str(parameters.get("entry_timing_mode", "source_confluence"))
            if timing_mode == "source_confluence" and not latest_sweep_ok(direction, index):
                diagnostics["blocked_no_sweep"] += 1
                return None
            buffer = current_atr * float(parameters.get("stop_buffer_atr_mult", 0.1))
            if entry_source == "asm_external_fib" and range_origin is not None:
                stop = range_origin - buffer if direction == 1 else range_origin + buffer
            else:
                stop = zone.bottom - buffer if direction == 1 else zone.top + buffer
            risk = abs(entry - stop)
            if risk <= 0:
                return None
            if parameters.get("target_mode", "fixed_r") == "opposing_external_range" and range_extreme is not None:
                target = range_extreme
            else:
                target = entry + (risk * float(parameters.get("target_rr", 2.0))) if direction == 1 else entry - (risk * float(parameters.get("target_rr", 2.0)))
            context_bias = context_bias_by_index[index] if index < len(context_bias_by_index) else {"bias": None, "event": None, "age": None, "bar_index": None}
            if parameters.get("context_bias_required", False):
                expected_bias = "bullish" if direction == 1 else "bearish"
                if context_bias.get("bias") is None or context_bias.get("age") is None or int(context_bias.get("age") or 0) > int(parameters.get("context_bias_max_age_bars", 96)):
                    diagnostics["blocked_no_context_bias"] += 1
                    return None
                if parameters.get("context_bias_must_align_with_external_bias", True) and context_bias.get("bias") != expected_bias:
                    diagnostics["blocked_context_bias_mismatch"] += 1
                    return None
            return {
                "direction": direction,
                "created_index": index,
                "entry": entry,
                "stop": stop,
                "target": target,
                "zone": zone,
                "kind": kind,
                "origin_price": range_origin,
                "extreme_price": range_extreme,
                "origin_index": origin_pivot.index if origin_pivot else None,
                "extreme_index": index if range_extreme is not None else None,
                "retracement_index": None,
                "sweep_index": None
                if timing_mode == "after_retracement_sweep_internal"
                else latest_bull_sweep_index
                if direction == 1
                else latest_bear_sweep_index,
                "internal_confirmation_index": None,
                "internal_confirmation_type": None,
                "context_bias": context_bias,
            }

        def open_quant_position(setup: dict[str, Any], entry_bar: Bar, entry_index: int) -> Position | None:
            direction = int(setup["direction"])
            fill = float(setup["entry"]) + slippage if direction == 1 else max(float(setup["entry"]) - slippage, 0.0)
            quantity = self._position_quantity(parameters, equity, fill, float(setup["stop"]))
            if quantity <= 0:
                return None
            zone = setup["zone"]
            features = {
                "side": "long" if direction == 1 else "short",
                "direction": "long" if direction == 1 else "short",
                "setup_type": setup["kind"],
                "source_baseline": "quantitative_smc_framework",
                "ob_top": round(zone.top, 6),
                "ob_bottom": round(zone.bottom, 6),
                "ob_score": round(zone.score, 4),
                "entry_price": round(fill, 6),
                "stop_price": round(float(setup["stop"]), 6),
                "target_price": round(float(setup["target"]), 6),
                "target_rr": float(parameters.get("target_rr", 2.0)),
                "entry_price_source": parameters.get("entry_price_source", "ob_midpoint"),
                "target_mode": parameters.get("target_mode", "fixed_r"),
                "fib_entry_retracement": float(parameters.get("fib_entry_retracement", 0.0)),
                "external_range_origin": round(float(setup["origin_price"]), 6) if setup.get("origin_price") is not None else None,
                "external_range_extreme": round(float(setup["extreme_price"]), 6) if setup.get("extreme_price") is not None else None,
                "context_bias": setup.get("context_bias", {}).get("bias") if isinstance(setup.get("context_bias"), dict) else None,
                "context_bias_event": setup.get("context_bias", {}).get("event") if isinstance(setup.get("context_bias"), dict) else None,
                "context_bias_age_bars": setup.get("context_bias", {}).get("age") if isinstance(setup.get("context_bias"), dict) else None,
                "internal_confirmation_type": setup.get("internal_confirmation_type"),
                "internal_confirmation_bar_index": setup.get("internal_confirmation_index"),
                "weekday": entry_bar.ts.weekday(),
                "utc_hour": entry_bar.ts.hour,
                "month": entry_bar.ts.month,
                "execution_model": execution_model,
                "signal_ts": bars[int(setup["created_index"])].ts.isoformat(),
                "fill_ts": entry_bar.ts.isoformat(),
            }
            return self._open_position(direction, entry_index, entry_bar, fill, float(setup["stop"]), quantity, commission_pct, equity, features)

        def exit_position(index: int, bar: Bar) -> tuple[dict[str, Any], str] | None:
            if position is None:
                return None
            target = float(position.entry_features["target_price"])
            if position.direction == 1:
                stop_hit = bar.low <= position.stop_price
                target_hit = bar.high >= target
                stop_price = max(position.stop_price - slippage, 0.0)
                target_price = max(target - slippage, 0.0)
            else:
                stop_hit = bar.high >= position.stop_price
                target_hit = bar.low <= target
                stop_price = position.stop_price + slippage
                target_price = target + slippage
            if stop_hit and target_hit:
                diagnostics["same_bar_stop_first_exits"] += 1
                return self._close_trade(position, bar, index, stop_price, "stop", commission_pct, equity), "stop_exits"
            if stop_hit:
                return self._close_trade(position, bar, index, stop_price, "stop", commission_pct, equity), "stop_exits"
            if target_hit:
                return self._close_trade(position, bar, index, target_price, "target", commission_pct, equity), "target_exits"
            return None

        for index, bar in enumerate(bars):
            current_atr = atr_values[index]
            if current_atr is None:
                append_equity_point(bar)
                continue
            avwap_num += ((bar.high + bar.low + bar.close) / 3.0) * (bar.volume or 1.0)
            avwap_den += bar.volume or 1.0
            add_fvg(index, float(current_atr))
            mitigate_zones(bull_fvgs, index)
            mitigate_zones(bear_fvgs, index)
            mitigate_zones(bull_obs, index)
            mitigate_zones(bear_obs, index)

            new_major: Pivot | None = None
            if parameters.get("pivot_engine", "adaptive") == "adaptive":
                threshold = float(current_atr) * float(parameters.get("adaptive_atr_mult", 1.8))
                if bar.high >= rc_high:
                    rc_high, rc_high_index = bar.high, index
                if bar.low <= rc_low:
                    rc_low, rc_low_index = bar.low, index
                if last_confirmed_direction != 1 and (rc_high - bar.low) >= threshold:
                    new_major = Pivot(rc_high_index, rc_high, "high")
                    last_confirmed_direction = 1
                    rc_low, rc_low_index = bar.low, index
                elif last_confirmed_direction != -1 and (bar.high - rc_low) >= threshold:
                    new_major = Pivot(rc_low_index, rc_low, "low")
                    last_confirmed_direction = -1
                    rc_high, rc_high_index = bar.high, index
            else:
                new_major = self._confirmed_pivot(bars, index, int(parameters.get("fixed_pivot_window", 25)))
            if new_major:
                major_pivots.append(new_major)
                del major_pivots[:-40]
                diagnostics["major_pivots"] += 1
                if new_major.kind == "high":
                    pending_high = new_major
                else:
                    pending_low = new_major

            new_minor = self._confirmed_pivot(bars, index, int(parameters.get("minor_pivot_window", 4)))
            if new_minor:
                minor_pivots.append(new_minor)
                del minor_pivots[:-80]
                diagnostics["minor_pivots"] += 1
                if new_minor.kind == "high":
                    pending_minor_high = new_minor
                else:
                    pending_minor_low = new_minor

            bull_sweep = False
            bear_sweep = False
            if parameters.get("show_sweep", True) and minor_pivots:
                recent_high = next((p for p in reversed(minor_pivots[-12:]) if p.kind == "high" and index - p.index > 2), None)
                recent_low = next((p for p in reversed(minor_pivots[-12:]) if p.kind == "low" and index - p.index > 2), None)
                rng = max(bar.high - bar.low, 0.000001)
                top_wick = bar.high - max(bar.open, bar.close)
                bot_wick = min(bar.open, bar.close) - bar.low
                if recent_high and bar.high > recent_high.price and bar.close < recent_high.price and top_wick >= float(current_atr) * float(parameters.get("sweep_wick_atr", 0.8)) and top_wick / rng >= float(parameters.get("sweep_wick_ratio", 0.35)) and index - last_bear_sweep > int(parameters.get("sweep_cooldown_bars", 8)):
                    bear_sweep = True
                    last_bear_sweep = index
                    latest_bear_sweep_index = index
                    diagnostics["bear_sweeps"] += 1
                if recent_low and bar.low < recent_low.price and bar.close > recent_low.price and bot_wick >= float(current_atr) * float(parameters.get("sweep_wick_atr", 0.8)) and bot_wick / rng >= float(parameters.get("sweep_wick_ratio", 0.35)) and index - last_bull_sweep > int(parameters.get("sweep_cooldown_bars", 8)):
                    bull_sweep = True
                    last_bull_sweep = index
                    latest_bull_sweep_index = index
                    diagnostics["bull_sweeps"] += 1

            if not position and pending_setup and mt5_bar_proxy:
                if index - int(pending_setup["created_index"]) > int(parameters.get("max_setup_age_bars", 48)):
                    diagnostics["pending_orders_expired"] += 1
                    pending_setup = None
                elif bar.low <= float(pending_setup["entry"]) <= bar.high:
                    position = open_quant_position(pending_setup, bar, index)
                    if position:
                        diagnostics["entries"] += 1
                        diagnostics["pending_order_fills"] += 1
                        if pending_setup.get("internal_confirmation_index") is not None:
                            diagnostics["entries_after_internal_confirmation"] += 1
                    pending_setup = None

            if position:
                self._update_excursion(position, bar)
                result = exit_position(index, bar)
                if result:
                    trade, reason = result
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics[reason] += 1
                    position = None

            if index < warmup:
                append_equity_point(bar)
                continue

            bull_break = pending_high is not None and bar.close > pending_high.price and bars[index - 1].close <= pending_high.price
            bear_break = pending_low is not None and bar.close < pending_low.price and bars[index - 1].close >= pending_low.price
            bull_minor_break = pending_minor_high is not None and bar.close > pending_minor_high.price and bars[index - 1].close <= pending_minor_high.price
            bear_minor_break = pending_minor_low is not None and bar.close < pending_minor_low.price and bars[index - 1].close >= pending_minor_low.price
            previous_minor_state = minor_state
            if bull_minor_break:
                diagnostics["bull_minor_breaks"] += 1
                minor_state = 1
                pending_minor_high = None
            if bear_minor_break:
                diagnostics["bear_minor_breaks"] += 1
                minor_state = -1
                pending_minor_low = None

            if active_setup:
                if index - int(active_setup["created_index"]) > int(parameters.get("max_setup_age_bars", 48)):
                    diagnostics["pending_orders_expired"] += 1
                    active_setup = None
                else:
                    if active_setup.get("retracement_index") is None and bar.low <= float(active_setup["entry"]) <= bar.high:
                        active_setup["retracement_index"] = index
                    if active_setup.get("sweep_index") is None:
                        if int(active_setup["direction"]) == 1 and bull_sweep:
                            active_setup["sweep_index"] = index
                        elif int(active_setup["direction"]) == -1 and bear_sweep:
                            active_setup["sweep_index"] = index
                    if parameters.get("internal_confirmation_required", False) and active_setup.get("retracement_index") is not None and active_setup.get("sweep_index") is not None:
                        if int(active_setup["direction"]) == 1 and bull_minor_break:
                            active_setup["internal_confirmation_index"] = index
                            active_setup["internal_confirmation_type"] = "bullish_ichoch" if previous_minor_state == -1 else "bullish_ibos"
                        elif int(active_setup["direction"]) == -1 and bear_minor_break:
                            active_setup["internal_confirmation_index"] = index
                            active_setup["internal_confirmation_type"] = "bearish_ichoch" if previous_minor_state == 1 else "bearish_ibos"
                    active_ready = active_setup.get("retracement_index") is not None
                    if parameters.get("require_sweep", True):
                        active_ready = active_ready and active_setup.get("sweep_index") is not None
                    if parameters.get("internal_confirmation_required", False):
                        active_ready = active_ready and active_setup.get("internal_confirmation_index") is not None
                    if active_ready and pending_setup is None and not position:
                        if int(active_setup["direction"]) == 1:
                            diagnostics["signals_long"] += 1
                        else:
                            diagnostics["signals_short"] += 1
                        if mt5_bar_proxy:
                            pending_setup = active_setup
                            diagnostics["pending_entry_orders"] += 1
                        else:
                            position = open_quant_position(active_setup, bar, index)
                            if position:
                                diagnostics["entries"] += 1
                        active_setup = None

            setup: dict[str, Any] | None = None
            if bull_break and parameters.get("allow_long", True):
                diagnostics["bull_major_breaks"] += 1
                shift = major_state == -1
                kind = "BOS"
                if shift:
                    disp_ok = self._quant_smc_displacement_bar(bar, float(current_atr), float(parameters.get("displacement_atr_mult", 1.2)))
                    kind = "MSS" if parameters.get("require_mss_displacement", True) and disp_ok else "CHoCH"
                    anchor_index, avwap_num, avwap_den = index, 0.0, 0.0
                diagnostics["mss_breaks" if kind == "MSS" else "choch_breaks" if kind == "CHoCH" else "bos_breaks"] += 1
                major_state = 1
                setup = build_setup(1, index, kind, float(current_atr))
                if setup:
                    bull_obs.append(setup["zone"])
                    diagnostics["bull_obs"] += 1
                    pending_high = None
            if bear_break and parameters.get("allow_short", True):
                diagnostics["bear_major_breaks"] += 1
                shift = major_state == 1
                kind = "BOS"
                if shift:
                    disp_ok = self._quant_smc_displacement_bar(bar, float(current_atr), float(parameters.get("displacement_atr_mult", 1.2)))
                    kind = "MSS" if parameters.get("require_mss_displacement", True) and disp_ok else "CHoCH"
                    anchor_index, avwap_num, avwap_den = index, 0.0, 0.0
                diagnostics["mss_breaks" if kind == "MSS" else "choch_breaks" if kind == "CHoCH" else "bos_breaks"] += 1
                major_state = -1
                setup = build_setup(-1, index, kind, float(current_atr))
                if setup:
                    bear_obs.append(setup["zone"])
                    diagnostics["bear_obs"] += 1
                    pending_low = None

            if setup and not position and pending_setup is None:
                if parameters.get("entry_timing_mode", "source_confluence") == "after_retracement_sweep_internal":
                    active_setup = setup
                else:
                    if setup["direction"] == 1:
                        diagnostics["signals_long"] += 1
                    else:
                        diagnostics["signals_short"] += 1
                    if mt5_bar_proxy:
                        pending_setup = setup
                        diagnostics["pending_entry_orders"] += 1
                    else:
                        position = open_quant_position(setup, bar, index)
                        if position:
                            diagnostics["entries"] += 1

            append_equity_point(bar)

        if position:
            last_bar = bars[-1]
            exit_price = max(last_bar.close - slippage, 0.0) if position.direction == 1 else last_bar.close + slippage
            trade = self._close_trade(position, last_bar, len(bars) - 1, exit_price, "time_exit", commission_pct, equity)
            trades.append(trade)
            equity += trade["net_pnl"]
            diagnostics["time_exits"] += 1
            if equity_curve:
                equity_curve[-1] = {"ts": last_bar.ts.isoformat(), "equity": round(equity, 2), "mark_to_market_equity": round(equity, 2), "realized_equity": round(equity, 2)}

        buy_hold_start_price = bars[warmup].close if len(bars) > warmup else bars[0].close
        buy_hold_end_price = bars[-1].close
        buy_hold_return_pct = ((buy_hold_end_price - buy_hold_start_price) / buy_hold_start_price) * 100 if buy_hold_start_price else 0.0
        metrics = compute_metrics(
            initial_capital=initial_capital,
            trades=trades,
            equity_curve=equity_curve,
            buy_hold_return=initial_capital * (buy_hold_return_pct / 100),
            buy_hold_return_pct=buy_hold_return_pct,
            buy_hold_start_price=buy_hold_start_price,
            buy_hold_end_price=buy_hold_end_price,
            buy_hold_max_drawdown_pct=buy_hold_drawdown_pct(bars, warmup),
        )
        return {"metrics": metrics, "trades": trades, "equity_curve": equity_curve, "diagnostics": diagnostics, "resolved_parameters": parameters}

    @staticmethod
    def _quant_smc_displacement_bar(bar: Bar, atr_value: float, impulse: float) -> bool:
        body = abs(bar.close - bar.open)
        rng = bar.high - bar.low
        ratio = body / rng if rng > 0 else 0.0
        return ratio >= 0.55 and body >= atr_value * impulse

    def _run_ghl_dc_breakout(self, spec: dict[str, Any], bars: list[Bar]) -> dict[str, Any]:
        parameters = spec["parameters"]
        if not bars:
            raise HTTPException(status_code=400, detail="GHL/DC engine requires bars.")
        execution_model = str(parameters.get("execution_model", "mt5_bar_proxy"))
        if execution_model not in {"next_bar_open", "research_same_close", "mt5_bar_proxy"}:
            raise HTTPException(status_code=400, detail="execution_model must be `next_bar_open`, `research_same_close`, or `mt5_bar_proxy`.")

        highs = [bar.high for bar in bars]
        lows = [bar.low for bar in bars]
        closes = [bar.close for bar in bars]
        gann_high_period = int(parameters.get("gann_high_period", 13))
        gann_low_period = int(parameters.get("gann_low_period", 21))
        donchian_length = int(parameters.get("donchian_length", 55))
        max_breakout_bars = int(parameters.get("max_breakout_bars", 7))
        atr_values = atr(bars, int(parameters.get("atr_len", 14)))
        sma_high = sma(highs, gann_high_period)
        sma_low = sma(lows, gann_low_period)
        dc_upper = rolling_high(highs, donchian_length)
        dc_lower = rolling_low(lows, donchian_length)
        mt5_bar_proxy = execution_model == "mt5_bar_proxy"

        hilo_values: list[float | None] = []
        state_values: list[int] = []
        gann_state = 0
        for index, bar in enumerate(bars):
            if index > 0 and sma_high[index - 1] is not None and bar.close > float(sma_high[index - 1]):
                gann_state = 1
            elif index > 0 and sma_low[index - 1] is not None and bar.close < float(sma_low[index - 1]):
                gann_state = -1
            state_values.append(gann_state)
            hilo_values.append(sma_low[index] if gann_state == 1 else sma_high[index] if gann_state == -1 else None)

        position: Position | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        equity = float(parameters.get("initial_capital", 100_000.0))
        tick_size = float(parameters.get("tick_size", 0.01))
        slippage = int(parameters.get("slippage_ticks", 0)) * tick_size
        configured_spread = int(parameters.get("spread_ticks", 0)) * tick_size
        spread = configured_spread if mt5_bar_proxy else 0.0
        commission_pct = float(parameters.get("commission_pct", 0.0)) / 100
        diagnostics = {
            "bars": len(bars),
            "gann_cross_up": 0,
            "gann_cross_down": 0,
            "signals_long": 0,
            "signals_short": 0,
            "entries": 0,
            "reverse_exits": 0,
            "gann_state_exits": 0,
            "gann_exit_confirmation_candidates": 0,
            "gann_exit_confirmation_suppressed": 0,
            "gann_exit_confirmation_confirmed": 0,
            "gann_exit_confirmation_adverse_escapes": 0,
            "gann_exit_confirmation_recovered": 0,
            "gann_exit_confirmation_suppressed_net_pnl": 0.0,
            "stop_exits": 0,
            "breakeven_stop_moves": 0,
            "breakeven_stop_exits": 0,
            "breakeven_maturity_blocks": 0,
            "failed_entry_triage_exits": 0,
            "failed_entry_triage_candidates": 0,
            "time_risk_filter_blocks": 0,
            "time_risk_filter_long_blocks": 0,
            "time_risk_filter_short_blocks": 0,
            "mt5_invalid_lot_skips": 0,
            "mt5_stop_modify_rejects": 0,
            "pending_entry_orders": 0,
            "pending_order_fills": 0,
            "pending_order_gap_fills": 0,
            "pending_gann_exits": 0,
            "gann_exit_next_open_fills": 0,
            "gap_stop_fills": 0,
            "expired_setups": 0,
            "time_exits": 0,
            "execution_model": execution_model,
            "spread_ticks": int(parameters.get("spread_ticks", 0)),
            "execution_semantics": (
                "closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit"
                if mt5_bar_proxy
                else "research_same_bar"
            ),
        }
        pending_long = False
        pending_short = False
        pending_long_bar = 0
        pending_short_bar = 0
        pending_long_breakout: float | None = None
        pending_short_breakdown: float | None = None
        last_gann_flip_index: int | None = None
        gann_exit_candidate_index: int | None = None
        pending_market_exit_reason: str | None = None
        pending_market_exit_index: int | None = None
        warmup = benchmark_warmup_index(parameters, len(bars))

        def append_equity_point(current_bar: Bar) -> None:
            mtm = mark_to_market_equity(equity, position, current_bar.close, commission_pct)
            equity_curve.append(
                {
                    "ts": current_bar.ts.isoformat(),
                    "equity": round(mtm, 2),
                    "mark_to_market_equity": round(mtm, 2),
                    "realized_equity": round(equity, 2),
                }
            )

        for index, bar in enumerate(bars):
            if index < warmup or hilo_values[index] is None or atr_values[index] is None:
                append_equity_point(bar)
                continue

            # Closed-bar exits become executable market orders at the next bar open.
            # A stop already resting at the broker has priority when the market gaps
            # through it before that market exit can execute.
            if (
                mt5_bar_proxy
                and position
                and pending_market_exit_reason
                and pending_market_exit_index is not None
                and index > pending_market_exit_index
            ):
                stop_gapped = self._ghl_dc_stop_gapped_at_open(position.direction, bar, position.stop_price, spread)
                if stop_gapped:
                    reason = "breakeven_stop" if position.stop_moved_to_breakeven else "stop"
                    exit_price = self._ghl_dc_stop_fill_price(position.direction, bar, position.stop_price, slippage, spread)
                    diagnostics["breakeven_stop_exits" if reason == "breakeven_stop" else "stop_exits"] += 1
                    diagnostics["gap_stop_fills"] += 1
                else:
                    reason = pending_market_exit_reason
                    exit_price = self._ghl_dc_market_open_fill_price(position.direction, bar, slippage, spread)
                    diagnostics["gann_exit_next_open_fills"] += int(reason == "gann_state_exit")
                    diagnostics["gann_state_exits"] += int(reason == "gann_state_exit")
                    diagnostics["reverse_exits"] += int(reason == "reverse")
                    diagnostics["failed_entry_triage_exits"] += int(reason == "failed_entry_triage_exit")
                trade = self._close_trade(position, bar, index, exit_price, reason, commission_pct, equity)
                trades.append(trade)
                equity += trade["net_pnl"]
                position = None
                pending_market_exit_reason = None
                pending_market_exit_index = None
                gann_exit_candidate_index = None

            if position:
                self._update_excursion(position, bar)

            stop_can_trigger = position is not None and index > position.stop_initialized_on_index
            if position and stop_can_trigger:
                if self._ghl_dc_stop_triggered(position.direction, bar, position.stop_price, spread):
                    reason = "breakeven_stop" if position.stop_moved_to_breakeven else "stop"
                    if mt5_bar_proxy:
                        exit_price = self._ghl_dc_stop_fill_price(position.direction, bar, position.stop_price, slippage, spread)
                        diagnostics["gap_stop_fills"] += int(
                            self._ghl_dc_stop_gapped_at_open(position.direction, bar, position.stop_price, spread)
                        )
                    else:
                        exit_price = max(position.stop_price - slippage, 0.0) if position.direction == 1 else position.stop_price + slippage
                    trade = self._close_trade(position, bar, index, exit_price, reason, commission_pct, equity)
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["breakeven_stop_exits" if reason == "breakeven_stop" else "stop_exits"] += 1
                    position = None
                    pending_market_exit_reason = None
                    pending_market_exit_index = None
                    gann_exit_candidate_index = None

            if position and parameters.get("breakeven_stop_enabled", False):
                initial_risk = position.initial_risk_per_unit
                if initial_risk > 0:
                    bars_held = index - position.entry_index
                    min_bars = int(parameters.get("breakeven_min_bars", 0))
                    trigger_r = float(parameters.get("breakeven_trigger_mfe_r", 1.0))
                    lock_r = float(parameters.get("breakeven_lock_r", 0.0))
                    if position.direction == 1 and ((bar.high - position.entry_price) / initial_risk) >= trigger_r:
                        if bars_held < min_bars:
                            diagnostics["breakeven_maturity_blocks"] += 1
                        else:
                            new_stop = position.entry_price + (initial_risk * lock_r)
                            if mt5_bar_proxy and new_stop >= bar.close:
                                diagnostics["mt5_stop_modify_rejects"] += 1
                            elif new_stop > position.stop_price:
                                position.stop_price = new_stop
                                position.stop_moved_to_breakeven = True
                                diagnostics["breakeven_stop_moves"] += 1
                    elif position.direction == -1 and ((position.entry_price - bar.low) / initial_risk) >= trigger_r:
                        if bars_held < min_bars:
                            diagnostics["breakeven_maturity_blocks"] += 1
                        else:
                            new_stop = position.entry_price - (initial_risk * lock_r)
                            if mt5_bar_proxy and new_stop <= bar.close:
                                diagnostics["mt5_stop_modify_rejects"] += 1
                            elif new_stop < position.stop_price:
                                position.stop_price = new_stop
                                position.stop_moved_to_breakeven = True
                                diagnostics["breakeven_stop_moves"] += 1

            if position and parameters.get("failed_entry_triage_enabled", False):
                initial_risk = position.initial_risk_per_unit
                bars_held = index - position.entry_index
                triage_bars = int(parameters.get("failed_entry_triage_bars", 3))
                min_mfe_r = float(parameters.get("failed_entry_triage_min_mfe_r", 0.25))
                max_current_r = float(parameters.get("failed_entry_triage_max_current_r", 0.0))
                if initial_risk > 0 and bars_held >= triage_bars:
                    current_r = ((bar.close - position.entry_price) * position.direction) / initial_risk
                    mfe_r = position.max_favorable_excursion / initial_risk
                    if mfe_r < min_mfe_r and current_r <= max_current_r:
                        diagnostics["failed_entry_triage_candidates"] += 1
                        if mt5_bar_proxy:
                            pending_market_exit_reason = "failed_entry_triage_exit"
                            pending_market_exit_index = index
                        else:
                            exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                            trade = self._close_trade(position, bar, index, exit_price, "failed_entry_triage_exit", commission_pct, equity)
                            trades.append(trade)
                            equity += trade["net_pnl"]
                            diagnostics["failed_entry_triage_exits"] += 1
                            position = None
                            gann_exit_candidate_index = None

            previous_hilo = hilo_values[index - 1]
            current_hilo = hilo_values[index]

            # In MT5 mode, only orders armed by a previous closed bar can fill.
            # Capture and consume those orders before the current close is allowed
            # to arm a replacement setup.
            long_age = index - pending_long_bar if pending_long else 0
            short_age = index - pending_short_bar if pending_short else 0
            causal_long_trigger = bool(
                mt5_bar_proxy
                and pending_long
                and 1 <= long_age <= max_breakout_bars
                and pending_long_breakout is not None
                and (bar.high + spread) >= pending_long_breakout
            )
            causal_short_trigger = bool(
                mt5_bar_proxy
                and pending_short
                and 1 <= short_age <= max_breakout_bars
                and pending_short_breakdown is not None
                and bar.low <= pending_short_breakdown
            )
            signal_long_trigger = pending_long_breakout if causal_long_trigger else None
            signal_short_trigger = pending_short_breakdown if causal_short_trigger else None
            signal_long_age = long_age
            signal_short_age = short_age
            signal_long_setup_index = pending_long_bar if causal_long_trigger else index
            signal_short_setup_index = pending_short_bar if causal_short_trigger else index
            if causal_long_trigger:
                pending_long = False
                pending_long_breakout = None
            if causal_short_trigger:
                pending_short = False
                pending_short_breakdown = None
            if pending_long and long_age > max_breakout_bars:
                pending_long = False
                pending_long_breakout = None
                diagnostics["expired_setups"] += 1
            if pending_short and short_age > max_breakout_bars:
                pending_short = False
                pending_short_breakdown = None
                diagnostics["expired_setups"] += 1

            gann_cross_up = previous_hilo is not None and current_hilo is not None and closes[index - 1] <= float(previous_hilo) and bar.close > float(current_hilo)
            gann_cross_down = previous_hilo is not None and current_hilo is not None and closes[index - 1] >= float(previous_hilo) and bar.close < float(current_hilo)
            if gann_cross_up:
                diagnostics["gann_cross_up"] += 1
                last_gann_flip_index = index
                pending_long = True
                pending_long_bar = index
                pending_long_breakout = dc_upper[index - 1] if index > 0 else None
                diagnostics["pending_entry_orders"] += int(mt5_bar_proxy and pending_long_breakout is not None)
                pending_short = False
                pending_short_breakdown = None
            if gann_cross_down:
                diagnostics["gann_cross_down"] += 1
                last_gann_flip_index = index
                pending_short = True
                pending_short_bar = index
                pending_short_breakdown = dc_lower[index - 1] if index > 0 else None
                diagnostics["pending_entry_orders"] += int(mt5_bar_proxy and pending_short_breakdown is not None)
                pending_long = False
                pending_long_breakout = None

            if mt5_bar_proxy:
                long_signal = causal_long_trigger
                short_signal = causal_short_trigger
                long_trigger_level = signal_long_trigger
                short_trigger_level = signal_short_trigger
                long_signal_age = signal_long_age
                short_signal_age = signal_short_age
            else:
                long_age = index - pending_long_bar if pending_long else 0
                short_age = index - pending_short_bar if pending_short else 0
                long_signal = bool(pending_long and long_age <= max_breakout_bars and pending_long_breakout is not None and bar.high > pending_long_breakout and highs[index - 1] <= pending_long_breakout)
                short_signal = bool(pending_short and short_age <= max_breakout_bars and pending_short_breakdown is not None and bar.low < pending_short_breakdown and lows[index - 1] >= pending_short_breakdown)
                long_trigger_level = pending_long_breakout
                short_trigger_level = pending_short_breakdown
                long_signal_age = long_age
                short_signal_age = short_age
                signal_long_setup_index = pending_long_bar
                signal_short_setup_index = pending_short_bar

            adverse_gann_state = bool(
                position
                and (
                    (position.direction == 1 and bar.close < float(current_hilo) and state_values[index] == -1)
                    or (position.direction == -1 and bar.close > float(current_hilo) and state_values[index] == 1)
                )
            )
            if position and adverse_gann_state:
                exit_allowed = True
                if parameters.get("gann_exit_confirmation_enabled", False):
                    diagnostics["gann_exit_confirmation_candidates"] += 1
                    initial_risk = position.initial_risk_per_unit
                    current_r = ((bar.close - position.entry_price) * position.direction) / initial_risk if initial_risk > 0 else 0.0
                    adverse_escape_r = float(parameters.get("gann_exit_confirm_allow_if_unrealized_r_lte", -0.35))
                    confirm_bars = max(1, int(parameters.get("gann_exit_confirm_bars", 1)))
                    if current_r <= adverse_escape_r:
                        diagnostics["gann_exit_confirmation_adverse_escapes"] += 1
                        gann_exit_candidate_index = None
                    elif gann_exit_candidate_index is None:
                        gann_exit_candidate_index = index
                        diagnostics["gann_exit_confirmation_suppressed"] += 1
                        position.gann_exit_confirmation_suppressed += 1
                        exit_allowed = False
                    elif index - gann_exit_candidate_index < confirm_bars:
                        diagnostics["gann_exit_confirmation_suppressed"] += 1
                        position.gann_exit_confirmation_suppressed += 1
                        exit_allowed = False
                    else:
                        diagnostics["gann_exit_confirmation_confirmed"] += 1
                        gann_exit_candidate_index = None
                if exit_allowed:
                    if mt5_bar_proxy:
                        if pending_market_exit_reason is None:
                            pending_market_exit_reason = "gann_state_exit"
                            pending_market_exit_index = index
                            diagnostics["pending_gann_exits"] += 1
                    else:
                        exit_price = max(bar.close - slippage, 0.0) if position.direction == 1 else bar.close + slippage
                        trade = self._close_trade(position, bar, index, exit_price, "gann_state_exit", commission_pct, equity)
                        trades.append(trade)
                        equity += trade["net_pnl"]
                        diagnostics["gann_state_exits"] += 1
                        position = None
                        gann_exit_candidate_index = None
            elif position and gann_exit_candidate_index is not None:
                diagnostics["gann_exit_confirmation_recovered"] += 1
                gann_exit_candidate_index = None

            if long_signal and parameters.get("allow_long", True):
                diagnostics["signals_long"] += 1
            else:
                long_signal = False
            if short_signal and parameters.get("allow_short", True):
                diagnostics["signals_short"] += 1
            else:
                short_signal = False

            if parameters.get("time_risk_filter_enabled", False):
                blocked_hours = {int(hour) for hour in parameters.get("time_risk_block_utc_hours", [])}
                blocked_weekdays = {int(day) for day in parameters.get("time_risk_block_weekdays", [])}
                if bar.ts.hour in blocked_hours or bar.ts.weekday() in blocked_weekdays:
                    if long_signal:
                        diagnostics["time_risk_filter_blocks"] += 1
                        diagnostics["time_risk_filter_long_blocks"] += 1
                        long_signal = False
                    if short_signal:
                        diagnostics["time_risk_filter_blocks"] += 1
                        diagnostics["time_risk_filter_short_blocks"] += 1
                        short_signal = False

            if position and position.direction == 1 and short_signal:
                if mt5_bar_proxy:
                    if pending_market_exit_reason is None:
                        pending_market_exit_reason = "reverse"
                        pending_market_exit_index = index
                else:
                    trade = self._close_trade(position, bar, index, max(bar.close - slippage, 0.0), "reverse", commission_pct, equity)
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["reverse_exits"] += 1
                    position = None
                    gann_exit_candidate_index = None
            elif position and position.direction == -1 and long_signal:
                if mt5_bar_proxy:
                    if pending_market_exit_reason is None:
                        pending_market_exit_reason = "reverse"
                        pending_market_exit_index = index
                else:
                    trade = self._close_trade(position, bar, index, bar.close + slippage, "reverse", commission_pct, equity)
                    trades.append(trade)
                    equity += trade["net_pnl"]
                    diagnostics["reverse_exits"] += 1
                    position = None
                    gann_exit_candidate_index = None

            if position is None and (long_signal or short_signal):
                direction = 1 if long_signal else -1
                trigger_level = long_trigger_level if direction == 1 else short_trigger_level
                if execution_model == "research_same_close":
                    reference = bar.close
                    fill = reference + slippage if direction == 1 else max(reference - slippage, 0.0)
                elif trigger_level is not None:
                    fill = self._ghl_dc_pending_fill_price(direction, bar, float(trigger_level), slippage, spread)
                else:
                    fill = self._ghl_dc_market_open_fill_price(direction, bar, slippage, spread)
                risk_index = index - 1 if mt5_bar_proxy and index > 0 else index
                channel_opposite = dc_lower[risk_index] if direction == 1 else dc_upper[risk_index]
                stop = self._ghl_dc_initial_stop(
                    parameters,
                    direction,
                    fill,
                    bars[risk_index],
                    float(atr_values[risk_index] or 0.0),
                    channel_opposite,
                )
                quantity = self._position_quantity(parameters, equity, fill, stop)
                if quantity <= 0:
                    diagnostics["mt5_invalid_lot_skips"] += 1
                    append_equity_point(bar)
                    continue
                features = self._ghl_dc_entry_features(
                    bars, risk_index, direction, parameters, atr_values, sma_high, sma_low, hilo_values, state_values, dc_upper, dc_lower,
                    trigger_level,
                    long_signal_age if direction == 1 else short_signal_age,
                    last_gann_flip_index, stop, fill,
                )
                features.update(
                    {
                        "execution_model": execution_model,
                        "execution_ts": bar.ts.isoformat(),
                        "setup_index": signal_long_setup_index if direction == 1 else signal_short_setup_index,
                        "fill_index": index,
                        "stop_active_from_index": index + 1 if mt5_bar_proxy else index,
                        "utc_hour": bar.ts.hour,
                        "weekday": bar.ts.weekday(),
                        "spread_ticks": int(parameters.get("spread_ticks", 0)),
                        "gap_fill": bool(
                            mt5_bar_proxy
                            and trigger_level is not None
                            and self._ghl_dc_pending_order_gapped_at_open(direction, bar, float(trigger_level), spread)
                        ),
                    }
                )
                position = self._open_position(
                    direction,
                    index,
                    bar,
                    fill,
                    stop,
                    quantity,
                    commission_pct,
                    equity,
                    features,
                    account_conversion_mode=str(parameters.get("account_conversion_mode", "identity")),
                    contract_size=float(parameters.get("contract_size", 0.0)),
                    commission_per_lot_side=float(parameters.get("commission_per_lot_side", 0.0)),
                )
                gann_exit_candidate_index = None
                diagnostics["entries"] += 1
                diagnostics["pending_order_fills"] += int(mt5_bar_proxy)
                diagnostics["pending_order_gap_fills"] += int(features["gap_fill"])
                if not mt5_bar_proxy:
                    pending_long = pending_short = False
                    pending_long_breakout = pending_short_breakdown = None

            append_equity_point(bar)

        if position:
            last_bar = bars[-1]
            exit_price = max(last_bar.close - slippage, 0.0) if position.direction == 1 else last_bar.close + slippage
            trade = self._close_trade(position, last_bar, len(bars) - 1, exit_price, "time_exit", commission_pct, equity)
            trades.append(trade)
            equity += trade["net_pnl"]
            diagnostics["time_exits"] += 1
            equity_curve[-1] = {"ts": last_bar.ts.isoformat(), "equity": round(equity, 2), "mark_to_market_equity": round(equity, 2), "realized_equity": round(equity, 2)}

        initial_capital = float(parameters.get("initial_capital", 100_000.0))
        buy_hold_start_price = bars[warmup].close if len(bars) > warmup else bars[0].close
        buy_hold_end_price = bars[-1].close
        buy_hold_return_pct = ((buy_hold_end_price - buy_hold_start_price) / buy_hold_start_price) * 100 if buy_hold_start_price else 0.0
        metrics = compute_metrics(
            initial_capital=initial_capital,
            trades=trades,
            equity_curve=equity_curve,
            buy_hold_return=initial_capital * (buy_hold_return_pct / 100),
            buy_hold_return_pct=buy_hold_return_pct,
            buy_hold_start_price=buy_hold_start_price,
            buy_hold_end_price=buy_hold_end_price,
            buy_hold_max_drawdown_pct=buy_hold_drawdown_pct(bars, warmup),
        )
        diagnostics["gann_exit_confirmation_suppressed_net_pnl"] = round(
            sum(
                trade["net_pnl"]
                for trade in trades
                if int(trade.get("gann_exit_confirmation_suppressed", 0)) > 0
            ),
            2,
        )
        return {"metrics": metrics, "trades": trades, "equity_curve": equity_curve, "diagnostics": diagnostics}

    @staticmethod
    def _ghl_dc_pending_order_gapped_at_open(direction: int, bar: Bar, trigger: float, spread: float) -> bool:
        if direction == 1:
            return (bar.open + spread) >= trigger
        return bar.open <= trigger

    @staticmethod
    def _ghl_dc_pending_fill_price(direction: int, bar: Bar, trigger: float, slippage: float, spread: float) -> float:
        if direction == 1:
            return max(bar.open + spread, trigger) + slippage
        return max(min(bar.open, trigger) - slippage, 0.0)

    @staticmethod
    def _ghl_dc_market_open_fill_price(direction: int, bar: Bar, slippage: float, spread: float) -> float:
        if direction == 1:
            return max(bar.open - slippage, 0.0)
        return bar.open + spread + slippage

    @staticmethod
    def _ghl_dc_stop_triggered(direction: int, bar: Bar, stop: float, spread: float) -> bool:
        if direction == 1:
            return bar.low <= stop
        return (bar.high + spread) >= stop

    @staticmethod
    def _ghl_dc_stop_gapped_at_open(direction: int, bar: Bar, stop: float, spread: float) -> bool:
        if direction == 1:
            return bar.open <= stop
        return (bar.open + spread) >= stop

    @staticmethod
    def _ghl_dc_stop_fill_price(direction: int, bar: Bar, stop: float, slippage: float, spread: float) -> float:
        if direction == 1:
            return max(min(bar.open, stop) - slippage, 0.0)
        return max(bar.open + spread, stop) + slippage

    @staticmethod
    def _ghl_dc_initial_stop(parameters: dict[str, Any], direction: int, fill: float, bar: Bar, atr_value: float, channel_opposite: float | None) -> float:
        stop_mode = parameters.get("stop_mode", "atr")
        stop_mult = float(parameters.get("stop_mult", 2.5))
        atr_stop = fill - (atr_value * stop_mult) if direction == 1 else fill + (atr_value * stop_mult)
        if stop_mode == "donchian_opposite" and channel_opposite is not None:
            return min(float(channel_opposite), atr_stop) if direction == 1 else max(float(channel_opposite), atr_stop)
        if stop_mode == "bar_extreme":
            return min(bar.low, atr_stop) if direction == 1 else max(bar.high, atr_stop)
        return atr_stop

    @staticmethod
    def _ghl_dc_entry_features(
        bars: list[Bar], index: int, direction: int, parameters: dict[str, Any], atr_values: list[float | None],
        sma_high: list[float | None], sma_low: list[float | None], hilo_values: list[float | None], state_values: list[int],
        dc_upper: list[float | None], dc_lower: list[float | None], breakout_level: float | None, signal_age: int,
        last_gann_flip_index: int | None, stop_price: float, entry_price: float,
    ) -> dict[str, Any]:
        bar = bars[index]
        lookback = min(index, 20)
        prior = bars[index - lookback : index + 1]
        prior_close = bars[index - lookback].close if lookback else bar.close
        prior_high = max(item.high for item in prior)
        prior_low = min(item.low for item in prior)
        prior_returns = [(bars[item].close - bars[item - 1].close) / bars[item - 1].close for item in range(max(1, index - lookback + 1), index + 1) if bars[item - 1].close]
        current_atr = float(atr_values[index] or 0.0)
        current_high_sma = float(sma_high[index] or 0.0)
        current_low_sma = float(sma_low[index] or 0.0)
        previous_high_sma = float(sma_high[index - 1] or current_high_sma) if index > 0 else current_high_sma
        previous_low_sma = float(sma_low[index - 1] or current_low_sma) if index > 0 else current_low_sma
        current_hilo = float(hilo_values[index] or 0.0)
        breakout = float(breakout_level or entry_price)
        opposite_channel = float((dc_lower[index] if direction == 1 else dc_upper[index]) or stop_price)
        stop_distance = abs(entry_price - stop_price)
        bars_since_flip = index - last_gann_flip_index if last_gann_flip_index is not None else 0
        normalized_gann_distance = ((bar.close - current_hilo) / bar.close) if bar.close and current_hilo else 0.0
        breakout_distance = (bar.close - breakout) if direction == 1 else (breakout - bar.close)
        channel_width = float(dc_upper[index] or bar.high) - float(dc_lower[index] or bar.low)
        recent_cross_count = 0
        for item in range(max(1, index - lookback + 1), index + 1):
            previous = hilo_values[item - 1]
            current = hilo_values[item]
            if previous is not None and current is not None:
                recent_cross_count += int((bars[item - 1].close <= float(previous) and bars[item].close > float(current)) or (bars[item - 1].close >= float(previous) and bars[item].close < float(current)))
        return {
            "side": "long" if direction == 1 else "short",
            "weekday": bar.ts.weekday(),
            "utc_hour": bar.ts.hour,
            "month": bar.ts.month,
            "gann_state": state_values[index],
            "gann_high_sma": round(current_high_sma, 6),
            "gann_low_sma": round(current_low_sma, 6),
            "gann_high_slope": round(current_high_sma - previous_high_sma, 6),
            "gann_low_slope": round(current_low_sma - previous_low_sma, 6),
            "fast_slope": round(current_high_sma - previous_high_sma, 6),
            "slow_slope": round(current_low_sma - previous_low_sma, 6),
            "hilo_value": round(current_hilo, 6),
            "normalized_ma_distance": round(normalized_gann_distance, 8),
            "bars_since_gann_flip": bars_since_flip,
            "breakout_age_bars": signal_age,
            "donchian_breakout_level": round(breakout, 6),
            "donchian_opposite_level": round(opposite_channel, 6),
            "donchian_channel_width": round(channel_width, 6),
            "donchian_channel_width_pct": round(channel_width / bar.close, 8) if bar.close else 0.0,
            "donchian_breakout_distance": round(breakout_distance, 6),
            "donchian_breakout_distance_atr": round(breakout_distance / current_atr, 6) if current_atr else 0.0,
            "atr": round(current_atr, 6),
            "atr_pct": round(current_atr / bar.close, 8) if bar.close else 0.0,
            "recent_return_20": round((bar.close - prior_close) / prior_close, 8) if prior_close else 0.0,
            "recent_range_20": round((prior_high - prior_low) / bar.close, 8) if bar.close else 0.0,
            "recent_volatility_20": round(math.sqrt(sum(item * item for item in prior_returns) / len(prior_returns)), 8) if prior_returns else 0.0,
            "recent_cross_count": recent_cross_count,
            "stop_distance": round(stop_distance, 6),
            "stop_distance_atr": round(stop_distance / current_atr, 6) if current_atr else 0.0,
            "stop_distance_pct": round(stop_distance / entry_price, 8) if entry_price else 0.0,
            "time_risk_filter_enabled": bool(parameters.get("time_risk_filter_enabled", False)),
            "blocked_utc_hour_count": len(parameters.get("time_risk_block_utc_hours", [])),
        }

    @staticmethod
    def _open_position(
        direction: int,
        index: int,
        bar: Bar,
        fill: float,
        stop: float,
        quantity: float,
        commission_pct: float,
        equity: float,
        features: dict[str, Any],
        account_conversion_mode: str = "identity",
        contract_size: float = 0.0,
        commission_per_lot_side: float = 0.0,
    ) -> Position:
        lots = quantity / contract_size if contract_size > 0 else 0.0
        entry_commission = (
            lots * commission_per_lot_side
            if commission_per_lot_side > 0
            else fill * quantity * commission_pct
        )
        entry_notional = quantity if account_conversion_mode == "quote_divide_price" else fill * quantity
        return Position(
            direction=direction,
            entry_index=index,
            entry_ts=bar.ts,
            entry_price=fill,
            stop_price=stop,
            quantity=quantity,
            entry_commission=entry_commission,
            entry_equity=equity,
            entry_notional=entry_notional,
            initial_risk_per_unit=abs(fill - stop),
            stop_initialized_on_index=index,
            entry_features=features,
            account_conversion_mode=account_conversion_mode,
            contract_size=contract_size,
            commission_per_lot_side=commission_per_lot_side,
        )

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
        if mode == "mt5_fixed_risk_lot":
            risk_per_unit = abs(entry_price - stop_price)
            contract_size = max(0.0, float(parameters.get("contract_size", 100.0)))
            lot_step = max(0.0, float(parameters.get("lot_step", 0.01)))
            min_lot = max(0.0, float(parameters.get("min_lot", 0.01)))
            max_lot = max(0.0, float(parameters.get("max_lot", 100.0)))
            if risk_per_unit <= 0 or contract_size <= 0 or lot_step <= 0 or max_lot <= 0:
                return 0.0
            risk_pct = max(0.0, float(parameters.get("risk_pct", 0.005)))
            quote_divide_price = parameters.get("account_conversion_mode") == "quote_divide_price"
            risk_per_lot = risk_per_unit * contract_size
            if quote_divide_price:
                risk_per_lot /= entry_price
            risk_lots = (equity * risk_pct) / risk_per_lot
            notional_per_lot = contract_size if quote_divide_price else entry_price * contract_size
            leverage_lots = max_notional / notional_per_lot
            raw_lots = min(risk_lots, leverage_lots, max_lot)
            stepped_lots = math.floor(raw_lots / lot_step) * lot_step
            if stepped_lots < min_lot:
                if parameters.get("skip_below_min_lot", True):
                    return 0.0
                stepped_lots = min_lot
            return min(max_lot, round(stepped_lots, 8)) * contract_size
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
        lots = position.quantity / position.contract_size if position.contract_size > 0 else 0.0
        exit_commission = (
            lots * position.commission_per_lot_side
            if position.commission_per_lot_side > 0
            else price * position.quantity * commission_pct
        )
        if position.direction == 1:
            gross_pnl = (price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - price) * position.quantity
        if position.account_conversion_mode == "quote_divide_price" and price > 0:
            gross_pnl /= price
        net_pnl = gross_pnl - position.entry_commission - exit_commission
        initial_risk = position.initial_risk_per_unit
        initial_risk_amount = initial_risk * position.quantity
        mfe_amount = position.max_favorable_excursion * position.quantity
        mae_amount = position.max_adverse_excursion * position.quantity
        if position.account_conversion_mode == "quote_divide_price" and position.entry_price > 0:
            initial_risk_amount /= position.entry_price
            mfe_amount /= position.entry_price
            mae_amount /= position.entry_price
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
            "mfe": round(mfe_amount, 2),
            "mae": round(mae_amount, 2),
            "mfe_r": round(position.max_favorable_excursion / initial_risk, 4) if initial_risk else 0.0,
            "mae_r": round(position.max_adverse_excursion / initial_risk, 4) if initial_risk else 0.0,
            "return_on_equity_pct": round((net_pnl / equity_before) * 100, 4) if equity_before else 0.0,
            "time_decay_confirmation_suppressed": position.time_decay_confirmation_suppressed,
            "reverse_confirmation_suppressed": position.reverse_confirmation_suppressed,
            "gann_exit_confirmation_suppressed": position.gann_exit_confirmation_suppressed,
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
