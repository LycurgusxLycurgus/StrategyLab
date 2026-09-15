# Pine2Python Mini-Repository Build Specification

## Instruction to the Codex instance receiving this document

You are responsible for creating a complete, working mini-repository named **Pine2Python** directly inside StrategyLab at `services/pine2python/`. Treat this document as the implementation contract and source of truth for the first production-capable version. Read the entire document before editing files. Inspect every upstream dependency you plan to use, record the exact versions and licenses you find, and implement the system rather than merely scaffolding it. Do not stop after producing an architecture diagram, placeholder endpoints, mocked runtime responses, or a README that describes work that does not exist.

The finished repository must run locally, run in a container, expose a stable HTTP API and CLI, analyze Pine Script source, execute the supported Pine subset against caller-supplied OHLCV data, emit LLM-friendly artifacts, compare Pine-derived traces with Python-derived traces, and generate Pine for explicitly supported strategy adapters. It must report unsupported constructs and semantic uncertainty honestly. It must never claim that local execution is official TradingView verification.

When a detail in this document conflicts with an observed upstream API, preserve the intent of the contract and adapt the implementation. Record the adaptation in `docs/implementation-decisions.md`, add a regression test, and keep the public API stable whenever possible. Do not silently omit a required capability.

### 2026-07-23 controlling amendment

The service is built and tested **in place inside StrategyLab from the first
commit**. It remains an independently runnable package and container, but there is
no build-elsewhere, publish, copy, or vendor-later step. Where later text says
"repository", read it as the independently buildable
`StrategyLab/services/pine2python/` boundary.

Pine2Python is also the evidence engine for a StrategyLab Pine Workbench that
starts before Phase 1. The workbench supports greenfield strategy creation,
source-licensed adaptation of public Pine, and indicator-first development when a
strategy depends on a complex reusable indicator. LLMs may propose and repair Pine
or Python using the evidence packages, but the deterministic service never claims
to translate arbitrary code faithfully by itself.

TradingView chart-data CSV export is **not an accepted dependency**. A supplied
Basic-plan screenshot proves that export is paywalled. Official corroboration uses
a generated on-chart **TradingView Parity Proof Dashboard** over an explicit
`input.time` window. The dashboard presents cross-runtime fingerprints for:

- source/settings/profile identity and the exact test window;
- normalized OHLC dataset identity, bar count, and first/last timestamp;
- declared feature, state, signal, rejection, and order-intent streams;
- closed-trade lifecycle fields and official `strategy.*` totals where applicable;
- multiple time segments for mismatch localization.

The same fingerprint algorithm runs in Pine, PineTS, and Python. Prices are
normalized to integer ticks and all arithmetic stays inside values exactly
representable by each runtime. Use at least three independent rolling
fingerprints; describe them as comparison fingerprints, never cryptographic
hashes. An exact execution claim is forbidden unless the TradingView OHLC
fingerprints match the local dataset fingerprints first.

The fast human path is one screenshot of the dashboard after paste/run and setting
the supplied inputs. Request an additional chart or Strategy Tester screenshot
only when a visual lifecycle or broker-emulator claim cannot be encoded. The
service can prepare expected values and compare user-supplied observed values, but
only the user/StrategyLab acceptance action may award a TradingView acceptance
status. Do not use TradingView browser automation, alerts, webhooks, or scraping as
the default substitute.

Ship a versioned `tradingview_profile`. Its default is `basic_v1`, bounded to the
history and execution limits of the current Basic plan; the proof generator must
reject oversized windows rather than silently truncate them.

---

## 1. Repository identity and naming decision

Use **Pine2Python** as the repository name, `pine2python` as the Python package and command name, and `pine2python` as the Docker service name. The name is intentionally broader than a literal source-to-source compiler. It describes the practical transition from Pine-based strategy definitions into structured artifacts that Python research systems can inspect, execute, compare, and eventually port.

The repository is not a universal Pine-to-Python compiler. Arbitrary Pine Script contains platform-specific state, broker-emulator behavior, drawing lifecycles, realtime rollback semantics, proprietary data assumptions, and constructs that cannot be translated safely by syntax substitution. Pine2Python must therefore center its design around **analysis, normalization, capability reporting, deterministic local execution where supported, trace extraction, parity comparison, and adapter-driven generation**. It may produce Python scaffolds or an intermediate representation, but it must never label an unverified scaffold as a faithful translation.

The one-sentence product description is:

> Pine2Python is a local-first Pine Script analysis, execution, trace, parity, and adapter-generation service for Python strategy research systems.

Use that description consistently in the README, API metadata, package metadata, and container labels.

---

## 2. Why this repository exists

Pine Script is convenient for chart-centered strategy creation, visual inspection, TradingView distribution, and alerts. It is difficult to use as the sole research environment when a team needs reproducible automation, LLM-assisted code analysis, multi-asset testing, detailed state traces, automated regression tests, or systematic Pine-to-Python parity work.

The direct pain point is the gap between a Pine source file and the evidence needed to port or verify it. Raw Pine source is compact and stateful. An LLM can read it, yet important semantics remain implicit: every expression may be a time series, historical indexing changes meaning bar by bar, `var` and `varip` alter persistence, `request.security()` changes time ownership, strategy orders have broker-emulator timing, and realtime execution can roll state back. TradingView exposes the authoritative behavior through its own compiler and runtime, while programmatic access to the complete execution state is limited.

Pine2Python reduces this gap. It converts a source file into a durable evidence package containing normalized source, AST or partial parse output, semantic inventories, temporal-risk findings, capability status, a local execution trace when supported, and a machine-readable parity report against another engine. This package is designed for both humans and LLMs. It gives a strategy-research system stable facts to reason about without pretending that an unofficial runtime is TradingView itself.

---

## 3. Ground-truth hierarchy

Every implementation decision and every API response must follow this hierarchy:

1. **Official TradingView behavior is authoritative for Pine Script.** Official Pine documentation and an actual TradingView compile/run are the external source of truth.
2. **Frozen source, settings, data identity, and test fixtures define the comparison contract.** A parity claim without these frozen inputs is invalid.
3. **Pine2Python local runtime output is evidence, not official verification.** It can establish local reproducibility and compare two implementations under a declared contract.
4. **Static analysis can identify risk and structure.** It cannot prove runtime correctness by itself.
5. **Unsupported or uncertain semantics must remain visible.** Never repair, approximate, or suppress them without an explicit status and artifact.

