# BTC successor Phase 2: fixed comparison

**RETURN_TO_PHASE_1. None of nine candidate contexts qualifies for Phase 3.**

All 120 real annual/cost evaluations completed: nine candidate contexts and three clock controls, five folds, two cost conditions. The 112-test block passed before economics (42 new successor cases, 70 preserved cases). Root reconciled every saved payload, current/frozen identity, raw-to-terminal funnel, funding and marked accounting without discrepancies.

All nine candidates lost in 2025; eight also lost in January-August 2026. Shock reversal short made +0.257% in 2026, but lost 0.890% in 2025 and failed sample, profit-factor and stress gates. No control or least-losing row qualifies.

## Candidate results

Each fold resets a 100,000-USDT portfolio. Returns are marked net, not compounded; 2026 ends August 31. PF aggregates NET closed-trade profits/losses across all five base folds. Recent stress is the sum of separately reset 2025/2026 stress-fold returns.

| Context | 2022 % | 2023 % | 2024 % | 2025 % | 2026 % | Net PF | Closed trades | Recent trades | Max close DD % | Recent stress sum % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shock_reversal_2h-long | -1.646 | 0.885 | -0.818 | -2.631 | -0.301 | 0.663 | 208 | 78 | 2.792 | -3.267 |
| shock_reversal_2h-short | -1.536 | -2.889 | -0.958 | -0.890 | 0.257 | 0.567 | 223 | 74 | 2.978 | -1.013 |
| shock_reversal_2h-both | -2.757 | -2.094 | -1.865 | -3.708 | -0.413 | 0.593 | 416 | 148 | 3.937 | -4.797 |
| utc_noise_momentum-long | -8.876 | -6.324 | -12.642 | -15.797 | -7.738 | 0.568 | 2098 | 749 | 16.034 | -27.120 |
| utc_noise_momentum-short | -5.266 | -7.722 | -10.778 | -9.091 | -7.004 | 0.655 | 2077 | 761 | 11.456 | -20.164 |
| utc_noise_momentum-both | -13.168 | -13.035 | -19.739 | -22.506 | -12.674 | 0.619 | 3982 | 1435 | 22.580 | -41.791 |
| close_channel_24h-long | -9.378 | -1.690 | -4.180 | -7.439 | -3.717 | 0.732 | 1249 | 429 | 9.378 | -13.350 |
| close_channel_24h-short | -4.429 | -6.573 | -6.002 | -3.169 | -2.006 | 0.748 | 1180 | 422 | 7.007 | -7.520 |
| close_channel_24h-both | -13.397 | -8.061 | -9.939 | -10.380 | -5.657 | 0.740 | 2428 | 851 | 13.397 | -20.351 |

## Gate failures

The frozen screen requires positive recent base returns in BOTH folds, at least 30 closed trades in each and 100 combined, defined aggregate net PF >=1.05, every base-fold close drawdown <=10%, and positive summed recent stress returns. All nine fail return, PF and stress gates. Both one-direction shock contexts also fail recent sample gates; several momentum/channel contexts exceed the drawdown ceiling. These are economic failures after implementation validation, rather than missing trades.

- **shock_reversal_2h-long**: 2025: nonpositive base return; 2026: nonpositive base return; 2026: insufficient closed trades; insufficient recent total closed trades; combined profit factor below screen or undefined; recent stress return nonpositive.
- **shock_reversal_2h-short**: 2025: nonpositive base return; insufficient recent total closed trades; combined profit factor below screen or undefined; recent stress return nonpositive.
- **shock_reversal_2h-both**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- **utc_noise_momentum-long**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- **utc_noise_momentum-short**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- **utc_noise_momentum-both**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.
- **close_channel_24h-long**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- **close_channel_24h-short**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; recent stress return nonpositive.
- **close_channel_24h-both**: 2025: nonpositive base return; 2026: nonpositive base return; combined profit factor below screen or undefined; annual close drawdown above ceiling; recent stress return nonpositive.

