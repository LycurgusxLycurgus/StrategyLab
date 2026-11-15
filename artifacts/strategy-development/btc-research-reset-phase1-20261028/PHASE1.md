# BTC Phase 1 research reset

**Decision: move to new information-driven research. Retire SMC as the project default and stop varying the three failed successor rules.**

**Phase gate: STOP -- no new candidate is ready for Phase 2.** This completes the requested reassessment; it does not abandon Bitcoin research or prove that every SMC, reversal or trend system is impossible. The current evidence supports ending these branches of the research budget, rather than spending further trials on altered thresholds. Conditional research directions below are not accepted strategies.

## What the tests taught us

The accepted Phase 2 run contained 120 real evaluations and zero qualifiers. All 150 files in its saved artifact manifest still match. Current/prior engine and input hashes also match. This reassessment reads saved fills and verifies additional archived fields; it runs zero new strategy simulations. Detailed diagnosis: [DIAGNOSIS.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/DIAGNOSIS.json).

The following are the five-fold BASE both-direction portfolios. Raw-move bps are arithmetic per-trade price returns before modeled entry/exit slippage; they are not size-weighted strategy returns or a zero-cost replay. Holding times for intrabar stops use the existing bar-end timestamp proxy.

| Tested strategy | Closed trades | Mean raw price move bps | Median hold min | Median initial stop bps | Net PF |
|---|---:|---:|---:|---:|---:|
| shock_reversal_2h-both | 416 | -2.975 | 120 | 179.62 | 0.593 |
| utc_noise_momentum-both | 3982 | 0.540 | 60 | 149.50 | 0.619 |
| close_channel_24h-both | 2428 | 1.952 | 360 | 160.45 | 0.740 |

Nominal round-trip costs are about 16 bps base and 20 bps stress before signed funding. Actual costs vary with fill notionals; the table is a diagnostic comparison, not a trade-admission estimate. Stops were already much wider than the 80 bps minimum implied by the new friction guard. The guard protects initial stop geometry; it cannot manufacture predictive movement or make short timed/trailing exits cover costs. All three both-direction saved streams lost after slippage even before fees.

Noise momentum made many rapid exits (median 60 minutes; 3,116 noise exits of 3,982 closed trades). Channel held to its 360-minute deadline in 1,699 of 2,428 closed trades; only 31 closed via queued trail decisions. Those observations identify what actually happened; they do not select a new exit window or prove that longer holds would work. No clock, volatility, regime or winning-subset search was performed.

## Retire or vary?

| Family | Decision now | Reason | What would reopen it? |
|---|---|---|---|
| Tested SMC/liquidity emulations | Retire as default and allocate no new variant trials | Several distinct causal formulations failed; indicator labels supply no independent net edge | A genuinely different observable mechanism, complete point-in-time rules and credible cost-aware evidence; expert adjudication if faithful discretionary replication is claimed |
| Two-hour shock reversal | Retire exact formulation; no sigma/timer tweak | Negative saved raw-price PnL before trading costs | Independent evidence for a distinct shock mechanism/horizon, not a better-looking historical threshold |
| UTC noise momentum | Retire BTC conversion; no clock/band/rearm search | Marginal captured raw movement and high turnover; SPY session economics did not transfer | BTC-specific timing/information mechanism with plausible executable movement after costs |
| Six-hour close channel | Retire exact conversion; do not optimize the least-losing row | Multiday trend findings did not validate this intraday management; all directional contexts failed | A separately supported holding/predictor contract; a daily/multiday source is not evidence for a shorter hold |

SMC has not been universally falsified. Our tests concern designed systematic emulations and their specified execution. They do justify a practical research decision: the label no longer gets preference, and new proposals must earn their place by mechanism and evidence. Price structure may later be a controlled feature if a new complete hypothesis justifies it; adding SMC filters to a failed model does not by itself create that hypothesis.

## New directions, ranked for further research

These are research priorities chosen by the root, not a three-strategy shortlist. Terra ranked settled funding highest among already-local inputs; the root puts flow research first because a new information set better addresses the observed weak captured movement, while funding's shorter-horizon evidence is especially weak. Neither ranking is based on a new backtest.

### 1. Aggressive trade flow: first research priority, conditional

