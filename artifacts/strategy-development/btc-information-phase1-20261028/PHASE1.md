# New information research: intraday BTC, 5m and 15m

**Recommended next hypothesis: reversal after a large observed liquidation-driven dislocation.** Use 5m or 15m decisions, give the move time to mean-revert, and remain flat within the UTC day. This is an original designed research proposal, not a profitable strategy or a replication of the supporting study.

**Current gate: BLOCKED for Phase 2.** One proposal is fully specified for feasibility, but continuous event data and execution costs during stress are not accepted. No new economic backtest has run. This phase made concrete progress: correct trade-tape inputs, two historical sample audits, actual liquidation data, the local-history inventory, a provider comparison and an explicit hypothesis/control contract.

## Your constraints and the best route

Keep both 5m and 15m execution frames. Root uses a common UTC trading day to make intraday precise: no position carries beyond next 00:00. The initial proposal holds at most 120 minutes and admits entry no later than 22:00 UTC; longer holds remain possible only in another independently justified hypothesis. The chart interval need not equal holding time.

My recommendation is event-driven research aimed at moves large enough to plausibly pay for both fills. Ordinary small-flow continuation is a weak starting point under the current 16/20 bps round-trip cost assumptions. Do not reduce assumed fees or add an optimistic maker-fill model to make a weak signal pass.

## I found the earlier Binance history

The local database registry lists `binance-btc-15m-full-1mil`, dataset `ds_d14d74e36d0d`, with 303,723 rows at `artifacts/data/ds_d14d74e36d0d.csv`. Its header is `ts,open,high,low,close,volume,symbol,timeframe`. Several other registered BTC candle sets are also present. Current `binance_public` downloader code calls the spot `/api/v3/klines` endpoint; the older normalized CSV alone must not be relabeled as verified perpetual-event history. A stale registry path into the earlier pre-nexuz checkout no longer exists.

The separately audited campaign data at `artifacts/strategy-development/btc-liquidity-20261023/raw` contains 2022–August 2026 USD-M 5m candles, quote/taker volume, historical funding and mark-price provenance. These are reusable price/risk/funding inputs. They cannot identify individual forced liquidation events or their collector receive times. The inspected workspace and dataset registry contained no earlier continuous liquidation capture. [LOCAL_DATA_INVENTORY.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/LOCAL_DATA_INVENTORY.json) records this inspection.

## What the new samples proved

| Check | Observed result | Limit |
|---|---|---|
| Official Binance aggregate-trade sample, 2022-01-01 | 997,179 records, official SHA-256 matches, no aggregate-ID gaps; 96 nonempty first-10-second quarter-hour windows | One day, not all history or real-time latency |
| Aggregate tape versus existing 5m candles | Daily base/quote/buy totals exactly equal; 43 of 288 bins differ | Boundary allocation cause unproven; retain original clocks and do not force parity |
| Reported liquidation sample, same preselected day | 1,052 rows; exchange and receive timestamps; 599 buy/453 sell; all IDs absent | Public stream is sampled; IDs do not identify unique orders |
| Receive timing on liquidation sample | Median 20.05 ms, max 549.60 ms after exchange timestamp; no negative sample lags | Neither a population latency guarantee nor a complete capture audit |
| Public trade archive catalog | 365 daily ZIPs for 2022, 7,506,959,689 compressed bytes | Metadata only; full history not downloaded |

Both market samples were selected by calendar date before any outcome analysis. Stored sample/metadata payloads total 14,170,658 bytes, below the 25 MiB cap. The trade ZIP has an official checksum. The liquidation gzip has verified readable CRC and our frozen SHA, but no independently published checksum is claimed. The earlier liquidation HEAD returned 404; a bounded GET returned 200 and a valid gzip. A HEAD result was therefore not used as proof of unavailable data. Audit files: [SAMPLE_AUDIT.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/SAMPLE_AUDIT.json), [TIMESTAMP_RECONCILIATION.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/TIMESTAMP_RECONCILIATION.json), [LIQUIDATION_SAMPLE_AUDIT.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/LIQUIDATION_SAMPLE_AUDIT.json). The first audit retains the failed exact 5m bin-parity check rather than rewriting it as a pass.

## Why simple quarter-hour flow was downgraded

