# StrategyLab reference-first migration plan

Status: planned transition, revised 2026-10-13 for strategy origin and development
operation. Repository rules were relocated on 2026-10-08. This plan does not
implement the reference workflow or grant any strategy acceptance. Current inspected HEAD is
`9e859f920e22772f1d809e928dd1c76323a4192f` (Hesse merge). Existing untracked
artifacts and browser files remain user-owned. Recheck HEAD before execution.

## Inputs and governing decision

The supplied `Pasted text.txt` attachment contains both **StrategyLab:
Reference-First Strategy Development / Codex implementation handoff** and the
**PROPOSAL**. Both were read completely. They agree: establish strategy meaning
through a small executable reference, Python by default, before economic search
and target-platform implementation. The handoff adds repository compatibility,
machine-enforced gates, two different consumers, and concrete regression duties.
The initial request asked for a plan and repository-rule relocation. The
2026-10-13 attachment, **Systematic-Native Development and
Discretionary-to-Systematic Translation**, supplements that plan. It was read
fully; its requirements are integrated below. Runtime and active phase-prompt
migration remain future work within the implementation slices.

Adopt one lineage and one strategy specification, with separate evidence for:
source interpretation, reference correctness, data integrity, execution fidelity,
economics, platform parity, and operation. The specification and independently
authored expectations govern strategy meaning; an accepted reference executes
that meaning. A reference implementation cannot silently redefine its source.

For existing Pine, preserve the original bytes and source-to-rule mapping from
intake. Use original-source behavior as an independent oracle where available;
unsupported executable semantics block the affected replication acceptance.
For underdetermined discretionary components, an explicitly selected executable
interpretation can earn semantic acceptance against its own specification while
source fidelity remains limited or blocked. Final
engineering of new Pine and TradingView target acceptance move later. An early
platform feasibility or source-oracle check may be needed, without requiring
greenfield work to start with Pine. Indicators first earn semantic acceptance
before a child adds order rules.

## Strategy origin, operation and transformation

Keep creation and translation distinct within one reference-first workflow.
Classify the actual decision procedure rather than its methodology, source
format, asset or platform. These dimensions are metadata within
`reference_v1` or `legacy_pine_v1`, not additional phase graphs or engines.

| Dimension | Values and responsibility |
|---|---|
| Strategy origin | `systematic_native`: explicit reproducible decisions under defined inputs/state/config/event history; `discretionary_origin`: human judgment or underdetermined decisions; `hybrid`: classify rule groups and translate only the discretionary components. |
| Development operation | `create`: author a new decision procedure; `replicate`: reproduce defined source behavior; `translate`: make discretionary decisions executable; `improve`: deliberately change an accepted parent under stated objectives. Record transitions within the lineage. |
| Translation objective | `fidelity_oriented`: minimize unsupported departures while achieving computability; `performance_oriented`: permit documented adaptations under declared objectives and research authorization; `not_applicable` for work without discretionary translation. |

Origin records provenance; a resulting executable specification can be
systematic even when its source was discretionary. Code or indicators do not
automatically establish determinism. A probabilistic/ML strategy qualifies as
systematic when inference, decision policy and randomness are controlled or
recorded so identical declared histories reproduce decisions. Replication
fidelity and systematic construction are separate objectives even where
`translation_objective` is `not_applicable`.

Systematic-native preparation extracts or constructs rules, causal timing,
states and independent expectations. Discretionary-origin preparation also
inventories subjective terms, missing thresholds/transitions, contextual choices
and competing interpretations before selecting an executable specification.
Hybrid preparation preserves executable components and isolates unresolved
selection/management decisions. All converge on the same reference, execution,
ledger, persistence, metrics and downstream verification contracts.
Mixed-origin `hybrid` classification does not itself authorize the statistical
hybrid layer of Phases 4/4.1; that layer still requires its existing justification.

For every material transformation, record the original concept/source locator,
ambiguity or problem, selected executable definition or modification, rationale,
effect on meaning and expected operational/economic consequences, and independent
validation evidence. Use stable parent/child rule IDs linked to spec revisions.

