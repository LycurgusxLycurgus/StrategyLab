# StrategyLab evidence architecture and handoff map

Status: durable project map; reference-first implementation accepted after terminal independent review, 2026-10-17.
The reference-first contract is specified in
`agentic/reference-first-migration-plan.md`. New API intake defaults to
`reference_v1`; existing versions and direct callers without a selector retain
`legacy_pine_v1`. Python2Pine is the public workflow name; internal Pine2Python
package paths and existing API routes remain compatibility interfaces. This document is the compact recovery
entry point for the whole repository. The detailed, future-model-facing issue
register and proof obligations live in
`STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`; this map records its ownership, flow,
maintained files, durable lessons, and current limits. Neither document
reconstructs the deleted conversation verbatim or claims that SmartMoney-4 is
profitable or TradingView-accepted.

The plan's 2026-10-13 refinement separates strategy origin
(`systematic_native`, `discretionary_origin`, component-classified `hybrid`)
from development operation (`create`, `replicate`, `translate`, `improve`).
These are provenance/specification responsibilities inside the existing
workflow versions. Both origins converge on one reference/execution/evidence
pipeline. Translation records interpretations, operational formalizations and
adaptations; reference semantic acceptance and source fidelity have separate
evidence. A selected proxy can be correct against its own specification without
proving exact discretionary-source equivalence. `app/reference_evidence.py`
enforces these metadata and gate distinctions; bounded MA and pivot/BOS fixtures
exercise the common runtime. This is not an arbitrary-strategy translator.

## Scope and current decision

StrategyLab remains the system of record for source authority, frozen parents,
criteria, datasets, phase state, Python engines, mutations, economic evaluation
and promotion. Pine2Python is an embedded evidence instrument: it parses Pine,
reports supported capabilities, executes only its bounded supported subset,
generates deterministic proof artifacts and standard traces, and compares
caller-owned traces. It does not own StrategyLab lineage, optimization,
mutation, promotion or market-data acquisition. TradingView remains authoritative
for official compilation, feed/runtime behavior, drawings, realtime/replay
behavior and human acceptance.

The active SmartMoney-4 artifact is the registered v6.3 coverage candidate
`pvr_362b3c72c6d2e797c46a`, based on the exact source hash recorded in the
unresolved-proof register. Its current evidence is source-accepted,
parse-complete and statically reviewed, with
`TRADINGVIEW_REVIEW_REQUIRED`; its local runtime is unavailable because the
analysis records `request.*` as `REQUEST_RUNTIME_UNVERIFIED`. The v6.3 line
keeps 71% as the coverage-oriented default (75% selectable) and ledger-backed
history for pending, missed and open records, but these are not claims of
official TradingView acceptance, Python parity, profitability or production
readiness. PF and win rate remain diagnostics, never Phase 1 filters.

The authoritative detailed status, issue IDs, evidence locators and reopening
conditions are maintained in `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`.

## Project memory and maintained flow

The repository has one instruction file: `AGENTS.md`. All phase prompts and the
embedded service use it. The old service-local instruction file was consolidated
into that root file and is removed as part of this recovery change.

The reference operational flow is:

```text
0 source/idea intake -> 1 executable specification -> 1.5 independent semantic cases
  -> 2 causal reference execution/data acceptance -> 2.5 fixed economic baseline
  -> 3–4 authorized training-only optimization/mutation -> 5 late target port/parity
  -> 6 platform/forward/operational acceptance
```

Indicators can earn semantic acceptance before a separate child adds strategy
orders. Pine and TradingView are not early prerequisites for this route. The
preserved legacy flow is:

```text
Pine Workbench / Phase 0
  -> Phase 1 criteria and research
  -> Phase 1.5 Pine build + TradingView/user acceptance
  -> Phase 2 Python port + criterion-level trace parity
  -> Phase 2.5 faithful economic qualification
  -> Phases 3/3.1 whitebox diagnostics and mutation
  -> Phases 4.1/4/4.2 bounded hybrid/viability work
  -> Phase 4.3 successor decision
  -> production robustness, execution, forward and operational gates
```

Every phase prompt now reads the shared phase operator and the unresolved-proof
register, carries source/data/settings/proof identities and relevant issue
dispositions, and blocks dependent work when required evidence is missing or
stale. The operator owns the shared evidence contract; each strategy criteria
manifest owns strategy-specific correctness; the register owns unresolved
boundary status and proof-to-closure requirements.

