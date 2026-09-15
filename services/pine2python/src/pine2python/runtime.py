from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .analyzer import analyze_source
from .config import Settings
from .errors import Pine2PythonError
from .models import Candle


def _standardize_runtime_trace(
    result: dict[str, Any], candles: list[Candle]
) -> dict[str, Any]:
    rows_by_time: dict[int, dict[str, Any]] = {}
    for index, candle in enumerate(candles):
        rows_by_time[candle.time] = {
            "time": candle.time,
            "bar_index": index,
            "market": {
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            },
            "features": {},
            "signals": {},
            "rejections": {},
            "orders": {},
            "state": {},
            "events": {"entries": [], "exits": []},
        }
    prefix_map = {
        "p2p__feature__": "features",
        "p2p__signal__": "signals",
        "p2p__rejection__": "rejections",
        "p2p__order__": "orders",
        "p2p__state__": "state",
    }
    capabilities = {
        "market": True,
        "position": False,
        "orders": False,
        "trades": False,
        "equity": False,
        "features": False,
        "signals": False,
        "rejections": False,
    }
    for title, plot in result.get("plots", {}).items():
        category = None
        field = None
        for prefix, target in prefix_map.items():
            if title.startswith(prefix):
                category = target
                field = title[len(prefix) :].replace("__", ".")
                break
        if not category or not field:
            continue
        capability = {
            "state": "position",
            "orders": "orders",
        }.get(category, category)
        capabilities[capability] = True
        for point in plot.get("data", []):
            time_ms = int(point.get("time", -1))
            if time_ms in rows_by_time:
                rows_by_time[time_ms][category][field] = point.get("value")
    strategy = result.get("strategy") or {}
    for trade in strategy.get("closedtrades", []):
        entry_time = int(trade.get("entry_time", -1))
        exit_time = int(trade.get("exit_time", -1))
        direction = "long" if float(trade.get("size", 0)) >= 0 else "short"
        if entry_time in rows_by_time:
            rows_by_time[entry_time]["events"]["entries"].append(
                {
                    "id": trade.get("id"),
                    "entry_id": trade.get("entry_id"),
                    "direction": direction,
                    "price": trade.get("entry_price"),
                    "quantity": abs(float(trade.get("size", 0))),
                }
            )
        if exit_time in rows_by_time:
            rows_by_time[exit_time]["events"]["exits"].append(
                {
                    "id": trade.get("id"),
                    "exit_id": trade.get("exit_id"),
                    "direction": direction,
                    "price": trade.get("exit_price"),
                    "quantity": abs(float(trade.get("size", 0))),
                    "profit": trade.get("profit"),
                }
            )
    if strategy.get("closedtrades"):
        capabilities["trades"] = True
        capabilities["orders"] = True
    return {
        "schema_version": "1.0",
        "engine_id": "pinets-0.9.29",
        "rows": [rows_by_time[key] for key in sorted(rows_by_time)],
        "capabilities": capabilities,
    }


def execute_pine(
    source: str,
    candles: list[Candle],
    *,
    service_settings: Settings,
    analysis_source: str | None = None,
    symbol: str = "CUSTOM",
    timeframe: str = "1",
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    analysis = analyze_source(
        analysis_source or source,
        max_source_bytes=service_settings.max_source_bytes,
    )
    blockers = analysis["capabilities"]["runtime_blockers"]
    if blockers:
        raise Pine2PythonError(
            "LOCAL_RUNTIME_UNSUPPORTED",
            "The source contains constructs outside the configured network-free runtime subset.",
            {"blockers": blockers},
            422,
        )
    if len(candles) > service_settings.max_bars:
        raise Pine2PythonError(
            "BAR_LIMIT_EXCEEDED",
            f"Runtime request exceeds {service_settings.max_bars} bars.",
            {"bars": len(candles), "limit": service_settings.max_bars},
            413,
        )
    if not candles:
        raise Pine2PythonError("EMPTY_CANDLES", "Runtime request has no candles.")
    service_settings.ensure_dirs()
    timeout = timeout_seconds or service_settings.worker_timeout_seconds
    with tempfile.TemporaryDirectory(
        prefix="p2p-worker-", dir=service_settings.work_root
    ) as temp_name:
        temp_dir = Path(temp_name)
        request_path = temp_dir / "request.json"
        result_path = temp_dir / "result.json"
        request_path.write_text(
            json.dumps(
                {
                    "source": source,
                    "candles": [candle.model_dump() for candle in candles],
                    "symbol": symbol,
                    "timeframe": timeframe,
                },
                separators=(",", ":"),
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        # Node on Windows needs SystemRoot and other process environment values
        # for cryptographic initialization. Preserve the host environment while
        # disabling proxy discovery; network isolation is enforced by the
        # container/network boundary and the runtime capability gate.
        environment = os.environ.copy()
        environment.update(
            {
                "NODE_ENV": "production",
                "NO_PROXY": "*",
                "HTTP_PROXY": "",
                "HTTPS_PROXY": "",
                "ALL_PROXY": "",
            }
        )
        try:
            process = subprocess.run(
                [
                    service_settings.node_bin,
                    str(service_settings.worker_path),
                    str(request_path),
                    str(result_path),
                ],
                cwd=temp_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise Pine2PythonError(
                "RUNTIME_TIMEOUT",
                f"Pine runtime exceeded {timeout:.3f} seconds.",
                {"timeout_seconds": timeout},
                408,
            ) from exc
        if (
            len(process.stdout.encode("utf-8")) > 1_000_000
            or len(process.stderr.encode("utf-8")) > 1_000_000
        ):
            raise Pine2PythonError(
                "WORKER_LOG_LIMIT",
                "Pine runtime log output exceeded the configured safety limit.",
                status_code=413,
            )
        if not result_path.exists():
            raise Pine2PythonError(
                "RUNTIME_RESULT_MISSING",
                "Pine runtime exited without a result artifact.",
                {
                    "exit_code": process.returncode,
                    "stderr": process.stderr[-4000:],
                },
                502,
            )
        if result_path.stat().st_size > service_settings.max_worker_output_bytes:
            raise Pine2PythonError(
                "WORKER_OUTPUT_LIMIT",
                "Pine runtime result exceeded the configured safety limit.",
                {
                    "bytes": result_path.stat().st_size,
                    "limit": service_settings.max_worker_output_bytes,
                },
                413,
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if process.returncode != 0 or "error" in result:
            raise Pine2PythonError(
                "RUNTIME_FAILED",
                result.get("error", {}).get(
                    "message", "PineTS worker returned a failure."
                ),
                {
                    "exit_code": process.returncode,
                    "runtime_error": result.get("error"),
                    "stderr": process.stderr[-4000:],
                },
                422,
            )
        result["analysis_status"] = analysis["status"]
        result["trace"] = _standardize_runtime_trace(result, candles)
        result["status"] = [
            "LOCAL_RUNTIME_SUPPORTED",
            "LOCAL_RUNTIME_COMPLETE",
            "TRADINGVIEW_REVIEW_REQUIRED",
        ]
        return result