| Transformation operation | Meaning |
|---|---|
| Formalize | Supply explicit variables, conditions, timing and state transitions. |
| Add / remove | Introduce or eliminate a component, condition, risk rule or execution mechanism. |
| Increase / decrease | Change a threshold, sensitivity, duration or confirmation magnitude. |
| Substitute | Replace a mechanism with a declared executable approximation. |
| Combine / split | Merge related conditions or separate a compound rule. |
| Reorder | Change condition sequence or priority. |
| Condition | Restrict a rule to explicitly defined circumstances. |

This vocabulary records choices; it supplies no mandatory filter/model catalog.
Distinguish **interpretation** (what the source supports), **operational
formalization** (explicit assumptions/proxies needed to compute), and **strategic
adaptation** (deliberate changes to feasibility, frequency, risk or economics).
An economically consequential formalization does not by itself authorize an
improvement. Add/remove/substitute can trade fidelity for other objectives;
document that tradeoff. A materially adapted descendant cannot claim exact source
replication, and terminology should change if it no longer represents the source
concept. Original sources remain immutable; changes belong to descendants.

Source fidelity, semantic correctness, operational/execution viability, economic
qualification, platform parity and operational acceptance receive separate
evidence and scoped verdicts. Add a fidelity assessment only for a real
source-to-result claim; reuse the existing semantic verdict. Greenfield creation
has no source-equivalence gate. A profitable result does not prove fidelity;
passing tests of a chosen proxy does not prove that a trader used it.

Material source ambiguity blocks faithful-translation claims. Explicitly
provisional interpretations may run bounded diagnostic experiments with declared
limitations while remaining outside accepted/promotable states. Once a complete
executable interpretation is selected and independently tested, its semantic
acceptance can coexist with qualified or unresolved source fidelity. If the
objective requires exact source equivalence, missing fidelity evidence remains
blocking. Performance-oriented translation still earns semantic and execution
gates, saves a fixed baseline and receives search authorization before economic
optimization. It does not inherit imaginary discretionary performance history.

Semantic-debugging casebooks in Phase 1.5 consume saved reference evidence;
platform visual acceptance remains late. The new handoff's emphasis on later
visualization is applied as a prohibition on visuals defining semantics, while
retaining the existing plan's early ledger-driven semantic inspection. Both
visual uses read the same evidence and never implement a competing detector.

## Inspected state and contradictions

