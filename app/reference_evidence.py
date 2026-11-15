"""Content-verified reference evidence and operation gates owned by StrategyLab."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from app.data import Bar
from app.reference import (
    EXECUTION_CONTRACT,
    digest,
    effective_parameters,
    fail,
    render_casebook,
    run_reference,
    validate_spec,
    workflow,
)


def provenance(spec: dict, parent: dict | None = None) -> None:
    validate_spec(spec)
    if spec.get("execution_contract") != EXECUTION_CONTRACT:
        fail(
            "EXECUTION_CONTRACT_REQUIRED",
            "Select the explicit registered next-open/static-ATR/censored-cutoff execution contract.",
        )
    origin = spec.get("strategy_origin")
    operation = spec.get("development_operation")
    objective = spec.get("translation_objective", "not_applicable")
    if origin not in {
        "systematic_native",
        "discretionary_origin",
        "hybrid",
    } or operation not in {"create", "replicate", "translate", "improve"}:
        fail(
            "PROVENANCE_REQUIRED", "Declare strategy_origin and development_operation."
        )
    if objective not in {"not_applicable", "fidelity_oriented", "performance_oriented"}:
        fail("TRANSLATION_OBJECTIVE", "Unknown translation objective.")
    if origin in {"discretionary_origin", "hybrid"} and (
        not spec.get("interpretation")
        or not spec.get("ambiguities")
        or objective == "not_applicable"
    ):
        fail(
            "INTERPRETATION_REQUIRED",
            "Declare ambiguity inventory, selected interpretation and translation objective.",
        )
    if origin == "hybrid" and not spec.get("rule_group_origins"):
        fail(
            "RULE_GROUP_ORIGINS_REQUIRED",
            "Hybrid origin requires component classifications.",
        )
    if spec.get("provisional", False):
        fail(
            "PROVISIONAL_REFERENCE",
            "Provisional interpretations cannot earn accepted evidence.",
        )
    if operation == "replicate" and not spec.get("source_mapping"):
        fail("SOURCE_MAPPING_REQUIRED", "Replication requires source-to-rule mapping.")
    if operation == "improve" and (
        not parent or not spec.get("development_authorization")
    ):
        fail(
            "ADAPTATION_UNAUTHORIZED",
            "Improvement requires an accepted parent and explicit development authorization.",
        )
    transformations = spec.get("transformations", [])
    if operation in {"translate", "improve"} and not transformations:
        fail("TRANSFORMATIONS_REQUIRED", "Record material formalizations/adaptations.")
    required = {
        "parent_rule_id",
        "child_rule_id",
        "operation",
        "rationale",
        "source_evidence",
        "ambiguity_or_problem",
        "executable_choice",
        "meaning_change",
        "expected_effect",
        "validation_evidence",
    }
    for item in transformations:
        if not isinstance(item, dict) or any(k not in item for k in required):
            fail(
                "TRANSFORMATION_INCOMPLETE", "Transformation provenance is incomplete."
            )
    if parent:
        old = parent["spec_json"]
        changed_rules = old.get("parameters", {}) != spec.get(
            "parameters", {}
        ) or old.get("engine_id") != spec.get("engine_id")
        if changed_rules and (
            operation != "improve" or not spec.get("development_authorization")
        ):
            fail(
                "ADAPTATION_UNAUTHORIZED",
                "A changed executable rule requires improve operation and explicit development authorization.",
            )
        if old.get("strategy_origin") != origin:
            fail("ORIGIN_IMMUTABLE", "A child preserves its original strategy origin.")
        if old.get("development_operation") != operation and not spec.get(
            "operation_transition"
        ):
            fail(
                "OPERATION_TRANSITION_REQUIRED",
                "Record a changed development operation.",
            )
        if old != spec and not transformations:
            fail(
                "TRANSFORMATIONS_REQUIRED",
                "A changed child requires rule transformations.",
            )
    if spec.get("claim_exact_source") and (
        operation not in {"replicate", "translate"}
        or any(t.get("meaning_change") for t in transformations)
    ):
        fail(
            "FALSE_SOURCE_EQUIVALENCE",
            "Material adaptation cannot claim exact source replication.",
        )


def case_bars(case: dict) -> list[Bar]:
    try:
        return [
            Bar(
                ts=datetime.fromisoformat(row["ts"]),
                **{
                    k: row[k]
                    for k in (
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "symbol",
                        "timeframe",
                    )
                },
            )
            for row in case["bars"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            422,
            detail={
                "code": "CASE_INVALID",
                "message": "Cases require serialized bars and independent expected decisions.",
            },
        ) from exc


def check_cases(spec: dict, cases: list[dict]) -> dict:
    if not cases or any(
        not c.get("name") or "expected_decisions" not in c for c in cases
    ):
        fail(
            "EXPECTED_CASES_REQUIRED",
            "Supply named independent cases with exact expected_decisions.",
        )
    accepted = rejected = 0
    for case in cases:
        bars = case_bars(case)
        if len(bars) > 500:
            fail("CASE_TOO_LARGE", "Independent cases are bounded to 500 bars each.")
        result = run_reference(spec, bars)
        if result["decisions"] != case["expected_decisions"]:
            fail(
                "SEMANTIC_CASE_FAILED",
                f"Independent expected decisions differ: {case['name']}.",
            )
        accepted += sum(d["reason"] == "accepted" for d in result["decisions"])
        rejected += sum(e["event_type"] == "rejected" for e in result["ledger"])
        untraced = run_reference(spec, bars, collect_ledger=False)
        for key in ("decisions", "order_intents", "trades", "equity_curve"):
            if result[key] != untraced[key]:
                fail("TRACE_CHANGES_BEHAVIOR", f"Ledger toggle changes {key}.")
        # Re-run every prefix for bounded adjudicated fixtures. This compares
        # observable decisions, never final settlement or cutoff censorship.
        for end in range(1, len(bars) + 1):
            prefix = run_reference(spec, bars[:end])
            if prefix["decisions"] != [
                d for d in result["decisions"] if d["bar_index"] < end
            ]:
                fail(
                    "PREFIX_UNSTABLE",
                    f"Future observations change decisions: {case['name']}.",
                )
    if not accepted or not rejected:
        fail(
            "CASE_COVERAGE_REQUIRED",
            "Expected cases must cover accepted and rejected events.",
        )
    return {
        "status": "PASSED",
        "cases": len(cases),
        "accepted": accepted,
        "rejected": rejected,
        "causality": "PASSED",
        "prefix": "PASSED",
        "ledger_toggle": "PASSED",
    }


class EvidenceService:
    def __init__(self, repo, data_service):
        self.repo = repo
        self.data = data_service

    def _version(self, version_id: str) -> dict:
        version = self.repo.get_version(version_id)
        if not version:
            raise HTTPException(404, "Strategy version not found.")
        return version

    def _reference_version(self, version_id: str) -> dict:
        version = self._version(version_id)
        if workflow(version["spec_json"]) != "reference_v1":
            fail(
                "REFERENCE_WORKFLOW_REQUIRED",
                "Legacy lineages retain their Pine evidence; create an explicit reference child for migration.",
            )
        return version

    def dependencies(
        self, version: dict, dataset_id: str, spec: dict | None = None
    ) -> dict:
        spec = spec or version["spec_json"]
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(404, "Dataset not found.")
        from app import backtest, data, reference

        quality_manifest = self.data.dataset_quality_manifest(dataset_id)
        parent_evidence_hash = None
        if (
            version.get("parent_version_id")
            and spec.get("development_operation") == "improve"
        ):
            parent = self._reference_version(version["parent_version_id"])
            parent_evidence_hash = digest(
                {
                    "authorization": self._read(
                        parent, dataset_id, "search_authorization"
                    ),
                    "baseline": self._read(parent, dataset_id, "baseline"),
                }
            )
        oracle_hash = None
        oracle = spec.get("source_oracle")
        if oracle:
            oracle_path = Path(oracle.get("artifact_path", "")).resolve()
            if (
                not oracle_path.is_relative_to(self._root())
                or not oracle_path.is_file()
            ):
                fail(
                    "SOURCE_EQUIVALENCE_REQUIRED",
                    "Independent source oracle is missing or outside the artifact root.",
                )
            oracle_hash = hashlib.sha256(oracle_path.read_bytes()).hexdigest()
            if oracle_hash != oracle.get("artifact_sha256"):
                fail(
                    "SOURCE_ORACLE_TAMPERED", "Independent source oracle hash differs."
                )

        return {
            "workflow_version": workflow(spec),
            "parent_evidence_hash": parent_evidence_hash,
            "spec_hash": digest(spec),
            "config_hash": digest(spec.get("parameters", {})),
            "reference_code_hash": hashlib.sha256(
                Path(reference.__file__).read_bytes()
                + Path(backtest.__file__).read_bytes()
                + Path(data.__file__).read_bytes()
                + Path(__file__).read_bytes()
            ).hexdigest(),
            "source_hash": hashlib.sha256(
                version["source_code"].encode("utf-8")
            ).hexdigest(),
            "dataset_raw_hash": self.data.dataset_content_hash(dataset_id)["sha256"],
            "quality_manifest_hash": digest(quality_manifest),
            "source_oracle_hash": oracle_hash,
            "execution_model_hash": digest(
                {
                    k: spec.get("parameters", {}).get(k)
                    for k in (
                        "execution_model",
                        "sizing_mode",
                        "commission_pct",
                        "slippage_ticks",
                        "quantity",
                        "stop_mult",
                        "target_r",
                        "max_gap_bars",
                    )
                }
            ),
        }

    def _root(self) -> Path:
        return settings.pine_development_dir.resolve()

    def _save(
        self, version: dict, dataset_id: str, kind: str, payload: dict, deps: dict
    ) -> dict:
        raw = json.dumps(
            {
                "schema_version": "reference_v1",
                "version_id": version["version_id"],
                "dataset_id": dataset_id,
                "dependencies": deps,
                **payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        sha = hashlib.sha256(raw).hexdigest()
        path = self._root() / "reference" / version["version_id"] / f"{kind}-{sha}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != raw:
            fail("EVIDENCE_COLLISION", "Immutable evidence collision.")
        path.write_bytes(raw)
        record = {
            "evidence_id": f"ref_{sha[:24]}",
            "version_id": version["version_id"],
            "dataset_id": dataset_id,
            "kind": kind,
            "artifact_path": str(path),
            "artifact_hash": sha,
            "dependencies": deps,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_workflow_evidence(record)
        return {**record, "payload": json.loads(raw)}

    def _read(
        self, version: dict, dataset_id: str, kind: str, deps: dict | None = None
    ) -> dict:
        deps = deps or self.dependencies(version, dataset_id)
        for record in self.repo.list_workflow_evidence(
            version["version_id"], dataset_id
        ):
            if record["kind"] != kind or record["dependencies"] != deps:
                continue
            path = Path(record["artifact_path"]).resolve()
            if not path.is_relative_to(self._root()) or not path.is_file():
                fail(
                    "EVIDENCE_PATH_INVALID",
                    "Evidence must resolve inside the artifact root.",
                )
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != record["artifact_hash"]:
                fail("EVIDENCE_TAMPERED", "Saved evidence content hash changed.")
            payload = json.loads(raw)
            if (
                payload.get("dependencies") != deps
                or payload.get("version_id") != version["version_id"]
                or payload.get("dataset_id") != dataset_id
            ):
                fail(
                    "EVIDENCE_IDENTITY",
                    "Evidence identities differ from the indexed request.",
                )
            return payload
        fail("EVIDENCE_REQUIRED", f"Missing or stale {kind} evidence.")

    def validate(self, version_id: str, dataset_id: str, cases: list[dict]) -> dict:
        from app.data import audit_bars

        version = self._reference_version(version_id)
        parent = (
            self.repo.get_version(version["parent_version_id"])
            if version.get("parent_version_id")
            else None
        )
        provenance(version["spec_json"], parent)
        spec = version["spec_json"]
        if parent and spec.get("development_operation") == "improve":
            self.require(parent, dataset_id, "save", spec)
        semantic = check_cases(spec, cases)
        bars = self.data.load_bars(dataset_id)
        quality = audit_bars(bars)
        raw_quality = self.data.dataset_quality_manifest(dataset_id)
        if raw_quality.get("status") not in {"VERIFIED", "UNVERIFIED"}:
            fail(
                "RAW_DATA_AUDIT_STALE",
                "Raw audit no longer matches saved observations; reimport original data.",
            )
        if raw_quality.get("status") == "UNVERIFIED":
            if not spec.get("data_contract", {}).get("allow_normalized_only", False):
                fail(
                    "RAW_DATA_AUDIT_REQUIRED",
                    "Original raw audit unavailable; reimport original data or explicitly scope acceptance to normalized observations.",
                )
            quality = {
                **quality,
                "status": "PASS_WITH_LIMITATIONS",
                "raw_audit": raw_quality,
                "limitations": [
                    "Original raw input audit unavailable; only saved normalized observations inspected."
                ],
            }
        else:
            quality = {**quality, "raw_audit": raw_quality}
            if raw_quality.get("data_audit", {}).get("status") == "BLOCKED":
                fail(
                    "RAW_DATA_AUDIT_BLOCKED",
                    "Original observations have blocking audit findings.",
                )
        result = run_reference(spec, bars)
        deps = self.dependencies(version, dataset_id)
        normalized = digest(
            [
                [
                    b.ts.isoformat(),
                    b.open,
                    b.high,
                    b.low,
                    b.close,
                    b.volume,
                    b.symbol,
                    b.timeframe,
                ]
                for b in bars
            ]
        )
        source_fidelity = {
            "status": "NOT_APPLICABLE"
            if spec["development_operation"] == "create"
            else "PASS_WITH_LIMITATIONS",
            "limitations": [
                "Reference expectations prove the selected specification, not discretionary source equivalence."
            ],
        }
        if (
            spec.get("claim_exact_source")
            or spec["development_operation"] == "replicate"
        ):
            oracle = spec.get("source_oracle", {})
            path = Path(oracle.get("artifact_path", "")).resolve()
            if not path.is_relative_to(self._root()) or not path.is_file():
                fail(
                    "SOURCE_EQUIVALENCE_REQUIRED",
                    "Source equivalence needs a saved independent source-execution/adjudication artifact.",
                )
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != oracle.get("artifact_sha256"):
                fail(
                    "SOURCE_ORACLE_TAMPERED", "Independent source oracle hash differs."
                )
            source_cases = json.loads(raw)
            if (
                source_cases.get("authority")
                not in {"original_source_execution", "expert_adjudication"}
                or source_cases.get("source_hash") != deps["source_hash"]
                or not source_cases.get("cases")
            ):
                fail(
                    "SOURCE_EQUIVALENCE_REQUIRED",
                    "Exact replication needs independent source cases tied to immutable source bytes.",
                )
            check_cases(spec, source_cases["cases"])
            if not spec.get("source_mapping"):
                fail(
                    "SOURCE_MAPPING_REQUIRED", "Map source rules to independent cases."
                )
            source_fidelity = {
                "status": "PASSED",
                "scope": "declared source oracle cases only",
                "limitations": ["Uncovered source behavior is not proven equivalent."],
            }
        quality_status = quality.get("status", "PASSED")
        if quality_status not in {"PASSED", "PASS_WITH_LIMITATIONS"}:
            fail("DATA_QUALITY_BLOCKED", "Dataset quality has blocking findings.")
        gates = {
            "semantic": semantic,
            "data": {
                "status": quality_status,
                "quality": quality,
                "normalized_hash": normalized,
            },
            "execution": {
                "status": "PASS_WITH_LIMITATIONS",
                "limitations": result["limitations"],
                "ledger_hash": digest(result["ledger"]),
            },
            "source_fidelity": source_fidelity,
        }
        casebook_bytes = render_casebook(result).encode("utf-8")
        saved = self._save(
            version,
            dataset_id,
            "validation",
            {
                "gates": gates,
                "cases": cases,
                "ledger": result["ledger"],
                "decisions": result["decisions"],
                "order_intents": result["order_intents"],
                "trace": result["trace"],
                "casebook_sha256": hashlib.sha256(casebook_bytes).hexdigest(),
                "normalized_hash": normalized,
                "quality_manifest_hash": digest(quality),
            },
            deps,
        )
        casebook = Path(saved["artifact_path"]).with_suffix(".html")
        casebook.write_bytes(casebook_bytes)
        return {**saved, "gates": gates, "casebook_path": str(casebook)}

    def require(
        self, version: dict, dataset_id: str, operation: str, spec: dict | None = None
    ) -> dict | None:
        if operation not in {
            "run",
            "search",
            "save",
            "promote",
            "target_accept",
            "production",
        }:
            fail("WORKFLOW_OPERATION_UNKNOWN", "Unknown evidence operation.")
        if workflow(version["spec_json"]) == "legacy_pine_v1":
            return None
        parent = (
            self.repo.get_version(version["parent_version_id"])
            if version.get("parent_version_id")
            else None
        )
        provenance(version["spec_json"], parent)
        saved = self._read(version, dataset_id, "validation")
        if any(
            saved["gates"][k]["status"] not in {"PASSED", "PASS_WITH_LIMITATIONS"}
            for k in ("semantic", "data", "execution")
        ):
            fail(
                "REFERENCE_GATES_BLOCKED",
                "Semantic, data and execution evidence must pass.",
            )
        if operation in {"search", "save", "promote"}:
            self._read(version, dataset_id, "baseline")
        if operation in {"target_accept", "production"}:
            self._read(version, dataset_id, "target_acceptance")
        if operation == "production":
            self._read(version, dataset_id, "operational")
        if operation in {"search", "save"}:
            authorization = self._read(version, dataset_id, "search_authorization")[
                "authorization"
            ]
            current = effective_parameters(version["spec_json"])
            candidate = effective_parameters(spec or version["spec_json"])
            for key in current.keys() | candidate.keys():
                value = candidate.get(key)
                if value != current.get(key) and value not in authorization[
                    "parameters"
                ].get(key, []):
                    fail(
                        "SEARCH_DOMAIN_UNAUTHORIZED",
                        f"{key} lies outside the authorized parameter domain.",
                    )
            check_cases(spec or version["spec_json"], saved["cases"])
            return authorization
        return saved

    def baseline(self, version: dict, dataset_id: str, run_payload: dict) -> None:
        if workflow(version["spec_json"]) == "reference_v1":
            self.require(version, dataset_id, "run")
            self._save(
                version,
                dataset_id,
                "baseline",
                {
                    "run_id": run_payload["run_id"],
                    "metrics": run_payload["metrics"],
                    "data_scope": run_payload.get("data_scope", "fixed_baseline"),
                    "comparison": run_payload.get("comparison"),
                    "status": "PASSED",
                    "meaning": "fixed run recorded; profitability is a separate verdict",
                },
                self.dependencies(version, dataset_id),
            )

    def authorize(self, version_id: str, dataset_id: str, authorization: dict) -> dict:
        version = self._reference_version(version_id)
        self.require(version, dataset_id, "promote")
        authorization = dict(authorization)
        authorization.setdefault("objective_metric", "existing_score_v1")
        try:
            train_end = datetime.fromisoformat(authorization["train_end"])
            holdout = datetime.fromisoformat(authorization["holdout_start"])
            if (
                not train_end.tzinfo
                or not holdout.tzinfo
                or train_end > holdout
                or not authorization["objective"]
                or not isinstance(authorization["parameters"], dict)
                or authorization["objective_metric"]
                not in {
                    "existing_score_v1",
                    "net_pnl",
                    "profit_factor",
                    "max_equity_drawdown_pct",
                }
            ):
                raise ValueError()
            bars = self.data.load_bars(dataset_id)
            if not any(b.ts < train_end for b in bars) or not any(
                b.ts >= holdout for b in bars
            ):
                raise ValueError()
            try:
                previous = self._read(version, dataset_id, "search_authorization")[
                    "authorization"
                ]
            except HTTPException as exc:
                if exc.detail.get("code") != "EVIDENCE_REQUIRED":
                    raise
            else:
                if train_end > datetime.fromisoformat(
                    previous["train_end"]
                ) or holdout < datetime.fromisoformat(previous["holdout_start"]):
                    raise ValueError()
            if (
                version.get("parent_version_id")
                and version["spec_json"].get("development_operation") == "improve"
            ):
                parent = self._version(version["parent_version_id"])
                inherited = self._read(parent, dataset_id, "search_authorization")[
                    "authorization"
                ]
                if train_end > datetime.fromisoformat(
                    inherited["train_end"]
                ) or holdout < datetime.fromisoformat(inherited["holdout_start"]):
                    raise ValueError()
            for key, values in authorization["parameters"].items():
                if (
                    key not in version["spec_json"]["parameters"]
                    or not isinstance(values, list)
                    or not values
                ):
                    raise ValueError()
                for value in values:
                    candidate = deepcopy(version["spec_json"])
                    candidate["parameters"][key] = value
                    validate_spec(candidate)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                422,
                detail={
                    "code": "SEARCH_AUTHORIZATION_INVALID",
                    "message": "Declare objective, existing parameters with finite value lists, timezone-aware train_end <= holdout_start and observations in both partitions.",
                },
            ) from exc
        return self._save(
            version,
            dataset_id,
            "search_authorization",
            {"authorization": authorization},
            self.dependencies(version, dataset_id),
        )

    def training_bars(
        self, version: dict, dataset_id: str, bars: list[Bar]
    ) -> list[Bar]:
        authorization = self.require(version, dataset_id, "search")
        if authorization is None:
            return bars
        end = datetime.fromisoformat(authorization["train_end"])
        # A bar must have closed before the training boundary.
        from app.data import INTERVAL_MS

        step = INTERVAL_MS[version["spec_json"]["timeframe"]]
        return [
            b for b in bars if b.ts.timestamp() * 1000 + step <= end.timestamp() * 1000
        ]

    def child(self, parent: dict, child: dict, dataset_id: str) -> None:
        if workflow(parent["spec_json"]) != "reference_v1":
            return
        self.require(parent, dataset_id, "save", child["spec_json"])
        old = self._read(parent, dataset_id, "validation")
        # Re-run semantics and execution under the exact child tuple, never copy
        # parent PASS values into a new configuration.
        self.validate(child["version_id"], dataset_id, old["cases"])

    def status(self, version_id: str, dataset_id: str | None = None) -> dict:
        version = self._version(version_id)
        route = workflow(version["spec_json"])
        gates = {
            key: {"status": "NOT_RUN"}
            for key in (
                "semantic",
                "data",
                "execution",
                "economics",
                "target",
                "platform",
                "operational",
            )
        }
        result = {
            "workflow_version": route,
            "gates": gates,
            "blockers": [],
            "selected_target": version["spec_json"].get("selected_target"),
            "source_fidelity": {"status": "NOT_RUN"},
        }
        if route == "legacy_pine_v1":
            result["limitations"] = [
                "Legacy Pine evidence retains its original meaning; reference gates have not been inferred."
            ]
            return result
        if dataset_id:
            try:
                saved = self.require(version, dataset_id, "run")
                gates.update(
                    {k: saved["gates"][k] for k in ("semantic", "data", "execution")}
                )
                result["source_fidelity"] = saved["gates"]["source_fidelity"]
                try:
                    baseline = self._read(version, dataset_id, "baseline")
                    gates["economics"] = {
                        "status": "PASS_WITH_LIMITATIONS",
                        "metrics": baseline["metrics"],
                        "limitations": [
                            "Fixed baseline measured; economic qualification remains strategy-specific."
                        ],
                    }
                except HTTPException:
                    pass
                try:
                    target = self._read(version, dataset_id, "pine_target_preparation")
                    gates["target"] = {
                        "status": target["target_status"],
                        "feature_signal_parity": target["feature_signal_parity"],
                        "limitations": target["limitations"],
                    }
                    gates["platform"] = {"status": target["platform_status"]}
                except HTTPException:
                    pass
            except HTTPException as exc:
                result["blockers"].append(exc.detail)
        return result

    def casebook_path(self, version_id: str, dataset_id: str) -> Path:
        version = self._reference_version(version_id)
        dependencies = self.dependencies(version, dataset_id)
        saved = self._read(version, dataset_id, "validation", dependencies)
        record = next(
            r
            for r in self.repo.list_workflow_evidence(version_id, dataset_id)
            if r["kind"] == "validation" and r["dependencies"] == dependencies
        )
        path = Path(record["artifact_path"]).with_suffix(".html").resolve()
        if (
            not path.is_relative_to(self._root())
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != saved["casebook_sha256"]
        ):
            fail(
                "CASEBOOK_TAMPERED",
                "Casebook missing or differs from the saved ledger rendering.",
            )
        return path

    def prepare_pine_target(self, version_id: str, dataset_id: str, workbench) -> dict:
        """Late port demonstration. Feature parity is not broker/TV acceptance."""
        version = self._reference_version(version_id)
        self.require(version, dataset_id, "promote")
        spec = version["spec_json"]
        if spec["engine_id"] != "reference_ma_cross_v1":
            fail(
                "TARGET_ADAPTER_UNIMPLEMENTED",
                "Only the bounded MA Pine target demonstration is implemented.",
            )
        p = spec.get("parameters", {})
        source = f"""//@version=6
