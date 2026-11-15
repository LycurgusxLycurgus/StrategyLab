# Production Backtest Engine Constitution

## Purpose

The backtest engine must preserve the strategy's accepted decision semantics while modeling the deployment context honestly enough to support research and forward testing. Engine sophistication is not the objective. The objective is a reproducible path from information availability to decision, order, fill, position state, risk, and portfolio result.

## Context Ownership

The reference-first Phase 0/1 specification defines the asset, venue, timeframe, session, source/provenance, data, decision, order, capital, cost, benchmark, validation, and production contracts. The engine implements that contract. It must not substitute a preferred venue model, benchmark, sizing method, stress multiplier, or evaluation frequency when the strategy requires a different one. Existing `legacy_pine_v1` versions keep their prior Pine-derived contract unless explicitly migrated.

Every run freezes the context contract and reports any unsupported behavior before performance is interpreted.

For the bounded `reference_v1` controls, the declared contract is explicit:
next-bar-open intent, fixed quantity, static ATR risk from decision time,
optional risk-multiple target, adverse stop-first OHLC ambiguity, censored
cutoff, and decision-only feedback. This narrow envelope is not a universal
broker simulator. Missing or unsupported behavior (including fill-aware
decisions and venue-specific lifecycle) remains blocked when the strategy
requires it; do not silently supply a convenient default.

## Decision-Time Integrity

Every input has an availability timestamp. Every strategy decision has an evaluation timestamp. Every order action has an earliest legal submission timestamp. The engine must preserve this ordering.

Completed data may influence only decisions made after completion. Confirmed historical structures may influence only bars on which confirmation was available. Imported timeframe data must respect its own completion and publication boundary. Missing or revised data must follow an explicit policy.

Future information, retrospective state placement, and same-period path knowledge are prohibited unless the declared execution model supplies that information before the action.

## Order and Fill State

Signals and orders are separate states. The engine records when a setup becomes valid, when an order becomes legal, when it is submitted, when it can fill, when it expires or is cancelled, and how later protective or exit actions replace existing state.

Intraperiod ambiguity follows a declared policy derived from available market data. The engine must not choose the favorable path after observing the result. Any approximation is recorded as an execution-model limitation and included in adverse validation.

## Position and Portfolio State

The engine maintains explicit cash, position quantity, average price, realized result, unrealized result, equity, exposure, margin or collateral use, and active order state at every evaluation boundary required by the contract.

Risk and sizing use information available before order submission. Quantity obeys the declared instrument and account constraints. Unsupported order sizes or state transitions are rejected visibly rather than normalized silently.

Portfolio reporting uses mark-to-market state at the evaluation frequency declared by Phase 0/1. Realized-only reporting cannot hide open risk. The reference control preserves open positions and unfilled intents as censored at the cutoff rather than assuming liquidation.

## Cost and Venue Contract

Costs are modeled from the declared venue and execution path. Every cost component has a source, unit, timing rule, and stress policy. Missing cost information remains an explicit limitation.

Venue feasibility covers quantity increments, price increments, minimums, maximums, order capabilities, position mode, leverage or margin rules, protective-order behavior, replacement behavior, cancellation behavior, and acknowledgement or rejection state. The engine must distinguish an economic signal from an order that can legally exist.

## Metrics and Benchmark Contract

The report exposes the evidence selected in Phase 1 at the portfolio, trade, state, chronology, and operational levels needed by the strategy. Metric computation must be stable, timestamp-aware, and reproducible.

Benchmark relevance is strategy-specific. The benchmark, comparison method, evaluation frequency, and acceptance interpretation are frozen before results. The engine cannot assume that one passive, cash, risk, or peer benchmark is correct for every asset and objective.

## Optimization Contract

The accepted unoptimized parent runs before search. For `reference_v1`, search additionally needs explicit baseline-backed authorization: objective, finite values for existing parameters, time-aware chronological train/holdout split, and a declared objective metric. Selection uses training only; holdout stays untouched. A child must remain inside that authorization and re-earn impacted semantic/data/execution evidence. Optimization changes only declared tunable parameters and preserves implementation constants and accepted semantics.

