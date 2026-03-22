from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.get("/runs/{run_id}")
def get_run_evaluation(run_id: str, request: Request) -> dict:
    return request.app.state.evaluation_service.get_run_evaluation(run_id)
