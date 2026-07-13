# Mutation Lab Run run_9b21a7a7e7b1

- Family: `xauusd_ghl_dc`
- Version: `XAUUSD GHL+DC Parent | robustness repair UTC block 1,7,8,11,12,13,14,21 | tuned initial_capital=5000, sizing_mode=mt5_fixed_risk_lot | tuned time_risk_block_utc_hours=[1, 7, 12, 14, 21] | tuned breakeven_trigger_mfe_r=0.5, notional_pct=0.05 | tuned breakeven_stop_enabled=True, donchian_length=34 | tuned breakeven_lock_r=0.1, breakeven_min_bars=2, contract_size=100, gann_low_period=21...`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_4e109af56413`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `XAUUSD` at `IC Markets MT5` / `30m`. The live parameters are `{"allow_long": true, "allow_short": false, "atr_len": 34, "breakeven_lock_r": 0.1, "breakeven_min_bars": 2, "breakeven_stop_enabled": true, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0035, "contract_size": 100.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "failed_entry_triage_bars": 3, "failed_entry_triage_enabled": false, "failed_entry_triage_max_current_r": 0.0, "failed_entry_triage_min_mfe_r": 0.25, "gann_high_period": 21, "gann_low_period": 21, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.05, "quantity": 1.0, "risk_pct": 0.01, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 10, "stop_mode": "atr", "stop_mult": 2.5, "tick_size": 0.01, "time_risk_block_utc_hours": [1, 7, 14, 21], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `7260.96`
- Return %: `145.22`
- Profit Factor: `2.0881`
- Max Drawdown %: `4.99`
- Expected Payoff: `7.47`
- Total Trades: `972`
- Win Rate %: `65.23`
- Avg Win / Avg Loss Ratio: `1.1132`
- Approx Breakeven Win Rate: `47.32`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `5.0653`
- Trade-Level Sortino: `9.5484`
- Daily Portfolio Sharpe: `2.2937`
- Daily Portfolio Sortino: `2.6781`
- Daily Volatility %: `6.61`
- Worst Daily Return %: `-1.18`
- Positive Day %: `29.26`
- Calmar: `29.0932`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `83.37`
- Max Entry Exposure %: `99.97`
- Avg Initial Risk %: `0.3341`
- Max Initial Risk %: `0.9355`
- Buy & Hold Net PnL: `13154.17`
- Buy & Hold Asset Return %: `263.08`
- Buy & Hold Max Drawdown %: `25.96`
- Buy & Hold Calmar: `10.1331`
- Buy & Hold Start/End: `1277.39` -> `4637.99`
- Outperformance %: `-117.86`
- Calmar Delta: `18.9601`

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

- Profit Factor Delta: `0.2388`
- Net PnL Delta: `721.35`
- Drawdown % Delta: `0.36`
- Trade Count Delta: `-200`

## Single Mutation

- Summary: `repaired contract_size=100 for MT5 XAUUSD contract parity`
- Rationale: contract_size is an execution constant, not an optimizable alpha lever; contract_size=1 inflated the saved optimization and is not accepted for MT5 parity.

## Diagnostics

- Entries: `972`
- Long signals: `1125`
- Short signals: `0`
- Short quality gate blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- Entry black-box veto blocks: `0`
- Entry black-box veto long blocks: `0`
- Entry black-box veto short blocks: `0`
- Breakeven stop moves: `633`
- Breakeven maturity blocks: `320`
- MT5 stop modify rejects: `38`
- Failed-entry triage exits: `0`
- Failed-entry triage candidates: `0`
- Time risk filter blocks: `141`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `1`
- Stop exits: `209`
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
- Pending entry orders: `0`
- Pending order fills: `0`
- Dropped pending orders at end of data: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 972 | 7260.96 | 2.0881 | 65.23% | 21.98 | -19.74 | 16.27 |
| short | 0 | 0.0 | 0.0 | 0.0% | 0.0 | 0.0 | 0.0 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| breakeven_stop | 377 | 636.08 | 636.08 | 100.0% | 1.69 | 0.0 | 9.39 |
| gann_state_exit | 385 | 11104.17 | 6.0676 | 66.49% | 51.94 | -16.99 | 29.51 |
| stop | 209 | -4482.06 | 0.0 | 0.0% | 0.0 | -21.45 | 4.34 |
| time_exit | 1 | 2.77 | 2.77 | 100.0% | 2.77 | 0.0 | 4.0 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 20 | -17.93 | 0.7374 | 65.0% | 3.87 | -9.75 | 11.9 |
| 2018 | 105 | 25.87 | 1.0606 | 63.81% | 6.76 | -11.24 | 14.69 |
| 2019 | 114 | 555.56 | 2.1368 | 63.16% | 14.5 | -11.64 | 17.6 |
| 2020 | 113 | 738.61 | 1.9526 | 69.03% | 19.41 | -22.15 | 16.18 |
| 2021 | 124 | 83.99 | 1.0966 | 61.29% | 12.55 | -18.11 | 14.76 |
| 2022 | 118 | 580.88 | 1.7131 | 66.95% | 17.66 | -20.89 | 14.91 |
| 2023 | 122 | 523.76 | 1.6217 | 59.84% | 18.72 | -17.19 | 14.2 |
| 2024 | 113 | 829.93 | 1.8051 | 62.83% | 26.21 | -24.54 | 16.98 |
| 2025 | 110 | 2072.88 | 3.313 | 71.82% | 37.58 | -28.91 | 20.4 |
| 2026 | 33 | 1867.41 | 5.0567 | 78.79% | 89.53 | -65.76 | 21.64 |

## Trade Duration

- 25th percentile bars held: `4.0`
- Median bars held: `10.0`
- 75th percentile bars held: `22.0`
- 90th percentile bars held: `39.0`
- 95th percentile bars held: `50.0`

## Excursion Diagnostics

- Average MFE/R: `1.4236`
- Average MAE/R: `-0.6323`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.