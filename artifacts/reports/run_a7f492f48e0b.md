# Mutation Lab Run run_a7f492f48e0b

- Family: `xauusd_ghl_dc`
- Version: `XAUUSD GHL+DC | causal MT5 execution repair | spread 5 ticks`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_4e109af56413`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `XAUUSD` at `IC Markets MT5` / `30m`. The live parameters are `{"allow_long": true, "allow_short": false, "atr_len": 34, "breakeven_lock_r": 0.1, "breakeven_min_bars": 2, "breakeven_stop_enabled": true, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0035, "contract_size": 100.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_exit_confirm_allow_if_unrealized_r_lte": -0.35, "gann_exit_confirm_bars": 1, "gann_exit_confirmation_enabled": false, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.05, "quantity": 1.0, "risk_pct": 0.01, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 10, "spread_ticks": 5, "stop_mode": "atr", "stop_mult": 2.5, "tick_size": 0.01, "time_risk_block_utc_hours": [1, 7, 14, 21], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `4445.79`
- Return %: `88.92`
- Profit Factor: `1.6635`
- Max Drawdown %: `7.61`
- Expected Payoff: `4.64`
- Total Trades: `958`
- Win Rate %: `62.11`
- Avg Win / Avg Loss Ratio: `1.0148`
- Approx Breakeven Win Rate: `49.63`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `3.7999`
- Trade-Level Sortino: `6.3367`
- Daily Portfolio Sharpe: `1.642`
- Daily Portfolio Sortino: `1.7602`
- Daily Volatility %: `6.59`
- Worst Daily Return %: `-1.94`
- Positive Day %: `27.38`
- Calmar: `11.6894`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `86.19`
- Max Entry Exposure %: `99.97`
- Avg Initial Risk %: `0.3355`
- Max Initial Risk %: `0.9638`
- Buy & Hold Net PnL: `13154.17`
- Buy & Hold Asset Return %: `263.08`
- Buy & Hold Max Drawdown %: `25.96`
- Buy & Hold Calmar: `10.1331`
- Buy & Hold Start/End: `1277.39` -> `4637.99`
- Outperformance %: `-174.17`
- Calmar Delta: `1.5563`

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

- mt5_fixed_risk_lot sizes each trade from the stop-distance risk budget, then rounds to broker lot constraints; `0.01` means `1.0%` of current equity is the intended pre-rounding loss budget.

## Parent Comparison

- Profit Factor Delta: `-0.4246`
- Net PnL Delta: `-2815.17`
- Drawdown % Delta: `2.62`
- Trade Count Delta: `-14`

## Single Mutation

- Summary: `spread_ticks=5`
- Rationale: 

## Diagnostics

- Entries: `958`
- Long signals: `1095`
- Short signals: `0`
- Short quality gate blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- Entry black-box veto blocks: `0`
- Entry black-box veto long blocks: `0`
- Entry black-box veto short blocks: `0`
- Breakeven stop moves: `598`
- Breakeven maturity blocks: `288`
- MT5 stop modify rejects: `37`
- Failed-entry triage exits: `0`
- Failed-entry triage candidates: `0`
- Gann exit confirmation candidates: `0`
- Gann exit confirmation suppressed: `0`
- Gann exit confirmation confirmed: `0`
- Gann exit confirmation adverse escapes: `0`
- Gann exit confirmation recovered: `0`
- Gann exit confirmation suppressed Net PnL: `0`
- Time risk filter blocks: `126`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `1`
- Execution semantics: `closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit`
- Spread ticks: `5`
- Stop exits: `235`
- Gap stop fills: `24`
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
- Time exits: `1`
- Pending entry orders: `5989`
- Pending order fills: `958`
- Pending order gap fills: `143`
- Pending Gann exits: `366`
- Gann exits filled next open: `365`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 958 | 4445.79 | 1.6635 | 62.11% | 18.73 | -18.46 | 16.15 |
| short | 0 | 0.0 | 0.0 | 0.0% | 0.0 | 0.0 | 0.0 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| breakeven_stop | 357 | 464.56 | 11.8644 | 98.88% | 1.44 | -10.69 | 9.37 |
| gann_state_exit | 365 | 8767.81 | 5.6916 | 66.03% | 44.14 | -15.07 | 30.5 |
| stop | 235 | -4789.35 | 0.0 | 0.0% | 0.0 | -20.38 | 4.2 |
| time_exit | 1 | 2.77 | 2.77 | 100.0% | 2.77 | 0.0 | 4.0 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 19 | -4.54 | 0.9385 | 63.16% | 5.78 | -10.55 | 13.53 |
| 2018 | 107 | -47.31 | 0.8989 | 59.81% | 6.57 | -10.88 | 14.99 |
| 2019 | 110 | 503.28 | 2.028 | 61.82% | 14.6 | -11.66 | 18.03 |
| 2020 | 109 | 533.01 | 1.6086 | 66.97% | 19.3 | -24.33 | 16.74 |
| 2021 | 124 | -199.08 | 0.8077 | 55.65% | 12.12 | -18.83 | 14.46 |
| 2022 | 117 | 224.78 | 1.2508 | 62.39% | 15.36 | -20.37 | 13.74 |
| 2023 | 120 | 292.45 | 1.3148 | 57.5% | 17.7 | -18.22 | 13.79 |
| 2024 | 110 | 398.19 | 1.5212 | 60.0% | 17.61 | -17.36 | 16.3 |
| 2025 | 107 | 1810.3 | 3.039 | 69.16% | 36.46 | -26.9 | 20.47 |
| 2026 | 35 | 934.71 | 4.3285 | 77.14% | 45.02 | -35.1 | 21.69 |

## Trade Duration

- 25th percentile bars held: `4.0`
- Median bars held: `10.0`
- 75th percentile bars held: `23.0`
- 90th percentile bars held: `39.0`
- 95th percentile bars held: `49.0`

## Excursion Diagnostics

- Average MFE/R: `1.3809`
- Average MAE/R: `-0.6795`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.