from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import settings


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class Repository:
    def __init__(self, db_path: Path | None = None) -> None:
        settings.ensure_dirs()
        self.db_path = db_path or settings.db_path
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def session(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.session() as conn:
            conn.executescript(
                """
                create table if not exists datasets (
                    dataset_id text primary key,
                    name text not null,
                    symbol text not null,
                    timeframe text not null,
                    rows_count integer not null,
                    path text not null,
                    created_at text not null
                );
                create table if not exists runs (
                    run_id text primary key,
                    kind text not null,
                    dataset_id text not null,
                    status text not null,
                    verdict text not null,
                    metrics_json text not null,
                    artifact_path text not null,
                    report_path text not null,
                    created_at text not null
                );
                create table if not exists paper_runs (
                    paper_id text primary key,
                    dataset_id text not null,
                    status text not null,
                    metrics_json text not null,
                    artifact_path text not null,
                    created_at text not null
                );
                create table if not exists webhooks (
                    event_id text primary key,
                    payload_json text not null,
                    response_json text not null,
                    created_at text not null
                );
                """
            )

    def upsert_dataset(self, record: dict[str, Any]) -> None:
        with self.session() as conn:
            conn.execute(
                """
                insert into datasets(dataset_id, name, symbol, timeframe, rows_count, path, created_at)
                values(:dataset_id, :name, :symbol, :timeframe, :rows_count, :path, :created_at)
                on conflict(dataset_id) do update set
                    name=excluded.name,
                    symbol=excluded.symbol,
                    timeframe=excluded.timeframe,
                    rows_count=excluded.rows_count,
                    path=excluded.path,
                    created_at=excluded.created_at
                """,
                record,
            )

    def list_datasets(self) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute("select * from datasets order by created_at desc").fetchall()
        return [row_to_dict(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute("select * from datasets where dataset_id = ?", (dataset_id,)).fetchone()
        return row_to_dict(row) if row else None

    def delete_dataset(self, dataset_id: str) -> None:
        record = self.get_dataset(dataset_id)
        if record:
            path = Path(record["path"])
            if path.exists():
                path.unlink()
        with self.session() as conn:
            conn.execute("delete from datasets where dataset_id = ?", (dataset_id,))

    def store_run(self, record: dict[str, Any]) -> None:
        payload = record.copy()
        payload["metrics_json"] = json.dumps(payload["metrics_json"])
        with self.session() as conn:
            conn.execute(
                """
                insert into runs(run_id, kind, dataset_id, status, verdict, metrics_json, artifact_path, report_path, created_at)
                values(:run_id, :kind, :dataset_id, :status, :verdict, :metrics_json, :artifact_path, :report_path, :created_at)
                on conflict(run_id) do update set
                    kind=excluded.kind,
                    dataset_id=excluded.dataset_id,
                    status=excluded.status,
                    verdict=excluded.verdict,
                    metrics_json=excluded.metrics_json,
                    artifact_path=excluded.artifact_path,
                    report_path=excluded.report_path,
                    created_at=excluded.created_at
                """,
                payload,
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute("select * from runs order by created_at desc").fetchall()
        items = [row_to_dict(row) for row in rows]
        for item in items:
            item["metrics"] = json.loads(item.pop("metrics_json"))
        return items

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute("select * from runs where run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        item = row_to_dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json"))
        return item

    def delete_run(self, run_id: str) -> None:
        record = self.get_run(run_id)
        if record:
            for key in ("artifact_path", "report_path"):
                path = Path(record[key])
                if path.exists():
                    path.unlink()
        with self.session() as conn:
            conn.execute("delete from runs where run_id = ?", (run_id,))

    def store_paper_run(self, record: dict[str, Any]) -> None:
        payload = record.copy()
        payload["metrics_json"] = json.dumps(payload["metrics_json"])
        with self.session() as conn:
            conn.execute(
                """
                insert into paper_runs(paper_id, dataset_id, status, metrics_json, artifact_path, created_at)
                values(:paper_id, :dataset_id, :status, :metrics_json, :artifact_path, :created_at)
                on conflict(paper_id) do update set
                    dataset_id=excluded.dataset_id,
                    status=excluded.status,
                    metrics_json=excluded.metrics_json,
                    artifact_path=excluded.artifact_path,
                    created_at=excluded.created_at
                """,
                payload,
            )

    def list_paper_runs(self) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute("select * from paper_runs order by created_at desc").fetchall()
        items = [row_to_dict(row) for row in rows]
        for item in items:
            item["metrics"] = json.loads(item.pop("metrics_json"))
        return items

    def store_webhook(self, record: dict[str, Any]) -> None:
        payload = record.copy()
        payload["payload_json"] = json.dumps(payload["payload_json"])
        payload["response_json"] = json.dumps(payload["response_json"])
        with self.session() as conn:
            conn.execute(
                """
                insert into webhooks(event_id, payload_json, response_json, created_at)
                values(:event_id, :payload_json, :response_json, :created_at)
                on conflict(event_id) do update set
                    payload_json=excluded.payload_json,
                    response_json=excluded.response_json,
                    created_at=excluded.created_at
                """,
                payload,
            )
