from __future__ import annotations

import contextvars
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.infra.logging import get_logger
from app.shared.errors import AppError


request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get("")


def attach_http_runtime(app: FastAPI) -> None:
    logger = get_logger("strategylab.http")

    @app.middleware("http")
    async def request_runtime(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
        request_id_var.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except AppError as exc:
            logger.warning(
                exc.message,
                extra={"request_id": request_id, "extra_data": {"code": exc.code, "status": exc.status}},
            )
            return JSONResponse(status_code=exc.status, content=exc.to_payload(request_id))
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "unhandled error",
                extra={"request_id": request_id, "extra_data": {"error": str(exc)}},
            )
            return JSONResponse(
                status_code=500,
                content=AppError(500, "INTERNAL_ERROR", "unexpected server error").to_payload(request_id),
            )
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_payload(getattr(request.state, "request_id", "")),
        )
