# Mutation Lab Run run_bb62a3abbe1b

- Family: `btc_intraday`
- Version: `BTC Intraday Parent | tuned atr_len=103, fast_len=26, max_no_cross=1, slow_len=104... | tuned atr_len=70, fast_len=30, stop_mult=5.1 | tuned breakeven_lock_r=1, breakeven_stop_enabled=True, breakeven_trigger_mfe_r=0.25, short_quality_gate_enabled=True...`
- Stage: `white_box`
- Verdict: `promotion_candidate`
- Dataset: `ds_d14d74e36d0d`

## Frozen Strategy Contract

This run freezes `ma_cross_atr_stop_v1` on `BTCUSDT` at `Binance Spot` / `15m`. The live parameters are `{"allow_long": true, "allow_short": true, "atr_len": 70, "atr_timeframe": "15m", "breakeven_lock_r": 1.0, "breakeven_stop_enabled": true, "breakeven_trigger_mfe_r": 0.25, "commission_pct": 0.04, "entry_mode": "crossover_only", "fast_len": 30, "initial_capital": 100000.0, "ma_kind": "sma", "max_no_cross": 1, "noise_lookback": 25, "quantity": 1.0, "short_quality_gate_enabled": true, "short_quality_gate_len_bars": 24960, "short_quality_gate_rule": "block_below_sma", "slippage_ticks": 2, "slow_len": 104, "stop_mult": 5.1, "tick_size": 0.01, "time_decay_bars": 40, "time_decay_exit_enabled": true, "time_decay_min_mfe_r": 0.35, "time_risk_block_utc_hours": [13, 15, 21], "time_risk_block_weekdays": [6], "time_risk_filter_enabled": true}`.

## Metrics

- Net PnL: `369712.51`
- Return %: `369.71`
- Profit Factor: `4.3941`
- Max Drawdown %: `2.13`
- Expected Payoff: `472.78`
- Total Trades: `782`
- Win Rate %: `73.4`
- Avg Win / Avg Loss Ratio: `1.5923`
- Approx Breakeven Win Rate: `38.58`
- Buy & Hold Return %: `70.69`
- Outperformance %: `299.03`

## Performance Interpretation

This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.

## Parent Comparison

- Profit Factor Delta: `3.0872`
- Net PnL Delta: `230411.02`
- Drawdown % Delta: `-8.31`
- Trade Count Delta: `-321`

## Single Mutation

- Summary: `breakeven_lock_r=1, breakeven_stop_enabled=True, breakeven_trigger_mfe_r=0.25, short_quality_gate_enabled=True...`
- Rationale: 

## Diagnostics

- Entries: `782`
- Long signals: `656`
- Short signals: `371`
- Short quality gate blocks: `294`
- Breakeven stop moves: `559`
- Time risk filter blocks: `244`
- Stop exits: `634`
- Reverse exits: `32`
- Time-decay exits: `116`
- Time exits: `0`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 500 | 230605.69 | 4.3814 | 74.0% | 807.58 | -524.61 | 17.12 |
| short | 282 | 139106.82 | 4.4154 | 72.34% | 881.55 | -522.17 | 14.98 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| reverse | 32 | -5316.04 | 0.2935 | 3.12% | 2208.5 | -242.73 | 16.06 |
| stop | 634 | 401335.56 | 6.3937 | 88.01% | 852.59 | -979.05 | 12.04 |
| time_decay | 116 | -26307.01 | 0.0255 | 12.93% | 45.96 | -267.29 | 40.0 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 13 | 2476.54 | 3.3368 | 76.92% | 353.64 | -353.27 | 21.62 |
| 2018 | 45 | 4893.49 | 2.4345 | 60.0% | 307.58 | -189.52 | 18.69 |
| 2019 | 90 | 11716.16 | 9.235 | 72.22% | 202.14 | -56.91 | 16.01 |
| 2020 | 96 | 9183.25 | 3.7233 | 71.88% | 181.96 | -124.89 | 17.76 |
| 2021 | 113 | 105635.44 | 4.666 | 76.11% | 1563.38 | -1067.23 | 14.92 |
| 2022 | 62 | 22405.67 | 4.6412 | 74.19% | 620.85 | -384.59 | 15.56 |
| 2023 | 110 | 23628.4 | 4.6359 | 70.91% | 386.24 | -203.08 | 16.42 |
| 2024 | 105 | 78620.77 | 5.7663 | 80.0% | 1132.33 | -785.49 | 14.95 |
| 2025 | 125 | 99637.81 | 3.8357 | 74.4% | 1449.19 | -1098.03 | 16.58 |
| 2026 | 23 | 11514.98 | 2.7544 | 69.57% | 1129.9 | -937.63 | 18.13 |

## Trade Duration

- 25th percentile bars held: `5.0`
- Median bars held: `11.0`
- 75th percentile bars held: `27.0`
- 90th percentile bars held: `40.0`
- 95th percentile bars held: `40.0`

## Excursion Diagnostics

- Average MFE/R: `0.3594`
- Average MAE/R: `-0.3719`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.