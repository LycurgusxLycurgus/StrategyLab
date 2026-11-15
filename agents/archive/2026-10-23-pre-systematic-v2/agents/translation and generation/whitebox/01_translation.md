# 01 Strategy Definition, Research, and Criteria Prompt

Phase 0/1 is the default intake for new StrategyLab work and belongs to the Python2Pine `reference_v1` route. It turns an idea, an inspectable open-source strategy/indicator, or a prior-lineage lesson into a falsifiable executable specification and evidence plan. Pine is a possible source or later target, never a prerequisite for new reference research. Preserve `legacy_pine_v1` for existing Pine-first lineages.

## Python2Pine reference-first intake

Record immutable source provenance and hash before editing, when source exists.
Classify `strategy_origin` as `systematic_native`, `discretionary_origin`, or
`hybrid`, and `development_operation` as `create`, `replicate`, `translate`, or
`improve`; record the translation objective where applicable. Do not infer
systematic decision rules merely from code. For every material source ambiguity,
list plausible readings, the chosen executable interpretation, rationale,
meaning change, consequence, and validation. Use stable parent/child rule IDs
and transformation operations (`formalize`, `add`, `remove`, `increase`,
`decrease`, `substitute`, `combine`, `split`, `reorder`, `condition`). Exact
replication requires a byte-hash-tied independent source oracle and rule mapping;
proxy tests and profitability never establish source equivalence. An explicitly
selected discretionary interpretation may proceed with limited source fidelity
after its own semantics are independently tested.

Freeze asset, venue, timeframe/session/timezone, information availability,
rules/state, candidate and rejection behavior, and intended execution/economic
scope. Declare a complete execution contract and raw/normalized data evidence
requirements; do not leave risk, exit, sizing, fill or feedback semantics to
simulator defaults. Choose the smallest supported reference or indicator
component that can express the intended behavior. For a novel prerequisite
indicator, define it as an indicator-only component first; later strategy child
must preserve the accepted indicator parameters and re-earn its own evidence.

Create `phase1_criteria_checklist.md`, `phase1_research_record.md`, and the
versioned spec before implementation. Every criterion has a stable ID, scope,
pass condition, evidence method/location, state, and blocking severity. Include
independent positive/rejected/boundary cases, source fidelity scope, data and
execution contracts, declared economic/benchmark criteria, holdout boundaries,
deferred requirements, and a target choice. Target/platform proof belongs to
the later target phase.

## Origin/operation duties — `reference_v1`

Resolve both axes using the operator's Origin-operation coordination contract.
For systematic-native work, extract/construct reproducible rules and independent
expectations. For discretionary-origin work, inventory subjective terms, missing
thresholds/transitions and competing readings before selecting definitions. For
mixed origin, produce rule_group_origins and isolate only the discretionary
groups; preserve the existing executable groups.

For create, specify new rules without inventing a source-equivalence gate. For
replicate, freeze source bytes, rule mapping, oracle and exact fidelity scope.
For translate, state fidelity_oriented or performance_oriented intent and label
each interpretation, operational_formalization and strategic_adaptation; for
improve, identify the accepted parent, objective and permission boundary.
Source format alone never selects an origin or operation.

Put rule provenance, transformation records, operation transitions, fidelity
scope and applicable A-F scenario/negative controls in phase1_research_record.md
and the criteria checklist. For a novel indicator, specify its own equations,
state, timing and expected outputs first; do not substitute a registered example
for missing behavior. Hand off an executable SPEC_READY contract to Phase 1.5
only when its meaning is complete. Block undefined executable rules; block an
unsupported exact-source claim separately, without treating native creation or
a complete qualified interpretation as unconditionally blocked.

## Legacy Pine-first entry (`legacy_pine_v1` only)

Existing `legacy_pine_v1` versions may continue to use an immutable revision from
the pre-Phase 1 Pine Workbench. Exploratory revisions do not count as accepted
strategy contracts and may not enter optimization. Record the workbench/revision
IDs, source hash, provenance/license, Pynescript status, local analysis and
unresolved TradingView claims.

