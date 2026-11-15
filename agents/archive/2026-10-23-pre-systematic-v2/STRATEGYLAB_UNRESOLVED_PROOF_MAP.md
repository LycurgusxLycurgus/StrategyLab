# StrategyLab unresolved work and root-proof map

Status: maintained historical recovery record, updated 2026-10-17. This document is the
future-model-facing companion to `PINE2PYTHON_INTEGRATION_REPORT.md`. It is the
detailed register for unresolved boundaries, proof obligations, ownership, and
reopening conditions. It is not a claim that the SMC indicator is accepted,
that the strategy is profitable, or that the deleted conversation has been
recovered verbatim.

## Purpose and recovery limits

The prior phase-conversation thread was deleted. The repository still contains
the integration report, the phase operator and prompts, source contracts,
Pine2Python implementation decisions, deterministic tests, evidence bundles,
and SMC case material. Those artifacts reconstruct operational decisions only
where they are supported by inspectable evidence. They cannot reconstruct the
missing dialogue, intent that was never recorded, or a user/expert verdict that
was never persisted.

Use this file when a new model or task resumes StrategyLab:

1. Read `AGENTS.md` completely, then the binding repository constraints in
   `agentic/architecture.md`. The reference-first migration plan is at
   `agentic/reference-first-migration-plan.md`; consult the current migration
   note below for implementation evidence and its still-open acceptance limits.
2. Read `agents/translation and generation/agents/codex_phase_operator.md` and
   the applicable phase prompt.
3. Read this register, then the strategy-specific criteria and design contract.
4. Read `PINE2PYTHON_INTEGRATION_REPORT.md` for the historical integration
   result, not as fresh validation of the current dirty worktree.
5. Inspect the exact source, dataset, settings, proof and verdict artifacts
   named by the issue being worked.

The authority order is: explicit user instruction and verdict; root project
rules; source-cited strategy criteria and immutable source identity; verified
implementation and regression evidence; then summaries, prior reports and
model interpretations. When two records disagree, keep both identities,
identify the conflict, and resolve it at the responsible boundary. Never use a
new summary to overwrite an older immutable artifact.

## 2026-10-17 Python2Pine migration snapshot

New strategy work now defaults to `reference_v1`, publicly presented as
Python2Pine. Existing stored lineages retain `legacy_pine_v1`; old evidence and
Pine2Python APIs are not silently rewritten. The active operator and phase
prompts define Phase 0/1 specification, independent Phase 1.5 semantics,
Phase 2 data/execution, Phase 2.5 baseline/search authorization, Phases 3–4
research, Phase 5 selected-target acceptance, and Phase 6 operations. A novel
indicator may be accepted before a child adds order rules.

Current implementation evidence is local to this worktree. Terminal independent
implementation review passed; this is not broad strategy acceptance:

- Final affected checks passed 33/33: 24 reference, 4 data-integrity, and 5
  parity tests. Combined application/reference regression passed 171 tests
  before the final reference-only authorization correction. The correction
  rejects omitted parameters that select unauthorized effective defaults.
  `node --check app/ui/app.js` passed; browser checks covered accepted/blocked/
  legacy states, mobile layout, casebook and delayed-response selection safety.
- The isolated vertical run is
  `artifacts/strategy-development/reference-demo/run-20261017T142234Z-a299b75e/`.
  Its MA and bounded pivot/BOS references saved independent cases, ledgers,
  casebooks, fixed baselines, and authorized training-only children. The late
  MA Pine target had local feature/signal `PARITY_PASS` on 12/12 aligned rows;
  target stayed `BLOCKED`, platform stayed `TRADINGVIEW_REVIEW_REQUIRED`,
  source fidelity was `PASS_WITH_LIMITATIONS` for the chosen discretionary
  interpretation, economics remained unqualified, and production was not
  accepted. No TradingView human corroboration was performed.
- These bounded controls do not establish SMC behavior, source equivalence for
  other strategies, broker execution parity, profitability, cross-strategy
  transfer, or strategy-specific production acceptance. Keep the
  issue records below at their historical verdicts unless fresh evidence
  addresses their exact identities and criteria.

## Current project snapshot

### Ownership

| Boundary | Owns | Does not own |
|---|---|---|
| StrategyLab application and artifacts | Dataset acquisition and hashes, source lineage, phase state, Python engines, mutation, economic evaluation and promotion state. | Official TradingView runtime truth. |
| `services/pine2python/` | Pynescript analysis, capability findings, bounded PineTS execution, proof generation, standard traces, parity comparison, and registered generation. | Optimization, mutation, promotion, StrategyLab lineage, market-data fetching, or arbitrary Pine-to-Python translation. |
| TradingView | Official compile/runtime/feed behavior, chart object behavior, replay/realtime behavior, and visible corroboration. | Local artifact identity or user acceptance decisions. |
| User/expert reviewer | Explicit acceptance or rejection of the exact source/settings/evidence package. | Silent correction of source semantics through an unrecorded opinion. |
| Git synchronization | Explicit commits, remote comparison, and safe fork synchronization. | Changing strategy semantics or converting a Git result into a trading/TradingView verdict. |

### Identity and evidence observed in the current checkout

- The observed branch is `master`, with HEAD
  `ffe04aebe10a942f0043164b5f1ce8547cb11b58`; the checkout has substantial
  tracked and untracked user-owned changes. HEAD is not an identity for those
  uncommitted files. The observed `origin` is
  `https://github.com/LycurgusxLycurgus/StrategyLab.git`; the Hesse comparison
  remote is `https://github.com/Hesse66/StrategyLab.git`, fetched as
  `hesse/master` at `f5b1f9c1d5e93a984cf0328d1b0c6793095e8044` with merge base
  `f8e3e01be8d2cb8f691d8ba7d81d86e183082fb5`. These refs are Git evidence only;
  they do not change the proof or acceptance status below.
- The active SmartMoney-4 source is
  `pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine`, whose
  exact UTF-8 file SHA-256 is
  `5ef00859797f0dc960d3762b4d217fd76e92c70d7b0cb4d70a7f556909cf0718`.
  The inspected registered revision is `pvr_362b3c72c6d2e797c46a`, under
  workbench `pwb_f89ea6f3774a`, with proof `pev_a6fb9e4e8dd1a838d665`.
- That revision is source-accepted, parse-complete and statically reviewed, but
  its proof status is `TRADINGVIEW_REVIEW_REQUIRED`. Its instrumented proof
  source has SHA-256
  `fb69e209d4d6f41f61eac6066a1cdd15a5909ce5c6c45eb96e85759875b92c66`.
  The local runtime is `LOCAL_PROOF_RUNTIME_UNAVAILABLE` because the immutable
  analysis records `request.*` as `REQUEST_RUNTIME_UNVERIFIED`; this is a
  capability boundary, not a successful runtime comparison.
- Older SMC revisions have their own proof and TradingView artifacts. A
  signature, screenshot, or verdict attached to another source hash does not
  transfer to v6.3. The active v6.3 line is an indicator candidate, not an
  accepted indicator, accepted Python strategy, optimized parent, or production
  system.
- The integration report records a historical validation block of 97
  StrategyLab tests, 10 Pine2Python Python tests, two Node tests, a 240-row
  vertical parity fixture, static/Compose checks, and browser checks. Those
  numbers remain useful historical evidence of the integration work; they are
  not claimed as a fresh run against this task's final worktree.

### Evidence status vocabulary

The following labels belong to this document and do not replace API or phase
statuses:

| Status | Meaning |
|---|---|
| `OPEN` | The responsible boundary or required proof is not closed. |
| `LOCAL_FIX_PROVEN` | A bounded local correction has evidence, but external evidence, transfer, or a wider scope remains open. |
| `AWAITING_EXTERNAL_EVIDENCE` | Local prerequisites are sufficient; TradingView, native-feed, expert/user, or other external evidence is still required. |
| `ROOT_RESOLVED` | The cause was reproduced, localized, corrected at its responsible boundary, and all applicable root and transfer gates passed for the declared scope. |
| `SUPERSEDED` | A later immutable child replaces the issue's active path; the old evidence remains recoverable and the replacement is named. |