Search design, chronology, untouched evidence, parameter bounds, selection objective, and complexity penalty are declared before optimization. Selection favors stable evidence under the strategy contract. An isolated optimum cannot override weak neighboring behavior, failed chronology, unsupported execution, or an incomplete sample.

Optimization cannot repair parity, state, timing, or order defects. Those defects return to their owning phase.

## Robustness Contract

Robustness challenges the exact saved candidate under adverse but plausible conditions derived from deployment uncertainty. The strategy contract determines data partitions, parameter perturbation, cost and fill adversity, market coverage, operational disruptions, and forward-evidence requirements.

No universal multiplier, fold count, trade count, date duration, or market count can prove robustness for every strategy. Each requirement must have a mechanism tied to the declared deployment risk.

## Engine Do Constitution

- Freeze data, strategy, parameter, execution, capital, and benchmark identities for every run.
- Record information availability and action timing.
- Expose unsupported behavior and approximation boundaries.
- Preserve rejected orders and invalid state transitions as diagnostics.
- Maintain mark-to-market portfolio truth.
- Make results reproducible from saved inputs and versions.
- Compare candidates under the same parent contract.
- Provide state and order traces sufficient for parity and forward reconciliation.

## Engine Do-Not Constitution

- Do not infer favorable intraperiod ordering.
- Do not fill an order before it can be submitted.
- Do not use future-confirmed state at an earlier timestamp.
- Do not hide open risk through realized-only accounting.
- Do not normalize illegal orders silently.
- Do not change costs, benchmarks, chronology, or acceptance rules after results.
- Do not treat parameter search as generalization evidence.
- Do not promote a strategy whose intended actions cannot be represented by the deployment venue.

## Phase Integration

Active schedule: systematic_v2. Phase 1 classifies the requested approach, prepares at least three fresh complete candidate dossiers in research-only mode by default, and freezes source-transfer/measurement, context matrix/criteria/budgets/chronology; fewer than three supported candidates leaves research incomplete. Human approval of the new batch/protocol precedes Phase 2, with a visible transition when combined work was explicitly approved. Phase 2 separates measurement validity and incremental signal evidence from net strategy economics, implements and compares causally verified fixed candidates, and advances only one meeting every frozen requirement. Failure retains useful components as research-only and proposes at least three fresh next-batch candidates with an evidence-backed new/revision/mix rationale and explicit approval before testing; Phase 3 consolidates that candidate's qualifying rules/contexts and accepts independent semantic cases, original/normalized data, supported execution and fixed base economics. Phase 4 performs baseline-authorized parameter search; Phase 5 unifies structural mutation, revalidation and child-authorized reoptimization, then freezes one finalist for once-only final holdout and required target acceptance. Phase 6 requires an actual paper adapter and forward reconciliation before a graduation verdict. Earlier runtime authorization holdouts remain protected in addition to the campaign final holdout; use development folds only within authorized training.

Existing runtime selectors remain reference_v1 and legacy_pine_v1. Historical phase numbers retain their historical meaning; continuing an old campaign requires explicit mapping, not silently relabeling artifacts. A new schedule is not a new engine capability or broker adapter.

Signal tests must use legal availability/entry times, defensible matched controls, independent-event/dependence-aware uncertainty and complete selection accounting on development data only. Lower loss from less exposure is not proven information value, and wider stops are not captured-move headroom. Invalid proxies block conclusions; a promising component does not grant full-strategy acceptance.

An implementation defect returns to its owning boundary. Later performance cannot compensate for earlier semantic or temporal failure. No universal threshold replaces predeclared context-specific criteria.

## New Engine Contract

Every engine family must declare its identifier, supported data and execution boundaries, warmup, information timing, state lifecycle, signal timing, order timing, fill policy, position policy, cost policy, sizing policy, diagnostics, parity fixtures, unsupported behavior, and regression tests.

An engine is ready for Mutation Lab only when another agent can reconstruct when information becomes available, when an action becomes legal, how state changes, and how the saved evidence proves those claims.