The relevant BTC-perpetual study examines quarter-hour opening flow at ten-second resolution and 4–12-hour outcomes; it supplies no ready net-cost strategy. Our five-minute aggregates cannot reconstruct that feature. Source: [Kim and Hansen v2](https://arxiv.org/abs/2607.09426v2).

Root verified all 490,752 local rows in 56 checksum-verified archives: taker-buy base/quote volume and trade counts satisfy side, unit and timestamp bounds. The available 5m signed share can be defined as `(2*buy_base-base)/base` when `base>0`, observed only after bar close. It is not L2 order-book imbalance, trader identity, a liquidation feed or proof of informed money. See [DATA_FEASIBILITY.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/DATA_FEASIBILITY.json) and [official schema](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).

Next qualification must choose between acquiring and auditing suitable finer trade records for the source mechanism, or treating 5m pressure as a new adaptation with independent sign/horizon justification. Complete entries/exits, delay and overlapping-event policy remain unresolved; therefore no candidate is promoted. The required control asks whether flow adds anything beyond lagged price/volume and the settlement/clock pattern after legal delayed entry and costs.

### 2. Settled funding state: defer an intraday trading candidate

The funding study reports 4h and 8h gross spot effects below our nominal cost reference, with its strongest association at 24h. That is neither an executable perpetual strategy nor evidence for a profitable shorter hold. Source: [Memon et al.](https://www.aijmr.com/papers/2026/4/1493.pdf).

Existing funding records describe settlements, not an archived pre-settlement forecast. Reopening requires reliable availability timing, incremental information beyond recent returns and settlement-clock controls, a complete funded execution model and credible intraday net magnitude. A 24-hour or multiday route changes the current shorter-hold contract and must be declared separately. A funding filter applied to the old strategies is an additional untested hypothesis.

### 3. Cost-aware forecasting: defer; provenance and scope unresolved

A forecasting paper reports promising selected configurations, but calls its input Binance USD-M futures beginning in 2017. Binance's own futures launch announcement is from 2019. The lineage needs raw endpoint/manifests or author clarification; this is a provenance conflict, not an accusation of fabrication. [Paper,section 3.1](https://arxiv.org/html/2606.00060v1), [official launch](https://www.binance.com/en/support/announcement/detail/360033314152).

Training/model-selection adds substantial decisions and exposure; the repository's learned-strategy roadmap remains plan-only. This task authorizes no training. A calibrated expected-return-versus-cost rule would also be materially different from the stop-distance guard already tested. The source cannot justify merely adding another cost filter to failed signals.

A separate cost-matched study reports negative net results despite positive predictive correlations. Its finite scope supports caution, not a proof that every model must fail. [Zeng et al.v1](https://arxiv.org/abs/2608.25348v1).

## Why this Phase 1 stops before another comparison

The repository Phase 1 contract permits a smaller shortlist or STOP when no complete defensible candidate is supported. Here, creating three fully specified strategies would require unsupported choices about sign, horizon, entry threshold and data transfer. A list of interesting indicators is not a strategy, and repeating a published headline with our own stops would repeat the previous transfer problem.

The stop applies to promotion, not to the completed research assessment. No Phase 2 matrix is authorized: zero accepted candidates, zero economic cells, zero parameter/mutation budget. [protocol.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/protocol.json) freezes that state. The next work is Phase 1 information-set qualification under [NEXT_RESEARCH_HANDOFF.md](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/NEXT_RESEARCH_HANDOFF.md). Only after its evidence gaps are resolved should complete causal rules, a finite comparison matrix, controls and economic gates be frozen.

## Controls, chronology and proof status

Any later accepted candidate must retain honest adverse execution, signed funding, marked cutoffs and the existing capital/risk discipline. No lower fee tier, maker fill assumption, wider universe or longer hold is silently substituted. Prior absolute screen criteria remain a documented reference; any changed context needs explicit justified gates before outcomes, not relaxed thresholds after failure.

All 2022–August 2026 history is exposed. Local cumulative economic exposure remains 810 evaluations, including 240 validation replays, across 42 candidate contexts plus 15 controls; these are correlated portfolios, not independent discoveries. Published tests are additional qualitative selection exposure, not locally reproduced trials. Earlier protected September–October 2026 data and the reserved November 2026 warmup/December 2026–April 2027 final window remain unfetched and unevaluated by this task.

| Proof axis | Current status |
|---|---|
| Research reassessment and source checking | Complete; 13 registered sources, critical claims checked by root |
| New local aggregate-field feasibility | PASS for captured 5m schema/value/checksum census |
| Exact ten-second signal input | Missing from accepted local dataset |
| New complete strategy semantics/execution | NOT_IMPLEMENTED; behavior/data gaps explicitly unresolved |
| New source replication | NOT_CLAIMED |
| New economic evidence | NOT_EVALUATED; 0 new evaluations |
| Phase 2 readiness | STOP; 0 complete selected candidates |
| Pine/live/paper target | NOT_APPLICABLE to this research task |

Sources, their limitations, versions and access metadata are in [SOURCES.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/SOURCES.json) and [RESEARCH.md](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-research-reset-phase1-20261028/RESEARCH.md). No third-party code was copied/executed; no newly archived PDF-byte identity is claimed. Prior source PDFs remain hash-preserved. Read-only fill attribution and raw-field checks require no new automated suite; unchanged runtime tests are prior evidence, not tests of these unimplemented leads.
