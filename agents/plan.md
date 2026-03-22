# StrategyLab Plan

## Decision

Action mode: planning.

This required `LIRA` before `EYE` because:

- `agents/canon.md` did not exist
- the repo had no implementation scaffold
- the source defined the product but left deterministic strategy details unresolved
- the work spans API, storage, manifests, backtesting, evaluation, artifacts, and a minimal UI

Locality budget for implementation:

- files: 20-26
- LOC/file: 120-700, hard ceiling under 1000
- deps: 4 core now

## Zero - Context

### Environment matrix

- OS: Windows 10 `10.0.19045.0`
- shell: PowerShell `5.1.19041.7058`
- Python: `3.12.7`
- pip: `24.3.1`
- git build id: repository has no valid `HEAD` commit yet
- current repo state: prompt-only repo with `bridgecode/` and `agents/` docs, no app code

### Non-functional requirements

- local-first single-operator app
- deterministic replay and reproducible artifacts
- all errors must be explicit and structured
- all critical boundaries must emit correlation ids
- cold start should stay under 3 seconds on a normal laptop
- a 2-year BTC 1H backtest should complete in under 10 seconds for a single strategy instance on a typical developer machine
- no hidden remote dependencies in v1
- no secret leakage in logs or reports

### Constraints and assumptions

- v1 uses CSV or Parquet ingest only
- v1 does not require exchange credentials
- v1 does not implement live trading
- Smart Money news filtering is a disabled feature flag in v1
- Codex frontend output must remain plain browser-default HTML and JS with no styling

### Risks

- strategy ambiguity can leak into code if boundaries are not frozen first
- bar-resolution edge cases can create false optimism if same-bar execution rules are sloppy
- research artifacts can become non-reproducible if manifests and datasets are mutable in place

## Implementation Block

### C1: Foundation and operator shell

Objective: boot a working local application with config, storage, request ids, error envelopes, and a functional no-style operator console.

Deliverable scope:

- UI:
  - `app/ui/index.html` with forms for dataset import, strategy listing, backtest runs, and report lookup
  - `app/ui/app.js` for fetch calls and DOM updates
- API:
  - app boot route
  - health route
  - request-id middleware
- Data:
  - DuckDB connection factory
  - startup creation of required tables
  - artifact directories created on boot
- Validation and errors:
  - common error envelope
  - config validation
- Observability:
  - JSON logging with request ids

Dependencies:

- `fastapi`
- `uvicorn`
- `pydantic`
- `duckdb`

Implementation boundaries:

- Boundary A: config load -> validated app config object
- Boundary B: HTTP request -> request id -> response or error envelope
- Boundary C: storage bootstrap -> ready DuckDB file and artifact paths

Structured error envelope:

```python
{ "status": 400, "code": "VALIDATION_ERROR", "message": "invalid dataset request", "details": {...}, "request_id": "..." }
```

Testscript:

- ID: `TS-C1-boot`
- Objective: app boots and serves both JSON and HTML
- Prerequisites:
  - Python virtual environment
  - installed `requirements.txt`
- Setup:
  - `.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Run:
  - `Invoke-RestMethod http://127.0.0.1:8000/health`
  - `Invoke-WebRequest http://127.0.0.1:8000/`
- Expected observations:
  - health returns `{"status":"ok"}`
  - root returns HTML with dataset and backtest controls
- Artifact capture points:
  - stdout logs
  - any boot errors copied to `agents/testscripts/`
- Cleanup:
  - stop the local server
- Known limitations:
  - no strategy logic yet

Observation checklist:

- environment details confirmed
- exact server command captured
- observed vs expected for `/health` and `/`
- reproducibility target `3/3`

Pass/fail gate:

- PASS if boot works and request ids appear in logs
- FAIL if any route crashes or artifact paths are missing

### C2: Dataset ingest vertical slice

Objective: import OHLCV data from CSV or Parquet, normalize it, register datasets, and make them queryable.

Deliverable scope:

- UI:
  - import form and dataset list
- API:
  - `POST /api/data/import`
  - `GET /api/data/datasets`
- Data:
  - normalized candle storage in DuckDB
  - dataset metadata table
- Validation and errors:
  - timeframe validation
  - OHLCV column validation
- Observability:
  - log imported row counts and dataset ids

Dependencies:

- C1 complete

Implementation boundaries:

- Boundary A: import request -> validated file path and metadata
- Boundary B: raw file -> normalized candles
- Boundary C: normalized candles -> dataset id and metadata row

Testscript:

- ID: `TS-C2-data-import`
- Objective: import a BTC 1H CSV and confirm it is queryable
- Prerequisites:
  - running app
  - sample CSV at `artifacts/data/sample_btc_1h.csv`
- Setup:
  - place a valid CSV with columns `timestamp,open,high,low,close,volume`
- Run:
  - PowerShell `Invoke-RestMethod` POST to `/api/data/import`
  - GET `/api/data/datasets`
- Expected observations:
  - import response includes `dataset_id`
  - dataset list includes the imported dataset with row count
- Artifact capture points:
  - import response JSON
  - DuckDB dataset row count
- Cleanup:
  - none

Observation checklist:

- imported dataset id recorded
- row count matches source file
- timestamps are normalized to UTC

Pass/fail gate:

- PASS if the dataset is stored and listable
- FAIL if column validation is weak or row counts drift

### C3: Strategy registry and manifest loading

Objective: load built-in strategy families from disk, validate manifests, and present operator-ready strategy instances.

Deliverable scope:

- UI:
  - strategy family list
  - manifest detail view
- API:
  - `GET /api/strategies/families`
  - `GET /api/strategies/families/{family_id}`
- Data:
  - manifest loader from `strategies/families/*/manifest.json`
- Validation and errors:
  - required manifest fields
  - parameter range checks
- Observability:
  - log manifest-load success and failure

Dependencies:

- C1 complete

Implementation boundaries:

- Boundary A: manifest file -> Pydantic model
- Boundary B: strategy request -> family resolution

Testscript:

- ID: `TS-C3-strategy-registry`
- Objective: both A-ZERO and SMART_MONEY manifests load successfully
- Prerequisites:
  - built-in family files exist
- Setup:
  - start app
- Run:
  - GET `/api/strategies/families`
  - GET each family detail
- Expected observations:
  - two family ids returned
  - manifest parameters show deterministic defaults from `agents/canon.md`
- Artifact capture points:
  - family list JSON
  - any manifest validation errors

Pass/fail gate:

- PASS if both families validate and serialize
- FAIL if any family needs runtime code edits just to change parameters

### C4: Backtest engine and evaluation

Objective: run deterministic bar-by-bar backtests and compute verdict metrics.

Deliverable scope:

- UI:
  - backtest run form
  - run summary table
- API:
  - `POST /api/backtests/run`
  - `GET /api/backtests/runs/{run_id}`
- Data:
  - backtest run records
  - trade ledger records
  - run artifact JSON written to `artifacts/runs/`
- Validation and errors:
  - dataset and family compatibility checks
  - cost model validation
- Observability:
  - log each run start and finish

Dependencies:

- C1, C2, C3 complete

Implementation boundaries:

- Boundary A: run request -> validated backtest job spec
- Boundary B: job spec -> strategy-specific signal replay
- Boundary C: replay output -> evaluation summary and verdict

Testscript:

- ID: `TS-C4-a-zero-backtest`
- Objective: run A-ZERO end to end on imported BTC 1H data
- Prerequisites:
  - dataset imported
  - strategy manifests loaded
- Setup:
  - choose dataset id and `a_zero_srlc`
- Run:
  - POST `/api/backtests/run`
  - GET run summary by returned `run_id`
- Expected observations:
  - run artifact exists
  - evaluation metrics include sharpe, max drawdown, profit factor, expectancy
  - verdict is one of the canonical states
- Artifact capture points:
  - run JSON in `artifacts/runs/`
  - report JSON or Markdown in `artifacts/reports/`

Observation checklist:

- fee and slippage model recorded
- same-bar conflict rule recorded as stop-first
- run is reproducible on repeat execution

Pass/fail gate:

- PASS if repeated identical runs produce identical results
- FAIL if results drift between runs or metrics omit cost assumptions

### C5: Rejection, graveyard, and optimization

Objective: turn evaluation into action by rejecting poor candidates, preserving evidence, and enabling bounded parameter sweeps for survivors.

Deliverable scope:

- UI:
  - verdict table
  - graveyard report links
  - optimization trigger
- API:
  - `POST /api/lab/optimize`
  - `GET /api/lab/graveyard`
- Data:
  - elimination reports in Markdown
  - optimization result rankings
- Validation and errors:
  - bounded sweep validation
  - survivor-only optimization guard
- Observability:
  - log rejection reasons and optimization ranks

Dependencies:

- C4 complete

Implementation boundaries:

- Boundary A: evaluation verdict -> rejection or survivor path
- Boundary B: optimization request -> bounded parameter grid
- Boundary C: sweep results -> ranked candidates and reports