An issue status, a proof result, and a phase verdict are separate fields. A
`TRADINGVIEW_SIGNATURE_MATCH` can still require a user verdict. A
`LOCAL_FIX_PROVEN` issue can still block a phase whose scope depends on the
unproven part. A missing artifact is `missing`, never `PASS` by implication.

## What the SMC/Pine2Python work has already established

These are implemented or bounded mechanisms, not universal proof of every
strategy that may use them:

| Mechanism | Established evidence | Remaining boundary |
|---|---|---|
| Immutable lineage and byte identity | Workbench revisions, source/proof hashes, protected-source review, and binary artifact storage in `app/pine_workbench.py`, `app/pine_review.py`, `app/storage.py`, and service artifacts. | Every future child must preserve exact bytes and must not inherit a verdict from another identity. |
| Criteria before implementation | Phase 1 research/checklist artifacts and the active phase prompts require source-cited hard, conditional, quality, context, and alternative rules. | Each new strategy must create its own manifest; SMC rules cannot become a reusable trading specification. |
| Detector/checklist/lifecycle separation | SMC evaluators keep raw events, checklist fields, setup lifecycle and rendering evidence distinct; later phases are instructed to preserve the separation. | Independent detector recall and strategy order behavior remain empirical. |
| Event-level accounting | `event_accounting` and golden reports assign terminal states and first-failure information, with direction counts and censored window-end states. | Complete accounting is not recall; an independent opportunity inventory and expert labels are still required. |
| Dataset-first proof | Pine2Python fingerprints dataset and segments before execution streams; `DataService` owns exact dataset hashes and bounded Basic windows. | Native feed/session/timezone/HTF identity must still be verified for each external context. |
| Local Pine evidence | The service uses a fixed worker, caller candles, bounded requests, explicit capability blockers, standard traces, proof dashboards and first-divergence comparison. | PineTS/Pynescript are experimental local evidence; unsupported semantics and TradingView behavior require their own proof. |
| TradingView boundary | The generated dashboard, exact instrumented bytes, screenshot hash and explicit user verdict are separate from local capture/parity. | The v6.3 exact source still requires the external review and verdict. |
| Source-derived repair discipline | Existing-source workflow freezes the unchanged source, protected regions and one semantic child change before proving the child. | SMC structure ownership, sweep recall, and expert correctness are still open. |
| Timestamp-owned history | The SMC candidate and contracts use frozen event timestamps and `xloc.bar_time`, with a bounded object budget; the old-level/time-index failure was reproduced and repaired locally. | Direct historical navigation, reload, and any claimed realtime/replay first appearance still require TradingView evidence. |
| Economic separation | SMC viability reports coverage, outcomes, costs, PF, win rate, ambiguity and sample size separately; low PF is not used to delete Phase 1 events. | No current evidence establishes an edge, robustness, forward feasibility, or production readiness. |

## Shared phase contract now used by every phase

The phase operator is the shared owner. Each independently copied phase prompt
loads the operator, its phase section, and this register before acting, then
records the entry identities and applicable issue dispositions. The prompts do
not duplicate the whole contract, which keeps later corrections from drifting
across ten copies.

| Phase | Required evidence and stopping rule |
|---:|---|
| 0 / 1 | Freeze source authority, provenance, data/feed context and criteria. Separate hard prerequisites, conditional rules, quality grades, context and isolated alternatives. Select positive, negative and boundary fixtures; define trace fields and source/known/ready/action timestamps. Do not create a Python parent or optimize. |
| 1.5 | Use the exact candidate bytes. Preflight parse, plot count including `alertcondition`, compiled-token pressure, warmup/state assumptions and protected regions. Run local evidence, then focused TradingView review and one dashboard over a declared closed-bar window. The user accepts the exact source hash; local evidence cannot self-approve. |
| 2 | Port only the accepted Pine package. Map every criterion to Pine/Python locations and standard traces. Match dataset identity first, compare feature/signal/state/rejection/order/position/trade lifecycle, localize the first divergence, and use only predeclared tolerances or approved divergences. |
| 2.5 | Verify prerequisite freshness and hashes without repeating sufficient parity. Run and preserve the unoptimized baseline; evaluate economics under the frozen context. PF/WR may diagnose economics but cannot repair semantics or hide source-valid events. |
| 3.1 / 3 | Diagnose the current parent and test one conceptual dependency at a time. Preserve unchanged, added, removed, retimed and re-anchored opportunities, terminal outcomes and first-failure classes. A mutation cannot silently change the accepted semantic boundary. |
| 4.1 / 4 | Freeze decision-time information, target, ambiguity policy, chronology, opportunity preservation and complexity before outcome inspection. An offline survivor must reproduce in the live engine before promotion. |
| 4.2 | Keep the untouched evaluation boundary and admissible information set frozen. Record failed relationships. Discovery does not promote opaque behavior. |
| 4.3 | Carry forward evidence-backed constraints and unresolved issue IDs, not tuned content. A successor re-earns applicable Phase 1 through 2.5 and later gates under a new identity. |
| Production | Add chronological robustness, adverse execution, venue legality, forward reconciliation and operational controls. Earlier local, browser, parity or mutation evidence is not deployment readiness. |

Do not block every phase on every issue. Block only when the issue affects the
phase's accepted scope or invalidates an input identity. Do not close an issue
silently in a later phase; carry its ID, evidence, status and return route.

## Root-resolution proof standard

Mark an issue `ROOT_RESOLVED` only when all applicable conditions below are
observable in the issue's proof bundle:

1. **Complete identity.** Original, parent, candidate, criteria revision,
   dataset file and hash, exact symbol/venue/session/timezone/timeframe,
   settings, instrumentation/runtime versions, warmup/reset boundary, proof
   window and dependency environment are identified. Hash the exact UTF-8 bytes
   written to disk and verify them by binary readback.
2. **Reproduced failure.** Preserve the failing event, field, bar, timestamp or
   supported-path behavior. An aggregate count without a causal reproducer is
   not enough.
3. **Independent expected behavior.** Derive the expected result from the
   source contract, an expert-labelled case, a mathematical invariant, or a
   separately derived primitive. Two implementations of the same hypothesis
   are not independent semantic oracles.
4. **First cause localized.** Check data/context identity first. For signature
   mismatches use contiguous field groups, time-window partitions, then exact
   bar primitive probes. Do not drop a failing field merely to obtain agreement.
5. **Responsible-boundary repair.** The correction acts where the cause lives;
   source, instrumentation, dataset and adapter changes are distinguishable.
   Existing protected regions remain unchanged unless the issue explicitly owns
   them.
6. **Denominators reconcile.** Every emitted candidate has one terminal result
   at the observation cutoff; pending/open states are censored rather than
   silently failed; baseline-to-child comparison lists unchanged, added,
   removed, retimed and re-anchored cases; and an independently selected chart
   inventory counts opportunities neither implementation emitted.
7. **Applicable invariants pass.** Run relevant confirmation timing, prefix
   stability, warmup/reset equivalence, direction symmetry, missing-data,
   duplicate-prevention, object-budget and rendering-independence checks.
   Remaining OHLC ambiguity has an explicit reason code and review timestamp.
8. **External claims use external evidence.** TradingView compile/runtime/feed,
   historical drawings, replay/realtime timing and user acceptance cannot be
   closed by local PineTS or Python output.
9. **Durable, bounded regression.** Preserve the useful check in the repo's
   established test/artifact location, state the contexts actually tested, and
   give a reopening trigger for a changed source, settings, feed, runtime,
   protected contract or scope.

### Proof-bundle index

Reuse existing artifact formats where possible. A bundle for a resolved issue
should index the following, with each path's role and hash:

