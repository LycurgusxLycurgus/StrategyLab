# Pine2Python implementation report

## Result

Pine2Python 0.1.0 is an independently buildable service embedded in
StrategyLab. It accepts frozen Pine and caller-owned candles, performs Pynescript
analysis, runs capability-gated Pine through a fixed PineTS worker, generates a
TradingView Basic parity dashboard, emits standard JSONL-compatible traces,
compares traces with exact/tolerance contracts, and generates Pine only through
registered adapters.

The service does not claim to be TradingView, translate arbitrary Pine to Python,
optimize strategies, or approve promotion. Its local results always retain
`TRADINGVIEW_REVIEW_REQUIRED`.

## Runtime architecture

| Layer | Implementation | Trust boundary |
|---|---|---|
| HTTP/CLI | FastAPI and `pine2python` CLI | Validated Pydantic requests and shaped errors |
| Analysis | Pynescript 0.3.0 | Complete/partial parse is explicit; AST stays in artifacts |
| Runtime | PineTS 0.9.29 in fixed `worker.mjs` | Caller candles only; no shell; timeout and size bounds |
| Evidence | Content-addressed immutable bundles | Request hash controls identity and collision behavior |
| Proof | Triple rolling fingerprints plus 8 segments | Comparison fingerprints, not cryptographic hashes |
| Generation | Registered adapters | Unknown adapters and unsupported semantics fail closed |

## Public operations

| HTTP | CLI | Output |
|---|---|---|
| `GET /v1/version` | `capabilities` includes version | Service and schema versions |
| `GET /v1/capabilities` | `capabilities` | Support matrix and generator registry |
| `POST /v1/analyses` | `analyze` | Parser, inventory, temporal risks, blockers |
| `POST /v1/proofs` | `proof` | Expected dashboard, instrumented Pine, local trace |
| `POST /v1/tradingview-observations` | `observe` | Exact dashboard comparison and acceptance state |
| `POST /v1/runtime-executions` | `runtime` | PineTS result and standard trace |
| `POST /v1/parity-comparisons` | `parity` | Alignment, mismatches, first divergence |
| `POST /v1/generators/{adapter_id}` | `generate` | Generated source, settings, trace contract |

## Supported capability matrix

| Capability | Status |
|---|---|
| Pine v5/v6 parsing | Pynescript-supported; partial parse remains visible |
| Static inventory and temporal-risk candidates | Supported |
| Caller-supplied standard OHLCV execution | Supported for the declared PineTS subset |
| Dataset/segment proof fingerprints | Supported and independently implemented in Python/Pine |
| Declared feature/signal/state stream capture | Supported |
| Standard market/plot/trade trace | Supported |
| Exact and tolerance trace comparison | Supported |
| `ma_cross_v1` generation | Supported sample adapter |
| `ma_cross_atr_stop_v1` generation | Supported for `next_bar_open` |
| `request.*`, `varip`, imports, realtime semantics | Local execution blocked; TradingView review required |
| Arbitrary Pine-to-Python translation | Unsupported |
| MT5 proxy generation | Unsupported and rejected |

## Dependencies and licenses

| Dependency | Locked version | License |
|---|---:|---|
| PineTS / `pinets` | 0.9.29 | AGPL-3.0-only / commercial option |
| Pynescript | 0.3.0 | LGPL-3.0-or-later |
| ANTLR4 Python runtime | 4.13.2 | BSD-3-Clause |
| FastAPI | 0.115.14 | MIT |
| Pydantic | 2.12.5 | MIT |

`package-lock.json`, `requirements-lock.txt`, `LICENSE`, `NOTICE.md`, and
`third_party/` preserve the current dependency posture. The service is
AGPL-3.0-only while PineTS is used under its AGPL license. A closed-source or
hosted release needs a license review or a PineTS commercial agreement.

## Validation

The reusable golden regression is:

```powershell
.venv\Scripts\python agentic\testscripts\pine2python_vertical.py
```

It analyzes and generates `ma_cross_atr_stop_v1`, executes 240 deterministic
15-minute bars through PineTS, creates a local proof/trace, runs the corresponding
StrategyLab Python engine, and compares exact market plus position lifecycle. The
current result is `PARITY_PASS` with 240/240 aligned rows and no divergence.

The deterministic sample proof ID is
`tradingview-proof_127d8c847d78c12cbf03`, with service-relative artifact path
`tradingview-proof/12/127d8c847d78c12cbf03bc61c970311ba4bf65d7af461c49d729c7fa0e0ecdac`.

Other acceptance commands:

```powershell
npm test --prefix services\pine2python
.venv\Scripts\python -m unittest discover -s services\pine2python\tests -p "test_*.py"
```

The final acceptance run passed all 10 Python service tests and both Node worker
tests. Ruff, Ruff formatting, Mypy, Python compilation, JavaScript syntax, and
both Compose configuration parses also passed.

Dockerfile and Compose configuration parse successfully, both production images
build, and the container regression passes. The service is healthy on the private
Compose network, is not published to the host, runs as `pine2python` with a
read-only root filesystem and all capabilities dropped, and persists artifacts
through its named volumes. A StrategyLab container executed the 240-row fixture
over HTTP against Pine2Python twice with identical artifact IDs and
`PARITY_PASS`.

## Known limitations

- PineTS native Pine support is experimental and cannot replace official
  TradingView compilation or feed behavior.
- The Basic dashboard proves a maximum 5,000-bar explicit window.
- Local stream capture is not an independent parity result unless caller trace
  rows supplied the expected stream values.
- The first StrategyLab adapter does not implement `mt5_bar_proxy`, dynamic risk
  sizing, advanced time filters, breakeven moves, or hybrid exits.
- TradingView acceptance remains a user action backed by a screenshot hash.