Testscript:

- ID: `TS-C5-rejection-optimization`
- Objective: verify bad strategies are graveyarded and survivors can be optimized
- Prerequisites:
  - at least one finished backtest
- Setup:
  - run a deliberately poor parameter set
  - run a valid survivor parameter set
- Run:
  - POST optimization request for survivor
  - GET graveyard list
- Expected observations:
  - poor run generates elimination report
  - survivor sweep returns ranked parameter variants
- Artifact capture points:
  - graveyard Markdown report
  - optimization ranking JSON

Pass/fail gate:

- PASS if the system preserves failed evidence and only optimizes eligible candidates
- FAIL if rejected candidates disappear without explanation

### C6: SMART_MONEY implementation and lab proposals

Objective: add the second family and the first conjecture/refutation workflow without allowing arbitrary code generation.

Deliverable scope:

- UI:
  - SMART_MONEY family appears in the same operator flows
  - proposal cards list
- API:
  - SMART_MONEY backtests through the same endpoint
  - `POST /api/lab/proposals/dry-run`
- Data:
  - proposal artifacts limited to parameter patches, rule toggles, and candidate-manifest drafts
- Validation and errors:
  - proposal type whitelist
  - no direct code artifact writes
- Observability:
  - log proposal type and target family

Dependencies:

- C4 and C5 complete

Implementation boundaries:

- Boundary A: lab proposal request -> validated proposal spec
- Boundary B: proposal spec -> stored non-executable artifact

Testscript:

- ID: `TS-C6-smart-money-and-proposals`
- Objective: SMART_MONEY runs and dry-run proposals remain constrained artifacts
- Prerequisites:
  - imported dataset with 5m and 1H compatibility, or fixture data
- Setup:
  - load SMART_MONEY manifest
- Run:
  - run a SMART_MONEY backtest
  - post a dry-run proposal request
- Expected observations:
  - SMART_MONEY uses canonical deterministic rules
  - proposal artifact is JSON or Markdown only, never code
- Artifact capture points:
  - SMART_MONEY run artifact
  - proposal artifact under `artifacts/reports/`

Pass/fail gate:

- PASS if the second family shares the same lab pipeline and proposals remain non-executable
- FAIL if proposal output can mutate source code directly

## Regression Rule

After each capability slice:

1. rerun all previously passing testscripts
2. do not advance while any prior slice regresses
3. preserve artifacts from the failed run before editing code

## Testscripts Folder Policy

If implementation creates standalone testscript documents or debugging artifacts, store them in `agents/testscripts/`.

If debugging fails after two turns or more on the same issue, create `agents/testscripts/failure_report.md` with:

- title
- severity
- implementation block
- debug scope
- environment matrix
- exact reproduction steps
- observed behavior
- expected behavior
- artifact references
- initial hypothesis
- requested human follow-up

## Manual Operator Policy

No human-only manual setup is required to complete this planning phase.

During `EYE` implementation, generate a runbook that follows `agents/manual_operator_steps.txt` only if a step truly requires human-only work such as:

- retrieving exchange credentials
- configuring third-party dashboards
- setting remote environment variables
- deployment to a hosted platform

If those steps are needed, the runbook must:

- match Windows PowerShell syntax
- separate browser actions from CLI actions
- include verification commands and success signals after each critical step

## Frontend Model Instructions For Claude Opus

These instructions live here so no extra artifact file is needed before implementation.

1. Preserve the backend contracts and DOM hooks exactly as shipped by Codex.
2. Do not rename form fields, element ids, API routes, JSON keys, or request payload shapes.
3. Treat the current Codex UI as a semantic skeleton only; your job is styling, layout, interaction clarity, and information hierarchy.
4. Use the deferred style canon in `agents/canon.md`, especially the graphite, fog, rust, and moss palette and the IBM Plex type pairing.
5. Design for a research console, not a marketing site. Prioritize dense comparative tables, run-status visibility, artifact drill-down, and keyboard efficiency.
6. Keep accessibility non-negotiable: visible focus states, semantic landmarks, AA contrast, reduced-motion support, and touch targets of at least 44px where applicable.
7. Avoid generic dashboard tropes. Do not use a safe blue SaaS card grid. The UI should feel like an operator ledger for strategy research.
8. Preserve locality. If new CSS or frontend modules are added, keep them adjacent to `app/ui/`.

## Handoff

`EYE` should now execute the implementation block in one shot using `bridgecode/plan-code-debug.md`, with `agents/canon.md` as the frozen project definition and this file as the sequencing and verification guide.
