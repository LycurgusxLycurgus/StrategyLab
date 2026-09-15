# SmartMoney-4 v6.3 coverage candidate contract

Status: v8 is USER_REJECTED. The user explicitly selected v6 on 2026-09-02.
The v6.1 parent repaired the BOS/endpoint boundary and two browser-proven
drawing-history failures. The v6.2 child preserves that baseline and repairs
premature sweep-context consumption. The v6.3 child keeps those semantics,
defaults the transcript's coverage-oriented 71% Fib entry (75% remains
selectable), and renders every eligible historical setup rather than only
filled setups. It is NOT an accepted indicator,
accepted Python strategy, or profitable trading system. Evidence gates below
remain separate; more setups alone cannot satisfy them. User clarification on
2026-09-02: Phase 1 prioritizes broad source-valid detection, not profit-based
filtering. Low PF is a reported diagnostic, not a veto on a faithful baseline.

## Authority and lineage

Product authority: the timestamped transcript and mandatory frames under
`pre-strategies/smart-money-4/The ONLY 15 Minute Trading Strategy You Need in 2026`.
ASM course material supplies concept examples; open-source code supplies
mechanism comparisons, not a replacement trading specification.

Workbench: `pwb_f89ea6f3774a`.
Immutable recovery parent: `pvr_35b4dee03de37a299c7e` (v6),
SHA-256 `900ce8a712bbadb98a790532614af71087fd45f2e28b4c9d120fe228b9037820`.
v7 `pvr_dfe72cd3eeaccde22e6e` and rejected v8
`pvr_5b403b82f40e83d6179d` remain archived for comparison.
Current source: `pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine`.

## v6.3 bounded delta

- Pine title and Python registration identify the child as v6.3 Coverage.
- The default Fib setting is 71%; changing to 75% remains an explicit user
  choice and does not alter raw detection.
- Historical setup cards are drawn for all eligible ledger records within the
  existing bounded cap, including pending, missed and open records. Unfinished
  cards use `ready_time + 4 * 15m` as a finite right edge; completed cards may
  extend through their frozen exit time.
- No checklist, HTF, POC, sweep, BOS, range, lifecycle or trader-mode visual
  semantics are changed by this child.

## Frozen criteria

- Hard prerequisites: confirmed 15m body-close BOS, causal positive range,
  confirmed endpoint, no pre-readiness entry touch; actionable next bar.
- Structure: v6 independent retained 2/2 levels (96 bounded levels, 64 sweep
  candidates), not v8's most-extreme/protected-owner gate.
- Endpoint: the first qualifying confirmed 2/2 extreme may originate ON or
  after the BOS candle. Two later closed bars still confirm it. Source time is
  not readiness time. An earlier endpoint cannot be used.
- Sweep: strict wick through an already known level, close back inside, followed
  by an opposite body-close BOS; an intervening body break invalidates it.
  Fresh sweeps retain v6 selection priority. Linking one to a candidate records
  its BOS time rather than invalidating it. If no fresh causal sweep fits a later
  BOS, select the most recently linked still-valid manipulation (v6 extreme/time
  tie-break). A new wick may create fresh evidence at the same structural level.
  Body-close invalidation and causal ordering remain; score never owns validity.
  Freeze candidate metadata at linkage; do not mutate past anchors on refresh.
- Context: previous completed 4h 2/2 structure, unchanged from v6.
- Default Video Standard: HTF alignment, BOS, linked sweep, causal imbalance;
  3 of 4 = 75. Video Perfect requires all four. The v6.3 default Fib setting
  is 71% for coverage; the 75% variant remains available.
- Optional POC Extended: adds proximity, 4 of 5 = 80, Perfect = 100.
  POC tolerance remains the POC row plus two neighboring rows per side.
- Imbalance: still-open causal three-candle gap overlapping selected 71% or 75%
  Fib entry. Profile remains 1m-derived, 32–72 rows with existing ATR sizing.
- Stop/target remain range endpoints. USD risk budget and explicit base-unit /
  lots conversion are unchanged. Detection remains independent of concurrency.

## Protected presentation and lifecycle

Preserve v6 colors, labels, dark tables, checklist, risk calculator, profile,
history cap and all layout choices. One required rendering repair is allowed:
replace dynamic time[] lookups and current-renderer bar-index coordinates with
timestamp coordinates. A bounded 100,000-timestamp ring supplies historical
metadata; future display projection uses the existing 15m bar duration. The
ring does not feed prices, pivots, scores, readiness or lifecycle decisions.
Beyond its retention horizon metadata is unavailable rather than invented.

This fixes two reproduced OANDA:XAUUSD failures at bar 5417: RE10007 from an
old level's time[] lookup and RE10026 from line.new using old bar index 137.
Do not fix these by deleting the old structural level or suppressing its setup.
Historical setup cards already use frozen timestamps; their geometry is unchanged.