| Boundary | Current evidence | Required migration |
|---|---|---|
| Phase operator, README, all ten whitebox prompts | Phase 0 creates Pine, Phase 1 exits `READY_FOR_PINE_CREATION`, 1.5 accepts TradingView, 2 ports Pine; successors repeat this chain. | Change ownership and route selectors coherently. Retain an explicit legacy route for existing lineages. |
| Origin and operation | Existing prompts distinguish `GREENFIELD_PINE` / `SOURCE_DERIVED_PINE`; the proposed plan previously treated source interpretation primarily as a single blocking boundary. No `strategy_origin` / `development_operation` runtime model was found. | Preserve creation/replication/translation/improvement separately; add conditional preparation and scoped fidelity verdicts inside the planned workflow. |
| `agents/docs/universal_mutation_constitution.md` | Required inputs and Pine-deployable mutation gate require prior Pine acceptance and Phase 2 parity. | New reference route requires semantic/execution evidence before research; Pine gate belongs to the selected target phase. |
| `agents/docs/production_backtest_engine.md` | Sound timing/execution principles; Phase Integration assumes Pine-first. | Retain principles, update ownership and failure-return routes. |
| `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` | Early Pine prohibitions occur in phase table, PROOF-003, ECON-001, and related SMC records. | Add versioned routing/applicability; retain original issue evidence and verdicts. Do not announce semantic or visual closure. |
| `BacktestEngine.run` in `app/backtest.py` | Five `engine_id` branches; strategy decisions and fills coexist inside family implementations. | Keep legacy engines; add a thin registered reference execution path only after two consumers prove the contract. |
| `BacktestEngine._standard_trace` | Post-run trades/equity reconstruction; empty `features`, `signals`, `rejections`, declared false capabilities. | Preserve old trace format; emit new decision ledger during reference computation. Never infer rejected opportunities from filled trades. |
| `DataService._read_mt5_csv_text` / `_dedupe_bars` | Sorts rows, keeps last duplicate timestamp. | Audit original input before normalization; conflicting duplicates block new reference runs, identical duplicates require a declared reported policy. |
| `compare_traces` in service `parity.py` | Dict comprehensions overwrite duplicate trace keys; missing field reads as `None`. | Validate unique keys and required fields before comparison; missing required fields cannot equal their way to a pass. |
| `LabService.register_baseline` / `promote_version` | Baseline saves `white_box`; promotion updates family pointer after family existence check. | Validate same-family candidate and required current evidence before mutation of a family pointer. |
| `optimize_lever`, `optimize_all`, proposals and tuned saves | Economic/search machinery exists, without a reference phase-evidence manifest. | Gate the shared service boundary and all callers; preserve research previews with explicit non-promotable status. |
| `Repository` in `app/storage.py` | SQLite versions/runs/proposals/Pine evidence plus artifact paths; no generic reference phase manifest. | Reuse IDs and artifact conventions; minimal additive migration, no second database and no Pine-only evidence table misuse. |
| API, CLI, UI | API jobs call `lab.optimize_all`; UI has previews/search/promotion; CLI also has unrelated Telegram management. | Backend enforcement first, matching UI status after; protect job and direct service bypasses. Keep unrelated research lanes scoped. |
| SMC diagnostics | `evaluate`, `event_accounting`, `regression_checks`, `render_casebook` provide causal/event methods. | Reuse methods and admissible cases, not disputed SMC definitions as universal primitives. |
| Existing MA fixture | 240 rows validate OHLCV and position lifecycle under `next_bar_open`; README says features/signals await direct emission. | Preserve control; add pre-authored decision expectations and explain any intentional differences. |
| `agents/plan.md` | Older Python-first Aurum vision includes its own topology, webhook and week-long paper ideas. | Historical context only; no adoption of its fixed durations, strategy catalog or parallel topology. |

Current docs describe stronger gates than application paths enforce. Their
relocation into architecture preserves requirements; it does not implement them.
The preserved SMC v6.3 record and its external review remain separate from the
new reference milestone. A new bounded pivot/BOS example is a contract consumer,
not acceptance of full SmartMoney-4.

## Proposed phase ownership and exit evidence

Keep familiar numbers and add explicit final phases. Machine-readable states
are independent of the human phase names. These are proposed names until wired.

| Phase | Owns | Required output / return boundary |
|---|---|---|
| 0 | Intake, provenance, feasibility and workflow selection | Source/idea record, immutable original, complete/partial/discretionary procedure, strategy origin and rule-group classification, requested operation/objective, target intent, `reference_v1` or `legacy_pine_v1`; no unnecessary translation for defined rules. |
| 1 | Decomposition, source mapping, specification, timing, independent cases | Rule IDs and existing classifications; source-supported rules, interpretations, formalizations, adaptations and new rules; discretionary ambiguity inventory and selected alternatives; independently expected executable behavior and scoped source-fidelity evidence. |
| 1.5 | Custom reference implementation and semantic acceptance | Common reference/config/spec identities, independent cases, causal/prefix checks, ledger/casebook and semantic verdict; fidelity separately qualified where claimed. Provisional experiments never imply accepted/promotable status. |
| 2 | Data audit and execution integration | Same raw/normalized hashes, quality findings, broker feedback, linked lifecycle/accounting and known-time rules for both origins; missing stops/exits/management require explicit spec decisions, not hidden simulator defaults. |
| 2.5 | Fixed baseline, economic qualification and separately authorized search | Fixed unoptimized translation/reference evaluated on declared frequency, expectancy, risk, costs and chronology; no invented human performance history or universal numeric targets; search only when authorized. |
| 3.1 / 3 | Whitebox diagnosis and bounded mutation | Frozen parent; classify changed rule as source-preserving, interpretation/formalization or adaptation; child spec/reference, impacted tests, opportunity/rejection/execution/risk and economic comparison. |
| 4.1 / 4 / 4.2 | Justified hybrid and constrained discovery | Same admissibility/holdout/reproduction requirements; transformations record provenance and gate impact for either origin; no opaque discovery promotion. |
| 4.3 | Successor decision | Evidence-backed constraints/issues return to 0/1; record operation transition, preserve original provenance, re-earn gates and retire misleading source terminology. |
| 5 | Independent target port and platform acceptance | Selected reference/spec frozen; aligned criterion traces and first divergence; target-specific limitations; Pine additionally needs exact TradingView proof and user verdict. |
| 6 | Forward, operational and deployment validation | Replay/shadow/paper evidence, venue legality, risk controls, reconciliation and context-specific coverage. No universal duration/trade count. |

