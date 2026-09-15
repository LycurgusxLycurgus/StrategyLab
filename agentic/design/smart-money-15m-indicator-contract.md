# Smart Money dual-timeframe indicator contract

Status: transcript entry contract implemented, visually corroborated, and
signature-matched; explicit user/expert acceptance remains pending.

## Authority and lineage

The authoritative product baseline is the Pine v5 indicator embedded at lines
7–1747 of `pre-strategies/smart-money-3.txt`. Its byte-exact extracted source is
`pre-strategies/smart-money-indicator-baseline.pine`.

The current immutable candidate is Workbench revision
`pvr_28090860d3444b575353`, source SHA-256
`449f4c298751e4cb5e4edff8d85de8bd2a20fb208c6ae92e5d36ba82e580cecf`.
Its immediate semantic parent is revision `pvr_e191fd164eac85786003`,
source SHA-256
`4547b865fa2e89f24a4fca8e320f107cbbc2a21263881444180bfd9a27ca1dd7`.
The candidate preserves the accepted-looking 4-hour calculations, repaired
15-minute alternating pivots, temporal ledger, event-level checklist funnel,
conditional sweep ownership and causal displacement-leg FVG provenance, then
adds independent concurrent setup recording. CHoCH reversals require a
confirmed manipulation while BOS continuations do not.

The machine-readable preservation and review contract is
`agentic/design/smart-money-indicator-fidelity.json`. The Phase 1 authority is
`artifacts/strategy-development/smart-money-btcusdt-15m/phase1_criteria_checklist.md`.

## Product identity

- Pine v5 `indicator()`; no orders. Long/short position-style drawings denote
  pending setups, never fills or performance.
- Target symbol and venue: `BINANCE:BTCUSDT`.
- Execution timeframe: 15 minutes.
- Context timeframe: 4 hours.
- Execution semantics: all persistent state commits at confirmed 15-minute bar
  close; a ready setup becomes actionable from the following bar.
- HTF semantics: previous completed 4-hour source bar only.
- Canonical day Fib: 67%; 4-hour swing audit Fib: 71%.

## 15-minute structure

The raw primitive remains confirmed symmetric
`ta.pivothigh/ta.pivotlow(length=2)`. Accepted pivots alternate. A same-side
candidate replaces the active point only when it is more extreme. Weaker
same-side candidates reject and cannot move a break level. BOS/CHoCH requires a
body close through an active, unconsumed level.

## Confirmed 4-hour ownership

Imported 4-hour OHLC, pivot values, and source times use the previous source-bar
offset with `barmerge.lookahead_on`. The state therefore changes only when a new
4-hour period begins and cannot depend on a developing 4-hour candle. This
deliberate confirmation delay is part of the product contract.

## Direction ownership

Direction is not the latest structural bias. A locked confirmed 4-hour range
owns a midpoint. Confirmed price below the midpoint is discount and permits
longs only; confirmed price above it is premium and permits shorts only. An
unlocked range produces `WAIT`. HTF structural bias remains visible context and
cannot override the premium/discount gate.

## Temporal and sweep lifecycle

A buy-side sweep wicks above the active high and closes back at or below it. A
sell-side sweep wicks below the active low and closes back at or above it. A
body close through the level is a break.

The wick/reclaim event is a `POTENTIAL SWEEP`, not yet a manipulation. It becomes
a `CONFIRMED MANIPULATION` only when a later opposite-direction body-close
BOS/CHoCH consumes it. A body close through its swept level or replacement of
its structural reference invalidates it. A candle that sweeps both sides is
ambiguous. Repeated wicks cannot refresh an already-active candidate.

Every finalized record owns `source_time`, `known_time`, and
`confirmation_time`. For an imported 4-hour event, `source_time` belongs to the
completed 4-hour candle while `known_time` belongs to the later 15-minute close
where that completed source first committed. Visuals may point to the source but
the state label must appear at known/confirmation time.

Finalized confirmed, invalidated, and ambiguous records persist in a bounded
ledger. Production shows confirmed manipulations; audit mode additionally shows
candidates and rejected records.

## Canonical setup ledger

A setup may be created only when all of these are simultaneously knowable on a
confirmed 15-minute close: locked confirmed 4-hour context, locked 15-minute
range, a historically break-linked directional FVG, and valid canonical 67%
entry/100% stop/0% target levels. A reversal/CHoCH additionally requires an
opposite-break-confirmed manipulation. A continuation/BOS may proceed without
a fresh sweep because the day-trading transcript explicitly says that a new
liquidity purge is not always present or necessary for continuation trades.
The 4-hour premium/discount location is recorded as pro- or counter-location;
it does not veto a counter-trend entry.

