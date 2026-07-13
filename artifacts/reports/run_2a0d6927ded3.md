# Mutation Lab Run run_2a0d6927ded3

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 | robustness repair UTC 1,19,20`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 21, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.75, "gann_exit_confirm_bars": 2, "gann_exit_confirmation_enabled": true, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.0025, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "bar_extreme", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [1, 19, 20], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `2634.27`
- Return %: `52.69`
- Profit Factor: `1.504`
- Max Drawdown %: `3.09`
- Expected Payoff: `2.91`
- Total Trades: `905`
- Win Rate %: `40.22`
- Avg Win / Avg Loss Ratio: `2.2353`
- Approx Breakeven Win Rate: `30.91`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `4.0355`
- Trade-Level Sortino: `8.2104`
- Daily Portfolio Sharpe: `1.6937`
- Daily Portfolio Sortino: `1.9529`
- Daily Volatility %: `4.19`
- Worst Daily Return %: `-0.79`
- Positive Day %: `31.93`
- Calmar: `17.0485`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `68.97`
- Max Entry Exposure %: `99.9`
- Avg Initial Risk %: `0.2057`
- Max Initial Risk %: `0.2498`
- Buy & Hold Net PnL: `1858.33`
- Buy & Hold Asset Return %: `37.17`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.332`
- Buy & Hold Start/End: `114.073` -> `156.47`
- Outperformance %: `15.52`
- Calmar Delta: `14.7165`

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

- Profit Factor Delta: `0.0133`
- Net PnL Delta: `39.71`
- Drawdown % Delta: `-0.25`
- Trade Count Delta: `-21`

## Single Mutation

- Summary: `time_risk_block_utc_hours=[1, 19, 20], time_risk_filter_enabled=True`
- Rationale: 

## Diagnostics

- Entries: `905`
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
- Gann exit confirmation candidates: `1940`
- Gann exit confirmation suppressed: `1298`
- Gann exit confirmation confirmed: `553`
- Gann exit confirmation adverse escapes: `89`
- Gann exit confirmation recovered: `57`
- Gann exit confirmation suppressed Net PnL: `6345.17`
- Time risk filter blocks: `79`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `7`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `252`
- Gap stop fills: `11`
- Reverse exits: `11`
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
- Pending order fills: `905`
- Pending order gap fills: `106`
- Pending Gann exits: `642`
- Gann exits filled next open: `642`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 471 | 2054.87 | 1.819 | 43.31% | 22.37 | -9.4 | 26.71 |
| short | 434 | 579.4 | 1.2132 | 36.87% | 20.61 | -9.92 | 22.84 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 642 | 5800.4 | 4.046 | 55.45% | 21.64 | -6.66 | 31.39 |
| reverse | 11 | 148.71 | 20.6706 | 72.73% | 19.53 | -2.52 | 52.91 |
| stop | 252 | -3314.84 | 0.0 | 0.0% | 0.0 | -13.15 | 6.98 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 8 | -1.02 | 0.9662 | 37.5% | 9.71 | -6.03 | 25.25 |
| 2018 | 110 | 167.27 | 1.3316 | 46.36% | 13.17 | -8.55 | 26.04 |
| 2019 | 115 | 48.27 | 1.0859 | 34.78% | 15.26 | -7.5 | 23.86 |
| 2020 | 102 | 372.74 | 1.6824 | 36.27% | 24.84 | -8.4 | 25.37 |
| 2021 | 124 | 113.21 | 1.1812 | 41.94% | 14.19 | -8.68 | 24.13 |
| 2022 | 92 | 963.09 | 3.0882 | 47.83% | 32.37 | -9.61 | 28.71 |
| 2023 | 121 | 269.72 | 1.3397 | 38.02% | 23.12 | -10.59 | 23.38 |
| 2024 | 98 | 487.75 | 1.6937 | 36.73% | 33.08 | -11.34 | 24.36 |
| 2025 | 96 | 200.24 | 1.2959 | 42.71% | 21.39 | -12.3 | 24.22 |
| 2026 | 39 | 13.0 | 1.0401 | 35.9% | 24.06 | -12.96 | 23.67 |

## Trade Duration

- 25th percentile bars held: `10.0`
- Median bars held: `22.0`
- 75th percentile bars held: `35.0`
- 90th percentile bars held: `50.0`
- 95th percentile bars held: `62.0`

## Excursion Diagnostics

- Average MFE/R: `1.5811`
- Average MAE/R: `-0.7561`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.