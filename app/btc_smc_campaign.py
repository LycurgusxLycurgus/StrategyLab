"""Run the fixed SMC-inspired BTC comparison without fetching data."""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import re
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from app.btc_liquidity import Execution, Parameters, detect as control_detect, simulate
from app.btc_liquidity_data import load_candles, load_funding, resample_15m
from app.btc_liquidity_campaign import sha, write_json, timestamp, combined, qualifies, rank_key
from app.btc_smc import SmcParameters, detect


def _validate(protocol):
    expected = {'development_start':'2022-01-01', 'development_end_exclusive':'2026-09-01',
        'annual_folds':[2022,2023,2024,2025,2026],
        'candidate_timeframes':{'bos_order_block':[5,15], 'silver_bullet':[5], 'turtle_soup_plus1':[5,15]},
        'directions':['long','short','both'], 'control':'breakout_control', 'control_timeframes':[5,15],
        'budget':{'fixed_candidate_contexts':15,'fixed_control_contexts':6,'annual_runs':210,'parameter_searches':0,'mutations':0},
        'smc_parameters':asdict(SmcParameters()),
        'broker_parameters':asdict(Parameters(max_hold_minutes=180)),
        'execution':asdict(Execution(funding_mark_buffer_fraction=0.01)), 'stress_slip_bps':4.0,
        'screen':{'positive_years':[2025,2026], 'minimum_recent_total_closed_trades':100,
                  'minimum_each_recent_closed_trades':30, 'minimum_combined_profit_factor':1.05,
                  'maximum_fold_close_drawdown_pct':10.0, 'recent_stress_net_positive':True}}
    if any(protocol.get(k) != v for k,v in expected.items()): raise ValueError('Unsupported protocol contract')
    if protocol.get('data_root') != 'artifacts/strategy-development/btc-liquidity-20261023/raw': raise ValueError('Unsupported data root')