Return semantic defects to 1/1.5, data/execution defects to 2, weak economics to
2.5 research disposition, target defects to 5, and operational defects to 6.
Platform exceptions that change strategy meaning create a child specification and
re-run affected earlier gates. A line with no Pine target has no TradingView gate;
any selected production target still earns independent validation appropriate to
that target. A Python deployment target needs independent expected behavior and
replay/shadow comparison, not a rename of the research module as proof.

## Narrow contracts to prove before integration

Use simple Python records/functions; introduce a shared package or generic engine
only if two actual consumers demonstrate a repeated boundary. Proposed locations
are `app/reference.py` for the small contract/auditor/driver and
`app/reference_strategies/` for registered local strategies. Names may change to
fit implementation evidence; arbitrary caller modules/code/imports are excluded.

```python
# Proposed interface kernel; strategy internals can be vectorized or stateful.
result = run_reference(spec, observations, *, collect_ledger=True)
# result: decisions/order_intents + optional detailed ledger + declared limitations
execution = simulate(result.order_intents, observations, execution_contract)
# execution: order/fill/position/portfolio events linked by intent_id
```

For fill-aware strategies use a chronological driver rather than a precomputed
batch: consume market and broker events known by time t, update strategy state,
emit intents, process only eligible execution, then deliver acknowledgements
through the same ordered queue. No fill feeds backward into an earlier decision.
The batch API is sufficient only for strategies explicitly independent of fills.

The ledger envelope contains stable `event_id`, `event_type`, `rule_id`,
`source_at`, `known_at`, `decision_at` where applicable, available evidence
references, prior/next state, reason, and `intent_id` links. State/payload depth
is strategy-specific. Broker events separately contain eligibility/submission/
fill time, status/reason, quantity/price/cost and causal links. Snapshot state by
value; later mutation must not rewrite earlier ledger records. At an observation
cutoff, retain pending/open events as censored, with one terminal result per
terminated candidate. Visualization reads saved market data and ledger fields;
it does not compute a second detector.

Audit `source_at <= known_at <= decision_at <= earliest_submission <= fill_at`
where those fields apply. Rule-specific exceptions (e.g. exchange publication
delay, higher-timeframe completion) are explicit. Data timestamps distinguish
bar open from close and venue session/timezone. Prefix comparisons preserve
all decisions observable by the cutoff rather than comparing final settlement
artifacts with different horizons.

Tracing on/off must produce identical decisions and execution for identical
inputs. Costs/fill-policy perturbations preserve decisions for the decision-only
control. For fill-aware strategies, identical broker-event histories must produce
identical decisions; changed fills/affordability may legitimately alter later
decisions via explicit feedback. Do not impose false cost invariance on those
strategies.

### Evidence and gate kernel

Use versioned manifests under the existing strategy-development lineage, indexed
from current version storage. Plan a minimal additive evidence index with version,
kind, artifact path/hash and dependency identities; select the exact table/column
migration after caller tests. Do not overload `pine_evidence` for non-Pine truth.

```text
workflow_version; strategy/version/parent IDs
spec_hash; reference_code_hash; config_hash; source_hash and source_mapping
strategy_origin; rule_group_origins; development_operation; development_objective
translation_objective: fidelity_oriented | performance_oriented | not_applicable
rule_provenance: source_rule | interpretation | operational_formalization |
                 strategic_adaptation | new_rule
transformations -> {parent_rule_id, child_rule_id, operation, rationale,
                    source_evidence, ambiguity_or_problem, executable_choice,
                    meaning_change, expected_effect, validation_evidence}
source_fidelity -> {status, scope, evidence, limitations}  # only if claimed
dataset_raw_hash; normalized_hash; quality_manifest_hash; execution_model_hash
stage -> {status, evidence_path/hash, dependency_hashes, limitations, verdict}
search_authorization -> {parameters, objective, chronological boundaries, holdout}
selected_target -> {kind, source_hash, parity_contract, platform_verdict}
```

