# Whitebox, Hybrid, and Black-Box Perspectives

## Purpose

These perspectives describe where decision logic lives and what evidence is required. They are not strategy families and do not prescribe indicators, features, models, filters, or mutations.

## Shared Foundation

Every perspective begins with a frozen objective, market context, data contract, timing contract, execution model, capital model, benchmark policy, validation chronology, and acceptance criteria. Every decision must use information available before its action takes effect. Every promoted result must be reproducible in the live strategy engine.

The perspectives differ in how much decision logic is specified directly and how much is learned from data. They share the same integrity and production boundaries.

## Whitebox Perspective

In a whitebox strategy, the decision path is expressed through explicit state, rules, transitions, and parameters. A reviewer can reconstruct the reason for each action from the recorded inputs and strategy state.

Whitebox work is strongest when the hypothesis has a coherent mechanism, state can be observed locally, invalidation is explicit, and failure can be localized to a decision boundary. Its main risk is narrative overfitting: a plausible causal story can still be economically false or temporally invalid.

Whitebox evidence therefore requires semantic fidelity, bar-level auditability, chronological comparison, realistic execution, and refutation conditions declared before testing.

## Hybrid Perspective

In a hybrid strategy, an explicit parent delegates one bounded decision to a statistical representation. The parent remains responsible for the broader strategy identity and lifecycle.

Hybrid work is justified only when the parent is already strong, the remaining weakness is localized, another explicit rule has a worse evidence-to-complexity ratio, and the delegated decision has a lawful decision-time information set.

The hybrid layer must define its information, target, ambiguity, representation, validation, and live-action contracts before outcome-driven search. Offline survival authorizes implementation; live-engine reproduction authorizes promotion.

## Black-Box Perspective

Black-box work permits the internal relationship between admissible information and a bounded output to be learned with less direct human specification. Reduced interpretability increases the burden on chronology, leakage prevention, stability, calibration, operational monitoring, and forward reconciliation.

Mutation Lab uses black-box work as constrained viability discovery rather than direct opaque strategy promotion. A discovered relationship must become an auditable live-engine behavior before it can affect the parent.

## Complexity Rule

Complexity is earned by evidence. The permitted representation is the least complex form that can express the diagnosed mechanism, survive the declared chronology, fit the available sample, remain operationally feasible, and provide sufficient decision accountability.

No model class is preferred in isolation. Selection follows the decision contract and evidence.

## Mutation Rule

Mutation candidates come from the current parent's diagnosed behavior. The process identifies one failing decision boundary, states rival mechanisms, freezes decision-time information, defines a minimal refutable candidate, and compares it with the frozen parent.

A candidate from another strategy, historical lineage, explanatory document, or common research habit has no standing until current evidence independently derives it.

## LLM Role

The LLM acts as a contract and evidence reasoner. It should:

- freeze the strategy and validation context;
- identify missing evidence before interpretation;
- explain the observed economic engine with uncertainty;
- distinguish semantic, implementation, economic, and context failures;
- generate rival explanations before a candidate;
- derive the smallest lawful test;
- precommit acceptance and rejection conditions;
- preserve failed evidence and lineage;
- route to the correct phase boundary.

The LLM should not select strategy content from a catalog, infer hidden causal certainty, treat optimization as proof, or turn an offline relationship into a promoted rule.

## Phase Integration

Phase 1 defines the strategy-specific criteria and research record. Phase 1.5 creates and manually validates the canonical Pine strategy. Phase 2 proves Python parity. Phase 2.5 qualifies the faithful baseline. Phase 3 handles explicit decision-boundary mutations. Phase 4 handles bounded hybrid layers. Phase 4.2 performs constrained viability discovery. Phase 4.3 converts a completed lineage into a new creation brief when reseeding is justified.

All later phases follow `agents/docs/universal_mutation_constitution.md`.

## Production Boundary

Whitebox, hybrid, and black-box evidence can all fail in production through timing, data, execution, capital, operational, or regime mismatch. The final standard is aligned behavior across research, live decision computation, submitted orders, venue responses, fills, positions, risk controls, and monitoring under the declared deployment contract.
