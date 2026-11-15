"""Bounded reference strategies and their shared, decision-independent broker.

Bar timestamps denote opens. References observe completed bars and submit market
intents no earlier than the following open. Neither registered strategy consumes
fills; adding fill-aware behavior requires a chronological feedback contract.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

from fastapi import HTTPException

from app.data import INTERVAL_MS, Bar

REFERENCE_ENGINES = {"reference_ma_cross_v1", "reference_pivot_bos_v1"}
EXECUTION_CONTRACT = {
    "entry": "next_bar_open",
    "sizing": "fixed_quantity_unconstrained",
    "stop": "static_atr_from_decision",
    "target": "risk_multiple_or_disabled",
    "ambiguity": "adverse_stop_first",
    "cutoff": "censored",
    "feedback": "decision_only",
    "parameter_resolution": "explicit_parameters_override_declared_defaults",
    "parameter_defaults": {
        "quantity": 1,
        "stop_mult": 2,
        "atr_len": 7,
        "initial_capital": 100000,
        "tick_size": 0.01,
        "commission_pct": 0,
        "slippage_ticks": 0,
        "target_r": 0,
        "max_gap_bars": 0,
    },
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def fail(code: str, message: str) -> None:
    raise HTTPException(422, detail={"code": code, "message": message})


def workflow(spec: dict) -> str:
    value = spec.get("workflow_version", "legacy_pine_v1")
    if value not in {"reference_v1", "legacy_pine_v1"}:
        fail("WORKFLOW_UNKNOWN", "Unknown workflow version.")
    return value


def effective_parameters(spec: dict) -> dict:
    """Resolve the same registered defaults for execution and authorization."""
    return {
        **EXECUTION_CONTRACT["parameter_defaults"],
        "fast_len": 5,
        "slow_len": 20,
        "min_atr": 0,
        "allow_long": True,
        "allow_short": True,
        "pivot_left": 2,
        "pivot_right": 2,
        "level_ttl": 100,
        "execution_model": "next_bar_open",
        "sizing_mode": "fixed_quantity",
        **spec.get("parameters", {}),
    }


def validate_spec(spec: dict) -> None:
    if (
        workflow(spec) != "reference_v1"
        or spec.get("engine_id") not in REFERENCE_ENGINES
    ):
        fail("REFERENCE_UNREGISTERED", "Choose a registered reference engine.")
    if spec.get("component_kind", "strategy") not in {"indicator", "strategy"}:
        fail("REFERENCE_COMPONENT", "component_kind must be indicator or strategy.")
    p = spec.get("parameters", {})
    if not isinstance(p, dict):
        fail("REFERENCE_PARAMETER", "parameters must be an object.")
    supported = {
        "fast_len",
        "slow_len",
        "atr_len",
        "quantity",
        "stop_mult",
        "initial_capital",
        "tick_size",
        "execution_model",
        "sizing_mode",
        "commission_pct",
        "slippage_ticks",
        "target_r",
        "min_atr",
        "max_gap_bars",
        "allow_long",
        "allow_short",
        "pivot_left",
        "pivot_right",
        "level_ttl",
    }
    if set(p) - supported:
        fail(
            "REFERENCE_PARAMETER_UNSUPPORTED",
            f"Unsupported parameters: {sorted(set(p) - supported)}",
        )
    for key in ("allow_long", "allow_short"):
        if key in p and not isinstance(p[key], bool):
            fail("REFERENCE_PARAMETER", f"{key} must be a boolean.")
    for key in ("slippage_ticks", "max_gap_bars"):
        if key in p and (isinstance(p[key], bool) or not isinstance(p[key], int)):
            fail("REFERENCE_PARAMETER", f"{key} must be an integer.")
    if (
        p.get("execution_model", "next_bar_open") != "next_bar_open"
        or p.get("sizing_mode", "fixed_quantity") != "fixed_quantity"
    ):
        fail(
            "REFERENCE_EXECUTION_UNSUPPORTED",
            "References support next_bar_open and fixed_quantity only.",
        )
    if spec.get("fill_aware", False):
        fail(
            "REFERENCE_FEEDBACK_UNSUPPORTED",
            "These controls are decision-only and do not consume broker feedback.",
        )
    for key, default in (
        ("quantity", 1),
        ("stop_mult", 2),
        ("initial_capital", 100000),
        ("tick_size", 0.01),
    ):
        value = p.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
            or value <= 0
        ):
            fail("REFERENCE_PARAMETER", f"{key} must be positive and finite.")
    for key in (
        "commission_pct",
        "slippage_ticks",
        "target_r",
        "min_atr",
        "max_gap_bars",
    ):
        value = p.get(key, 0)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            fail("REFERENCE_PARAMETER", f"{key} must be nonnegative and finite.")
    for key, default in (
        ("fast_len", 5),
        ("slow_len", 20),
        ("atr_len", 7),
        ("pivot_left", 2),
        ("pivot_right", 2),
        ("level_ttl", 100),
    ):
        value = p.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            fail("REFERENCE_PARAMETER", f"{key} must be a positive integer.")
    if p.get("fast_len", 5) >= p.get("slow_len", 20):
        fail("REFERENCE_PARAMETER", "fast_len must be smaller than slow_len.")


def audit_ledger(ledger: list[dict]) -> None:
    ids: set[str] = set()
    for event in ledger:
        if event["event_id"] in ids:
            fail("LEDGER_DUPLICATE", "Ledger event IDs must be unique.")
        ids.add(event["event_id"])
        clocks = [
            event[k]
            for k in (
                "source_at",
                "known_at",
                "decision_at",
                "earliest_submission",
                "fill_at",
            )
            if event.get(k) is not None
        ]
        if clocks != sorted(clocks):
            fail("CAUSALITY_VIOLATION", f"Invalid causal order in {event['event_id']}.")


def run_reference(
    spec: dict, observations: list[Bar], *, collect_ledger: bool = True
) -> dict:
    # Imports remain local to avoid a backtest/reference module cycle.
    from app.backtest import atr, compute_metrics, sma
    from app.data import audit_bars

    validate_spec(spec)
    quality = audit_bars(observations)
    if quality["status"] == "BLOCKED":
        fail(
            "REFERENCE_DATA_INVALID",
            "Raw observations have blocking integrity findings.",
        )
    if not observations:
        fail("REFERENCE_EMPTY", "Reference needs market observations.")
    bars = observations
    if any(
        b.timeframe != spec.get("timeframe", b.timeframe)
        or (spec.get("asset") and b.symbol != spec["asset"])
        for b in bars
    ):
        fail(
            "REFERENCE_DATA_CONTEXT",
            "Dataset symbol/timeframe differs from the declared reference.",
        )
    p = effective_parameters(spec)
    step = INTERVAL_MS.get(spec.get("timeframe", bars[0].timeframe))
    if step is None:
        fail("REFERENCE_TIMEFRAME", "Unsupported reference timeframe.")
    opens = [int(b.ts.timestamp() * 1000) for b in bars]
    closes = [t + step for t in opens]
    if any(opens[i] < closes[i - 1] for i in range(1, len(opens))):
        fail("REFERENCE_OVERLAP", "Observations overlap their declared timeframe.")
    ledger: list[dict] = []
    decisions: list[dict] = []
    intents: list[dict] = []
    features: list[dict] = []

    def emit(
        kind: str,
        i: int,
        reason: str,
        *,
        source: int | None = None,
        known: int | None = None,
        before: Any = None,
        after: Any = None,
        intent: str | None = None,
        **extra: Any,
    ) -> None:
        ledger.append(
            copy.deepcopy(
                {
                    "event_id": f"e{len(ledger):07d}",
                    "event_type": kind,
                    "rule_id": spec["engine_id"],
                    "bar_index": i,
                    "source_at": closes[i] if source is None else source,
                    "known_at": closes[i] if known is None else known,
                    "decision_at": closes[i],
                    "prior_state": before,
                    "next_state": after,
                    "reason": reason,
                    "intent_id": intent,
                    "evidence": [f"bar:{i}"],
                    **extra,
                }
            )
        )

    atr_values = atr(bars, p.get("atr_len", 7))
    fast = sma([b.close for b in bars], p.get("fast_len", 5))
    slow = sma([b.close for b in bars], p.get("slow_len", 20))
    levels: dict[int, dict] = {}
    for i, bar in enumerate(bars):
        feature: dict = {"atr": atr_values[i]}
        direction = 0
        source_at = closes[i]
        known_at = closes[i]
        if spec["engine_id"] == "reference_ma_cross_v1":
            feature.update(fast=fast[i], slow=slow[i])
            if i and None not in (fast[i], slow[i], fast[i - 1], slow[i - 1]):
                if fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]:
                    direction = 1
                elif fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]:
                    direction = -1
        else:
            left, right = p.get("pivot_left", 2), p.get("pivot_right", 2)
            pivot = i - right
            if pivot >= left:
                for side in (1, -1):
                    price = bars[pivot].high if side == 1 else bars[pivot].low
                    others = [
                        bars[j].high if side == 1 else bars[j].low
                        for j in range(pivot - left, i + 1)
                        if j != pivot
                    ]
                    if all(price > v if side == 1 else price < v for v in others):
                        old = levels.get(side)
                        if old:
                            emit(
                                "invalidated",
                                i,
                                "level_replaced",
                                source=old["source_at"],
                                known=old["known_at"],
                                before=old,
                            )
                        levels[side] = {
                            "price": price,
                            "source_at": closes[pivot],
                            "known_at": closes[i],
                            "confirmed_index": i,
                        }
                        emit(
                            "confirmed",
                            i,
                            "pivot_confirmed",
                            source=closes[pivot],
                            after=levels[side],
                        )
            for side, level in list(levels.items()):
                if i - level["confirmed_index"] > p.get("level_ttl", 100):
                    emit(
                        "expired",
                        i,
                        "level_expired",
                        source=level["source_at"],
                        known=level["known_at"],
                        before=level,
                    )
                    del levels[side]
                elif i > level["confirmed_index"] and (
                    bar.close > level["price"]
                    if side == 1
                    else bar.close < level["price"]
                ):
                    direction, source_at, known_at = (
                        side,
                        level["source_at"],
                        level["known_at"],
                    )
                    emit(
                        "consumed",
                        i,
                        "close_bos",
                        source=source_at,
                        known=known_at,
                        before=level,
                    )
                    del levels[side]
                    break
            feature.update(
                {
                    "pivot_high": levels.get(1, {}).get("price"),
                    "pivot_low": levels.get(-1, {}).get("price"),
                }
            )
        features.append(feature)
        if direction:
            allowed = (
                p.get("allow_long", True)
                if direction == 1
                else p.get("allow_short", True)
            )
            reason = (
                "accepted"
                if allowed
                and atr_values[i] is not None
                and atr_values[i] > 0
                and atr_values[i] >= p.get("min_atr", 0)
                else "direction_disabled"
                if not allowed
                else "atr_gate"
            )
            decision = {
                "bar_index": i,
                "direction": direction if reason == "accepted" else 0,
                "reason": reason,
            }
            decisions.append(decision)
            intent_id = (
                f"intent:{i}:{direction}"
                if reason == "accepted"
                and spec.get("component_kind", "strategy") == "strategy"
                else None
            )
            emit(
                "accepted" if reason == "accepted" else "rejected",
                i,
                reason,
                source=source_at,
                known=known_at,
                intent=intent_id,
                direction=direction,
                features=feature,
            )
            if intent_id:
                intents.append(
                    {
                        "intent_id": intent_id,
                        "bar_index": i,
                        "direction": direction,
                        "source_at": source_at,
                        "known_at": known_at,
                        "decision_at": closes[i],
                        "earliest_submission": closes[i],
                        "risk_distance": atr_values[i] * p.get("stop_mult", 2),
                    }
                )
        else:
            emit(
                "rejected",
                i,
                "warmup" if atr_values[i] is None else "no_signal",
                features=feature,
            )
    for level in levels.values():
        emit(
            "censored",
            len(bars) - 1,
            "level_pending_at_cutoff",
            source=level["source_at"],
            known=level["known_at"],
            before=level,
        )

    execution = simulate(intents, bars, p, step)
    # Keep stable event IDs distinct across decision and broker streams.
    for event in execution["ledger"]:
        event["event_id"] = f"b{event['event_id']}"
    complete_ledger = sorted(
        ledger + execution["ledger"],
        key=lambda e: (
            e.get("observed_at", e["decision_at"]),
            0 if e["event_id"].startswith("e") else 1,
            e["event_id"],
        ),
    )
    audit_ledger(complete_ledger)
    initial = float(p.get("initial_capital", 100000))
    hold_pct = (bars[-1].close / bars[0].close - 1) * 100 if bars[0].close else 0
    metrics = compute_metrics(
        initial,
        execution["trades"],
        execution["equity_curve"],
        initial * hold_pct / 100,
        hold_pct,
        bars[0].close,
        bars[-1].close,
    )
    metrics["marked_equity"] = execution["equity_curve"][-1]["equity"]
    return {
        "metrics": metrics,
        "trades": execution["trades"],
        "equity_curve": execution["equity_curve"],
        "diagnostics": {
            "accepted": len(intents),
            "rejected": sum(e["event_type"] == "rejected" for e in ledger),
            "censored": sum(e["event_type"] == "censored" for e in complete_ledger),
        },
        "decisions": decisions,
        "order_intents": intents,
        "ledger": complete_ledger if collect_ledger else [],
        "limitations": [
            "Decision-only fixed-quantity next-open control; no broker feedback.",
            "Open positions and pending intentions are censored, not liquidated at cutoff.",
            "OHLC stop/target ambiguity uses adverse stop-first ordering with reason codes.",
        ],
        "trace": {
            "schema_version": "1.0",
            "engine_id": spec["engine_id"],
            "capabilities": {"features": True, "signals": True, "position": True},
            "rows": [
                {
                    "time": opens[i],
                    "bar_index": i,
                    "market": {
                        k: getattr(b, k)
                        for k in ("open", "high", "low", "close", "volume")
                    },
                    "features": features[i],
                    "signals": {
                        "direction": next(
                            (d["direction"] for d in decisions if d["bar_index"] == i),
                            0,
                        )
                    },
                    "state": {"position_size": execution["positions"][i]},
                }
                for i, b in enumerate(bars)
            ],
        },
    }


def simulate(intents: list[dict], bars: list[Bar], p: dict, step: int) -> dict:
    """One broker shared by both references; fills never feed their decisions."""
    ledger: list[dict] = []
    trades: list[dict] = []
    curve: list[dict] = []
    positions: list[float] = []
    position: dict | None = None
    equity = float(p.get("initial_capital", 100000))
    qty = float(p.get("quantity", 1))
    fee = float(p.get("commission_pct", 0)) / 100
    slip = float(p.get("slippage_ticks", 0)) * float(p.get("tick_size", 0.01))
    pending = {item["bar_index"] + 1: item for item in intents}

    def record(
        kind: str,
        i: int,
        intent: dict,
        reason: str,
        *,
        at: int | None = None,
        **fields: Any,
    ) -> None:
        when = int(bars[i].ts.timestamp() * 1000) if at is None else at
        ledger.append(
            copy.deepcopy(
                {
                    "event_id": str(len(ledger)),
                    "event_type": kind,
                    "rule_id": "next_open_fixed_quantity_v1",
                    "bar_index": i,
                    "source_at": intent["source_at"],
                    "known_at": intent["known_at"],
                    "decision_at": intent["decision_at"],
                    "earliest_submission": intent["earliest_submission"],
                    "fill_at": when if kind == "fill" else None,
                    "observed_at": when,
                    "intent_id": intent["intent_id"],
                    "reason": reason,
                    "prior_state": position,
                    "next_state": position,
                    "evidence": [intent["intent_id"], f"bar:{i}"],
                    **fields,
                }
            )
        )

    def close(i: int, price: float, reason: str, at: int) -> None:
        nonlocal position, equity
        assert position is not None
        direction = position["direction"]
        exit_price = price - slip * direction
        cost = fee * (abs(position["price"] * qty) + abs(exit_price * qty))
        net = (exit_price - position["price"]) * direction * qty - cost
        trades.append(
            {
                "trade_id": position["intent"]["intent_id"],
                "intent_id": position["intent"]["intent_id"],
                "direction": "long" if direction == 1 else "short",
                "entry_ts": bars[position["index"]].ts.isoformat(),
                "exit_ts": bars[i].ts.isoformat(),
                "entry_price": position["price"],
                "exit_price": exit_price,
                "quantity": qty,
                "net_pnl": net,
                "gross_pnl": net + cost,
                "commission": cost,
                "return_on_equity_pct": net / position["equity"] * 100
                if position["equity"]
                else 0,
                "bars_held": i - position["index"],
                "reason": reason,
                "entry_exposure_pct": abs(position["price"] * qty) / initial * 100,
                "initial_risk_pct": position["intent"]["risk_distance"]
                * qty
                / initial
                * 100,
            }
        )
        record(
            "fill",
            i,
            position["intent"],
            reason,
            at=at,
            price=exit_price,
            quantity=qty,
            cost=cost,
            status="closed",
            prior_state=position,
            next_state=None,
        )
        equity += net
        position = None

    initial = equity
    for i, bar in enumerate(bars):
        at = int(bar.ts.timestamp() * 1000)
        item = pending.get(i)
        if item:
            if at < item["earliest_submission"]:
                fail("CAUSALITY_VIOLATION", "Intent submitted before decision.")
            if (
                p.get("max_gap_bars", 0)
                and at - item["decision_at"] > step * p["max_gap_bars"]
            ):
                record("expired", i, item, "gap_expiry")
            else:
                if position and position["direction"] != item["direction"]:
                    close(i, bar.open, "reverse", at)
                if position:
                    record("cancelled", i, item, "position_concurrency")
                else:
                    price = bar.open + slip * item["direction"]
                    position = {
                        "direction": item["direction"],
                        "price": price,
                        "index": i,
                        "intent": item,
                        "equity": equity,
                    }
                    record(
                        "fill",
                        i,
                        item,
                        "next_open",
                        price=price,
                        quantity=qty,
                        status="opened",
                        prior_state=None,
                        next_state=position,
                    )
        if position:
            d = position["direction"]
            risk = position["intent"]["risk_distance"]
            stop = position["price"] - d * risk
            target = position["price"] + d * risk * p.get("target_r", 0)
            stop_hit = bar.low <= stop if d == 1 else bar.high >= stop
            target_hit = bool(p.get("target_r", 0)) and (
                bar.high >= target if d == 1 else bar.low <= target
            )
            if stop_hit:
                gap = bar.open < stop if d == 1 else bar.open > stop
                close(
                    i,
                    bar.open if gap else stop,
                    "stop_gap"
                    if gap
                    else "ambiguous_stop_first"
                    if target_hit
                    else "stop",
                    at + step,
                )
            elif target_hit:
                gap = bar.open > target if d == 1 else bar.open < target
                close(i, bar.open if gap else target, "target", at + step)
        amount = qty * position["direction"] if position else 0
        marked = (
            equity
            + (bar.close - position["price"]) * amount
            - abs(position["price"] * qty) * fee
            if position
            else equity
        )
        positions.append(amount)
        curve.append(
            {
                "ts": bar.ts.isoformat(),
                "equity": marked,
                "realized_equity": equity,
                "mark_to_market_equity": marked,
            }
        )
    if position:
        record(
            "censored",
            len(bars) - 1,
            position["intent"],
            "position_open_at_cutoff",
            at=int(bars[-1].ts.timestamp() * 1000) + step,
        )
    for index, item in pending.items():
        if index >= len(bars):
            record(
                "censored",
                len(bars) - 1,
                item,
                "intent_pending_at_cutoff",
                at=int(bars[-1].ts.timestamp() * 1000) + step,
            )
    return {
        "trades": trades,
        "equity_curve": curve,
        "ledger": ledger,
        "positions": positions,
    }


def render_casebook(result: dict) -> str:
    """Saved ledger is the only source of visual state; no detector here."""
    import html

    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(e.get(k, '')))}</td>"
            for k in (
                "event_id",
                "bar_index",
                "event_type",
                "reason",
                "source_at",
                "known_at",
                "decision_at",
                "intent_id",
            )
        )
        + '<td><details><summary>Full event</summary><pre>'
        + html.escape(json.dumps(e, sort_keys=True, indent=2))
        + "</pre></details></td></tr>"
        for e in result["ledger"]
    )
    market = result.get("trace", {}).get("rows", [])
    chart = ""
    if market:
        low = min(row["market"]["low"] for row in market)
        high = max(row["market"]["high"] for row in market)
        span = high - low or 1

        def point(i: int, price: float) -> tuple[float, float]:
            return 20 + 960 * i / max(1, len(market) - 1), 300 - 270 * (
                price - low
            ) / span

        candles = []
        stride = max(1, (len(market) + 999) // 1000)
        for i in range(0, len(market), stride):
            values = market[i]["market"]
            x, top = point(i, values["high"])
            _, bottom = point(i, values["low"])
            _, open_y = point(i, values["open"])
            _, close_y = point(i, values["close"])
            color = "#167d50" if values["close"] >= values["open"] else "#bd3444"
            candles.append(
                f'<path d="M{x:.2f},{top:.2f} V{bottom:.2f} M{x - 2:.2f},{open_y:.2f} H{x + 2:.2f} M{x - 2:.2f},{close_y:.2f} H{x + 2:.2f}" stroke="{color}"/>'
            )
        markers = []
        for event in result["ledger"][-300:]:
            i = event["bar_index"]
            x, y = point(i, market[i]["market"]["close"])
            label = html.escape(
                f"{event['event_id']} {event['event_type']}: {event['reason']}"
            )
            markers.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#315dd8"><title>{label}</title></circle>'
            )
        chart = (
            '<svg viewBox="0 0 1000 320" role="img" aria-label="Saved market observations and ledger events">'
            + "".join(candles + markers)
            + "</svg><p>Chart samples at most 1,000 candles and the latest 300 ledger markers. The complete event ledger remains below; rendering never limits detection.</p>"
        )
    return (
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><link rel="icon" href="data:,"><title>Reference casebook</title><style>body{font:15px system-ui;margin:24px}svg{width:100%;max-height:480px;background:#f6f8fa}table{border-collapse:collapse}td,th{padding:6px;border:1px solid #ccd}th{position:sticky;top:0;background:white}.ledger{overflow:auto}pre{max-width:36rem;white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Reference event casebook</h1>'
        + chart
        + '<div class="ledger"><table><tr><th>Event</th><th>Bar</th><th>Type</th><th>Reason</th><th>Source</th><th>Known</th><th>Decision</th><th>Intent</th><th>State and evidence</th></tr>'
        + rows
        + "</table></div>"
    )
