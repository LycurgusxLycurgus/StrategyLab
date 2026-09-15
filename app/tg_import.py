from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import struct
import zlib
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException

from app.config import settings
from app.tg_models import IMPORTER_VERSION, MODEL_VERSION, SUPPORTED_ASSETS, Tick


ARCHIVE_SCHEMA_VERSION = 2
TICK_CODEC = "zlib-struct-qddI-v1"
TICK_STRUCT = struct.Struct("<qddI")
SNAPSHOT_MANIFEST_VERSION = 1
SUPPORTED_OPERATIONAL_MIGRATIONS = set(range(16, 23))
MIN_SUPPORTED_OPERATIONAL_MIGRATION = 16
MIGRATION_20_EXECUTION_COLUMNS = {
    "execution_venue", "provider_entry_price", "provider_stop_loss",
    "provider_tp1", "provider_tp2", "provider_tp3", "venue_price_delta",
    "reference_quote_bid", "reference_quote_ask", "destination_quote_bid",
    "destination_quote_ask", "quote_skew_seconds", "quote_acquisition_seconds",
    "venue_order_id", "venue_position_key",
}
MIGRATION_20_LEG_COLUMNS = {"venue_order_id"}
MIGRATION_21_EXECUTION_COLUMNS = {
    "cohort_decision", "cohort_decided_at", "cohort_authority_execution_id",
    "cohort_authority_status",
}
MIGRATION_22_EXECUTION_COLUMNS = {"cohort_authority_leg_count"}


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@contextmanager
def readonly_sqlite(path: Path) -> Iterator[sqlite3.Connection]:
    """Open a finalized SQLite snapshot without creating journals or sidecars."""
    path = path.resolve()
    if not path.is_file():
        raise HTTPException(400, f"SQLite snapshot not found: {path}")
    sidecars = [Path(f"{path}-wal"), Path(f"{path}-shm")]
    present = [item.name for item in sidecars if item.exists()]
    if present:
        raise HTTPException(400, f"Unconsolidated SQLite snapshot; sidecars present: {', '.join(present)}")
    uri = f"{path.as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
        if integrity != "ok":
            raise HTTPException(400, f"SQLite integrity check failed: {integrity}")
        yield connection
    finally:
        connection.close()


def decode_tick_payload(payload: bytes, checksum: str, codec: str = TICK_CODEC, ordinal_start: int = 0) -> list[Tick]:
    if codec != TICK_CODEC:
        raise ValueError(f"Unsupported tick codec: {codec}")
    actual = sha256_bytes(payload)
    if actual.lower() != checksum.lower():
        raise ValueError(f"Tick checksum mismatch: expected {checksum}, got {actual}")
    raw = zlib.decompress(payload)
    if len(raw) % TICK_STRUCT.size:
        raise ValueError("Tick payload length is not a multiple of the record size")
    ticks: list[Tick] = []
    for index, values in enumerate(TICK_STRUCT.iter_unpack(raw)):
        ticks.append(Tick(int(values[0]), float(values[1]), float(values[2]), int(values[3]), ordinal_start + index))
    return ticks


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _parse_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _number(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    return float(value)


def _first_present(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), None)


