"""BTC liquidity-excursion research reference; no exchange order submission.

Information clocks use millisecond UTC bar opens. Signals observe closed bars;
market orders use the next open. This is a deliberately bounded OHLC simulator,
not a live broker or an engine registered with Mutation Lab.
"""
from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Candle:
    t: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True, slots=True)
class Parameters:
    lookback_minutes: int = 360
    atr_minutes: int = 120
    confirm_minutes: int = 45
    max_hold_minutes: int = 360
    stop_buffer_atr: float = 0.1
    min_sweep_atr: float = 0.1
    displacement_atr: float = 0.5
    target_r: float = 2.0


@dataclass(frozen=True, slots=True)
class Signal:
    index: int
    direction: int
    stop: float
    sweep_index: int
    reason: str


@dataclass(frozen=True, slots=True)
class Execution:
    initial_capital: float = 100000.0
    risk_fraction: float = 0.0025
    max_notional_fraction: float = 1.0
    fee_bps: float = 6.0
    slip_bps: float = 2.0
    tick: float = 0.1
    quantity_step: float = 0.001
    min_quantity: float = 0.001
    max_quantity: float = 120.0
    min_notional: float = 50.0
    funding_mark_buffer_fraction: float = 0.0


APPROACHES = ("reclaim", "confirm", "confirm_fvg", "breakout_control")
DIRECTIONS = {"long": {1}, "short": {-1}, "both": {-1, 1}}


def validate_bars(bars: list[Candle], minutes: int) -> None:
    if minutes not in (5, 15) or not bars:
        raise ValueError("Nonempty 5m or 15m candles required")
    step = minutes * 60000
    for i, b in enumerate(bars):
        if (not isinstance(b.t, int) or b.t % step or
                (i and b.t - bars[i - 1].t != step)):
            raise ValueError(f"Misaligned, duplicated, or missing candle at {i}")
        if (not all(math.isfinite(v) and v > 0 for v in
                    (b.open, b.high, b.low, b.close)) or
                not math.isfinite(b.volume) or b.volume < 0 or
                b.low > min(b.open, b.close) or b.high < max(b.open, b.close)):
            raise ValueError(f"Invalid OHLCV at {i}")


def indicators(bars: list[Candle], minutes: int, p: Parameters) -> list[dict]:
    """Prior completed range and mean true range; current bar excluded."""
    validate_bars(bars, minutes)
    durations = (p.lookback_minutes, p.atr_minutes, p.confirm_minutes,
                 p.max_hold_minutes)
    if any(v < minutes or v % minutes for v in durations):
        raise ValueError("Durations must be positive multiples of timeframe")
    if (any(not math.isfinite(v) or v < 0 for v in
            (p.stop_buffer_atr, p.min_sweep_atr, p.displacement_atr)) or
            not math.isfinite(p.target_r) or p.target_r <= 0):
        raise ValueError("Invalid strategy geometry")
    n, a = p.lookback_minutes // minutes, p.atr_minutes // minutes
    hi: deque[int] = deque()
    lo: deque[int] = deque()
    trs: deque[float] = deque()
    total = 0.0
    out = []
    for i, b in enumerate(bars):
        while hi and hi[0] < i - n:
            hi.popleft()
        while lo and lo[0] < i - n:
            lo.popleft()
        ready = i >= max(n, a)
        out.append({"atr": total / a if ready else None,
                    "high": bars[hi[0]].high if ready else None,
                    "low": bars[lo[0]].low if ready else None})
        previous = bars[i - 1].close if i else b.open
        tr = max(b.high - b.low, abs(b.high - previous), abs(b.low - previous))
        trs.append(tr)
        total += tr
        if len(trs) > a:
            total -= trs.popleft()
        while hi and bars[hi[-1]].high <= b.high:
            hi.pop()
        while lo and bars[lo[-1]].low >= b.low:
            lo.pop()
        hi.append(i)
        lo.append(i)
    return out


