from __future__ import annotations

from fastapi import APIRouter, Request

from app.features.lab.schema import OptimizeRequest, ProposalRequest, ReviewRequest


router = APIRouter(prefix="/api/lab", tags=["lab"])


@router.get("/graveyard")
def list_graveyard(request: Request) -> list[dict]:
    return request.app.state.lab_service.list_graveyard()


@router.delete("/graveyard/{artifact_id}")
def delete_graveyard(artifact_id: str, request: Request) -> dict:
    return request.app.state.lab_service.delete_graveyard(artifact_id)


@router.post("/optimize")
def optimize(payload: OptimizeRequest, request: Request) -> dict:
    return request.app.state.lab_service.optimize(payload)


@router.post("/proposals/dry-run")
def create_proposal(payload: ProposalRequest, request: Request) -> dict:
    return request.app.state.lab_service.create_proposal(payload)


@router.post("/review")
def review_family(payload: ReviewRequest, request: Request) -> dict:
    return request.app.state.lab_service.review_family(payload)
