from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import struct
import tempfile
import unittest
import zlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.config import Settings
from app.storage import Repository
from app.tg_import import SUPPORTED_OPERATIONAL_MIGRATIONS, TICK_CODEC, TgSnapshotImporter, decode_tick_payload, sha256_file
from app.tg_lab import TgManagementLabService
from app.tg_models import ManagementPolicy, TargetGeometryPolicy, Tick
from app.tg_replay import TgSignalReplayEngine
from app.tg_validation import chronological_split, dual_promotion_improvement, full_promotion_improvement, paired_block_bootstrap_equivalence


TICK_STRUCT = struct.Struct("<qddI")


def _compressed_ticks(rows: list[tuple[int, float, float, int]]) -> tuple[bytes, str]:
    payload = zlib.compress(b"".join(TICK_STRUCT.pack(*row) for row in rows))
    return payload, hashlib.sha256(payload).hexdigest()


def build_tg_package(root: Path, count: int = 1, *, schema: int = 19, actual_pnl: float = 17.0, gap: int = 0) -> Path:
    package = root / "package"
    package.mkdir()
    operational = package / "operational.sqlite3"
    connection = sqlite3.connect(operational)
    connection.executescript(
        """
        CREATE TABLE schema_migrations (version INTEGER);
        CREATE TABLE telegram_messages (
          id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, published_at TEXT
        );
        CREATE TABLE sentinel_signals (
          id TEXT PRIMARY KEY, telegram_message_id INTEGER, parser_version TEXT,
          structured_timeframe TEXT, symbol TEXT, side TEXT, entry_price REAL,
          stop_loss REAL, tp1 REAL, tp2 REAL, tp3 REAL
        );
        CREATE TABLE sentinel_executions (
          id TEXT, signal_id TEXT, status TEXT, runtime_mode TEXT,
          provider_symbol TEXT, mt5_symbol TEXT, side TEXT, order_kind TEXT,
          entry_price REAL, entry_actual REAL, stop_loss REAL, tp1 REAL, tp2 REAL, tp3 REAL,
          volume REAL, original_volume REAL, initial_risk_amount REAL,
          realized_pnl REAL, opened_at TEXT, closed_at TEXT, close_reason TEXT,
          strategy_lane TEXT, statistics_schema_version TEXT, signal_version TEXT,
          execution_policy_version TEXT, management_policy_version TEXT,
          broker_profile TEXT, config_fingerprint TEXT,
          entry_bid REAL, entry_ask REAL, entry_spread_price REAL,
          manual_intervention INTEGER, anomalous_state INTEGER, last_error TEXT,
          created_at TEXT
        );
        CREATE TABLE sentinel_execution_legs (
          id TEXT, execution_id TEXT, leg_index INTEGER, target_name TEXT,
          fraction REAL, volume REAL, take_profit REAL, status TEXT,
          order_ticket TEXT, position_ticket TEXT, realized_pnl REAL
        );
        CREATE TABLE sentinel_execution_events (
          id INTEGER, execution_id TEXT, event_type TEXT, message TEXT,
          details_json TEXT, created_at TEXT
        );
        """
    )
    connection.execute("INSERT INTO schema_migrations VALUES (?)", (schema,))
    base = datetime(2026, 8, 10, 5, 1, tzinfo=UTC)
    execution_times: dict[str, tuple[str, str, int]] = {}
    for index in range(count):
        execution_id = f"exec-{index:03d}"
        opened = base + timedelta(hours=index * 2)
        closed = opened + timedelta(seconds=3)
        published = opened - timedelta(minutes=1)
        connection.execute("INSERT INTO telegram_messages VALUES (?,?,?,?)", (index + 1, "-1003998783404", str(9000 + index), published.isoformat()))
        connection.execute("INSERT INTO sentinel_signals VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"sig-{index:03d}", index + 1, "parser-v1", "M15" if index % 2 == 0 else "H1", "XAUUSD", "BUY", 100.0, 99.0, 101.0, 102.0, 103.0))
        values = (
            execution_id, f"sig-{index:03d}", "CLOSED", "demo", "XAUUSD", "XAUUSD",
            "BUY", "MARKET", 100.0, 100.0, 99.0, 101.0, 102.0, 103.0, 0.0, 1.0, 10.0,
            actual_pnl, opened.isoformat(), closed.isoformat(), "TP3",
            "FAST" if index % 2 == 0 else "CORE", "tgs-stats-v5", "signal-v1",
            "exec-v1", "management-v1", "AXI_DEMO_PRO", "fingerprint",
            99.9, 100.0, 0.1, 0, 0, "", published.isoformat(),
        )
        connection.execute("INSERT INTO sentinel_executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        for leg_index, (fraction, target) in enumerate(((0.5, 101.0), (0.3, 102.0), (0.2, 103.0)), start=1):
            connection.execute("INSERT INTO sentinel_execution_legs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"{execution_id}-leg-{leg_index}", execution_id, leg_index, f"TP{leg_index}", fraction, fraction, target, "CLOSED", str(1000 + index * 10 + leg_index), str(2000 + index * 10 + leg_index), None))
        execution_times[execution_id] = (opened.isoformat(), closed.isoformat(), int(opened.timestamp() * 1000))
    if schema >= 20:
        migration_20_columns = (
            ("execution_venue", "TEXT"), ("provider_entry_price", "REAL"),
            ("provider_stop_loss", "REAL"), ("provider_tp1", "REAL"),
            ("provider_tp2", "REAL"), ("provider_tp3", "REAL"),
            ("venue_price_delta", "REAL"), ("reference_quote_bid", "REAL"),
            ("reference_quote_ask", "REAL"), ("destination_quote_bid", "REAL"),
            ("destination_quote_ask", "REAL"), ("quote_skew_seconds", "REAL"),
            ("quote_acquisition_seconds", "REAL"), ("venue_order_id", "TEXT"),
            ("venue_position_key", "TEXT"),
        )
        for name, column_type in migration_20_columns:
            connection.execute(
                f"ALTER TABLE sentinel_executions ADD COLUMN {name} {column_type}"
            )
        connection.execute(
            "ALTER TABLE sentinel_execution_legs ADD COLUMN venue_order_id TEXT"
        )
        connection.execute(
            """
            UPDATE sentinel_executions SET
              execution_venue='AXI_DEMO_PRO', provider_entry_price=100.25,
              provider_stop_loss=99.25, provider_tp1=101.25,
              provider_tp2=102.25, provider_tp3=103.25,
              venue_price_delta=0.25, reference_quote_bid=100.20,
              reference_quote_ask=100.21, destination_quote_bid=100.24,
              destination_quote_ask=100.25, quote_skew_seconds=0.2,
              quote_acquisition_seconds=0.05, venue_order_id='venue-order',
              venue_position_key='venue-position'
            """
        )
        connection.execute(
            "UPDATE sentinel_execution_legs SET venue_order_id='venue-leg-' || id"
        )
    if schema >= 21:
        connection.execute("ALTER TABLE sentinel_executions ADD COLUMN cohort_decision TEXT")
        connection.execute("ALTER TABLE sentinel_executions ADD COLUMN cohort_decided_at TEXT")
        connection.execute("ALTER TABLE sentinel_executions ADD COLUMN cohort_authority_execution_id INTEGER")
        connection.execute("ALTER TABLE sentinel_executions ADD COLUMN cohort_authority_status TEXT")
        connection.execute(
            "UPDATE sentinel_executions SET cohort_decision='APPROVED', "
            "cohort_decided_at=opened_at, cohort_authority_execution_id=17, "
            "cohort_authority_status='APPROVED'"
        )
    if schema >= 22:
        connection.execute("ALTER TABLE sentinel_executions ADD COLUMN cohort_authority_leg_count INTEGER")
        connection.execute("UPDATE sentinel_executions SET cohort_authority_leg_count=2")
    connection.commit()
    connection.close()

    archive = package / "ticks.sqlite3"
    connection = sqlite3.connect(archive)
    connection.executescript(
        """
        CREATE TABLE archive_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE archived_executions (
          execution_id TEXT PRIMARY KEY, broker_profile TEXT, symbol TEXT,
          opened_at TEXT, archive_start_at TEXT, closed_at TEXT,
          broker_clock_offset_seconds INTEGER, config_fingerprint TEXT,
          status TEXT, tick_count INTEGER, compressed_bytes INTEGER,
          coverage_start_at TEXT, coverage_end_at TEXT, gap_count INTEGER,
          error TEXT, updated_at TEXT
        );
        CREATE TABLE tick_chunks (
          id INTEGER PRIMARY KEY, execution_id TEXT, range_start_msc INTEGER,
          range_end_msc INTEGER, tick_count INTEGER, codec TEXT, checksum TEXT,
          payload BLOB, created_at TEXT
        );
        """
    )
    connection.execute("INSERT INTO archive_meta VALUES ('schema_version', '2')")
    for index, (execution_id, (opened, closed, start)) in enumerate(execution_times.items(), start=1):
        rows = [(start, 99.9, 100.0, 0), (start + 1000, 101.0, 101.1, 0), (start + 2000, 102.0, 102.1, 0), (start + 3000, 103.0, 103.1, 0)]
        payload, checksum = _compressed_ticks(rows)
        connection.execute("INSERT INTO archived_executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (execution_id, "AXI_DEMO_PRO", "XAUUSD", opened, opened, closed, 0, "fingerprint", "COMPLETE", 4, len(payload), opened, closed, gap, "", closed))
        connection.execute("INSERT INTO tick_chunks VALUES (?,?,?,?,?,?,?,?,?)", (index, execution_id, start, start + 3000, 4, TICK_CODEC, checksum, payload, closed))
    connection.commit()
    connection.close()

    policies = {
        "management-v1": {
            "policy_id": "baseline-management-v1", "parent_policy_id": None,
            "management_policy_version": "management-v1", "partials": [0.5, 0.3, 0.2],
            "tp1_action": "breakeven", "breakeven_offset_price": 0.0,
            "tp2_action": "stop_to_tp1",
        }
    }
    (package / "policies.json").write_text(json.dumps(policies), encoding="utf-8")
    (package / "symbol_specs.json").write_text(json.dumps({"XAUUSD": {"contract_size": 10, "volume_min": 0.1, "volume_step": 0.1, "point_size": 0.01, "trade_tick_size": 0.01, "digits": 2, "source": "broker_snapshot"}}), encoding="utf-8")
    with (package / "deals.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["execution_id", "profit", "commission", "swap", "fee"])
        writer.writeheader()
        for execution_id in execution_times:
            writer.writerow({"execution_id": execution_id, "profit": actual_pnl, "commission": 0, "swap": 0, "fee": 0})
    manifest = {
        "manifest_schema_version": 1,
        "snapshot_state": "FINALIZED",
        "broker_name": "Axi Demo Pro",
        "broker_profile": "AXI_DEMO_PRO",
        "cohort": {"cohort_id": "axi-demo-pro-20260810", "published_from_utc": "2026-08-10T05:00:00+00:00", "original_timezone": "America/Bogota", "assets": ["XAUUSD", "EURUSD", "BTCUSD", "NASDAQ", "US30"]},
        "versions": {"operational_migration": schema, "tick_archive_schema": 2},
        "files": {"operational_sqlite": "operational.sqlite3", "tick_sqlite": "ticks.sqlite3", "policy_registry": "policies.json", "symbol_specs": "symbol_specs.json", "deals_csv": "deals.csv"},
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return package


def direct_operation(side: str = "BUY") -> dict:
    return {
        "execution_id": "direct", "side": side, "provider_entry": 100.0, "actual_fill": 100.0,
        "initial_provider_sl": 99.0 if side == "BUY" else 101.0,
        "tp1": 101.0 if side == "BUY" else 99.0,
        "tp2": 102.0 if side == "BUY" else 98.0,
        "tp3": 103.0 if side == "BUY" else 97.0,
        "filled_volume": 1.0, "requested_volume": 1.0, "volume_min": 0.1,
        "volume_step": 0.1, "symbol_spec_resolved": True,
        "symbol_spec": {"contract_size": 10, "trade_tick_size": 0.01, "digits": 2}, "costs_complete": True,
        "commission": 0.0, "swap": 0.0, "fees": 0.0, "risk_amount": 10.0,
        "opened_at": "2026-08-10T05:00:00+00:00", "closed_at": "2026-08-10T05:00:03+00:00",
        "legs": [
            {"id": "l1", "native_target": "TP1", "target_price": 101 if side == "BUY" else 99, "filled_volume": 0.5},
            {"id": "l2", "native_target": "TP2", "target_price": 102 if side == "BUY" else 98, "filled_volume": 0.3},
            {"id": "l3", "native_target": "TP3", "target_price": 103 if side == "BUY" else 97, "filled_volume": 0.2},
        ],
    }


def baseline_policy() -> ManagementPolicy:
    return ManagementPolicy("baseline", None, "management-v1")


def complete_coverage() -> dict:
    return {
        "status": "COMPLETE", "gap_count": 0,
        "coverage_start_at": "2026-08-10T05:00:00+00:00",
        "coverage_end_at": "2026-08-10T05:00:03+00:00",
        "horizon_end_at": "2026-08-10T05:00:03+00:00",
        "horizon_reason": "ORIGINAL_TP3", "horizon_complete": True,
    }


class TgManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = Repository(self.root / "lab.sqlite3")
        self.importer = TgSnapshotImporter(self.repo, self.root / "snapshots")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_import_is_read_only_idempotent_and_preserves_source_files(self) -> None:
        package = build_tg_package(self.root)
        before = {path.name: (sha256_file(path), path.stat().st_mtime_ns) for path in package.iterdir() if path.is_file()}
        first = self.importer.import_package(package)
        second = self.importer.import_package(package)
        after = {path.name: (sha256_file(path), path.stat().st_mtime_ns) for path in package.iterdir() if path.is_file()}
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(before, after)
        self.assertFalse(any(package.glob("*.sqlite3-wal")))
        self.assertEqual(len(self.repo.list_tg_snapshots()), 1)
        canonical = Path(first["path"]) / "snapshot.sqlite3"
        connection = sqlite3.connect(canonical)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM external_events").fetchone()[0], 6)
        connection.close()

    def test_operational_migrations_16_through_22_are_explicitly_supported(self) -> None:
        self.assertEqual(SUPPORTED_OPERATIONAL_MIGRATIONS, set(range(16, 23)))
        for migration in range(16, 23):
            migration_root = self.root / f"migration-{migration}"
            migration_root.mkdir()
            package = build_tg_package(migration_root, schema=migration)
            snapshot = self.importer.import_package(package)
            self.assertEqual(
                snapshot["versions_json"]["operational_migration"], migration
            )

    def test_future_additive_operational_migration_is_capability_compatible(self) -> None:
        package = build_tg_package(self.root, schema=23)
        snapshot = self.importer.import_package(package)
        self.assertEqual(snapshot["versions_json"]["operational_migration"], 23)
        canonical = Path(snapshot["path"]) / "snapshot.sqlite3"
        connection = sqlite3.connect(canonical)
        operation = json.loads(connection.execute(
            "SELECT payload_json FROM operations WHERE execution_id='exec-000'"
        ).fetchone()[0])
        connection.close()
        self.assertEqual(operation["venue_translation"]["operational_migration"], 23)
        self.assertEqual(operation["provider_entry"], 100.25)

    def test_migration_20_imports_venue_metadata_and_frozen_provider_geometry(self) -> None:
        package = build_tg_package(self.root, schema=20)
        source_hash = sha256_file(package / "operational.sqlite3")
        snapshot = self.importer.import_package(package)
        self.assertEqual(source_hash, sha256_file(package / "operational.sqlite3"))
        canonical = Path(snapshot["path"]) / "snapshot.sqlite3"
        connection = sqlite3.connect(canonical)
        operation = json.loads(connection.execute(
            "SELECT payload_json FROM operations WHERE execution_id='exec-000'"
        ).fetchone()[0])
        connection.close()
        self.assertEqual(operation["actual_fill"], 100.0)
        self.assertEqual(operation["provider_entry"], 100.25)
        self.assertEqual(operation["initial_provider_sl"], 99.25)
        self.assertEqual(
            (operation["tp1"], operation["tp2"], operation["tp3"]),
            (101.25, 102.25, 103.25),
        )
        metadata = operation["venue_translation"]
        self.assertEqual(metadata["operational_migration"], 20)
        self.assertEqual(
            metadata["provider_geometry_source"],
            "MIGRATION_20_PLUS_PROVIDER_FIELDS",
        )
        self.assertEqual(metadata["execution_venue"], "AXI_DEMO_PRO")
        self.assertEqual(metadata["venue_price_delta"], 0.25)
        self.assertEqual(metadata["reference_quote_bid"], 100.20)
        self.assertEqual(metadata["destination_quote_ask"], 100.25)
        self.assertEqual(metadata["quote_skew_seconds"], 0.2)
        self.assertEqual(metadata["quote_acquisition_seconds"], 0.05)
        self.assertEqual(metadata["venue_order_id"], "venue-order")
        self.assertEqual(metadata["venue_position_key"], "venue-position")
        self.assertTrue(all(leg["venue_order_id"] for leg in operation["legs"]))

    def test_migration_22_preserves_cumulative_geometry_and_cohort_metadata(self) -> None:
        package = build_tg_package(self.root, schema=22)
        snapshot = self.importer.import_package(package)
        connection = sqlite3.connect(Path(snapshot["path"]) / "snapshot.sqlite3")
        operation = json.loads(connection.execute(
            "SELECT payload_json FROM operations WHERE execution_id='exec-000'"
        ).fetchone()[0])
        connection.close()
        self.assertEqual(operation["provider_entry"], 100.25)
        metadata = operation["venue_translation"]
        self.assertEqual(metadata["operational_migration"], 22)
        self.assertEqual(metadata["provider_geometry_source"], "MIGRATION_20_PLUS_PROVIDER_FIELDS")
        self.assertEqual(metadata["cohort_decision"], "APPROVED")
        self.assertEqual(metadata["cohort_authority_execution_id"], 17)
        self.assertEqual(metadata["cohort_authority_status"], "APPROVED")
        self.assertEqual(metadata["cohort_authority_leg_count"], 2)

    def test_migration_20_rejects_incomplete_columns_and_manifest_mismatch(self) -> None:
        incomplete_root = self.root / "incomplete-20"
        incomplete_root.mkdir()
        incomplete = build_tg_package(incomplete_root, schema=19)
        connection = sqlite3.connect(incomplete / "operational.sqlite3")
        connection.execute("UPDATE schema_migrations SET version=20")
        connection.commit(); connection.close()
        manifest_path = incomplete / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["versions"]["operational_migration"] = 20
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(HTTPException, "migration 20 contract is incomplete"):
            self.importer.import_package(incomplete)

        mismatch_root = self.root / "mismatch-20"
        mismatch_root.mkdir()
        mismatch = build_tg_package(mismatch_root, schema=20)
        mismatch_manifest_path = mismatch / "manifest.json"
        mismatch_manifest = json.loads(
            mismatch_manifest_path.read_text(encoding="utf-8")
        )
        mismatch_manifest["versions"]["operational_migration"] = 19
        mismatch_manifest_path.write_text(
            json.dumps(mismatch_manifest), encoding="utf-8"
        )
        with self.assertRaisesRegex(HTTPException, "migration mismatch"):
            self.importer.import_package(mismatch)

    def test_legacy_provider_geometry_is_not_reinterpreted(self) -> None:
        package = build_tg_package(self.root, schema=19)
        snapshot = self.importer.import_package(package)
        connection = sqlite3.connect(Path(snapshot["path"]) / "snapshot.sqlite3")
        operation = json.loads(connection.execute(
            "SELECT payload_json FROM operations WHERE execution_id='exec-000'"
        ).fetchone()[0])
        connection.close()
        self.assertEqual(operation["provider_entry"], 100.0)
        self.assertEqual(operation["initial_provider_sl"], 99.0)
        self.assertEqual(
            operation["venue_translation"]["provider_geometry_source"],
            "LEGACY_FROZEN_FIELDS",
        )

    def test_import_rejects_unconsolidated_wal_and_unknown_schema(self) -> None:
        package = build_tg_package(self.root, schema=15)
        with self.assertRaises(HTTPException):
            self.importer.import_package(package)
        package = self.root / "wal-case"
        package.mkdir()
        source = build_tg_package(package)
        Path(f"{source / 'operational.sqlite3'}-wal").write_bytes(b"pending")
        with self.assertRaises(HTTPException):
            TgSnapshotImporter(self.repo, self.root / "other").import_package(source)

    def test_import_rejects_id_collision_and_bad_chunk_checksum(self) -> None:
        package = build_tg_package(self.root)
        connection = sqlite3.connect(package / "operational.sqlite3")
        row = list(connection.execute("SELECT * FROM sentinel_executions LIMIT 1").fetchone())
        row[21] = "ALTERED"
        connection.execute("INSERT INTO sentinel_executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        connection.commit()
        connection.close()
        with self.assertRaises(HTTPException) as raised:
            self.importer.import_package(package)
        self.assertEqual(raised.exception.status_code, 409)

        other = self.root / "bad-checksum"
        other.mkdir()
        package = build_tg_package(other)
        connection = sqlite3.connect(package / "ticks.sqlite3")
        connection.execute("UPDATE tick_chunks SET checksum = ?", ("0" * 64,))
        connection.commit()
        connection.close()
        with self.assertRaises(HTTPException):
            self.importer.import_package(package)

    def test_checksum_and_exact_tick_decoding_with_source_ordinal(self) -> None:
        rows = [(10, 1.1, 1.2, 3), (10, 1.0, 1.1, 4)]
        payload, checksum = _compressed_ticks(rows)
        decoded = decode_tick_payload(payload, checksum, ordinal_start=7)
        self.assertEqual([(item.time_msc, item.bid, item.ask, item.flags, item.source_ordinal) for item in decoded], [(10, 1.1, 1.2, 3, 7), (10, 1.0, 1.1, 4, 8)])
        with self.assertRaises(ValueError):
            decode_tick_payload(payload, "0" * 64)

    def test_buy_closes_on_bid_and_sell_closes_on_ask(self) -> None:
        engine = TgSignalReplayEngine()
        buy_ticks = [Tick(1786338000000, 100, 100.1, 0, 0), Tick(1786338001000, 101, 101.2, 0, 1), Tick(1786338002000, 102, 102.2, 0, 2), Tick(1786338003000, 103, 103.2, 0, 3)]
        buy = engine.replay(direct_operation("BUY"), buy_ticks, complete_coverage(), baseline_policy())
        self.assertEqual([fill.price for fill in buy.fills], [101, 102, 103])
        sell_ticks = [Tick(1786338000000, 99.9, 100, 0, 0), Tick(1786338001000, 98.8, 99, 0, 1), Tick(1786338002000, 97.8, 98, 0, 2), Tick(1786338003000, 96.8, 97, 0, 3)]
        sell = engine.replay(direct_operation("SELL"), sell_ticks, complete_coverage(), baseline_policy())
        self.assertEqual([fill.price for fill in sell.fills], [99, 98, 97])

    def test_same_millisecond_uses_source_order_and_stable_leg_order(self) -> None:
        engine = TgSignalReplayEngine()
        ticks = [Tick(1786338000000, 100, 100.1, 0, 0), Tick(1786338001000, 101, 101.1, 0, 1), Tick(1786338001000, 100, 100.1, 0, 2)]
        operation = direct_operation()
        operation["closed_at"] = "2026-08-10T05:00:01+00:00"
        coverage = dict(complete_coverage(), coverage_end_at=operation["closed_at"])
        result = engine.replay(operation, ticks, coverage, baseline_policy())
        self.assertEqual(result.fills[0].reason, "TP1")
        self.assertEqual(result.fills[1].reason, "SL")

    def test_partials_and_unrepresentable_volume_fallback(self) -> None:
        engine = TgSignalReplayEngine()
        operation = direct_operation()
        legs, valid = engine._build_legs(operation, replace(baseline_policy(), parent_policy_id="baseline"), 1.0, 0.1, 0.1)
        self.assertTrue(valid)
        self.assertEqual([round(item["volume"], 2) for item in legs], [0.5, 0.3, 0.2])
        legs, valid = engine._build_legs(operation, replace(baseline_policy(), parent_policy_id="baseline"), 0.2, 0.1, 0.1)
        self.assertTrue(valid)
        self.assertEqual([item["volume"] for item in legs], [0.2])

    def test_tp1_be_tp2_stop_to_tp1_and_monotonic_trailing(self) -> None:
        engine = TgSignalReplayEngine()
        ticks = [Tick(1786338000000, 100, 100.1, 0, 0), Tick(1786338001000, 101, 101.1, 0, 1), Tick(1786338002000, 102, 102.1, 0, 2), Tick(1786338003000, 101.0, 101.1, 0, 3)]
        baseline = engine.replay(direct_operation(), ticks, complete_coverage(), baseline_policy())
        self.assertTrue(any(item["event"] == "BREAKEVEN_AFTER_TP1" for item in baseline.milestones))
        self.assertTrue(any(item["event"] == "STOP_TO_TP1_AFTER_TP2" for item in baseline.milestones))
        self.assertEqual(baseline.fills[-1].reason, "SL")
        self.assertEqual(baseline.fills[-1].price, 101.0)
        policy = replace(baseline_policy(), trailing_activation_r=1.0, trailing_distance_r=0.5, trailing_step_r=0.0)
        result = engine.replay(direct_operation(), ticks, complete_coverage(), policy)
        stops = [item["stop"] for item in result.milestones if "stop" in item]
        self.assertEqual(stops, sorted(stops))

    def test_early_be_mfe_has_no_lookahead_and_cost_slippage_apply(self) -> None:
        engine = TgSignalReplayEngine()
        policy = replace(baseline_policy(), early_breakeven_activation_r=0.5, mfe_protect_activation_r=0.5, mfe_protect_fraction=0.5, exit_slippage_price=0.1)
        operation = direct_operation()
        operation["commission"] = -1.0
        ticks = [Tick(1786338000000, 100, 100.1, 0, 0), Tick(1786338001000, 100.5, 100.6, 0, 1), Tick(1786338002000, 100.2, 100.3, 0, 2)]
        operation["closed_at"] = "2026-08-10T05:00:02+00:00"
        coverage = dict(complete_coverage(), coverage_end_at=operation["closed_at"])
        result = engine.replay(operation, ticks, coverage, policy)
        self.assertEqual(result.fills[0].reason, "SL")
        self.assertLess(result.net_pnl, sum(fill.gross_pnl for fill in result.fills))

    def test_candidate_replay_can_continue_after_actual_close(self) -> None:
        engine = TgSignalReplayEngine()
        operation = direct_operation()
        operation["closed_at"] = "2026-08-10T05:00:01+00:00"
        ticks = [
            Tick(1786338000000, 100, 100.1, 0, 0),
            Tick(1786338001000, 100.5, 100.6, 0, 1),
            Tick(1786338002000, 101, 101.1, 0, 2),
            Tick(1786338003000, 102, 102.1, 0, 3),
            Tick(1786338004000, 103, 103.1, 0, 4),
        ]
        coverage = dict(
            complete_coverage(),
            coverage_end_at="2026-08-10T05:00:04+00:00",
            horizon_end_at="2026-08-10T05:00:04+00:00",
        )
        result = engine.replay(operation, ticks, coverage, baseline_policy())
        self.assertEqual(result.status, "COMPLETE")
        self.assertEqual([fill.reason for fill in result.fills], ["TP1", "TP2", "TP3"])

    def test_forced_close_terminalizes_remaining_volume_at_horizon(self) -> None:
        engine = TgSignalReplayEngine()
        operation = direct_operation()
        operation["closed_at"] = "2026-08-10T05:00:01+00:00"
        ticks = [
            Tick(1786338000000, 100, 100.1, 0, 0),
            Tick(1786338001000, 100.5, 100.6, 0, 1),
            Tick(1786338002000, 100.6, 100.7, 0, 2),
        ]
        coverage = dict(
            complete_coverage(),
            coverage_end_at="2026-08-10T05:00:02+00:00",
            horizon_end_at="2026-08-10T05:00:02+00:00",
            horizon_reason="DAILY_FORCED_CLOSE",
        )
        result = engine.replay(operation, ticks, coverage, baseline_policy())
        self.assertEqual(result.status, "COMPLETE")
        self.assertTrue(result.fills)
        self.assertTrue(all(
            fill.reason == "DAILY_FORCED_CLOSE" for fill in result.fills
        ))

    def test_forced_close_uses_broker_actual_exit_when_available(self) -> None:
        engine = TgSignalReplayEngine()
        operation = direct_operation()
        operation.update(
            closed_at="2026-08-10T05:00:02+00:00",
            close_reason="DAILY_PAUSE",
            actual_exit=100.25,
        )
        ticks = [
            Tick(1786338000000, 100, 100.1, 0, 0),
            Tick(1786338002000, 99.5, 99.6, 0, 1),
        ]
        coverage = dict(
            complete_coverage(),
            coverage_end_at="2026-08-10T05:00:02+00:00",
            horizon_end_at="2026-08-10T05:00:02+00:00",
            horizon_reason="DAILY_FORCED_CLOSE",
        )
        result = engine.replay(operation, ticks, coverage, baseline_policy())
        self.assertEqual({fill.price for fill in result.fills}, {100.25})

    def test_native_tp_uses_requested_level_not_later_tick_overshoot(self) -> None:
        engine = TgSignalReplayEngine()
        ticks = [
            Tick(1786338000000, 100, 100.1, 0, 0),
            Tick(1786338001000, 101.5, 101.6, 0, 1),
            Tick(1786338002000, 102.5, 102.6, 0, 2),
            Tick(1786338003000, 103.5, 103.6, 0, 3),
        ]
        result = engine.replay(
            direct_operation(), ticks, complete_coverage(), baseline_policy(),
        )
        self.assertEqual([fill.price for fill in result.fills], [101.0, 102.0, 103.0])

    def test_baseline_uses_exact_broker_deals_including_entry_costs(self) -> None:
        operation = direct_operation()
        operation["deals"] = [
            {"ticket": 1, "entry": 0, "volume": 1.0, "price": 100.0, "profit": 0, "commission": -0.4, "swap": 0, "fee": 0, "time_msc": 1786338000000},
            {"ticket": 2, "entry": 1, "volume": 1.0, "price": 101.0, "profit": 10.0, "commission": -0.4, "swap": -0.1, "fee": 0, "time_msc": 1786338001000},
        ]
        result = TgSignalReplayEngine().replay(
            operation,
            [Tick(1786338000000, 100, 100.1, 0, 0)],
            complete_coverage(),
            baseline_policy(),
        )
        self.assertEqual(result.status, "COMPLETE")
        self.assertAlmostEqual(result.net_pnl, 9.1)
        self.assertEqual(result.diagnostics["baseline_source"], "BROKER_DEALS")

    def test_gap_censors_and_one_second_marks_never_promote(self) -> None:
        operation = direct_operation()
        ticks = [Tick(1786338000000, 100, 100.1, 0, 0)]
        result = TgSignalReplayEngine().replay(operation, ticks, dict(complete_coverage(), gap_count=1), baseline_policy())
        self.assertEqual(result.status, "CENSORED")
        self.assertIn("ARCHIVE_GAPS", result.exclusions)

        marks_root = self.root / "marks"
        marks_root.mkdir()
        package = build_tg_package(marks_root, count=20)
        connection = sqlite3.connect(package / "operational.sqlite3")
        connection.execute("CREATE TABLE sentinel_execution_marks (id INTEGER PRIMARY KEY, execution_id TEXT, sampled_at TEXT)")
        for index in range(20):
            connection.execute("INSERT INTO sentinel_execution_marks VALUES (?,?,?)", (index + 1, f"exec-{index:03d}", "2026-08-10T05:01:00+00:00"))
        connection.commit(); connection.close()
        connection = sqlite3.connect(package / "ticks.sqlite3")
        connection.execute("DELETE FROM tick_chunks"); connection.execute("DELETE FROM archived_executions")
        connection.commit(); connection.close()
        snapshot = self.importer.import_package(package)
        evidence = TgManagementLabService(self.repo).run_baseline(snapshot["snapshot_id"], "XAUUSD")
        self.assertEqual(evidence["status"], "RESEARCH_ONLY")
        self.assertEqual(evidence["result_json"]["coverage"]["exclusion_reasons"], {"ONE_SECOND_MARKS_ONLY": 20})

    def test_one_second_prices_are_imported_for_research_replay(self) -> None:
        root = self.root / "priced-marks"
        root.mkdir()
        package = build_tg_package(root)
        connection = sqlite3.connect(package / "operational.sqlite3")
        connection.execute(
            "CREATE TABLE sentinel_execution_marks ("
            "id INTEGER PRIMARY KEY, execution_id TEXT, sampled_at TEXT, "
            "price REAL, floating_pnl REAL, risk_amount REAL, pnl_r REAL, "
            "volume REAL, status TEXT)"
        )
        for ordinal, price in enumerate((100.0, 101.0, 102.0, 103.0)):
            connection.execute(
                "INSERT INTO sentinel_execution_marks VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    ordinal + 1, "exec-000",
                    f"2026-08-10T05:01:0{ordinal}+00:00", price,
                    0.0, 10.0, 0.0, 1.0, "OPEN",
                ),
            )
        connection.commit(); connection.close()
        connection = sqlite3.connect(package / "ticks.sqlite3")
        connection.execute("DELETE FROM tick_chunks")
        connection.execute("DELETE FROM archived_executions")
        connection.commit(); connection.close()
        snapshot = self.importer.import_package(package)
        snapshot_db = Path(snapshot["path"]) / "snapshot.sqlite3"
        operation, ticks, coverage = TgSignalReplayEngine().load_operation(
            snapshot_db, "exec-000",
        )
        self.assertEqual(len(ticks), 4)
        self.assertEqual(coverage["evidence_tier"], "APPROXIMATE_1S")
        candidate = replace(
            baseline_policy(), policy_id="candidate",
            parent_policy_id="baseline-management-v1",
        )
        replay = TgSignalReplayEngine().replay(
            operation, ticks, coverage, candidate,
        )
        self.assertEqual(replay.status, "COMPLETE_APPROXIMATE")
        self.assertFalse(replay.diagnostics["promotion_eligible"])

    def test_version_sets_are_strata_and_never_exclude_cohort_trades(self) -> None:
        root = self.root / "version-strata"
        root.mkdir()
        package = build_tg_package(root, count=4)
        connection = sqlite3.connect(package / "operational.sqlite3")
        connection.execute(
            "UPDATE sentinel_executions SET signal_version='signal-v0' "
            "WHERE id IN ('exec-000','exec-001')"
        )
        connection.commit(); connection.close()
        snapshot = self.importer.import_package(package)
        result = TgManagementLabService(self.repo).run_baseline(
            snapshot["snapshot_id"], "XAUUSD",
        )["result_json"]
        self.assertEqual(len(result["cohort_execution_ids"]), 4)
        self.assertEqual(len(result["included_execution_ids"]), 4)
        self.assertEqual(result["excluded_executions"], {})
        self.assertEqual(len(result["version_strata"]), 2)

    def test_chronological_split_has_no_leakage_and_groups_by_operation(self) -> None:
        operations = [{"execution_id": str(index), "opened_at": f"2026-08-{10 + index:02d}T00:00:00+00:00"} for index in range(8)]
        split = chronological_split(operations)
        self.assertEqual(split.holdout_ids, ("6", "7"))
        for train, test in split.walk_forward:
            self.assertLess(max(map(int, train)), min(map(int, test)))

    def test_dual_promotion_gate_requires_both_conditions(self) -> None:
        baseline = {"gross_profit_net": 100, "gross_loss_net": 50}
        self.assertTrue(dual_promotion_improvement({"gross_profit_net": 101, "gross_loss_net": 49}, baseline))
        self.assertFalse(dual_promotion_improvement({"gross_profit_net": 101, "gross_loss_net": 50}, baseline))
        self.assertFalse(dual_promotion_improvement({"gross_profit_net": 100, "gross_loss_net": 49}, baseline))

    def test_baseline_parity_pass_failure_insufficient_sample_and_determinism(self) -> None:
        package = build_tg_package(self.root, count=3)
        snapshot = self.importer.import_package(package)
        service = TgManagementLabService(self.repo)
        first = service.run_baseline(snapshot["snapshot_id"], "XAUUSD")
        second = service.run_baseline(snapshot["snapshot_id"], "XAUUSD")
        self.assertEqual(first["experiment_id"], second["experiment_id"])
        self.assertEqual(first["result_json"], second["result_json"])
        self.assertEqual(first["status"], "INSUFFICIENT_TRADES")
        self.assertEqual(first["result_json"]["baseline_parity"]["status"], "PASSED")

        other_root = self.root / "bad-parity"
        other_root.mkdir()
        bad = build_tg_package(other_root, count=20)
        connection = sqlite3.connect(bad / "operational.sqlite3")
        connection.execute("UPDATE sentinel_executions SET realized_pnl=99.0")
        connection.commit()
        connection.close()
        bad_snapshot = self.importer.import_package(bad)
        failed = service.run_baseline(bad_snapshot["snapshot_id"], "XAUUSD")
        self.assertEqual(failed["status"], "BASELINE_PARITY_FAILED")

    def test_research_threshold_and_timeframe_lane_diagnostics(self) -> None:
        package = build_tg_package(self.root, count=20)
        snapshot = self.importer.import_package(package)
        service = TgManagementLabService(self.repo)
        result = service.optimize_asset(snapshot["snapshot_id"], "XAUUSD")
        repeated = service.optimize_asset(snapshot["snapshot_id"], "XAUUSD")
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertEqual(result["experiment_id"], repeated["experiment_id"])
        self.assertEqual(result["result_json"], repeated["result_json"])
        groups = result["result_json"]["timeframe_lane_diagnostics"]
        self.assertEqual({(item["timeframe"], item["lane"]) for item in groups}, {("M15", "FAST"), ("H1", "CORE")})

    def test_all_cohort_operations_are_retained_with_quality_flags(self) -> None:
        package = build_tg_package(self.root, count=20)
        connection = sqlite3.connect(package / "operational.sqlite3")
        connection.execute("UPDATE sentinel_executions SET manual_intervention = 1 WHERE id = 'exec-000'")
        connection.execute("UPDATE sentinel_executions SET anomalous_state = 1 WHERE id = 'exec-001'")
        connection.commit(); connection.close()
        snapshot = self.importer.import_package(package)
        result = TgManagementLabService(self.repo).run_baseline(snapshot["snapshot_id"], "XAUUSD")["result_json"]
        self.assertIn("exec-000", result["included_execution_ids"])
        self.assertIn("exec-001", result["included_execution_ids"])
        self.assertIn("MANUAL_INTERVENTION", result["quality_flags"]["exec-000"])
        self.assertIn("ANOMALOUS_STATE", result["quality_flags"]["exec-001"])

        missing_root = self.root / "missing-costs"
        missing_root.mkdir()
        package = build_tg_package(missing_root)
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["files"]["deals_csv"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        snapshot = self.importer.import_package(package)
        result = TgManagementLabService(self.repo).run_baseline(snapshot["snapshot_id"], "XAUUSD")["result_json"]
        self.assertIn("exec-000", result["included_execution_ids"])
        self.assertIn("MISSING_COST_BREAKDOWN", result["quality_flags"]["exec-000"])

    def test_forty_operations_evaluate_candidates_but_do_not_false_promote(self) -> None:
        package = build_tg_package(self.root, count=40)
        snapshot = self.importer.import_package(package)
        progress: list[dict] = []
        result = TgManagementLabService(self.repo).optimize_asset(
            snapshot["snapshot_id"], "XAUUSD", progress_callback=progress.append,
        )
        self.assertEqual(result["status"], "REJECTED")
        payload = result["result_json"]
        self.assertEqual(payload["candidates_tested"], 158)
        self.assertEqual(len(payload["chronology"]["holdout_ids"]), 10)
        self.assertEqual(payload["chronology"]["holdout_candidate_evaluation_count"], 1)
        self.assertEqual(payload["chronology"]["holdout_evaluated_candidate_ids"], [payload["selected_candidate"]["candidate_id"]])
        self.assertTrue(payload["chronology"]["holdout_excluded_from_search_ranking_and_ties"])
        self.assertEqual(sum(item["candidate_family"] == "JOINT_TARGETS_AND_MANAGEMENT" for item in payload["candidates"]), 39)
        self.assertEqual(sum(len(item["results"]) == 40 for item in payload["candidates"]), 1)
        self.assertTrue(all(
            item["target_geometry"]["candidate_family"] == "JOINT_TARGETS_AND_MANAGEMENT"
            for item in payload["candidates"]
            if item["candidate_family"] == "JOINT_TARGETS_AND_MANAGEMENT"
        ))
        self.assertTrue({"asset", "family", "completed", "total", "percent", "elapsed_seconds", "eta_seconds", "stage"} <= set(progress[-1]))

    def test_fixed_r_geometry_buy_sell_normalization_and_native_volumes(self) -> None:
        engine = TgSignalReplayEngine()
        geometry = TargetGeometryPolicy(
            "fixed", "provider_original", mode="FIXED_R",
            candidate_family="TARGET_GEOMETRY_ONLY",
            tp1_r=0.5, tp2_r=1.5, tp3_r=2.5,
        )
        opened_msc = int(datetime(2026, 8, 10, 5, tzinfo=UTC).timestamp() * 1000)
        for side, prices in (("BUY", (100.5, 101.5, 102.5)), ("SELL", (99.5, 98.5, 97.5))):
            operation = direct_operation(side)
            ticks = [
                Tick(opened_msc + index * 1000, price, price, 0, index)
                for index, price in enumerate((100.0, *prices))
            ]
            result = engine.replay(operation, ticks, complete_coverage(), baseline_policy(), geometry)
            self.assertTrue(result.comparable)
            self.assertEqual(tuple(fill.price for fill in result.fills), prices)
            self.assertEqual(tuple(fill.volume for fill in result.fills), (0.5, 0.3, 0.2))
            self.assertEqual(result.diagnostics["resolved_targets"], dict(zip(("TP1", "TP2", "TP3"), prices)))

    def test_fixed_r_invalid_at_fill_and_target_horizon_are_non_promotional(self) -> None:
        engine = TgSignalReplayEngine()
        invalid_operation = dict(direct_operation(), actual_fill=100.75)
        geometry = TargetGeometryPolicy(
            "fixed", "provider_original", mode="FIXED_R",
            tp1_r=0.5, tp2_r=2.0, tp3_r=6.0,
        )
        invalid = engine.replay(
            invalid_operation, [Tick(int(datetime(2026, 8, 10, 5, tzinfo=UTC).timestamp() * 1000), 100.75, 100.8, 0, 0)],
            complete_coverage(), baseline_policy(), geometry,
        )
        self.assertIn("INVALID_TARGET_AT_FILL", invalid.exclusions)
        self.assertFalse(invalid.comparable)
        operation = direct_operation()
        opened_msc = int(datetime(2026, 8, 10, 5, tzinfo=UTC).timestamp() * 1000)
        ticks = [Tick(opened_msc + index * 1000, price, price + 0.01, 0, index) for index, price in enumerate((100.0, 100.5, 102.0, 103.0))]
        censored = engine.replay(operation, ticks, complete_coverage(), baseline_policy(), geometry)
        self.assertIn("CENSORED_TARGET_HORIZON", censored.exclusions)
        self.assertTrue(censored.diagnostics["requires_future_capture"])
        self.assertFalse(censored.diagnostics["promotion_eligible"])

    def test_target_grid_bootstrap_and_full_gate_contracts(self) -> None:
        service = TgManagementLabService(self.repo)
        geometries = service._target_geometries()
        self.assertEqual(len(geometries), 106)
        self.assertTrue(all(item.tp1_r < item.tp2_r < item.tp3_r for item in geometries))
        ids = [f"e{index}" for index in range(12)]
        left = {item: {"net_pnl": float(index % 3)} for index, item in enumerate(ids)}
        right = {item: {"net_pnl": float(index % 3)} for index, item in enumerate(ids)}
        first = paired_block_bootstrap_equivalence(left, right, ids, seed=7, samples=200, block_length=3)
        second = paired_block_bootstrap_equivalence(left, right, ids, seed=7, samples=200, block_length=3)
        self.assertEqual(first, second)
        self.assertTrue(first["equivalent"])
        baseline = {"gross_profit_net": 10, "gross_loss_net": 5, "net_pnl": 5, "profit_factor": 2, "max_drawdown_money": 3}
        passing = {"gross_profit_net": 11, "gross_loss_net": 4, "net_pnl": 7, "profit_factor": 2.75, "max_drawdown_money": 2}
        one_only = dict(passing, gross_loss_net=6, net_pnl=5)
        self.assertTrue(full_promotion_improvement(passing, baseline))
        self.assertFalse(full_promotion_improvement(one_only, baseline))

    def test_selection_score_cannot_observe_holdout(self) -> None:
        baseline = {
            "walk_forward_oos": {"gross_profit_net": 10, "gross_loss_net": 5},
            "holdout": {"gross_profit_net": 1, "gross_loss_net": 99},
        }
        candidate = {"sections": {
            "walk_forward_oos": {"gross_profit_net": 12, "gross_loss_net": 4},
            "holdout": {"gross_profit_net": 9999, "gross_loss_net": 0},
        }}
        score = TgManagementLabService._selection_score(candidate, baseline)
        candidate["sections"]["holdout"] = {"gross_profit_net": 0, "gross_loss_net": 999999}
        self.assertEqual(score, TgManagementLabService._selection_score(candidate, baseline))

    def test_modules_have_no_mt5_telegram_or_network_dependency(self) -> None:
        import app.tg_import as importer_module
        import app.tg_replay as replay_module
        self.assertFalse(any(name.lower().startswith(("mt5", "telegram", "requests", "httpx")) for name in importer_module.__dict__))
        self.assertFalse(any(name.lower().startswith(("mt5", "telegram", "requests", "httpx")) for name in replay_module.__dict__))
