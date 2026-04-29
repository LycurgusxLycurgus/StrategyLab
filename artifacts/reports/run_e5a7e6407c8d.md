# Mutation Lab Run run_e5a7e6407c8d

- Family: `btc_intraday`
- Version: `BTC Intraday Parent | tuned atr_len=103, fast_len=26, max_no_cross=1, slow_len=104... | tuned atr_len=70, fast_len=30, stop_mult=5.1`
- Stage: `white_box`
- Verdict: `research_survivor`
- Dataset: `ds_d14d74e36d0d`

## Frozen Strategy Contract

This run freezes `ma_cross_atr_stop_v1` on `BTCUSDT` at `Binance Spot` / `15m`. The live parameters are `{"allow_long": true, "allow_short": true, "atr_len": 70, "atr_timeframe": "15m", "commission_pct": 0.04, "entry_mode": "crossover_only", "fast_len": 30, "initial_capital": 100000.0, "ma_kind": "sma", "max_no_cross": 1, "noise_lookback": 25, "quantity": 1.0, "slippage_ticks": 2, "slow_len": 104, "stop_mult": 5.1, "tick_size": 0.01}`.

## Metrics

- Net PnL: `139301.49`
- Return %: `139.3`
- Profit Factor: `1.3069`
- Max Drawdown %: `10.44`
- Expected Payoff: `126.29`
- Total Trades: `1103`
- Win Rate %: `30.55`
- Avg Win / Avg Loss Ratio: `2.9706`
- Approx Breakeven Win Rate: `25.19`
- Buy & Hold Return %: `70.69`
- Outperformance %: `68.62`

## Performance Interpretation

This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.

## Single Mutation

- Summary: `atr_len=70, fast_len=30, stop_mult=5.1`
- Rationale: 

## Diagnostics

- Entries: `1103`
- Long signals: `656`
- Short signals: `665`
- Stop exits: `510`
- Reverse exits: `592`
- Time exits: `1`

## Side Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| long | 547 | 121120.49 | 1.5633 | 33.64% | 1826.91 | -592.37 | 200.26 |
| short | 556 | 18181.0 | 1.0761 | 27.52% | 1679.93 | -592.68 | 169.81 |

## Exit-Reason Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| reverse | 592 | 515719.19 | 7.6577 | 56.93% | 1760.18 | -303.77 | 244.37 |
| stop | 510 | -376069.86 | 0.0 | 0.0% | 0.0 | -737.39 | 116.02 |
| time_exit | 1 | -347.84 | 0.0 | 0.0% | 0.0 | -347.84 | 124.0 |

## Period Decomposition

| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 38 | -1946.16 | 0.7914 | 36.84% | 527.51 | -388.8 | 217.61 |
| 2018 | 105 | 2432.73 | 1.162 | 32.38% | 513.24 | -211.51 | 192.92 |
| 2019 | 119 | 8957.27 | 1.8636 | 26.89% | 604.03 | -119.22 | 215.91 |
| 2020 | 127 | 4681.18 | 1.3177 | 28.35% | 539.39 | -161.94 | 170.59 |
| 2021 | 139 | 43301.12 | 1.4159 | 37.41% | 2834.94 | -1196.73 | 184.45 |
| 2022 | 125 | 6762.67 | 1.1485 | 28.8% | 1453.24 | -511.84 | 184.92 |
| 2023 | 139 | 12993.67 | 1.4549 | 25.18% | 1187.34 | -274.65 | 166.63 |
| 2024 | 118 | 21475.94 | 1.2788 | 30.51% | 2736.59 | -939.53 | 202.11 |
| 2025 | 138 | 40304.42 | 1.3506 | 34.06% | 3303.81 | -1263.46 | 185.18 |
| 2026 | 55 | 338.65 | 1.0099 | 27.27% | 2300.82 | -854.34 | 122.82 |

## Trade Duration

- 25th percentile bars held: `44.0`
- Median bars held: `102.0`
- 75th percentile bars held: `242.0`
- 90th percentile bars held: `417.0`
- 95th percentile bars held: `602.0`

## Excursion Diagnostics

- Average MFE/R: `2.0731`
- Average MAE/R: `-0.8483`

MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.

## Full-Whitebox Diagnostic Queue

Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.