strategy("Python2Pine MA reference target", overlay=true, pyramiding=0, initial_capital={p.get("initial_capital", 100000)}, commission_type=strategy.commission.percent, commission_value={p.get("commission_pct", 0)}, slippage={p.get("slippage_ticks", 0)})
fast = ta.sma(close, {p.get("fast_len", 5)})
slow = ta.sma(close, {p.get("slow_len", 20)})
tr = na(close[1]) ? high - low : math.max(high - low, math.max(math.abs(high - close[1]), math.abs(low - close[1])))
atrValue = ta.sma(tr, {p.get("atr_len", 7)})
longCross = ta.crossover(fast, slow)
shortCross = ta.crossunder(fast, slow)
atrOk = not na(atrValue) and atrValue > 0 and atrValue >= {p.get("min_atr", 0)}
longSignal = longCross and atrOk and {str(p.get("allow_long", True)).lower()}
shortSignal = shortCross and atrOk and {str(p.get("allow_short", True)).lower()}
direction = longSignal ? 1 : shortSignal ? -1 : 0
if longSignal
    strategy.entry("L", strategy.long, qty={p.get("quantity", 1)})
if shortSignal
    strategy.entry("S", strategy.short, qty={p.get("quantity", 1)})
var float activeStop = na
var float activeTarget = na
if strategy.position_size != 0 and (strategy.position_size[1] == 0 or strategy.position_size * strategy.position_size[1] < 0)
    side = strategy.position_size > 0 ? 1 : -1
    activeStop := strategy.position_avg_price - side * atrValue[1] * {p.get("stop_mult", 2)}
    activeTarget := {p.get("target_r", 0)} > 0 ? strategy.position_avg_price + side * atrValue[1] * {p.get("stop_mult", 2)} * {p.get("target_r", 0)} : na
