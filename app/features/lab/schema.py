from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    source_run_id: str
    max_variants: int = Field(default=9, ge=1, le=16)


class ProposalRequest(BaseModel):
    family_id: str
    proposal_type: Literal["parameter_patch", "rule_toggle", "candidate_manifest"]
    hypothesis: str
    patch: dict[str, float | int | bool | str] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    family_id: str
    dataset_id: str