Setup creation freezes its ID, direction, entry, stop, target, sweep ID and
times, break time, FVG ID, range endpoints, and `setup_ready_time`. A 67% level
already touched between the final range extreme and readiness rejects the setup.
The pending setup activates only on the next bar. Outcomes are `FILLED`,
`TARGET`, `STOP`, `MISSED_TP_BEFORE_FILL`, `INVALIDATED_BEFORE_FILL`, or
`AMBIGUOUS`; same-candle OHLC cannot invent intrabar order.

Every transcript-valid setup is recorded independently. An older pending or
filled setup cannot suppress a later valid setup; overlap policy belongs to the
future strategy execution layer. To stay below TradingView object limits, at
most 100 concurrent active setups receive drawings, but every active record
continues to be evaluated and included in the event ledger.

Late-entry tracking treats an uninitialized locked-range event pointer as a
new event explicitly; Pine comparisons with `na` are never used as booleans.
The rolling three-bar low/high window is evaluated on every bar before the
first confirmed range lock, then the committed touch state persists until the
next structural event. This is the cross-runtime contract exercised by the
`ENTRY_TOUCHED_BEFORE_READY` rejection.

## Event-linked imbalance

General FVG detection and mitigation remain available for chart context.
The LTF link belongs to the causal displacement leg from the event's opposite
structural origin through the confirmed post-break extreme. This replaces the
earlier two-bar distance heuristic. An unrelated older same-direction FVG
cannot satisfy readiness. The link remains historical evidence after
mitigation, matching the transcript's valid example where the imbalance had
mostly filled and disappeared before parameters were placed. Exact overlap
between the frozen 67% entry and the linked FVG is an `A+` quality grade; a
causal FVG without exact overlap remains a valid base setup.

## Visual and debug contract

Production mode keeps the existing structure, range, Fib, and FVG language and
adds bounded confirmed-manipulation records plus frozen position-style setup
drawings: green target box, red risk box, entry line, direction, setup ID, and
lifecycle state. Active setups are prominent; finalized setups are muted but
remain visibly inspectable.
Drawings begin only at the setup-ready bar. Audit mode adds rejected sweep
records. Debug mode exposes source/known/confirmation times and hidden proof
fields. Absolute drawing IDs are diagnostic only and excluded from parity.
Stable source/known/confirmation/readiness times and frozen price coordinates
carry the cross-runtime linkage instead.

The dense checklist dashboard remains an opt-in review surface and is disabled
by default. The default production chart must leave the candles, confirmed
manipulations, and long/short position geometry unobscured.

## Acceptance boundary

Acceptance requires:

1. exact parent and child byte identities;
2. Pine2Python parse and static inventory;
3. preservation of every declared unaffected source region and input default;
4. deterministic positive and negative fixtures for pivots, confirmed HTF
   ownership, premium/discount, sweep promotion/invalidation/ambiguity, late
   setup rejection, frozen setup fields, every lifecycle outcome, and reload
   stability;
5. compilation of the exact immutable candidate on TradingView;
6. focused 15m Bar Replay before/at/after review, historical persistence, a
   separate 4h preservation review, and reload stability;
7. matching proof-dashboard identity and values; and
8. an event-level funnel accounting for every BOS/CHoCH with one explicit
   terminal reason, exact transcript-ready/implementation-ready equality, no
   active-setup suppression, and frequency reported over the declared window;
   and
9. explicit user acceptance of the exact candidate hash.

Indicator acceptance does not authorize strategy construction, Python parity,
optimization, or the separate 71% aligned 15m alternative.

The current proof is `pev_148804e9528ff1f46091`, instrumentation v2.6, with
instrumented SHA-256
`70061ec29526fdcd850d3d453f54535dcf4841a1d200bbfbc106514e2cb60fb8`.
TradingView observation `pev_e834561bd129554ad866` matches exact source,
settings, window, data and all eight data segments, features, states, signals,
and rejections. The screenshot SHA-256 is
`02f6354c74cbda5b1010f9fd8f1ae3039b75e69a60373792027d6b1eccca118f`.
The observation remains `TRADINGVIEW_REVIEW_REQUIRED` only because the explicit
user/expert verdict for this exact source hash is pending. All earlier proof IDs
apply only to superseded revisions or diagnostic bisections.