## Actual trades

Below are the first three closed trades per both-direction candidate in the 2025 base fold, selected chronologically rather than by profitability. Prices include adverse slippage; net PnL includes both fees and signed funding. Full export: [trades.csv](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/runs/comparison-v1/trades.csv). Its 62,090 records span separate portfolios and cost scenarios; they are not independent market samples.

| Context | Side | Entry UTC | Exit UTC | Entry | Initial stop | Exit | Qty BTC | Net USDT | Exit |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| shock_reversal_2h-both | short | 2025-01-06T16:00:00+00:00 | 2025-01-06T18:00:00+00:00 | 102084.08 | 103546.10 | 101815.56 | 0.155 | 22.66 | time_exit |
| shock_reversal_2h-both | long | 2025-01-07T16:00:00+00:00 | 2025-01-07T17:45:00+00:00 | 97934.98 | 96708.90 | 96689.56 | 0.183 | -250.78 | stop |
| shock_reversal_2h-both | short | 2025-01-09T16:00:00+00:00 | 2025-01-09T18:00:00+00:00 | 94176.26 | 95877.60 | 92675.13 | 0.135 | 187.52 | time_exit |
| utc_noise_momentum-both | long | 2025-01-01T01:00:00+00:00 | 2025-01-01T01:30:00+00:00 | 94382.47 | 92791.10 | 93781.24 | 0.145 | -103.55 | noise_exit |
| utc_noise_momentum-both | long | 2025-01-01T03:00:00+00:00 | 2025-01-01T03:30:00+00:00 | 94083.21 | 92444.90 | 93781.24 | 0.141 | -58.47 | noise_exit |
| utc_noise_momentum-both | long | 2025-01-02T00:30:00+00:00 | 2025-01-02T02:00:00+00:00 | 94932.88 | 93991.10 | 94827.63 | 0.232 | -50.83 | noise_exit |
| close_channel_24h-both | short | 2025-01-01T09:00:00+00:00 | 2025-01-01T15:00:00+00:00 | 93379.52 | 94567.60 | 94166.03 | 0.189 | -169.92 | time_exit |
| close_channel_24h-both | long | 2025-01-01T21:00:00+00:00 | 2025-01-02T03:00:00+00:00 | 94786.25 | 93959.90 | 95203.76 | 0.260 | 76.43 | time_exit |
| close_channel_24h-both | long | 2025-01-02T05:00:00+00:00 | 2025-01-02T11:00:00+00:00 | 95717.84 | 94265.20 | 96674.56 | 0.157 | 130.56 | time_exit |

Intrabar stop timestamps use a bar-end proxy: OHLC cannot reveal the exact stop time. Other modeled open exits retain their opening timestamps. Cutoff-open positions remain censored and marked including an estimated exit fee; no terminal liquidation is invented.

## Costs and raw-to-terminal funnel

Both-direction base contexts across all five folds are shown below. Raw-price PnL is algebraic attribution of saved fills, NOT a zero-cost strategy replay. Closed net = raw-price PnL - slippage - paid fees + funding. Closed attribution excludes cutoff-open positions and can differ from marked fold PnL.

| Context | Raw intents | Cost rejects | Rejection % | Occupancy | Daily cap | Raw-price PnL | Slippage | Fees | Funding | Closed net PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shock_reversal_2h-both | 441 | 9 | 2.0 | 16 | 0 | -2262.63 | 2152.53 | 6457.59 | 34.90 | -10837.84 |
| utc_noise_momentum-both | 20391 | 1523 | 7.5 | 13279 | 1607 | 9881.19 | 22739.32 | 68217.96 | -45.97 | -81122.06 |
| close_channel_24h-both | 7184 | 1210 | 16.8 | 3545 | 1 | 7496.52 | 13666.19 | 40998.56 | -265.34 | -47433.56 |

