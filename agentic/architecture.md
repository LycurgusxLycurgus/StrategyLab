# StrategyLab evidence architecture and handoff map

## Research-quality and return-loop correction — 2026-10-29

Current operator/Phase 1/2 contracts supersede earlier smaller-batch readiness
rules prospectively; historical one-candidate campaigns below remain immutable.
The audit at `agentic/research/phase1-phase2-quality-audit-2026-10-29.md` documents
source-to-target transfer, captured-move cost failures, exposure-confounded controls
and correlated trial counts. Root reran 186 existing research-engine tests with
PASS; no new economic campaign, protected-data access or code repair occurred.
One earlier funding-after-gap bug was already corrected with unchanged historical
payloads. Its intermediate correction record retains PENDING, while the later
ACCEPTANCE.json records terminal review PASS; neither record is rewritten here.
Root owns planning/review under the latest explicit user hierarchy; Terra provided
a read-only evidence audit. Root instruction-contract review PASS; two existing
discovery/README checks and local-link/whitespace checks passed alongside the
186 engine tests. No runtime API or test implementation changed. The prior README
archive recovery gap is unchanged and is not part of this acceptance.

## BTC funding-state Phase 2 — 2026-10-28

The user's `continue` authorized implementation and the frozen 90-evaluation
comparison from the funding-state Phase 1 below. Evidence lives in
`artifacts/strategy-development/btc-funding-state-phase2-20261028/PHASE2.md`.
The implementation/evidence verdict is **first root review PASS**, with no
correction stage or extra reviewer under the user's explicit hierarchy. The
economic verdict is **RETURN_TO_PHASE_1: 0/2 candidate contexts qualify**.
No Phase 3 candidate was selected and no additional research/tuning started.

Maintained standalone research modules:

- `app/btc_funding.py`: `FundingExecution` expresses fixed-notional costs and
  sizing without legacy stop-risk fields; `Intent` retains event/source-event,
  observation, decision and fill clocks. `build_event_features` verifies initial
  and contiguous 8h funding slots, causal 180-day midrank, exact tenth-boundary
  ties, 187-day shared warmup and 21-slot lag. `detect` supports the candidate,
  stale control and every eligible continuous-control opportunity. Availability
  uses raw timestamps; slot rounding is only a schedule identity.
- `app/btc_funding_broker.py`: explicit opening funding → time exit → queued
  fill → occupied-decision check → intrabar funding → close/adverse marks.
  Decisions occur at observation end+1ms and fills at the following grid open;
  no end-of-bar position peek. One fixed-quantity long, 10% fee-inclusive entry
  notional, 24-hour hold, no stop/target/day-flat. Exact-open funding belongs to
  the carried position, never a new entrant. Signed subsequent funding and the
  1% adverse payment buffer count. Censored positions include estimated exit
  slippage and fee without a fake trade; adverse marks preserve pre/post funding
  cash lows. Negative cash/nonpositive equity produces `INVALID_EXECUTION` with
  evidence, not an invented liquidation. Exposure integrates opening notional
  × bar-duration days. Entry-week PnL groups by Monday UTC.
- `app/btc_funding_campaign.py`: exact frozen schema/protocol/rules and source/raw
  identity checks, safe unique run IDs, immediate run/cumulative trial records,
  partial-failure evidence and all 90 saved annual payloads. Full-history
  features warm annual folds, but positions and incoming decisions reset.
  Select the continuous control's first opportunity **after annual filtering**.
  `screen_rows` applies absolute/control/concentration gates only after a full
  6-context ×5-fold ×3-cost matrix; invalid candidate or paired-control execution
  blocks qualification. Standard stress is mandatory; severe is diagnostic as
  frozen before results. Controls cannot win. This is a bounded research CLI,
  not a registered Mutation Lab engine or live adapter.
- `app/btc_funding_tests.py`: 42 independently authored cases cover ranks/ties,
  positive low-state rates, warmup/lag/prefix causality, ms availability, 5m/15m
  execution, overnight/weekend holds, occupancy, sizing, funding ownership,
  insolvency ordering, marks/censoring/exposure and campaign gates/identities.

Both contexts have positive base returns in 2022–2024 and pooled net PF above
1.05 (5m 1.244; 15m 1.335), but lose in each recent fold: 5m -1.122%/-1.837%
and 15m -0.099%/-1.477% for 2025/January–August 2026. Both have 70+49 closed
recent trades and pass count/PF/close-drawdown screens. Both fail recent return,
standard stress, stale-control, continuous-long exposure-efficiency and
best-entry-week-removal requirements. Do not promote a positive aggregate over
these failed recent gates. On recent saved fills, 5m raw-price PnL is negative;
15m is slightly positive before slippage but negative after slippage before fees.
These are fixed-fill diagnostics, not zero-cost counterfactual reruns.

`runs/comparison-v1/trades.csv` contains 3,090 closed records, including 1,542
candidate records; `open_positions.csv` separately preserves 30 censored
continuous-benchmark positions. Candidate contexts share 257 distinct funding
triggers; repeated costs/grids are correlated. `RECONCILIATION.json` independently
rebuilds ranks/entry occupancy, raw-price fills and sizing, every owned funding
payment, all cashflows, 5,889,024 close/adverse equity observations, notional-day
denominators, PF, drawdown and entry-week totals. All 59 frozen input identities
remain unchanged. Every modeled execution context is valid; economics fails.
`TEST_RESULTS.json` records **186 tests PASS: 42 new +144 previous**.

Run the bundled Python from the repository root with
`-m unittest app.btc_funding_tests app.btc_flow_tests app.btc_liquidity_tests app.btc_smc_tests app.btc_successor_tests`.
Campaign entry is `-m app.btc_funding_campaign --root artifacts/strategy-development/btc-funding-state-phase2-20261028 --run-id <unique-id>`;
a replay needs authorization and adds 90 exposures. Cumulative economic exposure
is now **1,020**, including 240 earlier validation replays. Root reconciliation
is not a new economic run. All history through August 2026 is exposed screening
evidence; protected prices remain untouched. No new market downloads, training,
optimization, purchases or orders occurred. Settlement receive timing, mark-open
proxies, historical venue filters and live collateral behavior retain their
declared limitations. The future 187-day warmup/final-window permission issue
below remains unresolved and was not exercised by this comparison.

## BTC funding-state Phase 1 and holding-scope revision — 2026-10-28

**Latest user scope:** 5m/15m are execution timeframes. Overnight and intraweek
positions are permitted; the previous same-day-flat requirement no longer
governs new research. The user did not impose a five-day maximum. Earlier
campaigns retain their original intraday rules and immutable failures.

`artifacts/strategy-development/btc-information-reset-phase1-20261028/PHASE1.md`
selects one source-informed native candidate,
`low_percentile_funding_long_24h_v1`, for a future controlled comparison.
Published funding-state evidence is strongest at a one-day horizon, now
eligible under the revised scope. It remains a gross spot-return association
from a single observational paper with overlapping exposed history, not an
independently demonstrated net perpetual edge. No new economic evaluations,
strategy implementation, automated tests, training or orders occurred.

Maintained research artifacts:

- `MACRO_RESEARCH.md` / `MACRO_SOURCES.json`: Terra's primary macro evidence,
  announcement-window versus post-entry distinction, official release data and
  consensus/timing gaps. Macro is deferred, not disproved.
- `MULTIDAY_RESEARCH.md` / `MULTIDAY_SOURCES.json`: Terra's funding, weekly trend
  and hedged carry comparison. Root corrections in `ROOT_REVIEW.json` take
  precedence over provisional notes: weekly holding is eligible; mark history
  is partly exact and partly approximated, rather than wholly missing; root
  cost scenarios supersede illustrative fee arithmetic.
- `sources/funding_2026.pdf`: archived primary paper with SHA256 identity.
  `research_ledger.jsonl` preserves selected/deferred/blocked approaches.
- `DATA_FEASIBILITY.json`: existing `load_funding` revalidated 5,112 events with
  complete 8h slots and 0–31ms timestamp jitter. Marks comprise 3,107 API values,
  1,996 verified 5m mark-open proxies and nine daily repairs. Funding-only
  classification/calendar audits inspect no future returns. After the basic
  180-day warmup there are 551 low-state events, including 113 numerically
  nonnegative rates. Shared 187-day warmup plus nominal non-overlap gives
  2025/2026 capacities of 70/49 per execution grid before censoring/size checks;
  these are not actual backtested trades or independent samples.
- `RULES.md` and `protocol.json`: complete proposed causal decisions and a
  frozen 90-evaluation future matrix; **Phase 2 execution is not authorized by
  the Phase 1 research instruction**. `PHASE2_HANDOFF.md` carries exact future
  implementation/test/review duties and evidence limits. No `app/` source was
  changed. The proposed executor is not implemented or registered.

