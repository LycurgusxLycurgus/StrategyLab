from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from app.config import settings
from app.domain import Bar, Candidate, Trade


def classify_session(ts: datetime) -> str:
    local = ts.astimezone(settings.timezone)
    hour = local.hour + (local.minute / 60)
    if 2 <= hour < 5:
        return "london_killzone"
    if 7 <= hour < 10:
        return "ny_killzone"
    if hour >= 18 or hour < 2:
        return "asian_build"
    return "off_session"


def trading_day(ts: datetime) -> date:
    local = ts.astimezone(settings.timezone)
    return local.date() if local.hour < 18 else (local + timedelta(days=1)).date()


def atr_series(bars: list[Bar], period: int = 14) -> list[float]:
    result: list[float] = []
    prev_close = bars[0].close if bars else 0.0
    trs: list[float] = []
    for bar in bars:
        tr = max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close))
        trs.append(tr)
        window = trs[-period:]
        result.append(sum(window) / len(window))
        prev_close = bar.close
    return result


def compute_metrics(trades: list[Trade]) -> dict[str, float]:
    if not trades:
        return {
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "win_rate": 0.0,
            "trades": 0,
            "total_return": 0.0,
            "avg_r": 0.0,
        }
    outcomes = [trade.outcome_r for trade in trades]
    avg = sum(outcomes) / len(outcomes)
    variance = sum((value - avg) ** 2 for value in outcomes) / len(outcomes)
    downside = [value for value in outcomes if value < 0]
    downside_var = sum(value**2 for value in downside) / len(downside) if downside else 0.0
    sharpe = (avg / math.sqrt(variance)) * math.sqrt(len(outcomes)) if variance > 0 else 0.0
    sortino = (avg / math.sqrt(downside_var)) * math.sqrt(len(outcomes)) if downside_var > 0 else 0.0
    gross_wins = sum(value for value in outcomes if value > 0)
    gross_losses = abs(sum(value for value in outcomes if value < 0))
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in outcomes:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown": round(max_drawdown, 4),
        "profit_factor": round(gross_wins / gross_losses, 4) if gross_losses else round(gross_wins, 4),
        "expectancy": round(avg, 4),
        "win_rate": round(sum(1 for value in outcomes if value > 0) / len(outcomes), 4),
        "trades": len(outcomes),
        "total_return": round(sum(outcomes), 4),
        "avg_r": round(avg, 4),
    }


