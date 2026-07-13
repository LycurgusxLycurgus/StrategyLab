# Mutation Lab Run run_87fcbd5dd9de

- Family: `xauusd_ghl_dc`
- Version: `XAUUSD GHL+DC Parent | robustness repair UTC block 1,7,8,11,12,13,14,21 | tuned initial_capital=5000, sizing_mode=mt5_fixed_risk_lot | tuned time_risk_block_utc_hours=[1, 7, 12, 14, 21] | tuned breakeven_trigger_mfe_r=0.5, notional_pct=0.05 | tuned breakeven_stop_enabled=True, donchian_length=34`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_4e109af56413`

## Frozen Strategy Contract

This run freezes `ghl_dc_breakout_v1` on `XAUUSD` at `IC Markets MT5` / `30m`. The live parameters are `{"allow_long": true, "allow_short": false, "atr_len": 34, "breakeven_lock_r": 0.0, "breakeven_stop_enabled": true, "breakeven_trigger_mfe_r": 0.5, "commission_pct": 0.0035, "contract_size": 100.0, "donchian_length": 34, "execution_model": "mt5_bar_proxy", "gann_high_period": 21, "gann_low_period": 13, "initial_capital": 5000.0, "lot_step": 0.01, "max_breakout_bars": 12, "max_leverage": 1.0, "max_lot": 100.0, "min_lot": 0.01, "notional_pct": 0.05, "quantity": 1.0, "risk_pct": 0.01, "sizing_mode": "mt5_fixed_risk_lot", "skip_below_min_lot": true, "slippage_ticks": 10, "stop_mode": "atr", "stop_mult": 2.5, "tick_size": 0.01, "time_risk_block_utc_hours": [1, 7, 12, 14, 21], "time_risk_block_weekdays": [], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `6539.61`
- Return %: `130.79`
- Profit Factor: `1.8493`
- Max Drawdown %: `4.63`
- Expected Payoff: `5.58`
- Total Trades: `1172`
- Win Rate %: `29.35`
- Avg Win / Avg Loss Ratio: `4.4513`
- Approx Breakeven Win Rate: `18.34`
- Execution Model: `mt5_bar_proxy`
- Equity Marking: `mark_to_market`
- Trade-Level Sharpe: `5.2837`
- Trade-Level Sortino: `12.3487`
- Daily Portfolio Sharpe: `2.1956`
- Daily Portfolio Sortino: `3.0895`
- Daily Volatility %: `6.44`
- Worst Daily Return %: `-1.1`
- Positive Day %: `19.72`
- Calmar: `28.2337`
- Sizing Mode: `mt5_fixed_risk_lot`
- Avg Entry Exposure %: `83.12`
- Max Entry Exposure %: `99.99`
- Avg Initial Risk %: `0.3378`
- Max Initial Risk %: `0.9866`
- Buy & Hold Net PnL: `13154.17`
- Buy & Hold Asset Return %: `263.08`
- Buy & Hold Max Drawdown %: `25.96`
- Buy & Hold Calmar: `10.1331`
- Buy & Hold Start/End: `1277.39` -> `4637.99`
- Outperformance %: `-132.29`
- Calmar Delta: `18.1006`

## Performance Interpretation

This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.

## Production Gate

- Core failures: `[]`
- Portfolio / benchmark failures: `[]`
- Live execution review failures: `[]`
- Production sizing modes: `['fixed_notional_pct', 'fixed_risk_pct', 'mt5_fixed_risk_lot']`
- Benchmark policy: `outperform_return_or_calmar`
- Execution model: `mt5_bar_proxy`

The platform-level rule is deliberately generic: first prove the strategy has enough activity, positive expectancy, bounded mark-to-market drawdown, acceptable daily portfolio Sharpe/Sortino/Calmar, bounded daily loss, and bounded per-trade risk; then judge it under a portfolio sizing model against buy-and-hold. Trade-level Sharpe/Sortino are diagnostic only and may overstate deployable portfolio quality. A strategy does not need to beat buy-and-hold on raw return if it delivers better drawdown-adjusted efficiency, but if it loses on both raw return and Calmar it is not production-comparable yet.

## Capital Model Warning

- mt5_fixed_risk_lot sizes each trade from the stop-distance risk budget, then rounds to broker lot constraints; `0.01` means `1.0%` of current equity is the intended pre-rounding loss budget.

## Parent Comparison

- Profit Factor Delta: `0.358`
- Net PnL Delta: `2851.48`
- Drawdown % Delta: `-0.59`
- Trade Count Delta: `297`

## Single Mutation

- Summary: `breakeven_stop_enabled=True, donchian_length=34`
- Rationale: 

## Diagnostics

- Entries: `1172`
- Long signals: `1437`
- Short signals: `0`
- Short quality gate blocks: `0`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- Entry black-box veto blocks: `0`
- Entry black-box veto long blocks: `0`
- Entry black-box veto short blocks: `0`
- Breakeven stop moves: `759`
- MT5 stop modify rejects: `37`
- Time risk filter blocks: `228`
- Entry exposure gate blocks: `0`
- Entry exposure gate long blocks: `0`
- Entry exposure gate short blocks: `0`
- MT5 invalid lot skips: `1`
- Stop exits: `202`
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
| long | 1172 | 6539.61 | 1.8493 | 29.35% | 41.39 | -9.3 | 13.02 |
| short | 0 | 0.0 | 0.0 | 0.0% | 0.0 | 0.0 | 0.0 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| breakeven_stop | 415 | -290.12 | 0.0 | 0.0% | 0.0 | -0.7 | 7.16 |
| gann_state_exit | 554 | 11114.68 | 4.5601 | 61.91% | 41.51 | -14.8 | 20.9 |
| stop | 202 | -4287.72 | 0.0 | 0.0% | 0.0 | -21.23 | 3.47 |
| time_exit | 1 | 2.77 | 2.77 | 100.0% | 2.77 | 0.0 | 4.0 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 23 | 24.53 | 1.3578 | 30.43% | 13.3 | -4.29 | 15.22 |
| 2018 | 123 | 108.59 | 1.228 | 24.39% | 19.5 | -5.12 | 12.0 |
| 2019 | 133 | 693.89 | 2.299 | 36.09% | 25.58 | -6.28 | 14.55 |
| 2020 | 153 | 751.27 | 1.7539 | 28.76% | 39.72 | -9.14 | 13.88 |
| 2021 | 138 | 139.73 | 1.1434 | 24.64% | 32.77 | -9.37 | 12.08 |
| 2022 | 134 | 256.58 | 1.2708 | 29.1% | 30.88 | -9.98 | 11.55 |
| 2023 | 144 | 379.45 | 1.4245 | 26.39% | 33.51 | -8.43 | 10.99 |
| 2024 | 145 | 717.25 | 1.5647 | 28.28% | 48.47 | -12.21 | 12.37 |
| 2025 | 140 | 1737.0 | 2.4463 | 33.57% | 62.51 | -12.91 | 15.46 |
| 2026 | 39 | 1731.32 | 6.1344 | 41.03% | 129.28 | -14.66 | 15.85 |

## Trade Duration

- 25th percentile bars held: `4.0`
- Median bars held: `9.0`
- 75th percentile bars held: `19.0`
- 90th percentile bars held: `29.0`
- 95th percentile bars held: `37.0`

## Excursion Diagnostics

- Average MFE/R: `1.2816`
- Average MAE/R: `-0.592`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.