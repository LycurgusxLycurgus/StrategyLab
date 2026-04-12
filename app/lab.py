from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.backtest import BacktestEngine, apply_patch_to_spec
from app.config import settings
from app.data import DataService
from app.storage import Repository


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
        {
            "kind": "hybrid",
            "lever": "quality_gate_placeholder",
            "path": "metadata.hybrid_placeholder",
            "values": ["score_parent_candidates_only"],
            "rationale": "Reserve the first cheap black-box mutation for later, only after the white-box parent survives broader history.",
        },
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
            current_version = self.repo.get_version(family["current_version_id"]) if family.get("current_version_id") else None
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
        current_version = self.repo.get_version(family["current_version_id"]) if family.get("current_version_id") else None
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

    def list_tuning_edges(self, version_id: str, include_hybrid: bool = False) -> list[dict[str, Any]]:
        version = self.repo.get_version(version_id)
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
        version = self.repo.get_version(version_id)
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
            if mutation["kind"] == "hybrid" and not include_hybrid:
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
        version = self.repo.get_version(version_id)
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
        version = self.repo.get_version(version_id)
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

    def save_tuned_version(
        self,
        version_id: str,
        dataset_id: str,
        parameter_overrides: dict[str, Any],
        name: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        parent = self.repo.get_version(version_id)
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
        parent = self.repo.get_version(proposal["parent_version_id"])
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
    def _read_path(payload: dict[str, Any], path: str) -> Any:
        cursor: Any = payload
        for step in path.split("."):
            cursor = cursor[step]
        return cursor

    @staticmethod
    def _value_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "enum"

    def _apply_parameter_overrides(self, spec: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        tuned_spec = json.loads(json.dumps(spec))
        parameters = tuned_spec.setdefault("parameters", {})
        for key, value in overrides.items():
            if key not in parameters:
                raise HTTPException(status_code=400, detail=f"Unknown parameter override: {key}")
            current_value = parameters[key]
            if isinstance(current_value, bool):
                parameters[key] = bool(value)
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

    def _verdict(self, spec: dict[str, Any], metrics: dict[str, Any], comparison: dict[str, Any] | None) -> str:
        rules = spec.get("evaluation", {})
        if (
            metrics["total_trades"] < rules.get("minimum_trades", 0)
            or metrics["profit_factor"] < rules.get("minimum_profit_factor", 0)
            or metrics["max_equity_drawdown_pct"] > rules.get("maximum_drawdown_pct", 100)
            or metrics["net_pnl"] <= rules.get("minimum_net_pnl", float("-inf"))
        ):
            return "graveyard"
        if comparison and comparison["profit_factor_delta"] > 0 and comparison["drawdown_pct_delta"] <= 0.5:
            return "promotion_candidate"
        return "research_survivor"

    def _run_report(self, version: dict[str, Any], payload: dict[str, Any]) -> str:
        metrics = payload["metrics"]
        comparison = payload["comparison"]
        lines = [
            f"# Mutation Lab Run {payload['run_id']}",
            "",
            f"- Family: `{version['family_id']}`",
            f"- Version: `{version['name']}`",
            f"- Stage: `{version['stage']}`",
            f"- Verdict: `{payload['verdict']}`",
            f"- Dataset: `{payload['dataset_id']}`",
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
            "",
        ]
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
                f"- Stop exits: `{payload['diagnostics']['stop_exits']}`",
                f"- Reverse exits: `{payload['diagnostics']['reverse_exits']}`",
                f"- Time exits: `{payload['diagnostics']['time_exits']}`",
            ]
        )
        return "\n".join(lines)
