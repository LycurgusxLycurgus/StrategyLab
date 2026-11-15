# Codex Phase Operator Guide for Mutation Lab

This guide is the active workflow for creating, validating, qualifying, mutating, and hardening strategies in StrategyLab. New work defaults to the Python-first `reference_v1` workflow presented publicly as Python2Pine. Existing versions without an explicit migration retain `legacy_pine_v1` and their original Pine-first requirements. Resolve the workflow from the saved version/spec before acting; never silently transfer a status across routes. Each phase owns one evidence boundary, and later results cannot compensate for an earlier failed or missing gate.

## Repository Map

Phase prompts live in `agents/translation and generation/whitebox/`.

| Phase | Prompt | Owned outcome |
|---:|---|---|
| 0 / 1 | `01_translation.md` | Intake and provenance; strategy meaning, origin, operation, transformations, indicator-first option, executable specification, and independent acceptance contract. |
| 1.5 | `01-5_baseline_transformation.md` | Independently authored expected cases; causal semantic validation; saved decision ledger and casebook. No TradingView prerequisite. |
| 2 | `02_baseline.md` | Raw/normalized data integrity, declared execution contract, and reference execution validation. |
| 2.5 | `02-5_baseline_qualification.md` | Fixed unoptimized baseline, declared economics, chronological search authorization, and qualification decision. |
| 3.1 | `03-1_whitebox_diagnostics.md` | Evidence-derived whitebox diagnosis and mutation hypotheses. |
| 3 | `03_full-whitebox.md` | One-by-one whitebox previews and an optimized survivor batch. |
| 4.1 | `04-1_hybrid_diagnostics.md` | Hybrid justification and strategy-specific information, target, representation, and validation contracts. |
| 4 | `04_hybrid-blackbox.md` | Offline previews, live-engine reproduction, and an optimized hybrid survivor batch. |
| 4.2 | `04-2_blackbox_viability.md` | Optional constrained discovery and live reproduction of stable decision-time relationships. |
| 4.3 | `04-3_successor_baseline.md` | Optional evidence-preserving reseed into the new reference-first intake or an explicitly selected legacy route. |
| 5 | Operator contract below | Selected target implementation; Pine target analysis and TradingView corroboration only when Pine is actually selected. |
| 6 | Operator contract below | Venue/operations evidence and production controls; no phase verdict implies deployment readiness. |

Phases 3 through 4.3 also require `agents/docs/universal_mutation_constitution.md`.

Strategy-development artifacts belong under `artifacts/strategy-development/<strategy_id>/`. Run evidence remains under `artifacts/runs/`, `artifacts/reports/`, and `artifacts/diagnostics/`. Preserve open-source Pine/Python originals byte-for-byte under `pre-strategies/` with provenance and distinct filenames. `services/pine2python/` remains the compatible service/package/API path for Pine analysis, legacy runtime proofs, and target-port checks; Python2Pine is the public workflow name, not a destructive package rename. Do not create a temporary external repository or vendor it later.

## Operating Constitution

