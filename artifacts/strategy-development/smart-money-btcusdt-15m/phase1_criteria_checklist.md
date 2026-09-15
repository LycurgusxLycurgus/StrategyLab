# Smart Money BTCUSDT 15m — Phase 1 criteria checklist

Status: `TRADINGVIEW_SIGNATURE_MATCH / USER_VERDICT_PENDING`

This is the canonical indicator-acceptance checklist. A setup count alone cannot
pass Phase 1. Every structural event must receive one terminal classification,
Pine and Python must agree on every strategy-consumed stream, TradingView must
corroborate the exact immutable bytes, and the user/expert must accept that hash.

## Transcript-derived entry contract

| Class | Rule | Transcript evidence | Implementation result |
|---|---|---|---|
| HARD | Confirmed body-close BOS/CHoCH and accepted imbalance in its causal displacement leg. | `smart-money-3.txt` lines 2034–2039 | Causal-leg provenance replaces the invented ±2-bar link. |
| HARD | The post-break 15m endpoint is confirmed before freezing parameters. | Lines 2079–2084 | Locked-range gate retained. |
| HARD | Intraday levels are 67% entry, 100% stop, 0% target. | Lines 2270–2273, 2382–2384 | Defaults preserved. |
| HARD | Only completed 4h context and confirmed 15m events may own readiness. | Lines 2226–2235 | Confirmed-close ownership retained. |
| CONDITIONAL | A CHoCH reversal requires a confirmed manipulation. | Lines 2040–2046, 2117–2120 | Enforced. |
| CONDITIONAL | A BOS continuation may pass without a fresh sweep. | Lines 2115–2122, 2369–2374 | Newly enabled; absence of a new sweep is no longer a rejection. |
| QUALITY | Exact 67%/FVG overlap is A+ confluence, not base validity. | Lines 2288–2300 | Recorded as a grade, not a veto. |
| CONTEXT | Pro/counter 4h location is disclosed but does not veto a valid 15m setup. | Lines 2275–2283, 2385–2391 | Recorded as context. |
| ALTERNATIVE | The later 71% sweep-required model is separate. | Lines 2052–2054 | Disabled and not mixed into the 67% model. |

## Acceptance gates

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| LIN-01 | Existing indicator lineage remains the source-derived parent; accepted 4h and visual regions are protected. | Workbench `pwb_6994ce1e623d`; baseline SHA `6994ce1e…`; final review `pev_1f40c4d1e536ea682f4b`. | PASS |
| DET-01 | Every confirmed 15m BOS/CHoCH receives one event ID and one terminal result. | 461 events: 57 READY + 404 exclusive failures. | PASS |
| DET-02 | Reversal and continuation are classified separately. | CHoCH requires manipulation; BOS continuation does not. | PASS |
| DET-03 | Imbalance belongs to the complete causal displacement leg, not an arbitrary bar-distance window. | 330 causal FVG events; positive and negative fixtures. | PASS |
| DET-04 | Existing pending/filled setups cannot suppress a later valid indicator setup. | Independent ledger arrays; 57 transcript-ready = 57 implementation-ready = 57 emitted. | PASS |
| DET-05 | Sweep, manipulation, range and setup state commit only on confirmed bars and are never backdated before known time. | Confirmed-event guards plus source/known/confirmation fields. | PASS_LOCAL_STATIC |
| DET-06 | Manipulations and setups persist with frozen historical geometry and lifecycle. | TradingView long #78 and short #71 plus current persisted history; separate 4h review. | PASS_VISUAL |
| FREQ-01 | Frequency plausibility is reported, not reduced to “at least one long and short.” | 57 setups over 7.439 weeks = 7.6623/week; 29 long, 28 short. | PASS_PLAUSIBILITY |
| LIFE-01 | Indicator records every valid setup independently and classifies its later OHLC lifecycle without inventing intrabar order. | 18 fills, 37 missed, 16 stops, 2 targets, 2 ambiguous; lifecycle fixtures pass. | PASS_LOCAL |
| VIS-01 | Position-style drawings begin at readiness, preserve coordinates, remain readable, and denote setups—not executed orders. | Exact candidate compiled and visually inspected on BTCUSDT 15m; historical long/short risk-target geometry persists. | PASS_STATIC_VISUAL |
| HTF-01 | Accepted 4h structure/range/FVG calculations and visual language remain preserved. | Exact candidate compiled and reviewed separately on 4h. | PASS_VISUAL |
| P2P-01 | Static analysis, source fidelity and platform budgets pass. | 62/64 plot counts; bounded drawings; immutable review package. | PASS |
| P2P-02 | Pine2Python and TradingView agree on dataset identity. | DATA, BARS, FIRST/LAST and all eight DATA SEG signatures match. | PASS |
| P2P-03 | Pine2Python and TradingView agree on strategy-consumed semantics. | FEATURES, STATES, SIGNALS and REJECTIONS all match. History-origin checklist counters and redundant latest-object time pointers remain diagnostic-only; lifecycle signal timing stays strict. | PASS |
| TV-01 | The exact immutable readable candidate compiles on 15m and inherits the protected 4h visual/calculation contract. | Revision `pvr_28090860d3444b575353`; SHA `449f4c298751e4cb5e4edff8d85de8bd2a20fb208c6ae92e5d36ba82e580cecf`. | PASS |
| TV-02 | The exact instrumented proof compiles within TradingView limits. | Proof `pev_148804e9528ff1f46091`, v2.6, instrumented SHA `70061ec29526fdcd850d3d453f54535dcf4841a1d200bbfbc106514e2cb60fb8`. | PASS |
| TV-03 | Bar Replay proves first appearance before/at/after readiness. | TradingView Basic blocks intraday Bar Replay. Static known-time and persistence evidence cannot substitute for replay. | EXPLICIT_LIMITATION |
| TV-04 | Expert/user accepts the exact candidate hash. | Technical and browser gates pass; explicit verdict for SHA `449f4c29…` is still required. | PENDING |

