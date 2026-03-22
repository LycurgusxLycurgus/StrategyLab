from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: int
    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None


class AppError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self, request_id: str | None = None) -> dict:
        return ErrorResponse(
            status=self.status,
            code=self.code,
            message=self.message,
            details=self.details or None,
            request_id=request_id,
        ).model_dump()