Use the following verification vocabulary throughout the repository:

| Status | Meaning |
|---|---|
| `SOURCE_ACCEPTED` | Input was received, hashed, and stored. No syntax or semantic claim is implied. |
| `PARSE_COMPLETE` | The configured parser produced a complete AST without reported recovery or unsupported syntax. |
| `PARSE_PARTIAL` | Useful structure was extracted, but parsing was incomplete or fallback analysis was used. |
| `STATIC_REVIEW_COMPLETE` | All configured static checks ran and produced a report. Findings may still block execution. |
| `LOCAL_RUNTIME_SUPPORTED` | The current runtime adapter declares support for the required constructs. |
| `LOCAL_RUNTIME_COMPLETE` | The script executed locally against the frozen dataset and produced an artifact bundle. |
| `SIGNAL_PARITY_PASS` | Declared signal fields matched under the supplied alignment and tolerance contract. |
| `EXECUTION_PARITY_PASS` | Declared order, fill, position, and exit fields matched under the supplied contract. |
| `TRADINGVIEW_SIGNATURE_MATCH` | User-supplied values from the on-chart proof dashboard exactly match the expected profile, window, dataset, and declared stream fingerprints. This is strong external evidence, not a universal Pine-runtime claim. |
| `TRADINGVIEW_SIGNATURE_MISMATCH` | At least one supplied TradingView dashboard value differs. Dataset mismatches block execution comparison; segmented fingerprints localize the next inspection. |
| `TRADINGVIEW_REVIEW_REQUIRED` | The remaining claims require TradingView or human evidence. |
| `TRADINGVIEW_ACCEPTED` | An external caller supplied an explicit accepted TradingView evidence record. Pine2Python does not self-award this status. |

Avoid a single `verified: true` field. Verification must always identify its level and evidence.

---

## 4. Upstream dependency snapshot and mandatory due diligence

As of July 23, 2026, the intended implementation starts from these upstream projects:

| Dependency | Intended role | Observed status at specification time |
|---|---|---|
| `LuxAlgo/PineTS`, npm package `pinets` | Native Pine v5/v6 transpilation and local runtime | Version `0.9.29`; native Pine support described as experimental; strategy namespace present; AGPL-3.0-only with a commercial-license option |
| `pinecoders/pynescript` | Python/ANTLR parsing, AST dump, and normalized unparse | CLI and library APIs expose parse, dump, and unparse; LGPL-3.0-or-later |
| TradingView Pine documentation | Authoritative semantic reference | Bar-by-bar execution, realtime rollback, `varip`, order-fill recalculation, `request.security()`, and broker-emulator behavior remain platform-defining concerns |

Before writing application code, perform and record an upstream capability spike. Pin exact dependency versions using lockfiles. Do not use floating `latest` dependencies. The spike must answer these questions with executable fixtures and saved output:

| Question | Required evidence |
|---|---|
| Can the pinned `pynescript` parse representative Pine v5 and v6 strategies? | Source fixtures, AST artifacts, normalized source, and parser exit status |
| Which v6 syntax fails or recovers partially? | Minimal failing fixtures and capability flags |
| Can the pinned `pinets` execute custom caller-supplied OHLCV arrays without network access? | Runtime fixture and stable output |
| What does `pinets.run()` return for an indicator? | Captured and normalized runtime object |
| What does it return for a strategy using `strategy.entry`, `strategy.exit`, and reversal? | Captured object, including whether orders/trades are directly available |
| Are `request.security()`, persistent variables, arrays, maps, and user-defined functions supported in the required forms? | One focused fixture per construct |
| Can source inputs be overridden programmatically? | Test and documented mechanism |
| Can execution be interrupted reliably on timeout? | Deliberately expensive fixture and terminated worker test |

If PineTS does not expose reliable order events for arbitrary strategies, do not fabricate them. Implement capability-aware extraction and the standard instrumentation contract described later in this document. The service may still execute plots and declared trace outputs while reporting order extraction as unsupported.

Create `docs/upstream-capability-snapshot.md` containing the exact dependency versions, commit or package identifiers, licenses, commands run, fixture names, results, known gaps, and the date of verification. Add the upstream license texts or required notices under `third_party/` according to their terms.

### Licensing gate

The default implementation assumes Pine2Python itself will be released under **AGPL-3.0-only** because its core runtime dependency is AGPL and the intended use includes a network service. Add a clear `LICENSE`, `NOTICE.md`, and a README licensing section. Do not provide legal conclusions beyond the repository facts. State that any proprietary or closed-source deployment must review the PineTS commercial-license path and all transitive obligations before use.

Pynescript is intended as a separately identifiable library dependency. Preserve its notices and comply with its LGPL terms. Do not copy upstream source into this repository unless a documented reason makes vendoring necessary.

---

## 5. Scope of the first complete version

The first complete version must provide a coherent vertical slice. It must accept Pine source and frozen OHLCV data, analyze the source, decide whether local execution is supportable, run the local adapter when permitted, emit a standard trace bundle, compare that trace with a caller-supplied Python trace, and expose all operations through HTTP and CLI.

### Required capabilities

The implementation must include:

| Capability | Required behavior |
|---|---|
| Source ingestion | Accept source inline or from an allowed local path, normalize line endings, validate size, compute SHA-256, and preserve the original bytes |
| Parsing | Use Pynescript through an adapter, persist AST output, normalize source when possible, and distinguish complete from partial parsing |
| Static analysis | Extract declarations, inputs, functions, assignments, stateful variables, history references, timeframe requests, strategy operations, plots, alerts, drawings, and unsupported constructs |
| Temporal-risk analysis | Flag lookahead patterns, future leakage candidates, unconfirmed-bar dependence, dynamic timeframe requests, `varip`, same-bar ambiguity, and likely repainting behavior |
| Capability report | Map observed constructs against parser, runtime, trace, and generator support |
| Local runtime | Execute supported source against caller-supplied OHLCV data with no runtime network access |
| Trace bundle | Emit metadata, aligned market bars, accessible features, trace-contract outputs, runtime plots, strategy events when genuinely exposed, warnings, and content hashes |
| Parity comparison | Align two traces, apply exact and tolerance policies, identify first divergence, summarize mismatch clusters, and emit machine-readable and Markdown reports |
| Generation registry | Generate Pine only for registered adapters with tests; include one complete sample adapter and a stable plugin interface |
| CLI | Provide commands equivalent to the public HTTP operations |
| Container | Build a non-root image containing Python, Node, pinned dependencies, the API, CLI, and isolated worker |
| Documentation | Explain installation, architecture, API, trace contract, capability semantics, security, and licensing |
| Tests | Cover parsing, static analysis, runtime, trace normalization, parity, generation, failure handling, security limits, and container health |

