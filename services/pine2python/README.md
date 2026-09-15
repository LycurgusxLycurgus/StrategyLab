# Pine2Python

Pine2Python is StrategyLab's local-first Pine analysis, execution, proof, trace,
parity, and registered-adapter service. It is built inside the monorepo but can run
on its own.

It does not compile Pine with TradingView, translate arbitrary Pine faithfully,
optimize strategies, or promote versions. PineTS output is local evidence.
Official corroboration uses a generated TradingView Parity Proof Dashboard and an
explicit user acceptance record.

## Local run

```powershell
.venv\Scripts\python -m pip install -e services\pine2python
npm ci --prefix services\pine2python
.venv\Scripts\uvicorn pine2python.api:app --host 127.0.0.1 --port 8080
```

Useful CLI commands:

```powershell
.venv\Scripts\pine2python capabilities
.venv\Scripts\pine2python analyze pre-strategies\BTC-intraday.txt
```

## Basic-plan TradingView workflow

1. Analyze or generate a frozen Pine revision.
2. For an existing-source repair, compare protected baseline regions and prepare
   focused event fixtures before changing or proving the candidate.
3. Run supported PineTS evidence and generate the proof artifact. Preserve
   unsupported MTF/drawing behavior for focused TradingView review.
4. Open the exact TradingView symbol/timeframe, paste the instrumented Pine, and
   use the supplied absolute test window and settings.
5. Capture the complete proof table in one screenshot.
6. Compare its values with `proof.json`. Dataset identity must match before signal,
   state, order, or trade evidence can pass.
7. Record the screenshot hash and user verdict. Focused visual/realtime review is
   added only for claims the table cannot encode.

When a dashboard stream differs, localize it before editing strategy semantics:

1. split the failing stream into contiguous field groups with
   `agentic/testscripts/pine_proof_field_groups.py`;
2. split the first failing field across time with
   `agentic/testscripts/pine_proof_partition.py`;
3. fingerprint the smallest causal Pine predicates on the first failing bar with
   `agentic/testscripts/pine_proof_probe.py`;
4. repair that first divergence and rerun the complete proof.

History-origin display counters and latest-object pointers are not strict parity
fields when stable event signals and lifecycle states already encode the same
strategy-consumed behavior. Every such exclusion and its strict replacement must
be declared in the revision's fidelity contract.

No chart-data export, Premium plan, webhook, alert, or automated TradingView login
is required.

## API

| Endpoint | Purpose |
|---|---|
| `GET /v1/version` | Service and schema versions |
| `GET /v1/capabilities` | Honest current support matrix |
| `POST /v1/analyses` | Immutable Pine source analysis |
| `POST /v1/proofs` | Expected proof plus instrumented Pine artifact |
| `POST /v1/tradingview-observations` | Compare and record observed dashboard values |
| `POST /v1/runtime-executions` | Capability-gated PineTS execution |
| `POST /v1/parity-comparisons` | First-divergence trace comparison |
| `POST /v1/generators/{adapter_id}` | Registered deterministic Pine generation |

Large source, AST, proof Pine, and runtime results live in content-addressed
artifact bundles rather than being duplicated in every response.
Proof creation also reuses immutable revision runtime blockers, so expanding a
focused review to the Basic-plan 5,000-bar window does not rerun static parsing
for Pine that is already known to require TradingView.

Registered generation currently includes:

- `ma_cross_v1`, the small sample adapter;
- `ma_cross_atr_stop_v1`, the StrategyLab golden adapter for the explicit
  `next_bar_open` contract.

The MA/ATR adapter rejects `mt5_bar_proxy`; it does not silently approximate that
different fill and stop model. Its golden market/position regression is:

```powershell
.venv\Scripts\python agentic\testscripts\pine2python_vertical.py
```

## Licensing

This service is AGPL-3.0-only under the current PineTS dependency posture. See
`NOTICE.md`. Closed-source or hosted release requires a license review, including
PineTS's commercial option.
