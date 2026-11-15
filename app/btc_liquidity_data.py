"""Checksummed Binance USD-M BTCUSDT 5-minute research data.

The downloader keeps Binance's original ZIP, CHECKSUM, exchange-info, and
funding-response bytes. Parsing is deliberately strict: damaged, incomplete,
duplicated, reordered, or non-contiguous candles are rejected rather than
repaired.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from app.btc_liquidity import Candle


SYMBOL = "BTCUSDT"
INTERVAL = "5m"
INTERVAL_MS = 300_000
START_MS = 1_640_995_200_000  # 2022-01-01T00:00:00Z
END_EXCLUSIVE_MS = 1_788_220_800_000  # 2026-09-01T00:00:00Z
FUNDING_END_MS = END_EXCLUSIVE_MS - 1
FUNDING_DEFAULT_INTERVAL_MS = 8 * 60 * 60_000
FUNDING_JITTER_TOLERANCE_MS = 60_000
MAX_DOWNLOAD_WORKERS = 4
MAX_ATTEMPTS = 4
HTTP_TIMEOUT_SECONDS = 45
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
ARCHIVE_BASE_URL = (
    "https://data.binance.vision/data/futures/um/monthly/klines/"
    f"{SYMBOL}/{INTERVAL}/"
)
MARK_PRICE_ARCHIVE_BASE_URL = (
    "https://data.binance.vision/data/futures/um/monthly/markPriceKlines/"
    f"{SYMBOL}/{INTERVAL}/"
)
MARK_PRICE_DAILY_ARCHIVE_BASE_URL = (
    "https://data.binance.vision/data/futures/um/daily/markPriceKlines/"
    f"{SYMBOL}/{INTERVAL}/"
)
MARK_PRICE_SUBDIR = "mark_price"
AUTHORIZED_DAILY_REPAIR_DATES = ("2022-07-31", "2022-10-02", "2023-02-24")
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
USER_AGENT = "StrategyLab-BTC-liquidity-research/1.0"


@dataclass(frozen=True, slots=True)
class _RawCandle:
    t: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class _Month:
    year: int
    month: int

    @property
    def stem(self) -> str:
        return f"{SYMBOL}-{INTERVAL}-{self.year:04d}-{self.month:02d}"

    @property
    def filename(self) -> str:
        return f"{self.stem}.zip"

    @property
    def source_url(self) -> str:
        return ARCHIVE_BASE_URL + self.filename

    @property
    def checksum_url(self) -> str:
        return self.source_url + ".CHECKSUM"

    @property
    def mark_price_source_url(self) -> str:
        return MARK_PRICE_ARCHIVE_BASE_URL + self.filename

    @property
    def mark_price_checksum_url(self) -> str:
        return self.mark_price_source_url + ".CHECKSUM"

    @property
    def first_ms(self) -> int:
        return _utc_ms(self.year, self.month, 1)

    @property
    def next_month_ms(self) -> int:
        if self.month == 12:
            return _utc_ms(self.year + 1, 1, 1)
        return _utc_ms(self.year, self.month + 1, 1)

    @property
    def expected_rows(self) -> int:
        days = calendar.monthrange(self.year, self.month)[1]
        return days * 24 * 60 * 60_000 // INTERVAL_MS


@dataclass(frozen=True, slots=True)
class _DailyMarkArchive:
    year: int
    month: int
    day: int

    @property
    def date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    @property
    def stem(self) -> str:
        return f"{SYMBOL}-{INTERVAL}-{self.date}"

    @property
    def filename(self) -> str:
        return f"{self.stem}.zip"

    @property
    def source_url(self) -> str:
        return MARK_PRICE_DAILY_ARCHIVE_BASE_URL + self.filename

    @property
    def checksum_url(self) -> str:
        return self.source_url + ".CHECKSUM"

    @property
    def first_ms(self) -> int:
        return _utc_ms(self.year, self.month, self.day)

    @property
    def end_exclusive_ms(self) -> int:
        return self.first_ms + 24 * 60 * 60_000

    @property
    def expected_rows(self) -> int:
        return 24 * 60 // 5


def _daily_mark_archive(date_value: str) -> _DailyMarkArchive:
    if date_value not in AUTHORIZED_DAILY_REPAIR_DATES:
        raise ValueError(f"Daily mark-price repair date {date_value!r} was not authorized.")
    try:
        year, month, day = (int(value) for value in date_value.split("-"))
        archive = _DailyMarkArchive(year, month, day)
        if datetime(year, month, day, tzinfo=UTC).strftime("%Y-%m-%d") != date_value:
            raise ValueError
        return archive
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid authorized daily repair date {date_value!r}.") from exc


def _utc_ms(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=UTC).timestamp() * 1000)


def _months() -> list[_Month]:
    result: list[_Month] = []
    year, month = 2022, 1
    while (year, month) <= (2026, 8):
        result.append(_Month(year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _iso_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, UTC).isoformat().replace("+00:00", "Z")


def _read_limited(response: Any, limit: int, url: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        block = response.read(min(1024 * 1024, limit + 1 - total))
        if not block:
            break
        chunks.append(block)
        total += len(block)
        if total > limit:
            raise ValueError(f"Response from {url} exceeded the {limit}-byte safety limit.")
    return b"".join(chunks)


def _fetch_bytes(url: str, *, limit: int) -> tuple[bytes, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    last_error: BaseException | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            request = Request(url, headers=headers, method="GET")
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                payload = _read_limited(response, limit, url)
                return payload, _now_utc()
        except HTTPError as exc:
            last_error = exc
            if exc.code in {400, 401, 403, 404}:
                raise ValueError(f"Public data request failed with HTTP {exc.code}: {url}") from exc
            if exc.code in {418, 429}:
                # Respect an explicit server retry delay, but keep it bounded.
                retry_after = exc.headers.get("Retry-After", "")
                try:
                    delay = min(30.0, max(0.5, float(retry_after)))
                except ValueError:
                    delay = min(8.0, 0.5 * (2**attempt))
            else:
                delay = min(8.0, 0.5 * (2**attempt))
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            delay = min(8.0, 0.5 * (2**attempt))
        if attempt + 1 < MAX_ATTEMPTS:
            time.sleep(delay)
    raise ValueError(f"Public data request failed after {MAX_ATTEMPTS} attempts: {url}: {last_error}") from last_error


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _load_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        return {
            "schema_version": "btc_liquidity_raw_v1",
            "symbol": SYMBOL,
            "venue": "Binance USD-M perpetual",
            "interval": INTERVAL,
            "requested_start_ms": START_MS,
            "requested_end_exclusive_ms": END_EXCLUSIVE_MS,
            "monthly_archives": {},
            "mark_price_archives": {},
            "mark_price_daily_archives": {},
            "funding_pages": [],
            "sources": {},
        }
    try:
        manifest = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot read raw-data manifest {path}: {exc}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "btc_liquidity_raw_v1"
        or manifest.get("symbol") != SYMBOL
        or manifest.get("interval") != INTERVAL
        or manifest.get("requested_start_ms") != START_MS
        or manifest.get("requested_end_exclusive_ms") != END_EXCLUSIVE_MS
    ):
        raise ValueError(f"Raw-data manifest has an unsupported identity or date range: {path}")
    manifest.setdefault("monthly_archives", {})
    manifest.setdefault("mark_price_archives", {})
    manifest.setdefault("mark_price_daily_archives", {})
    manifest.setdefault("funding_pages", [])
    manifest.setdefault("sources", {})
    return manifest


def _write_manifest(root: Path, manifest: dict[str, Any]) -> bytes:
    manifest["updated_utc"] = _now_utc()
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write(root / "manifest.json", payload)
    return payload


def _checksum_digest(payload: bytes, expected_filename: str) -> str:
    try:
        text = payload.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"Checksum for {expected_filename} is not ASCII.") from exc
    # Binance publishes the usual "<hex>  <filename>" format. Accept the
    # equivalent OpenSSL-style line as well, but require the named archive.
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+(.+)", text)
    if match:
        digest, filename = match.groups()
        if Path(filename.strip()).name != expected_filename:
            raise ValueError(
                f"Checksum names {filename.strip()!r}; expected {expected_filename!r}."
            )
        return digest.lower()
    match = re.fullmatch(
        r"SHA256\s*\(\s*(.+?)\s*\)\s*=\s*([0-9a-fA-F]{64})", text, re.IGNORECASE
    )
    if match:
        filename, digest = match.groups()
        if Path(filename.strip()).name != expected_filename:
            raise ValueError(
                f"Checksum names {filename.strip()!r}; expected {expected_filename!r}."
            )
        return digest.lower()
    raise ValueError(f"Checksum for {expected_filename} has an unsupported format.")


def _record(
    *, source_url: str, downloaded_utc: str | None, payload: bytes, cache_state: str
) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "download_utc": downloaded_utc,
        "sha256": _sha256_bytes(payload),
        "bytes": len(payload),
        "cache_state": cache_state,
    }


def _verified_archive_cache(
    root: Path, month: _Month, prior_records: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    zip_path = root / month.filename
    checksum_path = root / (month.filename + ".CHECKSUM")
    if not zip_path.is_file() or not checksum_path.is_file():
        return None
    try:
        checksum_bytes = checksum_path.read_bytes()
        expected_digest = _checksum_digest(checksum_bytes, month.filename)
        actual_digest = sha256_file(zip_path)
        if actual_digest != expected_digest:
            return None
        zip_bytes = zip_path.read_bytes()
        if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
            return None
    except (OSError, ValueError):
        return None
    if prior_records is None:
        prior_records = _load_manifest(root).get("monthly_archives", {})
    prior = prior_records.get(month.stem, {})
    prior_zip = prior.get("archive", {}) if isinstance(prior, dict) else {}
    prior_sum = prior.get("checksum", {}) if isinstance(prior, dict) else {}
    zip_time = prior_zip.get("download_utc") if prior_zip.get("sha256") == actual_digest else None
    checksum_digest = _sha256_bytes(checksum_bytes)
    sum_time = prior_sum.get("download_utc") if prior_sum.get("sha256") == checksum_digest else None
    return (
        _record(
            source_url=month.source_url,
            downloaded_utc=zip_time,
            payload=zip_bytes,
            cache_state="verified_cache" if zip_time else "verified_cache_timestamp_unknown",
        ),
        _record(
            source_url=month.checksum_url,
            downloaded_utc=sum_time,
            payload=checksum_bytes,
            cache_state="verified_cache" if sum_time else "verified_cache_timestamp_unknown",
        ),
    )


def _download_month(
    root: Path, month: _Month, prior_records: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    cached = _verified_archive_cache(root, month, prior_records)
    if cached is not None:
        return month.stem, {
            "archive": cached[0],
            "checksum": cached[1],
            "expected_rows": month.expected_rows,
            "first_open_ms": month.first_ms,
            "end_exclusive_ms": month.next_month_ms,
        }

    zip_bytes, zip_time = _fetch_bytes(month.source_url, limit=MAX_ARCHIVE_BYTES)
    checksum_bytes, checksum_time = _fetch_bytes(month.checksum_url, limit=64 * 1024)
    expected = _checksum_digest(checksum_bytes, month.filename)
    actual = _sha256_bytes(zip_bytes)
    if actual != expected:
        raise ValueError(
            f"SHA-256 mismatch for {month.filename}: checksum={expected}, downloaded={actual}."
        )
    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        raise ValueError(f"Downloaded archive is not a valid ZIP file: {month.filename}")
    _atomic_write(root / month.filename, zip_bytes)
    _atomic_write(root / (month.filename + ".CHECKSUM"), checksum_bytes)
    return month.stem, {
        "archive": _record(
            source_url=month.source_url,
            downloaded_utc=zip_time,
            payload=zip_bytes,
            cache_state="downloaded_and_checksum_verified",
        ),
        "checksum": _record(
            source_url=month.checksum_url,
            downloaded_utc=checksum_time,
            payload=checksum_bytes,
            cache_state="downloaded",
        ),
        "expected_rows": month.expected_rows,
        "first_open_ms": month.first_ms,
        "end_exclusive_ms": month.next_month_ms,
    }


def _cache_source(
    root: Path,
    *,
    name: str,
    url: str,
    path: Path,
    limit: int,
    manifest: dict[str, Any],
) -> bytes:
    prior = manifest.get("sources", {}).get(name, {})
    if path.is_file() and isinstance(prior, dict):
        cached = path.read_bytes()
        if (
            prior.get("source_url") == url
            and prior.get("sha256") == _sha256_bytes(cached)
            and prior.get("bytes") == len(cached)
        ):
            return cached
    payload, downloaded_utc = _fetch_bytes(url, limit=limit)
    _atomic_write(path, payload)
    manifest.setdefault("sources", {})[name] = _record(
        source_url=url,
        downloaded_utc=downloaded_utc,
        payload=payload,
        cache_state="downloaded",
    )
    _write_manifest(root, manifest)
    return payload


def _read_json_payload(payload: bytes, description: str) -> Any:
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{description} returned invalid JSON: {exc}") from exc


def _funding_coverage(
    rows: list[dict[str, int | float]], provenance: list[dict[str, Any]]
) -> dict[str, Any]:
    """Describe and reject gaps beyond the observed 8-hour default cadence."""
    if len(rows) != len(provenance):
        raise ValueError("Funding coverage rows and mark provenance have different lengths.")
    source_counts = {
        "api_mark": 0,
        "mark_price_open_proxy": 0,
        "mark_price_daily_open_repair": 0,
    }
    for item in provenance:
        source = item.get("source")
        if source not in source_counts:
            raise ValueError(f"Funding mark provenance has an unsupported source {source!r}.")
        source_counts[source] += 1
    if not rows:
        return {
            "status": "BLOCKED",
            "rows": 0,
            "first_ts": None,
            "last_ts": None,
            "start_gap_ms": None,
            "end_gap_ms": None,
            "max_gap_ms": None,
            "gap_intervals_ms": {},
            "gaps_over_8h": [],
            "mark_source_counts": source_counts,
            "expected_default_interval_ms": FUNDING_DEFAULT_INTERVAL_MS,
            "jitter_tolerance_ms": FUNDING_JITTER_TOLERANCE_MS,
        }
    timestamps = [int(row["ts"]) for row in rows]
    gaps = [right - left for left, right in zip(timestamps, timestamps[1:])]
    gap_counts: dict[str, int] = {}
    for gap in gaps:
        key = str(gap)
        gap_counts[key] = gap_counts.get(key, 0) + 1
    excessive = [
        {"after_ts": timestamps[index], "before_ts": timestamps[index + 1], "gap_ms": gap}
        for index, gap in enumerate(gaps)
        if gap > FUNDING_DEFAULT_INTERVAL_MS + FUNDING_JITTER_TOLERANCE_MS
    ]
    start_gap = timestamps[0] - START_MS
    end_gap = END_EXCLUSIVE_MS - timestamps[-1]
    status = (
        "PASS"
        if start_gap <= FUNDING_DEFAULT_INTERVAL_MS + FUNDING_JITTER_TOLERANCE_MS
        and end_gap <= FUNDING_DEFAULT_INTERVAL_MS + FUNDING_JITTER_TOLERANCE_MS
        and not excessive
        else "BLOCKED"
    )
    return {
        "status": status,
        "rows": len(rows),
        "first_ts": timestamps[0],
        "first_utc": _iso_ms(timestamps[0]),
        "last_ts": timestamps[-1],
        "last_utc": _iso_ms(timestamps[-1]),
        "start_gap_ms": start_gap,
        "end_gap_ms": end_gap,
        "max_gap_ms": max(gaps, default=0),
        "gap_intervals_ms": dict(sorted(gap_counts.items(), key=lambda item: int(item[0]))),
        "gaps_over_8h": excessive,
        "mark_source_counts": source_counts,
        "expected_default_interval_ms": FUNDING_DEFAULT_INTERVAL_MS,
        "jitter_tolerance_ms": FUNDING_JITTER_TOLERANCE_MS,
    }


def _funding_cached_page(
    root: Path, start_ms: int, page_index: int, manifest: dict[str, Any]
) -> tuple[bytes, dict[str, Any]] | None:
    page_path = root / "funding_pages" / f"funding-{page_index:04d}-{start_ms}.json"
    if not page_path.is_file():
        return None
    record = next(
        (
            item
            for item in manifest.get("funding_pages", [])
            if isinstance(item, dict)
            and item.get("page_index") == page_index
            and item.get("request_start_ms") == start_ms
        ),
        None,
    )
    if not isinstance(record, dict):
        return None
    payload = page_path.read_bytes()
    if record.get("sha256") != _sha256_bytes(payload) or record.get("bytes") != len(payload):
        return None
    return payload, record


def _funding_page_url(start_ms: int) -> str:
    query = urlencode(
        {"symbol": SYMBOL, "startTime": start_ms, "endTime": FUNDING_END_MS, "limit": 1000}
    )
    return f"{FUNDING_URL}?{query}"


def _parse_funding_page(body: Any, page_index: int) -> list[dict[str, Any]]:
    if not isinstance(body, list) or len(body) > 1000:
        raise ValueError(f"Funding page {page_index} is not a list of at most 1000 rows.")
    rows: list[dict[str, Any]] = []
    previous_ts: int | None = None
    for row_index, item in enumerate(body):
        if not isinstance(item, dict):
            raise ValueError(f"Funding page {page_index} row {row_index} is not an object.")
        try:
            ts = int(item["fundingTime"])
            rate = float(item["fundingRate"])
            mark_value = item["markPrice"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Funding page {page_index} row {row_index} lacks a valid fundingTime, fundingRate, or markPrice."
            ) from exc
        if ts < START_MS or ts > FUNDING_END_MS:
            raise ValueError(f"Funding timestamp {ts} falls outside the requested UTC range.")
        if previous_ts is not None and ts <= previous_ts:
            raise ValueError(f"Funding page {page_index} timestamps are not strictly increasing.")
        if not math.isfinite(rate):
            raise ValueError(f"Funding rate at timestamp {ts} is not finite.")
        if mark_value in (None, ""):
            api_mark = None
        else:
            try:
                api_mark = float(mark_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Funding API mark at timestamp {ts} is invalid.") from exc
            if not math.isfinite(api_mark) or api_mark <= 0:
                raise ValueError(f"Funding API mark at timestamp {ts} is not finite and positive.")
        rows.append({"ts": ts, "rate": rate, "api_mark": api_mark})
        previous_ts = ts
    return rows


def _read_funding_api_pages(
    root: Path, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    page_records = manifest.get("funding_pages")
    if not isinstance(page_records, list) or not page_records:
        raise ValueError("Funding manifest has no exact API response pages.")
    raw_rows: list[dict[str, Any]] = []
    expected_start = START_MS
    stopped = False
    for expected_index, record in enumerate(page_records):
        if stopped:
            raise ValueError("Funding manifest contains pages after a short or empty response.")
        if not isinstance(record, dict) or record.get("page_index") != expected_index:
            raise ValueError("Funding manifest page indices are missing or out of order.")
        start_ms = record.get("request_start_ms")
        if start_ms != expected_start or record.get("request_end_ms") != FUNDING_END_MS:
            raise ValueError(f"Funding page {expected_index} has an incomplete pagination identity.")
        path = root / "funding_pages" / f"funding-{expected_index:04d}-{start_ms}.json"
        if not path.is_file():
            raise ValueError(f"Exact funding API response is missing: {path}")
        payload = path.read_bytes()
        if record.get("sha256") != _sha256_bytes(payload) or record.get("bytes") != len(payload):
            raise ValueError(f"Exact funding API response hash mismatch: {path}")
        if record.get("source_url") != _funding_page_url(start_ms):
            raise ValueError(f"Funding page {expected_index} has an unexpected source URL.")
        body = _read_json_payload(payload, f"Funding page {expected_index}")
        parsed = _parse_funding_page(body, expected_index)
        if raw_rows and parsed and parsed[0]["ts"] <= raw_rows[-1]["ts"]:
            raise ValueError("Funding page timestamps are duplicated or not globally increasing.")
        raw_rows.extend(parsed)
        if len(body) == 1000:
            if not parsed:
                raise ValueError(f"Funding page {expected_index} has no rows to advance pagination.")
            expected_start = parsed[-1]["ts"] + 1
            if expected_start > FUNDING_END_MS:
                stopped = True
        else:
            stopped = True
    if not raw_rows:
        raise ValueError("Funding endpoint returned no records for the requested range.")
    if not stopped:
        raise ValueError("Funding manifest ends before pagination covers the requested range.")
    return raw_rows


def _download_funding_pages(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows: list[dict[str, Any]] = []
    new_records: list[dict[str, Any]] = []
    start_ms = START_MS
    page_index = 0
    while start_ms <= FUNDING_END_MS:
        url = _funding_page_url(start_ms)
        cached = _funding_cached_page(root, start_ms, page_index, manifest)
        if cached is None:
            payload, downloaded_utc = _fetch_bytes(url, limit=MAX_JSON_BYTES)
            page_path = root / "funding_pages" / f"funding-{page_index:04d}-{start_ms}.json"
            _atomic_write(page_path, payload)
            page_record = {
                **_record(
                    source_url=url,
                    downloaded_utc=downloaded_utc,
                    payload=payload,
                    cache_state="downloaded",
                ),
                "page_index": page_index,
                "request_start_ms": start_ms,
                "request_end_ms": FUNDING_END_MS,
            }
        else:
            payload, page_record = cached
            if page_record.get("source_url") != url:
                raise ValueError(f"Cached funding page {page_index} has a different request identity.")
        new_records.append(page_record)
        manifest["funding_pages"] = list(new_records)
        _write_manifest(root, manifest)
        body = _read_json_payload(payload, f"Funding page {page_index}")
        parsed = _parse_funding_page(body, page_index)
        if raw_rows and parsed and parsed[0]["ts"] <= raw_rows[-1]["ts"]:
            raise ValueError("Funding pages are duplicated or out of ascending timestamp order.")
        raw_rows.extend(parsed)
        if len(body) < 1000:
            break
        last_ts = parsed[-1]["ts"]
        next_start = last_ts + 1
        if next_start <= start_ms:
            raise ValueError(f"Funding pagination did not advance after timestamp {last_ts}.")
        if next_start > FUNDING_END_MS:
            break
        start_ms = next_start
        page_index += 1

    if not raw_rows:
        raise ValueError("Funding endpoint returned no records for the requested range.")
    return raw_rows


def _verified_mark_price_cache(
    root: Path, month: _Month, manifest: dict[str, Any]
) -> dict[str, Any] | None:
    directory = root / MARK_PRICE_SUBDIR
    zip_path = directory / month.filename
    checksum_path = directory / (month.filename + ".CHECKSUM")
    if not zip_path.is_file() or not checksum_path.is_file():
        return None
    try:
        checksum_bytes = checksum_path.read_bytes()
        expected = _checksum_digest(checksum_bytes, month.filename)
        actual = sha256_file(zip_path)
        if actual != expected or not zipfile.is_zipfile(zip_path):
            return None
    except (OSError, ValueError):
        return None
    archive_bytes = zip_path.read_bytes()
    record = manifest.get("mark_price_archives", {}).get(month.stem, {})
    prior_archive = record.get("archive", {}) if isinstance(record, dict) else {}
    prior_checksum = record.get("checksum", {}) if isinstance(record, dict) else {}
    archive_time = prior_archive.get("download_utc") if prior_archive.get("sha256") == actual else None
    checksum_digest = _sha256_bytes(checksum_bytes)
    checksum_time = (
        prior_checksum.get("download_utc")
        if prior_checksum.get("sha256") == checksum_digest
        else None
    )
    return {
        "archive": _record(
            source_url=month.mark_price_source_url,
            downloaded_utc=archive_time,
            payload=archive_bytes,
            cache_state="verified_cache" if archive_time else "verified_cache_timestamp_unknown",
        ),
        "checksum": _record(
            source_url=month.mark_price_checksum_url,
            downloaded_utc=checksum_time,
            payload=checksum_bytes,
            cache_state="verified_cache" if checksum_time else "verified_cache_timestamp_unknown",
        ),
        "expected_rows": month.expected_rows,
        "first_open_ms": month.first_ms,
        "end_exclusive_ms": month.next_month_ms,
    }


def _download_mark_price_month(
    root: Path, month: _Month, manifest: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    cached = _verified_mark_price_cache(root, month, manifest)
    if cached is not None:
        return month.stem, cached
    zip_bytes, zip_time = _fetch_bytes(month.mark_price_source_url, limit=MAX_ARCHIVE_BYTES)
    checksum_bytes, checksum_time = _fetch_bytes(month.mark_price_checksum_url, limit=64 * 1024)
    expected = _checksum_digest(checksum_bytes, month.filename)
    actual = _sha256_bytes(zip_bytes)
    if actual != expected:
        raise ValueError(
            f"SHA-256 mismatch for mark-price archive {month.filename}: "
            f"checksum={expected}, downloaded={actual}."
        )
    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        raise ValueError(f"Downloaded mark-price archive is not a valid ZIP file: {month.filename}")
    directory = root / MARK_PRICE_SUBDIR
    _atomic_write(directory / month.filename, zip_bytes)
    _atomic_write(directory / (month.filename + ".CHECKSUM"), checksum_bytes)
    return month.stem, {
        "archive": _record(
            source_url=month.mark_price_source_url,
            downloaded_utc=zip_time,
            payload=zip_bytes,
            cache_state="downloaded_and_checksum_verified",
        ),
        "checksum": _record(
            source_url=month.mark_price_checksum_url,
            downloaded_utc=checksum_time,
            payload=checksum_bytes,
            cache_state="downloaded",
        ),
        "expected_rows": month.expected_rows,
        "first_open_ms": month.first_ms,
        "end_exclusive_ms": month.next_month_ms,
    }


def _ensure_mark_price_archives(
    root: Path, months: list[_Month], manifest: dict[str, Any]
) -> None:
    if not months:
        return
    failures: list[tuple[str, str]] = []
    cached_manifest = {"mark_price_archives": dict(manifest.get("mark_price_archives", {}))}
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {
            executor.submit(_download_mark_price_month, root, month, cached_manifest): month
            for month in months
        }
        for future in as_completed(futures):
            month = futures[future]
            try:
                stem, record = future.result()
                manifest.setdefault("mark_price_archives", {})[stem] = record
                _write_manifest(root, manifest)
            except Exception as exc:
                failures.append((month.stem, str(exc)))
    if failures:
        details = "; ".join(f"{month}: {error}" for month, error in sorted(failures))
        raise ValueError(f"One or more required mark-price archives could not be verified: {details}")


def _open_mark_price_member(
    root: Path, month: _Month, manifest: dict[str, Any]
) -> tuple[zipfile.ZipFile, Any]:
    directory = root / MARK_PRICE_SUBDIR
    zip_path = directory / month.filename
    checksum_path = directory / (month.filename + ".CHECKSUM")
    if not zip_path.is_file() or not checksum_path.is_file():
        raise ValueError(f"Required checksum-verified mark-price archive is missing: {zip_path}")
    try:
        checksum_bytes = checksum_path.read_bytes()
        expected = _checksum_digest(checksum_bytes, month.filename)
        actual = sha256_file(zip_path)
        if expected != actual:
            raise ValueError(f"SHA-256 mismatch for cached mark-price archive {month.filename}.")
        record = manifest.get("mark_price_archives", {}).get(month.stem)
        if not isinstance(record, dict):
            raise ValueError(f"Manifest has no mark-price archive record for {month.filename}.")
        archive_record = record.get("archive")
        checksum_record = record.get("checksum")
        archive_bytes = zip_path.read_bytes()
        if (
            not isinstance(archive_record, dict)
            or archive_record.get("source_url") != month.mark_price_source_url
            or archive_record.get("sha256") != actual
            or archive_record.get("bytes") != len(archive_bytes)
        ):
            raise ValueError(f"Manifest mark-price archive identity does not match {month.filename}.")
        if (
            not isinstance(checksum_record, dict)
            or checksum_record.get("source_url") != month.mark_price_checksum_url
            or checksum_record.get("sha256") != _sha256_bytes(checksum_bytes)
            or checksum_record.get("bytes") != len(checksum_bytes)
        ):
            raise ValueError(
                f"Manifest mark-price checksum identity does not match {month.filename}.CHECKSUM."
            )
        archive = zipfile.ZipFile(zip_path)
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            archive.close()
            raise ValueError(
                f"Mark-price archive {month.filename} must contain one CSV member; found {len(csv_members)}."
            )
        return archive, archive.open(csv_members[0], "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Cannot open checksum-verified mark-price archive {month.filename}: {exc}") from exc


def _parse_mark_price_openings(
    member: Any,
    filename: str,
    first_ms: int,
    end_exclusive_ms: int,
    target_times: set[int],
    *,
    expected_rows: int | None = None,
) -> dict[int, float]:
    openings: dict[int, float] = {}
    previous_t: int | None = None
    row_count = 0
    first_t: int | None = None
    last_t: int | None = None
    text = io.TextIOWrapper(member, encoding="utf-8", newline="")
    for line_number, values in enumerate(csv.reader(text), start=1):
        if line_number == 1 and _is_header(values):
            continue
        if len(values) < 5:
            raise ValueError(f"{filename} mark-price CSV row {line_number} has fewer than five fields.")
        try:
            t = int(values[0])
            open_price, high, low, close = (float(value) for value in values[1:5])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{filename} mark-price row {line_number} has an invalid timestamp or OHLC value."
            ) from exc
        values_to_check = (open_price, high, low, close)
        if not all(math.isfinite(value) and value > 0 for value in values_to_check):
            raise ValueError(f"{filename} mark-price row {line_number} has a non-finite or non-positive OHLC.")
        if low > min(open_price, close) or high < max(open_price, close) or low > high:
            raise ValueError(f"{filename} mark-price row {line_number} has invalid OHLC ordering.")
        if t % INTERVAL_MS or t < first_ms or t >= end_exclusive_ms:
            raise ValueError(f"{filename} mark-price row {line_number} has a misaligned or out-of-period timestamp.")
        if previous_t is not None and (
            t <= previous_t or (expected_rows is not None and t != previous_t + INTERVAL_MS)
        ):
            raise ValueError(f"{filename} mark-price timestamps are duplicated, out of order, or gapped.")
        if first_t is None:
            first_t = t
        if t in target_times:
            openings[t] = open_price
        previous_t = last_t = t
        row_count += 1
    if expected_rows is not None and (
        row_count != expected_rows
        or first_t != first_ms
        or last_t != end_exclusive_ms - INTERVAL_MS
    ):
        raise ValueError(
            f"{filename} has {row_count} mark-price rows; expected a contiguous {expected_rows}-row period."
        )
    return openings


def _read_mark_price_opens(
    root: Path,
    month: _Month,
    manifest: dict[str, Any],
    target_times: set[int],
) -> dict[int, float]:
    archive, member = _open_mark_price_member(root, month, manifest)
    try:
        return _parse_mark_price_openings(
            member, month.filename, month.first_ms, month.next_month_ms, target_times
        )
    finally:
        try:
            member.close()
        finally:
            archive.close()


def _verified_daily_mark_cache(
    root: Path, archive: _DailyMarkArchive, manifest: dict[str, Any]
) -> dict[str, Any] | None:
    directory = root / MARK_PRICE_SUBDIR / "daily"
    zip_path = directory / archive.filename
    checksum_path = directory / (archive.filename + ".CHECKSUM")
    if not zip_path.is_file() or not checksum_path.is_file():
        return None
    try:
        checksum_bytes = checksum_path.read_bytes()
        expected = _checksum_digest(checksum_bytes, archive.filename)
        actual = sha256_file(zip_path)
        if actual != expected or not zipfile.is_zipfile(zip_path):
            return None
    except (OSError, ValueError):
        return None
    zip_bytes = zip_path.read_bytes()
    prior = manifest.get("mark_price_daily_archives", {}).get(archive.date, {})
    prior_zip = prior.get("archive", {}) if isinstance(prior, dict) else {}
    prior_sum = prior.get("checksum", {}) if isinstance(prior, dict) else {}
    zip_time = prior_zip.get("download_utc") if prior_zip.get("sha256") == actual else None
    sum_digest = _sha256_bytes(checksum_bytes)
    sum_time = prior_sum.get("download_utc") if prior_sum.get("sha256") == sum_digest else None
    return {
        "archive": _record(
            source_url=archive.source_url,
            downloaded_utc=zip_time,
            payload=zip_bytes,
            cache_state="verified_cache" if zip_time else "verified_cache_timestamp_unknown",
        ),
        "checksum": _record(
            source_url=archive.checksum_url,
            downloaded_utc=sum_time,
            payload=checksum_bytes,
            cache_state="verified_cache" if sum_time else "verified_cache_timestamp_unknown",
        ),
        "date": archive.date,
        "expected_rows": archive.expected_rows,
        "start_ms": archive.first_ms,
        "end_exclusive_ms": archive.end_exclusive_ms,
    }


def _download_daily_mark_archive(
    root: Path, archive: _DailyMarkArchive, manifest: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    cached = _verified_daily_mark_cache(root, archive, manifest)
    if cached is not None:
        return archive.date, cached
    zip_bytes, zip_time = _fetch_bytes(archive.source_url, limit=MAX_ARCHIVE_BYTES)
    checksum_bytes, checksum_time = _fetch_bytes(archive.checksum_url, limit=64 * 1024)
    expected = _checksum_digest(checksum_bytes, archive.filename)
    actual = _sha256_bytes(zip_bytes)
    if actual != expected:
        raise ValueError(
            f"SHA-256 mismatch for daily mark-price archive {archive.filename}: "
            f"checksum={expected}, downloaded={actual}."
        )
    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        raise ValueError(f"Downloaded daily mark-price archive is not a valid ZIP: {archive.filename}")
    directory = root / MARK_PRICE_SUBDIR / "daily"
    _atomic_write(directory / archive.filename, zip_bytes)
    _atomic_write(directory / (archive.filename + ".CHECKSUM"), checksum_bytes)
    return archive.date, {
        "archive": _record(
            source_url=archive.source_url,
            downloaded_utc=zip_time,
            payload=zip_bytes,
            cache_state="downloaded_and_checksum_verified",
        ),
        "checksum": _record(
            source_url=archive.checksum_url,
            downloaded_utc=checksum_time,
            payload=checksum_bytes,
            cache_state="downloaded",
        ),
        "date": archive.date,
        "expected_rows": archive.expected_rows,
        "start_ms": archive.first_ms,
        "end_exclusive_ms": archive.end_exclusive_ms,
    }


def _ensure_daily_mark_archives(
    root: Path, dates: list[str], manifest: dict[str, Any]
) -> None:
    if not dates:
        return
    archives = [_daily_mark_archive(value) for value in sorted(set(dates))]
    cached_manifest = {
        "mark_price_daily_archives": dict(manifest.get("mark_price_daily_archives", {}))
    }
    failures: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {
            executor.submit(_download_daily_mark_archive, root, archive, cached_manifest): archive
            for archive in archives
        }
        for future in as_completed(futures):
            archive = futures[future]
            try:
                date_value, record = future.result()
                manifest.setdefault("mark_price_daily_archives", {})[date_value] = record
                _write_manifest(root, manifest)
            except Exception as exc:
                failures.append((archive.date, str(exc)))
    if failures:
        details = "; ".join(f"{date}: {error}" for date, error in sorted(failures))
        raise ValueError(f"One or more authorized daily mark-price repairs failed: {details}")


def _open_daily_mark_price_member(
    root: Path, archive: _DailyMarkArchive, manifest: dict[str, Any]
) -> tuple[zipfile.ZipFile, Any]:
    directory = root / MARK_PRICE_SUBDIR / "daily"
    zip_path = directory / archive.filename
    checksum_path = directory / (archive.filename + ".CHECKSUM")
    if not zip_path.is_file() or not checksum_path.is_file():
        raise ValueError(f"Required checksum-verified daily mark-price archive is missing: {zip_path}")
    try:
        checksum_bytes = checksum_path.read_bytes()
        expected = _checksum_digest(checksum_bytes, archive.filename)
        actual = sha256_file(zip_path)
        if expected != actual:
            raise ValueError(f"SHA-256 mismatch for cached daily mark-price archive {archive.filename}.")
        record = manifest.get("mark_price_daily_archives", {}).get(archive.date)
        if not isinstance(record, dict):
            raise ValueError(f"Manifest has no daily mark-price record for {archive.filename}.")
        archive_record, checksum_record = record.get("archive"), record.get("checksum")
        zip_bytes = zip_path.read_bytes()
        if (
            not isinstance(archive_record, dict)
            or archive_record.get("source_url") != archive.source_url
            or archive_record.get("sha256") != actual
            or archive_record.get("bytes") != len(zip_bytes)
        ):
            raise ValueError(f"Manifest daily mark-price identity does not match {archive.filename}.")
        if (
            not isinstance(checksum_record, dict)
            or checksum_record.get("source_url") != archive.checksum_url
            or checksum_record.get("sha256") != _sha256_bytes(checksum_bytes)
            or checksum_record.get("bytes") != len(checksum_bytes)
        ):
            raise ValueError(
                f"Manifest daily mark-price checksum identity does not match {archive.filename}.CHECKSUM."
            )
        zip_archive = zipfile.ZipFile(zip_path)
        members = [name for name in zip_archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            zip_archive.close()
            raise ValueError(
                f"Daily mark-price archive {archive.filename} must contain one CSV member; found {len(members)}."
            )
        return zip_archive, zip_archive.open(members[0], "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(
            f"Cannot open checksum-verified daily mark-price archive {archive.filename}: {exc}"
        ) from exc


def _read_daily_mark_price_opens(
    root: Path,
    archive: _DailyMarkArchive,
    manifest: dict[str, Any],
    target_times: set[int],
) -> dict[int, float]:
    zip_archive, member = _open_daily_mark_price_member(root, archive, manifest)
    try:
        openings = _parse_mark_price_openings(
            member,
            archive.filename,
            archive.first_ms,
            archive.end_exclusive_ms,
            target_times,
            expected_rows=archive.expected_rows,
        )
    finally:
        try:
            member.close()
        finally:
            zip_archive.close()
    missing = sorted(target_times - openings.keys())
    if missing:
        raise ValueError(f"Daily mark-price archive {archive.filename} lacks required candle opens at {missing}.")
    return openings


def _resolve_funding_marks(
    root: Path,
    manifest: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    *,
    download_missing: bool,
) -> tuple[list[dict[str, int | float]], dict[str, Any], dict[str, Any]]:
    missing = [row for row in raw_rows if row["api_mark"] is None]
    target_months: dict[str, _Month] = {}
    candle_time_by_funding: dict[int, int] = {}
    for row in missing:
        candle_t = (row["ts"] // INTERVAL_MS) * INTERVAL_MS
        candle_time_by_funding[row["ts"]] = candle_t
        month_date = datetime.fromtimestamp(candle_t / 1000, UTC)
        month = _Month(month_date.year, month_date.month)
        target_months[month.stem] = month
    if download_missing:
        _ensure_mark_price_archives(root, list(target_months.values()), manifest)

    opens_by_month: dict[str, dict[int, float]] = {}
    targets_by_month: dict[str, set[int]] = {stem: set() for stem in target_months}
    for row in missing:
        candle_t = candle_time_by_funding[row["ts"]]
        month_date = datetime.fromtimestamp(candle_t / 1000, UTC)
        stem = f"{SYMBOL}-{INTERVAL}-{month_date.year:04d}-{month_date.month:02d}"
        targets_by_month[stem].add(candle_t)
    for stem, month in target_months.items():
        opens_by_month[stem] = _read_mark_price_opens(
            root, month, manifest, targets_by_month[stem]
        )

    daily_targets: dict[str, set[int]] = {}
    daily_month_by_date: dict[str, str] = {}
    for row in missing:
        candle_t = candle_time_by_funding[row["ts"]]
        month_dt = datetime.fromtimestamp(candle_t / 1000, UTC)
        month_stem = f"{SYMBOL}-{INTERVAL}-{month_dt.year:04d}-{month_dt.month:02d}"
        if candle_t in opens_by_month[month_stem]:
            continue
        date_value = datetime.fromtimestamp(candle_t / 1000, UTC).strftime("%Y-%m-%d")
        _daily_mark_archive(date_value)
        daily_targets.setdefault(date_value, set()).add(candle_t)
        daily_month_by_date[date_value] = month_stem
    if download_missing:
        _ensure_daily_mark_archives(root, list(daily_targets), manifest)
    opens_by_day: dict[str, dict[int, float]] = {}
    for date_value, target_times in daily_targets.items():
        opens_by_day[date_value] = _read_daily_mark_price_opens(
            root, _daily_mark_archive(date_value), manifest, target_times
        )

    normalized: list[dict[str, int | float]] = []
    provenance_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        ts, api_mark = row["ts"], row["api_mark"]
        if api_mark is not None:
            mark = api_mark
            provenance_rows.append(
                {
                    "funding_ts": ts,
                    "source": "api_mark",
                    "mark": mark,
                    "mark_candle_open_ts": None,
                    "archive_type": None,
                    "archive_id": None,
                }
            )
        else:
            candle_t = candle_time_by_funding[ts]
            candle_dt = datetime.fromtimestamp(candle_t / 1000, UTC)
            stem = f"{SYMBOL}-{INTERVAL}-{candle_dt.year:04d}-{candle_dt.month:02d}"
            if candle_t in opens_by_month[stem]:
                mark = opens_by_month[stem][candle_t]
                source, archive_type, archive_id = "mark_price_open_proxy", "monthly", stem
            else:
                date_value = candle_dt.strftime("%Y-%m-%d")
                mark = opens_by_day[date_value][candle_t]
                source, archive_type, archive_id = "mark_price_daily_open_repair", "daily", date_value
            provenance_rows.append(
                {
                    "funding_ts": ts,
                    "source": source,
                    "mark": mark,
                    "mark_candle_open_ts": candle_t,
                    "archive_type": archive_type,
                    "archive_id": archive_id,
                }
            )
        normalized.append({"ts": ts, "rate": float(row["rate"]), "mark": float(mark)})

    repairs: list[dict[str, Any]] = []
    for date_value, target_times in sorted(daily_targets.items()):
        month_stem = daily_month_by_date[date_value]
        month_record = manifest.get("mark_price_archives", {}).get(month_stem)
        daily_record = manifest.get("mark_price_daily_archives", {}).get(date_value)
        if not isinstance(month_record, dict) or not isinstance(daily_record, dict):
            raise ValueError(f"Repair provenance lacks archive identities for {date_value}.")
        month = target_months[month_stem]
        daily_archive = _daily_mark_archive(date_value)
        repaired_rows = [
            {
                "funding_ts": row["ts"],
                "mark_candle_open_ts": candle_time_by_funding[row["ts"]],
                "mark": opens_by_day[date_value][candle_time_by_funding[row["ts"]]],
                "source": "mark_price_daily_open_repair",
            }
            for row in missing
            if datetime.fromtimestamp(candle_time_by_funding[row["ts"]] / 1000, UTC).strftime("%Y-%m-%d")
            == date_value
        ]
        repairs.append(
            {
                "date": date_value,
                "missing_funding_timestamps": sorted(row["funding_ts"] for row in repaired_rows),
                "missing_candle_open_timestamps": sorted(target_times),
                "monthly_archive": {
                    "source_url": month.mark_price_source_url,
                    "sha256": month_record["archive"]["sha256"],
                    "bytes": month_record["archive"]["bytes"],
                    "checksum_url": month.mark_price_checksum_url,
                    "checksum_sha256": month_record["checksum"]["sha256"],
                },
                "daily_archive": {
                    "source_url": daily_archive.source_url,
                    "sha256": daily_record["archive"]["sha256"],
                    "bytes": daily_record["archive"]["bytes"],
                    "checksum_url": daily_archive.checksum_url,
                    "checksum_sha256": daily_record["checksum"]["sha256"],
                },
                "row_provenance": repaired_rows,
            }
        )

    monthly_proxy_rows = sum(item["source"] == "mark_price_open_proxy" for item in provenance_rows)
    daily_repair_rows = sum(item["source"] == "mark_price_daily_open_repair" for item in provenance_rows)
    proxy_months = sorted(
        {item["archive_id"] for item in provenance_rows if item["archive_type"] == "monthly"}
    )
    provenance = {
        "schema_version": "btc_liquidity_funding_mark_provenance_v1",
        "rows": provenance_rows,
        "summary": {
            "rows": len(provenance_rows),
            "api_mark_rows": sum(item["source"] == "api_mark" for item in provenance_rows),
            "proxy_mark_rows": monthly_proxy_rows + daily_repair_rows,
            "monthly_proxy_rows": monthly_proxy_rows,
            "daily_repair_rows": daily_repair_rows,
            "proxy_archive_months": proxy_months,
            "daily_repair_dates": sorted(daily_targets),
        },
    }
    repair_log = {
        "schema_version": "btc_liquidity_mark_price_gap_repairs_v1",
        "repairs": repairs,
        "summary": {
            "dates": sorted(daily_targets),
            "repaired_funding_rows": daily_repair_rows,
            "repaired_candle_open_rows": sum(len(item["missing_candle_open_timestamps"]) for item in repairs),
        },
    }
    return normalized, provenance, repair_log


def _write_funding_outputs(
    root: Path,
    manifest: dict[str, Any],
    normalized: list[dict[str, int | float]],
    provenance: dict[str, Any],
    repair_log: dict[str, Any],
) -> None:
    provenance_bytes = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    normalized_bytes = (json.dumps(normalized, indent=2) + "\n").encode("utf-8")
    coverage = _funding_coverage(normalized, provenance["rows"])
    coverage_bytes = (json.dumps(coverage, indent=2, sort_keys=True) + "\n").encode("utf-8")
    repairs_bytes = (json.dumps(repair_log, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write(root / "funding_mark_provenance.json", provenance_bytes)
    _atomic_write(root / "normalized_funding.json", normalized_bytes)
    _atomic_write(root / "funding_coverage.json", coverage_bytes)
    _atomic_write(root / "mark_price_gap_repairs.json", repairs_bytes)
    sources = manifest.setdefault("sources", {})
    counts = provenance["summary"]
    sources["funding_mark_provenance"] = {
        "source_url": "derived from exact funding pages and checksum-verified mark-price archives",
        "download_utc": None,
        "sha256": _sha256_bytes(provenance_bytes),
        "bytes": len(provenance_bytes),
        "cache_state": "reconstructed_from_exact_sources",
        "api_mark_rows": counts["api_mark_rows"],
        "proxy_mark_rows": counts["proxy_mark_rows"],
        "monthly_proxy_rows": counts["monthly_proxy_rows"],
        "daily_repair_rows": counts["daily_repair_rows"],
        "proxy_archive_months": counts["proxy_archive_months"],
        "daily_repair_dates": counts["daily_repair_dates"],
    }
    sources["normalized_funding"] = {
        "source_url": "derived from exact funding pages and funding mark provenance",
        "download_utc": None,
        "sha256": _sha256_bytes(normalized_bytes),
        "bytes": len(normalized_bytes),
        "cache_state": "normalized_without_rate_or_mark_repair",
    }
    sources["funding_coverage"] = {
        "source_url": "derived from exact funding timestamps and mark provenance",
        "download_utc": None,
        "sha256": _sha256_bytes(coverage_bytes),
        "bytes": len(coverage_bytes),
        "cache_state": "coverage_audit",
    }
    sources["mark_price_gap_repairs"] = {
        "source_url": "derived from exact missing monthly marks and verified daily mark-price opens",
        "download_utc": None,
        "sha256": _sha256_bytes(repairs_bytes),
        "bytes": len(repairs_bytes),
        "cache_state": "bounded_missing_row_repairs",
        "dates": repair_log["summary"]["dates"],
        "repaired_funding_rows": repair_log["summary"]["repaired_funding_rows"],
    }
    _write_manifest(root, manifest)


def _download_funding(root: Path, manifest: dict[str, Any]) -> list[dict[str, int | float]]:
    raw_rows = _download_funding_pages(root, manifest)
    normalized, provenance, repair_log = _resolve_funding_marks(
        root, manifest, raw_rows, download_missing=True
    )
    _write_funding_outputs(root, manifest, normalized, provenance, repair_log)
    return normalized


def _download_exchange_info(root: Path, manifest: dict[str, Any]) -> bytes:
    return _cache_source(
        root,
        name="exchange_info",
        url=EXCHANGE_INFO_URL,
        path=root / "exchangeInfo.json",
        limit=MAX_JSON_BYTES,
        manifest=manifest,
    )


def download(root: Path) -> dict[str, Any]:
    """Download the fixed public data contract into ``root`` and audit it."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(root)
    months = _months()
    failures: list[tuple[str, str]] = []
    cached_month_records = dict(manifest.get("monthly_archives", {}))
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {
            executor.submit(_download_month, root, month, cached_month_records): month
            for month in months
        }
        for future in as_completed(futures):
            month = futures[future]
            try:
                stem, record = future.result()
                manifest.setdefault("monthly_archives", {})[stem] = record
                _write_manifest(root, manifest)
            except Exception as exc:  # record all independent month outcomes before failing
                failures.append((month.stem, str(exc)))
    if failures:
        details = "; ".join(f"{month}: {error}" for month, error in sorted(failures))
        raise ValueError(f"One or more monthly archives could not be verified: {details}")

    exchange_payload = _download_exchange_info(root, manifest)
    exchange_body = _read_json_payload(exchange_payload, "exchangeInfo")
    if not isinstance(exchange_body, dict) or not isinstance(exchange_body.get("symbols"), list):
        raise ValueError("exchangeInfo did not contain the expected symbols list.")
    if not any(item.get("symbol") == SYMBOL for item in exchange_body["symbols"] if isinstance(item, dict)):
        raise ValueError(f"exchangeInfo does not list {SYMBOL}.")

    _download_funding(root, manifest)
    _write_manifest(root, manifest)
    report = audit(root)
    load_funding(root)
    return report


