# Bitcoin intraday SMC-inspired research strategies

These are three fixed mechanical hypotheses for Binance USD-M BTCUSDT perpetuals. They are original systematic emulations of selected SMC ideas, not faithful replicas of discretionary ICT trading or evidence of institutional activity. Economic acceptance is pending the recorded comparison. The executable reference is Python; no TypeScript implementation was requested by placing the request inside a TypeScript code fence.

## Why these candidates

SMC leaves consequential choices to the trader: which structure matters, which block survives, what constitutes displacement, and which retest to trade. Two formalization routes were considered: port an indicator's exact state machine and separately add order rules, or design an explicit causal emulation of selected concepts. The second fits a request for an **inspired** strategy and avoids claiming fidelity to an indicator that is not itself a broker strategy. All added rules below are design choices fixed before testing, not source claims or optimized settings.

Selection criteria, frozen before performance: traceable primary descriptions, distinct hypothesis, complete causal rules, BTC intraday relevance, existing data/execution feasibility, and disclosed costs and gaps. None has independently established net BTC evidence. The order below ranks conceptual fit and inspectability, not expected profit.

1. **BOS/order-block pullback:** continuation after confirmed structure breaks, with a later rejection of a previously known block. Strongest direct SMC fit; symmetric pivots and last opposing candle are explicit adaptations.
2. **New York AM FVG reversal:** a session-limited liquidity excursion followed by displacement and a later gap rejection. The AM session and FVG concept have a primary description, but the prior-hour sweep filter, exact confirmation and BTC adaptation are designed additions.
3. **Turtle Soup +1 emulation:** an age-qualified failed breakout with next-bar reclaim. It supplies an independently described reversal family without asserting that Turtle Soup originated as SMC. The intraday channel, stop and market-entry rules are adaptations, not a reproduction of the original daily book system.

The old unconstrained reclaim/confirmation/FVG prototypes all failed their economic screen. They are not eligible winners here. Higher-timeframe lookahead examples, retrospectively labeled swings without availability times, protected-source strategies, and unverified vendor backtests were excluded. The prior shortlist informed source inspection but did not establish candidate acceptance. Three source-described hypotheses suffice; adding a fourth without stronger evidence would pad the comparison.

## Shared information and execution contract

Only contiguous closed 5m or 15m UTC candles are accepted. The 120-minute ATR is the arithmetic mean of true ranges from **prior** completed candles, excluding the current candle. No detector can emit until that ATR exists and is positive. Candles use UTC opening timestamps; a signal at index `i` becomes known at `open[i] + timeframe`, and can enter only at `open[i+1]`. Detection is independent of portfolio occupancy.

All entries are next-open market proxies. Risk is 0.25% of current equity, including modeled entry/stop costs, capped at 1x entry exposure. One position, no pyramiding, no automatic reversal. Stop distance determines a 2R gross-price target, with adverse tick rounding. Exit at stop, target or 180 minutes after entry; BTC's continuous market permits crossing a UTC date boundary within that duration. A stop gap exits at the adverse open. A candle touching both stop and target takes the stop. The existing simulator records that ambiguity and censors positions still open at a fold boundary, including marked equity rather than fabricating a fill.

Costs: 6 bps fee plus 2 bps adverse slippage **per fill**, with 4 bps slippage stress, and signed historical funding. These are research assumptions, not account quotes. Funding marks retain the previous campaign's audited opening-quote proxies, nine official daily archive repairs, and 1% adverse funding-payment buffer. Historical filter changes and exact settlement execution remain unverified. A next-open gap that places entry on the wrong side of the frozen stop rejects the order.

## 1. Confirmed BOS → order block → rejection

Supported execution: 5m and 15m, independently evaluated long, short and both.

At each close `i`, confirm a pivot at `k = i - 2` only if its high is strictly greater than the highs of all other candles in `[k-2, k+2]`; lows mirror this. Equal extrema are not pivots. Keep the latest confirmed high and low, each with its original index and unbroken/broken flag. A high BOS requires previous close at or below that high and current close strictly above; low BOS mirrors this. A pivot can break once. Consume its break even when no eligible block exists or displacement fails.