Pending, filled, TP, SL, missed/invalid and reason-coded ambiguous states are
unchanged. OHLC ordering is inferred only where price-path invariants prove it.
Rendering capacity is not detection count; missing drawings and missing events
must be diagnosed separately. All 9 trader/reviewer inputs remain unchanged.

## Recovery validation

Run the same complete block after final code changes:

1. `smart_money_4_clean.py --bars 5000 --register`: production evaluator,
   mirrored synthetic BOS-endpoint fixtures, parse/static/plot preflight, exact
   immutable source and declared-field proof.
2. `smart_money_4_golden.py --write`: exact source-diff whitelist, candidate
   accounting, same raw structure events, mirrored prices, prefix stability,
   endpoint confirmation delay, added/retimed/removed setup reconciliation,
   decision-only casebook and identical-window proof recomputation.
3. `smart_money_4_viability.py --write`: v6 / candidate / v7 / rejected v8
   counts, directions, resolved outcomes, gross and assumed-cost PF/win rate.
4. TradingView exact-byte compile, runtime completion, BTC signature dashboard,
   focused long/short boundary cases and OANDA gold runtime/history review.
   Save screenshot hashes; user/expert acceptance must identify exact source.

A changed baseline setup is not automatically a regression or a correction.
Earlier valid locking may change levels, score, sweep availability and late-entry
classification. Record every change and adjudicate annotated positives before
promotion. Code consistency and event accounting do not establish detection recall.

## Data and economic limitations

BTC: `ds_207c4624f554` last 5,000 bars (June 27–August 18, 2026),
1m `ds_1e4ab545aa12`; older BTC `ds_42d92b3cda9f` last 20,000.
Gold `ds_77827283d58c` last 20,000 is legacy MT5, NOT OANDA or FXCM.
Its server timezone and native 4h sessions are unverified (219 gaps, 225
incomplete fixed-UTC buckets). Gold metrics are provisional diagnostics only.
Native HTF interval input is supported and tested but no verified gold native
HTF dataset is available. Do not relabel a feed to manufacture parity.

Local recovery census: recent BTC 75 -> 89; older BTC 250 -> 302; gold 255 -> 283.
Recent BTC gross PF worsens 1.143 -> 0.857; older BTC 0.568 -> 0.632; provisional
gold 0.587 -> 0.663. This improves candidate coverage but does not establish a
trading edge. PF/win rate exclude open, missed and ambiguous cases and include
sample counts separately. Assumed costs, overlapping setups, reused research
windows and missing ETH/FX/index validation prevent portfolio/holdout claims.
Do not optimize away this negative evidence. Indicator acceptance, complete
strategy acceptance and Python parity are still required before freezing the
unoptimized strategy parent; low PF alone does not prohibit that parent.

## Tentative Phase 1 do/don't constitution (pilot, not promoted)

Purpose: produce one source-faithful, inspectable, independently accepted
indicator/strategy contract for creation, translation or modification. Inputs:
user intent, source/transcript, demonstrations, current lineage and exact data.
Output: minimal implementation, case-level evidence, explicit limitations and
an exact-hash verdict. Phase 1 seeks high coverage of source-valid opportunities
under the selected checklist, not the most profitable historical subset. Keep
raw detection separate from checklist filtering and execution policy. Phase 3/4
may later adapt parameters or filters to a specified asset/timeframe with proper
out-of-sample testing; success or profitable deployability is not guaranteed.
Apply in existing whitebox `01_translation.md` /
`01-5_baseline_transformation.md` only after this pilot's unresolved gates close.

### Demonstrated useful controls — DO

- Freeze the user-selected baseline and annotated positive/negative examples.
  Preserve calculations and visuals outside the demonstrated defect.
- Reconcile active criteria, source/revision identity and test contract before
  implementing a child. A stale generated checklist must not silently restore
  a rejected mechanism. Keep archived evidence distinct from active authority.
- Create one source-cited macro checklist: hard, conditional, quality, context
  and alternative rules. Operationalize ambiguous terms before coding.
- Ask for chart demonstrations when translating; create falsifiable examples
  for greenfield strategies. Give source/known/ready times and exact feed.
- Start from one reproduced miss. Repair the first causal discrepancy with a
  small child; include symmetric long/short and neighboring negative cases.
  This iteration recovered the BOS-candle endpoint without changing scoring.
- Compare baseline/child by owned level and source/known times, not direction
  and timestamp alone. Report unchanged, added, retimed and removed cases.
- Separate emitted-event funnels from independent recall. Inspect continuous
  chart windows and count opportunities neither detector emits.
- Use code for broad census, deterministic fixtures, symmetry, prefix/reload
  and source-diff checks; browser for compiler/runtime, signatures and selected
  human-readable chart cases. Exact-byte readback must precede UI acceptance.
- Test an old retained level on long chart history. Persist timestamps rather
  than indexing time[] thousands of bars back. Rendering failure must not
  remove detection. Run after navigation and reload, not only compilation.
