# StrategyLab Canon

## Prime Directive

`agents/canon.md` is the source of truth for StrategyLab until it is replaced by a newer canon. `AGENTS.md` remains globally binding. Because this repository had no prior canon and the supplied source still had strategy-rule ambiguity, this project requires a `LIRA` architecture pass before `EYE` implementation.

## Why `LIRA` Came First

The source and original query are strong enough to define the product, but not strong enough to safely code without first freezing deterministic contracts. The missing or ambiguous items were:

- A-ZERO swing confirmation and range-high precedence
- same-bar stop-loss/take-profit collision behavior
- slippage and fee defaults
- breakout fill timing and stop-hunt re-entry timing
- SMART_MONEY sweep threshold units
- DST-safe killzone handling
- deterministic market-structure-shift overshoot threshold
- stricter order-block displacement rules
- whether news filtering is mandatory in v1

This canon resolves those gaps with explicit defaults so `EYE` can implement without waiting on further clarification.

## Non-Generic Product Decision

StrategyLab is not a trading bot first. It is a local-first strategy laboratory that:

1. stores strategies as versioned research artifacts
2. executes deterministic backtests with explicit cost models
3. rejects, promotes, and graveyards candidates with reports
4. supports white-box structural families now
5. leaves true black-box and deep-learning layers for later phases after the lab proves it can reject bad ideas reliably

The superior architecture is a small Python monolith with vertical slices, a DuckDB research store, strategy manifests on disk, and a bare semantic operator console. This beats the generic "React dashboard + Node API + framework bot" path because it keeps the quant logic local, inspectable, and cheap to extend.

## Locality Budget

- files: target 20-26 in v1
- LOC/file: target 120-700, hard ceiling under 1000
- deps: 4 core now, 3 deferred later

Core dependencies:

- `fastapi`
- `uvicorn`
- `pydantic`
- `duckdb`

Deferred dependencies:

- `ccxt` only when direct exchange OHLCV or paper/live execution is required
- `hmmlearn` only when regime overlays are implemented
- `torch` only when deep-learning models are justified by profitable upstream families

## Product Scope

### v1 capabilities

- dataset ingest from CSV or Parquet into DuckDB
- strategy-family registry from JSON manifests on disk
- deterministic backtesting over OHLCV bars
- evaluation and promotion/rejection gates
- optimization by bounded parameter sweep
- graveyard and elimination reports
- two built-in families:
  - `a_zero_srlc`
  - `smart_money_structural`
- bare semantic web console for operator workflows

### explicitly out of v1

- live order execution
- authenticated multi-user access
- automatic LLM edits to trading code
- mandatory external news API integration
- GPU training

## Architecture Summary

### Stack

- language: Python 3.12
- API: FastAPI
- validation/contracts: Pydantic v2
- storage: DuckDB file at `artifacts/strategy_lab.duckdb`
- UI: one semantic HTML page plus one vanilla JS file, no CSS in Codex phase
- tests: standard-library `unittest`

### Runtime shape

- local single-process monolith
- one FastAPI app serving JSON APIs and the operator HTML shell
- strategy manifests loaded from disk
- datasets, experiment artifacts, and reports stored locally
- structured JSON logs to stdout with request correlation ids

### Repository shape

