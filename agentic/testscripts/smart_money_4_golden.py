from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from smart_money_4_clean import Bar, NativeHtfBar, completed_htf_context, evaluate, event_accounting
from smart_money_4_viability import data_quality
from pine2python.models import ProofRequest
from pine2python.proof import create_proof

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = (
    ROOT
    / "artifacts"
    / "strategy-development"
    / "smart-money-4-btcusdt-15m"
    / "golden_case_manifest.json"
)

DATASETS = {
    "BTCUSDT": ("ds_42d92b3cda9f.csv", 20_000),
    "XAUUSD": ("ds_77827283d58c.csv", 20_000),
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


def event_key(row: dict[str, Any]) -> tuple[int, int] | None:
    direction = int(bool(row["signals"]["bull_break"])) - int(
        bool(row["signals"]["bear_break"])
    )
    return (row["time"], direction) if direction else None


def ownership_key(event: dict[str, Any]) -> tuple[Any, ...]:
    return (event["event_open_ms"], event["direction"], event["owner_source_ms"],
            event["owner_known_ms"], event["broken_level"])


def candidate_case(
    case_id: str,
    bars: list[Bar],
    row: dict[str, Any],
    classification: str,
) -> dict[str, Any]:
    features = row["features"]
    ready = next(i for i, bar in enumerate(bars) if int(bar.ts.timestamp() * 1000) == row["time"])
    return {
        "case_id": case_id,
        "classification": classification,
        "review_status": "PENDING_EXPERT",
        "symbol": bars[0].symbol,
        "timeframe": bars[0].timeframe,
        "candidate_time": bars[ready].ts.isoformat(),
        "candidate_known_at_close": (bars[ready].ts + timedelta(minutes=15)).isoformat(),
        "setup_ready_time": (bars[ready].ts + timedelta(minutes=15)).isoformat() if row["signals"]["setup_ready"] else None,
        "eligible_setup": bool(row["signals"]["setup_ready"]),
        "terminal": "SETUP_READY" if row["signals"]["setup_ready"] else row["rejections"]["code"],
        "timestamp_convention": "bar-open locators; committed events available at that bar's close",
        "direction": "LONG" if features["direction"] == 1 else "SHORT",
        "bos_kind": "CHOCH" if features["bos_kind"] == 2 else "BOS",
        "owner_role": "PROTECTED" if features["owner_role"] == 2 else "PENDING",
        "owner_source_time": (
            bars[features["owner_source"]].ts.isoformat()
            if features["owner_source"] is not None
            else None
        ),
        "owner_known_time": (
            (bars[features["owner_known"]].ts + timedelta(minutes=15)).isoformat()
            if features["owner_known"] is not None
            else None
        ),
        "sweep_time": (
            bars[features["sweep_bar"]].ts.isoformat()
            if features["sweep_bar"] is not None
            else None
        ),
        "bos_time": (
            bars[features["bos_bar"]].ts.isoformat()
            if features["bos_bar"] is not None
            else None
        ),
        "range_start_time": (
            bars[features["range_start"]].ts.isoformat()
            if features["range_start"] is not None
            else None
        ),
        "range_end_time": (
            bars[features["range_end"]].ts.isoformat()
            if features["range_end"] is not None
            else None
        ),
        "bos_level": features["bos_level"],
        "sweep_level": features["sweep_level"],
        "entry": features["entry"],
        "stop": features["stop"],
        "target": features["target"],
        "score": features["score"],
        "missing": features["missing"],
        "selection_uses_outcome": False,
        "annotations": "MODEL_OBSERVATION_PENDING_REFERENCE_ADJUDICATION",
        "checks": {
            name: bool(features[name])
            for name in ("htf", "bos", "sweep", "imbalance", "poc_pass")
        },
    }


def structural_invariants(bars: list[Bar], rows: list[dict[str, Any]]) -> dict[str, bool]:
    event_rows = [row for row in rows if event_key(row)]
    candidate_rows = [row for row in rows if row["signals"]["candidate_updated"]]
    owner_known_before_break = all(
        row["structure"]["owner_known"] is not None
        and row["structure"]["owner_known"] <= index
        for index, row in enumerate(rows)
        if event_key(row)
    )
    owner_role_matches_kind = all(
        (row["structure"]["bos_kind"], row["structure"]["owner_role"])
        in {(1, 1), (2, 2)}
        for row in event_rows
    )
    one_direction_per_event = all(
        not (row["signals"]["bull_break"] and row["signals"]["bear_break"])
        for row in rows
    )
    causal_sweeps = True
    strict_reclaims = True
    causal_ranges = True
    for row in candidate_rows:
        features = row["features"]
        if features["sweep"]:
            sweep_index = features["sweep_bar"]
            bos_index = features["bos_bar"]
            level = features["sweep_level"]
            causal_sweeps &= bool(
                sweep_index is not None
                and bos_index is not None
                and sweep_index < bos_index
                and features["range_start"] == sweep_index
            )
            if sweep_index is not None and level is not None:
                sweep_bar = bars[sweep_index]
                strict_reclaims &= bool(
                    (features["direction"] == 1 and sweep_bar.low < level <= sweep_bar.close)
                    or (
                        features["direction"] == -1
                        and sweep_bar.high > level >= sweep_bar.close
                    )
                )
        causal_ranges &= bool(
            features["bos_bar"] is not None
            and features["range_end"] is not None
            and features["range_end"] > features["bos_bar"]
        )
    return {
        "events_exist": bool(event_rows),
        "candidates_exist": bool(candidate_rows),
        "owner_known_before_break": owner_known_before_break,
        "owner_role_matches_bos_kind": owner_role_matches_kind,
        "one_direction_per_event": one_direction_per_event,
        "sweep_precedes_opposite_bos": causal_sweeps,
        "strict_wick_reclaim": strict_reclaims,
        "range_endpoint_after_bos": causal_ranges,
    }


def sample_evenly(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not items or count <= 0:
        return []
    if count == 1:
        return [items[len(items) // 2]]
    if len(items) <= count:
        return items
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def audit_dataset(symbol: str, path: Path, limit: int) -> dict[str, Any]:
    bars = load_csv(path, limit)
    v7_audit: list[dict[str, Any]] = []
    protected_audit: list[dict[str, Any]] = []
    v7_rows, v7_setups = evaluate(bars, [], structure_mode="hierarchical", event_audit=v7_audit)
    protected_rows, protected_setups = evaluate(
        bars, [], structure_mode="protected_owner", event_audit=protected_audit
    )
    v7_events = {event_key(row) for row in v7_rows if event_key(row)}
    protected_events = {event_key(row) for row in protected_rows if event_key(row)}
    candidates = [
        row for row in protected_rows if row["signals"]["candidate_updated"]
    ]
    selected: list[tuple[str, dict[str, Any]]] = []
    for direction in (1, -1):
        ready = [row for row in candidates if row["signals"]["setup_ready"] and row["features"]["direction"] == direction]
        # Prefer all-four-check examples if they exist; never inspect future outcomes.
        best = max((row["features"]["score"] for row in ready), default=0)
        selected.extend(("ELIGIBLE_SETUP", row) for row in sample_evenly([r for r in ready if r["features"]["score"] == best], 1))
    rejected = [row for row in candidates if row["rejections"]["code"]]
    selected.extend(("REJECTED_CANDIDATE", row) for row in sample_evenly(rejected, 1))
    suspect = [row for row in candidates if row["features"]["direction"] * (row["features"]["target"] - row["features"]["bos_level"]) <= 0]
    selected.extend(("RANGE_ENDPOINT_DISPUTE", row) for row in sample_evenly(suspect, 1))
    positive_cases = [candidate_case(f"{symbol}-C{index+1:02d}", bars, row, kind) for index, (kind, row) in enumerate(selected)]
    protected_keys = {ownership_key(event) for event in protected_audit}
    v7_keys = {ownership_key(event) for event in v7_audit}
    v7_only = [event for event in v7_audit if ownership_key(event) not in protected_keys]
    sampled_v7_only = [event for direction in (1, -1) for event in sample_evenly([e for e in v7_only if e["direction"] == direction], 1)]
    suppressed_cases = [
        {
            "case_id": f"{symbol}-N{index + 1:02d}",
            "classification": "V7_OWNED_EVENT_ABSENT_OR_CHANGED_IN_V8",
            "review_status": "PENDING_EXPERT",
            "symbol": symbol,
            "timeframe": "15m",
            "event_time": datetime.fromtimestamp(event["event_open_ms"] / 1000, tz=UTC).isoformat(),
            "event_known_at_close": datetime.fromtimestamp(event["event_known_ms"] / 1000, tz=UTC).isoformat(),
            "direction": "LONG" if event["direction"] == 1 else "SHORT",
            "v7_event": event,
            "v8_same_time_events": [other for other in protected_audit if other["event_open_ms"] == event["event_open_ms"]],
            "selection_uses_outcome": False,
            "annotations": "ABSENCE_IS_NOT_PROOF_OF_A_DETECTOR_MISS",
        }
        for index, event in enumerate(sampled_v7_only)
    ]
    cases = positive_cases + suppressed_cases
    for case in cases:
        reference = case.get("candidate_time", case.get("event_time"))
        at = next(i for i, bar in enumerate(bars) if bar.ts == datetime.fromisoformat(reference))
        # Independent raw candle evidence, ending at the decision; outcomes hidden.
        case["candles"] = [{"time": bar.ts.isoformat(), "open": bar.open, "high": bar.high,
                            "low": bar.low, "close": bar.close} for bar in bars[max(0, at-119):at+1]]
    return {
        "identity": {
            "symbol": bars[0].symbol,
            "timeframe": bars[0].timeframe,
            "bars": len(bars),
            "start": bars[0].ts.isoformat(),
            "end": bars[-1].ts.isoformat(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        "event_counts": {
            "v7": len(v7_events),
            "protected_owner": len(protected_events),
            "same_time_and_direction": len(v7_events & protected_events),
            "v7_only": len(v7_events - protected_events),
            "protected_only": len(protected_events - v7_events),
        },
        "ownership_comparison": {
            "same_owned_events": len(v7_keys & protected_keys),
            "v7_only_owned_events": len(v7_keys - protected_keys),
            "v8_only_owned_events": len(protected_keys - v7_keys),
            "identity_fields": ["event_open_ms", "direction", "owner_source_ms", "owner_known_ms", "broken_level"],
        },
        "event_accounting": {"v7": event_accounting(v7_audit, v7_rows), "v8": event_accounting(protected_audit, protected_rows)},
        "event_ledger": {"v7": v7_audit, "v8": protected_audit},
        "data_quality": data_quality(bars, timezone_verified=symbol == "BTCUSDT", continuous_utc=symbol == "BTCUSDT"),
        "setup_counts": {
            "v7": len(v7_setups),
            "protected_owner": len(protected_setups),
            "protected_direction": dict(
                Counter("LONG" if setup.direction == 1 else "SHORT" for setup in protected_setups)
            ),
        },
        "invariants": structural_invariants(bars, protected_rows),
        "regressions": regression_checks(bars[:3000]),
        "adjudication_cases": cases,
    }


def regression_checks(bars: list[Bar], mode: str = "protected_owner") -> dict[str, bool]:
    rows, setups = evaluate(bars, [], structure_mode=mode)
    events: list[dict[str, Any]] = []
    audited_rows, audited_setups = evaluate(bars, [], structure_mode=mode, event_audit=events)
    first_event = next(i for i, row in enumerate(rows) if event_key(row))
    censored: list[dict[str, Any]] = []
    evaluate(bars[:first_event+1], [], structure_mode=mode, event_audit=censored)
    ceiling = 2 * max(bar.high for bar in bars)
    mirrored = [Bar(ts=bar.ts, open=ceiling-bar.open, high=ceiling-bar.low,
                    low=ceiling-bar.high, close=ceiling-bar.close,
                    volume=bar.volume, symbol=bar.symbol, timeframe=bar.timeframe)
                for bar in bars]
    mirror_rows, mirror_setups = evaluate(mirrored, [], structure_mode=mode)
    prefix_stable = True
    for stop in (len(bars)//3, 2*len(bars)//3):
        prefix, _ = evaluate(bars[:stop], [], structure_mode=mode)
        prefix_stable &= prefix == rows[:stop]
    return {
        "protected_event_mirror": all(a["signals"]["bull_break"] == b["signals"]["bear_break"] and a["signals"]["bear_break"] == b["signals"]["bull_break"] for a,b in zip(rows, mirror_rows, strict=True)),
        "protected_setup_mirror": [(s.ready,s.direction,s.state) for s in setups] == [(s.ready,-s.direction,s.state) for s in mirror_setups],
        "confirmed_prefix_stability": prefix_stable,
        "audit_does_not_change_decisions": rows == audited_rows and setups == audited_setups,
        "event_accounting_complete": event_accounting(events, audited_rows)["complete"],
        "window_end_is_censored_not_rejected": bool(censored) and censored[-1]["terminal"] == "WINDOW_END_UNRESOLVED",
    }


def data_contract_fixtures() -> dict[str, bool]:
    origin = datetime(2026, 1, 1, tzinfo=UTC)
    base = int(origin.timestamp() * 1000)
    native = [NativeHtfBar(base, base+14_400_000, 10, 5),
              NativeHtfBar(base+14_400_000, base+28_800_000, 20, 1),
              NativeHtfBar(base+28_800_000, base+39_600_000, 15, 4)]
    bars = [Bar(ts=origin+timedelta(minutes=minute), open=7, high=8, low=6, close=7,
                volume=1, symbol="TEST", timeframe="15m") for minute in (645,660,675)]
    actual = completed_htf_context(bars, 1, native)
    duplicate_rejected = overlap_rejected = False
    try:
        completed_htf_context([bars[0], bars[0]], 1)
    except ValueError:
        duplicate_rejected = True
    try:
        completed_htf_context(bars, 1, native + [native[-1]])
    except ValueError:
        overlap_rejected = True
    return {
        "shortened_native_candle_preserved": actual[1:] == [(20, 1), (20, 1)],
        "native_htf_not_available_before_close": actual[0] == (None, None),
        "native_prefix_stable": completed_htf_context(bars[:1], 1, native) == actual[:1],
        "duplicate_child_timestamps_rejected": duplicate_rejected,
        "overlapping_native_intervals_rejected": overlap_rejected,
    }


def render_casebook(report: dict[str, Any]) -> None:
    """Minimal static scientific charts; no indicator visuals or outcomes changed."""
    lines = ["# SmartMoney-4 decision review cases", "",
             "Model observations, NOT expert ground truth. Candles stop at the decision; future outcomes are hidden.",
             "For each case: confirm/correct the broken level, sweep validity, range anchors and earliest knowable setup time.",
             "Gold is provisional: original server timezone/feed and 4h session ownership are unverified.", ""]
    target = OUTPUT.parent / "golden-cases"
    target.mkdir(exist_ok=True)
    for dataset in report["datasets"].values():
        for case in dataset["adjudication_cases"]:
            candles = case["candles"]
            lo, hi = min(c["low"] for c in candles), max(c["high"] for c in candles)
            levels = [case.get(k) for k in ("entry", "stop", "target", "bos_level", "sweep_level")]
            levels.append(case.get("v7_event", {}).get("broken_level"))
            lo = min([lo] + [v for v in levels if v is not None])
            hi = max([hi] + [v for v in levels if v is not None])
            pad = max((hi-lo)*0.12, 0.01)
            lo, hi = lo-pad, hi+pad
            def y(price: float) -> float:
                return 55 + (hi-price)/(hi-lo)*330
            def x(index: int) -> float:
                return 45 + index*840/max(1, len(candles)-1)
            svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="435" viewBox="0 0 1060 435">',
                   '<rect width="1060" height="435" fill="#151b25"/>',
                   f'<text x="20" y="24" fill="#eeeeee" font-family="sans-serif" font-size="15">{html.escape(case["case_id"] + " | " + case["classification"] + " | " + case["direction"])}</text>']
            for i,candle in enumerate(candles):
                color = "#57b99b" if candle["close"] >= candle["open"] else "#df7781"
                svg.extend([f'<line x1="{x(i):.2f}" x2="{x(i):.2f}" y1="{y(candle["high"]):.2f}" y2="{y(candle["low"]):.2f}" stroke="{color}"/>',
                            f'<rect x="{x(i)-2:.2f}" y="{y(max(candle["open"],candle["close"])):.2f}" width="4" height="{max(1,abs(y(candle["open"])-y(candle["close"]))):.2f}" fill="{color}"/>'])
            for label_index,(name,color) in enumerate((("bos_level","#a4b9e8"),("sweep_level","#a4c8bf"),("entry","#d3bd6d"),("stop","#df7781"),("target","#57b99b"))):
                value = case.get(name)
                if name == "bos_level" and value is None:
                    value = case.get("v7_event", {}).get("broken_level")
                if value is not None:
                    svg.append(f'<line x1="45" x2="890" y1="{y(value):.2f}" y2="{y(value):.2f}" stroke="{color}" stroke-dasharray="4 5" opacity="0.65"/><text x="900" y="{70+label_index*23}" fill="{color}" font-family="sans-serif" font-size="11">{name} {value:.2f}</text>')
            svg.append(f'<text x="25" y="415" fill="#bbbbbb" font-family="sans-serif" font-size="12">{html.escape(candles[0]["time"])} — {html.escape(candles[-1]["time"])} | decision only; no future candles</text></svg>')
            (target / (case["case_id"] + ".svg")).write_text("\n".join(svg), encoding="utf-8")
            lines.extend([f'## {case["case_id"]}: {case["classification"]}', "",
                          f'![Decision candles](golden-cases/{case["case_id"]}.svg)', "",
                          f'- Direction: {case["direction"]}; score: {case.get("score", "not a locked candidate")}; missing: {case.get("missing", "see event ledger")}.',
                          f'- Candidate confirmed: {case.get("candidate_known_at_close", case.get("event_known_at_close"))}.',
                          f'- Candidate setup ready: {case.get("setup_ready_time") or "NO ready setup asserted for this case"}; comparison terminal: {case.get("v7_event", {}).get("terminal", "see event ledger")}.',
                          f'- Owner source/known: {case.get("owner_source_time", case.get("v7_event",{}).get("owner_source_ms"))} / {case.get("owner_known_time", case.get("v7_event",{}).get("owner_known_ms"))}.',
                          f'- Sweep/BOS: {case.get("sweep_time")} / {case.get("bos_time", case.get("event_time"))}.',
                          f'- Frozen range: {case.get("range_start_time")} → {case.get("range_end_time")}.',
                          f'- Checks: {json.dumps(case.get("checks", {}), sort_keys=True)}.',
                          '- Expert verdict: PENDING. Explain the first incorrect or missing primitive, not whether the later trade wins.', ""])
    (OUTPUT.parent / "golden_case_review.md").write_text("\n".join(lines), encoding="utf-8")


def source_fidelity() -> dict[str, Any]:
    parent = ROOT / "artifacts/strategy-development/pwb_f89ea6f3774a/pvr_dfe72cd3eeaccde22e6e/source.pine"
    child = ROOT / "pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine"
    before, after = parent.read_bytes(), child.read_bytes()
    regions = {}
    for name, start, end in (
        ("history_renderer", b"f_draw_history_setup(", b"bool bullBreakSignal = false"),
        ("downstream_range_profile_scoring_lifecycle_and_visuals", b"    bool lockLong =", None),
    ):
        a = before[before.index(start):before.index(end) if end else len(before)]
        b = after[after.index(start):after.index(end) if end else len(after)]
        regions[name] = {"unchanged": a == b, "parent_sha256": hashlib.sha256(a).hexdigest(), "child_sha256": hashlib.sha256(b).hexdigest()}
    return {"parent_sha256": hashlib.sha256(before).hexdigest(), "child_sha256": hashlib.sha256(after).hexdigest(), "regions": regions,
            "parent_lines": len(before.splitlines()), "child_lines": len(after.splitlines())}


def declared_signature_regression(proof_path: Path | None = None) -> dict[str, Any]:
    """Recompute the existing proof from today's evaluator, not its saved trace."""
    root = ROOT / "artifacts/strategy-development"
    current_hash = hashlib.sha256((ROOT / "pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine").read_bytes()).hexdigest()
    if proof_path is None:
        candidates = []
        for path in (root / "pwb_f89ea6f3774a").glob("*/proofs/*/proof.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                request_path = root / "pine2python-artifacts" / payload["artifact"]["artifact_path"] / "request.json"
                dashboard = payload.get("dashboard_values", {})
                if payload.get("identity", {}).get("source_sha256") == current_hash and request_path.exists() and dashboard.get("SIGNALS") and dashboard.get("FEATURES"):
                    candidates.append(path)
            except (OSError, KeyError, json.JSONDecodeError):
                continue
        proof_path = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None
    if proof_path is None:
        return {"matches": False, "reason": "Register this exact child first", "source_sha256": current_hash}
    evidence = json.loads(proof_path.read_text(encoding="utf-8"))
    request_path = root / "pine2python-artifacts" / evidence["artifact"]["artifact_path"] / "request.json"
    request = ProofRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    bars = [Bar(ts=datetime.fromtimestamp(c.time/1000, UTC), open=c.open, high=c.high,
                low=c.low, close=c.close, volume=c.volume, symbol="BTCUSDT", timeframe="15m")
            for c in request.candles]
    one = load_csv(ROOT / "artifacts/data/ds_1e4ab545aa12.csv", 1_000_000)
    rows, _ = evaluate(bars, [b for b in one if b.ts >= bars[0].ts])
    request = request.model_copy(update={"trace_rows": rows})
    actual = create_proof(request)["dashboard_values"]
    expected = evidence["dashboard_values"]
    return {"matches": actual == expected and current_hash == evidence["identity"]["source_sha256"], "proof_evidence_id": proof_path.parent.name,
            "dashboard_values": actual, "scope": "Existing declared fields only; new audit ledger is not in this proof."}


def sweep_source_fidelity() -> dict[str, Any]:
    parent_path = ROOT / "artifacts/strategy-development/pwb_f89ea6f3774a/pvr_122d076db526ae8f9628/source.pine"
    child_path = ROOT / "pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine"
    parent, child = parent_path.read_text(encoding="utf-8"), child_path.read_text(encoding="utf-8")
    helper = '''
var array<int> sweepLinkedBar = array.new_int()

// Fresh sweeps keep v6 priority. Reuse only the latest confirmed context when
// no fresh candidate fits this BOS; an old extreme cannot displace fresh evidence.
f_prefer_sweep(int candidate, int selected, int direction) =>
    bool better = na(selected)
    if not na(selected)
        int candidateLink = array.get(sweepLinkedBar, candidate)
        int selectedLink = array.get(sweepLinkedBar, selected)
        if na(candidateLink) != na(selectedLink)
            better := na(candidateLink)
        else if not na(candidateLink) and candidateLink != selectedLink
            better := candidateLink > selectedLink
        else
            float a = array.get(sweepExtreme, candidate)
            float b = array.get(sweepExtreme, selected)
            better := (direction == 1 ? a < b : a > b) or (a == b and array.get(sweepBar, candidate) > array.get(sweepBar, selected))
    better
'''
    expected = parent.replace("15m v6.1 Candidate", "15m v6.2 Candidate")
    changes = [
        ("// an opposite BOS causally consumes one. No fixed bar timeout changes meaning.",
         "// an opposite BOS links one without consuming it. Only market invalidation\n// ends validity; checklist outcomes never change the evidence pool."),
        ("var array<bool> sweepValid = array.new_bool()\n", "var array<bool> sweepValid = array.new_bool()\n" + helper.lstrip("\n")),
        ("bool sweepCandidateSignal = false", "bool sweepCandidateSignal = false\nbool sweepLinkedSignal = false\nint sweepInvalidatedCount = 0"),
        ("                    array.set(sweepValid, i, false)", "                    array.set(sweepValid, i, false)\n                    sweepInvalidatedCount += 1"),
        ("if array.get(sweepValid, j) and array.get(sweepDirection, j)", "if array.get(sweepValid, j) and na(array.get(sweepLinkedBar, j)) and array.get(sweepDirection, j)"),
        ("                    array.push(sweepValid, true)", "                    array.push(sweepValid, true)\n                    array.push(sweepLinkedBar, na)"),
        ("        array.remove(sweepValid, removeAt)", "        array.remove(sweepValid, removeAt)\n        array.remove(sweepLinkedBar, removeAt)"),
        ("            if linkedSweep\n                array.set(sweepValid, selectedSweep, false)", "            sweepLinkedSignal := linkedSweep\n            if linkedSweep\n                array.set(sweepLinkedBar, selectedSweep, bar_index)"),
    ]
    for op, direction in (("<",1),(">",-1)):
        changes.append((f"if causal and (na(selectedSweep) or array.get(sweepExtreme, i) {op} array.get(sweepExtreme, selectedSweep) or (array.get(sweepExtreme, i) == array.get(sweepExtreme, selectedSweep) and array.get(sweepBar, i) > array.get(sweepBar, selectedSweep)))", f"if causal and f_prefer_sweep(i, selectedSweep, {direction})"))
    for before, after in changes:
        assert before in expected, before
        expected = expected.replace(before, after)
    # v6.3 coverage/persistence child: these are the only intentional changes
    # beyond the frozen v6.2 sweep-context delta. Keep the source-fidelity test
    # explicit so future visual or semantic edits cannot hide in this child.
    v63_changes = [
        (
            'indicator("SmartMoney-4 Structural Memory 15m v6.2 Candidate",',
            'indicator("SmartMoney-4 Structural Memory 15m v6.3 Coverage Candidate",',
        ),
        (
            'fibChoice = input.string("75%", "Fibonacci entry", options=["71%", "75%"], group=GROUP_SETUP)',
            '// 71% is the coverage-oriented default from the source transcript. 75% remains\n// selectable for the stricter video variant; neither choice changes detection.\nfibChoice = input.string("71%", "Fibonacci entry", options=["71%", "75%"], group=GROUP_SETUP)',
        ),
        (
            '    int visualRightTime = na(exitTime) ? time : math.max(readyTime + 4 * BAR_MS, exitTime)',
            '    // A historical setup must have a deterministic finite right edge. Using the\n    // current realtime `time` made unfinished records stretch and disappear as\n    // the viewport moved; completed records still extend through their exit.\n    int visualRightTime = na(exitTime) ? readyTime + 4 * BAR_MS : math.max(readyTime + 4 * BAR_MS, exitTime)',
        ),
        (
            '// Full historical setup cards are materialized from the ledger once, so zoom,\n// Go-to-date, and history loading never own their existence. The automatic\n// cap fits Pine\'s drawing budgets; older events remain available in Reviewer.',
            '// Full historical eligible setup cards are materialized from the ledger once,\n// including pending, missed and open records. History must not depend on a\n// setup having filled: that hid valid source setups and made the chart appear\n// empty. The automatic cap fits Pine\'s drawing budgets; older events remain\n// available in Reviewer.',
        ),
        ('                int fillBar = array.get(setupFillBar, si)\n', ''),
        (
            'if historyDrawn < MAX_ARCHIVED_FULL_SETUPS and not na(fillBar) and setupCi != displayCandidateIndex',
            'if historyDrawn < MAX_ARCHIVED_FULL_SETUPS and setupCi != displayCandidateIndex',
        ),
    ]
    for before, after in v63_changes:
        assert before in expected, before
        expected = expected.replace(before, after)
    downstream = "    bool lockLong ="
    return {"only_declared_sweep_change": child == expected,
            # v6.3 intentionally changes the historical renderer below the
            # ledger/lifecycle section. Compare the semantic child only through
            # the renderer marker; the explicit v6.3 renderer delta is checked
            # by the coverage/history assertions in smart_money_4_clean.py.
            "downstream_scoring_lifecycle_visuals_unchanged": child[child.index(downstream):child.index("// Full historical eligible setup cards")]
            == parent[parent.index(downstream):parent.index("// Full historical setup cards")],
            "parent_lines":len(parent.splitlines()), "child_lines":len(child.splitlines())}


def sweep_regressions(bars: list[Bar]) -> dict[str, bool]:
    audit: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    rows, setups = evaluate(bars, [], sweep_audit=audit, event_audit=events)
    links = [x for x in audit if x["kind"] == "LINKED"]
    valid_links = all(x["level_index"] + 2 < x["bar"] < x["at"]
        and all(b.close >= x["level"] if x["direction"] == 1 else b.close <= x["level"]
                for b in bars[x["bar"]:x["at"]+1]) for x in links)
    snapshots = {x["at"]: x for x in links}
    frozen = all(all(e["sweep_snapshot"][k] == snapshots[e["event_bar"]][k]
                    for k in ("bar","level_index","level","extreme"))
                 for e in events if e.get("sweep_snapshot"))
    def market(r: dict[str, Any]) -> dict[str, Any]:
        return {k:v for k,v in r["features"].items() if k not in {"score","eligible","missing"}}
    mode_independent = True
    for poc, quality in ((False,"Perfect"),(True,"Standard"),(True,"Perfect")):
        other, _ = evaluate(bars, [], include_poc=poc, quality=quality)
        mode_independent &= all(market(x)==market(y) for x,y in zip(rows,other,strict=True))
    keys = [(s.direction,rows[s.ready]["features"]["bos_time"],
             rows[s.ready]["features"]["range_start"], rows[s.ready]["features"]["range_end"]) for s in setups]
    return {"no_market_invalidated_sweep_reused": valid_links,
            "linked_metadata_is_frozen": frozen,
            "checklist_mode_cannot_change_market_detection": mode_independent,
            "same_event_never_duplicated": len(keys)==len(set(keys)),
            "candidate_link_does_not_consume": not any(x["kind"]=="CONSUMED" for x in audit),
            "invalidation_and_link_paths_exercised": bool(links) and any(x["kind"]=="INVALIDATED" for x in audit),
            **regression_checks(bars,"v6_sweep")}


def recovery_report() -> dict[str, Any]:
    """Compare the sweep child with v6.1; retain v6 recovery measurements."""
    from smart_money_4_viability import metrics
    report: dict[str, Any] = {
        "status":"V6_3_COVERAGE_CANDIDATE_EXPERT_PENDING",
        "semantic_change":"Fresh v6 sweeps retain priority; latest still-valid linked manipulation is fallback, independent of scoring.",
        "parent_revision":"pvr_122d076db526ae8f9628",
        "source_sha256":hashlib.sha256((ROOT/"pre-strategies/smart-money-4/smart-money-4-clean-indicator.pine").read_bytes()).hexdigest(),
        "source_fidelity":sweep_source_fidelity(),
        "data_contract_fixtures":data_contract_fixtures(), "datasets":{}}
    def key(s: Any) -> tuple[Any,...]:
        return (s.direction,s.ready,s.entry,s.stop,s.target)
    expected_recoveries = {"BTCUSDT":["2026-04-12T13:30","2026-05-02T16:45"],
                           "XAUUSD":["2025-08-04T17:15","2025-12-24T18:15"]}
    for name,(filename,limit) in {"BTC_REFERENCE":("ds_207c4624f554.csv",5000),**DATASETS}.items():
        path=ROOT/"artifacts/data"/filename
        bars=load_csv(path,limit)
        base_events: list[dict[str,Any]]=[]
        events: list[dict[str,Any]]=[]
        sweeps: list[dict[str,Any]]=[]
        # The v6/v6.1/v6.2 lineage comparison is frozen at its historical 75%
        # setting. v6.3's 71% default is measured separately, not allowed to
        # masquerade as a structural sweep change in this regression.
        original, v6=evaluate(bars,[],structure_mode="arrays",fib_pct=0.75)
        before, old=evaluate(bars,[],structure_mode="v6_endpoint",fib_pct=0.75,event_audit=base_events)
        after, new=evaluate(bars,[],fib_pct=0.75,event_audit=events,sweep_audit=sweeps)
        old_keys,new_keys={key(s) for s in old},{key(s) for s in new}
        added=[s for s in new if key(s) not in old_keys]
        changed=[{"previous_ready_open":bars[s.ready].ts.isoformat(),"previous":before[s.ready]["features"],
                  "current":after[s.ready]["features"],"cause":"SWEEP_CONTEXT_REANCHORED","expert_verdict":"PENDING"}
                 for s in old if key(s) not in new_keys]
        recovered=[]
        for locator in expected_recoveries.get(name,[]):
            i=next(i for i,b in enumerate(bars) if b.ts.isoformat().startswith(locator))
            recovered.append({"locator":locator,"v6":original[i]["features"],"v6_1":before[i]["features"],"v6_2":after[i]["features"],
                              "restored_geometry":all(original[i]["features"][k]==after[i]["features"][k] for k in ("entry","stop","target","sweep_level")),
                              "eligible":after[i]["features"]["eligible"]})
        selected=[]
        for direction in (1,-1):
            choices=[s for s in added if s.direction==direction and not before[s.ready]["features"]["eligible"]]
            if choices: selected.append((choices[0].ready,"SWEEP_CONTEXT_RECOVERED"))
            kept=[s for s in new if s.direction==direction and key(s) in old_keys]
            if kept: selected.append((kept[0].ready,"V61_POSITIVE_PRESERVED"))
        for item in recovered:
            i=next(i for i,b in enumerate(bars) if b.ts.isoformat().startswith(item["locator"]))
            selected.append((i,"KNOWN_SUPPRESSION_RECOVERED"))
        missing=[i for i,r in enumerate(after) if r["signals"]["candidate_updated"] and not r["features"]["sweep"]]
        if missing: selected.append((missing[0],"NO_LINKED_SWEEP_NEGATIVE"))
        cases=[]
        for number,(i,classification) in enumerate(selected):
            case=candidate_case(f"{name}-V62-{number+1}",bars,after[i],classification)
            start=max(0,min(after[i]["features"]["range_start"],after[i]["features"]["owner_source"])-5)
            case["candles"]=[{"time":b.ts.isoformat(),"open":b.open,"high":b.high,"low":b.low,"close":b.close} for b in bars[start:i+1]]
            cases.append(case)
        raw=("raw_high_pivot","raw_low_pivot","sweep_candidate","bull_break","bear_break")
        checks={"raw_detection_unchanged":all(all(x["signals"][k]==y["signals"][k] for k in raw) for x,y in zip(before,after,strict=True)),
                "baseline_events_preserved":[ownership_key(e) for e in base_events]==[ownership_key(e) for e in events],
                "all_baseline_setups_accounted":len(old_keys & new_keys)+len(changed)==len(old),
                "no_baseline_eligibility_lost":all(x["current"]["eligible"] for x in changed),
                "known_four_cases_recovered":all(x["restored_geometry"] and x["eligible"] for x in recovered),
                "candidate_expansion":len(new)>len(old),
                "confirmation_delay_preserved":all(r["features"]["range_end"]+2==i for i,r in enumerate(after) if r["signals"]["candidate_updated"]),
                "no_same_bar_action":all(s.fill is None or s.fill>s.ready for s in new),
                **sweep_regressions(bars[:3000])}
        ignored=[e for e in events if e["terminal"]=="LEG_ALREADY_OWNED"]
        report["datasets"][name]={"dataset_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "gross":{"v6":metrics(v6),"v6_1":metrics(old),"v6_2":metrics(new)},
            "preserved_exact":len(old_keys & new_keys),"added_or_retimed":len(added),
            "changed_baseline":changed,"change_causes":dict(Counter(x["cause"] for x in changed)),
            "known_recoveries":recovered,"checks":checks,"adjudication_cases":cases,
            "sweep_audit":sweeps,"event_ledger":events,
            "ignored_bos_audit":{"count":len(ignored),"examples":ignored[:5],"verdict":"Not assumed invalid; separate continuous-window expert review required. No second detector change."},
            "event_accounting":{"v6_1":event_accounting(base_events,before),"v6_2":event_accounting(events,after)},
            "data_quality":data_quality(bars,timezone_verified=name!="XAUUSD",continuous_utc=name!="XAUUSD")}
    # Select the newest full proof for the exact current source hash. Do not
    # hard-code a v6.2 dashboard signature: the v6.3 71% default intentionally
    # changes the declared feature/signal fingerprints.
    report["declared_signature_regression"] = declared_signature_regression()
    report["code_invariants_pass"]=(all(report["source_fidelity"][k] for k in ("only_declared_sweep_change","downstream_scoring_lifecycle_visuals_unchanged"))
        and all(report["data_contract_fixtures"].values()) and report["declared_signature_regression"]["matches"]
        and all(all(d["checks"].values()) and all(e["complete"] for e in d["event_accounting"].values()) for d in report["datasets"].values()))
    report["acceptance"]="EXPERT_PENDING; economics diagnostic, not Phase 1 filtering objective"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--legacy-v8", action="store_true", help="Inspect the superseded v8 audit, not the current recovery candidate.")
    args = parser.parse_args()
    if not args.legacy_v8:
        report = recovery_report()
        if args.write:
            OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
            render_casebook(report)
        print(json.dumps({"code_invariants_pass":report["code_invariants_pass"],
                          "source_fidelity":report["source_fidelity"],
                          "declared_signature_regression":report["declared_signature_regression"],
                          "datasets":{name:{k:d[k] for k in ("gross","preserved_exact","added_or_retimed","change_causes","checks")} for name,d in report["datasets"].items()}}, indent=2))
        return 0 if report["code_invariants_pass"] else 1
    report = {
        "status": "PENDING_EXPERT_ADJUDICATION",
        "source_fidelity": source_fidelity(),
        "data_contract_fixtures": data_contract_fixtures(),
        "declared_signature_regression": declared_signature_regression(),
        "authority": {
            "transcript": "pre-strategies/smart-money-4/The ONLY 15 Minute Trading Strategy You Need in 2026/Transcript con timestamps.txt",
            "canonical_visuals": [
                {
                    "concept": "SHORT sweep, BOS, FVG and external range",
                    "transcript_window": "00:04:25-00:05:36",
                    "frame": "00-05-10.650.png",
                    "symbol": "GBPCAD",
                    "fixture_status": "VISUAL_ONLY_UNTIL_TIME_AND_FEED_ARE_EXACT",
                },
                {
                    "concept": "XAUUSD LONG sweep, BOS, 71/75 zone and POC",
                    "transcript_window": "00:06:38-00:08:13",
                    "frame": "00-07-21.670.png",
                    "symbol": "FXCM:XAUUSD", "visible_window": "2026-07-29, chart UTC-4",
                    "fixture_status": "EXACT_FEED_UNAVAILABLE_IN_CURRENT_TRADINGVIEW_SESSION",
                },
            ],
        },
        "datasets": {
            symbol: audit_dataset(
                symbol, ROOT / "artifacts" / "data" / filename, limit
            )
            for symbol, (filename, limit) in DATASETS.items()
        },
    }
    report["code_invariants_pass"] = all(
        all(dataset["invariants"].values()) and all(dataset["regressions"].values())
        and all(value["complete"] for value in dataset["event_accounting"].values())
        for dataset in report["datasets"].values()
    ) and all(region["unchanged"] for region in report["source_fidelity"]["regions"].values()) and all(report["data_contract_fixtures"].values()) and report["declared_signature_regression"]["matches"]
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        render_casebook(report)
    print(json.dumps({"code_invariants_pass": report["code_invariants_pass"],
                      "data_contract_fixtures": report["data_contract_fixtures"],
                      "datasets": {name: {key: value[key] for key in ("event_accounting", "ownership_comparison", "setup_counts", "data_quality")}
                                   for name, value in report["datasets"].items()},
                      "report_path": str(OUTPUT) if args.write else None}, indent=2, sort_keys=True))
    return 0 if report["code_invariants_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
