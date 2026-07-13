# Production Backtest Engine Constitution

## Purpose

The backtest engine must preserve the strategy's accepted decision semantics while modeling the deployment context honestly enough to support research and forward testing. Engine sophistication is not the objective. The objective is a reproducible path from information availability to decision, order, fill, position state, risk, and portfolio result.

## Context Ownership

Phase 1 defines the asset, venue, timeframe, session, data, order, capital, cost, benchmark, validation, and production contracts. The engine implements that contract. It must not substitute a preferred venue model, benchmark, sizing method, stress multiplier, or evaluation frequency when the strategy requires a different one.

Every run freezes the context contract and reports any unsupported behavior before performance is interpreted.

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

Portfolio reporting uses mark-to-market state at the evaluation frequency declared by Phase 1. Realized-only reporting cannot hide open risk.

## Cost and Venue Contract

Costs are modeled from the declared venue and execution path. Every cost component has a source, unit, timing rule, and stress policy. Missing cost information remains an explicit limitation.

Venue feasibility covers quantity increments, price increments, minimums, maximums, order capabilities, position mode, leverage or margin rules, protective-order behavior, replacement behavior, cancellation behavior, and acknowledgement or rejection state. The engine must distinguish an economic signal from an order that can legally exist.

## Metrics and Benchmark Contract

The report exposes the evidence selected in Phase 1 at the portfolio, trade, state, chronology, and operational levels needed by the strategy. Metric computation must be stable, timestamp-aware, and reproducible.

Benchmark relevance is strategy-specific. The benchmark, comparison method, evaluation frequency, and acceptance interpretation are frozen before results. The engine cannot assume that one passive, cash, risk, or peer benchmark is correct for every asset and objective.

## Optimization Contract

The accepted unoptimized parent runs before search. Optimization changes only declared tunable parameters and preserves implementation constants and accepted semantics.

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

Phase 1 defines the engine requirements. Phase 1.5 proves Pine semantics manually. Phase 2 reproduces those semantics in Python and identifies platform boundaries. Phase 2.5 evaluates and optimizes only the faithful parent. Phases 3 and 4 compare mutations under the same execution contract. Final production gates add context-specific robustness, venue feasibility, forward reconciliation, and operations.

An implementation defect returns to its owning phase. Later performance cannot compensate for earlier semantic or temporal failure.

## New Engine Contract

Every engine family must declare its identifier, supported data and execution boundaries, warmup, information timing, state lifecycle, signal timing, order timing, fill policy, position policy, cost policy, sizing policy, diagnostics, parity fixtures, unsupported behavior, and regression tests.

An engine is ready for Mutation Lab only when another agent can reconstruct when information becomes available, when an action becomes legal, how state changes, and how the saved evidence proves those claims.
