from __future__ import annotations

import csv
import json
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException

from app.config import settings
from app.storage import Repository


@dataclass(slots=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str

    def to_csv_row(self) -> list[str]:
        return [
            self.ts.isoformat(),
            f"{self.open:.8f}",
            f"{self.high:.8f}",
            f"{self.low:.8f}",
            f"{self.close:.8f}",
            f"{self.volume:.8f}",
            self.symbol,
            self.timeframe,
        ]


INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


class DataService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list_datasets(self) -> list[dict[str, Any]]:
        return self.repo.list_datasets()

    def delete_dataset(self, dataset_id: str) -> None:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = Path(dataset["path"])
        if path.exists():
            path.unlink()
        self.repo.delete_dataset(dataset_id)

    def load_bars(self, dataset_id: str) -> list[Bar]:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = Path(dataset["path"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="Dataset file is missing.")
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            bars: list[Bar] = []
            for row in reader:
                bars.append(
                    Bar(
                        ts=datetime.fromisoformat(row["ts"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        symbol=row["symbol"],
                        timeframe=row["timeframe"],
                    )
                )
        return bars

    def download_binance_dataset(
        self,
        symbol: str,
        timeframe: str,
        bars: int,
        full_history: bool = False,
        name: str | None = None,
    ) -> dict[str, Any]:
        if timeframe not in INTERVAL_MS:
            raise HTTPException(status_code=400, detail="Unsupported timeframe.")
        if not full_history and bars < 40_000:
            raise HTTPException(
                status_code=400,
                detail="Mutation Lab requires at least 40000 bars unless full history is selected.",
            )
        target_bars = bars if not full_history else bars
        collected = self._download_klines(symbol, timeframe, target_bars, full_history)
        if len(collected) < min(500, bars):
            raise HTTPException(status_code=502, detail="Downloaded dataset is too small for research use.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        dataset_name = name or (
            f"binance-{symbol.lower()}-{timeframe}-full" if full_history else f"binance-{symbol.lower()}-{timeframe}-{len(collected)}"
        )
        path = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(path, collected)
        payload = {
            "dataset_id": dataset_id,
            "name": dataset_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "binance_public",
            "rows_count": len(collected),
            "path": str(path),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset(payload)
        return payload

    def write_bars(self, path: Path, bars: list[Bar]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["ts", "open", "high", "low", "close", "volume", "symbol", "timeframe"])
            for bar in bars:
                writer.writerow(bar.to_csv_row())

    def import_fixture_dataset(self, bars: list[Bar], symbol: str, timeframe: str, name: str) -> dict[str, Any]:
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        path = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(path, bars)
        payload = {
            "dataset_id": dataset_id,
            "name": name,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "fixture",
            "rows_count": len(bars),
            "path": str(path),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset(payload)
        return payload

    def _download_klines(self, symbol: str, timeframe: str, bars: int, full_history: bool) -> list[Bar]:
        limit = 1000
        interval_ms = INTERVAL_MS[timeframe]
        collected: list[list[Any]] = []
        start_time = 0 if full_history else max(0, int(datetime.now(UTC).timestamp() * 1000) - (bars * interval_ms))
        while True:
            query = {"symbol": symbol.upper(), "interval": timeframe, "limit": limit}
            query["startTime"] = start_time
            url = f"https://api.binance.com/api/v3/klines?{urlencode(query)}"
            payload = self._fetch_klines_page(url, full_history=full_history)
            if not isinstance(payload, list) or not payload:
                break
            collected.extend(payload)
            if not full_history and len(collected) >= bars:
                collected = collected[-bars:]
                break
            if len(payload) < limit:
                break
            start_time = int(payload[-1][0]) + interval_ms
            if len(collected) >= 300_000:
                break
        bars_out: list[Bar] = []
        for row in collected:
            bars_out.append(
                Bar(
                    ts=datetime.fromtimestamp(int(row[0]) / 1000, UTC),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                )
            )
        return bars_out

    def _fetch_klines_page(self, url: str, full_history: bool) -> Any:
        backoffs = [1.0, 2.0, 4.0]
        for attempt in range(len(backoffs) + 1):
            try:
                with urlopen(url, timeout=45) as response:
                    return json.load(response)
            except HTTPError as exc:
                if exc.code in {418, 429}:
                    raise HTTPException(
                        status_code=502,
                        detail="Binance rate-limited the download. Retry in a minute, or request a smaller window first.",
                    ) from exc
                if exc.code >= 500 and attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                raise HTTPException(
                    status_code=502,
                    detail=f"Binance download failed with HTTP {exc.code}. Retry, or reduce the request scope.",
                ) from exc
            except (URLError, TimeoutError, socket.timeout) as exc:
                if attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                detail = (
                    "Binance full-history download timed out while paging the archive. Retry, or start with a fixed bar window before requesting full history."
                    if full_history
                    else "Binance download timed out. Retry in a minute, or reduce the request scope."
                )
                raise HTTPException(status_code=502, detail=detail) from exc
