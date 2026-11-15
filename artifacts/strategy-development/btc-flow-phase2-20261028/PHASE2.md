# BTC executed-taker-pressure Phase 2

**Completed: 120/120 fixed annual evaluations. No candidate qualifies for Phase 3; return to Phase 1.**

We tested a new observable-flow hypothesis using the existing verified Binance USD-M BTCUSDT history. The original liquidation proposal remains blocked and unchanged. This campaign measures aggressive executed quote volume; it does not recover liquidations or replicate the opening-ten-second paper.

## What actually ran

The candidate fades a completed 60bps price impulse only when same-direction signed taker quote pressure exceeds the prior-30-complete-day 99th percentile. It uses a known bar-open anchor, a completed-hourly 2ATR stop, one whole execution bar of entry delay, at least 60bps remaining target room, and a two-hour maximum hold. Entries stop at 22:00 UTC; all positions flatten by 23:45 UTC. The paired price-only control removes the flow filter while preserving the other rules.

The matrix contains 5m and 15m execution, long/short/both directions, five annual folds and base/severe costs: six candidate contexts plus six controls, 120 evaluations. Base costs are 6bps fee plus 2bps adverse slippage per fill; severe costs retain fees and use 20bps slippage per fill. Historical funding and a 1% adverse funding-mark buffer apply. Costs and OHLC fills are declared research assumptions, not measured executable quotes. Full rules and all promotion gates were frozen before results in [protocol.json](protocol.json) and [PHASE1.md](PHASE1.md).

## Candidate results

Returns below are net of modeled fees, slippage and funding. 2026 means January–August only. The stress column sums two separately capital-reset annual percentage returns; it is not a compounded investment return. Profit factor pools net closed-trade wins and losses across all five folds.

| Frame | Direction | 2025 net | 2026 net | Recent trades 2025 / 2026 | Pooled net PF | Recent severe sum | Qualified |
|---|---|---:|---:|---:|---:|---:|---|
| 5m | long | -1.016% | -1.221% | 67 / 41 | 0.673 | -5.478% | No |
| 5m | short | -2.215% | -1.249% | 62 / 55 | 0.504 | -5.426% | No |
| 5m | both | -2.738% | -2.599% | 120 / 94 | 0.588 | -10.126% | No |
| 15m | long | -1.857% | -0.007% | 57 / 41 | 0.684 | -5.452% | No |
| 15m | short | -1.668% | -1.611% | 45 / 29 | 0.473 | -5.259% | No |
| 15m | both | -3.610% | -1.677% | 100 / 69 | 0.574 | -10.649% | No |

Every candidate fails positive returns in both recent folds, pooled net profit factor of at least 1.05, and positive summed recent severe-cost return. The 15m long context also has only 98 recent trades against the required 100; 15m short has 74 recent trades and only 29 in 2026 against the required 30 per recent fold. No candidate fails the 10% annual close-equity drawdown ceiling. None is promoted for losing less than another context.

## Does flow add anything here?

The filtered candidate has a less-negative summed recent base return than its matched price-only control in all six contexts. That is a descriptive improvement, not a profitable edge or proof of predictive information: the filter changes trade frequency, exposure and portfolio occupancy. In particular, the 5m long candidate is worse than its control in 2026 alone despite its smaller two-fold summed loss.

| Frame | Direction | Candidate recent base sum | Price-only recent base sum |
|---|---|---:|---:|
| 5m | long | -2.236% | -2.562% |
| 5m | short | -3.464% | -6.984% |
| 5m | both | -5.337% | -9.715% |
| 15m | long | -1.864% | -10.287% |
| 15m | short | -3.280% | -10.929% |
| 15m | both | -5.287% | -20.250% |

The failure is not explained solely by fees. On the saved both-direction base fills across the five separately reset annual accounts, raw entry/exit-price PnL is already negative. This diagnostic keeps actual saved quantities, admissions and fills; it is not a rerun of a zero-cost strategy.

