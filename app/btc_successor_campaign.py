"""Run the fixed 120-evaluation BTC successor comparison from local data."""
import argparse
import gzip
import json
import re
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from app.btc_liquidity import Execution
from app.btc_liquidity_data import load_candles, load_funding, resample_15m
from app.btc_liquidity_campaign import sha, write_json, timestamp, combined, qualifies
from app.btc_successor import APPROACHES, ModelParameters, build_features, cost_admitted, detect
from app.btc_successor_data import load_quote_turnover
from app.btc_successor_broker import simulate

ADMIN_HASHES={'protocol.json':'6027e1be528e882f84fd8c370458d2a3b680b9d33332418860d8816a438136a5','INPUT_IDENTITIES.json':'325d6aafe044f057999d0c6aee1e591b8ec886d5e004381a9d57856a5a001dd6','AUTHORIZATION.json':'e75a9c2a1c9360d254949b7bdba689a0db848370f6922130a872b9e1bddd47b1'}

def _validate(protocol):
    if protocol['execution']!=asdict(Execution(funding_mark_buffer_fraction=.01)) or protocol['stress_slip_bps']!=4.0 or protocol['data_root']!='artifacts/strategy-development/btc-liquidity-20261023/raw' or protocol['screen']!={'positive_years':[2025,2026],'minimum_recent_total_closed_trades':100,'minimum_each_recent_closed_trades':30,'minimum_combined_profit_factor':1.05,'maximum_fold_close_drawdown_pct':10.0,'recent_stress_net_positive':True}: raise ValueError('Unsupported frozen protocol')

