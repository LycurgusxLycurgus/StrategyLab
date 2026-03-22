from __future__ import annotations

from fastapi import APIRouter, Request

from app.features.data.schema import BinanceDatasetRequest, DemoDatasetRequest, ImportDatasetRequest


router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/datasets")
def list_datasets(request: Request) -> list[dict]:
    return [dataset.model_dump() for dataset in request.app.state.data_service.list_datasets()]


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, request: Request) -> dict:
    return request.app.state.data_service.delete_dataset(dataset_id)


@router.post("/import")
def import_dataset(payload: ImportDatasetRequest, request: Request) -> dict:
    return request.app.state.data_service.import_dataset(payload).model_dump()


@router.post("/demo")
def create_demo_dataset(payload: DemoDatasetRequest, request: Request) -> dict:
    return request.app.state.data_service.create_demo_dataset(payload).model_dump()


@router.post("/binance")
def import_binance_dataset(payload: BinanceDatasetRequest, request: Request) -> dict:
    return request.app.state.data_service.import_binance_dataset(payload).model_dump()
