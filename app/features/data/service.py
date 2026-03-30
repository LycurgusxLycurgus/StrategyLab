from __future__ import annotations

import csv
import json
import io
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from pathlib import Path
from fastapi import HTTPException

from app.config import settings
from app.domain import Bar
from app.storage import Repository


class DataService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def download_market_dataset(
        self,
        symbol: str,
        timeframe: str,
        lookback_days: int,
        provider: str = "auto",
        name: str | None = None,
    ) -> dict:
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        resolved_provider = self._resolve_provider(symbol, provider)
        bars = self._download_oanda(symbol, timeframe, lookback_days)
        dataset_name = name or f"{resolved_provider}-{symbol.lower().replace('=', '-').replace('/', '-')}-{timeframe}-{lookback_days}d"
        path = settings.data_dir / f"{dataset_id}.csv"

        self.write_bars(path, bars)
        record = {
            "dataset_id": dataset_id,
            "name": dataset_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "rows_count": len(bars),
            "path": str(path),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.upsert_dataset(record)
        return record

    def _resolve_provider(self, symbol: str, provider: str) -> str:
        if provider == "auto":
            provider = "oanda"
        if provider != "oanda":
            raise HTTPException(status_code=400, detail="Only OANDA download is supported. Use manual HistData import otherwise.")
        if symbol != "XAU_USD":
            raise HTTPException(status_code=400, detail="OANDA download currently supports XAU_USD only.")
        if not settings.oanda_api_token:
            raise HTTPException(
                status_code=400,
                detail="APP_OANDA_API_TOKEN is missing. Add your OANDA practice token or use manual HistData import.",
            )
        return "oanda"

    def _download_oanda(self, symbol: str, timeframe: str, lookback_days: int) -> list[Bar]:
        if timeframe != "15m":
            raise HTTPException(status_code=400, detail="OANDA adapter currently supports 15m only.")
        end = datetime.now(UTC)
        start = end - timedelta(days=lookback_days)
        bars: list[Bar] = []
        cursor = start
        step = timedelta(days=10)
        while cursor < end:
            window_end = min(cursor + step, end)
            params = urllib.parse.urlencode(
                {
                    "price": "M",
                    "granularity": "M15",
                    "from": cursor.isoformat().replace("+00:00", "Z"),
                    "to": window_end.isoformat().replace("+00:00", "Z"),
                }
            )
            url = f"{settings.oanda_base_url}/v3/instruments/{symbol}/candles?{params}"
            request = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {settings.oanda_api_token}",
                    "Accept-Datetime-Format": "RFC3339",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                detail = f"OANDA error HTTP {exc.code}"
                try:
                    error_payload = json.loads(body)
                    message = error_payload.get("errorMessage") or error_payload.get("message")
                    if message:
                        detail = f"OANDA error: {message}"
                except json.JSONDecodeError:
                    if body:
                        detail = f"OANDA error: {body}"
                raise HTTPException(status_code=502, detail=detail) from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"OANDA download failed: {exc}") from exc

            candles = payload.get("candles", [])
            for candle in candles:
                if not candle.get("complete", False):
                    continue
                mid = candle.get("mid")
                if not mid:
                    continue
                bars.append(
                    Bar(
                        ts=datetime.fromisoformat(candle["time"].replace("Z", "+00:00")).astimezone(UTC),
                        open=float(mid["o"]),
                        high=float(mid["h"]),
                        low=float(mid["l"]),
                        close=float(mid["c"]),
                        volume=float(candle.get("volume", 0.0) or 0.0),
                        symbol=symbol,
                        timeframe=timeframe,
                    )
                )
            cursor = window_end

        deduped: dict[str, Bar] = {bar.ts.isoformat(): bar for bar in bars}
        ordered = [deduped[key] for key in sorted(deduped.keys())]
        if not ordered:
            raise HTTPException(status_code=400, detail="OANDA returned no completed candles for that range.")
        return ordered

    def list_datasets(self) -> list[dict]:
        return self.repo.list_datasets()

    def import_csv_dataset(
        self,
        content: bytes,
        filename: str,
        symbol: str,
        timeframe: str,
        name: str | None = None,
    ) -> dict:
        bars = self._parse_csv_bars(content, symbol, timeframe)
        if not bars:
            raise HTTPException(status_code=400, detail="CSV import produced no bars.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        safe_name = name or Path(filename).stem or f"manual-{symbol.lower()}-{timeframe}"
        dataset_name = f"manual-{safe_name}"
        path = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(path, bars)
        record = {
            "dataset_id": dataset_id,
            "name": dataset_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "rows_count": len(bars),
            "path": str(path),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.upsert_dataset(record)
        return record

    def delete_dataset(self, dataset_id: str) -> None:
        self.repo.delete_dataset(dataset_id)

    def load_bars(self, dataset_id: str) -> list[Bar]:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        return self.read_bars(Path(dataset["path"]))

    @staticmethod
    def write_bars(path: Path, bars: list[Bar]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["ts", "open", "high", "low", "close", "volume", "symbol", "timeframe"],
            )
            writer.writeheader()
            for bar in bars:
                row = asdict(bar)
                row["ts"] = bar.ts.isoformat()
                writer.writerow(row)

    @staticmethod
    def read_bars(path: Path) -> list[Bar]:
        bars: list[Bar] = []
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
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

    def _parse_csv_bars(self, content: bytes, symbol: str, timeframe: str) -> list[Bar]:
        text = content.decode("utf-8-sig")
        histdata_rows = self._parse_histdata_ascii_m1(text, symbol)
        if histdata_rows is not None:
            if timeframe == "15m":
                return self._aggregate_bars(histdata_rows, timeframe)
            return histdata_rows
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV import needs a header row.")

        headers = {field.lower().strip(): field for field in reader.fieldnames}

        def pick(*names: str) -> str:
            for name in names:
                key = headers.get(name)
                if key:
                    return key
            raise HTTPException(
                status_code=400,
                detail=(
                    "CSV is missing required columns. Required: timestamp/date/time and open/high/low/close. "
                    "Optional: volume."
                ),
            )

        ts_key = pick("timestamp", "datetime", "date", "time")
        open_key = pick("open", "o")
        high_key = pick("high", "h")
        low_key = pick("low", "l")
        close_key = pick("close", "c")
        volume_key = headers.get("volume") or headers.get("vol") or headers.get("v")

        bars: list[Bar] = []
        for row in reader:
            ts = self._parse_timestamp(row[ts_key])
            bars.append(
                Bar(
                    ts=ts,
                    open=float(row[open_key]),
                    high=float(row[high_key]),
                    low=float(row[low_key]),
                    close=float(row[close_key]),
                    volume=float(row[volume_key]) if volume_key and row.get(volume_key) else 0.0,
                    symbol=symbol,
                    timeframe=timeframe,
                )
            )
        bars.sort(key=lambda bar: bar.ts)
        deduped: dict[str, Bar] = {bar.ts.isoformat(): bar for bar in bars}
        ordered = [deduped[key] for key in sorted(deduped.keys())]
        if timeframe == "15m" and ordered and self._is_minute_series(ordered):
            return self._aggregate_bars(ordered, timeframe)
        return ordered

    def _parse_histdata_ascii_m1(self, text: str, symbol: str) -> list[Bar] | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        first = lines[0]
        parts = first.split(";")
        if len(parts) != 6 or " " not in parts[0]:
            return None
        date_part, time_part = parts[0].split(" ", 1)
        if len(date_part) != 8 or len(time_part) != 6 or not (date_part + time_part).isdigit():
            return None
        bars: list[Bar] = []
        for line in lines:
            fields = line.split(";")
            if len(fields) != 6:
                continue
            raw_dt, raw_open, raw_high, raw_low, raw_close, raw_volume = fields
            dt = datetime.strptime(raw_dt, "%Y%m%d %H%M%S").replace(tzinfo=UTC)
            bars.append(
                Bar(
                    ts=dt,
                    open=float(raw_open),
                    high=float(raw_high),
                    low=float(raw_low),
                    close=float(raw_close),
                    volume=float(raw_volume or 0.0),
                    symbol=symbol,
                    timeframe="1m",
                )
            )
        return bars

    @staticmethod
    def _is_minute_series(bars: list[Bar]) -> bool:
        if len(bars) < 2:
            return False
        delta = bars[1].ts - bars[0].ts
        return delta <= timedelta(minutes=1)

    @staticmethod
    def _aggregate_bars(bars: list[Bar], timeframe: str) -> list[Bar]:
        if timeframe != "15m":
            return bars
        buckets: dict[datetime, list[Bar]] = {}
        for bar in bars:
            bucket_ts = bar.ts.replace(minute=(bar.ts.minute // 15) * 15, second=0, microsecond=0)
            buckets.setdefault(bucket_ts, []).append(bar)
        aggregated: list[Bar] = []
        for bucket_ts in sorted(buckets.keys()):
            group = buckets[bucket_ts]
            aggregated.append(
                Bar(
                    ts=bucket_ts,
                    open=group[0].open,
                    high=max(item.high for item in group),
                    low=min(item.low for item in group),
                    close=group[-1].close,
                    volume=sum(item.volume for item in group),
                    symbol=group[0].symbol,
                    timeframe="15m",
                )
            )
        return aggregated

    @staticmethod
    def _parse_timestamp(raw: str) -> datetime:
        value = raw.strip()
        if value.isdigit():
            ts = datetime.fromtimestamp(int(value), tz=UTC)
            return ts
        value = value.replace("/", "-")
        if " " in value and "T" not in value:
            value = value.replace(" ", "T", 1)
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        ts = datetime.fromisoformat(value)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.astimezone(UTC)