The candidate ranks each finalized funding rate against `[t-180days,t)`, with
at least 300 events and complete history; midrank <=.10 is a long opportunity.
The exact boundary is `5*(2*less+equal)<=N`. Do not add a numerical-negative
filter or infer a symmetric short rule. Common warmup is 187 days to support a
seven-day stale-state control. Raw timestamp controls availability: first full
execution-bar end after event+1ms, decision end+1ms, first later grid open. A
settlement at 08:00:00.006 models fills at 08:10 on 5m and 08:30 on 15m; receive
latency remains an explicit unmeasured assumption.

Proposed risk is fixed 10% fee-inclusive entry notional, one fixed-quantity
long, 24-hour time exit, no stop/target/day-flat. Suppress occupied decisions
and reject carried-position fill opens; no same-open replacement. This is a
new risk contract, not the old 0.25% stop-risk model or stop-distance guard.
Charge all owned future funding with the accepted 1% adverse payment buffer;
never credit the already-paid trigger settlement. Mark hypothetical adverse
exit slippage/fee without inventing cutoff trades. Adverse intrabar valuation
uses the lower pre/post funding cash value so credits cannot hide earlier lows.
Unsupported solvency/collateral behavior is `INVALID_EXECUTION`, never a
fabricated liquidation fill. Live margin behavior remains uncertified.

Controls are seven-day-old funding classification at the same current
opportunities, and continuous fixed-quantity long BTC perpetual. Both are
descriptive benchmarks with limitations, not randomized causal nulls. The
future matrix is three roles × two grids × five folds × three costs =90 annual
evaluations, two candidate contexts and four controls. Fees remain 6bps/fill;
base slippage 2bps, mandatory standard stress 4bps, required severe sensitivity
20bps. Standard versus severe qualification is a new pre-results decision,
not a reinterpretation of the failed flow campaign. Higher measured execution
costs must reopen mandatory economics. Full absolute/control/concentration
gates are frozen in RULES.md; no parameter or horizon rescue is authorized.

`ROOT_REVIEW.json` accepts Phase 1 information/specification under root review,
with no extra planner/reviewer per user. `ACCEPTANCE.json` records research
readiness only: economics untested, execution specified but not implemented,
modeled data feasible with disclosed proxies, no target parity claim. All
previous source/input identities and 148 preceding campaign artifacts remain
unchanged. Cumulative economic exposure stays 930, including 240 replays.

**Future final-validation dependency:** legacy Nov1 warmup cannot supply the
new 187-day history before reserved Dec1 evaluation. Retaining that start
would require May28 onward funding history, including protected intervening
dates. Do not fetch or redesignate those dates now. A later authorized
frozen-finalist contract must resolve warmup permissions or a genuinely fresh
evaluation schedule. This does not certify or authorize a final test today.

## BTC executed-taker-pressure Phase 2 — 2026-10-28

The user authorized another data source or another way to reach Phase 2.
`artifacts/strategy-development/btc-flow-phase2-20261028/PHASE1.md` freezes a
**new native executed-taker-pressure reversal hypothesis**, distinct from the
still-blocked reported-liquidation proposal below. Additional public provider
research did not establish its continuous 2022–August 2026 USD-M dual-clock
requirement. No new market data, credentials, purchase or account was needed:
verified original five-minute kline quote and taker-buy quote fields supply the
new observable measure. Do not label this measure liquidations or order-book OFI,
or treat it as a replication of the first-ten-second flow paper.

Maintained standalone research flow:

- `app/btc_flow_data.py`: `load_flow` streams the accepted checksum-verified
  monthly archives, joining exact timestamps/OHLC/base volume and validating
  finite nonnegative total/buy/sell base and quote quantities and their average
  prices. `aggregate_flow_15m` sums complete triplets of quote components.
- `app/btc_flow.py`: `build_features` computes signed pressure `2*buy_quote-quote`,
  nearest-rank Q99 over the previous 30 complete UTC days at the same timeframe,
  including healthy zeros and excluding the entire current day. Completed-hour
  ATR uses 20 true ranges and a preceding hourly close. `detect` fades a 60bps
  completed price impulse; the candidate additionally requires strict tail
  pressure in the impulse direction. The price-only control shares warmup,
  stops and timing. Known bar-open anchor, 2ATR stop and all constants are fixed.
- `app/btc_flow_broker.py`: supports 5m/15m, fixed quantity, signal index plus two
  entry (legal after bar end +1ms), actual slipped-fill anchor room at least
  60bps, inherited signal/fill stop-distance guards and sizing, four daily
  entries, no same-open replacement, stop/anchor/time exits, stop-first OHLC,
  funding ownership and marked/adverse equity. Entries must remain on the
  observing date through 22:00 UTC; deadlines are the earlier of two hours and
  23:45 UTC. Favorable anchor gaps receive no price improvement. Uncertain
  intrabar funding credits are omitted and debits charged. Intrabar exit clocks
  are candle-resolution bounds, not measured fills. Numeric boundary comparisons
  use price-scaled 1e-12 tolerance; stop tick quotients use the accepted 1e-9
  rounding epsilon. This bounded broker is not a live adapter or a new registered
  Mutation Lab runtime.
- `app/btc_flow_campaign.py`: validates the exact frozen protocol SHA, required
  source/raw metadata identities and authorization hashes. It saves features,
  detectors and all 120 annual trade/state payloads, updates run/cumulative
  ledgers after every evaluation, preserves partial failure evidence and refuses
  run-ID overwrite. Annual accounts reset flat; prior history warms features
  only. `screen_rows` applies the inherited gates plus a strict summed-recent-base
  improvement over the same-frame/direction price-only control; controls cannot
  qualify. That comparison is descriptive, not exposure-matched causality.
- `app/btc_flow_tests.py`: 32 independently authored tests cover causal features,
  aggregation, source alignment, long/short and 5m/15m execution, equality cases,
  timing, costs, funding, cap/replacement, marking/censoring and campaign gates.

`protocol.json` freezes six candidate and six control contexts, five folds and
two costs: 120 evaluations. Base costs are 6bps fee +2bps slippage per fill;
severe stress uses 6+20bps per fill. The inherited K=.002 admission reference
remains separate from severe stress. These and OHLC/availability/venue settings
are research assumptions, not quote-calibrated execution guarantees.

`PHASE2.md`, `ACCEPTANCE.json` and `ROOT_REVIEW.json` accept the implementation
and evidence with **first root review PASS, no correction stage, no extra
reviewer**, following the user's explicit hierarchy. The economic verdict is
**RETURN_TO_PHASE_1, 0/6 qualifying candidate contexts**. Every candidate loses
in both 2025 and January–August 2026 and fails pooled net PF and severe stress.
The flow filter reduces summed recent losses versus its matched control in all
six contexts but creates no profitable context. Both-direction raw-price PnL on
the saved five-fold base fills is negative even before slippage/fees; this is a
fixed-fill diagnostic, not a zero-cost-strategy rerun. Do not automatically tune
or invert this failed family.

`runs/comparison-v1/trades.csv` exposes 19,695 closed records across all contexts
and costs, including 6,148 candidate records; overlaps are not independent
events. `RECONCILIATION.json` checks every payload hash, matrix/ledger coverage,
trade clocks/intraday boundaries, quantity/risk/cost arithmetic, funding, PnL,
cash equity and recomputed drawdown. All 40 frozen input identities and all 27
prior information-research artifacts remain unchanged. All positions finish
flat. `TEST_RESULTS.json` records **144 tests PASS: 32 new +112 previous**.

Run tests from the repository root with the bundled Python runtime and
`-m unittest app.btc_flow_tests app.btc_liquidity_tests app.btc_smc_tests app.btc_successor_tests`.
The local `.venv` references an absent Python installation. Campaign entry is
`-m app.btc_flow_campaign --root artifacts/strategy-development/btc-flow-phase2-20261028 --run-id <unique-id>`;
replays require authorization and add 120 economic exposures. The recorded
cumulative total is now 930 correlated evaluations, including 240 earlier
validation replays. All 2022–August 2026 history is exposed development evidence;
protected windows remain untouched. No training, parameter search, Phase 3
implementation or orders occurred. No further campaign started automatically.

## BTC information-driven Phase 1 — 2026-10-28

`artifacts/strategy-development/btc-information-phase1-20261028/PHASE1.md`
records the new information qualification and the user's later constraint:
**5m and 15m execution, strictly intraday, longer holds permitted**. Root makes
the UTC-day convention explicit. The selected research prototype is observed
liquidation-dislocation reversal, with a designed two-hour maximum and last
entry at 22:00 UTC. `CANDIDATE_PROPOSAL.json` defines the original, untested
rules, including prior-30-complete-day Q99 reported net pressure, 60bps impulse
and remaining anchor room, one complete execution-bar latency, 2ATR stop,
known pre-impulse-open target and mandatory UTC flattening. These additions are
preregistered feasibility choices, not source replication or profitable rules.
The proposal and paired price-only control imply 120 possible future evaluations;
**zero are currently authorized or run**. `protocol.json` keeps Phase 2 BLOCKED
on continuous event/capture-health access and event-conditioned execution proof.

