# StrategyLab Integration Specification for the Pine2Python Mini-Repository

## Instruction to the Codex instance responsible for StrategyLab

You are responsible for building and integrating **Pine2Python** directly inside the existing `LycurgusxLycurgus/StrategyLab` repository as a containerized internal service. Create it in place at `services/pine2python/`; no prebuilt Pine2Python folder will be supplied. Treat this document as the integration contract. Read this entire document, inspect the current StrategyLab repository, run its existing tests before changing code, and preserve StrategyLab’s research constitution, strategy lineage, manual TradingView acceptance boundary, and existing strategy behavior.

Your job is to make StrategyLab call Pine2Python as a deterministic analysis and parity component. Pine2Python must not become a second strategy optimizer, a second source of strategy lineage, or an authority that can promote a strategy. StrategyLab remains the system of record for strategy families, versions, datasets, research contracts, mutations, optimization, robustness, execution feasibility, evidence, and promotion. Pine2Python owns Pine parsing, static review, local supported-subset execution, standard trace artifacts, parity comparison, and adapter-driven Pine generation.

Implement the integration fully. Do not stop after copying the folder, adding a Compose service, or creating a client with uncalled methods. The finished StrategyLab must expose the integrated operations through its API, persist integration records and artifact references, produce StrategyLab-native Python traces, run end-to-end parity for at least one existing engine, and update the phase workflow so automated evidence supplements the existing TradingView gate without replacing it.

When repository reality differs from the paths or assumptions in this document, preserve the architectural intent and adapt carefully. Record each adaptation in `artifacts/integration/pine2python/implementation-decisions.md` or another durable project document. Avoid broad unrelated refactors.

### 2026-07-23 controlling amendment

Build the mini-repository already integrated in this monorepo. It must retain its
own dependencies, API, CLI, tests, license notices, Dockerfile, and package
boundary, but all development and capability tests happen against StrategyLab
from the outset. References below to receiving, copying, vendoring, or recording
an external source commit are superseded.

Add a **Pine Workbench before Phase 1**. It is the default entry for:

- a greenfield Pine strategy;
- a source-licensed public strategy or indicator adaptation with provenance;
- an indicator-first component that must be validated before strategy rules are
  composed.

Each edit creates an immutable revision and re-runs local analysis and supported
execution. Phase 1 freezes the economic and causal contract only after the Pine
candidate is coherent. Phase 1.5 remains the explicit TradingView boundary. Phase
2 ports the frozen accepted Pine to StrategyLab Python and proves criterion-level
parity before any optimization or mutation.

Do not rely on TradingView chart-data export. The Basic plan blocks it. Replace
the old external-data assumption with a generated on-chart **Parity Proof
Dashboard**. StrategyLab prepares an exact Basic-plan-compatible window and
expected proof artifact; the user runs the frozen Pine in TradingView and supplies
the dashboard screenshot/values. StrategyLab records:

- source, settings, profile, symbol, timeframe, and absolute window identity;
- first/last timestamps and bar count;
- three independent OHLC fingerprints and segmented mismatch fingerprints;
- feature/state/signal/rejection/order-intent fingerprints declared by the
  strategy contract;
- closed-trade fingerprints and official Strategy Tester totals;
- screenshot hashes, observed values, exact mismatches, and user verdict.

`TRADINGVIEW_SIGNATURE_MATCH` requires dataset identity before execution fields
can pass. It is the normal one-screenshot corroboration path and does not by
itself approve visual drawing lifecycles, intrabar/realtime behavior, unsupported
broker-emulator semantics, or nonstandard chart types. Route those declared claims
to a focused second screenshot or explicit manual review. Pine2Python and
StrategyLab never self-award `TRADINGVIEW_ACCEPTED`.

---

## 1. Current StrategyLab architecture that must be preserved

At the time this specification was prepared, StrategyLab identifies itself as Mutation Lab: a whitebox-first strategy creation, porting, qualification, and mutation workbench. Its documented lifecycle treats TradingView as the canonical proving ground for chart-based Pine strategies. A manually accepted Pine strategy is frozen, ported into a Python strategy engine, proven at criterion-level parity, qualified as a faithful baseline, and only then exposed to whitebox or later hybrid mutation work.

The repository already has a coherent control plane. `app/main.py` exposes FastAPI endpoints for strategy families, versions, datasets, runs, tuning, optimization jobs, robustness, proposals, and execution audits. `app/lab.py` orchestrates strategy lifecycle, mutation spaces, optimization, evaluation, robustness, and artifacts. `app/backtest.py` contains the custom event-oriented strategy engines and performance calculations. `app/data.py` manages Binance and MT5 bar data. `app/storage.py` persists datasets, families, versions, proposals, and runs in SQLite. The repository stores strategy contracts, data, runs, reports, diagnostics, accepted source, and phase artifacts under project directories.

The current engine dispatch is explicit: a strategy specification contains an `engine_id`, and `BacktestEngine.run()` selects one of the implemented engine paths. Existing examples include moving-average/ATR, Gann/Donchian, BOS demand pullback, ASM/Fibonacci/liquidity/FVG, and quantitative SMC strategy families. Their JSON specifications already carry parameters, evaluation rules, mutation spaces, metadata, asset, venue, and timeframe. The full behavioral semantics still live partly in Python implementation code.

The mutation constitution requires a frozen parent and context, diagnosis before mutation, one conceptual dependency per test, decision-time information only, precommitted acceptance boundaries, persistence of failures, chronological validation, and live-engine reproduction before promotion. Pine2Python must strengthen this evidence chain. It must not weaken or bypass it.

Before implementing, confirm the current repository state by reading at least:

```text
README.md
requirements.txt or current dependency files
app/main.py
app/config.py
app/data.py
app/storage.py
app/lab.py
app/backtest.py
app/execution_audit.py
app/tests.py and any newer test layout
app/ui/
strategies/
pre-strategies/
agents/translation and generation/whitebox/
agents/docs/universal_mutation_constitution.md
```

Run the existing test command exactly as documented, record the baseline result, and preserve it in the final integration report.

---

## 2. Integration objective

The integrated system should support this complete lifecycle:

```text
Strategy idea or inspectable Pine source
        │
        ▼
StrategyLab Phase 1 contract and provenance
        │
        ▼
Pine2Python source analysis and capability evidence
        │
        ▼
Pine creation or source-derived adaptation
        │
        ▼
Pine2Python automated review, local trace, and fixture selection
        │
        ▼
Manual TradingView compile and one-screen Parity Proof Dashboard acceptance
        │
        ▼
Frozen accepted Pine and settings
        │
        ├──────────────► Pine2Python reference trace
        │
        ▼
Faithful StrategyLab Python implementation
        │
        ├──────────────► StrategyLab candidate trace
        │
        ▼
Pine2Python parity comparison
        │
        ▼
Phase 2 parity acceptance
        │
        ▼
StrategyLab diagnosis, mutation, optimization, robustness, and promotion
        │
        ▼
Pine2Python adapter generation for promoted supported engines
        │
        ▼
Python/Pine trace parity and final sampled TradingView acceptance
```

The immediate value begins in the pre-Phase 1 Pine Workbench and continues through Phase 1.5 and Phase 2. Pine2Python should automate source review, supported execution, proof generation, and reproducible reference traces that otherwise demand large amounts of manual reasoning. StrategyLab should then emit a corresponding Python trace and receive a precise first-divergence report. TradingView remains necessary for official compilation and the one-screen proof, plus focused review of visual lifecycle, unsupported broker-emulator behavior, realtime semantics, nonstandard charts, feed-specific behavior, and final human acceptance.

---

## 3. Responsibility boundary

Keep ownership explicit.

| Concern | StrategyLab | Pine2Python | TradingView/user |
|---|---:|---:|---:|
| Strategy identity and declared market context | Owns | Reads labels only | Confirms context during review |
| Source provenance and license record | Owns | Preserves hashes and source artifacts | May provide source |
| Phase criteria and acceptance contract | Owns | Consumes selected parity requirements | User approves criteria |
| Pine parsing and semantic inventory | Receives | Owns | — |
| Temporal/repainting risk candidates | Receives and routes | Owns static report | Final platform review where required |
| Local supported-subset Pine execution | Requests and records | Owns | — |
| Official Pine compile | Records evidence | Cannot provide | Owns through TradingView |
| Strategy families and versions | Owns | Must not create | — |
| Python engine implementations | Owns | Does not execute arbitrary StrategyLab Python | — |
| Python trace production | Owns | Imports and validates | — |
| Trace alignment and parity report | Requests and stores verdict | Owns deterministic comparison | May approve intentional divergences |
| Mutation generation and optimization | Owns | Must not perform | — |
| Robustness and execution feasibility | Owns | Provides evidence only | — |
| Promotion | Owns | Never decides | User/StrategyLab contract |
| Pine generation for registered engine adapters | Requests and records | Owns deterministic template adapter | Final TradingView review |

If a new endpoint or database record blurs this boundary, redesign it before proceeding.

---

## 4. Placement of the mini-repository

Place the supplied repository under:

```text
StrategyLab/services/pine2python/
```

Remove any nested `.git` directory before committing into StrategyLab. Preserve Pine2Python’s `LICENSE`, `NOTICE.md`, `third_party/`, lockfiles, tests, and documentation. Do not flatten its source into the StrategyLab Python package. The service must remain independently buildable and testable from its folder.

Use an in-place monorepo package arrangement rather than a Git submodule. A submodule would complicate Codex workflows, offline builds, release reproducibility, and pull-request review. Record pinned upstream dependency versions and capability evidence, not a fictitious Pine2Python source commit. Future updates must change the owned package deliberately and rerun the compatibility suite.

Do not modify Pine2Python internals merely to avoid writing a proper StrategyLab adapter. Changes required for a generally useful contract should be made inside the vendored service and documented. StrategyLab-specific lifecycle behavior belongs in StrategyLab.

---

## 5. Container topology

Create or extend a root `compose.yaml` that starts at least these services:

```text
strategylab
pine2python
```

If StrategyLab does not currently have a Dockerfile, add one. Keep the existing direct virtual-environment run path working. The containerization layer is an additional supported run mode, not a forced replacement for local development.

The recommended topology is:

```text
Browser or API client
        │
        ▼
StrategyLab :8000
        │ internal HTTP
        ▼
Pine2Python :8080
        │
        ├── read-only StrategyLab input artifacts
        └── write-only or read/write Pine2Python output artifacts
```

Use one internal Compose network. Do not publish Pine2Python’s port by default in the StrategyLab compose file. StrategyLab reaches it through `http://pine2python:8080`. A development override may publish the port for debugging.

Use separate mounts to reduce accidental access:

```text
StrategyLab artifact root
    datasets and source packages
        mounted read-only into Pine2Python input root

Pine2Python artifact root
        mounted read/write into Pine2Python
        mounted read-only or read/write into StrategyLab according to the artifact import design
```

A practical Compose fragment is:

```yaml
services:
  strategylab:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
      PINE2PYTHON_URL: http://pine2python:8080
      PINE2PYTHON_REQUIRED: "true"
      PINE2PYTHON_INPUT_ROOT: /shared/p2p-input
      PINE2PYTHON_ARTIFACT_ROOT: /shared/p2p-output
    volumes:
      - strategylab-artifacts:/app/artifacts
      - pine2python-input:/shared/p2p-input
      - pine2python-output:/shared/p2p-output
    depends_on:
      pine2python:
        condition: service_healthy

  pine2python:
    build:
      context: ./services/pine2python
    environment:
      P2P_HOST: 0.0.0.0
      P2P_PORT: 8080
      P2P_INPUT_ROOT: /var/lib/pine2python/input
      P2P_ARTIFACT_ROOT: /var/lib/pine2python/artifacts
    volumes:
      - pine2python-input:/var/lib/pine2python/input:ro
      - pine2python-output:/var/lib/pine2python/artifacts
    read_only: true
    tmpfs:
      - /tmp:size=512m
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready')"]
      interval: 10s
      timeout: 5s
      retries: 12

volumes:
  strategylab-artifacts:
  pine2python-input:
  pine2python-output:
```

Adapt this to the actual artifact-path strategy. Bind mounts may be preferable in development so evidence is visible on the host. Named volumes are appropriate for a self-contained deployment. Document both.

Pine2Python’s runtime should not download data. StrategyLab remains responsible for dataset acquisition and passes a frozen manifest and file through the shared input area.

---

## 6. StrategyLab configuration

Extend `app/config.py` with typed settings:

| Setting | Suggested default | Meaning |
|---|---|---|
| `PINE2PYTHON_URL` | `http://127.0.0.1:8080` | Base service URL for direct local development |
| `PINE2PYTHON_REQUIRED` | `false` outside Compose | Whether StrategyLab readiness fails when the service is unavailable |
| `PINE2PYTHON_TIMEOUT_SECONDS` | `120` | Client request timeout; must exceed Pine2Python worker timeout slightly |
| `PINE2PYTHON_INPUT_ROOT` | project artifact integration folder | StrategyLab-side path copied/mounted into Pine2Python input root |
| `PINE2PYTHON_ARTIFACT_ROOT` | project artifact integration folder | StrategyLab-visible Pine2Python output root |
| `PINE2PYTHON_MAX_RETRIES` | `1` | Retry count for idempotent transport failures only |
| `PINE2PYTHON_ENABLED` | `true` | Feature flag |

Add environment examples and document direct-run behavior. When StrategyLab runs outside Compose, the developer should be able to start Pine2Python separately or disable the feature. Do not make existing non-Pine operations fail merely because the optional service is unavailable unless `PINE2PYTHON_REQUIRED=true`.

Extend `/health` or add `/health/ready` to report StrategyLab and Pine2Python status separately. A response should distinguish `disabled`, `unavailable`, `degraded`, and `ready`.

---

## 7. Pine2Python client adapter

Create a focused integration module, preferably:

```text
app/integrations/pine2python_client.py
app/integrations/pine2python_models.py
```

Use the standard library HTTP client only if it supports required timeouts and JSON behavior cleanly; otherwise add a small maintained dependency such as `httpx` and pin it. The client must not leak raw HTTP mechanics through `MutationLabService`.

Define methods equivalent to:

```python
class Pine2PythonClient:
    def readiness(self) -> ServiceReadiness: ...

    def capabilities(self) -> CapabilitySnapshot: ...

    def analyze_source(
        self,
        *,
        source: str,
        labels: dict[str, str],
        requested_checks: list[str],
        idempotency_key: str,
    ) -> PineAnalysisResult: ...

    def execute_analysis(
        self,
        *,
        analysis_id: str,
        dataset_manifest_path: str,
        input_overrides: dict[str, object],
        trace_contract: dict[str, object] | None,
        idempotency_key: str,
    ) -> PineExecutionResult: ...

    def import_trace(
        self,
        *,
        trace_manifest_path: str,
        idempotency_key: str,
    ) -> ImportedTraceResult: ...

    def compare_traces(
        self,
        *,
        reference_trace_uri: str,
        candidate_trace_uri: str,
        parity_contract: dict[str, object],
        idempotency_key: str,
    ) -> ParityComparisonResult: ...

    def generate_pine(
        self,
        *,
        adapter_id: str,
        strategy_spec: dict[str, object],
        idempotency_key: str,
    ) -> PineGenerationResult: ...
```

Map Pine2Python error envelopes into StrategyLab-domain exceptions. Preserve the upstream error code and request ID in stored records. Retry only connection resets or gateway failures for operations protected by an idempotency key. Do not retry validation errors, unsupported capabilities, runtime timeouts, or parity failures.

The client must verify the Pine2Python service version and supported schema versions at startup or before first use. Refuse incompatible major schema versions with a clear error.

---

## 8. StrategyLab domain records for Pine evidence

Do not overload the existing `runs` table with every Pine analysis and comparison. Add explicit additive tables in `app/storage.py` or a small migration layer. Because the current repository initializes SQLite tables directly, implement idempotent schema creation and safe additive migrations without deleting existing data.

Recommended tables:

```sql
CREATE TABLE IF NOT EXISTS pine_analyses (
    pine_analysis_id TEXT PRIMARY KEY,
    strategy_id TEXT,
    family_id TEXT,
    version_id TEXT,
    phase TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    pine2python_analysis_id TEXT NOT NULL,
    status TEXT NOT NULL,
    capability_status TEXT NOT NULL,
    artifact_manifest_path TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    service_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pine_executions (
    pine_execution_id TEXT PRIMARY KEY,
    pine_analysis_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    pine2python_execution_id TEXT NOT NULL,
    status TEXT NOT NULL,
    trace_uri TEXT,
    artifact_manifest_path TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parity_comparisons (
    parity_id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    reference_execution_id TEXT NOT NULL,
    candidate_trace_id TEXT NOT NULL,
    pine2python_comparison_id TEXT NOT NULL,
    status TEXT NOT NULL,
    level TEXT NOT NULL,
    verdict TEXT NOT NULL,
    first_divergence_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    artifact_manifest_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_pine_artifacts (
    generation_id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    spec_hash TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    pine2python_generation_id TEXT NOT NULL,
    status TEXT NOT NULL,
    source_path TEXT NOT NULL,
    artifact_manifest_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Use foreign-key-style validation in service code even if SQLite foreign keys are not currently enabled. Add repository methods for put/get/list operations. Never mutate a completed evidence record in place; create a new record when source, data, service version, or contract changes.

A strategy version may have many analyses and executions. The accepted reference is selected through phase artifacts and explicit StrategyLab state, not by “latest wins” without context.

---

## 9. Artifact exchange and path contract

StrategyLab must never send its arbitrary host paths to Pine2Python. Create a controlled exchange area:

```text
artifacts/integration/pine2python/
├── input/
│   ├── datasets/
│   ├── sources/
│   ├── python-traces/
│   └── contracts/
├── output/
│   ├── analyses/
│   ├── executions/
│   ├── comparisons/
│   └── generations/
└── implementation-decisions.md
```

In Compose, map `input/` to Pine2Python’s read-only input root and `output/` to its artifact root. StrategyLab writes input packages atomically and refers to relative paths. Pine2Python recomputes hashes. StrategyLab then imports or references output manifests after verifying their hashes.

Do not duplicate enormous trace files unnecessarily. The artifact record may point into the shared output root. Reports and summaries needed by StrategyLab’s UI can be copied or indexed. Preserve immutable evidence and use content hashes to detect tampering.

---

## 10. Dataset identity upgrade

The current dataset record includes an ID, name, symbol, timeframe, source, row count, path, and creation time. Pine parity needs a stronger identity. Extend dataset metadata and persisted manifests with:

```text
content_hash
first_timestamp
last_timestamp
timezone
timestamp_semantics
column_mapping
missing_bar_policy
normalization_version
validation_findings
```

Compute the hash from the exact CSV bytes used by the StrategyLab engine. Do not hash a logically equivalent in-memory representation and assume file identity. When existing datasets lack a hash, compute and persist it lazily without changing their bars.

Add `DataService.create_dataset_manifest(dataset_id)` that validates the file, records the metadata above, and writes a versioned JSON manifest into the Pine2Python exchange input folder. The manifest’s `relative_path` must resolve from Pine2Python’s mounted input root.

Pine and Python traces may only receive exact parity status when their dataset hashes match. If TradingView uses a different feed, that comparison belongs to a tolerance-bound or fixture-based external review, not this exact local parity operation.

---

## 11. Strategy specification evolution

Preserve existing strategy JSON. Add optional sections that make execution and parity contracts explicit:

```json
{
  "semantics": {
    "decision_time": "bar_close",
    "entry_execution": "next_bar_open",
    "exit_execution": "next_bar_open_or_resting_stop",
    "higher_timeframe_policy": "completed_bars_only",
    "same_bar_exit_policy": "stop_first",
    "timestamp_semantics": "bar_open"
  },
  "ports": {
    "pine": {
      "supported": true,
      "generator_adapter": "ma_cross_atr_stop_v1",
      "trace_contract_version": "1.0"
    }
  },
  "trace_schema": {
    "features": ["fast_ma", "slow_ma", "atr"],
    "state": ["position", "pending_entry", "stop_price"],
    "signals": ["long_entry", "short_entry", "reverse_exit"],
    "rejections": ["anti_chop", "time_risk", "exposure"]
  },
  "parity": {
    "schema_version": "1.0",
    "exact_fields": [
      "signals.long_entry",
      "signals.short_entry",
      "state.position"
    ],
    "numeric_fields": {
      "features.fast_ma": {"absolute_tolerance": 0.000001},
      "features.slow_ma": {"absolute_tolerance": 0.000001},
      "features.atr": {"absolute_tolerance": 0.000001}
    },
    "warmup_policy": "engine_declared",
    "required_level": "signal"
  }
}
```

Update `_upgrade_spec` or its successor to add only safe defaults. Do not infer exact semantics for existing engines without inspecting their code and accepted Pine contract. For each engine, populate these sections through an explicit migration function and tests. Unknown semantics stay absent or `unknown`; they must not receive a guessed value merely to satisfy a schema.

The Phase 1 criteria own parity tolerances. A strategy-spec default must be traceable to that contract or an existing accepted implementation. Later optimization must not alter parity semantics as an ordinary tunable parameter.

---

## 12. StrategyLab trace production

Pine2Python can compare traces only when StrategyLab emits a standard candidate trace. Introduce a tracing layer that is independent of performance metrics.

Create modules such as:

```text
app/tracing.py
app/trace_contracts.py
```

Define a collector interface:

```python
class TraceCollector:
    def begin(self, manifest: dict[str, object]) -> None: ...
    def emit_bar(
        self,
        *,
        index: int,
        bar: Bar,
        features: dict[str, object],
        state: dict[str, object],
        signals: dict[str, object],
        order_intents: list[dict[str, object]],
        orders: list[dict[str, object]],
        rejections: list[dict[str, object]],
        warnings: list[dict[str, object]],
    ) -> None: ...
    def complete(self, summary: dict[str, object]) -> TraceArtifact: ...
```

Update `BacktestEngine.run()` to accept an optional trace configuration without changing existing callers:

```python
def run(
    self,
    spec: dict[str, Any],
    bars: list[Bar],
    trace_collector: TraceCollector | None = None,
) -> dict[str, Any]:
    ...
