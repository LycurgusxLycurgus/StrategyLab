"""Run a small, isolated reference-first vertical workflow demonstration.

The default run exercises the MA control and stateful pivot/BOS consumer,
records independent expected cases and gates, saves fixed baselines, and makes
an authorized stop-distance child. ``--pine-target`` additionally exercises the
late Pine workbench adapter; this never fabricates a TradingView verdict.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def configure_isolated_paths(run_root: Path) -> None:
    """Set app storage before importing any StrategyLab modules."""
    os.environ["APP_DB_PATH"] = str(run_root / "mutation_lab.sqlite3")
    os.environ["APP_DATA_DIR"] = str(run_root / "data")
    os.environ["APP_RUN_DIR"] = str(run_root / "runs")
    os.environ["APP_REPORT_DIR"] = str(run_root / "reports")
    os.environ["APP_DIAGNOSTIC_DIR"] = str(run_root / "diagnostics")
    os.environ["APP_TG_SNAPSHOT_DIR"] = str(run_root / "tg-snapshots")
    os.environ["APP_TG_EXPERIMENT_DIR"] = str(run_root / "tg-experiments")
    os.environ["PINE_DEVELOPMENT_DIR"] = str(run_root / "strategy-development")


def json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def make_reference_spec(
    engine_id: str,
    *,
    origin: str,
    operation: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    from app.reference import EXECUTION_CONTRACT

    spec: dict[str, Any] = {
        "workflow_version": "reference_v1",
        "engine_id": engine_id,
        "timeframe": "15m",
        "strategy_origin": origin,
        "development_operation": operation,
        "translation_objective": "not_applicable" if operation == "create" else "performance_oriented",
        "execution_contract": dict(EXECUTION_CONTRACT),
        "parameters": parameters,
    }
    if origin in {"discretionary_origin", "hybrid"}:
        spec.update(
            {
                "translation_objective": "performance_oriented",
                "interpretation": {
                    "entry": "Publish a strict confirmed swing only after right-side bars close; accept a later close through its level.",
                    "indicator": "Use the bounded pivot/BOS detector as the explicit executable interpretation.",
                },
                "ambiguities": [
                    "The source idea does not define displacement magnitude or discretionary swing selection.",
                    "This bounded example chooses strict pivots and a later close break; that choice does not prove trader equivalence.",
                ],
                "transformations": [
                    {
                        "parent_rule_id": "source.swing_selection",
                        "child_rule_id": "reference.pivot_bos",
                        "operation": "formalize",
                        "rationale": "Make swing publication and entry timing executable.",
                        "source_evidence": "bounded demonstration interpretation",
                        "ambiguity_or_problem": "Discretionary swing and displacement terms lack thresholds.",
                        "executable_choice": "Strict two-left/two-right pivot; later close beyond the confirmed level.",
                        "meaning_change": False,
                        "expected_effect": "Confirmation delay and deterministic close-based entry.",
                        "validation_evidence": "Independent accepted, equal-high, replaced-level and expired-level cases.",
                    }
                ],
            }
        )
    return spec


def register_version(repo, *, version_id: str, family_id: str, name: str, source: str, spec: dict) -> dict:
    from datetime import UTC, datetime

    created_at = datetime.now(UTC).isoformat()
    version = {
        "version_id": version_id,
        "family_id": family_id,
        "parent_version_id": None,
        "name": name,
        "stage": "reference_spec",
        "source_code": source,
        "spec_json": spec,
        "causal_story": "Small independently adjudicated reference-first vertical fixture.",
        "mutation_json": {"origin": "reference_vertical_fixture"},
        "notes": "Disposable isolated reference workflow demonstration.",
        "created_at": created_at,
    }
    repo.put_family(
        {
            "family_id": family_id,
            "title": name,
            "asset": "CASE",
            "venue": "Fixture",
            "timeframe": "15m",
            "current_version_id": version_id,
            "created_at": created_at,
        }
    )
    repo.put_version(version)
    return version


def run_pipeline(run_root: Path, *, pine_target: bool) -> dict[str, Any]:
    configure_isolated_paths(run_root)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from app.config import settings
    from app.data import Bar, DataService
    from app.lab import MutationLabService
    from app.reference import EXECUTION_CONTRACT
    from app.reference_evidence import EvidenceService
    from app.reference_tests import _bars, reference_expected_cases
    from app.storage import Repository

    settings.ensure_dirs()
    repo = Repository(settings.db_path)
    data = DataService(repo)
    lab = MutationLabService(repo, data)
    evidence = EvidenceService(repo, data)

    cases = reference_expected_cases()
    ma_cases = [cases[2]]
    # This frozen TTL=100 spec accepts the BOS, strict-equality, and replacement
    # fixtures. The separate TTL=2 boundary remains covered by the focused test
    # suite instead of mixing a different parameter value into one validation.
    pivot_cases = cases[3:6]
    ma_bars = _bars(cases[2]["bars"])
    dataset = data.import_fixture_dataset(ma_bars, "CASE", "15m", "reference-vertical")
    dataset_id = dataset["dataset_id"]

    ma_spec = make_reference_spec(
        "reference_ma_cross_v1",
        origin="systematic_native",
        operation="create",
        parameters={"fast_len": 2, "slow_len": 3, "atr_len": 2, "stop_mult": 2, "allow_long": False},
    )
    ma_version = register_version(
        repo,
        version_id="ver_reference_ma_demo",
        family_id="family_reference_ma_demo",
        name="Reference MA control",
        source="Independent two-line moving-average rule fixture.",
        spec=ma_spec,
    )
    ma_validation = evidence.validate(ma_version["version_id"], dataset_id, ma_cases)
    ma_run = lab.run_version(ma_version["version_id"], dataset_id)

    pivot_spec = make_reference_spec(
        "reference_pivot_bos_v1",
        origin="discretionary_origin",
        operation="translate",
        parameters={
            "pivot_left": 2,
            "pivot_right": 2,
            "atr_len": 2,
            "stop_mult": 2,
            "allow_long": True,
            "allow_short": True,
        },
    )
    pivot_source = "Qualitative swing / break idea; source does not settle swing thresholds or discretionary selection."
    pivot_version = register_version(
        repo,
        version_id="ver_reference_pivot_demo",
        family_id="family_reference_pivot_demo",
        name="Discretionary pivot interpretation",
        source=pivot_source,
        spec=pivot_spec,
    )
    pivot_validation = evidence.validate(
        pivot_version["version_id"], dataset_id, pivot_cases
    )
    pivot_run = lab.run_version(pivot_version["version_id"], dataset_id)

    bars = data.load_bars(dataset_id)
    authorization = {
        "objective": "Demonstrate a bounded stop-distance mutation after a fixed reference baseline.",
        "parameters": {"stop_mult": [2, 3]},
        "train_end": (bars[7].ts + timedelta(minutes=15)).isoformat(),
        "holdout_start": (bars[8].ts + timedelta(minutes=15)).isoformat(),
    }
    ma_authorization = evidence.authorize(
        ma_version["version_id"], dataset_id, authorization
    )
    ma_child_run = lab.save_tuned_version(
        ma_version["version_id"],
        dataset_id,
        {"stop_mult": 3},
        name="Authorized MA stop-distance child",
    )
    pivot_authorization = evidence.authorize(
        pivot_version["version_id"], dataset_id, authorization
    )
    pivot_child_run = lab.save_tuned_version(
        pivot_version["version_id"],
        dataset_id,
        {"stop_mult": 3},
        name="Authorized pivot interpretation child",
    )

    pine_result: dict[str, Any] | None = None
    if pine_target:
        from app.pine2python_client import Pine2PythonClient
        from app.pine_workbench import PineWorkbenchService

        workbench = PineWorkbenchService(repo, data, Pine2PythonClient())
        pine_result = evidence.prepare_pine_target(
            ma_version["version_id"], dataset_id, workbench
        )

    report = {
        "schema_version": "reference_vertical_v1",
        "run_root": str(run_root),
        "dataset_id": dataset_id,
        "dataset_quality": data.dataset_quality_manifest(dataset_id),
        "workflow_version": "reference_v1",
        "execution_contract": EXECUTION_CONTRACT,
        "consumers": {
            "ma": {
                "version_id": ma_version["version_id"],
                "independent_cases": ma_cases,
                "validation_path": ma_validation["artifact_path"],
                "casebook_path": ma_validation["casebook_path"],
                "fixed_baseline_run_id": ma_run["run_id"],
                "authorized_search": ma_authorization["payload"]["authorization"],
                "child_run_id": ma_child_run["run_id"],
                "child_version_id": ma_child_run["version_id"],
                "source_fidelity": "NOT_APPLICABLE",
            },
            "pivot_bos": {
                "version_id": pivot_version["version_id"],
                "source_description": pivot_source,
                "interpretation": pivot_spec["interpretation"],
                "ambiguities": pivot_spec["ambiguities"],
                "independent_cases": pivot_cases,
                "validation_path": pivot_validation["artifact_path"],
                "casebook_path": pivot_validation["casebook_path"],
                "fixed_baseline_run_id": pivot_run["run_id"],
                "authorized_search": pivot_authorization["payload"]["authorization"],
                "child_run_id": pivot_child_run["run_id"],
                "child_version_id": pivot_child_run["version_id"],
                "source_fidelity": pivot_validation["gates"]["source_fidelity"],
            },
        },
        "pine_target": None
        if pine_result is None
        else {
            "revision_id": pine_result["revision_id"],
            "feature_signal_parity": pine_result["feature_signal_parity"],
            "target_status": pine_result["target_status"],
            "platform_status": pine_result["platform_status"],
            "limitations": pine_result["limitations"],
        },
        "verdicts": {
            "semantics": "independently checked for both bounded consumers",
            "source_fidelity": "qualified for selected discretionary interpretation; not trader equivalence",
            "economics": "fixed baselines recorded; no profitability qualification claimed",
            "pine_tradingview": "not run" if pine_result is None else "review remains blocked pending TradingView and broker corroboration",
            "production": "not accepted",
        },
    }
    json_write(run_root / "reference-vertical-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pine-target",
        action="store_true",
        help="Additionally use the real late Pine target workbench adapter.",
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[2]
    demo_root = repository_root / "artifacts" / "strategy-development" / "reference-demo"
    run_root = demo_root / f"run-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    try:
        report = run_pipeline(run_root, pine_target=args.pine_target)
    except Exception as error:
        json_write(
            run_root / "reference-vertical-error.json",
            {"run_root": str(run_root), "error_type": type(error).__name__, "error": str(error)},
        )
        raise
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