def _open_archive_member(
    root: Path, month: _Month, manifest: dict[str, Any]
) -> tuple[zipfile.ZipFile, Any]:
    path = root / month.filename
    if not path.is_file():
        raise ValueError(f"Required monthly archive is missing: {path}")
    checksum_path = root / (month.filename + ".CHECKSUM")
    if not checksum_path.is_file():
        raise ValueError(f"Required checksum file is missing: {checksum_path}")
    try:
        checksum_bytes = checksum_path.read_bytes()
        checksum = _checksum_digest(checksum_bytes, month.filename)
        actual = sha256_file(path)
        if actual != checksum:
            raise ValueError(f"SHA-256 mismatch for cached archive {month.filename}.")
        archive_record = manifest.get("monthly_archives", {}).get(month.stem)
        if not isinstance(archive_record, dict):
            raise ValueError(f"Manifest has no archive record for {month.filename}.")
        archive_provenance = archive_record.get("archive")
        checksum_provenance = archive_record.get("checksum")
        zip_bytes = path.read_bytes()
        if (
            not isinstance(archive_provenance, dict)
            or archive_provenance.get("source_url") != month.source_url
            or archive_provenance.get("sha256") != actual
            or archive_provenance.get("bytes") != len(zip_bytes)
        ):
            raise ValueError(f"Manifest archive identity does not match {month.filename}.")
        if (
            not isinstance(checksum_provenance, dict)
            or checksum_provenance.get("source_url") != month.checksum_url
            or checksum_provenance.get("sha256") != _sha256_bytes(checksum_bytes)
            or checksum_provenance.get("bytes") != len(checksum_bytes)
        ):
            raise ValueError(f"Manifest checksum identity does not match {month.filename}.CHECKSUM.")
        archive = zipfile.ZipFile(path)
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            archive.close()
            raise ValueError(
                f"Archive {month.filename} must contain exactly one CSV member; found {len(csv_members)}."
            )
        return archive, archive.open(csv_members[0], "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Cannot open checksum-verified archive {month.filename}: {exc}") from exc


