from __future__ import annotations

from fastapi import APIRouter, Request

from app.features.backtests.schema import BacktestRunRequest, FamilySweepRequest


router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("/runs")
def list_runs(request: Request) -> list[dict]:
    return request.app.state.backtest_service.list_runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    return request.app.state.backtest_service.get_run(run_id)


@router.delete("/runs/{run_id}")
def delete_run(run_id: str, request: Request) -> dict:
    return request.app.state.backtest_service.delete_run(run_id)


@router.post("/runs/{run_id}/rerun")
def rerun_run(run_id: str, request: Request) -> dict:
    return request.app.state.backtest_service.rerun(run_id).model_dump()


@router.post("/run")
def run_backtest(payload: BacktestRunRequest, request: Request) -> dict:
    return request.app.state.backtest_service.run_backtest(payload).model_dump()


@router.post("/sweep")
def run_family_sweep(payload: FamilySweepRequest, request: Request) -> dict:
    return request.app.state.backtest_service.run_family_sweep(payload).model_dump()