```text
/
|-- app/
|   |-- main.py
|   |-- infra/
|   |   |-- config.py
|   |   |-- db.py
|   |   `-- logging.py
|   |-- shared/
|   |   |-- errors.py
|   |   `-- http.py
|   |-- features/
|   |   |-- data/
|   |   |   |-- api.py
|   |   |   |-- service.py
|   |   |   |-- schema.py
|   |   |   `-- tests.py
|   |   |-- strategies/
|   |   |   |-- api.py
|   |   |   |-- service.py
|   |   |   |-- schema.py
|   |   |   `-- tests.py
|   |   |-- backtests/
|   |   |   |-- api.py
|   |   |   |-- service.py
|   |   |   |-- schema.py
|   |   |   `-- tests.py
|   |   |-- evaluations/
|   |   |   |-- api.py
|   |   |   |-- service.py
|   |   |   |-- schema.py
|   |   |   `-- tests.py
|   |   `-- lab/
|   |       |-- api.py
|   |       |-- service.py
|   |       |-- schema.py
|   |       `-- tests.py
|   `-- ui/
|       |-- index.html
|       `-- app.js
|-- strategies/
|   `-- families/
|       |-- a_zero_srlc/
|       |   |-- manifest.json
|       |   `-- notes.md
|       `-- smart_money_structural/
|           |-- manifest.json
|           `-- notes.md
|-- artifacts/
|   |-- data/
|   |-- runs/
|   |-- reports/
|   `-- graveyard/
|-- agents/
|   |-- canon.md
|   `-- plan.md
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

File-size rule: soft target 500 LOC, hard split review at 800 LOC, hard ceiling under 1000 LOC.
Max nesting depth: 4 directories from repo root.

## Logic And Behavior Decisions

### A1. Authentication and authorization

- auth method: none in v1
- user model file location: none
- permission enforcement point: not applicable; app is single-operator local software
- future hardening path: API-key header at the HTTP boundary if remote exposure is later required

Example future guard pattern:

```python
if config.api_key and request.headers.get("x-api-key") != config.api_key:
    raise AppError(status=403, code="FORBIDDEN", message="invalid api key")
```

### A2. Request flow and state management

- entry points:
  - HTTP routes for operator actions
  - filesystem strategy manifests under `strategies/families/`
- request lifecycle order:
  - assign request id
  - parse input
  - validate with Pydantic
  - execute feature service
  - persist artifacts
  - format output envelope
  - log result
- state storage:
  - metadata and run summaries in DuckDB
  - immutable artifacts as JSON or Markdown files under `artifacts/`
  - strategy definitions as JSON on disk
- transaction boundaries:
  - per request for DuckDB writes
  - artifact write after successful transaction commit

### A3. Error handling and recovery

Error envelope:

```python
class ErrorResponse(BaseModel):
    status: int
    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None
