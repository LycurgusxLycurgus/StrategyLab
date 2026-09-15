from __future__ import annotations

import json
import itertools
import math
import sqlite3
from dataclasses import replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from app.tg_import import decode_tick_payload
from app.tg_models import ENGINE_VERSION, ExitFill, ManagementPolicy, ReplayResult, TargetGeometryPolicy, Tick, utc_milliseconds


EPSILON = 1e-9


def _float(payload: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if payload.get(key) not in (None, ""):
            return float(payload[key])
    return default


def _target_label(leg: dict[str, Any], ordinal: int) -> str:
    raw = str(leg.get("native_target") or leg.get("target") or leg.get("target_name") or "").upper()
    return raw if raw in {"TP1", "TP2", "TP3"} else f"TP{min(ordinal + 1, 3)}"


class TgSignalReplayEngine:
    engine_version = ENGINE_VERSION

    def load_operation(self, snapshot_db: Path, execution_id: str) -> tuple[dict[str, Any], list[Tick], dict[str, Any]]:
        connection = sqlite3.connect(snapshot_db)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute("SELECT payload_json FROM operations WHERE execution_id = ?", (execution_id,)).fetchone()
            if not row:
                raise KeyError(f"Unknown execution: {execution_id}")
            operation = json.loads(row[0])
            coverage_row = connection.execute("SELECT payload_json FROM tick_coverage WHERE execution_id = ?", (execution_id,)).fetchone()
            coverage = json.loads(coverage_row[0]) if coverage_row else {}
            ticks: list[Tick] = []
            source_ordinal = 0
            rows = connection.execute(
                "SELECT * FROM tick_chunks WHERE execution_id = ? ORDER BY range_start_msc, id", (execution_id,)
            ).fetchall()
            for chunk in rows:
                decoded = decode_tick_payload(chunk["payload"], chunk["checksum"], chunk["codec"], source_ordinal)
                ticks.extend(decoded)
                source_ordinal += len(decoded)
            ticks.sort(key=lambda tick: (tick.time_msc, tick.source_ordinal))
            if not ticks:
                tables = {
                    str(item[0]) for item in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                if "one_second_marks" in tables:
                    marks = connection.execute(
                        "SELECT sampled_at,price,source_ordinal "
                        "FROM one_second_marks WHERE execution_id=? "
                        "ORDER BY sampled_at,source_ordinal",
                        (execution_id,),
                    ).fetchall()
                    ticks = [
                        Tick(
                            utc_milliseconds(str(mark["sampled_at"])),
                            float(mark["price"]), float(mark["price"]), 0,
                            int(mark["source_ordinal"]),
                        )
                        for mark in marks
                    ]
                    if ticks:
                        coverage = {
                            "status": "APPROXIMATE_1S",
                            "coverage_start_at": str(marks[0]["sampled_at"]),
                            "coverage_end_at": str(marks[-1]["sampled_at"]),
                            "coverage_gap_count": 0,
                            "horizon_complete": False,
                            "evidence_tier": "APPROXIMATE_1S",
                            "sample_resolution_seconds": 1,
                        }
            coverage.setdefault(
                "evidence_tier",
                "EXACT_TICK" if ticks and str(coverage.get("status")) == "COMPLETE"
                else "MISSING",
            )
            return operation, ticks, coverage
        finally:
            connection.close()

    @staticmethod
    def policy_from_snapshot(snapshot_db: Path, management_policy_version: str) -> ManagementPolicy | None:
        connection = sqlite3.connect(snapshot_db)
        try:
            row = connection.execute("SELECT payload_json FROM policies WHERE version = ?", (management_policy_version,)).fetchone()
        finally:
            connection.close()
        if not row:
            return None
        payload = json.loads(row[0])
        payload.setdefault("management_policy_version", management_policy_version)
        payload.setdefault("policy_id", f"baseline_{management_policy_version}")
        payload.setdefault("parent_policy_id", None)
        return ManagementPolicy.from_dict(payload)

    def replay(
        self, operation: dict[str, Any], ticks: list[Tick],
        coverage: dict[str, Any], policy: ManagementPolicy,
        target_geometry: TargetGeometryPolicy | None = None,
        counterfactual: bool = False,
    ) -> ReplayResult:
        geometry = target_geometry or TargetGeometryPolicy.provider_original()
        if geometry.mode == "PROVIDER_ORIGINAL" and policy.parent_policy_id is None and not counterfactual and (
            operation.get("deals")
            or operation.get("_use_broker_actual_baseline")
        ):
            result = self._broker_actual_baseline(operation, policy)
            diagnostics = dict(result.diagnostics)
            diagnostics["evidence_tier"] = "BROKER_DEALS"
            return replace(result, diagnostics=diagnostics)

        exclusions = self._preflight(operation, ticks, coverage)
        if exclusions:
            return ReplayResult(operation["execution_id"], policy.policy_id, "CENSORED", False, tuple(exclusions), None, None, (), (), float(operation.get("filled_volume") or 0), {"engine_version": self.engine_version})

        side = str(operation["side"]).upper()
        direction = 1.0 if side == "BUY" else -1.0
        entry = float(operation["actual_fill"])
        initial_stop = float(operation["initial_provider_sl"])
        risk_price = abs(entry - initial_stop)
        if risk_price <= EPSILON:
            return ReplayResult(operation["execution_id"], policy.policy_id, "CENSORED", False, ("INVALID_INITIAL_RISK",), None, None, (), (), float(operation.get("filled_volume") or 0), {"engine_version": self.engine_version})
        total_volume = float(operation.get("filled_volume") or operation.get("requested_volume") or 0)
        symbol_spec = operation.get("symbol_spec") or {}
        contract_size = float(symbol_spec.get("contract_size") or 0)
        point_size = float(symbol_spec.get("point_size") or symbol_spec.get("point") or 0)
        volume_min = float(operation.get("volume_min") or 0)
        volume_step = float(operation.get("volume_step") or 0)
        if not operation.get("symbol_spec_resolved") or contract_size <= 0 or volume_min <= 0 or volume_step <= 0:
            return ReplayResult(operation["execution_id"], policy.policy_id, "NON_COMPARABLE", False, ("MISSING_SYMBOL_ECONOMICS",), None, None, (), (), total_volume, {"engine_version": self.engine_version})
        target_prices, target_error = self._resolve_targets(operation, geometry, symbol_spec)
        if target_error:
            return ReplayResult(
                operation["execution_id"], self._policy_identity(policy, geometry),
                "NON_COMPARABLE", False, (target_error,), None, None, (), (),
                total_volume, {
                    "engine_version": self.engine_version,
                    "target_geometry": geometry.to_dict(),
                    "promotion_eligible": False,
                },
            )
        legs, representable = self._build_legs(
            operation, policy, total_volume, volume_min, volume_step,
            target_prices,
        )
        if not representable:
            return ReplayResult(operation["execution_id"], policy.policy_id, "NON_COMPARABLE", False, ("UNREPRESENTABLE_VOLUME",), None, None, (), (), total_volume, {"engine_version": self.engine_version})

        current_stop = initial_stop
        pending_stop: tuple[int, float, str] | None = None
        achieved_targets: set[str] = set()
        max_favorable = 0.0
        last_trail_anchor = 0.0
        fills: list[ExitFill] = []
        milestones: list[dict[str, Any]] = []
        open_legs = {leg["leg_id"]: leg for leg in legs}
        opened_msc = utc_milliseconds(operation["opened_at"])
        horizon_msc = (
            utc_milliseconds(str(coverage["horizon_end_at"]))
            if coverage.get("horizon_end_at") else None
        )
        horizon_reason = str(coverage.get("horizon_reason") or "")
        last_tick: Tick | None = None

        replay_ticks = ticks
        if policy.stress_same_millisecond_stop_first:
            replay_ticks = []
            for _, group in itertools.groupby(ticks, key=lambda item: item.time_msc):
                same_millisecond = list(group)
                same_millisecond.sort(key=(lambda item: (item.bid, item.source_ordinal)) if side == "BUY" else (lambda item: (-item.ask, item.source_ordinal)))
                replay_ticks.extend(same_millisecond)
        for tick in replay_ticks:
            if tick.time_msc < opened_msc:
                continue
            if horizon_msc is not None and tick.time_msc > horizon_msc:
                break
            last_tick = tick
            if pending_stop and tick.time_msc >= pending_stop[0]:
                candidate_stop = pending_stop[1]
                if self._more_protective(side, candidate_stop, current_stop):
                    current_stop = candidate_stop
                    milestones.append({"event": pending_stop[2], "time_msc": tick.time_msc, "stop": current_stop})
                pending_stop = None
            close_price = tick.bid if side == "BUY" else tick.ask
            favorable_r = direction * (close_price - entry) / risk_price
            max_favorable = max(max_favorable, favorable_r)

            requested_stop = self._dynamic_stop(policy, side, entry, risk_price, max_favorable, favorable_r, last_trail_anchor, point_size, achieved_targets)
            if requested_stop is not None and self._more_protective(side, requested_stop, current_stop):
                activation = tick.time_msc + max(0, policy.latency_msc)
                if activation <= tick.time_msc:
                    current_stop = requested_stop
                    milestones.append({"event": "DYNAMIC_STOP", "time_msc": tick.time_msc, "stop": current_stop})
                else:
                    pending_stop = (activation, requested_stop, "DYNAMIC_STOP")
                last_trail_anchor = max_favorable

            stop_hit = close_price <= current_stop + EPSILON if side == "BUY" else close_price >= current_stop - EPSILON
            if stop_hit:
                for leg in sorted(open_legs.values(), key=lambda item: (str(item.get("order_ticket") or ""), item["ordinal"])):
                    fills.append(self._fill(operation, leg, "SL", tick, current_stop, contract_size, policy))
                open_legs.clear()
                break

            target_hits = []
            for leg in open_legs.values():
                target = leg.get("target_price")
                if target is None:
                    continue
                hit = close_price >= target - EPSILON if side == "BUY" else close_price <= target + EPSILON
                if hit:
                    target_hits.append(leg)
            for leg in sorted(target_hits, key=lambda item: (str(item.get("order_ticket") or ""), item["ordinal"])):
                label = leg["target_label"]
                fills.append(self._fill(operation, leg, label, tick, float(leg["target_price"]), contract_size, policy))
                del open_legs[leg["leg_id"]]
                milestones.append({"event": label, "time_msc": tick.time_msc, "price": leg["target_price"], "remaining_volume": sum(item["volume"] for item in open_legs.values())})
                achieved_targets.add(label)
                requested = None
                event_name = ""
                if label == "TP1" and policy.tp1_action in {"breakeven", "breakeven_offset", "trailing"}:
                    offset = policy.breakeven_offset_price
                    if policy.breakeven_offset_points is not None:
                        offset = policy.breakeven_offset_points * point_size
                    requested = entry + direction * offset
                    event_name = "BREAKEVEN_AFTER_TP1"
                elif label == "TP2" and policy.tp2_action == "stop_to_tp1" and target_prices.get("TP1") is not None:
                    requested = float(target_prices["TP1"])
                    event_name = "STOP_TO_TP1_AFTER_TP2"
                if requested is not None and self._more_protective(side, requested, current_stop):
                    activation = tick.time_msc + max(0, policy.latency_msc)
                    if activation <= tick.time_msc:
                        current_stop = requested
                        milestones.append({"event": event_name, "time_msc": tick.time_msc, "stop": current_stop})
                    else:
                        pending_stop = (activation, requested, event_name)
            if not open_legs:
                break

            if policy.time_stop_seconds is not None and tick.time_msc >= opened_msc + policy.time_stop_seconds * 1000:
                for leg in sorted(open_legs.values(), key=lambda item: item["ordinal"]):
                    fills.append(self._fill(operation, leg, "TIME_STOP", tick, close_price, contract_size, policy))
                open_legs.clear()
                break
        if (
            open_legs
            and last_tick is not None
            and bool(coverage.get("horizon_complete"))
            and horizon_reason in {"DAILY_FORCED_CLOSE", "WEEKLY_FORCED_CLOSE"}
        ):
            actual_exit = operation.get("actual_exit")
            use_actual_exit = (
                actual_exit is not None
                and str(operation.get("close_reason") or "") in {
                    "DAILY_PAUSE", "WEEKEND_CLOSE",
                }
            )
            forced_bid = (
                float(actual_exit)
                if use_actual_exit and side == "BUY" else last_tick.bid
            )
            forced_ask = (
                float(actual_exit)
                if use_actual_exit and side == "SELL" else last_tick.ask
            )
            forced_tick = Tick(
                horizon_msc or last_tick.time_msc,
                forced_bid,
                forced_ask,
                last_tick.flags,
                last_tick.source_ordinal,
            )
            close_price = forced_tick.bid if side == "BUY" else forced_tick.ask
            for leg in sorted(open_legs.values(), key=lambda item: item["ordinal"]):
                fills.append(self._fill(
                    operation, leg, horizon_reason, forced_tick,
                    close_price, contract_size, policy,
                ))
            open_legs.clear()
            milestones.append({
                "event": horizon_reason,
                "time_msc": forced_tick.time_msc,
                "price": close_price,
            })

        if open_legs:
            reason = (
                "CENSORED_TARGET_HORIZON"
                if geometry.mode == "FIXED_R"
                else "TRAJECTORY_ENDED_WITH_OPEN_VOLUME"
            )
            pending_targets = [
                {
                    "leg_id": leg["leg_id"],
                    "target": leg["target_label"],
                    "price": leg.get("target_price"),
                    "r": getattr(geometry, f"{leg['target_label'].lower()}_r", None),
                }
                for leg in open_legs.values()
            ]
            return ReplayResult(operation["execution_id"], self._policy_identity(policy, geometry), "CENSORED", False, (reason,), None, None, tuple(fills), tuple(milestones), sum(item["volume"] for item in open_legs.values()), {"engine_version": self.engine_version, "max_favorable_r": max_favorable, "target_geometry": geometry.to_dict(), "pending_targets": pending_targets, "requires_future_capture": geometry.mode == "FIXED_R", "promotion_eligible": False})
        net = sum(fill.net_pnl for fill in fills)
        result_r = net / float(operation["risk_amount"]) if float(operation.get("risk_amount") or 0) > 0 else None
        comparable = bool(operation.get("costs_complete"))
        approximate = coverage.get("evidence_tier") == "APPROXIMATE_1S"
        status = "COMPLETE_APPROXIMATE" if comparable and approximate else (
            "COMPLETE" if comparable else "NON_COMPARABLE"
        )
        missing = () if comparable else ("MISSING_NET_COSTS",)
        return ReplayResult(operation["execution_id"], self._policy_identity(policy, geometry), status, comparable, missing, net, result_r, tuple(fills), tuple(milestones), 0.0, {"engine_version": self.engine_version, "max_favorable_r": max_favorable, "evidence_tier": coverage.get("evidence_tier", "EXACT_TICK"), "promotion_eligible": not approximate, "target_geometry": geometry.to_dict(), "resolved_targets": target_prices})

    def _broker_actual_baseline(
        self, operation: dict[str, Any], policy: ManagementPolicy,
    ) -> ReplayResult:
        deals = list(operation.get("deals") or [])
        if deals and all(deal.get("entry") in (None, "") for deal in deals):
            net = sum(
                float(deal.get("profit") or 0)
                + float(deal.get("commission") or 0)
                + float(deal.get("swap") or 0)
                + float(deal.get("fee") or deal.get("fees") or 0)
                for deal in deals
            )
            risk = float(operation.get("risk_amount") or 0)
            fill = ExitFill(
                "broker:aggregate", "BROKER_ACTUAL",
                utc_milliseconds(str(operation["closed_at"])),
                float(operation.get("actual_exit") or 0),
                float(operation.get("filled_volume") or 0), net, net,
            )
            return ReplayResult(
                operation["execution_id"], policy.policy_id, "COMPLETE", True,
                (), net, (net / risk if risk > EPSILON else None), (fill,), (),
                0.0, {
                    "engine_version": self.engine_version,
                    "baseline_source": "BROKER_DEALS_AGGREGATE",
                },
            )
        exits = [deal for deal in deals if int(deal.get("entry") or 0) != 0]
        if not exits:
            actual = operation.get("broker_realized_net_pnl")
            if actual is not None:
                net = float(actual)
                risk = float(operation.get("risk_amount") or 0)
                fill = ExitFill(
                    "broker:execution-aggregate", "BROKER_ACTUAL",
                    utc_milliseconds(str(operation["closed_at"])),
                    float(operation.get("actual_exit") or 0),
                    float(operation.get("filled_volume") or 0), net, net,
                )
                return ReplayResult(
                    operation["execution_id"], policy.policy_id, "COMPLETE",
                    True, (), net, (net / risk if risk > EPSILON else None),
                    (fill,), (), 0.0,
                    {
                        "engine_version": self.engine_version,
                        "baseline_source": "BROKER_EXECUTION_AGGREGATE",
                        "quality_flags": ["DEAL_BREAKDOWN_UNAVAILABLE"],
                    },
                )
            return ReplayResult(
                operation["execution_id"], policy.policy_id, "NON_COMPARABLE",
                False, ("MISSING_BROKER_EXIT_DEALS",), None, None, (), (),
                float(operation.get("filled_volume") or 0),
                {"engine_version": self.engine_version},
            )
        entry_costs = sum(
            float(deal.get("commission") or 0)
            + float(deal.get("swap") or 0)
            + float(deal.get("fee") or deal.get("fees") or 0)
            for deal in deals if int(deal.get("entry") or 0) == 0
        )
        total_exit_volume = sum(float(deal.get("volume") or 0) for deal in exits)
        fills: list[ExitFill] = []
        for ordinal, deal in enumerate(exits):
            volume = float(deal.get("volume") or 0)
            profit = float(deal.get("profit") or 0)
            own_costs = (
                float(deal.get("commission") or 0)
                + float(deal.get("swap") or 0)
                + float(deal.get("fee") or deal.get("fees") or 0)
            )
            allocated_entry_cost = (
                entry_costs * volume / total_exit_volume
                if total_exit_volume > EPSILON else 0.0
            )
            fills.append(ExitFill(
                str(deal.get("ticket") or f"broker:{ordinal}"),
                "BROKER_ACTUAL",
                int(deal.get("time_msc") or int(deal.get("time") or 0) * 1000),
                float(deal.get("price") or 0), volume, profit,
                profit + own_costs + allocated_entry_cost,
            ))
        net = sum(fill.net_pnl for fill in fills)
        risk = float(operation.get("risk_amount") or 0)
        return ReplayResult(
            operation["execution_id"], policy.policy_id, "COMPLETE", True, (),
            net, (net / risk if risk > EPSILON else None), tuple(fills), (), 0.0,
            {
                "engine_version": self.engine_version,
                "baseline_source": "BROKER_DEALS",
            },
        )

    @staticmethod
    def _preflight(operation: dict[str, Any], ticks: list[Tick], coverage: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if not ticks or not coverage:
            reasons.append("MISSING_TICK_ARCHIVE")
            return reasons
        if str(coverage.get("status")) not in {"COMPLETE", "APPROXIMATE_1S"}:
            reasons.append("ARCHIVE_NOT_COMPLETE")
        if int(
            coverage.get("coverage_gap_count")
            or coverage.get("gap_count")
            or 0
        ) != 0:
            reasons.append("ARCHIVE_GAPS")
        if not coverage.get("coverage_start_at") or (operation.get("opened_at") and utc_milliseconds(str(coverage["coverage_start_at"])) > utc_milliseconds(operation["opened_at"])):
            reasons.append("ENTRY_OUTSIDE_COVERAGE")
        if operation.get("closed_at") and (not coverage.get("coverage_end_at") or utc_milliseconds(str(coverage["coverage_end_at"])) + (1000 if coverage.get("evidence_tier") == "APPROXIMATE_1S" else 0) < utc_milliseconds(operation["closed_at"])):
            reasons.append("CLOSE_OUTSIDE_COVERAGE")
        return reasons

    @staticmethod
    def _build_legs(operation: dict[str, Any], policy: ManagementPolicy, total: float, volume_min: float, volume_step: float, target_prices: dict[str, float | None] | None = None) -> tuple[list[dict[str, Any]], bool]:
        target_prices = target_prices or {
            "TP1": operation.get("tp1"), "TP2": operation.get("tp2"),
            "TP3": operation.get("tp3"),
        }
        native = operation.get("legs") or []
        baseline_native = policy.parent_policy_id is None and native
        legs: list[dict[str, Any]] = []
        if baseline_native:
            for ordinal, leg in enumerate(native):
                volume = _float(leg, "filled_volume", "volume", "requested_volume")
                label = _target_label(leg, ordinal)
                target = target_prices.get(label)
                legs.append({"leg_id": str(leg.get("id") or leg.get("leg_id") or f"{operation['execution_id']}:{ordinal}"), "ordinal": int(leg.get("leg_index") or ordinal), "volume": volume, "target_label": label, "target_price": target or None, "order_ticket": leg.get("order_ticket")})
            return legs, abs(sum(item["volume"] for item in legs) - total) <= max(EPSILON, volume_step / 2)
        raw = [total * fraction for fraction in policy.partials]
        volumes = [math.floor((value + EPSILON) / volume_step) * volume_step for value in raw]
        remainder = round(total - sum(volumes), 10)
        if volumes:
            volumes[0] += remainder
        if len(volumes) > 1 and any(volume + EPSILON < volume_min for volume in volumes):
            volumes = [total]
        if any(volume + EPSILON < volume_min or abs(round(volume / volume_step) * volume_step - volume) > 1e-7 for volume in volumes):
            return [], False
        for ordinal, volume in enumerate(volumes):
            label = f"TP{min(ordinal + 1, 3)}"
            legs.append({"leg_id": f"{operation['execution_id']}:{ordinal}", "ordinal": ordinal, "volume": volume, "target_label": label, "target_price": target_prices.get(label), "order_ticket": None})
        return legs, True

    @staticmethod
    def _policy_identity(policy: ManagementPolicy, geometry: TargetGeometryPolicy) -> str:
        return (
            policy.policy_id if geometry.mode == "PROVIDER_ORIGINAL"
            else f"{policy.policy_id}+{geometry.geometry_id}"
        )

    @staticmethod
    def _resolve_targets(
        operation: dict[str, Any], geometry: TargetGeometryPolicy,
        symbol_spec: dict[str, Any],
    ) -> tuple[dict[str, float | None], str | None]:
        if geometry.mode == "PROVIDER_ORIGINAL":
            return {
                "TP1": operation.get("tp1"), "TP2": operation.get("tp2"),
                "TP3": operation.get("tp3"),
            }, None
        if geometry.mode != "FIXED_R":
            return {}, "UNKNOWN_TARGET_GEOMETRY_MODE"
        provider_entry = float(operation.get("provider_entry") or 0)
        provider_sl = float(operation.get("initial_provider_sl") or 0)
        side = str(operation.get("side") or "").upper()
        direction = Decimal("1") if side == "BUY" else Decimal("-1")
        provider_r = abs(Decimal(str(provider_entry)) - Decimal(str(provider_sl)))
        if provider_r <= 0 or (
            side == "BUY" and provider_sl >= provider_entry
        ) or (
            side == "SELL" and provider_sl <= provider_entry
        ):
            return {}, "INVALID_PROVIDER_R"
        values = (geometry.tp1_r, geometry.tp2_r, geometry.tp3_r)
        if any(value is None for value in values):
            return {}, "INCOMPLETE_TARGET_GEOMETRY"
        rs = tuple(float(value) for value in values if value is not None)
        if not (0 < rs[0] < rs[1] < rs[2]):
            return {}, "INVALID_TARGET_R_ORDER"
        tick_size = symbol_spec.get("trade_tick_size") or symbol_spec.get("tick_size")
        digits = symbol_spec.get("digits")
        if tick_size in (None, "", 0) or digits in (None, ""):
            return {}, "MISSING_TARGET_NORMALIZATION_SPEC"
        quantum = Decimal(str(tick_size))
        digit_quantum = Decimal(1).scaleb(-int(digits))
        entry_dec = Decimal(str(provider_entry))
        targets: list[float] = []
        for r_value in rs:
            raw = entry_dec + direction * provider_r * Decimal(str(r_value))
            normalized = (raw / quantum).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * quantum
            normalized = normalized.quantize(digit_quantum, rounding=ROUND_HALF_UP)
            targets.append(float(normalized))
        correct = (
            targets[0] > provider_entry and targets[0] < targets[1] < targets[2]
            if side == "BUY" else
            targets[0] < provider_entry and targets[0] > targets[1] > targets[2]
        )
        if not correct:
            return {}, "INVALID_NORMALIZED_TARGET_ORDER"
        actual_fill = float(operation.get("actual_fill") or 0)
        if (side == "BUY" and any(target <= actual_fill for target in targets)) or (
            side == "SELL" and any(target >= actual_fill for target in targets)
        ):
            return {}, "INVALID_TARGET_AT_FILL"
        return dict(zip(("TP1", "TP2", "TP3"), targets)), None

    @staticmethod
    def _dynamic_stop(policy: ManagementPolicy, side: str, entry: float, risk: float, mfe_r: float, favorable_r: float, last_anchor: float, point_size: float = 0.0, achieved_targets: set[str] | None = None) -> float | None:
        direction = 1.0 if side == "BUY" else -1.0
        stops: list[float] = []
        if policy.early_breakeven_activation_r is not None and favorable_r >= policy.early_breakeven_activation_r:
            offset = policy.early_breakeven_offset_r * risk
            if policy.early_breakeven_offset_price is not None:
                offset = policy.early_breakeven_offset_price
            if policy.early_breakeven_offset_points is not None:
                offset = policy.early_breakeven_offset_points * point_size
            stops.append(entry + direction * offset)
        achieved_targets = achieved_targets or set()
        trailing_allowed = policy.trailing_after == "entry" or (policy.trailing_after == "tp1" and "TP1" in achieved_targets) or (policy.trailing_after == "tp2" and "TP2" in achieved_targets)
        distance = policy.trailing_distance_r * risk if policy.trailing_distance_r is not None else None
        if policy.trailing_distance_price is not None:
            distance = policy.trailing_distance_price
        if policy.trailing_distance_points is not None:
            distance = policy.trailing_distance_points * point_size
        if trailing_allowed and policy.trailing_activation_r is not None and distance is not None and mfe_r >= policy.trailing_activation_r and mfe_r - last_anchor >= policy.trailing_step_r:
            stops.append(entry + direction * (mfe_r * risk - distance))
        if policy.mfe_protect_activation_r is not None and policy.mfe_protect_fraction is not None and mfe_r >= policy.mfe_protect_activation_r:
            stops.append(entry + direction * mfe_r * policy.mfe_protect_fraction * risk)
        if not stops:
            return None
        return max(stops) if side == "BUY" else min(stops)

    @staticmethod
    def _more_protective(side: str, candidate: float, current: float) -> bool:
        return candidate > current + EPSILON if side == "BUY" else candidate < current - EPSILON

    @staticmethod
    def _fill(operation: dict[str, Any], leg: dict[str, Any], reason: str, tick: Tick, requested_price: float, contract_size: float, policy: ManagementPolicy) -> ExitFill:
        direction = 1.0 if operation["side"] == "BUY" else -1.0
        adverse = -direction * policy.exit_slippage_price
        executable = tick.bid if operation["side"] == "BUY" else tick.ask
        if reason == "SL":
            price = min(executable, requested_price) if direction > 0 else max(executable, requested_price)
        elif reason.startswith("TP"):
            price = requested_price
        else:
            price = executable
        price += adverse
        volume = float(leg["volume"])
        gross = direction * (price - float(operation["actual_fill"])) * contract_size * volume
        total_volume = float(operation.get("filled_volume") or operation.get("requested_volume") or volume)
        costs = float(operation.get("commission") or 0) + float(operation.get("swap") or 0) + float(operation.get("fees") or 0)
        net = gross + costs * (volume / total_volume)
        return ExitFill(leg["leg_id"], reason, tick.time_msc, price, volume, gross, net)


def stress_policy(policy: ManagementPolicy, *, latency_msc: int, slippage_price: float) -> ManagementPolicy:
    return replace(policy, policy_id=f"{policy.policy_id}_stress", latency_msc=latency_msc, exit_slippage_price=slippage_price, stress_same_millisecond_stop_first=True)