def _is_header(row: list[str]) -> bool:
    if len(row) < 5:
        return False
    normalized = [cell.strip().lower().replace(" ", "_") for cell in row[:6]]
    return normalized[0] in {"open_time", "opentime", "timestamp"} and normalized[1:5] == [
        "open",
        "high",
        "low",
        "close",
    ]


def _read_month_rows(
    root: Path, month: _Month, manifest: dict[str, Any]
) -> list[_RawCandle]:
    archive, member = _open_archive_member(root, month, manifest)
    rows: list[_RawCandle] = []
    try:
        text = io.TextIOWrapper(member, encoding="utf-8", newline="")
        reader = csv.reader(text)
        for line_number, values in enumerate(reader, start=1):
            if line_number == 1 and _is_header(values):
                continue
            if len(values) < 6:
                raise ValueError(
                    f"{month.filename} CSV row {line_number} has {len(values)} fields; at least six are required."
                )
            try:
                t = int(values[0])
                candle = _RawCandle(
                    t=t,
                    open=float(values[1]),
                    high=float(values[2]),
                    low=float(values[3]),
                    close=float(values[4]),
                    volume=float(values[5]),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{month.filename} CSV row {line_number} has an invalid timestamp or OHLCV value."
                ) from exc
            if candle.t < month.first_ms or candle.t >= month.next_month_ms:
                raise ValueError(
                    f"{month.filename} row {line_number} timestamp {candle.t} falls outside that archive month."
                )
            rows.append(candle)
    finally:
        try:
            member.close()
        finally:
            archive.close()
    if len(rows) != month.expected_rows:
        raise ValueError(
            f"{month.filename} has {len(rows)} candle rows; expected {month.expected_rows} for the full UTC month."
        )
    return rows