Statuses: `NOT_RUN`, `BLOCKED`, `FAILED`, `PASS_WITH_LIMITATIONS`, `PASSED`.
Origin/operation/provenance fields above are conceptual additions to existing
specs/source maps/mutation records and planned manifests. Use existing JSON
storage (`spec_json`, `mutation_json`, source artifacts) where it fits; no new
origin-specific table, database or duplicate semantic verdict. A metadata change
that affects a fidelity claim invalidates that claim's evidence; changed meanings
also invalidate impacted semantic/execution evidence. Record operation changes
on descendant/transition artifacts instead of overwriting origin or history.
Missing/stale evidence blocks the relevant operation. A limitation can pass only
when explicitly outside the accepted operation's scope; a required criterion
remains blocking. Resolve artifact paths within the existing artifact root and
verify actual content hashes against the current dependency tuple. A supplied
status string is never sufficient.

```python
require_evidence(version, operation, current_dependencies)
# run/economics: semantic + data/execution evidence for this spec/config/dataset
# search: above + frozen unoptimized baseline + explicit search authorization
# save/promote mutation: child impacted semantic gates + execution + comparison
# target accept: target parity + target-specific verdict (TV when Pine)
# production: selected target acceptance + forward/operational gates
```

Apply gates in `LabService`, not only the UI or FastAPI. Cover direct services,
sync APIs, async optimize jobs, proposal runs/packs and tuned saves. Preview may
compute incomplete evidence but cannot promote it. Hash-changing parameters
create new configs and invalidate dependent evidence; unaffected tests may be
reused only through an explicit validated parameter domain, never inherited
blindly. Algorithm/rule changes create child specs and re-run impacted semantics.
Gate against the declared development objective as well as evidence dependencies:
an exact replication claim requires its source-equivalence proof; a selected
discretionary interpretation may have semantic PASS with limited source fidelity.
Provisional candidates remain non-promotable; material adaptations outside the
declared operation/objective require explicit authorization and a child record.

## Incremental implementation sequence

Each slice ends with durable evidence and a compatibility decision before the
next begins. The implementation root owns planning/integration. If Luna is used
under the requested flow, assign bounded mechanical/test edits only after these
interfaces are frozen, with disjoint files and complete packets. Fresh reviewers
follow Bridgecode routing and the one-correction/two-review limit.

1. **Coherent governing workflow and version selector.** Update operator, all
   ten prompts, universal constitution, production engine constitution, README,
   architecture and current proof-register applicability together. Add small
   Phase 0/5/6 prompts only if the operator alone cannot provide an independently
   usable contract. Existing lineages explicitly retain `legacy_pine_v1`; new
   intake selects `reference_v1`. Add origin/operation/objective and conditional
   translation duties to the same phase contracts, not parallel prompt families.
   Acceptance: no greenfield early Pine gate in
   reference-route docs, no silent reinterpretation of old statuses, every
   named route has inputs/outputs/failure path. Do not advertise runtime support
   before the following slices land.
2. **Simple reference control and independent expectations.** Implement the MA
   crossover/ATR control as local strategy code with direct decisions and a
   minimal next-bar execution adapter. Reuse `Bar`, existing calculation helpers
   only where their timing matches the specification, existing metrics and saved
   artifacts. Author short expected scenarios before engine output; keep the
   240-row old fixture as compatibility evidence, not an oracle for new features.
   Produce one saved ledger/casebook and unoptimized result. Acceptance: early
   decision injection fails; accepted and rejected candidates are traceable;
   ledger toggle stable; cost perturbation changes execution only as declared.
   Use bounded variants for native creation, replication and improvement; do
   not require discretionary ambiguity artifacts where they do not apply.
