# SmartMoney-4 video-faithful 15-minute indicator contract

Status: local validation and TradingView signature pass; explicit user/expert
acceptance pending.

## Lineage

SmartMoney-4 is a separate product branch. Its immutable conceptual parent is
SmartMoney-3 revision `pvr_28090860d3444b575353`, source SHA-256
`449f4c298751e4cb5e4edff8d85de8bd2a20fb208c6ae92e5d36ba82e580cecf`.
SmartMoney-3 remains unchanged and recoverable. SmartMoney-4 reuses its
confirmed 15-minute structure, completed 4-hour context, sweep lifecycle,
causal range ownership, and independent setup ledger, then replaces the 15m
entry/scoring/visual contract with the video contract below.

The exact review candidate is Workbench revision `pvr_d74f2a2bfe9a19e11f8d`,
source SHA-256
`bdb0f5e43a3b99c7edc8445b6b6dd1758fc5ca05e7c6273ab03bb77d39159ed3`.
It is a child of the first SmartMoney-4 implementation revision
`pvr_412e28f408611644c233`; the only child change is a proof-compaction marker
around the pure video-dashboard render block, with no calculation or visible
behavior change.

The product authority is `pre-strategies/smart-money-4/The ONLY 15 Minute
Trading Strategy You Need in 2026/Transcript con timestamps.txt` plus the
timestamped screenshots in its `Capturas` folder.

## Product identity

- Pine v5 `indicator()` only; no orders or performance claims.
- Execution timeframe: 15 minutes. Context timeframe: completed 4 hours.
- Persistent state commits only at confirmed 15-minute closes.
- A ready setup becomes actionable from the next bar.
- Default execution entry: 75% of the locked 15m range.
- Optional companion/alternate entry: 71%.
- Stop and target are the opposite range endpoints: long stop low / target
  high; short stop high / target low.

## Four-item trade score

Each criterion contributes exactly 25 points:

1. `HTF Alignment`: a long lies in confirmed 4h discount or a short lies in
   confirmed 4h premium.
2. `Break of Structure`: a confirmed 15m body close breaks an active,
   unconsumed structural level and the associated range becomes locked.
3. `Liquidity Sweep`: the event owns an opposite-side wick/reclaim candidate
   promoted by the confirming structural break. Source and known time remain
   separate; no sweep is backdated.
4. `Imbalance`: a directional raw three-candle gap belongs to the causal
   displacement leg. The optional ATR filter is an audit variant and is off by
   default because it is not in the video checklist.

A candidate requires a confirmed BOS and locked geometry because otherwise
entry, stop, and target cannot be defined. A score of 75 or 100 may emit a
setup. Alignment, sweep, and imbalance are scored, not hidden vetoes. A 100
score is the all-four grade; 75 is valid because the source explicitly takes a
75 setup with negative HTF alignment.

The score and all four Boolean values freeze at setup readiness. Later market
state cannot rewrite the explanation of a historical setup.

## Visual contract

- A compact two-column checklist at top right shows 4h location, BUY/SELL,
  four pass/fail rows, and 0/25/50/75/100 score.
- The current setup uses TradingView Long/Short Position visual language:
  green target box, red risk box, entry line, direction, score, state, and
  frozen levels.
- When a setup reaches a terminal state, its boxes/line/detail label are
  deleted and replaced at the original readiness time by one `LONG` or `SHORT`
  marker. Historical geometry never remains as chart clutter.
- A 71% dotted companion line and the 75% execution line form the visible
  golden zone when both differ.
- The dense engineering dashboard remains opt-in and cannot replace the compact
  production checklist.
- POC/volume profile and scanner behavior are non-gating and out of scope.

## Acceptance boundary

Acceptance requires source identity, Pine2Python parse/static review, plot and
compiled-token preflight, an event-level score funnel, deterministic lifecycle
fixtures, exact Pine/Python agreement on the four criteria and score, exact
TradingView compilation, focused visual comparison against the mandatory video
frames, historical marker persistence, separate 4h preservation review, and an
explicit user/expert verdict for the exact source hash.

SmartMoney-4 indicator acceptance does not authorize a Pine strategy, Python
strategy port, optimization, or asset adaptation.

## Current evidence

- Dataset `ds_f6f2d4ba05c4`, 5,000 BTCUSDT 15m bars, 7.439 weeks.
- 461 structural events, all terminally classified; 91 ready setups (50 long,
  41 short), 12.2328 setups/week.
- Score distribution by event maximum: 0 = 6, 25 = 55, 50 = 288, 75 = 109,
  100 = 3.
- Exact Pine2Python proof: `pev_e78575983dd76190d01b`, instrumentation
  `tv_table_v2_12`, instrumented SHA-256
  `d2bd9d5801326748b8f37be74c66e921356f6eb3ce152ee076347e4de7887931`.
- TradingView observation `pev_84deaabf572a5e482f8e` is an exact signature
  and dataset match; status remains `TRADINGVIEW_REVIEW_REQUIRED` solely because
  the explicit user/expert verdict is pending.
- Readable screenshot SHA-256
  `f21e8298cf2376d1d9d4183a68ac1fb7c811fa968c1f2a286e752714a95ef3c5`;
  proof screenshot SHA-256
  `60c5f4c4a6995f74902220acdeeb2fab75db337b0247c2fb62d19c2fdb9b6e0b`.
