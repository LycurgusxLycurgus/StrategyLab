from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.features.backtests.schema import BacktestRunRequest, FamilySweepRequest
from app.features.backtests.service import BacktestService
from app.features.data.schema import ImportDatasetRequest
from app.features.data.service import DataService
from app.features.evaluations.service import EvaluationService
from app.features.strategies.service import StrategyService
from app.infra.db import Database
from app.test_support import make_test_config, write_csv, write_strategy_family, write_ui_files


class BacktestServiceTests(unittest.TestCase):
    def test_runs_a_zero_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            data_service = DataService(config, db)
            csv_path = config.app_data_dir / "btc_1h.csv"
            write_csv(csv_path, "1H")
            dataset = data_service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="1H", dataset_name="btc-1h")
            )
            strategy_service = StrategyService(config)
            evaluation_service = EvaluationService(db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
            first = backtest_service.run_backtest(BacktestRunRequest(family_id="a_zero_srlc", dataset_id=dataset.dataset_id), persist=False)
            second = backtest_service.run_backtest(BacktestRunRequest(family_id="a_zero_srlc", dataset_id=dataset.dataset_id), persist=False)
            self.assertEqual(first.metrics, second.metrics)
            self.assertEqual(first.verdict, second.verdict)
            self.assertGreater(first.metrics["overall"]["trades"], 0)

    def test_runs_smart_money_with_gate_debugger_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "smart_money_structural", "5m")
            db = Database(config)
            data_service = DataService(config, db)
            csv_path = config.app_data_dir / "btc_5m.csv"
            write_csv(csv_path, "5m")
            dataset = data_service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="5m", dataset_name="btc-5m")
            )
            strategy_service = StrategyService(config)
            evaluation_service = EvaluationService(db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
            result = backtest_service.run_backtest(
                BacktestRunRequest(
                    family_id="smart_money_structural",
                    dataset_id=dataset.dataset_id,
                    parameter_overrides={
                        "mss_confirmation_type": "relaxed",
                        "displacement_requirement_atr": 0.8,
                        "entry_retrace_level": 0.705,
                        "htf_fractal_depth": 3,
                        "min_rr_target": 2.0,
                        "stop_loss_padding_atr": 0.1,
                    },
                ),
                persist=False,
            )
            artifact = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
            self.assertGreater(artifact["diagnostics"]["zone_hits"], 0)
            self.assertGreater(artifact["diagnostics"]["sweeps"], 0)
            self.assertGreater(artifact["diagnostics"]["gate_no_mss"], 0)

    def test_smart_money_parameters_change_gate_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "smart_money_structural", "5m")
            db = Database(config)
            data_service = DataService(config, db)
            csv_path = config.app_data_dir / "btc_5m.csv"
            write_csv(csv_path, "5m")
            dataset = data_service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="5m", dataset_name="btc-5m")
            )
            strategy_service = StrategyService(config)
            evaluation_service = EvaluationService(db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
            conservative = backtest_service.run_backtest(
                BacktestRunRequest(
                    family_id="smart_money_structural",
                    dataset_id=dataset.dataset_id,
                    parameter_overrides={
                        "entry_retrace_level": 0.5,
                        "displacement_requirement_atr": 1.2,
                        "htf_fractal_depth": 3,
                        "min_rr_target": 2.0,
                        "stop_loss_padding_atr": 0.3,
                    },
                ),
                persist=False,
            )
            aggressive = backtest_service.run_backtest(
                BacktestRunRequest(
                    family_id="smart_money_structural",
                    dataset_id=dataset.dataset_id,
                    parameter_overrides={
                        "entry_retrace_level": 0.705,
                        "displacement_requirement_atr": 0.8,
                        "htf_fractal_depth": 5,
                        "min_rr_target": 3.0,
                        "stop_loss_padding_atr": 0.1,
                    },
                ),
                persist=False,
            )
            conservative_artifact = json.loads(Path(conservative.artifact_path).read_text(encoding="utf-8"))
            aggressive_artifact = json.loads(Path(aggressive.artifact_path).read_text(encoding="utf-8"))
            self.assertGreater(conservative_artifact["diagnostics"]["zone_hits"], 0)
            self.assertGreater(aggressive_artifact["diagnostics"]["zone_hits"], 0)
            self.assertNotEqual(conservative_artifact["diagnostics"]["sweeps"], aggressive_artifact["diagnostics"]["sweeps"])

    def test_reruns_and_deletes_persisted_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            data_service = DataService(config, db)
            csv_path = config.app_data_dir / "btc_1h.csv"
            write_csv(csv_path, "1H")
            dataset = data_service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="1H", dataset_name="btc-1h")
            )
            strategy_service = StrategyService(config)
            evaluation_service = EvaluationService(db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
            first = backtest_service.run_backtest(
                BacktestRunRequest(
                    family_id="a_zero_srlc",
                    dataset_id=dataset.dataset_id,
                    parameter_overrides={"lookback_days": 10},
                )
            )
            rerun = backtest_service.rerun(first.run_id)
            self.assertNotEqual(first.run_id, rerun.run_id)
            self.assertEqual(rerun.parameters["lookback_days"], 10)
            deleted = backtest_service.delete_run(first.run_id)
            self.assertTrue(deleted["deleted"])
            self.assertIsNone(db.fetch_one("select run_id from backtest_runs where run_id = ?", (first.run_id,)))

    def test_runs_family_sweep(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            db = Database(config)
            data_service = DataService(config, db)
            csv_path = config.app_data_dir / "btc_1h.csv"
            write_csv(csv_path, "1H")
            dataset = data_service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="1H", dataset_name="btc-1h")
            )
            strategy_service = StrategyService(config)
            evaluation_service = EvaluationService(db)
            backtest_service = BacktestService(config, db, strategy_service, data_service, evaluation_service)
            sweep = backtest_service.run_family_sweep(FamilySweepRequest(family_id="a_zero_srlc", dataset_id=dataset.dataset_id))
            self.assertGreaterEqual(sweep.total_variants, 2)
            self.assertEqual(len(sweep.runs), sweep.total_variants)

    def test_strategy_manifest_allows_string_grid_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_strategy_family(config, "smart_money_structural", "5m")
            strategy_service = StrategyService(config)
            family = strategy_service.get_family("smart_money_structural")
            self.assertEqual(family.parameters["mss_confirmation_type"], "strict")
            self.assertEqual(family.parameters["displacement_requirement_atr"], 1.0)


if __name__ == "__main__":
    unittest.main()
