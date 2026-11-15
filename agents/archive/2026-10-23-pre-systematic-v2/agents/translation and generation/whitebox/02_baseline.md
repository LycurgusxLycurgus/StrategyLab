# 02 Data Integrity and Reference Execution Prompt

For new `reference_v1` work, Phase 2 binds source observations to an auditable normalized dataset, freezes the full execution contract, and verifies the registered Python reference on that exact identity. It is not a Pine port or optimization stage. Never infer full venue/broker behavior from the bounded reference adapter.

The supported reference envelope is explicit: decisions on completed bars, earliest submission at next bar open, fixed quantity, static ATR stop from decision, optional risk-multiple target, adverse stop-first ordering, censored cutoff, and decision-only feedback. Any required behavior outside this contract remains blocked until implemented and independently tested.

## Python2Pine reference-first data/execution evidence

Audit original input before sorting or deduplication. Preserve raw bytes when
available, source/venue identity, audit report, raw hash, exact normalized CSV
hash, and immutable quality-manifest hash. Report identical duplicate rows;
reject conflicting duplicate timestamps, non-finite or invalid OHLCV, and
descending raw timestamps. A stale normalized hash or changed quality manifest
invalidates dependent evidence. Legacy datasets without original raw audit stay
`UNVERIFIED`; an explicit normalized-only contract may accept only that narrow
scope as `PASS_WITH_LIMITATIONS`, never original-data PASS.

Record the exact execution contract in the spec and validate its values before
running. Require current semantic, data and execution gates for fixed runs; save
decisions, intents, full ledger, trace, metrics, limitations, and dataset/spec/
code/execution identities. Keep source fidelity, semantic correctness, data
integrity, execution fidelity, and economics independent. A run is not parity,
profit qualification, target acceptance or production approval.

## Origin/operation duties — `reference_v1`

Consume the accepted rule provenance and source-fidelity scope without changing
origin or silently refining entry/exit meaning. For both native and translated
references, bind the same observation/event history to the same execution
driver. For mixed origin, trace preserved and translated groups through that
shared driver; do not introduce an origin-specific broker.

Classify newly exposed timing, fill, risk or management assumptions as
operational_formalization or strategic_adaptation with parent/child rule IDs.
A missing source exit is an explicit specification decision, not a simulator
default or permission to optimize. Return a meaning-changing assumption to
Phase 1/1.5; return an economic adaptation to the accepted-parent authorization
boundary before search. Exercise delayed-known-time and lifecycle negatives
from applicable A-F cases.

The execution handoff records source/known/decision/submission/fill links,
ambiguity policy, transformations and independent fidelity/reference/data/
execution verdicts. Reject any early action or omitted execution rule; do not
use a working backtest to close a source-fidelity issue. Pass the exact frozen
execution package, not a tuned variant, to Phase 2.5.

## Legacy Pine-to-Python parity (`legacy_pine_v1` only)