### Explicit non-goals

The first version must not claim to:

- compile Pine with TradingView’s official compiler;
- automate the TradingView web UI;
- require paid TradingView chart-data export, alerts, or webhooks;
- reproduce every broker-emulator or realtime-tick behavior;
- translate arbitrary Pine into production-ready Python automatically;
- infer data-feed parity from matching symbol names;
- optimize strategies or choose economic parameters;
- download market data during execution;
- execute user-supplied JavaScript, Python, shell commands, imports, or arbitrary file paths;
- decide whether a strategy is profitable, robust, or production-ready.

These boundaries belong in the README and API capability response.

---

## 6. Architectural shape

Build one repository and one deployable container with three internal layers:

```text
HTTP API and CLI
        │
        ▼
Python orchestration layer
    source registry
    parser adapter
    static analyzer
    capability engine
    artifact manager
    parity comparator
    generator registry
        │
        ├───────────────┐
        ▼               ▼
Pynescript adapter   Isolated Node worker
                     pinned PineTS runtime
                     no network data provider
```

The FastAPI process must never evaluate transpiled JavaScript in-process. Local Pine execution occurs in a short-lived Node subprocess launched through an explicit executable and argument list. Do not invoke a shell. Pass request data through bounded files in a per-job working directory. Enforce a wall-clock timeout, output-size limit, source-size limit, bar-count limit, and allowed-path root. Capture stdout and stderr separately. Delete temporary working directories unless artifact retention is requested and allowed.

Use the PineTS library directly through a small owned Node worker such as `runtime/worker.mjs`. Do not make the service contract depend on human-oriented CLI output. The worker should read a request JSON file, read a source file, read normalized candles, invoke the pinned `pinets` API, and write one result JSON file. Its stdout is for structured logs only; its result file is the data contract.

The Python layer owns all public schemas and normalization. Upstream runtime objects are never returned directly to callers because they may change across releases. Preserve the raw upstream output as a diagnostic artifact when configured, then map it into Pine2Python’s versioned schemas.

---

## 7. Required repository layout

Create this structure unless the language tooling requires a small adjustment. Preserve the separation of contracts, adapters, services, and tests.

```text
Pine2Python/
├── README.md
├── AGENTS.md
├── LICENSE
├── NOTICE.md
├── pyproject.toml
├── uv.lock                         # or another exact Python lockfile
├── package.json
├── package-lock.json
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .gitignore
├── .env.example
├── Makefile
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── trace-contract.md
│   ├── capability-model.md
│   ├── security.md
│   ├── licensing.md
│   ├── upstream-capability-snapshot.md
│   └── implementation-decisions.md
├── third_party/
│   ├── README.md
│   └── notices/
├── src/pine2python/
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py
│   ├── cli.py
│   ├── config.py
│   ├── errors.py
│   ├── logging.py
│   ├── hashing.py
│   ├── paths.py
│   ├── models/
│   │   ├── common.py
│   │   ├── source.py
│   │   ├── analysis.py
│   │   ├── capability.py
│   │   ├── dataset.py
│   │   ├── execution.py
│   │   ├── trace.py
│   │   ├── parity.py
│   │   └── generation.py
│   ├── services/
│   │   ├── source_service.py
│   │   ├── analysis_service.py
│   │   ├── execution_service.py
│   │   ├── parity_service.py
│   │   └── generation_service.py
│   ├── parsers/
│   │   ├── base.py
│   │   ├── pynescript_adapter.py
│   │   └── fallback_scanner.py
│   ├── analysis/
│   │   ├── ast_walk.py
│   │   ├── inventory.py
│   │   ├── temporal.py
│   │   ├── orders.py
│   │   ├── timeframes.py
│   │   ├── trace_contract.py
│   │   └── capabilities.py
│   ├── runtime/
│   │   ├── base.py
│   │   ├── pinets_adapter.py
│   │   ├── process_runner.py
│   │   └── normalization.py
│   ├── traces/
│   │   ├── writer.py
│   │   ├── reader.py
│   │   ├── align.py
│   │   └── compare.py
│   ├── generators/
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── ma_cross_atr_stop_v1/
│   │       ├── adapter.py
│   │       ├── template.pine.j2
│   │       └── schema.py
│   └── artifacts/
│       ├── manager.py
│       └── manifest.py
├── runtime/
│   ├── worker.mjs
│   ├── normalize-result.mjs
│   └── README.md
├── schemas/
│   ├── trace-bundle-v1.schema.json
│   ├── parity-contract-v1.schema.json
│   └── capability-report-v1.schema.json
├── fixtures/
│   ├── pine/
│   ├── candles/
│   ├── traces/
│   └── expected/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   ├── security/
│   └── container/
└── scripts/
    ├── verify_upstreams.py
    ├── regenerate_golden.py
    └── smoke_test.sh
```

`AGENTS.md` must summarize the invariants a future coding agent must preserve: capability honesty, immutable hashes, no shell execution, no runtime network access, versioned schemas, no silent semantic repair, and no TradingView-verification claims.

---

## 8. Configuration and runtime limits

Create a typed settings object loaded from environment variables. The defaults must be safe for local development and easy to override in StrategyLab later.

| Variable | Default | Meaning |
|---|---:|---|
| `P2P_HOST` | `0.0.0.0` | API bind host |
| `P2P_PORT` | `8080` | API port |
| `P2P_ARTIFACT_ROOT` | `/var/lib/pine2python/artifacts` | Durable output root |
| `P2P_INPUT_ROOT` | `/var/lib/pine2python/input` | Only root from which path-based input may be read |
| `P2P_TMP_ROOT` | `/tmp/pine2python` | Per-request working directories |
| `P2P_MAX_SOURCE_BYTES` | `1000000` | Maximum source size |
| `P2P_MAX_BARS` | `1000000` | Maximum bars per execution request |
| `P2P_MAX_INLINE_BARS` | `5000` | Maximum bars accepted inline over HTTP |
| `P2P_EXECUTION_TIMEOUT_SECONDS` | `60` | Node worker wall-clock limit |
| `P2P_MAX_RESULT_BYTES` | `268435456` | Maximum worker result size |
| `P2P_RETAIN_RAW_RUNTIME` | `false` | Whether raw PineTS output is retained |
| `P2P_LOG_LEVEL` | `INFO` | Structured application log level |
| `P2P_ALLOW_GENERATION` | `true` | Feature flag for adapter generation |

