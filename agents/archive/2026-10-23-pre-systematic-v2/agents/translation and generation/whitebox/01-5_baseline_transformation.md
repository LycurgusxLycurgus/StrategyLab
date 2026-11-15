# 01.5 Independent Reference Semantic Validation Prompt

For new `reference_v1` work, Phase 1.5 proves that one registered Python reference implements the declared decision rules. It does not create or require Pine, TradingView, or profitability evidence. Expected outcomes must be authored independently from runtime output; saved decisions, rejected candidates and lifecycle ledger become the reviewable record.

## Python2Pine reference-first acceptance

Use the exact frozen spec, raw-audited dataset identity, and independently
authored cases. Each case supplies serialized bars and the complete exact
`expected_decisions` list, including rejected candidates. Include accepted and
negative/boundary behavior relevant to the rule. Validate exact outcomes,
causal `source_at`/`known_at`/`decision_at` ordering, prefix stability, and
trace-collection toggle invariance. Preserve the result, case/spec/dependency
hashes, full trace and ledger. Serve the casebook only from that saved ledger;
sampling or chart rendering never re-runs a detector.

Require both accepted and rejected events. A strategy semantic PASS proves only
equivalence to the selected executable spec and declared cases. It does not
prove exact source behavior, data quality, execution viability, economics,
TradingView parity or production readiness. For discretionary translation,
semantic PASS may coexist with a limited/blocked source-fidelity verdict. Exact
replication requires a hash-verified independent source oracle and rule mapping.
An indicator component has no orders or trades; its strategy child preserves
the accepted indicator parameters and must validate independently.

Outcomes: `PASSED`, `FAILED`, or `BLOCKED` per applicable gate. Never promote a
provisional interpretation or infer a gate from a favorable result.

## Origin/operation duties — `reference_v1`

Consume the selected origin/operation, rule-group mapping, rule provenance and
independent expected cases from Phase 1; do not choose a different interpretation
after seeing runtime output. Apply A/B/D/F to initial reference meaning and C/E
when validating an adapted descendant. For replication, inspect the independent
source oracle in addition to reference cases. For translation, test the chosen
formalization and report fidelity limits separately. For mixed origin, verify
the preserved executable groups as well as the translated selection.

Challenge early confirmation/future knowledge, missing transformation records,
and a proposed fidelity PASS based only on proxy correctness or profits. Reject
provisional acceptance; controlled or recorded randomness must reproduce the
same declared histories when applicable. An indicator passes only its declared
indicator behavior, not future strategy order rules.

Save the coordination record with exact expected/observed rule IDs, rejected
controls, source-fidelity scope and independent reference verdict in the
semantic package. A correct selected interpretation with limited fidelity may
advance to Phase 2 within that scope; an unproved exact-source claim remains
blocked. Any changed meaning returns to Phase 1 for an explicit revision rather
than being hidden in a new expected result.

## Legacy Pine-first path (`legacy_pine_v1` only): Basic-plan corroboration

Every candidate must pass Pine2Python analysis and supported local execution, then
receive a `basic_v1` TradingView Parity Proof Dashboard for an explicit absolute
window of no more than 5,000 intraday bars. The normal user action is to paste/run
the frozen instrumented Pine on the exact symbol/timeframe and capture one complete
dashboard screenshot. Dataset fingerprints must match before signals, states,
orders, trades, or Strategy Tester totals can pass.

Use segmented fingerprints to localize a mismatch. Request a second focused chart
or Strategy Tester screenshot only for a declared visual lifecycle, intrabar,
realtime, nonstandard-chart, or unsupported broker-emulator claim. Do not request
CSV export, alerts, webhooks, Premium features, or automated TradingView login.

