from __future__ import annotations

import json
import uuid
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.backtest import BacktestEngine, apply_patch_to_spec, buy_hold_drawdown_pct
from app.config import settings
from app.data import DataService
from app.storage import Repository


LENGTH_OPTIMIZATION_MAX = 300
MAX_NO_CROSS_OPTIMIZATION_MAX = 50
FLOAT_OPTIMIZATION_MAX_CANDIDATES = 200

PHASE_3_PARAMETERS = {
    "time_decay_exit_enabled": False,
    "time_decay_bars": 96,
    "time_decay_min_mfe_r": 0.5,
    "short_quality_gate_enabled": False,
    "short_quality_gate_rule": "block_below_sma",
    "short_quality_gate_len_bars": 19200,
    "breakeven_stop_enabled": False,
    "breakeven_trigger_mfe_r": 1.0,
    "breakeven_lock_r": 0.0,
    "time_risk_filter_enabled": False,
    "time_risk_block_weekdays": [],
    "time_risk_block_utc_hours": [],
}

PHASE_3_MUTATION_SPACE = [
    {
        "kind": "white_box",
        "lever": "time_decay_exit_enabled",
        "path": "parameters.time_decay_exit_enabled",
        "priority": 88,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable failed-entry time-decay exits as a full-whitebox rule mutation.",
    },
    {
        "kind": "white_box",
        "lever": "time_decay_bars",
        "path": "parameters.time_decay_bars",
        "priority": 87,
        "values": [48, 96, 144, 192],
        "search_mode": "range",
        "search_min": 1,
        "search_max": 300,
        "search_step": 1,
        "rationale": "Tune how long a trade may fail to prove favorable excursion before it is exited.",
    },
    {
        "kind": "white_box",
        "lever": "time_decay_min_mfe_r",
        "path": "parameters.time_decay_min_mfe_r",
        "priority": 86,
        "values": [0.25, 0.5, 0.75, 1.0],
        "search_mode": "range",
        "search_min": 0.05,
        "search_max": 2.0,
        "search_step": 0.05,
        "rationale": "Tune the minimum favorable excursion required before the time-decay window expires.",
    },
    {
        "kind": "white_box",
        "lever": "short_quality_gate_enabled",
        "path": "parameters.short_quality_gate_enabled",
        "priority": 78,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable the short-side context gate without touching the long-side entry logic.",
    },
    {
        "kind": "white_box",
        "lever": "short_quality_gate_rule",
        "path": "parameters.short_quality_gate_rule",
        "priority": 77,
        "values": ["block_below_sma", "block_above_sma"],
        "search_mode": "values_only",
        "rationale": "Choose whether shorts are blocked below or above the long-context trend SMA.",
    },
    {
        "kind": "white_box",
        "lever": "short_quality_gate_len_bars",
        "path": "parameters.short_quality_gate_len_bars",
        "priority": 76,
        "values": [9600, 19200, 28800],
        "search_mode": "range",
        "search_min": 4800,
        "search_max": 38400,
        "search_step": 480,
        "rationale": "Tune the short-side context horizon using 100/200/300-day equivalents on 15m BTC bars.",
    },
    {
        "kind": "white_box",
        "lever": "breakeven_stop_enabled",
        "path": "parameters.breakeven_stop_enabled",
        "priority": 58,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable breakeven stop management after favorable movement.",
    },
    {
        "kind": "white_box",
        "lever": "breakeven_trigger_mfe_r",
        "path": "parameters.breakeven_trigger_mfe_r",
        "priority": 57,
        "values": [0.75, 1.0, 1.5, 2.0],
        "search_mode": "range",
        "search_min": 0.25,
        "search_max": 3.0,
        "search_step": 0.05,
        "rationale": "Tune the favorable-excursion threshold that moves the stop toward breakeven.",
    },
    {
        "kind": "white_box",
        "lever": "breakeven_lock_r",
        "path": "parameters.breakeven_lock_r",
        "priority": 56,
        "values": [0.0, 0.25],
        "search_mode": "range",
        "search_min": 0.0,
        "search_max": 1.0,
        "search_step": 0.05,
        "rationale": "Choose whether the breakeven move locks only entry or a small favorable R amount.",
    },
    {
        "kind": "white_box",
        "lever": "time_risk_filter_enabled",
        "path": "parameters.time_risk_filter_enabled",
        "priority": 92,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable the entry-time risk filter found in full-whitebox diagnostics.",
    },
    {
        "kind": "white_box",
        "lever": "time_risk_block_weekdays",
        "path": "parameters.time_risk_block_weekdays",
        "priority": 91,
        "values": [[], [0], [1], [2], [3], [4], [5], [6], [5, 6], [0, 6], [0, 1, 2, 3, 4]],
        "search_mode": "values_only",
        "rationale": "Tune weekday entry exclusion; Python weekdays are Monday=0 through Sunday=6.",
    },
    {
        "kind": "white_box",
        "lever": "time_risk_block_utc_hours",
        "path": "parameters.time_risk_block_utc_hours",
        "priority": 90,
        "values": [
            [],
            [0],
            [1],
            [2],
            [3],
            [4],
            [5],
            [6],
            [7],
            [8],
            [9],
            [10],
            [11],
            [12],
            [13],
            [14],
            [15],
            [16],
            [17],
            [18],
            [19],
            [20],
            [21],
            [22],
            [23],
            [13, 15],
            [13, 21],
            [15, 21],
            [13, 15, 21],
            [12, 13, 14],
            [14, 15, 16],
            [20, 21, 22],
        ],
        "search_mode": "values_only",
        "rationale": "Tune UTC entry-hour exclusions using every single hour plus diagnostic combinations around weak pockets.",
    },
]

PHASE_4_PARAMETERS = {
    "hybrid_time_decay_triage_enabled": False,
    "hybrid_time_decay_triage_checkpoints": [10, 20, 30],
    "hybrid_time_decay_triage_max_unrealized_r": 0.10,
    "hybrid_time_decay_triage_max_mfe_r": 0.25,
    "hybrid_reverse_exit_triage_enabled": True,
    "hybrid_reverse_exit_min_mfe_r": 0.10,
}

PHASE_4_MUTATION_SPACE = [
    {
        "kind": "hybrid",
        "lever": "hybrid_time_decay_triage_enabled",
        "path": "parameters.hybrid_time_decay_triage_enabled",
        "priority": 98,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable the phase-4 in-trade score triage that exits low-quality time-decay paths early.",
    },
    {
        "kind": "hybrid",
        "lever": "hybrid_time_decay_triage_checkpoints",
        "path": "parameters.hybrid_time_decay_triage_checkpoints",
        "priority": 97,
        "values": [[10], [20], [30], [10, 20], [20, 30], [10, 20, 30]],
        "search_mode": "values_only",
        "rationale": "Choose the bars-held checkpoints where the hybrid time-decay path rule can intervene.",
    },
    {
        "kind": "hybrid",
        "lever": "hybrid_time_decay_triage_max_unrealized_r",
        "path": "parameters.hybrid_time_decay_triage_max_unrealized_r",
        "priority": 96,
        "values": [-0.25, 0.0, 0.10, 0.25],
        "search_mode": "range",
        "search_min": -1.0,
        "search_max": 0.5,
        "search_step": 0.05,
        "rationale": "Tune how much unrealized progress is enough to spare a trade from hybrid time-decay triage.",
    },
    {
        "kind": "hybrid",
        "lever": "hybrid_time_decay_triage_max_mfe_r",
        "path": "parameters.hybrid_time_decay_triage_max_mfe_r",
        "priority": 95,
        "values": [0.10, 0.25, 0.50],
        "search_mode": "range",
        "search_min": 0.0,
        "search_max": 1.0,
        "search_step": 0.05,
        "rationale": "Tune the maximum favorable excursion that still qualifies as a failing path at a checkpoint.",
    },
    {
        "kind": "hybrid",
        "lever": "hybrid_reverse_exit_triage_enabled",
        "path": "parameters.hybrid_reverse_exit_triage_enabled",
        "priority": 84,
        "values": [True, False],
        "search_mode": "values_only",
        "rationale": "Enable or disable the phase-4 rule that ignores weak-MFE reversal exits instead of closing immediately.",
    },
    {
        "kind": "hybrid",
        "lever": "hybrid_reverse_exit_min_mfe_r",
        "path": "parameters.hybrid_reverse_exit_min_mfe_r",
        "priority": 83,
        "values": [0.0, 0.10, 0.25, 0.50],
        "search_mode": "range",
        "search_min": 0.0,
        "search_max": 3.0,
        "search_step": 0.05,
        "rationale": "Tune the minimum favorable excursion needed before a reversal signal is allowed to close the current trade.",
    },
]

PRODUCTION_EVALUATION_DEFAULTS = {
    "minimum_sharpe": 0.5,
    "minimum_sortino": 0.75,
    "minimum_daily_sharpe": 0.75,
    "minimum_daily_sortino": 1.0,
    "minimum_calmar": 0.5,
    "maximum_initial_risk_pct": 1.0,
    "maximum_entry_exposure_pct": 100.0,
    "maximum_avg_exposure_pct": 100.0,
    "maximum_worst_daily_loss_pct": 5.0,
    "production_sizing_modes": ["fixed_notional_pct", "fixed_risk_pct"],
    "benchmark_policy": "outperform_return_or_calmar",
}

PORTFOLIO_PARAMETERS = {
    "sizing_mode": "fixed_risk_pct",
    "notional_pct": 0.25,
    "risk_pct": 0.005,
    "max_leverage": 1.0,
}

PORTFOLIO_MUTATION_SPACE = [
    {
        "kind": "portfolio",
        "lever": "sizing_mode",
        "path": "parameters.sizing_mode",
        "priority": 130,
        "values": ["fixed_quantity", "fixed_notional_pct", "fixed_risk_pct"],
        "search_mode": "values_only",
        "rationale": "Choose the capital model. fixed_quantity is an alpha-engine diagnostic, fixed_notional_pct compounds a notional share of current equity, and fixed_risk_pct sizes by loss budget to the stop.",
    },
    {
        "kind": "portfolio",
        "lever": "notional_pct",
        "path": "parameters.notional_pct",
        "priority": 129,
        "values": [0.1, 0.25, 0.5, 1.0],
        "search_mode": "range",
        "search_min": 0.05,
        "search_max": 1.0,
        "search_step": 0.05,
        "rationale": "When sizing_mode is fixed_notional_pct, tune the current-equity fraction used as trade notional. 1.0 means every new trade uses 100% of current equity and compounds after each closed trade.",
    },
    {
        "kind": "portfolio",
        "lever": "risk_pct",
        "path": "parameters.risk_pct",
        "priority": 128,
        "values": [0.0025, 0.005, 0.01],
        "search_mode": "range",
        "search_min": 0.001,
        "search_max": 0.01,
        "search_step": 0.001,
        "rationale": "When sizing_mode is fixed_risk_pct, tune the current-equity fraction risked to the stop. 0.01 means a 1% account-loss budget before max-leverage caps.",
    },
    {
        "kind": "portfolio",
        "lever": "max_leverage",
        "path": "parameters.max_leverage",
        "priority": 127,
        "values": [0.5, 1.0],
        "search_mode": "range",
        "search_min": 0.25,
        "search_max": 1.0,
        "search_step": 0.25,
        "rationale": "Cap position notional as a multiple of current equity. Production optimization defaults to unlevered exposure at 1.0 or lower; higher leverage should be tested only as an explicit research stress scenario.",
    },
]