The saved both-direction shock fills already lose on raw price movement before modeled slippage and fees. Noise momentum and close-channel fills have modest positive raw-price PnL, but slippage alone erases it before fees. The initial-stop guard controls estimated friction relative to the initial stop; it does not ensure that a short timed or trailing exit captures a large enough move. These are saved-fill attributions, not counterfactual strategy replays.

All 120 evaluations, including directions, active days/exposure, cost rejection rates, time/queued exits, close/adverse drawdowns, censoring and largest winning days, are expanded in [ECONOMIC_DETAILS.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/runs/comparison-v1/ECONOMIC_DETAILS.json). Concentration shares use positive daily PnL as denominator. Annual concentration appears in the fold table and per-fold closed PnL. First feature-ready, raw, direction/cost-admitted and filled timestamps appear in [comparison.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/runs/comparison-v1/comparison.json) with explicit definitions.

## Descriptive controls

Controls cannot be selected. They are not exposure-matched to six-hour strategies or calibrated statistical nulls. Cash return and drawdown are zero.

| Control | 2025 % | 2026 % | Net PF | Closed trades | Worst fold % |
|---|---:|---:|---:|---:|---:|
| clock_6h_long-both | -33.057 | -21.607 | 0.473 | 5728 | -33.057 |
| clock_6h_short-both | -22.443 | -17.062 | 0.572 | 5728 | -28.133 |
| clock_6h_alternating-both | -28.707 | -19.901 | 0.507 | 5728 | -29.074 |

## Evidence and limits

- [VALIDATION.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/VALIDATION.json): 112 passing cases; mocked orchestration is separate from economic runs.
- [data_audit.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/runs/comparison-v1/data_audit.json): 490,752 exact 5m price/turnover joins, 163,584 execution bars, 5,112 funding events, verified local archives and frozen extent.
- [ROOT_ARTIFACT_RECONCILIATION.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/ROOT_ARTIFACT_RECONCILIATION.json): 120 payload hashes, all current input/code identities, terminal/fill/funding/timing/risk and marked accounting; maximum equity residual below 0.000001 USDT.
- [trials.jsonl](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/runs/comparison-v1/trials.jsonl) and [cumulative_trials.jsonl](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/cumulative_trials.jsonl): 120 unique real evaluations appended as completed; full gzip broker payloads are beside the run ledger.
- [protocol.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/protocol.json), [AUTHORIZATION.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/AUTHORIZATION.json) and [INPUT_IDENTITIES.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-successor-phase2-20261028/INPUT_IDENTITIES.json): original behavior, explicit phase authorization and preserved prior identities.

Fees remain 6 bps/fill; adverse slippage 2 bps/fill base and 4 bps stress; signed funding includes a 1% adverse payment buffer. The initial-stop guard uses the same fixed stress reference in both conditions and rejects rather than widens invalid stops. OHLC fills, historical funding-mark proxies and historical venue-filter assumptions remain limitations; live execution is unverified.

2022-2024 are development history; 2025-August 2026 are reused screening history, not pristine out-of-sample data. Prior campaigns account for 690 economic evaluations including 240 validation replays, across 33 candidate and 12 benchmark contexts. This adds 120, yielding 810 cumulative evaluations. Contexts are correlated; unit fixtures and the mocked runner are not real economic trials.

These results reject the exact frozen BTC adaptations under this contract. They do not disprove all shock, momentum, channel or SMC strategies. Phase 3 has no entrant. Further work belongs to Phase 1 research under a new contract. No thresholds were tuned, no search/mutation ran, and no protected or future window was fetched.

## Reproduce validation

```powershell
$python = 'C:/Users/Baham/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python -m unittest app.btc_successor_tests app.btc_smc_tests app.btc_liquidity_tests
```

The saved run is immutable. Any separately authorized replay needs a new run ID and cumulative accounting; rerunning is unnecessary for this accepted result. Implemented runner: `python -m app.btc_successor_campaign --root artifacts/strategy-development/btc-successor-phase2-20261028 --run-id NEW_UNIQUE_ID`. No downloads or order submission occur.
