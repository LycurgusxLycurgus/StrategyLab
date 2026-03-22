from __future__ import annotations

from fastapi import APIRouter, Request

from app.features.strategies.schema import StrategyDraftRequest


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/families")
def list_families(request: Request) -> list[dict]:
    return [manifest.model_dump() for manifest in request.app.state.strategy_service.list_families()]


@router.get("/families/{family_id}")
def get_family(family_id: str, request: Request) -> dict:
    return request.app.state.strategy_service.get_family(family_id).model_dump()


@router.post("/drafts")
def create_draft(payload: StrategyDraftRequest, request: Request) -> dict:
    return request.app.state.strategy_service.create_draft(payload).model_dump()
