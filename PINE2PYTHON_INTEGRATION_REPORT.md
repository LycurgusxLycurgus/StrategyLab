# StrategyLab Pine2Python integration report

This is the historical integration record. For the current recoverable project
context, phase contract, unresolved issue register, root-proof obligations and
future GitHub-sync handoff, read
`STRATEGYLAB_UNRESOLVED_PROOF_MAP.md` together with
`agentic/architecture.md`.

## Outcome

Pine2Python now lives inside StrategyLab at `services/pine2python/` and the Pine
Workbench is the default pre-Phase 1 evidence path. An agent can create a
greenfield strategy, freeze a licensed open-source adaptation, or begin with an
indicator; obtain structured analysis; run the supported Pine locally; generate
one-screen TradingView Basic corroboration; persist immutable Pine and Python
traces; and receive a precise parity verdict before optimization or mutation.

TradingView CSV export is no longer required. The external gate uses an explicit
window of at most 5,000 bars and a generated on-chart proof table. The table
contains exact context/window identity, bar count, three dataset fingerprints,
eight segment fingerprints, and declared strategy-stream fingerprints. Normal
human work is paste/run, confirm the exact chart/settings, and capture one
screenshot. Visual lifecycle, realtime, nonstandard-chart, feed, or unsupported
broker-emulator claims still receive focused TradingView review.

PineTS evidence and a matching dashboard earn strong automated corroboration, but
only the user can record `TRADINGVIEW_ACCEPTED`. Optimization and mutation remain
blocked until the accepted Pine is translated and the required Pine/Python trace
level passes.

## Final architecture

| Owner | Responsibilities |
|---|---|
| StrategyLab | Dataset acquisition/hash, Pine lineage/provenance, phase state, user verdict, Python engines, mutation and promotion |
| Pine2Python service | Parse/analyze, capability gate, local PineTS runtime, proof dashboard, standard Pine trace, parity comparison, registered generation |
| TradingView | Official compile/runtime/feed corroboration and the visible dashboard evidence |
| User | Final acceptance and any intentional-divergence approval |

Direct development uses the embedded local client fallback. Compose disables that
fallback and routes StrategyLab to the internal `pine2python:8080` service. The
Pine2Python container is read-only, non-root, capability-dropped, and attached to
an internal network.

## SmartMoney-4 process handoff (universal, not an SMC implementation rule)

The current SMC work produced a reusable evidence contract now recorded in
`agentic/architecture.md`. Future Phase 1 creation, translation and revision
flows should carry immutable source/data hashes, a source-cited macro checklist,
event-level detector/checklist/lifecycle traces, explicit source/known/ready
times, first-failure codes, timestamp-owned persistent drawings, feed/session
provenance, golden cases, and a separate TradingView acceptance record. Phase 1
must preserve broad source-valid coverage and report PF/win rate rather than use
those metrics to hide events; later phases may optimize a frozen parent.

No Pine2Python detector rewrite is required by this cycle. The next general
service extension is a versioned evidence-bundle adapter carrying those fields;
StrategyLab remains responsible for strategy-specific criteria and fixture
selection. SMC-specific structure ownership, sweep recall, HTF/feed parity and
economic performance remain unresolved and must not be promoted as universal
rules.

## Important files

| Path | Purpose |
|---|---|
| `services/pine2python/src/pine2python/` | Owned service implementation |
| `services/pine2python/runtime/worker.mjs` | Fixed PineTS worker |
| `services/pine2python/tests/fixtures/ma_cross_atr_stop_v1/` | First golden adapter contract |
| `app/pine2python_client.py` | HTTP/local transport boundary |
| `app/pine_workbench.py` | StrategyLab lineage and evidence orchestration |
| `app/data.py` | Exact CSV hash and Basic proof-window selection |
| `app/backtest.py` | Opt-in standard Python trace |
| `app/storage.py` | Immutable Pine revisions/evidence and dataset hashes |
| `app/ui/` | Compact operator-facing Pine evidence surface |
| `agentic/testscripts/pine2python_vertical.py` | Reusable end-to-end parity regression |
| `artifacts/integration/pine2python/implementation-decisions.md` | Durable integration decisions |

## StrategyLab endpoints