```text
identity:
  original_source, parent_source, candidate_source, exact UTF-8 SHA-256 values
  workbench/revision/parent IDs and one declared semantic delta
  criteria/research revision and protected-region comparison
  runtime, dependency, schema and instrumentation versions

inputs:
  dataset file, dataset SHA-256 and data-quality manifest
  exact symbol, venue, session, timezone, chart/Pine timeframe and settings
  supplied history warmup, source-owned reset boundary, and hashed [start,end)

observations:
  expected/candidate traces and declared field contract
  event ledger, first-failure funnel, terminal/censored outcomes
  independent positive, negative, boundary and state-transition cases
  contiguous-field/time-partition/bar-probe first-divergence evidence

external:
  exact instrumented Pine bytes and SHA-256
  displayed dashboard values and dataset/signature comparison
  focused and full screenshots with verified file SHA-256 values
  explicit user/expert verdict linked to the same source/settings identity

validation:
  commands, environment, execution date and actual results
  tested strategy x mechanism x context matrix
  unsupported claims, owner, phase route, residual limitations and reopen trigger
```

## Cross-strategy generalization gate

Use three labels instead of one vague “works” claim:

1. **Mechanism verified:** the named primitive passes its discriminating proof on
   the original SMC case or strategy.
2. **Transfer demonstrated:** the same failure mechanism is exercised and passes
   on a materially different non-SMC strategy, not merely another SMC asset.
3. **Strategy accepted:** that strategy independently passes its own semantic,
   TradingView, Python parity and economic/production gates.

For a reusable correction, keep the SMC reproducer and add a non-SMC consumer
that actually exercises the same boundary. Use positive, negative, boundary and
state-transition cases, choose validation windows before inspecting outcomes,
and change only declared strategy inputs or a thin adapter. No shared behavior
may special-case the SMC name, asset, venue or known fixture. Report the tested
strategy × mechanism × context matrix and explicit exclusions.

The existing `services/pine2python/tests/fixtures/ma_cross_atr_stop_v1/`
fixture demonstrates a useful transport/basic lifecycle comparison: its 240
rows align exact OHLCV and `state.position_size` under the declared
`next_bar_open` contract. It does not establish HTF ownership, sweep semantics,
rich FEATURES streams, persistent drawings, same-bar ambiguity, or broker-
emulator parity. For those boundaries, create a non-SMC fixture that consumes
the boundary rather than claiming transfer from an unrelated MA result.

## Explicit non-proof

The following observations are useful diagnostics but cannot close the listed
issues:

- Complete event accounting does not prove detector recall.
- One long and one short, a high setup count, or a higher PF on a reused window
  does not prove coverage or an edge.
- Mirrored synthetic prices do not replace independent market examples.
- Matching Python and PineTS implementations do not constitute an independent
  semantic oracle or official TradingView proof.
- DATA/SIGNALS agreement does not excuse a required FEATURES mismatch.
- A dashboard fingerprint is a comparison fingerprint, not a cryptographic
  source hash.
- A screenshot filename or stored hash string does not prove that the file was
  independently verified or that the user accepted it.
- A prior revision's signature or user verdict does not transfer after source,
  settings, data, instrumentation or scope changes.
- Compilation alone does not prove runtime completion, historical drawing
  persistence, reload stability, replay, realtime behavior or feed identity.
- A local state-reset declaration proves only the bounded reset contract; it does
  not prove the source has no state dependency outside the declared boundary.
- A parser/worker capability status does not make unsupported `request.*`,
  `varip`, imports, realtime semantics or arbitrary translation safe by default.
- Documentation or a phase prompt cannot prove that code enforces the rule.
- Successful commits, merges or remote synchronization do not prove trading or
  TradingView acceptance.

## Issue index

| ID | Category | Status | Blocks or informs | Owner | Next proof |
|---|---|---|---|---|---|
| REC-001 | `RECOVERY` | `OPEN` | Verbatim conversation recovery | StrategyLab/user | Recover an original export if one exists; otherwise retain this bounded record. |
| SEM-001 | `SEMANTICS` | `OPEN` | SMC indicator acceptance; any structural mutation | StrategyLab + expert | Expert-labelled internal-versus-owning-boundary breaks with preserved positives and negatives. |
| SEM-002 | `SEMANTICS` | `OPEN` | SMC recall and reversal semantics | StrategyLab + expert | Independent sweep opportunity inventory with known-level, reclaim, BOS and invalidation evidence. |
| SEM-003 | `SEMANTICS` | `LOCAL_FIX_PROVEN` | SMC endpoint/range acceptance | StrategyLab + expert | Adjudicate changed/re-anchored cases and causal endpoint timing on native contexts. |
| SEM-004 | `SEMANTICS` | `OPEN` | Optional POC/extended checklist | StrategyLab + expert | Tick/row calculation and 1m profile proof plus source-supported “near” cases. |
| SEM-005 | `SEMANTICS` | `LOCAL_FIX_PROVEN` | Causal feature ownership transfer | StrategyLab | A non-SMC strategy that consumes an equivalent event-to-feature linkage. |
| SEM-006 | `SEMANTICS` | `OPEN` | Phase 1 detector-recall claims | StrategyLab + expert | Independently selected continuous-window opportunity census and miss taxonomy. |
| SEM-007 | `SEMANTICS` | `OPEN` | Long/short and context interpretation | StrategyLab | Directional detector/checklist/lifecycle funnels with non-SMC transfer evidence. |
| TIME-001 | `TIME` | `OPEN` | HTF/repaint and realtime claims | StrategyLab + TradingView | Confirmed HTF values, prefix behavior and focused TradingView realtime/reload cases. |
| TIME-002 | `TIME` | `OPEN` | Local stateful proof and Python parity | StrategyLab + Pine2Python | Warmup/reset equivalence against supplied history and a stateful non-SMC fixture. |
| TIME-003 | `TIME` | `OPEN` | Historical first appearance and action timing | StrategyLab + TradingView/user | Direct-jump positive/negative cases, reload and replay/realtime sequence where claimed. |
| TIME-004 | `TIME` | `OPEN` | Indicator lifecycle and future strategy orders | StrategyLab | Price-path fixtures, lower-timeframe ordering where necessary, reason-coded residual `AMB`. |
| DATA-001 | `DATA` | `OPEN` | OANDA gold and HTF parity | StrategyLab/data owner | Native OANDA:XAUUSD 15m plus native completed 4h/session/timezone manifest. |
| DATA-002 | `DATA` | `OPEN` | Multi-context POC/profile and units | StrategyLab/data owner | Verified 1m coverage, units, sessions, gaps and missing-data behavior per context. |
| DATA-003 | `DATA` | `OPEN` | Economic qualification/generalization | StrategyLab | Predeclared untouched chronological windows and context-specific cost/benchmark evidence. |
| PROOF-001 | `PROOF` | `OPEN` | v6.3 TradingView acceptance | StrategyLab/Pine2Python | Localize earlier FEATURES mismatch and/or obtain exact current TV values using the declared order. |
| PROOF-002 | `PROOF` | `OPEN` | Generated proof compile and budget | Pine2Python + TradingView | Exact generated-byte compile, plot/token evidence and complete closed-bar dashboard. |
| PROOF-003 | `PROOF` | `OPEN` | SMC strategy port and parity | StrategyLab | Accepted indicator child strategy, its own TV proof, Python trace and criterion-level parity. |
| PROOF-004 | `PROOF` | `OPEN` | Reusable evidence-bundle adapter | StrategyLab + Pine2Python | Demonstrate schema information loss on a real consumer before extending public schema. |
| VIS-001 | `VISUAL` | `OPEN` | Persistent SMC history | StrategyLab + TradingView/user | Direct historical navigation, reload, collision/object-budget and focused geometry review. |
| VIS-002 | `VISUAL` | `OPEN` | Exact product acceptance | TradingView/user | Mandatory visual cases, protected regions, dashboard and explicit verdict for one hash. |
| SERV-001 | `SERVICE` | `LOCAL_FIX_PROVEN` | Service safety/ownership boundary | Pine2Python | Keep service tests and security evidence current; reopen on worker/schema/runtime changes. |
| SERV-002 | `SERVICE` | `OPEN` | Broader Pine/runtime adapter coverage | Pine2Python | Add only a demanded adapter with explicit lifecycle contract and parity fixture. |
| SERV-003 | `SERVICE` | `OPEN` | Hosted/closed-source deployment | StrategyLab + legal owner | License review for AGPL PineTS posture and deployment topology. |
| ECON-001 | `ECONOMICS` | `OPEN` | SMC edge/qualification | StrategyLab | Unoptimized baseline, costs, sample/overlap/censoring report and untouched chronology. |
| ECON-002 | `ECONOMICS` | `OPEN` | Production claims | StrategyLab + operations owner | Venue legality, adverse execution, forward paper reconciliation and monitoring. |

