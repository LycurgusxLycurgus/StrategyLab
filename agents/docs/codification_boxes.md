# Strategy Codification Constitution

## Purpose

This document defines first principles for converting trading intent into executable, auditable research without prescribing strategy content. It contains no mutation catalog, feature catalog, model catalog, or worked strategy pattern. The active phase prompts derive every implementation and mutation from the current strategy contract and evidence.

## Codification Boundary

A strategy is codified when its decisions can be reproduced from declared inputs, state, timing, and execution rules. Descriptive plausibility is not codification. A chart that looks coherent is not sufficient. A profitable backtest is not sufficient. The model must expose what was knowable, when it was knowable, how state changed, why an action became legal, and how the position lifecycle followed.

Codification quality has four independent dimensions:

- semantic fidelity to the declared strategy;
- temporal integrity at every decision point;
- execution realism under the declared venue contract;
- evidentiary reproducibility across implementations and validation periods.

Failure in one dimension cannot be repaired by strength in another.

## Whitebox Codification

A whitebox strategy expresses its decision path through explicit states, rules, parameters, and transitions. Its implementation is auditable when a reviewer can reconstruct each decision from recorded inputs and state.

Whitebox quality depends on causal coherence, local observability, explicit invalidation, stable state ownership, and parameters that retain strategy meaning. Interpretability does not prove correctness; it makes correctness and failure testable.

Whitebox mutation begins only after a faithful baseline qualifies. Each candidate changes one conceptual dependency and is derived from a diagnosed boundary in the current parent. The candidate must state its mechanism, rival explanations, decision-time information, active first test, and rejection condition before execution.

## Hybrid Codification

A hybrid strategy preserves an explicit parent and delegates one bounded decision to a statistical layer. The delegated decision must have a frozen information contract, target contract, ambiguity policy, representation contract, validation design, and live-engine action.

The statistical layer remains subordinate to the parent identity. It earns complexity only when simpler representations cannot express the hypothesis and the available evidence can support the expanded search space. Every live decision must remain reproducible and operationally legal.

Offline evidence authorizes implementation only. Promotion requires live-engine reproduction against the frozen parent.

## Black-Box Viability

Black-box viability work asks whether a strong parent contains a stable relationship that explicit diagnosis has not yet represented. It begins with a precommitted decision boundary, admissible information set, target, chronology, untouched evaluation boundary, complexity budget, and rejection policy.

Outcome inspection cannot define the feature contract retroactively. Full-sample fit cannot replace chronological stability. An opaque relationship cannot become strategy behavior until it is converted into an auditable live contract that reproduces its evidence.

## Strategy Creation

Creation begins with one bounded market context and a criteria/checklist that defines correctness before implementation. Research verifies current platform mechanisms and inspects public precedent. The evidence then selects either greenfield Pine creation or licensed source adaptation. Neither route has default priority.

TradingView is the canonical proving ground for chart-based strategies. The user manually accepts the Pine implementation through checklist-linked screenshots and state evidence on the declared asset and timeframe. Only the accepted Pine version can become the source for a Python port.

## Port Fidelity

Porting is a semantic reproduction task. Every required criterion maps from Pine behavior to Python behavior, diagnostics, and parity evidence. Exact semantics require exact agreement. Numerical tolerance is valid only when declared before comparison and limited to a known platform or data boundary.

Economic optimization begins only after parity closes every required criterion. Optimization may tune declared parameters inside accepted semantics. It may not repair a broken port or redefine the strategy.

## Evidence-Derived Mutation

The mutation process follows one chain:

1. Freeze the parent and context.
2. Describe the observed economic engine.
3. Locate one decision boundary that departs from the declared objective.
4. State direct evidence and uncertainty.
5. Generate rival causal explanations.
6. Select one explanation that can be tested with decision-time information.
7. Define one minimal active candidate and precommitted rejection boundary.
8. Compare it with the frozen parent.
9. Persist the result.
10. Promote only live-engine survivors.

The chain may end without a candidate. Insufficient evidence is a valid conclusion.

## Universal Evidence Rules

- Context owns metric meaning, benchmark relevance, sample sufficiency, cost stress, and forward-validation duration.
- Chronology owns validation order.
- Decision timing owns information admissibility.
- The frozen parent owns comparison.
- The accepted strategy identity owns the mutation boundary.
- The live engine owns promotion.
- The user-owned criteria/checklist owns semantic acceptance.

No universal indicator, filter, model, threshold, benchmark, stress multiplier, trade count, or paper duration can replace those contracts.

## Failure Routing

Contract ambiguity returns to Phase 1. Pine semantic or visual failure returns to Phase 1.5. Python fidelity failure returns to Phase 2. Economic weakness remains a preserved research result after Phase 2.5. Explainable decision-boundary work belongs to Phase 3. Bounded statistical work belongs to Phase 4. Constrained relationship discovery belongs to Phase 4.2. A structurally capped but informative lineage may reseed through Phase 4.3.

Failure artifacts remain evidence. Family deletion is a separate user-directed repository decision.

## Production Boundary

Research promotion is not production readiness. A final candidate must survive strategy-specific chronological robustness, adverse execution assumptions, venue feasibility, forward decision and order reconciliation, operational risk controls, and monitoring. These gates are derived from the declared strategy and deployment context rather than fixed universal values.
