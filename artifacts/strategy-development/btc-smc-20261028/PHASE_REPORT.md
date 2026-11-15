# Bitcoin intraday SMC research outcome

**Implementation complete; no strategy qualified for a baseline.** All 15 candidate contexts failed the frozen research screen. Phase 2 returns to Phase 1; no accepted Phase 3 base, optimization, final test, paper or live promotion follows.

Three original systematic emulations are executable in `app/btc_smc.py`: confirmed BOS/order-block rejection, New York AM sweep/FVG rejection, and age-qualified Turtle Soup +1. Their exact causal rules and source/adaptation record are in [STRATEGY.md](STRATEGY.md). The comparison runner is `app/btc_smc_campaign.py`; independent cases are `app/btc_smc_tests.py`.

## What the comparison establishes

Data: checksummed Binance USD-M BTCUSDT perpetual candles from January 2022 through August 2026. Five annual portfolios reset capital; 2026 ends August 31. All these windows are development or reused chronological screening evidence, not a pristine final holdout. September 2026 onward was not fetched or evaluated by this campaign.

The fixed matrix used 15 candidate contexts and six breakout controls, each with five folds and two cost conditions: 210 evaluations. There were zero parameter searches and zero mutations. The previous 18-candidate failed campaign remains separate and counts as prior research exposure.

Orders use confirmed closes and next-open market proxies, 2R gross-price targets, 180-minute maximum hold, 0.25% modeled stop risk and 1x entry exposure cap. Base costs are 6 bps fees and 2 bps adverse slippage per fill; stress raises slippage to 4 bps. Signed funding retains verified official opening-price proxies and a 1% adverse funding buffer. Exact settlement and live execution are unverified.

## All fixed candidate results

PF is net closed-trade profit factor aggregated over the five reset portfolios. Fold returns below are percentages; they are not one compounded investment return. The selection order ranks worst-fold then mean-fold results only after qualification. No row qualified.

| Candidate context | Closed trades | Net PF | Worst fold % | 2025 % | Jan-Aug 2026 % |
|---|---:|---:|---:|---:|---:|
| 5m-silver_bullet-short | 5 | 1.467 | -0.250 | 0.077 | -0.250 |
| 5m-silver_bullet-long | 7 | 0.770 | -0.252 | 0.509 | -0.180 |
| 5m-silver_bullet-both | 12 | 0.991 | -0.429 | 0.586 | -0.429 |
| 15m-turtle_soup_plus1-long | 794 | 0.410 | -17.989 | -17.989 | -11.298 |
| 15m-turtle_soup_plus1-short | 850 | 0.410 | -18.591 | -18.591 | -4.637 |
| 15m-bos_order_block-short | 1161 | 0.484 | -21.682 | -21.380 | -7.576 |
| 15m-bos_order_block-long | 1178 | 0.392 | -23.633 | -23.633 | -12.196 |
| 15m-turtle_soup_plus1-both | 1614 | 0.419 | -32.267 | -32.267 | -14.774 |
| 15m-bos_order_block-both | 2321 | 0.441 | -39.301 | -39.301 | -18.583 |
| 5m-turtle_soup_plus1-long | 2605 | 0.324 | -51.199 | -51.199 | -38.069 |
| 5m-turtle_soup_plus1-short | 2730 | 0.323 | -51.217 | -51.217 | -31.572 |
| 5m-bos_order_block-long | 4415 | 0.372 | -65.653 | -65.653 | -46.319 |
| 5m-bos_order_block-short | 4581 | 0.391 | -65.675 | -63.283 | -50.499 |
| 5m-turtle_soup_plus1-both | 5093 | 0.330 | -74.759 | -74.759 | -56.373 |
| 5m-bos_order_block-both | 8510 | 0.389 | -86.297 | -85.222 | -71.388 |

The superficially strongest PF, 1.467 for short-only Silver Bullet, comes from **five trades** across the entire development range. Its 2026 return and recent summed stress return were negative, and it failed all required sample counts. It is not an eligible winner. The both-direction Silver Bullet model produced only 12 closed trades. The more active BOS/order-block and failed-breakout models lost after modeled costs.

The unchanged screen required positive 2025 and 2026 base folds, at least 30 closed trades in each and 100 combined, overall net PF at least 1.05, each fold close drawdown at most 10%, and positive summed recent stress return. Full per-context reasons, annual base/stress metrics and control metrics are in [comparison.json](runs/comparison-v1/comparison.json). These thresholds are preliminary rejection criteria, not statistical significance tests.