class WhiteBoxEngine:
    def __init__(self, profile: dict[str, float]) -> None:
        self.profile = profile

    def run(self, bars: list[Bar]) -> dict[str, Any]:
        if len(bars) < 80:
            return {
                "candidates": [],
                "trades": [],
                "metrics": compute_metrics([]),
                "diagnostics": {"bars": len(bars), "note": "Dataset too small for strategy logic."},
                "trace": [],
            }

        atrs = atr_series(bars)
        previous_day_levels: dict[date, dict[str, float]] = {}
        asian_levels: dict[date, dict[str, float]] = {}
        day_highs: dict[date, list[float]] = {}
        day_lows: dict[date, list[float]] = {}
        asian_highs: dict[date, list[float]] = {}
        asian_lows: dict[date, list[float]] = {}

        for bar in bars:
            local = bar.ts.astimezone(settings.timezone)
            calendar_day = local.date()
            day_highs.setdefault(calendar_day, []).append(bar.high)
            day_lows.setdefault(calendar_day, []).append(bar.low)
            if classify_session(bar.ts) == "asian_build":
                td = trading_day(bar.ts)
                asian_highs.setdefault(td, []).append(bar.high)
                asian_lows.setdefault(td, []).append(bar.low)

        ordered_days = sorted(day_highs.keys())
        prev: dict[str, float] | None = None
        for day in ordered_days:
            if prev:
                previous_day_levels[day] = prev
            prev = {"high": max(day_highs[day]), "low": min(day_lows[day])}
        for day in asian_highs:
            asian_levels[day] = {"high": max(asian_highs[day]), "low": min(asian_lows[day])}

        diagnostics = {
            "bars": len(bars),
            "killzone_bars": 0,
            "sweeps": 0,
            "confirmed_candidates": 0,
            "orders_filled": 0,
            "setup_expired": 0,
            "pending_expired": 0,
        }
        candidates: list[Candidate] = []
        trades: list[Trade] = []
        trace: list[dict[str, Any]] = []
        active_setup: dict[str, Any] | None = None
        pending_order: dict[str, Any] | None = None
        open_trade: dict[str, Any] | None = None

        for index, bar in enumerate(bars):
            atr = atrs[index]
            session = classify_session(bar.ts)
            local = bar.ts.astimezone(settings.timezone)
            td = trading_day(bar.ts)
            current_levels = self._current_liquidity_levels(td, local.date(), asian_levels, previous_day_levels)
            trace_entry = self._make_trace_entry(
                bar=bar,
                atr=atr,
                session=session,
                levels=current_levels,
                active_setup=active_setup,
                pending_order=pending_order,
                open_trade=open_trade,
            )
            if session in {"london_killzone", "ny_killzone"}:
                diagnostics["killzone_bars"] += 1

            if open_trade:
                self._manage_open_trade(open_trade, bar, trades)
                trace_entry["active_trade"] = {
                    "direction": open_trade["direction"],
                    "entry": round(open_trade["entry"], 4),
                    "stop": round(open_trade["stop"], 4),
                    "target": round(open_trade["target"], 4),
                    "candidate_id": open_trade["candidate"].candidate_id,
                }
                if open_trade.get("closed"):
                    trace_entry["events"].append(
                        f"trade_closed:{trades[-1].exit_reason}:{trades[-1].outcome_r}R"
                    )
                    open_trade = None

            if pending_order and index > pending_order["created_index"]:
                if index > pending_order["expires_index"] or classify_session(bar.ts) != pending_order["session"]:
                    trace_entry["rejection_reason"] = "pending_order_expired_or_session_changed"
                    trace_entry["events"].append("pending_order_cancelled")
                    diagnostics["pending_expired"] += 1
                    pending_order = None
                elif bar.low <= pending_order["entry"] <= bar.high:
                    open_trade = self._open_trade(pending_order, bar.ts)
                    diagnostics["orders_filled"] += 1
                    trace_entry["events"].append("pending_order_filled")
                    pending_order = None

            if active_setup:
                trace_entry["confirmation"] = self._confirmation_status(bars, index, active_setup, atr)
                if index > active_setup["expires_index"] or session != active_setup["session"]:
                    trace_entry["rejection_reason"] = "setup_expired_without_confirmation"
                    trace_entry["events"].append("setup_cancelled")
                    diagnostics["setup_expired"] += 1
                    active_setup = None
                elif trace_entry["confirmation"]["confirmed"]:
                    candidate = self._build_candidate(bars, index, active_setup, atr, previous_day_levels.get(local.date()))
                    candidates.append(candidate)
                    diagnostics["confirmed_candidates"] += 1
                    trace_entry["candidate_id"] = candidate.candidate_id
                    trace_entry["planned_order"] = {
                        "entry": candidate.entry,
                        "stop": candidate.stop,
                        "target": candidate.target,
                    }
                    trace_entry["events"].append("candidate_confirmed")
                    pending_order = {
                        "candidate": candidate,
                        "direction": candidate.direction,
                        "entry": candidate.entry,
                        "stop": candidate.stop,
                        "target": candidate.target,
                        "session": active_setup["session"],
                        "created_index": index,
                        "expires_index": index + int(self.profile["order_ttl_bars"]),
                    }
                    active_setup = None

            if active_setup or pending_order or open_trade or session not in {"london_killzone", "ny_killzone"} or index < 20:
                trace_entry["state"] = self._state_name(active_setup, pending_order, open_trade)
                trace.append(trace_entry)
                continue

            if not current_levels:
                trace_entry["rejection_reason"] = "no_liquidity_levels_for_bar"
                trace_entry["state"] = self._state_name(active_setup, pending_order, open_trade)
                trace.append(trace_entry)
                continue

            sweep = self._detect_sweep(bar, atr, current_levels)
            if sweep:
                diagnostics["sweeps"] += 1
                trace_entry["sweep"] = sweep
                trace_entry["events"].append("liquidity_sweep_detected")
                active_setup = {
                    "direction": sweep["direction"],
                    "session": session,
                    "level_name": sweep["level_name"],
                    "level_price": sweep["level_price"],
                    "sweep_extreme": sweep["sweep_extreme"],
                    "start_index": index,
                    "expires_index": index + 8,
                }
            else:
                trace_entry["rejection_reason"] = "no_valid_sweep"
            trace_entry["state"] = self._state_name(active_setup, pending_order, open_trade)
            trace.append(trace_entry)

        if open_trade:
            self._force_close(open_trade, bars[-1], trades)

        return {
            "candidates": [candidate.to_dict() for candidate in candidates],
            "trades": [trade.to_dict() for trade in trades],
            "metrics": compute_metrics(trades),
            "diagnostics": diagnostics,
            "trace": trace,
        }

    def _current_liquidity_levels(
        self,
        trade_day: date,
        local_day: date,
        asian_levels: dict[date, dict[str, float]],
        previous_day_levels: dict[date, dict[str, float]],
    ) -> list[tuple[str, float]]:
        levels: list[tuple[str, float]] = []
        if trade_day in asian_levels:
            levels.append(("asian_high", asian_levels[trade_day]["high"]))
            levels.append(("asian_low", asian_levels[trade_day]["low"]))
        if local_day in previous_day_levels:
            levels.append(("previous_day_high", previous_day_levels[local_day]["high"]))
            levels.append(("previous_day_low", previous_day_levels[local_day]["low"]))
        return levels

    def _detect_sweep(self, bar: Bar, atr: float, levels: list[tuple[str, float]]) -> dict[str, Any] | None:
        max_excursion = atr * float(self.profile["sweep_atr_max"])
        for level_name, level_price in levels:
            if "high" in level_name and bar.high > level_price and bar.close < level_price and (bar.high - level_price) <= max_excursion:
                return {
                    "direction": "short",
                    "level_name": level_name,
                    "level_price": level_price,
                    "sweep_extreme": bar.high,
                }
            if "low" in level_name and bar.low < level_price and bar.close > level_price and (level_price - bar.low) <= max_excursion:
                return {
                    "direction": "long",
                    "level_name": level_name,
                    "level_price": level_price,
                    "sweep_extreme": bar.low,
                }
        return None

    def _confirmation_status(self, bars: list[Bar], index: int, setup: dict[str, Any], atr: float) -> dict[str, Any]:
        lookback = int(self.profile["swing_lookback"])
        if index - setup["start_index"] < 2 or index < lookback + 2:
            return {
                "confirmed": False,
                "state": "waiting_for_minimum_bars",
                "blockers": ["not_enough_bars_after_sweep"],
            }
        window = bars[max(setup["start_index"], index - lookback) : index]
        body_size = abs(bars[index].close - bars[index].open)
        body_threshold = atr * float(self.profile["poi_atr_threshold"])
        if setup["direction"] == "long":
            pivot = max(bar.high for bar in window)
            has_fvg = bars[index].low > bars[index - 2].high
            close_pass = bars[index].close > pivot
        else:
            pivot = min(bar.low for bar in window)
            has_fvg = bars[index].high < bars[index - 2].low
            close_pass = bars[index].close < pivot
        blockers: list[str] = []
        if not close_pass:
            blockers.append("close_not_through_local_pivot")
        if not has_fvg and body_size < body_threshold:
            blockers.append("no_displacement_confirmation")
        return {
            "confirmed": close_pass and (has_fvg or body_size >= body_threshold),
            "state": "confirmed" if close_pass and (has_fvg or body_size >= body_threshold) else "waiting_confirmation",
            "pivot": round(pivot, 4),
            "body_size": round(body_size, 4),
            "body_threshold": round(body_threshold, 4),
            "has_fvg": has_fvg,
            "blockers": blockers,
        }

    def _build_candidate(
        self,
        bars: list[Bar],
        index: int,
        setup: dict[str, Any],
        atr: float,
        previous_day: dict[str, float] | None,
    ) -> Candidate:
        bar = bars[index]
        if setup["direction"] == "long":
            gap_low = bars[index - 2].high
            gap_high = max(gap_low, bar.low)
            entry = gap_low + (gap_high - gap_low) * float(self.profile["entry_offset"])
            stop = setup["sweep_extreme"] - (atr * float(self.profile["stop_atr"]))
            target = entry + ((entry - stop) * float(self.profile["target_r"]))
            distance_to_prev = abs((previous_day or {"high": bar.high})["high"] - bar.close) / max(atr, 0.0001)
        else:
            gap_high = bars[index - 2].low
            gap_low = min(gap_high, bar.high)
            entry = gap_high - ((gap_high - gap_low) * float(self.profile["entry_offset"]))
            stop = setup["sweep_extreme"] + (atr * float(self.profile["stop_atr"]))
            target = entry - ((stop - entry) * float(self.profile["target_r"]))
            distance_to_prev = abs(bar.close - (previous_day or {"low": bar.low})["low"]) / max(atr, 0.0001)
        body_size = abs(bar.close - bar.open)
        fvg_size = abs(gap_high - gap_low)
        sma_window = [sample.close for sample in bars[max(0, index - 20) : index]]
        bias = 1 if not sma_window or bar.close >= mean(sma_window) else -1
        session = classify_session(bar.ts)
        features = {
            "session_ny": 1 if session == "ny_killzone" else 0,
            "sweep_depth_atr": round(abs(setup["level_price"] - setup["sweep_extreme"]) / max(atr, 0.0001), 4),
            "body_atr": round(body_size / max(atr, 0.0001), 4),
            "fvg_size_atr": round(fvg_size / max(atr, 0.0001), 4),
            "bias": bias,
            "distance_to_prev_day_atr": round(distance_to_prev, 4),
        }
        reason = (
            f"{setup['level_name']} swept during {session}; "
            f"CHoCH confirmed with displacement; entry plans retrace into imbalance."
        )
        return Candidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:12]}",
            ts=bar.ts,
            direction=setup["direction"],
            sweep_level=setup["level_name"],
            poi_type="fvg",
            entry=round(entry, 4),
            stop=round(stop, 4),
            target=round(target, 4),
            atr=round(atr, 4),
            reason=reason,
            features=features,
            context={"session": session, "trade_day": trading_day(bar.ts).isoformat()},
        )

    def _open_trade(self, pending_order: dict[str, Any], ts: datetime) -> dict[str, Any]:
        candidate: Candidate = pending_order["candidate"]
        return {
            "trade_id": f"tr_{uuid.uuid4().hex[:12]}",
            "candidate": candidate,
            "entry": candidate.entry,
            "stop": candidate.stop,
            "target": candidate.target,
            "direction": candidate.direction,
            "entry_ts": ts,
            "breakeven_done": False,
            "risk": abs(candidate.entry - candidate.stop),
        }

    def _manage_open_trade(self, open_trade: dict[str, Any], bar: Bar, trades: list[Trade]) -> None:
        risk = max(open_trade["risk"], 0.0001)
        if open_trade["direction"] == "long":
            favorable = bar.high - open_trade["entry"]
            if favorable >= risk * float(self.profile["breakeven_r"]) and not open_trade["breakeven_done"]:
                open_trade["stop"] = open_trade["entry"]
                open_trade["breakeven_done"] = True
            stop_hit = bar.low <= open_trade["stop"]
            target_hit = bar.high >= open_trade["target"]
        else:
            favorable = open_trade["entry"] - bar.low
            if favorable >= risk * float(self.profile["breakeven_r"]) and not open_trade["breakeven_done"]:
                open_trade["stop"] = open_trade["entry"]
                open_trade["breakeven_done"] = True
            stop_hit = bar.high >= open_trade["stop"]
            target_hit = bar.low <= open_trade["target"]
        if stop_hit and target_hit:
            target_hit = False
        if stop_hit:
            self._close_trade(open_trade, bar.ts, open_trade["stop"], "stop", trades)
        elif target_hit:
            self._close_trade(open_trade, bar.ts, open_trade["target"], "target", trades)

    def _close_trade(
        self,
        open_trade: dict[str, Any],
        exit_ts: datetime,
        exit_price: float,
        exit_reason: str,
        trades: list[Trade],
    ) -> None:
        candidate: Candidate = open_trade["candidate"]
        risk = max(open_trade["risk"], 0.0001)
        if open_trade["direction"] == "long":
            outcome = (exit_price - open_trade["entry"]) / risk
        else:
            outcome = (open_trade["entry"] - exit_price) / risk
        trades.append(
            Trade(
                trade_id=open_trade["trade_id"],
                candidate_id=candidate.candidate_id,
                direction=open_trade["direction"],
                entry_ts=open_trade["entry_ts"],
                exit_ts=exit_ts,
                entry=round(open_trade["entry"], 4),
                exit=round(exit_price, 4),
                stop=round(candidate.stop, 4),
                target=round(candidate.target, 4),
                risk_r=1.0,
                outcome_r=round(outcome, 4),
                exit_reason=exit_reason,
                reason=candidate.reason,
            )
        )
        open_trade["closed"] = True

    def _force_close(self, open_trade: dict[str, Any], last_bar: Bar, trades: list[Trade]) -> None:
        self._close_trade(open_trade, last_bar.ts, last_bar.close, "time_exit", trades)

    @staticmethod
    def _state_name(
        active_setup: dict[str, Any] | None,
        pending_order: dict[str, Any] | None,
        open_trade: dict[str, Any] | None,
    ) -> str:
        if open_trade:
            return "in_trade"
        if pending_order:
            return "pending_order"
        if active_setup:
            return "watching_confirmation"
        return "searching"

    def _make_trace_entry(
        self,
        bar: Bar,
        atr: float,
        session: str,
        levels: list[tuple[str, float]],
        active_setup: dict[str, Any] | None,
        pending_order: dict[str, Any] | None,
        open_trade: dict[str, Any] | None,
    ) -> dict[str, Any]:
        level_map = {name: round(price, 4) for name, price in levels}
        entry: dict[str, Any] = {
            "ts": bar.ts.isoformat(),
            "session": session,
            "bar": {
                "open": round(bar.open, 4),
                "high": round(bar.high, 4),
                "low": round(bar.low, 4),
                "close": round(bar.close, 4),
            },
            "atr": round(atr, 4),
            "asian_range": {
                "high": level_map.get("asian_high"),
                "low": level_map.get("asian_low"),
            },
            "previous_day_range": {
                "high": level_map.get("previous_day_high"),
                "low": level_map.get("previous_day_low"),
            },
            "sweep": None,
            "confirmation": None,
            "planned_order": None,
            "active_trade": None,
            "candidate_id": None,
            "state": self._state_name(active_setup, pending_order, open_trade),
            "events": [],
            "rejection_reason": None,
        }
        if active_setup:
            entry["active_setup"] = {
                "direction": active_setup["direction"],
                "level_name": active_setup["level_name"],
                "level_price": round(active_setup["level_price"], 4),
                "sweep_extreme": round(active_setup["sweep_extreme"], 4),
            }
        if pending_order:
            entry["planned_order"] = {
                "entry": round(pending_order["entry"], 4),
                "stop": round(pending_order["stop"], 4),
                "target": round(pending_order["target"], 4),
                "candidate_id": pending_order["candidate"].candidate_id,
            }
        return entry