The 2026-10-20 prompt-contract clarification makes the operator's
`Origin-operation coordination contract` authoritative for separate origin and
operation axes, interpretation/formalization/adaptation, per-rule transformation
provenance and conditional source-fidelity duties. All ten standalone prompts
contain phase-specific `Origin/operation duties` with required handoffs and
rejecting controls. A-F cover native creation/replication/improvement,
discretionary translation/adaptation and mixed components; they validate the
workflow, not a requirement to create six strategies per run. Mixed-origin
`hybrid` does not justify a statistical Phase 4 layer. The shared route precedence
prevents retained Pine-specific legacy prose from overriding reference work.
Source coverage and preservation checks plus independent review passed; no
runtime or automated-test code changed in that prompt-only cycle.

### Maintained file tree

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Single repository instruction; project constraints are maintained here in architecture. |
| `agentic/reference-first-migration-plan.md` | Reference-first phase ownership, contracts, compatibility and staged proof requirements. |
| `app/reference.py` | Registered MA/pivot detectors, causal ledger, shared next-open broker, ledger-derived casebook. |
| `app/reference_evidence.py` | Provenance, independent semantic cases, content-verified evidence, baseline/search/child/target gates. |
| `app/reference_tests.py`, `agentic/testscripts/reference_vertical.py` | Focused contracts and isolated two-consumer demonstration. |
| `PINE2PYTHON_INTEGRATION_REPORT.md` | Historical integration architecture and validation record. |
| `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` | Current recoverable context, issue ledger, root-proof bundles, non-proof and handoff. |
| `agents/translation and generation/agents/codex_phase_operator.md` | Shared phase contract, Phase 0–Production routing and evidence rules. |
| `agents/translation and generation/whitebox/*.md` | Standalone prompts that apply the shared contract to each phase. |
| `agents/docs/universal_mutation_constitution.md` | Additional guardrails for Phases 3–4.3. |
| `services/pine2python/` | Typed local/HTTP analysis, bounded runtime, proofs, traces and parity boundary. |
| `app/`, `strategies/` | StrategyLab API, engines, storage, UI and parent definitions. |
| `pre-strategies/` | Inspectable source and immutable source-derived Pine candidates. |
| `artifacts/strategy-development/` | Strategy lineage, criteria, proof, review and phase evidence. |

### Reference runtime and evidence boundary

`BacktestEngine.run` dispatches explicit `reference_v1` to the registered
`reference_ma_cross_v1` or `reference_pivot_bos_v1` consumer. Both share one
decision-only execution driver: bar timestamps denote opens; decisions use
closed bars; earliest entry is next open; fixed quantity, static decision-time
ATR stop, optional R target, adverse stop-first ambiguity and censored cutoff
are explicit in `EXECUTION_CONTRACT`. Fill-aware feedback is unsupported.
Selecting that exact contract also declares numeric execution defaults (including
quantity, ATR risk, capital, costs and disabled target); explicit parameters
override those disclosed values. They are not inferred from strategy profit.
Ledger collection cannot change decisions or economics; the HTML casebook
renders saved trace/ledger, not another detector. Expandable rows expose the
complete saved event, including rule/state/lifecycle and evidence references.

`DataService` audits before normalization and records a per-dataset raw-quality
sidecar with raw and normalized hashes. Missing historical raw evidence remains
unverified unless an explicit normalized-only limitation is accepted; stale or
blocked audits reject acceptance. Parity rejects duplicate keys and absent
required fields rather than overwriting or comparing two missing values.

`Repository.workflow_evidence` is additive to existing databases. Immutable
JSON/HTML artifacts are checked against actual file bytes and current
spec/source/code/dataset/execution dependencies before reuse. `MutationLabService`
guards runs, queued optimization, proposals, saves and promotion; UI display is
not the enforcement boundary. Independent cases precede a fixed baseline;
search additionally needs a declared objective, parameter domains and a frozen
train/holdout boundary. Reference search sees only bars closed by train_end.
`objective_metric` defaults to `existing_score_v1`; explicit net_pnl/profit_factor
maximize and max_equity_drawdown_pct minimizes within the existing optimizer.
Children revalidate; parent evidence is not copied as child PASS.
Authorization compares effective values across parent/child parameter unions,
including omitted keys: `effective_parameters` is shared with reference runtime.
Removing an explicit value cannot bypass authorization by selecting a default.
Legacy offline
hybrid trade-filter experiments reject reference versions because they lack a
causal reference adapter. Legacy behavior otherwise remains separate.