## Detailed issue records

### REC-001 — Deleted phase conversation

- **Scope, owner, status:** Project memory; StrategyLab/user; `OPEN` with a
  non-recoverable limitation.
- **Observed problem and evidence:** The prior main thread is unavailable. The
  integration report, phase prompts, architecture map, SMC contracts and
  artifacts preserve operational decisions but not the complete dialogue or
  unrecorded user choices. This document and `agentic/architecture.md` are the
  recovery surface.
- **Root-cause hypothesis and responsible boundary:** The missing state is a
  conversation-retention problem, not a Pine or service defect. The responsible
  boundary is project memory/documentation: source-cited decisions must be
  written to repository artifacts before a task ends.
- **Required proof:** There is no technical proof that recreates missing text.
  Closure for operational continuity is the existence of this register, a
  project-level architecture map, phase references to both, and explicit
  uncertainty labels. If an original export is found, hash it, preserve it as
  source material, and reconcile differences rather than replacing the map.
- **Explicit non-proof and reopen trigger:** A plausible narrative is not the
  lost conversation. Reopen if the original transcript/export becomes
  available or if a new user instruction contradicts a recovered decision.

### SEM-001 — Structure ownership and directional bias

- **Scope, owner, status:** SmartMoney-4 v6/v6.3 structural detector; StrategyLab
  and expert reviewer; `OPEN`. It blocks indicator acceptance and any mutation
  that changes structure semantics.
- **Observed problem and evidence:** The active detector retains independent 2/2
  levels and selects broken extremes. Existing evidence says an internal
  opposing break can be selected as the macro direction. The `v6_bias` shadow
  guard did not materially change aggregate counts, and restrictive v7/v8
  owner gates removed source-valid setups. These are local/model observations,
  not expert ground truth.
- **Root-cause hypotheses and boundary:** The candidate may lack an explicit
  owner relationship between internal and macro levels, or the expert's
  “owning boundary” may not be the same primitive as the current 2/2 detector.
  The responsible boundary is the structure candidate ledger in the SMC Pine and
  Python evaluator, before checklist scoring and lifecycle policy.
- **Required proof bundle:** Freeze the current source and parent hashes. Add
  expert-labelled positive, negative and near-miss cases containing competing
  internal/macro breaks, direction, source/known/confirmation/ready times and
  the expected owning level. Reconcile unchanged, added, removed, retimed and
  re-anchored cases; preserve all named valid baseline setups; prove long/short
  symmetry and unknown ownership behavior; run the complete local proof and
  exact-byte TradingView focused review after one semantic child change.
- **Cross-strategy gate:** Exercise the same nested-level ownership ambiguity in
  a non-SMC breakout or range strategy that has internal and higher-level
  boundaries. Do not claim transfer from another SMC asset.
- **Non-proof, resolution and next action:** Higher PF, a cleaner narrative,
  extreme-only selection, or a filter that deletes losing setups is not proof.
  Resolve only when a named rule explains the expert cases without a blanket
  veto and the non-SMC consumer passes; next action is to obtain/adjudicate the
  exact cases.

### SEM-002 — Sweep recall and linkage lifecycle

- **Scope, owner, status:** SMC liquidity/sweep detector and its link to BOS
  candidates; StrategyLab and expert reviewer; `OPEN`.
- **Observed problem and evidence:** The current work operationalizes wick,
  reclaim and opposite body break, separates validity from score/linkage and
  preserves fresh-versus-linked context. Expert material still reports missed
  liquidity events. Earlier implementations could consume or suppress a sweep
  when linking it to a candidate.
- **Root-cause hypotheses and boundary:** Misses may be caused by the known-level
  definition, reclaim/invalidation ordering, level ownership, sweep-to-BOS
  linkage, or event-candidate suppression. The responsible boundary is the raw
  sweep ledger and its causal link, before checklist quality or order policy.
- **Required proof bundle:** Select an independent chart window in advance and
  label every candidate wick/reclaim, known level, body-close invalidation,
  confirming BOS, first knowable time and linked candidate. Compare raw
  detector events, linked events, setup events and terminal classifications with
  explicit `DETECTION_MISS`, `CHECKLIST_FAIL` and lifecycle/render suppression
  classes. Include positive, negative, intervening-break and duplicate cases in
  both directions. Re-run exact source/Python evidence and focused TradingView
  review for the repaired child.
- **Cross-strategy gate:** Use a non-SMC breakout/retest strategy with a
  multi-stage “event remains valid until invalidated” relationship. The fixture
  must consume the lifecycle state, not merely run a second sweep detector.
- **Non-proof, resolution and next action:** More sweeps, removed sweep gates,
  a score-dependent timeout, or aggregate setup counts do not establish recall.
  Resolve when the same lifecycle cause is corrected and transfer passes; next
  action is an independently labelled opportunity census.

### SEM-003 — Range endpoint and confirmation timing

- **Scope, owner, status:** Post-BOS endpoint/range ownership; StrategyLab and
  expert reviewer; `LOCAL_FIX_PROVEN` locally, with external adjudication open.
- **Observed problem and evidence:** The SMC line contains a v6.1 endpoint repair
  allowing the first qualifying confirmed 2/2 extreme on or after the BOS and
  requiring two later closed bars. The local golden block checks confirmation
  delay and changed anchors, but the active casebook marks expert verdicts
  pending.
- **Root-cause hypothesis and boundary:** The historical endpoint may be chosen
  from an earlier or later structural event, or a confirmed source time may be
  confused with readiness time. The responsible boundary is the locked-range
  state transition, before Fib/POC/scoring.
- **Required proof bundle:** Preserve the exact BOS-candle, on-BOS endpoint,
  after-BOS endpoint, late-touch and invalid-range fixtures. Record source,
  known, confirmation, ready and action times. Compare parent/child anchors and
  all affected setups by owned level and timestamps, then run prefix/reload and
  exact proof checks. Obtain expert and TradingView focused confirmation on the
  native contexts.
- **Cross-strategy gate:** A non-SMC range-break strategy with delayed endpoint
  confirmation must pass the same “source is not ready” timing and prefix tests.
- **Non-proof, resolution and next action:** A passing local endpoint test or a
  count increase does not validate every expert case. Root resolution requires
  case adjudication and transfer; next action is to resolve the pending casebook.

### SEM-004 — POC/profile precision and interpretation

- **Scope, owner, status:** Optional POC/extended checklist and 1m-derived
  profile; StrategyLab and expert reviewer; `OPEN`.
- **Observed problem and evidence:** The profile uses dynamic 32–72 rows and a
  row-neighborhood tolerance. The contract states that the video's “near POC”
  judgment is not a universal numeric truth, and available data/POC use is
  bounded. The current proof's POC fields are not an independent TradingView
  acceptance of the visual or source interpretation.
- **Root-cause hypothesis and boundary:** Differences may arise from 1m feed
  coverage, row quantization, price units, midpoint convention, or a mismatch
  between a visual near judgment and a gating rule. The responsible boundary is
  profile construction and the declared POC criterion, before setup lifecycle.