| Endpoint | Contract |
|---|---|
| `GET /health` | App health plus Pine2Python transport/status |
| `GET /health/ready` | Fails only when Pine2Python is configured as required and unavailable |
| `GET /api/pine2python/status` | Version, capabilities, transport, and readiness |
| `GET/POST /api/pine-workbench/revisions` | List/create immutable Pine revisions |
| `GET /api/pine-workbench/revisions/{id}` | Source, analysis, lineage, and evidence |
| `POST /api/pine-workbench/generate/{adapter}` | Registered generation plus automatic analysis |
| `GET /api/datasets/{id}/pine-proof-window` | Latest Basic-compatible window and exact CSV SHA-256 |
| `POST /api/pine-workbench/revisions/{id}/proofs` | Local proof, standard Pine trace, and paste-ready source |
| `POST /api/pine-workbench/revisions/{id}/tradingview-observations` | Dashboard comparison, screenshot hash, user verdict |
| `POST /api/versions/{id}/python-trace` | Opt-in standard Python trace |
| `GET /api/versions/{id}/pine-evidence` | Persisted version-level trace evidence |
| `POST /api/pine2python/parity-comparisons` | Exact/tolerance comparison and first divergence |

## Evidence schemas and states

| Evidence | Key fields |
|---|---|
| Pine revision | Workbench/revision/parent IDs, mode, source SHA-256, settings, provenance, parser and capability findings |
| TradingView proof | Dataset SHA-256, symbol/timeframe, `[start,end)`, mintick, bar count, fingerprints, local runtime basis |
| Pine trace | Exact market rows, declared plot streams, position/trade events, capabilities |
| Python trace | Exact market rows, position/orders/trades/equity capabilities, dataset SHA-256 |
| Parity result | Aligned/missing/extra keys, exact/tolerance mismatches, first divergence |

`LOCAL_PROOF_CAPTURE_COMPLETE` means PineTS produced the reference streams when no
independent trace was supplied. `LOCAL_PROOF_PARITY_PASS` is reserved for streams
checked against caller-owned reference rows. Both still require
`TRADINGVIEW_REVIEW_REQUIRED`. `TRADINGVIEW_ACCEPTED` requires an exact signature,
an explicit user verdict, and a screenshot SHA-256.

## First adapter and parity result

The first full adapter is `ma_cross_atr_stop_v1`. It implements the stable
`next_bar_open` subset: SMA/EMA cross, price/fast-MA noise gate, fixed quantity,
long/short selection, commission/slippage configuration, and a static ATR stop.
It rejects `mt5_bar_proxy`; advanced existing StrategyLab features remain explicit
future adapter work.

The golden regression aligns 240 PineTS and 240 Python rows. Exact OHLCV and
`state.position_size` pass with no divergence. The deterministic proof artifact
ID is `tradingview-proof_127d8c847d78c12cbf03`; its service-relative path is
`tradingview-proof/12/127d8c847d78c12cbf03bc61c970311ba4bf65d7af461c49d729c7fa0e0ecdac`.

## Validation

The pre-change StrategyLab suite passed 90 tests with unchanged baseline behavior.
The final regression block passed all 97 StrategyLab tests, all 10 Pine2Python
Python tests, both Node worker tests, the 240-row vertical parity fixture,
compile/static checks, and both Compose configuration parses. Browser validation
confirmed the service-ready state, immutable generated revision, local proof
status, `TRADINGVIEW_REVIEW_REQUIRED`, copy-ready proof action, persisted Python
trace, locked Compare action without prerequisites, and no horizontal overflow
at desktop or mobile breakpoints.

Docker Desktop 4.83.0, Docker CLI 29.6.2, and Compose 5.3.1 are installed.
After AMD SVM was enabled, both production images built and the complete
two-container regression passed. StrategyLab was healthy at
`127.0.0.1:8000`, reached the required Pine2Python service through HTTP, and
kept Pine2Python unexposed to the host. Pine2Python ran as its non-root user with
a read-only root filesystem and all Linux capabilities dropped. The 240-row
vertical fixture passed inside the StrategyLab container against the private
Pine2Python container, and an identical repeat returned the same proof and parity
artifact IDs. The isolated acceptance containers, networks, and volumes were
removed after validation.

## Remaining manual TradingView requirement

For a real candidate, open the exact TradingView symbol and timeframe, paste the
proof source, set the supplied window and inputs, and capture the entire dashboard
in one screenshot. Submit its values and file SHA-256, then explicitly accept or
reject. A matching local/golden test is not permission to skip that step.