PROMPT
"""
Before executing this phase, read `agents/translation and generation/agents/codex_phase_operator.md`,
its Phase 2 section, and `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Record the
accepted source, dataset/settings/proof identities, applicable issue IDs and
dispositions in the parity ledger; a relevant missing or stale input blocks the
port.

Resolve the saved workflow. For `reference_v1`, perform only the Python2Pine
data-audit/execution task above: verify raw and normalized hashes, exact
execution contract and current semantic/data/execution gates; run the frozen
reference; preserve all separate verdicts and limitations. Never ask for
TradingView export or create a Pine prerequisite. For `legacy_pine_v1`, continue
the original Pine port/parity requirements below and preserve their status
meanings.

You are the Phase 2 port and parity engineer inside Mutation Lab. Implement the frozen Pine strategy in the Mutation Lab Python engine and parent schema, then prove the port against every in-scope Phase 1 criterion.

## Input Gate

Stop unless Phase 1.5 is `ACCEPTED_FOR_PHASE_2` and the following frozen inputs exist:

- accepted Pine script and content hash;
- Phase 1 criteria/checklist revision;
- Phase 1 research record;
- Phase 1.5 manual review and explicit user verdict;
- screenshot manifest;
- portability package;
- timestamped fixtures;
- complete TradingView settings freeze.
- Pine2Python analysis and local-runtime artifact IDs;
- the expected/observed parity-dashboard comparison and screenshot hash;
- `TRADINGVIEW_SIGNATURE_MATCH` with matching dataset fingerprints.

Reject any request to port from an explanation, screenshot set, public page, obsolete prototype, or unaccepted Pine revision.

## Port Contract

Create a criterion-to-code mapping before implementation. Every required behavior must identify its Pine source location, Python implementation location, parent-schema representation, standard trace field, diagnostic output, parity evidence, and permitted tolerance or approved divergence. Generate the StrategyLab trace through `/api/versions/<version_id>/python-trace` and compare it through `/api/pine2python/parity-comparisons`.

Preserve the accepted causal identity, state lifecycle, timeframe ownership, bar-confirmation semantics, signal timing, order lifecycle, sizing, costs, capital behavior, and audit observability. Separate tunable strategy parameters from implementation constants. The parent schema may expose only controls that belong to the accepted Pine contract. New strategy ideas belong to later mutation phases.

Translate Pine platform behavior deliberately. Any platform-specific mechanism must be emulated or replaced by an explicitly approved equivalent. A difference caused by the Python engine is not acceptable merely because the language or platform changed.

## Parity Test Design

Create `artifacts/strategy-development/<strategy_id>/phase2_parity_ledger.json` and `phase2_port_report.md`.

Test parity on aligned market data whenever the required data can be exported or reproduced. When data feeds cannot be identical, use the frozen timestamped fixtures and the predeclared tolerance contract. Do not invent tolerances after seeing a discrepancy.

Evaluate parity at the strategy-decision level, not only through headline metrics. Every required criterion must be assigned one parity state:

- `EXACT_MATCH`;
- `WITHIN_PREDECLARED_TOLERANCE`;
- `APPROVED_INTENTIONAL_DIVERGENCE`;
- `FAIL`;
- `BLOCKED`.

Exact semantic criteria require exact agreement. Tolerance applies only to the numerical boundary declared in Phase 1. Intentional divergence requires a written mechanism, proof that causal identity is preserved, and explicit approval. A visually similar equity curve cannot compensate for mismatched states, signals, orders, or lifecycle transitions.

The parity ledger must connect each criterion to reproducible evidence. Include input data identity, timestamps, Pine observations, Python observations, comparison method, result, discrepancy cause, and resolution. Preserve diagnostics needed to inspect the Python strategy bar by bar.

## Implementation Integrity

Audit both implementations for future leakage, repainting, same-bar ambiguity, unavailable decision-time data, warmup differences, session or timezone drift, missing-data handling, price rounding, order-state sequencing, position replacement, and mark-to-market behavior. Resolve implementation defects before interpreting economic results.

Run focused tests for the new engine path, parent schema, migration behavior, report fields, and parity fixtures. Existing saved versions must not be silently changed by the new family.

## Completion Gate

Phase 2 reaches 100 percent parity completion only when:

- every required checklist criterion has a closed parity result;
- no required criterion is `FAIL` or `BLOCKED`;
- all tolerance results use Phase 1 bounds;
- all intentional divergences are documented and approved;
- the Python engine and parent schema preserve the accepted strategy identity;
- diagnostics can reconstruct the required fixtures;
- the unoptimized Python parent is frozen with a content and parameter hash;
- tests for the implemented contract pass.

If parity fails because the Python code is wrong, remain in Phase 2. If the accepted Pine contract is contradictory or incomplete, return to Phase 1. If Pine behavior fails manual acceptance after closer inspection, return to Phase 1.5. Do not optimize around a parity failure.

The valid outcomes are `PARITY_ACCEPTED`, `PORT_REPAIR_REQUIRED`, `RETURN_TO_PHASE_1`, `RETURN_TO_PHASE_1_5`, or `PORT_BLOCKED`.

Write the port report with these sections:

1. Frozen Pine Reference
2. Frozen Python Parent
3. Criterion-to-Code Map
4. Data and Execution Alignment
5. State and Signal Parity
6. Order and Position Parity
7. Numerical Tolerance Results
8. Intentional Divergences
9. Integrity Audit
10. Test Results
11. Unresolved Discrepancies
12. Phase 2 Verdict
"""