Validate every value at startup. The `/health/ready` endpoint must fail when the Node worker cannot import the pinned `pinets` package, the Python parser cannot import, schema files are missing, or artifact paths are unwritable.

---

## 9. Public data contracts

All public schemas must include `schema_version`. Use ISO 8601 timestamps in UTC with `Z`. Use SHA-256 prefixed as `sha256:<hex>`. Never use local filesystem paths as permanent public identifiers. Return artifact URIs rooted in the service, such as `artifact://analyses/<analysis_id>/analysis.json`, while allowing an integration layer to resolve those URIs to mounted paths.

### Source envelope

```json
{
  "schema_version": "1.0",
  "source": {
    "kind": "inline",
    "text": "//@version=6\nstrategy(...)"
  },
  "requested_checks": [
    "parse",
    "inventory",
    "temporal",
    "orders",
    "timeframes",
    "capabilities"
  ],
  "labels": {
    "strategy_id": "btc_intraday",
    "version_id": "ver_btc_intraday_parent"
  }
}
```

Also permit `kind: "path"` with a path relative to `P2P_INPUT_ROOT`. Reject absolute paths, `..`, symlink escapes, device files, and paths outside the allowed root.

### Dataset manifest

```json
{
  "schema_version": "1.0",
  "dataset_id": "ds_abc123",
  "content_hash": "sha256:...",
  "format": "csv",
  "relative_path": "datasets/ds_abc123.csv",
  "symbol": "BTCUSDT",
  "venue": "Binance Spot",
  "timeframe": "15m",
  "timezone": "UTC",
  "timestamp_semantics": "bar_open",
  "columns": {
    "timestamp": "ts",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume"
  },
  "row_count": 40000,
  "first_timestamp": "2024-01-01T00:00:00Z",
  "last_timestamp": "2025-02-20T15:45:00Z",
  "missing_bar_policy": "preserve",
  "normalization_version": "1"
}
```

Pine2Python must independently hash the referenced file and reject a mismatch. It must validate sorted unique timestamps, numeric OHLCV values, `high >= max(open, close, low)`, `low <= min(open, close, high)`, finite numbers, and row-count consistency. Report data-quality findings rather than silently fixing bars. A caller may explicitly request deduplication or sorting through a future normalization operation, but execution uses the frozen identity supplied for the parity contract.

---

## 10. Source ingestion and artifact immutability

For every accepted source, create an immutable source record containing:

- the original bytes;
- normalized UTF-8 source with LF line endings;
- source hash for original bytes and normalized text;
- detected Pine version;
- declaration type (`indicator`, `strategy`, `library`, or unknown);
- ingestion timestamp;
- caller labels;
- service and dependency versions.

Use content-addressed storage where practical. Repeated analysis of the same normalized source and analyzer version may reuse artifacts, but the response must identify whether a cached result was used. Cache keys must include all analyzer versions and feature flags. Do not reuse old capability results after dependency upgrades.

The artifact manifest must contain hashes for every file it references. An artifact is written to a temporary directory and atomically renamed after successful completion. Partial artifacts remain marked `FAILED` and are never returned as complete evidence.

---

## 11. Parser adapter and fallback behavior

Define a parser protocol independent of Pynescript. The protocol returns a normalized `ParseResult` with:

```text
status
parser_name
parser_version
pine_version
ast_format
ast_artifact_uri
normalized_source_artifact_uri
syntax_findings
unsupported_nodes
recovery_used
source_locations_available
```

The Pynescript adapter should use its library API when stable and its CLI only when necessary. Catch parser exceptions and preserve a sanitized error with line/column information. Never rewrite the source to make it parse unless the caller requests a separate repair operation, which is outside the first-version scope.

When complete parsing fails, invoke a conservative fallback scanner. The fallback scanner is not a parser and must never set `PARSE_COMPLETE`. It should extract only high-confidence lexical facts while respecting comments and string literals as much as practical. It may identify the version directive, declaration call, input calls, namespaces, strategy order operations, `request.*` calls, history-index tokens, `var`/`varip`, plot and drawing calls, user-defined function headers, and imports. Every fallback fact includes a source range and confidence.

The analysis service should continue after a partial parse when checks can run safely, but execution capability may become `UNKNOWN` or `UNSUPPORTED` based on the missing structure.

---

## 12. Static semantic inventory

The semantic inventory is designed to be directly useful to an LLM and to a port engineer. Produce both `inventory.json` and `inventory.md`. The JSON must include stable IDs and source locations.

At minimum, inventory these categories:

| Category | Required fields |
|---|---|
| Declaration | script type, title, overlay, declared calculation flags, pyramiding, capital, commission, slippage, bar magnifier, order timing arguments |
| Inputs | variable name, input function, type, default, bounds, options, title, group, active condition, source location |
| Variables | declaration mode, type if available, initialization, reassignment sites, scope, historical references, statefulness |
| Functions | name, parameters, return form, calls, stateful operations, source range |
| Dependencies | variable-to-variable and function-call dependency edges |
| Timeframes | chart timeframe assumptions, input timeframes, every `request.*` call, symbols, lookahead, gaps, offsets, dynamic scope |
| Orders | `strategy.entry`, `strategy.order`, `strategy.exit`, `strategy.close`, `strategy.close_all`, cancellation, risk settings, sizing arguments |
| Visuals | plots, plot shapes, labels, lines, boxes, tables, backgrounds, colors, display flags |
| Alerts and logs | alert calls, alert conditions, log calls, message expressions |
| Collections and user types | arrays, maps, matrices, user-defined types, methods |
| External dependencies | imports and libraries |

Build a dependency graph suitable for LLM consumption. Nodes should use stable identifiers, and edges should describe `reads`, `writes`, `calls`, `historical_read`, `timeframe_request`, `order_dependency`, or `visual_dependency`. Persist it as JSON; Graphviz output may be optional.

---

## 13. Temporal, repainting, and execution-risk analysis

Static risk findings require careful wording. A pattern can be a risk candidate without being a proven bug. Every finding contains a code, severity, confidence, source location, evidence, why it matters, and a concrete verification method.

