from __future__ import annotations

import math
import json
import socket
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi import HTTPException

from app.backtest import BacktestEngine, Position
from app.config import settings
from app.backtest import BacktestEngine, Position
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


def build_mt5_proxy_bars() -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    raw = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 100.5, 98.5, 99.0),
        (99.0, 99.5, 97.5, 98.0),
        (98.0, 105.0, 97.5, 104.0),
        (104.0, 105.0, 90.0, 92.0),
        (92.0, 93.0, 89.0, 90.0),
        (90.0, 91.0, 88.0, 89.0),
    ]
    return [
        Bar(
            ts=start + timedelta(minutes=15 * index),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
            symbol="BTCUSDT",
            timeframe="15m",
        )
        for index, (open_price, high, low, close) in enumerate(raw)
    ]


def build_ma_proxy_spec(**overrides: object) -> dict[str, object]:
    parameters = {
        "ma_kind": "sma",
        "fast_len": 2,
        "slow_len": 3,
        "noise_lookback": 1,
        "max_no_cross": 2,
        "entry_mode": "crossover_only",
        "allow_long": True,
        "allow_short": False,
        "atr_len": 1,
        "stop_mult": 1.0,
        "sizing_mode": "fixed_quantity",
        "quantity": 1.0,
        "initial_capital": 100000.0,
        "commission_pct": 0.0,
        "slippage_ticks": 0,
        "tick_size": 0.01,
        "risk_pct": 0.005,
        "notional_pct": 0.25,
        "max_leverage": 1.0,
        "execution_model": "next_bar_open",
    }
    parameters.update(overrides)
    return {
        "engine_id": "ma_cross_atr_stop_v1",
        "asset": "BTCUSDT",
        "venue": "Binance Spot",
        "timeframe": "15m",
        "metadata": {"family_id": "ma_proxy_fixture", "title": "MA Proxy Fixture"},
        "parameters": parameters,
        "evaluation": {"minimum_trades": 1, "minimum_profit_factor": 1.0, "maximum_drawdown_pct": 100.0, "minimum_net_pnl": -999999},
        "mutation_space": [],
    }


def build_asm_bars(same_bar_ambiguous: bool = False) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    raw = [
        (100, 102, 99, 100),
        (100, 103, 98, 101),
        (101, 104, 90, 95),
        (95, 105, 96, 102),
        (102, 106, 97, 103),
        (103, 110, 100, 108),
        (108, 106, 101, 104),
        (104, 105, 102, 103),
        (103, 112, 104, 111),
        (111, 108, 100, 105),
        (105, 106, 102, 104),
        (104, 107, 103, 105),
        (105, 106, 102, 104),
        (104, 113, 104, 108),
    ]
    if same_bar_ambiguous:
        raw[9] = (111, 113, 89, 105)
    return [
        Bar(
            ts=start + timedelta(minutes=15 * index),
            open=float(open_price),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=1000.0,
            symbol="BTCUSDT",
            timeframe="15m",
        )
        for index, (open_price, high, low, close) in enumerate(raw)
    ]


def build_asm_bearish_bars() -> list[Bar]:
    mirrored: list[Bar] = []
    for bar in build_asm_bars():
        mirrored.append(
            Bar(
                ts=bar.ts,
                open=200 - bar.open,
                high=200 - bar.low,
                low=200 - bar.high,
                close=200 - bar.close,
                volume=bar.volume,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
            )
        )
    return mirrored


def build_resample_bars(count: int = 18, timeframe: str = "15m") -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    for index in range(count):
        price = 100 + index
        bars.append(
            Bar(
                ts=start + timedelta(minutes=15 * index),
                open=float(price),
                high=float(price + 2),
                low=float(price - 2),
                close=float(price + 1),
                volume=100.0 + index,
                symbol="BTCUSDT",
                timeframe=timeframe,
            )
        )
    return bars


def build_bos_demand_bars() -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    raw = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 105.0, 99.0, 104.0),
        (104.0, 110.0, 103.0, 109.0),
        (108.0, 109.0, 104.0, 105.0),
        (105.0, 106.0, 102.0, 103.0),
        (103.0, 106.0, 100.0, 101.0),
        (104.0, 112.0, 103.0, 109.0),
        (105.0, 107.1, 104.9, 107.0),
        (107.0, 119.0, 106.0, 109.0),
    ]
    while len(raw) < 24:
        index = len(raw)
        base = 106.0 + ((index % 3) - 1)
        raw.append((base, base + 2.0, base - 2.0, base + 0.5))
    return [
        Bar(
            ts=start + timedelta(minutes=15 * index),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
            symbol="BTCUSDT",
            timeframe="15m",
        )
        for index, (open_price, high, low, close) in enumerate(raw)
    ]


def build_asm_spec(**overrides: object) -> dict[str, object]:
    parameters = {
        "allow_long": True,
        "allow_short": True,
        "external_pivot_period": 2,
        "internal_pivot_period": 1,
        "structure_stream": "external_only",
        "active_timeframe_profile": "intraday_15m",
        "use_timeframe_profile_overrides": False,
        "execution_timeframe": "15m",
        "context_timeframe": "1h",
        "higher_context_timeframe": "4h",
        "resample_context_from_execution_bars": False,
        "context_bias_required": False,
        "context_bias_event": "bos_or_choch",
        "context_bias_max_age_bars": 96,
        "context_bias_must_align_with_external_bias": True,
        "timeframe_profiles": {
            "intraday_15m": {"execution_timeframe": "15m", "fib_entry_retracement": 0.67},
            "swing_4h": {"execution_timeframe": "4h", "fib_entry_retracement": 0.71},
        },
        "internal_confirmation_required": False,
        "internal_confirmation_event": "bos_or_choch",
        "internal_confirmation_max_age_bars": 24,
        "internal_must_align_with_external_bias": True,
        "max_setup_age_bars": 20,
        "range_min_atr": 0.0,
        "range_max_atr": 100.0,
        "displacement_atr_len": 3,
        "min_displacement_atr": 0.0,
        "fib_entry_retracement": 0.5,
        "fib_stop_retracement": 1.0,
        "fib_target_retracement": 0.0,
        "stop_buffer_atr_mult": 0.0,
        "require_discount_for_longs": True,
        "require_premium_for_shorts": True,
        "premium_discount_midpoint": 0.5,
        "fvg_enabled": True,
        "fvg_min_gap_atr": 0.0,
        "fvg_max_age_bars": 20,
        "fvg_overlap_required": False,
        "fvg_overlap_tolerance_atr": 0.1,
        "fvg_mitigation_rule": "touch_through_far_edge",
        "liquidity_sweep_required": False,
        "sweep_lookback_bars": 3,
        "sweep_window_bars": 10,
        "sweep_close_back_inside": True,
        "same_bar_exit_policy": "stop_first",
        "time_stop_enabled": False,
        "time_stop_bars": 20,
        "time_stop_min_mfe_r": 0.25,
        "time_risk_filter_enabled": False,
        "time_risk_block_weekdays": [],
        "time_risk_block_utc_hours": [],
        "sizing_mode": "fixed_quantity",
        "quantity": 1.0,
        "initial_capital": 100000.0,
        "commission_pct": 0.0,
        "slippage_ticks": 0,
        "tick_size": 0.01,
        "risk_pct": 0.005,
        "notional_pct": 0.25,
        "max_leverage": 1.0,
        "execution_model": "research_same_close",
    }
    parameters.update(overrides)
    return {
        "engine_id": "asm_fib_liquidity_fvg_v1",
        "asset": "BTCUSDT",
        "venue": "Binance Spot",
        "timeframe": "15m",
        "metadata": {"family_id": "asm_fixture", "title": "ASM Fixture"},
        "parameters": parameters,
        "evaluation": {"minimum_trades": 1, "minimum_profit_factor": 1.0, "maximum_drawdown_pct": 100.0, "minimum_net_pnl": -999999},
        "mutation_space": [
            {
                "kind": "white_box",
                "lever": "fib_entry_retracement",
                "path": "parameters.fib_entry_retracement",
                "priority": 100,
                "values": [0.5, 0.67],
                "search_mode": "range",
                "search_min": 0.4,
                "search_max": 0.8,
                "search_step": 0.1,
                "rationale": "Tune fib entry.",
            }
        ],
    }


def build_bos_demand_spec(**overrides: object) -> dict[str, object]:
    parameters = {
        "variant": "v0_exact_pine",
        "allow_long": True,
        "allow_short": False,
        "pivot_len": 2,
        "atr_len": 3,
        "atr_mult": 0.0,
        "min_green": 1,
        "max_zone_age": 8,
        "demand_lookback_bars": 10,
        "tp_r": 1.5,
        "bos_break_mode": "wick",
        "ema_filter_enabled": True,
        "ema_len": 3,
        "same_bar_exit_policy": "stop_first",
        "sizing_mode": "fixed_quantity",
        "quantity": 1.0,
        "initial_capital": 100000.0,
        "commission_pct": 0.0,
        "slippage_ticks": 0,
        "tick_size": 0.01,
        "risk_pct": 0.005,
        "notional_pct": 0.25,
        "max_leverage": 1.0,
        "execution_model": "next_bar_open",
    }
    parameters.update(overrides)
    return {
        "engine_id": "bos_demand_pullback_v1",
        "asset": "BTCUSDT",
        "venue": "Binance Spot",
        "timeframe": "15m",
        "metadata": {"family_id": "bos_fixture", "title": "BOS Demand Fixture"},
        "parameters": parameters,
        "evaluation": {"minimum_trades": 1, "minimum_profit_factor": 1.0, "maximum_drawdown_pct": 100.0, "minimum_net_pnl": -999999},
        "mutation_space": [],
    }


