"""Run the preregistered fixed BTC flow comparison from audited local data."""
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
from app.btc_flow import APPROACHES, build_features, detect
from app.btc_flow_data import load_flow, aggregate_flow_15m
from app.btc_flow_broker import simulate

PROTOCOL_SHA256='1995f909f8808c53e65d4e32b7d9b2e7667e2e369659769620d0047e1543bb68'
REQUIRED_SOURCES={'app/btc_flow.py','app/btc_flow_data.py','app/btc_flow_broker.py','app/btc_flow_campaign.py','app/btc_flow_tests.py','app/btc_liquidity.py','app/btc_liquidity_data.py','app/btc_liquidity_campaign.py','app/btc_successor.py'}

def validate_protocol(protocol):
    canonical=Path('artifacts/strategy-development/btc-flow-phase2-20261028/protocol.json')
    if sha(canonical)!=PROTOCOL_SHA256 or protocol != json.loads(canonical.read_text(encoding='utf-8')):
        raise ValueError('Protocol differs from frozen contract')
    if (protocol.get('schema_version')!='btc_flow_phase2_v1' or protocol.get('campaign_id')!='btc-flow-phase2-20261028' or protocol.get('phase2_execution_authorized') is not True or protocol.get('approaches')!=list(APPROACHES) or protocol.get('execution_timeframes_minutes')!=[5,15] or protocol.get('directions')!=['long','short','both'] or protocol.get('execution')!=asdict(Execution(funding_mark_buffer_fraction=.01)) or protocol.get('stress_slip_bps')!=20.0 or protocol.get('budget',{}).get('phase2_economic_evaluations')!=120):
        raise ValueError('Unsupported frozen protocol')
    return True

def screen_rows(rows, protocol):
    if len(rows)!=12: raise ValueError('Incomplete matrix')
    expected={(m,a,d) for m in (5,15) for a in APPROACHES for d in ('long','short','both')}
    if {(r['minutes'],r['approach'],r['direction']) for r in rows}!=expected: raise ValueError('Invalid context matrix')
    for row in rows:
        if set(row['base'])!={'2022','2023','2024','2025','2026'} or set(row['stress'])!={'2022','2023','2024','2025','2026'}: raise ValueError('Incomplete fold matrix')
        row['combined']=combined(list(row['base'].values())); row['qualified'],row['screen_failures']=qualifies(row,protocol)
        row['control']=row['approach']==APPROACHES[1]
        if row['control']:
            row['qualified']=False; row['screen_failures'].append('benchmark only; ineligible for selection')
    lookup={(r['minutes'],r['direction']):r for r in rows if r['control']}
    for row in rows:
        if row['control']: continue
        control=lookup[(row['minutes'],row['direction'])]
        own=sum(row['base'][str(y)]['net_return_pct'] for y in (2025,2026)); other=sum(control['base'][str(y)]['net_return_pct'] for y in (2025,2026))
        row['matched_control_recent_base_return_pct']=other; row['recent_base_return_pct']=own
        if own<=other: row['screen_failures'].append('recent base return does not exceed matched price control'); row['qualified']=False
    return rows