def _manifest_digest(root: Path) -> str:
    path = root / "manifest.json"
    if not path.is_file():
        raise ValueError(f"Raw-data manifest is missing: {path}")
    return sha256_file(path)


def _audit_candle_rows(rows: list[_RawCandle], manifest_digest: str) -> dict[str, Any]:
    duplicates: list[int] = []
    gaps: list[dict[str, int]] = []
    order_violations: list[dict[str, int]] = []
    invalid_rows: list[dict[str, Any]] = []
    for index, candle in enumerate(rows):
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(value) for value in values):
            invalid_rows.append({"index": index, "t": candle.t, "reason": "non_finite_value"})
        elif min(candle.open, candle.high, candle.low, candle.close) <= 0:
            invalid_rows.append({"index": index, "t": candle.t, "reason": "non_positive_ohlc"})
        elif candle.volume < 0:
            invalid_rows.append({"index": index, "t": candle.t, "reason": "negative_volume"})
        elif candle.low > min(candle.open, candle.close) or candle.high < max(
            candle.open, candle.close
        ) or candle.low > candle.high:
            invalid_rows.append({"index": index, "t": candle.t, "reason": "invalid_ohlc_order"})
        if candle.t < START_MS or candle.t >= END_EXCLUSIVE_MS:
            invalid_rows.append({"index": index, "t": candle.t, "reason": "outside_requested_range"})
        if candle.t % INTERVAL_MS:
            invalid_rows.append({"index": index, "t": candle.t, "reason": "misaligned_5m_timestamp"})
        if index:
            previous = rows[index - 1].t
            if candle.t == previous:
                duplicates.append(candle.t)
            elif candle.t < previous:
                order_violations.append({"previous_t": previous, "t": candle.t})
            elif candle.t - previous > INTERVAL_MS:
                gaps.append(
                    {
                        "after_t": previous,
                        "before_t": candle.t,
                        "missing_intervals": (candle.t - previous) // INTERVAL_MS - 1,
                    }
                )
            elif candle.t - previous < INTERVAL_MS:
                order_violations.append({"previous_t": previous, "t": candle.t})
    expected_rows = (END_EXCLUSIVE_MS - START_MS) // INTERVAL_MS
    first_t = rows[0].t if rows else None
    last_t = rows[-1].t if rows else None
    if first_t != START_MS:
        invalid_rows.append({"index": 0 if rows else None, "t": first_t, "reason": "wrong_first_timestamp"})
    expected_last = END_EXCLUSIVE_MS - INTERVAL_MS
    if last_t != expected_last:
        invalid_rows.append(
            {"index": len(rows) - 1 if rows else None, "t": last_t, "reason": "wrong_last_timestamp"}
        )
    if len(rows) != expected_rows:
        invalid_rows.append(
            {"index": None, "t": None, "reason": "wrong_total_row_count", "actual": len(rows), "expected": expected_rows}
        )
    return {
        "schema_version": "btc_liquidity_audit_v1",
        "status": "PASS" if not (duplicates or gaps or order_violations or invalid_rows) else "BLOCKED",
        "symbol": SYMBOL,
        "venue": "Binance USD-M perpetual",
        "interval": INTERVAL,
        "timezone": "UTC",
        "rows": len(rows),
        "expected_rows": expected_rows,
        "bounds": {
            "first_t": first_t,
            "first_utc": _iso_ms(first_t),
            "last_t": last_t,
            "last_utc": _iso_ms(last_t),
            "start_inclusive_ms": START_MS,
            "end_exclusive_ms": END_EXCLUSIVE_MS,
        },
        "duplicates": {"count": len(duplicates), "timestamps": duplicates[:100]},
        "gaps": {"count": len(gaps), "intervals": gaps[:100]},
        "order_violations": {"count": len(order_violations), "examples": order_violations[:100]},
        "invalid_rows": {"count": len(invalid_rows), "examples": invalid_rows[:100]},
        "manifest_digest": manifest_digest,
    }