SEED_SPEC = {
    "engine_id": "ma_cross_atr_stop_v1",
    "asset": "BTCUSDT",
    "venue": "Binance Spot",
    "timeframe": "15m",
    "metadata": {},
    "parameters": {
        "ma_kind": "sma",
        "fast_len": 25,
        "slow_len": 96,
        "noise_lookback": 25,
        "max_no_cross": 5,
        "entry_mode": "crossover_only",
        "allow_long": True,
        "allow_short": True,
        "atr_len": 23,
        "atr_timeframe": "15m",
        "stop_mult": 4.6,
        **PHASE_3_PARAMETERS,
        **PHASE_4_PARAMETERS,
        **PORTFOLIO_PARAMETERS,
        "quantity": 1.0,
        "initial_capital": 100000.0,
        "commission_pct": 0.04,
        "slippage_ticks": 2,
        "tick_size": 0.01,
    },
    "evaluation": {
        "minimum_trades": 50,
        "minimum_profit_factor": 1.2,
        "maximum_drawdown_pct": 12.0,
        "minimum_net_pnl": 0.0,
        **PRODUCTION_EVALUATION_DEFAULTS,
    },
    "mutation_space": [
        {
            "kind": "white_box",
            "lever": "fast_len",
            "path": "parameters.fast_len",
            "priority": 95,
            "values": [21, 34],
            "rationale": "Shift reaction speed while holding the slow anchor fixed.",
        },
        {
            "kind": "white_box",
            "lever": "slow_len",
            "path": "parameters.slow_len",
            "priority": 90,
            "values": [72, 120],
            "rationale": "Re-anchor the trend horizon without stacking other changes.",
        },
        {
            "kind": "white_box",
            "lever": "max_no_cross",
            "path": "parameters.max_no_cross",
            "priority": 80,
            "values": [4, 6],
            "rationale": "Tighten or loosen the anti-chop gate.",
        },
        {
            "kind": "white_box",
            "lever": "atr_len",
            "path": "parameters.atr_len",
            "priority": 70,
            "values": [14, 34],
            "rationale": "Change stop responsiveness through ATR memory only.",
        },
        {
            "kind": "white_box",
            "lever": "stop_mult",
            "path": "parameters.stop_mult",
            "priority": 100,
            "values": [4.0, 5.0],
            "rationale": "Tighten or loosen the static volatility stop.",
        },
        {
            "kind": "white_box",
            "lever": "entry_mode",
            "path": "parameters.entry_mode",
            "priority": 65,
            "values": ["crossover_plus_pullback"],
            "rationale": "Test whether the family benefits from adding pullback continuation entries.",
        },
        {
            "kind": "white_box",
            "lever": "ma_kind",
            "path": "parameters.ma_kind",
            "priority": 55,
            "values": ["ema"],
            "rationale": "Swap the smoothing model without changing the causal family.",
        },
        {
            "kind": "white_box",
            "lever": "allow_short",
            "path": "parameters.allow_short",
            "priority": 35,
            "values": [False],
            "rationale": "Check whether short-side participation is degrading the parent.",
        },
        {
            "kind": "white_box",
            "lever": "allow_long",
            "path": "parameters.allow_long",
            "priority": 30,
            "values": [False],
            "rationale": "Check whether long-side participation is degrading the parent.",
        },
        *PHASE_3_MUTATION_SPACE,
        *PHASE_4_MUTATION_SPACE,
        *PORTFOLIO_MUTATION_SPACE,
    ],
}