def comparison(root, run_id):
    root=Path(root)
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',run_id) or run_id in ('.','..'): raise ValueError('Invalid run id')
    pp=root/'protocol.json'; ip=root/'INPUT_IDENTITIES.json'; ap=root/'AUTHORIZATION.json'
    if sha(pp)!=PROTOCOL_SHA256: raise ValueError('Changed frozen protocol')
    protocol=json.loads(pp.read_text(encoding='utf-8')); validate_protocol(protocol)
    auth=json.loads(ap.read_text(encoding='utf-8')); expected=json.loads(ip.read_text(encoding='utf-8'))
    if auth.get('protocol_sha256')!=sha(pp) or auth.get('input_identities_sha256')!=sha(ip): raise ValueError('Invalid administrative authorization')
    raw=Path(protocol['data_root'])
    required=REQUIRED_SOURCES | {p.as_posix() for p in raw.glob('*.json')} | {(raw/'manifest.json').as_posix()}
    if not isinstance(expected,dict) or not required.issubset(expected): raise ValueError('Missing source or raw identities')
    for name,digest in expected.items():
        if sha(Path(name))!=digest: raise ValueError(f'Changed input identity: {name}')
    raw=Path(protocol['data_root']); paths=[pp,ip,ap]+[Path(n) for n in expected]+sorted(raw.glob('*.json'))
    before={str(p):sha(p) for p in paths}; out=root/'runs'/run_id; out.mkdir(parents=True,exist_ok=False)
    write_json(out/'identities_before_run.json',before); completed=0; rows=[]; write_json(out/'progress.json',{'status':'RUNNING','completed':0,'expected':120})
    try:
        bars5=load_candles(raw); flow5=load_flow(raw,bars5); bars15=resample_15m(bars5); funding=load_funding(raw); end=int(datetime(2026,9,1,tzinfo=UTC).timestamp()*1000)
        if len(bars5)!=490752 or len(bars15)!=163584 or len(funding)!=5112 or bars5[0].t!=timestamp(2022) or bars5[-1].t+300000!=end or any(not timestamp(2022)<=f['ts']<end for f in funding) or sha(raw/'manifest.json')!=protocol['raw_manifest_sha256']: raise ValueError('Development extent or manifest mismatch')
        flow15=aggregate_flow_15m(flow5)
        write_json(out/'data_audit.json',{'raw_bars':len(bars5),'bars15':len(bars15),'funding_events':len(funding),'start':bars5[0].t,'end_exclusive':end,'flow_rows':len(flow5),'manifest_sha256':sha(raw/'manifest.json')})
        for minutes,bars,flow in ((5,bars5,flow5),(15,bars15,flow15)):
            features=build_features(bars,flow,minutes)
            with gzip.open(out/f'features-{minutes}.json.gz','wt',encoding='utf-8',compresslevel=1) as f: json.dump(features,f,separators=(',',':'),allow_nan=False)
            for approach in APPROACHES:
                signals,events=detect(bars,features,minutes,approach)
                with gzip.open(out/f'detector-{minutes}-{approach}.json.gz','wt',encoding='utf-8',compresslevel=1) as f: json.dump({'signals':[asdict(s) for s in signals],'events':events},f,separators=(',',':'),allow_nan=False)
                for direction in protocol['directions']:
                    trial=f'{minutes}m-{approach}-{direction}'; row={'id':trial,'minutes':minutes,'approach':approach,'direction':direction,'control':approach==APPROACHES[1],'detector_funnel':dict(Counter(x['kind'] for x in events)),'base':{},'stress':{}}; rows.append(row)
                    for year in range(2022,2027):
                        start=timestamp(year); stop=min(timestamp(year+1),end); step=minutes*60000; left=(start-bars[0].t)//step; right=(stop-bars[0].t)//step
                        part=bars[left:right]; fs=features[left:right]; ss=[replace(s,index=s.index-left) for s in signals if left<=s.index<right]; ff=[x for x in funding if start<=x['ts']<stop]
                        for condition in ('base','stress'):
                            ex=Execution(funding_mark_buffer_fraction=.01,slip_bps=2.0 if condition=='base' else 20.0)
                            result=simulate(part,ss,fs,minutes,approach,direction,ff,ex); row[condition][str(year)]=result['metrics']; saved=out/f'{trial}-{year}-{condition}.json.gz'
                            with gzip.open(saved,'wt',encoding='utf-8',compresslevel=1) as f: json.dump(result,f,separators=(',',':'),allow_nan=False)
                            entry={'trial_id':trial,'year':year,'condition':condition,'artifact':saved.name,'sha256':sha(saved),'metrics':result['metrics'],'parameters':protocol['parameters'],'execution':asdict(ex),'identities':before}
                            with (out/'trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(entry,allow_nan=False)+'\n')
                            with (root/'cumulative_trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'campaign_id':protocol['campaign_id'],'run_id':run_id,**entry},allow_nan=False)+'\n')
                            completed+=1; write_json(out/'comparison.partial.json',rows); write_json(out/'progress.json',{'status':'RUNNING','completed':completed,'expected':120,'last':saved.name})
        if completed!=120: raise ValueError('Incomplete matrix')
        screen_rows(rows,protocol)
        after={str(p):sha(p) for p in paths}; write_json(out/'identities_after_run.json',after)
        if after!=before: raise ValueError('Input identities changed during run')
        candidates=[x for x in rows if not x['control']]; controls=[x for x in rows if x['control']]
        eligible=sorted((x for x in candidates if x['qualified']),key=lambda x:(-x['combined']['worst_fold_return_pct'],-x['combined']['mean_fold_return_pct'],x['id']))
        failures=Counter(reason for x in candidates for reason in x['screen_failures'])
        summary={'campaign_id':protocol['campaign_id'],'run_id':run_id,'status':'PASS_TO_PHASE_3' if eligible else 'RETURN_TO_PHASE_1','selected':eligible[0]['id'] if eligible else None,'completed_annual_runs':completed,'candidates':candidates,'controls':controls,'failure_counts':dict(failures),'cash_benchmark':protocol['cash_benchmark'],'chronology':protocol['chronology'],'limitations':protocol['limitations'],'identities':before}
        write_json(out/'comparison.json',summary)
        (out/'REPORT.md').write_text('# BTC executed taker pressure comparison\n\n'+f"Status: {summary['status']}; selected: {summary['selected'] or 'none'}.\n\n"+'\n'.join(f"- {r['id']}: failures: {'; '.join(r['screen_failures']) or 'none'}" for r in rows)+'\n',encoding='utf-8')
        write_json(out/'progress.json',{'status':'COMPLETE','completed':completed,'expected':120}); return out
    except Exception as exc:
        write_json(out/'progress.json',{'status':'FAILED','completed':completed,'expected':120,'error':str(exc)}); raise
    finally:
        write_json(out/'identities_after_run.json',{str(p):sha(p) if p.exists() else None for p in paths})

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',required=True,type=Path); parser.add_argument('--run-id',required=True); args=parser.parse_args(); print(comparison(args.root,args.run_id))
if __name__=='__main__': main()