def _read_all_rows(root: Path) -> list[_RawCandle]:
    manifest = _load_manifest(root)
    rows: list[_RawCandle] = []
    for month in _months():
        rows.extend(_read_month_rows(root, month, manifest))
    return rows


def audit(root: Path) -> dict[str, Any]:
    """Verify all raw archives and write the candle-quality audit report."""
    root = Path(root)
    try:
        rows = _read_all_rows(root)
        report = _audit_candle_rows(rows, _manifest_digest(root))
    except ValueError as exc:
        report = {
            "schema_version": "btc_liquidity_audit_v1",
            "status": "BLOCKED",
            "symbol": SYMBOL,
            "venue": "Binance USD-M perpetual",
            "interval": INTERVAL,
            "timezone": "UTC",
            "rows": None,
            "expected_rows": (END_EXCLUSIVE_MS - START_MS) // INTERVAL_MS,
            "bounds": {"start_inclusive_ms": START_MS, "end_exclusive_ms": END_EXCLUSIVE_MS},
            "duplicates": {"count": None, "timestamps": []},
            "gaps": {"count": None, "intervals": []},
            "error": str(exc),
            "manifest_digest": _manifest_digest(root) if (root / "manifest.json").is_file() else None,
        }
        _atomic_write(root / "audit.json", (json.dumps(report, indent=2) + "\n").encode("utf-8"))
        raise ValueError(f"BTC raw-data audit failed: {exc}") from exc
    _atomic_write(root / "audit.json", (json.dumps(report, indent=2) + "\n").encode("utf-8"))
    if report["status"] != "PASS":
        raise ValueError(
            "BTC raw-data audit failed: "
            f"rows={report['rows']}, duplicates={report['duplicates']['count']}, "
            f"gaps={report['gaps']['count']}, invalid={report['invalid_rows']['count']}."
        )
    return report