3. **Stateful contract consumer.** Add a bounded confirmed-pivot/BOS example
   using source/known/ready distinctions and independently adjudicated examples.
   Preserve SMC disputed rules and source hashes. Acceptance: same narrow
   envelope/driver, prefix stability, delayed confirmation negative, invalidation,
   censored cutoff and no detector loss under rendering limits. Rework the small
   interface if this needs broker duplication or SMC-specific shared fields.
   Use bounded source/interpretation variants to demonstrate discretionary
   translation, adaptation and hybrid preparation; record confirmation delay,
   source-fidelity limits and transformations. No full strategy family is needed.
4. **Integrity fixes at responsible boundaries.** Add raw-data audit before
   `_dedupe_bars`, explicit conflicting/identical duplicate policy, OHLC/finite/
   time ordering checks and context-specific gap/session findings. Reject duplicate
   parity keys and missing required fields before indexing. Record missing/extra
   alignment as first divergence when same keys are required. Preserve old valid
   dataset/trace results; unsafe historical imports remain labelled unverified
   rather than silently rewritten. Acceptance: concrete conflicting duplicates,
   invalid data, malformed traces and numerical mismatch regressions.
5. **Storage, evaluation and application integration.** Add minimal versioned
   manifests/index, explicit reference registry dispatch, `LabService` gate checks,
   current API/job hooks and UI evidence display. Reuse `_store_run`, reports,
   chronological robustness and optimizer; adapt result shape once at the edge.
   Do not add a second optimizer. Cover family membership, stale dependency hashes,
   baseline-before-search and non-promotable preview. Acceptance: two consumers
   use current stored versions/runs and cannot bypass gates through direct calls,
   jobs or proposal/tuned-save paths; existing valid legacy tests still pass.
   Add origin/operation/provenance handling to current specs/artifacts and planned
   manifests, plus independent fidelity reporting only where needed. Tests reject
   undocumented adaptation, false equivalence and provisional promotion; no
   second engine/store or origin-specific downstream gate implementation.
6. **Research, late target and operator demonstration.** Prove a child mutation
   re-earns impacted semantic/execution evidence before comparison and preserves
   holdout. Demonstrate late Pine port on the simple control using existing
   Pine2Python analysis/traces/proof and first divergence; TV verdict remains an
   external gate until actually obtained. Describe MT5/LEAN as unimplemented
   targets until a real adapter/test exists. Demonstrate an idea/source ambiguity
   through specification, expected cases, reference, visual, fixed run, authorized
   search and target status without relying on conversation memory.

## Proof and regression matrix

| Required outcome | Minimum observable evidence |
|---|---|
| Greenfield semantic validation without Pine | New reference lineage/spec/cases/ledger/verdict; no Pine artifact or TV prerequisite through 1.5. |
| Preserved source authority | Exact original/source hash and criterion mapping; unknown meaning blocks faithful-replication claims, while selected proxy correctness is independently tested and fidelity remains qualified. |
| Simple and stateful internals share a narrow boundary | MA and bounded pivot/BOS outputs accepted by the same consumer/driver without copying the broker. |
| Causality is falsifiable | Pre-authored expected cases plus deliberate early pivot/decision mutant fails; timestamps and prefix checks pass. |
| Event coverage and visuals | One accepted and one rejected/expired case followed through rule/state/intent/broker/terminal links; chart sourced solely from ledger. |
| Honest execution | Gap, next-open, cancellation/expiry and applicable stop/target ambiguity cases; reason-coded uncertainty, adverse policies; explicit feedback check for fill-aware consumer if supported. |
| Data and parity integrity | Conflicting duplicates block; identical duplicates disclosed; required-field/duplicate-key errors; numerical and alignment first divergence preserved. |
| Safe research/promotion | Missing/stale manifest, absent baseline, unauthorized search and cross-family promotion rejected at service boundary; jobs/proposals cannot bypass. |
| Compatibility | Existing engine fixtures/stored versions remain usable under explicit legacy route; additive migration tested on old database shape. |
| No conflated verdicts | Semantic PASS, execution PASS, economics result, platform parity, TV verdict and production status shown independently. |