On a BOS, require a directional candle body of at least 0.5 prior ATR. Search backward from `i-1` through `max(pivot_index, i-12)` inclusive for the most recent opposite-colored candle: red for a bullish break, green for bearish; dojis do not qualify. Its full high-low range is the block. Freeze the stop at block low minus 0.1 ATR for longs, block high plus 0.1 ATR for shorts, using the BOS ATR. A valid new block replaces the single pending block; a failed BOS does not replace it. This full-range, last-opposing-candle definition is an original simplification, not LuxAlgo's exact block algorithm.

Process an already pending block before creating a new one on the same close. Retests must occur strictly after creation, within 60 minutes inclusive. Invalidate a long block on a low strictly below its low; mirror shorts. Invalidation precedes retest acceptance. A long retest must intersect the block (`low <= block_high` and `high >= block_low`), close strictly above its high, and have a bullish body. Shorts close strictly below block low with a bearish body. Emit one signal and consume the block. An unsuccessful touch remains pending; expiry and invalidation consume it. New confirmed pivots alone do not replace the pending block.

## 2. AM range sweep → displacement/FVG → rejection

Supported execution: **5m only**, long, short and both. Use `America/New_York` calendar dates and daylight-saving rules, including weekends because BTC trades continuously. Do not hardcode a UTC session offset.

Build the complete 09:00–10:00 local range from exactly twelve 5m candles on that date. No partial range or prior-date range is valid. From 10:00 onward, permit a signal only when its next-open timestamp is **strictly before 11:00 local**. Reset pending state on a new local date and terminate session state at 11:00.

A bullish sweep has a low strictly below the range low and closes strictly above it; bearish mirrors the range high. A candle satisfying both sweeps cannot arm a fresh sweep. Freeze its extreme, index and ATR-based stop beyond that extreme by 0.1 ATR. A new single-sided sweep replaces pending sweep or gap state. Process existing state first, including on a dual-sweep candle; after a signal, consume the day's allowance and do not arm another sweep. At most one signal per local date across both directions, independent of later portfolio suppression.

After the sweep and within 30 minutes inclusive, require a close strictly beyond the sweep's opposite extreme, a directional body at least 0.5 prior ATR, and a strict three-candle FVG: bullish `low[i] > high[i-2]`, bearish `high[i] < low[i-2]`. Freeze bullish gap `[high[i-2], low[i]]`, bearish `[high[i], low[i-2]]`. Confirmation creates a gap; it cannot simultaneously retest it. A new adverse sweep extreme invalidates either pending stage before confirmation/retest. A pending gap additionally invalidates on a long close below its lower boundary or short close above its upper boundary.

Within 30 minutes inclusive after gap creation, a later candle must intersect the gap, close strictly beyond its favorable edge, and have the directional body color. Emit a signal using the frozen sweep stop. No midnight carry of session state, no use of end-of-session hidden/remaining FVGs, no retroactive midpoint fill. If an existing setup expires or invalidates, the current candle can arm a fresh eligible sweep. A failed touch leaves the gap pending.

## 3. Age-qualified failed breakout +1

Supported execution: 5m and 15m, long, short and both.

Compute the high/low of the prior 20 completed bars, excluding the current bar. Use the **most recent** occurrence of each extreme when tied. An eligible downside breakout closes strictly below the prior low, whose most recent occurrence must be at least four bars old. Upside mirrors this. Freeze that original channel level and breakout candle.

On exactly the next candle, a long requires a close strictly above the frozen low; shorts require strictly below the frozen high. Equality fails. Long stop is the lower of breakout and reclaim lows minus 0.1 of the reclaim candle's prior ATR; shorts mirror the higher high. Emit at reclaim close, enter next open. No same-bar breakout/reclaim, additional displacement, FVG, trailing or hidden bias rule. A failed next-bar reclaim consumes the old breakout, and the current candle may independently arm a new qualified breakout. After a signal, do not arm a new breakout on that same candle.

## Comparison and stopping rules

