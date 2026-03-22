from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import duckdb

from app.infra.config import AppConfig


SCHEMA_SQL = """
create table if not exists datasets (
    dataset_id text primary key,
    dataset_name text not null,
    symbol text not null,
    timeframe text not null,
    source_path text not null,
    row_count bigint not null,
    start_ts bigint not null,
    end_ts bigint not null,
    created_at timestamp not null default current_timestamp
);

create table if not exists candles (
    dataset_id text not null,
    ts bigint not null,
    open double not null,
    high double not null,
    low double not null,
    close double not null,
    volume double not null
);

create table if not exists backtest_runs (
    run_id text primary key,
    family_id text not null,
    dataset_id text not null,
    timeframe text not null,
    status text not null,
    verdict text not null,
    parameters_json text not null,
    metrics_json text not null,
    artifact_path text not null,
    report_path text,
    created_at timestamp not null default current_timestamp
);

create table if not exists lab_artifacts (
    artifact_id text primary key,
    artifact_type text not null,
    family_id text,
    dataset_id text,
    source_run_id text,
    path text not null,
    payload_json text not null,
    created_at timestamp not null default current_timestamp
);
"""


class Database:
    def __init__(self, config: AppConfig):
        self.config = config
        self.path = Path(config.app_db_path)
        self.initialize()

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.path))

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(SCHEMA_SQL)

    def execute(self, sql: str, params: tuple | None = None) -> None:
        with self.connect() as conn:
            if params is None:
                conn.execute(sql)
            else:
                conn.execute(sql, params)

    def executemany(self, sql: str, rows: Iterable[tuple]) -> None:
        buffered = list(rows)
        if not buffered:
            return
        with self.connect() as conn:
            conn.executemany(sql, buffered)

    def fetch_all(self, sql: str, params: tuple | None = None) -> list[dict]:
        with self.connect() as conn:
            cursor = conn.execute(sql, params) if params is not None else conn.execute(sql)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def fetch_one(self, sql: str, params: tuple | None = None) -> dict | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def delete_dataset_related(self, dataset_id: str) -> None:
        with self.connect() as conn:
            run_rows = conn.execute(
                "select run_id, artifact_path, report_path from backtest_runs where dataset_id = ?",
                (dataset_id,),
            ).fetchall()
            run_ids = [row[0] for row in run_rows]
            if run_ids:
                placeholders = ",".join(["?"] * len(run_ids))
                conn.execute(f"delete from lab_artifacts where source_run_id in ({placeholders})", tuple(run_ids))
            conn.execute("delete from backtest_runs where dataset_id = ?", (dataset_id,))
            conn.execute("delete from candles where dataset_id = ?", (dataset_id,))
            conn.execute("delete from datasets where dataset_id = ?", (dataset_id,))

    def delete_run_related(self, run_id: str) -> None:
        with self.connect() as conn:
            conn.execute("delete from lab_artifacts where source_run_id = ?", (run_id,))
            conn.execute("delete from backtest_runs where run_id = ?", (run_id,))

    def delete_artifact(self, artifact_id: str) -> None:
        self.execute("delete from lab_artifacts where artifact_id = ?", (artifact_id,))

    def insert_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        path: str,
        payload: dict,
        family_id: str | None = None,
        dataset_id: str | None = None,
        source_run_id: str | None = None,
    ) -> None:
        self.execute(
            """
            insert into lab_artifacts
            (artifact_id, artifact_type, family_id, dataset_id, source_run_id, path, payload_json)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                artifact_type,
                family_id,
                dataset_id,
                source_run_id,
                path,
                json.dumps(payload, sort_keys=True),
            ),
        )
