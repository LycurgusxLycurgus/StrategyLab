# BTC liquidity-excursion campaign

Status: **RETURN_TO_PHASE_1**.

Best observed fixed candidate: **15m-confirm_fvg-long**. Qualified selection: **none**.

These are development comparisons, not final out-of-sample performance. The final September–October 2026 window remains unfetched and unevaluated. Annual folds reset capital; summed returns are not a continuous compounded portfolio return.

## Fixed rules

Use the prior completed six-hour high/low and two-hour mean true range. A long sweep trades at least 0.1 ATR below the prior low and closes above it; shorts mirror this. Reclaim enters next open. Confirm waits at most 45 minutes for a close beyond the sweep candle's opposite extreme with a directional body of at least 0.5 ATR. Confirm+FVG additionally requires a strict directional three-candle gap on that confirmation bar. A new extreme invalidates pending confirmation. A new single-sided sweep replaces a remaining pending sweep. Dual sweeps are excluded. Stops sit 0.1 ATR beyond the sweep; targets are 2R; time exit follows six hours. The breakout control removes the sweep requirement and enters a close beyond the prior range.

One position, no pyramiding/reversals, 0.25% nominal equity risk including modeled stop costs, maximum 1× entry exposure. Fees are assumed at 6 bps per fill, adverse slippage at 2 bps (4 bps stress), plus historical signed funding. Missing historical API funding marks use official 5m mark-price opening quotes with a fixed 1% adverse funding-payment buffer. Exact settlement marks remain unverified. This fee is a research assumption, not a verified account quote.

## All 18 candidates

| Candidate | 2022 % | 2023 % | 2024 % | 2025 % | Jan–Aug 2026 % | PF | Trades | Max fold DD % | Qualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 15m-confirm_fvg-long | 1.51 | -2.00 | -3.09 | -0.39 | -1.13 | 0.806 | 265 | 3.15 | no |
| 15m-confirm_fvg-short | -0.07 | -3.73 | -0.37 | -4.43 | -0.32 | 0.718 | 284 | 5.08 | no |
| 15m-confirm_fvg-both | 1.44 | -5.96 | -3.65 | -4.50 | -2.36 | 0.730 | 531 | 6.45 | no |
| 5m-confirm_fvg-short | -5.83 | -12.19 | -9.29 | -13.56 | -11.70 | 0.632 | 1146 | 14.16 | no |
| 15m-confirm-long | -10.75 | -13.76 | -8.79 | -19.30 | -7.23 | 0.647 | 1463 | 19.76 | no |
| 5m-confirm_fvg-long | -10.91 | -17.13 | -10.50 | -19.66 | -10.96 | 0.541 | 1163 | 19.93 | no |
| 15m-confirm-short | -8.15 | -21.47 | -19.57 | -22.08 | -12.62 | 0.555 | 1513 | 22.14 | no |
| 5m-confirm_fvg-both | -14.67 | -24.12 | -17.14 | -27.21 | -18.91 | 0.599 | 2137 | 27.49 | no |
| 15m-confirm-both | -16.75 | -29.84 | -24.80 | -33.42 | -17.37 | 0.593 | 2676 | 33.44 | no |
| 5m-confirm-short | -24.46 | -39.91 | -44.39 | -50.10 | -30.66 | 0.536 | 3366 | 50.17 | no |
| 5m-confirm-long | -29.13 | -47.44 | -38.06 | -52.14 | -32.61 | 0.523 | 3464 | 52.58 | no |
| 5m-confirm-both | -39.72 | -63.63 | -62.95 | -73.12 | -49.32 | 0.541 | 6246 | 73.24 | no |
| 15m-reclaim-short | -56.76 | -70.57 | -64.71 | -73.29 | -53.05 | 0.432 | 5442 | 73.33 | no |
| 15m-reclaim-long | -63.77 | -70.80 | -65.47 | -75.65 | -56.87 | 0.414 | 5533 | 75.66 | no |
| 5m-reclaim-short | -72.69 | -86.04 | -85.77 | -89.08 | -71.04 | 0.354 | 7732 | 89.08 | no |
| 5m-reclaim-long | -82.18 | -83.66 | -83.38 | -91.02 | -75.37 | 0.350 | 7971 | 91.04 | no |
| 15m-reclaim-both | -81.67 | -88.39 | -85.56 | -91.98 | -77.74 | 0.435 | 10129 | 91.99 | no |
| 5m-reclaim-both | -94.63 | -97.46 | -97.45 | -98.86 | -92.52 | 0.360 | 15314 | 98.86 | no |

