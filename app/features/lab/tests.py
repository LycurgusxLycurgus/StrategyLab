from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.features.backtests.service import BacktestService
from app.features.data.service import DataService
from app.features.evaluations.service import EvaluationService
from app.features.lab.schema import OptimizeRequest, ProposalRequest, ReviewRequest
from app.features.lab.service import LabService
from app.features.strategies.service import StrategyService
from app.infra.db import Database
from app.test_support import make_test_config, write_strategy_family, write_ui_files


class LabServiceTests(unittest.TestCase):
    def test_optimizes_survivor_and_creates_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            strategy_service = StrategyService(config)
            data_service = DataService(config, db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, EvaluationService(db))
            db.execute(
                """
                insert into backtest_runs
                (run_id, family_id, dataset_id, timeframe, status, verdict, parameters_json, metrics_json, artifact_path, report_path)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run_survivor",
                    "a_zero_srlc",
                    "dataset_survivor",
                    "1H",
                    "completed",
                    "research_survivor",
                    json.dumps({"lookback_days": 60, "range_multiplier": 1.18, "age_threshold_bars": 100}),
                    json.dumps({"out_of_sample": {"sharpe": 1.3, "profit_factor": 1.2, "max_drawdown": 0.1}}),
                    str(config.app_run_dir / "survivor.json"),
                    None,
                ),
            )
            lab_service = LabService(config, db, strategy_service, backtest_service)
            original = backtest_service.run_backtest
            backtest_service.run_backtest = lambda payload, persist=False: type(
                "Summary",
                (),
                {
                    "parameters": payload.parameter_overrides,
                    "verdict": "research_survivor",
                    "metrics": {"out_of_sample": {"sharpe": 1.4, "profit_factor": 1.2, "max_drawdown": 0.1}},
                },
            )()
            result = lab_service.optimize(OptimizeRequest(source_run_id="run_survivor", max_variants=2))
            proposal = lab_service.create_proposal(
                ProposalRequest(
                    family_id="a_zero_srlc",
                    proposal_type="parameter_patch",
                    hypothesis="Tighten range age threshold for faster breakout bias.",
                    patch={"age_threshold_bars": 120},
                )
            )
            backtest_service.run_backtest = original
            self.assertEqual(len(result["rankings"]), 2)
            self.assertTrue(proposal["artifact_path"].endswith(".md"))

    def test_deletes_graveyard_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            strategy_service = StrategyService(config)
            data_service = DataService(config, db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, EvaluationService(db))
            report_path = config.app_graveyard_dir / "graveyard_run.md"
            report_path.write_text("graveyard\n", encoding="utf-8")
            db.insert_artifact(
                artifact_id="graveyard_run",
                artifact_type="graveyard_report",
                family_id="a_zero_srlc",
                dataset_id="dataset_1",
                source_run_id="run_1",
                path=str(report_path),
                payload={"run_id": "run_1"},
            )
            db.execute(
                """
                insert into backtest_runs
                (run_id, family_id, dataset_id, timeframe, status, verdict, parameters_json, metrics_json, artifact_path, report_path)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run_1",
                    "a_zero_srlc",
                    "dataset_1",
                    "1H",
                    "completed",
                    "rejected",
                    json.dumps({"lookback_days": 60}),
                    json.dumps({"out_of_sample": {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0}}),
                    str(config.app_run_dir / "run_1.json"),
                    str(report_path),
                ),
            )
            lab_service = LabService(config, db, strategy_service, backtest_service)
            deleted = lab_service.delete_graveyard("graveyard_run")
            self.assertTrue(deleted["deleted"])
            self.assertFalse(report_path.exists())
            row = db.fetch_one("select report_path from backtest_runs where run_id = ?", ("run_1",))
            self.assertIsNone(row["report_path"])

    def test_creates_llm_review_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            config.gemini_api_key = "test-key"
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            strategy_service = StrategyService(config)
            data_service = DataService(config, db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, EvaluationService(db))
            db.execute(
                """
                insert into backtest_runs
                (run_id, family_id, dataset_id, timeframe, status, verdict, parameters_json, metrics_json, artifact_path, report_path)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run_review",
                    "a_zero_srlc",
                    "dataset_review",
                    "1H",
                    "completed",
                    "rejected",
                    json.dumps({"lookback_days": 60}),
                    json.dumps({"overall": {"trades": 24}, "out_of_sample": {"sharpe": 0.5, "profit_factor": 0.9, "max_drawdown": 0.2}}),
                    str(config.app_run_dir / "review.json"),
                    None,
                ),
            )
            lab_service = LabService(config, db, strategy_service, backtest_service)
            lab_service._call_gemini = lambda prompt: json.dumps(
                {
                    "family_diagnosis": "test diagnosis",
                    "parameter_grid_patch": {"keep": {}, "expand": {}, "drop": [], "reason": "test"},
                    "conjectures": [],
                    "black_box_meta_notes": [],
                    "coding_agent_brief": {"priority": "test", "safe_changes": [], "avoid": []},
                }
            )
            result = lab_service.review_family(ReviewRequest(family_id="a_zero_srlc", dataset_id="dataset_review"))
            self.assertEqual(result["family_id"], "a_zero_srlc")
            self.assertTrue(Path(result["artifact_path"]).exists())


if __name__ == "__main__":
    unittest.main()