- **Required proof bundle:** Freeze tick size, units, 1m dataset hash, rows,
  range, row height and tolerance. Test exact-row, neighboring-row, outside-
  tolerance, missing-1m and truncated-profile cases with both directions. Show
  raw POC, selected row and pass/fail separately; compare local, Python and
  TradingView values on a declared window and retain `n/a` when inputs are
  unavailable.
- **Cross-strategy gate:** Use a non-SMC volume/profile consumer that actually
  gates or grades a decision using the same row/tick calculation and missing
  data behavior.
- **Non-proof, resolution and next action:** A POC input that never gates the
  default setup, a visually close line, or a higher PF is not proof. Resolve
  only after the numeric contract and source-supported interpretation agree;
  next action is a declared native 1m/context fixture.

### SEM-005 — Causal feature ownership

- **Scope, owner, status:** Features such as SMC causal displacement/FVG linkage;
  StrategyLab; `LOCAL_FIX_PROVEN` on the current local SMC contract, transfer
  still open.
- **Observed problem and evidence:** The earlier SMC implementation accepted any
  active same-direction FVG, while the repaired contract links the feature to
  the complete causal displacement leg. `smart_money_4_clean.py` and golden
  reports retain `break_fvg` and causal linkage fields, and local fixtures pass.
- **Root-cause hypothesis and boundary:** The failure was an arbitrary temporal
  proximity/active-state test replacing event provenance. The responsible
  boundary is feature construction and provenance, before score/checklist use.
- **Required proof bundle:** Include a causal-leg positive, nearby-but-unrelated
  gap negative, stale/mitigated gap, concurrent gap and delayed-confirmation
  case. Preserve source/known/ready timestamps, event IDs and field-level trace
  comparison. Run the source-fidelity whitelist and first-divergence process;
  verify that an unrelated visual gap cannot change the strategy-consumed field.
- **Cross-strategy gate:** Add a non-SMC strategy whose signal consumes a
  feature tied to a causal event, such as a breakout retest or volatility event;
  prove that a nearby unrelated feature is rejected for the same provenance
  reason. No shared helper may mention SMC semantics.
- **Non-proof, resolution and next action:** One repaired FVG case or matching
  feature total does not demonstrate reusable causal ownership. Root resolution
  awaits the non-SMC fixture and its own accepted contract.

### SEM-006 — Independent detector recall and opportunity census

- **Scope, owner, status:** Phase 1 coverage claims for any detector; StrategyLab
  plus expert/user labels; `OPEN`.
- **Observed problem and evidence:** SMC event accounting is complete, and local
  counts report dozens of ready setups with both directions. The contracts
  explicitly state that accounting and “at least one long and one short” do not
  prove recall; chart opportunities neither model emits have not been fully
  adjudicated.
- **Root-cause hypothesis and boundary:** The detector's opportunity universe is
  not fully observable from its own output. The responsible boundary is Phase 1
  evidence design, not a later optimizer or filter.
- **Required proof bundle:** Choose windows, symbols, timeframes and labels
  before looking at outcomes. Build an independent continuous chart inventory
  of candidate structures, then classify implementation misses, checklist
  failures, lifecycle suppression, rendering suppression and genuine negatives.
  Report denominators, direction, frequency per calendar period, censoring and
  expert confidence. Reconcile parent/child changes and retain rejected cases.
- **Cross-strategy gate:** Repeat the same independent inventory for a non-SMC
  detector with a known event definition. The proof must show that the process
  can detect misses outside SMC rather than merely reusing SMC labels.
- **Non-proof, resolution and next action:** A broader local census, more visible
  cards, or profitable subset is not recall. Root resolution requires the
  independent denominator and reproducible miss classes; next action is to
  freeze the inventory protocol and label cases.

### SEM-007 — Direction and context asymmetry

- **Scope, owner, status:** Long/short semantics, HTF location and context
  effects; StrategyLab; `OPEN`.
- **Observed problem and evidence:** Local SMC windows show materially different
  long/short outcomes and missing-HTF cohorts. The work correctly refuses blind
  direction inversion and generic trend vetoes, but no expert-adjudicated
  symmetry proof or independent context explanation closes the difference.
- **Root-cause hypothesis and boundary:** The asymmetry may be market/context
  distribution, a direction-specific detector or range rule, feed/session drift,
  or economic outcomes rather than semantic inversion. The responsible boundary
  must be localized before changing a rule.
- **Required proof bundle:** Compare long and short raw events, first failures,
  features, ready/action timing, lifecycle states and data-quality cohorts on
  fixed windows. Use mirrored synthetic fixtures only as invariants, not as
  market truth. Separately report semantic symmetry and economic asymmetry.
- **Cross-strategy gate:** A non-SMC directional strategy must pass the same
  directional-field, lifecycle and context accounting without a direction
  inversion patch.
- **Non-proof, resolution and next action:** Equal counts, forced alternation,
  flipping shorts, or a better PF on one side do not solve the issue. Resolve
  when the causal source is identified or the asymmetry is documented as a
  context property with transfer evidence; next action is the directional
  funnel.

### TIME-001 — Confirmed HTF ownership and repaint behavior

- **Scope, owner, status:** Completed 4h context imported into 15m decisions;
  StrategyLab and TradingView/user; `OPEN`.
- **Observed problem and evidence:** The earlier research record identified
  unoffset `request.security()` as a potential realtime repaint source. Current
  contracts require previous completed 4h context, and current analysis flags
  `request.*` as a local runtime blocker. Static source and local prefix checks
  do not prove TradingView realtime ownership.
- **Root-cause hypothesis and boundary:** Developing HTF values, lookahead
  interpretation, session bucket formation or confirmation timing may leak into
  a 15m decision. The responsible boundary is the timeframe request and its
  confirmed-state adapter, before score or order policy.
- **Required proof bundle:** Freeze exact Pine source, chart/feed/timezones,
  requested timeframe and confirmation pattern. Compare historical and forward
  confirmed values, prefix outputs, reload outputs and a still-forming boundary;
  directly inspect a TradingView chart on 15m and 4h. Include a negative case
  where a developing HTF change must not alter a 15m signal.
- **Cross-strategy gate:** Use a non-SMC dual-timeframe moving-average or
  breakout strategy whose decision consumes the same completed-HTF contract.
  It must pass both local and TradingView-focused timing review.
- **Non-proof, resolution and next action:** `lookahead_off` by itself, a local
  static warning, or matching historical totals is not enough. Root resolution
  needs confirmed realtime/reload evidence and the non-SMC consumer; next action
  is an exact TV focus review after the source is pinned.

### TIME-002 — Warmup, state reset and prefix equivalence

- **Scope, owner, status:** Stateful Pine/PineTS proofs and later Python ports;
  StrategyLab + Pine2Python; `OPEN`.
- **Observed problem and evidence:** The service supports a declared
  `settings.state_start_ms` only when the source resets all state needed by the
  proof. The current SMC revision records a reset boundary, but local runtime is
  unavailable because of `request.*`; history-origin object IDs are expressly
  diagnostic-only when lifecycle state is stable.
- **Root-cause hypothesis and boundary:** A proof may accidentally omit required
  state history, or Python and Pine may warm up different windows. The boundary
  is the source-owned state initialization and proof-window selection, not the
  hash mixer.
- **Required proof bundle:** Compare full supplied history with the declared
  reset run, hash only the declared window, inspect all state variables and
  arrays, and test prefixes, reloads, missing data and the earliest valid event.
  Show that every strategy-consumed field is identical; retain object IDs only
  as diagnostics unless the strategy uses them.
- **Cross-strategy gate:** The existing MA/ATR fixture covers a basic lifecycle;
  add a non-SMC stateful indicator/strategy with a genuine warmup/reset boundary
  and a prefix-sensitive case.