def build_quant_smc_bars(count: int = 160) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    price = 100.0
    for index in range(count):
        drift = 1.2 if (index // 20) % 2 == 0 else -1.1
        open_price = price
        close = max(1.0, open_price + drift)
        high = max(open_price, close) + (2.5 if index % 13 == 0 else 0.8)
        low = min(open_price, close) - (2.5 if index % 17 == 0 else 0.8)
        volume = 2000.0 if index % 11 == 0 else 1000.0
        bars.append(
            Bar(
                ts=start + timedelta(minutes=15 * index),
                open=open_price,
                high=high,
                low=max(0.01, low),
                close=close,
                volume=volume,
                symbol="BTCUSDT",
                timeframe="15m",
            )
        )
        price = close
    return bars


def build_quant_smc_spec(**overrides: object) -> dict[str, object]:
    spec = json.loads(Path("strategies/quant_smc_parent.json").read_text(encoding="utf-8"))
    spec["parameters"].update(overrides)
    return spec


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
            "strategy_specs_dir": settings.strategy_specs_dir,
            "seed_spec_path": settings.seed_spec_path,
        }
        settings.db_path = self.root / "artifacts" / "mutation_lab.sqlite3"
        settings.data_dir = self.root / "artifacts" / "data"
        settings.run_dir = self.root / "artifacts" / "runs"
        settings.report_dir = self.root / "artifacts" / "reports"
        settings.diagnostic_dir = self.root / "artifacts" / "diagnostics"
        settings.strategy_specs_dir = self.root / "strategies"
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
        settings.strategy_specs_dir = self.original["strategy_specs_dir"]
        settings.seed_spec_path = self.original["seed_spec_path"]
        self.temp_dir.cleanup()

    def test_seed_family_and_version_exist(self) -> None:
        family = self.repo.get_family("btc_intraday")
        self.assertIsNotNone(family)
        self.assertEqual(family["current_version_id"], "ver_btc_intraday_parent")
        version = self.repo.get_version("ver_btc_intraday_parent")
        self.assertIsNotNone(version)
        self.assertTrue(settings.seed_spec_path.exists())

    def test_additional_parent_json_specs_are_registered(self) -> None:
        spec = {
            "engine_id": "custom_engine_v1",
            "asset": "BTCUSDT",
            "venue": "Binance Spot",
            "timeframe": "15m",
            "metadata": {
                "family_id": "custom_family",
                "title": "Custom Family",
                "causal_story": "Imported custom strategy.",
            },
            "parameters": {"allow_long": True},
            "evaluation": {},
            "mutation_space": [
                {
                    "kind": "white_box",
                    "lever": "allow_long",
                    "path": "parameters.allow_long",
                    "values": [True, False],
                    "search_mode": "values_only",
                    "rationale": "Toggle long side.",
                }
            ],
        }
        (settings.strategy_specs_dir / "custom_family_parent.json").write_text(json.dumps(spec), encoding="utf-8")
        self.lab.ensure_seeded()
        family = self.repo.get_family("custom_family")
        self.assertIsNotNone(family)
        self.assertEqual(family["current_version_id"], "ver_custom_family_parent")
        version = self.repo.get_version("ver_custom_family_parent")
        self.assertIsNotNone(version)
        self.assertEqual(version["spec_json"]["engine_id"], "custom_engine_v1")

    def test_intraday_parent_exposes_surviving_phase_three_and_phase_four_controls(self) -> None:
        spec = json.loads(Path("strategies/intraday_trend_atr_parent.json").read_text(encoding="utf-8"))
        (settings.strategy_specs_dir / "intraday_trend_atr_parent.json").write_text(json.dumps(spec), encoding="utf-8")
        self.lab.ensure_seeded()
        family = self.repo.get_family("intraday_trend_atr")
        self.assertIsNotNone(family)
        self.assertEqual(family["current_version_id"], "ver_intraday_trend_atr_parent")
        version = self.repo.get_version("ver_intraday_trend_atr_parent")
        self.assertEqual(version["spec_json"]["parameters"]["execution_model"], "mt5_bar_proxy")
        self.assertTrue(version["spec_json"]["parameters"]["time_decay_exit_enabled"])
        self.assertEqual(version["spec_json"]["parameters"]["time_decay_bars"], 30)
        self.assertEqual(version["spec_json"]["parameters"]["time_decay_min_mfe_r"], 0.25)
        self.assertTrue(version["spec_json"]["parameters"]["short_time_risk_filter_enabled"])
        self.assertEqual(version["spec_json"]["parameters"]["short_time_risk_block_utc_hours"], [6, 9, 16, 20])
        self.assertEqual(version["spec_json"]["parameters"]["short_time_risk_block_weekdays"], [4])
        self.assertTrue(version["spec_json"]["parameters"]["reverse_confirmation_enabled"])
        self.assertEqual(version["spec_json"]["parameters"]["reverse_confirm_max_bars"], 2)
        self.assertEqual(version["spec_json"]["parameters"]["reverse_confirm_min_mfe_r"], 0.2)
        self.assertEqual(version["spec_json"]["parameters"]["reverse_confirm_allow_if_unrealized_r_lte"], -0.35)
        self.assertTrue(version["spec_json"]["parameters"]["entry_blackbox_veto_enabled"])
        self.assertEqual(version["spec_json"]["parameters"]["entry_blackbox_veto_utc_hours"], [15])
        self.assertEqual(version["spec_json"]["parameters"]["entry_blackbox_veto_side_months"], ["long:8"])
        edges = self.lab.list_tuning_edges("ver_intraday_trend_atr_parent")
        edge_levers = {edge["lever"] for edge in edges}
        self.assertIn("fast_len", edge_levers)
        self.assertIn("time_decay_exit_enabled", edge_levers)
        self.assertIn("time_decay_bars", edge_levers)
        self.assertIn("time_decay_min_mfe_r", edge_levers)
        self.assertIn("short_time_risk_filter_enabled", edge_levers)
        self.assertIn("short_time_risk_block_utc_hours", edge_levers)
        self.assertIn("short_time_risk_block_weekdays", edge_levers)
        self.assertIn("reverse_confirmation_enabled", edge_levers)
        self.assertIn("reverse_confirm_max_bars", edge_levers)
        self.assertIn("reverse_confirm_min_mfe_r", edge_levers)
        self.assertIn("reverse_confirm_allow_if_unrealized_r_lte", edge_levers)
        self.assertIn("entry_blackbox_veto_enabled", edge_levers)
        self.assertIn("entry_blackbox_veto_utc_hours", edge_levers)
        self.assertIn("entry_blackbox_veto_side_months", edge_levers)
        self.assertNotIn("execution_model", edge_levers)
        self.assertNotIn("sizing_mode", edge_levers)
        self.assertNotIn("notional_pct", edge_levers)
        self.assertNotIn("hybrid_time_decay_triage_enabled", edge_levers)

    def test_child_versions_inherit_new_parent_schema_without_overwriting_tuned_values(self) -> None:
        spec = json.loads(Path("strategies/intraday_trend_atr_parent.json").read_text(encoding="utf-8"))
        legacy_child = json.loads(json.dumps(spec))
        legacy_child["parameters"].pop("time_decay_exit_enabled", None)
        legacy_child["parameters"].pop("time_decay_bars", None)
        legacy_child["parameters"].pop("time_decay_min_mfe_r", None)
        legacy_child["parameters"].pop("short_time_risk_filter_enabled", None)
        legacy_child["parameters"].pop("short_time_risk_block_utc_hours", None)
        legacy_child["parameters"].pop("short_time_risk_block_weekdays", None)
        legacy_child["parameters"].pop("reverse_confirmation_enabled", None)
        legacy_child["parameters"].pop("reverse_confirm_max_bars", None)
        legacy_child["parameters"].pop("reverse_confirm_min_mfe_r", None)
        legacy_child["parameters"].pop("reverse_confirm_allow_if_unrealized_r_lte", None)
        legacy_child["parameters"].pop("reverse_confirm_require_no_breakeven_move", None)
        legacy_child["parameters"].pop("entry_blackbox_veto_enabled", None)
        legacy_child["parameters"].pop("entry_blackbox_veto_utc_hours", None)
        legacy_child["parameters"].pop("entry_blackbox_veto_side_months", None)
        legacy_child["parameters"]["fast_len"] = 123
        inherited_levers = {
            "time_decay_exit_enabled",
            "time_decay_bars",
            "time_decay_min_mfe_r",
            "short_time_risk_filter_enabled",
            "short_time_risk_block_utc_hours",
            "short_time_risk_block_weekdays",
            "reverse_confirmation_enabled",
            "reverse_confirm_max_bars",
            "reverse_confirm_min_mfe_r",
            "reverse_confirm_allow_if_unrealized_r_lte",
            "reverse_confirm_require_no_breakeven_move",
            "entry_blackbox_veto_enabled",
            "entry_blackbox_veto_utc_hours",
            "entry_blackbox_veto_side_months",
        }
        legacy_child["mutation_space"] = [
            edge
            for edge in legacy_child["mutation_space"]
            if edge.get("lever") not in inherited_levers
        ]
        (settings.strategy_specs_dir / "intraday_trend_atr_parent.json").write_text(json.dumps(spec), encoding="utf-8")
        self.repo.put_family(
            {
                "family_id": "intraday_trend_atr",
                "title": "Intraday Trend ATR Baseline",
                "asset": "BTCUSDT",
                "venue": "Binance Spot",
                "timeframe": "15m",
                "current_version_id": "ver_intraday_trend_atr_parent",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        self.repo.put_version(
            {
                "version_id": "ver_intraday_trend_atr_parent",
                "family_id": "intraday_trend_atr",
                "parent_version_id": None,
                "name": "Intraday Trend ATR Baseline",
                "stage": "white_box",
                "source_code": "{}",
                "spec_json": spec,
                "causal_story": "",
                "mutation_json": {},
                "notes": "",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        self.repo.put_version(
            {
                "version_id": "ver_intraday_child",
                "family_id": "intraday_trend_atr",
                "parent_version_id": "ver_intraday_trend_atr_parent",
                "name": "Tuned child",
                "stage": "white_box",
                "source_code": "{}",
                "spec_json": legacy_child,
                "causal_story": "",
                "mutation_json": {},
                "notes": "",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        self.lab.ensure_seeded()
        child = self.repo.get_version("ver_intraday_child")
        self.assertEqual(child["spec_json"]["parameters"]["fast_len"], 123)
        self.assertTrue(child["spec_json"]["parameters"]["time_decay_exit_enabled"])
        self.assertEqual(child["spec_json"]["parameters"]["time_decay_bars"], 30)
        self.assertEqual(child["spec_json"]["parameters"]["time_decay_min_mfe_r"], 0.25)
        self.assertTrue(child["spec_json"]["parameters"]["short_time_risk_filter_enabled"])
        self.assertEqual(child["spec_json"]["parameters"]["short_time_risk_block_utc_hours"], [6, 9, 16, 20])
        self.assertEqual(child["spec_json"]["parameters"]["short_time_risk_block_weekdays"], [4])
        self.assertTrue(child["spec_json"]["parameters"]["reverse_confirmation_enabled"])
        self.assertEqual(child["spec_json"]["parameters"]["reverse_confirm_max_bars"], 2)
        self.assertEqual(child["spec_json"]["parameters"]["reverse_confirm_min_mfe_r"], 0.2)
        self.assertEqual(child["spec_json"]["parameters"]["reverse_confirm_allow_if_unrealized_r_lte"], -0.35)
        self.assertTrue(child["spec_json"]["parameters"]["entry_blackbox_veto_enabled"])
        self.assertEqual(child["spec_json"]["parameters"]["entry_blackbox_veto_utc_hours"], [15])
        self.assertEqual(child["spec_json"]["parameters"]["entry_blackbox_veto_side_months"], ["long:8"])
        child_edges = {edge["lever"] for edge in child["spec_json"]["mutation_space"]}
        self.assertIn("time_decay_exit_enabled", child_edges)
        self.assertIn("time_decay_bars", child_edges)
        self.assertIn("time_decay_min_mfe_r", child_edges)
        self.assertIn("short_time_risk_filter_enabled", child_edges)
        self.assertIn("short_time_risk_block_utc_hours", child_edges)
        self.assertIn("short_time_risk_block_weekdays", child_edges)
        self.assertIn("reverse_confirmation_enabled", child_edges)
        self.assertIn("reverse_confirm_max_bars", child_edges)
        self.assertIn("reverse_confirm_min_mfe_r", child_edges)
        self.assertIn("reverse_confirm_allow_if_unrealized_r_lte", child_edges)
        self.assertIn("entry_blackbox_veto_enabled", child_edges)
        self.assertIn("entry_blackbox_veto_utc_hours", child_edges)
        self.assertIn("entry_blackbox_veto_side_months", child_edges)

    def test_asm_engine_id_is_accepted_and_unknown_engine_still_fails(self) -> None:
        result = self.lab.engine.run(build_asm_spec(), build_asm_bars())
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["diagnostics"]["entries"], 1)
        with self.assertRaises(HTTPException) as ctx:
            self.lab.engine.run({"engine_id": "not_real", "parameters": {}}, build_asm_bars())
        self.assertEqual(ctx.exception.status_code, 400)

    def test_quant_smc_engine_runs_saved_open_source_parent(self) -> None:
        result = self.lab.engine.run(
            build_quant_smc_spec(
                require_sweep=False,
                require_fvg_overlap=False,
                require_pd_zone=False,
                ob_volume_required=False,
                min_ob_score=0,
                execution_model="research_same_close",
                sizing_mode="fixed_quantity",
                quantity=1.0,
                commission_pct=0.0,
                slippage_ticks=0,
            ),
            build_quant_smc_bars(),
        )
        self.assertIn("metrics", result)
        self.assertIn("major_pivots", result["diagnostics"])
        self.assertIn("bull_major_breaks", result["diagnostics"])
        self.assertIn("bear_major_breaks", result["diagnostics"])

    def test_quant_smc_asm_transformation_hooks_are_runnable(self) -> None:
        result = self.lab.engine.run(
            build_quant_smc_spec(
                entry_price_source="asm_external_fib",
                entry_timing_mode="after_retracement_sweep_internal",
                pd_method="external_range_midpoint",
                context_bias_required=True,
                resample_context_from_execution_bars=True,
                execution_timeframe="15m",
                context_timeframe="1h",
                internal_confirmation_required=True,
                target_mode="opposing_external_range",
                require_fvg_overlap=False,
                require_pd_zone=False,
                ob_volume_required=False,
                min_ob_score=0,
                execution_model="research_same_close",
                sizing_mode="fixed_quantity",
                quantity=1.0,
                commission_pct=0.0,
                slippage_ticks=0,
            ),
            build_quant_smc_bars(240),
        )
        self.assertIn("metrics", result)
        self.assertGreater(result["diagnostics"]["context_bars_built"], 0)
        self.assertIn("blocked_no_internal_confirmation", result["diagnostics"])
        self.assertIn("entries_after_internal_confirmation", result["diagnostics"])

    def test_asm_confirmed_pivots_wait_for_right_side_bars(self) -> None:
        bars = build_asm_bars()
        self.assertIsNone(self.lab.engine._confirmed_pivot(bars, 3, 2))
        pivot = self.lab.engine._confirmed_pivot(bars, 4, 2)
        self.assertIsNotNone(pivot)
        self.assertEqual(pivot.kind, "low")
        self.assertEqual(pivot.index, 2)

    def test_asm_fvg_detection_matches_three_candle_definition(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=UTC)
        bars = [
            Bar(ts=start, open=99, high=100, low=98, close=99, volume=1000, symbol="BTCUSDT", timeframe="15m"),
            Bar(ts=start + timedelta(minutes=15), open=100, high=102, low=99, close=101, volume=1000, symbol="BTCUSDT", timeframe="15m"),
            Bar(ts=start + timedelta(minutes=30), open=106, high=110, low=105, close=109, volume=1000, symbol="BTCUSDT", timeframe="15m"),
        ]
        atr_values = [10.0 for _ in bars]
        active = []
        self.lab.engine._register_asm_fvg({"fvg_enabled": True, "fvg_min_gap_atr": 0.0}, bars, atr_values, active, 2)
        self.assertTrue(active)
        self.assertEqual(active[0].direction, 1)
        self.assertEqual(active[0].bottom, bars[0].high)
        self.assertEqual(active[0].top, bars[2].low)

    def test_asm_liquidity_sweep_proxy_marks_long_and_short(self) -> None:
        bars = build_asm_bars()
        setup = self.lab.engine._build_asm_setup(
            parameters=build_asm_spec()["parameters"],
            bars=bars,
            atr_value=10,
            active_fvgs=[],
            direction=1,
            index=8,
            origin=self.lab.engine._confirmed_pivot(bars, 4, 2),
            broken=self.lab.engine._confirmed_pivot(bars, 7, 2),
        )
        self.assertIsNotNone(setup)
        self.lab.engine._update_asm_setup_sweep(
            {"sweep_lookback_bars": 3, "sweep_close_back_inside": True}, bars, setup, 9
        )
        self.assertEqual(setup.sweep_index, 9)

        short_bars = [
            Bar(ts=bars[0].ts + timedelta(minutes=15 * i), open=100, high=high, low=low, close=close, volume=1000, symbol="BTCUSDT", timeframe="15m")
            for i, (high, low, close) in enumerate([(110, 100, 105), (108, 99, 104), (107, 98, 103), (111, 101, 106), (109, 100, 102)])
        ]
        short_setup = build_asm_spec()["parameters"]
        del short_setup
        setup_short = type(setup)(
            direction=-1,
            created_index=1,
            setup_type="BOS",
            origin_index=0,
            origin_price=110,
            extreme_index=1,
            extreme_price=98,
            range_size=12,
            range_atr_multiple=1,
            entry_price=105,
            stop_price=110,
            target_price=98,
            discount_premium_passed=True,
        )
        self.lab.engine._update_asm_setup_sweep(
            {"sweep_lookback_bars": 3, "sweep_close_back_inside": True}, short_bars, setup_short, 3
        )
        self.assertEqual(setup_short.sweep_index, 3)

    def test_asm_known_bullish_fixture_enters_and_targets(self) -> None:
        result = self.lab.engine.run(build_asm_spec(), build_asm_bars())
        self.assertEqual(result["diagnostics"]["entries"], 1)
        self.assertEqual(result["diagnostics"]["target_exits"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["direction"], "long")
        self.assertEqual(trade["reason"], "target")
        self.assertEqual(trade["entry_price"], 101.0)
        self.assertEqual(trade["stop_price"], 90.0)
        self.assertEqual(trade["exit_price"], 112.0)
        self.assertIn("range_atr_multiple", trade["entry_features"])
        self.assertIn("discount_premium_passed", trade["entry_features"])

    def test_asm_same_bar_stop_target_ambiguity_uses_stop_first(self) -> None:
        result = self.lab.engine.run(build_asm_spec(), build_asm_bars(same_bar_ambiguous=True))
        self.assertEqual(result["diagnostics"]["entries"], 1)
        self.assertEqual(result["diagnostics"]["same_bar_stop_first_exits"], 1)
        self.assertEqual(result["trades"][0]["reason"], "stop")

    def test_asm_intraday_stream_blocks_old_external_only_entry_path(self) -> None:
        spec = build_asm_spec(
            structure_stream="external_and_internal_intraday",
            liquidity_sweep_required=True,
            internal_confirmation_required=True,
        )
        result = self.lab.engine.run(spec, build_asm_bars()[:10])
        self.assertEqual(result["diagnostics"]["entries"], 0)
        self.assertGreater(result["diagnostics"]["blocked_no_internal_confirmation"], 0)

    def test_asm_intraday_bullish_internal_confirmation_allows_entry(self) -> None:
        spec = build_asm_spec(
            structure_stream="external_and_internal_intraday",
            liquidity_sweep_required=True,
            internal_confirmation_required=True,
        )
        result = self.lab.engine.run(spec, build_asm_bars())
        self.assertEqual(result["diagnostics"]["entries_after_internal_confirmation"], 1)
        self.assertEqual(result["diagnostics"]["internal_confirmations_bullish"], 1)
        features = result["trades"][0]["entry_features"]
        self.assertEqual(features["external_bias"], "bullish")
        self.assertEqual(features["internal_confirmation_type"], "bullish_bos")
        self.assertIn("external_range_origin", features)
        self.assertIn("internal_confirmation_age_bars", features)

    def test_asm_intraday_bearish_internal_confirmation_allows_entry(self) -> None:
        spec = build_asm_spec(
            structure_stream="external_and_internal_intraday",
            liquidity_sweep_required=True,
            internal_confirmation_required=True,
        )
        result = self.lab.engine.run(spec, build_asm_bearish_bars())
        self.assertEqual(result["diagnostics"]["entries_after_internal_confirmation"], 1)
        self.assertEqual(result["diagnostics"]["internal_confirmations_bearish"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["direction"], "short")
        self.assertEqual(trade["entry_features"]["external_bias"], "bearish")
        self.assertEqual(trade["entry_features"]["internal_confirmation_type"], "bearish_bos")

    def test_asm_intraday_confirmation_before_retracement_or_sweep_does_not_count(self) -> None:
        bars = build_asm_bars()
        spec = build_asm_spec(
            structure_stream="external_and_internal_intraday",
            liquidity_sweep_required=True,
            internal_confirmation_required=True,
        )
        result = self.lab.engine.run(spec, bars[:10])
        self.assertEqual(result["diagnostics"]["entries"], 0)
        self.assertEqual(result["diagnostics"]["internal_confirmations_bullish"], 0)

    def test_asm_intraday_old_internal_confirmation_is_rejected(self) -> None:
        bars = build_asm_bars()
        setup = self.lab.engine._build_asm_setup(
            parameters=build_asm_spec()["parameters"],
            bars=bars,
            atr_value=10,
            active_fvgs=[],
            direction=1,
            index=8,
            origin=self.lab.engine._confirmed_pivot(bars, 4, 2),
            broken=self.lab.engine._confirmed_pivot(bars, 7, 2),
        )
        self.assertIsNotNone(setup)
        setup.retracement_index = 9
        setup.sweep_index = 9
        setup.internal_confirmation_index = 5
        setup.internal_confirmation_type = "bullish_bos"
        reason = self.lab.engine._asm_setup_block_reason(
            build_asm_spec(
                structure_stream="external_and_internal_intraday",
                internal_confirmation_required=True,
                internal_confirmation_max_age_bars=1,
                liquidity_sweep_required=True,
            )["parameters"],
            bars,
            setup,
            [],
            10,
        )
        self.assertEqual(reason, "blocked_no_internal_confirmation")

    def test_asm_intraday_registered_parent_exposes_internal_mutation_edges(self) -> None:
        asm_spec = json.loads(Path("strategies/asm_fib_liquidity_parent.json").read_text(encoding="utf-8"))
        (settings.strategy_specs_dir / "asm_fib_liquidity_parent.json").write_text(json.dumps(asm_spec), encoding="utf-8")
        self.lab.ensure_seeded()
        edges = self.lab.list_tuning_edges("ver_asm_fib_liquidity_parent")
        levers = {edge["lever"] for edge in edges}
        self.assertIn("internal_confirmation_required", levers)
        self.assertIn("internal_confirmation_event", levers)
        self.assertIn("internal_confirmation_max_age_bars", levers)
        self.assertIn("internal_pivot_period", levers)

    def test_asm_timeframe_profile_overrides_base_parameters(self) -> None:
        parameters = build_asm_spec(
            use_timeframe_profile_overrides=True,
            active_timeframe_profile="intraday_15m",
            fib_entry_retracement=0.5,
            timeframe_profiles={
                "intraday_15m": {"execution_timeframe": "15m", "fib_entry_retracement": 0.67},
                "swing_4h": {"execution_timeframe": "4h", "fib_entry_retracement": 0.71},
            },
        )["parameters"]
        resolved, applied = self.lab.engine._resolve_asm_parameters(parameters)
        self.assertTrue(applied)
        self.assertEqual(resolved["fib_entry_retracement"], 0.67)

        swing_params = dict(parameters)
        swing_params["active_timeframe_profile"] = "swing_4h"
        resolved_swing, _ = self.lab.engine._resolve_asm_parameters(swing_params)
        self.assertEqual(resolved_swing["fib_entry_retracement"], 0.71)

    def test_asm_dataset_timeframe_mismatch_raises_clear_error(self) -> None:
        spec = build_asm_spec(execution_timeframe="5m")
        with self.assertRaises(HTTPException) as ctx:
            self.lab.engine.run(spec, build_asm_bars())
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("does not match ASM execution timeframe", ctx.exception.detail)

    def test_asm_resamples_completed_15m_bars_to_1h_and_4h_without_leakage(self) -> None:
        bars = build_resample_bars(count=18)
        one_hour = self.lab.engine._resample_bars(bars, "15m", "1h")
        four_hour = self.lab.engine._resample_bars(bars, "15m", "4h")
        self.assertEqual(len(one_hour), 4)
        self.assertEqual(one_hour[0].open, bars[0].open)
        self.assertEqual(one_hour[0].close, bars[3].close)
        self.assertEqual(one_hour[-1].close, bars[15].close)
        self.assertEqual(len(four_hour), 1)
        self.assertEqual(four_hour[0].close, bars[15].close)

    def test_asm_context_bias_series_is_precomputed_per_completed_context_bar(self) -> None:
        bars = build_resample_bars(count=18)
        context = self.lab.engine._resample_bars(bars, "15m", "1h")
        parameters = build_asm_spec(
            context_bias_required=True,
            resample_context_from_execution_bars=True,
            context_timeframe="1h",
            external_pivot_period=1,
        )["parameters"]
        series = self.lab.engine._context_bias_series(parameters, bars, context)
        self.assertEqual(len(series), len(bars))
        self.assertEqual(series[0]["bias"], None)
        self.assertEqual(series[3], series[4])
        self.assertNotEqual(id(series[3]), id(series[4]))

    def test_asm_missing_context_bias_blocks_required_context(self) -> None:
        spec = build_asm_spec(
            context_bias_required=True,
            resample_context_from_execution_bars=True,
            context_timeframe="1h",
            external_pivot_period=2,
        )
        result = self.lab.engine.run(spec, build_asm_bars())
        self.assertEqual(result["diagnostics"]["entries"], 0)
        self.assertGreater(result["diagnostics"]["blocked_no_context_bias"], 0)
        self.assertEqual(result["diagnostics"]["context_bars_built"], 3)

    def test_asm_context_bias_mismatch_blocks_execution_bias(self) -> None:
        setup = self.lab.engine._build_asm_setup(
            parameters=build_asm_spec()["parameters"],
            bars=build_asm_bars(),
            atr_value=10,
            active_fvgs=[],
            direction=1,
            index=8,
            origin=self.lab.engine._confirmed_pivot(build_asm_bars(), 4, 2),
            broken=self.lab.engine._confirmed_pivot(build_asm_bars(), 7, 2),
            context_bias={"bias": "bearish", "event": "bearish_bos", "bar_index": 1, "bar_ts": build_asm_bars()[1].ts, "age": 0},
        )
        self.assertIsNotNone(setup)
        setup.retracement_index = 9
        reason = self.lab.engine._asm_setup_block_reason(
            build_asm_spec(context_bias_required=True, context_bias_must_align_with_external_bias=True)["parameters"],
            build_asm_bars(),
            setup,
            [],
            9,
        )
        self.assertEqual(reason, "blocked_context_bias_mismatch")

    def test_asm_trade_features_include_profile_and_context_fields(self) -> None:
        spec = build_asm_spec(
            active_timeframe_profile="intraday_15m",
            context_bias_required=False,
            higher_context_timeframe="4h",
        )
        result = self.lab.engine.run(spec, build_asm_bars())
        features = result["trades"][0]["entry_features"]
        self.assertEqual(features["active_timeframe_profile"], "intraday_15m")
        self.assertEqual(features["execution_timeframe"], "15m")
        self.assertEqual(features["context_timeframe"], "1h")
        self.assertEqual(features["higher_context_timeframe"], "4h")
        self.assertIn("context_bias", features)
        self.assertIn("fib_entry_retracement_resolved", features)

    def test_asm_registered_family_runs_and_exports_artifacts(self) -> None:
        asm_spec = build_asm_spec()
        asm_spec["metadata"] = {
            "family_id": "asm_fib_liquidity",
            "title": "ASM Fibonacci Liquidity",
            "causal_story": "Fixture registered ASM parent.",
        }
        (settings.strategy_specs_dir / "asm_fib_liquidity_parent.json").write_text(json.dumps(asm_spec), encoding="utf-8")
        self.lab.ensure_seeded()
        edges = self.lab.list_tuning_edges("ver_asm_fib_liquidity_parent")
        self.assertTrue(any(edge["lever"] == "fib_entry_retracement" for edge in edges))
        dataset = self.data_service.import_fixture_dataset(
            build_asm_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="asm-fixture",
        )
        payload = self.lab.run_version("ver_asm_fib_liquidity_parent", dataset["dataset_id"])
        self.assertGreaterEqual(payload["metrics"]["total_trades"], 1)
        self.assertTrue(Path(payload["artifact_path"]).exists())
        self.assertTrue(Path(payload["report_path"]).exists())
        self.assertIn("blocked_no_fvg", payload["diagnostics"])

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

    def test_mt5_production_execution_fills_after_signal_and_marks_open_equity(self) -> None:
        bars = build_fixture_bars()
        version = self.repo.get_version("ver_btc_intraday_parent")
        result = self.lab.engine.run(version["spec_json"], bars)
        self.assertEqual(result["diagnostics"]["execution_model"], "mt5_bar_proxy")
        self.assertGreater(result["diagnostics"]["pending_entry_orders"], 0)
        self.assertGreater(result["diagnostics"]["pending_order_fills"], 0)
        self.assertGreater(result["metrics"]["total_trades"], 0)
        first_trade = result["trades"][0]
        self.assertNotEqual(first_trade["entry_features"]["signal_ts"], first_trade["entry_features"]["fill_ts"])
        self.assertTrue(
            any(
                point["mark_to_market_equity"] != point["realized_equity"]
                for point in result["equity_curve"]
            )
        )

    def test_research_same_close_execution_remains_explicit_diagnostic_mode(self) -> None:
        bars = build_fixture_bars()
        spec = json.loads(json.dumps(self.repo.get_version("ver_btc_intraday_parent")["spec_json"]))
        spec["parameters"]["execution_model"] = "research_same_close"
        result = self.lab.engine.run(spec, bars)
        self.assertEqual(result["diagnostics"]["execution_model"], "research_same_close")
        self.assertGreater(result["metrics"]["total_trades"], 0)
        first_trade = result["trades"][0]
        self.assertEqual(first_trade["entry_features"]["signal_ts"], first_trade["entry_features"]["fill_ts"])

    def test_mt5_bar_proxy_allows_stop_after_next_open_fill_inside_entry_bar(self) -> None:
        bars = build_mt5_proxy_bars()
        next_open = BacktestEngine().run(build_ma_proxy_spec(execution_model="next_bar_open"), bars)
        mt5_proxy = BacktestEngine().run(build_ma_proxy_spec(execution_model="mt5_bar_proxy"), bars)
        self.assertEqual(next_open["diagnostics"]["pending_order_fills"], 1)
        self.assertEqual(next_open["diagnostics"]["stop_exits"], 1)
        self.assertEqual(mt5_proxy["diagnostics"]["pending_order_fills"], 1)
        self.assertEqual(mt5_proxy["diagnostics"]["stop_exits"], 1)
        self.assertEqual(mt5_proxy["trades"][0]["reason"], "stop")
        self.assertEqual(mt5_proxy["trades"][0]["bars_held"], 0)
        self.assertEqual(mt5_proxy["trades"][0]["entry_features"]["execution_model"], "mt5_bar_proxy")

    def test_mt5_bar_proxy_rejects_invalid_breakeven_stop_modification(self) -> None:
        bars = build_mt5_proxy_bars()
        bars[4] = Bar(
            ts=bars[4].ts,
            open=104.0,
            high=110.0,
            low=100.0,
            close=105.0,
            volume=bars[4].volume,
            symbol=bars[4].symbol,
            timeframe=bars[4].timeframe,
        )
        result = BacktestEngine().run(
            build_ma_proxy_spec(
                execution_model="mt5_bar_proxy",
                breakeven_stop_enabled=True,
                breakeven_trigger_mfe_r=0.0,
                breakeven_lock_r=0.5,
            ),
            bars,
        )
        self.assertGreaterEqual(result["diagnostics"]["mt5_stop_modify_rejects"], 1)

    def test_ghl_dc_engine_runs(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        spec = {
            "engine_id": "ghl_dc_breakout_v1",
            "parameters": {
                "gann_high_period": 5,
                "gann_low_period": 8,
                "donchian_length": 13,
                "max_breakout_bars": 10,
                "allow_long": True,
                "allow_short": True,
                "atr_len": 8,
                "stop_mode": "atr",
                "stop_mult": 2.0,
                "initial_capital": 100000.0,
                "commission_pct": 0.0,
                "slippage_ticks": 1,
                "tick_size": 0.01,
                "sizing_mode": "fixed_risk_pct",
                "risk_pct": 0.005,
                "max_leverage": 1.0,
                "execution_model": "mt5_bar_proxy",
            },
            "evaluation": {},
        }
        result = BacktestEngine().run(spec, bars)
        self.assertIn("metrics", result)
        self.assertIn("diagnostics", result)
        self.assertEqual(result["diagnostics"]["execution_model"], "mt5_bar_proxy")
        self.assertGreaterEqual(result["diagnostics"]["bars"], 1200)
        self.assertIn("breakeven_stop_moves", result["diagnostics"])
        self.assertTrue(result["trades"])
        features = result["trades"][0]["entry_features"]
        for key in (
            "atr_pct",
            "normalized_ma_distance",
            "recent_return_20",
            "recent_range_20",
            "recent_volatility_20",
            "recent_cross_count",
            "stop_distance_atr",
            "donchian_breakout_distance_atr",
            "breakout_age_bars",
            "bars_since_gann_flip",
        ):
            self.assertIn(key, features)

    def test_ghl_dc_mt5_pending_and_stop_fills_are_gap_and_spread_aware(self) -> None:
        bar = Bar(
            ts=datetime(2024, 1, 1, tzinfo=UTC),
            open=105.0,
            high=108.0,
            low=90.0,
            close=100.0,
            volume=1000.0,
            symbol="XAUUSD",
            timeframe="30m",
        )

        self.assertAlmostEqual(BacktestEngine._ghl_dc_pending_fill_price(1, bar, 100.0, 0.1, 0.05), 105.15)
        self.assertAlmostEqual(BacktestEngine._ghl_dc_pending_fill_price(-1, bar, 100.0, 0.1, 0.05), 99.9)
        self.assertAlmostEqual(BacktestEngine._ghl_dc_stop_fill_price(1, bar, 95.0, 0.1, 0.05), 94.9)
        self.assertAlmostEqual(BacktestEngine._ghl_dc_stop_fill_price(-1, bar, 102.0, 0.1, 0.05), 105.15)
        self.assertTrue(BacktestEngine._ghl_dc_pending_order_gapped_at_open(1, bar, 100.0, 0.05))
        gap_bar = Bar(
            ts=bar.ts,
            open=90.0,
            high=93.0,
            low=88.0,
            close=91.0,
            volume=bar.volume,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
        )
        self.assertTrue(BacktestEngine._ghl_dc_stop_gapped_at_open(1, gap_bar, 95.0, 0.05))
        self.assertAlmostEqual(BacktestEngine._ghl_dc_stop_fill_price(1, gap_bar, 95.0, 0.1, 0.05), 89.9)

    def test_ghl_dc_mt5_proxy_arms_before_fill_and_defers_stop_activation(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        spec = {
            "engine_id": "ghl_dc_breakout_v1",
            "parameters": {
                "gann_high_period": 5,
                "gann_low_period": 8,
                "donchian_length": 13,
                "max_breakout_bars": 10,
                "allow_long": True,
                "allow_short": True,
                "atr_len": 8,
                "stop_mode": "atr",
                "stop_mult": 2.0,
                "initial_capital": 100000.0,
                "commission_pct": 0.0,
                "slippage_ticks": 1,
                "spread_ticks": 5,
                "tick_size": 0.01,
                "sizing_mode": "fixed_risk_pct",
                "risk_pct": 0.005,
                "max_leverage": 1.0,
                "execution_model": "mt5_bar_proxy",
            },
            "evaluation": {},
        }

        result = BacktestEngine().run(spec, bars)

        self.assertTrue(result["trades"])
        self.assertEqual(result["diagnostics"]["execution_semantics"], "closed_bar_setup_pending_stop_next_bar_gap_aware_next_open_gann_exit")
        self.assertEqual(result["diagnostics"]["entries"], result["diagnostics"]["pending_order_fills"])
        self.assertEqual(result["diagnostics"]["gann_state_exits"], result["diagnostics"]["gann_exit_next_open_fills"])
        for trade in result["trades"]:
            features = trade["entry_features"]
            self.assertLess(features["setup_index"], features["fill_index"])
            self.assertEqual(features["stop_active_from_index"], features["fill_index"] + 1)
            self.assertEqual(features["spread_ticks"], 5)

    def test_mt5_fixed_risk_lot_sizing_rounds_to_broker_step(self) -> None:
        quantity = BacktestEngine._position_quantity(
            {
                "sizing_mode": "mt5_fixed_risk_lot",
                "risk_pct": 0.01,
                "max_leverage": 1.0,
                "contract_size": 100.0,
                "min_lot": 0.01,
                "lot_step": 0.01,
                "max_lot": 100.0,
                "skip_below_min_lot": True,
            },
            equity=5000.0,
            entry_price=2500.0,
            stop_price=2490.0,
        )
        self.assertEqual(quantity, 2.0)

    def test_ghl_dc_failed_entry_triage_exits_weak_young_trades(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        spec = {
            "engine_id": "ghl_dc_breakout_v1",
            "parameters": {
                "gann_high_period": 5,
                "gann_low_period": 8,
                "donchian_length": 13,
                "max_breakout_bars": 10,
                "allow_long": True,
                "allow_short": True,
                "atr_len": 8,
                "stop_mode": "atr",
                "stop_mult": 2.0,
                "initial_capital": 100000.0,
                "commission_pct": 0.0,
                "slippage_ticks": 1,
                "tick_size": 0.01,
                "sizing_mode": "fixed_risk_pct",
                "risk_pct": 0.005,
                "max_leverage": 1.0,
                "execution_model": "mt5_bar_proxy",
                "failed_entry_triage_enabled": True,
                "failed_entry_triage_bars": 1,
                "failed_entry_triage_min_mfe_r": 999.0,
                "failed_entry_triage_max_current_r": 999.0,
            },
            "evaluation": {},
        }

        result = BacktestEngine().run(spec, bars)

        self.assertGreater(result["diagnostics"]["failed_entry_triage_exits"], 0)
        self.assertEqual(
            result["diagnostics"]["failed_entry_triage_exits"],
            sum(1 for trade in result["trades"] if trade["reason"] == "failed_entry_triage_exit"),
        )

    def test_ghl_dc_gann_exit_confirmation_suppresses_first_candidate(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        base_parameters = {
            "gann_high_period": 5,
            "gann_low_period": 8,
            "donchian_length": 13,
            "max_breakout_bars": 10,
            "allow_long": True,
            "allow_short": True,
            "atr_len": 8,
            "stop_mode": "atr",
            "stop_mult": 10.0,
            "initial_capital": 100000.0,
            "commission_pct": 0.0,
            "slippage_ticks": 1,
            "tick_size": 0.01,
            "sizing_mode": "fixed_risk_pct",
            "risk_pct": 0.005,
            "max_leverage": 1.0,
            "execution_model": "mt5_bar_proxy",
        }
        baseline = BacktestEngine().run({"engine_id": "ghl_dc_breakout_v1", "parameters": base_parameters, "evaluation": {}}, bars)
        confirmed = BacktestEngine().run(
            {
                "engine_id": "ghl_dc_breakout_v1",
                "parameters": {
                    **base_parameters,
                    "gann_exit_confirmation_enabled": True,
                    "gann_exit_confirm_bars": 1,
                    "gann_exit_confirm_allow_if_unrealized_r_lte": -999.0,
                },
                "evaluation": {},
            },
            bars,
        )

        self.assertGreater(confirmed["diagnostics"]["gann_exit_confirmation_candidates"], 0)
        self.assertGreater(confirmed["diagnostics"]["gann_exit_confirmation_suppressed"], 0)
        self.assertLessEqual(confirmed["diagnostics"]["gann_state_exits"], baseline["diagnostics"]["gann_state_exits"])
        self.assertTrue(any(trade["gann_exit_confirmation_suppressed"] > 0 for trade in confirmed["trades"]))

    def test_ghl_dc_gann_exit_confirmation_allows_adverse_escape(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        result = BacktestEngine().run(
            {
                "engine_id": "ghl_dc_breakout_v1",
                "parameters": {
                    "gann_high_period": 5,
                    "gann_low_period": 8,
                    "donchian_length": 13,
                    "max_breakout_bars": 10,
                    "allow_long": True,
                    "allow_short": True,
                    "atr_len": 8,
                    "stop_mode": "atr",
                    "stop_mult": 10.0,
                    "initial_capital": 100000.0,
                    "commission_pct": 0.0,
                    "slippage_ticks": 1,
                    "tick_size": 0.01,
                    "sizing_mode": "fixed_risk_pct",
                    "risk_pct": 0.005,
                    "max_leverage": 1.0,
                    "execution_model": "mt5_bar_proxy",
                    "gann_exit_confirmation_enabled": True,
                    "gann_exit_confirm_bars": 3,
                    "gann_exit_confirm_allow_if_unrealized_r_lte": 999.0,
                },
                "evaluation": {},
            },
            bars,
        )

        self.assertGreater(result["diagnostics"]["gann_exit_confirmation_adverse_escapes"], 0)
        self.assertEqual(result["diagnostics"]["gann_exit_confirmation_suppressed"], 0)

    def test_ghl_dc_mt5_sizing_reports_invalid_lot_skips(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        spec = {
            "engine_id": "ghl_dc_breakout_v1",
            "parameters": {
                "gann_high_period": 5,
                "gann_low_period": 8,
                "donchian_length": 13,
                "max_breakout_bars": 10,
                "allow_long": True,
                "allow_short": False,
                "atr_len": 8,
                "stop_mode": "atr",
                "stop_mult": 2.0,
                "initial_capital": 5000.0,
                "commission_pct": 0.0,
                "slippage_ticks": 1,
                "tick_size": 0.01,
                "sizing_mode": "mt5_fixed_risk_lot",
                "risk_pct": 0.0001,
                "max_leverage": 1.0,
                "contract_size": 100.0,
                "min_lot": 100.0,
                "lot_step": 0.01,
                "max_lot": 100.0,
                "skip_below_min_lot": True,
                "execution_model": "mt5_bar_proxy",
            },
            "evaluation": {},
        }
        result = BacktestEngine().run(spec, bars)
        self.assertGreater(result["diagnostics"]["mt5_invalid_lot_skips"], 0)
        self.assertEqual(result["diagnostics"]["entries"], 0)

    def test_usdjpy_mt5_lot_sizing_and_quote_conversion_match_usd_account_economics(self) -> None:
        parameters = {
            "sizing_mode": "mt5_fixed_risk_lot",
            "risk_pct": 0.01,
            "max_leverage": 10.0,
            "contract_size": 100000.0,
            "min_lot": 0.01,
            "lot_step": 0.01,
            "max_lot": 100.0,
            "skip_below_min_lot": True,
            "account_conversion_mode": "quote_divide_price",
        }
        quantity = BacktestEngine._position_quantity(parameters, 5000.0, 150.0, 149.25)
        self.assertEqual(quantity, 10000.0)  # 0.10 standard lots

        bar = Bar(
            ts=datetime(2026, 1, 1, tzinfo=UTC),
            open=150.0,
            high=150.8,
            low=149.8,
            close=150.75,
            volume=1.0,
            symbol="USDJPY",
            timeframe="1h",
        )
        position = BacktestEngine._open_position(
            1,
            0,
            bar,
            150.0,
            149.25,
            quantity,
            0.0,
            5000.0,
            {},
            account_conversion_mode="quote_divide_price",
            contract_size=100000.0,
            commission_per_lot_side=3.5,
        )
        trade = BacktestEngine()._close_trade(position, bar, 1, 150.75, "test", 0.0, 5000.0)

        self.assertAlmostEqual(position.entry_commission, 0.35, places=6)
        self.assertAlmostEqual(trade["gross_pnl"], 49.75, places=2)
        self.assertAlmostEqual(trade["net_pnl"], 49.05, places=2)
        self.assertAlmostEqual(trade["initial_risk_amount"], 50.0, places=2)

    def test_time_decay_confirmation_suppresses_unconfirmed_exit(self) -> None:
        diagnostics = {
            "time_decay_confirmation_candidates": 0,
            "time_decay_confirmation_exits": 0,
            "time_decay_confirmation_suppressed": 0,
        }
        position = Position(
            direction=1,
            entry_index=10,
            entry_ts=datetime(2024, 1, 1, tzinfo=UTC),
            entry_price=100.0,
            stop_price=95.0,
            quantity=1.0,
            entry_commission=0.0,
            entry_equity=100000.0,
            entry_notional=100.0,
            initial_risk_per_unit=5.0,
            stop_initialized_on_index=10,
            entry_features={},
        )

        allowed = BacktestEngine._time_decay_confirmation_allows_exit(
            parameters={
                "time_decay_triage_confirmation_enabled": True,
                "time_decay_confirm_max_unrealized_r": 0.0,
                "time_decay_confirm_max_mfe_r": 0.35,
                "time_decay_confirm_require_no_breakeven_move": False,
            },
            position=position,
            unrealized_r=0.2,
            mfe_r=0.5,
            diagnostics=diagnostics,
        )

        self.assertFalse(allowed)
        self.assertEqual(diagnostics["time_decay_confirmation_candidates"], 1)
        self.assertEqual(diagnostics["time_decay_confirmation_exits"], 0)
        self.assertEqual(diagnostics["time_decay_confirmation_suppressed"], 1)
        self.assertEqual(position.time_decay_confirmation_suppressed, 1)

    def test_reverse_confirmation_suppresses_young_weak_opposite_signal(self) -> None:
        diagnostics = {
            "reverse_confirmation_candidates": 0,
            "reverse_confirmation_exits_allowed": 0,
            "reverse_confirmation_suppressed": 0,
            "reverse_confirmation_adverse_escape_allowed": 0,
        }
        position = Position(
            direction=1,
            entry_index=10,
            entry_ts=datetime(2024, 1, 1, tzinfo=UTC),
            entry_price=100.0,
            stop_price=90.0,
            quantity=1.0,
            entry_commission=0.0,
            entry_equity=100000.0,
            entry_notional=100.0,
            initial_risk_per_unit=10.0,
            stop_initialized_on_index=10,
            entry_features={},
            max_favorable_excursion=1.0,
        )

        allowed = BacktestEngine._reverse_confirmation_allows_exit(
            parameters={
                "reverse_confirmation_enabled": True,
                "reverse_confirm_max_bars": 2,
                "reverse_confirm_min_mfe_r": 0.20,
                "reverse_confirm_allow_if_unrealized_r_lte": -0.35,
                "reverse_confirm_require_no_breakeven_move": False,
            },
            position=position,
            index=12,
            current_close=99.0,
            long_signal=False,
            short_signal=True,
            diagnostics=diagnostics,
        )

        self.assertFalse(allowed)
        self.assertEqual(diagnostics["reverse_confirmation_candidates"], 1)
        self.assertEqual(diagnostics["reverse_confirmation_exits_allowed"], 0)
        self.assertEqual(diagnostics["reverse_confirmation_suppressed"], 1)
        self.assertEqual(position.reverse_confirmation_suppressed, 1)

    def test_reverse_confirmation_keeps_adverse_escape(self) -> None:
        diagnostics = {
            "reverse_confirmation_candidates": 0,
            "reverse_confirmation_exits_allowed": 0,
            "reverse_confirmation_suppressed": 0,
            "reverse_confirmation_adverse_escape_allowed": 0,
        }
        position = Position(
            direction=1,
            entry_index=10,
            entry_ts=datetime(2024, 1, 1, tzinfo=UTC),
            entry_price=100.0,
            stop_price=90.0,
            quantity=1.0,
            entry_commission=0.0,
            entry_equity=100000.0,
            entry_notional=100.0,
            initial_risk_per_unit=10.0,
            stop_initialized_on_index=10,
            entry_features={},
            max_favorable_excursion=1.0,
        )

        allowed = BacktestEngine._reverse_confirmation_allows_exit(
            parameters={
                "reverse_confirmation_enabled": True,
                "reverse_confirm_max_bars": 2,
                "reverse_confirm_min_mfe_r": 0.20,
                "reverse_confirm_allow_if_unrealized_r_lte": -0.35,
                "reverse_confirm_require_no_breakeven_move": False,
            },
            position=position,
            index=12,
            current_close=96.0,
            long_signal=False,
            short_signal=True,
            diagnostics=diagnostics,
        )

        self.assertTrue(allowed)
        self.assertEqual(diagnostics["reverse_confirmation_candidates"], 1)
        self.assertEqual(diagnostics["reverse_confirmation_exits_allowed"], 1)
        self.assertEqual(diagnostics["reverse_confirmation_adverse_escape_allowed"], 1)
        self.assertEqual(diagnostics["reverse_confirmation_suppressed"], 0)

    def test_entry_exposure_gate_blocks_over_limit_entry(self) -> None:
        diagnostics = {
            "entry_exposure_gate_blocks": 0,
            "entry_exposure_gate_long_blocks": 0,
            "entry_exposure_gate_short_blocks": 0,
        }

        allowed = BacktestEngine._entry_exposure_gate_allows_entry(
            parameters={
                "entry_exposure_gate_enabled": True,
                "entry_exposure_gate_max_pct": 75.0,
            },
            direction=1,
            equity=5000.0,
            entry_notional=4000.0,
            diagnostics=diagnostics,
        )

        self.assertFalse(allowed)
        self.assertEqual(diagnostics["entry_exposure_gate_blocks"], 1)
        self.assertEqual(diagnostics["entry_exposure_gate_long_blocks"], 1)
        self.assertEqual(diagnostics["entry_exposure_gate_short_blocks"], 0)

    def test_entry_exposure_gate_allows_under_limit_entry(self) -> None:
        diagnostics = {
            "entry_exposure_gate_blocks": 0,
            "entry_exposure_gate_long_blocks": 0,
            "entry_exposure_gate_short_blocks": 0,
        }

        allowed = BacktestEngine._entry_exposure_gate_allows_entry(
            parameters={
                "entry_exposure_gate_enabled": True,
                "entry_exposure_gate_max_pct": 75.0,
            },
            direction=-1,
            equity=5000.0,
            entry_notional=3500.0,
            diagnostics=diagnostics,
        )

        self.assertTrue(allowed)
        self.assertEqual(diagnostics["entry_exposure_gate_blocks"], 0)

    def test_entry_blackbox_veto_blocks_hour_and_side_month(self) -> None:
        diagnostics = {
            "entry_blackbox_veto_blocks": 0,
            "entry_blackbox_veto_long_blocks": 0,
            "entry_blackbox_veto_short_blocks": 0,
        }
        parameters = {
            "entry_blackbox_veto_enabled": True,
            "entry_blackbox_veto_utc_hours": [15],
            "entry_blackbox_veto_side_months": ["long:8"],
        }

        hour_allowed = BacktestEngine._entry_blackbox_veto_allows_entry(
            parameters=parameters,
            direction=-1,
            entry_ts=datetime(2024, 1, 1, 15, 0, tzinfo=UTC),
            diagnostics=diagnostics,
        )
        side_month_allowed = BacktestEngine._entry_blackbox_veto_allows_entry(
            parameters=parameters,
            direction=1,
            entry_ts=datetime(2024, 8, 1, 12, 0, tzinfo=UTC),
            diagnostics=diagnostics,
        )
        clean_allowed = BacktestEngine._entry_blackbox_veto_allows_entry(
            parameters=parameters,
            direction=1,
            entry_ts=datetime(2024, 9, 1, 12, 0, tzinfo=UTC),
            diagnostics=diagnostics,
        )

        self.assertFalse(hour_allowed)
        self.assertFalse(side_month_allowed)
        self.assertTrue(clean_allowed)
        self.assertEqual(diagnostics["entry_blackbox_veto_blocks"], 2)
        self.assertEqual(diagnostics["entry_blackbox_veto_long_blocks"], 1)
        self.assertEqual(diagnostics["entry_blackbox_veto_short_blocks"], 1)

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

    def test_breakeven_min_bars_blocks_immature_stop_moves(self) -> None:
        bars = build_fixture_bars(1200)
        for bar in bars:
            bar.symbol = "XAUUSD"
            bar.timeframe = "30m"
        spec = {
            "engine_id": "ghl_dc_breakout_v1",
            "parameters": {
                "gann_high_period": 5,
                "gann_low_period": 8,
                "donchian_length": 13,
                "max_breakout_bars": 10,
                "allow_long": True,
                "allow_short": True,
                "atr_len": 8,
                "stop_mode": "atr",
                "stop_mult": 2.0,
                "initial_capital": 100000.0,
                "commission_pct": 0.0,
                "slippage_ticks": 1,
                "tick_size": 0.01,
                "sizing_mode": "fixed_risk_pct",
                "risk_pct": 0.005,
                "max_leverage": 1.0,
                "execution_model": "mt5_bar_proxy",
                "breakeven_stop_enabled": True,
                "breakeven_trigger_mfe_r": 0.0,
                "breakeven_lock_r": 0.0,
                "breakeven_min_bars": 999,
            },
            "evaluation": {},
        }

        result = BacktestEngine().run(spec, bars)

        self.assertGreater(result["diagnostics"]["breakeven_maturity_blocks"], 0)
        self.assertEqual(result["diagnostics"]["breakeven_stop_moves"], 0)

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
        edge_levers = {edge["lever"] for edge in edges}
        self.assertIn("stop_mult", edge_levers)
        self.assertNotIn("execution_model", edge_levers)
        self.assertNotIn("sizing_mode", edge_levers)
        self.assertNotIn("notional_pct", edge_levers)
        with self.assertRaises(HTTPException):
            self.lab.optimize_lever("ver_btc_intraday_parent", dataset["dataset_id"], "initial_capital")
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
        hidden_levers = {edge["lever"] for edge in child_edges}
        self.assertNotIn("execution_model", hidden_levers)
        self.assertNotIn("sizing_mode", hidden_levers)
        self.assertNotIn("notional_pct", hidden_levers)

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
        legacy_spec["parameters"]["execution_model"] = "next_bar_open"
        legacy_spec["evaluation"]["production_sizing_modes"] = ["fixed_notional_pct", "fixed_risk_pct"]
        legacy_spec["evaluation"]["maximum_initial_risk_pct"] = 5
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
        self.assertEqual(upgraded["spec_json"]["parameters"]["execution_model"], "mt5_bar_proxy")
        self.assertEqual(upgraded["spec_json"]["parameters"]["sizing_mode"], "mt5_fixed_risk_lot")
        self.assertEqual(upgraded["spec_json"]["evaluation"]["production_sizing_modes"], ["mt5_fixed_risk_lot"])
        self.assertEqual(upgraded["spec_json"]["evaluation"]["maximum_initial_risk_pct"], 1.0)
        self.assertTrue(any(edge["lever"] == "breakeven_trigger_mfe_r" for edge in edges))
        self.assertTrue(any(edge["lever"] == "hybrid_reverse_exit_min_mfe_r" for edge in edges))
        self.assertTrue(any(edge["lever"] == "max_leverage" for edge in edges))
        weekday_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_weekdays")
        hour_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_utc_hours")
        self.assertIn([5, 6], weekday_edge["alternatives"])
        self.assertIn([23], hour_edge["alternatives"])
        self.assertGreaterEqual(len(hour_edge["alternatives"]), 30)

    def test_upgrade_preserves_broker_execution_constants(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        spec = json.loads(json.dumps(version["spec_json"]))
        spec["engine_id"] = "ghl_dc_breakout_v1"
        spec["parameters"].update(
            {
                "contract_size": 100000.0,
                "min_lot": 0.01,
                "lot_step": 0.01,
                "max_lot": 100.0,
                "skip_below_min_lot": True,
            }
        )
        self.repo.put_version(
            {
                **version,
                "version_id": "ver_usdjpy_execution_constants",
                "spec_json": spec,
            }
        )

        edges = self.lab.list_tuning_edges("ver_usdjpy_execution_constants")
        upgraded = self.repo.get_version("ver_usdjpy_execution_constants")["spec_json"]
        contract_edge = next(item for item in upgraded["mutation_space"] if item["lever"] == "contract_size")
        skip_edge = next(item for item in upgraded["mutation_space"] if item["lever"] == "skip_below_min_lot")

        self.assertEqual(contract_edge["values"], [100000.0])
        self.assertFalse(contract_edge["optimizable"])
        self.assertEqual(skip_edge["values"], [True])
        self.assertFalse(skip_edge["optimizable"])
        self.assertEqual(next(edge for edge in edges if edge["lever"] == "contract_size")["current_value"], 100000.0)

    def test_ghl_dc_upgrade_exposes_gann_exit_confirmation_controls(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        spec = json.loads(json.dumps(version["spec_json"]))
        spec["engine_id"] = "ghl_dc_breakout_v1"
        self.repo.put_version(
            {
                **version,
                "version_id": "ver_ghl_gann_confirmation_controls",
                "spec_json": spec,
            }
        )

        edges = self.lab.list_tuning_edges("ver_ghl_gann_confirmation_controls")
        by_lever = {edge["lever"]: edge for edge in edges}

        self.assertIn("gann_exit_confirmation_enabled", by_lever)
        self.assertIn("gann_exit_confirm_bars", by_lever)
        self.assertIn("gann_exit_confirm_allow_if_unrealized_r_lte", by_lever)
        self.assertEqual(by_lever["gann_exit_confirm_bars"]["alternatives"], [1, 2, 3, 4])

    def test_upgrade_preserves_asset_specific_time_risk_hour_candidates(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        spec = json.loads(json.dumps(version["spec_json"]))
        spec["engine_id"] = "ghl_dc_breakout_v1"
        spec["parameters"]["time_risk_block_utc_hours"] = [19, 20]
        self.repo.put_version(
            {
                **version,
                "version_id": "ver_ghl_asset_time_hours",
                "spec_json": spec,
            }
        )

        edges = self.lab.list_tuning_edges("ver_ghl_asset_time_hours")
        hour_edge = next(edge for edge in edges if edge["lever"] == "time_risk_block_utc_hours")

        self.assertIn([19], hour_edge["alternatives"])
        self.assertIn([20], hour_edge["alternatives"])
        self.assertIn([19, 20], hour_edge["alternatives"])

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
        self.assertIn("time_decay_triage_confirmation_enabled", edges)
        self.assertEqual(edges["time_decay_confirm_max_mfe_r"]["search_mode"], "range")
        self.assertIn("reverse_confirmation_enabled", edges)
        self.assertEqual(edges["reverse_confirm_min_mfe_r"]["search_mode"], "range")
        self.assertIn("entry_exposure_gate_enabled", edges)
        self.assertEqual(edges["entry_exposure_gate_max_pct"]["search_mode"], "range")
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["short_quality_gate_len_bars"])), 70)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["breakeven_trigger_mfe_r"])), 55)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["breakeven_lock_r"])), 21)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_reverse_exit_min_mfe_r"])), 60)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_time_decay_triage_max_unrealized_r"])), 30)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["hybrid_time_decay_triage_max_mfe_r"])), 20)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["entry_exposure_gate_max_pct"])), 19)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["reverse_confirm_max_bars"])), 12)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["reverse_confirm_min_mfe_r"])), 40)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["reverse_confirm_allow_if_unrealized_r_lte"])), 40)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["time_decay_confirm_max_unrealized_r"])), 60)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["time_decay_confirm_max_mfe_r"])), 40)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["risk_pct"])), 10)
        self.assertGreaterEqual(len(self.lab._candidate_values(edges["max_leverage"])), 4)

    def test_execution_and_sizing_modes_are_hidden_from_operator_levers(self) -> None:
        edges = {edge["lever"]: edge for edge in self.lab.list_tuning_edges("ver_btc_intraday_parent")}
        self.assertNotIn("execution_model", edges)
        self.assertNotIn("sizing_mode", edges)
        self.assertNotIn("notional_pct", edges)
        with self.assertRaises(HTTPException) as ctx:
            self.lab.optimize_lever("ver_btc_intraday_parent", "missing_dataset", "execution_model", {})
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", str(ctx.exception.detail))

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

    def test_capital_model_warnings_explain_mt5_lot_sizing(self) -> None:
        version = self.repo.get_version("ver_btc_intraday_parent")
        spec = json.loads(json.dumps(version["spec_json"]))
        spec["parameters"].update(
            {
                "sizing_mode": "mt5_fixed_risk_lot",
                "risk_pct": 0.005,
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
        self.assertIn("mt5_fixed_risk_lot", joined)
        self.assertIn("broker lot constraints", joined)
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
        production_spec["parameters"]["sizing_mode"] = "mt5_fixed_risk_lot"
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
        self.assertIn(
            result["selection_mode"],
            {"eligible_only", "research_score_fallback", "no_production_eligible_keep_current"},
        )
        if result["selection_mode"] == "eligible_only":
            self.assertIn("atr_len", result["best"]["parameter_overrides"])
        elif result["selection_mode"] == "no_production_eligible_keep_current":
            self.assertEqual(result["best"]["parameter_overrides"], {})
        else:
            self.assertIn("atr_len", result["best"]["parameter_overrides"])
        self.assertIn("buy_hold_return_pct", result["best"]["metrics"])
        self.assertIn("eligible_count", result)
        self.assertIn("selection_mode", result)
        self.assertIn("score_components", result["best"])
        self.assertIn("best_spec", result)

    def test_optimizer_skips_dataset_incompatible_timeframe_profiles(self) -> None:
        spec = build_asm_spec(use_timeframe_profile_overrides=True)
        spec["mutation_space"] = [
            {
                "kind": "white_box",
                "lever": "active_timeframe_profile",
                "path": "parameters.active_timeframe_profile",
                "priority": 100,
                "values": ["intraday_15m", "swing_4h"],
                "search_mode": "values_only",
                "rationale": "Run profile-specific baselines.",
            }
        ]
        detail = self.lab.register_baseline(
            family_id="asm_fixture",
            title="ASM Fixture",
            asset="BTCUSDT",
            venue="Binance Spot",
            timeframe="15m",
            version_name="ASM Fixture Parent",
            source_code="",
            spec_json=spec,
            causal_story="ASM fixture.",
            notes="",
        )
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        version_id = detail["family"]["current_version_id"]
        result = self.lab.optimize_lever(version_id, dataset["dataset_id"], "active_timeframe_profile", {})
        self.assertEqual(result["mode"], "optimize_lever")
        self.assertEqual(result["lever"], "active_timeframe_profile")
        self.assertTrue(result["candidates"])
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["skipped_candidates"][0]["value"], "swing_4h")
        self.assertIn("Dataset timeframe `15m`", result["skipped_candidates"][0]["reason"])

    def test_research_optimizer_can_move_when_no_production_candidate_is_eligible(self) -> None:
        spec = {
            "engine_id": "mock_engine_v1",
            "asset": "BTCUSDT",
            "venue": "Binance Spot",
            "timeframe": "15m",
            "metadata": {"family_id": "mock_optimizer", "title": "Mock Optimizer"},
            "parameters": {"alpha": 1, "sizing_mode": "fixed_risk_pct", "risk_pct": 0.005, "max_leverage": 1.0},
            "evaluation": {
                "minimum_trades": 50,
                "minimum_profit_factor": 10.0,
                "maximum_drawdown_pct": 1.0,
                "minimum_net_pnl": 0.0,
                "minimum_daily_sharpe": 5.0,
                "minimum_daily_sortino": 5.0,
                "production_sizing_modes": ["fixed_risk_pct"],
            },
            "mutation_space": [
                {
                    "kind": "white_box",
                    "lever": "alpha",
                    "path": "parameters.alpha",
                    "priority": 100,
                    "values": [1, 2],
                    "search_mode": "values_only",
                    "rationale": "Mock alpha.",
                }
            ],
        }
        detail = self.lab.register_baseline(
            family_id="mock_optimizer",
            title="Mock Optimizer",
            asset="BTCUSDT",
            venue="Binance Spot",
            timeframe="15m",
            version_name="Mock Optimizer Parent",
            source_code="",
            spec_json=spec,
            causal_story="Mock optimizer.",
            notes="",
        )
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )

        def fake_run(tuned_spec: dict, bars: list[Bar]) -> dict:
            alpha = tuned_spec["parameters"]["alpha"]
            return {
                "metrics": {
                    "profit_factor": 0.8 + alpha,
                    "return_pct": float(alpha),
                    "total_trades": 60,
                    "max_equity_drawdown_pct": 20.0,
                    "daily_sharpe": float(alpha) * 0.1,
                    "daily_sortino": float(alpha) * 0.1,
                    "worst_daily_return_pct": -2.0,
                    "calmar": float(alpha) * 0.1,
                    "outperformance_pct": float(alpha),
                    "max_initial_risk_pct": 0.5,
                    "max_entry_exposure_pct": 100.0,
                    "avg_entry_exposure_pct": 50.0,
                    "net_pnl": 100.0 * alpha,
                    "sharpe": float(alpha) * 0.1,
                    "sortino": float(alpha) * 0.1,
                    "percent_profitable": 40.0 + alpha,
                    "expected_payoff": 10.0 * alpha,
                    "calmar_delta": -1.0,
                },
                "diagnostics": {},
                "trades": [],
            }

        with patch.object(self.lab.engine, "run", side_effect=fake_run):
            version_id = detail["family"]["current_version_id"]
            production = self.lab.optimize_lever(version_id, dataset["dataset_id"], "alpha", {}, optimization_mode="production")
            research = self.lab.optimize_lever(version_id, dataset["dataset_id"], "alpha", {}, optimization_mode="research")
        self.assertEqual(production["selection_mode"], "no_production_eligible_keep_current")
        self.assertEqual(production["best"]["parameter_overrides"], {})
        self.assertEqual(research["selection_mode"], "research_best_score")
        self.assertEqual(research["best"]["parameter_overrides"]["alpha"], 2)

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

    def test_live_execution_gate_rejects_managed_stop_artifact(self) -> None:
        spec = {
            "engine_id": "ma_cross_atr_stop_v1",
            "parameters": {
                "breakeven_stop_enabled": True,
                "time_decay_exit_enabled": True,
                "sizing_mode": "mt5_fixed_risk_lot",
            },
            "evaluation": {
                "production_sizing_modes": ["mt5_fixed_risk_lot"],
                "benchmark_policy": "outperform_return_or_calmar",
            },
        }
        metrics = {
            "total_trades": 43747,
            "profit_factor": 2.9883,
            "max_equity_drawdown_pct": 2.55,
            "net_pnl": 1243550863.27,
            "sharpe": 42.0,
            "sortino": 98.0,
            "daily_sharpe": 12.0,
            "daily_sortino": 33.0,
            "calmar": 1000.0,
            "max_initial_risk_pct": 1.0,
            "max_entry_exposure_pct": 100.0,
            "avg_entry_exposure_pct": 31.0,
            "worst_daily_return_pct": -1.58,
            "outperformance_pct": 100.0,
            "calmar_delta": 100.0,
            "stop_exit_net_pnl": 1814299859.62,
            "stop_exit_profit_factor": 67.0953,
            "stop_exit_win_rate_pct": 98.1,
            "stop_exit_pnl_share_pct": 145.89,
            "reverse_exit_net_pnl": -570743749.76,
        }
        self.assertEqual(
            self.lab._live_execution_gate_failures(spec, metrics),
            [
                "requires_mt5_execution_model",
                "requires_mt5_parity_validation",
                "managed_stop_execution_dependency",
            ],
        )
        self.assertFalse(self.lab._optimization_eligible(spec, metrics))
        self.assertEqual(self.lab._verdict(spec, metrics, None), "research_survivor")

    def test_live_execution_gate_allows_managed_stops_after_mt5_parity_validation(self) -> None:
        spec = {
            "engine_id": "ma_cross_atr_stop_v1",
            "parameters": {
                "breakeven_stop_enabled": True,
                "time_decay_exit_enabled": False,
                "sizing_mode": "mt5_fixed_risk_lot",
                "execution_model": "mt5_bar_proxy",
            },
            "evaluation": {
                "mt5_parity_validated": True,
                "production_sizing_modes": ["mt5_fixed_risk_lot"],
            },
        }
        metrics = {
            "net_pnl": 10000.0,
            "stop_exit_net_pnl": 2500.0,
            "stop_exit_profit_factor": 2.0,
            "stop_exit_win_rate_pct": 55.0,
            "stop_exit_pnl_share_pct": 25.0,
            "reverse_exit_net_pnl": 7500.0,
        }
        self.assertEqual(self.lab._live_execution_gate_failures(spec, metrics), [])

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
        self.assertNotIn("execution_model", {step["lever"] for step in result["steps"]})
        self.assertEqual(result["preview"]["spec"]["parameters"]["sizing_mode"], "mt5_fixed_risk_lot")
        self.assertLessEqual(result["preview"]["spec"]["parameters"]["risk_pct"], 0.01)
        self.assertLessEqual(result["preview"]["spec"]["parameters"]["max_leverage"], 1.0)

    def test_robustness_repair_mode_scores_all_cost_scenarios(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m-robustness-repair",
        )

        result = self.lab.optimize_lever(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            "ma_kind",
            {},
            optimization_mode="robustness_repair",
        )

        self.assertEqual(result["optimization_mode"], "robustness_repair")
        self.assertTrue(result["candidates"])
        for candidate in result["candidates"]:
            evidence = candidate["robustness_evidence"]
            self.assertEqual(evidence["cost_stress_total"], 3)
            self.assertEqual(len(evidence["cost_stress"]), 3)
            self.assertIn("percent_profitable", evidence["cost_stress"][0]["metrics"])
            self.assertIn("walk_forward_passed", evidence)
            self.assertIn("walk_forward_total", evidence)

    def test_robustness_repair_full_gate_outranks_a_higher_screen_score(self) -> None:
        passed = {
            "screen_rank": [True, 7, 4, 3, 10.0, 10.0],
            "full_robustness": {
                "summary": {
                    "passed": True,
                    "walk_forward_passed": 4,
                    "anchored_train_test_passed": 3,
                    "cost_stress_passed": 3,
                }
            },
        }
        failed = {
            "screen_rank": [True, 7, 4, 3, 999.0, 999.0],
            "full_robustness": {
                "summary": {
                    "passed": False,
                    "walk_forward_passed": 4,
                    "anchored_train_test_passed": 2,
                    "cost_stress_passed": 3,
                }
            },
        }

        selected = max([failed, passed], key=self.lab._full_robustness_rank)

        self.assertIs(selected, passed)

    def test_cost_stress_reports_benchmark_weakness_without_failing_operational_survival(self) -> None:
        spec = self.repo.get_version("ver_btc_intraday_parent")["spec_json"]
        spec["parameters"]["sizing_mode"] = "mt5_fixed_risk_lot"
        metrics = {
            "net_pnl": 1000.0,
            "return_pct": 20.0,
            "profit_factor": 1.5,
            "total_trades": 500,
            "max_equity_drawdown_pct": 5.0,
            "sharpe": 1.5,
            "sortino": 1.5,
            "daily_sharpe": 1.5,
            "daily_sortino": 1.5,
            "worst_daily_return_pct": -1.0,
            "calmar": 4.0,
            "outperformance_pct": -10.0,
            "calmar_delta": -1.0,
            "max_initial_risk_pct": 0.5,
            "max_entry_exposure_pct": 90.0,
            "avg_entry_exposure_pct": 50.0,
            "percent_profitable": 50.0,
            "expected_payoff": 2.0,
        }
        with patch.object(self.lab.engine, "run", return_value={"metrics": metrics}):
            stresses = self.lab._cost_stress_runs(spec, build_fixture_bars())

        self.assertEqual(len(stresses), 3)
        self.assertTrue(all(item["passed"] for item in stresses))
        self.assertTrue(all(not item["benchmark_passed"] for item in stresses))
        self.assertTrue(
            all(item["benchmark_findings"] == ["weak_vs_buy_hold_benchmark"] for item in stresses)
        )

    def test_cost_stress_doubles_fixed_per_lot_commission(self) -> None:
        spec = self.repo.get_version("ver_btc_intraday_parent")["spec_json"]
        spec["parameters"]["commission_pct"] = 0.0
        spec["parameters"]["commission_per_lot_side"] = 3.5

        with patch.object(self.lab.engine, "run", return_value={"metrics": {
            "net_pnl": 1000.0,
            "return_pct": 20.0,
            "profit_factor": 1.5,
            "total_trades": 500,
            "max_equity_drawdown_pct": 5.0,
            "sharpe": 1.5,
            "sortino": 1.5,
            "daily_sharpe": 1.5,
            "daily_sortino": 1.5,
            "worst_daily_return_pct": -1.0,
            "calmar": 4.0,
            "outperformance_pct": 10.0,
            "calmar_delta": 1.0,
            "max_initial_risk_pct": 0.5,
            "max_entry_exposure_pct": 90.0,
            "avg_entry_exposure_pct": 50.0,
            "percent_profitable": 50.0,
            "expected_payoff": 2.0,
        }}):
            stresses = self.lab._cost_stress_runs(spec, build_fixture_bars())

        by_name = {item["scenario"]: item for item in stresses}
        self.assertEqual(by_name["commission_2x"]["commission_per_lot_side"], 7.0)
        self.assertEqual(by_name["slippage_2x"]["commission_per_lot_side"], 3.5)
        self.assertEqual(by_name["commission_2x_slippage_2x"]["commission_per_lot_side"], 7.0)

    def test_robustness_repair_mode_is_valid_and_execution_constants_are_not_optimized(self) -> None:
        self.assertEqual(self.lab._normalize_optimization_mode("robustness_repair"), "robustness_repair")
        version = self.repo.get_version("ver_btc_intraday_parent")
        version["spec_json"]["parameters"]["spread_ticks"] = 5
        version["spec_json"]["mutation_space"].append(
            {
                "kind": "execution",
                "lever": "spread_ticks",
                "path": "parameters.spread_ticks",
                "values": [5],
                "search_mode": "values_only",
                "optimizable": False,
                "rationale": "Fixed broker assumption.",
            }
        )
        self.repo.put_version(version)

        edges = self.lab.list_tuning_edges("ver_btc_intraday_parent")
        spread_edge = next(edge for edge in edges if edge["lever"] == "spread_ticks")
        self.assertFalse(spread_edge["optimizable"])

    def test_optimize_all_emits_parameter_progress(self) -> None:
        progress_events: list[dict[str, Any]] = []
        fake_edges = [
            {"lever": "fast_len", "current_value": 25, "optimizable": True},
            {"lever": "slow_len", "current_value": 96, "optimizable": True},
        ]

        def fake_optimize_lever(version_id: str, dataset_id: str, lever: str, overrides: dict, optimization_mode: str = "production", **kwargs: Any) -> dict:
            next_overrides = {**overrides, lever: 26 if lever == "fast_len" else 104}
            callback = kwargs.get("_progress_callback")
            context = kwargs.get("_progress_context") or {}
            if callback:
                callback(
                    {
                        "pass": context.get("pass_index", 1),
                        "passes": context.get("passes", 1),
                        "edge_index": context.get("lever_index", 1),
                        "total_edges": context.get("total_levers", 1),
                        "lever": lever,
                        "next_lever": None,
                    }
                )
            return {
                "best": {"parameter_overrides": next_overrides, "score": 1.0, "metrics": {}},
                "selection_mode": "research_score_fallback",
                "eligible_count": 1,
            }

        with (
            patch.object(self.lab, "list_tuning_edges", return_value=fake_edges),
            patch.object(self.lab, "optimize_lever", side_effect=fake_optimize_lever),
            patch.object(
                self.lab,
                "preview_tuned_version",
                return_value={
                    "mode": "preview",
                    "spec": {"parameters": {"sizing_mode": "mt5_fixed_risk_lot"}, "evaluation": {}},
                    "metrics": {
                        "total_trades": 100,
                        "net_pnl": 1000.0,
                        "profit_factor": 2.0,
                        "max_equity_drawdown_pct": 1.0,
                        "daily_sharpe": 2.0,
                        "daily_sortino": 2.0,
                        "calmar": 2.0,
                        "worst_daily_return_pct": -1.0,
                        "max_initial_risk_pct": 0.5,
                        "avg_entry_exposure_pct": 50.0,
                        "max_entry_exposure_pct": 75.0,
                        "outperformance_pct": 1.0,
                        "calmar_delta": 1.0,
                    },
                },
            ),
        ):
            self.lab.optimize_all(
                "ver_btc_intraday_parent",
                "fake_dataset",
                {},
                passes=1,
                optimization_mode="research",
                progress_callback=progress_events.append,
            )
        self.assertGreaterEqual(len(progress_events), 1)
        first = progress_events[0]
        self.assertEqual(first["pass"], 1)
        self.assertEqual(first["passes"], 1)
        self.assertEqual(first["edge_index"], 1)
        self.assertGreaterEqual(first["total_edges"], 1)
        self.assertIn("lever", first)
        self.assertIn("next_lever", first)

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
        self.assertEqual(len(result["anchored_train_test"]), 3)
        self.assertEqual(len(result["cost_stress"]), 3)
        self.assertIn(result["summary"]["label"], {"production_robustness_candidate", "needs_review", "not_robust"})
        self.assertIn("daily_sharpe", result["walk_forward"][0]["metrics"])
        self.assertIn("anchored_train_test_total", result["summary"])
        self.assertIn("commission_2x", {item["scenario"] for item in result["cost_stress"]})

    def test_execution_feasibility_audit_flags_diagnostic_sizing(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m-execution-audit",
        )
        run = self.lab.save_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"sizing_mode": "fixed_quantity", "quantity": 1.0},
        )
        audit = self.lab.execution_feasibility_audit(run["run_id"])
        self.assertEqual(audit["mode"], "execution_feasibility_audit")
        self.assertFalse(audit["passed"])
        self.assertIn("diagnostic_fixed_quantity_sizing", audit["failures"])
        self.assertIn("order_samples", audit)

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

    def test_logistic_entry_quality_model_separates_bad_setups_and_scales_risk(self) -> None:
        rows = []
        for index in range(80):
            bad = index >= 40
            rows.append(
                {
                    "bad_entry_quality": bad,
                    "side": "short" if bad else "long",
                    "weekday": index % 5,
                    "utc_hour": index % 24,
                    "month": (index % 12) + 1,
                    "gann_state": -1 if bad else 1,
                    "gap_fill": bad,
                    "gann_high_slope": -1.0 if bad else 1.0,
                    "gann_low_slope": -1.0 if bad else 1.0,
                    "normalized_ma_distance": -0.01 if bad else 0.01,
                    "bars_since_gann_flip": 20 if bad else 2,
                    "breakout_age_bars": 10 if bad else 1,
                    "donchian_channel_width_pct": 0.01,
                    "donchian_breakout_distance_atr": -1.0 if bad else 1.0,
                    "atr_pct": 0.01,
                    "recent_return_20": -0.02 if bad else 0.02,
                    "recent_range_20": 0.03,
                    "recent_volatility_20": 0.01,
                    "recent_cross_count": 8 if bad else 1,
                    "stop_distance_atr": 2.5,
                    "stop_distance_pct": 0.01,
                }
            )
        model = self.lab._fit_logistic_entry_quality(rows)
        good_score = self.lab._logistic_entry_quality_score(rows[0], model)
        bad_score = self.lab._logistic_entry_quality_score(rows[-1], model)
        self.assertLess(good_score, bad_score)
        scaled = self.lab._scale_trade(
            {"quantity": 1.0, "net_pnl": -20.0, "return_on_equity_pct": -0.4, "bars_held": 3},
            0.5,
        )
        self.assertEqual(scaled["quantity"], 0.5)
        self.assertEqual(scaled["net_pnl"], -10.0)
        self.assertEqual(scaled["bars_held"], 3)

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

    def test_bos_demand_exact_pine_wick_bos_enters_from_confirmed_pivot(self) -> None:
        result = BacktestEngine().run(build_bos_demand_spec(), build_bos_demand_bars())
        self.assertEqual(result["diagnostics"]["wick_bos_events"], 1)
        self.assertEqual(result["diagnostics"]["close_bos_events"], 0)
        self.assertEqual(result["diagnostics"]["signals_long"], 1)
        self.assertEqual(result["metrics"]["total_trades"], 1)
        self.assertEqual(result["trades"][0]["reason"], "target")
        self.assertEqual(result["trades"][0]["entry_features"]["variant"], "v0_exact_pine")

    def test_bos_demand_close_bos_variant_rejects_wick_only_break(self) -> None:
        result = BacktestEngine().run(
            build_bos_demand_spec(variant="v0_integrity_close_bos"),
            build_bos_demand_bars(),
        )
        self.assertEqual(result["diagnostics"]["wick_bos_events"], 0)
        self.assertEqual(result["diagnostics"]["close_bos_events"], 0)
        self.assertEqual(result["diagnostics"]["signals_long"], 0)
        self.assertEqual(result["metrics"]["total_trades"], 0)

    def test_bos_demand_no_ema_variant_forces_filter_off(self) -> None:
        result = BacktestEngine().run(
            build_bos_demand_spec(variant="v0_no_ema_diagnostic"),
            build_bos_demand_bars(),
        )
        self.assertEqual(result["diagnostics"]["ema_filter_enabled"], 0)
        self.assertEqual(result["trades"][0]["entry_features"]["ema_filter_enabled"], False)


if __name__ == "__main__":
    unittest.main()
