from __future__ import annotations

import csv
import math
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import duckdb

from app.features.data.schema import BinanceDatasetRequest, DatasetSummary, DemoDatasetRequest, ImportDatasetRequest
from app.infra.config import AppConfig
from app.infra.db import Database
from app.infra.logging import get_logger
from app.shared.errors import AppError


REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
TIMEFRAMES = {"5m", "1H", "4H"}
BINANCE_INTERVALS = {"5m": "5m", "1H": "1h", "4H": "4h"}
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


class DataService:
    def __init__(self, config: AppConfig, db: Database):
        self.config = config
        self.db = db
        self.logger = get_logger("strategylab.data")

    def import_dataset(self, payload: ImportDatasetRequest) -> DatasetSummary:
        if payload.timeframe not in TIMEFRAMES:
            raise AppError(400, "INVALID_TIMEFRAME", "unsupported timeframe", {"timeframe": payload.timeframe})
        path = Path(payload.path)
        if not path.exists():
            raise AppError(404, "DATASET_NOT_FOUND", "dataset file does not exist", {"path": str(path)})
        rows = self._load_rows(path)
        if len(rows) < 30:
            raise AppError(400, "DATASET_TOO_SMALL", "dataset requires at least 30 rows")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        candle_rows = [
            (
                dataset_id,
                self._parse_timestamp(row["timestamp"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            )
            for row in rows
        ]
        candle_rows.sort(key=lambda item: item[1])
        self.db.executemany(
            """
            insert into candles (dataset_id, ts, open, high, low, close, volume)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            candle_rows,
        )
        start_ts = candle_rows[0][1]
        end_ts = candle_rows[-1][1]
        self.db.execute(
            """
            insert into datasets
            (dataset_id, dataset_name, symbol, timeframe, source_path, row_count, start_ts, end_ts)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                payload.dataset_name,
                payload.symbol,
                payload.timeframe,
                str(path),
                len(candle_rows),
                start_ts,
                end_ts,
            ),
        )
        self.logger.info(
            "dataset imported",
            extra={"extra_data": {"dataset_id": dataset_id, "rows": len(candle_rows), "timeframe": payload.timeframe}},
        )
        return DatasetSummary(
            dataset_id=dataset_id,
            dataset_name=payload.dataset_name,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            row_count=len(candle_rows),
            start_ts=start_ts,
            end_ts=end_ts,
            source_path=str(path),
        )

    def create_demo_dataset(self, payload: DemoDatasetRequest) -> DatasetSummary:
        if payload.timeframe not in TIMEFRAMES:
            raise AppError(400, "INVALID_TIMEFRAME", "unsupported timeframe", {"timeframe": payload.timeframe})
        path = self.config.app_data_dir / f"{payload.dataset_name}.csv"
        rows = self._demo_rows(payload.timeframe, payload.bars)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            writer.writerows(rows)
        return self.import_dataset(
            ImportDatasetRequest(
                path=str(path),
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                dataset_name=payload.dataset_name,
            )
        )

    def import_binance_dataset(self, payload: BinanceDatasetRequest) -> DatasetSummary:
        if payload.timeframe not in BINANCE_INTERVALS:
            raise AppError(400, "INVALID_TIMEFRAME", "unsupported timeframe for Binance download", {"timeframe": payload.timeframe})
        rows = self._fetch_binance_klines(payload.symbol, BINANCE_INTERVALS[payload.timeframe], payload.bars)
        path = self.config.app_data_dir / f"{payload.dataset_name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            writer.writerows(rows)
        return self.import_dataset(
            ImportDatasetRequest(
                path=str(path),
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                dataset_name=payload.dataset_name,
            )
        )

    def list_datasets(self) -> list[DatasetSummary]:
        rows = self.db.fetch_all("select * from datasets order by created_at desc")
        return [DatasetSummary(**row) for row in rows]

    def delete_dataset(self, dataset_id: str) -> dict:
        dataset = self.get_dataset(dataset_id)
        run_rows = self.db.fetch_all(
            "select artifact_path, report_path from backtest_runs where dataset_id = ?",
            (dataset_id,),
        )
        self.db.delete_dataset_related(dataset_id)
        for path_value in [dataset.source_path, *[row["artifact_path"] for row in run_rows], *[row["report_path"] for row in run_rows if row["report_path"]]]:
            if not path_value:
                continue
            path = Path(path_value)
            if path.exists():
                path.unlink()
        return {"dataset_id": dataset_id, "deleted": True}

    def get_dataset(self, dataset_id: str) -> DatasetSummary:
        row = self.db.fetch_one("select * from datasets where dataset_id = ?", (dataset_id,))
        if not row:
            raise AppError(404, "DATASET_NOT_FOUND", "unknown dataset", {"dataset_id": dataset_id})
        return DatasetSummary(**row)

    def load_candles(self, dataset_id: str) -> list[dict]:
        dataset = self.get_dataset(dataset_id)
        return self.db.fetch_all(
            """
            select ts, open, high, low, close, volume
            from candles
            where dataset_id = ?
            order by ts asc
            """,
            (dataset.dataset_id,),
        )

    def _load_rows(self, path: Path) -> list[dict]:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or set(reader.fieldnames) != REQUIRED_COLUMNS:
                    raise AppError(
                        400,
                        "INVALID_COLUMNS",
                        "csv must contain timestamp, open, high, low, close, volume columns",
                        {"columns": reader.fieldnames or []},
                    )
                return [row for row in reader]
        if path.suffix.lower() == ".parquet":
            with duckdb.connect() as conn:
                cursor = conn.execute(f"select * from read_parquet('{self._escape(path)}')")
                columns = [column[0] for column in cursor.description]
                if set(columns) != REQUIRED_COLUMNS:
                    raise AppError(
                        400,
                        "INVALID_COLUMNS",
                        "parquet must contain timestamp, open, high, low, close, volume columns",
                        {"columns": columns},
                    )
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        raise AppError(400, "UNSUPPORTED_FORMAT", "only csv and parquet files are supported")

    def _fetch_binance_klines(self, symbol: str, interval: str, limit: int) -> list[dict]:
        remaining = limit
        end_time_ms: int | None = None
        rows: list[dict] = []
        while remaining > 0:
            batch_size = min(1000, remaining)
            query_args = {"symbol": symbol.upper(), "interval": interval, "limit": batch_size}
            if end_time_ms is not None:
                query_args["endTime"] = end_time_ms
            query = urlencode(query_args)
            url = f"{BINANCE_KLINES_URL}?{query}"
            try:
                with urlopen(url, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except Exception as exc:  # pragma: no cover - network boundary
                raise AppError(
                    502,
                    "BINANCE_FETCH_FAILED",
                    "failed to download market candles from Binance",
                    {"symbol": symbol, "interval": interval, "error": str(exc)},
                ) from exc
            if not isinstance(payload, list) or not payload:
                break
            batch = [
                {
                    "timestamp": int(item[0]) // 1000,
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "volume": item[5],
                }
                for item in payload
            ]
            rows = batch + rows
            remaining -= len(batch)
            oldest_open_ms = int(payload[0][0])
            end_time_ms = oldest_open_ms - 1
            if len(batch) < batch_size:
                break
        deduped: dict[int, dict] = {row["timestamp"]: row for row in rows}
        ordered = [deduped[key] for key in sorted(deduped.keys())]
        return ordered[-limit:]

    @staticmethod
    def _demo_rows(timeframe: str, bars: int) -> list[dict]:
        step = {"5m": 300, "1H": 3600, "4H": 14400}[timeframe]
        start_ts = 1_700_000_000
        rows: list[dict] = []
        for index in range(bars):
            trend = 28_000 + index * (4 if timeframe == "1H" else 0.5 if timeframe == "5m" else 12)
            wave = math.sin(index / 8) * 180 + math.cos(index / 19) * 90
            base = trend + wave
            close = base + math.sin(index / 3) * 55
            rows.append(
                {
                    "timestamp": start_ts + index * step,
                    "open": round(base, 4),
                    "high": round(max(base, close) + 45, 4),
                    "low": round(min(base, close) - 45, 4),
                    "close": round(close, 4),
                    "volume": round(100 + (index % 12) * 5.5, 4),
                }
            )
        return rows

    @staticmethod
    def _escape(path: Path) -> str:
        return path.as_posix().replace("'", "''")

    @staticmethod
    def _parse_timestamp(value: object) -> int:
        if isinstance(value, (int, float)):
            raw = int(value)
            return raw // 1000 if raw > 10_000_000_000 else raw
        text = str(value).strip()
        if text.isdigit():
            raw = int(text)
            return raw // 1000 if raw > 10_000_000_000 else raw
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp())