- **Non-proof, resolution and next action:** Matching a truncated window or
  state-insensitive output does not prove reset safety. Resolve when state
  inventory, equivalence and transfer pass; next action is a stateful fixture
  that the local worker actually supports or an explicit TV route.

### TIME-003 — First appearance, action timing and historical persistence

- **Scope, owner, status:** SMC marker/setup first appearance, confirmed-bar
  readiness, reload and replay/realtime behavior; StrategyLab + TradingView/user;
  `OPEN`.
- **Observed problem and evidence:** Contracts separate source, known,
  confirmation, ready and next-bar action times and use frozen timestamps for
  history. Basic TradingView limits and local evidence do not provide Bar Replay
  or universal realtime proof; the active casebook still has pending expert
  review.
- **Root-cause hypothesis and boundary:** A value may be drawn at its source
  wick instead of when it becomes knowable, or a renderer may recompute history
  from current state. The responsible boundaries are state commit and the
  timestamp-owned rendering layer.
- **Required proof bundle:** Directly jump to named positive and negative
  historical cases without pan/zoom, inspect first appearance, readiness and
  next-bar action, reload the chart, and verify stable geometry/collision-free
  objects within the declared budget. Use replay/forward observation whenever
  the contract makes a realtime claim, and hash screenshots.
- **Cross-strategy gate:** A non-SMC persistent event renderer must pass the same
  direct-navigation/reload and confirmation-timing cases.
- **Non-proof, resolution and next action:** Compilation, a static screenshot,
  `bar_index` on a short window or a correct current view does not prove direct
  historical persistence. Resolve with the external sequence; next action is a
  TradingView review package tied to exact timestamps.

### TIME-004 — OHLC lifecycle ambiguity and order concurrency

- **Scope, owner, status:** Indicator lifecycle classifications and future
  strategy order/fill semantics; StrategyLab; `OPEN`.
- **Observed problem and evidence:** The SMC evaluator emits reason-coded
  ambiguous cases and applies price-path invariants. An unfilled entry and stop
  on one bar is deterministic when the bar opens on the valid side of the stop;
  entry/target, stop-gap and already-open stop/target coexistence remain
  ambiguous without lower-timeframe order. The current SMC line has no strategy
  orders and the MA adapter is only `next_bar_open`.
- **Root-cause hypothesis and boundary:** OHLC bars do not encode intrabar path,
  and indicator state can be mistaken for broker-emulator behavior. The
  responsible boundary is lifecycle classification and then the strategy order
  adapter, kept separate.
- **Required proof bundle:** Build price-path fixtures for deterministic stops,
  targets, gaps, entry/stop coexistence, already-open exits, cancellations and
  replacement. Use lower-timeframe data or an explicit `AMB` reason and review
  timestamp where ordering cannot be proven. Compare indicator events and order
  events separately.
- **Cross-strategy gate:** Extend a non-SMC order strategy with the same
  same-bar/next-bar boundary and compare Pine/StrategyLab traces under a declared
  broker model; the current MA fixture alone is not enough.
- **Non-proof, resolution and next action:** A chosen tie-break, gross backtest,
  or fabricated broker event is not proof. Root resolution requires an explicit
  deterministic/ambiguous partition and a separately accepted order model.

### DATA-001 — Native OANDA gold and higher-timeframe identity

- **Scope, owner, status:** OANDA:XAUUSD 15m/4h browser and parity context;
  StrategyLab/data owner; `OPEN`.
- **Observed problem and evidence:** The available 20,000-bar gold data is
  legacy MT5. Its server timezone, sessions and native 4h ownership are
  unverified, with incomplete buckets and gaps. The contracts correctly refuse
  to relabel it as OANDA or FXCM.
- **Root-cause hypothesis and boundary:** Differences may be feed, venue,
  session, timezone, bucket construction or missing data rather than SMC logic.
  The responsible boundary is dataset import/manifests and HTF construction.
- **Required proof bundle:** Obtain or import the exact native OANDA chart feed
  used for review, record symbol/venue/session/timezone/timeframe, row count,
  file hash, gaps, duplicates, units and native completed 4h ownership. Match
  the exact TradingView proof window and dataset fingerprints before comparing
  feature or execution fields.
- **Cross-strategy gate:** A non-SMC strategy using the same OANDA 15m/4h data
  contract must pass identity and missing-data checks; another asset or the
  legacy MT5 feed is not transfer.
- **Non-proof, resolution and next action:** UTC labels, symbol names, or a
  passing legacy run do not prove native identity. Resolve only after the native
  manifest and dashboard match; next action is data acquisition/verification.

### DATA-002 — Multi-context 1m profile, units and missing data

- **Scope, owner, status:** 1m-derived POC/profile, asset units, session rules and
  missing-data behavior; StrategyLab/data owner; `OPEN`.
- **Observed problem and evidence:** BTC has declared 15m and 1m datasets;
  gold's native 1m/HTF context is not verified. Contracts record feed-specific
  units and refuse fabricated values, but no cross-context proof closes the
  contract.
- **Root-cause hypothesis and boundary:** A profile or risk value can be
  numerically valid for one unit/feed and wrong for another, or missing rows can
  change the profile without a visible failure. The responsible boundary is
  data normalization and explicit context ownership.
- **Required proof bundle:** For each declared context, hash 15m/1m inputs,
  record units/tick size/session/timezone, quantify gaps and incomplete buckets,
  test `n/a`/blocked behavior, and compare a complete and deliberately damaged
  feed. POC, risk and setup traces must identify the input context.
- **Cross-strategy gate:** A non-SMC strategy that consumes a lower-timeframe
  aggregation or unit-sensitive risk calculation must pass the same matrix.
- **Non-proof, resolution and next action:** Resampling, UTC relabeling, or
  matching only BTC does not generalize. Resolve per declared context; next
  action is a verified data manifest rather than detector tuning.

### DATA-003 — Untouched chronology and economic evidence context

- **Scope, owner, status:** Phase 2.5 through production economic qualification;
  StrategyLab; `OPEN`.
- **Observed problem and evidence:** Current SMC reports reuse research windows,
  overlap setups, censor open/missed/ambiguous outcomes and use provisional
  costs; no untouched holdout or forward reconciliation establishes deployable
  economics.
- **Root-cause hypothesis and boundary:** Weak economics may be genuine, a
  context mismatch, data/venue issue, execution assumption, or selection bias.
  The responsible boundary is evaluation design, after semantic fidelity has
  passed.
- **Required proof bundle:** Freeze chronological train/validation/holdout
  boundaries before outcome inspection, benchmark and costs, sample and
  censoring policy, overlapping exposure, regime coverage and adverse scenarios.
  Preserve the unoptimized baseline and report all opportunity/lifecycle counts
  separately from PF/WR.
- **Cross-strategy gate:** Run the same evaluation contract for a non-SMC parent
  with its own strategy-specific benchmark, so the process—not the SMC numbers—
  is what transfers.
- **Non-proof, resolution and next action:** A better in-sample PF, a larger
  sample without a holdout, or optimizing away losing setups is not proof.
  Resolve only with predeclared chronological evidence and later forward gates.

### PROOF-001 — FEATURES divergence and first-cause localization

- **Scope, owner, status:** Pine2Python/TradingView feature proof for SMC v6/v6.3;
  StrategyLab, with Pine2Python ownership determined by localization; `OPEN`.
- **Observed problem and evidence:** Earlier exact proof evidence matched DATA
  and SIGNALS while FEATURES diverged. The current v6.3 expected proof
  `pev_a6fb9e4e8dd1a838d665` retains `TRADINGVIEW_REVIEW_REQUIRED` and cannot
  run PineTS locally because `request.*` is blocked, so it does not independently
  settle the earlier divergence.
- **Root-cause hypotheses and boundary:** The first cause may be an expression
  or state mismatch, feed/HTF identity, instrumentation transform, or a
  diagnostic-only field incorrectly treated as strict. The responsible boundary
  must be identified before excluding a field.
