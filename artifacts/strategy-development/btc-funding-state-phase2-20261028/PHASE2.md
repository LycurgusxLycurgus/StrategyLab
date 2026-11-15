# BTC funding-state Phase 2

**Completed 90/90 fixed annual evaluations. Neither candidate context qualifies: RETURN_TO_PHASE_1.**

The implementation and evidence passed validation. The economic hypothesis did not meet the frozen recent-performance and control gates. No Phase 3 candidate is selected, and no parameters, costs or horizons were changed after results.

## What was tested

One native candidate, `low_percentile_funding_long_24h_v1`, enters long after a settled funding rate ranks in the lowest historical decile. The rate may be numerically positive. Ranking uses the previous 180 days with exact midrank ties, excludes the current event, and requires complete history. A shared 187-day warmup supports the seven-day stale-information control.

Execution uses 5m or 15m bars after a completed-bar observation and another legal grid open: a settlement just after 08:00 permits modeled entry at 08:10 or 08:30 respectively. Positions use 10% fee-inclusive entry notional, fixed quantity, a 24-hour time exit, and no stop, target or daily flattening. They cross midnight and weekends. All subsequently owned funding payments count; the entry-trigger settlement is not received retroactively.

Controls are the same 24-hour rule using seven-day-old funding classification, and continuously held long BTC perpetual with the same initial notional budget. The continuous benchmark remains open at each annual cutoff and is valued with estimated adverse exit slippage and fee. Those marks are not actual closing trades.

The frozen matrix is three roles × two grids × five folds × three cost conditions =90 evaluations. Fees are 6bps per fill; adverse slippage is 2bps base, 4bps mandatory standard stress, and 20bps severe sensitivity. These are research assumptions, not measured executable quotes. Existing signed funding and the 1% adverse funding-payment buffer apply. See [protocol.json](protocol.json) and the immutable [Phase 1 rules](../btc-information-reset-phase1-20261028/RULES.md).

## Candidate results

All returns are percentages of separate annual accounts starting at 100,000, using the specified 10% entry allocation. 2022 has a partial year after warmup; 2026 covers January–August. These annual returns are not a continuously compounded portfolio. PF pools net closed-trade wins/losses across the five folds.

| Grid | 2022 net | 2023 net | 2024 net | 2025 net | 2026 net | Pooled net PF | Recent closed trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| 5m | 0.671% | 3.196% | 4.278% | -1.122% | -1.837% | 1.244 | 70 + 49 |
| 15m | 0.794% | 2.832% | 4.739% | -0.099% | -1.477% | 1.335 | 70 + 49 |

Both contexts pass the predeclared sample-count, pooled-PF and annual close-drawdown screens. Both fail positive net returns in each recent fold, positive recent standard-stress return, improvement over the stale control, improvement over continuous-long exposure efficiency, and positive recent closed net after removing the best entry week. A favorable pooled PF cannot override those failed requirements.

| Grid | Recent base sum | Recent standard-stress sum | Recent severe-sensitivity sum | Stale-control recent base sum | Net after removing best recent entry week |
|---|---:|---:|---:|---:|---:|
| 5m | -2.959% | -3.418% | -7.090% | -0.855% | $-3,747.85 |
| 15m | -1.576% | -2.049% | -5.740% | -0.649% | $-2,372.48 |

Recent sums add two independently reset annual returns and are not compounded returns. Severe sensitivity was reported as frozen; it was not the mandatory promotion gate for this new campaign. The candidate already fails at base and standard stress.

## Does fresh funding information improve the result?

It does not clear either frozen comparison. Current funding-state timing loses more than the stale-state timing over the two recent folds. It also produces worse net PnL per notional-day than continuous long BTC exposure. This normalized measure divides net account profit by integrated held notional-days; it is not a portfolio return from retrospectively resizing the benchmark, and the controls are not randomized causal nulls.

| Grid | Candidate recent net bps / notional-day | Continuous-long recent net bps / notional-day |
|---|---:|---:|
| 5m | -25.292 | -4.094 |
| 15m | -13.408 | -4.124 |

All controls, including their early positive years, remain visible below. Controls cannot qualify as winners.

| Control | Grid | 2022 base | 2023 base | 2024 base | 2025 base | 2026 base |
|---|---|---:|---:|---:|---:|---:|
| Seven-day stale state | 5m | 0.488% | 1.151% | 1.109% | 0.248% | -1.104% |
| Continuous long | 5m | -2.136% | 14.045% | 10.046% | -1.222% | -1.198% |
| Seven-day stale state | 15m | 0.527% | 1.338% | 1.564% | 0.322% | -0.971% |
| Continuous long | 15m | -2.141% | 14.035% | 10.043% | -1.239% | -1.200% |

## Cost and price contribution

