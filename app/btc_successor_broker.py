"""Bounded successor OHLC broker with causal amendments and cutoff censoring."""
import math
from collections import Counter
from dataclasses import asdict
from app.btc_liquidity import Execution, DIRECTIONS, validate_bars
from app.btc_successor import APPROACHES, STEP, DAY, cost_admitted

def simulate(bars15, signals, features, approach, direction, funding, e=Execution(funding_mark_buffer_fraction=.01)):
    validate_bars(bars15,15)
    if approach not in APPROACHES or direction not in DIRECTIONS or len(features)!=len(bars15): raise ValueError('Invalid broker inputs')
    if any(not math.isfinite(v) or v<=0 for v in (e.initial_capital,e.risk_fraction,e.max_notional_fraction,e.tick,e.quantity_step,e.min_quantity,e.max_quantity,e.min_notional)) or e.risk_fraction>1 or e.max_notional_fraction>1 or any(not math.isfinite(v) or v<0 for v in (e.fee_bps,e.slip_bps)) or not math.isfinite(e.funding_mark_buffer_fraction) or not 0<=e.funding_mark_buffer_fraction<1: raise ValueError('Invalid execution settings')
    intents={}
    for s in signals:
        if type(s.index)!=int or not 0<=s.index<len(bars15) or s.direction not in (-1,1) or not math.isfinite(s.stop) or type(s.hold_minutes)!=int or s.hold_minutes<=0 or s.hold_minutes%15: raise ValueError('Invalid intent')
        intents.setdefault(s.index+1,[]).append(s)
    for i,f in enumerate(features):
        if f.get('known_at')!=bars15[i].t+STEP: raise ValueError('Feature timing mismatch')
    for i,f in enumerate(funding):
        if type(f['ts'])!=int or (i and f['ts']<=funding[i-1]['ts']) or not math.isfinite(f['rate']) or not math.isfinite(f['mark']) or f['mark']<=0: raise ValueError('Invalid funding')
    cash=e.initial_capital; fee=e.fee_bps/10000; slip=e.slip_bps/10000; pos=None; trades=[]; curve=[]; ledger=[]; counts=Counter(); entries=Counter(); fi=0; peak=cash; adverse_dd=0; queued=None; amendment=None; exposed_bars=0; active_days=set(); filled_directions=Counter()
    def log(i,kind,**kw): ledger.append({'bar_index':i,'t':bars15[i].t,'kind':kind,**kw})
    def fund(i,f,uncertain=False):
        nonlocal cash
        if pos is None: return
        amount=-pos['direction']*pos['quantity']*f['mark']*f['rate']; amount-=abs(amount)*e.funding_mark_buffer_fraction
        if uncertain: amount=min(amount,0.)
        cash+=amount; pos['funding']+=amount; log(i,'funding',at=f['ts'],amount=amount,uncertain_exit_order=uncertain)
    def close(i,raw,reason,at):
        nonlocal cash,pos,queued,amendment
        d=pos['direction']; q=pos['quantity']; price=raw*(1-d*slip); exit_fee=price*q*fee; gross=d*q*(price-pos['entry']); cash+=gross-exit_fee
        net=gross-pos['entry_fee']-exit_fee+pos['funding']; tr={**pos,'exit':price,'raw_exit':raw,'exit_index':i,'exit_at':at,'exit_fee':exit_fee,'gross_pnl':gross,'net_pnl':net,'reason':reason}; trades.append(tr); counts[reason]+=1; log(i,'exit',at=at,reason=reason,raw_price=raw,price=price,net_pnl=net); pos=None; queued=None; amendment=None
    while fi<len(funding) and funding[fi]['ts']<bars15[0].t: fi+=1
    for i,b in enumerate(bars15):
        carried=pos is not None; prior_exit_decision=queued
        carried_equity=cash+(pos['direction']*pos['quantity']*(b.open-pos['entry']) if pos else 0)
        while fi<len(funding) and funding[fi]['ts']<=b.t: fund(i,funding[fi]); fi+=1
        if pos and amendment is not None:
            pos['stop']=amendment; log(i,'amendment_activated',stop=amendment,at=b.t); amendment=None
        if pos and (b.open<=pos['stop'] if pos['direction']==1 else b.open>=pos['stop']): close(i,b.open,'stop_gap',b.t)
        if pos and (queued or b.t>=pos['deadline']): close(i,b.open,queued or 'time_exit',b.t)
        for s in intents.get(i,[]):
            known=bars15[s.index].t+STEP; log(i,'submission',signal_index=s.index,known_at=known,expected_fill_at=b.t,direction=s.direction,stop=s.stop)
            reason=None
            suppressed_by_exit = carried and prior_exit_decision=='noise_exit'
            if suppressed_by_exit: log(i,'same_check_exit_suppression',signal_index=s.index,decision_at=known)
            if s.direction not in DIRECTIONS[direction]: reason='direction_excluded'
            elif not cost_admitted(bars15[s.index].close,s.stop,s.direction): reason='signal_cost_guard'
            elif carried or pos is not None: reason='occupied_at_open'
            elif entries[b.t//DAY]>=4: reason='daily_entry_cap'
            else:
                d=s.direction; entry=b.open*(1+d*slip); stop=(math.floor(s.stop/e.tick+1e-9) if d==1 else math.ceil(s.stop/e.tick-1e-9))*e.tick
                if not cost_admitted(entry,stop,d): reason='fill_cost_guard'
                else:
                    stopped=stop*(1-d*slip); risk=d*(entry-stopped)+fee*(entry+stopped)
                    desired=min(cash*e.risk_fraction/risk,cash*e.max_notional_fraction/(entry*(1+fee)),e.max_quantity) if cash>0 and risk>0 else 0
                    qty=math.floor(desired/e.quantity_step+1e-9)*e.quantity_step
                    if qty<e.min_quantity or qty*entry<e.min_notional: reason='size_rejected'
                    else:
                        deadline=b.t+s.hold_minutes*60000
                        if approach=='utc_noise_momentum': deadline=min(deadline,(b.t//DAY+1)*DAY)
                        entry_fee=entry*qty*fee
                        pos={'entry':entry,'raw_entry':b.open,'entry_index':i,'entry_at':b.t,'signal_index':s.index,'known_at':known,'direction':d,'quantity':qty,'initial_stop':stop,'stop':stop,'entry_fee':entry_fee,'funding':0.,'initial_risk':qty*risk,'entry_equity':cash,'deadline':deadline,'reason_entry':s.reason}
                        cash-=entry_fee; entries[b.t//DAY]+=1; filled_directions['long' if d==1 else 'short']+=1; counts['filled']+=1; log(i,'filled',**pos)
            if reason: counts[reason]+=1; log(i,'entry_rejected',reason=reason,signal_index=s.index,at=b.t)
        worst=cash
        if pos:
            exposed_bars+=1; active_days.add(b.t//DAY)
            d=pos['direction']; q=pos['quantity']; stop=pos['stop']; hit=b.low<=stop if d==1 else b.high>=stop
            # An opening gap for a newly entered position is ruled out by admission.
            while fi<len(funding) and funding[fi]['ts']<b.t+STEP: fund(i,funding[fi],hit); fi+=1
            adverse=stop if hit else (b.low if d==1 else b.high)
            worst=cash+d*q*(adverse-pos['entry'])-adverse*q*fee
            if hit: close(i,stop,'stop',b.t+STEP)
        else:
            while fi<len(funding) and funding[fi]['ts']<b.t+STEP: fi+=1
        marked=cash
        if pos:
            d=pos['direction']; q=pos['quantity']; marked+=d*q*(b.close-pos['entry'])-b.close*q*fee
            f=features[i]
            if approach=='utc_noise_momentum' and f['noise_check'] and f['noise_upper'] is not None and f['noise_lower'] is not None and f['vwap'] is not None:
                if (b.close<=max(f['noise_upper'],f['vwap']) if d==1 else b.close>=min(f['noise_lower'],f['vwap'])):
                    queued='noise_exit'; log(i,'exit_decision',reason=queued,known_at=b.t+STEP,expected_fill_at=b.t+STEP)
            if approach=='close_channel_24h' and f['hour_close'] and f['trail_midpoint'] is not None:
                previous_stop=pos['stop']; unrounded=max(previous_stop,f['trail_midpoint']) if d==1 else min(previous_stop,f['trail_midpoint'])
                proposed=(math.floor(unrounded/e.tick+1e-9) if d==1 else math.ceil(unrounded/e.tick-1e-9))*e.tick
                proposed=max(pos['stop'],proposed) if d==1 else min(pos['stop'],proposed)
                if (b.close<=unrounded if d==1 else b.close>=unrounded): queued='trail_exit'; log(i,'exit_decision',reason=queued,known_at=b.t+STEP,expected_fill_at=b.t+STEP,previous_stop=previous_stop,proposed_stop=unrounded,rounded_stop=proposed)
                elif proposed!=pos['stop']: amendment=proposed; log(i,'amendment_proposed',previous_stop=previous_stop,proposed_stop=unrounded,rounded_stop=proposed,stop=proposed,known_at=b.t+STEP,effective_at=b.t+STEP)
        adverse_dd=max(adverse_dd,(peak-min(worst,marked,carried_equity))/peak*100); peak=max(peak,marked)
        curve.append({'t':b.t+STEP,'equity':marked,'cash':cash,'quantity':pos['quantity']*pos['direction'] if pos else 0.,'notional':pos['quantity']*b.close if pos else 0.,'adverse_equity':min(worst,marked,carried_equity)})
    for s in intents.get(len(bars15),[]):
        reason='direction_excluded' if s.direction not in DIRECTIONS[direction] else 'signal_cost_guard' if not cost_admitted(bars15[s.index].close,s.stop,s.direction) else 'censored_intent'
        counts[reason]+=1; log(len(bars15)-1,reason,signal_index=s.index,known_at=bars15[-1].t+STEP,expected_fill_at=bars15[-1].t+STEP,direction=s.direction)
    if pos: counts['censored_position']+=1; log(len(bars15)-1,'censored_position',at=bars15[-1].t+STEP,position=pos,queued_exit=queued,pending_amendment=amendment)
    wins=sum(max(t['net_pnl'],0) for t in trades); losses=-sum(min(t['net_pnl'],0) for t in trades); cp=e.initial_capital; dd=0
    for point in curve: cp=max(cp,point['equity']); dd=max(dd,(cp-point['equity'])/cp*100)
    daily_pnl=Counter()
    for t in trades: daily_pnl[t['exit_at']//DAY]+=t['net_pnl']
    winning_days=sorted((v for v in daily_pnl.values() if v>0),reverse=True)
    metrics={'active_days':len(active_days),'exposed_bars':exposed_bars,'exposure_fraction':exposed_bars/len(bars15),'filled_direction_counts':dict(filled_directions),'largest_winning_days':winning_days[:10],'net_return_pct':(curve[-1]['equity']/e.initial_capital-1)*100,'closed_trades':len(trades),'wins':sum(t['net_pnl']>0 for t in trades),'profit_factor':wins/losses if losses else None,'gross_profit':wins,'gross_loss':losses,'closed_net_pnl':sum(t['net_pnl'] for t in trades),'closed_gross_pnl':sum(t['gross_pnl'] for t in trades),'fees':sum(t['entry_fee']+t['exit_fee'] for t in trades)+(pos['entry_fee'] if pos else 0),'funding':sum(t['funding'] for t in trades)+(pos['funding'] if pos else 0),'slippage':sum(t['quantity']*(abs(t['entry']-t['raw_entry'])+abs(t['exit']-t['raw_exit'])) for t in trades)+(pos['quantity']*abs(pos['entry']-pos['raw_entry']) if pos else 0),'max_drawdown_pct':dd,'adverse_drawdown_pct':adverse_dd,'marked_equity':curve[-1]['equity'],'counts':dict(counts),'entry_days':len(entries),'direction_counts':{'long':sum(t['direction']==1 for t in trades),'short':sum(t['direction']==-1 for t in trades)}}
    return {'metrics':metrics,'trades':trades,'equity':curve,'ledger':ledger,'open_position':pos,'execution':asdict(e),'approach':approach,'funding_policy':'exact-open carried ownership; uncertain intrabar debit charged and credit omitted; no funding after deterministic open exit'}