- New lineages start as `reference_v1`; saved legacy lineages remain `legacy_pine_v1` until the user explicitly migrates them.
- The reference specification, immutable source/provenance, and independently authored expected cases—not a generated target script—define intended meaning.
- `strategy_origin` (`systematic_native`, `discretionary_origin`, `hybrid`) and `development_operation` (`create`, `replicate`, `translate`, `improve`) are separate facts; source fidelity is separate from semantic correctness.
- Preserve original code and records; every meaning-changing adaptation becomes an explicit child transformation with an objective, rationale, and validation.
- Phase 1.5 establishes semantic correctness through expected cases, causal checks, saved ledger and ledger-only casebook. Pine or TradingView is not an early gate for `reference_v1`.
- Phase 2 validates raw-data audit, normalized data identity, and an explicit execution contract before fixed reference runs. Never infer missing exit, sizing, or fill rules.
- Phase 2.5 records an unoptimized baseline before any search; search requires explicit objective, finite declared parameter domains, chronological train/holdout boundaries, and candidate revalidation. Never use holdout to choose parameters.
- Whitebox and hybrid phases operate only on accepted reference evidence. Every changed child re-earns affected evidence; previews do not promote.
- Phase 5 is the late target boundary. For Pine, use the existing Pine2Python toolchain to analyze/generate/test the target and make the user's TradingView corroboration small and claim-driven. No chart-data CSV export, paid plan, alerts, webhooks, or automated account access is required or assumed.
- TradingView screenshots prove only what they show. Without matching raw OHLC identities, event checks or Strategy Tester totals are not full dataset parity. Record feed/platform uncertainty honestly; never fabricate equivalence.
- A target is selected by the intended deployment, not by default. Python semantics/economics, target parity, TradingView acceptance, broker feasibility, and operations remain distinct verdicts.
- Existing Pine-first routes, APIs, and evidence remain available for `legacy_pine_v1`; new reference states never rewrite their meaning.
- Later mutations are derived from the current strategy evidence, never from reusable catalogs.
- Every test preserves the frozen parent and comparable context.
- Offline evidence cannot promote live behavior.
- Production claims require robustness, execution feasibility, forward reconciliation, and operational controls beyond the mutation phases.
- Strategy families remain in the repo until the user explicitly requests removal.

## Shared Project Evidence Contract

This guide is the shared owner of the evidence rules used by every phase. Each
standalone phase prompt must read this guide, the applicable phase section, and
the current `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` before acting. The register is
the detailed project memory for open questions, proof obligations, owners,
non-proof, and reopening triggers; it is not a substitute for the
strategy-specific criteria or a phase verdict.

Every phase carries forward these identities when applicable: workflow version;
authoritative source and immutable parent/child hashes; strategy origin,
development operation and transformation history; specification and criteria
revision; raw audit, normalized dataset hash, symbol, venue, session, timezone
and timeframe; explicit execution contract; validation cases and saved evidence
hashes; Python version/run IDs; and the exact evidence window and warmup/reset
boundary. Add Pine analysis, instrumented source, target, TradingView settings,
fingerprint and screenshot IDs only when the selected target is Pine. Hash exact
bytes written to disk and verify by binary readback before treating any artifact
as immutable.

Keep these evidence classes separate:

- Reference semantic acceptance requires exact agreement with independently
  authored full expected decisions plus causal, prefix-stability, and
  trace-toggle checks; reference tests are not source-equivalence or profit
  evidence.
- Data acceptance requires a current quality sidecar tied to raw observations
  and saved normalized bytes. Historical datasets without an original audit are
  unverified unless the spec explicitly limits scope to normalized-only data;
  that limitation is never raw-data PASS.
- Execution evidence is scoped to the exact declared contract and known
  limitations. Unsupported broker feedback, fill-aware rules, and venue behavior
  remain blockers for claims requiring them.
- Source fidelity, semantics, data, execution, economics, selected-target
  parity, platform/user acceptance, and operational readiness are independent
  states. A status string, profitable backtest, proxy test, compile, or
  screenshot alone cannot combine or substitute these gates.
- `LOCAL_PROOF_CAPTURE_COMPLETE`, `LOCAL_PROOF_PARITY_PASS`, and
  `TRADINGVIEW_ACCEPTED` remain available as legacy/target-specific evidence;
  they do not gate new reference research before Phase 5.
- When Pine is selected, TradingView acceptance additionally requires exact
  source/settings/window identity, displayed evidence, screenshot SHA-256, and
  explicit user verdict. Without matching raw dataset fingerprints, record only
  the behavior actually visible and verified.

For detector-based work, account for every candidate with one terminal result
and a first-failure funnel, then assess independent chart opportunity recall.
Separate detector events, checklist/quality gates, lifecycle/order policy, and
rendering capacity. Record source/known/confirmation/ready/action timestamps;
pending or open outcomes remain explicitly unresolved at the observation
cutoff. Use the first causal divergence order for proof mismatches: contiguous
field groups, time partitions, then exact-bar primitive probes. Count all
TradingView plot calls, including `alertcondition`, and preflight compiled-token
pressure on the exact generated bytes. Stateful proofs separate supplied
history warmup from the hashed window. Persistent historical drawings own
frozen timestamps and use `xloc.bar_time`; an object-budget failure must not
erase a detection event. Remaining OHLC ambiguity requires a reason code and
the evidence/review timestamp that leaves it unresolved.