Research artifacts and measured boundaries:

- `RESEARCH.md` / `SOURCES.json`: Terra's terminal source/provider work integrated
  with root checks. BTC-specific quarter-hour-flow contrasts are small relative
  to costs; the source actually uses aggregate trades, so that input family is
  now identified. An industry matched-event liquidation study motivates only a
  low-confidence reversal hypothesis; its group contrast is not trade PnL.
- `sample/`: preselected 2022-01-01 official aggTrades ZIP, companion checksum,
  derived ten-second windows, and a free Tardis reported-liquidation gzip.
  `SAMPLE_AUDIT.json` retains the failed exact candle-bin parity check;
  `TIMESTAMP_RECONCILIATION.json` finds daily volume totals exact but 43/288
  five-minute bins differ. Do not shift records to force agreement. The tape has
  997,179 groups, no aggregate-ID gaps and 96 nonempty first-ten-second windows.
- `LIQUIDATION_SAMPLE_AUDIT.json`: 1,052 valid reported records with exchange and
  receive microsecond clocks, all order IDs absent; median observed lag 20.05ms,
  maximum 549.60ms. One-day timing is not a general latency guarantee. Tardis
  HEAD returned 404 but bounded GET succeeded; preserve that distinction.
- `catalog/`, `ARCHIVE_CATALOG.json`, `FETCH_PLAN.json`, `FETCH_RESULTS.json`:
  2022 trade metadata has 365 ZIPs totaling 7.51GB compressed. Collection stopped
  after one trade-day sample; a second small liquidation sample and provider
  metadata bring stored fetched payloads to 14,170,658 bytes, under 25MiB.
  No sample outcomes/PnL were analyzed and no protected market dates fetched.
- `LOCAL_DATA_INVENTORY.json`: inspected the workspace/SQLite dataset registry
  and CSV schemas. The remembered `ds_d14d74e36d0d.csv` is registered as 303,723
  15m OHLCV rows. Current `binance_public` loader uses spot `/api/v3/klines`;
  old normalized candles cannot be relabeled as verified perpetual events.
  Accepted USD-M candle/turnover/funding archives remain reusable. No prior
  continuous liquidation capture was found in that inspected scope.
- `DATA_PROVIDERS.md` / `PROVIDER_COVERAGE_CHECK.json`: Tardis is strongest
  documented dual-clock lead; metadata lists BTCUSDT liquidation and quote/BBO
  types with a broad 2019–2026 envelope and 18 unadjudicated incidents. Neither
  complete date/type coverage nor user entitlement is proved. First-of-month
  samples are free; continuous other-day access needs suitable entitlement.
  Official current USD-M daily listing lacks liquidationSnapshot and the 2025
  prefix is empty. CoinAPI remains unverified; Kaiko starts too late for the
  full requested interval; CoinGlass/Coinalyze aggregates lack receive clocks.
- `QUALIFICATION_HANDOFF.md`: exact next data/cost prerequisites, proposal,
  candidate/control matrix, future independent-case duties and role routing.
  Current informational review PASS is in `ROOT_REVIEW.json`; it does not accept
  the candidate or new execution engine. No runtime/test source changed.

The feature measures **reported snapshot pressure**, not complete liquidation
notional, institutional identity or unique orders. Binance publishes only the
latest symbol liquidation per second. Use the later event/receive clock for
availability, retain capture order and distinguish known healthy zero-message
intervals from missing capture. Provider CSV omits disconnect markers; capture
health may need native replay/incident evidence. Event stress costs need quotes
or an independently justified adverse contract. Existing fixed-R/no-target
brokers do not prove the explicit anchor-target/one-bar-delay combination.

This section records the original liquidation route, whose advancement remains
blocked awaiting continuous records/access and data/execution qualification.
Its frozen artifacts preserve recovery state. The later executed-taker-flow
campaign above does not unblock or relabel this proposal. Exposure was 810 at
this original research checkpoint; the new campaign records the later total.
No model training, purchase, orders or protected-window evaluation occurred in
this research. All previous exposed/protected-window constraints remain.

## BTC Phase 1 reassessment — 2026-10-28

`artifacts/strategy-development/btc-research-reset-phase1-20261028/PHASE1.md`
answers the post-Phase-2 direction decision: retire the tested SMC/liquidity
emulations and exact three successor rules from the current research budget;
prioritize new information research rather than threshold, clock or exit tweaks.
This is a practical allocation decision, not universal falsification of SMC,
reversal or trend families. `protocol.json` records **STOP**, zero accepted
complete candidates, an empty economic matrix and no Phase 2 authorization.
Research assessment is complete; conditional leads are not implemented strategies.
`ROOT_REVIEW.json` records root informational review PASS under the user's
no-extra-reviewer override, with no correction stage. No runtime/test source changed.

Maintained evidence in that campaign directory:

- `DIAGNOSIS.json`: attribution from all nine accepted base-context saved fills;
  both-direction mean raw price moves are -2.975/+0.540/+1.952 bps for
  shock/noise/channel, versus nominal 16/20 bps round-trip base/stress friction.
  Median initial stops are 179.62/149.50/160.45 bps and median holds 120/60/360
  minutes. These are correlated saved-fill diagnostics, not a zero-cost replay,
  filter search, new exit experiment or estimate of a prospective strategy.
- `DATA_FEASIBILITY.json`: all 490,752 rows across 56 checksum-verified local
  archives pass taker-buy base/quote, trade count, side-volume, unit and timestamp
  checks. The available 5m signed share `(2*buy_base-base)/base`, when base>0,
  becomes usable after bar close. This is neither L2 order-flow imbalance nor
  a reconstruction of ten-second opening flow or trader identity.
- `RESEARCH.md` and `SOURCES.json`: Terra's primary-source assessment, integrated
  with root verification; 13 source records, current versions/limitations and
  explicit source-versus-design distinctions. No new PDF-byte archives or hashes
  are claimed. `research_ledger.jsonl` retains rejected/conditional directions;
  `INPUT_IDENTITIES.json` preserves the basis and prior source/code evidence.
- `NEXT_RESEARCH_HANDOFF.md`: future Phase 1 information-set qualification;
  complete predictor/entry/exit/data timing and finite comparison contracts must
  precede any Phase 2. No market-data acquisition, training or evaluation follows
  automatically from the handoff.

Root research priority is aggressive trade-pressure information. The source's
ten-second feature requires finer records than the accepted dataset; the verified
five-minute substitute is a different hypothesis with unresolved sign/horizon and
cost magnitude. Settled-funding research is secondary: source shorter-horizon
gross spot effects are below current nominal costs, strongest evidence is at 24h,
and settled records are not pre-settlement forecasts. Cost-aware ML forecasting
is deferred: the inspected paper calls its sample Binance USD-M futures beginning
in 2017, preceding Binance's 2019 launch; actual instrument lineage is unresolved,
with no fabrication inference. The existing learned-strategy roadmap remains
plan-only. Published predictive accuracy is not executable net-return evidence.

All 150 prior Phase 2 manifest entries and current/prior input/code identities
were verified unchanged. This reassessment adds zero economic evaluations,
parameter searches, mutations or market-data downloads; cumulative local exposure
remains 810, including 240 validation replays, across 42 candidate contexts and
15 controls. All earlier exposed-window and protected/future-window constraints
below remain binding. No new tests are claimed for unimplemented research leads.

## BTC successor Phase 2 — 2026-10-28

`artifacts/strategy-development/btc-successor-phase2-20261028/PHASE2.md`
records the completed fixed comparison: **RETURN_TO_PHASE_1**, zero of nine
candidate contexts qualified, no Phase 3 entrant. `runs/comparison-v1/` contains
120 real evaluations (nine candidate plus three control contexts, five reset
annual folds, base/stress), full broker payloads, causal feature/detector streams,
trial/identity ledgers, `ECONOMIC_DETAILS.json`, and `trades.csv`. The 62,090 closed
trade rows span correlated contexts/costs, not independent market samples.
`ROOT_REVIEW.json` records first root review PASS under the user's no-extra-reviewer
override, no correction stage; implementation acceptance and economic failure are
separate. `VALIDATION.json` records 112 passing tests (42 successor + 70 preserved).
`ROOT_ARTIFACT_RECONCILIATION.json` reconciles every payload's identities,
raw/terminal and fill balances, funding, timing/risk and marked accounting.

Maintained bounded research path, separate from prior immutable engines:

- `app/btc_successor.py`: completed UTC hourly/two-hour features, prior-only shock
  sample SD, 14 immediately preceding complete-day noise means, exact quote/base
  session VWAP, close-only channel, raw intents and fixed stress cost admission.
- `app/btc_successor_data.py`: verified existing archive-member/checksum helpers;
  original row-7 quote turnover joins exact row timestamps and base volume.