| Frame, both directions | Raw-price PnL before slippage | Slippage | Fees | Funding | Net PnL |
|---|---:|---:|---:|---:|---:|
| 5m | $-8,793.89 | $5,057.55 | $15,172.64 | $-13.44 | $-29,037.53 |
| 15m | $-6,729.95 | $3,875.01 | $11,625.02 | $-25.20 | $-22,255.17 |

These rows are alternative contexts, not positions in one combined portfolio. The evidence rejects this exact tail-pressure fade under the fixed rules. It does not establish that all information-driven strategies fail, nor justify automatically reversing the rules into a momentum strategy.

## Trades and verification

There are **19,695 closed-trade records** across every context, year and cost condition, including **6,148 candidate records**. Directions and cost conditions overlap, so these are not independent market events. [All trades](runs/comparison-v1/trades.csv) include UTC entry/exit clocks, quantities, slipped and raw prices, stop, anchor, fees, funding, net PnL and exit reason. The compressed annual artifacts additionally retain every equity observation and order event.

The following are the first recorded base trades in each long/short candidate context, selected chronologically rather than for favorable outcomes. Intrabar exit timestamps represent the candle-resolution upper boundary, not a measured fill clock.

| Frame | Side | Entry UTC | Exit UTC | Entry price after slippage | Exit price after slippage | Net PnL | Exit |
|---|---|---|---|---:|---:|---:|---|
| 5m | Long | 2022-01-31T00:50:00+00:00 | 2022-01-31T02:50:00+00:00 | 36924.1634 | 36918.9447 | $-29.32 | time_exit |
| 5m | Short | 2022-02-01T09:10:00+00:00 | 2022-02-01T09:30:00+00:00 | 38999.9285 | 38584.1953 | $132.17 | anchor |
| 15m | Long | 2022-02-02T15:00:00+00:00 | 2022-02-02T16:15:00+00:00 | 37704.5294 | 37229.7526 | $-250.46 | stop |
| 15m | Short | 2022-01-31T17:15:00+00:00 | 2022-01-31T19:15:00+00:00 | 38415.3954 | 38585.3855 | $-81.29 | time_exit |

The coordinated regression block passed **144 tests**, including 32 independently authored new flow tests and 112 previous regressions. The original 490,752 five-minute flow records align with the checksum-verified candles; 163,584 complete 15m bars and 5,112 funding events were used. Root reconciliation checked all 120 payload hashes, complete trial/cumulative matrices, every trade's legal timing and intraday limits, quantity/risk/fee arithmetic, funding ledgers, PnL/cash equity, finite curves and recomputed close-equity drawdowns. All positions ended flat and all input identities remained unchanged. See [TEST_RESULTS.json](TEST_RESULTS.json) and [RECONCILIATION.json](runs/comparison-v1/RECONCILIATION.json).

## Source route and limits

[PHASE1.md](PHASE1.md) and [SOURCES.json](SOURCES.json) record the additional provider search and the explicit change of hypothesis. No new market files, credentials, purchases, accounts, training, parameter searches or orders were needed. The verified bar data provides a workable alternative to the unavailable continuous dual-clock liquidation series. It does not remove the original liquidation proposal's data requirement.

All January 2022–August 2026 history is exposed research/screening history, not pristine out-of-sample evidence. Prior exposure was 810 economic evaluations including 240 validation replays; this campaign adds 120, bringing the recorded total to 930 correlated evaluations. All previously protected windows remain unfetched and unevaluated by this task. Bar availability, OHLC execution, the severe-cost level and historical venue filters remain modeling limitations.

## Decision

Return to Phase 1. Do not tune this exact pressure-reversal family or advance its least-losing context. The next research decision should require a different information mechanism and a credible cost budget before more economic testing. Additional liquidation-data purchases would test a different, still-blocked hypothesis; these results neither require nor justify buying that access. No further campaign is started here.

To reproduce the exact fixed comparison, use the bundled Python runtime from the repository root with `-m app.btc_flow_campaign --root artifacts/strategy-development/btc-flow-phase2-20261028 --run-id <new-unique-id>`. A replay adds 120 exposed evaluations and must be recorded as such; this report does not request one. The existing run ID is protected against overwrite.