`protocol.json` is preregistered: 15 candidate contexts plus six matched breakout controls, five chronological annual folds, base and stress costs: **210 economic evaluations**, zero parameter searches and zero mutations. 2022–2024 is historical development; 2025 and January–August 2026 are reused chronological screening evidence. The old 18-candidate comparison and published-source exposure remain disclosed. No window reused here is pristine out-of-sample evidence.

The breakout control uses the prior six-hour range with matching risk, costs, 2R target and three-hour maximum hold. Cash provides a zero-return/zero-drawdown negative benchmark. Advancement requires both recent base folds positive, at least 30 closed trades in each and 100 combined, overall closed-trade net PF at least 1.05, each fold close drawdown at most 10%, and summed recent stress returns positive. These preliminary gates were inherited unchanged to avoid weakening them after observing results. Eligible candidates rank by greatest worst-fold return, then mean-fold return. Relative rank alone never qualifies a candidate.

If none qualifies, stop at `RETURN_TO_PHASE_1`; do not create an accepted baseline or tune the least-losing strategy. If one qualifies, preserve its exact rules and evidence for Phase 3 acceptance; that does not authorize optimization or final testing. September 2026 onward remains uninspected by this campaign. A final test needs a separately frozen finalist and demonstrably untouched or forward data.

## Sources and fidelity limits

- [LuxAlgo SMC](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/): primary description of BOS/CHoCH and order blocks. It is an indicator, not a complete execution specification. Page rechecked October 28, 2026; displayed update September 23, 2025. Prior decoded-source audit identity and license are recorded in the [research shortlist](../../../agentic/research/smc-mechanical-shortlist-2026-10-23.md); no indicator code is copied here.
- [LuxAlgo Silver Bullet](https://www.tradingview.com/script/fq4wSUev-ICT-Silver-Bullet-LuxAlgo/): primary AM 10:00–11:00 New York window, FVG/retest description, and below-15m guidance. Page rechecked October 28, 2026; displayed update July 6, 2023. End-of-session chart filtering is deliberately excluded from causal decisions.
- [Silver Bullet AM Session implementation](https://github.com/hindsight-finance/Silver-Bullet-AM-Session): an inspectable NQ 1m formulation, useful for separating session, sweep and entry concepts. Its performance does not transfer to BTC; no code is reused and its license remains unverified.
- [Puzanov, Turtle Soup and Turtle Soup +1 formalization](https://www.mql5.com/en/articles/2717): a published daily formulation with disclosed interpretation gaps. This is conceptual provenance, not a BTC intraday profitability result or exact replication claim.
- [Binance public data](https://github.com/binance/binance-public-data): official archive/checksum mechanism; exact raw identities and funding provenance remain in the data manifest and each run's identities.
- [Deprez and Frömmel, 2024](https://doi.org/10.1016/j.iref.2024.05.003): cost-aware technical-rule research supports chronology and selection controls, not an SMC edge. Abstract-level evidence only.
- [Tangirala, 2026 research repository](https://github.com/harshatangirala/smc-ict-research): author-reported daily S&P 500 SMC detector study, not independently audited here. Its distinct market/horizon prevents importing its conclusion to BTC; it reinforces the need to separate indicator events from net strategy evidence.

Source licenses/versions and past rejection reasons remain in the prior research shortlist. The code here is independently authored from this explicit design contract. Detector correctness, discretionary-source fidelity, data integrity, modeled execution, economics, and platform acceptance receive separate verdicts.

## Reproduce

From repository root with a working Python 3.12+ interpreter and IANA timezone data for `America/New_York`. The bundled interpreter was verified in this workspace; its location is environment-specific:

```powershell
$python = 'C:\Users\Baham\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m unittest app.btc_smc_tests app.btc_liquidity_tests
& $python -m app.btc_smc_campaign --run-id comparison-v1
```

The runner reads the existing checksummed development archives; it does not download data. Existing run IDs must fail rather than overwrite evidence. Each run must retain protocol/code/data identities, detector events, all economic evaluations, trade/funding/equity traces, visual ledger, comparison report and trial ledger. Read the actual run report for current results; this document specifies the frozen hypotheses.
