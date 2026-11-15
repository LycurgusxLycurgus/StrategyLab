# Phase 2 outcome: return to research

Campaign `btc-liquidity-20261023`, schedule `systematic_v2`, origin `systematic_native`, operation `create`. Python research target; no discretionary-source replication or Pine delivery was promised.

**No candidate qualified.** The corrected fixed comparison completed all 240 annual economic evaluations: 18 candidates and six breakout controls, five chronological folds, two cost conditions. Every candidate's combined net profit factor is below one. The best observed candidate is **15m / long-only / confirmation plus FVG**, with 265 closed trades and a combined net profit factor of **0.806**. It still fails the frozen research screen. The selected strategy is **none**.

The six context winners below all use the confirmation-plus-FVG approach. “Best” means the least-bad observed fixed approach under the preregistered worst-fold/mean-fold ranking; it does not mean profitable or suitable for deployment.

| Context | Combined net PF | Closed trades | Worst fold return | Qualified |
|---|---:|---:|---:|---|
| 5m long-only | 0.541 | 1,163 | −19.66% | No |
| 5m short-only | 0.632 | 1,146 | −13.56% | No |
| 5m both | 0.599 | 2,137 | −27.21% | No |
| 15m long-only | 0.806 | 265 | −3.09% | No |
| 15m short-only | 0.718 | 284 | −4.43% | No |
| 15m both | 0.730 | 531 | −5.96% | No |

For the best observed candidate, fold returns were **+1.51%, −2.00%, −3.09%, −0.39%, −1.13%** for 2022, 2023, 2024, 2025 and January–August 2026 respectively. Recent stressed returns were **−1.38%** and **−1.45%**. Each fold starts flat with 100,000 USDT; these are separate fold returns, not a continuous compounded equity curve. Results include modeled fees, slippage and signed funding with the disclosed mark proxy/buffer.

The evidence favors 15m over 5m and long-only over short-only/both **within this particular fixed family and ranking**. That is a development comparison, not proof that Bitcoin should generally be traded long-only or that another systematic SMC-like mechanism cannot work. No parameter changes followed inspection of these results.

## Separate evidence verdicts

| Boundary | Verdict | Proof and limit |
|---|---|---|
| Source fidelity | NOT_APPLICABLE | Original mechanical rules, not a replica of a supplied discretionary strategy |
| Indicator/reference semantics | PASS within declared model | 43 independent regression cases cover positive/negative signals, causal prefixes, pending lifecycle, execution, sizing, funding, aggregation, integrity and screening |
| Market data | PASS within declared proxy contract | 56 checksummed original 5m archives; 490,752 valid contiguous rows; 163,584 complete 15m bars; raw audit has zero gaps, duplicates, invalid rows or ordering violations |
| Funding data | PASS within declared proxy contract | Six exact pages, 5,112 events; 3,107 API marks, 1,996 monthly opening-quote proxies, nine daily opening-quote repairs; original sources and repair provenance retained |
| Execution model | PASS for bounded research simulator | Next-open causal decisions, risk/lot limits, adverse stop/gap policy, fees, signed funding, time exits and censored marked equity tested; live venue execution remains UNVERIFIED |
| Economic hypothesis | FAIL / NOT_QUALIFIED | All 18 candidates fail the predeclared screen; all six breakout controls also fail |
| Final untouched test | NOT_RUN | September 1–October 22, 2026 data remains unfetched and unevaluated |
| Pine target | NOT_APPLICABLE | No Pine compilation or parity claim |
| Paper/live graduation | NOT_ELIGIBLE | Failed approach gate; no actual paper adapter, forward reconciliation or live authorization |

## Correction and replay

First independent review found a simulator defect: intrabar funding could be charged after a deterministic opening stop-gap exit. The correction closes that position at the open before processing later funding; funding exactly at the opening timestamp retains the declared carried-position treatment. Eight independent long/short, debit/credit, exact-open/post-open regression subcases cover the fix.

The corrected `comparison-v2` replay contains 240 result payloads identical to their `comparison-v1` counterparts. No production trade received the erroneous post-exit charge, so every reported economic result is unchanged. The original evidence remains preserved and marked as a superseded engine version. Total saved economic evaluations are 480 including this validation replay, with the same 24 fixed contexts and no additional parameter searches or mutations. `cumulative_trials.jsonl` accounts for both runs; `CORRECTION_EVIDENCE.json` records the equality and identity checks.

## Validation and identities

The integrated regression command `python -m unittest app.btc_liquidity_tests` passed **43/43**. Python compilation and scoped `git diff --check` passed. The new research modules use only the standard library and do not alter existing registered engines or runtime APIs.

Root verification found exactly **240 unique trial/year/cost records**, every saved compressed result matching its trial-ledger hash, and every frozen code/protocol/raw JSON identity matching the current files. A production-output check on the 15m long/FVG 2025 fold verified legal signal-to-entry timing, maximum nominal initial risk **0.249995%** of equity, maximum entry exposure **72.57%**, and final-equity reconciliation to trade P&L within **0.000000001 USDT**. No position remained open in that inspected fold. Other folds retain their own complete traces and any censor status.

Raw manifest SHA-256: `49ed1b895b054df0447c99ce2b109c58ff8f7f27e5a0c3be1dbb7b54a708cfe8`. Full code, settings and raw identity hashes are in `runs/comparison-v2/identities.json` and `comparison.json`; individual result hashes are in `trials.jsonl`.

- [Research rules, source criteria, execution assumptions and reproduction commands](RESEARCH.md)
- [Frozen protocol](protocol.json)
- [Complete results and all failed screens](runs/comparison-v2/REPORT.md)
- [Machine-readable comparison](runs/comparison-v2/comparison.json)
- [Corrected-run economic trial ledger](runs/comparison-v2/trials.jsonl)
- [All evaluations, including the original run and validation replay](cumulative_trials.jsonl)
- [Correction and replay verification](CORRECTION_EVIDENCE.json)
- [Raw candle audit](raw/audit.json)
- [Funding coverage](raw/funding_coverage.json)
- [Funding mark provenance](raw/funding_mark_provenance.json)
- [Exact-source daily repair log](raw/mark_price_gap_repairs.json)

## Disposition

**RETURN_TO_PHASE_1.** Preserve the failed approaches and the untouched final window. Phase 3 acceptance, Phase 4 optimization, Phase 5 mutation/final testing and Phase 6 paper graduation are not earned by these results. The next research decision would need a new explicit hypothesis and budget, with these results counted as prior selection exposure. This completed comparison does not authorize an unbounded search until something looks profitable.

## Independent review closure

The first independent review returned FIX for funding after a deterministic opening stop-gap exit. One correction stage added the event-ordering fix and independent regression cases. The fresh terminal review returned **PASS**. Root verification confirmed the accepted run still matches current code, protocol and raw identities. This accepts the research implementation and its negative comparison; economic status remains RETURN_TO_PHASE_1. See [acceptance evidence](ACCEPTANCE.json).