- Track instrument/feed/session provenance, warmup and data hash. Match data
  before interpreting feature signatures. Mark unavailable native HTF honestly.
- Report coverage, false positives, PF, costs, win rate and sample size
  separately. Preserve negative findings and model-generated/expert labels.
  PF/win rate diagnose economics; they do not choose Phase 1 detector filters.
- Build a reusable mechanism with unchanged baseline rules across declared
  comparable assets. Document per-feed units, sessions, native HTF, volume and
  missing-data behavior. Record validated/untested scope rather than promising
  universal validity across all assets or timeframes. Data normalization is not
  permission for asset-specific performance tuning in Phase 1.
- Change one semantic hypothesis at a time; rerun the same full acceptance
  block. Keep canonical artifacts current instead of spawning duplicate plans.

### Demonstrated failures — DON'T

- Do not replace a permissive detector with a restrictive ownership theory to
  make the narrative sound cleaner. v7/v8 lost setups before the checklist.
- Do not treat a reference's swing-only subset as its whole algorithm when it
  also consumes internal structure. Verify the full consumer path and license.
- Do not accept because both runtimes agree, all events have terminal codes,
  one long/short exists, or a tiny retained sample has higher PF.
- Do not equate SUPERSEDED/ALREADY_OWNED with a genuinely invalid opportunity.
  Those explain code behavior, not the video's rules.
- Do not infer that more detections are better trades. v6.1 expands the census
  while recent BTC PF falls; neither restrictive nor permissive counts prove edge.
  Favor recovering independently justified setups, but never inflate counts with
  duplicate, stale, future-informed or below-threshold entries. Removing a false
  positive needs a contract/correctness reason, not its subsequent stop loss.
- Do not relax scoring or select parameters from winning examples to hide
  missed detection. Do not discard good baseline cases without adjudication.
- Do not confuse archive limits, deferred drawing errors, feed differences or
  missing 1m data with structural misses. Do not claim browser success at save.
- Do not trust Monaco fill alone: explicitly select all, replace, verify source
  identity and line count, compile and wait for the chart's runtime completion.
- Do not call two matching implementations independent strategy validation.
  Python supplied traces are not PineTS execution; unsupported requests remain
  unsupported. Static charts are not realtime/replay evidence.
- Do not promote a Phase 1 constitution as proven while expert recall cases or
  source-hash acceptance remain unresolved. Keep indicator acceptance separate
  from strategy acceptance and Python parity; no Phase 3/4 without permission.

### Still unproven

Expert-adjudicated recall/false-positive performance, changed baseline case
validity, complete gold feed/HTF parity, live/replay first appearance and final
source-hash acceptance remain unresolved fidelity/evidence questions. Multi-asset
profitability is a separate unproven economic question, not a Phase 1 acceptance
gate. When fidelity passes, report that result independently of poor historical
PF; do not claim trading readiness or invent another detector restriction.

## Current evidence — v6.3 local/static validation recorded, TradingView acceptance pending

v6.2 separates market-evidence validity from candidate linkage and score filtering.
Fresh evidence keeps priority; previously linked evidence is a most-recent-context
fallback. The diagnostic version that ranked every surviving sweep solely by
extreme was rejected before registration: it displaced recent anchors with old
extremes and failed the known gold case. No PF-based choice was made.

The refined child restores all four known suppression cases in local diagnostics;
all previous v6.1 setups remain eligible, with six re-anchored across the three
windows. These are algorithm observations, not expert ground truth. Source
fidelity preserves the complete downstream range/scoring/lifecycle/rendering
section. The detailed checks are in `agentic/analysis.md` and the golden report.
No separate LEG_ALREADY_OWNED detector change has been demonstrated or applied.

The v6.2 local regression, golden-case and viability block passed previously.
The v6.3 child has a deterministic Python smoke census, registration metadata,
source revision `pvr_362b3c72c6d2e797c46a`, source SHA-256
`5ef00859797f0dc960d3762b4d217fd76e92c70d7b0cb4d70a7f556909cf0718`, and
expected proof `pev_a6fb9e4e8dd1a838d665`. Its immutable analysis records
`request.*` as a local-runtime blocker, so the current proof remains
`TRADINGVIEW_REVIEW_REQUIRED`; this is not a user verdict. The prior exact
v6.2 bytes compiled and ran on BTC plus six additional TradingView feeds, with
runtime history screenshots saved. Earlier BTC instrumented evidence matched
DATA and SIGNALS but left FEATURES divergence unresolved; the current expected
proof artifact cannot close that issue without matching runtime/TradingView
observations. Astra-medium identified and the root fixed stale diagnostic
feature partitions in `smart_money_4_clean.py`; those partitions now cover all
26 fields and map POC correctly. This is proof tooling only and does not change
the Pine contract. Detailed remaining obligations live in
`STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`, not only in the temporary task board.
