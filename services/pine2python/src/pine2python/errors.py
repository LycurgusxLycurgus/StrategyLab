from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Pine2PythonError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None
    status_code: int = 400

    def __str__(self) -> str:
        return self.message

    def envelope(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details or {},
                "request_id": request_id,
            }
        }
