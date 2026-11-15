# Research contract: BTC liquidity excursions

This campaign creates explicit rules inspired by liquidity sweeps and local structure shifts. It does not replicate a particular discretionary SMC trader or assume that discretionary strategies must fail when automated. The question is whether a small, fully specified analogue survives Bitcoin trading costs and several chronological market periods.

The campaign context and rejection screen were saved in `protocol.json` before evaluating performance. The raw data covers Binance USD-M BTCUSDT perpetual futures, January 2022 through August 2026. Five-minute bars are the original input; fifteen-minute bars aggregate complete UTC triplets from the same feed. September 1 through October 22, 2026 is reserved and must not be fetched until one qualified finalist and its final-test criteria freeze. Older BTC spot backtests in this repository constitute prior development exposure, not clean final evidence.

## Phase 1 decision

| Hypothesis | Mechanical interpretation | Main uncertainty | Decision before performance |
|---|---|---|---|
| Failed range break / liquidity sweep | Pierce a prior completed range, reclaim it, then fade the excursion | A wick does not reveal resting liquidity or institutional intent; small reversals may not cover fees | Top-1 research concept: minimal causal definition and a clear ablation |
| Structure breakout and continuation | Close outside the prior range and enter in the breakout direction | Breakouts can whipsaw; it is not the same hypothesis as fading an excursion | Simple comparator, never silently combined with the top-1 |
| Order-block midpoint / displacement retest | Select an opposing candle before an impulse and wait for its midpoint | Extra choices about anchors, expiry and limit fills substantially expand the trial space | Defer; no evidence yet justifies the extra mechanism |

This ordering reflects simplicity, falsifiability and data feasibility. It is not an empirical profit ranking. No source consulted supplies independent evidence that these exact BTC intraday rules are profitable. The implementation is original Python; no third-party indicator code or licensed trader rule set is copied.

## Rule criteria and provenance

| Class | Rule | Availability / adaptation | Responsible symbol and proof |
|---|---|---|---|
| Hard | Prior six-hour range excludes the current bar | Explicit rolling-range substitute for discretionary liquidity levels; no future-confirmed pivots | `indicators`; hand-computed range and prefix-invariance tests |
| Hard | ATR is the arithmetic mean of true ranges over the prior two hours | Fully completed bars; deliberately not Wilder ATR | `indicators`; prior-bar exclusion fixture |
| Hard | Long: low below prior low by more than 0.1 ATR, then close above prior low; short mirrors it | Objective failed excursion, not evidence about actual order-book liquidity | `detect`; independent sweep and negative cases |
| Hard | Exclude a bar sweeping both sides | Intrabar excursion order is unknown | `detect`; dual-sweep case |
| Isolated alternative | Immediate reclaim | Signal at sweep close, earliest entry next open | `reclaim`; timing fixtures |
| Isolated alternative | Local break confirmation | Within 45 minutes, close beyond the sweep candle's opposite extreme with directional body at least 0.5 prior ATR; invalidate on a new sweep extreme | `confirm`; positive, invalidation and expiry cases |
| Conditional | Strict three-candle gap at confirmation | Long current low above high two bars ago, short current high below low two bars ago. The gap is a price-pattern filter, not proof of an unfilled institutional order | `confirm_fvg`; positive and no-gap fixtures |
| Hard | New single-sided sweep replaces a remaining pending sweep | One pending detector state; simultaneous confirmed signals may coexist with a new pending state | Detector replacement tests and event funnel |
| Hard | Stop 0.1 ATR beyond the original sweep, rounded outward; 2R target from actual simulated entry | Geometry freezes before the following bar; target is a market-trigger proxy, not a guaranteed limit fill | `simulate`; tick, gap and dual-touch cases |
| Hard | Six-hour maximum holding period, then next-open exit | Time exit is scheduled using elapsed completed bars | `simulate`; time-exit fixture |
| Hard | One position, no pyramiding/reversal | Detector remains independent of position policy; order concurrency suppression is recorded separately | Detector funnel versus broker counters |
| Context | BTCUSDT perpetual, 24/7 UTC, 5m and 15m; long/short/both | Separate fair comparisons with common clock durations | All 24 contexts and annual trial ledger |
| Quality screen | Profit, cost adversity, drawdown and activity thresholds | Research rejection criteria only, frozen in protocol; no universal trade-count or significance claim | Campaign runner `qualifies` and full results |

## Execution and uncertainty

Capital starts at 100,000 USDT in each annual fold. Nominal stop risk, including modeled entry/stop-exit fees and slippage, is capped at 0.25% of current equity. Entry notional is capped at 1× equity, inclusive of entry fees. Quantity floors to 0.001 BTC and respects a 0.001 minimum, 120 BTC maximum and 50 USDT minimum notional. These are the captured contemporary research filters; historical changes remain unverified.

Before any economic evaluation, the historical funding endpoint returned blank mark prices in all 1,000 rows of its first page. The exact pages and rates remain authoritative. Missing marks therefore use the opening quote of Binance's official checksum-verified five-minute mark-price candle containing the funding timestamp. Funding timestamps sometimes have a few milliseconds of publication jitter. This opening quote is a causal proxy, not a claim to recover exact settlement prices. Existing valid API marks are preserved. A fixed 1% adverse funding-payment buffer increases all debits and reduces all credits, in both baseline and stress runs. No future mark-candle high, low or close enters this join. This evidence-driven adaptation changes the data contract before performance comparison; it does not change the strategy or search budget.