Implement at least these checks:

| Code | Detection intent |
|---|---|
| `VARIP_REALTIME_STATE` | Detect `varip` and explain that intrabar persistence may not reproduce in historical-only local execution |
| `CALC_ON_EVERY_TICK` | Detect strategy realtime recalculation settings |
| `CALC_ON_ORDER_FILLS` | Detect additional executions after fills |
| `PROCESS_ORDERS_ON_CLOSE` | Record order timing change |
| `BAR_MAGNIFIER_DEPENDENCY` | Detect declared bar magnifier use |
| `SECURITY_LOOKAHEAD_ON` | Detect `barmerge.lookahead_on`; distinguish offset-safe idioms from obvious future-leak candidates |
| `HTF_DEVELOPING_VALUE` | Flag higher-timeframe values that may use an incomplete current HTF bar |
| `DYNAMIC_REQUEST` | Identify request calls in local scopes or with dynamic symbol/timeframe expressions |
| `NEGATIVE_OR_DYNAMIC_HISTORY` | Flag suspicious history indexing |
| `PIVOT_CONFIRMATION_DELAY` | Identify pivot functions or symmetric lookback patterns whose values become known after future bars |
| `UNCONFIRMED_BAR_DECISION` | Detect decisions gated by realtime or missing confirmation where relevant |
| `SAME_BAR_ENTRY_EXIT_AMBIGUITY` | Identify entry and exit conditions that may be true on the same bar without declared order policy |
| `STOP_TARGET_INTRABAR_AMBIGUITY` | Identify strategies where both stop and target may lie inside one OHLC bar |
| `SESSION_TIMEZONE_DEPENDENCY` | Detect session and timezone logic requiring exact calendar semantics |
| `SYNTHETIC_CHART_RISK` | Detect ticker transformations such as Heikin Ashi, Renko, or other synthetic sources |
| `IMPORTED_LIBRARY_UNRESOLVED` | Report imports not available to the local runtime |
| `DRAWING_STATE_UNVERIFIED` | Drawing-object behavior cannot be verified from numeric runtime output alone |

Do not label all `request.security()` usage as repainting. The report must explain the exact expression, timeframe relation, lookahead setting, and offset pattern. Keep the analysis evidence-based.

---

## 14. Capability model

A capability report answers four separate questions for every observed feature:

1. Can the parser represent it?
2. Can static analysis understand it?
3. Can the local runtime execute it?
4. Can Pine2Python extract enough evidence to compare it?