if strategy.position_size > 0
    strategy.exit("L-exit", "L", stop=activeStop, limit=activeTarget)
if strategy.position_size < 0
    strategy.exit("S-exit", "S", stop=activeStop, limit=activeTarget)
plot(fast, "Fast")
plot(slow, "Slow")
"""
        streams = {
            "features": [
                {
                    "name": "fast",
                    "expression": "fast",
                    "kind": "float",
                    "scale": 1000000,
                },
                {
                    "name": "slow",
                    "expression": "slow",
                    "kind": "float",
                    "scale": 1000000,
                },
                {
                    "name": "atr",
                    "expression": "atrValue",
                    "kind": "float",
                    "scale": 1000000,
                },
            ],
            "signals": [
                {
                    "name": "direction",
                    "expression": "direction",
                    "kind": "int",
                    "scale": 1,
                }
            ],
        }
        revision = workbench.create_revision(
            source_code=source,
            source_name="reference_ma_target.pine",
            mode="greenfield_strategy",
            settings_payload={
                "reference_version_id": version_id,
                "reference_dependencies": self.dependencies(version, dataset_id),
            },
            provenance={"origin": "python_reference_target", "trace_contract": streams},
            workbench_id=None,
            parent_revision_id=None,
        )
        window = self.data.pine_proof_window(dataset_id)
        proof = workbench.create_proof(
            revision["revision_id"],
            dataset_id=dataset_id,
            start_ms=window["start_ms"],
            end_ms=window["end_ms"],
            mintick=p.get("tick_size", 0.01),
            trace_rows=[],
            stream_expressions=streams,
            profile="basic_v1",
        )
        limitations = [
            "Generated Pine broker orders need independent execution/lifecycle parity, including entry-bar stops and gaps.",
            "Feature/signal local parity does not grant target acceptance; exact TradingView proof and explicit user verdict remain required.",
        ]
        parity = None
        if proof.get("local_trace"):
            reference = run_reference(spec, self.data.load_bars(dataset_id))
            parity = workbench.client.parity(
                {
                    "reference_rows": reference["trace"]["rows"],
                    "candidate_rows": proof["local_trace"]["rows"],
                    "contract": {
                        "exact_fields": ["signals.direction"],
                        "tolerance_fields": {
                            "features.fast": 1e-9,
                            "features.slow": 1e-9,
                            "features.atr": 1e-9,
                        },
                        "require_same_keys": True,
                    },
                }
            )
        saved = self._save(
            version,
            dataset_id,
            "pine_target_preparation",
            {
                "revision_id": revision["revision_id"],
                "pine_source_hash": revision["source_sha256"],
                "proof_evidence_id": proof["evidence_id"],
                "feature_signal_parity": parity,
                "target_status": "BLOCKED",
                "platform_status": "TRADINGVIEW_REVIEW_REQUIRED",
                "limitations": limitations,
            },
            self.dependencies(version, dataset_id),
        )
        return {
            **saved,
            "revision_id": revision["revision_id"],
            "feature_signal_parity": parity,
            "target_status": "BLOCKED",
            "platform_status": "TRADINGVIEW_REVIEW_REQUIRED",
            "limitations": limitations,
        }
