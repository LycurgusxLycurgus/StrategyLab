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

                CREATE TABLE IF NOT EXISTS dataset_hashes (
                    dataset_id TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL,
                    bytes_count INTEGER NOT NULL,
                    computed_at TEXT NOT NULL
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

                CREATE TABLE IF NOT EXISTS pine_revisions (
                    revision_id TEXT PRIMARY KEY,
                    workbench_id TEXT NOT NULL,
                    parent_revision_id TEXT,
                    mode TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    status_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_pine_revisions_workbench
                    ON pine_revisions (workbench_id, created_at);

                CREATE TABLE IF NOT EXISTS pine_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    revision_id TEXT,
                    strategy_version_id TEXT,
                    dataset_id TEXT,
                    kind TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status_json TEXT NOT NULL,
                    artifact_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_pine_evidence_revision
                    ON pine_evidence (revision_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_pine_evidence_version
                    ON pine_evidence (strategy_version_id, created_at);
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
            connection.execute(
                "DELETE FROM dataset_hashes WHERE dataset_id = ?", (dataset_id,)
            )
            connection.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))

    def put_dataset_hash(self, payload: dict[str, Any]) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO dataset_hashes (
                    dataset_id, sha256, bytes_count, computed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    payload["dataset_id"],
                    payload["sha256"],
                    payload["bytes_count"],
                    payload["computed_at"],
                ),
            )

    def get_dataset_hash(self, dataset_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM dataset_hashes WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()
        return self._row_to_dict(row)

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

    def put_pine_revision(self, payload: dict[str, Any]) -> None:
        existing = self.get_pine_revision(payload["revision_id"])
        if existing:
            comparable = {
                key: existing[key]
                for key in (
                    "revision_id",
                    "workbench_id",
                    "parent_revision_id",
                    "mode",
                    "stage",
                    "source_sha256",
                    "source_code",
                    "settings",
                    "provenance",
                )
            }
            requested = {
                key: payload.get(key)
                for key in (
                    "revision_id",
                    "workbench_id",
                    "parent_revision_id",
                    "mode",
                    "stage",
                    "source_sha256",
                    "source_code",
                    "settings",
                    "provenance",
                )
            }
            if comparable != requested:
                raise ValueError(
                    f"immutable Pine revision collision: {payload['revision_id']}"
                )
            return
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO pine_revisions (
                    revision_id, workbench_id, parent_revision_id, mode, stage,
                    source_sha256, source_code, settings_json, provenance_json,
                    analysis_json, status_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["revision_id"],
                    payload["workbench_id"],
                    payload.get("parent_revision_id"),
                    payload["mode"],
                    payload["stage"],
                    payload["source_sha256"],
                    payload["source_code"],
                    json.dumps(payload.get("settings", {})),
                    json.dumps(payload.get("provenance", {})),
                    json.dumps(payload.get("analysis", {})),
                    json.dumps(payload.get("status", [])),
                    payload["created_at"],
                ),
            )

    @staticmethod
    def _decode_pine_revision(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["settings"] = json.loads(payload.pop("settings_json"))
        payload["provenance"] = json.loads(payload.pop("provenance_json"))
        payload["analysis"] = json.loads(payload.pop("analysis_json"))
        payload["status"] = json.loads(payload.pop("status_json"))
        return payload

    def get_pine_revision(self, revision_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM pine_revisions WHERE revision_id = ?",
                (revision_id,),
            ).fetchone()
        return self._decode_pine_revision(row) if row else None

    def list_pine_revisions(
        self, workbench_id: str | None = None
    ) -> list[dict[str, Any]]:
        with self._session() as connection:
            if workbench_id:
                rows = connection.execute(
                    """
                    SELECT * FROM pine_revisions
                    WHERE workbench_id = ?
                    ORDER BY created_at ASC
                    """,
                    (workbench_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM pine_revisions ORDER BY created_at DESC"
                ).fetchall()
        return [self._decode_pine_revision(row) for row in rows]

    def put_pine_evidence(self, payload: dict[str, Any]) -> None:
        existing = self.get_pine_evidence(payload["evidence_id"])
        if existing:
            if existing["request_hash"] != payload["request_hash"]:
                raise ValueError(
                    f"immutable Pine evidence collision: {payload['evidence_id']}"
                )
            return
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO pine_evidence (
                    evidence_id, revision_id, strategy_version_id, dataset_id,
                    kind, request_hash, status_json, artifact_json, payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["evidence_id"],
                    payload.get("revision_id"),
                    payload.get("strategy_version_id"),
                    payload.get("dataset_id"),
                    payload["kind"],
                    payload["request_hash"],
                    json.dumps(payload.get("status", [])),
                    json.dumps(payload.get("artifact", {})),
                    json.dumps(payload.get("payload", {})),
                    payload["created_at"],
                ),
            )

    @staticmethod
    def _decode_pine_evidence(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["status"] = json.loads(payload.pop("status_json"))
        payload["artifact"] = json.loads(payload.pop("artifact_json"))
        payload["payload"] = json.loads(payload.pop("payload_json"))
        return payload

    def get_pine_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM pine_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        return self._decode_pine_evidence(row) if row else None

    def list_pine_evidence(
        self,
        *,
        revision_id: str | None = None,
        strategy_version_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM pine_evidence"
        conditions: list[str] = []
        parameters: list[Any] = []
        if revision_id:
            conditions.append("revision_id = ?")
            parameters.append(revision_id)
        if strategy_version_id:
            conditions.append("strategy_version_id = ?")
            parameters.append(strategy_version_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at ASC"
        with self._session() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._decode_pine_evidence(row) for row in rows]

    def delete_run(self, run_id: str) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