Use statuses `SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `UNKNOWN`, and `NOT_USED`. Include the adapter version and a reason.

```json
{
  "schema_version": "1.0",
  "source_hash": "sha256:...",
  "summary": {
    "parse": "PARTIAL",
    "static_analysis": "SUPPORTED",
    "local_execution": "PARTIAL",
    "signal_trace": "SUPPORTED",
    "order_trace": "UNKNOWN",
    "drawing_trace": "UNSUPPORTED"
  },
  "features": [
    {
      "feature": "request.security",
      "observed": true,
      "parser": "SUPPORTED",
      "runtime": "PARTIAL",
      "trace": "SUPPORTED",
      "reason": "Pinned runtime supports completed-bar HTF fixture; dynamic requests remain unverified."
    }
  ],
  "blocking_findings": [],
  "required_external_verification": [
    "official_compile",
    "drawing_lifecycle",
    "broker_emulator_fill_parity"
  ]
}
```

Local execution proceeds only when no configured blocking feature is `UNSUPPORTED`. An explicit `force_partial` flag may allow a research run, but the result status remains partial and repeats every unsupported feature prominently.

---

## 15. Standard Pine trace instrumentation contract

Arbitrary Pine scripts do not necessarily expose internal decisions as plots, and an unofficial runtime may not expose every strategy event. Pine2Python therefore supports two trace modes.

**Passive mode** extracts what the runtime naturally exposes: plots, plot shapes, accessible context, and strategy events confirmed by the upstream capability spike. It does not alter source.

**Instrumented mode** relies on source that intentionally emits hidden, namespaced trace plots. This is the preferred mode for Pine generated by StrategyLab or another cooperating system. Define the naming convention:

```text
__p2p.feature.<name>
__p2p.state.<name>
__p2p.signal.<name>
__p2p.order_intent.<name>
__p2p.reject.<name>
__p2p.debug.<name>
```

A generated Pine strategy can emit numeric or boolean series using plots with `display = display.none` when supported. The runtime normalizer maps these plot names into typed trace fields. The source analysis report identifies which expected trace fields are present and which are absent.

Do not automatically inject arbitrary expressions into imported source in the first version. Source instrumentation can change Pine scope, history buffers, execution cost, and semantics. A later explicit source-transformation operation may be added with its own proof requirements.

Create `docs/trace-contract.md` explaining how a cooperating Pine template should expose signals, state, and rejection reasons. Include a complete instrumented example fixture.

---

## 16. Local execution pipeline

An execution request references a completed analysis and a frozen dataset. The service performs these steps in order:

1. Resolve and verify the analysis artifact and source hash.
2. Resolve the dataset under the allowed input root and recompute its hash.
3. Validate bars and normalize them into the exact candle shape expected by the pinned PineTS API.
4. Re-evaluate runtime capability using the analysis result and current adapter version.
5. Create an isolated working directory and copy only the required source and candle files.
6. Write a bounded worker request containing source path, candle path, input overrides, trace configuration, and output path.
7. Launch `node runtime/worker.mjs <request-file>` through `asyncio.create_subprocess_exec` or an equivalent no-shell API.
8. Apply timeout and output-size enforcement. Terminate, then kill if necessary.
9. Validate the worker result against an internal schema.
10. Normalize upstream values into the versioned Pine2Python trace contract.
11. Write the artifact bundle atomically and return a summary.

The runtime worker must not fetch Binance or any other provider. Construct `new PineTS(candles)` or the verified equivalent using caller-supplied data. Reject scripts or runtime paths that attempt network access. The container should run with no outbound network in the StrategyLab deployment; standalone compose should document how to enable the same restriction.

### Input overrides

Pine input overrides are useful only when the pinned runtime supports them reliably. Implement them behind a capability flag. Preserve original defaults in the analysis report and record every override in the execution manifest. Reject unknown input names and invalid types rather than silently ignoring them.

### Runtime identity

Every execution manifest contains:

```text
pine2python version
Python version
Node version
Pynescript version
PineTS version
source hashes
dataset hash
runtime adapter version
trace schema version
input overrides
execution timeout
capability status
```

This information is required for reproducibility and cache invalidation.

---

## 17. Trace bundle schema

Use a directory bundle rather than one enormous JSON object. The canonical first-version format is newline-delimited JSON because it is easy to stream, diff, inspect, and consume without a heavy dataframe dependency. Add optional Parquet export later through a versioned adapter; do not make Parquet a prerequisite for the first complete version.

```text
artifact://executions/<execution_id>/
├── manifest.json
├── summary.json
├── bars.jsonl
├── findings.json
├── runtime-stderr.txt
└── raw-runtime.json              # only when retention is enabled
```

Each `bars.jsonl` row follows this logical structure:

```json
{
  "bar_index": 1000,
  "timestamp": "2025-01-01T12:00:00Z",
  "market": {
    "open": 95000.0,
    "high": 95600.0,
    "low": 94700.0,
    "close": 95400.0,
    "volume": 121.4
  },
  "features": {
    "fast_ma": 95114.32,
    "slow_ma": 94881.73,
    "atr": 802.17
  },
  "state": {
    "position": "flat",
    "pending_entry": null,
    "stop_price": null
  },
  "signals": {
    "long_entry": true,
    "short_entry": false,
    "exit": false
  },
  "order_intents": [
    {
      "id": "Long",
      "operation": "entry",
      "side": "long",
      "order_type": "market",
      "execution_policy": "next_available_tick"
    }
  ],
  "orders": [],
  "plots": {},
  "rejections": [],
  "warnings": []
}
```

Fields absent from the runtime remain absent or null according to the JSON schema; never invent state from static source. `order_intents` may come from instrumented trace outputs. `orders` and fills require genuine runtime evidence.

The `summary.json` contains row count, warmup boundary if known, counts of true signals, accessible plots, null-rate statistics, first and last timestamp, runtime warnings, and trace-field coverage.

---

## 18. Python trace import contract

Parity comparison must work with traces produced outside Pine2Python. Support an import descriptor that maps JSONL or CSV columns into the standard trace field paths. A cooperating Python engine should ideally write the same `TraceBundle` schema directly.

The importer validates:

- trace schema version;
- dataset hash and identity;
- strictly increasing timestamps;
- duplicate timestamps;
- field types;
- market-bar equality when market data is included;
- required comparison fields;
- source engine identity.

If two traces use different datasets, parity must fail before field comparison unless the caller explicitly supplies an approved data-divergence contract. A symbol and timeframe match is never sufficient.

---

## 19. Parity contract and comparator

A parity request contains a reference trace, a candidate trace, alignment rules, fields, tolerances, null semantics, and optional warmup exclusion.

```json
{
  "schema_version": "1.0",
  "reference_trace_uri": "artifact://executions/exe_pine/",
  "candidate_trace_uri": "artifact://imports/exe_python/",
  "alignment": {
    "key": "timestamp",
    "join": "inner",
    "require_equal_market_bars": true,
    "ignore_before": "2024-02-01T00:00:00Z"
  },
  "fields": [
    {
      "path": "signals.long_entry",
      "mode": "exact"
    },
    {
      "path": "features.atr",
      "mode": "numeric",
      "absolute_tolerance": 0.000001,
      "relative_tolerance": 0.0000001,
      "null_policy": "equal_only"
    },
    {
      "path": "state.position",
      "mode": "exact"
    }
  ],
  "acceptance": {
    "max_mismatches": 0,
    "max_mismatch_rate": 0.0
  }
}
```

The comparator must:

- verify artifact hashes and schemas;
- compare dataset identities;
- report missing timestamps on each side;
- align rows deterministically;
- compare each configured field using its declared policy;
- identify the first divergence globally and per field;
- calculate mismatch count and rate;
- group contiguous mismatch bars into clusters;
- include a context window before and after the first divergence;
- distinguish missing, null, type, exact-value, and tolerance failures;
- emit `parity.json`, `parity.md`, and `first-divergence.json`.

Probable-cause classification may be rule-based and explicitly labeled as a hypothesis. Useful categories include warmup mismatch, timestamp alignment, higher-timeframe alignment, moving-average seeding, order timing, same-bar stop/target ambiguity, rounding, missing data, session boundaries, and unsupported runtime semantics. Never allow the probable-cause label to alter the pass/fail calculation.

---

## 20. Generation registry

Pine generation is adapter-driven. Each registered adapter owns one known strategy schema and must provide:

```text
adapter ID and version
input JSON schema
semantic assumptions
Pine template
trace instrumentation fields
source generator
generator tests
round-trip analysis test
golden Pine output
```

Define a `StrategyGenerator` protocol with `validate_spec`, `generate`, `expected_trace_contract`, and `capabilities` methods. Register adapters by explicit code import, not dynamic arbitrary modules.

Implement one complete sample adapter named `ma_cross_atr_stop_v1`. It should generate a self-contained Pine v6 strategy with configurable moving-average kind, fast and slow lengths, ATR length, ATR stop multiplier, long/short permissions, capital, sizing, commission, slippage, and an explicit decision/execution policy. It must emit hidden `__p2p.*` trace plots for the features, signals, position state, stop price, and rejection reasons that can be represented safely.

The generated source header must contain machine-readable comments:

```text
// @generated-by Pine2Python <version>
// @generator ma_cross_atr_stop_v1 <adapter-version>
// @spec-hash sha256:...
// @trace-contract 1.0
```

After generation, automatically run source ingestion, parsing, static analysis, and capability review. Generation succeeds only when those stages complete under the adapter’s declared requirements. Local execution may be an optional next operation because it requires a dataset.

Do not implement a generic LLM-based generator inside this service. An external LLM may create a spec or source, while Pine2Python validates deterministic artifacts.

---

## 21. HTTP API

Use FastAPI with generated OpenAPI documentation. All errors use one envelope:

```json
{
  "error": {
    "code": "DATASET_HASH_MISMATCH",
    "message": "The referenced dataset does not match its manifest.",
    "details": {},
    "request_id": "req_..."
  }
}
```

Required endpoints:

| Method and path | Purpose |
|---|---|
| `GET /health/live` | Process liveness |
| `GET /health/ready` | Dependency, worker, schema, and storage readiness |
| `GET /v1/version` | Service and dependency versions |
| `GET /v1/capabilities` | Global parser/runtime/generator capability snapshot |
| `POST /v1/analyses` | Ingest and analyze Pine source |
| `GET /v1/analyses/{analysis_id}` | Analysis summary and artifact manifest |
| `POST /v1/executions` | Execute a completed analysis on a frozen dataset |
| `GET /v1/executions/{execution_id}` | Execution summary and trace artifacts |
| `POST /v1/imports/traces` | Register a caller-produced standard or mapped trace |
| `POST /v1/parity-comparisons` | Compare two traces |
| `GET /v1/parity-comparisons/{comparison_id}` | Parity summary and report artifacts |
| `GET /v1/generators` | Registered generation adapters and schemas |
| `POST /v1/generators/{adapter_id}/generate` | Generate Pine from a supported strategy spec |
| `GET /v1/artifacts/{artifact_path:path}` | Optional controlled artifact download endpoint; reject traversal and unauthorized roots |

For the first version, operations may be synchronous because StrategyLab will wrap them in its own job orchestration. Still assign immutable IDs and persist results. The API must remain safe under client disconnects and duplicate retries. Support an optional `Idempotency-Key` header for creation endpoints; repeated requests with the same key and request hash return the original result.

Do not create an internal distributed queue in the first version. Keep the service narrow.

---

## 22. CLI

Install a `pine2python` console command. Commands mirror the API while also supporting fully local operation without starting a server.

```text
pine2python version
pine2python capabilities
pine2python analyze strategy.pine --output ./out/analysis
pine2python execute --analysis ./out/analysis/manifest.json --dataset ./dataset-manifest.json --output ./out/execution
pine2python trace import ./python-trace.jsonl --manifest ./python-trace-manifest.json
pine2python compare --reference ./pine-trace --candidate ./python-trace --contract ./parity-contract.json --output ./out/parity
pine2python generators
pine2python generate ma_cross_atr_stop_v1 --spec ./strategy-spec.json --output ./out/generated
pine2python serve
```

CLI output defaults to concise human-readable summaries and supports `--json`. Exit codes must distinguish validation failure, unsupported capability, runtime failure, parity failure, and internal error. Document them.

---

## 23. Error model and failure artifacts

Failures are evidence. Preserve enough information to reproduce them without exposing sensitive host details.

Define stable error codes for:

```text
SOURCE_TOO_LARGE
SOURCE_ENCODING_INVALID
SOURCE_PATH_FORBIDDEN
PARSE_FAILED
PARSE_PARTIAL
UNSUPPORTED_CONSTRUCT
DATASET_NOT_FOUND
DATASET_HASH_MISMATCH
DATASET_INVALID
DATASET_TOO_LARGE
RUNTIME_UNAVAILABLE
RUNTIME_TIMEOUT
RUNTIME_MEMORY_LIMIT
RUNTIME_OUTPUT_TOO_LARGE
RUNTIME_FAILED
RUNTIME_RESULT_INVALID
TRACE_SCHEMA_INVALID
TRACE_ALIGNMENT_FAILED
PARITY_FAILED
GENERATOR_NOT_FOUND
GENERATOR_SPEC_INVALID
ARTIFACT_NOT_FOUND
INTERNAL_ERROR
```

A runtime failure artifact contains the source and dataset hashes, worker request without source body, exit code, timeout state, truncated stderr, dependency versions, and capability report. Never include unrestricted environment variables or host paths.

---

## 24. Security model

Treat Pine source, dataset files, imported traces, and generator specs as untrusted input.

The implementation must enforce:

| Boundary | Required control |
|---|---|
| Filesystem | Resolve paths under configured roots; reject traversal, symlink escape, devices, sockets, and oversized files |
| Process execution | Use explicit executable/arguments with no shell; fixed worker path; sanitized environment |
| Network | Runtime worker performs no market-data fetches; deployment supports `network_mode: none` or equivalent worker isolation |
| Resource limits | Source, bars, runtime, stdout, stderr, result file, memory where supported, and concurrency limits |
| Serialization | Strict Pydantic and JSON-schema validation; reject NaN and Infinity in public JSON |
| Artifacts | Atomic writes, content hashes, no arbitrary artifact path downloads |
| Logs | Structured request IDs; no full source or dataset dumps by default |
| Dependencies | Locked versions, vulnerability scanning, and documented license checks |
| Generated code | Deterministic templates only; no arbitrary template path or code execution |

The single-container MVP cannot perfectly isolate the Node process from the Python process. Document this limitation. The StrategyLab integration may later split the worker into a separate no-network container. The current worker still runs as an unprivileged user with a restricted working directory.

---

## 25. Observability

Use structured JSON logs in container mode. Every request receives a request ID. Every artifact operation receives an entity ID such as `ana_`, `exe_`, `imp_`, `cmp_`, or `gen_`.

Log state transitions and durations without logging complete source. Include metrics through a simple `/metrics` endpoint only if a lightweight dependency is acceptable; otherwise expose counters in `/v1/status`. Useful metrics include analysis count, parse-partial rate, runtime success rate, runtime timeout count, average bars per execution, parity mismatch rate, artifact bytes, and dependency readiness.

---

## 26. Test strategy

The repository is incomplete until its tests prove the contracts. Use pytest for Python and the standard Node test runner or Vitest only where the worker needs isolated tests. Keep golden fixtures small enough for source control.

### Unit tests

Cover path safety, hashing, source normalization, parser-result normalization, fallback scanning, inventory extraction, temporal findings, capability aggregation, dataset validation, trace reading/writing, alignment, every comparison policy, error envelopes, generator validation, and artifact atomicity.

### Golden parser and analysis fixtures

Create Pine fixtures for:

```text
simple indicator
simple strategy
v5 and v6 declarations
var and reassignment
varip
history references
request.security with safe completed-bar pattern
request.security with lookahead risk
strategy entry and reversal
strategy exit with stop and limit
same-bar stop/target ambiguity
session/timezone logic
arrays and maps
user-defined functions
import statement
labels, lines, boxes, and tables
invalid source
unsupported v6 syntax discovered during the spike
```

Golden expected artifacts should test stable normalized fields, not incidental upstream formatting.

### Runtime integration tests

Run the pinned PineTS worker against deterministic candles and assert trace values for a small indicator and the instrumented sample strategy. Add an execution timeout test. Add a malformed worker-output test. Add a dependency-unavailable readiness test.

### Parity tests

Create exact-match, tolerance-pass, tolerance-fail, missing-timestamp, null mismatch, dataset-hash mismatch, warmup exclusion, and first-divergence context fixtures.

### Generator tests

Validate the sample spec, compare generated Pine to a golden file, analyze the generated source, execute it on deterministic candles, and verify its `__p2p.*` trace contract.

### Container smoke test

Build the image, start it, wait for readiness, analyze a fixture, execute it, compare a trace, and stop the container. CI must run this smoke test.

Target meaningful coverage, but use behavioral acceptance as the real gate. Do not chase coverage by testing trivial getters while leaving runtime or parity paths untested.

---

## 27. Docker and local development

Use a multi-stage Dockerfile. Install locked Node dependencies and locked Python dependencies in build stages. Copy only runtime artifacts into the final image. Run as a dedicated non-root user. Expose port `8080`. Provide a health check against `/health/ready`.

The standalone `compose.yaml` should mount separate input and artifact volumes:

```yaml
services:
  pine2python:
    build: .
    ports:
      - "8080:8080"
    environment:
      P2P_INPUT_ROOT: /var/lib/pine2python/input
      P2P_ARTIFACT_ROOT: /var/lib/pine2python/artifacts
    volumes:
      - ./local/input:/var/lib/pine2python/input:ro
      - ./local/artifacts:/var/lib/pine2python/artifacts
    read_only: true
    tmpfs:
      - /tmp:size=512m
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

