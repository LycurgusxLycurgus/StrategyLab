from __future__ import annotations

import math
import json
import socket
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.config import settings
from app.data import Bar, DataService
from app.lab import MutationLabService
from app.main import DatasetDownloadRequest
from app.storage import Repository


def build_fixture_bars(count: int = 3200) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    price = 30000.0
    previous_close = price
    for index in range(count):
        regime = (index // 220) % 4
        drift = [9.0, -7.0, 5.5, -4.5][regime]
        wave = math.sin(index / 5.0) * 38 + math.sin(index / 19.0) * 66
        impulse = ((index % 87) - 43) * 0.9
        close = price + drift + wave + impulse
        open_price = previous_close + math.sin(index / 3.0) * 9
        high = max(open_price, close) + 18 + abs(math.sin(index / 7.0) * 11)
        low = min(open_price, close) - 18 - abs(math.cos(index / 9.0) * 11)
        volume = 400 + abs(math.sin(index / 11.0) * 180)
        bars.append(
            Bar(
                ts=start + timedelta(minutes=15 * index),
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=round(volume, 4),
                symbol="BTCUSDT",
                timeframe="15m",
            )
        )
        price = close + drift * 0.12
        previous_close = close
    return bars


class MutationLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original = {
            "db_path": settings.db_path,
            "data_dir": settings.data_dir,
            "run_dir": settings.run_dir,
            "report_dir": settings.report_dir,
            "diagnostic_dir": settings.diagnostic_dir,
            "seed_spec_path": settings.seed_spec_path,
        }
        settings.db_path = self.root / "artifacts" / "mutation_lab.sqlite3"
        settings.data_dir = self.root / "artifacts" / "data"
        settings.run_dir = self.root / "artifacts" / "runs"
        settings.report_dir = self.root / "artifacts" / "reports"
        settings.diagnostic_dir = self.root / "artifacts" / "diagnostics"
        settings.seed_spec_path = self.root / "strategies" / "btc_intraday_parent.json"
        settings.ensure_dirs()
        self.repo = Repository(settings.db_path)
        self.data_service = DataService(self.repo)
        self.lab = MutationLabService(self.repo, self.data_service)
        self.lab.ensure_seeded()

    def tearDown(self) -> None:
        settings.db_path = self.original["db_path"]
        settings.data_dir = self.original["data_dir"]
        settings.run_dir = self.original["run_dir"]
        settings.report_dir = self.original["report_dir"]
        settings.diagnostic_dir = self.original["diagnostic_dir"]
        settings.seed_spec_path = self.original["seed_spec_path"]
        self.temp_dir.cleanup()

    def test_seed_family_and_version_exist(self) -> None:
        family = self.repo.get_family("btc_intraday")
        self.assertIsNotNone(family)
        self.assertEqual(family["current_version_id"], "ver_btc_intraday_parent")
        version = self.repo.get_version("ver_btc_intraday_parent")
        self.assertIsNotNone(version)
        self.assertTrue(settings.seed_spec_path.exists())

    def test_run_parent_persists_metrics_and_artifacts(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        payload = self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        self.assertIn(payload["verdict"], {"graveyard", "research_survivor", "promotion_candidate"})
        self.assertGreater(payload["metrics"]["total_trades"], 0)
        self.assertIn("buy_hold_return_pct", payload["metrics"])
        self.assertIn("outperformance_pct", payload["metrics"])
        self.assertIn("buy_hold_start_price", payload["metrics"])
        self.assertIn("buy_hold_end_price", payload["metrics"])
        self.assertIn("buy_hold_max_drawdown_pct", payload["metrics"])
        self.assertIn("buy_hold_calmar", payload["metrics"])
        self.assertIn("calmar", payload["metrics"])
        self.assertIn("calmar_delta", payload["metrics"])
        self.assertIn("daily_sharpe", payload["metrics"])
        self.assertIn("daily_sortino", payload["metrics"])
        self.assertIn("worst_daily_return_pct", payload["metrics"])
        self.assertIn("avg_entry_exposure_pct", payload["metrics"])
        self.assertIn("max_entry_exposure_pct", payload["metrics"])
        self.assertIn("avg_initial_risk_pct", payload["metrics"])
        start_price = payload["metrics"]["buy_hold_start_price"]
        end_price = payload["metrics"]["buy_hold_end_price"]
        expected_buy_hold_pct = ((end_price - start_price) / start_price) * 100
        self.assertAlmostEqual(payload["metrics"]["buy_hold_return_pct"], round(expected_buy_hold_pct, 2))
        self.assertAlmostEqual(
            payload["metrics"]["buy_hold_return"],
            round(payload["metrics"]["initial_capital"] * (payload["metrics"]["buy_hold_return_pct"] / 100), 2),
            delta=1.0,
        )
        self.assertIn("mfe_r", payload["trades"][0])
        self.assertIn("mae_r", payload["trades"][0])
        self.assertIn("quantity", payload["trades"][0])
        self.assertIn("entry_notional", payload["trades"][0])
        self.assertIn("entry_exposure_pct", payload["trades"][0])
        self.assertIn("initial_risk_pct", payload["trades"][0])
        self.assertIn("entry_features", payload["trades"][0])
        self.assertTrue(Path(payload["artifact_path"]).exists())
        self.assertTrue(Path(payload["report_path"]).exists())
        report = Path(payload["report_path"]).read_text(encoding="utf-8")
        self.assertIn("## Side Decomposition", report)
        self.assertIn("## Exit-Reason Decomposition", report)
        self.assertIn("## Period Decomposition", report)
        self.assertIn("## Production Gate", report)
        self.assertIn("## Full-Whitebox Diagnostic Queue", report)
        stored_runs = self.repo.list_runs(family_id="btc_intraday")
        self.assertEqual(len(stored_runs), 1)

    def test_time_decay_exit_is_disabled_by_default_and_opt_in(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        base_result = self.lab.engine.run(version["spec_json"], bars)
        self.assertEqual(base_result["diagnostics"]["time_decay_exits"], 0)

        tuned_spec = json.loads(json.dumps(version["spec_json"]))
        tuned_spec["parameters"].update(
            {
                "time_decay_exit_enabled": True,
                "time_decay_bars": 10,
                "time_decay_min_mfe_r": 10.0,
            }
        )
        tuned_result = self.lab.engine.run(tuned_spec, bars)
        self.assertGreater(tuned_result["diagnostics"]["time_decay_exits"], 0)
        self.assertTrue(any(trade["reason"] == "time_decay" for trade in tuned_result["trades"]))

    def test_short_quality_gate_is_disabled_by_default_and_blocks_opt_in_shorts(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        base_result = self.lab.engine.run(version["spec_json"], bars)
        self.assertEqual(base_result["diagnostics"]["short_quality_gate_blocks"], 0)

        tuned_spec = json.loads(json.dumps(version["spec_json"]))
        tuned_spec["parameters"].update(
            {
                "short_quality_gate_enabled": True,
                "short_quality_gate_rule": "block_below_sma",
                "short_quality_gate_len_bars": 100,
            }
        )
        tuned_result = self.lab.engine.run(tuned_spec, bars)
        self.assertGreater(tuned_result["diagnostics"]["short_quality_gate_blocks"], 0)
        self.assertLessEqual(tuned_result["diagnostics"]["signals_short"], base_result["diagnostics"]["signals_short"])

    def test_breakeven_stop_is_disabled_by_default_and_moves_stop_when_opt_in(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        base_result = self.lab.engine.run(version["spec_json"], bars)
        self.assertEqual(base_result["diagnostics"]["breakeven_stop_moves"], 0)

        tuned_spec = json.loads(json.dumps(version["spec_json"]))
        tuned_spec["parameters"].update(
            {
                "breakeven_stop_enabled": True,
                "breakeven_trigger_mfe_r": 0.1,
                "breakeven_lock_r": 0.0,
            }
        )
        tuned_result = self.lab.engine.run(tuned_spec, bars)
        self.assertGreater(tuned_result["diagnostics"]["breakeven_stop_moves"], 0)
        self.assertTrue(any(abs(trade["stop_price"] - trade["entry_price"]) < 0.01 for trade in tuned_result["trades"]))

    def test_time_risk_filter_is_disabled_by_default_and_blocks_opt_in_entries(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        base_result = self.lab.engine.run(version["spec_json"], bars)
        self.assertEqual(base_result["diagnostics"]["time_risk_filter_blocks"], 0)

        tuned_spec = json.loads(json.dumps(version["spec_json"]))
        tuned_spec["parameters"].update(
            {
                "time_risk_filter_enabled": True,
                "time_risk_block_weekdays": [0, 1, 2, 3, 4, 5, 6],
                "time_risk_block_utc_hours": [],
            }
        )
        tuned_result = self.lab.engine.run(tuned_spec, bars)
        self.assertGreater(tuned_result["diagnostics"]["time_risk_filter_blocks"], 0)
        self.assertLess(tuned_result["diagnostics"]["entries"], base_result["diagnostics"]["entries"])

    def test_generate_white_box_proposals_and_run_pack(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        proposals = self.lab.generate_proposals("ver_btc_intraday_parent", include_hybrid=False)
        self.assertTrue(proposals)
        self.assertTrue(all(proposal["kind"] == "white_box" for proposal in proposals))
        result = self.lab.run_proposal_pack("ver_btc_intraday_parent", dataset["dataset_id"], include_hybrid=False)
        self.assertEqual(result["tested_count"], len(proposals))
        self.assertIsNotNone(result["best_run"])
        self.assertGreaterEqual(len(self.repo.list_runs(family_id="btc_intraday")), len(proposals) + 1)

    def test_tuning_edges_preview_and_save_tuned_child(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        edges = self.lab.list_tuning_edges("ver_btc_intraday_parent")
        self.assertTrue(edges)
        self.assertGreaterEqual(edges[0]["priority"], edges[-1]["priority"])
        preview = self.lab.preview_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["spec"]["parameters"]["stop_mult"], 4.0)
        self.assertIsNotNone(preview["comparison"])
        saved = self.lab.save_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        self.assertNotEqual(saved["version_id"], "ver_btc_intraday_parent")
        child = self.repo.get_version(saved["version_id"])
        self.assertEqual(child["mutation_json"]["origin"], "manual_parameter_tune")
        self.assertEqual(child["spec_json"]["parameters"]["stop_mult"], 4.0)
        child_edges = self.lab.list_tuning_edges(saved["version_id"])
        stop_edge = next(edge for edge in child_edges if edge["lever"] == "stop_mult")
        self.assertEqual(stop_edge["current_value"], 4.0)
        self.assertTrue(any(edge["lever"] == "time_risk_block_utc_hours" for edge in child_edges))
        self.assertTrue(any(edge["value_type"] == "list" for edge in child_edges))
        self.assertTrue(any(edge["lever"] == "sizing_mode" for edge in child_edges))

    def test_existing_child_versions_are_upgraded_with_phase_three_edges(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        legacy_spec = json.loads(json.dumps(version["spec_json"]))
        for key in (
            "time_decay_exit_enabled",
            "short_quality_gate_enabled",
            "breakeven_stop_enabled",
            "time_risk_filter_enabled",
            "hybrid_reverse_exit_triage_enabled",
            "hybrid_time_decay_triage_enabled",
            "sizing_mode",
            "notional_pct",
            "risk_pct",
            "max_leverage",
        ):
            legacy_spec["parameters"].pop(key, None)
        legacy_spec["mutation_space"] = [
            item
            for item in legacy_spec["mutation_space"]
            if not item["lever"].startswith(("time_", "short_quality_", "breakeven_", "hybrid_"))
            and item["lever"] not in {"sizing_mode", "notional_pct", "risk_pct", "max_leverage"}
        ]
        self.repo.put_version(
            {
                **version,
                "version_id": "ver_legacy_child",
                "parent_version_id": "ver_btc_intraday_parent",
                "name": "Legacy Child",
                "spec_json": legacy_spec,
            }
        )
        edges = self.lab.list_tuning_edges("ver_legacy_child")
        upgraded = self.repo.get_version("ver_legacy_child")
        self.assertIn("time_risk_filter_enabled", upgraded["spec_json"]["parameters"])
        self.assertIn("hybrid_reverse_exit_triage_enabled", upgraded["spec_json"]["parameters"])
        self.assertIn("hybrid_time_decay_triage_enabled", upgraded["spec_json"]["parameters"])
        self.assertIn("sizing_mode", upgraded["spec_json"]["parameters"])
        self.assertTrue(any(edge["lever"] == "breakeven_trigger_mfe_r" for edge in edges))
        self.assertTrue(any(edge["lever"] == "hybrid_reverse_exit_min_mfe_r" for edge in edges))
        self.assertTrue(any(edge["lever"] == "max_leverage" for edge in edges))
        weekday_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_weekdays")
        hour_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_utc_hours")
        self.assertIn([5, 6], weekday_edge["alternatives"])
        self.assertIn([23], hour_edge["alternatives"])
        self.assertGreaterEqual(len(hour_edge["alternatives"]), 30)

    def test_phase_three_upgrade_refreshes_existing_narrow_candidate_grids(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        legacy_spec = json.loads(json.dumps(version["spec_json"]))
        for mutation in legacy_spec["mutation_space"]:
            if mutation["lever"] == "time_risk_block_utc_hours":
                mutation["values"] = [[], [13], [15], [21], [13, 15, 21]]
            if mutation["lever"] == "time_risk_block_weekdays":
                mutation["values"] = [[], [6]]
        self.repo.put_version({**version, "spec_json": legacy_spec})
        edges = self.lab.list_tuning_edges("ver_btc_intraday_parent")
        weekday_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_weekdays")
        hour_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_utc_hours")
        self.assertIn([0, 1, 2, 3, 4], weekday_edge["alternatives"])
        self.assertIn([20, 21, 22], hour_edge["alternatives"])

    def test_phase_three_numeric_levers_use_extensive_range_searches(self) -> None:
        edges = {edge["lever"]: edge for edge in self.lab.list_tuning_edges("ver_btc_intraday_parent")}
        self.assertEqual(edges["time_decay_bars"]["search_mode"], "range")
        self.assertEqual(len(self.lab._candidate_values(edges["time_decay_bars"])), 300)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["time_decay_min_mfe_r"])), 40)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["short_quality_gate_len_bars"])), 70)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["breakeven_trigger_mfe_r"])), 55)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["breakeven_lock_r"])), 21)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_reverse_exit_min_mfe_r"])), 60)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_time_decay_triage_max_unrealized_r"])), 30)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_time_decay_triage_max_mfe_r"])), 20)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["notional_pct"])), 15)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["risk_pct"])), 10)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["max_leverage"])), 4)

    def test_portfolio_sizing_modes_change_exposure(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        fixed_spec = json.loads(json.dumps(version["spec_json"]))
        fixed_spec["parameters"]["sizing_mode"] = "fixed_quantity"
        fixed_result = self.lab.engine.run(fixed_spec, bars)

        notional_spec = json.loads(json.dumps(version["spec_json"]))
        notional_spec["parameters"].update(
            {
                "sizing_mode": "fixed_notional_pct",
                "notional_pct": 0.5,
                "max_leverage": 1.0,
            }
        )
        notional_result = self.lab.engine.run(notional_spec, bars)

        risk_spec = json.loads(json.dumps(version["spec_json"]))
        risk_spec["parameters"].update(
            {
                "sizing_mode": "fixed_risk_pct",
                "risk_pct": 0.005,
                "max_leverage": 1.0,
            }
        )
        risk_result = self.lab.engine.run(risk_spec, bars)

        self.assertGreater(fixed_result["metrics"]["total_trades"], 0)
        self.assertGreater(notional_result["metrics"]["total_trades"], 0)
        self.assertGreater(risk_result["metrics"]["total_trades"], 0)
        self.assertAlmostEqual(notional_result["trades"][0]["entry_exposure_pct"], 50.0, delta=0.5)
        self.assertLessEqual(max(trade["entry_exposure_pct"] for trade in risk_result["trades"]), 100.01)
        self.assertNotEqual(fixed_result["metrics"]["net_pnl"], notional_result["metrics"]["net_pnl"])

    def test_capital_model_warnings_explain_all_in_notional_sizing(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        spec = json.loads(json.dumps(version["spec_json"]))
        spec["parameters"].update(
            {
                "sizing_mode": "fixed_notional_pct",
                "notional_pct": 1.0,
                "allow_short": True,
            }
        )
        warnings = self.lab._capital_model_warnings(
            spec,
            {
                "max_initial_risk_pct": 12.5,
            },
        )
        joined = " ".join(warnings)
        self.assertIn("100.0%", joined)
        self.assertIn("all-in 1x compounding", joined)
        self.assertIn("tail-risk flag", joined)

    def test_production_gate_requires_portfolio_model_or_benchmark_efficiency(self) -> None:
        spec = self.repo.get_version("ver_btc_intraday_parent")["spec_json"]
        metrics = {
            "total_trades": 100,
            "profit_factor": 1.5,
            "max_equity_drawdown_pct": 8.0,
            "net_pnl": 10_000,
            "sharpe": 1.0,
            "sortino": 1.4,
            "daily_sharpe": 1.0,
            "daily_sortino": 1.2,
            "calmar": 0.9,
            "max_initial_risk_pct": 1.0,
            "max_entry_exposure_pct": 100.0,
            "avg_entry_exposure_pct": 80.0,
            "worst_daily_return_pct": -2.0,
            "outperformance_pct": -20.0,
            "calmar_delta": -0.1,
        }
        self.assertEqual(self.lab._verdict(spec, metrics, None), "research_survivor")

        production_spec = json.loads(json.dumps(spec))
        production_spec["parameters"]["sizing_mode"] = "fixed_risk_pct"
        self.assertEqual(self.lab._verdict(production_spec, metrics, None), "research_survivor")

        metrics["calmar_delta"] = 0.2
        self.assertEqual(self.lab._verdict(production_spec, metrics, None), "promotion_candidate")

    def test_optimize_single_lever_returns_best_candidate(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        result = self.lab.optimize_lever("ver_btc_intraday_parent", dataset["dataset_id"], "atr_len", {})
        self.assertEqual(result["mode"], "optimize_lever")
        self.assertEqual(result["lever"], "atr_len")
        self.assertTrue(result["candidates"])
        self.assertEqual(result["search"]["min"], 1)
        self.assertGreaterEqual(result["search"]["candidate_count"], 300)
        self.assertIn(result["selection_mode"], {"eligible_only", "no_production_eligible_keep_current"})
        if result["selection_mode"] == "eligible_only":
            self.assertIn("atr_len", result["best"]["parameter_overrides"])
        else:
            self.assertEqual(result["best"]["parameter_overrides"], {})
        self.assertIn("buy_hold_return_pct", result["best"]["metrics"])
        self.assertIn("eligible_count", result)
        self.assertIn("selection_mode", result)
        self.assertIn("score_components", result["best"])
        self.assertIn("best_spec", result)

    def test_optimizer_penalizes_low_trade_high_profit_factor_candidates(self) -> None:
        spec = {
            "evaluation": {
                "minimum_trades": 50,
                "minimum_profit_factor": 1.2,
                "maximum_drawdown_pct": 12.0,
                "minimum_net_pnl": 0.0,
                "maximum_initial_risk_pct": 1.0,
                "maximum_entry_exposure_pct": 100.0,
                "maximum_avg_exposure_pct": 100.0,
                "production_sizing_modes": ["fixed_risk_pct"],
            },
            "parameters": {
                "sizing_mode": "fixed_risk_pct",
            },
        }
        low_trade_high_pf = {
            "profit_factor": 6.9488,
            "return_pct": 110.81,
            "outperformance_pct": 0.0,
            "max_equity_drawdown_pct": 3.06,
            "percent_profitable": 62.5,
            "expected_payoff": 3462.9,
            "total_trades": 32,
            "net_pnl": 110812.81,
            "sharpe": 2.0,
            "sortino": 2.0,
            "daily_sharpe": 2.0,
            "daily_sortino": 2.0,
            "calmar": 1.0,
            "calmar_delta": 0.1,
            "max_initial_risk_pct": 1.0,
            "max_entry_exposure_pct": 100.0,
            "avg_entry_exposure_pct": 80.0,
            "worst_daily_return_pct": -2.0,
        }
        enough_trade_credible = {
            "profit_factor": 2.05,
            "return_pct": 65.0,
            "outperformance_pct": 0.0,
            "max_equity_drawdown_pct": 7.5,
            "percent_profitable": 48.0,
            "expected_payoff": 812.5,
            "total_trades": 80,
            "net_pnl": 65000.0,
            "sharpe": 1.0,
            "sortino": 1.0,
            "daily_sharpe": 1.0,
            "daily_sortino": 1.2,
            "calmar": 1.0,
            "calmar_delta": 0.1,
            "max_initial_risk_pct": 1.0,
            "max_entry_exposure_pct": 100.0,
            "avg_entry_exposure_pct": 80.0,
            "worst_daily_return_pct": -2.0,
        }
        self.assertFalse(self.lab._optimization_eligible(spec, low_trade_high_pf))
        self.assertTrue(self.lab._optimization_eligible(spec, enough_trade_credible))
        self.assertLess(
            self.lab._optimization_score(spec, low_trade_high_pf),
            self.lab._optimization_score(spec, enough_trade_credible),
        )

    def test_optimize_all_runs_sequential_passes(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        result = self.lab.optimize_all("ver_btc_intraday_parent", dataset["dataset_id"], {}, passes=2)
        self.assertEqual(result["mode"], "optimize_all")
        self.assertTrue(result["steps"])
        self.assertIn("preview", result)
        self.assertIn("parameter_overrides", result)
        self.assertEqual(result["preview"]["spec"]["parameters"]["sizing_mode"], "fixed_risk_pct")
        self.assertLessEqual(result["preview"]["spec"]["parameters"]["risk_pct"], 0.01)
        self.assertLessEqual(result["preview"]["spec"]["parameters"]["max_leverage"], 1.0)

    def test_robustness_check_returns_walk_forward_and_cost_stress(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(count=40000),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m-robustness",
        )
        result = self.lab.robustness_check(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"sizing_mode": "fixed_risk_pct", "risk_pct": 0.005, "max_leverage": 1.0},
        )
        self.assertEqual(result["mode"], "robustness_check")
        self.assertEqual(len(result["walk_forward"]), 4)
        self.assertEqual(len(result["cost_stress"]), 3)
        self.assertIn(result["summary"]["label"], {"production_robustness_candidate", "needs_review", "not_robust"})
        self.assertIn("daily_sharpe", result["walk_forward"][0]["metrics"])
        self.assertIn("commission_2x", {item["scenario"] for item in result["cost_stress"]})

    def test_promote_child_updates_current_version(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        proposal = self.lab.generate_proposals("ver_btc_intraday_parent")[0]
        run_payload = self.lab.run_proposal(proposal["proposal_id"], dataset["dataset_id"])
        detail = self.lab.promote_version("btc_intraday", run_payload["version_id"])
        self.assertEqual(detail["family"]["current_version_id"], run_payload["version_id"])

    def test_delete_non_current_child_version_cascades_runs(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        saved = self.lab.save_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        child_version_id = saved["version_id"]
        detail = self.lab.delete_version(child_version_id)
        self.assertEqual(detail["family"]["current_version_id"], "ver_btc_intraday_parent")
        self.assertIsNone(self.repo.get_version(child_version_id))
        child_runs = [run for run in self.repo.list_runs(family_id="btc_intraday") if run["version_id"] == child_version_id]
        self.assertEqual(child_runs, [])

    def test_binance_downloader_uses_explicit_start_time_for_history_window(self) -> None:
        urls: list[str] = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(url, timeout=30):
            del timeout
            urls.append(url)
            return FakeResponse(None)

        payload = [
            [
                1_700_000_000_000,
                "100.0",
                "101.0",
                "99.0",
                "100.5",
                "123.0",
                1_700_000_900_000,
                "0",
                "0",
                "0",
                "0",
                "0",
            ]
        ]
        with patch("app.data.urlopen", side_effect=fake_urlopen), patch("app.data.json.load", return_value=payload):
            bars, meta = self.data_service._download_klines("BTCUSDT", "15m", 40000, full_history=False)
        self.assertEqual(len(bars), 1)
        self.assertFalse(meta["history_truncated"])
        self.assertTrue(urls)
        self.assertIn("startTime=", urls[0])

    def test_binance_full_history_timeout_is_wrapped_in_operator_friendly_http_error(self) -> None:
        with patch("app.data.urlopen", side_effect=socket.timeout("timed out")), patch("app.data.time.sleep"):
            with self.assertRaises(HTTPException) as ctx:
                self.data_service.download_binance_dataset("BTCUSDT", "15m", 40000, True, None)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("full-history download timed out", ctx.exception.detail)

    def test_full_history_dataset_marks_download_mode_and_truncation_flag(self) -> None:
        payload = []
        for index in range(600):
            open_time = 1_700_000_000_000 + (index * 900_000)
            payload.append(
                [
                    open_time,
                    "100.0",
                    "101.0",
                    "99.0",
                    "100.5",
                    "123.0",
                    open_time + 900_000,
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                ]
            )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("app.data.urlopen", return_value=FakeResponse()), patch("app.data.json.load", return_value=payload):
            dataset = self.data_service.download_binance_dataset("BTCUSDT", "15m", 40000, True, None)
        self.assertEqual(dataset["download_mode"], "full_history")
        self.assertFalse(dataset["history_truncated"])
        self.assertIsNotNone(dataset["history_cap_bars"])

    def test_full_history_request_accepts_zero_bars_for_ui_sentinel_mode(self) -> None:
        request = DatasetDownloadRequest(symbol="BTCUSDT", timeframe="15m", bars=0, full_history=True)
        self.assertEqual(request.bars, 0)
        self.assertTrue(request.full_history)

    def test_hybrid_entry_quality_experiment_exports_trade_features(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        run_payload = self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        result = self.lab.run_hybrid_entry_quality_experiment(run_payload["run_id"], veto_fraction=0.15)
        self.assertEqual(result["mode"], "offline_entry_quality_veto")
        self.assertIn(result["verdict"], {"hybrid_candidate", "research_survivor", "rejected_no_edge", "rejected_drawdown", "rejected_low_activity", "rejected_no_veto"})
        self.assertTrue(Path(result["export_path"]).exists())
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertTrue(result["rows"])
        self.assertIn("bad_entry_quality_score", result["rows"][0])
        self.assertIn("entry_ts", result["rows"][0])
        self.assertIn("mfe_r", result["rows"][0])

    def test_hybrid_time_decay_triage_experiment_exports_snapshots(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        run_payload = self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        result = self.lab.run_hybrid_time_decay_triage_experiment(run_payload["run_id"], exit_fraction=0.15)
        self.assertEqual(result["mode"], "offline_time_decay_path_triage")
        self.assertIn(result["verdict"], {"hybrid_candidate", "research_survivor", "rejected_no_edge", "rejected_drawdown", "rejected_low_activity", "rejected_no_veto"})
        self.assertTrue(Path(result["export_path"]).exists())
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertTrue(result["rows"])
        self.assertIn("bad_time_decay_path_score", result["rows"][0])
        self.assertIn("checkpoint_bars", result["rows"][0])
        self.assertIn("unrealized_r", result["rows"][0])


if __name__ == "__main__":
    unittest.main()