- **Required proof bundle:** Freeze exact source/proof/settings/window and
  matching dataset. Run feature groups, time partitions, then exact-bar
  primitive probes. Include all 26 declared SMC feature fields, classify any
  diagnostic-only exclusion with a strict replacement, and rerun the complete
  proof after the first causal repair. Obtain exact current TradingView values
  if local capability remains blocked.
- **Cross-strategy gate:** A non-SMC strategy with declared feature streams must
  pass the same group/partition/probe localization and retain all strategy-
  consumed fields. A basic MA position trace is not a rich FEATURES transfer.
- **Non-proof, resolution and next action:** Matching DATA/SIGNALS, dropping a
  field, or relying on an expected dashboard artifact is not closure. Resolve
  when the first cause is repaired or an evidence-backed diagnostic exclusion
  has a strict substitute and transfer passes; next action is the localized
  current proof/TV comparison.

### PROOF-002 — Exact generated proof compile and budget

- **Scope, owner, status:** Generated TradingView dashboard and source budgets;
  Pine2Python + TradingView; `OPEN`.
- **Observed problem and evidence:** The service preflights the 64-plot limit,
  counts `alertcondition`, shares expressions across fingerprint lanes, packs
  table metadata and permits proof-only compaction only for explicitly marked
  pure rendering blocks. Static preflight is not browser compilation, and
  `request.*`/drawing/runtime behavior can remain external.
- **Root-cause hypothesis and boundary:** Generated source can exceed compiled
  token pressure or behave differently in TradingView even when source length
  and local parser checks look safe. The responsible boundary is proof-source
  generation and exact-byte browser compilation.
- **Required proof bundle:** Read back the exact generated bytes, hash them,
  record schema/instrumentation version, plot count including series-valued
  calls, compacted blocks, token/compile result, declared closed-bar window,
  expected/observed dashboard values and screenshot SHA-256. Keep runtime-only
  arrays/hidden streams distinct from table-only proofs.
- **Cross-strategy gate:** Generate and compile a non-SMC proof source with
  feature/signal/state streams, not only the sample adapter, and demonstrate
  that the same budget/accounting rules hold.
- **Non-proof, resolution and next action:** Source byte length, Python proof
  output, or a screenshot with no exact-byte link does not prove TradingView
  compile. Resolve with the exact browser artifact and transfer fixture.

### PROOF-003 — SMC strategy child and criterion-level parity

- **Scope, owner, status:** StrategyLab's next SMC strategy after indicator
  acceptance; StrategyLab; `OPEN`.
- **Observed problem and evidence:** The active SmartMoney-4 source declares
  `indicator()` and has no orders. The contracts explicitly prohibit a strategy
  port, optimization or mutation until the indicator is accepted and the child
  strategy independently passes TradingView.
- **Root-cause hypothesis and boundary:** The absent strategy is an incomplete
  lineage stage, not a parity bug. The responsible boundary is Phase 1.5
  strategy construction followed by Phase 2 trace mapping.
- **Required proof bundle:** Inherit the accepted indicator calculations by exact
  child lineage, add explicit signal/rejection/order-intent/sizing/fill/stop/
  target/position contracts, obtain the separate exact-byte TV verdict, then
  compare Python feature, signal, state, rejection, order, position and trade
  traces on aligned data. Freeze the unoptimized Python parent before economics.
- **Cross-strategy gate:** Use the existing MA/ATR fixture for basic plumbing and
  a richer non-SMC strategy for the same state/order/rejection field families.
  Do not claim SMC strategy parity from the indicator proof.
- **Non-proof, resolution and next action:** A valid indicator, local evaluator,
  or matching headline equity curve is not a strategy port. Resolve only after
  the child earns its own Phase 1.5 and Phase 2 gates.

### PROOF-004 — Versioned evidence-bundle adapter and schema scope

- **Scope, owner, status:** Proposed generic adapter between StrategyLab evidence
  and Pine2Python; StrategyLab + Pine2Python; `OPEN`.
- **Observed problem and evidence:** The architecture proposes a versioned bundle
  with source/data/criteria/event/checklist/lifecycle/TradingView fields, while
  current service schemas already carry many analysis, proof, trace and parity
  fields. No concrete information-loss boundary has yet justified adding a
  public adapter.
- **Root-cause hypothesis and boundary:** A real cross-system consumer may lose
  lineage or event ownership when StrategyLab flattens service evidence, or the
  proposal may duplicate existing artifacts. The responsible boundary is the
  StrategyLab adapter/schema, not a strategy detector.
- **Required proof bundle:** Select a real SMC and non-SMC consumer, map current
  request/response/artifact fields end to end, identify a field that is actually
  lost or ambiguous, version the smallest schema extension, preserve unknown/
  unsupported fields, and run compatibility tests plus deterministic artifact
  identity checks.
- **Cross-strategy gate:** Both consumers must round-trip the same generic fields
  without strategy-name special cases, while strategy-specific fields remain
  extensions rather than invented universal values.
- **Non-proof, resolution and next action:** A desired field list or architecture
  suggestion is not a demonstrated gap. Resolve only after an observed loss and
  schema/contract regression; next action is current schema inspection.

### VIS-001 — Persistent history, direct navigation and object budget

- **Scope, owner, status:** SMC historical setup cards, labels, boxes and lines;
  StrategyLab + TradingView/user; `OPEN`.
- **Observed problem and evidence:** Reproduced old-level failures involved
  `time[]` lookup and old bar-index drawing limits. The local child now uses
  frozen timestamps, `xloc.bar_time` and a bounded FIFO/object budget, and v6.3
  renders eligible pending/missed/open records rather than only fills. External
  direct navigation/reload/geometry acceptance remains open.
- **Root-cause hypothesis and boundary:** A renderer may depend on viewport or
  current state, exceed the 5,000-bar drawing boundary, collide, or suppress a
  detection when it cannot draw. The responsible boundary is the rendering
  adapter; ledger detection must remain independent.
- **Required proof bundle:** Use known positive/negative historical timestamps,
  jump directly without pan/zoom, reload, change timeframe when in scope, check
  collision-free geometry, finite right edges, archive/object caps and stable
  labels. Compare ledger event counts before and after render limits; save exact
  source and screenshot hashes.
- **Cross-strategy gate:** A non-SMC persistent historical renderer must pass the
  same timestamp/direct-navigation/reload/object-budget checks.
- **Non-proof, resolution and next action:** A current-window screenshot,
  compilation, or lowering the history cap until errors disappear is not proof.
  Resolve only when events survive rendering failure and the browser cases pass.

### VIS-002 — Exact product visual and user acceptance

- **Scope, owner, status:** SMC compact checklist, risk/position geometry,
  protected 4h review, dashboard and exact source verdict; TradingView/user
  with StrategyLab preparation; `OPEN`.
- **Observed problem and evidence:** Design contracts preserve a dark compact
  visual language and mandatory video frames. Current source/proof artifacts are
  statically reviewed or expected; the active v6.3 source remains
  `TRADINGVIEW_REVIEW_REQUIRED`, and expert/user acceptance is pending.
- **Root-cause hypothesis and boundary:** A technically matching stream can
  still render the wrong historical product, hide a protected region, or be
  attached to the wrong source/settings. The boundary is the exact-byte
  TradingView review package and user verdict.
- **Required proof bundle:** Freeze readable and instrumented source hashes,
  settings, chart context, review timeframes, protected-region hashes and
  strategy-specific positive/negative screenshots. Compare visible dashboard,
  geometry, density, labels, 4h preservation and reload behavior. Store every
  screenshot SHA-256 and the explicit verdict against the same candidate.
- **Cross-strategy gate:** A non-SMC source-derived indicator must complete its
  own protected-source and focused visual review; this proves the review method,
  not SMC visual semantics.
- **Non-proof, resolution and next action:** Local parity, a readable PNG, or a
  prior revision's user verdict is not current acceptance. Resolve after the
  user/expert records a verdict for the exact v6.3 source or a later child.

