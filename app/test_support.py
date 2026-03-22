from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from app.infra.config import build_config


def make_test_config(root: Path):
    return build_config(
        {
            "root_dir": root,
            "app_db_path": root / "artifacts" / "strategy_lab.duckdb",
            "app_data_dir": root / "artifacts" / "data",
            "app_run_dir": root / "artifacts" / "runs",
            "app_report_dir": root / "artifacts" / "reports",
            "app_graveyard_dir": root / "artifacts" / "graveyard",
            "strategies_dir": root / "strategies" / "families",
            "ui_dir": root / "app" / "ui",
        }
    )


def write_ui_files(config) -> None:
    config.ui_dir.mkdir(parents=True, exist_ok=True)
    (config.ui_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    (config.ui_dir / "app.js").write_text("console.log('ok');\n", encoding="utf-8")


def write_strategy_family(config, family_id: str, timeframe: str) -> None:
    family_dir = config.strategies_dir / family_id
    family_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "family_id": family_id,
        "title": family_id,
        "class_type": "white_box",
        "class_description": "test strategy",
        "asset": "BTCUSDT",
        "timeframe": timeframe,
        "supported_timeframes": [timeframe],
        "min_bars_by_timeframe": {timeframe: 120},
        "parameters": {"lookback_days": 5, "range_multiplier": 1.18, "age_threshold_bars": 40},
        "risk": {"risk_per_trade": 0.01},
        "gates": {"sharpe_keep": 1.25},
        "optimization_grid": {"lookback_days": [5, 10], "range_multiplier": [1.15, 1.18]},
        "rules": {"same_bar_rule": "stop_first"},
        "notes_path": f"strategies/families/{family_id}/notes.md",
    }
    if family_id == "smart_money_structural":
        manifest["parameters"] = {
            "displacement_requirement_atr": 1.0,
            "entry_retrace_level": 0.618,
            "htf_fractal_depth": 5,
            "htf_pd_filter": True,
            "htf_timeframe": "1H",
            "min_rr_target": 2.5,
            "mss_confirmation_type": "strict",
            "sweep_min_atr": 0.2,
            "stop_loss_padding_atr": 0.2,
            "take_profit_logic": "opposing_liquidity_pool",
        }
        manifest["optimization_grid"] = {
            "displacement_requirement_atr": [0.8, 1.2],
            "entry_retrace_level": [0.5, 0.705],
            "htf_fractal_depth": [3, 5],
            "min_rr_target": [2.0, 2.5],
            "stop_loss_padding_atr": [0.1, 0.3],
        }
        manifest["rules"]["killzone_buffer_minutes"] = 15
        manifest["rules"]["cancel_order_on_session_close"] = True
        manifest["rules"]["killzone_profile"] = "crypto"
        manifest["rules"]["news_filter_mode"] = "cancel_pending"
        manifest["rules"]["trade_min_duration_bars"] = 1
    (family_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (family_dir / "notes.md").write_text(f"{family_id}\n", encoding="utf-8")


def write_csv(path: Path, timeframe: str) -> None:
    rows = synthetic_rows(timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)


def synthetic_rows(timeframe: str) -> list[dict]:
    count = 1800 if timeframe == "1H" else 2000 if timeframe == "5m" else 600
    step = 3600 if timeframe == "1H" else 300
    start = 1_700_000_000
    if timeframe == "5m":
        start = int(datetime(2023, 11, 14, 12, 0, tzinfo=timezone.utc).timestamp())
    rows: list[dict] = []
    for index in range(count):
        base = 30000 + index * (4 if timeframe == "1H" else 0.3) + math.sin(index / 9) * 200
        close = base + math.sin(index / 4) * 70
        rows.append(
            {
                "timestamp": start + index * step,
                "open": round(base, 4),
                "high": round(max(base, close) + 45, 4),
                "low": round(min(base, close) - 45, 4),
                "close": round(close, 4),
                "volume": round(100 + (index % 12) * 4.5, 4),
            }
        )
        if timeframe == "5m":
            cycle = index % 120
            if cycle == 30 and len(rows) >= 6:
                prior_lows = [item["low"] for item in rows[-6:-1]]
                rows[-1]["low"] = round(min(prior_lows) - 30, 4)
                rows[-1]["close"] = round(rows[-2]["low"] + 12, 4)
                rows[-1]["open"] = round(rows[-2]["close"] - 18, 4)
                rows[-1]["high"] = round(max(rows[-1]["open"], rows[-1]["close"]) + 20, 4)
            if cycle == 31 and len(rows) >= 3:
                two_back_high = rows[-3]["high"]
                prev_high = rows[-2]["high"]
                rows[-1]["open"] = round(prev_high + 20, 4)
                rows[-1]["low"] = round(two_back_high + 8, 4)
                rows[-1]["close"] = round(rows[-1]["open"] + 60, 4)
                rows[-1]["high"] = round(rows[-1]["close"] + 18, 4)
                rows[-1]["volume"] = round(rows[-1]["volume"] * 1.8, 4)
            if cycle == 32 and len(rows) >= 3:
                gap_bottom = rows[-3]["high"]
                gap_top = rows[-2]["low"]
                retrace = gap_bottom + (gap_top - gap_bottom) * 0.5
                rows[-1]["open"] = round(rows[-2]["close"] - 8, 4)
                rows[-1]["high"] = round(max(rows[-1]["open"], retrace + 5), 4)
                rows[-1]["low"] = round(min(rows[-1]["open"], retrace - 5), 4)
                rows[-1]["close"] = round(retrace, 4)
            if cycle == 78 and len(rows) >= 6:
                prior_highs = [item["high"] for item in rows[-6:-1]]
                rows[-1]["high"] = round(max(prior_highs) + 30, 4)
                rows[-1]["close"] = round(rows[-2]["high"] - 12, 4)
                rows[-1]["open"] = round(rows[-2]["close"] + 18, 4)
                rows[-1]["low"] = round(min(rows[-1]["open"], rows[-1]["close"]) - 20, 4)
            if cycle == 79 and len(rows) >= 3:
                two_back_low = rows[-3]["low"]
                prev_low = rows[-2]["low"]
                rows[-1]["open"] = round(prev_low - 20, 4)
                rows[-1]["close"] = round(rows[-1]["open"] - 60, 4)
                rows[-1]["high"] = round(max(rows[-1]["open"], rows[-1]["close"]) + 10, 4)
                rows[-1]["low"] = round(min(two_back_low - 8, rows[-1]["close"] - 18), 4)
                rows[-1]["volume"] = round(rows[-1]["volume"] * 1.8, 4)
            if cycle == 80 and len(rows) >= 3:
                gap_top = rows[-3]["low"]
                gap_bottom = rows[-2]["high"]
                retrace = gap_top - (gap_top - gap_bottom) * 0.5
                rows[-1]["open"] = round(rows[-2]["close"] + 8, 4)
                rows[-1]["high"] = round(max(rows[-1]["open"], retrace + 5), 4)
                rows[-1]["low"] = round(min(rows[-1]["open"], retrace - 5), 4)
                rows[-1]["close"] = round(retrace, 4)
    return rows