def comparison(root: Path, run_id: str)->Path:
    root=Path(root)
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',run_id) or run_id in ('.','..'): raise ValueError('Invalid run id')
    for name,digest in ADMIN_HASHES.items():
        if sha(root/name)!=digest: raise ValueError(f'Changed administrative identity: {name}')
    protocol=json.loads((root/'protocol.json').read_text(encoding='utf-8')); _validate(protocol)
    expected=json.loads((root/'INPUT_IDENTITIES.json').read_text(encoding='utf-8'))
    for name,digest in expected.items():
        if sha(Path(name))!=digest: raise ValueError(f'Changed source identity: {name}')
    raw=Path(protocol['data_root']); paths=[root/name for name in ADMIN_HASHES]+[Path(name) for name in expected]+[Path('app')/f'btc_successor{suffix}.py' for suffix in ('','_data','_broker','_campaign','_tests')]+sorted(raw.glob('*.json'))
    before={str(path):sha(path) for path in paths}; out=root/'runs'/run_id; out.mkdir(parents=True,exist_ok=False)
    write_json(out/'identities_before_run.json',before); completed=0; rows=[]; write_json(out/'progress.json',{'status':'RUNNING','completed':0,'expected':120})
    try:
        bars5=load_candles(raw); quotes=load_quote_turnover(raw,bars5); bars=resample_15m(bars5); funding=load_funding(raw); end=int(datetime(2026,9,1,tzinfo=UTC).timestamp()*1000)
        if len(bars5)!=490752 or len(bars)!=163584 or len(funding)!=5112 or bars5[0].t!=timestamp(2022) or bars5[-1].t+300000!=end or any(not timestamp(2022)<=f['ts']<end for f in funding): raise ValueError('Development extent/count mismatch')
        write_json(out/'data_audit.json',{'raw_bars':len(bars5),'bars15':len(bars),'funding_events':len(funding),'start':bars5[0].t,'end_exclusive':bars5[-1].t+300000,'zero_base_rows':sum(b.volume==0 for b in bars5),'turnover_rows':len(quotes),'archive_checksums':'verified by local audited loader and turnover adapter','manifest_sha256':sha(raw/'manifest.json')})
        quote15=[sum(quotes[i:i+3]) for i in range(0,len(quotes),3)]; features=build_features(bars,quote15)
        with gzip.open(out/'features.json.gz','wt',encoding='utf-8',compresslevel=1) as f: json.dump(features,f,separators=(',',':'),allow_nan=False)
        for approach in APPROACHES:
            signals,events=detect(bars,features,approach)
            with gzip.open(out/f'detector-{approach}.json.gz','wt',encoding='utf-8',compresslevel=1) as f: json.dump({'signals':[asdict(s) for s in signals],'events':events},f,separators=(',',':'),allow_nan=False)
            directions=('long','short','both') if not approach.startswith('clock_') else ('both',)
            for direction in directions:
                trial=f'{approach}-{direction}'; row={'id':trial,'approach':approach,'direction':direction,'control':approach.startswith('clock_'),'detector_funnel':dict(Counter(x['kind'] for x in events)),'base':{},'stress':{}}; rows.append(row)
                for year in range(2022,2027):
                    start=timestamp(year); stop=min(timestamp(year+1),end); left=(start-bars[0].t)//900000; right=(stop-bars[0].t)//900000
                    part=bars[left:right]; fs=features[left:right]; ss=[replace(s,index=s.index-left) for s in signals if left<=s.index<right]; ff=[x for x in funding if start<=x['ts']<stop]
                    def ready(f):
                        if approach=='shock_reversal_2h': return f['two_hour_close'] and f['shock_return'] is not None and f['shock_sigma'] is not None and f['shock_sigma']>0 and f['atr'] is not None
                        if approach=='utc_noise_momentum': return f['noise_check'] and 1800000<=(f['known_at']-1)%86400000+1<=64800000 and f['noise_upper'] is not None and f['vwap'] is not None and f['atr'] is not None
                        if approach=='close_channel_24h': return f['hour_close'] and f['channel_upper'] is not None
                        return f['known_at']%21600000==0 and f['atr'] is not None
                    row.setdefault('first_eligible_by_year',{})[str(year)]=next((f['known_at'] for f in fs if ready(f)),None)
                    for condition in ('base','stress'):
                        ex=Execution(funding_mark_buffer_fraction=.01,slip_bps=2.0 if condition=='base' else 4.0)
                        result=simulate(part,ss,fs,approach,direction,ff,ex); row[condition][str(year)]=result['metrics']; eligible_intents=[s for s in ss if (direction=='both' or (direction=='long' and s.direction==1) or (direction=='short' and s.direction==-1)) and cost_admitted(part[s.index].close,s.stop,s.direction)]; row.setdefault('first_direction_and_signal_cost_admitted_known_at',{})[str(year)]=part[eligible_intents[0].index].t+900000 if eligible_intents else None; fills=[t['entry_at'] for t in result['trades']]; fills += [result['open_position']['entry_at']] if result['open_position'] else []; row.setdefault('first_filled_entry_at',{}).setdefault(condition,{})[str(year)]=min(fills) if fills else None; row.setdefault('first_raw_by_year',{})[str(year)]=next((bars[s.index].t+900000 for s in signals if left<=s.index<right),None); saved=out/f'{trial}-{year}-{condition}.json.gz'
                        with gzip.open(saved,'wt',encoding='utf-8',compresslevel=1) as f: json.dump(result,f,separators=(',',':'),allow_nan=False)
                        entry={'trial_id':trial,'year':year,'condition':condition,'artifact':saved.name,'sha256':sha(saved),'metrics':result['metrics'],'parameters':asdict(ModelParameters()),'execution':asdict(ex),'identities':before}
                        with (out/'trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(entry,allow_nan=False)+'\n')
                        with (root/'cumulative_trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'campaign_id':protocol['campaign_id'],'run_id':run_id,**entry},allow_nan=False)+'\n')
                        completed+=1; write_json(out/'comparison.partial.json',rows); write_json(out/'progress.json',{'status':'RUNNING','completed':completed,'expected':120,'last':saved.name})
                row['combined']=combined(list(row['base'].values())); row['qualified'],row['screen_failures']=qualifies(row,protocol)
                if row['control']: row['qualified']=False; row['screen_failures'].append('benchmark only; ineligible for selection')
        if completed!=120 or len(rows)!=12 or sum(not x['control'] for x in rows)!=9: raise ValueError('Incomplete matrix')
        after={str(path):sha(path) for path in paths}; write_json(out/'identities_after_run.json',after)
        if after!=before: raise ValueError('Input identities changed during run')
        candidates=[r for r in rows if not r['control']]; controls=[r for r in rows if r['control']]; eligible=sorted((r for r in candidates if r['qualified']),key=lambda r:(-r['combined']['worst_fold_return_pct'],-r['combined']['mean_fold_return_pct'],r['id']))
        summary={'campaign_id':protocol['campaign_id'],'run_id':run_id,'status':'PASS_TO_PHASE_3' if eligible else 'RETURN_TO_PHASE_1','selected':eligible[0]['id'] if eligible else None,'completed_annual_runs':completed,'candidates':candidates,'controls':controls,'cash_benchmark':protocol['cash_benchmark'],'chronology':protocol['chronology'],'timing_definitions':{'first_eligible_by_year':'first closed observation with all model features available, before signal or direction filtering','first_raw_by_year':'first raw signal known-at in the fold before direction and cost filtering','first_direction_and_signal_cost_admitted_known_at':'first raw signal known-at in the fold matching the context direction and passing signal-close cost admission; no portfolio or fill eligibility implied','first_filled_entry_at':'earliest actual entry timestamp per fold and cost condition, including a position censored open at cutoff'},'identities':before,'prior_exposure':'690 prior economic evaluations including 240 validation replays; 33 prior candidate contexts (18 liquidity and 15 SMC) excluding 12 benchmark contexts, not independent discoveries','limitations':'OHLC fills and funding proxies are research assumptions; screening is exposed, not out of sample; no live execution or source replication claimed.'}
        write_json(out/'comparison.json',summary)
        (out/'REPORT.md').write_text('# BTC successor comparison\n\n'+f"Status: {summary['status']}; selected: {summary['selected'] or 'none'}.\n\n"+summary['limitations']+'\n\n'+ '\n'.join(f"- {r['id']}: worst {r['combined']['worst_fold_return_pct']:.3f}%, mean {r['combined']['mean_fold_return_pct']:.3f}%; failures: {'; '.join(r['screen_failures']) or 'none'}" for r in rows)+'\n',encoding='utf-8')
        write_json(out/'progress.json',{'status':'COMPLETE','completed':completed,'expected':120}); return out
    except Exception as exc:
        write_json(out/'progress.json',{'status':'FAILED','completed':completed,'expected':120,'error':str(exc)}); raise
    finally:
        write_json(out/'identities_after_run.json',{str(path):sha(path) if path.exists() else None for path in paths})

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',required=True,type=Path); parser.add_argument('--run-id',required=True); args=parser.parse_args(); print(comparison(args.root,args.run_id))
if __name__=='__main__': main()