- `app/btc_successor_broker.py`: no-target successor OHLC adapter; exact-open
  carried funding, prior-close amendment activation, stop-gap priority, queued or
  timed exits, then entry only when previously flat. Intrabar stop uncertainty
  charges funding debits and omits credits; exact intrabar stop time is unknown
  and represented by a bar-end proxy. Fixed quantity, four UTC entries maximum,
  cost admission at signal and adverse slipped fill, cutoff marked/censored.
- `app/btc_successor_campaign.py`: validates hash-frozen Phase 2 administration
  and preserved Phase 1/prior inputs, reuses local audited loaders, freezes full
  code/data identities, records each economic evaluation immediately, and rejects
  incomplete coverage before ranking. Controls cannot qualify; exact eligible
  ties resolve lexicographically after worst/mean fold returns. Run IDs cannot
  overwrite evidence. Paths assume execution from the repository root.
- `app/btc_successor_tests.py`: independent constructed aggregation, estimator,
  turnover, detector, broker and campaign cases. Sparse runner-spy metrics prove
  orchestration only and are not economic evidence.

Timing constraints belong to those files: an unfinished hour retains the latest
completed ATR; partial initial sessions have unavailable VWAP; flat entry channels
are disabled but their midpoint remains valid for an existing trail. Compare the
closing price with the **unrounded** proposed trail to queue a next-open exit,
then retain rounded stop evidence; amendments never protect an earlier wick.
Fold decisions belong to observing bar opens inside the fold; no prior-year
intent transfers, and last-bar intents without an in-fold fill are censored.

The frozen hypotheses remain two-hour shock reversal, UTC noise momentum and
24-hour close-channel continuation. All nine contexts lost in 2025; eight lost
in January–August 2026. Aggregate base net PF ranges 0.567–0.748 versus the 1.05
screen. In both-direction saved-fill attribution, shock loses even before modeled
slippage/fees; noise and channel show modest raw-price profits erased by slippage
before fees. This algebra is not a zero-cost strategy replay. A wider initial
stop-cost guard cannot ensure that timed/trailing exits capture sufficient movement.

No tuning, mutation, Phase 3 baseline, protected/future data fetch or orders occurred.
Historical screening remains exposed. This adds 120 evaluations to the prior 690
(including 240 validation replays), yielding 810; earlier engines/artifacts remain
unchanged. Future research needs a new Phase 1 contract. All prior protected-window
constraints below remain binding.

Validation: use the bundled interpreter documented in `PHASE2.md` with
`-m unittest app.btc_successor_tests app.btc_smc_tests app.btc_liquidity_tests`.
Saved comparison command:
`-m app.btc_successor_campaign --root artifacts/strategy-development/btc-successor-phase2-20261028 --run-id NEW_UNIQUE_ID`;
any separately authorized replay must use a new ID and count toward exposure.

## BTC successor Phase 1 — 2026-10-28

`artifacts/strategy-development/btc-successor-phase1-20261028/` is the accepted
**research/specification handoff**, not implemented successor strategy code.
`PHASE1.md` owns the complete rules and failure-driven selection;
`protocol.json` freezes nine candidate contexts, three fixed-clock benchmark
contexts, five historical folds and two costs (120 planned evaluations, zero run).
The three distinct predictors are two-hour shock reversal, UTC same-clock
noise-area momentum, and a 24-hour channel of completed hourly closes.
`PHASE2_HANDOFF.md` records implementation, independent-case and review duties;
`ACCEPTANCE.json` records `PASS_TO_PHASE_2` with semantic/execution/economic
successor evidence explicitly not implemented or evaluated. Root performed the
research review under the user's override; Phase 1 spawned no workers and changed
no runtime source or tests. Original research PDFs and exact versions/hashes live
under `sources/` and `SOURCES.json`; no third-party code was copied or executed.

`LESSONS.json` attributes saved closed-trade outcomes without rerunning models.
The prior active both-direction models had 20-44 bps median initial stops against
approximately 16 bps base round-trip costs; all four BOS/Turtle both-direction
contexts lost after slippage before fees. Removing slippage algebraically from
fixed saved fills is not a zero-cost counterfactual strategy replay. Silver Bullet
remained sample-deficient. The new common admission rule rejects, rather than
widens, stops when estimated stress friction exceeds 25% of initial stop distance;
this does not establish an edge or guarantee sufficient realized price movement.

`QUOTE_VOLUME_FEASIBILITY.json` verifies all 490,752 raw rows and 56 archive
identities/checksums: the original 5m files contain quote turnover as well as base
volume, with 55 consistent zero/zero-volume bars. A future noise model can use
session sum(quote)/sum(base) instead of silently substituting HLC3; positive
cumulative base volume, verified timestamps and completed-bar availability are
required. This column is not in the existing `Candle` interface.

The accepted liquidity simulator's fixed-R targets cannot represent the frozen
absent-target, timed/queued exits and delayed midpoint amendments unchanged.
Phase 2 requires a small independently validated successor execution adapter and
turnover/aggregate checks while preserving both previous accepted research engines.
No such adapter exists from this Phase 1. Keep prior costs and qualification gates;
do not advance a control or least-losing candidate. Historical 2022-August 2026
windows are already exposed development/screening data. Preserve prior protected
September-October data; additionally reserve November 2026 for future warmup only
and December 1, 2026-May 1, 2027 exclusive for prospective final evaluation. Even
warmup cannot be fetched before a separately authorized frozen-finalist contract.
This reservation creates no collection, automation, final test or trading authority.

## BTC SMC-inspired comparison — 2026-10-28

`app/btc_smc.py` owns three independently authored, causal systematic emulations:
confirmed two-left/two-right BOS with later order-block rejection, New York AM
range sweep/displacement/FVG rejection, and age-qualified next-bar Turtle Soup
+1 reclaim. `SmcParameters` and `detect` return the existing `Signal` contract
and closed-bar event ledgers. Prior ATR excludes the current candle and becomes
available after its own 120-minute history, independently of the control's
six-hour range. Silver Bullet supports 5m only and uses `America/New_York` IANA
timezone data; entries must become known strictly before 11:00 local. The other
two models support 5m/15m. Detection remains independent of portfolio state;
explicit rejection, invalidation, expiry, replacement and session-end events
balance the detector lifecycle. These are designed emulations, not accepted
discretionary-source replicas or evidence of institutional orders.

`app/btc_smc_campaign.py` owns the fixed 15-candidate-context/six-control
comparison. It reuses the unchanged, previously accepted liquidity broker,
audited data loaders and selection helpers. Its supported orders are next-open
market proxies, 2R gross-price targets and 180-minute maximum holds, with 0.25%
nominal modeled stop risk, 1x entry exposure and declared fees/slippage/funding.
Annual portfolios reset and censor open risk. The runner accepts only its frozen
protocol, excludes September 2026 onward, preserves run IDs, records code/data
identities, and appends completed evaluations to both run and cumulative ledgers.
It is isolated research, without UI/Mutation Lab registration or paper/live/Pine
integration. No optimization or workflow gate is bypassed.

The authoritative rule/adaptation record and numeric protocol live at
`artifacts/strategy-development/btc-smc-20261028/{STRATEGY.md,protocol.json}`.
`PHASE_REPORT.md`, `ACCEPTANCE.json`, `DATA_AUDIT.json`, `VERIFICATION.json` and
`runs/comparison-v1/` retain current acceptance, all negative results and exact
identities. All 210 fixed annual/cost evaluations completed; **all 15 candidate
contexts failed qualification**. Short-only Silver Bullet's PF 1.467 had just
five trades and failed sample/recent-period gates. There is no selected baseline;
the economic status is `RETURN_TO_PHASE_1_NOT_QUALIFIED`, with zero parameter
searches or mutations. This adds to the previous campaign's selection exposure;
reused development windows are not a pristine final holdout.

`app/btc_smc_tests.py` owns 27 independent constructed detector/orchestration
tests; run with the existing 43 broker/data cases using
`python -m unittest app.btc_smc_tests app.btc_liquidity_tests` (70 passed).
Its campaign mock proves orchestration, not economics. Actual run verification
checked every result hash, trial/cumulative identities, detector lifecycle totals
and saved trade timing. Root performed review under the user's explicit override;
no independent reviewer was used. `STRATEGY.md` records the verified bundled
interpreter command because the old local virtualenv remains unusable. Reproduce
with `python -m app.btc_smc_campaign --run-id <new-id>`; a replay is additional
recorded exposure, not a new independent trial. No forward profitability,
statistical significance, exact broker execution or trading eligibility is implied.

## BTC liquidity-excursion research vertical — 2026-10-23

`app/btc_liquidity.py` is an isolated, standard-library Python reference for
fixed liquidity-reclaim/local-break/FVG prototypes and a breakout control.
`indicators` excludes the current candle; `detect` owns setup lifecycle independently
of portfolio state; `simulate` owns next-open intents, one-position concurrency,
risk/lot constraints, adverse OHLC/gap execution, signed funding and censored
mark-to-market equity. A deterministic opening stop-gap closes before later
funding in that candle; exact-open funding retains the carried-position policy.
Independent long/short debit/credit cases protect this event ordering.
This research engine is **not registered with Mutation Lab**
and does not bypass its baseline-backed optimization/child authorization gates.