def detect(bars: list[Candle], minutes: int, approach: str,
           p: Parameters = Parameters()) -> tuple[list[Signal], list[dict]]:
    if approach not in APPROACHES:
        raise ValueError("Unknown approach")
    features = indicators(bars, minutes, p)
    signals: list[Signal] = []
    events: list[dict] = []
    pending: dict | None = None

    def event(i: int, kind: str, **fields: Any) -> None:
        events.append({"index": i, "known_at": bars[i].t + minutes * 60000,
                       "kind": kind, **fields})

    for i, (b, f) in enumerate(zip(bars, features)):
        atr = f["atr"]
        if atr is None or atr <= 0:
            continue
        if pending:
            d, j = pending["direction"], pending["index"]
            original = bars[j]
            invalid = b.low < original.low if d == 1 else b.high > original.high
            if invalid or (i - j) * minutes > p.confirm_minutes:
                event(i, "invalidated" if invalid else "expired", sweep_index=j)
                pending = None
            else:
                crossed = b.close > original.high if d == 1 else b.close < original.low
                displacement = d * (b.close - b.open) >= p.displacement_atr * atr
                gap = (i >= 2 and (b.low > bars[i - 2].high if d == 1
                                   else b.high < bars[i - 2].low))
                if crossed and displacement and (approach != "confirm_fvg" or gap):
                    signals.append(Signal(i, d, pending["stop"], j, approach))
                    event(i, "confirmed", sweep_index=j, direction=d)
                    pending = None
        if approach == "breakout_control":
            d = 1 if b.close > f["high"] else -1 if b.close < f["low"] else 0
            if d:
                stop = b.low - p.stop_buffer_atr * atr if d == 1 else b.high + p.stop_buffer_atr * atr
                signals.append(Signal(i, d, stop, i, approach))
                event(i, "control_signal", direction=d)
            continue
        long = b.low < f["low"] - p.min_sweep_atr * atr and b.close > f["low"]
        short = b.high > f["high"] + p.min_sweep_atr * atr and b.close < f["high"]
        if long and short:
            event(i, "dual_sweep_excluded")
            continue
        d = 1 if long else -1 if short else 0
        if d:
            event(i, "sweep", direction=d)
            stop = b.low - p.stop_buffer_atr * atr if d == 1 else b.high + p.stop_buffer_atr * atr
            if approach == "reclaim":
                signals.append(Signal(i, d, stop, i, approach))
            else:
                if pending:
                    event(i, "replaced", sweep_index=pending["index"])
                pending = {"index": i, "direction": d, "stop": stop}
    if pending:
        event(len(bars) - 1, "pending_at_cutoff", sweep_index=pending["index"])
    return signals, events