An issue may block only a phase whose accepted scope it affects or whose input
identity it invalidates. A later phase may not silently close an earlier issue;
it records the issue ID, evidence locator, disposition, and return route. A
mechanism is called reusable only after its same failure mechanism passes on a
materially different non-SMC consumer; additional SMC assets demonstrate
context coverage, not cross-strategy transfer. The detailed root-resolution and
cross-strategy proof gates live in the register.

## Origin-operation coordination contract

Apply this contract before selecting a phase task. `strategy_origin` describes
where the decisions came from; `development_operation` describes what this
version is doing. Neither source language nor a methodology name establishes
either fact. A Python program can encode discretionary choices; a stochastic or
ML procedure is systematic only when its inference, decision policy and
randomness are controlled or recorded so the same declared history reproduces
the same decisions.

Resolve the workflow before executing a standalone prompt. For reference_v1,
its reference-first contract and Origin/operation duties govern; use later
shared research or output-format instructions only where consistent with that
route. Unqualified accepted-Pine, Python-port, early TradingView and Pine-parity
prerequisites in retained legacy prose do not apply to reference research.
For legacy_pine_v1, preserve its original prerequisites and status meanings;
record applicable provenance without silently migrating its lineage or evidence.

| Dimension | Meaning and preparation duty |
|---|---|
| `systematic_native` | Extract or construct explicit inputs, rules, state, timing and independent expected decisions. Do not invent subjective ambiguity or require a discretionary translation package when none exists. |
| `discretionary_origin` | Inventory subjective terms, missing thresholds, contextual selection, management decisions and competing readings. Select an executable interpretation and disclose what the source does not settle. The executable result can be systematic without changing its origin. |
| `hybrid` (mixed origin) | Record `rule_group_origins`; preserve already executable groups and isolate the discretionary groups requiring interpretation. Converge on the same reference pipeline. This origin does not justify the statistical layer of Phases 4.1/4. |
| `create` | Author a new decision procedure. With no source-equivalence claim, fidelity is not applicable; explicit specification and independent reference tests still apply. |
| `replicate` | Reproduce defined source behavior. Require immutable source, rule mapping and independent source-output evidence for the claimed scope. A language port alone does not authorize strategic changes. |
| `translate` | Make underdetermined decisions executable. Record ambiguity, alternatives, selected definitions and `translation_objective`: `fidelity_oriented` or `performance_oriented`. Do not claim that a tested proxy proves a trader used that proxy. |
| `improve` | Deliberately change an accepted parent under a declared objective and authorization. Freeze parent identity, record the operation transition and transformations, and re-earn affected evidence before economic comparison. |

Origin and operation are separate axes, not three origins mapped to three
mandatory operations. A systematic source can be replicated or improved; a
discretionary source can first be translated and its accepted reference later
improved. Mixed-origin work applies the appropriate preparation per rule group,
not a separate broker, optimizer, phase graph or acceptance standard.

### Rule meaning, provenance and permission

Classify each material rule in the specification as `source_rule`,
`interpretation`, `operational_formalization`, `strategic_adaptation`, or
`new_rule`. Interpretation states what the source supports; operational
formalization supplies variables, thresholds, proxies, timing or transitions
needed to compute; strategic adaptation deliberately changes feasibility,
frequency, risk or economics. Keep these distinctions visible even when one
edit serves more than one purpose: record both purposes and their consequences.
An economic effect of formalization is not, by itself, permission to optimize.