Semantic, data, execution, economic, target, platform and operational statuses
remain independent. `qualified_reference` means declared economic criteria, not
production readiness. Native replication requires independently adjudicated
source-oracle cases tied to original source bytes; proxy tests and profitable
runs cannot manufacture source fidelity. The bounded late MA Pine adapter uses
the existing workbench and compares features/signals; broker parity remains
blocked pending corroboration, and official TradingView review is external.
MT5 and LEAN adapters and operational acceptance are unimplemented, not PASS.

The offline TgSignalSniper management lab is a separate StrategyLab research
lane owned by `app/tg_import.py`, `app/tg_models.py`, `app/tg_replay.py`,
`app/tg_validation.py`, and `app/tg_lab.py`, with routes in `app/main.py` and
the `tg-management` panel in `app/ui/`. It accepts only a finalized,
content-addressed package, rejects SQLite WAL/SHM sidecars, reads source
databases in immutable query-only mode, verifies the declared operational
migration (known 16–22 plus only capability-compatible additive later
versions), tick archive codec/checksums, broker symbol economics and policy
identities, and never connects to MT5, Telegram, AutoKraken, or a live account.
Baseline realized P&L uses the imported broker deal record; exact tick replay is
for counterfactual management/target policies, with one-second paths remaining
explicitly approximate. Search uses chronological walk-forward development and
one untouched holdout evaluation, and statistical promotion advice is not a
production or trading acceptance.

The GHL/DC strategy line also exposes opt-in Phase 4.2 entry black-box veto
controls in `app/lab.py` and `app/backtest.py`. They are disabled by default,
apply before order-concurrency handling, and emit side/hour/month diagnostics;
they do not alter the shared phase prompts or the Pine2Python/TradingView
acceptance boundary.

GitHub commit and fork synchronization are repository operations rather than
proof evidence. The former copy/paste packet for a separate thread was removed
once that workflow became the authorized current task; this map records no
remote synchronization or TradingView verdict. A clean commit or merge never
supplies a trading or TradingView verdict.

## Reusable lessons that are sufficiently resolved

These are process mechanisms that can be carried into future creation,
translation and modification work. “Resolved” means the repository has a
clear contract and demonstrated implementation pattern; it does not mean that
the resulting trading idea is economically successful.

1. **Freeze lineage before mutation.** Give every source, dataset, contract and
   child an immutable identity/hash. Record the exact semantic hypothesis and
   keep rejected parents available for comparison.
2. **Distill a source-cited macro checklist.** Separate hard prerequisites,
   conditional rules, quality grades, context and alternate variants. Do not
   let a later generated checklist silently change the source model.
3. **Separate three questions.** Emit detector events first; evaluate checklist
   gates second; evaluate order concurrency/lifecycle last. A missing trade is
   then classifiable as `DETECTION_MISS`, `CHECKLIST_FAIL` or
   `LIFECYCLE/RENDER_SUPPRESSION` instead of being “fixed” by relaxing a gate.
4. **Use event-level accounting.** Every candidate receives one terminal
   outcome and a first-failure funnel. Counts are per event, with long/short
   symmetry and preserved rejected candidates.
5. **Make time provenance explicit.** Store source, known/confirmation,
   readiness, activation, fill and exit timestamps. A marker may point at a
   source wick, but it must not appear before the bar on which the information
   became knowable. Confirmed-bar gating is the default for persistent state.
6. **Keep raw detection and filtered views separate.** Coverage modes may expose
   more source-valid candidates, while trader mode stays minimal. Rendering
   caps must never be detection caps, and a drawing failure must not delete a
   ledger event.
7. **Use frozen timestamp-owned drawings.** Historical geometry is materialized
   from immutable records, with finite deterministic right edges. It must not
   depend on viewport position, current `time`, or fragile old `time[]` lookups.
8. **Make data/feed identity first-class.** Record instrument, venue, session,
   timezone, timeframe, warmup, source file hash, row count and data-quality
   findings. Never relabel a legacy feed as the requested native feed.
9. **Use the right tool for each proof.** Code/Pine2Python handles static
   analysis, deterministic census, fixtures, prefix/reload stability, source
   hashes and first-divergence reports. TradingView handles official compile,
   chart object behavior, replay/realtime timing and visual human review.
