from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, cast

from .analyzer import analyze_source
from .artifacts import ArtifactStore
from .config import Settings, settings
from .errors import Pine2PythonError
from .generators import ADAPTERS, generate_adapter
from .hashing import sha256_bytes
from .models import (
    AnalyzeRequest,
    Candle,
    GenerateRequest,
    ParityRequest,
    ProofRequest,
    RuntimeRequest,
    TradingViewObservationRequest,
)
from .parity import compare_traces
from .proof import (
    LANES,
    compare_tradingview_observation,
    create_proof,
    generate_dashboard_source,
)
from .runtime import execute_pine
from .version import (
    PROOF_SCHEMA_VERSION,
    SCHEMA_VERSION,
    SERVICE_VERSION,
    TRACE_SCHEMA_VERSION,
)


class Pine2PythonService:
    def __init__(self, service_settings: Settings = settings) -> None:
        self.settings = service_settings
        self.settings.ensure_dirs()
        self.artifacts = ArtifactStore(self.settings.artifact_root)

    def version(self) -> dict[str, Any]:
        return {
            "service": "pine2python",
            "service_version": SERVICE_VERSION,
            "schemas": {
                "api": SCHEMA_VERSION,
                "proof": PROOF_SCHEMA_VERSION,
                "trace": TRACE_SCHEMA_VERSION,
            },
            "dependencies": {
                "pynescript": "0.3.0",
                "pinets": "0.9.29",
            },
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            **self.version(),
            "official_tradingview_runtime": False,
            "operations": {
                "source_analysis": "supported",
                "local_runtime": "capability_gated",
                "trace_comparison": "supported",
                "tradingview_parity_dashboard": "supported",
                "paid_chart_export_required": False,
                "arbitrary_pine_to_python_translation": "unsupported",
                "optimization": "forbidden",
                "promotion": "forbidden",
            },
            "tradingview_profiles": {
                "basic_v1": {
                    "max_bars": 5_000,
                    "default_manual_evidence": "one dashboard screenshot",
                }
            },
            "fingerprint_lanes": [asdict(lane) for lane in LANES],
            "generator_adapters": ADAPTERS,
        }

    def analyze(self, request: AnalyzeRequest) -> dict[str, Any]:
        analysis = analyze_source(
            request.source,
            name=request.name,
            max_source_bytes=self.settings.max_source_bytes,
        )
        public_analysis = {
            **analysis,
            "parser": {
                **analysis["parser"],
                "ast_dump": None,
                "normalized_source": None,
            },
        }
        artifact = self.artifacts.put_bundle(
            "analysis",
            request.model_dump(),
            {
                "source.pine": request.source,
                "analysis.json": analysis,
                "ast.txt": analysis["parser"]["ast_dump"] or "",
                "normalized.pine": analysis["parser"]["normalized_source"] or "",
            },
        )
        return {**public_analysis, "artifact": artifact}

    @staticmethod
    def _proof_runtime_candles(
        request: ProofRequest,
    ) -> tuple[list[Candle], dict[str, Any]]:
        declared_start = request.settings.get("state_start_ms")
        if declared_start is None:
            state_start_ms = min(candle.time for candle in request.candles)
            basis = "dataset_history"
        elif isinstance(declared_start, bool) or not isinstance(
            declared_start, int
        ):
            raise Pine2PythonError(
                "INVALID_STATE_START",
                "settings.state_start_ms must be an integer UNIX timestamp in milliseconds.",
            )
        else:
            state_start_ms = declared_start
            basis = "declared_state_reset"
        if state_start_ms > request.start_ms:
            raise Pine2PythonError(
                "STATE_START_AFTER_PROOF_WINDOW",
                "settings.state_start_ms cannot be later than the proof window start.",
                {
                    "state_start_ms": state_start_ms,
                    "proof_start_ms": request.start_ms,
                },
            )
        candles = [
            candle
            for candle in request.candles
            if state_start_ms <= candle.time < request.end_ms
        ]
        if not candles:
            raise Pine2PythonError(
                "EMPTY_RUNTIME_WINDOW",
                "No candles remain inside the declared proof runtime boundary.",
                {
                    "state_start_ms": state_start_ms,
                    "proof_end_ms": request.end_ms,
                },
            )
        return candles, {
            "basis": basis,
            "state_start_ms": state_start_ms,
            "start_ms": candles[0].time,
            "end_exclusive_ms": request.end_ms,
            "bar_count": len(candles),
        }

    def proof(self, request: ProofRequest) -> dict[str, Any]:
        proof = create_proof(request)
        runtime_instrumented_source = generate_dashboard_source(
            request,
            base_source_sha256=proof["identity"]["source_sha256"],
            settings_sha256=proof["identity"]["settings_sha256"],
            emit_runtime_plots=True,
        )
        runtime_instrumented_sha256 = sha256_bytes(
            runtime_instrumented_source.encode("utf-8")
        )
        runtime_candles, runtime_window = self._proof_runtime_candles(request)
        local_runtime: dict[str, Any]
        local_trace: dict[str, Any] | None = None
        if request.local_runtime_policy == "skip_static_blockers":
            local_runtime = {
                "status": "LOCAL_PROOF_RUNTIME_UNAVAILABLE",
                "matched": None,
                "error": {
                    "code": "LOCAL_RUNTIME_SKIPPED_FROM_REVISION_ANALYSIS",
                    "message": (
                        "Local runtime was skipped because the immutable "
                        "revision already records unsupported constructs."
                    ),
                    "details": {
                        "blockers": request.local_runtime_blockers,
                    },
                    "request_id": None,
                },
                "runtime_window": runtime_window,
                "instrumented_source_sha256": runtime_instrumented_sha256,
            }
        else:
            try:
                runtime_result = execute_pine(
                    runtime_instrumented_source,
                    runtime_candles,
                    service_settings=self.settings,
                    analysis_source=request.source,
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                )

                def final_plot(title: str) -> int | None:
                    data = runtime_result.get("plots", {}).get(title, {}).get("data", [])
                    if not data:
                        return None
                    value = data[-1].get("value")
                    return None if value is None else round(float(value))

                observed_data = [
                    final_plot(f"p2p__proof__data_h{lane}") for lane in range(1, 4)
                ]
                observed_segments = [
                    [
                        final_plot(f"p2p__proof__segment_{segment}_h{lane}")
                        for lane in range(1, 4)
                    ]
                    for segment in range(1, request.segments + 1)
                ]
                observed_streams = {
                    name: [
                        final_plot(f"p2p__proof__{name}_h{lane}")
                        for lane in range(1, 4)
                    ]
                    for name, expressions in request.stream_expressions.items()
                    if expressions
                }
                dataset_match = (
                    observed_data == proof["dataset"]["fingerprint"]
                    and observed_segments == proof["dataset"]["segments"]
                )
                streams_complete = all(
                    all(value is not None for value in fingerprint)
                    for fingerprint in observed_streams.values()
                )
                has_reference_streams = bool(proof["streams"])
                stream_match = (
                    all(
                        observed_streams[name] == value["fingerprint"]
                        for name, value in proof["streams"].items()
                    )
                    if has_reference_streams
                    else streams_complete
                )
                local_match = dataset_match and stream_match
                if not has_reference_streams and local_match:
                    proof["streams"] = {
                        name: {"fingerprint": fingerprint}
                        for name, fingerprint in observed_streams.items()
                    }
                    proof["dashboard_values"].update(
                        {
                            name.upper(): "-".join(
                                f"{cast(int, value):07d}"
                                for value in fingerprint
                            )
                            for name, fingerprint in observed_streams.items()
                        }
                    )
                if not local_match:
                    local_status = "LOCAL_PROOF_PARITY_FAIL"
                elif has_reference_streams:
                    local_status = "LOCAL_PROOF_PARITY_PASS"
                else:
                    local_status = "LOCAL_PROOF_CAPTURE_COMPLETE"
                local_runtime = {
                    "status": local_status,
                    "matched": local_match,
                    "validation_basis": (
                        "caller_reference_trace"
                        if has_reference_streams
                        else "pinets_stream_capture"
                    ),
                    "observed": {
                        "dataset": observed_data,
                        "segments": observed_segments,
                        "streams": observed_streams,
                    },
                    "runtime_window": runtime_window,
                    "instrumented_source_sha256": runtime_instrumented_sha256,
                }
                local_trace = runtime_result.get("trace")
            except Pine2PythonError as exc:
                local_runtime = {
                    "status": "LOCAL_PROOF_RUNTIME_UNAVAILABLE",
                    "matched": None,
                    "error": exc.envelope()["error"],
                    "runtime_window": runtime_window,
                    "instrumented_source_sha256": runtime_instrumented_sha256,
                }
        proof["local_runtime"] = local_runtime
        if local_trace is not None:
            proof["local_trace"] = local_trace
        public = dict(proof)
        trace_summary = (
            {
                "schema_version": local_trace["schema_version"],
                "engine_id": local_trace["engine_id"],
                "row_count": len(local_trace["rows"]),
                "capabilities": local_trace["capabilities"],
            }
            if local_trace is not None
            else None
        )
        proof_artifact_payload = {
            **public,
            "instrumented_source": None,
            "local_trace": trace_summary,
        }
        trace_jsonl = (
            "\n".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"))
                for row in local_trace["rows"]
            )
            + "\n"
            if local_trace is not None and local_trace["rows"]
            else ""
        )
        artifact = self.artifacts.put_bundle(
            "tradingview-proof",
            request.model_dump(),
            {
                "proof.json": proof_artifact_payload,
                "instrumented.pine": proof["instrumented_source"],
                "local-runtime-instrumented.pine": runtime_instrumented_source,
                "local-runtime.json": local_runtime,
                "local-trace.jsonl": trace_jsonl,
                "local-trace-summary.json": trace_summary or {},
            },
        )
        return {**public, "artifact": artifact}

    def observe(self, request: TradingViewObservationRequest) -> dict[str, Any]:
        result = compare_tradingview_observation(request)
        artifact = self.artifacts.put_bundle(
            "tradingview-observation",
            request.model_dump(),
            {"comparison.json": result},
        )
        return {**result, "artifact": artifact}

    def runtime(self, request: RuntimeRequest) -> dict[str, Any]:
        result = execute_pine(
            request.source,
            request.candles,
            service_settings=self.settings,
            symbol=request.symbol,
            timeframe=request.timeframe,
            timeout_seconds=request.timeout_seconds,
        )
        artifact = self.artifacts.put_bundle(
            "runtime",
            request.model_dump(),
            {"runtime.json": result},
        )
        return {**result, "artifact": artifact}

    def parity(self, request: ParityRequest) -> dict[str, Any]:
        result = compare_traces(
            request.reference_rows,
            request.candidate_rows,
            request.contract,
        )
        artifact = self.artifacts.put_bundle(
            "parity",
            request.model_dump(),
            {"parity.json": result},
        )
        return {**result, "artifact": artifact}

    def generate(self, adapter_id: str, request: GenerateRequest) -> dict[str, Any]:
        result = generate_adapter(adapter_id, request)
        public = dict(result)
        artifact = self.artifacts.put_bundle(
            "generation",
            {"adapter_id": adapter_id, **request.model_dump()},
            {
                "generation.json": {
                    **public,
                    "source": None,
                    "preview_instrumented_source": None,
                },
                "generated.pine": result["source"],
                "proof-preview.pine": result["preview_instrumented_source"],
            },
        )
        return {**public, "artifact": artifact}
