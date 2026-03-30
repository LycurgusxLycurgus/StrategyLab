from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WhiteBoxRunRequest(BaseModel):
    dataset_id: str
    profile: Literal["conservative", "balanced", "aggressive"] = "balanced"


class HybridRunRequest(BaseModel):
    dataset_id: str
    profile: Literal["conservative", "balanced", "aggressive"] = "balanced"
    threshold: float | None = None