`app/btc_liquidity_data.py` downloads and verifies Binance USD-M BTCUSDT public
archives and exact funding pages. Its fixed development range is January 2022
through August 2026: 490,752 original 5m bars, 163,584 complete UTC 15m aggregates,
and 5,112 funding events. Historical blank API funding marks use checksummed
mark-price candle opening quotes; nine missing monthly quotes are recovered from
official daily files for 2022-07-31, 2022-10-02 and 2023-02-24, with retained
originals and row-level provenance. These are disclosed proxies, not exact
settlement-price proof. The campaign applies a 1% adverse funding-payment buffer.

`app/btc_liquidity_campaign.py` executes the preregistered fixed comparison and
stores immutable run directories, full detector/broker/equity traces, hashes,
trial ledger, screening failures and a report. Its protocol and research rationale
live at `artifacts/strategy-development/btc-liquidity-20261023/{protocol.json,RESEARCH.md}`;
the results are under `runs/`. Eighteen candidate contexts and six controls each
run five chronological annual folds at two cost settings. Reserved September 1
through October 22, 2026 data must remain unfetched until a qualified finalist and
final-test contract freeze. A failed approach screen returns to Phase 1; research
comparisons do not establish a deployable winner or paper/live permission.

`app/btc_liquidity_tests.py` owns independent constructed signal, causality,
execution, funding, sizing, source-integrity, aggregation and selection cases.
Run `python -m unittest app.btc_liquidity_tests`; reproduce a comparison with
`python -m app.btc_liquidity_campaign --run-id <new-id>` after the documented
download command. These modules use no third-party Python packages. The local
`.venv` currently points to a missing interpreter; use a working Python 3.12+
(the Codex bundled interpreter was verified) rather than claiming that venv works.
No Pine target, UI integration, live adapter or forward paper evidence is implied.

Completed evidence: `runs/comparison-v2` is the accepted corrected comparison;
43 regression tests and terminal independent review passed. All 18 candidates
failed the economic screen; best observed was 15m confirmation-plus-FVG long-only
(net PF 0.806 across 265 closed trades). `PHASE_REPORT.md` and `ACCEPTANCE.json`
record RETURN_TO_PHASE_1, not deployment eligibility. All 240 replay payloads
matched the original run; the cumulative ledger retains 480 evaluations including
that validation replay, with no additional parameter/mutation trials.

Research-only follow-up: `agentic/research/smc-mechanical-shortlist-2026-10-23.md`
records three proposed model families and targeted source/license/timing audits:
BOS/order-block pullback, Silver Bullet AM reversal, and age-qualified Turtle Soup
+1. That dated shortlist remains a research artifact, not an implementation or
economic ranking. The new October 28 creation request authorized the separate
explicit emulation/comparison above; its failed screen does not alter earlier
source-fidelity or SmartMoney proof obligations.

Status: durable project map; reference-first runtime accepted 2026-10-17;
systematic_v2 prompt revamp dated 2026-10-23 remains under validation in
agentic/analysis.md until its archive/review obligations close.
The reference-first contract is specified in
`agentic/reference-first-migration-plan.md`. New API intake defaults to
`reference_v1`; existing versions and direct callers without a selector retain
`legacy_pine_v1`. Python2Pine is the public workflow name; internal Pine2Python
package paths and existing API routes remain compatibility interfaces. This document is the compact recovery
entry point for the whole repository. The detailed, future-model-facing issue
register and proof obligations live in
`STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`; this map records its ownership, flow,
maintained files, durable lessons, and current limits. Neither document
reconstructs the deleted conversation verbatim or claims that SmartMoney-4 is
profitable or TradingView-accepted.

The plan's 2026-10-13 refinement separates strategy origin
(`systematic_native`, `discretionary_origin`, component-classified `hybrid`)
from development operation (`create`, `replicate`, `translate`, `improve`).
These are provenance/specification responsibilities inside the existing
workflow versions. Both origins converge on one reference/execution/evidence
pipeline. Translation records interpretations, operational formalizations and
adaptations; reference semantic acceptance and source fidelity have separate
evidence. A selected proxy can be correct against its own specification without
proving exact discretionary-source equivalence. `app/reference_evidence.py`
enforces these metadata and gate distinctions; bounded MA and pivot/BOS fixtures
exercise the common runtime. This is not an arbitrary-strategy translator.

## Scope and current decision

StrategyLab remains the system of record for source authority, frozen parents,
criteria, datasets, phase state, Python engines, mutations, economic evaluation
and promotion. Pine2Python is an embedded evidence instrument: it parses Pine,
reports supported capabilities, executes only its bounded supported subset,
generates deterministic proof artifacts and standard traces, and compares
caller-owned traces. It does not own StrategyLab lineage, optimization,
mutation, promotion or market-data acquisition. TradingView remains authoritative
for official compilation, feed/runtime behavior, drawings, realtime/replay
behavior and human acceptance.

The active SmartMoney-4 artifact is the registered v6.3 coverage candidate
`pvr_362b3c72c6d2e797c46a`, based on the exact source hash recorded in the
unresolved-proof register. Its current evidence is source-accepted,
parse-complete and statically reviewed, with
`TRADINGVIEW_REVIEW_REQUIRED`; its local runtime is unavailable because the
analysis records `request.*` as `REQUEST_RUNTIME_UNVERIFIED`. The v6.3 line
keeps 71% as the coverage-oriented default (75% selectable) and ledger-backed
history for pending, missed and open records, but these are not claims of
official TradingView acceptance, Python parity, profitability or production
readiness. PF and win rate cannot establish source/indicator correctness; new
research may assess net-economic evidence under the active campaign contract.

The authoritative detailed status, issue IDs, evidence locators and reopening
conditions are maintained in `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`.

## Project memory and maintained flow

The repository has one instruction file: `AGENTS.md`. All phase prompts and the
embedded service use it. The old service-local instruction file was consolidated
into that root file and is removed as part of this recovery change.

The active campaign schedule, **systematic_v2** (2026-10-23), is:

```text
1 research / distinct complete shortlist -> 2 controlled candidate comparison
  -> 3 qualifying candidate Python base
  -> 4 parameter optimization -> 5 unified mutation + reoptimization
  -> one frozen finalist / once-only final holdout / required target acceptance
  -> 6 paper trading -> GRADUATED_FOR_LIVE_REVIEW | NOT_GRADUATED | BLOCKED
```

The schedule is document-level coordination, not a new runtime workflow enum.
Existing `reference_v1` and `legacy_pine_v1` APIs/stored versions remain unchanged.
The operator owns shared evidence and routing; six standalone prompts own phase
deliverables. Phase 1 first classifies the requested approach, then investigates
systematic sources or performs discretionary transformation research followed by
complete-formulation assessment. Every initial or return attempt must prepare at
least three fresh complete test-ready hypotheses (target 3–4); a meaningful
revision needs failure-specific new causal predictions, not minor threshold/filter
changes. Fewer than three supported candidates means INCOMPLETE/BLOCKED; no batch
is padded or promoted on count alone. Translation categories and source fidelity remain explicit. Every
trading decision must have a causal rule before testing, with no hidden discretion.
Phase 1 is research-only by default and explicitly distinguishes specifications
from tested trades, signal validation and economic acceptance. A new batch/protocol
needs human testing approval; explicitly approved bounded research-and-test work
executes both stages with a visible transition, not an unexplained readiness stop.
Phase 2 validates measurement, signal increment and full-strategy economics
separately, using predeclared matched controls and uncertainty before ranking a
preregistered bounded asset/timeframe/direction matrix. Unspecified settings need
justification before outcomes. Absolute advancement gates precede
results; no qualifying candidate returns evidence and questions to research, not
a least-losing winner. Its failure report proposes at least three fresh candidates,
chooses new mechanisms/meaningful revisions/mix from the failure evidence, and
states that new-batch testing requires approval. Invalid proxies are vetoed;
noise claims require adequate scoped tests, inconclusive evidence is not noise,
and promising/supported components remain research evidence even when their
wrapper fails. Phase 3 inherits exact qualifying rules, contexts, proof,
provenance and trial accounting. Active prompts/handoffs contain no anchoring
examples; strategy-specific evidence elsewhere is not a default candidate list.

The candidate-comparison prompt correction passed independent review on
2026-10-23. Existing production prompt-discovery and README-link tests passed
(two tests), changed-document local links and diff checks passed. No runtime,
workflow enum or test implementation changed. This acceptance does not close the
separately recorded pre-revamp README archive recovery gap.

Raw-data audit, independent positive/negative cases, causal reference and supported
execution precede economic selection. Phase 3 saves a fixed baseline; Phases 4–5
preserve existing baseline-backed search/child authorizations. Selection uses
development evidence only; final holdout is reserved before trials and consumed
once after one finalist freezes. Pine is optional and late; Basic-compatible
sampled corroboration cannot establish whole-performance parity. Phase 6 blocks
without a real paper adapter; graduation never authorizes live orders.