```

Each engine emits only decision-time information for that bar. Do not reconstruct internal state after the run from trades and metrics; that loses rejected signals, pending orders, state transitions, and the first divergence.

The minimum fields common to every engine are:

```text
bar index and timestamp
market OHLCV
position direction
entry signal booleans
exit signal booleans
pending order state
order intents
actual fills when modeled
stop state when applicable
rejection reasons when a candidate decision is blocked
engine warnings
```

Each engine adds its strategy-specific features. The trace contract in its strategy spec defines the canonical names.

### Preserve performance

Trace generation should be optional because optimization sweeps can evaluate many candidates. Normal runs and parity runs enable it. Bulk optimization should keep it disabled unless diagnostics require a finalist trace. Use streaming JSONL writes to avoid retaining a million bar rows in memory.

### No future information

A trace row records the information available when the engine made the decision. Do not attach eventual trade outcomes or future maximum excursion to an entry-decision row. Outcome diagnostics belong in separate run artifacts.

---

## 13. Engine registry refactor

The current central conditional dispatch should be converted carefully into an engine registry. This is desirable for Pine adapters and trace contracts, but do not mix the refactor with behavioral changes.

Define a protocol:

```python
class StrategyEngine(Protocol):
    engine_id: str

    def run(
        self,
        spec: dict[str, Any],
        bars: list[Bar],
        trace_collector: TraceCollector | None = None,
    ) -> dict[str, Any]: ...

    def trace_contract(self, spec: dict[str, Any]) -> dict[str, Any]: ...

    def pine_port(self, spec: dict[str, Any]) -> dict[str, Any] | None: ...