```

- validation library: Pydantic
- validation location: HTTP boundary and manifest-loading boundary
- retry strategy: none for v1 research operations; fail fast with explicit errors
- fallback behavior on critical failure: return error, do not partially save a run

### A4. Data contracts and schemas

- schema tool: Pydantic models co-located with each feature
- schema files location: `app/features/*/schema.py`
- contract testing approach: schema-validation tests plus end-to-end API tests

Main strategy-manifest schema shape:

```python
class StrategyManifest(BaseModel):
    family_id: str
    title: str
    class_type: Literal["white_box", "hybrid", "black_box"]
    asset: str
    timeframe: str
    parameters: dict[str, float | int | bool | str]
    risk: dict[str, float | int]
    gates: dict[str, float]
    notes_path: str
```

### A5. Critical user journeys

Primary happy path:

1. `POST /api/data/import` validates a CSV import request in `app/features/data/api.py`
2. `import_dataset()` in `app/features/data/service.py` normalizes candles and writes DuckDB rows
3. `POST /api/backtests/run` validates a strategy instance and dataset selection
4. `run_backtest()` in `app/features/backtests/service.py` loads the manifest, replays bars, and writes a run artifact
5. `evaluate_run()` in `app/features/evaluations/service.py` computes gates and sets verdict
6. if rejected, a graveyard report is written
7. UI fetches summary tables and renders browser-default HTML

First decision point:

- after evaluation gate computation in `app/features/evaluations/service.py`
- branches:
  - rejected -> write elimination report and optionally move manifest to `artifacts/graveyard/`
  - research_survivor -> keep for further parameter sweeps
  - paper_candidate -> available for future paper execution slice

Failure recovery example:

- if DuckDB is unavailable, request returns `503 STORAGE_UNAVAILABLE`, no artifact write occurs, and the UI keeps prior results unchanged

## Strategy Decisions

### Strategy taxonomy

- structural white-box: deterministic rule families such as A-ZERO and SMART_MONEY
- hybrid: structural family plus statistical overlay such as HMM veto or score
- black-box: model produces signals directly from features; not in v1

### Research state machine

Allowed strategy states:

- `draft`
- `backtesting`
- `rejected`
- `research_survivor`
- `paper_candidate`
- `live_candidate`
- `retired`

### Evaluation gates

Reject immediately if any are true:

- out-of-sample sharpe < 0.75
- expectancy <= 0
- profit factor < 1.0
- unstable walk-forward folds

Keep for research if all are true:

- out-of-sample sharpe >= 1.25
- max drawdown <= 0.20
- profit factor >= 1.15
- trades >= 30 in the tested window

Promote to paper candidate if all are true:

- out-of-sample sharpe >= 1.75
- max drawdown <= 0.12
- profit factor >= 1.30
- stable walk-forward folds
- survives fee and slippage stress test

### Cost model defaults

- fee per side: 0.0005
- slippage per fill:
  - 0.0002 for 1H and 4H
  - 0.0004 for 5m
- same-bar SL/TP collision rule: pessimistic ordering, stop-loss first

### A-ZERO deterministic decisions

- swing definition: 5-bar fractal, pivot confirmed only after two bars print after the pivot
- macro lookback: default 90 days, optimized within 60-90
- bottom confirmation: two consecutive closes at least 2 percent above the rolling low-zone floor
- top confirmation: two consecutive closes at least 2 percent below the rolling high-zone ceiling
- range-high precedence:
  - use most recent confirmed swing high after bottom confirmation
  - if none exists, use `range_low * range_multiplier`
- breakout entry timing: qualifying close on bar `n`, fill at next bar open
- re-entry timing: if stop is hit and price closes back inside the range within the next two fully closed bars, allow one re-entry
- TP1 size: 0.33 of position
- post-TP1 stop: breakeven on remainder

### SMART_MONEY deterministic decisions

- higher timeframe: 1H
- execution timeframe: 5m
- killzones: America/New_York DST-aware windows
  - London 02:00-05:00
  - New York 07:00-10:00
- sweep threshold: `max(0.0003 * price, 0.10 * atr_14)`
- equal-high or equal-low tolerance: 0.0005 of price
- market-structure shift:
  - bullish: prior sell-side sweep then close above latest confirmed bearish fractal by `max(0.0002 * price, 0.05 * atr_14)`
  - bearish: mirrored logic
- order-block rule:
  - last opposite candle before a displacement bundle
  - displacement bundle must exceed `1.5 * atr_14`, close in the top or bottom quartile, and break a prior confirmed fractal
- news filter:
  - feature flag in manifest
  - default mode in v1 is `off`
  - external calendar integration is deferred

## Interface And Design Decisions

### Codex implementation rule

Because `agents/codex-no-frontend.txt` is binding for this repo, Codex implementation must ship only:

- semantic HTML
- native controls
- no CSS
- no styling classes for presentation
- no layout system beyond document structure
- no icons or animation

The operator console must work end-to-end as a plain browser-default page.

### Deferred frontend canon for the dedicated frontend model

This section is the style canon for the later Claude Opus pass. Codex must not implement this styling in the backend phase.

- base system: custom design system applied in one CSS file during the dedicated frontend pass
- typography:
  - display: `"IBM Plex Sans", "Segoe UI", sans-serif`
  - data and code: `"IBM Plex Mono", "Cascadia Code", monospace`
- color direction:
  - graphite `#1f2328`
  - fog `#eef1e8`
  - rust `#b14a2b`
  - moss `#44513c`
  - signal red `#8f1d1d`
- spacing scale: `4, 8, 12, 16, 24, 32`
- border radius: `2px`
- motion: `150ms` maximum, functional only
- responsive strategy for later pass:
  - mobile first
  - breakpoints `640px`, `960px`, `1280px`
  - touch target minimum `44px`
- accessibility baseline:
  - AA contrast minimum
  - `:focus-visible` with a 2px outline in rust
  - keyboard access for every control
  - semantic HTML first, ARIA only where semantics are insufficient

Example deferred token block for the frontend model:

```css
:root {
  --bg: #eef1e8;
  --ink: #1f2328;
  --accent: #b14a2b;
  --accent-soft: #44513c;
  --danger: #8f1d1d;
  --radius: 2px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
}
```

### Component architecture

- component file pattern: one HTML shell and one JS module in `app/ui/`
- state management: browser-native state in `app.js`
- prop validation: not applicable; API boundary validation stays on the server

## Architecture And Operations Decisions

### C1. Environment and configuration

Required env files:

- `.env.example`
- `.env.local` for real local overrides, gitignored

Config loading:

- custom loader in `app/infra/config.py`
- fail fast on missing required values

Expected `.env.example`:

```bash
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
APP_DB_PATH=artifacts/strategy_lab.duckdb
APP_DATA_DIR=artifacts/data
APP_RUN_DIR=artifacts/runs
APP_REPORT_DIR=artifacts/reports
APP_GRAVEYARD_DIR=artifacts/graveyard
APP_LOG_LEVEL=INFO
APP_API_KEY=
```

### C2. Dependency management

- package manager: `pip`
- lock discipline: pinned `requirements.txt`
- dependency count budget: production max 7, current target 4
- vanilla-first exceptions:
  - `fastapi` for HTTP routing and docs
  - `pydantic` for contracts
  - `duckdb` for the research store
  - `uvicorn` for serving the app

### C3. Build and development

Commands:

- `python -m venv .venv`
- `.venv\Scripts\python -m pip install -r requirements.txt`
- `.venv\Scripts\python -m uvicorn app.main:app --reload`
- `.venv\Scripts\python -m unittest discover -s app -p tests.py`

- dev server port: `8000`
- hot reload: yes through `uvicorn --reload`
- output directory: none in v1; runtime is source-based

### C4. Testing

- test framework: `unittest`
- test file pattern: `tests.py` co-located in each feature
- test database approach: temporary DuckDB file under `artifacts/`
- required test types:
  - smoke: yes
  - unit: yes
  - integration: yes
  - end-to-end: yes
- coverage target: meaningful boundary coverage, not percentage theater

### C5. Logging and observability

- logging library: stdlib `logging`
- log format: JSON lines
- log levels: `ERROR`, `WARNING`, `INFO`, `DEBUG`
- correlation id strategy: generated UUID at the HTTP boundary, passed through the request lifecycle

Example log line:

```json
{"level":"INFO","request_id":"1b2d9f74","feature":"backtests","event":"run_finished","run_id":"bt_20260318_001","status":"rejected"}
```

### C6. Security baseline

- secrets management: environment variables only
- input hardening: boundary validation with Pydantic
- injection prevention: parameterized DuckDB queries only
- XSS prevention: plain text rendering in the HTML shell, no raw HTML injection
- CORS: none in v1 because the UI is same-origin
- rate limiting: none in v1 because the app is local single-user software

### C7. Git and version control

`.gitignore` must include:

```gitignore
.venv/
__pycache__/
*.pyc
artifacts/
.env.local
*.log
```

- branch strategy: trunk plus short-lived `codex/*` branches if needed
- commit format: conventional commits preferred

### C8. Deployment

- deployment target in v1: local workstation only
- deployment trigger: manual local command
- environment parity: dev and run environments should be identical
- infrastructure as code: none in v1

## Project-Specific Constitution

1. Build the research lab before any live-execution ambition.
2. Treat strategy definitions as data and reports, not hardcoded branching scattered through the app.
3. Every feature slice must own its API contract, service logic, validation, and tests together.
4. Every run must be reproducible from dataset id, manifest id, parameter set, and cost model.
5. Every rejection must leave a report artifact; never silently discard failed research.
6. Every black-box idea is downstream of a functioning rejection pipeline, not a substitute for one.
7. Codex frontend work stays designless and semantic; stylistic decisions are deferred to the dedicated frontend model.
8. If debugging uncovers a preventable repo-specific failure, add one dense prevention line under `2) Specific repo rules` in `AGENTS.md`.
