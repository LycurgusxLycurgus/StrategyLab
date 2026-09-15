# Smart Money BTCUSDT 15m — Phase 1 research record

Status: `READY_FOR_PINE_CREATION`

## Identity and authority

- Asset and venue: `BINANCE:BTCUSDT`
- Execution timeframe: 15 minutes
- Context timeframe: 4 hours
- Chart type: standard candles or hollow candles using exchange OHLC
- Execution policy: confirmed chart bars; confirmed 4-hour inputs
- Source route: `SOURCE_DERIVED_PINE`
- Authoritative source: `pre-strategies/smart-money-3.txt`
- Immutable extracted baseline:
  `pre-strategies/smart-money-indicator-baseline.pine`
- Current repair parent:
  `pre-strategies/smart-money-indicator-first.pine`
- Workbench: `pwb_6994ce1e623d`
- Parent revision: `pvr_30c0d57e607c8d8a7ff1`
- Parent SHA-256:
  `6878af85d56dd763020583760ca05ff367330bf5481dfd437330187166096756`

## Transcript contract

The 4-hour chart owns the active trading range and premium/discount direction.
Price above the confirmed range midpoint permits shorts; price below the
midpoint permits longs. The 15-minute chart owns execution structure. The
strict setup sequence is direction alignment, opposite-side liquidity sweep,
BOS/CHoCH plus displacement imbalance, confirmed execution range, and a pending
limit retracement. The canonical day entry is 67%, stop is the 100% range
extreme, and target is the 0% opposite extreme.

The source also contains a newer 71% 15-minute variant and says a fresh sweep
can be optional in continuation trades. Those rules conflict with the canonical
existing indicator and the approved strict-first model, so they are recorded as
audit-only alternatives and cannot influence accepted signals.

## Platform research

TradingView documents that `request.security()` can return developing
higher-timeframe values on realtime bars even with `lookahead_off`. The
confirmed-only pattern offsets the requested expression by one source bar and
uses `barmerge.lookahead_on`, which exposes the last completed HTF bar without
historical future leakage.

Primary references:

- https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
- https://www.tradingview.com/pine-script-docs/concepts/repainting/

## Existing implementation findings

1. Imported 4-hour OHLC and pivots use unoffset `request.security()` calls with
   `lookahead_off`; realtime HTF state can repaint.
2. The dashboard calls the latest structural break `HTF Bias`, but the
   transcript defines direction through premium/discount.
3. Sweep confluence tests only whether a historical sweep timestamp precedes a
   break. A sweep remains eligible forever and can qualify multiple events.
4. Directional FVG readiness tests whether any active same-direction FVG exists,
   not whether the FVG belongs to the qualifying break impulse.
5. HTF sweep labels use the source bar opening time and a large ATR offset,
   making the label appear detached from the swept level.

## Creation decision

Continue the existing immutable lineage. Make one semantic child for each of:
confirmed HTF ownership, premium/discount direction, sweep lifecycle, and
event-linked FVG/readability. Preserve the accepted 15-minute pivot repair and
all unrelated existing calculations and visuals.