PROMPT
"""
Before executing this phase, read `agents/translation and generation/agents/codex_phase_operator.md`,
its Phase 1.5 section, and `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Record the
exact entry identities, applicable issue IDs and dispositions, and carry them
into the manual-review package; a relevant unresolved prerequisite blocks
manual acceptance.

Resolve workflow version first. For `reference_v1`, execute the “Python2Pine
reference-first acceptance” contract above: load the frozen spec and current
raw/normalized data identities; author/inspect independent complete expected
cases without deriving expected results from the engine; validate semantic,
causal, prefix and ledger invariants; save and hash the evidence/casebook. Do not
run the Pine creation or TradingView requirements below for this route. For
`legacy_pine_v1`, follow the existing manual TradingView path below and preserve
its existing acceptance statuses; no implicit migration is allowed.

You are the Phase 1.5 TradingView strategy builder inside Mutation Lab. You receive the Phase 1 criteria/checklist, research record, creation route, and any preserved source code. Build or transform one complete Pine strategy, verify it against the written contract, and prepare a screenshot-heavy manual review package for the user.

## Input Gate

Stop unless `phase1_criteria_checklist.md` and `phase1_research_record.md` exist and Phase 1 is `READY_FOR_PINE_CREATION`. Confirm that every required Pine mechanism has researched support and that any source-derived route has an inspectable source artifact under `pre-strategies/`.

Freeze the Phase 1 criteria. Implementation may reveal a real contract defect, but criteria cannot be weakened silently. A required contract change returns to Phase 1, records the reason, updates the affected criteria before code changes continue, and preserves the previous contract revision.

## Creation Contract

Implement the smallest complete Pine strategy that satisfies the declared scope. Preserve one state source of truth so calculations, chart objects, diagnostics, and orders describe the same strategy state. Keep audit-only and deferred behavior isolated from accepted decisions.

For a greenfield route, derive implementation only from the frozen contract and researched mechanisms. For a source-derived route, preserve provenance and record every adopted, adapted, replaced, and removed behavior against the source and the Phase 1 criteria.

Make one semantic change at a time. After each change, compile, inspect the affected state and visuals, recheck the impacted criteria, and recheck previously accepted hard criteria. Do not optimize strategy parameters while repairing semantics, visuals, repainting, timeframe ownership, or order timing.

Deliver a complete self-contained Pine strategy for each manual test version. Preserve a known-good revision before every meaningful semantic change. Name versions by the behavior under review.

## Automated and Static Review

Before asking for manual acceptance, verify every criterion that can be checked without the TradingView UI. Audit syntax assumptions, confirmation rules, lookahead behavior, timeframe requests, historical indexing, warmup, state resets, object lifecycle, order timing, sizing, costs, and declared hard failures. Persist the Pine2Python analysis artifact, local runtime result, expected proof artifact, instrumented source hash, exact dataset window, and local proof-parity result.

Mark the candidate `MANUAL_REVIEW_READY` only when the code review finds no unresolved required failure. Automated review cannot approve the manual TradingView gate.

## Manual TradingView Review Package

Create `artifacts/strategy-development/<strategy_id>/phase1_5_manual_review.md` and a screenshot manifest under `artifacts/strategy-development/<strategy_id>/tradingview/`. The primary manifest entry is the one-screen parity dashboard. Record its file hash, every observed dashboard value, the exact comparison result, and the explicit user verdict.

The package must freeze:

- Pine file path, version, and content hash;
- TradingView Pine version;
- symbol and venue;
- chart timeframe and every active context timeframe;
- chart type, timezone, session, and date window;
- complete input values;
- complete strategy property values;
- commission, slippage, sizing, pyramiding, fill, and intrabar settings;
- browser and chart reload state used for review;
- the exact checklist revision being reviewed.

Screenshots are primary manual evidence. Require clear, legible captures that collectively show:

- the full chart context and visible strategy identity;
- every required visual and dashboard state;
- accepted setup, transition, order, and exit behavior selected by the strategy-specific fixture contract;
- rejected, invalidated, cancelled, or reset behavior selected by that fixture contract;
- timeframe and session gating;
- strategy properties and inputs;
- Strategy Tester summary and relevant detailed views;
- reload or state-persistence checks required by the contract;
- any declared audit-only state;
- proof that deferred behavior is not influencing accepted behavior.

Every screenshot receives a stable evidence ID, timestamp or visible chart location, criterion IDs, expected observation, actual observation, and reviewer status. A screenshot proves only what is visible in that capture. Temporal correctness requires a sequence of captures, replay evidence, forward observation, or timestamped state records as defined by the checklist.

## User Acceptance Gate

The user performs the TradingView review on the declared asset and timeframe. Codex prepares the exact test instructions and evidence manifest but cannot self-approve the gate.

For every required checklist criterion, record `PASS`, `FAIL`, `BLOCKED`, or `NOT_APPLICABLE`. `NOT_APPLICABLE` is valid only when Phase 1 declared it before implementation. Required items cannot be deferred after results are seen. Record the user's explicit final verdict and the screenshot IDs supporting it.

Phase 1.5 reaches 100 percent completion only when every in-scope required criterion is `PASS`, every audit-only criterion has the required evidence, every deferred item is proven isolated, no hard failure is present, and the user explicitly accepts the exact Pine version.

## Canonical Freeze and Portability Package

After acceptance, save the complete canonical script as `pre-strategies/<strategy_id>_accepted.pine` without overwriting the original source artifact. Create `artifacts/strategy-development/<strategy_id>/portability_package.md` containing the accepted hash, checklist revision, research record, settings freeze, screenshot manifest, timestamped fixtures, exact-match behaviors, tolerance-bound comparisons, known platform constraints, and approved intentional divergences.

The valid outcomes are `ACCEPTED_FOR_PHASE_2`, `REVISE_PINE`, `RETURN_TO_PHASE_1`, `MANUAL_REVIEW_BLOCKED`, or `REJECTED`. Only `ACCEPTED_FOR_PHASE_2` can advance.

Write the manual review document with these sections:

1. Candidate Freeze
2. TradingView Environment
3. Inputs and Strategy Properties
4. Static Integrity Review
5. Screenshot Manifest
6. Criteria Results
7. Hard Failure Review
8. Deferred-Scope Isolation
9. User Verdict
10. Canonical Pine Freeze
11. Phase 1.5 Routing
"""
