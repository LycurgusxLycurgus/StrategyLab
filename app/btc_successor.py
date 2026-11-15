"""Frozen causal feature and signal definitions for BTC successor research."""
from dataclasses import dataclass
from collections import deque
import math
import statistics
from app.btc_liquidity import validate_bars

STEP = 900000
DAY = 86400000
APPROACHES = ('shock_reversal_2h','utc_noise_momentum','close_channel_24h','clock_6h_long','clock_6h_short','clock_6h_alternating')

@dataclass(frozen=True, slots=True)
class ModelParameters:
    atr_hours: int = 20
    shock_returns: int = 240
    shock_multiple: float = 3.0
    noise_days: int = 14
    channel_hours: int = 24
    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in (self.atr_hours,self.shock_returns,self.noise_days,self.channel_hours)) or self.shock_returns < 2 or self.channel_hours < 2 or not math.isfinite(self.shock_multiple) or self.shock_multiple <= 0:
            raise ValueError('Invalid model parameters')

@dataclass(frozen=True, slots=True)
class Intent:
    index: int
    direction: int
    stop: float
    hold_minutes: int
    reason: str

def cost_admitted(price, stop, direction):
    return (direction in (-1,1) and math.isfinite(price) and math.isfinite(stop) and price > 0 and stop > 0 and direction*(price-stop)>0 and .002*price <= .25*abs(price-stop)+1e-12*max(price,1))

def build_features(bars15, quote15, p=ModelParameters()):
    validate_bars(bars15,15)
    if len(quote15)!=len(bars15): raise ValueError('Turnover count mismatch')
    for b,q in zip(bars15,quote15):
        if not math.isfinite(q) or q < 0 or (b.volume == 0) != (q == 0) or (b.volume and not b.low*(1-1e-5) <= q/b.volume <= b.high*(1+1e-5)):
            raise ValueError('Invalid quote turnover')
    out=[]; hourly=[]; trs=deque(maxlen=p.atr_hours); returns=deque(maxlen=p.shock_returns)
    prev_hour=None; prev_two=None; atr=None; days={}; current_day=None; daybars=[]; dayopen=None; prevdayclose=None; qsum=bsum=0.0
    for i,(b,q) in enumerate(zip(bars15,quote15)):
        day=b.t//DAY
        if day != current_day:
            if current_day is not None:
                if len(daybars)==96 and daybars[0][0] % DAY == 0:
                    days[current_day]=(dayopen,[x[1] for x in daybars])
                    prevdayclose=daybars[-1][1]
                else: prevdayclose=None
            current_day=day; daybars=[]; dayopen=b.open if b.t%DAY==0 else None; qsum=bsum=0.0
            for old in list(days):
                if old < day-p.noise_days: del days[old]
        daybars.append((b.t,b.close)); qsum+=q; bsum+=b.volume
        known=b.t+STEP; hc=known%3600000==0 and i>=3 and bars15[i-3].t%3600000==0
        tc=known%7200000==0 and i>=7 and bars15[i-7].t%7200000==0
        f={'known_at':known,'atr':None,'hour_close':hc,'two_hour_close':tc,'shock_return':None,'shock_sigma':None,'channel_upper':None,'channel_lower':None,'channel_midpoint':None,'trail_midpoint':None,'noise_upper':None,'noise_lower':None,'vwap':qsum/bsum if bsum>0 and dayopen is not None else None,'noise_check':known%1800000==0}
        if hc:
            high=max(x.high for x in bars15[i-3:i+1]); low=min(x.low for x in bars15[i-3:i+1])
            if prev_hour is not None:
                trs.append(max(high-low,abs(high-prev_hour),abs(low-prev_hour)))
                if len(trs)==p.atr_hours: atr=sum(trs)/len(trs)
            prev_hour=b.close
            if len(hourly)>=p.channel_hours:
                h=max(hourly[-p.channel_hours:]); l=min(hourly[-p.channel_hours:])
                if h>l: f.update(channel_upper=h,channel_lower=l,channel_midpoint=(h+l)/2)
            hourly.append(b.close)
            if len(hourly)>=p.channel_hours:
                h=max(hourly[-p.channel_hours:]); l=min(hourly[-p.channel_hours:]); f['trail_midpoint']=(h+l)/2
        f['atr']=atr if atr is not None and atr>0 else None
        if tc:
            if prev_two is not None:
                r=b.close/prev_two-1; f['shock_return']=r
                if len(returns)==p.shock_returns: f['shock_sigma']=statistics.stdev(returns)
                returns.append(r)
            prev_two=b.close
        offset=len(daybars)-1
        if dayopen is not None and prevdayclose is not None and all(day-j in days for j in range(1,p.noise_days+1)):
            m=sum(abs(days[day-j][1][offset]/days[day-j][0]-1) for j in range(1,p.noise_days+1))/p.noise_days
            u=max(dayopen,prevdayclose)*(1+m); l=min(dayopen,prevdayclose)*(1-m)
            if l>0 and u>l: f['noise_upper']=u; f['noise_lower']=l
        out.append(f)
    return out

def detect(bars15, features, approach, p=ModelParameters()):
    validate_bars(bars15,15)
    if approach not in APPROACHES or len(features)!=len(bars15): raise ValueError('Invalid detector inputs')
    signals=[]; events=[]
    for i,(b,f) in enumerate(zip(bars15,features)):
        if f.get('known_at')!=b.t+STEP: raise ValueError('Feature timing mismatch')
        d=0; stop=None; hold=360; eligible=False
        if approach=='shock_reversal_2h' and f['two_hour_close']:
            eligible=True; r=f['shock_return']; s=f['shock_sigma']
            if r is not None and s is not None and s>0 and r and abs(r)>=p.shock_multiple*s: d=-1 if r>0 else 1
            hold=120
        elif approach=='utc_noise_momentum' and f['noise_check'] and 1800000 <= (f['known_at']-1)%DAY+1 <= 64800000:
            eligible=True; u=f['noise_upper']; l=f['noise_lower']; v=f['vwap']
            if u is not None and l is not None and v is not None: d=1 if b.close>u and b.close>v else -1 if b.close<l and b.close<v else 0
        elif approach=='close_channel_24h' and f['hour_close']:
            eligible=True; u=f['channel_upper']; l=f['channel_lower']
            if u is not None and l is not None: d=1 if b.close>u else -1 if b.close<l else 0
            stop=f['channel_midpoint']
        elif approach.startswith('clock_6h_') and f['known_at']%21600000==0:
            eligible=True; hold=120
            d=1 if approach=='clock_6h_long' else -1 if approach=='clock_6h_short' else (1 if (f['known_at']//3600000)%24 in (0,12) else -1)
        if d and approach!='close_channel_24h':
            if f['atr'] is None: d=0; events.append({'index':i,'known_at':f['known_at'],'kind':'unavailable_feature','feature':'atr'})
            else: stop=b.close-d*2*f['atr']
        if d:
            s=Intent(i,d,stop,hold,approach); signals.append(s)
            events.append({'index':i,'known_at':f['known_at'],'kind':'raw_signal','direction':d,'stop':stop,'cost_admitted':cost_admitted(b.close,stop,d)})
        elif eligible and ((approach=='shock_reversal_2h' and (f['shock_return'] is None or f['shock_sigma'] is None)) or (approach=='utc_noise_momentum' and (f['noise_upper'] is None or f['vwap'] is None)) or (approach=='close_channel_24h' and f['channel_upper'] is None)):
            events.append({'index':i,'known_at':f['known_at'],'kind':'unavailable_feature'})
    return signals,events