class MutationLabService:
    def __init__(
        self,
        repo: Repository | None = None,
        data_service: DataService | None = None,
        engine: BacktestEngine | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.data_service = data_service or DataService(self.repo)
        self.engine = engine or BacktestEngine()

    def ensure_seeded(self) -> None:
        settings.ensure_dirs()
        if not settings.seed_spec_path.exists():
            settings.seed_spec_path.write_text(json.dumps(SEED_SPEC, indent=2), encoding="utf-8")
        family = self.repo.get_family("btc_intraday")
        if family:
            self._upgrade_family_versions("btc_intraday")
            return
        source_code = settings.seed_strategy_path.read_text(encoding="utf-8")
        spec = json.loads(settings.seed_spec_path.read_text(encoding="utf-8"))
        created_at = datetime.now(UTC).isoformat()
        version_id = "ver_btc_intraday_parent"
        self.repo.put_family(
            {
                "family_id": "btc_intraday",
                "title": "BTC Intraday Mutation Lab Seed",
                "asset": "BTCUSDT",
                "venue": "Binance Spot",
                "timeframe": "15m",
                "current_version_id": version_id,
                "created_at": created_at,
            }
        )
        self.repo.put_version(
            {
                "version_id": version_id,
                "family_id": "btc_intraday",
                "parent_version_id": None,
                "name": "BTC Intraday Parent",
                "stage": "white_box",
                "source_code": source_code,
                "spec_json": spec,
                "causal_story": (
                    "Trend-following intraday BTC parent using aggressive moving-average crossovers, "
                    "an anti-chop fast-MA cross counter, and a static ATR stop."
                ),
                "mutation_json": {"origin": "seed"},
                "notes": "Seeded from pre-strategies/BTC-intraday.txt",
                "created_at": created_at,
            }
        )
        self._upgrade_family_versions("btc_intraday")

    def _upgrade_family_versions(self, family_id: str) -> None:
        for version in self.repo.list_versions(family_id):
            upgraded_spec, changed = self._upgrade_spec(version["spec_json"])
            if not changed:
                continue
            version["spec_json"] = upgraded_spec
            self.repo.put_version(version)

    @staticmethod
    def _upgrade_spec(spec: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        upgraded = json.loads(json.dumps(spec))
        changed = False
        if upgraded.get("engine_id") != "ma_cross_atr_stop_v1":
            return upgraded, changed
        parameters = upgraded.setdefault("parameters", {})
        for key, value in {**PHASE_3_PARAMETERS, **PHASE_4_PARAMETERS, **PORTFOLIO_PARAMETERS}.items():
            if key not in parameters:
                parameters[key] = value
                changed = True
        evaluation = upgraded.setdefault("evaluation", {})
        for key, value in PRODUCTION_EVALUATION_DEFAULTS.items():
            if key not in evaluation:
                evaluation[key] = json.loads(json.dumps(value))
                changed = True
        mutation_space = upgraded.setdefault("mutation_space", [])
        next_mutation_space = [item for item in mutation_space if item.get("lever") != "quality_gate_placeholder"]
        if len(next_mutation_space) != len(mutation_space):
            upgraded["mutation_space"] = next_mutation_space
            mutation_space = next_mutation_space
            changed = True
        existing_by_lever = {item.get("lever"): item for item in mutation_space}
        for mutation in [*PHASE_3_MUTATION_SPACE, *PHASE_4_MUTATION_SPACE, *PORTFOLIO_MUTATION_SPACE]:
            existing = existing_by_lever.get(mutation["lever"])
            if existing is None:
                mutation_space.append(json.loads(json.dumps(mutation)))
                changed = True
                continue
            for key in ("priority", "values", "search_mode", "search_min", "search_max", "search_step", "rationale", "path", "kind"):
                next_value = mutation.get(key)
                if existing.get(key) != next_value:
                    existing[key] = json.loads(json.dumps(next_value))
                    changed = True
        return upgraded, changed

    def _get_upgraded_version(self, version_id: str) -> dict[str, Any] | None:
        version = self.repo.get_version(version_id)
        if not version:
            return None
        upgraded_spec, changed = self._upgrade_spec(version["spec_json"])
        if changed:
            version["spec_json"] = upgraded_spec
            self.repo.put_version(version)
        return version

    def list_prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for path in sorted(settings.prompt_dir.glob("*.md")):
            prompts.append({"name": path.name, "content": path.read_text(encoding="utf-8")})
        return prompts

    def list_families(self) -> list[dict[str, Any]]:
        self.ensure_seeded()
        families = self.repo.list_families()
        runs = self.repo.list_runs()
        latest_by_version: dict[str, dict[str, Any]] = {}
        for run in runs:
            latest_by_version.setdefault(run["version_id"], run)
        items: list[dict[str, Any]] = []
        for family in families:
            current_version = self._get_upgraded_version(family["current_version_id"]) if family.get("current_version_id") else None
            latest_run = latest_by_version.get(family.get("current_version_id"))
            items.append(
                {
                    **family,
                    "current_version": current_version,
                    "latest_run": latest_run,
                }
            )
        return items

    def family_detail(self, family_id: str) -> dict[str, Any]:
        self.ensure_seeded()
        family = self.repo.get_family(family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Family not found.")
        self._upgrade_family_versions(family_id)
        current_version = self._get_upgraded_version(family["current_version_id"]) if family.get("current_version_id") else None
        versions = self.repo.list_versions(family_id)
        proposals = self.repo.list_proposals(family_id=family_id, parent_version_id=family["current_version_id"])
        runs = [run for run in self.repo.list_runs(family_id=family_id)]
        return {
            "family": family,
            "current_version": current_version,
            "versions": versions,
            "proposals": proposals,
            "tuning_edges": self.list_tuning_edges(family["current_version_id"]) if current_version else [],
            "runs": runs,
            "prompts": self.list_prompts(),
        }

    def list_tuning_edges(self, version_id: str, include_hybrid: bool = True) -> list[dict[str, Any]]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        spec = version["spec_json"]
        edges: list[dict[str, Any]] = []
        for mutation in spec.get("mutation_space", []):
            if mutation["kind"] == "hybrid" and not include_hybrid:
                continue
            current_value = self._read_path(spec, mutation["path"])
            suggestions = sorted(
                mutation["values"],
                key=lambda item: (str(type(item)), item if isinstance(item, (int, float)) else str(item)),
            )
            numeric_values = [item for item in suggestions if isinstance(item, (int, float)) and not isinstance(item, bool)]
            lower = [item for item in numeric_values if item < current_value]
            upper = [item for item in numeric_values if item > current_value]
            edge = {
                "lever": mutation["lever"],
                "path": mutation["path"],
                "kind": mutation["kind"],
                "priority": mutation.get("priority", 50),
                "rationale": mutation["rationale"],
                "current_value": current_value,
                "value_type": self._value_type(current_value),
                "suggested_down": lower[-1] if lower else None,
                "suggested_up": upper[0] if upper else None,
                "alternatives": suggestions,
                "search_mode": mutation.get("search_mode", "auto"),
                "search_min": mutation.get("search_min"),
                "search_max": mutation.get("search_max"),
                "search_step": mutation.get("search_step"),
            }
            edges.append(edge)
        return sorted(edges, key=lambda item: (-item["priority"], item["lever"]))

    def register_baseline(
        self,
        family_id: str,
        title: str,
        asset: str,
        venue: str,
        timeframe: str,
        version_name: str,
        source_code: str,
        spec_json: dict[str, Any],
        causal_story: str,
        notes: str,
    ) -> dict[str, Any]:
        created_at = datetime.now(UTC).isoformat()
        version_id = f"ver_{uuid.uuid4().hex[:12]}"
        self.repo.put_family(
            {
                "family_id": family_id,
                "title": title,
                "asset": asset,
                "venue": venue,
                "timeframe": timeframe,
                "current_version_id": version_id,
                "created_at": created_at,
            }
        )
        spec_json, _ = self._upgrade_spec(spec_json)
        self.repo.put_version(
            {
                "version_id": version_id,
                "family_id": family_id,
                "parent_version_id": None,
                "name": version_name,
                "stage": "white_box",
                "source_code": source_code,
                "spec_json": spec_json,
                "causal_story": causal_story,
                "mutation_json": {"origin": "manual_registration"},
                "notes": notes,
                "created_at": created_at,
            }
        )
        return self.family_detail(family_id)

    def generate_proposals(self, version_id: str, include_hybrid: bool = False) -> list[dict[str, Any]]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        spec = version["spec_json"]
        mutation_space = spec.get("mutation_space", [])
        existing = {
            json.dumps(item["patch_json"], sort_keys=True): item
            for item in self.repo.list_proposals(parent_version_id=version_id)
        }
        proposals: list[dict[str, Any]] = []
        for mutation in mutation_space:
            if mutation["kind"] != "white_box" and not include_hybrid:
                continue
            for value in mutation["values"]:
                patch = {"path": mutation["path"], "value": value}
                patch_key = json.dumps(patch, sort_keys=True)
                if patch_key in existing:
                    proposals.append(existing[patch_key])
                    continue
                proposal = {
                    "proposal_id": f"prop_{uuid.uuid4().hex[:12]}",
                    "family_id": version["family_id"],
                    "parent_version_id": version_id,
                    "status": "proposed",
                    "kind": mutation["kind"],
                    "lever": mutation["lever"],
                    "summary": f"{mutation['lever']} -> {value}",
                    "rationale": mutation["rationale"],
                    "patch_json": patch,
                    "created_at": datetime.now(UTC).isoformat(),
                }
                self.repo.put_proposal(proposal)
                proposals.append(proposal)
        return proposals

    def run_version(self, version_id: str, dataset_id: str) -> dict[str, Any]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        bars = self.data_service.load_bars(dataset_id)
        result = self.engine.run(version["spec_json"], bars)
        return self._store_run(version, dataset_id, result)

    def preview_tuned_version(
        self,
        version_id: str,
        dataset_id: str,
        parameter_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        if not isinstance(parameter_overrides, dict):
            raise HTTPException(status_code=400, detail="parameter_overrides must be an object.")
        tuned_spec = self._apply_parameter_overrides(version["spec_json"], parameter_overrides)
        bars = self.data_service.load_bars(dataset_id)
        result = self.engine.run(tuned_spec, bars)
        comparison = self._comparison(version_id, dataset_id, result["metrics"])
        return {
            "mode": "preview",
            "family_id": version["family_id"],
            "base_version_id": version_id,
            "dataset_id": dataset_id,
            "parameter_overrides": parameter_overrides,
            "spec": tuned_spec,
            "metrics": result["metrics"],
            "diagnostics": result["diagnostics"],
            "trades": result["trades"],
            "comparison": comparison,
            "verdict": self._verdict(tuned_spec, result["metrics"], comparison),
        }

    def robustness_check(
        self,
        version_id: str,
        dataset_id: str,
        parameter_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        tuned_spec = self._apply_parameter_overrides(version["spec_json"], dict(parameter_overrides or {}))
        bars = self.data_service.load_bars(dataset_id)
        if len(bars) < 40_000:
            raise HTTPException(status_code=400, detail="Robustness checks require at least 40000 bars.")
        base_result = self.engine.run(tuned_spec, bars)
        base_verdict = self._verdict(tuned_spec, base_result["metrics"], None)
        walk_forward = self._walk_forward_checks(tuned_spec, bars)
        cost_stress = self._cost_stress_checks(tuned_spec, bars)
        summary = self._robustness_summary(base_verdict, walk_forward, cost_stress)
        return {
            "mode": "robustness_check",
            "version_id": version_id,
            "dataset_id": dataset_id,
            "parameter_overrides": parameter_overrides or {},
            "base_verdict": base_verdict,
            "base_metrics": base_result["metrics"],
            "walk_forward": walk_forward,
            "cost_stress": cost_stress,
            "summary": summary,
        }

    def _walk_forward_checks(self, spec: dict[str, Any], bars: list[Any]) -> list[dict[str, Any]]:
        folds: list[dict[str, Any]] = []
        fold_count = 4
        fold_size = len(bars) // fold_count
        for index in range(fold_count):
            start = index * fold_size
            end = len(bars) if index == fold_count - 1 else (index + 1) * fold_size
            fold_bars = bars[start:end]
            if len(fold_bars) < 500:
                continue
            result = self.engine.run(spec, fold_bars)
            failures = self._core_gate_failures(spec, result["metrics"]) + self._portfolio_gate_failures(spec, result["metrics"])
            folds.append(
                {
                    "fold": index + 1,
                    "start_ts": fold_bars[0].ts.isoformat(),
                    "end_ts": fold_bars[-1].ts.isoformat(),
                    "bars": len(fold_bars),
                    "passed": not failures,
                    "failures": failures,
                    "metrics": self._compact_metrics(result["metrics"]),
                }
            )
        return folds

    def _cost_stress_checks(self, spec: dict[str, Any], bars: list[Any]) -> list[dict[str, Any]]:
        parameters = spec.get("parameters", {})
        base_commission = float(parameters.get("commission_pct", 0.0))
        base_slippage = int(parameters.get("slippage_ticks", 0))
        scenarios = [
            ("commission_2x", base_commission * 2, base_slippage),
            ("slippage_2x", base_commission, base_slippage * 2),
            ("commission_2x_slippage_2x", base_commission * 2, base_slippage * 2),
        ]
        results: list[dict[str, Any]] = []
        for name, commission, slippage in scenarios:
            stressed = json.loads(json.dumps(spec))
            stressed.setdefault("parameters", {})["commission_pct"] = commission
            stressed["parameters"]["slippage_ticks"] = slippage
            result = self.engine.run(stressed, bars)
            failures = self._core_gate_failures(stressed, result["metrics"]) + self._portfolio_gate_failures(
                stressed, result["metrics"]
            )
            results.append(
                {
                    "scenario": name,
                    "commission_pct": commission,
                    "slippage_ticks": slippage,
                    "passed": not failures,
                    "failures": failures,
                    "metrics": self._compact_metrics(result["metrics"]),
                }
            )
        return results

    @staticmethod
    def _compact_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "return_pct",
            "profit_factor",
            "total_trades",
            "max_equity_drawdown_pct",
            "daily_sharpe",
            "daily_sortino",
            "worst_daily_return_pct",
            "calmar",
            "outperformance_pct",
            "max_initial_risk_pct",
            "max_entry_exposure_pct",
        ]
        return {key: metrics.get(key, 0.0) for key in keys}

    @staticmethod
    def _robustness_summary(base_verdict: str, walk_forward: list[dict[str, Any]], cost_stress: list[dict[str, Any]]) -> dict[str, Any]:
        walk_passed = sum(1 for item in walk_forward if item["passed"])
        stress_passed = sum(1 for item in cost_stress if item["passed"])
        passed = base_verdict == "promotion_candidate" and walk_passed == len(walk_forward) and stress_passed == len(cost_stress)
        if passed:
            label = "production_robustness_candidate"
        elif walk_passed >= max(1, len(walk_forward) - 1) and stress_passed >= max(1, len(cost_stress) - 1):
            label = "needs_review"
        else:
            label = "not_robust"
        return {
            "label": label,
            "passed": passed,
            "walk_forward_passed": walk_passed,
            "walk_forward_total": len(walk_forward),
            "cost_stress_passed": stress_passed,
            "cost_stress_total": len(cost_stress),
        }

    def optimize_lever(
        self,
        version_id: str,
        dataset_id: str,
        lever: str,
        parameter_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        base_overrides = dict(parameter_overrides or {})
        edges = self.list_tuning_edges(version_id)
        edge = next((item for item in edges if item["lever"] == lever), None)
        if not edge:
            raise HTTPException(status_code=404, detail="Tuning lever not found.")
        bars = self.data_service.load_bars(dataset_id)
        candidates: list[dict[str, Any]] = []
        values = self._candidate_values(edge)
        for value in values:
            overrides = {**base_overrides, lever: value}
            tuned_spec = self._apply_parameter_overrides(version["spec_json"], overrides)
            result = self.engine.run(tuned_spec, bars)
            comparison = self._comparison(version_id, dataset_id, result["metrics"])
            verdict = self._verdict(tuned_spec, result["metrics"], comparison)
            candidates.append(
                {
                    "lever": lever,
                    "value": value,
                    "score": self._optimization_score(tuned_spec, result["metrics"]),
                    "score_components": self._optimization_score_components(tuned_spec, result["metrics"]),
                    "eligible": self._optimization_eligible(tuned_spec, result["metrics"]),
                    "verdict": verdict,
                    "metrics": result["metrics"],
                    "comparison": comparison,
                    "parameter_overrides": overrides,
                }
            )
        if not candidates:
            raise HTTPException(status_code=400, detail="No candidates generated for this lever.")
        eligible_candidates = [candidate for candidate in candidates if candidate["eligible"]]
        if eligible_candidates:
            best = max(eligible_candidates, key=lambda item: item["score"])
            selection_mode = "eligible_only"
        else:
            current_value = base_overrides.get(lever, version["spec_json"].get("parameters", {}).get(lever))
            current_candidates = [candidate for candidate in candidates if candidate["value"] == current_value]
            best = current_candidates[0] if current_candidates else max(candidates, key=lambda item: item["score"])
            best = {**best, "parameter_overrides": base_overrides}
            selection_mode = "no_production_eligible_keep_current"
        best_spec = self._apply_parameter_overrides(version["spec_json"], best["parameter_overrides"])
        return {
            "mode": "optimize_lever",
            "family_id": version["family_id"],
            "base_version_id": version_id,
            "dataset_id": dataset_id,
            "lever": lever,
            "objective": (
                "first require enough trade evidence, positive net PnL, profit factor, drawdown, Sharpe/Sortino/Calmar, "
                "bounded trade risk, production sizing, and benchmark comparability when any candidate satisfies them; "
                "then maximize a balanced risk-adjusted score using capped profit factor, trade evidence, net return, "
                "buy-and-hold outperformance, Calmar efficiency, win rate, payoff, and drawdown"
            ),
            "search": self._search_summary(edge, values),
            "eligible_count": len(eligible_candidates),
            "selection_mode": selection_mode,
            "best": best,
            "best_spec": best_spec,
            "candidates": sorted(candidates, key=lambda item: (item["eligible"], item["score"]), reverse=True),
        }

    def optimize_all(
        self,
        version_id: str,
        dataset_id: str,
        parameter_overrides: dict[str, Any] | None = None,
        passes: int = 2,
    ) -> dict[str, Any]:
        version = self._get_upgraded_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        passes = max(1, min(int(passes), 5))
        overrides = self._production_baseline_overrides(version["spec_json"], dict(parameter_overrides or {}))
        steps: list[dict[str, Any]] = []
        for pass_index in range(1, passes + 1):
            improved = False
            for edge in self.list_tuning_edges(version_id):
                before = dict(overrides)
                result = self.optimize_lever(version_id, dataset_id, edge["lever"], overrides)
                best_overrides = result["best"]["parameter_overrides"]
                if best_overrides != before:
                    improved = True
                    overrides = best_overrides
                steps.append(
                    {
                        "pass": pass_index,
                        "lever": edge["lever"],
                        "before": before.get(edge["lever"], edge["current_value"]),
                        "after": overrides.get(edge["lever"], edge["current_value"]),
                        "best_score": result["best"]["score"],
                        "best_metrics": result["best"]["metrics"],
                    }
                )
            if not improved:
                break
        preview = self.preview_tuned_version(version_id, dataset_id, overrides)
        return {
            "mode": "optimize_all",
            "base_version_id": version_id,
            "dataset_id": dataset_id,
            "passes_requested": passes,
            "parameter_overrides": overrides,
            "steps": steps,
            "preview": preview,
        }

    @staticmethod
    def _production_baseline_overrides(spec: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        parameters = spec.get("parameters", {})
        rules = spec.get("evaluation", {})
        output = dict(overrides)
        allowed_modes = rules.get("production_sizing_modes", ["fixed_notional_pct", "fixed_risk_pct"])
        selected_mode = output.get("sizing_mode", parameters.get("sizing_mode", "fixed_quantity"))
        if selected_mode not in allowed_modes:
            output["sizing_mode"] = "fixed_risk_pct"
        selected_risk = float(output.get("risk_pct", parameters.get("risk_pct", 0.005)))
        max_risk = float(rules.get("maximum_initial_risk_pct", 1.0)) / 100
        if selected_risk <= 0 or selected_risk > max_risk:
            output["risk_pct"] = min(0.005, max_risk)
        selected_leverage = float(output.get("max_leverage", parameters.get("max_leverage", 1.0)))
        max_exposure = float(rules.get("maximum_entry_exposure_pct", 100.0)) / 100
        if selected_leverage <= 0 or selected_leverage > max_exposure:
            output["max_leverage"] = max_exposure
        return output

    def save_tuned_version(
        self,
        version_id: str,
        dataset_id: str,
        parameter_overrides: dict[str, Any],
        name: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        parent = self._get_upgraded_version(version_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Version not found.")
        tuned_spec = self._apply_parameter_overrides(parent["spec_json"], parameter_overrides)
        child_version_id = f"ver_{uuid.uuid4().hex[:12]}"
        summary = self._summarize_overrides(parameter_overrides)
        child_version = {
            "version_id": child_version_id,
            "family_id": parent["family_id"],
            "parent_version_id": parent["version_id"],
            "name": name or f"{parent['name']} | tuned {summary}",
            "stage": "white_box",
            "source_code": parent["source_code"],
            "spec_json": tuned_spec,
            "causal_story": parent["causal_story"],
            "mutation_json": {
                "origin": "manual_parameter_tune",
                "summary": summary,
                "parameter_overrides": parameter_overrides,
            },
            "notes": notes or f"Saved from in-app parameter tuning against {dataset_id}.",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_version(child_version)
        result = self.engine.run(tuned_spec, self.data_service.load_bars(dataset_id))
        return self._store_run(child_version, dataset_id, result)

    def run_proposal(self, proposal_id: str, dataset_id: str) -> dict[str, Any]:
        proposal = self.repo.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found.")
        parent = self._get_upgraded_version(proposal["parent_version_id"])
        if not parent:
            raise HTTPException(status_code=404, detail="Parent version not found.")
        child_version_id = proposal.get("child_version_id") or f"ver_{uuid.uuid4().hex[:12]}"
        child_spec = apply_patch_to_spec(parent["spec_json"], proposal["patch_json"])
        child_version = {
            "version_id": child_version_id,
            "family_id": parent["family_id"],
            "parent_version_id": parent["version_id"],
            "name": f"{parent['name']} | {proposal['summary']}",
            "stage": proposal["kind"],
            "source_code": parent["source_code"],
            "spec_json": child_spec,
            "causal_story": parent["causal_story"],
            "mutation_json": {
                "proposal_id": proposal["proposal_id"],
                "summary": proposal["summary"],
                "rationale": proposal["rationale"],
                "patch": proposal["patch_json"],
            },
            "notes": parent.get("notes", ""),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_version(child_version)
        result = self.engine.run(child_spec, self.data_service.load_bars(dataset_id))
        run_payload = self._store_run(child_version, dataset_id, result)
        proposal["status"] = "tested"
        proposal["child_version_id"] = child_version_id
        proposal["run_id"] = run_payload["run_id"]
        self.repo.put_proposal(proposal)
        return run_payload

    def run_proposal_pack(self, version_id: str, dataset_id: str, include_hybrid: bool = False) -> dict[str, Any]:
        proposals = self.generate_proposals(version_id, include_hybrid=include_hybrid)
        tested: list[dict[str, Any]] = []
        for proposal in proposals:
            if proposal["status"] == "tested":
                continue
            tested.append(self.run_proposal(proposal["proposal_id"], dataset_id))
        best_run = None
        if tested:
            best_run = max(tested, key=lambda item: item["metrics"]["profit_factor"])
        return {
            "version_id": version_id,
            "dataset_id": dataset_id,
            "tested_runs": tested,
            "tested_count": len(tested),
            "best_run": best_run,
        }

    def promote_version(self, family_id: str, version_id: str) -> dict[str, Any]:
        family = self.repo.get_family(family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Family not found.")
        family["current_version_id"] = version_id
        self.repo.put_family(family)
        return self.family_detail(family_id)

    def list_runs(self, family_id: str | None = None) -> list[dict[str, Any]]:
        return self.repo.list_runs(family_id=family_id)

    def run_hybrid_entry_quality_experiment(
        self,
        run_id: str,
        veto_fraction: float = 0.15,
    ) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifact_path = Path(run["artifact_path"])
        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="Run artifact not found.")
        parent_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        bars = self.data_service.load_bars(parent_payload["dataset_id"])
        result = self.engine.run(parent_payload["spec"], bars)
        rows = self._hybrid_trade_rows(
            run_id=run_id,
            family_id=parent_payload["family_id"],
            version_id=parent_payload["version_id"],
            dataset_id=parent_payload["dataset_id"],
            trades=result["trades"],
        )
        if len(rows) < 50:
            raise HTTPException(status_code=400, detail="Hybrid experiment requires at least 50 trades.")
        model = self._fit_entry_quality_scorecard(rows)
        scored_rows = self._score_hybrid_rows(rows, model)
        cutoff = self._veto_cutoff(scored_rows, veto_fraction, "bad_entry_quality_score")
        retained_trades = [
            row["trade"]
            for row in scored_rows
            if row["bad_entry_quality_score"] < cutoff or row["split"] == "train"
        ]
        vetoed_rows = [
            row
            for row in scored_rows
            if row["bad_entry_quality_score"] >= cutoff and row["split"] != "train"
        ]
        retained_metrics = self._metrics_from_filtered_trades(parent_payload["spec"], bars, retained_trades)
        comparison = {
            "parent_run_id": run_id,
            "profit_factor_delta": round(retained_metrics["profit_factor"] - result["metrics"]["profit_factor"], 4),
            "net_pnl_delta": round(retained_metrics["net_pnl"] - result["metrics"]["net_pnl"], 2),
            "drawdown_pct_delta": round(
                retained_metrics["max_equity_drawdown_pct"] - result["metrics"]["max_equity_drawdown_pct"],
                2,
            ),
            "trade_count_delta": retained_metrics["total_trades"] - result["metrics"]["total_trades"],
        }
        payload = {
            "experiment_id": f"hyb_{uuid.uuid4().hex[:12]}",
            "parent_run_id": run_id,
            "family_id": parent_payload["family_id"],
            "version_id": parent_payload["version_id"],
            "dataset_id": parent_payload["dataset_id"],
            "mode": "offline_entry_quality_veto",
            "veto_fraction": veto_fraction,
            "model": model,
            "parent_metrics": result["metrics"],
            "hybrid_metrics": retained_metrics,
            "comparison": comparison,
            "rows": [
                {key: value for key, value in row.items() if key != "trade"}
                for row in scored_rows
            ],
            "vetoed_summary": self._vetoed_summary(vetoed_rows),
            "verdict": self._hybrid_verdict(result["metrics"], retained_metrics, len(vetoed_rows), len(rows)),
        }
        export_path = settings.diagnostic_dir / f"{payload['experiment_id']}_trade_features.json"
        report_path = settings.diagnostic_dir / f"{payload['experiment_id']}.md"
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report_path.write_text(self._hybrid_report(payload), encoding="utf-8")
        payload["export_path"] = str(export_path)
        payload["report_path"] = str(report_path)
        return payload

    def run_hybrid_time_decay_triage_experiment(
        self,
        run_id: str,
        exit_fraction: float = 0.15,
    ) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifact_path = Path(run["artifact_path"])
        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="Run artifact not found.")
        parent_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        bars = self.data_service.load_bars(parent_payload["dataset_id"])
        result = self.engine.run(parent_payload["spec"], bars)
        snapshots = self._hybrid_time_decay_snapshot_rows(
            run_id=run_id,
            family_id=parent_payload["family_id"],
            version_id=parent_payload["version_id"],
            dataset_id=parent_payload["dataset_id"],
            trades=result["trades"],
            bars=bars,
            spec=parent_payload["spec"],
        )
        if len(snapshots) < 50:
            raise HTTPException(status_code=400, detail="Hybrid time-decay triage requires at least 50 snapshots.")
        model = self._fit_time_decay_triage_scorecard(snapshots)
        scored_rows = self._score_time_decay_rows(snapshots, model)
        cutoff = self._veto_cutoff(scored_rows, exit_fraction, "bad_time_decay_path_score")
        triaged = self._apply_time_decay_triage(
            rows=scored_rows,
            trades=result["trades"],
            cutoff=cutoff,
            spec=parent_payload["spec"],
        )
        hybrid_metrics = self._metrics_from_filtered_trades(parent_payload["spec"], bars, triaged["trades"])
        comparison = {
            "parent_run_id": run_id,
            "profit_factor_delta": round(hybrid_metrics["profit_factor"] - result["metrics"]["profit_factor"], 4),
            "net_pnl_delta": round(hybrid_metrics["net_pnl"] - result["metrics"]["net_pnl"], 2),
            "drawdown_pct_delta": round(
                hybrid_metrics["max_equity_drawdown_pct"] - result["metrics"]["max_equity_drawdown_pct"],
                2,
            ),
            "trade_count_delta": hybrid_metrics["total_trades"] - result["metrics"]["total_trades"],
        }
        payload = {
            "experiment_id": f"hyb_{uuid.uuid4().hex[:12]}",
            "parent_run_id": run_id,
            "family_id": parent_payload["family_id"],
            "version_id": parent_payload["version_id"],
            "dataset_id": parent_payload["dataset_id"],
            "mode": "offline_time_decay_path_triage",
            "exit_fraction": exit_fraction,
            "model": model,
            "parent_metrics": result["metrics"],
            "hybrid_metrics": hybrid_metrics,
            "comparison": comparison,
            "rows": [
                {key: value for key, value in row.items() if key != "trade"}
                for row in scored_rows
            ],
            "triage_summary": triaged["summary"],
            "verdict": self._hybrid_verdict(result["metrics"], hybrid_metrics, triaged["summary"]["early_exit_count"], len(result["trades"])),
        }
        export_path = settings.diagnostic_dir / f"{payload['experiment_id']}_time_decay_snapshots.json"
        report_path = settings.diagnostic_dir / f"{payload['experiment_id']}.md"
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report_path.write_text(self._hybrid_time_decay_report(payload), encoding="utf-8")
        payload["export_path"] = str(export_path)
        payload["report_path"] = str(report_path)
        return payload

    def delete_run(self, run_id: str) -> None:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        for artifact in (run["artifact_path"], run["report_path"]):
            path = Path(artifact)
            if path.exists():
                path.unlink()
        self.repo.delete_run(run_id)

    def delete_version(self, version_id: str) -> dict[str, Any]:
        version = self.repo.get_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found.")
        family = self.repo.get_family(version["family_id"])
        if not family:
            raise HTTPException(status_code=404, detail="Family not found.")
        if family.get("current_version_id") == version_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the current family version. Promote another version first.",
            )
        runs = [run for run in self.repo.list_runs(family_id=version["family_id"]) if run["version_id"] == version_id]
        for run in runs:
            self.delete_run(run["run_id"])
        self.repo.delete_proposals_for_version(version_id)
        self.repo.delete_version(version_id)
        return self.family_detail(version["family_id"])

    def _store_run(self, version: dict[str, Any], dataset_id: str, result: dict[str, Any]) -> dict[str, Any]:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        artifact_path = settings.run_dir / f"{run_id}.json"
        report_path = settings.report_dir / f"{run_id}.md"
        comparison = self._comparison(version["parent_version_id"], dataset_id, result["metrics"])
        verdict = self._verdict(version["spec_json"], result["metrics"], comparison)
        payload = {
            "run_id": run_id,
            "family_id": version["family_id"],
            "version_id": version["version_id"],
            "dataset_id": dataset_id,
            "verdict": verdict,
            "metrics": result["metrics"],
            "diagnostics": result["diagnostics"],
            "trades": result["trades"],
            "equity_curve": result["equity_curve"],
            "comparison": comparison,
            "spec": version["spec_json"],
            "mutation": version.get("mutation_json", {}),
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report_path.write_text(self._run_report(version, payload), encoding="utf-8")
        self.repo.put_run(
            {
                "run_id": run_id,
                "family_id": version["family_id"],
                "version_id": version["version_id"],
                "dataset_id": dataset_id,
                "status": "completed",
                "verdict": verdict,
                "metrics_json": result["metrics"],
                "artifact_path": str(artifact_path),
                "report_path": str(report_path),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        payload["artifact_path"] = str(artifact_path)
        payload["report_path"] = str(report_path)
        return payload

    def _hybrid_trade_rows(
        self,
        run_id: str,
        family_id: str,
        version_id: str,
        dataset_id: str,
        trades: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for trade in trades:
            entry_ts = datetime.fromisoformat(trade["entry_ts"])
            exit_ts = datetime.fromisoformat(trade["exit_ts"])
            features = trade.get("entry_features", {})
            bad_label = trade["reason"] == "time_decay" or (trade["net_pnl"] < 0 and trade.get("mfe_r", 0.0) < 0.35)
            row = {
                "run_id": run_id,
                "trade_id": trade["trade_id"],
                "family_id": family_id,
                "version_id": version_id,
                "dataset_id": dataset_id,
                "entry_ts": trade["entry_ts"],
                "exit_ts": trade["exit_ts"],
                "year": entry_ts.year,
                "month": entry_ts.month,
                "weekday": entry_ts.weekday(),
                "utc_hour": entry_ts.hour,
                "split": self._chronological_split(entry_ts.year),
                "side": trade["direction"],
                "entry_price": trade["entry_price"],
                "stop_price": trade["stop_price"],
                "exit_reason": trade["reason"],
                "net_pnl": trade["net_pnl"],
                "return_on_equity_pct": trade["return_on_equity_pct"],
                "duration_bars": trade["bars_held"],
                "mfe_r": trade.get("mfe_r", 0.0),
                "mae_r": trade.get("mae_r", 0.0),
                "bad_entry_quality": bad_label,
                "time_decay_failure": trade["reason"] == "time_decay",
                "low_mfe_failure": trade["net_pnl"] < 0 and trade.get("mfe_r", 0.0) < 0.35,
                "trade": trade,
            }
            row.update(features)
            rows.append(row)
            del exit_ts
        return rows

    def _hybrid_time_decay_snapshot_rows(
        self,
        run_id: str,
        family_id: str,
        version_id: str,
        dataset_id: str,
        trades: list[dict[str, Any]],
        bars: list[Any],
        spec: dict[str, Any],
    ) -> list[dict[str, Any]]:
        checkpoints = [10, 20, 30]
        bars_by_ts = {bar.ts.isoformat(): index for index, bar in enumerate(bars)}
        closes = [bar.close for bar in bars]
        from app.backtest import atr, sma

        fast = sma(closes, int(spec["parameters"]["fast_len"]))
        slow = sma(closes, int(spec["parameters"]["slow_len"]))
        atr_values = atr(bars, int(spec["parameters"]["atr_len"]))
        rows: list[dict[str, Any]] = []
        for trade in trades:
            entry_index = bars_by_ts.get(trade["entry_ts"])
            if entry_index is None:
                continue
            entry_ts = datetime.fromisoformat(trade["entry_ts"])
            exit_index = bars_by_ts.get(trade["exit_ts"], entry_index + int(trade["bars_held"]))
            initial_risk = abs(float(trade["entry_price"]) - float(trade["stop_price"]))
            if not initial_risk:
                continue
            for checkpoint in checkpoints:
                snapshot_index = entry_index + checkpoint
                if snapshot_index >= len(bars) or snapshot_index >= exit_index:
                    continue
                bar = bars[snapshot_index]
                path = bars[entry_index + 1 : snapshot_index + 1]
                if not path:
                    continue
                if trade["direction"] == "long":
                    unrealized = bar.close - float(trade["entry_price"])
                    mfe = max(item.high - float(trade["entry_price"]) for item in path)
                    mae = min(item.low - float(trade["entry_price"]) for item in path)
                    distance_to_stop = bar.close - float(trade["stop_price"])
                else:
                    unrealized = float(trade["entry_price"]) - bar.close
                    mfe = max(float(trade["entry_price"]) - item.low for item in path)
                    mae = min(float(trade["entry_price"]) - item.high for item in path)
                    distance_to_stop = float(trade["stop_price"]) - bar.close
                current_fast = float(fast[snapshot_index] or 0.0)
                current_slow = float(slow[snapshot_index] or 0.0)
                current_atr = float(atr_values[snapshot_index] or 0.0)
                final_bad = trade["reason"] == "time_decay" or (trade["net_pnl"] < 0 and trade.get("mfe_r", 0.0) < 0.35)
                rows.append(
                    {
                        "run_id": run_id,
                        "trade_id": trade["trade_id"],
                        "family_id": family_id,
                        "version_id": version_id,
                        "dataset_id": dataset_id,
                        "entry_ts": trade["entry_ts"],
                        "snapshot_ts": bar.ts.isoformat(),
                        "exit_ts": trade["exit_ts"],
                        "year": entry_ts.year,
                        "month": entry_ts.month,
                        "weekday": bar.ts.weekday(),
                        "utc_hour": bar.ts.hour,
                        "split": self._chronological_split(entry_ts.year),
                        "side": trade["direction"],
                        "checkpoint_bars": checkpoint,
                        "entry_price": trade["entry_price"],
                        "snapshot_close": bar.close,
                        "stop_price": trade["stop_price"],
                        "unrealized_r": round(unrealized / initial_risk, 6),
                        "mfe_r_so_far": round(mfe / initial_risk, 6),
                        "mae_r_so_far": round(mae / initial_risk, 6),
                        "distance_to_stop_r": round(distance_to_stop / initial_risk, 6),
                        "fast_minus_slow": round(current_fast - current_slow, 6),
                        "normalized_ma_distance": round((current_fast - current_slow) / bar.close, 8) if bar.close else 0.0,
                        "atr_pct": round(current_atr / bar.close, 8) if bar.close else 0.0,
                        "final_exit_reason": trade["reason"],
                        "final_net_pnl": trade["net_pnl"],
                        "final_mfe_r": trade.get("mfe_r", 0.0),
                        "bad_time_decay_path": final_bad,
                        "trade": trade,
                    }
                )
        return rows

    @staticmethod
    def _chronological_split(year: int) -> str:
        if year <= 2022:
            return "train"
        if year <= 2024:
            return "validation"
        return "test"

    def _fit_entry_quality_scorecard(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        train_rows = [row for row in rows if row["split"] == "train"] or rows[: max(1, int(len(rows) * 0.6))]
        feature_names = [
            "side",
            "weekday",
            "utc_hour",
            "month",
            "normalized_ma_distance",
            "fast_slope",
            "slow_slope",
            "atr_pct",
            "recent_return_20",
            "recent_range_20",
            "recent_volatility_20",
            "recent_cross_count",
            "stop_distance_atr",
        ]
        base_rate = sum(1 for row in train_rows if row["bad_entry_quality"]) / len(train_rows)
        feature_scores: dict[str, dict[str, float]] = {}
        for name in feature_names:
            buckets: dict[str, list[dict[str, Any]]] = {}
            values = [row.get(name) for row in train_rows if isinstance(row.get(name), (int, float))]
            cuts = self._quartile_cuts([float(value) for value in values]) if values else []
            for row in train_rows:
                bucket = self._score_bucket(row.get(name), cuts)
                buckets.setdefault(bucket, []).append(row)
            feature_scores[name] = {}
            for bucket, bucket_rows in buckets.items():
                bad_rate = sum(1 for row in bucket_rows if row["bad_entry_quality"]) / len(bucket_rows)
                weight = min(len(bucket_rows) / max(1, len(train_rows) * 0.10), 1.0)
                feature_scores[name][bucket] = round((bad_rate - base_rate) * weight, 6)
        return {
            "family": "vanilla_scorecard",
            "target": "bad_entry_quality",
            "base_rate": round(base_rate, 6),
            "features": feature_names,
            "feature_scores": feature_scores,
            "trained_rows": len(train_rows),
            "train_bad_rows": sum(1 for row in train_rows if row["bad_entry_quality"]),
        }

    def _fit_time_decay_triage_scorecard(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        train_rows = [row for row in rows if row["split"] == "train"] or rows[: max(1, int(len(rows) * 0.6))]
        feature_names = [
            "side",
            "checkpoint_bars",
            "weekday",
            "utc_hour",
            "month",
            "unrealized_r",
            "mfe_r_so_far",
            "mae_r_so_far",
            "distance_to_stop_r",
            "normalized_ma_distance",
            "atr_pct",
        ]
        base_rate = sum(1 for row in train_rows if row["bad_time_decay_path"]) / len(train_rows)
        feature_scores: dict[str, dict[str, float]] = {}
        for name in feature_names:
            buckets: dict[str, list[dict[str, Any]]] = {}
            values = [row.get(name) for row in train_rows if isinstance(row.get(name), (int, float))]
            cuts = self._quartile_cuts([float(value) for value in values]) if values else []
            for row in train_rows:
                bucket = self._score_bucket(row.get(name), cuts)
                buckets.setdefault(bucket, []).append(row)
            feature_scores[name] = {}
            for bucket, bucket_rows in buckets.items():
                bad_rate = sum(1 for row in bucket_rows if row["bad_time_decay_path"]) / len(bucket_rows)
                weight = min(len(bucket_rows) / max(1, len(train_rows) * 0.10), 1.0)
                feature_scores[name][bucket] = round((bad_rate - base_rate) * weight, 6)
        return {
            "family": "vanilla_scorecard",
            "target": "bad_time_decay_path",
            "base_rate": round(base_rate, 6),
            "features": feature_names,
            "feature_scores": feature_scores,
            "trained_rows": len(train_rows),
            "train_bad_rows": sum(1 for row in train_rows if row["bad_time_decay_path"]),
        }

    def _score_hybrid_rows(self, rows: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        cuts_by_feature: dict[str, list[float]] = {}
        train_rows = [row for row in rows if row["split"] == "train"] or rows
        for name in model["features"]:
            values = [row.get(name) for row in train_rows if isinstance(row.get(name), (int, float))]
            cuts_by_feature[name] = self._quartile_cuts([float(value) for value in values]) if values else []
        for row in rows:
            score = float(model["base_rate"])
            for name in model["features"]:
                bucket = self._score_bucket(row.get(name), cuts_by_feature[name])
                score += model["feature_scores"].get(name, {}).get(bucket, 0.0)
            next_row = dict(row)
            next_row["bad_entry_quality_score"] = round(max(0.0, min(score, 1.0)), 6)
            scored.append(next_row)
        return scored

    def _score_time_decay_rows(self, rows: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        cuts_by_feature: dict[str, list[float]] = {}
        train_rows = [row for row in rows if row["split"] == "train"] or rows
        for name in model["features"]:
            values = [row.get(name) for row in train_rows if isinstance(row.get(name), (int, float))]
            cuts_by_feature[name] = self._quartile_cuts([float(value) for value in values]) if values else []
        for row in rows:
            score = float(model["base_rate"])
            for name in model["features"]:
                bucket = self._score_bucket(row.get(name), cuts_by_feature[name])
                score += model["feature_scores"].get(name, {}).get(bucket, 0.0)
            next_row = dict(row)
            next_row["bad_time_decay_path_score"] = round(max(0.0, min(score, 1.0)), 6)
            scored.append(next_row)
        return scored

    @staticmethod
    def _quartile_cuts(values: list[float]) -> list[float]:
        if not values:
            return []
        ordered = sorted(values)
        return [
            ordered[int((len(ordered) - 1) * 0.25)],
            ordered[int((len(ordered) - 1) * 0.50)],
            ordered[int((len(ordered) - 1) * 0.75)],
        ]

    @staticmethod
    def _score_bucket(value: Any, cuts: list[float]) -> str:
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, str):
            return value
        if not isinstance(value, (int, float)) or math.isnan(float(value)):
            return "missing"
        if not cuts:
            return str(value)
        numeric = float(value)
        if numeric <= cuts[0]:
            return "q1"
        if numeric <= cuts[1]:
            return "q2"
        if numeric <= cuts[2]:
            return "q3"
        return "q4"

    @staticmethod
    def _veto_cutoff(rows: list[dict[str, Any]], veto_fraction: float, score_field: str) -> float:
        validation_rows = [row for row in rows if row["split"] != "train"]
        scores = sorted(row[score_field] for row in validation_rows)
        if not scores:
            return 1.1
        veto_count = max(1, int(len(scores) * max(0.0, min(veto_fraction, 0.9))))
        return scores[-veto_count]

    def _metrics_from_filtered_trades(
        self,
        spec: dict[str, Any],
        bars: list[Any],
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        initial_capital = float(spec.get("parameters", {}).get("initial_capital", 100_000.0))
        equity = initial_capital
        equity_curve: list[dict[str, Any]] = []
        for trade in sorted(trades, key=lambda item: item["exit_ts"]):
            equity += trade["net_pnl"]
            equity_curve.append({"ts": trade["exit_ts"], "equity": round(equity, 2)})
        if not equity_curve and bars:
            equity_curve.append({"ts": bars[-1].ts.isoformat(), "equity": round(equity, 2)})
        from app.backtest import benchmark_warmup_index, compute_metrics

        parameters = spec.get("parameters", {})
        warmup = benchmark_warmup_index(parameters, len(bars))
        buy_hold_start_price = bars[warmup].close if len(bars) > warmup else bars[0].close
        buy_hold_end_price = bars[-1].close
        buy_hold_return_pct = (
            ((buy_hold_end_price - buy_hold_start_price) / buy_hold_start_price) * 100
            if buy_hold_start_price
            else 0.0
        )
        buy_hold_return = initial_capital * (buy_hold_return_pct / 100)
        buy_hold_max_drawdown = buy_hold_drawdown_pct(bars, warmup)

        return compute_metrics(
            initial_capital,
            trades,
            equity_curve,
            buy_hold_return,
            buy_hold_return_pct,
            buy_hold_start_price,
            buy_hold_end_price,
            buy_hold_max_drawdown,
        )

    def _apply_time_decay_triage(
        self,
        rows: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        cutoff: float,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        rows_by_trade: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if row["split"] == "train":
                continue
            rows_by_trade.setdefault(row["trade_id"], []).append(row)
        early_exit_by_trade: dict[str, dict[str, Any]] = {}
        for trade_id, trade_rows in rows_by_trade.items():
            candidates = sorted(
                [row for row in trade_rows if row["bad_time_decay_path_score"] >= cutoff],
                key=lambda item: item["checkpoint_bars"],
            )
            if candidates:
                early_exit_by_trade[trade_id] = candidates[0]

        commission_pct = float(spec.get("parameters", {}).get("commission_pct", 0.0)) / 100
        triaged_trades: list[dict[str, Any]] = []
        changed_rows: list[dict[str, Any]] = []
        for trade in trades:
            row = early_exit_by_trade.get(trade["trade_id"])
            if not row:
                triaged_trades.append(trade)
                continue
            exit_price = float(row["snapshot_close"])
            entry_price = float(trade["entry_price"])
            quantity = float(trade.get("quantity", spec.get("parameters", {}).get("quantity", 1.0)))
            if trade["direction"] == "long":
                gross_pnl = (exit_price - entry_price) * quantity
            else:
                gross_pnl = (entry_price - exit_price) * quantity
            entry_commission = entry_price * quantity * commission_pct
            exit_commission = exit_price * quantity * commission_pct
            net_pnl = gross_pnl - entry_commission - exit_commission
            next_trade = dict(trade)
            next_trade.update(
                {
                    "exit_ts": row["snapshot_ts"],
                    "exit_price": round(exit_price, 4),
                    "quantity": round(quantity, 8),
                    "gross_pnl": round(gross_pnl, 2),
                    "net_pnl": round(net_pnl, 2),
                    "bars_held": int(row["checkpoint_bars"]),
                    "reason": "hybrid_time_decay_triage",
                    "mfe_r": row["mfe_r_so_far"],
                    "mae_r": row["mae_r_so_far"],
                    "return_on_equity_pct": round((net_pnl / float(spec.get("parameters", {}).get("initial_capital", 100_000.0))) * 100, 4),
                }
            )
            triaged_trades.append(next_trade)
            changed_rows.append(row)
        return {
            "trades": triaged_trades,
            "summary": {
                "early_exit_count": len(changed_rows),
                "bad_rate": round((sum(1 for row in changed_rows if row["bad_time_decay_path"]) / len(changed_rows)) * 100, 2)
                if changed_rows
                else 0.0,
                "time_decay_count": sum(1 for row in changed_rows if row["final_exit_reason"] == "time_decay"),
                "original_net_pnl": round(sum(row["final_net_pnl"] for row in changed_rows), 2),
                "avg_checkpoint": round(sum(row["checkpoint_bars"] for row in changed_rows) / len(changed_rows), 2)
                if changed_rows
                else 0.0,
            },
        }

    @staticmethod
    def _vetoed_summary(vetoed_rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not vetoed_rows:
            return {"count": 0, "bad_rate": 0.0, "time_decay_count": 0, "net_pnl": 0.0}
        return {
            "count": len(vetoed_rows),
            "bad_rate": round((sum(1 for row in vetoed_rows if row["bad_entry_quality"]) / len(vetoed_rows)) * 100, 2),
            "time_decay_count": sum(1 for row in vetoed_rows if row["time_decay_failure"]),
            "net_pnl": round(sum(row["net_pnl"] for row in vetoed_rows), 2),
        }

    @staticmethod
    def _hybrid_verdict(
        parent_metrics: dict[str, Any],
        hybrid_metrics: dict[str, Any],
        vetoed_count: int,
        total_count: int,
    ) -> str:
        retained_ratio = hybrid_metrics["total_trades"] / total_count if total_count else 0.0
        if retained_ratio < 0.70:
            return "rejected_low_activity"
        if hybrid_metrics["net_pnl"] < parent_metrics["net_pnl"] and hybrid_metrics["profit_factor"] <= parent_metrics["profit_factor"]:
            return "rejected_no_edge"
        if hybrid_metrics["max_equity_drawdown_pct"] > parent_metrics["max_equity_drawdown_pct"] + 0.5:
            return "rejected_drawdown"
        if vetoed_count <= 0:
            return "rejected_no_veto"
        if hybrid_metrics["profit_factor"] > parent_metrics["profit_factor"] or hybrid_metrics["net_pnl"] > parent_metrics["net_pnl"]:
            return "hybrid_candidate"
        return "research_survivor"

    def _hybrid_report(self, payload: dict[str, Any]) -> str:
        parent = payload["parent_metrics"]
        hybrid = payload["hybrid_metrics"]
        comparison = payload["comparison"]
        vetoed = payload["vetoed_summary"]
        return "\n".join(
            [
                f"# Hybrid Entry-Quality Experiment {payload['experiment_id']}",
                "",
                f"- Parent run: `{payload['parent_run_id']}`",
                f"- Dataset: `{payload['dataset_id']}`",
                f"- Mode: `{payload['mode']}`",
                f"- Verdict: `{payload['verdict']}`",
                f"- Veto fraction: `{payload['veto_fraction']}`",
                "",
                "## Parent vs Hybrid",
                "",
                "| Metric | Parent | Hybrid | Delta |",
                "|---|---:|---:|---:|",
                f"| Net PnL | {parent['net_pnl']} | {hybrid['net_pnl']} | {comparison['net_pnl_delta']} |",
                f"| Profit Factor | {parent['profit_factor']} | {hybrid['profit_factor']} | {comparison['profit_factor_delta']} |",
                f"| Max Drawdown % | {parent['max_equity_drawdown_pct']} | {hybrid['max_equity_drawdown_pct']} | {comparison['drawdown_pct_delta']} |",
                f"| Trades | {parent['total_trades']} | {hybrid['total_trades']} | {comparison['trade_count_delta']} |",
                "",
                "## Vetoed Trades",
                "",
                f"- Vetoed count: `{vetoed['count']}`",
                f"- Vetoed bad-label rate: `{vetoed['bad_rate']}%`",
                f"- Vetoed time-decay count: `{vetoed['time_decay_count']}`",
                f"- Vetoed net PnL: `{vetoed['net_pnl']}`",
                "",
                "## Model",
                "",
                f"- Family: `{payload['model']['family']}`",
                f"- Target: `{payload['model']['target']}`",
                f"- Trained rows: `{payload['model']['trained_rows']}`",
                f"- Train bad rows: `{payload['model']['train_bad_rows']}`",
                "",
                "## Interpretation",
                "",
                "This is an offline first hybrid experiment. It tests whether decision-time entry features can identify low-quality trades before entry. It does not yet mutate the live backtest engine, so a survivor here should become a live hybrid veto parameter set before promotion.",
            ]
        )

    def _hybrid_time_decay_report(self, payload: dict[str, Any]) -> str:
        parent = payload["parent_metrics"]
        hybrid = payload["hybrid_metrics"]
        comparison = payload["comparison"]
        summary = payload["triage_summary"]
        return "\n".join(
            [
                f"# Hybrid Time-Decay Triage Experiment {payload['experiment_id']}",
                "",
                f"- Parent run: `{payload['parent_run_id']}`",
                f"- Dataset: `{payload['dataset_id']}`",
                f"- Mode: `{payload['mode']}`",
                f"- Verdict: `{payload['verdict']}`",
                f"- Exit fraction: `{payload['exit_fraction']}`",
                "",
                "## Parent vs Hybrid",
                "",
                "| Metric | Parent | Hybrid | Delta |",
                "|---|---:|---:|---:|",
                f"| Net PnL | {parent['net_pnl']} | {hybrid['net_pnl']} | {comparison['net_pnl_delta']} |",
                f"| Profit Factor | {parent['profit_factor']} | {hybrid['profit_factor']} | {comparison['profit_factor_delta']} |",
                f"| Max Drawdown % | {parent['max_equity_drawdown_pct']} | {hybrid['max_equity_drawdown_pct']} | {comparison['drawdown_pct_delta']} |",
                f"| Trades | {parent['total_trades']} | {hybrid['total_trades']} | {comparison['trade_count_delta']} |",
                "",
                "## Early Exit Triage",
                "",
                f"- Early exit count: `{summary['early_exit_count']}`",
                f"- Early-exit bad-label rate: `{summary['bad_rate']}%`",
                f"- Original time-decay count in early exits: `{summary['time_decay_count']}`",
                f"- Original net PnL of early-exited trades: `{summary['original_net_pnl']}`",
                f"- Average checkpoint: `{summary['avg_checkpoint']}`",
                "",
                "## Model",
                "",
                f"- Family: `{payload['model']['family']}`",
                f"- Target: `{payload['model']['target']}`",
                f"- Trained rows: `{payload['model']['trained_rows']}`",
                f"- Train bad rows: `{payload['model']['train_bad_rows']}`",
                "",
                "## Interpretation",
                "",
                "This offline hybrid experiment tests whether in-trade snapshots can identify trades that should be cut before the parent time-decay exit. A survivor here should become a live hybrid early-exit parameter set before promotion.",
            ]
        )

    def _comparison(self, parent_version_id: str | None, dataset_id: str, child_metrics: dict[str, Any]) -> dict[str, Any] | None:
        if not parent_version_id:
            return None
        parent_runs = [run for run in self.repo.list_runs() if run["version_id"] == parent_version_id and run["dataset_id"] == dataset_id]
        if not parent_runs:
            return None
        parent_metrics = parent_runs[0]["metrics_json"]
        return {
            "parent_version_id": parent_version_id,
            "profit_factor_delta": round(child_metrics["profit_factor"] - parent_metrics["profit_factor"], 4),
            "net_pnl_delta": round(child_metrics["net_pnl"] - parent_metrics["net_pnl"], 2),
            "drawdown_pct_delta": round(child_metrics["max_equity_drawdown_pct"] - parent_metrics["max_equity_drawdown_pct"], 2),
            "trade_count_delta": child_metrics["total_trades"] - parent_metrics["total_trades"],
        }

    @staticmethod
    def _trade_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
        if not trades:
            return {
                "trades": 0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_bars": 0.0,
                "avg_mfe_r": None,
                "avg_mae_r": None,
            }
        wins = [trade for trade in trades if trade["net_pnl"] > 0]
        losses = [trade for trade in trades if trade["net_pnl"] < 0]
        gross_profit = sum(trade["net_pnl"] for trade in wins)
        gross_loss = abs(sum(trade["net_pnl"] for trade in losses))
        mfe_values = [trade["mfe_r"] for trade in trades if "mfe_r" in trade]
        mae_values = [trade["mae_r"] for trade in trades if "mae_r" in trade]
        return {
            "trades": len(trades),
            "net_pnl": round(sum(trade["net_pnl"] for trade in trades), 2),
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else round(gross_profit, 4),
            "win_rate": round((len(wins) / len(trades)) * 100, 2),
            "avg_win": round(gross_profit / len(wins), 2) if wins else 0.0,
            "avg_loss": round(sum(trade["net_pnl"] for trade in losses) / len(losses), 2) if losses else 0.0,
            "avg_bars": round(sum(trade["bars_held"] for trade in trades) / len(trades), 2),
            "avg_mfe_r": round(sum(mfe_values) / len(mfe_values), 4) if mfe_values else None,
            "avg_mae_r": round(sum(mae_values) / len(mae_values), 4) if mae_values else None,
        }

    @staticmethod
    def _quantile(values: list[float], ratio: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        return ordered[int((len(ordered) - 1) * ratio)]

    def _stats_table(self, grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
        lines = [
            "| Segment | Trades | Net PnL | PF | Win Rate | Avg Win | Avg Loss | Avg Bars |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for label, trades in grouped.items():
            stats = self._trade_stats(trades)
            lines.append(
                f"| {label} | {stats['trades']} | {stats['net_pnl']} | {stats['profit_factor']} | "
                f"{stats['win_rate']}% | {stats['avg_win']} | {stats['avg_loss']} | {stats['avg_bars']} |"
            )
        return lines

    @staticmethod
    def _read_path(payload: dict[str, Any], path: str) -> Any:
        cursor: Any = payload
        for step in path.split("."):
            cursor = cursor[step]
        return cursor

    @staticmethod
    def _value_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, list):
            return "list"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "enum"

    def _candidate_values(self, edge: dict[str, Any]) -> list[Any]:
        current = edge["current_value"]
        alternatives = list(edge.get("alternatives", []))
        if edge.get("search_mode") == "values_only":
            return self._dedupe_values([current, *alternatives])
        if edge.get("search_mode") == "range":
            return self._range_candidate_values(edge, alternatives)
        if isinstance(current, bool):
            return [True, False]
        if isinstance(current, list):
            return self._dedupe_values([current, *alternatives])
        if edge["value_type"] == "enum":
            values = [current, *alternatives]
            return self._dedupe_values(values)
        numeric_alternatives = [item for item in alternatives if isinstance(item, (int, float)) and not isinstance(item, bool)]
        if isinstance(current, int) and not isinstance(current, bool):
            lower, upper = self._integer_search_bounds(edge, numeric_alternatives)
            candidates = set(range(lower, upper + 1))
            candidates.update(int(value) for value in numeric_alternatives)
            candidates.add(int(current))
            return sorted(value for value in candidates if lower <= value <= upper)
        if isinstance(current, float):
            lower, upper, step = self._float_search_bounds(edge, numeric_alternatives)
            candidates = {round(lower + (index * step), 4) for index in range(int(round((upper - lower) / step)) + 1)}
            candidates.update(round(float(value), 4) for value in numeric_alternatives)
            candidates.add(round(float(current), 4))
            return sorted(value for value in candidates if lower <= value <= upper)
        return self._dedupe_values([current, *alternatives])

    def _range_candidate_values(self, edge: dict[str, Any], alternatives: list[Any]) -> list[Any]:
        current = edge["current_value"]
        lower = edge.get("search_min")
        upper = edge.get("search_max")
        step = edge.get("search_step")
        if lower is None or upper is None or step in (None, 0):
            raise HTTPException(status_code=400, detail=f"Incomplete range search config for {edge['lever']}.")
        if isinstance(current, int) and not isinstance(current, bool):
            start = int(lower)
            stop = int(upper)
            increment = int(step)
            values = set(range(start, stop + 1, increment))
            values.add(int(current))
            values.update(int(value) for value in alternatives if isinstance(value, (int, float)) and not isinstance(value, bool))
            return sorted(value for value in values if start <= value <= stop)
        if isinstance(current, float):
            start = float(lower)
            stop = float(upper)
            increment = float(step)
            count = int(round((stop - start) / increment))
            values = {round(start + (index * increment), 4) for index in range(count + 1)}
            values.add(round(float(current), 4))
            values.update(round(float(value), 4) for value in alternatives if isinstance(value, (int, float)) and not isinstance(value, bool))
            return sorted(value for value in values if start <= value <= stop)
        return self._dedupe_values([current, *alternatives])

    @staticmethod
    def _integer_search_bounds(edge: dict[str, Any], alternatives: list[int | float]) -> tuple[int, int]:
        current = int(edge["current_value"])
        lever = edge["lever"]
        if any(token in lever for token in ("len", "lookback", "window", "period")):
            return 1, max(LENGTH_OPTIMIZATION_MAX, current, *(int(value) for value in alternatives))
        if lever == "max_no_cross":
            return 0, max(MAX_NO_CROSS_OPTIMIZATION_MAX, current, *(int(value) for value in alternatives))
        upper = max(current * 5, current + 50, *(int(value) for value in alternatives), 10)
        return 0, upper

    @staticmethod
    def _float_search_bounds(edge: dict[str, Any], alternatives: list[int | float]) -> tuple[float, float, float]:
        current = float(edge["current_value"])
        lever = edge["lever"]
        if "mult" in lever:
            lower = 0.1
            upper = max(10.0, current * 3, *(float(value) for value in alternatives))
            return lower, upper, 0.1
        lower = max(0.0001, round(current * 0.1, 4))
        upper = max(current * 5, *(float(value) for value in alternatives), current + 1.0)
        step = max(round((upper - lower) / FLOAT_OPTIMIZATION_MAX_CANDIDATES, 4), 0.0001)
        return lower, upper, step

    def _search_summary(self, edge: dict[str, Any], values: list[Any]) -> dict[str, Any]:
        if not values:
            return {"type": edge["value_type"], "candidate_count": 0}
        return {
            "type": edge["value_type"],
            "candidate_count": len(values),
            "min": min(values) if edge["value_type"] in {"int", "float"} else None,
            "max": max(values) if edge["value_type"] in {"int", "float"} else None,
            "exhaustive": edge["value_type"] in {"int", "bool", "enum"},
        }

    @staticmethod
    def _dedupe_values(values: list[Any]) -> list[Any]:
        output: list[Any] = []
        seen: set[str] = set()
        for value in values:
            key = json.dumps(value, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            output.append(value)
        return output

    @staticmethod
    def _optimization_eligible(spec: dict[str, Any], metrics: dict[str, Any]) -> bool:
        return not MutationLabService._core_gate_failures(spec, metrics) and not MutationLabService._portfolio_gate_failures(
            spec, metrics
        )

    @staticmethod
    def _optimization_score(spec: dict[str, Any], metrics: dict[str, Any]) -> float:
        return MutationLabService._optimization_score_components(spec, metrics)["score"]

    @staticmethod
    def _optimization_score_components(spec: dict[str, Any], metrics: dict[str, Any]) -> dict[str, float]:
        rules = spec.get("evaluation", {})
        minimum_trades = max(1, int(rules.get("minimum_trades", 1)))
        maximum_drawdown = max(0.01, float(rules.get("maximum_drawdown_pct", 100)))
        minimum_profit_factor = float(rules.get("minimum_profit_factor", 1.0))
        minimum_net_pnl = float(rules.get("minimum_net_pnl", 0.0))
        trade_ratio = float(metrics["total_trades"]) / minimum_trades
        trade_evidence_score = min(trade_ratio, 2.5) * 120.0
        low_trade_penalty = ((1.0 - min(trade_ratio, 1.0)) ** 2) * 2400.0
        drawdown_ratio = metrics["max_equity_drawdown_pct"] / maximum_drawdown
        drawdown_penalty = metrics["max_equity_drawdown_pct"] * 10.0
        drawdown_breach_penalty = max(0.0, drawdown_ratio - 1.0) * 600.0
        profit_factor_score = min(metrics["profit_factor"], 3.0) * 40.0
        profit_factor_penalty = 0.0
        if metrics["profit_factor"] < minimum_profit_factor:
            profit_factor_penalty = (minimum_profit_factor - metrics["profit_factor"]) * 220.0
        negative_pnl_penalty = 600.0 if metrics["net_pnl"] <= minimum_net_pnl else 0.0
        return_score = metrics["return_pct"] * 4.0
        alpha_score = metrics.get("outperformance_pct", 0.0) * 3.0
        calmar_score = metrics.get("calmar", 0.0) * 45.0
        benchmark_efficiency_score = metrics.get("calmar_delta", 0.0) * 30.0
        daily_sharpe_score = metrics.get("daily_sharpe", 0.0) * 80.0
        worst_daily_loss_penalty = abs(min(metrics.get("worst_daily_return_pct", 0.0), 0.0)) * 30.0
        win_rate_score = metrics["percent_profitable"] * 0.3
        payoff_score = max(min(metrics["expected_payoff"], 1000.0), -1000.0) * 0.12
        score = (
            profit_factor_score
            + trade_evidence_score
            + return_score
            + alpha_score
            + calmar_score
            + benchmark_efficiency_score
            + daily_sharpe_score
            + win_rate_score
            + payoff_score
            - drawdown_penalty
            - drawdown_breach_penalty
            - low_trade_penalty
            - profit_factor_penalty
            - negative_pnl_penalty
            - worst_daily_loss_penalty
        )
        return {
            "score": round(score, 4),
            "minimum_trades": float(minimum_trades),
            "trade_ratio": round(trade_ratio, 4),
            "profit_factor_score": round(profit_factor_score, 4),
            "trade_evidence_score": round(trade_evidence_score, 4),
            "return_score": round(return_score, 4),
            "alpha_score": round(alpha_score, 4),
            "calmar_score": round(calmar_score, 4),
            "benchmark_efficiency_score": round(benchmark_efficiency_score, 4),
            "daily_sharpe_score": round(daily_sharpe_score, 4),
            "win_rate_score": round(win_rate_score, 4),
            "payoff_score": round(payoff_score, 4),
            "drawdown_penalty": round(drawdown_penalty, 4),
            "drawdown_breach_penalty": round(drawdown_breach_penalty, 4),
            "low_trade_penalty": round(low_trade_penalty, 4),
            "profit_factor_penalty": round(profit_factor_penalty, 4),
            "negative_pnl_penalty": round(negative_pnl_penalty, 4),
            "worst_daily_loss_penalty": round(worst_daily_loss_penalty, 4),
        }

    def _apply_parameter_overrides(self, spec: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        tuned_spec = json.loads(json.dumps(spec))
        parameters = tuned_spec.setdefault("parameters", {})
        for key, value in overrides.items():
            if key not in parameters:
                raise HTTPException(status_code=400, detail=f"Unknown parameter override: {key}")
            current_value = parameters[key]
            if isinstance(current_value, bool):
                parameters[key] = bool(value)
            elif isinstance(current_value, list):
                parameters[key] = value if isinstance(value, list) else json.loads(value)
            elif isinstance(current_value, int) and not isinstance(current_value, bool):
                parameters[key] = int(value)
            elif isinstance(current_value, float):
                parameters[key] = float(value)
            else:
                parameters[key] = value
        return tuned_spec

    @staticmethod
    def _summarize_overrides(overrides: dict[str, Any]) -> str:
        items = [f"{key}={value}" for key, value in sorted(overrides.items())]
        return ", ".join(items[:4]) + ("..." if len(items) > 4 else "")

    @staticmethod
    def _core_gate_failures(spec: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
        rules = spec.get("evaluation", {})
        failures: list[str] = []
        checks = [
            (metrics["total_trades"] >= rules.get("minimum_trades", 0), "insufficient_trades"),
            (metrics["profit_factor"] >= rules.get("minimum_profit_factor", 0), "low_profit_factor"),
            (metrics["max_equity_drawdown_pct"] <= rules.get("maximum_drawdown_pct", 100), "excess_drawdown"),
            (metrics["net_pnl"] > rules.get("minimum_net_pnl", float("-inf")), "non_positive_net_pnl"),
            (metrics.get("sharpe", 0.0) >= rules.get("minimum_sharpe", float("-inf")), "low_sharpe"),
            (metrics.get("sortino", 0.0) >= rules.get("minimum_sortino", float("-inf")), "low_sortino"),
            (
                metrics.get("daily_sharpe", 0.0) >= rules.get("minimum_daily_sharpe", float("-inf")),
                "low_daily_sharpe",
            ),
            (
                metrics.get("daily_sortino", 0.0) >= rules.get("minimum_daily_sortino", float("-inf")),
                "low_daily_sortino",
            ),
            (metrics.get("calmar", 0.0) >= rules.get("minimum_calmar", float("-inf")), "low_calmar"),
            (
                metrics.get("max_initial_risk_pct", 0.0) <= rules.get("maximum_initial_risk_pct", 100.0),
                "excess_trade_risk",
            ),
            (
                metrics.get("max_entry_exposure_pct", 0.0) <= rules.get("maximum_entry_exposure_pct", 100.0),
                "excess_max_exposure",
            ),
            (
                metrics.get("avg_entry_exposure_pct", 0.0) <= rules.get("maximum_avg_exposure_pct", 100.0),
                "excess_avg_exposure",
            ),
            (
                abs(metrics.get("worst_daily_return_pct", 0.0)) <= rules.get("maximum_worst_daily_loss_pct", 100.0),
                "excess_worst_daily_loss",
            ),
        ]
        for passed, reason in checks:
            if not passed:
                failures.append(reason)
        return failures

    @staticmethod
    def _portfolio_gate_failures(spec: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
        rules = spec.get("evaluation", {})
        parameters = spec.get("parameters", {})
        failures: list[str] = []
        allowed_modes = set(rules.get("production_sizing_modes", ["fixed_notional_pct", "fixed_risk_pct"]))
        if parameters.get("sizing_mode", "fixed_quantity") not in allowed_modes:
            failures.append("diagnostic_capital_model")
        policy = rules.get("benchmark_policy", "outperform_return_or_calmar")
        if policy == "outperform_return_or_calmar":
            beats_return = metrics.get("outperformance_pct", 0.0) > 0
            beats_efficiency = metrics.get("calmar_delta", 0.0) > 0
            if not beats_return and not beats_efficiency:
                failures.append("weak_vs_buy_hold_benchmark")
        return failures

    def _verdict(self, spec: dict[str, Any], metrics: dict[str, Any], comparison: dict[str, Any] | None) -> str:
        if self._core_gate_failures(spec, metrics):
            return "graveyard"
        if self._portfolio_gate_failures(spec, metrics):
            return "research_survivor"
        if comparison and comparison["profit_factor_delta"] > 0 and comparison["drawdown_pct_delta"] <= 0.5:
            return "promotion_candidate"
        if metrics.get("outperformance_pct", 0.0) > 0 or metrics.get("calmar_delta", 0.0) > 0:
            return "promotion_candidate"
        return "research_survivor"

    @staticmethod
    def _capital_model_warnings(spec: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
        parameters = spec.get("parameters", {})
        warnings: list[str] = []
        mode = parameters.get("sizing_mode", "fixed_quantity")
        if mode == "fixed_notional_pct":
            notional_pct = float(parameters.get("notional_pct", 1.0))
            warnings.append(
                f"fixed_notional_pct compounds position size from current equity; `{notional_pct}` means "
                f"`{round(notional_pct * 100, 4)}%` of current equity is deployed as notional on every new trade."
            )
            if notional_pct >= 1.0:
                warnings.append(
                    "This is an all-in 1x compounding assumption. It can produce mechanically huge returns in a long "
                    "multi-year backtest, but it should be treated as an aggressive upper-bound scenario rather than a "
                    "production default."
                )
        if mode == "fixed_risk_pct":
            risk_pct = float(parameters.get("risk_pct", 0.0))
            warnings.append(
                f"fixed_risk_pct sizes each trade by stop distance; `{risk_pct}` means "
                f"`{round(risk_pct * 100, 4)}%` of current equity is the intended loss budget before leverage caps."
            )
        max_risk = float(metrics.get("max_initial_risk_pct", 0.0))
        if max_risk > 10.0:
            warnings.append(
                f"Max initial risk reached `{round(max_risk, 4)}%` of equity on at least one trade. "
                "A black-box/quant promotion review should treat this as a tail-risk flag even if headline drawdown looks acceptable."
            )
        return warnings

    def _run_report(self, version: dict[str, Any], payload: dict[str, Any]) -> str:
        metrics = payload["metrics"]
        comparison = payload["comparison"]
        capital_warnings = self._capital_model_warnings(payload["spec"], metrics)
        core_failures = self._core_gate_failures(payload["spec"], metrics)
        portfolio_failures = self._portfolio_gate_failures(payload["spec"], metrics)
        parameters = payload["spec"].get("parameters", {})
        rules = payload["spec"].get("evaluation", {})
        trades = payload["trades"]
        win_loss_ratio = metrics.get("ratio_avg_win_loss", 0.0)
        breakeven_win_rate = round(100 / (1 + win_loss_ratio), 2) if win_loss_ratio else 0.0
        by_side = {
            "long": [trade for trade in trades if trade["direction"] == "long"],
            "short": [trade for trade in trades if trade["direction"] == "short"],
        }
        exit_reasons = sorted({trade["reason"] for trade in trades})
        by_exit = {reason: [trade for trade in trades if trade["reason"] == reason] for reason in exit_reasons}
        years = sorted({trade["exit_ts"][:4] for trade in trades})
        by_year = {year: [trade for trade in trades if trade["exit_ts"].startswith(year)] for year in years}
        durations = [float(trade["bars_held"]) for trade in trades]
        has_excursion = any("mfe_r" in trade for trade in trades)
        lines = [
            f"# Mutation Lab Run {payload['run_id']}",
            "",
            f"- Family: `{version['family_id']}`",
            f"- Version: `{version['name']}`",
            f"- Stage: `{version['stage']}`",
            f"- Verdict: `{payload['verdict']}`",
            f"- Dataset: `{payload['dataset_id']}`",
            "",
            "## Frozen Strategy Contract",
            "",
            f"This run freezes `{payload['spec'].get('engine_id', 'unknown')}` on `{payload['spec'].get('asset', 'unknown')}` "
            f"at `{payload['spec'].get('venue', 'unknown')}` / `{payload['spec'].get('timeframe', 'unknown')}`. "
            f"The live parameters are `{json.dumps(parameters, sort_keys=True)}`.",
            "",
            "## Metrics",
            "",
            f"- Net PnL: `{metrics['net_pnl']}`",
            f"- Return %: `{metrics['return_pct']}`",
            f"- Profit Factor: `{metrics['profit_factor']}`",
            f"- Max Drawdown %: `{metrics['max_equity_drawdown_pct']}`",
            f"- Expected Payoff: `{metrics['expected_payoff']}`",
            f"- Total Trades: `{metrics['total_trades']}`",
            f"- Win Rate %: `{metrics['percent_profitable']}`",
            f"- Avg Win / Avg Loss Ratio: `{metrics['ratio_avg_win_loss']}`",
            f"- Approx Breakeven Win Rate: `{breakeven_win_rate}`",
            f"- Trade-Level Sharpe: `{metrics.get('sharpe', 0.0)}`",
            f"- Trade-Level Sortino: `{metrics.get('sortino', 0.0)}`",
            f"- Daily Portfolio Sharpe: `{metrics.get('daily_sharpe', 0.0)}`",
            f"- Daily Portfolio Sortino: `{metrics.get('daily_sortino', 0.0)}`",
            f"- Daily Volatility %: `{metrics.get('daily_volatility_pct', 0.0)}`",
            f"- Worst Daily Return %: `{metrics.get('worst_daily_return_pct', 0.0)}`",
            f"- Positive Day %: `{metrics.get('positive_day_pct', 0.0)}`",
            f"- Calmar: `{metrics.get('calmar', 0.0)}`",
            f"- Sizing Mode: `{parameters.get('sizing_mode', 'fixed_quantity')}`",
            f"- Avg Entry Exposure %: `{metrics.get('avg_entry_exposure_pct', 0.0)}`",
            f"- Max Entry Exposure %: `{metrics.get('max_entry_exposure_pct', 0.0)}`",
            f"- Avg Initial Risk %: `{metrics.get('avg_initial_risk_pct', 0.0)}`",
            f"- Max Initial Risk %: `{metrics.get('max_initial_risk_pct', 0.0)}`",
            f"- Buy & Hold Net PnL: `{metrics.get('buy_hold_return', 0.0)}`",
            f"- Buy & Hold Asset Return %: `{metrics.get('buy_hold_return_pct', 0.0)}`",
            f"- Buy & Hold Max Drawdown %: `{metrics.get('buy_hold_max_drawdown_pct', 0.0)}`",
            f"- Buy & Hold Calmar: `{metrics.get('buy_hold_calmar', 0.0)}`",
            f"- Buy & Hold Start/End: `{metrics.get('buy_hold_start_price', 0.0)}` -> `{metrics.get('buy_hold_end_price', 0.0)}`",
            f"- Outperformance %: `{metrics.get('outperformance_pct', 0.0)}`",
            f"- Calmar Delta: `{metrics.get('calmar_delta', 0.0)}`",
            "",
            "## Performance Interpretation",
            "",
            "This report separates the headline result from the mechanics that created it. A low win rate is not automatically a defect when the average win/loss ratio is high; the important question is whether the strategy preserves enough right-tail winners while reducing avoidable churn, weak sides, poor regimes, or expensive stop exits. Use the diagnostics below to decide the next full-whitebox mutation instead of guessing from the headline metrics alone.",
            "",
        ]
        lines.extend(
            [
                "## Production Gate",
                "",
                f"- Core failures: `{core_failures or []}`",
                f"- Portfolio / benchmark failures: `{portfolio_failures or []}`",
                f"- Production sizing modes: `{rules.get('production_sizing_modes', [])}`",
                f"- Benchmark policy: `{rules.get('benchmark_policy', 'outperform_return_or_calmar')}`",
                "",
                "The platform-level rule is deliberately generic: first prove the strategy has enough activity, positive expectancy, bounded drawdown, acceptable daily portfolio Sharpe/Sortino/Calmar, bounded daily loss, and bounded per-trade risk; then judge it under a portfolio sizing model against buy-and-hold. Trade-level Sharpe/Sortino are diagnostic only and may overstate deployable portfolio quality. A strategy does not need to beat buy-and-hold on raw return if it delivers better drawdown-adjusted efficiency, but if it loses on both raw return and Calmar it is not production-comparable yet.",
                "",
            ]
        )
        if capital_warnings:
            lines.extend(["## Capital Model Warning", ""])
            lines.extend([f"- {warning}" for warning in capital_warnings])
            lines.append("")
        if comparison:
            lines.extend(
                [
                    "## Parent Comparison",
                    "",
                    f"- Profit Factor Delta: `{comparison['profit_factor_delta']}`",
                    f"- Net PnL Delta: `{comparison['net_pnl_delta']}`",
                    f"- Drawdown % Delta: `{comparison['drawdown_pct_delta']}`",
                    f"- Trade Count Delta: `{comparison['trade_count_delta']}`",
                    "",
                ]
            )
        if version.get("mutation_json", {}).get("summary"):
            lines.extend(
                [
                    "## Single Mutation",
                    "",
                    f"- Summary: `{version['mutation_json']['summary']}`",
                    f"- Rationale: {version['mutation_json'].get('rationale', '')}",
                    "",
                ]
            )
        lines.extend(
            [
                "## Diagnostics",
                "",
                f"- Entries: `{payload['diagnostics']['entries']}`",
                f"- Long signals: `{payload['diagnostics']['signals_long']}`",
                f"- Short signals: `{payload['diagnostics']['signals_short']}`",
                f"- Short quality gate blocks: `{payload['diagnostics'].get('short_quality_gate_blocks', 0)}`",
                f"- Breakeven stop moves: `{payload['diagnostics'].get('breakeven_stop_moves', 0)}`",
                f"- Time risk filter blocks: `{payload['diagnostics'].get('time_risk_filter_blocks', 0)}`",
                f"- Stop exits: `{payload['diagnostics']['stop_exits']}`",
                f"- Reverse exits: `{payload['diagnostics']['reverse_exits']}`",
                f"- Time-decay exits: `{payload['diagnostics'].get('time_decay_exits', 0)}`",
                f"- Time exits: `{payload['diagnostics']['time_exits']}`",
                "",
                "## Side Decomposition",
                "",
                *self._stats_table(by_side),
                "",
                "## Exit-Reason Decomposition",
                "",
                *self._stats_table(by_exit),
                "",
                "## Period Decomposition",
                "",
                *self._stats_table(by_year),
                "",
                "## Trade Duration",
                "",
                f"- 25th percentile bars held: `{self._quantile(durations, 0.25)}`",
                f"- Median bars held: `{self._quantile(durations, 0.50)}`",
                f"- 75th percentile bars held: `{self._quantile(durations, 0.75)}`",
                f"- 90th percentile bars held: `{self._quantile(durations, 0.90)}`",
                f"- 95th percentile bars held: `{self._quantile(durations, 0.95)}`",
            ]
        )
        if has_excursion:
            all_stats = self._trade_stats(trades)
            lines.extend(
                [
                    "",
                    "## Excursion Diagnostics",
                    "",
                    f"- Average MFE/R: `{all_stats['avg_mfe_r']}`",
                    f"- Average MAE/R: `{all_stats['avg_mae_r']}`",
                    "",
                    "MFE/R and MAE/R are decision-time diagnostic fields for full-whitebox research. They help identify whether losses had enough favorable movement for breakeven or trailing-stop logic, and whether winners required wide adverse movement that a tighter stop would have destroyed.",
                ]
            )
        lines.extend(
            [
                "",
                "## Full-Whitebox Diagnostic Queue",
                "",
                "Before testing a new rule mutation, inspect whether the weakness is side-specific, exit-specific, period-specific, duration-specific, or excursion-specific. Good next mutations should attack one localized defect while preserving the parent contract and the right-tail behavior that funds the strategy.",
            ]
        )
        return "\n".join(lines)