For each material transformation, record stable `parent_rule_id` and
`child_rule_id`, source concept/locator and revision, ambiguity or problem,
alternatives, selected executable choice, operation, rationale, `meaning_change`,
expected operational/economic effect and independent validation evidence. Use
`formalize`, `add`, `remove`, `increase`, `decrease`, `substitute`, `combine`,
`split`, `reorder`, or `condition` to describe the edit; these are provenance,
not a mandatory strategy/filter catalog. Preserve original source bytes.

Record `not_applicable` when no discretionary translation objective applies;
replication can still require fidelity evidence. For `fidelity_oriented` work,
minimize unsupported departures and leave an unprovable exact claim blocked.
For `performance_oriented` translation, make permitted departures and the loss
of fidelity explicit before observing results. Its first specified reference
still earns semantic/execution evidence and a fixed baseline; repeated economic
selection requires search authorization. Improving that accepted reference is
an explicit `improve` descendant, not an unrecorded reinterpretation of its source.
Rename an adapted concept when the old source term no longer describes it.

### One pipeline, separate verdicts and conditional blockers

All origins converge after preparation: executable specification and independent
cases -> reference semantic acceptance -> data/execution validation -> fixed
economics -> authorized research -> selected target -> operations. A prerequisite
indicator uses the same path for its applicable claims before a child adds order
rules. MA and pivot/BOS are the currently registered bounded examples, not a
restriction that every future strategy must resemble them; unsupported new
indicator/reference behavior requires implementation and proof, not substitution
with a convenient example.

Assess source fidelity only for a real source-to-result claim. Keep it separate
from reference correctness, data integrity, execution viability, economics,
platform parity and production acceptance. Semantic PASS means conformity to
the selected executable specification, not source equivalence or profitability.
Profits, passing proxy cases, local Pine execution and screenshots cannot award
another gate. A complete selected interpretation can proceed with qualified
source fidelity if its accepted scope permits that limitation. Unknown executable
meaning blocks its dependent work; missing fidelity blocks an exact-replication
claim. Provisional candidates remain diagnostic and non-promotable, without
bypassing the registered runtime's validation gates.

Each phase consumes and updates a coordination record inside its existing
research/checklist/diagnostic artifact: origin and rule-group origins; operation
and transition; objective and permissions; source/parent/spec identities;
rule classification and transformations; separate verdicts with evidence scope;
applicable acceptance cases, negative controls, blockers and next owner/phase.
Carry unchanged facts by identity/reference rather than rewriting history. No
additional store or duplicated verdict system is required. Record applicability
and reason instead of fabricating source evidence for native creation or forcing
all six scenarios into every individual strategy.

### Six acceptance scenarios and negative controls

Use A-F to validate the coordination workflow when these contracts change; for
an individual strategy, select its applicable scenario(s) and concrete cases.
These are required evidence duties, not claims that every scenario has already
passed. Phases 1/1.5 own meaning and independent expectations; Phase 2 owns
causal execution; Phase 2.5 and research phases own authorized economic change.

| Case | Required positive evidence | Negative control and owning boundary |
|---|---|---|
| A — native creation | Explicit timing/risk specification and independently authored MA-style control cases; fidelity/translation objective not applicable where there is no source claim. | Phases 1/1.5 reject undefined rules or output-derived expectations; do not impose a discretionary-source gate. |
| B — native replication | Immutable deterministic source, source-to-rule mapping and independent output equivalence for the declared scope. | Phases 1/1.5 reject a replication claim after an unauthorized strategic change or without its source oracle. |
| C — native improvement | Frozen accepted parent, exit-policy or other bounded child, transformation rationale, impacted semantic/execution tests and same-context economic comparison. | Phase 2.5/3 reject absent authorization, parent overwrite or inherited child PASS. |
| D — discretionary translation | Qualitative swing/displacement/selection source, ambiguity inventory, chosen operational definitions, independent cases and delayed pivot known-time evidence. | Phases 1/1.5/2 reject early knowledge and a source-fidelity PASS inferred solely from correct proxy cases. |
| E — discretionary adaptation | D's descendant changes a threshold/filter/entry for a declared objective, records meaning change and authorization, and re-earns semantic/execution and comparable economic evidence. | Phases 2.5/3 reject an undocumented operation transition or calling an adapted child an exact source replica. |
| F — mixed-origin components | Deterministic indicator preserved, discretionary selection isolated with per-group provenance, and one common reference/execution contract. | Phases 1/1.5/4.1 reject silent modification of executable groups or treating mixed origin as permission to add an ML/statistical layer. |