The previous 0/1/1.5/2/2.5/3/4/5/6 reference schedule and Pine-first
3.1/4.1/4.2/4.3 schedule are historical. Exact pre-revamp documents and SHA-256
manifest live under `agents/archive/2026-10-23-pre-systematic-v2/`.
Do not relabel their evidence silently; map any continued campaign explicitly.

Origin, operation, transformation provenance and separate source-fidelity/reference
verdicts remain binding. Mixed-origin metadata does not imply learned policy.
Future discretionary-origin decision-model and learned/social research is plan
only in `agents/plans/discretionary_and_blackbox_roadmap.md`; no model integration,
training, collector or execution adapter was added by this prompt revamp.
Current SmartMoney-4 proof statuses and unresolved boundaries are unchanged.

### Maintained file tree

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Single repository instruction; project constraints are maintained here in architecture. |
| `agentic/reference-first-migration-plan.md` | Historical migration rationale and runtime compatibility contracts; active schedule lives in operator. |
| `app/reference.py` | Registered MA/pivot detectors, causal ledger, shared next-open broker, ledger-derived casebook. |
| `app/reference_evidence.py` | Provenance, independent semantic cases, content-verified evidence, baseline/search/child/target gates. |
| `app/reference_tests.py`, `agentic/testscripts/reference_vertical.py` | Focused contracts and isolated two-consumer demonstration. |
| `PINE2PYTHON_INTEGRATION_REPORT.md` | Historical integration architecture and validation record. |
| `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` | Current recoverable context, issue ledger, root-proof bundles, non-proof and handoff. |
| `agents/translation and generation/agents/codex_phase_operator.md` | Active systematic_v2 six-phase routing, evidence, chronology and promotion rules. |
| `agents/translation and generation/whitebox/*.md` | Exactly six active standalone prompts, discovered nonrecursively by MutationLabService.list_prompts. |
| `agents/docs/universal_mutation_constitution.md` | Parameter/structural-change boundaries and unified Phase 5 mutation guardrails. |
| `agents/plans/discretionary_and_blackbox_roadmap.md` | Future-only decision-model/CLEF and learned/social experiments, taxonomy and primary sources. |
| `agents/archive/2026-10-23-pre-systematic-v2/` | 24-record original manifest; 23 snapshots verified, archived README collision unresolved; ARCHIVE_README.md recovery guide; outside active discovery. |
| `app/workflow_tests.py` | Production prompt-discovery and recoverable archive regression checks. |
| `services/pine2python/` | Typed local/HTTP analysis, bounded runtime, proofs, traces and parity boundary. |
| `app/`, `strategies/` | StrategyLab API, engines, storage, UI and parent definitions. |
| `pre-strategies/` | Inspectable source and immutable source-derived Pine candidates. |
| `artifacts/strategy-development/` | Strategy lineage, criteria, proof, review and phase evidence. |

### Reference runtime and evidence boundary

`BacktestEngine.run` dispatches explicit `reference_v1` to the registered
`reference_ma_cross_v1` or `reference_pivot_bos_v1` consumer. Both share one
decision-only execution driver: bar timestamps denote opens; decisions use
closed bars; earliest entry is next open; fixed quantity, static decision-time
ATR stop, optional R target, adverse stop-first ambiguity and censored cutoff
are explicit in `EXECUTION_CONTRACT`. Fill-aware feedback is unsupported.
Selecting that exact contract also declares numeric execution defaults (including
quantity, ATR risk, capital, costs and disabled target); explicit parameters
override those disclosed values. They are not inferred from strategy profit.
Ledger collection cannot change decisions or economics; the HTML casebook
renders saved trace/ledger, not another detector. Expandable rows expose the
complete saved event, including rule/state/lifecycle and evidence references.

`DataService` audits before normalization and records a per-dataset raw-quality
sidecar with raw and normalized hashes. Missing historical raw evidence remains
unverified unless an explicit normalized-only limitation is accepted; stale or
blocked audits reject acceptance. Parity rejects duplicate keys and absent
required fields rather than overwriting or comparing two missing values.

`Repository.workflow_evidence` is additive to existing databases. Immutable
JSON/HTML artifacts are checked against actual file bytes and current
spec/source/code/dataset/execution dependencies before reuse. `MutationLabService`
guards runs, queued optimization, proposals, saves and promotion; UI display is
not the enforcement boundary. Independent cases precede a fixed baseline;
search additionally needs a declared objective, parameter domains and a frozen
train/holdout boundary. Reference search sees only bars closed by train_end.
`objective_metric` defaults to `existing_score_v1`; explicit net_pnl/profit_factor
maximize and max_equity_drawdown_pct minimizes within the existing optimizer.
Children revalidate; parent evidence is not copied as child PASS.
Authorization compares effective values across parent/child parameter unions,
including omitted keys: `effective_parameters` is shared with reference runtime.
Removing an explicit value cannot bypass authorization by selecting a default.
Legacy offline
hybrid trade-filter experiments reject reference versions because they lack a
causal reference adapter. Legacy behavior otherwise remains separate.

Semantic, data, execution, economic, target, platform and operational statuses
remain independent. `qualified_reference` means declared economic criteria, not
production readiness. Native replication requires independently adjudicated
source-oracle cases tied to original source bytes; proxy tests and profitable
runs cannot manufacture source fidelity. The bounded late MA Pine adapter uses
the existing workbench and compares features/signals; broker parity remains
blocked pending corroboration, and official TradingView review is external.
MT5 and LEAN adapters and operational acceptance are unimplemented, not PASS.

The offline TgSignalSniper management lab is a separate StrategyLab research
lane owned by `app/tg_import.py`, `app/tg_models.py`, `app/tg_replay.py`,
`app/tg_validation.py`, and `app/tg_lab.py`, with routes in `app/main.py` and
the `tg-management` panel in `app/ui/`. It accepts only a finalized,
content-addressed package, rejects SQLite WAL/SHM sidecars, reads source
databases in immutable query-only mode, verifies the declared operational
migration (known 16–22 plus only capability-compatible additive later
versions), tick archive codec/checksums, broker symbol economics and policy
identities, and never connects to MT5, Telegram, AutoKraken, or a live account.
Baseline realized P&L uses the imported broker deal record; exact tick replay is
for counterfactual management/target policies, with one-second paths remaining
explicitly approximate. Search uses chronological walk-forward development and
one untouched holdout evaluation, and statistical promotion advice is not a
production or trading acceptance.

The GHL/DC strategy line also exposes opt-in Phase 4.2 entry black-box veto
controls in `app/lab.py` and `app/backtest.py`. They are disabled by default,
apply before order-concurrency handling, and emit side/hour/month diagnostics;
they do not alter the shared phase prompts or the Pine2Python/TradingView
acceptance boundary.

GitHub commit and fork synchronization are repository operations rather than
proof evidence. The former copy/paste packet for a separate thread was removed
once that workflow became the authorized current task; this map records no
remote synchronization or TradingView verdict. A clean commit or merge never
supplies a trading or TradingView verdict.

## Reusable lessons that are sufficiently resolved

These are process mechanisms that can be carried into future creation,
translation and modification work. “Resolved” means the repository has a
clear contract and demonstrated implementation pattern; it does not mean that
the resulting trading idea is economically successful.

1. **Freeze lineage before mutation.** Give every source, dataset, contract and
   child an immutable identity/hash. Record the exact semantic hypothesis and
   keep rejected parents available for comparison.
2. **Distill a source-cited macro checklist.** Separate hard prerequisites,
   conditional rules, quality grades, context and alternate variants. Do not
   let a later generated checklist silently change the source model.
3. **Separate three questions.** Emit detector events first; evaluate checklist
   gates second; evaluate order concurrency/lifecycle last. A missing trade is
   then classifiable as `DETECTION_MISS`, `CHECKLIST_FAIL` or
   `LIFECYCLE/RENDER_SUPPRESSION` instead of being “fixed” by relaxing a gate.
4. **Use event-level accounting.** Every candidate receives one terminal
   outcome and a first-failure funnel. Counts are per event, with long/short
   symmetry and preserved rejected candidates.
5. **Make time provenance explicit.** Store source, known/confirmation,
   readiness, activation, fill and exit timestamps. A marker may point at a
   source wick, but it must not appear before the bar on which the information
   became knowable. Confirmed-bar gating is the default for persistent state.
6. **Keep raw detection and filtered views separate.** Coverage modes may expose
   more source-valid candidates, while trader mode stays minimal. Rendering
   caps must never be detection caps, and a drawing failure must not delete a
   ledger event.
7. **Use frozen timestamp-owned drawings.** Historical geometry is materialized
   from immutable records, with finite deterministic right edges. It must not
   depend on viewport position, current `time`, or fragile old `time[]` lookups.
