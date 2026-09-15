from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from smart_money_4_clean import Bar, evaluate, event_accounting

ROOT = Path(__file__).resolve().parents[2]


def data_quality(bars: list[Bar], *, timezone_verified: bool, continuous_utc: bool) -> dict[str, Any]:
    """Data-quality gate, not a session calendar inferred from missing candles."""
    timestamps = [int(bar.ts.timestamp()) for bar in bars]
    groups: dict[int, list[int]] = defaultdict(list)
    for stamp in timestamps:
        groups[stamp // 14_400].append(stamp)
    keys = sorted(groups)
    rejected = [key for key, group in groups.items()
                if group != [key * 14_400 + 900 * offset for offset in range(16)]]
    interior = [key for key in rejected if key not in {keys[0], keys[-1]}]
    gaps = [(a, b) for a, b in zip(timestamps, timestamps[1:]) if b - a != 900]
    malformed = sum(not all(math.isfinite(value) for value in (bar.open, bar.high, bar.low, bar.close, bar.volume))
                    or bar.high < max(bar.open, bar.low, bar.close)
                    or bar.low > min(bar.open, bar.close) or bar.volume < 0 for bar in bars)
    passed = timezone_verified and continuous_utc and not gaps and not interior and not malformed
    return {
        "status": "CONTINUOUS_UTC_INPUT_CHECK_PASS" if passed else "PROVISIONAL_SESSION_OR_TIMEZONE_UNVERIFIED",
        "timezone_verified": timezone_verified, "session_alignment_verified": continuous_utc and not gaps,
        "duplicate_timestamps": len(timestamps) - len(set(timestamps)), "malformed_ohlcv": malformed,
        "non_15m_gaps": len(gaps), "four_hour_bucket_sizes": dict(Counter(map(len, groups.values()))),
        "legacy_fixed16_discarded_interior_buckets": len(interior),
        "gap_examples": [{"before_ms": a * 1000, "after_ms": b * 1000, "missing_slots": (b-a)//900-1} for a,b in gaps[:5]],
        "native_htf_required_for_parity": not passed,
        "input_data_gate_pass": passed,
        "note": "UTC labels in an imported CSV do not verify the original MT5 server timezone. Short buckets may be legitimate sessions or missing data; neither is inferred here.",
    }


def load_csv(path: Path, limit: int) -> list[Bar]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))[-limit:]
    return [
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
        for row in rows
    ]


def metrics(setups: list[Any], *, bps_per_side: float = 0.0) -> dict[str, Any]:
    returns: list[float] = []
    tp = sl = 0
    for setup in setups:
        if setup.state not in {2, 3}:
            continue
        risk = abs(setup.entry - setup.stop)
        if risk <= 0:
            continue
        cost_r = 2.0 * bps_per_side / 10_000.0 * setup.entry / risk
        tp += setup.state == 2
        sl += setup.state == 3
        returns.append((abs(setup.target - setup.entry) / risk if setup.state == 2 else -1.0) - cost_r)
    resolved = len(returns)
    wins = sum(value > 0 for value in returns)
    # Descriptive binomial interval only; serially dependent trades need separate validation.
    z = 1.96
    p = wins / resolved if resolved else 0.0
    center = (p + z*z/(2*resolved))/(1+z*z/resolved) if resolved else 0.0
    margin = z*math.sqrt(p*(1-p)/resolved+z*z/(4*resolved*resolved))/(1+z*z/resolved) if resolved else 0.0
    gross_profit = sum(value for value in returns if value > 0)
    gross_loss = -sum(value for value in returns if value < 0)
    return {
        "setups": len(setups),
        "long": sum(setup.direction == 1 for setup in setups),
        "short": sum(setup.direction == -1 for setup in setups),
        "resolved": resolved,
        "tp": tp,
        "sl": sl,
        "pending_or_open": sum(setup.state in {0, 1} for setup in setups),
        "missed_or_invalid": sum(setup.state == 4 for setup in setups),
        "ambiguous": sum(setup.state == 5 for setup in setups),
        "win_rate_pct": round(100.0 * sum(value > 0 for value in returns) / resolved, 3) if resolved else None,
        "tp_rate_pct": round(100.0 * tp / resolved, 3) if resolved else None,
        "win_rate_wilson95_descriptive_pct": [round(100*(center-margin), 2), round(100*(center+margin), 2)] if resolved else None,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
        "expectancy_r": round((gross_profit - gross_loss) / resolved, 4) if resolved else None,
    }


def cohort_report(rows: list[dict[str, Any]], setups: list[Any]) -> dict[str, Any]:
    cohorts: dict[str, list[Any]] = defaultdict(list)
    for setup in setups:
        features = rows[setup.ready]["features"]
        cohorts[f"direction:{'long' if setup.direction == 1 else 'short'}"].append(setup)
        cohorts[f"missing:{setup.missing}"].append(setup)
        cohorts[f"sweep:{bool(features['sweep'])}"].append(setup)
        cohorts[f"imbalance:{bool(features['imbalance'])}"].append(setup)
        cohorts[f"htf:{bool(features['htf'])}"].append(setup)
    return {name: metrics(items) for name, items in sorted(cohorts.items())}


def evaluate_window(bars: list[Bar], structure_mode: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    rows, setups = evaluate(bars, [], structure_mode=structure_mode, event_audit=events)
    midpoint = len(bars) // 2
    # Segment by readiness while preserving identical pre-split structural state.
    # These reused research windows are diagnostics, not an untouched holdout.
    first_setups = [setup for setup in setups if setup.ready < midpoint]
    second_setups = [setup for setup in setups if setup.ready >= midpoint]
    candidates = [row for row in rows if row["signals"]["candidate_updated"]]
    endpoint_failures = [row for row in candidates if
        (row["features"]["direction"] == 1 and row["features"]["target"] <= row["features"]["bos_level"])
        or (row["features"]["direction"] == -1 and row["features"]["target"] >= row["features"]["bos_level"])]
    failed_times = {row["time"] for row in endpoint_failures}
    affected_setups = [setup for setup in setups if rows[setup.ready]["time"] in failed_times]
    return {
        "identity": {
            "symbol": bars[0].symbol,
            "timeframe": bars[0].timeframe,
            "bars": len(bars),
            "start": bars[0].ts.isoformat(),
            "end": bars[-1].ts.isoformat(),
        },
        "gross": metrics(setups),
        "event_accounting": event_accounting(events, rows),
        "setups_per_calendar_week": round(len(setups) / max((bars[-1].ts-bars[0].ts).total_seconds()/604800, 1/7), 3),
        "cost_stress_bps_per_side": {
            str(bps): metrics(setups, bps_per_side=bps) for bps in (2, 5, 10)
        },
        "chronological_halves": {
            "first": metrics(first_setups),
            "second_diagnostic": metrics(second_setups),
        },
        "cohorts": cohort_report(rows, setups),
        "range_diagnostics": {
            "candidates": len(candidates),
            "endpoint_not_beyond_broken_level": len(endpoint_failures),
            "affected_setups": metrics(affected_setups),
            "examples": [{"bar_open_ms": row["time"], "direction": row["features"]["direction"],
                          "bos_level": row["features"]["bos_level"], "target": row["features"]["target"],
                          "score": row["features"]["score"]} for row in endpoint_failures[:3]],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    datasets = {
        "btc_reference": ("ds_207c4624f554.csv", 5_000),
        "btc_older": ("ds_42d92b3cda9f.csv", 20_000),
        "xauusd": ("ds_77827283d58c.csv", 20_000),
    }
    report = {}
    for name, (filename, limit) in datasets.items():
        bars = load_csv(ROOT / "artifacts" / "data" / filename, limit)
        report[name] = {
            mode: evaluate_window(bars, mode)
            for mode in ("arrays", "v6_endpoint", "v6_sweep", "hierarchical", "protected_owner")
        }
        for result in report[name].values():
            result["identity"]["dataset_file_sha256"] = hashlib.sha256((ROOT / "artifacts" / "data" / filename).read_bytes()).hexdigest()
            result["limitations"] = ["OHLC indicator lifecycle, not broker fills", "POC disabled; no 1m profile required for four-check scoring", "Costs are stress assumptions, not venue quotations", "Reused research windows; no untouched holdout"]
            result["data_quality"] = data_quality(bars, timezone_verified=name != "xauusd", continuous_utc=name != "xauusd")
            result["verdict"] = "DESCRIPTIVE_ONLY_NOT_AN_EDGE_ACCEPTANCE" if name != "xauusd" else "PROVISIONAL_UNVERIFIED_GOLD_FEED_AND_SESSION"
    if args.write:
        output = ROOT / "artifacts/strategy-development/smart-money-4-btcusdt-15m/viability_report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({name: {mode: {key: result[key] for key in ("gross", "event_accounting", "verdict")}
                            for mode, result in variants.items()} for name, variants in report.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
