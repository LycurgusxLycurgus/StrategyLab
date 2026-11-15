# Phase 1 decision: funding-state information over a 24-hour hold

**Selected: one low-percentile funding-state long strategy for the next controlled test.** Use 5m and 15m execution, allow overnight positions, and hold for 24 hours. This is my preferred next research approach, not a claim that we have found a profitable strategy. No new strategy returns or trades were evaluated in this phase.

Your clarification changes the opportunity set: execution bars do not have to determine holding duration. The previous same-day requirement is revoked for this new research; old campaigns and their failures remain unchanged. A week-long strategy is also eligible—there is no user-imposed five-day maximum. I selected the one-day horizon because it has a directly relevant information hypothesis, not because longer positions are prohibited.

## Why this is the best next test

The earlier campaigns accumulated 930 correlated economic evaluations, including 240 validation replays. The latest flow-fade candidate failed in every context and had negative raw-price PnL on its saved both-direction fills before costs. That argues against another small filter, stop adjustment or automatic inversion of the same setup. It does not reject a different predictor at a newly allowed horizon.

The selected predictor is **settled perpetual funding state**, an observable derivatives-market input. A [2026 BTC study](https://www.aijmr.com/papers/2026/4/1493.pdf) reports a 0.506% mean gross 24-hour spot log return after low-percentile funding events. It does not establish net perpetual-trading profit: it uses spot outcomes, settlement-boundary observations and overlapping historical data, and excludes a deployable cost/execution model. Its sample substantially overlaps our exposed history; independent replication was not established. The paper is saved with a SHA256 identity in `sources/funding_2026.pdf`.

This is enough to justify one bounded test. It is insufficient to promise an edge. The plausible explanation is that an unusually low funding state sometimes precedes a slower adjustment in derivatives/spot conditions. The counterexplanations are ordinary BTC drift, a few stress clusters, prior price reversal or an in-sample association that disappears after delay, occupancy, costs and later funding payments. We are testing those alternatives, not claiming a causal short squeeze.

## Alternatives considered

| Approach | Decision | Reason |
|---|---|---|
| Low-relative funding state, 24-hour long | Select one fixed candidate | Direct one-day BTC information hypothesis and locally audited inputs; net edge remains unknown. |
| Scheduled macro-news continuation | Defer | [New York Fed evidence](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1052.pdf) concerns announcement windows that include immediate repricing. Post-entry drift and accessible point-in-time consensus remain uncertain; event samples are sparse. |
| Weekly time-series momentum | Reserve, eligible under the new scope | [Liu and Tsyvinski](https://www.nber.org/papers/w24877) provide an older weekly predictive association. That is useful evidence, but does not establish modern net USD-M performance or justify relabeling a failed short-hold channel. Full-paper access was unavailable here. |
| Hedged cash-and-carry | Defer | [BIS research](https://www.bis.org/publications/working-paper-1087-crypto-carry) concerns both spot and futures legs. Our single-perpetual data/executor does not establish two-leg costs, financing, collateral and margin behavior. |
| Reported-liquidation reversal | Keep original proposal blocked | Continuous dual-clock liquidation history is still unavailable under its original contract. Funding data is not a replacement label for liquidation events. |

The ranking prioritizes transferable signal/horizon evidence, causal testability, input availability, cost headroom, complete decisions and distinctness. A smaller shortlist is deliberate: only one coherent candidate is selected, with two execution contexts. Controls and minor timing contexts are not additional strategies.

## Frozen candidate and controls

[RULES.md](RULES.md) is the complete behavioral specification; [protocol.json](protocol.json) freezes its identity and future comparison.

At each finalized funding event, rank its rate against the preceding 180 days, excluding the current event and resolving ties by midrank. Require complete coverage and at least 300 prior events. A rank at or below the tenth percentile creates a long opportunity. **No additional negative-rate filter applies.** The local feature audit found 551 low-state events after the basic warmup, including 113 with nonnegative numerical rates; deleting them would create an untested extra rule.

Wait for a complete execution bar after settlement, then the next legal grid open. Model approximately ten minutes of delay on 5m and thirty on 15m for an event just after an eight-hour boundary. Actual raw timestamps remain authoritative. Historical rate publication/receive latency is not measured, so this is an explicit timing assumption requiring challenge before deployment.

Allocate at most 10% of equity to fee-inclusive entry notional, keep quantity fixed, and exit 24 hours after the actual fill. There is one position, no pyramiding, no stop, no target and no same-day flattening. The low-notional risk contract replaces earlier stop-based sizing only for this new candidate. Suppress occupied decisions, reject occupied fill opens, and do not replace a position at its exit open. All subsequent signed funding payments count; the trigger settlement is not earned retroactively. Use hypothetical liquidation-price marks including estimated exit slippage and fee at censored cutoffs.

Two benchmarks challenge the information claim: the same rule triggered by a seven-day-old funding state, and continuous long BTC perpetual exposure with the same initial notional budget. Report cash, net return, paid/received funding, exposure and net PnL per notional-day. Neither benchmark is a perfect randomized counterfactual; the stale state can retain genuine regime information. A candidate must beat both the absolute cash gates and the declared control comparisons, not merely lose less than a benchmark.

## Data and sample feasibility

The existing loader verifies 5,112 actual funding events with one event in every eight-hour slot. Timestamps have 0–31ms jitter, which must not be erased for availability. There are 3,107 API marks, 1,996 verified five-minute mark-open proxies and nine verified daily mark-open repairs. Thus mark history is partly available directly and partly approximated; it is not wholly missing. Retain the accepted 1% adverse funding-cashflow buffer and disclose the proxy limitation.

The shared candidate/control warmup is 187 days, allowing the seven-day stale control the same preceding 180-day history. A calendar-only occupancy audit suggests about 70 non-overlapping opportunities in 2025 and 49 in January–August 2026 per grid, before annual censoring and price/size checks. These are feasibility counts, **not backtested trades, returns or independent observations**. The first 2022 fold has less eligible history. Details are in [DATA_FEASIBILITY.json](DATA_FEASIBILITY.json).

The future comparison can use the existing verified five-minute perpetual candles, their complete 15m aggregates and funding records. It needs a new bounded fixed-notional, 24-hour executor and independent semantic cases; the old stop/target/day-flat brokers cannot be assumed compatible unchanged. No new market dataset, account, subscription or source/test code was needed in this phase.

## Costs, advancement and stopping

Freeze 6bps fees per fill and slippage of 2bps base, 4bps standard stress and 20bps severe sensitivity: approximately 16/20/52bps round trip before funding. These are research assumptions. The primary source's gross number is not an expected net return under those costs.

The mandatory stress gate is the 20bps condition for this **new, preregistered** delayed funding-state experiment. The 52bps case remains a required reported sensitivity. The previous shock strategy's mandatory severe gate remains unchanged in its own failed campaign. There are no new returns to rescue here; the source gross effect may disappear at 52bps. If measured execution later demands higher costs, they become mandatory and the affected evidence must be rerun before acceptance.

The inherited absolute gates remain: positive base returns in both recent folds, at least 30 closed trades each and 100 combined, pooled net profit factor at least 1.05 and annual close-equity drawdown at most 10%. Add positive recent standard-stress return, improvement over the stale control, superior recent net PnL per notional-day versus continuous long, and positive recent closed net after removing the best contributing entry week. Full definitions, ranking and failure rules are in RULES.md. No eligible result means return to research without tuning or adding horizons.

The planned matrix is **90 annual evaluations**: candidate plus two controls, two execution grids, five folds and three costs. This phase ran **zero**. No parameter searches, mutations, short contexts or 48/72-hour variants are authorized implicitly.

## Protected evidence and handoff

All January 2022–August 2026 history is exposed screening evidence; published-source selection adds exposure rather than independent validation. Protected dates remain untouched. The new history requirement also exposes a future scheduling dependency: the previous November-only warmup cannot supply 187 days before the reserved December 1 final evaluation. A later frozen-finalist contract must resolve authorized warmup or a fresh evaluation schedule; no protected dates are accessed or redesignated now.

**Phase 1 research-readiness verdict: PASS_TO_PHASE_2, one fully specified native candidate, with modeling limitations carried forward. Phase 2 execution is not authorized by this research-only turn.** Data feasibility is accepted for modeled screening; exact publication latency, proxy-free settlement valuation and live margin execution are not certified. Economics and prospective profitability are untested. Pine parity is not applicable. The next action is the bounded Phase 2 implementation, independent cases and frozen comparison when the user elects to proceed.