10. **Keep the acceptance boundary explicit.** Local parity is not TradingView
    acceptance; a proof dashboard is evidence, not self-approval. Store the
    exact bytes, settings, signatures, screenshots and user/expert verdict.
11. **Measure economics without steering Phase 1.** Report setup coverage,
    outcomes, PF, win rate, costs and sample size separately. Phase 1 seeks a
    broad source-faithful base; asset/timeframe adaptation and losing-trade
    reduction belong to later phases with out-of-sample controls.
12. **Change one conceptual dependency at a time.** Use a named child, the same
    validation window and symmetric positive/negative fixtures. Stop when a
    proposed rule needs contradictory exceptions or removes an annotated valid
    case.

## SMC-specific status

### Working or bounded enough to preserve

- Dark, minimalist trader/reviewer presentation, compact checklist, risk
  calculator, Fib/range/POC/FVG geometry and position-style historical cards.
- Selectable 71%/75% Fib entry and optional POC checklist score are explicit
  settings. 71% is the coverage-oriented default; 75% remains the stricter
  comparison.
- Confirmed 15m pivots, body-close BOS, causal FVG bookkeeping, prior-completed
  4h context, strict sweep candidate semantics and OHLC ambiguity codes have a
  documented contract or diagnostic implementation. Their cross-feed and
  TradingView behavior remains issue-scoped; do not infer acceptance from a
  local implementation alone.
- Setup history is ledger-backed rather than fill-backed in the v6.3 candidate,
  so a valid setup that was missed or never filled remains inspectable. The
  exact generated source still requires TradingView runtime and user review.

### Partial or unresolved

- **Structure ownership and bias:** independent 2/2 levels plus extreme-level
  selection can select an internal opposing break as the macro direction. The
  `v6_bias` shadow guard did not materially change aggregate counts and is not
  promoted. Exact expert-labelled BTC and native OANDA gold bars are required
  before a new owner rule is safe.
- **Sweep recall:** wick/reclaim plus opposite body break is operationalized,
  but expert cases still report missed LQ events. This is a detection question,
  not permission to remove the sweep requirement from reversal semantics.
- **Short/long asymmetry:** local windows show materially different outcomes;
  no blind direction inversion or generic trend veto is justified.
- **Range ownership and endpoint selection:** the v6 endpoint repair is
  reproducible, but its validity on all expert examples is not adjudicated.
- **POC precision:** the bounded profile and neighboring-row tolerance are
  inspectable; the video’s “near” judgement is not a universal numeric truth.
- **HTF/feed parity:** completed 4h logic is deterministic on BTC, while the
  available legacy gold feed has unverified sessions and incomplete buckets.
- **Economic performance:** current PF/win rate remain below deployable
  confidence on reused windows. More visible entries are a coverage improvement,
  not evidence of an edge.
- **TradingView and trace parity:** earlier evidence localized a FEATURES
  divergence while DATA/SIGNALS lanes were reported as matching for an older
  comparison. The current v6.3 proof is `TRADINGVIEW_REVIEW_REQUIRED` and its
  local PineTS runtime is unavailable because of `request.*`; neither result is
  a current parity or acceptance pass.

## Rejected approaches and why

- v7/v8 restrictive protected-owner/extreme gates: they removed source-valid
  setups before checklist evaluation and contradicted the coverage objective.
- Blindly flipping short direction, adding a generic trend filter, or using PF
  to delete setups: these change the strategy rather than diagnose detection.
- Fill-only history rendering: it made the chart look empty and hid missed or
  pending source setups; v6.3 removes that presentation suppression.
- Treating a matching Python implementation as independent TradingView proof:
  both can share the same mistake.

## Handoff actions

### Pine2Python / service

The service implements the broad boundary (analysis, capabilities,
supported local execution, proof generation, standard traces and parity). This
architecture map carries its binding safety rules: fixed worker invocation with
bounded input/output and timeout, caller-owned candles only, no arbitrary code
or path execution, versioned schemas, no silent repairs/fabricated events, and
no StrategyLab lineage or economic ownership. No strategy-specific detector
rewrite belongs in the service.

The next reusable addition should be a versioned evidence-bundle adapter with
fields for:

```text
source_hash, parent_id, dataset_manifest, criteria_manifest,
event_id, detector_fields, checklist_fields, lifecycle_fields,
source_time, known_time, ready_time, first_failure, render_id,
tradingview_signature, acceptance_status
```

