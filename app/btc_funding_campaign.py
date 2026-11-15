"""Run the frozen funding-state comparison on audited local data."""
import argparse
import gzip
import json
import re
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from app.btc_funding import APPROACHES, FundingExecution, build_event_features, detect
from app.btc_funding_broker import simulate
from app.btc_liquidity_data import load_candles, load_funding, resample_15m
from app.btc_liquidity_campaign import sha, write_json, timestamp, combined, qualifies

PROTOCOL_SHA256='a1a40fa117df51c18656d273b86527f6448782e7c9d825e255324b54dd53da75'
ROOT=Path('artifacts/strategy-development/btc-funding-state-phase2-20261028')
REQUIRED_SOURCES={'app/btc_funding.py','app/btc_funding_broker.py','app/btc_funding_campaign.py','app/btc_funding_tests.py','app/btc_liquidity.py','app/btc_liquidity_data.py','app/btc_liquidity_campaign.py'}

def validate_protocol(protocol):
    canonical=ROOT/'protocol.json'
    if sha(canonical)!=PROTOCOL_SHA256 or protocol!=json.loads(canonical.read_text(encoding='utf-8')): raise ValueError('Protocol differs from frozen contract')
    if protocol['schema_version']!='btc_funding_state_phase2_v1' or protocol['candidate']!=APPROACHES[0] or protocol['controls']!=list(APPROACHES[1:]) or protocol['execution_timeframes_minutes']!=[5,15] or protocol['phase2_execution_authorized'] is not True or protocol['future_comparison_budget']['economic_evaluations']!=90: raise ValueError('Unsupported frozen protocol')
    return True

def screen_rows(rows, protocol):
    if len(rows)!=6 or {(r['minutes'],r['approach']) for r in rows}!={(m,a) for m in (5,15) for a in APPROACHES}: raise ValueError('Incomplete context matrix')
    for r in rows:
        if any(set(r[k])!={'2022','2023','2024','2025','2026'} for k in ('base','stress','severe_sensitivity')): raise ValueError('Incomplete fold matrix')
        r['combined']=combined(list(r['base'].values())); r['qualified'],r['screen_failures']=qualifies(r,protocol); r['control']=r['approach']!=APPROACHES[0]
        if any(x.get('status')=='INVALID_EXECUTION' for k in ('base','stress','severe_sensitivity') for x in r[k].values()): r['screen_failures'].append('invalid execution'); r['qualified']=False
        if r['control']: r['qualified']=False; r['screen_failures'].append('benchmark only; ineligible for selection')
    for r in rows:
        if r['control']: continue
        stale=next(x for x in rows if x['minutes']==r['minutes'] and x['approach']==APPROACHES[1]); continuous=next(x for x in rows if x['minutes']==r['minutes'] and x['approach']==APPROACHES[2])
        if any(x.get('status')=='INVALID_EXECUTION' for control in (stale,continuous) for k in ('base','stress','severe_sensitivity') for x in control[k].values()): r['screen_failures'].append('paired control invalid execution')
        recent=[r['base'][str(y)] for y in (2025,2026)]; own=sum(x['net_return_pct'] for x in recent); other=sum(stale['base'][str(y)]['net_return_pct'] for y in (2025,2026)); r['recent_base_return_pct']=own; r['matched_stale_recent_base_return_pct']=other
        if own<=other: r['screen_failures'].append('recent base return does not exceed stale control')
        def ratio(row):
            folds=[row['base'][str(y)] for y in (2025,2026)]; denominator=sum(x['notional_days'] for x in folds)
            return 10000*sum(x['net_profit'] for x in folds)/denominator if denominator else None
        r['recent_net_bps_per_notional_day']=ratio(r); r['continuous_recent_net_bps_per_notional_day']=ratio(continuous)
        if r['recent_net_bps_per_notional_day'] is None or r['continuous_recent_net_bps_per_notional_day'] is None or r['recent_net_bps_per_notional_day']<=r['continuous_recent_net_bps_per_notional_day']: r['screen_failures'].append('recent return per notional-day does not exceed continuous control')
        weeks=Counter()
        for x in recent: weeks.update(x['entry_week_net_pnl'])
        best=max([0,*weeks.values()]); r['recent_entry_week_net_pnl']=dict(weeks); r['recent_closed_net_less_best_week']=sum(x['closed_net_pnl'] for x in recent)-best
        if r['recent_closed_net_less_best_week']<=0: r['screen_failures'].append('recent closed net after best entry week nonpositive')
        if r['screen_failures']: r['qualified']=False
    return rows