## Detector opportunity and lifecycle accounting

These counts describe the frozen emulations, not expert-labelled recall or actual institutional orders. Detection runs independently of position occupancy. Directions are detector directions before portfolio filtering; they are not additional independent strategy trials.

| Detector | Long signals | Short signals | Signals / calendar day | Terminal accounting |
|---|---:|---:|---:|---|
| 15-bos_order_block | 1236 | 1215 | 1.4384 | 14859 BOS = 2792 rejected + 12067 blocks; blocks = 2451 signals + 2504 invalidated + 6768 expired + 344 replaced + 0 pending |
| 15-turtle_soup_plus1 | 795 | 850 | 0.9654 | 5133 breakouts = 1645 signals + 3488 failed reclaim + 0 pending |
| 5-bos_order_block | 5030 | 5209 | 6.0088 | 45972 BOS = 9997 rejected + 35975 blocks; blocks = 10239 signals + 10433 invalidated + 7316 expired + 7987 replaced + 0 pending |
| 5-silver_bullet | 7 | 5 | 0.0070 | 2428 sweeps = 12 signals + 989 invalidated + 167 expired + 689 replaced + 571 session ended; 215 intermediate gaps |
| 5-turtle_soup_plus1 | 2632 | 2765 | 3.1673 | 17059 breakouts = 5397 signals + 11662 failed reclaim + 0 pending |

Portfolio suppression, direction exclusions, venue sizing/gap rejections, funding, exit reasons and censored positions remain in each full broker ledger. Detector and closed-trade counts differ because of that explicit execution layer. No independent source-fidelity or real-chart recall acceptance is claimed.

## Validation and identity

- 70 automated tests passed: 27 new independent detector/orchestration tests plus the existing 43 broker/data cases. They cover accepted/rejected long/short cases, 5m/15m operation, confirmed pivots, prefix/future mutation causality, stops, expiry, New York winter/summer sessions, incomplete ranges, the exclusive 11:00 entry boundary, next-open timing, invalid input and immutable-run/trial accounting.
- The campaign unit test mocks data loading and simulation. Actual economic acceptance uses the separate completed 210-evaluation run and audited archives; mocked output is not market evidence.
- Fresh data audit: 490,752 five-minute candles, 163,584 complete fifteen-minute aggregates, and 5,112 funding events. Old broker/data/helper/test modules still match their prior accepted hashes.
- Root verified all 210 saved result hashes, all 210 unique trial keys and matching cumulative records, unchanged protocol/code/data identities, and 141,700 saved closed-trade records for entry/holding clocks, quantities and P&L totals. Those records include overlapping long/short/both contexts and stress replays, not unique independent trades.
- Detector lifecycle totals above balance. Exact code/settings/data identities are in the run identity files; the verification record is [VERIFICATION.json](VERIFICATION.json). Full payloads retain trade, order/funding and equity ledgers; [visual_ledger.csv](runs/comparison-v1/visual_ledger.csv) supplies original OHLC around initial trades.
- Root performed the implementation review as explicitly requested; no separate planner or reviewer was spawned. Terra implemented the two source files; Luna authored the independent test suite using the user-approved complete task packet.

## Separate verdicts and stopping point

| Boundary | Verdict |
|---|---|
| Reference correctness against this design | PASS: constructed cases, causality and source review |
| Discretionary-source fidelity | NOT CLAIMED: original systematic emulations |
| Historical data | PASS within the frozen audited archive/proxy contract |
| Execution | PASS only for the tested bounded OHLC model; real broker semantics unverified |
| Economics | FAIL TO QUALIFY: all 15 candidate contexts |
| Pine / TradingView | NOT APPLICABLE: Python-only scope |
| Paper / live | NOT EVALUATED; no orders or connector |

Research questions returned to Phase 1: can a source-supported entry model deliver enough price excursion to cover the assumed round-trip costs; can the staged FVG model retain an adequate sample without hindsight; and does a distinct hypothesis warrant a new preregistered comparison? This run does not answer those questions by loosening its filters or retuning failed prototypes. No further trials were performed.

## Reproduce

Use the verified interpreter commands in [STRATEGY.md](STRATEGY.md). The accepted evidence run is `comparison-v1`; reusing that ID must fail. A new ID creates additional explicitly recorded research exposure. Source/version/license context and external references are in the same strategy document.