Adapt syntax for platform compatibility, and document that outbound-network isolation should be enabled in deployment. Because the API itself needs to accept connections, complete container-level `network_mode: none` is incompatible with serving HTTP from the same container. The first version therefore relies on code-level no-network runtime behavior and standard egress controls. A future split-worker deployment can give the worker container no network.

Provide Make targets or equivalent commands:

```text
make install
make lint
make test
make golden
make run
make docker-build
make docker-smoke
```

Use Ruff and a static type checker for Python. Use ESLint or a minimal equivalent only if needed for the small worker; avoid unnecessary toolchain bulk.

---

## 28. README requirements

The README must be truthful and operational. It should explain:

- what Pine2Python does;
- why it is not an official TradingView compiler;
- the verification hierarchy;
- installation with locked dependencies;
- CLI examples;
- API examples;
- the trace instrumentation contract;
- supported and unsupported features from the generated capability snapshot;
- container operation;
- StrategyLab integration expectations;
- security boundaries;
- licensing and AGPL network-service implications;
- how to add a generator adapter;
- how to report a parity discrepancy with a minimal fixture.

Do not claim “1:1 TradingView parity” in Pine2Python’s own voice. An upstream project may use that marketing phrase, while this repository must describe what its tests actually demonstrate.

---

## 29. Implementation order