Also exercise missing transformation provenance, fidelity inferred from profits,
future-information leakage and provisional promotion as rejecting controls.
Demonstrate that fidelity-oriented and authorized performance-oriented
translations use the same downstream gates, and that controlled/recorded
randomness reproduces decisions when applicable. Record unsupported cases as
blocked; never manufacture evidence to fill the matrix.

### Phase application map

| Phase | Required application of the shared contract |
|---:|---|
| 0 / 1 | Freeze source authority and lineage; classify origin/operation; record ambiguities and transformations; create the executable strategy/indicator spec, strategy-specific criteria, causal timestamp/data/execution contracts, and independent fixture plan before implementation. |
| 1.5 | Author independent accepted/rejected/boundary cases; validate exact decisions, prefix causality and ledger toggle; save current semantic evidence, ledger and casebook from one decision source. No Pine/TV requirement for `reference_v1`. |
| 2 | Audit raw observations before normalization and bind raw/normalized hashes; freeze the exact execution contract; validate/run MA or pivot/BOS reference only when all applicable gates pass; do not infer full broker semantics from a bounded adapter. |
| 2.5 | Run and freeze the unoptimized baseline first; declare economics and comparison criteria; authorize only finite domains with train/holdout split and objective; keep holdout out of selection; describe measured economics separately from semantics/fidelity. |
| 3.1 / 3 | Derive hypotheses from current evidence; preserve retained, added, removed, retimed and re-anchored opportunities and first-failure classes; test one conceptual dependency while keeping the accepted semantic boundary explicit. |
| 4.1 / 4 | Freeze decision-time information, target, ambiguity, chronology, opportunity preservation and complexity before outcome inspection; require offline-to-live reproduction before promotion. |
| 4.2 | Use a bounded untouched evaluation boundary; record failed relationships; discovery never promotes an opaque branch. |
| 4.3 | Carry evidence-backed constraints and unresolved issue IDs only; a successor re-enters `reference_v1` intake by default or explicitly selects legacy, then earns its own evidence. |
| 5 | Implement/validate only the selected target. For Pine, port the accepted reference, inspect feature/signal parity, then perform focused TradingView corroboration on the same symbol/timeframe and predeclared events. Full data/performance parity requires matching raw datasets; a screenshot alone cannot prove it. |
| 6 / Production | Require strategy-specific robustness, adverse execution, venue legality, forward reconciliation and operational controls; prior local, browser or mutation evidence is not deployment readiness. |

## Python2Pine `reference_v1`: Phases 0–2.5

### Phase 0 / 1: Intake, provenance and executable specification

Start from an idea, an inspectable open-source script/indicator, or a completed
lineage. Preserve any original source bytes, URL/author/license evidence and
source hash before editing. Record one `strategy_origin` (`systematic_native`,
`discretionary_origin`, or `hybrid`), one `development_operation` (`create`,
`replicate`, `translate`, or `improve`), and the applicable objective. These are
separate dimensions: source format or methodology alone does not establish
systematic decisions. Enumerate each ambiguity and every formalization,
addition/removal, substitution, threshold change, combination/split, reordering
or conditionalization that affects behavior. Give each transformation a parent
and child rule ID, source locator, executable choice, rationale, meaning/effect,
and planned validation. Do not claim exact replication from a proxy.

Freeze strategy/component identity, asset, venue, timeframe/session/timezone,
information timing, decision and state rules, expected intent, and bounded
execution/economic scope. For discretionary sources, choose an explicit
executable interpretation, record competing readings, and state source-fidelity
limits. An exact replication claim requires an independent, byte-hash-tied source
oracle with cases and mapping. A native create does not need a source-fidelity
claim. Unknown executable meaning blocks the affected claim; a provisional
interpretation may be diagnostic but cannot become accepted/promotable.