The following diagnostic uses the saved base fills and quantities for the two recent annual accounts. It is not a counterfactual rerun with different costs or sizing. Raw-price PnL uses the original entry/exit candle opens. Funding is subsequent realized signed cash flow, including the adverse buffer.

| Grid | Raw-price PnL before slippage | Executed slippage | Gross after slippage | Paid fees | Funding | Net |
|---|---:|---:|---:|---:|---:|---:|
| 5m | $-1,070.04 | $468.12 | $-1,538.16 | $1,404.36 | $-16.83 | $-2,959.35 |
| 15m | $321.92 | $470.26 | $-148.34 | $1,410.78 | $-17.08 | $-1,576.19 |

The 5m saved price contribution is already negative before costs. The 15m contribution is slightly positive before slippage, but becomes negative after slippage before fees. Reducing fees alone does not establish a recent profitable result on these fixed fills. There is no retrospective negative-rate filter, shorter entry delay, alternative horizon or short-side rescue in this campaign.

## Trades and verification

Saved evidence contains **3,090 closed-trade records**, including **1,542 candidate records**, plus **30 censored continuous-benchmark positions**. The candidate represents 257 distinct funding triggers across its two execution grids; cost replays and grid versions overlap and are not independent samples.

[Closed trades](runs/comparison-v1/trades.csv) show entry/exit UTC, quantity, raw/slipped prices, fees, funding, net PnL and information clocks. [Open benchmark positions](runs/comparison-v1/open_positions.csv) explicitly have no actual exit and show their cutoff mark instead. Compressed annual payloads preserve full order/funding ledgers and every equity observation.

The examples below are the first chronological candidate trades in each base context, chosen without filtering for outcome. They demonstrate the actual overnight holding behavior.

| Grid | Entry UTC | Exit UTC | Quantity BTC | Entry after slippage | Exit after slippage | Funding | Net PnL |
|---|---|---|---:|---:|---:|---:|---:|
| 5m | 2022-08-19T16:10:00+00:00 | 2022-08-20T16:10:00+00:00 | 0.466 | 21423.5839 | 21313.7364 | $1.00 | $-62.13 |
| 15m | 2022-08-19T16:30:00+00:00 | 2022-08-20T16:30:00+00:00 | 0.465 | 21481.4954 | 21319.8352 | $1.00 | $-86.11 |

The coordinated suite passed **186 tests: 42 independent new funding tests plus 144 existing regressions**. Root reconciliation independently rebuilt signal ranks and eligible entry clocks from funding history, quantities from the capital budget, payments from actual owned settlements, and every cash/equity/adverse observation from original OHLC and position lifecycles. It checked all 90 payload hashes, the complete cumulative matrix, exit slippage/fees on censored positions, notional-day denominators, pooled PF, drawdown and entry-week contributions. **5,889,024 equity observations reconciled**, every context had valid modeled execution, and all 59 frozen input identities remained unchanged. See [TEST_RESULTS.json](TEST_RESULTS.json) and [RECONCILIATION.json](runs/comparison-v1/RECONCILIATION.json).

## Meaning and limits

The test rejects this exact fully specified research adaptation under its frozen screening contract. It does not falsify every funding predictor or the source paper's gross spot-return association. Relative to that paper, this experiment changes the instrument's return, historical sample, full-history warmup, legal entry delay, overlapping-event occupancy, sizing, exit and cash-flow costs. The positive older folds and pooled PF make recent deterioration especially important; no cause of that change is established by this comparison.

All 2022–August 2026 history is exposed development/screening evidence. The cumulative ledger now contains **1,020 correlated economic evaluations**, including 240 earlier validation replays; the independent reconciliations are not extra economic runs. No protected market dates, new market downloads, parameter searches, model training, live orders or purchases occurred. Settlement receive timing remains assumed; some funding marks are verified mark-open proxies; historical venue filters and collateral behavior are modeled, not a certified live adapter.

The 187-day warmup conflict with the earlier prospective final-validation schedule remains recorded in Phase 1. No final holdout or warmup permission was inferred or exercised here.

## Decision and reproducibility

**RETURN_TO_PHASE_1. Selected: none. Phase 3 not started.** Retire the tested 24-hour low-funding long rule for this contract rather than promoting its positive full-history aggregate. Another research cycle requires new instruction; there is no automatic tuning, inversion or extra horizon.

From the repository root, the bundled Python runtime runs `-m unittest app.btc_funding_tests app.btc_flow_tests app.btc_liquidity_tests app.btc_smc_tests app.btc_successor_tests`. Campaign entry is `-m app.btc_funding_campaign --root artifacts/strategy-development/btc-funding-state-phase2-20261028 --run-id <unique-id>`. Existing run IDs cannot be overwritten. A replay requires authorization and adds 90 recorded economic exposures; this report does not initiate one.