def load_candles(root: Path) -> list[Candle]:
    """Load only fully audited candles as ``app.btc_liquidity.Candle`` values."""
    root = Path(root)
    rows = _read_all_rows(root)
    report = _audit_candle_rows(rows, _manifest_digest(root))
    _atomic_write(root / "audit.json", (json.dumps(report, indent=2) + "\n").encode("utf-8"))
    if report["status"] != "PASS":
        raise ValueError(
            "BTC candle audit failed: "
            f"rows={report['rows']}, duplicates={report['duplicates']['count']}, "
            f"gaps={report['gaps']['count']}, invalid={report['invalid_rows']['count']}."
        )
    try:
        from app.btc_liquidity import Candle
    except ImportError as exc:
        raise ValueError("Core API app.btc_liquidity.Candle is not available yet.") from exc
    return [
        Candle(candle.t, candle.open, candle.high, candle.low, candle.close, candle.volume)
        for candle in rows
    ]


def _verified_derived_file(
    root: Path, manifest: dict[str, Any], name: str, filename: str
) -> tuple[bytes, dict[str, Any]]:
    path = root / filename
    if not path.is_file():
        raise ValueError(f"Required funding audit file is missing: {path}")
    payload = path.read_bytes()
    record = manifest.get("sources", {}).get(name)
    if (
        not isinstance(record, dict)
        or record.get("sha256") != _sha256_bytes(payload)
        or record.get("bytes") != len(payload)
    ):
        raise ValueError(f"{filename} identity does not match its manifest record.")
    return payload, record