## Event-level funnel — 5,000 BTCUSDT 15m bars

| Terminal classification | Count |
|---|---:|
| READY | 57 |
| NO_LOCKED_HTF_CONTEXT | 212 |
| REVERSAL_WITHOUT_CONFIRMED_SWEEP | 106 |
| NO_CAUSAL_IMPULSE_FVG | 59 |
| ENTRY_TOUCHED_BEFORE_READY | 14 |
| CHECKLIST_GATES_NEVER_COINCIDE | 10 |
| NO_LOCKED_15M_RANGE | 3 |
| **Total BOS/CHoCH events** | **461** |

The count increase is caused by correcting transcript translation and detector
suppression, not parameter loosening: continuations no longer require an
invented fresh-sweep gate, FVG provenance uses the causal impulse, and the
indicator records concurrent setups independently.

## Exact proof identity and result

- Dataset: `ds_f6f2d4ba05c4`; 5,000-bar state history, last 1,000 bars hashed.
- Candidate revision: `pvr_28090860d3444b575353`.
- Candidate SHA-256: `449f4c298751e4cb5e4edff8d85de8bd2a20fb208c6ae92e5d36ba82e580cecf`.
- Review evidence: `pev_1f40c4d1e536ea682f4b`.
- Proof evidence: `pev_148804e9528ff1f46091` (`tv_table_v2_6`).
- TradingView observation: `pev_e834561bd129554ad866`
  (`TRADINGVIEW_SIGNATURE_MATCH`; user verdict pending).
- Proof window: `1784342700000..1785242700000`.
- Proof dashboard screenshot SHA-256:
  `02f6354c74cbda5b1010f9fd8f1ae3039b75e69a60373792027d6b1eccca118f`.
- Readable indicator screenshot SHA-256:
  `496dd986c9879ebcd26c3410737d2b205ba420a847f9425ee4e6a002be160263`.
- Readable indicator screenshot:
  `artifacts/strategy-development/pwb_6994ce1e623d/pvr_28090860d3444b575353/proofs/pev_148804e9528ff1f46091/tradingview-readable.png`.
- Matching: SOURCE, SETTINGS, WINDOW, BARS, FIRST/LAST, DATA, DATA SEG 1–8,
  FEATURES `0662028-0505754-0391294`, STATES
  `0548844-0533502-0336735`, SIGNALS
  `0580169-0924378-0924851`, REJECTIONS `0875125-0714658-0607458`.

The resolved Pine defect was the first-lock comparison
`na != internalRangeEventTime`, which evaluates to `na` rather than true. The
final child explicitly treats an uninitialized tracker as a new locked event
and evaluates the rolling three-bar touch inputs on every bar. Field grouping,
time partitioning, and exact-bar probes proved the correction before the full
dashboard was rerun.

## Strategy gate

No Pine strategy child, Python strategy port, optimization, or asset adaptation
is authorized yet. After feature parity and explicit indicator acceptance, the
strategy must inherit this exact indicator hash, add order semantics without
changing its calculations, receive separate TradingView corroboration, and
then pass Pine/Python trade parity.
