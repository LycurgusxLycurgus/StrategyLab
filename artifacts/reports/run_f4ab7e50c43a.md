# Mutation Lab Run run_f4ab7e50c43a

- Family: `usdjpy_ghl_dc`
- Version: `USDJPY GHL+DC H1 | robustness repair UTC 1,19,20 | tuned entry_blackbox_veto_enabled=True, entry_blackbox_veto_side_months=['short:4']`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_64d994c1b98b`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `USDJPY` at `IC Markets MT5` / `1h`. The live parameters are `{"account_conversion_mode": "quote_divide_price", "allow_long": true, "allow_short": true, "atr_len": 21, "breakeven_lock_r": 0.0, "breakeven_min_bars": 0, "breakeven_stop_enabled": false, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0, "commission_per_lot_side": 3.5, "contract_size": 100000.0, "donchian_length": 34, "entry_blackbox_veto_enabled": true, "entry_blackbox_veto_side_months": ["short:4"], "entry_blackbox_veto_utc_hours": [], "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.75, "gann_exit_confirm_bars": 2, "gann_exit_confirmation_enabled": true, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.25, "quantity": 1.0, "risk_pct": 0.0025, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 2, "spread_ticks": 8, "stop_mode": "bar_extreme", "stop_mult": 2.5, "tick_size": 0.001, "time_risk_block_utc_hours": [1, 19, 20], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `2810.39`
- Return %: `56.21`
- Profit Factor: `1.562`
- Max Drawdown %: `2.96`
- Expected Payoff: `3.26`
- Total Trades: `863`
- Win Rate %: `41.02`
- Avg Win / Avg Loss Ratio: `2.2459`
- Approx Breakeven Win Rate: `30.81`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `4.2976`
- Trade-Level Sortino: `8.8154`
- Daily Portfolio Sharpe: `1.8064`
- Daily Portfolio Sortino: `2.0823`
- Daily Volatility %: `4.14`
- Worst Daily Return %: `-0.76`
- Positive Day %: `31.06`
- Calmar: `19.0178`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `68.91`
- Max Entry Exposure %: `99.91`
- Avg Initial Risk %: `0.2061`
- Max Initial Risk %: `0.2498`
- Buy & Hold Net PnL: `1858.33`
- Buy & Hold Asset Return %: `37.17`
- Buy & Hold Max Drawdown %: `15.94`
- Buy & Hold Calmar: `2.332`
- Buy & Hold Start/End: `114.073` -> `156.47`
- Outperformance %: `19.04`
- Calmar Delta: `16.6858`

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

- Profit Factor Delta: `0.058`
- Net PnL Delta: `176.12`
- Drawdown % Delta: `-0.13`
- Trade Count Delta: `-42`

## Single Mutation

- Summary: `entry_blackbox_veto_enabled=True, entry_blackbox_veto_side_months=['short:4']`
- Rationale:

## Diagnostics

- Entries: `863`
- Long signals: `546`
- Short signals: `507`
- Short quality gate blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- Entry black-box veto blocks: `46`
- Entry black-box veto long blocks: `0`
- Entry black-box veto short blocks: `46`
- Breakeven stop moves: `0`
- Breakeven maturity blocks: `0`
- MT5 stop modify rejects: `0`
- Failed-entry triage exits: `0`
- Failed-entry triage candidates: `0`
- Gann exit confirmation candidates: `1855`
- Gann exit confirmation suppressed: `1244`
- Gann exit confirmation confirmed: `530`
- Gann exit confirmation adverse escapes: `81`
- Gann exit confirmation recovered: `55`
- Gann exit confirmation suppressed Net PnL: `6324.04`
- Time risk filter blocks: `79`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `7`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `8`
- Stop exits: `243`
- Gap stop fills: `11`
- Reverse exits: `9`
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
- Pending order fills: `863`
- Pending order gap fills: `101`
- Pending Gann exits: `611`
- Gann exits filled next open: `611`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 471 | 2072.96 | 1.8103 | 43.31% | 22.7 | -9.58 | 26.72 |
| short | 392 | 737.43 | 1.3019 | 38.27% | 21.2 | -10.09 | 23.13 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| gann_state_exit | 611 | 5862.36 | 4.2705 | 56.63% | 22.12 | -6.76 | 31.77 |
| reverse | 9 | 154.11 | 72.3472 | 88.89% | 19.53 | -2.16 | 55.11 |
| stop | 243 | -3206.08 | 0.0 | 0.0% | 0.0 | -13.19 | 7.16 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 8 | -1.02 | 0.9662 | 37.5% | 9.71 | -6.03 | 25.25 |
| 2018 | 107 | 192.2 | 1.4009 | 47.66% | 13.17 | -8.56 | 26.33 |
| 2019 | 108 | 74.11 | 1.1374 | 36.11% | 15.73 | -7.82 | 24.18 |
| 2020 | 98 | 319.89 | 1.6006 | 35.71% | 24.36 | -8.45 | 24.82 |
| 2021 | 115 | 156.33 | 1.2769 | 42.61% | 14.71 | -8.56 | 24.64 |
| 2022 | 90 | 974.47 | 3.125 | 48.89% | 32.57 | -9.97 | 28.96 |
| 2023 | 117 | 261.8 | 1.3305 | 37.61% | 23.95 | -10.85 | 22.97 |
| 2024 | 93 | 573.41 | 1.8661 | 38.71% | 34.32 | -11.62 | 25.0 |
| 2025 | 92 | 191.31 | 1.2844 | 42.39% | 22.15 | -12.69 | 24.32 |
| 2026 | 35 | 67.89 | 1.2524 | 40.0% | 24.06 | -12.81 | 25.66 |

## Trade Duration

- 25th percentile bars held: `10.0`
- Median bars held: `22.0`
- 75th percentile bars held: `35.0`
- 90th percentile bars held: `50.0`
- 95th percentile bars held: `63.0`

## Excursion Diagnostics

- Average MFE/R: `1.6065`
- Average MAE/R: `-0.7567`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.
