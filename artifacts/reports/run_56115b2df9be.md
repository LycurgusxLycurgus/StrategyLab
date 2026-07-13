# Mutation Lab Run run_56115b2df9be

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 | phase 3 Gann confirmation optimized`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 21, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.75, "gann_exit_confirm_bars": 2, "gann_exit_confirmation_enabled": true, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.0025, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "bar_extreme", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [], "time_risk_block_weekdays": [], "time_risk_filter_enabled": false}`.

## Metrics

- Net PnL: `2325.15`
- Return %: `46.5`
- Profit Factor: `1.417`
- Max Drawdown %: `3.89`
- Expected Payoff: `2.38`
- Total Trades: `975`
- Win Rate %: `39.49`
- Avg Win / Avg Loss Ratio: `2.1716`
- Approx Breakeven Win Rate: `31.53`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `3.5854`
- Trade-Level Sortino: `7.0935`
- Daily Portfolio Sharpe: `1.5061`
- Daily Portfolio Sortino: `1.7688`
- Daily Volatility %: `4.26`
- Worst Daily Return %: `-0.85`
- Positive Day %: `33.2`
- Calmar: `11.9687`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `68.94`
- Max Entry Exposure %: `99.95`
- Avg Initial Risk %: `0.2062`
- Max Initial Risk %: `0.2499`
- Buy & Hold Net PnL: `1858.33`
- Buy & Hold Asset Return %: `37.17`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.332`
- Buy & Hold Start/End: `114.073` -> `156.47`
- Outperformance %: `9.34`
- Calmar Delta: `9.6367`

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

- Profit Factor Delta: `0.0245`
- Net PnL Delta: `127.79`
- Drawdown % Delta: `-0.37`
- Trade Count Delta: `-9`

## Single Mutation

- Summary: `gann_exit_confirm_allow_if_unrealized_r_lte=-0.75, gann_exit_confirm_bars=2, gann_exit_confirmation_enabled=True`
- Rationale: 

## Diagnostics

- Entries: `975`
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
- Gann exit confirmation candidates: `2066`
- Gann exit confirmation suppressed: `1380`
- Gann exit confirmation confirmed: `586`
- Gann exit confirmation adverse escapes: `100`
- Gann exit confirmation recovered: `57`
- Gann exit confirmation suppressed Net PnL: `6254.72`
- Time risk filter blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `8`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `275`
- Gap stop fills: `11`
- Reverse exits: `14`
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
- Pending order fills: `975`
- Pending order gap fills: `111`
- Pending Gann exits: `686`
- Gann exits filled next open: `686`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 505 | 1931.76 | 1.7299 | 42.77% | 21.2 | -9.16 | 26.52 |
| short | 470 | 393.39 | 1.1343 | 35.96% | 19.66 | -9.73 | 22.59 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 686 | 5674.79 | 3.7638 | 54.52% | 20.66 | -6.58 | 31.06 |
| reverse | 14 | 164.99 | 22.8241 | 78.57% | 15.69 | -2.52 | 52.07 |
| stop | 275 | -3514.63 | 0.0 | 0.0% | 0.0 | -12.78 | 7.19 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 12 | -29.02 | 0.5009 | 25.0% | 9.71 | -6.46 | 23.0 |
| 2018 | 117 | 119.85 | 1.2177 | 44.44% | 12.89 | -8.47 | 25.29 |
| 2019 | 122 | 14.93 | 1.0249 | 34.43% | 14.65 | -7.51 | 23.85 |
| 2020 | 109 | 333.01 | 1.5795 | 35.78% | 23.27 | -8.21 | 25.16 |
| 2021 | 131 | 74.54 | 1.1121 | 41.22% | 13.7 | -8.64 | 23.9 |
| 2022 | 101 | 919.03 | 2.805 | 46.53% | 30.39 | -9.43 | 28.54 |
| 2023 | 128 | 177.17 | 1.2116 | 36.72% | 21.58 | -10.34 | 22.93 |
| 2024 | 104 | 464.07 | 1.6542 | 37.5% | 30.09 | -10.91 | 24.69 |
| 2025 | 109 | 175.32 | 1.2337 | 42.2% | 20.12 | -11.91 | 23.78 |
| 2026 | 42 | 76.25 | 1.2377 | 38.1% | 24.81 | -12.34 | 24.19 |

## Trade Duration

- 25th percentile bars held: `10.0`
- Median bars held: `21.0`
- 75th percentile bars held: `34.0`
- 90th percentile bars held: `49.0`
- 95th percentile bars held: `62.0`

## Excursion Diagnostics

- Average MFE/R: `1.5442`
- Average MAE/R: `-0.7613`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.