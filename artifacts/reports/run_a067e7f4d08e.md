# Mutation Lab Run run_a067e7f4d08e

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 | phase 3 time-risk UTC 19,20`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 21, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.75, "gann_exit_confirm_bars": 2, "gann_exit_confirmation_enabled": true, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.0025, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "bar_extreme", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [19, 20], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `2594.56`
- Return %: `51.89`
- Profit Factor: `1.4907`
- Max Drawdown %: `3.34`
- Expected Payoff: `2.8`
- Total Trades: `926`
- Win Rate %: `40.17`
- Avg Win / Avg Loss Ratio: `2.22`
- Approx Breakeven Win Rate: `31.06`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `3.9872`
- Trade-Level Sortino: `8.0128`
- Daily Portfolio Sharpe: `1.6715`
- Daily Portfolio Sortino: `1.9402`
- Daily Volatility %: `4.2`
- Worst Daily Return %: `-0.8`
- Positive Day %: `32.33`
- Calmar: `15.5147`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `68.9`
- Max Entry Exposure %: `99.98`
- Avg Initial Risk %: `0.206`
- Max Initial Risk %: `0.2499`
- Buy & Hold Net PnL: `1858.33`
- Buy & Hold Asset Return %: `37.17`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.332`
- Buy & Hold Start/End: `114.073` -> `156.47`
- Outperformance %: `14.72`
- Calmar Delta: `13.1827`

## Performance Interpretation

This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.

## Production Gate

- Core failures: `[]`
- Portfolio / benchmark failures: `[]`
- Live execution review failures: `[]`
- Production sizing modes: `['mt5_fixed_risk_lot']`
- Benchmark policy: `outperform_return_or_calmar`
- Execution model: `mt5_bar_proxy`

The platform-level rule is deliberately generic: first prove the strategy has enough activity, positive expectancy, bounded mark-to-market drawdown, acceptable daily portfolio Sharpe/Sortino/Calmar, bounded daily loss, and bounded per-trade risk; then judge it under a portfolio sizing model against buy-and-hold. Trade-level Sharpe/Sortino are diagnostic only and may overstate deployable portfolio quality. A strategy does not need to beat buy-and-hold on raw return if it delivers better drawdown-adjusted efficiency, but if it loses on both raw return and Calmar it is not production-comparable yet.

## Capital Model Warning

- mt5_fixed_risk_lot sizes each trade from the stop-distance risk budget, then rounds to broker lot constraints; `0.0025` means `0.25%` of current equity is the intended pre-rounding loss budget.

## Parent Comparison

- Profit Factor Delta: `0.0737`
- Net PnL Delta: `269.41`
- Drawdown % Delta: `-0.55`
- Trade Count Delta: `-49`

## Single Mutation

- Summary: `time_risk_block_utc_hours=[19, 20], time_risk_filter_enabled=True`
- Rationale: 

## Diagnostics

- Entries: `926`
- Long signals: `546`
- Short signals: `507`
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
- Gann exit confirmation candidates: `1982`
- Gann exit confirmation suppressed: `1328`
- Gann exit confirmation confirmed: `564`
- Gann exit confirmation adverse escapes: `90`
- Gann exit confirmation recovered: `57`
- Gann exit confirmation suppressed Net PnL: `6334.09`
- Time risk filter blocks: `56`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `7`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `259`
- Gap stop fills: `11`
- Reverse exits: `13`
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
- Pending entry orders: `2915`
- Pending order fills: `926`
- Pending order gap fills: `108`
- Pending Gann exits: `654`
- Gann exits filled next open: `654`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 482 | 2020.95 | 1.7919 | 43.36% | 21.88 | -9.35 | 26.65 |
| short | 444 | 573.61 | 1.2096 | 36.71% | 20.3 | -9.74 | 22.76 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 654 | 5810.88 | 4.0206 | 55.35% | 21.37 | -6.59 | 31.34 |
| reverse | 13 | 140.34 | 19.5635 | 76.92% | 14.79 | -2.52 | 51.0 |
| stop | 259 | -3356.66 | 0.0 | 0.0% | 0.0 | -12.96 | 6.92 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 11 | -26.8 | 0.5207 | 27.27% | 9.71 | -6.99 | 23.27 |
| 2018 | 112 | 151.56 | 1.2932 | 45.54% | 13.11 | -8.47 | 25.73 |
| 2019 | 116 | 46.27 | 1.082 | 34.48% | 15.26 | -7.42 | 23.97 |
| 2020 | 103 | 386.15 | 1.7127 | 36.89% | 24.42 | -8.34 | 25.45 |
| 2021 | 126 | 105.03 | 1.1648 | 42.06% | 14.0 | -8.73 | 24.05 |
| 2022 | 94 | 889.01 | 2.8241 | 46.81% | 31.28 | -9.75 | 28.24 |
| 2023 | 123 | 232.99 | 1.2921 | 37.4% | 22.41 | -10.36 | 23.07 |
| 2024 | 98 | 494.66 | 1.7368 | 37.76% | 31.51 | -11.01 | 24.74 |
| 2025 | 101 | 235.42 | 1.3417 | 43.56% | 21.01 | -12.09 | 24.25 |
| 2026 | 42 | 80.27 | 1.2458 | 38.1% | 25.43 | -12.56 | 24.19 |

## Trade Duration

- 25th percentile bars held: `10.0`
- Median bars held: `22.0`
- 75th percentile bars held: `35.0`
- 90th percentile bars held: `50.0`
- 95th percentile bars held: `62.0`

## Excursion Diagnostics

- Average MFE/R: `1.5709`
- Average MAE/R: `-0.756`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.