StrategyLab should populate that adapter; Pine2Python must preserve unknown or
unsupported fields instead of inventing values. Add it only after the current
service schema tests and the affected strategy's first FEATURES divergence are
localized.

### Main StrategyLab / phase integration

The operator and all standalone phase prompts now integrate the lessons. Require
the macro checklist, immutable lineage, event-level funnel, data/feed manifest,
golden cases, timestamp provenance, static/runtime/browser role separation and
explicit unresolved ledger. Default to broad source-valid coverage; reserve
PF/WR optimization and asset-specific filters for later phases. Keep indicator
acceptance separate from strategy profitability acceptance. The register's
cross-strategy gate requires the same failure mechanism to reproduce on a
materially different non-SMC consumer before a mechanism is called reusable.

## Validation entry points and next gate

The 2026-10-17 migration cycle passed terminal independent review after one
bounded effective-parameter authorization correction. Regression evidence:
combined application/reference suite 171 passed before the reference-only
correction; final affected block 33 passed (4 data-integrity, 24 reference,
5 parity tests). The unchanged complete service suite passed 21 tests, Node
runtime passed 2, and legacy vertical parity passed 240 aligned rows. New
reference modules passed Ruff; UI syntax and diff whitespace checks passed.
Real browser checks covered accepted/blocked/legacy states, indicator-source
fidelity limits, labeled registration, 390px layout, casebook event details,
console health and delayed-response family-selection ownership.

Run the reusable reference demonstration with
`python agentic/testscripts/reference_vertical.py --pine-target` and focused
checks with `python -m unittest app.reference_tests`. The final reviewed run is
`artifacts/strategy-development/reference-demo/run-20261017T142234Z-a299b75e/`.
Binary/hash readback verified both parent and both child semantic manifests and
the casebook against current code and parent authorization. The local Pine
feature/signal result is `PARITY_PASS` on 12 rows; target broker parity remains
`BLOCKED`, official platform status `TRADINGVIEW_REVIEW_REQUIRED`, and production
unaccepted. These bounded controls do not close historical SMC issues.

The smallest relevant regression surface is the StrategyLab unit suite plus
the Pine2Python vertical/schema checks, followed by exact-byte/hash and
document-link checks for evidence changes. The integration report's historical
test counts are not reused as a fresh result; new runs must report their own
commands and artifacts. Browser checks are required for UI or TradingView
claims, and a service startup/health check alone is insufficient.

Do not promote SmartMoney-4 until the active source/proof identity passes its
declared local or external gates, exact expert BTC and native OANDA:XAUUSD
cases adjudicate the relevant bias/sweep boundaries, the first FEATURES
divergence is localized, and TradingView exact bytes receive an explicit user or
expert verdict. If cases or external evidence remain unavailable, retain the
issue as unresolved rather than adding another restrictive detector theory.


## Binding repository constraints and verification map

On 2026-10-08 the twelve project-rule records below moved from root AGENTS.md
into this architecture map. Their meanings remain binding for their existing
supported paths. The implemented versioned reference route changes phase
ownership without granting source, target or production acceptance.
Read these constraints before affected source, proof, service or phase work.
The text is preserved verbatim to prevent rule loss during relocation.

Applicability: the preserved early accepted-Pine/Python prerequisite and Phase 1
signature scheduling apply to `legacy_pine_v1`. For `reference_v1`, semantic/data/
execution gates replace that early prerequisite; Pine-specific source/proof and
visual duties apply when relevant to source fidelity or the Phase 5 target.
Unresolved SMC-specific proof obligations remain unchanged.

### Preserved repository constraints