8. **Make data/feed identity first-class.** Record instrument, venue, session,
   timezone, timeframe, warmup, source file hash, row count and data-quality
   findings. Never relabel a legacy feed as the requested native feed.
9. **Use the right tool for each proof.** Code/Pine2Python handles static
   analysis, deterministic census, fixtures, prefix/reload stability, source
   hashes and first-divergence reports. TradingView handles official compile,
   chart object behavior, replay/realtime timing and visual human review.
10. **Keep the acceptance boundary explicit.** Local parity is not TradingView
    acceptance; a proof dashboard is evidence, not self-approval. Store the
    exact bytes, settings, signatures, screenshots and user/expert verdict.
11. **Measure economics without steering Phase 1.** Report setup coverage,
    outcomes, PF, win rate, costs and sample size separately. Phase 1 seeks a
    broad source-faithful base; asset/timeframe adaptation and losing-trade
    reduction belong to later phases with out-of-sample controls.
12. **Change one conceptual dependency at a time.** Use a named child, the same
    validation window and symmetric positive/negative fixtures. Stop when a
    proposed rule needs contradictory exceptions or removes an annotated valid
    case.

## SMC-specific status

### Working or bounded enough to preserve

- Dark, minimalist trader/reviewer presentation, compact checklist, risk
  calculator, Fib/range/POC/FVG geometry and position-style historical cards.
- Selectable 71%/75% Fib entry and optional POC checklist score are explicit
  settings. 71% is the coverage-oriented default; 75% remains the stricter
  comparison.
- Confirmed 15m pivots, body-close BOS, causal FVG bookkeeping, prior-completed
  4h context, strict sweep candidate semantics and OHLC ambiguity codes have a
  documented contract or diagnostic implementation. Their cross-feed and
  TradingView behavior remains issue-scoped; do not infer acceptance from a
  local implementation alone.
- Setup history is ledger-backed rather than fill-backed in the v6.3 candidate,
  so a valid setup that was missed or never filled remains inspectable. The
  exact generated source still requires TradingView runtime and user review.

### Partial or unresolved

- **Structure ownership and bias:** independent 2/2 levels plus extreme-level
  selection can select an internal opposing break as the macro direction. The
  `v6_bias` shadow guard did not materially change aggregate counts and is not
  promoted. Exact expert-labelled BTC and native OANDA gold bars are required
  before a new owner rule is safe.
- **Sweep recall:** wick/reclaim plus opposite body break is operationalized,
  but expert cases still report missed LQ events. This is a detection question,
  not permission to remove the sweep requirement from reversal semantics.
- **Short/long asymmetry:** local windows show materially different outcomes;
  no blind direction inversion or generic trend veto is justified.
- **Range ownership and endpoint selection:** the v6 endpoint repair is
  reproducible, but its validity on all expert examples is not adjudicated.
- **POC precision:** the bounded profile and neighboring-row tolerance are
  inspectable; the video’s “near” judgement is not a universal numeric truth.
- **HTF/feed parity:** completed 4h logic is deterministic on BTC, while the
  available legacy gold feed has unverified sessions and incomplete buckets.
- **Economic performance:** current PF/win rate remain below deployable
  confidence on reused windows. More visible entries are a coverage improvement,
  not evidence of an edge.
- **TradingView and trace parity:** earlier evidence localized a FEATURES
  divergence while DATA/SIGNALS lanes were reported as matching for an older
  comparison. The current v6.3 proof is `TRADINGVIEW_REVIEW_REQUIRED` and its
  local PineTS runtime is unavailable because of `request.*`; neither result is
  a current parity or acceptance pass.

## Rejected approaches and why

- v7/v8 restrictive protected-owner/extreme gates: they removed source-valid
  setups before checklist evaluation and contradicted the coverage objective.
- Blindly flipping short direction, adding a generic trend filter, or using PF
  to delete setups: these change the strategy rather than diagnose detection.
- Fill-only history rendering: it made the chart look empty and hid missed or
  pending source setups; v6.3 removes that presentation suppression.
- Treating a matching Python implementation as independent TradingView proof:
  both can share the same mistake.

## Handoff actions

### Pine2Python / service

The service implements the broad boundary (analysis, capabilities,
supported local execution, proof generation, standard traces and parity). This
architecture map carries its binding safety rules: fixed worker invocation with
bounded input/output and timeout, caller-owned candles only, no arbitrary code
or path execution, versioned schemas, no silent repairs/fabricated events, and
no StrategyLab lineage or economic ownership. No strategy-specific detector
rewrite belongs in the service.

The next reusable addition should be a versioned evidence-bundle adapter with
fields for:

```text
source_hash, parent_id, dataset_manifest, criteria_manifest,
event_id, detector_fields, checklist_fields, lifecycle_fields,
source_time, known_time, ready_time, first_failure, render_id,
tradingview_signature, acceptance_status
```

StrategyLab should populate that adapter; Pine2Python must preserve unknown or
unsupported fields instead of inventing values. Add it only after the current
service schema tests and the affected strategy's first FEATURES divergence are
localized.

### Main StrategyLab / phase integration

The active operator preserves immutable lineage, source criteria, relevant
event-level diagnostics, data/feed manifest, independent cases and timestamp
provenance. Strategy-specific SMC coverage and unresolved issue obligations apply
only to affected source consumers, not as invented universal Phase 1 research
filters. Source-correct detection, strategy economics and target acceptance remain
separate. Historical numeric phase references below describe their original
campaigns, not current scheduling.

## Validation entry points and next gate

The 2026-10-17 migration cycle passed terminal independent review after one
bounded effective-parameter authorization correction. Regression evidence:
combined application/reference suite 171 passed before the reference-only
correction; final affected block 33 passed (4 data-integrity, 24 reference,
5 parity tests). The unchanged complete service suite passed 21 tests, Node
runtime passed 2, and legacy vertical parity passed 240 aligned rows. New
reference modules passed Ruff; UI syntax and diff whitespace checks passed.
Real browser checks covered accepted/blocked/legacy states, indicator-source
fidelity limits, labeled registration, 390px layout, casebook event details,
console health and delayed-response family-selection ownership.

Run the reusable reference demonstration with
`python agentic/testscripts/reference_vertical.py --pine-target` and focused
checks with `python -m unittest app.reference_tests`. The final reviewed run is
`artifacts/strategy-development/reference-demo/run-20261017T142234Z-a299b75e/`.
Binary/hash readback verified both parent and both child semantic manifests and
the casebook against current code and parent authorization. The local Pine
feature/signal result is `PARITY_PASS` on 12 rows; target broker parity remains
`BLOCKED`, official platform status `TRADINGVIEW_REVIEW_REQUIRED`, and production
unaccepted. These bounded controls do not close historical SMC issues.

The smallest relevant regression surface is the StrategyLab unit suite plus
the Pine2Python vertical/schema checks, followed by exact-byte/hash and
document-link checks for evidence changes. The integration report's historical
test counts are not reused as a fresh result; new runs must report their own
commands and artifacts. Browser checks are required for UI or TradingView
claims, and a service startup/health check alone is insufficient.

Do not promote SmartMoney-4 until the active source/proof identity passes its
declared local or external gates, exact expert BTC and native OANDA:XAUUSD
cases adjudicate the relevant bias/sweep boundaries, the first FEATURES
divergence is localized, and TradingView exact bytes receive an explicit user or
expert verdict. If cases or external evidence remain unavailable, retain the
issue as unresolved rather than adding another restrictive detector theory.


## Binding repository constraints and verification map

On 2026-10-08 the twelve project-rule records below moved from root AGENTS.md
into this architecture map. Their meanings remain binding for their existing
supported paths. The implemented versioned reference route changes phase
ownership without granting source, target or production acceptance.
Read these constraints before affected source, proof, service or phase work.
The text is preserved verbatim to prevent rule loss during relocation.

Applicability: the preserved early accepted-Pine/Python prerequisite and Phase 1
signature scheduling apply to `legacy_pine_v1`. For `reference_v1`, semantic/data/
execution gates replace that early prerequisite; Pine-specific source/proof and
visual duties apply when relevant to source fidelity or the Phase 5 target.
Under systematic_v2, source/indicator obligations attach to relevant prototypes/base in Phases 2–3, optimization to Phase 4, structural trials and final target to Phase 5, and forward operations to Phase 6. Historical numeric labels below do not move those duties back into research. Unresolved SMC-specific proof obligations remain unchanged.

### Preserved repository constraints