def comparison(root,run_id):
    root=Path(root)
    if root.resolve()!=ROOT.resolve(): raise ValueError('Unexpected campaign root')
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',run_id) or run_id in ('.','..'): raise ValueError('Invalid run id')
    pp=root/'protocol.json'; ip=root/'INPUT_IDENTITIES.json'; ap=root/'AUTHORIZATION.json'
    if sha(pp)!=PROTOCOL_SHA256: raise ValueError('Changed frozen protocol')
    protocol=json.loads(pp.read_text(encoding='utf-8')); validate_protocol(protocol)
    auth=json.loads(ap.read_text(encoding='utf-8')); identities=json.loads(ip.read_text(encoding='utf-8'))
    if set(auth)!={'protocol_sha256','input_identities_sha256'} or auth['protocol_sha256']!=sha(pp) or auth['input_identities_sha256']!=sha(ip): raise ValueError('Invalid authorization')
    raw=Path(protocol['data_root']); required=REQUIRED_SOURCES|{p.as_posix() for p in raw.glob('*.json')}|{(raw/'manifest.json').as_posix()}
    if not isinstance(identities,dict) or not required.issubset(identities): raise ValueError('Missing source or raw identities')
    for name,digest in identities.items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or sha(path)!=digest: raise ValueError(f'Changed input identity: {name}')
    if sha(Path(protocol['rules_file']))!=protocol['rules_sha256']: raise ValueError('Changed rules')
    paths=[pp,ip,ap,Path(protocol['rules_file'])]+[Path(n) for n in identities]; before={str(p):sha(p) for p in paths}; out=root/'runs'/run_id; out.mkdir(parents=True,exist_ok=False)
    write_json(out/'identities_before_run.json',before); completed=0; rows=[]; write_json(out/'progress.json',{'status':'RUNNING','completed':0,'expected':90})
    try:
        bars5=load_candles(raw); bars15=resample_15m(bars5); funding=load_funding(raw); end=int(datetime(2026,9,1,tzinfo=UTC).timestamp()*1000); start=timestamp(2022)
        if len(bars5)!=490752 or len(bars15)!=163584 or len(funding)!=5112 or bars5[0].t!=start or bars5[-1].t+300000!=end or any(not start<=f['ts']<end for f in funding) or sha(raw/'manifest.json')!=protocol['raw_manifest_sha256']: raise ValueError('Development extent or manifest mismatch')
        features=build_event_features(funding,start)
        def save(name,value):
            with gzip.open(out/name,'wt',encoding='utf-8',compresslevel=1) as f: json.dump(value,f,separators=(',',':'),allow_nan=False)
        save('features.json.gz',features)
        write_json(out/'data_audit.json',{'raw_bars':len(bars5),'bars15':len(bars15),'funding_events':len(funding),'start':start,'end_exclusive':end,'manifest_sha256':sha(raw/'manifest.json')})
        for minutes,bars in ((5,bars5),(15,bars15)):
            step=minutes*60000
            for approach in APPROACHES:
                signals,events=detect(bars,minutes,features,approach); save(f'detector-{minutes}-{approach}.json.gz',{'signals':[asdict(s) for s in signals],'events':events})
                trial=f'{minutes}m-{approach}'; row={'id':trial,'minutes':minutes,'approach':approach,'direction':'long','detector_funnel':dict(Counter(x['kind'] for x in events)),'base':{},'stress':{},'severe_sensitivity':{}}; rows.append(row)
                for year in range(2022,2027):
                    fold_start=timestamp(year); stop=min(timestamp(year+1),end); left=(fold_start-start)//step; right=(stop-start)//step; part=bars[left:right]
                    ss=[replace(s,index=s.index-left) for s in signals if left<=s.index<right and fold_start<=s.event_ts<stop]
                    if approach==APPROACHES[2]: ss=ss[:1]
                    ff=[x for x in funding if fold_start<=x['ts']<stop]
                    for condition in ('base','stress','severe_sensitivity'):
                        costs=protocol['cost_conditions'][condition]; ex=FundingExecution(fee_bps=costs['fee_bps_each_fill'],slip_bps=costs['slip_bps_each_fill']); result=simulate(part,ss,minutes,approach,ff,ex); metrics={**result['metrics'],'status':result['status']}; row[condition][str(year)]=metrics
                        name=f'{trial}-{year}-{condition}.json.gz'; save(name,result); entry={'trial_id':trial,'year':year,'condition':condition,'artifact':name,'sha256':sha(out/name),'metrics':metrics,'execution':asdict(ex),'identities':before}
                        with (out/'trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(entry,allow_nan=False)+'\n')
                        with (root/'cumulative_trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'campaign_id':protocol['campaign_id'],'run_id':run_id,**entry},allow_nan=False)+'\n')
                        completed+=1; write_json(out/'comparison.partial.json',rows); write_json(out/'progress.json',{'status':'RUNNING','completed':completed,'expected':90,'last':name})
        if completed!=90: raise ValueError('Incomplete matrix')
        screen_rows(rows,protocol); after={str(p):sha(p) for p in paths}; write_json(out/'identities_after_run.json',after)
        if after!=before: raise ValueError('Input identities changed during run')
        candidates=[x for x in rows if not x['control']]; controls=[x for x in rows if x['control']]; eligible=sorted((x for x in candidates if x['qualified']),key=lambda x:(-x['combined']['worst_fold_return_pct'],-x['combined']['mean_fold_return_pct'],x['id']))
        summary={'campaign_id':protocol['campaign_id'],'run_id':run_id,'status':'PASS_TO_PHASE_3' if eligible else 'RETURN_TO_PHASE_1','selected':eligible[0]['id'] if eligible else None,'completed_annual_runs':completed,'candidates':candidates,'controls':controls,'failure_counts':dict(Counter(reason for x in candidates for reason in x['screen_failures'])),'cash_benchmark':protocol['cash_benchmark'],'chronology':protocol['chronology'],'limitations':protocol['source_and_execution_limits'],'identities':before}
        write_json(out/'comparison.json',summary); (out/'REPORT.md').write_text('# BTC funding-state comparison\n\n'+f"Status: {summary['status']}; selected: {summary['selected'] or 'none'}.\n\n"+'\n'.join(f"- {r['id']}: failures: {'; '.join(r['screen_failures']) or 'none'}" for r in rows)+'\n',encoding='utf-8'); write_json(out/'progress.json',{'status':'COMPLETE','completed':completed,'expected':90}); return out
    except Exception as exc:
        write_json(out/'progress.json',{'status':'FAILED','completed':completed,'expected':90,'error':str(exc)}); raise
    finally:
        write_json(out/'identities_after_run.json',{str(p):sha(p) if p.exists() else None for p in paths})

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',required=True,type=Path); parser.add_argument('--run-id',required=True); args=parser.parse_args(); print(comparison(args.root,args.run_id))
if __name__=='__main__': main()