- Architecture: StrategyLab owns strategy lineage, datasets, Python backtests, optimization, mutation, and promotion; the independently runnable `services/pine2python/` service is embedded in the same repository and provides Pre-Phase 1 Pine creation/adaptation, Pynescript analysis, bounded PineTS execution, deterministic proof artifacts, standard traces, source-fidelity review packages, and parity comparison through a typed local/HTTP boundary. Existing-indicator work freezes the user-supplied Pine bytes as the immutable workbench parent, declares protected source regions and visual contracts, and selects event-focused trace fixtures before TradingView review. TradingView Basic corroboration uses the original and exact child source for focused multi-timeframe visual review, then one generated on-chart signature dashboard over an exact window instead of CSV export; a stateful revision may declare a source-owned state-reset boundary so local execution and limited chart history own identical warmup, while revision settings preserve exact TradingView ticker/timeframe separately from dataset shorthand. Accepted Pine and Python traces are required before optimization or mutation. Direct virtualenv/Node operation remains supported alongside a two-container Compose topology where StrategyLab is dual-homed on a localhost edge network and an internal service network, while Pine2Python remains internal-only.
- TradingView corroboration never depends on paid CSV export, alerts, webhooks, or browser scraping. A local PineTS capture is evidence, not official TradingView acceptance; only matching dashboard values plus an explicit user verdict and screenshot SHA-256 may produce `TRADINGVIEW_ACCEPTED`.
- A Codex agent may perform TradingView corroboration through the user-authenticated interactive UI: remove only explicitly scoped stale indicators, paste the exact instrumented bytes, add the script, wait for the declared closed-bar window, and save the dashboard screenshot. This convenience never replaces the generated signature contract or the user's explicit verdict.
- Pine revision and proof files are byte-identity artifacts: hashes must be computed from and verified against the exact UTF-8 bytes written to disk, with no platform newline translation. Stateful Basic-plan proofs may bound local runtime only when the immutable revision declares and implements the same state reset at or before the proof window.
- Existing-source indicator repair must not start from a rewrite. Extract and hash the authoritative source, protect every accepted calculation and visual region outside the named defect, permit one reviewable semantic change per child revision, and require both source-fidelity evidence and focused TradingView review; parser, PineTS, trace, or signature agreement never substitutes for visual product acceptance.
- Pine2Python must preflight TradingView's 64-plot budget before browser corroboration, counting `alertcondition` and other plot-count calls and warning near the lower-bound limit because series-valued parameters may consume additional counts. Stateful proofs must separate supplied state-history warmup from the hashed proof window; history-origin-dependent object IDs are diagnostic only and cannot be parity fields when the strategy consumes only their stable lifecycle state.
- Phase 1 indicator/strategy work must begin with a source-cited criteria manifest that separates hard rules, conditional rules, quality grades, context, and isolated alternatives. It must then account for every structural candidate through an event-level terminal-failure funnel, report realistic setup frequency and direction distribution, distinguish detector misses from checklist failures and lifecycle suppression, and keep indicator detection independent from later order-concurrency policy. “At least one long and one short” is never sufficient acceptance evidence.
- Generated TradingView proofs must preflight both plot counts and compiled-token pressure. Stream hashing should evaluate each declared expression once and feed a shared fixed-lane mixer rather than duplicating expression code per fingerprint lane. Table proofs pack fingerprints into one matrix and metadata into one array; PineTS runtime proofs retain arrays and exact hidden trace exports. A source may opt into proof-only main-body relief only by explicitly marking a pure rendering block with matching `P2P_PROOF_COMPACT_BEGIN` / `P2P_PROOF_COMPACT_END` comments; calculation or state blocks may never be compacted. Browser compilation of the exact generated bytes remains a required gate because source size is not a reliable proxy for TradingView's compiled-token limit.
- Phase 1 signature mismatches are localized in this order: contiguous field groups, time-window partitions, then exact-bar primitive probes. Repair the first causal divergence before rerunning the complete proof. History-origin display counters or latest-object pointers may be diagnostic-only only when strict event signals and lifecycle states already encode the same strategy-consumed behavior; record every exclusion and its strict replacement in the fidelity contract.
- Persistent Pine history renderers must own frozen event timestamps and use `xloc.bar_time`; viewport-driven redraws and historical `bar_index` coordinates are rejected because they can fail to materialize after direct navigation or exceed TradingView's 5,000-bar drawing boundary. Their automatic archive cap must be derived from declared line/box/label budgets, not exposed as a trader history setting. Browser acceptance must directly jump to known feature-positive and feature-negative historical setups without pan/zoom, repeat after reload, and verify collision-free geometry.
- OHLC lifecycle ambiguity must be narrowed by price-path invariants before emitting `AMB`: an unfilled entry and stop on one bar is a deterministic stop when the bar opens on the valid side of the stop, while entry/target, stop-gap, or already-open stop/target coexistence remains ambiguous unless lower-timeframe ordering proves otherwise. Every remaining ambiguity requires an explicit reason code and browser-review timestamp.
- The single root instruction file also governs `services/pine2python/`: never label local PineTS execution as official TradingView verification; preserve original source bytes and immutable content hashes; never execute caller-provided JavaScript, Python, shell, imports, or arbitrary host paths; launch only the fixed Node worker with an argument array, `shell=False`, bounded input/output, a timeout, and a per-job directory; accept caller-supplied candles only and never fetch market data; version public schemas and expose unsupported or uncertain semantics; do not silently repair Pine or fabricate broker events; require matching dataset fingerprints before any TradingView execution fingerprint can pass; and keep Pine2Python limited to analysis/comparison rather than optimization, mutation, promotion, or StrategyLab lineage creation.

