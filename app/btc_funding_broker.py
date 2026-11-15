"""Fixed-notional, causal long broker for funding-state research."""
import math
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from app.btc_liquidity import validate_bars
from app.btc_funding import APPROACHES, DAY, SLOT, FundingExecution

def simulate(bars, signals, minutes, approach, funding, e=FundingExecution()):
    validate_bars(bars,minutes)
    if minutes not in (5,15) or approach not in APPROACHES: raise ValueError('Invalid broker inputs')
    if any(not math.isfinite(v) or v<=0 for v in (e.initial_capital,e.entry_notional_fraction,e.quantity_step,e.min_quantity,e.max_quantity,e.min_notional)) or e.entry_notional_fraction>1 or e.min_quantity>e.max_quantity or any(not math.isfinite(v) or v<0 for v in (e.fee_bps,e.slip_bps,e.funding_mark_buffer_fraction)) or e.slip_bps>=10000 or e.funding_mark_buffer_fraction>=1: raise ValueError('Invalid execution settings')
    step=minutes*60000; start=bars[0].t; end=bars[-1].t+step
    by_decision={}; seen=set(); funding_ts=set()
    for j,f in enumerate(funding):
        try: ts=f['ts']; rate=f['rate']; mark=f['mark']
        except (KeyError,TypeError) as exc: raise ValueError('Invalid funding') from exc
        if type(ts) is not int or not start<=ts<end or (j and ts<=funding[j-1]['ts']) or not math.isfinite(rate) or not math.isfinite(mark) or mark<=0: raise ValueError('Invalid funding')
        funding_ts.add(ts)
    if approach==APPROACHES[2] and len(signals)>1: raise ValueError('Continuous control accepts at most one signal')
    for s in signals:
        if type(s.index) is not int or not 0<=s.index<len(bars) or type(s.event_ts) is not int or s.event_ts not in funding_ts or s.event_ts in seen: raise ValueError('Invalid intent ownership')
        seen.add(s.event_ts); obs=((s.event_ts+1)//step+1)*step
        if s.observation_at!=obs or bars[s.index].t+step!=obs or s.decision_at!=obs+1 or s.fill_at!=obs+step or s.reason!=approach or s.hold_minutes!=(None if approach==APPROACHES[2] else 1440): raise ValueError('Invalid intent clock')
        if type(s.source_event_ts) is not int or (s.source_event_ts!=s.event_ts if approach!=APPROACHES[1] else s.source_event_ts//SLOT!=s.event_ts//SLOT-21): raise ValueError('Invalid source event')
        by_decision.setdefault(s.index+1,[]).append(s)
    cash=e.initial_capital; fee=e.fee_bps/10000; slip=e.slip_bps/10000; pos=None; pending={}; trades=[]; curve=[]; ledger=[]; counts=Counter(); days=set(); fi=0; peak=cash; dd=0.; adverse_dd=0.; exposed=0; notional_days=0.; invalid=False
    def log(i,kind,**data): ledger.append({'bar_index':i,'kind':kind,**data})
    def mark(raw):
        if pos is None: return cash,0.,0.
        price=raw*(1-slip); estimated_fee=price*pos['quantity']*fee; estimated_slip=raw*pos['quantity']*slip
        return cash+pos['quantity']*(price-pos['entry'])-estimated_fee,estimated_fee,estimated_slip
    def fund(i,f):
        nonlocal cash
        if pos:
            nominal=-pos['quantity']*f['mark']*f['rate']; amount=nominal-abs(nominal)*e.funding_mark_buffer_fraction
            cash+=amount; pos['funding']+=amount; log(i,'funding',at=f['ts'],amount=amount,nominal=nominal)
    def close(i,raw,at):
        nonlocal cash,pos
        q=pos['quantity']; price=raw*(1-slip); exit_fee=price*q*fee; gross=q*(price-pos['entry']); raw_pnl=q*(raw-pos['raw_entry']); cash+=gross-exit_fee
        trade={**pos,'exit':price,'raw_exit':raw,'exit_index':i,'exit_at':at,'exit_fee':exit_fee,'gross_pnl':gross,'raw_price_pnl':raw_pnl,'net_pnl':gross-pos['entry_fee']-exit_fee+pos['funding'],'reason':'time_exit'}
        trades.append(trade); counts['time_exit']+=1; log(i,'exit',at=at,net_pnl=trade['net_pnl'],raw_price=raw,price=price); pos=None
    for i,b in enumerate(bars):
        carried=pos is not None; carried_equity=mark(b.open)[0]
        while fi<len(funding) and funding[fi]['ts']==b.t: fund(i,funding[fi]); fi+=1
        if cash<0:
            marked,est_fee,est_slip=mark(b.open); invalid=True; counts['invalid_execution']+=1
            curve.append({'t':b.t,'cash':cash,'equity':marked,'adverse_equity':min(marked,carried_equity),'quantity':pos['quantity'] if pos else 0.,'notional_at_open':0.,'notional_days_increment':0.,'estimated_exit_fee':est_fee,'estimated_exit_slippage':est_slip})
            log(i,'invalid_execution',at=b.t,cash=cash,equity=marked); break
        if pos and pos['deadline'] is not None and b.t>=pos['deadline']: close(i,b.open,b.t)
        for s in pending.pop(i,[]):
            if carried or pos is not None:
                counts['occupied_at_open']+=1; log(i,'entry_rejected',at=b.t,reason='occupied_at_open',signal_index=s.index); continue
            entry=b.open*(1+slip); qty=math.floor(min(e.entry_notional_fraction*cash/(entry*(1+fee)),e.max_quantity)/e.quantity_step+1e-9)*e.quantity_step
            if qty<e.min_quantity or qty*entry<e.min_notional:
                counts['size_rejected']+=1; log(i,'entry_rejected',at=b.t,reason='size_rejected',quantity=qty,signal_index=s.index); continue
            entry_fee=entry*qty*fee; cash-=entry_fee
            pos={'entry':entry,'raw_entry':b.open,'entry_index':i,'entry_at':b.t,'signal_index':s.index,'event_ts':s.event_ts,'source_event_ts':s.source_event_ts,'observation_at':s.observation_at,'decision_at':s.decision_at,'fill_at':s.fill_at,'quantity':qty,'entry_fee':entry_fee,'funding':0.,'deadline':b.t+s.hold_minutes*60000 if s.hold_minutes is not None else None,'reason_entry':s.reason}
            counts['filled']+=1; log(i,'filled',**pos)
        for s in by_decision.get(i,[]):
            log(i,'raw_signal',**asdict(s))
            if pos is not None: counts['occupied_at_decision']+=1; log(i,'suppressed',at=s.decision_at,signal_index=s.index,reason='occupied_at_decision')
            else: pending.setdefault(i+1,[]).append(s); counts['queued']+=1; log(i,'queued',at=s.decision_at,fill_at=s.fill_at,signal_index=s.index)
        q=pos['quantity'] if pos else 0.; increment=q*b.open*step/DAY; notional_days+=increment
        if pos: exposed+=1; days.add(b.t//DAY)
        pre=cash
        while fi<len(funding) and funding[fi]['ts']<b.t+step:
            fund(i,funding[fi]); fi+=1
            if cash<0: break
        marked,est_fee,est_slip=mark(b.close)
        if pos:
            low=b.low*(1-slip); worst=min(pre,cash)+q*(low-pos['entry'])-low*q*fee
        else: worst=cash
        worst=min(worst,marked,carried_equity); adverse_dd=max(adverse_dd,(peak-worst)/peak*100); peak=max(peak,marked); dd=max(dd,(peak-marked)/peak*100)
        curve.append({'t':b.t+step,'cash':cash,'equity':marked,'adverse_equity':worst,'quantity':q,'notional_at_open':q*b.open,'notional_days_increment':increment,'estimated_exit_fee':est_fee,'estimated_exit_slippage':est_slip})
        if not all(math.isfinite(v) for v in (cash,marked,worst,notional_days)) or cash<0 or marked<=0 or worst<=0:
            invalid=True; counts['invalid_execution']+=1; log(i,'invalid_execution',at=b.t+step,cash=cash,equity=marked,adverse_equity=worst); break
    if not invalid:
        for idx in (len(bars),len(bars)+1):
            for s in by_decision.get(idx,[]): counts['censored_intent']+=1; log(len(bars)-1,'censored_intent',**asdict(s))
            for s in pending.get(idx,[]): counts['censored_intent']+=1; log(len(bars)-1,'censored_intent',**asdict(s))
        if pos: counts['censored_position']+=1; log(len(bars)-1,'censored_position',at=end,position=dict(pos))
    wins=sum(max(t['net_pnl'],0) for t in trades); losses=-sum(min(t['net_pnl'],0) for t in trades); week=Counter()
    for t in trades:
        dt=datetime.fromtimestamp(t['entry_at']/1000,UTC); monday=(dt-timedelta(days=dt.weekday())).strftime('%Y-%m-%d'); week[monday]+=t['net_pnl']
    marked=curve[-1]['equity']; est_fee=curve[-1]['estimated_exit_fee']; est_slip=curve[-1]['estimated_exit_slippage']; allpos=trades+([pos] if pos else [])
    metrics={'net_return_pct':(marked/e.initial_capital-1)*100,'net_profit':marked-e.initial_capital,'marked_equity':marked,'closed_trades':len(trades),'profit_factor':wins/losses if losses else None,'gross_profit':wins,'gross_loss':losses,'closed_net_pnl':sum(t['net_pnl'] for t in trades),'closed_gross_pnl':sum(t['gross_pnl'] for t in trades),'closed_raw_price_pnl':sum(t['raw_price_pnl'] for t in trades),'fees':sum(t['entry_fee']+t.get('exit_fee',0) for t in allpos),'funding':sum(t['funding'] for t in allpos),'executed_slippage':sum(t['quantity']*(abs(t['entry']-t['raw_entry'])+abs(t.get('exit',t['entry'])-t.get('raw_exit',t['entry']))) for t in allpos),'estimated_exit_fee':est_fee,'estimated_exit_slippage':est_slip,'max_drawdown_pct':dd,'adverse_drawdown_pct':adverse_dd,'counts':dict(counts),'active_days':len(days),'exposed_bars':exposed,'exposure_fraction':exposed/len(bars),'notional_days':notional_days,'net_bps_per_notional_day':10000*(marked-e.initial_capital)/notional_days if notional_days else None,'entry_week_net_pnl':dict(week)}
    return {'status':'INVALID_EXECUTION' if invalid else 'OK','metrics':metrics,'trades':trades,'equity':curve,'ledger':ledger,'open_position':pos,'execution':asdict(e),'approach':approach}