def load_funding(root: Path) -> list[dict[str, int | float]]:
    """Rebuild funding marks from exact API rows and verified mark-price opens."""
    root = Path(root)
    manifest = _load_manifest(root)
    raw_rows = _read_funding_api_pages(root, manifest)
    expected, provenance, expected_repairs = _resolve_funding_marks(
        root, manifest, raw_rows, download_missing=False
    )

    provenance_bytes, provenance_record = _verified_derived_file(
        root, manifest, "funding_mark_provenance", "funding_mark_provenance.json"
    )
    saved_provenance = _read_json_payload(provenance_bytes, "funding mark provenance")
    if saved_provenance != provenance:
        raise ValueError("Funding mark provenance does not match exact API rows and mark-price opens.")
    summary = provenance["summary"]
    for key in (
        "api_mark_rows",
        "proxy_mark_rows",
        "monthly_proxy_rows",
        "daily_repair_rows",
        "proxy_archive_months",
        "daily_repair_dates",
    ):
        if provenance_record.get(key) != summary[key]:
            raise ValueError(f"Funding mark provenance manifest field {key!r} does not match its file.")

    repairs_bytes, repairs_record = _verified_derived_file(
        root, manifest, "mark_price_gap_repairs", "mark_price_gap_repairs.json"
    )
    saved_repairs = _read_json_payload(repairs_bytes, "mark-price gap repair log")
    if saved_repairs != expected_repairs:
        raise ValueError("Mark-price gap repair log does not match exact monthly and daily source rows.")
    for key in ("dates", "repaired_funding_rows"):
        if repairs_record.get(key) != expected_repairs["summary"][key]:
            raise ValueError(f"Mark-price repair manifest field {key!r} does not match its file.")

    normalized_bytes, _ = _verified_derived_file(
        root, manifest, "normalized_funding", "normalized_funding.json"
    )
    saved_normalized = _read_json_payload(normalized_bytes, "normalized funding")
    if not isinstance(saved_normalized, list) or len(saved_normalized) != len(expected):
        raise ValueError("Normalized funding row count does not match the exact API pages.")
    checked: list[dict[str, int | float]] = []
    for index, item in enumerate(saved_normalized):
        if not isinstance(item, dict) or set(item) != {"ts", "rate", "mark"}:
            raise ValueError(f"Normalized funding row {index} must contain exactly ts, rate, and mark.")
        ts, rate, mark = item["ts"], item["rate"], item["mark"]
        if isinstance(ts, bool) or not isinstance(ts, int):
            raise ValueError(f"Normalized funding row {index} has a non-integer timestamp.")
        if not isinstance(rate, (int, float)) or not math.isfinite(rate):
            raise ValueError(f"Normalized funding row {index} has a non-finite rate.")
        if not isinstance(mark, (int, float)) or not math.isfinite(mark) or mark <= 0:
            raise ValueError(f"Normalized funding row {index} has an invalid mark price.")
        checked.append({"ts": ts, "rate": float(rate), "mark": float(mark)})
    if checked != expected:
        raise ValueError("Normalized funding values do not match the exact API pages and mark sources.")

    coverage = _funding_coverage(checked, provenance["rows"])
    coverage_bytes, _ = _verified_derived_file(
        root, manifest, "funding_coverage", "funding_coverage.json"
    )
    saved_coverage = _read_json_payload(coverage_bytes, "funding coverage")
    if saved_coverage != coverage:
        raise ValueError("Funding coverage does not match the exact timestamps and mark provenance.")
    if coverage["status"] != "PASS":
        raise ValueError(
            "Funding coverage is incomplete: "
            f"start gap={coverage['start_gap_ms']} ms, end gap={coverage['end_gap_ms']} ms, "
            f"max event gap={coverage['max_gap_ms']} ms, over-8h gaps={len(coverage['gaps_over_8h'])}."
        )
    return checked


