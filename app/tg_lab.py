from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import subprocess
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException

from app.config import BASE_DIR, settings
from app.tg_import import TgSnapshotImporter, canonical_json
from app.tg_models import ENGINE_VERSION, IMPORTER_VERSION, MODEL_VERSION, ManagementPolicy, SUPPORTED_ASSETS, TargetGeometryPolicy
from app.tg_replay import TgSignalReplayEngine
from app.tg_validation import chronological_split, full_promotion_improvement, paired_block_bootstrap_equivalence, pnl_metrics


class TgManagementLabService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.importer = TgSnapshotImporter(repository)
        self.replay_engine = TgSignalReplayEngine()
        settings.ensure_dirs()

    def import_snapshot(self, package_path: str) -> dict[str, Any]:
        return self.importer.import_package(package_path)

    def list_snapshots(self) -> list[dict[str, Any]]:
        return self.repository.list_tg_snapshots()

    def snapshot_detail(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self._snapshot(snapshot_id)
        return snapshot

    def coverage(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self._snapshot(snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "checksum": snapshot["checksum"],
            "broker_profile": snapshot["broker_profile"],
            "cohort_id": snapshot["cohort_id"],
            **snapshot["coverage_json"],
        }

    def run_baseline(self, snapshot_id: str, asset: str) -> dict[str, Any]:
        return self._run(snapshot_id, asset, optimize=False)

    def optimize_asset(
        self, snapshot_id: str, asset: str, seed: int = 0,
        candidate_family: str = "all", progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        return self._run(
            snapshot_id, asset, optimize=True, seed=seed,
            candidate_family=candidate_family, progress_callback=progress_callback,
        )

    def list_experiments(self, snapshot_id: str | None = None, asset: str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_tg_experiments(snapshot_id, asset)

    def experiment(self, experiment_id: str) -> dict[str, Any]:
        payload = self.repository.get_tg_experiment(experiment_id)
        if not payload:
            raise HTTPException(404, "TgSignalSniper experiment not found")
        return payload

    def _snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.repository.get_tg_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(404, "TgSignalSniper snapshot not found")
        return snapshot

    def _run(
        self, snapshot_id: str, asset: str, *, optimize: bool, seed: int = 0,
        candidate_family: str = "all", progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        asset = asset.upper()
        if asset not in SUPPORTED_ASSETS:
            raise HTTPException(400, f"Unsupported initial cohort asset: {asset}")
        candidate_family = candidate_family.lower()
        if candidate_family not in {"all", "management", "targets", "joint"}:
            raise HTTPException(400, "candidate_family must be all, management, targets, or joint")
        snapshot = self._snapshot(snapshot_id)
        snapshot_db = Path(snapshot["path"]) / "snapshot.sqlite3"
        all_operations = self._load_operations(snapshot_db, asset)
        evidence_tiers = self._evidence_tiers(snapshot_db, all_operations)
        version_sets = sorted({(
            item["statistics_schema_version"], item["signal_version"], item["parser_version"],
            item["execution_policy_version"], item["management_policy_version"], item["config_fingerprint"],
        ) for item in all_operations})
        def version_key(item: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
            return (
                item["statistics_schema_version"], item["signal_version"],
                item["parser_version"], item["execution_policy_version"],
                item["management_policy_version"], item["config_fingerprint"],
            )
        grouped: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = {}
        for operation in all_operations:
            grouped.setdefault(version_key(operation), []).append(operation)
        selected_version_set = (
            max(
                grouped,
                key=lambda key: (
                    max(str(item.get("published_at") or "") for item in grouped[key]),
                    len(grouped[key]), key,
                ),
            )
            if grouped else None
        )
        # Every closed operation in the declared cohort is mandatory evidence.
        # Version sets are diagnostic strata, never an exclusion filter.
        operations = list(all_operations)
        latest_operations = list(grouped.get(selected_version_set, []))
        baseline_versions = sorted({
            item["management_policy_version"] for item in latest_operations
            if item.get("management_policy_version")
        })
        baseline_policy = None
        for version in reversed(baseline_versions):
            baseline_policy = self.replay_engine.policy_from_snapshot(
                snapshot_db, version,
            )
            if baseline_policy is not None:
                break
        config = {
            "snapshot_id": snapshot_id,
            "asset": asset,
            "reference_version_set": (
                list(selected_version_set) if selected_version_set else None
            ),
            "version_sets_are_strata_not_filters": True,
            "observed_version_sets": [list(item) for item in version_sets],
            "seed": seed,
            "optimize": optimize,
            "candidate_family": candidate_family,
            "holdout_fraction": 0.25,
            "walk_forward_folds": 3,
            "minimum_exploratory_operations": 20,
            "minimum_promotional_operations": 40,
            "target_geometry_contract_version": "tg_target_geometry_v1",
            "target_grid": self._target_grid_contract(),
            "joint_top_targets": 3,
            "joint_max_candidates": 39,
            "bootstrap": {
                "purpose": "equivalence_and_simplicity_tiebreak_only",
                "confidence": 0.95, "seed": seed,
                "samples": 2000, "block_length": 3,
                "is_promotion_gate": False,
            },
            "holdout_contract": "single_final_candidate_evaluation_after_wf_selection",
            "engine_version": ENGINE_VERSION,
            "importer_version": IMPORTER_VERSION,
            "model_version": MODEL_VERSION,
        }
        code_hash = self._code_hash()
        experiment_hash = hashlib.sha256(canonical_json({"snapshot": snapshot["checksum"], "config": config, "code": code_hash}).encode()).hexdigest()
        experiment_id = f"tgexp_{experiment_hash[:16]}"

        exclusions: dict[str, list[str]] = {}
        baseline_results: dict[str, dict[str, Any]] = {}
        parity_diagnostics: list[dict[str, Any]] = []
        parity_failed = baseline_policy is None
        aggregate_actual = 0.0
        aggregate_replay = 0.0
        aggregate_abs_actual = 0.0
        for operation in operations:
            reasons: list[str] = []
            if not baseline_policy:
                reasons.append("INCOMPATIBLE_OR_MISSING_BASELINE_POLICY")
            if reasons:
                exclusions[operation["execution_id"]] = reasons
                continue
            # The immutable broker-deal baseline does not require a replay path.
            broker_operation = dict(operation)
            broker_operation["_use_broker_actual_baseline"] = True
            replay = self.replay_engine.replay(
                broker_operation, [], {}, baseline_policy,
            )
            replay_payload = replay.to_dict()
            baseline_results[operation["execution_id"]] = replay_payload
            if not replay.comparable or replay.net_pnl is None:
                exclusions[operation["execution_id"]] = list(replay.exclusions) or [replay.status]
                continue
            actual = operation.get("broker_realized_net_pnl")
            if actual is None:
                exclusions[operation["execution_id"]] = ["MISSING_BROKER_REALIZED_PNL"]
                continue
            actual = float(actual)
            difference = abs(float(replay.net_pnl) - actual)
            tolerance = max(0.01, 0.01 * float(operation.get("risk_amount") or 0))
            diagnostic = self._parity_diagnostic(operation, replay_payload, difference, tolerance)
            parity_diagnostics.append(diagnostic)
            if difference > tolerance:
                parity_failed = True
            aggregate_actual += actual
            aggregate_replay += float(replay.net_pnl)
            aggregate_abs_actual += abs(actual)
        aggregate_difference = abs(aggregate_replay - aggregate_actual)
        aggregate_tolerance = max(1.0, 0.0025 * aggregate_abs_actual)
        if aggregate_difference > aggregate_tolerance:
            parity_failed = True
        comparable = [operation for operation in operations if operation["execution_id"] in baseline_results and operation["execution_id"] not in exclusions]
        split = chronological_split(comparable)
        baseline_sections = self._sections(comparable, baseline_results, split)
        stress_profiles = list(snapshot["contract_json"].get("stress_profiles", []))
        parity = {
            "status": "BASELINE_PARITY_FAILED" if parity_failed else "PASSED",
            "individual_tolerance_formula": "max(USD 0.01, 0.01 * initial_risk_amount)",
            "aggregate_tolerance_formula": "max(USD 1.00, 0.0025 * sum(abs(actual_net_pnl)))",
            "aggregate_actual_net_pnl": aggregate_actual,
            "aggregate_replay_net_pnl": aggregate_replay,
            "aggregate_difference": aggregate_difference,
            "aggregate_tolerance": aggregate_tolerance,
            "operations": parity_diagnostics,
        }

        candidates: list[dict[str, Any]] = []
        family_finalists: dict[str, dict[str, Any]] = {}
        selected: dict[str, Any] | None = None
        holdout_evaluated_candidate_ids: list[str] = []
        started = time.monotonic()
        progress_done = 0
        target_count = len(self._target_geometries())
        management_count = len(self._candidate_policies(baseline_policy)) if baseline_policy else 0
        requested = {candidate_family} if candidate_family != "all" else {"management", "targets", "joint"}
        total_candidates = (
            (management_count if "management" in requested else 0)
            + (target_count if requested & {"targets", "joint"} else 0)
            + (39 if "joint" in requested else 0)
        )

        def progress(family: str, stage: str, message: str) -> None:
            if not progress_callback:
                return
            elapsed = time.monotonic() - started
            percent = round(100 * progress_done / max(1, total_candidates), 2)
            eta = (elapsed / progress_done * (total_candidates - progress_done)) if progress_done else None
            progress_callback({
                "asset": asset, "family": family, "stage": stage,
                "completed": progress_done, "total": total_candidates,
                "percent": percent, "elapsed_seconds": round(elapsed, 3),
                "eta_seconds": round(eta, 3) if eta is not None else None,
                "message": message,
            })

        evidence_status = self._evidence_status(len(comparable), len(operations), parity_failed, snapshot, operations, asset)
        if optimize and baseline_policy and not parity_failed and len(comparable) >= 20:
            development = [item for item in comparable if item["execution_id"] in set(split.development_ids)]
            management_candidates: list[dict[str, Any]] = []
            target_candidates: list[dict[str, Any]] = []
            if "management" in requested:
                for policy in self._candidate_policies(baseline_policy):
                    progress("MANAGEMENT_ONLY", "search", f"Evaluating {policy.policy_id}")
                    item = self._evaluate_development_candidate(
                        snapshot_db, development, split, baseline_sections, policy,
                        TargetGeometryPolicy.provider_original(), "MANAGEMENT_ONLY",
                        len(candidates), baseline_policy,
                    )
                    candidates.append(item); management_candidates.append(item)
                    progress_done += 1
                family_finalists["MANAGEMENT_ONLY"] = self._select_candidate(
                    management_candidates, split, seed, config["bootstrap"]
                )

            if requested & {"targets", "joint"}:
                for geometry in self._target_geometries():
                    progress("TARGET_GEOMETRY_ONLY", "search", f"Evaluating {geometry.geometry_id}")
                    item = self._evaluate_development_candidate(
                        snapshot_db, development, split, baseline_sections,
                        baseline_policy, geometry, "TARGET_GEOMETRY_ONLY",
                        len(candidates), baseline_policy,
                    )
                    target_candidates.append(item)
                    candidates.append(item)
                    progress_done += 1
                target_ranked = self._rank_candidates(target_candidates)
                if "targets" in requested:
                    family_finalists["TARGET_GEOMETRY_ONLY"] = self._select_candidate(
                        target_candidates, split, seed + 1000, config["bootstrap"]
                    )
                top_targets = target_ranked[:3]
                if "joint" in requested:
                    joint_candidates: list[dict[str, Any]] = []
                    for target in top_targets:
                        geometry = replace(
                            TargetGeometryPolicy.from_dict(target["target_geometry"]),
                            candidate_family="JOINT_TARGETS_AND_MANAGEMENT",
                        )
                        for policy in self._candidate_policies(baseline_policy):
                            if len(joint_candidates) >= 39:
                                break
                            progress("JOINT_TARGETS_AND_MANAGEMENT", "search", f"Evaluating {geometry.geometry_id} + {policy.policy_id}")
                            item = self._evaluate_development_candidate(
                                snapshot_db, development, split, baseline_sections,
                                policy, geometry, "JOINT_TARGETS_AND_MANAGEMENT",
                                len(candidates), baseline_policy,
                            )
                            candidates.append(item); joint_candidates.append(item)
                            progress_done += 1
                    if joint_candidates:
                        family_finalists["JOINT_TARGETS_AND_MANAGEMENT"] = self._select_candidate(
                            joint_candidates, split, seed + 2000, config["bootstrap"]
                        )

            finalists = list(family_finalists.values())
            if finalists:
                progress("ALL", "selection", "Selecting one finalist without holdout")
                selected = self._select_candidate(finalists, split, seed + 3000, config["bootstrap"])
                holdout_ops = [item for item in comparable if item["execution_id"] in set(split.holdout_ids)]
                progress(selected["candidate_family"], "holdout", "Evaluating the single finalist on untouched holdout")
                holdout_results = self._replay_many(
                    snapshot_db, holdout_ops,
                    ManagementPolicy.from_dict(selected["policy"]),
                    TargetGeometryPolicy.from_dict(selected["target_geometry"]),
                )
                selected["results"].update(holdout_results)
                selected["sections"] = self._sections(comparable, selected["results"], split)
                holdout_evaluated_candidate_ids = [selected["candidate_id"]]
                selected["holdout_evaluation_count"] = 1
                selected["walk_forward_gate"] = full_promotion_improvement(selected["sections"]["walk_forward_oos"], baseline_sections["walk_forward_oos"])
                selected["holdout_gate"] = full_promotion_improvement(selected["sections"]["holdout"], baseline_sections["holdout"])
                selected["same_comparable_operation_set"] = set(selected["results"]) == set(item["execution_id"] for item in comparable) and all(item.get("comparable") for item in selected["results"].values())
                selected["exact_promotion_set"] = all(item.get("diagnostics", {}).get("promotion_eligible", False) for item in selected["results"].values())
                progress(selected["candidate_family"], "stress", "Stressing baseline and the single finalist")
                selected["stress_scenarios"], selected["stress_gate"] = self._stress_finalist(
                    snapshot_db, comparable, split, baseline_policy, selected,
                    baseline_sections, stress_profiles,
                )
                selected["promotion_gate"] = bool(
                    len(comparable) >= 40 and selected["same_comparable_operation_set"]
                    and selected["exact_promotion_set"] and selected["walk_forward_gate"]
                    and selected["holdout_gate"] and selected["stress_gate"]
                )
            if len(comparable) < 40:
                evidence_status = "RESEARCH_ONLY"
            elif selected and selected["promotion_gate"]:
                evidence_status = "PROMOTION_CANDIDATE"
            else:
                evidence_status = "REJECTED"
            progress(selected["candidate_family"] if selected else "ALL", "writing", "Writing one experiment artifact")

        recommendation = self._recommendation(selected)

        result = {
            "experiment_id": experiment_id,
            "snapshot_id": snapshot_id,
            "snapshot_checksum": snapshot["checksum"],
            "broker_profile": snapshot["broker_profile"],
            "cohort_id": snapshot["cohort_id"],
            "asset": asset,
            "status": evidence_status,
            "promotion_is_statistical_only": True,
            "recommendation": recommendation,
            "recommendation_is_actionable": bool(selected and selected.get("promotion_gate")),
            "baseline_policy": baseline_policy.to_dict() if baseline_policy else None,
            "baseline_parity": parity,
            "coverage": snapshot["coverage_json"].get("assets", {}).get(asset, {}),
            "cohort_execution_ids": [item["execution_id"] for item in operations],
            "included_execution_ids": [item["execution_id"] for item in comparable],
            "excluded_executions": exclusions,
            "version_strata": {
                "|".join(key): [item["execution_id"] for item in values]
                for key, values in grouped.items()
            },
            "quality_flags": {
                item["execution_id"]: [
                    flag for flag, present in (
                        ("MANUAL_INTERVENTION", item.get("manual_intervention")),
                        ("ANOMALOUS_STATE", item.get("anomalous_state")),
                        ("MISSING_COST_BREAKDOWN", not item.get("costs_complete")),
                        ("UNRESOLVED_HISTORICAL_POLICY", not item.get("policy_resolved")),
                        ("MISSING_SYMBOL_SPEC", not item.get("symbol_spec_resolved")),
                    ) if present
                ]
                for item in operations
            },
            "evidence_tiers": evidence_tiers,
            "chronology": {
                "development_ids": list(split.development_ids),
                "holdout_ids": list(split.holdout_ids),
                "holdout_excluded_from_search_ranking_and_ties": True,
                "holdout_evaluated_candidate_ids": holdout_evaluated_candidate_ids,
                "holdout_candidate_evaluation_count": len(holdout_evaluated_candidate_ids),
                "walk_forward": [{"train_ids": list(train), "oos_ids": list(test)} for train, test in split.walk_forward],
            },
            "baseline_sections": baseline_sections,
            "baseline_results": baseline_results,
            "operation_contracts": {
                item["execution_id"]: {
                    "provider_entry": item.get("provider_entry"),
                    "actual_fill": item.get("actual_fill"),
                    "initial_provider_sl": item.get("initial_provider_sl"),
                    "provider_tp1": item.get("tp1"), "provider_tp2": item.get("tp2"),
                    "provider_tp3": item.get("tp3"), "timeframe": item.get("timeframe"),
                    "strategy_lane": item.get("strategy_lane"),
                } for item in operations
            },
            "venue_translation_diagnostics": {
                item["execution_id"]: item.get("venue_translation", {})
                for item in operations
            },
            "candidates_tested": len(candidates),
            "search_space": [{"candidate_id": item["candidate_id"], "family": item["candidate_family"], "policy": item["policy"], "target_geometry": item["target_geometry"]} for item in candidates],
            "search_space_hash": hashlib.sha256(canonical_json([{"candidate_id": item["candidate_id"], "family": item["candidate_family"]} for item in candidates]).encode()).hexdigest(),
            "search_contract": config,
            "stress_profiles": stress_profiles,
            "candidates": candidates,
            "family_finalists": family_finalists,
            "selected_candidate": selected,
            "timeframe_lane_diagnostics": self._subgroup_metrics(comparable, baseline_results, selected),
            "engine_version": ENGINE_VERSION,
            "importer_version": IMPORTER_VERSION,
            "model_version": MODEL_VERSION,
            "code_hash": code_hash,
            "seed": seed,
        }
        paths = self._write_artifacts(experiment_id, result)
        stored = {
            "experiment_id": experiment_id,
            "snapshot_id": snapshot_id,
            "broker_profile": snapshot["broker_profile"],
            "cohort_id": snapshot["cohort_id"],
            "asset": asset,
            "status": evidence_status,
            "engine_version": ENGINE_VERSION,
            "code_hash": code_hash,
            "config_json": config,
            "result_json": result,
            "artifact_path": str(paths["json"]),
            "report_path": str(paths["markdown"]),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repository.put_tg_experiment(stored)
        return self.repository.get_tg_experiment(experiment_id) or stored

    @staticmethod
    def _load_operations(snapshot_db: Path, asset: str) -> list[dict[str, Any]]:
        connection = sqlite3.connect(snapshot_db)
        try:
            return [json.loads(row[0]) for row in connection.execute("SELECT payload_json FROM operations WHERE asset = ? ORDER BY opened_at, execution_id", (asset,))]
        finally:
            connection.close()

    @staticmethod
    def _evidence_tiers(
        snapshot_db: Path, operations: list[dict[str, Any]],
    ) -> dict[str, str]:
        connection = sqlite3.connect(snapshot_db)
        try:
            tables = {
                str(row[0]) for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            exact_ids: set[str] = set()
            if "tick_coverage" in tables:
                for execution_id, payload_json in connection.execute(
                    "SELECT execution_id,payload_json FROM tick_coverage"
                ):
                    payload = json.loads(payload_json)
                    if (
                        str(payload.get("status")) == "COMPLETE"
                        and int(
                            payload.get("coverage_gap_count")
                            or payload.get("gap_count") or 0
                        ) == 0
                    ):
                        exact_ids.add(str(execution_id))
            mark_ids = (
                {
                    str(row[0]) for row in connection.execute(
                        "SELECT DISTINCT execution_id FROM one_second_marks"
                    )
                }
                if "one_second_marks" in tables else set()
            )
            return {
                item["execution_id"]: (
                    "EXACT_TICK" if item["execution_id"] in exact_ids
                    else "APPROXIMATE_1S"
                    if item["execution_id"] in mark_ids else "MISSING"
                )
                for item in operations
            }
        finally:
            connection.close()

    def _replay_many(
        self, snapshot_db: Path, operations: list[dict[str, Any]],
        policy: ManagementPolicy,
        target_geometry: TargetGeometryPolicy | None = None,
    ) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for operation in operations:
            _, ticks, coverage = self.replay_engine.load_operation(snapshot_db, operation["execution_id"])
            results[operation["execution_id"]] = self.replay_engine.replay(
                operation, ticks, coverage, policy, target_geometry,
                counterfactual=True,
            ).to_dict()
        return results

    def _evaluate_development_candidate(
        self, snapshot_db: Path, operations: list[dict[str, Any]], split: Any,
        baseline_sections: dict[str, Any], policy: ManagementPolicy,
        geometry: TargetGeometryPolicy, family: str, evaluation_order: int,
        baseline_policy: ManagementPolicy,
    ) -> dict[str, Any]:
        candidate_results = self._replay_many(snapshot_db, operations, policy, geometry)
        sections = self._sections(operations, candidate_results, split)
        expected_ids = {item["execution_id"] for item in operations}
        comparable_ids = {
            execution_id for execution_id, item in candidate_results.items()
            if item.get("comparable")
        }
        exact = all(
            item.get("diagnostics", {}).get("promotion_eligible", False)
            for item in candidate_results.values()
        )
        identity = expected_ids == comparable_ids
        candidate_id = "tgcand_" + hashlib.sha256(canonical_json({
            "family": family, "policy": policy.to_dict(),
            "target_geometry": geometry.to_dict(),
        }).encode()).hexdigest()[:16]
        candidate = {
            "candidate_id": candidate_id,
            "candidate_family": family,
            "evaluation_order": evaluation_order,
            "policy": policy.to_dict(),
            "target_geometry": geometry.to_dict(),
            "parent_policy_id": baseline_policy.policy_id,
            "sections": sections,
            "complexity": self._complexity(baseline_policy, policy, geometry),
            "development_comparable_operation_set": identity,
            "development_exact_promotion_set": exact,
            "preselection_eligible": identity and exact,
            "walk_forward_gate": full_promotion_improvement(
                sections["walk_forward_oos"], baseline_sections["walk_forward_oos"],
            ),
            "holdout_evaluated": False,
            "holdout_gate": None,
            "stress_scenarios": [],
            "stress_gate": None,
            "promotion_gate": False,
            "results": candidate_results,
        }
        candidate["selection_score"] = self._selection_score(candidate, baseline_sections)
        candidate["censored_execution_ids"] = [
            execution_id for execution_id, item in candidate_results.items()
            if not item.get("comparable")
        ]
        candidate["target_horizon_backfill"] = [
            {"execution_id": execution_id, "pending_targets": item.get("diagnostics", {}).get("pending_targets", [])}
            for execution_id, item in candidate_results.items()
            if "CENSORED_TARGET_HORIZON" in item.get("exclusions", [])
        ]
        return candidate

    @staticmethod
    def _rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(candidates, key=lambda item: (
            not item.get("preselection_eligible", False),
            not item.get("walk_forward_gate", False),
            -float(item.get("selection_score") or 0),
            float(item.get("sections", {}).get("walk_forward_oos", {}).get("max_drawdown_money") or 0),
            int(item.get("complexity") or 0), int(item.get("evaluation_order") or 0),
        ))

    def _select_candidate(
        self, candidates: list[dict[str, Any]], split: Any, seed: int,
        bootstrap: dict[str, Any],
    ) -> dict[str, Any]:
        ranked = self._rank_candidates(candidates)
        best = ranked[0]
        wf_ids = [execution_id for _, test in split.walk_forward for execution_id in test]
        for ordinal, challenger in enumerate(ranked[1:], start=1):
            if (
                challenger.get("preselection_eligible") != best.get("preselection_eligible")
                or challenger.get("walk_forward_gate") != best.get("walk_forward_gate")
            ):
                continue
            equivalence = paired_block_bootstrap_equivalence(
                challenger["results"], best["results"], wf_ids,
                seed=int(seed) + ordinal,
                samples=int(bootstrap["samples"]),
                block_length=int(bootstrap["block_length"]),
                confidence=float(bootstrap["confidence"]),
            )
            challenger.setdefault("equivalence_tests", []).append({
                "against": best["candidate_id"], **equivalence,
                "purpose": "simplicity_tiebreak_only",
            })
            if equivalence["equivalent"] and challenger["complexity"] < best["complexity"]:
                best = challenger
        return best

    def _stress_finalist(
        self, snapshot_db: Path, operations: list[dict[str, Any]], split: Any,
        baseline_policy: ManagementPolicy, selected: dict[str, Any],
        baseline_sections: dict[str, Any], stress_profiles: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], bool]:
        scenarios: list[dict[str, Any]] = []
        all_pass = True
        geometry = TargetGeometryPolicy.from_dict(selected["target_geometry"])
        candidate_policy = ManagementPolicy.from_dict(selected["policy"])
        for profile in stress_profiles:
            name = str(profile.get("name") or "stress")
            common = {
                "latency_msc": int(profile.get("latency_msc") or 0),
                "exit_slippage_price": float(profile.get("slippage_price") or 0),
                "stress_same_millisecond_stop_first": bool(profile.get("same_millisecond_stop_first", False)),
            }
            baseline_stress_policy = replace(
                baseline_policy, policy_id=f"{baseline_policy.policy_id}_{name}",
                parent_policy_id=None, **common,
            )
            candidate_stress_policy = replace(
                candidate_policy, policy_id=f"{candidate_policy.policy_id}_{name}",
                **common,
            )
            baseline_results = self._replay_many(
                snapshot_db, operations, baseline_stress_policy,
                TargetGeometryPolicy.provider_original(),
            )
            candidate_results = self._replay_many(
                snapshot_db, operations, candidate_stress_policy, geometry,
            )
            baseline_stress = self._sections(operations, baseline_results, split)
            candidate_stress = self._sections(operations, candidate_results, split)
            identity = (
                set(candidate_results) == set(baseline_results)
                and all(item.get("comparable") for item in candidate_results.values())
            )
            scenario_pass = bool(
                identity
                and full_promotion_improvement(candidate_stress["walk_forward_oos"], baseline_stress["walk_forward_oos"])
                and full_promotion_improvement(candidate_stress["holdout"], baseline_stress["holdout"])
            )
            all_pass = all_pass and scenario_pass
            scenarios.append({
                "name": name, "profile": profile,
                "baseline_sections": baseline_stress,
                "candidate_sections": candidate_stress,
                "same_comparable_operation_set": identity,
                "full_gate": scenario_pass,
            })
        return scenarios, all_pass

    @staticmethod
    def _target_grid_contract() -> dict[str, Any]:
        return {
            "tp1_r": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
            "tp2_r": [1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
            "tp3_r": [1.5, 2.0, 3.0, 4.0, 5.0, 6.0],
            "constraint": "0 < tp1_r < tp2_r < tp3_r",
            "valid_combinations": 106,
            "version": "tg_target_grid_v1",
        }

    @classmethod
    def _target_geometries(cls) -> list[TargetGeometryPolicy]:
        grid = cls._target_grid_contract()
        geometries: list[TargetGeometryPolicy] = []
        for tp1 in grid["tp1_r"]:
            for tp2 in grid["tp2_r"]:
                for tp3 in grid["tp3_r"]:
                    if not 0 < tp1 < tp2 < tp3:
                        continue
                    geometry_id = f"fixed_r_{tp1:g}_{tp2:g}_{tp3:g}".replace(".", "p")
                    geometries.append(TargetGeometryPolicy(
                        geometry_id, "provider_original", mode="FIXED_R",
                        candidate_family="TARGET_GEOMETRY_ONLY",
                        tp1_r=tp1, tp2_r=tp2, tp3_r=tp3,
                    ))
        return geometries

    @staticmethod
    def _recommendation(selected: dict[str, Any] | None) -> str:
        if not selected or not selected.get("promotion_gate"):
            return "KEEP_PROVIDER_BASELINE"
        return {
            "MANAGEMENT_ONLY": "KEEP_PROVIDER_TARGETS_OPTIMIZE_MANAGEMENT",
            "TARGET_GEOMETRY_ONLY": "OPTIMIZE_TARGET_GEOMETRY",
            "JOINT_TARGETS_AND_MANAGEMENT": "JOINT_POLICY_RESEARCH_CANDIDATE",
        }.get(selected["candidate_family"], "KEEP_PROVIDER_BASELINE")

    @staticmethod
    def _sections(operations: list[dict[str, Any]], results: dict[str, dict[str, Any]], split: Any) -> dict[str, Any]:
        by_id = {item["execution_id"]: item for item in operations}
        def metrics(ids: Iterable[str]) -> dict[str, Any]:
            selected = [results[item] for item in ids if item in results and results[item].get("comparable")]
            return pnl_metrics(selected)
        wf_ids = [execution_id for _, test in split.walk_forward for execution_id in test]
        return {
            "global": metrics(by_id),
            "development": metrics(split.development_ids),
            "walk_forward_oos": metrics(wf_ids),
            "holdout": metrics(split.holdout_ids),
            "walk_forward_windows": [
                {"train": metrics(train), "oos": metrics(test), "train_ids": list(train), "oos_ids": list(test)}
                for train, test in split.walk_forward
            ],
        }

    @staticmethod
    def _parity_diagnostic(operation: dict[str, Any], replay: dict[str, Any], difference: float, tolerance: float) -> dict[str, Any]:
        milestones = replay.get("milestones", [])
        replay_reason = replay.get("fills", [{}])[-1].get("reason") if replay.get("fills") else None
        return {
            "execution_id": operation["execution_id"],
            "actual_net_pnl": operation.get("broker_realized_net_pnl"),
            "replay_net_pnl": replay.get("net_pnl"),
            "difference": difference,
            "tolerance": tolerance,
            "passed": difference <= tolerance,
            "diagnostics": {
                "leg_order": [item.get("leg_id") for item in replay.get("fills", [])],
                "partial_targets": [item.get("event") for item in milestones if str(item.get("event", "")).startswith("TP")],
                "remaining_volume": replay.get("final_remaining_volume"),
                "breakeven": any("BREAKEVEN" in str(item.get("event")) for item in milestones),
                "stop_after_tp2": any(item.get("event") == "STOP_TO_TP1_AFTER_TP2" for item in milestones),
                "actual_close_reason": operation.get("close_reason"),
                "replay_close_reason": replay_reason,
                "opened_at_utc": operation.get("opened_at"),
                "closed_at_utc": operation.get("closed_at"),
                "timestamp_differences_are_diagnostic_only": True,
            },
        }

    @staticmethod
    def _candidate_policies(baseline: ManagementPolicy) -> list[ManagementPolicy]:
        mutations: list[dict[str, Any]] = [
            {"early_breakeven_activation_r": 0.5},
            {"early_breakeven_activation_r": 0.75},
            {"early_breakeven_activation_r": 1.0, "early_breakeven_offset_r": 0.05},
            {"trailing_activation_r": 1.0, "trailing_distance_r": 0.5, "trailing_step_r": 0.25},
            {"trailing_activation_r": 1.5, "trailing_distance_r": 0.75, "trailing_step_r": 0.25},
            {"trailing_activation_r": 1.0, "trailing_distance_r": 0.5, "trailing_step_r": 0.25, "trailing_after": "tp1", "tp1_action": "trailing"},
            {"trailing_activation_r": 1.5, "trailing_distance_r": 0.75, "trailing_step_r": 0.25, "trailing_after": "tp2", "tp2_action": "trailing"},
            {"mfe_protect_activation_r": 1.0, "mfe_protect_fraction": 0.5},
            {"mfe_protect_activation_r": 1.5, "mfe_protect_fraction": 0.7},
            {"partials": (0.4, 0.3, 0.3)},
            {"partials": (0.6, 0.2, 0.2)},
            {"time_stop_seconds": 3600},
            {"time_stop_seconds": 7200},
        ]
        candidates = []
        for ordinal, mutation in enumerate(mutations, start=1):
            candidates.append(replace(baseline, policy_id=f"{baseline.policy_id}_m{ordinal:02d}", parent_policy_id=baseline.policy_id, **mutation))
        return candidates

    @staticmethod
    def _complexity(
        baseline: ManagementPolicy, candidate: ManagementPolicy,
        geometry: TargetGeometryPolicy | None = None,
    ) -> int:
        base = baseline.to_dict()
        current = candidate.to_dict()
        ignored = {"policy_id", "parent_policy_id"}
        management_changes = sum(base[key] != current[key] for key in base if key not in ignored)
        geometry_changes = 0 if not geometry or geometry.mode == "PROVIDER_ORIGINAL" else 3
        return management_changes + geometry_changes

    @staticmethod
    def _selection_score(candidate: dict[str, Any], baseline_sections: dict[str, Any]) -> float:
        current = candidate["sections"]["walk_forward_oos"]
        baseline = baseline_sections["walk_forward_oos"]
        return (
            (current["gross_profit_net"] - baseline["gross_profit_net"])
            + (baseline["gross_loss_net"] - current["gross_loss_net"])
        )

    @staticmethod
    def _evidence_status(count: int, total_count: int, parity_failed: bool, snapshot: dict[str, Any], operations: list[dict[str, Any]], asset: str) -> str:
        if total_count < 20:
            return "INSUFFICIENT_TRADES"
        exact_count = int(snapshot.get("coverage_json", {}).get("assets", {}).get(asset, {}).get("complete_coverage", 0))
        if exact_count < 20 and any(item.get("one_second_mark_count") for item in operations):
            return "RESEARCH_ONLY"
        if exact_count < 20:
            return "INSUFFICIENT_EXACT_COVERAGE"
        if count < 20:
            return "INSUFFICIENT_TRADES"
        if parity_failed:
            return "BASELINE_PARITY_FAILED"
        if count < 40:
            return "RESEARCH_ONLY"
        if any(not item.get("costs_complete") or not item.get("policy_resolved") or not item.get("symbol_spec_resolved") for item in operations):
            return "RESEARCH_ONLY"
        return "RESEARCH_ONLY"

    @staticmethod
    def _subgroup_metrics(operations: list[dict[str, Any]], baseline_results: dict[str, dict[str, Any]], selected: dict[str, Any] | None) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], list[str]] = {}
        for operation in operations:
            groups.setdefault((operation["timeframe"], operation["strategy_lane"]), []).append(operation["execution_id"])
        diagnostics = []
        candidate_results = selected.get("results", {}) if selected else {}
        for (timeframe, lane), ids in sorted(groups.items()):
            baseline = pnl_metrics([baseline_results[item] for item in ids if item in baseline_results])
            candidate = pnl_metrics([candidate_results[item] for item in ids if item in candidate_results]) if selected else None
            diagnostics.append({"timeframe": timeframe, "lane": lane, "operation_ids": ids, "baseline": baseline, "candidate": candidate, "candidate_worsens_subgroup": bool(candidate and candidate["net_pnl"] < baseline["net_pnl"])})
        return diagnostics

    def _write_artifacts(self, experiment_id: str, result: dict[str, Any]) -> dict[str, Path]:
        root = settings.tg_experiment_dir
        json_path = root / f"{experiment_id}.json"
        csv_path = root / f"{experiment_id}.csv"
        markdown_path = root / f"{experiment_id}.md"
        json_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "execution_id", "included", "evidence_tier", "quality_flags",
                "exclusion_reasons", "baseline_net_pnl", "candidate_net_pnl",
                "candidate_status", "provider_entry", "actual_fill", "initial_provider_sl",
                "provider_tp1", "provider_tp2", "provider_tp3",
                "proposed_tp1", "proposed_tp2", "proposed_tp3",
                "timeframe", "strategy_lane", "candidate_family",
                "operational_migration", "provider_geometry_source",
                "execution_venue", "provider_entry_price", "provider_stop_loss",
                "venue_price_delta", "reference_quote_bid", "reference_quote_ask",
                "destination_quote_bid", "destination_quote_ask",
                "quote_skew_seconds", "quote_acquisition_seconds",
                "venue_order_id", "venue_position_key",
                "cohort_decision", "cohort_decided_at",
                "cohort_authority_execution_id", "cohort_authority_status",
                "cohort_authority_leg_count",
            ])
            writer.writeheader()
            selected_results = (result.get("selected_candidate") or {}).get("results", {})
            ids = sorted(set(result["included_execution_ids"]) | set(result["excluded_executions"]))
            for execution_id in ids:
                contract = result.get("operation_contracts", {}).get(execution_id, {})
                candidate_result = selected_results.get(execution_id, {})
                targets = candidate_result.get("diagnostics", {}).get("resolved_targets", {})
                venue = result.get("venue_translation_diagnostics", {}).get(
                    execution_id, {}
                )
                venue_csv = {
                    key: value for key, value in venue.items()
                    if key not in {"provider_tp1", "provider_tp2", "provider_tp3"}
                }
                writer.writerow({
                    "execution_id": execution_id,
                    "included": execution_id in result["included_execution_ids"],
                    "evidence_tier": result.get("evidence_tiers", {}).get(execution_id),
                    "quality_flags": "|".join(result.get("quality_flags", {}).get(execution_id, [])),
                    "exclusion_reasons": "|".join(result["excluded_executions"].get(execution_id, [])),
                    "baseline_net_pnl": result["baseline_results"].get(execution_id, {}).get("net_pnl"),
                    "candidate_net_pnl": candidate_result.get("net_pnl"),
                    "candidate_status": candidate_result.get("status"),
                    **contract,
                    "proposed_tp1": targets.get("TP1"),
                    "proposed_tp2": targets.get("TP2"),
                    "proposed_tp3": targets.get("TP3"),
                    "candidate_family": (result.get("selected_candidate") or {}).get("candidate_family"),
                    **venue_csv,
                })
        markdown_path.write_text(self._markdown_report(result), encoding="utf-8")
        return {"json": json_path, "csv": csv_path, "markdown": markdown_path}

    @staticmethod
    def _markdown_report(result: dict[str, Any]) -> str:
        baseline = result["baseline_sections"]
        lines = [
            f"# TgSignalSniper management experiment {result['experiment_id']}", "",
            f"- Asset: {result['asset']}", f"- Broker: {result['broker_profile']}",
            f"- Cohort: {result['cohort_id']}", f"- Snapshot: `{result['snapshot_id']}`",
            f"- Engine: `{result['engine_version']}`", f"- Status: **{result['status']}**", "",
            "`PROMOTION_CANDIDATE` is a statistical recommendation only. This lab never publishes policies or contacts AutoKraken, MT5, or Telegram.", "",
            "## Evidence", "",
            f"- Included operations: {len(result['included_execution_ids'])}",
            f"- Excluded/censored operations: {len(result['excluded_executions'])}",
            f"- Exact tick paths: {sum(value == 'EXACT_TICK' for value in result.get('evidence_tiers', {}).values())}",
            f"- One-second research paths: {sum(value == 'APPROXIMATE_1S' for value in result.get('evidence_tiers', {}).values())}",
            f"- Observed immutable version strata: {len(result.get('version_strata', {}))} (used as diagnostics, never as exclusions)",
            f"- Baseline parity: {result['baseline_parity']['status']}", "",
            f"- Final decision: **{result.get('recommendation', 'KEEP_PROVIDER_BASELINE')}**",
            f"- Holdout candidate evaluations: {result.get('chronology', {}).get('holdout_candidate_evaluation_count', 0)} (holdout excluded from all search/ranking/ties)",
            f"- Search-space hash: `{result.get('search_space_hash', '')}`", "",
            "## Baseline sections", "",
            "| Section | Operations | Gross profit net | Gross loss net | Net P&L | PF | Max DD |", "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for key in ("development", "walk_forward_oos", "holdout", "global"):
            metrics = baseline[key]
            lines.append(f"| {key} | {metrics['operations']} | {metrics['gross_profit_net']:.2f} | {metrics['gross_loss_net']:.2f} | {metrics['net_pnl']:.2f} | {metrics['profit_factor']:.4f} | {metrics['max_drawdown_money']:.2f} |")
        venue_diagnostics = result.get("venue_translation_diagnostics", {})
        migrations = sorted({
            str(item.get("operational_migration"))
            for item in venue_diagnostics.values()
            if item.get("operational_migration") is not None
        })
        venues = sorted({
            str(item.get("execution_venue"))
            for item in venue_diagnostics.values() if item.get("execution_venue")
        })
        migrated_geometry = sum(
            item.get("provider_geometry_source") == "MIGRATION_20_PROVIDER_FIELDS"
            for item in venue_diagnostics.values()
        )
        lines.extend([
            "", "## Venue and translation diagnostics", "",
            f"- Operational migrations: {', '.join(migrations) if migrations else 'not declared'}.",
            f"- Execution venues: {', '.join(venues) if venues else 'not recorded'}.",
            f"- Operations using migration-20 provider geometry: {migrated_geometry}.",
            "- Actual broker fill remains the replay entry; venue/provider fields are immutable diagnostics.",
        ])
        lines.extend(["", "## Coverage and backfill", ""])
        missing = result.get("coverage", {}).get("requires_backfill_execution_ids", [])
        lines.append(f"Executions requiring tick backfill: {', '.join(missing) if missing else 'none declared' }.")
        lines.extend(["", "## Timeframe and lane diagnostics", ""])
        for group in result["timeframe_lane_diagnostics"]:
            lines.append(f"- {group['timeframe']} / {group['lane']}: {len(group['operation_ids'])} operations; baseline net {group['baseline']['net_pnl']:.2f}.")
        lines.extend(["", "## Best development/WF candidate by family", ""])
        for family, finalist in result.get("family_finalists", {}).items():
            wf = finalist["sections"]["walk_forward_oos"]
            lines.append(
                f"- {family}: `{finalist['candidate_id']}`; score {finalist['selection_score']:.2f}; "
                f"WF net {wf['net_pnl']:.2f}; complexity {finalist['complexity']}; "
                f"geometry `{finalist['target_geometry']['geometry_id']}`."
            )
        if result.get("selected_candidate"):
            selected = result["selected_candidate"]
            lines.extend([
                "", "## Selected candidate", "",
                f"- Candidate: `{selected['candidate_id']}`",
                f"- Family: `{selected['candidate_family']}`",
                f"- Policy: `{selected['policy']['policy_id']}`",
                f"- Target geometry: `{selected['target_geometry']['geometry_id']}`",
                f"- Walk-forward full gate: {selected['walk_forward_gate']}",
                f"- Holdout full gate: {selected['holdout_gate']}",
                f"- Stress gate: {selected['stress_gate']}",
                f"- Same operation set: {selected.get('same_comparable_operation_set')}",
                f"- Exact promotion set: {selected.get('exact_promotion_set')}",
            ])
            geometry = selected["target_geometry"]
            lines.append(f"- Proposed R: TP1={geometry.get('tp1_r')}, TP2={geometry.get('tp2_r')}, TP3={geometry.get('tp3_r')}.")
            lines.extend(["", "### Finalist sections", "", "| Section | GP | GL | Net | PF | Max DD |", "|---|---:|---:|---:|---:|---:|"])
            for key in ("development", "walk_forward_oos", "holdout", "global"):
                metrics = selected["sections"][key]
                lines.append(f"| {key} | {metrics['gross_profit_net']:.2f} | {metrics['gross_loss_net']:.2f} | {metrics['net_pnl']:.2f} | {metrics['profit_factor']:.4f} | {metrics['max_drawdown_money']:.2f} |")
            lines.extend(["", "### Stress", ""])
            if selected.get("stress_scenarios"):
                for scenario in selected["stress_scenarios"]:
                    lines.append(f"- {scenario['name']}: full gate={scenario['full_gate']}; same operation set={scenario['same_comparable_operation_set']}.")
            else:
                lines.append("No stress profiles were declared by the snapshot.")
            backfill = selected.get("target_horizon_backfill", [])
            lines.extend(["", "### Target-horizon backfill", "", f"Executions requiring future target capture: {', '.join(item['execution_id'] for item in backfill) if backfill else 'none' }."])
            if selected.get("promotion_gate"):
                lines.extend(["", f"Actionable statistical recommendation: **{result['recommendation']}**. It is offline advice only and is never published automatically."])
            else:
                lines.extend(["", "No actionable policy recommendation: the provider baseline remains in force because the complete promotion contract did not pass."])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _code_hash() -> str:
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "unknown"
