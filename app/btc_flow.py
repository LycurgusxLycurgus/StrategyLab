"""Causal executed-taker-pressure features and fixed reversal intents."""
from collections import deque
from dataclasses import dataclass
import math
from app.btc_liquidity import validate_bars
from app.btc_successor import cost_admitted

DAY = 86400000
APPROACHES = ('executed_taker_pressure_reversal_v1', 'price_shock_reversal_control_v1')

@dataclass(frozen=True, slots=True)
class Intent:
    index: int
    direction: int
    stop: float
    anchor: float
    hold_minutes: int = 120
    reason: str = ''

def build_features(bars, flow, minutes):
    validate_bars(bars, minutes)
    if len(flow) != len(bars):
        raise ValueError('Flow count mismatch')
    step = minutes * 60000; perday = DAY // step; perhour = 3600000 // step
    days = deque(maxlen=30); current = None; day_values = []; atr = None
    prev_hour = None; trs = deque(maxlen=20); out = []
    for i, (b, item) in enumerate(zip(bars, flow)):
        try: q, buy = item['quote'], item['taker_buy_quote']
        except (KeyError, TypeError) as exc: raise ValueError('Invalid flow schema') from exc
        if not all(math.isfinite(x) and x >= 0 for x in (q,buy)) or buy > q or (b.volume == 0) != (q == 0):
            raise ValueError('Invalid flow')
        day = b.t // DAY
        if day != current:
            if current is not None:
                if len(day_values) == perday and current == day - 1:
                    days.append((current, day_values))
                else:
                    days.clear()
            current = day; day_values = []
            if len(days) == 30 and days[0][0] == day-30:
                ordered = sorted(v for _, values in days for v in values)
                threshold = ordered[math.ceil(.99*len(ordered))-1]
            else: threshold = None
        pressure = 2*buy-q; day_values.append(abs(pressure))
        known = b.t + step
        if known % 3600000 == 0 and i >= perhour-1 and bars[i-perhour+1].t % 3600000 == 0:
            chunk = bars[i-perhour+1:i+1]
            high = max(x.high for x in chunk); low = min(x.low for x in chunk)
            if prev_hour is not None:
                trs.append(max(high-low, abs(high-prev_hour), abs(low-prev_hour)))
                if len(trs) == 20: atr = sum(trs)/20
            prev_hour = b.close
        out.append({'known_at':known, 'atr':atr if atr is not None and atr > 0 else None,
                    'pressure':pressure, 'pressure_q99':threshold})
    return out

def detect(bars, features, minutes, approach):
    validate_bars(bars, minutes)
    if approach not in APPROACHES or len(features) != len(bars): raise ValueError('Invalid detector inputs')
    signals=[]; events=[]; step=minutes*60000
    for i,(b,f) in enumerate(zip(bars,features)):
        if f.get('known_at') != b.t+step: raise ValueError('Feature timing mismatch')
        r=b.close/b.open-1
        if abs(b.close-b.open) + 1e-12*max(b.open,1) < .006*b.open: continue
        if f.get('atr') is None or f.get('pressure_q99') is None:
            events.append({'index':i,'known_at':f['known_at'],'kind':'unavailable_feature'}); continue
        q=f['pressure']; threshold=f['pressure_q99']
        if approach == APPROACHES[0] and not (abs(q)>threshold and q*r>0):
            events.append({'index':i,'known_at':f['known_at'],'kind':'pressure_filter'}); continue
        d=-1 if r>0 else 1; stop=b.close-d*2*f['atr']
        if not math.isfinite(stop) or stop<=0:
            events.append({'index':i,'known_at':f['known_at'],'kind':'invalid_stop','stop':stop}); continue
        s=Intent(i,d,stop,b.open,120,approach); signals.append(s)
        events.append({'index':i,'known_at':f['known_at'],'legal_after':f['known_at']+1,'kind':'raw_signal','direction':d,'stop':stop,'anchor':b.open,'cost_admitted':cost_admitted(b.close,stop,d)})
    return signals,events