def _bar_time(bar: Any, index: int) -> int:
    try:
        value = int(bar.t)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"5m bar {index} has no integer millisecond timestamp field 't'.") from exc
    return value


def resample_15m(bars: list[Any]) -> list[Any]:
    """Aggregate complete, UTC-aligned 5m triplets without synthesizing bars."""
    if not bars:
        return []
    try:
        from app.btc_liquidity import Candle, validate_bars
        validate_bars(bars, 5)
    except ImportError as exc:
        raise ValueError("Core API app.btc_liquidity is not available yet.") from exc
    groups: list[list[Any]] = []
    current: list[Any] = []
    current_bucket: int | None = None
    previous_t: int | None = None
    for index, bar in enumerate(bars):
        t = _bar_time(bar, index)
        if t % INTERVAL_MS:
            raise ValueError(f"5m bar {index} timestamp {t} is not aligned to a UTC 5-minute boundary.")
        if previous_t is not None and t != previous_t + INTERVAL_MS:
            relation = "duplicate or out-of-order" if t <= previous_t else "missing"
            raise ValueError(
                f"5m input is {relation} at index {index}: expected {previous_t + INTERVAL_MS}, got {t}."
            )
        bucket = (t // 900_000) * 900_000
        if bucket != current_bucket:
            if current:
                groups.append(current)
            current = [bar]
            current_bucket = bucket
        else:
            current.append(bar)
        previous_t = t
    if current:
        groups.append(current)

    output: list[Any] = []
    for group in groups:
        first_t = _bar_time(group[0], 0)
        bucket_start = (first_t // 900_000) * 900_000
        expected = [bucket_start, bucket_start + INTERVAL_MS, bucket_start + 2 * INTERVAL_MS]
        times = [_bar_time(bar, index) for index, bar in enumerate(group)]
        if times != expected:
            # Incomplete edge buckets are omitted; any interior missing candle
            # was already rejected by the global contiguity check above.
            continue
        first, second, third = group
        try:
            output.append(
                Candle(
                    bucket_start,
                    float(first.open),
                    max(float(first.high), float(second.high), float(third.high)),
                    min(float(first.low), float(second.low), float(third.low)),
                    float(third.close),
                    sum(float(item.volume) for item in group),
                )
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"Cannot resample 5m triplet at timestamp {bucket_start}: {exc}") from exc
    return output


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="download fixed public Binance archives and audit")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("artifacts/strategy-development/btc-liquidity-20261023/raw"),
        help="raw artifact directory",
    )
    args = parser.parse_args()
    if not args.download:
        parser.error("--download is required; this tool only fetches the fixed public data contract.")
    try:
        report = download(args.root)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "rows": report["rows"],
                "expected_rows": report["expected_rows"],
                "first_t": report["bounds"]["first_t"],
                "last_t": report["bounds"]["last_t"],
                "manifest_digest": report["manifest_digest"],
                "audit_path": str(args.root / "audit.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
