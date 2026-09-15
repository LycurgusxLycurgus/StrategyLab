from __future__ import annotations

import csv
import hashlib
import io
import json
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
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

FULL_HISTORY_BAR_CAP = 1_000_000


class DataService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list_datasets(self) -> list[dict[str, Any]]:
        return self.repo.list_datasets()

    def delete_dataset(self, dataset_id: str) -> None:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = self._resolve_dataset_path(dataset)
        if path.exists():
            path.unlink()
        self.repo.delete_dataset(dataset_id)

    def load_bars(self, dataset_id: str) -> list[Bar]:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = self._resolve_dataset_path(dataset)
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

    def dataset_content_hash(self, dataset_id: str) -> dict[str, Any]:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = self._resolve_dataset_path(dataset)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Dataset file is missing.")
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        existing = self.repo.get_dataset_hash(dataset_id)
        if (
            existing
            and existing["sha256"] == digest
            and int(existing["bytes_count"]) == len(payload)
        ):
            return existing
        record = {
            "dataset_id": dataset_id,
            "sha256": digest,
            "bytes_count": len(payload),
            "computed_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset_hash(record)
        return record

    def pine_proof_window(
        self, dataset_id: str, max_bars: int = 5_000
    ) -> dict[str, Any]:
        if not 1 <= max_bars <= 5_000:
            raise HTTPException(
                status_code=400,
                detail="Pine Basic proof windows must contain 1..5000 bars.",
            )
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        bars = self.load_bars(dataset_id)
        if not bars:
            raise HTTPException(status_code=400, detail="Dataset has no bars.")
        window = bars[-max_bars:]
        interval_ms = INTERVAL_MS.get(dataset["timeframe"])
        if interval_ms is None and len(window) > 1:
            interval_ms = max(
                1,
                int((window[-1].ts - window[-2].ts).total_seconds() * 1_000),
            )
        interval_ms = interval_ms or 1
        start_ms = int(window[0].ts.timestamp() * 1_000)
        end_ms = int(window[-1].ts.timestamp() * 1_000) + interval_ms
        content_hash = self.dataset_content_hash(dataset_id)
        return {
            "profile": "basic_v1",
            "dataset_id": dataset_id,
            "dataset_sha256": content_hash["sha256"],
            "symbol": dataset["symbol"],
            "timeframe": dataset["timeframe"],
            "rows": len(window),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_iso": window[0].ts.isoformat(),
            "end_exclusive_iso": datetime.fromtimestamp(
                end_ms / 1_000, tz=UTC
            ).isoformat(),
            "selection": "latest_bars",
        }

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
        collected, download_meta = self._download_klines(
            symbol, timeframe, bars, full_history
        )
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
            "download_mode": "full_history" if full_history else "fixed_window",
            "history_truncated": download_meta["history_truncated"],
            "history_cap_bars": download_meta["history_cap_bars"],
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

    def import_mt5_csv_dataset(
        self,
        source_path: str,
        symbol: str,
        timeframe: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        if timeframe not in INTERVAL_MS:
            raise HTTPException(status_code=400, detail="Unsupported timeframe.")
        source = Path(source_path).expanduser()
        if not source.exists() or not source.is_file():
            raise HTTPException(status_code=404, detail="Source CSV file was not found.")
        bars = self._read_mt5_csv(source, symbol.upper(), timeframe)
        if len(bars) < 500:
            raise HTTPException(status_code=400, detail="Imported dataset is too small for research use.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        target = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(target, bars)
        payload = {
            "dataset_id": dataset_id,
            "name": name or f"mt5-{symbol.lower()}-{timeframe}-{source.stem.lower()}",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "source": "mt5_csv",
            "rows_count": len(bars),
            "path": str(target),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset(payload)
        return payload

    def import_mt5_csv_content(
        self,
        filename: str,
        content: str,
        symbol: str,
        timeframe: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        if timeframe not in INTERVAL_MS:
            raise HTTPException(status_code=400, detail="Unsupported timeframe.")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Selected CSV file is empty.")
        bars = self._read_mt5_csv_text(content, symbol.upper(), timeframe)
        if len(bars) < 500:
            raise HTTPException(status_code=400, detail="Imported dataset is too small for research use.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        target = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(target, bars)
        source_name = Path(filename).stem if filename else "selected-file"
        payload = {
            "dataset_id": dataset_id,
            "name": name or f"mt5-{symbol.lower()}-{timeframe}-{source_name.lower()}",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "source": "mt5_csv_upload",
            "rows_count": len(bars),
            "path": str(target),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset(payload)
        return payload

    def _read_mt5_csv(self, path: Path, symbol: str, timeframe: str) -> list[Bar]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            bars = self._read_mt5_csv_stream(handle, symbol, timeframe)
        return self._dedupe_bars(bars)

    def _read_mt5_csv_text(self, content: str, symbol: str, timeframe: str) -> list[Bar]:
        handle = io.StringIO(content.lstrip("\ufeff"))
        bars = self._read_mt5_csv_stream(handle, symbol, timeframe)
        return self._dedupe_bars(bars)

    def _read_mt5_csv_stream(self, handle: Any, symbol: str, timeframe: str) -> list[Bar]:
        sample = handle.readline()
        handle.seek(0)
        dialect = csv.excel_tab if "\t" in sample else csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV file has no header.")
        bars: list[Bar] = []
        for row_number, row in enumerate(reader, start=2):
            normalized = {str(key).strip().strip("<>").lower(): value for key, value in row.items()}
            try:
                ts = self._parse_mt5_timestamp(normalized)
                bars.append(
                    Bar(
                        ts=ts,
                        open=float(normalized["open"]),
                        high=float(normalized["high"]),
                        low=float(normalized["low"]),
                        close=float(normalized["close"]),
                        volume=float(normalized.get("tickvol") or normalized.get("vol") or 0.0),
                        symbol=symbol,
                        timeframe=timeframe,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"Invalid MT5 CSV row {row_number}.") from exc
        return bars

    def _dedupe_bars(self, bars: list[Bar]) -> list[Bar]:
        bars.sort(key=lambda item: item.ts)
        deduped: list[Bar] = []
        previous_ts: datetime | None = None
        for bar in bars:
            if previous_ts == bar.ts:
                deduped[-1] = bar
                continue
            deduped.append(bar)
            previous_ts = bar.ts
        return deduped

    def _resolve_dataset_path(self, dataset: dict[str, Any]) -> Path:
        path = Path(dataset["path"])
        if path.exists():
            return path
        relocated = settings.data_dir / path.name
        if relocated.exists():
            repaired = dict(dataset)
            repaired["path"] = str(relocated)
            self.repo.put_dataset(repaired)
            return relocated
        return path

    @staticmethod
    def _parse_mt5_timestamp(row: dict[str, str]) -> datetime:
        if "date" in row and "time" in row:
            value = f"{row['date']} {row['time']}"
            return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=UTC)
        if "time" in row:
            raw = row["time"]
            for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
                except ValueError:
                    continue
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        raise KeyError("time")

    def _download_klines(self, symbol: str, timeframe: str, bars: int, full_history: bool) -> tuple[list[Bar], dict[str, Any]]:
        limit = 1000
        interval_ms = INTERVAL_MS[timeframe]
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        closed_end_ms = (now_ms // interval_ms) * interval_ms
        collected: list[list[Any]] = []
        start_time = (
            0
            if full_history
            else max(0, closed_end_ms - (bars * interval_ms))
        )
        history_truncated = False
        while True:
            query = {
                "symbol": symbol.upper(),
                "interval": timeframe,
                "limit": limit,
                "endTime": closed_end_ms - 1,
            }
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
            next_start_time = int(payload[-1][0]) + interval_ms
            if next_start_time <= start_time:
                break
            start_time = next_start_time
            if full_history and len(collected) >= FULL_HISTORY_BAR_CAP:
                collected = collected[:FULL_HISTORY_BAR_CAP]
                history_truncated = True
                break
        bars_out: list[Bar] = []
        for row in collected:
            if int(row[0]) + interval_ms > closed_end_ms:
                continue
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
        return bars_out, {
            "history_truncated": history_truncated,
            "history_cap_bars": FULL_HISTORY_BAR_CAP if full_history else None,
        }

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
            except (URLError, TimeoutError) as exc:
                if attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                detail = (
                    "Binance full-history download timed out while paging the archive. Retry, or start with a fixed bar window before requesting full history."
                    if full_history
                    else "Binance download timed out. Retry in a minute, or reduce the request scope."
                )
                raise HTTPException(status_code=502, detail=detail) from exc