### SERV-001 — Fixed service safety and ownership boundary

- **Scope, owner, status:** Pine2Python worker, request validation, data boundary,
  schemas and role separation; Pine2Python; `LOCAL_FIX_PROVEN` for the current
  implementation, subject to regression freshness.
- **Observed problem and evidence:** The nested service instruction has been
  consolidated into the single repository contract and subsequently relocated
  to `agentic/architecture.md` on 2026-10-08. The implementation uses Pydantic bounds,
  caller candles, a fixed Node worker, argument-array invocation with
  `shell=False`, timeout/output bounds and per-job directories. Service reports
  explicit unsupported semantics and do not optimize, mutate, promote or create
  lineage.
- **Root-cause hypothesis and boundary:** The original risk was instruction
  fragmentation and the possibility of future callers treating a bounded local
  runtime as arbitrary code execution or TradingView truth. The responsible
  boundary is the service API/worker adapter and architecture constraint contract.
- **Required proof bundle:** Keep the nine nested invariants represented in the
  architecture constraints, run service/schema/worker tests, inspect the worker command and
  path/data restrictions, verify bounded failure behavior, and confirm artifact
  status labels. Reopen on worker, dependency, public-schema or container
  changes.
- **Cross-strategy gate:** Exercise at least one source-derived and one
  generated/non-SMC request through the same service boundary; unsupported or
  uncertain fields must remain explicit in both.
- **Non-proof, resolution and next action:** The service being local, a passing
  sample request, or a report paragraph is not a perpetual security audit.
  Current next action is to keep the existing regression green and record fresh
  results when the environment permits.

### SERV-002 — Broader adapter and runtime capability coverage

- **Scope, owner, status:** `request.*`, `varip`, imports, realtime semantics,
  dynamic risk, advanced exits, `mt5_bar_proxy` and arbitrary translation;
  Pine2Python; `OPEN`.
- **Observed problem and evidence:** The service explicitly blocks or rejects
  these capabilities; the first registered MA/ATR adapter implements only the
  declared `next_bar_open` subset. The SMC v6.3 proof is locally unavailable
  under the recorded `request.*` blocker.
- **Root-cause hypothesis and boundary:** Upstream PineTS/Pynescript support is
  experimental and cannot safely be assumed. The responsible boundary is
  capability analysis and adapter registration, not silent fallback behavior.
- **Required proof bundle:** Add a capability only when a user strategy needs it:
  version the support matrix, define security/data/runtime limits, implement the
  smallest adapter, preserve unknown/blocked semantics, and add a deterministic
  fixture plus exact parity/TradingView route. Keep rejected capabilities
  visibly rejected.
- **Cross-strategy gate:** The new capability must be consumed by a materially
  different non-SMC strategy and pass the same fixture/TV boundary; a second
  SMC source is not enough.
- **Non-proof, resolution and next action:** Upgrading a dependency, parsing a
  construct, or approximating its output is not support. Resolve only with a
  versioned contract and consumer evidence; do not implement speculative scope.

### SERV-003 — License and hosted deployment posture

- **Scope, owner, status:** PineTS AGPL-3.0-only posture and any closed-source
  or hosted release; StrategyLab/legal owner; `OPEN`.
- **Observed problem and evidence:** Service implementation reports lock
  Pynescript 0.3.0, PineTS 0.9.29 and associated licenses, and states that a
  closed-source or hosted release needs license review or a PineTS commercial
  agreement. No such legal decision is recorded in the repository.
- **Root-cause hypothesis and boundary:** The technical topology can be healthy
  while distribution rights remain unresolved. The boundary is release/legal
  governance, not a runtime test.
- **Required proof bundle:** Freeze dependency lockfiles, deployment mode,
  service boundary and intended distribution; obtain the applicable legal
  decision/license agreement and record the allowed topology. Recheck on
  dependency or deployment change.
- **Cross-strategy gate:** Not a strategy-semantic transfer claim; the same
  release posture must cover every consumer.
- **Non-proof, resolution and next action:** A successful Docker build or local
  test is not a license decision. Resolve before a hosted/closed-source release
  is claimed; next action is a legal/ownership review when that release is in
  scope.

### ECON-001 — SMC economics and qualification

- **Scope, owner, status:** SMC coverage candidate's PF/WR, costs, sample,
  overlap, censoring and benchmark; StrategyLab; `OPEN`.
- **Observed problem and evidence:** Current viability reports show broad
  coverage but PF/WR below deployable confidence on reused windows; provisional
  gold data, open/missed/ambiguous cases and assumed costs limit interpretation.
  The contract correctly treats low PF as diagnostic and not a Phase 1 filter.
- **Root-cause hypothesis and boundary:** The weak result may reflect a weak
  trading idea, feed/context mismatch, lifecycle assumptions, cost/execution
  model or insufficient chronology. The responsible boundary is Phase 2.5 and
  later economic evaluation after fidelity, not detector filtering.
- **Required proof bundle:** Freeze an accepted Pine and Python parent first;
  run the unoptimized baseline, declared benchmark/cost/position model,
  chronological untouched windows, sample/censoring/overlap policy, direction
  and regime cohorts, and robustness/adverse-cost scenarios. Preserve all raw
  opportunity outcomes even when the economic result is poor.
- **Cross-strategy gate:** Apply the process to a non-SMC accepted parent with a
  different economic engine and its own benchmark. Transfer means valid
  qualification mechanics, not equal returns.
- **Non-proof, resolution and next action:** A parameter optimum, setup filter,
  or removal of losing events is not root resolution. The current next action is
  to finish indicator acceptance before any strategy qualification claim.

### ECON-002 — Execution feasibility, forward reconciliation and production

- **Scope, owner, status:** Strategy order legality, adverse execution, forward
  paper and operations; StrategyLab/operations owner; `OPEN`.
- **Observed problem and evidence:** SmartMoney-4 is still an indicator and the
  MA/ATR service fixture is a bounded sample. No SMC strategy has completed the
  accepted Pine child, Python parity, venue legality, adverse execution and
  forward reconciliation gates.
- **Root-cause hypothesis and boundary:** Backtest semantics may not map to legal
  venue orders, fills, risk limits, monitoring or forward state. The responsible
  boundary is after Phase 2.5, not Pine2Python's proof dashboard.
- **Required proof bundle:** Freeze final candidate/data/parameters/execution
  model; audit order types, sizing, fees, slippage, exposure, venue constraints,
  cancellation and position state; run adverse scenarios; reconcile forward
  decisions, submitted orders, venue responses, fills, positions, risk controls
  and monitoring over strategy-specific calendar/event/regime evidence.
- **Cross-strategy gate:** A non-SMC production-candidate lineage must complete
  the same operational checklist with its own venue and failure scenarios.
- **Non-proof, resolution and next action:** Local parity, profitable backtests,
  a Docker health check or a successful commit cannot close production. Resolve
  only after forward/operational evidence; no production claim is currently
  authorized.

## Maintenance and closure procedure

When working an issue:

1. Copy its current identity and status into the active phase artifact.
2. Freeze the source, data, settings and proof contract before changing code.
3. Reproduce the named failure and distinguish data, instrumentation, semantics,
   lifecycle, rendering and economic causes.
4. Make one reviewable semantic change at the responsible boundary. Preserve the
   parent and keep rejected candidates.
5. Run the applicable local and external proof bundle; report missing evidence
   explicitly.
6. Update this issue's status, evidence locators, scope matrix, owner and
   reopening trigger. A phase verdict must reference the issue status rather
   than overwrite it.

An issue's closure becomes invalid when source bytes, protected regions,
criteria, settings, dataset/feed, timeframe/session, runtime/instrumentation,
execution model or declared scope changes in a way that can affect the proof.
Create a new child/issue rather than editing history in place. `SUPERSEDED`
retains the old evidence and names the replacement.
