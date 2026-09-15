from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.backtest import BacktestEngine
from app.config import settings
from app.data import DataService
from app.pine2python_client import Pine2PythonClient, Pine2PythonClientError
from app.pine_review import PineReviewContractError, build_review_package
from app.storage import Repository

WORKBENCH_MODES = {
    "greenfield_strategy",
    "source_adaptation",
    "indicator_first",
}
PINE_PROOF_INSTRUMENTATION_VERSION = "tv_table_v2_12"


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _status_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class PineWorkbenchService:
    def __init__(
        self,
        repo: Repository,
        data_service: DataService,
        client: Pine2PythonClient | None = None,
    ) -> None:
        self.repo = repo
        self.data_service = data_service
        self.client = client or Pine2PythonClient()
        self.engine = BacktestEngine()

    @staticmethod
    def _raise_client_error(exc: Pine2PythonClientError) -> None:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        payload = content.encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise HTTPException(
                    status_code=409,
                    detail=f"Immutable artifact collision at {path.name}.",
                )
            return
        handle, temp_name = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def status(self) -> dict[str, Any]:
        return self.client.status()

    def create_revision(
        self,
        *,
        source_code: str,
        source_name: str,
        mode: str,
        settings_payload: dict[str, Any],
        provenance: dict[str, Any],
        workbench_id: str | None,
        parent_revision_id: str | None,
    ) -> dict[str, Any]:
        if mode not in WORKBENCH_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"mode must be one of {sorted(WORKBENCH_MODES)}.",
            )
        if not source_code.strip():
            raise HTTPException(status_code=400, detail="Pine source is empty.")
        if mode == "source_adaptation":
            missing = [
                field
                for field in ("source_url", "license")
                if not str(provenance.get(field, "")).strip()
            ]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Source adaptations require explicit provenance.",
                        "missing": missing,
                    },
                )
        parent = None
        if parent_revision_id:
            parent = self.repo.get_pine_revision(parent_revision_id)
            if not parent:
                raise HTTPException(
                    status_code=404, detail="Parent Pine revision not found."
                )
            if workbench_id and parent["workbench_id"] != workbench_id:
                raise HTTPException(
                    status_code=409,
                    detail="Parent revision belongs to another workbench.",
                )
            workbench_id = parent["workbench_id"]
        source_hash = _sha256(source_code.encode("utf-8"))
        workbench_id = workbench_id or f"pwb_{source_hash[:12]}"
        identity = {
            "workbench_id": workbench_id,
            "parent_revision_id": parent_revision_id,
            "mode": mode,
            "source_sha256": source_hash,
            "settings": settings_payload,
            "provenance": provenance,
        }
        revision_id = f"pvr_{_sha256(_canonical_bytes(identity))[:20]}"
        existing = self.repo.get_pine_revision(revision_id)
        if existing:
            return self.revision_detail(revision_id)
        try:
            analysis = self.client.analyze(
                {
                    "source": source_code,
                    "name": source_name,
                    "provenance": provenance,
                }
            )
        except Pine2PythonClientError as exc:
            self._raise_client_error(exc)
        declaration = analysis.get("inventory", {}).get("declaration")
        if mode == "indicator_first" and declaration != "indicator":
            raise HTTPException(
                status_code=400,
                detail="indicator_first revisions must declare indicator().",
            )
        status = list(analysis.get("status", []))
        payload = {
            "revision_id": revision_id,
            "workbench_id": workbench_id,
            "parent_revision_id": parent_revision_id,
            "mode": mode,
            "stage": "pre_phase_1",
            "source_sha256": source_hash,
            "source_code": source_code,
            "settings": settings_payload,
            "provenance": provenance,
            "analysis": {
                "artifact": analysis.get("artifact"),
                "inventory": analysis.get("inventory"),
                "temporal_findings": analysis.get("temporal_findings"),
                "capabilities": analysis.get("capabilities"),
                "parser": analysis.get("parser"),
            },
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_revision(payload)
        revision_dir = settings.pine_development_dir / workbench_id / revision_id
        self._atomic_write(revision_dir / "source.pine", source_code)
        self._atomic_write(
            revision_dir / "revision.json",
            json.dumps(
                {**payload, "source_code": None},
                indent=2,
                sort_keys=True,
            ),
        )
        return self.revision_detail(revision_id)

    def list_revisions(self, workbench_id: str | None = None) -> list[dict[str, Any]]:
        return [
            {**revision, "source_code": None}
            for revision in self.repo.list_pine_revisions(workbench_id)
        ]

    def list_version_evidence(self, version_id: str) -> list[dict[str, Any]]:
        if not self.repo.get_version(version_id):
            raise HTTPException(status_code=404, detail="Strategy version not found.")
        return self.repo.list_pine_evidence(strategy_version_id=version_id)

    def revision_detail(self, revision_id: str) -> dict[str, Any]:
        revision = self.repo.get_pine_revision(revision_id)
        if not revision:
            raise HTTPException(status_code=404, detail="Pine revision not found.")
        return {
            **revision,
            "evidence": self.repo.list_pine_evidence(revision_id=revision_id),
        }

    def generate_revision(
        self,
        adapter_id: str,
        *,
        generator_payload: dict[str, Any],
        workbench_id: str | None,
        parent_revision_id: str | None,
    ) -> dict[str, Any]:
        try:
            generated = self.client.generate(adapter_id, generator_payload)
        except Pine2PythonClientError as exc:
            self._raise_client_error(exc)
        revision = self.create_revision(
            source_code=str(generated["source"]),
            source_name=f"{adapter_id}.pine",
            mode="greenfield_strategy",
            settings_payload=dict(generated.get("settings", {})),
            provenance={
                "origin": "pine2python_registered_adapter",
                "adapter_id": adapter_id,
                "generator_artifact": generated.get("artifact"),
                "trace_contract": generated.get("trace_contract", {}),
            },
            workbench_id=workbench_id,
            parent_revision_id=parent_revision_id,
        )
        return {
            **revision,
            "generation": {
                **generated,
                "source": None,
                "preview_instrumented_source": None,
            },
        }

    def create_proof(
        self,
        revision_id: str,
        *,
        dataset_id: str,
        start_ms: int,
        end_ms: int,
        mintick: float,
        trace_rows: list[dict[str, Any]],
        stream_expressions: dict[str, list[dict[str, Any]]],
        profile: str,
    ) -> dict[str, Any]:
        revision = self.repo.get_pine_revision(revision_id)
        if not revision:
            raise HTTPException(status_code=404, detail="Pine revision not found.")
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        bars = self.data_service.load_bars(dataset_id)
        proof_bars = [
            bar
            for bar in bars
            if start_ms <= int(bar.ts.timestamp() * 1000) < end_ms
        ]
        if not proof_bars:
            raise HTTPException(
                status_code=400,
                detail="The selected Pine proof window contains no dataset bars.",
            )
        revision_settings = revision.get("settings", {})
        declared_state_start = revision_settings.get("state_start_ms")
        state_start_ms = (
            declared_state_start
            if isinstance(declared_state_start, int)
            and not isinstance(declared_state_start, bool)
            else start_ms
        )
        if state_start_ms > start_ms:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The Pine revision state_start_ms cannot be later than "
                    "the proof window start."
                ),
            )
        runtime_bars = [
            bar
            for bar in bars
            if state_start_ms <= int(bar.ts.timestamp() * 1000) < end_ms
        ]
        if not runtime_bars:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The selected Pine proof runtime boundary contains no "
                    "dataset bars."
                ),
            )
        dataset_hash = self.data_service.dataset_content_hash(dataset_id)
        effective_stream_expressions = (
            stream_expressions
            or revision.get("provenance", {}).get("trace_contract", {})
        )
        proof_symbol = str(
            revision_settings.get("tradingview_symbol")
            or dataset["symbol"]
        ).strip()
        proof_timeframe = str(
            revision_settings.get("tradingview_timeframe")
            or revision_settings.get("chart_timeframe")
            or dataset["timeframe"]
        ).strip()
        declaration = (
            revision.get("analysis", {}).get("inventory", {}).get("declaration")
            or "strategy"
        )
        capabilities = revision.get("analysis", {}).get("capabilities", {})
        runtime_blockers = list(capabilities.get("runtime_blockers") or [])
        skip_static_runtime = (
            capabilities.get("local_runtime") == "blocked"
            and bool(runtime_blockers)
        )
        request_payload = {
            "source": revision["source_code"],
            "source_name": f"{revision_id}.pine",
            "source_id": revision_id,
            "dataset_sha256": dataset_hash["sha256"],
            "settings": revision["settings"],
            "profile": profile,
            "instrumentation_version": PINE_PROOF_INSTRUMENTATION_VERSION,
            "symbol": proof_symbol,
            "timeframe": proof_timeframe,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "mintick": mintick,
            "candles": [
                {
                    "time": int(bar.ts.timestamp() * 1000),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in runtime_bars
            ],
            "trace_rows": trace_rows,
            "stream_expressions": effective_stream_expressions,
            "declaration_kind": declaration,
            "local_runtime_policy": (
                "skip_static_blockers" if skip_static_runtime else "attempt"
            ),
            "local_runtime_blockers": (
                runtime_blockers if skip_static_runtime else []
            ),
        }
        try:
            proof = self.client.proof(request_payload)
        except Pine2PythonClientError as exc:
            self._raise_client_error(exc)
        request_hash = _sha256(_canonical_bytes(request_payload))
        evidence_id = f"pev_{request_hash[:20]}"
        proof_dir = (
            settings.pine_development_dir
            / revision["workbench_id"]
            / revision_id
            / "proofs"
            / evidence_id
        )
        instrumented_source = str(proof.get("instrumented_source") or "")
        if instrumented_source:
            self._atomic_write(proof_dir / "instrumented.pine", instrumented_source)
        local_trace = proof.get("local_trace")
        trace_summary = None
        if isinstance(local_trace, dict):
            trace_rows_payload = list(local_trace.get("rows", []))
            trace_summary = {
                "schema_version": local_trace.get("schema_version"),
                "engine_id": local_trace.get("engine_id"),
                "row_count": len(trace_rows_payload),
                "capabilities": local_trace.get("capabilities", {}),
                "dataset_sha256": dataset_hash["sha256"],
            }
            trace_jsonl = "\n".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"))
                for row in trace_rows_payload
            )
            if trace_jsonl:
                trace_jsonl += "\n"
            self._atomic_write(proof_dir / "pine-trace.jsonl", trace_jsonl)
            self._atomic_write(
                proof_dir / "pine-trace-summary.json",
                json.dumps(trace_summary, indent=2, sort_keys=True),
            )
        public_proof = {
            **proof,
            "instrumented_source": None,
            "local_trace": trace_summary,
        }
        self._atomic_write(
            proof_dir / "proof.json",
            json.dumps(public_proof, indent=2, sort_keys=True),
        )
        evidence = {
            "evidence_id": evidence_id,
            "revision_id": revision_id,
            "strategy_version_id": None,
            "dataset_id": dataset_id,
            "kind": "tradingview_proof",
            "request_hash": request_hash,
            "status": _status_list(proof.get("status")),
            "artifact": {
                "strategy_path": str(proof_dir),
                "pine2python": proof.get("artifact"),
                "pine_trace_path": (
                    str(proof_dir / "pine-trace.jsonl")
                    if trace_summary is not None
                    else None
                ),
            },
            "payload": public_proof,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_evidence(evidence)
        if trace_summary is not None:
            trace_request_hash = _sha256(
                f"{request_hash}:local-pine-trace".encode()
            )
            trace_evidence = {
                "evidence_id": f"pev_{trace_request_hash[:20]}",
                "revision_id": revision_id,
                "strategy_version_id": None,
                "dataset_id": dataset_id,
                "kind": "pine_trace",
                "request_hash": trace_request_hash,
                "status": ["LOCAL_PINE_TRACE_COMPLETE"],
                "artifact": {
                    "trace_path": str(proof_dir / "pine-trace.jsonl"),
                    "summary_path": str(
                        proof_dir / "pine-trace-summary.json"
                    ),
                },
                "payload": trace_summary,
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.repo.put_pine_evidence(trace_evidence)
        return {
            **evidence,
            "instrumented_source": instrumented_source,
            "local_trace": local_trace,
        }

    def prepare_review_package(
        self,
        revision_id: str,
        *,
        baseline_revision_id: str,
        fidelity_contract: dict[str, Any],
        trace_evidence_id: str | None,
        trace_rows: list[dict[str, Any]] | None = None,
        max_fixtures: int,
    ) -> dict[str, Any]:
        revision = self.repo.get_pine_revision(revision_id)
        baseline = self.repo.get_pine_revision(baseline_revision_id)
        if not revision or not baseline:
            raise HTTPException(
                status_code=404,
                detail="Candidate or baseline Pine revision was not found.",
            )
        if revision["workbench_id"] != baseline["workbench_id"]:
            raise HTTPException(
                status_code=409,
                detail="Candidate and baseline must belong to the same workbench.",
            )
        effective_contract = (
            fidelity_contract
            or revision.get("provenance", {}).get("fidelity_contract", {})
        )
        if trace_evidence_id and trace_rows is not None:
            raise HTTPException(
                status_code=400,
                detail="Provide trace_evidence_id or trace_rows, not both.",
            )
        if trace_evidence_id:
            trace_evidence = self.repo.get_pine_evidence(trace_evidence_id)
            if (
                not trace_evidence
                or trace_evidence.get("revision_id") != revision_id
                or trace_evidence.get("kind") != "pine_trace"
            ):
                raise HTTPException(
                    status_code=404,
                    detail="Matching Pine trace evidence was not found.",
                )
            trace_path_value = trace_evidence.get("artifact", {}).get(
                "trace_path"
            )
            if not trace_path_value:
                raise HTTPException(
                    status_code=409,
                    detail="Pine trace evidence has no trace artifact.",
                )
            trace_path = Path(str(trace_path_value)).resolve()
            artifact_root = settings.pine_development_dir.resolve()
            try:
                trace_path.relative_to(artifact_root)
            except ValueError as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Pine trace artifact is outside the development root.",
                ) from exc
            if not trace_path.is_file():
                raise HTTPException(
                    status_code=409,
                    detail="Pine trace artifact is missing.",
                )
            trace_rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        try:
            package = build_review_package(
                baseline_revision_id=baseline_revision_id,
                baseline_source=baseline["source_code"],
                candidate_revision_id=revision_id,
                candidate_source=revision["source_code"],
                fidelity_contract=effective_contract,
                trace_rows=trace_rows,
                max_fixtures=max_fixtures,
            )
        except PineReviewContractError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        request_payload = {
            "revision_id": revision_id,
            "baseline_revision_id": baseline_revision_id,
            "fidelity_contract": effective_contract,
            "trace_evidence_id": trace_evidence_id,
            "trace_rows_sha256": (
                _sha256(_canonical_bytes(trace_rows))
                if trace_rows is not None
                else None
            ),
            "max_fixtures": max_fixtures,
        }
        request_hash = _sha256(_canonical_bytes(request_payload))
        evidence_id = f"pev_{request_hash[:20]}"
        package_dir = (
            settings.pine_development_dir
            / revision["workbench_id"]
            / revision_id
            / "reviews"
            / evidence_id
        )
        self._atomic_write(
            package_dir / "review-package.json",
            json.dumps(package, indent=2, sort_keys=True),
        )
        evidence = {
            "evidence_id": evidence_id,
            "revision_id": revision_id,
            "strategy_version_id": None,
            "dataset_id": None,
            "kind": "pine_review_package",
            "request_hash": request_hash,
            "status": package["status"],
            "artifact": {
                "review_package_path": str(
                    package_dir / "review-package.json"
                )
            },
            "payload": package,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_evidence(evidence)
        return evidence

    def observe_tradingview(
        self,
        revision_id: str,
        *,
        proof_evidence_id: str,
        observed: dict[str, Any],
        screenshot_sha256: str | None,
        user_verdict: str,
    ) -> dict[str, Any]:
        revision = self.repo.get_pine_revision(revision_id)
        if not revision:
            raise HTTPException(status_code=404, detail="Pine revision not found.")
        proof_evidence = self.repo.get_pine_evidence(proof_evidence_id)
        if (
            not proof_evidence
            or proof_evidence.get("revision_id") != revision_id
            or proof_evidence.get("kind") != "tradingview_proof"
        ):
            raise HTTPException(
                status_code=404, detail="Matching proof evidence not found."
            )
        request_payload = {
            "expected": proof_evidence["payload"],
            "observed": observed,
            "screenshot_sha256": screenshot_sha256,
            "user_verdict": user_verdict,
        }
        try:
            result = self.client.observe(request_payload)
        except Pine2PythonClientError as exc:
            self._raise_client_error(exc)
        request_hash = _sha256(_canonical_bytes(request_payload))
        evidence_id = f"pev_{request_hash[:20]}"
        evidence = {
            "evidence_id": evidence_id,
            "revision_id": revision_id,
            "strategy_version_id": None,
            "dataset_id": proof_evidence.get("dataset_id"),
            "kind": "tradingview_observation",
            "request_hash": request_hash,
            "status": _status_list(result.get("status")),
            "artifact": result.get("artifact", {}),
            "payload": result,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_evidence(evidence)
        return evidence

    def python_trace(self, version_id: str, dataset_id: str) -> dict[str, Any]:
        version = self.repo.get_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Strategy version not found.")
        if not self.repo.get_dataset(dataset_id):
            raise HTTPException(status_code=404, detail="Dataset not found.")
        bars = self.data_service.load_bars(dataset_id)
        result = self.engine.run(version["spec_json"], bars, collect_trace=True)
        trace = result["trace"]
        dataset_hash = self.data_service.dataset_content_hash(dataset_id)
        request_payload = {
            "version_id": version_id,
            "dataset_id": dataset_id,
            "dataset_sha256": dataset_hash["sha256"],
            "source_spec": version["spec_json"],
        }
        request_hash = _sha256(_canonical_bytes(request_payload))
        evidence_id = f"pev_{request_hash[:20]}"
        trace_dir = (
            settings.pine_development_dir
            / "python-traces"
            / version_id
            / evidence_id
        )
        jsonl = "\n".join(
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in trace["rows"]
        )
        if jsonl:
            jsonl += "\n"
        self._atomic_write(trace_dir / "trace.jsonl", jsonl)
        summary = {
            "schema_version": trace["schema_version"],
            "engine_id": trace["engine_id"],
            "row_count": len(trace["rows"]),
            "capabilities": trace["capabilities"],
            "metrics": result["metrics"],
            "dataset_sha256": dataset_hash["sha256"],
        }
        self._atomic_write(
            trace_dir / "summary.json",
            json.dumps(summary, indent=2, sort_keys=True),
        )
        evidence = {
            "evidence_id": evidence_id,
            "revision_id": None,
            "strategy_version_id": version_id,
            "dataset_id": dataset_id,
            "kind": "python_trace",
            "request_hash": request_hash,
            "status": ["PYTHON_TRACE_COMPLETE"],
            "artifact": {
                "trace_path": str(trace_dir / "trace.jsonl"),
                "summary_path": str(trace_dir / "summary.json"),
            },
            "payload": summary,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_evidence(evidence)
        return evidence

    def compare_parity(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.parity(payload)
        except Pine2PythonClientError as exc:
            self._raise_client_error(exc)
        request_hash = _sha256(_canonical_bytes(payload))
        evidence_id = f"pev_{request_hash[:20]}"
        evidence = {
            "evidence_id": evidence_id,
            "revision_id": None,
            "strategy_version_id": None,
            "dataset_id": None,
            "kind": "parity_comparison",
            "request_hash": request_hash,
            "status": _status_list(result.get("status")),
            "artifact": result.get("artifact", {}),
            "payload": result,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_pine_evidence(evidence)
        return evidence