def comparison(root: Path, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', run_id) or run_id in ('.','..'):
        raise ValueError('run-id must be a single directory name')
    root = Path(root)
    protocol_path = root / 'protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    _validate(protocol)
    p, e = Parameters(**protocol['broker_parameters']), Execution(**protocol['execution'])
    data_root = Path(protocol['data_root'])
    output = root / 'runs' / run_id
    output.mkdir(parents=True, exist_ok=False)
    paths = [protocol_path, root/'STRATEGY.md', Path(__file__), Path('app/btc_smc.py'),
             Path('app/btc_smc_tests.py'), Path('app/btc_liquidity.py'), Path('app/btc_liquidity_data.py'),
             Path('app/btc_liquidity_campaign.py'), Path('app/btc_liquidity_tests.py')]
    paths += sorted(data_root.glob('*.json'))
    before = {str(x):sha(x) for x in paths}
    write_json(output/'identities_before_run.json', before)
    rows, completed = [], 0
    write_json(output/'progress.json', {'completed':0,'expected':210,'status':'RUNNING'})
    try:
        bars5 = load_candles(data_root)
        bars15 = resample_15m(bars5)
        funding = load_funding(data_root)
        end = int(datetime(2026,9,1,tzinfo=UTC).timestamp()*1000)
        if bars5[0].t != timestamp(2022) or bars5[-1].t + 300000 != end:
            raise ValueError('Development dataset must match frozen extent')
        if any(x['ts'] < timestamp(2022) or x['ts'] >= end for x in funding):
            raise ValueError('Funding outside development extent')
        with (output/'visual_ledger.csv').open('w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['trial_id','year','entry_at','bar_index','timestamp','open','high','low','close','stop','target','exit_reason'])
        for minutes, bars in ((5,bars5),(15,bars15)):
            approaches = [name for name, frames in protocol['candidate_timeframes'].items() if minutes in frames] + [protocol['control']]
            for approach in approaches:
                signals, events = (control_detect(bars, minutes, approach, p) if approach == protocol['control'] else detect(bars, minutes, approach))
                funnel = dict(Counter(x['kind'] for x in events))
                with gzip.open(output/f'detector-{minutes}-{approach}.json.gz','wt',encoding='utf-8',compresslevel=1) as f:
                    json.dump({'signals':[asdict(s) for s in signals],'events':events}, f, allow_nan=False)
                for direction in protocol['directions']:
                    trial = f'{minutes}m-{approach}-{direction}'
                    row = {'id':trial,'minutes':minutes,'approach':approach,'direction':direction,'control':approach == protocol['control'], 'detector_funnel':funnel,'base':{},'stress':{}}
                    rows.append(row)
                    for year in protocol['annual_folds']:
                        start, stop = timestamp(year), min(timestamp(year+1),end)
                        left = (start-bars[0].t)//(minutes*60000)
                        right = (stop-bars[0].t)//(minutes*60000)
                        part = bars[left:right]
                        # The source index may be negative: provenance is retained relative to the fold.
                        intents = [replace(s,index=s.index-left,sweep_index=s.sweep_index-left) for s in signals if left <= s.index < right-1]
                        fs = [x for x in funding if start <= x['ts'] < stop]
                        for condition in ('base','stress'):
                            ex = e if condition == 'base' else replace(e, slip_bps=protocol['stress_slip_bps'])
                            result = simulate(part,intents,minutes,direction,fs,p,ex)
                            row[condition][str(year)] = result['metrics']
                            saved = output/f'{trial}-{year}-{condition}.json.gz'
                            with gzip.open(saved,'wt',encoding='utf-8',compresslevel=1) as f: json.dump(result,f,separators=(',',':'),allow_nan=False)
                            entry = {'trial_id':trial,'year':year,'condition':condition,'artifact':saved.name,'sha256':sha(saved),'metrics':result['metrics'],'parameters':asdict(p),'execution':asdict(ex)}
                            with (output/'trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(entry,allow_nan=False)+'\n')
                            cumulative = {'campaign_id':protocol['campaign_id'], 'run_id':run_id, **entry}
                            with (root/'cumulative_trials.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(cumulative,allow_nan=False)+'\n')
                            completed += 1
                            write_json(output/'comparison.partial.json', rows)
                            write_json(output/'progress.json', {'completed':completed,'expected':210,'status':'RUNNING','last':entry['artifact']})
                            if condition == 'base':
                                with (output/'visual_ledger.csv').open('a',newline='',encoding='utf-8') as f:
                                    w = csv.writer(f)
                                    for trade in result['trades'][:2]:
                                        for index in range(max(0,trade['signal_index']-2),min(len(part),trade['exit_index']+2)):
                                            b=part[index]; w.writerow([trial,year,trade['entry_at'],index,b.t,b.open,b.high,b.low,b.close,trade['stop'],trade['target'],trade['reason']])
                            print(f'{trial} {year} {condition}: {result["metrics"]["net_return_pct"]:.3f}%',flush=True)
                    row['combined'] = combined(list(row['base'].values()))
                    row['qualified'], row['screen_failures'] = qualifies(row,protocol)
        if completed != 210 or len(rows) != 21 or sum(not r['control'] for r in rows) != 15: raise ValueError('Incomplete fixed comparison')
        after = {str(x):sha(x) for x in paths}
        write_json(output/'identities_after_run.json',after)
        if after != before: raise ValueError('Evidence identities changed during comparison')
        candidates = sorted((r for r in rows if not r['control']),key=rank_key,reverse=True)
        controls = sorted((r for r in rows if r['control']),key=rank_key,reverse=True)
        eligible = [r for r in candidates if r['qualified']]
        summary = {'campaign_id':protocol['campaign_id'],'run_id':run_id,'created_at':datetime.now(UTC).isoformat(),
            'status':'PHASE_3_CANDIDATE_REQUIRES_ACCEPTANCE' if eligible else 'RETURN_TO_PHASE_1',
            'selected':eligible[0]['id'] if eligible else None,'completed_annual_runs':completed,
            'candidates':candidates,'controls':controls,'reserved_status':'UNFETCHED_UNEVALUATED',
            'verdicts':{'semantic':'requires independent validation','data':'audited archive loader; exact extent checked',
                        'execution':'OHLC proxy; real execution unverified','economic':'preliminary screen only',
                        'target':'Phase 3 acceptance required; no live authorization','source_fidelity':'not claimed'},
            'benchmark':'Cash: zero return and drawdown; matched breakout controls.', 'limitations':protocol['limitations'], 'identities':before}
        write_json(output/'comparison.json',summary)
        lines = ['# BTC SMC-inspired comparison','',f"Status: {summary['status']}; selected: {summary['selected'] or 'none'}.", '',
                 'Annual portfolios reset and cutoff positions are censored at marked equity. Recent windows are reused screening data, not pristine holdouts. Fees 6 bps and slippage 2 bps per fill (4 bps stress), plus signed funding, are modeled assumptions. Source fidelity and live execution are not claimed.', '', '## All candidates and controls', '']
        for row in candidates+controls:
            m=row['combined']; lines.append(f"- {row['id']}: worst fold {m['worst_fold_return_pct']:.3f}%, mean {m['mean_fold_return_pct']:.3f}%, {m['closed_trades']} trades; screen: {'; '.join(row['screen_failures']) or 'passed'}.")
        lines += ['', '## Limitations', ''] + [f'- {x}' for x in protocol['limitations']]
        (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        write_json(output/'progress.json',{'completed':completed,'expected':210,'status':'COMPLETE'})
        return output
    except Exception as exc:
        write_json(output/'progress.json',{'completed':completed,'expected':210,'status':'FAILED','error':str(exc)})
        raise
    finally:
        after = {str(x):sha(x) if x.exists() else None for x in paths}
        write_json(output/'identities_after_run.json',after)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('artifacts/strategy-development/btc-smc-20261028'))
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    print(comparison(args.root,args.run_id))

if __name__ == '__main__': main()

