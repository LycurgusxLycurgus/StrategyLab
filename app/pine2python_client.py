from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings, settings


@dataclass(slots=True)
class Pine2PythonClientError(Exception):
    code: str
    message: str
    details: dict[str, Any]
    status_code: int = 502

    def __str__(self) -> str:
        return self.message


class Pine2PythonClient:
    """Typed StrategyLab boundary for HTTP or explicit local fallback."""

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self._local_service: Any = None
        self._prefer_local = False

    def _http(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        data = (
            json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(
                "utf-8"
            )
            if payload is not None
            else None
        )
        request = Request(
            f"{self.settings.pine2python_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(
                request,
                timeout=(
                    timeout_seconds
                    if timeout_seconds is not None
                    else self.settings.pine2python_timeout_seconds
                ),
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                envelope = json.loads(raw).get("error", {})
            except json.JSONDecodeError:
                envelope = {}
            raise Pine2PythonClientError(
                envelope.get("code", "PINE2PYTHON_HTTP_ERROR"),
                envelope.get("message", raw or str(exc)),
                envelope.get("details", {}),
                exc.code,
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise Pine2PythonClientError(
                "PINE2PYTHON_UNAVAILABLE",
                f"Pine2Python is unavailable at {self.settings.pine2python_url}.",
                {"reason": str(exc)},
                503,
            ) from exc

    def _local(self) -> Any:
        if self._local_service is not None:
            return self._local_service
        try:
            from pine2python.config import Settings as ServiceSettings
            from pine2python.service import Pine2PythonService
        except ImportError as exc:
            raise Pine2PythonClientError(
                "PINE2PYTHON_LOCAL_PACKAGE_MISSING",
                "The embedded Pine2Python package is not installed in this environment.",
                {"reason": str(exc)},
                503,
            ) from exc
        root = self.settings.pine_development_dir
        self._local_service = Pine2PythonService(
            ServiceSettings(
                artifact_root=root / "pine2python-artifacts",
                work_root=root / "pine2python-work",
            )
        )
        return self._local_service

    def status(self) -> dict[str, Any]:
        if not self.settings.pine2python_enabled:
            return {
                "status": "disabled",
                "required": self.settings.pine2python_required,
                "transport": None,
            }
        try:
            version = self._http("GET", "/v1/version", timeout_seconds=2)
            capabilities = self._http(
                "GET", "/v1/capabilities", timeout_seconds=2
            )
            self._prefer_local = False
            return {
                "status": "ready",
                "required": self.settings.pine2python_required,
                "transport": "http",
                "version": version,
                "capabilities": capabilities,
            }
        except Pine2PythonClientError as remote_error:
            if not self.settings.pine2python_local_fallback:
                return {
                    "status": "unavailable",
                    "required": self.settings.pine2python_required,
                    "transport": None,
                    "error": {
                        "code": remote_error.code,
                        "message": remote_error.message,
                    },
                }
            try:
                local = self._local()
                self._prefer_local = True
                return {
                    "status": "ready",
                    "required": self.settings.pine2python_required,
                    "transport": "local_embedded",
                    "version": local.version(),
                    "capabilities": local.capabilities(),
                    "http_error": {
                        "code": remote_error.code,
                        "message": remote_error.message,
                    },
                }
            except Pine2PythonClientError as local_error:
                return {
                    "status": "unavailable",
                    "required": self.settings.pine2python_required,
                    "transport": None,
                    "error": {
                        "code": local_error.code,
                        "message": local_error.message,
                    },
                }

    def _call_local(
        self,
        local_method: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        adapter_id: str | None,
        remote_error: Pine2PythonClientError | None = None,
    ) -> dict[str, Any]:
        try:
            from pine2python import models

            model = getattr(models, model_name).model_validate(payload)
            method = getattr(self._local(), local_method)
            self._prefer_local = True
            if adapter_id is None:
                return method(model)
            return method(adapter_id, model)
        except Pine2PythonClientError:
            raise
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                raise Pine2PythonClientError(
                    str(exc.code),
                    str(exc.message),
                    getattr(exc, "details", {}) or {},
                    getattr(exc, "status_code", 400),
                ) from exc
            details = (
                {"remote_error": remote_error.message}
                if remote_error is not None
                else {}
            )
            raise Pine2PythonClientError(
                "PINE2PYTHON_LOCAL_FAILURE",
                str(exc),
                details,
                500,
            ) from exc

    def _call(
        self,
        path: str,
        local_method: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        adapter_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.pine2python_enabled:
            raise Pine2PythonClientError(
                "PINE2PYTHON_DISABLED",
                "Pine2Python is disabled by configuration.",
                {},
                503,
            )
        if self.settings.pine2python_local_fallback and self._prefer_local:
            return self._call_local(
                local_method,
                model_name,
                payload,
                adapter_id=adapter_id,
            )
        try:
            result = self._http("POST", path, payload)
            self._prefer_local = False
            return result
        except Pine2PythonClientError as remote_error:
            if not self.settings.pine2python_local_fallback:
                raise
            return self._call_local(
                local_method,
                model_name,
                payload,
                adapter_id=adapter_id,
                remote_error=remote_error,
            )

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "/v1/analyses", "analyze", "AnalyzeRequest", payload
        )

    def proof(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("/v1/proofs", "proof", "ProofRequest", payload)

    def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "/v1/tradingview-observations",
            "observe",
            "TradingViewObservationRequest",
            payload,
        )

    def parity(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "/v1/parity-comparisons", "parity", "ParityRequest", payload
        )

    def generate(
        self, adapter_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call(
            f"/v1/generators/{adapter_id}",
            "generate",
            "GenerateRequest",
            payload,
            adapter_id=adapter_id,
        )