- Architecture: StrategyLab owns strategy lineage, datasets, Python backtests, optimization, mutation, and promotion; the independently runnable `services/pine2python/` service is embedded in the same repository and provides Pre-Phase 1 Pine creation/adaptation, Pynescript analysis, bounded PineTS execution, deterministic proof artifacts, standard traces, source-fidelity review packages, and parity comparison through a typed local/HTTP boundary. Existing-indicator work freezes the user-supplied Pine bytes as the immutable workbench parent, declares protected source regions and visual contracts, and selects event-focused trace fixtures before TradingView review. TradingView Basic corroboration uses the original and exact child source for focused multi-timeframe visual review, then one generated on-chart signature dashboard over an exact window instead of CSV export; a stateful revision may declare a source-owned state-reset boundary so local execution and limited chart history own identical warmup, while revision settings preserve exact TradingView ticker/timeframe separately from dataset shorthand. Accepted Pine and Python traces are required before optimization or mutation. Direct virtualenv/Node operation remains supported alongside a two-container Compose topology where StrategyLab is dual-homed on a localhost edge network and an internal service network, while Pine2Python remains internal-only.
- TradingView corroboration never depends on paid CSV export, alerts, webhooks, or browser scraping. A local PineTS capture is evidence, not official TradingView acceptance; only matching dashboard values plus an explicit user verdict and screenshot SHA-256 may produce `TRADINGVIEW_ACCEPTED`.
- A Codex agent may perform TradingView corroboration through the user-authenticated interactive UI: remove only explicitly scoped stale indicators, paste the exact instrumented bytes, add the script, wait for the declared closed-bar window, and save the dashboard screenshot. This convenience never replaces the generated signature contract or the user's explicit verdict.
- Pine revision and proof files are byte-identity artifacts: hashes must be computed from and verified against the exact UTF-8 bytes written to disk, with no platform newline translation. Stateful Basic-plan proofs may bound local runtime only when the immutable revision declares and implements the same state reset at or before the proof window.
- Existing-source indicator repair must not start from a rewrite. Extract and hash the authoritative source, protect every accepted calculation and visual region outside the named defect, permit one reviewable semantic change per child revision, and require both source-fidelity evidence and focused TradingView review; parser, PineTS, trace, or signature agreement never substitutes for visual product acceptance.
- Pine2Python must preflight TradingView's 64-plot budget before browser corroboration, counting `alertcondition` and other plot-count calls and warning near the lower-bound limit because series-valued parameters may consume additional counts. Stateful proofs must separate supplied state-history warmup from the hashed proof window; history-origin-dependent object IDs are diagnostic only and cannot be parity fields when the strategy consumes only their stable lifecycle state.
- Phase 1 indicator/strategy work must begin with a source-cited criteria manifest that separates hard rules, conditional rules, quality grades, context, and isolated alternatives. It must then account for every structural candidate through an event-level terminal-failure funnel, report realistic setup frequency and direction distribution, distinguish detector misses from checklist failures and lifecycle suppression, and keep indicator detection independent from later order-concurrency policy. “At least one long and one short” is never sufficient acceptance evidence.
- Generated TradingView proofs must preflight both plot counts and compiled-token pressure. Stream hashing should evaluate each declared expression once and feed a shared fixed-lane mixer rather than duplicating expression code per fingerprint lane. Table proofs pack fingerprints into one matrix and metadata into one array; PineTS runtime proofs retain arrays and exact hidden trace exports. A source may opt into proof-only main-body relief only by explicitly marking a pure rendering block with matching `P2P_PROOF_COMPACT_BEGIN` / `P2P_PROOF_COMPACT_END` comments; calculation or state blocks may never be compacted. Browser compilation of the exact generated bytes remains a required gate because source size is not a reliable proxy for TradingView's compiled-token limit.
- Phase 1 signature mismatches are localized in this order: contiguous field groups, time-window partitions, then exact-bar primitive probes. Repair the first causal divergence before rerunning the complete proof. History-origin display counters or latest-object pointers may be diagnostic-only only when strict event signals and lifecycle states already encode the same strategy-consumed behavior; record every exclusion and its strict replacement in the fidelity contract.
- Persistent Pine history renderers must own frozen event timestamps and use `xloc.bar_time`; viewport-driven redraws and historical `bar_index` coordinates are rejected because they can fail to materialize after direct navigation or exceed TradingView's 5,000-bar drawing boundary. Their automatic archive cap must be derived from declared line/box/label budgets, not exposed as a trader history setting. Browser acceptance must directly jump to known feature-positive and feature-negative historical setups without pan/zoom, repeat after reload, and verify collision-free geometry.
- OHLC lifecycle ambiguity must be narrowed by price-path invariants before emitting `AMB`: an unfilled entry and stop on one bar is a deterministic stop when the bar opens on the valid side of the stop, while entry/target, stop-gap, or already-open stop/target coexistence remains ambiguous unless lower-timeframe ordering proves otherwise. Every remaining ambiguity requires an explicit reason code and browser-review timestamp.
- The single root instruction file also governs `services/pine2python/`: never label local PineTS execution as official TradingView verification; preserve original source bytes and immutable content hashes; never execute caller-provided JavaScript, Python, shell, imports, or arbitrary host paths; launch only the fixed Node worker with an argument array, `shell=False`, bounded input/output, a timeout, and a per-job directory; accept caller-supplied candles only and never fetch market data; version public schemas and expose unsupported or uncertain semantics; do not silently repair Pine or fabricate broker events; require matching dataset fingerprints before any TradingView execution fingerprint can pass; and keep Pine2Python limited to analysis/comparison rather than optimization, mutation, promotion, or StrategyLab lineage creation.

### Responsible boundaries and implementation status

These are source-inspection results for relocation, not fresh runtime or browser
validation. Implemented primitives and unverified policy requirements are stated
separately; an inspected code path does not establish perpetual enforcement.

| Record (order above) | Responsible files / evidence | Status and limitation |
|---|---|---|
| 1 — ownership, original parent, review, topology | app/pine_workbench.py; app/pine_review.py; app/storage.py; app/reference_evidence.py; app/lab.py; services/pine2python/; compose.yaml; phase operator | Revision/review/service primitives and topology preserved. New reference operations have backend evidence gates; accepted-Pine/Python early prerequisite remains legacy-only. Docker runtime availability is environment-specific. |
| 2 — dataset-first TV acceptance | services/pine2python/src/pine2python/proof.py; app/pine_workbench.py; TradingView observation APIs | Comparison/verdict fields exist; exact external dashboard, screenshot and human verdict remain evidence duties. Local result cannot close them. |
| 3 — scoped interactive TV operation | services/pine2python/docs/tradingview-browser-corroboration.md | Operator constraint; no browser operation or acceptance performed by relocation. |
| 4 — byte identity and reset | app/pine_workbench.py artifact write/readback; service artifacts.py; service.py state_start_ms | Exact-byte storage and window bounds inspected. Full source-owned reset equivalence remains strategy-specific and unverified where runtime is blocked. |
| 5 — source repair fidelity | app/pine_review.py; existing source/design contracts | Review primitives present; one semantic child change and focused visual verdict are acceptance policy, not universal automatic enforcement. |
| 6 — plots, warmup, diagnostic IDs | service analyzer.py; proof.py; service.py; test_core.py | Plot inventory/warmup primitives and regression cases exist. Series-valued extra counts and diagnostic exclusions still need declared review. |
| 7 — criteria/census/detection isolation | Phase operator; app/reference.py; app/reference_tests.py; SMC evaluate/event_accounting; golden regression_checks | Bounded MA/pivot causal ledger and independent cases implemented. SMC independent recall remains unproven; bounded interface proof does not close it. |
| 8 — expression mixer/table compaction | service proof.py; analyzer.py; test_core.py | Shared expressions, matrix/metadata packing and marked rendering compaction inspected. Browser compiled-token and exact-generated-source runtime gate remain external. |
| 9 — first divergence/exclusions | agentic/testscripts/pine_proof_field_groups.py, pine_proof_partition.py, pine_proof_probe.py; service parity.py | Localization tools preserved; strict replacement/exclusion audit remains required. Duplicate keys and missing required fields now reject before comparison; alignment first divergence retained. |
| 10 — historical rendering and budgets | pre-strategies/smart-money-4/ source; agentic/design/smart-money-4-clean-contract.md; VIS-001/TIME-003 | Timestamp renderer candidate and budget contract recorded. Exact direct-jump/reload/collision browser acceptance remains open. |
| 11 — OHLC ambiguity | SMC evaluator/design contracts; TIME-004 | Bounded classification contract exists. Real broker path/lower-timeframe ordering and reason-coded external review remain scope-specific. |
| 12 — nine service invariants | service runtime.py, models.py, analyzer.py, artifacts.py; fixed worker; service tests; compose.yaml | Fixed argument array, shell=False, timeout, per-job directory and explicit capabilities inspected. Output checks occur after process capture; this is not a claim of hard streaming-memory isolation. Caller-candle/no-arbitrary-code/role rules remain binding; no fresh security audit claimed. |

Reference-first implementation must preserve every applicable source, data,
service and target-validation constraint. When relocating phase-specific gates,
update the operator, prompts, register applicability, backend evidence checks and
this map together; retain legacy statuses and original artifacts. Unverified
requirements stay binding until supported closure or an explicit authorized
contract change. Implementation acceptance depends on current code and checks,
not this map alone; unfinished cycle evidence remains in agentic/analysis.md.
