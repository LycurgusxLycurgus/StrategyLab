"""Fixed causal funding-state event features and long intents."""
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass
import math
from app.btc_liquidity import validate_bars

DAY=86400000
SLOT=8*3600000
APPROACHES=('low_percentile_funding_long_24h_v1','stale_funding_7d_long_24h_control_v1','continuous_long_control_v1')

@dataclass(frozen=True, slots=True)
class FundingExecution:
    initial_capital: float=100000
    entry_notional_fraction: float=.1
    fee_bps: float=6
    slip_bps: float=2
    quantity_step: float=.001
    min_quantity: float=.001
    max_quantity: float=120
    min_notional: float=50
    funding_mark_buffer_fraction: float=.01

@dataclass(frozen=True, slots=True)
class Intent:
    index: int
    event_ts: int
    source_event_ts: int
    observation_at: int
    decision_at: int
    fill_at: int
    hold_minutes: int | None
    reason: str

def build_event_features(funding, data_start):
    if type(data_start) is not int: raise ValueError('Invalid data start')
    out=[]; ordered=[]; left=0; prev=None
    for f in funding:
        try: ts=f['ts']; rate=f['rate']; mark=f['mark']
        except (KeyError,TypeError) as exc: raise ValueError('Invalid funding schema') from exc
        if type(ts) is not int or ts<data_start or not isinstance(rate,(int,float)) or not math.isfinite(rate) or not isinstance(mark,(int,float)) or not math.isfinite(mark) or mark<=0: raise ValueError('Invalid funding event')
        slot=ts//SLOT
        if prev is None and slot!=data_start//SLOT: raise ValueError('Funding coverage does not begin at data start')
        if prev is not None and (ts<=prev['ts'] or slot!=prev['ts']//SLOT+1): raise ValueError('Funding slots incomplete or unordered')
        while left<len(out) and funding[left]['ts']<ts-180*DAY:
            ordered.pop(bisect_left(ordered,funding[left]['rate'])); left+=1
        n=len(ordered); less=bisect_left(ordered,rate); equal=bisect_right(ordered,rate)-less
        ready=ts>=data_start+180*DAY and n>=300
        lag=out[-21] if len(out)>=21 and out[-21]['slot']==slot-21 else None
        out.append({'event_ts':ts,'slot':slot,'prior_count':n,'less_count':less,'equal_count':equal,'percentile':(2*less+equal)/(2*n) if ready else None,'low_state':5*(2*less+equal)<=n if ready else None,'common_ready':ts>=data_start+187*DAY and ready and lag is not None and lag['low_state'] is not None,'lag_low_state':lag['low_state'] if lag else None,'lag_event_ts':lag['event_ts'] if lag else None})
        insort(ordered,rate); prev=f
    return out

def detect(bars, minutes, event_features, approach):
    validate_bars(bars,minutes)
    if minutes not in (5,15) or approach not in APPROACHES: raise ValueError('Invalid detector inputs')
    step=minutes*60000; start=bars[0].t; end=bars[-1].t+step; signals=[]; events=[]; previous=None
    for f in event_features:
        ts=f['event_ts']
        if type(ts) is not int or (previous is not None and ts<=previous): raise ValueError('Invalid event features')
        previous=ts
        if not start<=ts<end: continue
        observation=((ts+1)//step+1)*step; index=(observation-start)//step-1
        if not 0<=index<len(bars): continue
        source=ts if approach!=APPROACHES[1] else f['lag_event_ts']
        eligible=f['common_ready'] and (approach==APPROACHES[2] or (f['low_state'] if approach==APPROACHES[0] else f['lag_low_state']))
        kind='raw_signal' if eligible else 'unavailable_feature' if not f['common_ready'] else 'state_filter'
        event={'index':index,'event_ts':ts,'source_event_ts':source,'observation_at':observation,'decision_at':observation+1,'fill_at':observation+step,'kind':kind}
        events.append(event)
        if eligible: signals.append(Intent(index,ts,source,observation,observation+1,observation+step,None if approach==APPROACHES[2] else 1440,approach))
    return signals,events