def simulate(bars: list[Candle], signals: list[Signal], minutes: int,
             direction: str, funding: list[dict], p: Parameters = Parameters(),
             e: Execution = Execution()) -> dict:
    """One position; signed funding; risk sizing; adverse OHLC and gap fills.

    Funding exactly at an open belongs to the position carried into that open.
    An intrabar funding event coinciding with a possible intrabar exit receives
    adverse treatment: debit charged, possible credit omitted.
    """
    validate_bars(bars, minutes)
    if direction not in DIRECTIONS:
        raise ValueError("Unknown direction")
    if (any(not math.isfinite(v) or v <= 0 for v in
            (e.initial_capital, e.risk_fraction, e.max_notional_fraction, e.tick,
             e.quantity_step, e.min_quantity, e.max_quantity, e.min_notional)) or
            not 0 < e.risk_fraction <= 1 or not 0 < e.max_notional_fraction <= 1 or
            any(not math.isfinite(v) or v < 0 for v in (e.fee_bps, e.slip_bps)) or
            not 0 <= e.funding_mark_buffer_fraction < 1):
        raise ValueError("Invalid execution settings")
    by_index: dict[int, list[Signal]] = {}
    for s in signals:
        if (s.index < 0 or s.index >= len(bars) or s.direction not in (-1, 1)
                or s.sweep_index > s.index or not math.isfinite(s.stop) or s.stop <= 0):
            raise ValueError("Invalid signal")
        by_index.setdefault(s.index + 1, []).append(s)
    for j, f in enumerate(funding):
        if (not isinstance(f["ts"], int) or (j and f["ts"] <= funding[j - 1]["ts"])
                or not math.isfinite(f["rate"]) or not math.isfinite(f["mark"])
                or f["mark"] <= 0):
            raise ValueError("Invalid funding history")
    cash = e.initial_capital
    fee, slip = e.fee_bps / 10000, e.slip_bps / 10000
    position = None
    trades, curve, ledger = [], [], []
    counts: Counter = Counter()
    fi = 0
    step = minutes * 60000
    max_hold = p.max_hold_minutes // minutes
    peak = e.initial_capital
    worst_dd = 0.0

    def log(i: int, kind: str, **fields: Any) -> None:
        ledger.append({"bar_index": i, "t": bars[i].t, "kind": kind, **fields})

    def fund(i: int, f: dict, uncertain: bool = False) -> None:
        nonlocal cash
        if position is None:
            return
        payment = -position["direction"] * position["quantity"] * f["mark"] * f["rate"]
        payment -= abs(payment) * e.funding_mark_buffer_fraction
        if uncertain:
            payment = min(payment, 0.0)
        cash += payment
        position["funding"] += payment
        log(i, "funding", amount=payment, at=f["ts"], uncertain_exit_order=uncertain)

    def close(i: int, raw: float, reason: str, at: int) -> None:
        nonlocal cash, position
        assert position is not None
        q, d = position["quantity"], position["direction"]
        price = raw * (1 - d * slip)
        exit_fee = price * q * fee
        gross = (price - position["entry"]) * q * d
        cash += gross - exit_fee
        net = gross - position["entry_fee"] - exit_fee + position["funding"]
        trades.append({**position, "exit": price, "exit_at": at,
                       "exit_index": i, "reason": reason, "net_pnl": net,
                       "gross_pnl": gross, "exit_fee": exit_fee})
        log(i, "exit", price=price, reason=reason, at=at, net_pnl=net)
        counts[reason] += 1
        position = None

    while fi < len(funding) and funding[fi]["ts"] < bars[0].t:
        fi += 1
    for i, b in enumerate(bars):
        carried_equity = cash + ((b.open - position["entry"]) * position["quantity"] *
                                 position["direction"] if position else 0)
        while fi < len(funding) and funding[fi]["ts"] <= b.t:
            fund(i, funding[fi])
            fi += 1
        if position and i - position["entry_index"] >= max_hold:
            close(i, b.open, "time_exit", b.t)
        for s in by_index.get(i, []):
            if s.direction not in DIRECTIONS[direction]:
                counts["direction_excluded"] += 1
                continue
            if position is not None:
                counts["position_concurrency"] += 1
                continue
            d = s.direction
            entry = b.open * (1 + d * slip)
            # Stops round away from the entry; target distances round outward.
            stop = (math.floor(s.stop / e.tick + 1e-9) if d == 1
                    else math.ceil(s.stop / e.tick - 1e-9)) * e.tick
            distance = d * (entry - stop)
            if cash <= 0 or distance <= 0 or stop <= 0:
                counts["invalid_entry_gap"] += 1
                log(i, "entry_rejected", reason="invalid_entry_gap", signal_index=s.index)
                continue
            stopped_exit = stop * (1 - d * slip)
            risk_per_unit = d * (entry - stopped_exit) + fee * (entry + stopped_exit)
            desired = min(cash * e.risk_fraction / risk_per_unit,
                          cash * e.max_notional_fraction / (entry * (1 + fee)),
                          e.max_quantity)
            quantity = math.floor(desired / e.quantity_step + 1e-9) * e.quantity_step
            if quantity < e.min_quantity or quantity * entry < e.min_notional:
                counts["venue_size_rejected"] += 1
                log(i, "entry_rejected", reason="venue_size_rejected", signal_index=s.index)
                continue
            target_raw = entry + d * distance * p.target_r
            target = (math.ceil(target_raw / e.tick - 1e-9) if d == 1
                      else math.floor(target_raw / e.tick + 1e-9)) * e.tick
            if target <= 0:
                counts["invalid_target"] += 1
                continue
            entry_fee = entry * quantity * fee
            position = {"entry": entry, "entry_index": i, "entry_at": b.t,
                        "signal_index": s.index, "known_at": bars[s.index].t + step,
                        "direction": d, "quantity": quantity, "stop": stop,
                        "target": target, "entry_fee": entry_fee, "funding": 0.0,
                        "initial_risk": quantity * risk_per_unit,
                        "entry_equity": cash, "reason_entry": s.reason}
            cash -= entry_fee
            counts["entries"] += 1
            log(i, "entry", **position)
        intrabar_worst = cash
        if position:
            d, q = position["direction"], position["quantity"]
            stop, target = position["stop"], position["target"]
            hit_stop = b.low <= stop if d == 1 else b.high >= stop
            hit_target = b.high >= target if d == 1 else b.low <= target
            gap = hit_stop and (b.open <= stop if d == 1 else b.open >= stop)
            if gap:
                # The exit is known at the open. Later funding cannot belong to
                # this position; funding exactly at the open was handled above.
                intrabar_worst = cash + d * q * (b.open - position["entry"]) - b.open * q * fee
                close(i, b.open, "stop_gap", b.t)
                while fi < len(funding) and funding[fi]["ts"] < b.t + step:
                    fi += 1
            else:
                while fi < len(funding) and funding[fi]["ts"] < b.t + step:
                    fund(i, funding[fi], hit_stop or hit_target)
                    fi += 1
                adverse = (stop if hit_stop else b.low if d == 1 else b.high)
                intrabar_worst = cash + d * q * (adverse - position["entry"]) - adverse * q * fee
                if hit_stop:
                    close(i, stop, "ambiguous_stop_first" if hit_target else "stop", b.t + step)
                elif hit_target:
                    # Market-on-trigger proxy: no favorable gap price improvement.
                    close(i, target, "target", b.t + step)
        else:
            while fi < len(funding) and funding[fi]["ts"] < b.t + step:
                fi += 1
        marked = cash
        if position:
            q, d = position["quantity"], position["direction"]
            marked += d * q * (b.close - position["entry"]) - b.close * q * fee
        worst_dd = max(worst_dd, (peak - min(intrabar_worst, marked, carried_equity)) / peak * 100)
        peak = max(peak, marked)
        curve.append({"t": b.t + step, "equity": marked, "cash": cash,
                      "quantity": position["quantity"] * position["direction"] if position else 0.0})
    if position:
        counts["open_at_cutoff"] += 1
        log(len(bars) - 1, "censored_position", **position)
    counts["pending_at_cutoff"] = len(by_index.get(len(bars), []))
    wins = sum(max(t["net_pnl"], 0) for t in trades)
    losses = -sum(min(t["net_pnl"], 0) for t in trades)
    close_peak, close_dd = e.initial_capital, 0.0
    for point in curve:
        close_peak = max(close_peak, point["equity"])
        close_dd = max(close_dd, (close_peak - point["equity"]) / close_peak * 100)
    metrics = {"net_return_pct": (curve[-1]["equity"] / e.initial_capital - 1) * 100,
               "closed_trades": len(trades), "wins": sum(t["net_pnl"] > 0 for t in trades),
               "profit_factor": wins / losses if losses else None,
               "gross_profit": wins, "gross_loss": losses,
               "closed_net_pnl": sum(t["net_pnl"] for t in trades),
               "fees": sum(t["entry_fee"] + t["exit_fee"] for t in trades) +
                       (position["entry_fee"] if position else 0),
               "funding": sum(t["funding"] for t in trades) + (position["funding"] if position else 0),
               "max_drawdown_pct": close_dd, "adverse_drawdown_pct": worst_dd,
               "marked_equity": curve[-1]["equity"], "counts": dict(counts)}
    return {"metrics": metrics, "trades": trades, "equity": curve, "ledger": ledger,
            "open_position": position, "execution": asdict(e), "parameters": asdict(p)}
