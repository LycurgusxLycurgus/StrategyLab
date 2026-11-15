"""Causal OHLC broker for fixed flow-reversal research; no order submission."""
import math
from collections import Counter
from dataclasses import asdict
from app.btc_liquidity import Execution, DIRECTIONS, validate_bars
from app.btc_flow import APPROACHES, DAY, cost_admitted


def simulate(bars, signals, features, minutes, approach, direction, funding, e=Execution(funding_mark_buffer_fraction=.01)):
    validate_bars(bars,minutes)
    if approach not in APPROACHES or direction not in DIRECTIONS or len(features)!=len(bars): raise ValueError('Invalid broker inputs')
    if any(not math.isfinite(v) or v<=0 for v in (e.initial_capital,e.risk_fraction,e.max_notional_fraction,e.tick,e.quantity_step,e.min_quantity,e.max_quantity,e.min_notional)) or e.risk_fraction>1 or e.max_notional_fraction>1 or any(not math.isfinite(v) or v<0 for v in (e.fee_bps,e.slip_bps)) or not 0<=e.funding_mark_buffer_fraction<1: raise ValueError('Invalid execution settings')
    step=minutes*60000; intents={}
    for s in signals:
        if type(s.index)!=int or not 0<=s.index<len(bars) or s.direction not in (-1,1) or not math.isfinite(s.stop) or s.stop<=0 or not math.isfinite(s.anchor) or s.anchor<=0 or s.hold_minutes!=120: raise ValueError('Invalid intent')
        intents.setdefault(s.index+2,[]).append(s)
    for i,f in enumerate(features):
        if f.get('known_at')!=bars[i].t+step: raise ValueError('Feature timing mismatch')
    for i,f in enumerate(funding):
        if type(f['ts'])!=int or (i and f['ts']<=funding[i-1]['ts']) or not math.isfinite(f['rate']) or not math.isfinite(f['mark']) or f['mark']<=0: raise ValueError('Invalid funding')
    cash=e.initial_capital; fee=e.fee_bps/10000; slip=e.slip_bps/10000; pos=None; trades=[]; curve=[]; ledger=[]; counts=Counter(); entries=Counter(); filled=Counter(); fi=0; peak=cash; adverse_dd=0; exposed=0; days=set()
    def log(i,kind,**kw): ledger.append({'bar_index':i,'t':bars[i].t,'kind':kind,**kw})
    def fund(i,f,uncertain=False):
        nonlocal cash
        if pos is None: return
        amount=-pos['direction']*pos['quantity']*f['mark']*f['rate']; amount-=abs(amount)*e.funding_mark_buffer_fraction
        if uncertain: amount=min(amount,0.)
        cash+=amount; pos['funding']+=amount; log(i,'funding',at=f['ts'],amount=amount,uncertain_exit_order=uncertain)
    def close(i,raw,reason,at):
        nonlocal cash,pos
        d=pos['direction']; q=pos['quantity']; price=raw*(1-d*slip); exit_fee=price*q*fee; gross=d*q*(price-pos['entry']); cash+=gross-exit_fee
        net=gross-pos['entry_fee']-exit_fee+pos['funding']; trades.append({**pos,'exit':price,'raw_exit':raw,'exit_index':i,'exit_at':at,'exit_fee':exit_fee,'gross_pnl':gross,'net_pnl':net,'reason':reason}); counts[reason]+=1
        log(i,'exit',at=at,reason=reason,raw_price=raw,price=price,net_pnl=net); pos=None
    while fi<len(funding) and funding[fi]['ts']<bars[0].t: fi+=1
    by_signal = {}
    for signal in signals: by_signal.setdefault(signal.index, []).append(signal)
    for i,b in enumerate(bars):
        for s in by_signal.get(i, []):
            log(i, 'raw_signal', signal_index=i, known_at=b.t+step, legal_after=b.t+step+1, expected_fill_at=b.t+2*step, direction=s.direction, stop=s.stop, anchor=s.anchor)
        carried=pos is not None; carried_equity=cash+(pos['direction']*pos['quantity']*(b.open-pos['entry']) if pos else 0)
        while fi<len(funding) and funding[fi]['ts']<=b.t: fund(i,funding[fi]); fi+=1
        if pos and (b.open<=pos['stop'] if pos['direction']==1 else b.open>=pos['stop']): close(i,b.open,'stop_gap',b.t)
        if pos and b.t>=pos['deadline']: close(i,b.open,'flat_exit' if b.t%DAY==1425*60000 else 'time_exit',b.t)
        if pos and (b.open>=pos['anchor'] if pos['direction']==1 else b.open<=pos['anchor']): close(i,pos['anchor'],'anchor_gap',b.t)
        for s in intents.get(i,[]):
            known=bars[s.index].t+step; log(i,'submission',signal_index=s.index,known_at=known,legal_after=known+1,expected_fill_at=b.t,direction=s.direction,stop=s.stop,anchor=s.anchor)
            reason=None
            if s.direction not in DIRECTIONS[direction]: reason='direction_excluded'
            elif not cost_admitted(bars[s.index].close,s.stop,s.direction): reason='signal_cost_guard'
            elif b.t//DAY != bars[s.index].t//DAY or b.t%DAY>1320*60000: reason='entry_time_reject'
            elif carried or pos is not None: reason='occupied_at_open'
            elif entries[b.t//DAY]>=4: reason='daily_entry_cap'
            else:
                d=s.direction; entry=b.open*(1+d*slip); stop=(math.floor(s.stop/e.tick+1e-9) if d==1 else math.ceil(s.stop/e.tick-1e-9))*e.tick
                if not cost_admitted(entry,stop,d): reason='fill_cost_guard'
                elif d*(s.anchor-entry) + 1e-12*max(entry,1) < .006*entry: reason='anchor_room_reject'
                else:
                    stopped=stop*(1-d*slip); risk=d*(entry-stopped)+fee*(entry+stopped)
                    desired=min(cash*e.risk_fraction/risk,cash*e.max_notional_fraction/(entry*(1+fee)),e.max_quantity) if cash>0 and risk>0 else 0
                    qty=math.floor(desired/e.quantity_step+1e-9)*e.quantity_step
                    if qty<e.min_quantity or qty*entry<e.min_notional: reason='size_rejected'
                    else:
                        deadline=min(b.t+120*60000,(b.t//DAY)*DAY+1425*60000); entry_fee=entry*qty*fee
                        pos={'entry':entry,'raw_entry':b.open,'entry_index':i,'entry_at':b.t,'signal_index':s.index,'known_at':known,'legal_after':known+1,'direction':d,'quantity':qty,'initial_stop':stop,'stop':stop,'anchor':s.anchor,'entry_fee':entry_fee,'funding':0.,'initial_risk':qty*risk,'entry_equity':cash,'deadline':deadline,'reason_entry':s.reason}
                        cash-=entry_fee; entries[b.t//DAY]+=1; filled['long' if d==1 else 'short']+=1; counts['filled']+=1; log(i,'filled',**pos)
            if reason: counts[reason]+=1; log(i,'entry_rejected',reason=reason,signal_index=s.index,at=b.t)
        worst=cash
        if pos:
            exposed+=1; days.add(b.t//DAY); d=pos['direction']; q=pos['quantity']; stop=pos['stop']; anchor=pos['anchor']
            stop_hit=b.low<=stop if d==1 else b.high>=stop; target_hit=b.high>=anchor if d==1 else b.low<=anchor
            while fi<len(funding) and funding[fi]['ts']<b.t+step: fund(i,funding[fi],stop_hit or target_hit); fi+=1
            adverse=stop if stop_hit else (b.low if d==1 else b.high); worst=cash+d*q*(adverse-pos['entry'])-adverse*q*fee
            if stop_hit: close(i,stop,'stop',b.t+step)
            elif target_hit: close(i,anchor,'anchor',b.t+step)
        else:
            while fi<len(funding) and funding[fi]['ts']<b.t+step: fi+=1
        marked=cash
        if pos: marked+=pos['direction']*pos['quantity']*(b.close-pos['entry'])-b.close*pos['quantity']*fee
        adverse_dd=max(adverse_dd,(peak-min(worst,marked,carried_equity))/peak*100); peak=max(peak,marked)
        curve.append({'t':b.t+step,'equity':marked,'cash':cash,'quantity':pos['quantity']*pos['direction'] if pos else 0.,'notional':pos['quantity']*b.close if pos else 0.,'adverse_equity':min(worst,marked,carried_equity)})
    for idx in (len(bars),len(bars)+1):
        for s in intents.get(idx,[]):
            reason='direction_excluded' if s.direction not in DIRECTIONS[direction] else 'signal_cost_guard' if not cost_admitted(bars[s.index].close,s.stop,s.direction) else 'censored_intent'
            counts[reason]+=1; log(len(bars)-1,reason,signal_index=s.index,known_at=bars[s.index].t+step,legal_after=bars[s.index].t+step+1,expected_fill_at=bars[s.index].t+2*step,direction=s.direction)
    if pos: counts['censored_position']+=1; log(len(bars)-1,'censored_position',at=bars[-1].t+step,position=pos)
    wins=sum(max(t['net_pnl'],0) for t in trades); losses=-sum(min(t['net_pnl'],0) for t in trades); cp=e.initial_capital; dd=0
    for point in curve: cp=max(cp,point['equity']); dd=max(dd,(cp-point['equity'])/cp*100)
    daily=Counter()
    for t in trades: daily[t['exit_at']//DAY]+=t['net_pnl']
    metrics={'active_days':len(days),'exposed_bars':exposed,'exposure_fraction':exposed/len(bars),'filled_direction_counts':dict(filled),'largest_winning_days':sorted((v for v in daily.values() if v>0),reverse=True)[:10],'net_return_pct':(curve[-1]['equity']/e.initial_capital-1)*100,'closed_trades':len(trades),'wins':sum(t['net_pnl']>0 for t in trades),'profit_factor':wins/losses if losses else None,'gross_profit':wins,'gross_loss':losses,'closed_net_pnl':sum(t['net_pnl'] for t in trades),'closed_gross_pnl':sum(t['gross_pnl'] for t in trades),'fees':sum(t['entry_fee']+t['exit_fee'] for t in trades)+(pos['entry_fee'] if pos else 0),'funding':sum(t['funding'] for t in trades)+(pos['funding'] if pos else 0),'slippage':sum(t['quantity']*(abs(t['entry']-t['raw_entry'])+abs(t['exit']-t['raw_exit'])) for t in trades)+(pos['quantity']*abs(pos['entry']-pos['raw_entry']) if pos else 0),'max_drawdown_pct':dd,'adverse_drawdown_pct':adverse_dd,'marked_equity':curve[-1]['equity'],'counts':dict(counts),'entry_days':len(entries),'direction_counts':{'long':sum(t['direction']==1 for t in trades),'short':sum(t['direction']==-1 for t in trades)}}
    return {'metrics':metrics,'trades':trades,'equity':curve,'ledger':ledger,'open_position':pos,'execution':asdict(e),'approach':approach,'funding_policy':'exact-open carried ownership; uncertain intrabar debit charged and credit omitted; no funding after deterministic open exit'}