For indicator-first work, freeze and test the indicator as a reference component
before adding orders. An accepted indicator produces no order intents or trades.
The first strategy child preserves the indicator parameters, records the
indicator-to-strategy transition, and earns fresh strategy semantic/data/
execution evidence; it inherits no parent PASS.

Produce `phase1_criteria_checklist.md`, `phase1_research_record.md`, and a
versioned machine-readable spec. Cases, source-fidelity scope, explicit
execution/data contracts, economic objective/benchmark, deferred requirements,
and the selected deployment target are recorded before their respective
implementation/results. The default new-version selector is `reference_v1`;
`legacy_pine_v1` is an explicit compatibility route, not the greenfield default.

### Phase 1.5: Independent semantic acceptance

Author serialized market cases and the complete expected decisions independently
from runtime output. Include accepted and rejected candidate behavior and
strategy-specific boundaries (for example, warmup, disabled direction,
confirmation delay, invalidation, expiry, or cutoff). Then validate exact full
decision lists, information-time causality, prefix stability, tracing-on/off
invariance, and the decision/event ledger. Save the current case/spec/evidence
hashes and an HTML casebook rendered only from that ledger; visualization cannot
recompute detector meaning or hide events. An indicator casebook has no trades.

Semantic PASS proves only that the implementation matches the declared
specification and independent cases. It does not establish source equivalence,
data integrity, viable execution, profitability, TradingView behavior, or
production readiness. The valid outcomes are `PASSED`, `BLOCKED`, or `FAILED`
for the applicable evidence gate; do not infer one gate from another. A complete
discretionary interpretation may pass semantic cases while source fidelity stays
`PASS_WITH_LIMITATIONS` or blocked.

### Phase 2: Data integrity and reference execution

Before execution, audit raw observations before sorting/deduplication. Preserve
the raw audit and hash, normalized file hash, dataset context, and quality
manifest. Conflicting duplicate timestamps, invalid OHLC/non-finite values,
descending source order, or missing/stale audit block reference acceptance.
Identical duplicates may be retained only under the recorded audit policy.
Legacy data without raw audit remains unverified unless the spec explicitly
limits its claim to normalized-only observations; that is never original-data
PASS.

Freeze the complete execution contract; do not fill omitted behavior with
convenient simulator defaults. Current bounded references use next-bar-open
submission, fixed quantity, static ATR stop from decision, optional
risk-multiple target, adverse stop-first ambiguity, censored cutoff, and
decision-only feedback. This envelope is not a broker adapter. Fill-aware,
dynamic risk, unsupported timeframe, or venue lifecycle requirements stay
blocked until implemented and proven.

Require current semantic, data and execution evidence before a fixed reference
run. Compare decisions, order intents, lifecycle/ledger and execution results on
the same saved dataset and contract; report source fidelity and limitations
separately. A successful local run is not an economic qualification or platform
verdict.

### Phase 2.5: Baseline, economics and search authorization

Run and hash the exact unoptimized parent first. Preserve its parameters,
dataset, execution contract, comparison context and report. State semantic,
source-fidelity, execution and economic outcomes separately. Economic evaluation
uses the strategy's declared objective and evaluation contract; do not imply
qualification from “a backtest ran” or allow metrics to prove semantics.

Search begins only after a comparable fixed baseline and explicit authorization.
Freeze an objective, finite domains for existing tunable parameters, chronology,
training end, untouched holdout start, and selection rule before search. Generate
and rank candidates on training data only. Do not inspect, score, or choose by
holdout. Every selected child stays within authorization, preserves its parent,
records a real `improve` transition and transformations, and re-earns impacted
semantic/data/execution evidence before comparable economics. A baseline failure
can remain a useful research result; it cannot be silently repaired by search.

## Phases 3–4.3: Mutations and constrained discovery