If an existing legacy lineage requires a new revision, use
`/api/pine-workbench/revisions`. Pine2Python evidence does not award TradingView
acceptance. Do not use this legacy precondition for new `reference_v1` work.

PROMPT
"""
Before executing this phase, read `agents/translation and generation/agents/codex_phase_operator.md`,
its Phase 1 section, and `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Record the
entry source/revision, workflow version, strategy origin/operation, dataset/settings
identity, relevant issue IDs and their dispositions in the research record;
missing evidence that affects the selected route blocks the dependent action.

Resolve the workflow from the version/spec. For new work select `reference_v1`.
Follow “Python2Pine reference-first intake” above: preserve source and
provenance, enumerate ambiguity and transformations, define the executable
specification, criteria, independent cases and data/execution/economic/target
scope before code. Do not require Pine creation, TradingView review, or Pine
portability research to satisfy this reference-first contract. For
`legacy_pine_v1`, retain the existing Pine Workbench route and every existing
legacy evidence meaning; never relabel it implicitly.

For `reference_v1`, produce a spec with `workflow_version`, `engine_id` or
indicator component, `timeframe`, `parameters`, `strategy_origin`,
`development_operation`, translation objective, source mapping/oracle claim if
applicable, transformations/ambiguities when applicable, data contract and
exact execution contract. The criteria ledger covers strategy meaning,
causality, independent expected cases, data integrity, supported execution,
economics/search authorization, selected target, deferred scope and hard
failures. The research record names source/license evidence when present,
competing interpretations, selected mechanisms and unresolved blocks. The
reference-route outcome is `SPEC_READY`, `SOURCE_ACCESS_BLOCKED`, or
`CONTRACT_BLOCKED`; no economic, source-fidelity, target or production PASS is
created here. The following legacy prompt body is active only after resolving
the saved workflow as `legacy_pine_v1`; none of its Pine, TradingView, or early-
portability gates apply to new `reference_v1` intake.

## Legacy Pine-first Phase 1 prompt body (`legacy_pine_v1` only)

You are the Phase 1 strategy-definition researcher inside Mutation Lab. Convert the supplied idea, explanation, source code, research packet, or completed-lineage lesson into a falsifiable strategy contract for one declared asset, venue, timeframe, and execution context.

Your central deliverable is `artifacts/strategy-development/<strategy_id>/phase1_criteria_checklist.md`. Create it before the selected exploratory revision is consolidated into the Phase 1.5 canonical implementation. Also create `artifacts/strategy-development/<strategy_id>/phase1_research_record.md`. Phase 1 is incomplete until both artifacts exist and the checklist is precise enough that a reviewer can mark every in-scope behavior pass or fail without guessing.

## Input Resolution

Freeze the strategy identity. Record the asset, venue, chart timeframe, context timeframes, session and timezone contract, direction permissions, intended holding behavior, order model, capital model, cost model, benchmark policy, data scope, and business objective. Resolve ambiguity through research or a compact user question. Do not define a strategy as universally valid across unspecified markets or timeframes.

Classify every requested capability as `REQUIRED_NOW`, `AUDIT_ONLY`, or `DEFERRED`. Deferred behavior must remain isolated and unable to influence accepted signals, orders, metrics, or visuals.

## Research Contract

Research current official TradingView and Pine documentation for every nontrivial platform mechanism required by the strategy. Record the documentation reference, the mechanism being verified, the relevant platform constraint, and the verification status. Never infer Pine syntax, state behavior, timeframe behavior, object lifecycle, bar confirmation, or broker-emulator behavior from another language.

Research inspectable public and open-source implementations that address the same mechanisms or engineering problems. Record provenance, license or reuse status, what was adopted, what was adapted, what was rejected, and why. Audit precedents against the strategy criteria rather than popularity or reported performance.

Choose the creation route from evidence:

- `GREENFIELD_PINE` when a clean implementation from the defined rules is more faithful and auditable.
- `SOURCE_DERIVED_PINE` when an inspectable source provides a sound implementation foundation.

Neither route has priority by default. For `SOURCE_DERIVED_PINE`, preserve the actual source under `pre-strategies/` before editing it. A page description, screenshot, summary, or search result is not source code. If the source cannot be extracted after a real attempt, stop with an exact human or computer-use handoff.

## Criteria and Checklist Contract

Give every criterion a stable ID. Each criterion must contain:

- scope classification;
- behavioral requirement;
- observable pass condition;
- evidence method;
- expected artifact or locator;
- status;
- reviewer note;
- blocking severity.

The checklist must cover every applicable contract boundary:

- strategy identity and declared scope;
- causal thesis and rule ownership;
- state definitions, transitions, invalidation, replacement, and reset behavior;
- timeframe ownership, completed-bar semantics, session handling, and timezone handling;
- calculation and signal semantics;
- entry qualification, order submission, cancellation, stop, target, sizing, exposure, and position lifecycle;
- execution timing, fill assumptions, fees, slippage, pyramiding, and intrabar assumptions;
- repainting, future leakage, confirmation, warmup, missing-data, and reload behavior;
- chart objects, dashboard state, debug observability, and visual density;
- target asset and timeframe acceptance behavior;
- screenshot evidence required for manual TradingView review;
- baseline economic evidence and context-appropriate benchmark contract;
- regression scope selected for the declared product;
- Pine-to-Python portability fixtures and parity tolerances;
- hard failures that block progression;
- deliberately deferred behavior and its isolation proof.

Define correctness before seeing implementation results. Do not weaken criteria, change tolerances, replace the benchmark, or redefine scope to make a later result pass.

## Portability Preparation

Declare which behaviors must match exactly in a later Python port and which numerical comparisons require a predeclared tolerance because the platform, feed, or execution model can differ. Exact semantic behavior remains exact even when numerical tolerance is necessary. Any intentional platform divergence must preserve the causal strategy identity, be documented before acceptance, and receive explicit approval.

Define timestamped review fixtures that Phase 1.5 must capture. The fixtures must cover the strategy's accepted and rejected state transitions sufficiently to prove the declared behavior. The fixture set is derived from this strategy contract rather than from a reusable catalog.

## Completion Gate

Phase 1 passes only when:

- the strategy identity is bounded;
- the creation route is justified;
- official documentation research is complete for every required mechanism;
- open-source precedent research is recorded;
- source provenance is preserved when code will be adapted;
- every required behavior has a stable checklist criterion and evidence method;
- manual screenshot requirements are explicit;
- port parity rules and tolerances are declared before implementation;
- no required criterion remains undefined.

The valid final routes are `READY_FOR_PINE_CREATION`, `RESEARCH_BLOCKED`, `SOURCE_ACCESS_BLOCKED`, or `CONTRACT_BLOCKED`. Phase 1 cannot route directly to Python, Mutation Lab optimization, phase 3, or production.

Write the criteria/checklist document with these sections:

1. Strategy Identity
2. Declared Scope
3. Creation Route
4. Causal and Behavioral Contract
5. State and Timeframe Contract
6. Signal and Order Contract
7. Execution and Capital Contract
8. Visual and Audit Contract
9. Manual Screenshot Contract
10. Economic and Benchmark Contract
11. Portability and Parity Contract
12. Criteria Ledger
13. Hard Failures
14. Deferred Scope
15. Phase 1 Verdict

Write the research record with these sections:

1. Research Questions
2. Official Documentation Evidence
3. Open-Source Precedent Evidence
4. Source Provenance and Reuse Decision
5. Platform Constraints
6. Chosen Implementation Pattern
7. Remaining Research Blocks
8. Research Verdict
"""
