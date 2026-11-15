from __future__ import annotations

import csv
import hashlib
import io
import json
import math
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


def audit_bars(
    bars: list[Bar],
    identical_duplicate_policy: str = "report_and_keep_first",
) -> dict[str, Any]:
    """Inspect raw bars before sorting or duplicate normalization.

    Conflicting duplicate timestamps and malformed market values block use.
    Identical duplicate rows are reported and remain usable only under the
    explicit ``report_and_keep_first`` policy. Gaps are reported for review,
    since sessions and venue closures can make them legitimate.
    """
    if identical_duplicate_policy not in {"report_and_keep_first", "reject"}:
        raise ValueError("Unsupported identical-duplicate policy.")

    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    duplicate_counts = {"identical_rows": 0, "conflicting_timestamps": 0}
    timestamps: dict[datetime, list[tuple[int, Bar]]] = {}
    previous_ts: datetime | None = None
    timeframes = sorted({bar.timeframe for bar in bars if isinstance(bar.timeframe, str)})
    timeframe = timeframes[0] if len(timeframes) == 1 else None

    if len(timeframes) > 1:
        findings.append(
            {
                "code": "DATA_MIXED_TIMEFRAMES",
                "severity": "error",
                "message": "A dataset must use one declared timeframe.",
                "timeframes": timeframes,
            }
        )

    for index, bar in enumerate(bars):
        ts = bar.ts
        if not isinstance(ts, datetime):
            findings.append(
                {
                    "code": "DATA_TIMESTAMP_INVALID",
                    "severity": "error",
                    "bar_index": index,
                    "message": "Every bar timestamp must be a datetime.",
                }
            )
        else:
            if ts.tzinfo is None or ts.utcoffset() is None:
                findings.append(
                    {
                        "code": "DATA_TIMEZONE_MISSING",
                        "severity": "error",
                        "bar_index": index,
                        "timestamp": ts.isoformat(),
                        "message": "Every bar timestamp must include a timezone.",
                    }
                )
            timestamps.setdefault(ts, []).append((index, bar))
            if previous_ts is not None:
                try:
                    if ts < previous_ts:
                        findings.append(
                            {
                                "code": "DATA_TIME_ORDER_DESCENDING",
                                "severity": "error",
                                "bar_index": index,
                                "previous_timestamp": previous_ts.isoformat(),
                                "timestamp": ts.isoformat(),
                                "message": "Raw bar timestamps must be nondecreasing.",
                            }
                        )
                except TypeError:
                    findings.append(
                        {
                            "code": "DATA_TIME_ORDER_INCOMPARABLE",
                            "severity": "error",
                            "bar_index": index,
                            "message": "Raw bar timestamps must have comparable timezones.",
                        }
                    )
            previous_ts = ts

        values = {
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        finite = True
        for field, value in values.items():
            try:
                valid = math.isfinite(float(value))
            except (TypeError, ValueError, OverflowError):
                valid = False
            if not valid:
                finite = False
                findings.append(
                    {
                        "code": "DATA_VALUE_NON_FINITE",
                        "severity": "error",
                        "bar_index": index,
                        "field": field,
                        "message": f"{field} must be a finite number.",
                    }
                )
        if finite:
            if bar.high < max(bar.open, bar.close) or bar.low > min(
                bar.open, bar.close
            ) or bar.low > bar.high:
                findings.append(
                    {
                        "code": "DATA_OHLC_INVALID",
                        "severity": "error",
                        "bar_index": index,
                        "message": "OHLC values must satisfy low <= open/close <= high.",
                    }
                )
            if bar.volume < 0:
                findings.append(
                    {
                        "code": "DATA_VOLUME_NEGATIVE",
                        "severity": "error",
                        "bar_index": index,
                        "message": "Volume cannot be negative.",
                    }
                )

    for ts, rows in timestamps.items():
        if len(rows) < 2:
            continue
        first = rows[0][1]
        identical = all(
            (
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.symbol,
                bar.timeframe,
            )
            == (
                first.open,
                first.high,
                first.low,
                first.close,
                first.volume,
                first.symbol,
                first.timeframe,
            )
            for _, bar in rows[1:]
        )
        if identical:
            duplicate_counts["identical_rows"] += len(rows) - 1
            severity = "warning" if identical_duplicate_policy == "report_and_keep_first" else "error"
            findings.append(
                {
                    "code": "DATA_DUPLICATE_IDENTICAL",
                    "severity": severity,
                    "timestamp": ts.isoformat(),
                    "bar_indices": [row_index for row_index, _ in rows],
                    "policy": identical_duplicate_policy,
                    "message": "Identical duplicate bars are explicitly reported.",
                }
            )
        else:
            duplicate_counts["conflicting_timestamps"] += 1
            findings.append(
                {
                    "code": "DATA_DUPLICATE_CONFLICT",
                    "severity": "error",
                    "timestamp": ts.isoformat(),
                    "bar_indices": [row_index for row_index, _ in rows],
                    "message": "Conflicting bars share a timestamp; normalization is unsafe.",
                }
            )

    interval_ms = INTERVAL_MS.get(timeframe or "")
    if interval_ms:
        ordered = sorted(
            {ts for ts in timestamps if ts.tzinfo is not None and ts.utcoffset() is not None}
        )
        for earlier, later in zip(ordered, ordered[1:]):
            delta_ms = int((later - earlier).total_seconds() * 1_000)
            if delta_ms > interval_ms:
                gaps.append(
                    {
                        "from": earlier.isoformat(),
                        "to": later.isoformat(),
                        "duration_ms": delta_ms,
                        "expected_interval_ms": interval_ms,
                        "missing_intervals_estimate": max(0, delta_ms // interval_ms - 1),
                    }
                )
                findings.append(
                    {
                        "code": "DATA_TIME_GAP",
                        "severity": "warning",
                        **gaps[-1],
                        "message": "A timeframe gap is present and must be interpreted in venue context.",
                    }
                )

    blocked = any(item["severity"] == "error" for item in findings)
    limited = any(item["severity"] == "warning" for item in findings)
    return {
        "schema_version": "1.0",
        "status": "BLOCKED" if blocked else "PASS_WITH_LIMITATIONS" if limited else "PASSED",
        "row_count": len(bars),
        "timeframe": timeframe,
        "timeframes": timeframes,
        "duplicate_counts": duplicate_counts,
        "identical_duplicate_policy": identical_duplicate_policy,
        "gaps": gaps,
        "findings": findings,
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

    def dataset_quality_manifest(self, dataset_id: str) -> dict[str, Any]:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        path = settings.data_dir / f"{dataset_id}.quality.json"
        if not path.is_file():
            return {
                "status": "UNVERIFIED",
                "reason": "Original raw audit unavailable",
                "dataset_id": dataset_id,
            }
        raw = path.read_bytes()
        manifest_hash = hashlib.sha256(raw).hexdigest()
        try:
            manifest = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            manifest = None
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema_version") != "dataset_quality_v1"
            or manifest.get("dataset_id") != dataset_id
            or not isinstance(manifest.get("raw_kind"), str)
            or not isinstance(manifest.get("data_audit"), dict)
            or not all(
                isinstance(manifest.get(key), str)
                and len(manifest[key]) == 64
                and all(character in "0123456789abcdef" for character in manifest[key])
                for key in ("raw_sha256", "normalized_sha256")
            )
        ):
            return {
                "status": "STALE",
                "reason": "Quality manifest is malformed or has an invalid identity",
                "dataset_id": dataset_id,
                "manifest_sha256": manifest_hash,
                "artifact_path": str(path),
            }
        try:
            dataset_path = self._resolve_dataset_path(dataset)
            actual_normalized_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        except OSError:
            return {
                **manifest,
                "status": "STALE",
                "reason": "Normalized dataset content is unavailable",
                "manifest_sha256": manifest_hash,
                "artifact_path": str(path),
            }
        expected_normalized_hash = manifest["normalized_sha256"]
        status = "VERIFIED" if actual_normalized_hash == expected_normalized_hash else "STALE"
        return {
            **manifest,
            "status": status,
            "reason": None if status == "VERIFIED" else "Normalized dataset content changed after its quality audit",
            "manifest_sha256": manifest_hash,
            "artifact_path": str(path),
            "actual_normalized_sha256": actual_normalized_hash,
        }

    @staticmethod
    def _observation_identity_bytes(bars: list[Bar]) -> bytes:
        rows = []
        for bar in bars:
            timestamp = bar.ts.isoformat() if isinstance(bar.ts, datetime) else repr(bar.ts)
            rows.append(
                [
                    timestamp,
                    repr(bar.open),
                    repr(bar.high),
                    repr(bar.low),
                    repr(bar.close),
                    repr(bar.volume),
                    bar.symbol,
                    bar.timeframe,
                ]
            )
        return json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _persist_quality_manifest(
        self,
        dataset_id: str,
        bars: list[Bar],
        data_audit: dict[str, Any],
        *,
        raw_kind: str,
        raw_bytes: bytes,
    ) -> dict[str, Any]:
        normalized_path = settings.data_dir / f"{dataset_id}.csv"
        normalized_bytes = normalized_path.read_bytes()
        manifest = {
            "schema_version": "dataset_quality_v1",
            "dataset_id": dataset_id,
            "raw_kind": raw_kind,
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "normalized_sha256": hashlib.sha256(normalized_bytes).hexdigest(),
            "normalized_row_count": len(bars),
            "data_audit": data_audit,
        }
        encoded = json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        manifest_path = settings.data_dir / f"{dataset_id}.quality.json"
        if manifest_path.exists() and manifest_path.read_bytes() != encoded:
            raise HTTPException(
                status_code=409,
                detail={"code": "DATA_QUALITY_MANIFEST_COLLISION", "dataset_id": dataset_id},
            )
        if not manifest_path.exists():
            manifest_path.write_bytes(encoded)
        return {
            **manifest,
            "status": "VERIFIED",
            "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
            "artifact_path": str(manifest_path),
        }

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
        data_audit = audit_bars(collected)
        quality_manifest = self._persist_quality_manifest(
            dataset_id,
            collected,
            data_audit,
            raw_kind="venue_observations_repr_v1",
            raw_bytes=self._observation_identity_bytes(collected),
        )
        payload = {
            "dataset_id": dataset_id,
            "name": dataset_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "binance_public",
            "rows_count": len(collected),
            "data_audit": data_audit,
            "quality_manifest": quality_manifest,
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
        data_audit = audit_bars(bars)
        quality_manifest = self._persist_quality_manifest(
            dataset_id,
            bars,
            data_audit,
            raw_kind="fixture_observations_repr_v1",
            raw_bytes=self._observation_identity_bytes(bars),
        )
        payload = {
            "dataset_id": dataset_id,
            "name": name,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "fixture",
            "rows_count": len(bars),
            "data_audit": data_audit,
            "quality_manifest": quality_manifest,
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
        raw_bytes = source.read_bytes()
        bars, data_audit = self._read_mt5_csv_text_with_audit(
            raw_bytes.decode("utf-8-sig"), symbol.upper(), timeframe
        )
        if len(bars) < 500:
            raise HTTPException(status_code=400, detail="Imported dataset is too small for research use.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        target = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(target, bars)
        quality_manifest = self._persist_quality_manifest(
            dataset_id,
            bars,
            data_audit,
            raw_kind="csv_bytes",
            raw_bytes=raw_bytes,
        )
        payload = {
            "dataset_id": dataset_id,
            "name": name or f"mt5-{symbol.lower()}-{timeframe}-{source.stem.lower()}",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "source": "mt5_csv",
            "rows_count": len(bars),
            "data_audit": data_audit,
            "quality_manifest": quality_manifest,
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
        bars, data_audit = self._read_mt5_csv_text_with_audit(
            content, symbol.upper(), timeframe
        )
        if len(bars) < 500:
            raise HTTPException(status_code=400, detail="Imported dataset is too small for research use.")
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        target = settings.data_dir / f"{dataset_id}.csv"
        self.write_bars(target, bars)
        raw_bytes = content.encode("utf-8")
        quality_manifest = self._persist_quality_manifest(
            dataset_id,
            bars,
            data_audit,
            raw_kind="csv_text_utf8",
            raw_bytes=raw_bytes,
        )
        source_name = Path(filename).stem if filename else "selected-file"
        payload = {
            "dataset_id": dataset_id,
            "name": name or f"mt5-{symbol.lower()}-{timeframe}-{source_name.lower()}",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "source": "mt5_csv_upload",
            "rows_count": len(bars),
            "data_audit": data_audit,
            "quality_manifest": quality_manifest,
            "path": str(target),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_dataset(payload)
        return payload

    def _read_mt5_csv(self, path: Path, symbol: str, timeframe: str) -> list[Bar]:
        bars, _ = self._read_mt5_csv_with_audit(path, symbol, timeframe)
        return bars

    def _read_mt5_csv_with_audit(
        self, path: Path, symbol: str, timeframe: str
    ) -> tuple[list[Bar], dict[str, Any]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_bars = self._read_mt5_csv_stream(handle, symbol, timeframe)
        return self._audit_and_dedupe_bars(raw_bars)

    def _read_mt5_csv_text(self, content: str, symbol: str, timeframe: str) -> list[Bar]:
        bars, _ = self._read_mt5_csv_text_with_audit(content, symbol, timeframe)
        return bars

    def _read_mt5_csv_text_with_audit(
        self, content: str, symbol: str, timeframe: str
    ) -> tuple[list[Bar], dict[str, Any]]:
        handle = io.StringIO(content.lstrip("\ufeff"))
        raw_bars = self._read_mt5_csv_stream(handle, symbol, timeframe)
        return self._audit_and_dedupe_bars(raw_bars)

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

    def _audit_and_dedupe_bars(
        self, bars: list[Bar]
    ) -> tuple[list[Bar], dict[str, Any]]:
        audit = audit_bars(bars)
        if audit["status"] == "BLOCKED":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "DATA_AUDIT_BLOCKED",
                    "message": "The imported market data failed raw-data validation.",
                    "audit": audit,
                },
            )
        return self._dedupe_bars(bars), audit

    def _dedupe_bars(self, bars: list[Bar]) -> list[Bar]:
        audit = audit_bars(bars)
        if audit["status"] == "BLOCKED":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "DATA_AUDIT_BLOCKED",
                    "message": "Bars cannot be normalized before raw-data audit passes.",
                    "audit": audit,
                },
            )
        deduped: list[Bar] = []
        previous_ts: datetime | None = None
        for bar in bars:
            if previous_ts == bar.ts:
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
