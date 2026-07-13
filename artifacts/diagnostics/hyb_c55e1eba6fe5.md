# Hybrid Entry-Quality Sizing Experiment hyb_c55e1eba6fe5

- Parent run: `run_2a0d6927ded3`
- Mode: `offline_entry_quality_conservative_sizing`
- Verdict: `rejected_offline_contract`
- Risk multiplier: `0.5`
- Reduced trades: `108` (11.93%)

## Parent vs Hybrid

| Metric | Parent | Hybrid | Delta |
|---|---:|---:|---:|
| Net PnL | 2634.27 | 2442.94 | -191.33 |
| Profit Factor | 1.504 | 1.4952 | -0.0088 |
| Max Drawdown % | 3.09 | 2.57 | -0.52 |
| Daily Sharpe | 1.6937 | 2.6297 | 0.936 |
| Daily Sortino | 1.9529 | 4.8482 | 2.8953 |
| Calmar | 17.0485 | 19.0452 | 1.9967 |
| Trades | 905 | 905 | 0 |

## Acceptance Contract

- PASS `all_trades_retained`
- PASS `reduced_fraction_in_range`
- FAIL `net_pnl_retained`
- FAIL `profit_factor`
- PASS `max_drawdown`
- PASS `daily_sharpe`
- PASS `daily_sortino`
- PASS `worst_day`
- PASS `calmar`

## Routing

Reject this offline branch. Failed gates: net_pnl_retained, profit_factor.