Kim/Hansen use the same aggregate-trade input family, not necessarily individual raw fills. The correct first 10-second feature is measurable; the old five-minute totals could not reconstruct it. Their BTC slopes imply only about 3.00/4.34/4.99 bps in conditional Q25-to-Q75 differences at 4/8/12 hours. Those are regression contrasts, not trade returns; they do not prove every tail loses, but they do not establish a standalone edge over our costs. The separate 0.5 bp opening-price forecast is a different target. [Versioned primary paper](https://arxiv.org/html/2607.09426v2).

## The chosen research hypothesis

An original industry matched-event study motivates liquidation exhaustion: reported liquidation shocks relaxed more than comparable non-liquidation shocks over two hours. Its 67 matched pairs, sampled dates, composite prices and marginally conflicting statistical tests do not establish executable Binance-only 5m/15m profits. A between-group difference is not expected trade PnL. This is weaker industry evidence, used as motivation only. [Original study](https://sharpeedge.substack.com/p/bitcoin-price-discovery-an-empirical).

The complete designed proposal is [CANDIDATE_PROPOSAL.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/CANDIDATE_PROPOSAL.json). It deliberately differs from that study:

1. Bin only reported Binance liquidation messages available by the decision, using the later of event and receive timestamps. Buy means forced short closure; sell means forced long closure. Treat this as observed-message pressure, not total liquidations or informed trader identity.
2. Require an unusually large net-pressure score: above the 99th percentile from 30 prior complete UTC days, with a same-direction price impulse of at least 60 bps. Zeros count only on verified healthy capture intervals; missing capture is unavailable, not zero.
3. Fade that move. The pre-impulse bar open is a known anchor. Wait one full execution bar after the observing close; reject entry unless at least 60 bps remains between the slipped entry and anchor. That is room for a possible reversal, not a forecast that it will occur.
4. Use a frozen 2ATR hard stop, anchor take-profit market trigger, at most 120-minute hold and mandatory UTC-day exit. Preserve the established 0.25% stop-risk/1x exposure/cost admission and adverse ambiguity conventions.
5. Compare against an otherwise identical price-shock reversal with the liquidation condition removed. That control tests whether the new information improves the hypothesis; it is never selected as a winning candidate.

The 60 bp requirement is three times the 20 bp stress roundtrip reference. It is a predeclared design choice, not an optimized threshold or proof of positive expectancy. The causal 30-day percentile replaces a full-sample ranking; the stop, target, delay and risk overlay are also original design choices. Sparse sample and execution-cost failure remain plausible. We have not counted qualifying events or inspected forward outcomes to choose these parameters.

If all data/execution prerequisites pass and Phase 2 is separately authorized, the bounded planned matrix is one candidate and one price-only control, 2 execution frames, 3 direction policies, 5 annual folds and 2 cost conditions: 120 evaluations. The authorized economic budget now is zero. Existing absolute economic gates remain the reference; they are not relaxed to accommodate rare events.

## Dataset source decision

| Source | Result for this contract |
|---|---|
| Existing Binance downloads | Reuse price/volume/funding; liquidation and receive-clock fields absent |
| Current Binance public archive | USD-M daily category listing lacks liquidationSnapshot; the 2025 prefix is empty. This does not prove no private or other historical archive exists |
| Tardis | Strongest documented fit; BTCUSDT metadata lists liquidation and quote/book-ticker types; successful free sample with both clocks |
| CoinAPI | Secondary inquiry route; exact historical event/receive-clock linkage and 2022 coverage unresolved |
| Kaiko | Published liquidation-event history starts 2025-01-08; misses 2022–24 |
| CoinGlass/Coinalyze | Time-bucketed series, receive clocks missing; Coinalyze retains only a short intraday window |

Tardis documents free first-of-month samples; continuous other-day access requires suitable API entitlement. Public metadata places BTCUSDT in a broad 2019–2026 symbol envelope and lists 18 incident reports, not yet adjudicated for our interval. That is not a guarantee of every date/type or our account access. CSV omits disconnect markers; capture-health validation may require its native replay alongside relevant quotes. No subscription, key search or provider contact occurred. More detail and primary links: [DATA_PROVIDERS.md](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/DATA_PROVIDERS.md) and [PROVIDER_COVERAGE_CHECK.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/PROVIDER_COVERAGE_CHECK.json).

All Binance-reported messages still omit liquidations discarded by the exchange snapshot. A complete collector archive cannot recover those missing orders. A strategy may use the observable feed, but must not interpret absence as proof of no actual liquidation. [Official Binance connector documentation](https://github.com/binance/binance-futures-connector-python/blob/main/binance/websocket/um_futures/websocket_client.py).

## What must happen before testing

The immediate requirement is access to continuous historical reported-liquidation records with event and receive clocks, plus capture-health/incidents and executable-price evidence. Prefer the same 2022–August 2026 scope to reuse audited prices/funding; any narrower interval is a new comparison contract, not a silent substitute. A user-provided local dataset or a suitable provider entitlement would allow this gate to be audited. Free first-of-month files cannot fill 30 consecutive days of causal threshold history.

Then audit every admitted partition, side/amount and clock semantics, duplicates and gaps, and quotes around legal entry and stressed exits. The old 2/4 bps slippage references are not validated for a liquidation event merely because they worked as prior research assumptions. Freeze accepted event-cost settings before economic outcomes. Finally, implement the exact contract with independent cases for both clocks, dimensions, percentile warmup, stop/anchor conflicts, funding, latency and UTC flattening. Existing brokers do not yet prove this anchor-target/one-bar-delay combination.

The planned 5m/15m comparison is therefore **blocked on data and execution proof, not approved or backtested**. Full rules make the proposal reviewable; they do not replace those gates. If adequate data/access cannot be obtained, reject this route rather than infer liquidation tags from ordinary candles or silently substitute a different contract/venue.

## Proof and exposure

Research selection, input-family clarification and bounded samples are complete. Proposed semantics, full data, stressed execution and economics are not accepted. Runtime source and tests are unchanged; no model training, parameter grid, mutation or new economic evaluation occurred. Previous 810 evaluations remain correlated exposure, including 240 validation replays. No protected September–October 2026 or prospective November 2026–April 2027 market records were downloaded or used for outcomes. Public provider coverage metadata is not market-price access. [protocol.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/protocol.json) freezes the blocked state; [INPUT_IDENTITIES.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/INPUT_IDENTITIES.json) preserves prior inputs/code; [SOURCES.json](C:/Users/Baham/Documents/Nexuz/dove_red/StrategyLab/artifacts/strategy-development/btc-information-phase1-20261028/SOURCES.json) retains source versions and limitations.