```

Register existing implementations explicitly. A low-risk first step may wrap current private methods without immediately moving thousands of lines:

```python
ENGINE_REGISTRY = {
    "ma_cross_atr_stop_v1": ExistingMethodEngine(...),
    "ghl_dc_breakout_v1": ExistingMethodEngine(...),
    ...
}
```

Then move engines into separate modules only after regression tests prove identical metrics, trades, diagnostics, and traces. Avoid a massive formatting-and-relocation commit combined with integration behavior.

Every existing engine must eventually expose a minimum trace. Pine generation support may remain absent for engines without a proven adapter. `pine_port()` returns an explicit unsupported capability rather than a fabricated template.

---

## 14. Phase 1 integration

Phase 1 remains responsible for strategy identity, declared scope, source provenance, research, criteria, execution assumptions, and predeclared parity rules.

Add an optional source-analysis operation when inspectable Pine source exists:

```http
POST /api/strategy-development/{strategy_id}/pine/analyze-source
```

The handler should:

1. locate or accept the preserved source under the Phase 1 provenance rules;
2. call Pine2Python analysis;
3. store the analysis record and artifact manifest;
4. generate a concise StrategyLab summary containing inputs, stateful constructs, timeframe calls, strategy operations, trace capability, and temporal-risk findings;
5. link findings into `phase1_research_record.md` and the criteria checklist without automatically deciding pass/fail.

Update the Phase 1 prompt so the Codex researcher uses the automated report as evidence while continuing to verify official TradingView documentation. Pine2Python output cannot replace official mechanism research.

The Phase 1 completion gate should require the Pine2Python report only when source is available and the service is enabled. A source-access-blocked route remains valid when inspectable source cannot be obtained.

---

## 15. Phase 1.5 integration

Phase 1.5 receives the largest automation improvement.

Add an operation such as:

```http
POST /api/strategy-development/{strategy_id}/pine/prepare-manual-review
```

The operation should:

1. freeze the candidate Pine bytes and hash;
2. call Pine2Python analysis;
3. block local execution when capability findings are unresolved and required by the contract;
4. create a frozen dataset manifest for the declared StrategyLab dataset when local evidence is applicable;
5. call Pine2Python execution;
6. import the execution summary and trace URI;
7. derive candidate timestamps for accepted signals, rejected signals, exits, state transitions, and edge cases from the standard trace;
8. write a fixture manifest that maps each timestamp to Phase 1 criteria;
9. prepare, rather than approve, the TradingView screenshot review package.

The fixture-selection logic belongs primarily in StrategyLab because the criteria contract is strategy-specific. Pine2Python supplies searchable structured events. StrategyLab chooses evidence that covers the declared criteria.

Suggested fixture manifest:

```json
{
  "schema_version": "1.0",
  "strategy_id": "btc_intraday",
  "source_hash": "sha256:...",
  "dataset_hash": "sha256:...",
  "fixtures": [
    {
      "fixture_id": "FX-SIG-LONG-001",
      "timestamp": "2025-03-14T15:00:00Z",
      "event_path": "signals.long_entry",
      "expected": true,
      "criterion_ids": ["SIG-03", "ORD-02"],
      "reason": "Representative accepted long entry after warmup",
      "review_method": "TradingView screenshot and Strategy Tester order marker",
      "status": "PENDING_MANUAL_REVIEW"
    }
  ]
}
```

Update the Phase 1.5 prompt’s automated/static review section to require the Pine2Python artifact IDs and unresolved capability findings. Preserve the explicit rule that automated review cannot self-approve the TradingView gate.

After manual acceptance, store the accepted source hash, TradingView settings freeze, user verdict, screenshot IDs, and Pine2Python analysis/execution IDs in the portability package.

---

## 16. Phase 2 integration and automated parity

Phase 2 ports the frozen accepted Pine to StrategyLab Python. The accepted Pine remains the reference behavior under the declared contract.

Add a parity operation:

```http
POST /api/versions/{version_id}/pine-parity
```

A request should identify:

```json
{
  "pine_execution_id": "pexe_...",
  "dataset_id": "ds_...",
  "parity_contract": {
    "source": "phase1_criteria",
    "required_level": "signal"
  },
  "persist_python_trace": true
}
```

The handler must:

1. load the version and frozen dataset;
2. verify that the Pine reference trace uses the same dataset hash or route to the declared non-identical-data method;
3. run the StrategyLab engine with trace collection enabled and no parameter optimization;
4. write the Python trace in Pine2Python’s standard bundle schema;
5. register/import it with Pine2Python;
6. construct the exact parity contract from the Phase 1 contract and strategy spec;
7. call Pine2Python comparison;
8. persist the comparison record and artifact references;
9. update the Phase 2 parity ledger without silently changing tolerances;
10. return the verdict and first divergence.

The comparison must occur at state and decision level. Headline metrics remain supplementary. A similar return curve cannot override signal, state, order, or lifecycle mismatches.

The UI and report should display:

```text
reference and candidate source identities
dataset identity
fields compared
bars aligned
missing timestamps
exact matches
numeric tolerance matches
mismatches by field
first divergence
context window
probable-cause hypothesis
unresolved unsupported semantics
required manual review
```

A parity result may be:

```text
EXACT_MATCH
WITHIN_PREDECLARED_TOLERANCE
APPROVED_INTENTIONAL_DIVERGENCE
FAIL
BLOCKED
```

Only StrategyLab’s Phase 2 workflow can turn the collection of criterion results into `PARITY_ACCEPTED`. Pine2Python returns field evidence and contract pass/fail.

---

## 17. Phase 3 and later integration

Do not call Pine2Python during every optimization candidate. StrategyLab’s Python engine remains the fast research and optimization authority. Pine2Python re-enters the workflow at evidence checkpoints:

- when a promoted mutation changes a signal or state transition that must remain portable to Pine;
- when a finalist is being prepared for TradingView deployment;
- when an engine adapter generates Pine for a promoted child;
- when a parity regression suite is run after engine or Pine2Python dependency changes.

Add a promotion precondition for Pine-deployable strategies: if the strategy spec declares a required Pine port, the promoted child must have a generated or manually implemented Pine artifact, a local Pine/Python parity report at the required level, and a `TRADINGVIEW_REVIEW_REQUIRED` route. Production promotion still follows StrategyLab’s robustness, execution feasibility, paper, and operational gates.

Do not require Pine generation for strategies whose product target is Python/MT5 only and whose Phase 1 contract marked Pine as an initial proving format rather than a deployment target.

---

## 18. Reverse generation for promoted StrategyLab versions

Expose:

```http
POST /api/versions/{version_id}/generate-pine
```

The operation checks the version’s `ports.pine` contract and calls the registered Pine2Python generator adapter. It stores the generated source under a version-specific artifact path, preserves source and spec hashes, analyzes the generated source automatically, and records required trace fields.

Suggested artifact layout:

```text
artifacts/strategy-development/<strategy_id>/versions/<version_id>/pine/
├── generated.pine
├── generation-manifest.json
├── analysis-manifest.json
├── capability-report.json
├── execution-manifest.json
├── parity-report.json
└── tradingview-review.md
```

The generated source is a candidate deployment artifact. It does not become accepted merely because it was generated. Run local parity against the Python trace, then route to sampled TradingView review.

For engines without a generator adapter, return an explicit unsupported status and create a human port task. Do not synthesize a generic Pine strategy from parameter names.

---

## 19. StrategyLab API surface

Add endpoints that follow existing `/api` conventions. Exact naming may adapt to current style, but provide equivalent operations:

| Method and path | Purpose |
|---|---|
| `GET /api/pine2python/status` | Service readiness, version, and global capabilities |
| `POST /api/strategy-development/{strategy_id}/pine/analyze-source` | Phase 1 or source-derived analysis |
| `POST /api/strategy-development/{strategy_id}/pine/prepare-manual-review` | Phase 1.5 automated package |
| `GET /api/versions/{version_id}/pine-evidence` | Analyses, executions, parity, and generated artifacts for a version |
| `POST /api/versions/{version_id}/python-trace` | Run and persist a StrategyLab standard trace |
| `POST /api/versions/{version_id}/pine-parity` | Compare frozen Pine and Python traces |
| `POST /api/versions/{version_id}/generate-pine` | Generate Pine through a registered adapter |
| `GET /api/parity/{parity_id}` | Detailed parity record and report links |

Keep the public response concise and include links or relative artifact paths for large reports. Use asynchronous StrategyLab jobs for long operations if the dataset size makes synchronous HTTP impractical. StrategyLab already has an optimization job pattern; extract a small reusable job store or implement a general durable job table rather than duplicating another in-memory dictionary.

Because the existing optimization job registry is in memory, this integration is an opportunity to create a generic job abstraction, but keep the first change bounded. At minimum, Pine operations must survive a client disconnect. A simple worker executor may be acceptable locally, while persisted job status should be stored if practical.

---

## 20. User interface integration

The current UI should gain a compact Pine evidence area within a strategy/version view. It must show actionable status rather than raw JSON.

Include:

```text
Pine source hash and accepted revision
analysis status
parser status
local runtime capability
blocking findings
TradingView review status
reference trace dataset and date range
Python trace status
parity level and verdict
first divergence timestamp and field
generated Pine status
links to Markdown/JSON artifacts
```

Provide buttons only when prerequisites are satisfied:

```text
Analyze Pine
Prepare Manual Review
Run Python Trace
Compare Pine/Python
Generate Pine
Open Evidence Report
```

A user must not be able to click “Compare” before both traces and a parity contract exist. Display `TradingView review required` prominently after a local pass.

Do not build a complex charting interface in this integration. The existing evidence artifacts and timestamps are sufficient for the first version.

---

## 21. Phase prompt updates

Update the relevant files under `agents/translation and generation/whitebox/` so future Codex operators use the service correctly.

### Phase 1 prompt

Add Pine2Python analysis as a required evidence source when inspectable Pine is present and the service is available. Require recording the analysis ID, source hash, parser status, capability findings, temporal-risk findings, and unresolved external verification. Preserve official TradingView documentation research.

### Phase 1.5 prompt

Require Pine2Python automated/static review, supported local execution, and StrategyLab-generated fixture manifest before manual acceptance where applicable. Preserve screenshot evidence, user acceptance, official compile, chart behavior, and Strategy Tester review as manual gates.

### Phase 2 prompt

Require standard Pine and Python trace artifacts, exact dataset identities, a versioned parity contract, automated first-divergence comparison, and criterion-to-field mapping. Preserve intentional-divergence approval and predeclared tolerances.

### Later phase prompts

Explain that normal optimization uses the Python engine. A promoted Pine-deployable child must re-enter generation and parity review. Pine2Python cannot promote a candidate.

Do not weaken the universal mutation constitution. Add a sentence that automated Pine evidence is part of the frozen evidence contract and must be regenerated whenever its source, dataset, trace schema, or runtime version changes.

---

## 22. Compatibility and versioning

Persist these versions with every integration artifact:

```text
StrategyLab commit or application version
strategy spec schema version
engine ID and engine implementation version
trace schema version
Pine2Python service version
Pine2Python API schema version
Pynescript version
PineTS version
source hash
dataset hash
parity contract hash
```

Add a StrategyLab-side compatibility table that defines accepted Pine2Python major schema versions. On startup, the client requests `/v1/version` and `/v1/capabilities`. A major mismatch marks the integration unavailable. A minor change may remain compatible if declared by the service.

When Pine2Python is upgraded, provide a regression command that reruns the golden compatibility set and compares prior trace summaries. Dependency changes can alter numerical behavior even when the API remains stable.

---

## 23. Failure handling

Translate Pine2Python errors into clear StrategyLab states.

| Pine2Python condition | StrategyLab route |
|---|---|
| Service unavailable | Mark operation blocked; preserve existing StrategyLab operations; fail readiness only when configured required |
| Parse partial | Store evidence, prevent claims requiring complete parse, allow manual route when Phase contract permits |
| Unsupported local runtime feature | Route to manual TradingView/fixture method; do not approximate silently |
| Dataset hash mismatch | Hard block and regenerate manifest or repair dataset identity |
| Runtime timeout | Persist failure artifact; allow bounded retry only after reducing declared workload or changing limit explicitly |
| Trace schema mismatch | Integration error; no parity calculation |
| Parity fail | Remain in Phase 2 or port-repair state; do not optimize around failure |
| Generator unavailable | Human Pine port required; Python research can continue according to product contract |
| Generated Pine analysis fail | Reject generated artifact and repair adapter |

Display upstream request IDs and artifact paths in operator diagnostics. Do not expose full source or host paths in generic UI errors.

---

## 24. Security and trust boundaries

StrategyLab may contain public or third-party Pine. Treat it as untrusted input. StrategyLab should copy only the required source and dataset files into the controlled exchange root. Never mount the entire repository read/write into Pine2Python.

The integrated Compose deployment must preserve Pine2Python’s non-root user, read-only root filesystem, dropped capabilities, temporary filesystem, source/bar/time limits, and no-shell process execution. Do not loosen these controls to make path sharing convenient.

Pine2Python is AGPL-based under the planned dependency posture. Preserve its license and source in the public StrategyLab repository. If StrategyLab later becomes proprietary or hosted privately, flag the PineTS commercial-license and AGPL review as a release blocker rather than deleting notices.

---

## 25. Test plan

Run the existing StrategyLab tests before and after every major integration stage. Add focused tests without weakening existing assertions.

### Client tests

Mock Pine2Python responses and cover readiness, version mismatch, successful analysis, partial parse, unsupported runtime, timeout, dataset mismatch, parity pass, parity fail, generation, and idempotent retry.

### Storage tests

Verify additive schema migration on a database containing existing families, versions, datasets, proposals, and runs. Test put/get/list methods and immutable evidence records.

### Dataset-manifest tests

Test content hash, timestamp range, duplicate timestamps, malformed bars, relative exchange path, existing-dataset lazy upgrade, and hash mismatch after file modification.

### Trace tests

For every existing engine, test that a trace-enabled run preserves the original trades, metrics, and diagnostics. Assert minimum common fields and engine-specific field declarations. Add a large-fixture streaming test to ensure memory does not scale with the complete trace size.

### Vertical parity fixture

Use `ma_cross_atr_stop_v1` as the required first complete integration because Pine2Python includes its generator adapter. The test must:

1. load a deterministic StrategyLab strategy spec;
2. generate Pine through Pine2Python;
3. analyze the generated source;
4. execute it on a frozen deterministic dataset;
5. run StrategyLab’s Python engine on the same dataset with trace collection;
6. import the Python trace;
7. compare declared fields;
8. assert exact or predeclared tolerance parity;
9. persist and retrieve the evidence records.

A failure in this fixture blocks completion.

### Regression tests for existing engines

Run existing baseline fixtures with tracing disabled and enabled. Metrics and trades must match their pre-integration golden values. Tracing must not change engine behavior.

### API tests

Use FastAPI’s test client or equivalent to cover all new StrategyLab endpoints, prerequisite enforcement, artifact links, and failure responses.

### Container test

Build the root Compose application, start both services, wait for health, call StrategyLab’s Pine2Python status endpoint, execute the vertical parity fixture through StrategyLab’s public API, and stop cleanly.

---

## 26. Implementation sequence

Follow this sequence to keep failures localized.

### Stage A: baseline and vendor import

Record current tests and application behavior. Copy Pine2Python into `services/pine2python`, remove nested Git metadata, preserve licenses, add `VENDORED_FROM.md`, and verify its own tests independently.

### Stage B: Compose and health

Containerize StrategyLab if necessary, add root Compose, configure internal networking and volumes, and expose Pine2Python readiness through StrategyLab. Do not proceed until both services start and health checks pass.

### Stage C: client, settings, and records

Implement configuration, typed client, error mapping, SQLite tables, repository methods, and integration artifact paths. Test without modifying strategy engines.

### Stage D: dataset identity

Add content hashes and manifest creation. Prove existing datasets remain readable and unchanged.

### Stage E: StrategyLab trace contract

Implement the streaming trace collector and instrument the first vertical engine. Prove identical existing behavior with tracing disabled and enabled.

### Stage F: end-to-end MA/ATR integration

Add generation, analysis, local execution, Python trace, and parity endpoints for `ma_cross_atr_stop_v1`. Complete the container-level vertical test.

### Stage G: phase artifacts and UI

Connect Phase 1, 1.5, and 2 documents and endpoints. Add fixture-manifest generation and Pine evidence UI.

### Stage H: remaining engine traces

Instrument all current engine paths with minimum traces and explicit Pine port capability. Do not create generator adapters without proven Pine semantics.

### Stage I: hardening and documentation

Complete security review, failure states, regression suite, operator docs, vendor-update procedure, and final integration report.

Each stage must leave the repository runnable and tested.

---

## 27. Exact files likely to be added or changed

Adapt paths after inspection, while keeping responsibilities clear.

```text
StrategyLab/
├── Dockerfile                                  # add if absent
├── compose.yaml                                # add or extend
├── .dockerignore
├── .env.example
├── requirements.txt                            # add HTTP client only if needed
├── README.md                                   # container and Pine evidence workflow
├── services/
│   └── pine2python/                            # vendored complete mini-repo
├── app/
│   ├── config.py                               # Pine2Python settings
│   ├── main.py                                 # new endpoints and health
│   ├── storage.py                              # additive tables and repository methods
│   ├── data.py                                 # dataset hashing and manifest creation
│   ├── lab.py                                  # lifecycle orchestration calls
│   ├── backtest.py                             # optional trace collector argument and engine emissions
│   ├── tracing.py                              # standard JSONL trace writer
│   ├── trace_contracts.py                      # field contracts and parity mapping
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── pine2python_client.py
│   │   └── pine2python_models.py
│   └── ui/
│       └── ...                                 # evidence panel and actions
├── strategies/
│   └── *_parent.json                           # optional semantics/ports/trace/parity sections
├── agents/
│   ├── docs/universal_mutation_constitution.md # narrow evidence-chain addition only
│   └── translation and generation/whitebox/
│       ├── 01_translation.md
│       ├── 01-5_baseline_transformation.md
│       ├── 02_baseline.md
│       └── later phase prompts as applicable
├── artifacts/integration/pine2python/
│   └── implementation-decisions.md
└── tests or app/tests.py                       # adapt to current discovery convention
```

If the existing test discovery only matches `app/tests.py`, either add integration tests there or deliberately modernize discovery while ensuring the documented command runs all old and new tests. Do not create tests that CI never executes.

---

## 28. Acceptance matrix

The integration is complete only when every row passes.

| Area | Acceptance condition |
|---|---|
| Existing behavior | Pre-integration StrategyLab test suite still passes; existing baseline metrics/trades are unchanged |
| Vendor integrity | Pine2Python folder is complete, independently testable, and retains licenses and lockfiles |
| Container | Root Compose starts StrategyLab and Pine2Python with internal health checks |
| Readiness | StrategyLab accurately reports enabled/disabled/degraded/ready Pine2Python state |
| Dataset identity | Existing and new datasets can produce immutable manifests with verified hashes |
| Source analysis | StrategyLab can analyze preserved Pine and store analysis/capability artifacts |
| Phase 1.5 | StrategyLab can prepare an automated review package and timestamped fixture manifest while retaining manual acceptance |
| Python traces | Every current engine emits the minimum trace contract when requested without changing behavior |
| Vertical parity | `ma_cross_atr_stop_v1` completes generation, Pine execution, Python execution, trace import, and parity comparison |
| Phase 2 | Parity evidence is stored at criterion/field level with first-divergence context |
| Generation | Supported versions generate Pine through explicit adapters; unsupported engines report honestly |
| Promotion boundary | Pine2Python cannot promote or optimize; StrategyLab remains authoritative |
| Security | Shared roots, path controls, non-root container, read-only filesystem, limits, and error sanitization are preserved |
| Licensing | Pine2Python AGPL and third-party notices remain visible in the integrated repository |
| UI | Operators can see status, prerequisites, first divergence, and artifact links |
| Documentation | README, phase prompts, operator workflow, and update procedure describe implemented behavior |
| End-to-end test | Compose-based public-API smoke test passes from fresh build |

---

## 29. Final integration report required from Codex

Create `PINE2PYTHON_INTEGRATION_REPORT.md` at the StrategyLab root. It must contain connected prose explaining the final architecture, followed by genuinely useful reference tables for files, endpoints, schemas, and tests.

The report must include:

```text
baseline StrategyLab commit and test result
vendored Pine2Python source identity
files added and changed
Compose topology
configuration variables
SQLite schema changes
dataset identity changes
trace contract implementation by engine
new API endpoints
phase-prompt changes
vertical MA/ATR parity result
existing regression results
container smoke-test commands and results
security controls
licenses and notices
known unsupported Pine semantics
remaining manual TradingView requirements
future adapter candidates
```

Include sample IDs and artifact paths from one successful end-to-end run. State every incomplete item honestly. Do not call the integration production-ready when the required vertical parity test or existing regression suite fails.

---

## 30. Final architectural principle

StrategyLab is the laboratory and ledger. It owns the scientific question, the frozen parent, the mutation hypothesis, the evidence contract, the test context, the economic evaluation, the robustness gates, and the promotion decision. Pine2Python is an instrument inside that laboratory. It turns Pine source into structured evidence, executes the subset it can support, and tells StrategyLab exactly where Pine-derived and Python-derived behavior first diverge.

Build the integration so that this relationship remains obvious in code, data, UI, and documentation. The finished system should reduce manual Pine porting effort while increasing rigor. It should never obtain convenience by erasing uncertainty or bypassing TradingView’s authoritative boundary.