class TgSnapshotImporter:
    def __init__(self, repository: Any, snapshot_dir: Path | None = None) -> None:
        self.repository = repository
        self.snapshot_dir = snapshot_dir or settings.tg_snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def import_package(self, package_path: str | Path) -> dict[str, Any]:
        package = Path(package_path).resolve()
        if str(package).startswith("\\\\"):
            raise HTTPException(400, "Network paths are not allowed; copy the finalized package locally first")
        manifest_path = package / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(400, "Offline package must contain manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._validate_manifest(manifest)
        roles = manifest["files"]
        source_paths = {role: (package / relative).resolve() for role, relative in roles.items() if relative}
        for role, path in source_paths.items():
            if package not in path.parents or not path.is_file():
                raise HTTPException(400, f"Invalid or missing {role} source")
        sqlite_paths = [path for role, path in source_paths.items() if role.endswith("sqlite")]
        for path in sqlite_paths:
            if Path(f"{path}-wal").exists() or Path(f"{path}-shm").exists():
                raise HTTPException(400, f"Unconsolidated SQLite snapshot: {path.name}")
        file_hashes = {role: sha256_file(path) for role, path in sorted(source_paths.items())}
        for role, expected in manifest.get("source_checksums", {}).items():
            if role not in file_hashes or file_hashes[role].lower() != str(expected).lower():
                raise HTTPException(400, f"Snapshot source checksum mismatch: {role}")
        fingerprint = sha256_bytes(canonical_json({
            "manifest": manifest,
            "files": file_hashes,
            "importer_version": IMPORTER_VERSION,
            "model_version": MODEL_VERSION,
        }).encode())
        snapshot_id = f"tgsnap_{fingerprint[:16]}"
        existing = self.repository.get_tg_snapshot(snapshot_id)
        if existing:
            return existing

        policies = self._load_json_mapping(source_paths.get("policy_registry"))
        symbol_specs = self._load_json_mapping(source_paths.get("symbol_specs"))
        deals = self._load_deals(source_paths.get("deals_csv"))
        operations, external_events, one_second_marks = self._read_operations(
            source_paths["operational_sqlite"], manifest, policies,
            symbol_specs, deals,
        )
        archive = self._verify_tick_archive(source_paths["tick_sqlite"])
        for operation in operations:
            record = archive.get(operation["execution_id"])
            operation.update({
                "coverage_status": str(record.get("status")) if record else "MISSING",
                "coverage_start_at": record.get("coverage_start_at") if record else None,
                "coverage_end_at": record.get("coverage_end_at") if record else None,
                "coverage_gap_count": int(
                    record.get("coverage_gap_count")
                    or record.get("gap_count")
                    or 0
                ) if record else 0,
                "horizon_end_at": record.get("horizon_end_at") if record else None,
                "horizon_reason": record.get("horizon_reason") if record else None,
                "horizon_complete": bool(record.get("horizon_complete")) if record else False,
                "horizon_version": record.get("horizon_version") if record else None,
                "checksum_status": "VALID" if record and int(record.get("tick_count") or 0) > 0 else "MISSING",
            })
        coverage = self._coverage_report(operations, archive)

        target = self.snapshot_dir / snapshot_id
        temp_target = self.snapshot_dir / f".{snapshot_id}.importing"
        if temp_target.exists():
            shutil.rmtree(temp_target)
        temp_target.mkdir(parents=True)
        try:
            canonical_path = temp_target / "snapshot.sqlite3"
            self._write_canonical(
                canonical_path, manifest, operations, external_events,
                one_second_marks, source_paths["tick_sqlite"], policies,
                symbol_specs, deals,
            )
            supporting = temp_target / "supporting_sources"
            for role in ("trades_csv", "shadow_csv"):
                if role in source_paths:
                    supporting.mkdir(exist_ok=True)
                    shutil.copyfile(source_paths[role], supporting / source_paths[role].name)
            normalized_manifest = {
                **manifest,
                "source_origin": str(package),
                "snapshot_id": snapshot_id,
                "snapshot_checksum": fingerprint,
                "source_hashes": file_hashes,
                "importer_version": IMPORTER_VERSION,
                "model_version": MODEL_VERSION,
                "coverage": coverage,
            }
            (temp_target / "manifest.json").write_text(json.dumps(normalized_manifest, indent=2), encoding="utf-8")
            temp_target.rename(target)
        except Exception:
            if temp_target.exists():
                shutil.rmtree(temp_target)
            raise
        payload = {
            "snapshot_id": snapshot_id,
            "checksum": fingerprint,
            "broker_profile": manifest["broker_profile"],
            "cohort_id": manifest["cohort"]["cohort_id"],
            "cohort_json": manifest["cohort"],
            "versions_json": manifest.get("versions", {}),
            "contract_json": normalized_manifest,
            "coverage_json": coverage,
            "path": str(target),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repository.put_tg_snapshot(payload)
        return self.repository.get_tg_snapshot(snapshot_id) or payload

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        if manifest.get("manifest_schema_version") != SNAPSHOT_MANIFEST_VERSION:
            raise HTTPException(400, "Unsupported snapshot manifest schema")
        if manifest.get("snapshot_state") != "FINALIZED":
            raise HTTPException(400, "StrategyLab imports finalized offline snapshots only")
        required = {"broker_profile", "broker_name", "cohort", "files"}
        if missing := sorted(required - manifest.keys()):
            raise HTTPException(400, f"Snapshot manifest missing: {', '.join(missing)}")
        cohort = manifest["cohort"]
        if not {"cohort_id", "published_from_utc", "original_timezone", "assets"} <= cohort.keys():
            raise HTTPException(400, "Incomplete cohort contract")
        if not set(cohort["assets"]) <= set(SUPPORTED_ASSETS):
            raise HTTPException(400, "Cohort contains unsupported initial assets")
        files = manifest["files"]
        if not files.get("operational_sqlite") or not files.get("tick_sqlite"):
            raise HTTPException(400, "Operational and tick SQLite snapshots are required")

    @staticmethod
    def _load_json_mapping(path: Path | None) -> dict[str, Any]:
        if not path:
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise HTTPException(400, f"Expected JSON object in {path.name}")
        return payload

    @staticmethod
    def _load_deals(path: Path | None) -> dict[str, list[dict[str, Any]]]:
        if not path:
            return {}
        grouped: dict[str, list[dict[str, Any]]] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                grouped.setdefault(str(row.get("execution_id", "")), []).append(dict(row))
        return grouped

    def _read_operations(
        self,
        path: Path,
        manifest: dict[str, Any],
        policies: dict[str, Any],
        symbol_specs: dict[str, Any],
        deals: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        with readonly_sqlite(path) as connection:
            tables = _table_names(connection)
            required = {"sentinel_executions", "sentinel_execution_legs"}
            if not required <= tables:
                raise HTTPException(400, "Operational snapshot lacks required TgSignalSniper tables")
            migration = 0
            if "schema_migrations" in tables:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(schema_migrations)")}
                key = "version" if "version" in columns else "id"
                migration = int(connection.execute(f"SELECT COALESCE(MAX({key}), 0) FROM schema_migrations").fetchone()[0])
            if migration < MIN_SUPPORTED_OPERATIONAL_MIGRATION:
                raise HTTPException(400, f"Unsupported operational schema migration: {migration}")
            declared_migration = manifest.get("versions", {}).get("operational_migration")
            if declared_migration is not None and int(declared_migration) != migration:
                raise HTTPException(
                    400,
                    "Operational migration mismatch: "
                    f"manifest={declared_migration}, sqlite={migration}",
                )
            if migration >= 20:
                execution_columns = {
                    str(row[1]) for row in connection.execute(
                        "PRAGMA table_info(sentinel_executions)"
                    )
                }
                leg_columns = {
                    str(row[1]) for row in connection.execute(
                        "PRAGMA table_info(sentinel_execution_legs)"
                    )
                }
                required_execution = set(MIGRATION_20_EXECUTION_COLUMNS)
                if migration >= 21:
                    required_execution.update(MIGRATION_21_EXECUTION_COLUMNS)
                if migration >= 22:
                    required_execution.update(MIGRATION_22_EXECUTION_COLUMNS)
                missing_execution = sorted(required_execution - execution_columns)
                missing_legs = sorted(MIGRATION_20_LEG_COLUMNS - leg_columns)
                if missing_execution or missing_legs:
                    missing = [
                        *(f"sentinel_executions.{item}" for item in missing_execution),
                        *(f"sentinel_execution_legs.{item}" for item in missing_legs),
                    ]
                    raise HTTPException(
                        400,
                        f"Operational migration {migration} contract is incomplete: "
                        + ", ".join(missing),
                    )
            execution_rows = [_row_dict(row) for row in connection.execute("SELECT * FROM sentinel_executions ORDER BY id")]
            leg_rows = [_row_dict(row) for row in connection.execute("SELECT * FROM sentinel_execution_legs ORDER BY execution_id, id")]
            event_rows = []
            if "sentinel_execution_events" in tables:
                event_rows = [_row_dict(row) for row in connection.execute("SELECT * FROM sentinel_execution_events ORDER BY execution_id, id")]
            mark_counts: dict[str, int] = {}
            one_second_marks: list[dict[str, Any]] = []
            if "sentinel_execution_marks" in tables:
                mark_counts = {str(row[0]): int(row[1]) for row in connection.execute("SELECT execution_id, COUNT(*) FROM sentinel_execution_marks GROUP BY execution_id")}
                mark_columns = {
                    str(row[1]) for row in connection.execute(
                        "PRAGMA table_info(sentinel_execution_marks)"
                    )
                }
                if "price" in mark_columns:
                    one_second_marks = [
                        _row_dict(row) for row in connection.execute(
                            "SELECT * FROM sentinel_execution_marks "
                            "ORDER BY execution_id, sampled_at, id"
                        )
                    ]
            signals = {}
            if "sentinel_signals" in tables:
                signals = {str(row["id"]): _row_dict(row) for row in connection.execute("SELECT * FROM sentinel_signals")}
            messages = {}
            if "telegram_messages" in tables:
                messages = {str(row["id"]): _row_dict(row) for row in connection.execute("SELECT * FROM telegram_messages")}

        grouped_legs: dict[str, list[dict[str, Any]]] = {}
        for row in leg_rows:
            grouped_legs.setdefault(str(row.get("execution_id")), []).append(row)
        grouped_events: dict[str, list[dict[str, Any]]] = {}
        for row in event_rows:
            grouped_events.setdefault(str(row.get("execution_id")), []).append(row)
        seen: dict[str, str] = {}
        seen_events: dict[str, str] = {}
        operations: list[dict[str, Any]] = []
        external_events: list[dict[str, Any]] = []
        cohort = manifest["cohort"]
        cutoff = cohort["published_from_utc"]

        def preserve_event(event_id: str, event_type: str, execution_id: str, signal_id: str, published_at: str, asset: str, payload: dict[str, Any]) -> None:
            event_hash = sha256_bytes(canonical_json(payload).encode())
            if event_id in seen_events and seen_events[event_id] != event_hash:
                raise HTTPException(409, f"Immutable event ID collision with different content: {event_id}")
            if event_id not in seen_events:
                seen_events[event_id] = event_hash
                external_events.append({
                    "event_id": event_id, "event_type": event_type,
                    "execution_id": execution_id, "signal_id": signal_id,
                    "published_at": published_at, "asset": asset,
                    "payload": payload, "content_hash": event_hash,
                })

        for source_signal_id, source_signal in signals.items():
            source_message = messages.get(str(source_signal.get("telegram_message_id") or ""), {})
            source_published = str(source_message.get("published_at") or source_signal.get("created_at") or "")
            source_symbol = str(source_signal.get("symbol") or "")
            if not source_published or source_symbol not in cohort["assets"] or utc_datetime(source_published) < utc_datetime(cutoff):
                continue
            if source_message:
                preserve_event(f"telegram_message:{source_message.get('id')}", "TELEGRAM_MESSAGE", "", source_signal_id, source_published, source_symbol, source_message)
            preserve_event(f"signal:{source_signal_id}", "SIGNAL", "", source_signal_id, source_published, source_symbol, source_signal)

        for row in execution_rows:
            execution_id = str(row.get("id") or row.get("execution_id"))
            signal_id = str(row.get("signal_id") or "")
            signal = signals.get(signal_id, {})
            message = messages.get(str(signal.get("telegram_message_id") or ""), {})
            published_at = str(message.get("published_at") or signal.get("published_at") or signal.get("signal_published_at") or row.get("signal_published_at") or row.get("created_at") or "")
            symbol = str(row.get("provider_symbol") or row.get("symbol") or signal.get("symbol") or "")
            broker = str(row.get("broker_profile") or "")
            if not published_at or broker != manifest["broker_profile"] or symbol not in cohort["assets"] or utc_datetime(published_at) < utc_datetime(cutoff):
                continue
            if message:
                preserve_event(f"telegram_message:{message.get('id')}", "TELEGRAM_MESSAGE", execution_id, signal_id, published_at, symbol, message)
            if signal:
                preserve_event(f"signal:{signal_id}", "SIGNAL", execution_id, signal_id, published_at, symbol, signal)
            preserve_event(f"execution:{execution_id}", "EXECUTION", execution_id, signal_id, published_at, symbol, row)
            for leg in grouped_legs.get(execution_id, []):
                preserve_event(f"execution_leg:{leg.get('id')}", "EXECUTION_LEG", execution_id, signal_id, published_at, symbol, leg)
            for event in grouped_events.get(execution_id, []):
                preserve_event(f"execution_event:{event.get('id')}", "EXECUTION_EVENT", execution_id, signal_id, published_at, symbol, event)
            if row.get("entry_actual") in (None, "") or not row.get("opened_at") or not grouped_legs.get(execution_id):
                continue
            management_version = str(row.get("management_policy_version") or "")
            spec = symbol_specs.get(str(row.get("mt5_symbol") or symbol), {})
            execution_deals = deals.get(execution_id, [])
            commission = sum(float(item.get("commission") or 0) for item in execution_deals) if execution_deals else None
            swap = sum(float(item.get("swap") or 0) for item in execution_deals) if execution_deals else None
            fees = sum(float(item.get("fee") or item.get("fees") or 0) for item in execution_deals) if execution_deals else None
            execution_events = grouped_events.get(execution_id, [])
            event_text = canonical_json(execution_events).lower()
            migration_20_geometry = migration >= 20 and row.get(
                "provider_entry_price"
            ) not in (None, "")
            provider_entry = _number(
                row.get("provider_entry_price")
                if migration_20_geometry else _first_present(
                    signal.get("entry_price"), signal.get("entry"),
                    row.get("entry_price"), row.get("entry_requested"),
                ),
                0.0,
            )
            provider_stop = _number(
                row.get("provider_stop_loss")
                if migration_20_geometry else _first_present(
                    row.get("stop_loss"), signal.get("stop_loss"),
                ),
                0.0,
            )
            provider_targets = {
                label: _number(
                    row.get(f"provider_{label}")
                    if migration_20_geometry else _first_present(
                        row.get(label), signal.get(label),
                    )
                )
                for label in ("tp1", "tp2", "tp3")
            }
            venue_translation = {
                "operational_migration": migration,
                "provider_geometry_source": (
                    "MIGRATION_20_PLUS_PROVIDER_FIELDS"
                    if migration_20_geometry else "LEGACY_FROZEN_FIELDS"
                ),
                "execution_venue": str(row.get("execution_venue") or "") or None,
                "provider_entry_price": _number(row.get("provider_entry_price")),
                "provider_stop_loss": _number(row.get("provider_stop_loss")),
                "provider_tp1": _number(row.get("provider_tp1")),
                "provider_tp2": _number(row.get("provider_tp2")),
                "provider_tp3": _number(row.get("provider_tp3")),
                "venue_price_delta": _number(row.get("venue_price_delta")),
                "reference_quote_bid": _number(row.get("reference_quote_bid")),
                "reference_quote_ask": _number(row.get("reference_quote_ask")),
                "destination_quote_bid": _number(row.get("destination_quote_bid")),
                "destination_quote_ask": _number(row.get("destination_quote_ask")),
                "quote_skew_seconds": _number(row.get("quote_skew_seconds")),
                "quote_acquisition_seconds": _number(row.get("quote_acquisition_seconds")),
                "venue_order_id": str(row.get("venue_order_id") or "") or None,
                "venue_position_key": str(row.get("venue_position_key") or "") or None,
                "cohort_decision": str(row.get("cohort_decision") or "") or None,
                "cohort_decided_at": str(row.get("cohort_decided_at") or "") or None,
                "cohort_authority_execution_id": (
                    int(row["cohort_authority_execution_id"])
                    if row.get("cohort_authority_execution_id") not in (None, "") else None
                ),
                "cohort_authority_status": str(row.get("cohort_authority_status") or "") or None,
                "cohort_authority_leg_count": (
                    int(row["cohort_authority_leg_count"])
                    if row.get("cohort_authority_leg_count") not in (None, "") else None
                ),
            }
            payload = {
                "execution_id": execution_id,
                "signal_id": signal_id,
                "telegram_channel_id": str(message.get("channel_id") or signal.get("telegram_channel_id") or "") or None,
                "telegram_message_id": str(message.get("message_id") or "") or None,
                "published_at": published_at,
                "original_timezone": cohort.get("original_timezone"),
                "broker_profile": broker,
                "provider_symbol": symbol,
                "mt5_symbol": str(row.get("mt5_symbol") or symbol),
                "side": str(row.get("side") or signal.get("side") or "").upper(),
                "timeframe": str(row.get("timeframe") or signal.get("structured_timeframe") or signal.get("header_timeframe") or "UNKNOWN"),
                "strategy_lane": str(row.get("strategy_lane") or signal.get("strategy_lane") or "UNKNOWN"),
                "signal_version": str(row.get("signal_version") or signal.get("signal_version") or ""),
                "parser_version": str(row.get("parser_version") or signal.get("parser_version") or ""),
                "statistics_schema_version": str(row.get("statistics_schema_version") or ""),
                "execution_policy_version": str(row.get("execution_policy_version") or ""),
                "management_policy_version": management_version,
                "config_fingerprint": str(row.get("config_fingerprint") or ""),
                "provider_entry": provider_entry,
                "actual_fill": _number(row.get("entry_actual"), 0.0),
                "actual_exit": _number(row.get("exit_actual")),
                "entry_bid": _number(row.get("entry_bid")),
                "entry_ask": _number(row.get("entry_ask")),
                "spread": _number(row.get("entry_spread_price")),
                "initial_provider_sl": provider_stop,
                "tp1": provider_targets["tp1"],
                "tp2": provider_targets["tp2"],
                "tp3": provider_targets["tp3"],
                "risk_amount": _number(row.get("initial_risk_amount"), 0.0),
                "risk_r": 1.0,
                "requested_volume": _number(row.get("original_volume") or row.get("volume") or row.get("initial_volume"), 0.0),
                "filled_volume": sum(_number(leg.get("filled_volume") or leg.get("volume"), 0.0) or 0.0 for leg in grouped_legs.get(execution_id, [])),
                "volume_min": _number(spec.get("volume_min")),
                "volume_step": _number(spec.get("volume_step")),
                "opened_at": str(row.get("opened_at") or ""),
                "closed_at": str(row.get("closed_at") or "") or None,
                "broker_realized_net_pnl": _number(row.get("realized_pnl")),
                "close_reason": str(row.get("close_reason") or "") or None,
                "commission": commission,
                "swap": swap,
                "fees": fees,
                "manual_intervention": _parse_bool(row.get("manual_intervention")) or "manual_intervention" in event_text,
                "anomalous_state": _parse_bool(row.get("anomalous_state")) or bool(row.get("last_error")) or "anomalous_state" in event_text,
                "costs_complete": bool(execution_deals) and all(key in spec for key in ("contract_size", "volume_min", "volume_step")),
                "policy_resolved": management_version in policies and (
                    not policies[management_version].get("config_fingerprint")
                    or policies[management_version].get("config_fingerprint") == str(row.get("config_fingerprint") or "")
                ),
                "symbol_spec_resolved": all(key in spec for key in ("contract_size", "volume_min", "volume_step")),
                "symbol_spec": spec,
                "legs": grouped_legs.get(execution_id, []),
                "events": execution_events,
                "one_second_mark_count": mark_counts.get(execution_id, 0),
                "deals": execution_deals,
                "venue_translation": venue_translation,
            }
            row_hash = sha256_bytes(canonical_json(payload).encode())
            if execution_id in seen and seen[execution_id] != row_hash:
                raise HTTPException(409, f"Execution ID collision with different content: {execution_id}")
            if execution_id not in seen:
                seen[execution_id] = row_hash
                operations.append(payload)
        operation_ids = {item["execution_id"] for item in operations}
        one_second_marks = [
            item for item in one_second_marks
            if str(item.get("execution_id")) in operation_ids
            and item.get("price") not in (None, "")
        ]
        return operations, external_events, one_second_marks

    def _verify_tick_archive(self, path: Path) -> dict[str, dict[str, Any]]:
        with readonly_sqlite(path) as connection:
            tables = _table_names(connection)
            if not {"archive_meta", "archived_executions", "tick_chunks"} <= tables:
                raise HTTPException(400, "Unknown tick archive schema")
            meta = {str(row[0]): str(row[1]) for row in connection.execute("SELECT key, value FROM archive_meta")}
            schema = int(meta.get("schema_version", "0"))
            if schema != ARCHIVE_SCHEMA_VERSION:
                raise HTTPException(400, f"Unsupported tick archive schema: {schema}")
            archive = {str(row["execution_id"]): _row_dict(row) for row in connection.execute("SELECT * FROM archived_executions")}
            ordinal = 0
            for chunk in connection.execute("SELECT * FROM tick_chunks ORDER BY execution_id, range_start_msc, id"):
                try:
                    decoded = decode_tick_payload(chunk["payload"], str(chunk["checksum"]), str(chunk["codec"]), ordinal)
                except ValueError as exc:
                    raise HTTPException(400, str(exc)) from exc
                if len(decoded) != int(chunk["tick_count"]):
                    raise HTTPException(400, f"Tick count mismatch in chunk {chunk['id']}")
                ordinal += len(decoded)
        return archive

    @staticmethod
    def _coverage_report(operations: list[dict[str, Any]], archive: dict[str, dict[str, Any]]) -> dict[str, Any]:
        assets: dict[str, dict[str, Any]] = {}
        for asset in SUPPORTED_ASSETS:
            selected = [operation for operation in operations if operation["provider_symbol"] == asset]
            reasons: dict[str, int] = {}
            complete = 0
            with_ticks = 0
            requiring_backfill: list[str] = []
            for operation in selected:
                record = archive.get(operation["execution_id"])
                if record and int(record.get("tick_count") or 0) > 0:
                    with_ticks += 1
                reason = None
                if not record:
                    reason = "ONE_SECOND_MARKS_ONLY" if operation.get("one_second_mark_count") else "MISSING_TICK_ARCHIVE"
                elif int(record.get("tick_count") or 0) <= 0:
                    reason = "NO_EXACT_TICKS"
                elif str(record.get("status")) != "COMPLETE":
                    reason = "ARCHIVE_NOT_COMPLETE"
                elif int(
                    record.get("coverage_gap_count")
                    or record.get("gap_count")
                    or 0
                ) != 0:
                    reason = "ARCHIVE_GAPS"
                elif not record.get("coverage_start_at") or (operation.get("opened_at") and utc_datetime(str(record["coverage_start_at"])) > utc_datetime(operation["opened_at"])):
                    reason = "ENTRY_OUTSIDE_COVERAGE"
                elif operation.get("closed_at") and (not record.get("coverage_end_at") or utc_datetime(str(record["coverage_end_at"])) < utc_datetime(operation["closed_at"])):
                    reason = "CLOSE_OUTSIDE_COVERAGE"
                else:
                    complete += 1
                if reason:
                    reasons[reason] = reasons.get(reason, 0) + 1
                    requiring_backfill.append(operation["execution_id"])
            assets[asset] = {
                "operations": len(selected),
                "closed_operations": sum(bool(item.get("closed_at")) for item in selected),
                "operations_with_ticks": with_ticks,
                "complete_coverage": complete,
                "censored": len(selected) - complete,
                "excluded": sum(item["manual_intervention"] or item["anomalous_state"] for item in selected),
                "exclusion_reasons": reasons,
                "promotion_coverage_percent": round(100 * complete / len(selected), 2) if selected else 0.0,
                "requires_backfill_execution_ids": requiring_backfill,
            }
        return {"assets": assets, "total_operations": len(operations)}

    @staticmethod
    def _write_canonical(
        target: Path,
        manifest: dict[str, Any],
        operations: list[dict[str, Any]],
        external_events: list[dict[str, Any]],
        one_second_marks: list[dict[str, Any]],
        tick_source: Path,
        policies: dict[str, Any],
        symbol_specs: dict[str, Any],
        deals: dict[str, list[dict[str, Any]]],
    ) -> None:
        connection = sqlite3.connect(target)
        try:
            connection.executescript(
                """
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE operations (execution_id TEXT PRIMARY KEY, asset TEXT NOT NULL, opened_at TEXT NOT NULL, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL);
                CREATE TABLE external_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, execution_id TEXT, signal_id TEXT, published_at TEXT NOT NULL, asset TEXT NOT NULL, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL);
                CREATE TABLE tick_coverage (execution_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
                CREATE TABLE tick_chunks (id INTEGER PRIMARY KEY, execution_id TEXT NOT NULL, range_start_msc INTEGER NOT NULL, range_end_msc INTEGER NOT NULL, tick_count INTEGER NOT NULL, codec TEXT NOT NULL, checksum TEXT NOT NULL, payload BLOB NOT NULL);
                CREATE TABLE one_second_marks (execution_id TEXT NOT NULL, sampled_at TEXT NOT NULL, price REAL NOT NULL, floating_pnl REAL, risk_amount REAL, pnl_r REAL, volume REAL, status TEXT, source_ordinal INTEGER NOT NULL, PRIMARY KEY(execution_id, sampled_at, source_ordinal));
                CREATE TABLE policies (version TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
                CREATE TABLE symbol_specs (symbol TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
                CREATE TABLE deals (execution_id TEXT NOT NULL, ordinal INTEGER NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(execution_id, ordinal));
                """
            )
            connection.executemany("INSERT INTO metadata VALUES (?, ?)", [("manifest", canonical_json(manifest)), ("model_version", MODEL_VERSION)])
            for operation in operations:
                encoded = canonical_json(operation)
                connection.execute("INSERT INTO operations VALUES (?, ?, ?, ?, ?)", (operation["execution_id"], operation["provider_symbol"], operation["opened_at"], encoded, sha256_bytes(encoded.encode())))
            for event in external_events:
                connection.execute("INSERT INTO external_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (event["event_id"], event["event_type"], event["execution_id"], event["signal_id"], event["published_at"], event["asset"], canonical_json(event["payload"]), event["content_hash"]))
            for ordinal, mark in enumerate(one_second_marks, start=1):
                connection.execute(
                    "INSERT INTO one_second_marks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(mark["execution_id"]), str(mark["sampled_at"]),
                        float(mark["price"]), _number(mark.get("floating_pnl")),
                        _number(mark.get("risk_amount")), _number(mark.get("pnl_r")),
                        _number(mark.get("volume")), str(mark.get("status") or ""),
                        ordinal,
                    ),
                )
            with readonly_sqlite(tick_source) as source:
                for row in source.execute("SELECT * FROM archived_executions"):
                    connection.execute("INSERT OR REPLACE INTO tick_coverage VALUES (?, ?)", (str(row["execution_id"]), canonical_json(_row_dict(row))))
                for ordinal, row in enumerate(source.execute("SELECT * FROM tick_chunks ORDER BY execution_id, range_start_msc, id"), start=1):
                    connection.execute("INSERT INTO tick_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (ordinal, str(row["execution_id"]), row["range_start_msc"], row["range_end_msc"], row["tick_count"], row["codec"], row["checksum"], row["payload"]))
            for version, policy in policies.items():
                connection.execute("INSERT INTO policies VALUES (?, ?)", (version, canonical_json(policy)))
            for symbol, spec in symbol_specs.items():
                connection.execute("INSERT INTO symbol_specs VALUES (?, ?)", (symbol, canonical_json(spec)))
            for execution_id, rows in deals.items():
                for ordinal, row in enumerate(rows):
                    connection.execute("INSERT INTO deals VALUES (?, ?, ?)", (execution_id, ordinal, canonical_json(row)))
            connection.commit()
        finally:
            connection.close()
