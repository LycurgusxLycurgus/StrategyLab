from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import settings


class Repository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self) -> sqlite3.Connection:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    source TEXT NOT NULL,
                    rows_count INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS families (
                    family_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    venue TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    current_version_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS versions (
                    version_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    parent_version_id TEXT,
                    name TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    causal_story TEXT NOT NULL,
                    mutation_json TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    parent_version_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    lever TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    patch_json TEXT NOT NULL,
                    child_version_id TEXT,
                    run_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    report_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def put_dataset(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO datasets (
                    dataset_id, name, symbol, timeframe, source, rows_count, path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["dataset_id"],
                    payload["name"],
                    payload["symbol"],
                    payload["timeframe"],
                    payload["source"],
                    payload["rows_count"],
                    payload["path"],
                    payload["created_at"],
                ),
            )

    def list_datasets(self) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM datasets ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM datasets WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def delete_dataset(self, dataset_id: str) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))

    def put_family(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO families (
                    family_id, title, asset, venue, timeframe, current_version_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["family_id"],
                    payload["title"],
                    payload["asset"],
                    payload["venue"],
                    payload["timeframe"],
                    payload.get("current_version_id"),
                    payload["created_at"],
                ),
            )

    def list_families(self) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM families ORDER BY created_at ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_family(self, family_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM families WHERE family_id = ?",
                (family_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def put_version(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO versions (
                    version_id, family_id, parent_version_id, name, stage, source_code,
                    spec_json, causal_story, mutation_json, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["version_id"],
                    payload["family_id"],
                    payload.get("parent_version_id"),
                    payload["name"],
                    payload["stage"],
                    payload["source_code"],
                    json.dumps(payload["spec_json"]),
                    payload["causal_story"],
                    json.dumps(payload.get("mutation_json", {})),
                    payload.get("notes", ""),
                    payload["created_at"],
                ),
            )

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM versions WHERE version_id = ?",
                (version_id,),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["spec_json"] = json.loads(payload["spec_json"])
        payload["mutation_json"] = json.loads(payload["mutation_json"])
        return payload

    def list_versions(self, family_id: str) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM versions WHERE family_id = ? ORDER BY created_at ASC",
                (family_id,),
            ).fetchall()
        versions: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["spec_json"] = json.loads(payload["spec_json"])
            payload["mutation_json"] = json.loads(payload["mutation_json"])
            versions.append(payload)
        return versions

    def delete_version(self, version_id: str) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM versions WHERE version_id = ?", (version_id,))

    def put_proposal(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO proposals (
                    proposal_id, family_id, parent_version_id, status, kind, lever, summary,
                    rationale, patch_json, child_version_id, run_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["proposal_id"],
                    payload["family_id"],
                    payload["parent_version_id"],
                    payload["status"],
                    payload["kind"],
                    payload["lever"],
                    payload["summary"],
                    payload["rationale"],
                    json.dumps(payload["patch_json"]),
                    payload.get("child_version_id"),
                    payload.get("run_id"),
                    payload["created_at"],
                ),
            )

    def list_proposals(self, family_id: str | None = None, parent_version_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if family_id:
            clauses.append("family_id = ?")
            params.append(family_id)
        if parent_version_id:
            clauses.append("parent_version_id = ?")
            params.append(parent_version_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._session() as connection:
            rows = connection.execute(
                f"SELECT * FROM proposals {where} ORDER BY created_at ASC",
                params,
            ).fetchall()
        proposals: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["patch_json"] = json.loads(payload["patch_json"])
            proposals.append(payload)
        return proposals

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["patch_json"] = json.loads(payload["patch_json"])
        return payload

    def delete_proposals_for_version(self, version_id: str) -> None:
        with self._session() as connection:
            connection.execute(
                "DELETE FROM proposals WHERE parent_version_id = ? OR child_version_id = ?",
                (version_id, version_id),
            )

    def put_run(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, family_id, version_id, dataset_id, status, verdict, metrics_json,
                    artifact_path, report_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["run_id"],
                    payload["family_id"],
                    payload["version_id"],
                    payload["dataset_id"],
                    payload["status"],
                    payload["verdict"],
                    json.dumps(payload["metrics_json"]),
                    payload["artifact_path"],
                    payload["report_path"],
                    payload["created_at"],
                ),
            )

    def list_runs(self, family_id: str | None = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if family_id:
            where = "WHERE family_id = ?"
            params.append(family_id)
        with self._session() as connection:
            rows = connection.execute(
                f"SELECT * FROM runs {where} ORDER BY created_at DESC",
                params,
            ).fetchall()
        runs: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["metrics_json"] = json.loads(payload["metrics_json"])
            runs.append(payload)
        return runs

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["metrics_json"] = json.loads(payload["metrics_json"])
        return payload

    def delete_run(self, run_id: str) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
