from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .errors import Pine2PythonError
from .models import (
    AnalyzeRequest,
    GenerateRequest,
    ParityRequest,
    ProofRequest,
    RuntimeRequest,
    TradingViewObservationRequest,
)
from .service import Pine2PythonService
from .version import SERVICE_VERSION

service = Pine2PythonService()
app = FastAPI(
    title="Pine2Python",
    version=SERVICE_VERSION,
    description="Local Pine analysis, proof, trace, parity, and adapter evidence service.",
)


@app.exception_handler(Pine2PythonError)
async def pine2python_error_handler(
    request: Request, exc: Pine2PythonError
) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    return JSONResponse(exc.envelope(request_id), status_code=exc.status_code)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live", "service": "pine2python"}


@app.get("/health/ready")
def health_ready() -> dict[str, object]:
    return {"status": "ready", **service.version()}


@app.get("/v1/version")
def version() -> dict:
    return service.version()


@app.get("/v1/capabilities")
def capabilities() -> dict:
    return service.capabilities()


@app.post("/v1/analyses")
def analyze(request: AnalyzeRequest) -> dict:
    return service.analyze(request)


@app.post("/v1/proofs")
def proof(request: ProofRequest) -> dict:
    return service.proof(request)


@app.post("/v1/tradingview-observations")
def observe(request: TradingViewObservationRequest) -> dict:
    return service.observe(request)


@app.post("/v1/runtime-executions")
def runtime(request: RuntimeRequest) -> dict:
    return service.runtime(request)


@app.post("/v1/parity-comparisons")
def parity(request: ParityRequest) -> dict:
    return service.parity(request)


@app.post("/v1/generators/{adapter_id}")
def generate(adapter_id: str, request: GenerateRequest) -> dict:
    return service.generate(adapter_id, request)