## Direction and timeframe

Each cell below is the best observed approach for that context under the frozen worst-fold/mean-fold ranking. Selecting the best of three remains selection exposure; it does not establish an edge.

| Context | Best observed approach | Worst fold return % | Mean fold return % | Qualified |
|---|---|---:|---:|---|
| 5m long | confirm_fvg | -19.66 | -13.83 | False |
| 5m short | confirm_fvg | -13.56 | -10.51 | False |
| 5m both | confirm_fvg | -27.21 | -20.41 | False |
| 15m long | confirm_fvg | -3.09 | -1.02 | False |
| 15m short | confirm_fvg | -4.43 | -1.78 | False |
| 15m both | confirm_fvg | -5.96 | -3.01 | False |

## Screening failures

- 15m-confirm_fvg-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- 15m-confirm_fvg-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- 15m-confirm_fvg-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- 5m-confirm_fvg-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-confirm-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-confirm_fvg-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-confirm-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-confirm_fvg-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-confirm-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-confirm-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-confirm-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-confirm-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-reclaim-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-reclaim-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-reclaim-short: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-reclaim-long: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 15m-reclaim-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- 5m-reclaim-both: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.

## Controls

- 15m-breakout_control-short: worst fold -46.68%; mean fold -37.83%; 3364 closed trades.
- 15m-breakout_control-long: worst fold -51.83%; mean fold -42.64%; 3570 closed trades.
- 5m-breakout_control-short: worst fold -72.98%; mean fold -60.96%; 4995 closed trades.
- 15m-breakout_control-both: worst fold -74.28%; mean fold -64.12%; 6934 closed trades.
- 5m-breakout_control-long: worst fold -78.45%; mean fold -63.27%; 5298 closed trades.
- 5m-breakout_control-both: worst fold -94.13%; mean fold -84.99%; 10293 closed trades.

## Phase gate and evidence

Phase 1 formalized a liquidity-excursion hypothesis; Phase 2 compared its three fixed approaches. A failed research screen returns to Phase 1. No Phase 4 search, Phase 5 mutation/final test, or Phase 6 paper graduation is implied. A qualifying prototype still requires Phase 3 acceptance and existing runtime authorization before optimization; this research engine is not registered with Mutation Lab.

`comparison.json` contains every fold, stress result, failure reason, detector funnel and code/data identities. `trials.jsonl` records all 240 annual economic evaluations. Each compressed result retains all trades, order/funding/censor events and bar-close marked equity. `visual_ledger.csv` joins original OHLC with the first two trades of each base fold; columns: trial, year, entry timestamp, local index, bar timestamp, O, H, L, C, stop, target, exit reason. Detector files preserve independent setup accounting.

Screen: both recent folds positive; at least 30 closed trades each and 100 combined; overall PF ≥1.05; no annual close drawdown above 10%; summed recent stress return positive. These are preliminary research rejection criteria, not a significance test. Serial dependence, 18-candidate selection, historical filter uncertainty and OHLC execution approximations remain relevant.

## Limitations

- Historical order-filter changes are unavailable; the captured current filters are a research feasibility envelope, not historical venue certification.
- OHLC last-trade prices and idealized next-open market execution cannot certify live trigger, latency, partial-fill, liquidation, mark-price or order-acknowledgement semantics.
- Stop-first dual-touch ordering is adverse. A funding credit with uncertain intrabar exit ordering is omitted; a debit is charged.
- Risk is nominal stop risk including fees and slippage; gaps and subsequent funding can exceed it. Exposure cap applies at entry.
- Each annual fold resets capital and position. Positions remaining at cutoff are censored and included through marked equity; no synthetic terminal liquidation.
- No live or paper orders, account integration, profitability guarantee or discretionary SMC replication claim.
- Missing API funding marks use official 5m mark opening quotes with a 1% adverse funding-notional buffer. This is a disclosed approximation; exact settlement marks and venue reconciliation remain unverified.

## Sources

- [Binance public data and checksums](https://github.com/binance/binance-public-data).
- [Binance funding history schema](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).
- [Binance instrument filter schema](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information).
- [Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). This supports trial accounting and caution, not profitability of this strategy.
