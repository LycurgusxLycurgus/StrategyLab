"""Causal, closed-bar SMC-inspired research detectors."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.btc_liquidity import Candle, Signal, Parameters, indicators

APPROACHES = ("bos_order_block", "silver_bullet", "turtle_soup_plus1")

@dataclass(frozen=True, slots=True)
class SmcParameters:
    atr_minutes: int = 120
    pivot_span: int = 2
    block_search_bars: int = 12
    setup_minutes: int = 60
    displacement_atr: float = 0.5
    stop_buffer_atr: float = 0.1
    silver_expiry_minutes: int = 30
    turtle_lookback: int = 20
    turtle_min_age: int = 4


def detect(bars: list[Candle], minutes: int, approach: str,
           p: SmcParameters = SmcParameters()) -> tuple[list[Signal], list[dict]]:
    if approach not in APPROACHES or minutes not in (5, 15) or (approach == "silver_bullet" and minutes != 5):
        raise ValueError("Unsupported approach or timeframe")
    ints = (p.atr_minutes, p.pivot_span, p.block_search_bars, p.setup_minutes,
            p.silver_expiry_minutes, p.turtle_lookback, p.turtle_min_age)
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in ints) or any(
            v % minutes for v in (p.atr_minutes, p.setup_minutes, p.silver_expiry_minutes)) or p.turtle_min_age > p.turtle_lookback or any(
            not math.isfinite(v) or v < 0 for v in (p.displacement_atr, p.stop_buffer_atr)):
        raise ValueError("Invalid detector settings")
    features = indicators(bars, minutes, Parameters(lookback_minutes=p.atr_minutes,
                          atr_minutes=p.atr_minutes, confirm_minutes=minutes, max_hold_minutes=minutes))
    ny = ZoneInfo("America/New_York") if approach == "silver_bullet" else None
    signals, events = [], []
    pending = None
    pivots = {1: None, -1: None}
    session_date, range_bars, session_used = None, [], False
    step = minutes * 60000
    def event(i, kind, **kw):
        events.append({"index": i, "known_at": bars[i].t + step, "kind": kind, **kw})
    def emit(i, state):
        signals.append(Signal(i, state['direction'], state['stop'], state['index'], approach))
        event(i, "signal", direction=state['direction'], source_index=state['index'], stop=state['stop'])
    for i, b in enumerate(bars):
        atr = features[i]['atr']
        if approach == 'bos_order_block':
            k = i - p.pivot_span
            if k >= p.pivot_span:
                window = bars[k-p.pivot_span:i+1]
                for d, attr in ((1, 'high'), (-1, 'low')):
                    value = getattr(bars[k], attr)
                    if all(d * (value - getattr(x, attr)) > 0 for j, x in enumerate(window) if j != p.pivot_span):
                        pivots[d] = {'index': k, 'level': value, 'broken': False}
                        event(i, 'pivot', direction=d, source_index=k, level=value)
            if pending:
                d = pending['direction']
                invalid = b.low < pending['low'] if d == 1 else b.high > pending['high']
                if (i - pending['created']) * minutes > p.setup_minutes or invalid:
                    event(i, 'invalidated' if invalid else 'expired', direction=d, source_index=pending['index'])
                    pending = None
                elif i > pending['created'] and b.low <= pending['high'] and b.high >= pending['low'] and d*(b.close-(pending['high'] if d == 1 else pending['low'])) > 0 and d*(b.close-b.open) > 0:
                    emit(i, pending); pending = None
            if i:
                for d in (1, -1):
                    pivot = pivots[d]
                    if pivot and not pivot['broken'] and d*(bars[i-1].close-pivot['level']) <= 0 and d*(b.close-pivot['level']) > 0:
                        pivot['broken'] = True
                        event(i, 'bos', direction=d, source_index=pivot['index'], level=pivot['level'])
                        created = False
                        if atr is not None and atr > 0 and d*(b.close-b.open) >= p.displacement_atr*atr:
                            for j in range(i-1, max(pivot['index'], i-p.block_search_bars)-1, -1):
                                block = bars[j]
                                if d*(block.close-block.open) < 0:
                                    if pending: event(i, 'replaced', direction=pending['direction'], source_index=pending['index'])
                                    pending = {'direction': d, 'index': j, 'created': i, 'low': block.low, 'high': block.high,
                                               'stop': block.low-p.stop_buffer_atr*atr if d == 1 else block.high+p.stop_buffer_atr*atr}
                                    event(i, 'block', direction=d, source_index=j, low=block.low, high=block.high, stop=pending['stop'])
                                    created = True
                                    break
                        if not created:
                            reason = 'displacement_or_atr_unavailable' if atr is None or atr <= 0 or d*(b.close-b.open) < p.displacement_atr*atr else 'no_opposing_candle'
                            event(i, 'bos_rejected', direction=d, source_index=pivot['index'], reason=reason)
        elif approach == 'turtle_soup_plus1':
            emitted = False
            if pending:
                d = pending['direction']
                if atr is not None and atr > 0 and d*(b.close-pending['level']) > 0:
                    pending['stop'] = min(b.low, bars[pending['index']].low)-p.stop_buffer_atr*atr if d == 1 else max(b.high, bars[pending['index']].high)+p.stop_buffer_atr*atr
                    emit(i, pending); emitted = True
                else: event(i, 'reclaim_failed', direction=d, source_index=pending['index'])
                pending = None
            if not emitted and i >= p.turtle_lookback and atr is not None and atr > 0:
                prior = bars[i-p.turtle_lookback:i]
                low, high = min(x.low for x in prior), max(x.high for x in prior)
                li = max(j for j in range(i-p.turtle_lookback, i) if bars[j].low == low)
                hi = max(j for j in range(i-p.turtle_lookback, i) if bars[j].high == high)
                d = 1 if b.close < low and i-li >= p.turtle_min_age else -1 if b.close > high and i-hi >= p.turtle_min_age else 0
                if d:
                    pending = {'direction': d, 'index': i, 'level': low if d == 1 else high}
                    event(i, 'breakout', direction=d, source_index=li if d == 1 else hi, level=pending['level'])
        else:
            local = datetime.fromtimestamp(b.t / 1000, timezone.utc).astimezone(ny)
            date = local.date()
            if date != session_date:
                if pending: event(i, 'date_reset', direction=pending['direction'], source_index=pending['index'])
                session_date, range_bars, session_used, pending = date, [], False, None
            clock = local.hour * 60 + local.minute
            if 540 <= clock < 600: range_bars.append((clock, b))
            if clock + minutes >= 660 and pending:
                event(i, 'session_ended', direction=pending['direction'], source_index=pending['index'])
                pending = None
            if not (600 <= clock and clock + minutes < 660) or session_used or len(range_bars) != 12 or [x[0] for x in range_bars] != list(range(540,600,5)) or atr is None or atr <= 0:
                continue
            rh, rl = max(x[1].high for x in range_bars), min(x[1].low for x in range_bars)
            if pending:
                d, j = pending['direction'], pending['index']
                invalid = b.low < bars[j].low if d == 1 else b.high > bars[j].high
                if pending['stage'] == 'gap': invalid = invalid or (b.close < pending['low'] if d == 1 else b.close > pending['high'])
                if invalid or (i-pending['created'])*minutes > p.silver_expiry_minutes:
                    event(i, 'invalidated' if invalid else 'expired', direction=d, source_index=j); pending = None
                elif pending['stage'] == 'sweep':
                    gap = i >= 2 and (b.low > bars[i-2].high if d == 1 else b.high < bars[i-2].low)
                    if d*(b.close-(bars[j].high if d == 1 else bars[j].low)) > 0 and d*(b.close-b.open) >= p.displacement_atr*atr and gap:
                        pending.update(stage='gap', created=i, low=bars[i-2].high if d == 1 else b.high, high=b.low if d == 1 else bars[i-2].low)
                        event(i, 'gap', direction=d, source_index=j, low=pending['low'], high=pending['high'])
                elif b.low <= pending['high'] and b.high >= pending['low'] and d*(b.close-(pending['high'] if d == 1 else pending['low'])) > 0 and d*(b.close-b.open) > 0:
                    emit(i, pending); pending = None; session_used = True
            if session_used: continue
            long = b.low < rl and b.close > rl
            short = b.high > rh and b.close < rh
            if long and short: event(i, 'dual_sweep_excluded'); continue
            d = 1 if long else -1 if short else 0
            if d:
                if pending: event(i, 'replaced', direction=pending['direction'], source_index=pending['index'])
                pending = {'direction': d, 'index': i, 'created': i, 'stage': 'sweep', 'stop': b.low-p.stop_buffer_atr*atr if d == 1 else b.high+p.stop_buffer_atr*atr}
                event(i, 'sweep', direction=d, source_index=i, stop=pending['stop'])
    if pending: event(len(bars)-1, 'pending_at_cutoff', direction=pending['direction'], source_index=pending['index'])
    return signals, events