Phases 3.1/3 diagnose a currently evidence-qualified reference parent and test
one causal mechanism at a time. Input includes current source/spec lineage,
semantic/data/execution gates, an unoptimized baseline, economic criteria and
any authorization. Pine hashes/parity are not universal prerequisites; they are
required only for a lineage/claim/target that actually depends on Pine. Every
meaning-changing candidate becomes a child and is independently revalidated.
The parent remains immutable, rejected previews persist, and no preview or
offline result can promote.

Phases 4.1/4 require the same reference gates plus an evidenced reason a bounded
statistical layer beats a cleaner rule or no change. Freeze decision-time
information, target, ambiguity, chronology and live reproduction contract before
outcome inspection. Keep any unsupported adapter explicitly blocked; do not run
an offline experiment that lacks a causal live-engine boundary. Phase 4.2 is
bounded discovery, never promotion. Phase 4.3 carries constraints and source
evidence, not tuned values or implicit acceptance; the successor creates a new
`reference_v1` spec by default or explicitly chooses the retained legacy route.

## Phase 5: Selected target and TradingView corroboration

Implement only a target selected by the strategy's declared deployment. For
Pine, use the compatible Pine2Python service to analyze, generate/inspect and
locally compare the target against the accepted Python reference on matching
input data where available. Keep feature/signal comparison distinct from fill,
broker-emulator and target acceptance. Target-dependent status remains blocked
until the target-specific evidence exists.

The operator's corroboration should be quick and claim-driven: load the frozen
Pine on the exact TradingView symbol/timeframe, compare its visible behavior at
predeclared events with the saved Python casebook, inspect Strategy Tester only
for the separately declared execution claim, and capture the required evidence
once. TradingView Basic CSV export is unavailable and is not a workflow step.
If the TradingView feed/window cannot be proven identical, do not call its
displayed totals full Python parity; record a sampled/platform corroboration
scope and the remaining feed/execution uncertainty. The user alone supplies the
verdict for the exact target artifact. Python targets use their own actual target
and broker acceptance contract; TradingView is not substituted for it.

## Phase 6: Production and operations

Freeze one exact final candidate, dataset, parameter set, execution model, and strategy contract. Run chronological robustness and adverse execution scenarios derived from the declared market and venue uncertainty. A universal stress multiplier is not a substitute for a context-specific stress design.

Audit whether every intended action can become a legal venue order under the declared account and instrument constraints. Then run forward paper reconciliation until the strategy-specific calendar coverage, event coverage, trade evidence, regime exposure, and operational confidence requirements are met. A universal paper duration or trade count is not valid.

Production readiness requires aligned reference intent, target decisions,
submitted orders, venue responses, fills, position state, risk controls, and
monitoring. Semantic, source fidelity, data, execution, economics, target,
platform and operational gates remain independently visible. A locally accepted
reference or a green TradingView chart alone is not production approval.

## Legacy `legacy_pine_v1` route

Existing Pine-first versions keep the Pine Workbench, Pine analysis/TradingView
manual acceptance, Python port/parity and baseline progression defined by the
legacy-specific sections in the standalone phase prompts and stored evidence.
They retain their original status meanings. New work may use this route only by
explicit selection; no existing family is rewritten or re-labelled in place.

## Running the App and Tests

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
```

Run the regression suite after engine, schema, migration, API, or report-generation changes. Prompt-only changes require reference and contract validation.

## Codex Execution Checklist

1. Read `AGENTS.md`, the active Bridgecode route, the phase prompt, and the universal mutation constitution when applicable.
2. Verify the previous phase artifact and verdict before acting.
3. Freeze the current strategy, data, and execution contracts.
4. Read the Markdown evidence first and request raw data only for a named missing question.
5. Make the smallest complete change for the active phase.
6. Persist accepted and rejected evidence.
7. Run focused validation and the full suite when implementation contracts changed.
8. Report the exact verdict, evidence, unresolved boundary, and next phase.
9. Preserve strategy families unless the user explicitly selects them for removal.

The workflow prevents false progress by separating strategy definition, manual semantic proof, port fidelity, economic qualification, explainable mutation, bounded statistical discovery, and production validation.
