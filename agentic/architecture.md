# StrategyLab evidence architecture and handoff map

Status: durable project map, 2026-09-15. This document is the compact recovery
entry point for the whole repository. The detailed, future-model-facing issue
register and proof obligations live in
`STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`; this map records its ownership, flow,
maintained files, durable lessons, and current limits. Neither document
reconstructs the deleted conversation verbatim or claims that SmartMoney-4 is
profitable or TradingView-accepted.

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

The operational flow is:

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

### Maintained file tree

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Single repository instruction and Pine2Python safety/ownership rules. |
| `PINE2PYTHON_INTEGRATION_REPORT.md` | Historical integration architecture and validation record. |
| `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` | Current recoverable context, issue ledger, root-proof bundles, non-proof and handoff. |
| `agents/translation and generation/agents/codex_phase_operator.md` | Shared phase contract, Phase 0–Production routing and evidence rules. |
| `agents/translation and generation/whitebox/*.md` | Standalone prompts that apply the shared contract to each phase. |
| `agents/docs/universal_mutation_constitution.md` | Additional guardrails for Phases 3–4.3. |
| `services/pine2python/` | Typed local/HTTP analysis, bounded runtime, proofs, traces and parity boundary. |
| `app/`, `strategies/` | StrategyLab API, engines, storage, UI and parent definitions. |
| `pre-strategies/` | Inspectable source and immutable source-derived Pine candidates. |
| `artifacts/strategy-development/` | Strategy lineage, criteria, proof, review and phase evidence. |

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

The service implements the correct broad boundary (analysis, capabilities,
supported local execution, proof generation, standard traces and parity). The
root `AGENTS.md` now carries its safety rules: fixed worker invocation with
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