### Responsible boundaries and implementation status

These are source-inspection results for relocation, not fresh runtime or browser
validation. Implemented primitives and unverified policy requirements are stated
separately; an inspected code path does not establish perpetual enforcement.

| Record (order above) | Responsible files / evidence | Status and limitation |
|---|---|---|
| 1 — ownership, original parent, review, topology | app/pine_workbench.py; app/pine_review.py; app/storage.py; app/reference_evidence.py; app/lab.py; services/pine2python/; compose.yaml; phase operator | Revision/review/service primitives and topology preserved. New reference operations have backend evidence gates; accepted-Pine/Python early prerequisite remains legacy-only. Docker runtime availability is environment-specific. |
| 2 — dataset-first TV acceptance | services/pine2python/src/pine2python/proof.py; app/pine_workbench.py; TradingView observation APIs | Comparison/verdict fields exist; exact external dashboard, screenshot and human verdict remain evidence duties. Local result cannot close them. |
| 3 — scoped interactive TV operation | services/pine2python/docs/tradingview-browser-corroboration.md | Operator constraint; no browser operation or acceptance performed by relocation. |
| 4 — byte identity and reset | app/pine_workbench.py artifact write/readback; service artifacts.py; service.py state_start_ms | Exact-byte storage and window bounds inspected. Full source-owned reset equivalence remains strategy-specific and unverified where runtime is blocked. |
| 5 — source repair fidelity | app/pine_review.py; existing source/design contracts | Review primitives present; one semantic child change and focused visual verdict are acceptance policy, not universal automatic enforcement. |
| 6 — plots, warmup, diagnostic IDs | service analyzer.py; proof.py; service.py; test_core.py | Plot inventory/warmup primitives and regression cases exist. Series-valued extra counts and diagnostic exclusions still need declared review. |
| 7 — criteria/census/detection isolation | Phase operator; app/reference.py; app/reference_tests.py; SMC evaluate/event_accounting; golden regression_checks | Bounded MA/pivot causal ledger and independent cases implemented. SMC independent recall remains unproven; bounded interface proof does not close it. |
| 8 — expression mixer/table compaction | service proof.py; analyzer.py; test_core.py | Shared expressions, matrix/metadata packing and marked rendering compaction inspected. Browser compiled-token and exact-generated-source runtime gate remain external. |
| 9 — first divergence/exclusions | agentic/testscripts/pine_proof_field_groups.py, pine_proof_partition.py, pine_proof_probe.py; service parity.py | Localization tools preserved; strict replacement/exclusion audit remains required. Duplicate keys and missing required fields now reject before comparison; alignment first divergence retained. |
| 10 — historical rendering and budgets | pre-strategies/smart-money-4/ source; agentic/design/smart-money-4-clean-contract.md; VIS-001/TIME-003 | Timestamp renderer candidate and budget contract recorded. Exact direct-jump/reload/collision browser acceptance remains open. |
| 11 — OHLC ambiguity | SMC evaluator/design contracts; TIME-004 | Bounded classification contract exists. Real broker path/lower-timeframe ordering and reason-coded external review remain scope-specific. |
| 12 — nine service invariants | service runtime.py, models.py, analyzer.py, artifacts.py; fixed worker; service tests; compose.yaml | Fixed argument array, shell=False, timeout, per-job directory and explicit capabilities inspected. Output checks occur after process capture; this is not a claim of hard streaming-memory isolation. Caller-candle/no-arbitrary-code/role rules remain binding; no fresh security audit claimed. |

Reference-first implementation must preserve every applicable source, data,
service and target-validation constraint. When relocating phase-specific gates,
update the operator, prompts, register applicability, backend evidence checks and
this map together; retain legacy statuses and original artifacts. Unverified
requirements stay binding until supported closure or an explicit authorized
contract change. Implementation acceptance depends on current code and checks,
not this map alone; unfinished cycle evidence remains in agentic/analysis.md.
