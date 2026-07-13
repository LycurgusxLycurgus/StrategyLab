# Mutation Lab Run run_b7ca48b6f20e

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 Parent`
- Stage: `white_box`
- Verdict: `graveyard`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 14, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.75, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 55, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.35, "gann_exit_confirm_bars": 1, "gann_exit_confirmation_enabled": false, "gann_high_period": 13, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 7, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.005, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "atr", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [], "time_risk_block_weekdays": [], "time_risk_filter_enabled": false}`.

## Metrics

- Net PnL: `479.48`
- Return %: `9.59`
- Profit Factor: `1.0951`
- Max Drawdown %: `9.95`
- Expected Payoff: `0.67`
- Total Trades: `713`
- Win Rate %: `36.75`
- Avg Win / Avg Loss Ratio: `1.8851`
- Approx Breakeven Win Rate: `34.66`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `0.877`
- Trade-Level Sortino: `1.4762`
- Daily Portfolio Sharpe: `0.3616`
- Daily Portfolio Sortino: `0.3465`
- Daily Volatility %: `4.47`
- Worst Daily Return %: `-1.2`
- Positive Day %: `20.3`
- Calmar: `0.9637`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `90.17`
- Max Entry Exposure %: `100.0`
- Avg Initial Risk %: `0.2977`
- Max Initial Risk %: `0.4999`
- Buy & Hold Net PnL: `1839.2`
- Buy & Hold Asset Return %: `36.78`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.308`
- Buy & Hold Start/End: `114.392` -> `156.47`
- Outperformance %: `-27.19`
- Calmar Delta: `-1.3443`

## Performance Interpretation

This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.

## Production Gate

- Core failures: `['low_profit_factor', 'low_daily_sharpe', 'low_daily_sortino']`
- Portfolio / benchmark failures: `['weak_vs_buy_hold_benchmark']`
- Live execution review failures: `[]`
- Production sizing modes: `['mt5_fixed_risk_lot']`
- Benchmark policy: `outperform_return_or_calmar`
- Execution model: `mt5_bar_proxy`

The platform-level rule is deliberately generic: first prove the strategy has enough activity, positive expectancy, bounded mark-to-market drawdown, acceptable daily portfolio Sharpe/Sortino/Calmar, bounded daily loss, and bounded per-trade risk; then judge it under a portfolio sizing model against buy-and-hold. Trade-level Sharpe/Sortino are diagnostic only and may overstate deployable portfolio quality. A strategy does not need to beat buy-and-hold on raw return if it delivers better drawdown-adjusted efficiency, but if it loses on both raw return and Calmar it is not production-comparable yet.

## Capital Model Warning

- mt5_fixed_risk_lot sizes each trade from the stop-distance risk budget, then rounds to broker lot constraints; `0.005` means `0.5%` of current equity is the intended pre-rounding loss budget.

## Diagnostics

- Entries: `713`
- Long signals: `311`
- Short signals: `407`
- Short quality gate blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- Entry black-box veto blocks: `0`
- Entry black-box veto long blocks: `0`
- Entry black-box veto short blocks: `0`
- Breakeven stop moves: `0`
- Breakeven maturity blocks: `0`
- MT5 stop modify rejects: `0`
- Failed-entry triage exits: `0`
- Failed-entry triage candidates: `0`
- Gann exit confirmation candidates: `0`
- Gann exit confirmation suppressed: `0`
- Gann exit confirmation confirmed: `0`
- Gann exit confirmation adverse escapes: `0`
- Gann exit confirmation recovered: `0`
- Gann exit confirmation suppressed Net PnL: `0`
- Time risk filter blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `0`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `192`
- Gap stop fills: `12`
- Reverse exits: `0`
- Reverse confirmation candidates: `0`
- Reverse confirmation exits allowed: `0`
- Reverse confirmation adverse escapes allowed: `0`
- Reverse confirmation suppressed: `0`
- Reverse confirmation suppressed Net PnL: `0.0`
- Time-decay exits: `0`
- Time-decay confirmation candidates: `0`
- Time-decay confirmation exits allowed: `0`
- Time-decay confirmation suppressed: `0`
- Time-decay confirmation suppressed Net PnL: `0.0`
- Time exits: `0`
- Pending entry orders: `3521`
- Pending order fills: `713`
- Pending order gap fills: `90`
- Pending Gann exits: `521`
- Gann exits filled next open: `521`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 309 | 444.48 | 1.2066 | 38.51% | 21.82 | -11.33 | 22.09 |
| short | 404 | 35.0 | 1.0121 | 35.4% | 20.44 | -11.07 | 15.63 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 521 | 3446.35 | 2.6621 | 50.29% | 21.07 | -8.01 | 23.24 |
| stop | 192 | -2966.87 | 0.0 | 0.0% | 0.0 | -15.45 | 5.37 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 9 | -8.08 | 0.8072 | 33.33% | 11.28 | -6.99 | 18.89 |
| 2018 | 88 | 104.31 | 1.2062 | 43.18% | 16.06 | -10.12 | 19.32 |
| 2019 | 90 | 55.77 | 1.122 | 34.44% | 16.54 | -7.75 | 19.22 |
| 2020 | 76 | -92.28 | 0.8281 | 34.21% | 17.09 | -10.73 | 18.42 |
| 2021 | 87 | -97.57 | 0.7751 | 37.93% | 10.19 | -8.03 | 17.43 |
| 2022 | 77 | 483.44 | 1.8431 | 40.26% | 34.09 | -12.46 | 20.86 |
| 2023 | 99 | 129.7 | 1.1428 | 34.34% | 30.53 | -13.97 | 17.39 |
| 2024 | 75 | -117.65 | 0.8155 | 36.0% | 19.25 | -13.28 | 16.63 |
| 2025 | 83 | -120.76 | 0.8426 | 34.94% | 22.3 | -14.21 | 17.77 |
| 2026 | 29 | 142.6 | 1.7987 | 34.48% | 32.11 | -9.4 | 19.79 |

## Trade Duration

- 25th percentile bars held: `8.0`
- Median bars held: `16.0`
- 75th percentile bars held: `24.0`
- 90th percentile bars held: `39.0`
- 95th percentile bars held: `45.0`

## Excursion Diagnostics

- Average MFE/R: `1.3471`
- Average MAE/R: `-0.7271`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.