### Origin/operation acceptance scenarios (planned bounded fixtures)

| Case | Required evidence and negative control |
|---|---|
| A — native creation | Explicit MA timing/risk spec and independently authored cases; source fidelity/translation objective not applicable, no forced discretionary preparation. |
| B — native replication | Immutable deterministic source, rule mapping and supported output equivalence; unauthorized strategic change rejects replication claim. |
| C — native improvement | Accepted parent's exit-policy child, transformation rationale, impacted semantic/execution tests and economic comparison; original remains unchanged. |
| D — discretionary translation | Qualitative swing/displacement/selection source, ambiguity inventory, selected operational definitions, independent expected cases and reference; delayed pivot known-time explicit, proxy semantic correctness does not grant exact trader equivalence. |
| E — discretionary adaptation | D's child removes a filter or changes threshold/entry to pursue frequency/economics; transformation and objective authorization, semantic/execution proof and comparable results; cannot call adapted child an exact replica. |
| F — mixed-origin components | Deterministic indicator plus discretionary selection; preserve executable rules, translate only selection, common reference/execution acceptance. |

Include negative fixtures for missing transformation provenance, a falsely
claimed fidelity PASS based only on proxy tests or profits, premature future
information, changed operation without a transition record, and provisional
promotion. Include positive evidence that both fidelity-oriented and authorized
performance-oriented translations use the same gates, while recorded/controlled
randomness remains reproducible. These are preparation/provenance variants of
the two reference consumers, not six new engines. Existing scenarios and metric/
chronology/legacy compatibility checks remain required.

Use focused new tests first, then the existing `app/tests.py` suite, service
`tests/test_core.py`, Node runtime tests and the vertical fixture where affected.
Future commands include `.venv\Scripts\python -m unittest discover -s app -p
tests.py`, service unittest discovery with its `src` on `PYTHONPATH`, `npm test
--prefix services/pine2python`, and
`.venv\Scripts\python agentic\testscripts\pine2python_vertical.py`.
Add focused reference tests in the existing test convention; exact class names
are assigned with implementation. API/UI changes require the running app,
relevant blocked/passed/legacy states, console and responsive/accessibility
checks. A startup or historical test count is insufficient. Environment and
dependency repair is a separate observed prerequisite if a command cannot run.

## Compatibility, unresolved work and execution handoff

Do not mass-migrate stored lineages, fabricate new-stage PASS values, rewrite
Pine2Python, change exact source bytes, erase original evidence, or reimplement
the offline TgSignalSniper management lane. Existing legacy evidence keeps its
meaning. Explicit migration creates new evidence tied to old IDs; rollback
leaves original versions and legacy dispatch available. No force push or Git
cleanup is part of this plan.

Keep all current SEM/TIME/DATA/PROOF/VIS/SERV/ECON issues and their evidence.
Phase scheduling changes their applicability, not their truth. Target visual
issues can remain open during reference research when they do not invalidate
source interpretation; unknown core structure/sweep/HTF meaning blocks faithful
source-equivalence claims. A complete explicitly selected interpretation can
earn semantic acceptance with its own independent cases and a qualified fidelity
verdict; unresolved executable behavior stays blocked and provisional experiments
cannot become accepted/promotable. Existing SMC legacy verdicts are unchanged.
Economic acceptance follows a verified
reference/execution package, while final Pine acceptance remains compulsory for
Pine deployment. A bounded pivot example proves the interface, not SMC recall,
source fidelity, profitability or root closure.

Next implementation task: read root AGENTS, architecture constraints, this plan,
operator, applicable prompts and open issue records; recheck HEAD and callers;
load `bridgecode/best-agent.md`, `writing.md`, `monoprompting.md` (and Taste only
for material discretionary expression), create the active CavePrompt board,
freeze slice 1–2 acceptance and exact file ownership, then implement and test.
Advance toward both consumers and backend gate enforcement; report any slice
boundary that remains unimplemented. No unresolved user-owned choice currently
blocks this plan. Strategy-specific interpretations, target limits and execution
assumptions must be settled from evidence or explicit user decisions before a
particular strategy is accepted.
