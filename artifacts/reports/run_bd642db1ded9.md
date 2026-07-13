# Mutation Lab Run run_bd642db1ded9

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 | phase 3 Gann exit confirmation`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 21, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.35, "gann_exit_confirm_bars": 2, "gann_exit_confirmation_enabled": true, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.0025, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "bar_extreme", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [], "time_risk_block_weekdays": [], "time_risk_filter_enabled": false}`.

## Metrics

- Net PnL: `2197.36`
- Return %: `43.95`
- Profit Factor: `1.3925`
- Max Drawdown %: `4.26`
- Expected Payoff: `2.23`
- Total Trades: `984`
- Win Rate %: `38.72`
- Avg Win / Avg Loss Ratio: `2.2039`
- Approx Breakeven Win Rate: `31.21`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `3.4444`
- Trade-Level Sortino: `6.8952`
- Daily Portfolio Sharpe: `1.4384`
- Daily Portfolio Sortino: `1.6907`
- Daily Volatility %: `4.26`
- Worst Daily Return %: `-0.83`
- Positive Day %: `32.74`
- Calmar: `10.3153`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `68.81`
- Max Entry Exposure %: `99.96`
- Avg Initial Risk %: `0.206`
- Max Initial Risk %: `0.2499`
- Buy & Hold Net PnL: `1858.33`
- Buy & Hold Asset Return %: `37.17`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.332`
- Buy & Hold Start/End: `114.073` -> `156.47`
- Outperformance %: `6.78`
- Calmar Delta: `7.9834`

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

- Profit Factor Delta: `0.0811`
- Net PnL Delta: `501.14`
- Drawdown % Delta: `0.48`
- Trade Count Delta: `-48`

## Single Mutation

- Summary: `gann_exit_confirm_allow_if_unrealized_r_lte=-0.35, gann_exit_confirm_bars=2, gann_exit_confirmation_enabled=True`
- Rationale: 

## Diagnostics

- Entries: `984`
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
- Gann exit confirmation candidates: `1775`
- Gann exit confirmation suppressed: `1058`
- Gann exit confirmation confirmed: `446`
- Gann exit confirmation adverse escapes: `271`
- Gann exit confirmation recovered: `48`
- Gann exit confirmation suppressed Net PnL: `7274.56`
- Time risk filter blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `8`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `255`
- Gap stop fills: `11`
- Reverse exits: `12`
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
- Pending order fills: `984`
- Pending order gap fills: `116`
- Pending Gann exits: `717`
- Gann exits filled next open: `717`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 510 | 1782.81 | 1.6616 | 41.76% | 21.02 | -9.07 | 25.97 |
| short | 474 | 414.55 | 1.1428 | 35.44% | 19.75 | -9.49 | 22.15 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 717 | 5269.33 | 3.2348 | 51.74% | 20.56 | -6.81 | 29.94 |
| reverse | 12 | 164.99 | 46.5773 | 83.33% | 16.86 | -1.81 | 53.58 |
| stop | 255 | -3236.96 | 0.0 | 0.0% | 0.0 | -12.69 | 6.4 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 12 | -34.11 | 0.4601 | 16.67% | 14.54 | -6.32 | 22.0 |
| 2018 | 117 | 132.23 | 1.2457 | 44.44% | 12.89 | -8.28 | 25.03 |
| 2019 | 124 | 14.7 | 1.0243 | 33.06% | 15.1 | -7.28 | 23.39 |
| 2020 | 110 | 332.64 | 1.5759 | 34.55% | 23.95 | -8.02 | 24.52 |
| 2021 | 131 | 67.06 | 1.0997 | 41.22% | 13.7 | -8.73 | 23.63 |
| 2022 | 101 | 883.13 | 2.6907 | 45.54% | 30.55 | -9.5 | 28.27 |
| 2023 | 130 | 151.11 | 1.1768 | 36.15% | 21.4 | -10.3 | 22.28 |
| 2024 | 106 | 409.69 | 1.56 | 36.79% | 29.26 | -10.92 | 23.92 |
| 2025 | 111 | 161.72 | 1.2195 | 41.44% | 19.53 | -11.33 | 23.14 |
| 2026 | 42 | 79.19 | 1.2663 | 38.1% | 23.54 | -11.44 | 23.93 |

## Trade Duration

- 25th percentile bars held: `9.0`
- Median bars held: `21.0`
- 75th percentile bars held: `33.0`
- 90th percentile bars held: `48.0`
- 95th percentile bars held: `62.0`

## Excursion Diagnostics

- Average MFE/R: `1.5315`
- Average MAE/R: `-0.7373`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.