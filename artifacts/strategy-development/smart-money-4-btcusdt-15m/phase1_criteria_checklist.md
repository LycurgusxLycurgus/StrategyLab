# SmartMoney-4 15m — active Phase 1 criteria checklist

Status: V6_3_COVERAGE_CANDIDATE / LOCAL_REGRESSION_PASS / TRADINGVIEW_REVIEW_REQUIRED / EXPERT_PENDING.
This document supersedes the rejected v8 checklist, not its archived evidence.

Current candidate identity: source `pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine`,
SHA-256 `5ef00859797f0dc960d3762b4d217fd76e92c70d7b0cb4d70a7f556909cf0718`,
Workbench `pwb_f89ea6f3774a`, registered revision `pvr_362b3c72c6d2e797c46a`,
and proof `pev_a6fb9e4e8dd1a838d665`. The revision is source-accepted,
parse-complete and statically reviewed, but remains `TRADINGVIEW_REVIEW_REQUIRED`
and is not an accepted indicator or strategy parent.

Authority: timestamped SmartMoney-4 transcript and mandatory video frames.
Phase 1 targets source-valid coverage; PF/win rate are diagnostics, not filters.
A successful indicator gate does not imply strategy acceptance or profitability.

## Macro contract

| Class | Rule | Source | Required observable |
|---|---|---|---|
| HARD | Confirmed 15m decisions, previous completed 4h context. | 01:52–02:03; approved non-repaint contract | Separate source/known/ready times; next-bar activation. |
| MECHANISM | Independent retained 2/2 structure, confirmed endpoint on or after BOS. | User-selected v6 plus approved v6.1 boundary repair | Preserve baseline pivots/BOS and two later confirmation bars. |
| HARD | Body-close BOS and positive locked range own geometry. | 04:25–04:41; causal implementation contract | Exact broken level and range anchors. |
| SCORE 25 | Long in 4h discount; short in premium. Mismatch is not a veto. | 02:02–02:56 | Frozen HTF row and provider context. |
| SCORE 25 | Confirmed BOS through prior structure. | 04:25–04:41 | Owned level, BOS time and direction. |
| SCORE 25 | Prior level pierced and reclaimed, then opposite causal BOS. | 04:41–05:10 | Known level before wick; no intervening close-through. |
| REPAIR | Attaching sweep evidence to a preliminary candidate does not invalidate that evidence. | Approved 2026-09-03 plan; video does not specify candidate-consumption rule | Validity independent of Standard/Perfect; frozen linked metadata; no duplicate same event. |
| SCORE 25 | Open causal three-candle FVG contains selected Fib entry. | 05:10–05:36 | Gap coordinates and selected Fib overlap. |
| ENTRY | 71% coverage default or 75% selectable; range endpoints are stop/target. | 05:51–06:12; 06:38–07:46; v6.3 candidate contract | Correct direction and no pre-readiness entry touch. |
| DECISION | Video Standard 75/100; Perfect 100/100. | 01:03–01:29; 02:46–02:56 | Three of four allowed, missing item explicit. |
| OPTIONAL | POC mode adds fifth check; Standard80; ±2 dynamic POC rows. | 03:10–03:39; approved product choice | No POC veto in default Video mode. |
| VISUAL | Preserve v6.1 dark checklist, risk and full historical geometry. | Approved user presentation | No restyling or added trader settings. |

## Mandatory video comparisons

| Frame | Acceptance purpose |
|---|---|
| `00-00-38.270.png` | 75 SELL with HTF mismatch and compact 3/4 checklist. |
| `00-01-04.290.png` | 75 remains a valid visible setup. |
| `00-04-13.390.png` | Short BOS/sweep/range/Fib relationship. |
| `00-05-10.650.png` | Short 75 entry, stop high, target low. |
| `00-06-56.130.png` | 100 BUY with all four criteria. |
| `00-07-21.670.png` | Long BOS/sweep/FVG and 71–75 golden zone. |
| `00-07-36.450.png` | Current long position geometry. |
| `00-08-13.950.png` | Frozen historical explanation despite later state changes. |

## Detection and regression gates

- Freeze v6.1 revision `pvr_122d076db526ae8f9628`, source SHA-256
  `8665c5570b1370d674c9a6b8705375fcf4d50010acad75650c08e4cc3456cbb4`.
- Preserve raw pivots/BOS, confirmed-bar semantics, HTF, thresholds and rendering.
- Real sweep invalidation remains close-through of the swept level. No arbitrary
  timeout or score-dependent consumption. Distinct causal BOS/ranges may share
  still-valid evidence; one identical event never creates duplicate setups.
- Every structural candidate receives a terminal status. Separately inventory
  continuous chart windows to find valid opportunities neither model emits.
- Reconcile all baseline setups by owned levels and timestamps, not totals alone.
- Test both directions, invalidation, frozen snapshots, quality-mode independence,
  duplicate prevention, prefix stability, delayed confirmation and next-bar action.
- Compare exact declared Pine/Python traces on identical data. Unsupported PineTS
  requests remain explicit. New sweep fields require expanded proof coverage.
- TradingView compile/runtime, matching dashboard, direct historical navigation
  and reload must pass; save screenshot hashes and exact source identity.
- Expert/user verdict is pending until explicitly given for that source hash.
- PF, costs, win rate, fills/unfilled/AMB and sample size are reported separately;
  a low PF alone does not reject a source-faithful Phase 1 baseline.

## Dataset boundary

Primary parity: BINANCE:BTCUSDT15m, previous completed4h.
Gold browser: OANDA:XAUUSD15m through ordinary symbol search.
Legacy MT5 gold local data has unverified timezone/native4h ownership; it is a
provisional comparison, never exact OANDA parity. Other assets use the same rules
with explicit feed/unit/session/volume contracts, not asset-specific tuning.

## Evidence routing

Current and child evidence: `golden_case_manifest.json`, `golden_case_review.md`,
`viability_report.json`, and `tradingview/` in this directory.
The prior v8 proof stays under its immutable revision and is not current evidence.
The detailed implementation checklist is `agentic/analysis.md`; source contract
and tentative workflow lessons are `agentic/design/smart-money-4-clean-contract.md`.

Current child identity: `pvr_362b3c72c6d2e797c46a`, source SHA-256
`5ef00859797f0dc960d3762b4d217fd76e92c70d7b0cb4d70a7f556909cf0718`.
The current exact instrumented proof is `pev_a6fb9e4e8dd1a838d665` with
instrumented-source SHA-256 `fb69e209d4d6f41f61eac6066a1cdd15a5909ce5c6c45eb96e85759875b92c66`.
Its local runtime is unavailable because the immutable analysis records
`request.*` runtime as unsupported; the proof therefore remains
`TRADINGVIEW_REVIEW_REQUIRED`. Earlier FEATURES divergence evidence remains an
open issue in `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` and cannot be closed by the
current expected-dashboard artifact alone.