Execute the work in this order because later layers depend on proven earlier contracts.

### Stage A: due diligence and project skeleton

Create the repository metadata, lockfiles, license/notice files, settings, base models, error envelope, artifact manager, and upstream capability spike. The stage passes when dependency versions are pinned and the spike artifacts exist.

### Stage B: source ingestion, parser adapter, and static analysis

Implement immutable source records, Pynescript integration, fallback scanning, semantic inventory, temporal findings, and capability aggregation. The stage passes when all golden source fixtures produce stable reports.

### Stage C: isolated PineTS runtime and trace normalization

Implement dataset manifests, candle normalization, the Node worker, process limits, passive trace extraction, instrumented trace mapping, and execution artifacts. The stage passes when deterministic indicator and strategy fixtures execute in the container.

### Stage D: trace import and parity

Implement external trace registration, alignment, field policies, mismatch clusters, first-divergence context, JSON/Markdown reports, and parity exit status. The stage passes when the parity fixture matrix succeeds.

### Stage E: generation adapter

Implement the registry and the complete `ma_cross_atr_stop_v1` adapter with generated trace plots, analysis round-trip, runtime test, and golden source.

### Stage F: API, CLI, documentation, and hardening

Complete all endpoints and commands, idempotency, security tests, structured logging, container hardening, smoke tests, and documentation.

Do not defer tests and documentation to an undefined later phase. Each stage includes its own tests and docs.

---

## 30. Definition of done

The repository is done only when all of the following are true:

| Area | Acceptance condition |
|---|---|
| Build | Fresh checkout installs from lockfiles and builds without manual patching |
| API | All required endpoints are implemented and documented in OpenAPI |
| CLI | All required commands work without starting the server |
| Analysis | A representative v5/v6 fixture set produces immutable source, AST/partial parse, inventory, temporal findings, and capabilities |
| Runtime | Supported fixtures run against local candles with no data-provider network call |
| Trace | Instrumented signals/features/state are emitted in the standard JSONL bundle |
| Parity | Exact and tolerance comparisons produce deterministic pass/fail and first-divergence reports |
| Generation | `ma_cross_atr_stop_v1` generates analyzed, executable, instrumented Pine from a validated spec |
| Honesty | Unsupported features remain visible; no endpoint claims TradingView acceptance |
| Security | Path traversal, source limits, bar limits, timeout, malformed output, and artifact traversal tests pass |
| Licensing | License, notices, upstream snapshot, and dependency locks are present |
| Container | Non-root image builds and passes the end-to-end smoke test |
| Quality | Lint, type checks, Python tests, Node tests, and container tests pass |
| Documentation | README and all required docs match the implemented behavior |

---

## 31. Final handoff report required from Codex

When implementation is complete, produce `IMPLEMENTATION_REPORT.md`. It must state what was built, the exact commands used to validate it, test results, container image identity, dependency versions, supported capability matrix, known unsupported semantics, licensing posture, security boundaries, sample artifact locations, and any intentional deviations from this specification.

The report must include one end-to-end example with these artifacts:

```text
input Pine source
analysis manifest
capability report
frozen dataset manifest
local execution summary
trace bundle
Python trace import
parity report
first divergence or exact-pass result
generated sample Pine
```

If any required capability remains incomplete, say so directly in the report and leave the repository in a runnable state with the failure represented by tests or capability flags. Do not describe incomplete work as production-ready.

---

## 32. Final operating principle

Pine2Python succeeds when it makes Pine behavior easier to inspect, port, and verify while preserving uncertainty at the exact boundary where TradingView remains authoritative. Its value comes from reproducible evidence: immutable sources, frozen data, structured semantics, standardized traces, explicit comparison contracts, and precise first-divergence reports. Build the repository around that evidence chain.