The full funding census contains 5,112 events: 3,107 valid API marks and 2,005 missing marks requiring 22 monthly mark-price archives. Three checksum-valid monthly archives omit a day: July 31, 2022; October 2, 2022; and February 24, 2023. Nine required funding opening quotes are therefore supplemented from the corresponding official daily archives, also checksum verified. Monthly source bytes remain unchanged; a repair log and per-row provenance identify this supplement. If either official source cannot supply an exact required candle open, the join blocks; neighboring quotes are never borrowed.

Signals use only closed bars. The broker sizes a synthetic market order at the following opening quote and applies adverse slippage immediately. That assumes idealized quote-to-fill timing, not a zero-latency venue guarantee. The fixed 6 bps fee per fill is a conservative account-independent assumption. Baseline adverse slippage is 2 bps per fill; stress is 4 bps. Historical funding uses the actual signed rate and an API mark or the disclosed opening-quote proxy. Funding exactly at an open applies to positions carried into that open. If an intrabar funding event and possible intrabar exit have unknown ordering, the simulator charges a possible debit and omits a possible credit.

Stops gap adversely. A candle touching both stop and target exits at the stop, with an ambiguity reason. Target gaps receive no favorable price improvement. Open positions remain censored at each fold cutoff; marked equity includes unrealized P&L and a reserved exit fee. Each annual fold starts flat with fixed capital and prior data available only for indicator warmup. Annual results are separate experiments; their sum is not continuous compounded performance. Marked equity uses last-trade candles, not venue mark-price candles. Liquidation, acknowledgement, rejection latency, partial fills and historical filter changes are unsupported; none of these research artifacts certifies live venue execution.

## Experiment and stopping rule

Three fixed approaches × two timeframes × three directions produce 18 candidates. One removed-sweep breakout control produces six more contexts. Each runs at baseline and stress costs in five chronological annual folds: 2022, 2023, 2024, 2025 and January–August 2026. Total: 240 economic evaluations, all recorded. There is no parameter search or structural mutation in this approach comparison.

A candidate clears the preliminary screen only when both recent folds are profitable, each has at least 30 closed trades and together at least 100, combined closed-trade profit factor is at least 1.05, annual close-equity drawdown stays within 10%, and summed recent stress returns remain positive. These thresholds reject sparse, fee-fragile and recent-regime failures; they are not statistical confidence bounds. Rank qualified candidates first, then by worst annual return and mean annual return. Publish every rejected candidate and control.

If none qualifies, return to Phase 1. Keep the reserved data untouched. Do not optimize failure away, call the least-losing candidate deployable, or bypass Phase 3/runtime authorization. If one qualifies, it remains a prototype pending independent Phase 3 acceptance, a valid baseline-backed optimization grant, and later final/forward evidence. Phase 6 requires an actual paper adapter and forward reconciliation; no paper or live orders are authorized here.

## Reproduce

Use a working Python 3.12+ interpreter from the repository root. The existing `.venv` points to a missing interpreter on this machine; these new modules use only the standard library. In this session the working interpreter is `C:/Users/Baham/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

```powershell
python -m app.btc_liquidity_data --download --root artifacts/strategy-development/btc-liquidity-20261023/raw
python -m unittest app.btc_liquidity_tests
python -m app.btc_liquidity_campaign --run-id my-new-reproduction
```

The downloader resumes verified archives and preserves original bytes and checksums. Run IDs must be new; evidence directories are never overwritten. Reproduction under the frozen development contract is not a new untouched test and does not reset selection exposure. Read the generated report and full trial ledger before drawing conclusions.

## Primary sources consulted, October 23, 2026

- [Binance public data](https://github.com/binance/binance-public-data): USD-M kline schema, monthly archives, checksum verification and revision policy. Source repository declares MIT; dataset use also refers to its separate terms. No source code was copied.
- [Funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History): inclusive time bounds, maximum 1,000 records per page, ascending records and mark prices.
- [Exchange information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information): use explicit tick/quantity filters rather than displayed precision. A raw current response is retained alongside the data.
- [Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf): motivates finite trials, disclosure of selection exposure and cautious interpretation. This campaign does not claim to compute the paper's PBO estimator or prove an edge with a holdout alone.

An attempted CME support/resistance URL returned not found and a Binance fee FAQ was blocked; neither was used as factual support. No current fee tier was authenticated or inferred from those pages.

## Data-development failure accounting

The initial sandboxed public-network probe was denied; the same scoped public requests succeeded through the approved elevated executor. The first complete candle download succeeded, while strict funding normalization stopped on blank historical API marks. After the explicit pre-performance mark-proxy adaptation above, a retry exposed a Windows manifest replacement/read race in cached download workers; passing a read-only manifest snapshot to those workers addressed that boundary. These are retained data-development failures, not rejected economic strategy trials. No economic results were inspected to motivate either correction.
