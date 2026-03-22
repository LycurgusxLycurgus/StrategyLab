from __future__ import annotations

import json
import uuid
from itertools import product
from pathlib import Path

from app.features.backtests.engine import run_a_zero, run_smart_money
from app.features.backtests.schema import BacktestRunRequest, BacktestSummary, FamilySweepRequest, FamilySweepSummary
from app.features.evaluations.service import EvaluationService
from app.features.strategies.service import StrategyService
from app.infra.config import AppConfig
from app.infra.db import Database
from app.infra.logging import get_logger
from app.shared.errors import AppError


FEE_PER_SIDE = 0.0005
SLIPPAGE_BY_TIMEFRAME = {"5m": 0.0004, "1H": 0.0002, "4H": 0.0002}


class BacktestService:
    def __init__(
        self,
        config: AppConfig,
        db: Database,
        strategy_service: StrategyService,
        data_service,
        evaluation_service: EvaluationService,
    ):
        self.config = config
        self.db = db
        self.strategy_service = strategy_service
        self.data_service = data_service
        self.evaluation_service = evaluation_service
        self.logger = get_logger("strategylab.backtests")

    def run_backtest(self, payload: BacktestRunRequest, persist: bool = True) -> BacktestSummary:
        manifest = self.strategy_service.get_family(payload.family_id)
        dataset = self.data_service.get_dataset(payload.dataset_id)
        supported_timeframes = manifest.supported_timeframes or [manifest.timeframe]
        if dataset.timeframe not in supported_timeframes:
            raise AppError(
                400,
                "TIMEFRAME_MISMATCH",
                "strategy family timeframe does not match dataset timeframe",
                {"supported_timeframes": supported_timeframes, "dataset_timeframe": dataset.timeframe},
            )
        parameters = {**manifest.parameters, **payload.parameter_overrides}
        candles = self.data_service.load_candles(dataset.dataset_id)
        minimum_bars = manifest.min_bars_by_timeframe.get(dataset.timeframe, 60)
        if len(candles) < minimum_bars:
            raise AppError(
                400,
                "DATASET_TOO_SHORT",
                "dataset does not have enough bars for this strategy and timeframe",
                {"required_bars": minimum_bars, "dataset_bars": len(candles), "timeframe": dataset.timeframe},
            )
        slippage = SLIPPAGE_BY_TIMEFRAME[dataset.timeframe]
        if manifest.family_id == "a_zero_srlc" or manifest.family_id.endswith("_a_zero"):
            engine_output = run_a_zero(candles, dataset.timeframe, parameters, manifest.risk, manifest.rules, FEE_PER_SIDE, slippage)
        else:
            engine_output = run_smart_money(candles, dataset.timeframe, parameters, manifest.risk, manifest.rules, FEE_PER_SIDE, slippage)
        evaluation = self.evaluation_service.evaluate(dataset.timeframe, engine_output["equity_curve"], engine_output["trades"])
        run_id = f"bt_{uuid.uuid4().hex[:12]}"
        artifact_path = self.config.app_run_dir / f"{run_id}.json"
        report_path = self._write_report(run_id, manifest.family_id, dataset.dataset_id, evaluation.model_dump()) if evaluation.verdict == "rejected" else None
        artifact_payload = {
            "run_id": run_id,
            "family_id": manifest.family_id,
            "dataset_id": dataset.dataset_id,
            "parameters": parameters,
            "metrics": evaluation.model_dump(),
            "trades": engine_output["trades"],
            "equity_curve": engine_output["equity_curve"],
            "diagnostics": engine_output.get("diagnostics", {}),
            "fee_per_side": FEE_PER_SIDE,
            "slippage": slippage,
            "same_bar_rule": "stop_first",
        }
        artifact_path.write_text(json.dumps(artifact_payload, indent=2, sort_keys=True), encoding="utf-8")
        summary = BacktestSummary(
            run_id=run_id,
            family_id=manifest.family_id,
            dataset_id=dataset.dataset_id,
            timeframe=dataset.timeframe,
            status="completed",
            verdict=evaluation.verdict,
            parameters=parameters,
            metrics=evaluation.model_dump(),
            artifact_path=str(artifact_path),
            report_path=str(report_path) if report_path else None,
        )
        if persist:
            self.db.execute(
                """
                insert into backtest_runs
                (run_id, family_id, dataset_id, timeframe, status, verdict, parameters_json, metrics_json, artifact_path, report_path)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    manifest.family_id,
                    dataset.dataset_id,
                    dataset.timeframe,
                    "completed",
                    evaluation.verdict,
                    json.dumps(parameters, sort_keys=True),
                    json.dumps(evaluation.model_dump(), sort_keys=True),
                    str(artifact_path),
                    str(report_path) if report_path else None,
                ),
            )
            if evaluation.verdict == "rejected" and report_path is not None:
                self.db.insert_artifact(
                    artifact_id=f"graveyard_{run_id}",
                    artifact_type="graveyard_report",
                    family_id=manifest.family_id,
                    dataset_id=dataset.dataset_id,
                    source_run_id=run_id,
                    path=str(report_path),
                    payload={"run_id": run_id, "verdict": evaluation.verdict, "metrics": evaluation.model_dump()},
                )
        self.logger.info(
            "backtest completed",
            extra={"extra_data": {"run_id": run_id, "family_id": manifest.family_id, "verdict": evaluation.verdict}},
        )
        return summary

    def list_runs(self) -> list[dict]:
        rows = self.db.fetch_all("select * from backtest_runs order by created_at desc")
        for row in rows:
            row["parameters"] = json.loads(row.pop("parameters_json"))
            row["metrics"] = json.loads(row.pop("metrics_json"))
        return rows

    def run_family_sweep(self, payload: FamilySweepRequest) -> FamilySweepSummary:
        manifest = self.strategy_service.get_family(payload.family_id)
        variants = self._parameter_variants(manifest)
        results: list[dict] = []
        rejected = 0
        research_survivors = 0
        paper_candidates = 0
        for overrides in variants:
            summary = self.run_backtest(
                BacktestRunRequest(
                    family_id=payload.family_id,
                    dataset_id=payload.dataset_id,
                    parameter_overrides=overrides,
                )
            )
            results.append(summary.model_dump())
            if summary.verdict == "paper_candidate":
                paper_candidates += 1
            elif summary.verdict == "research_survivor":
                research_survivors += 1
            else:
                rejected += 1
        results.sort(key=lambda item: item["metrics"]["out_of_sample"]["sharpe"], reverse=True)
        best = results[0] if results else None
        return FamilySweepSummary(
            family_id=payload.family_id,
            dataset_id=payload.dataset_id,
            total_variants=len(results),
            rejected=rejected,
            research_survivors=research_survivors,
            paper_candidates=paper_candidates,
            best_run_id=best["run_id"] if best else None,
            best_oos_sharpe=best["metrics"]["out_of_sample"]["sharpe"] if best else None,
            runs=results,
        )

    def get_run(self, run_id: str) -> dict:
        row = self.db.fetch_one("select * from backtest_runs where run_id = ?", (run_id,))
        if not row:
            raise AppError(404, "RUN_NOT_FOUND", "unknown backtest run", {"run_id": run_id})
        row["parameters"] = json.loads(row.pop("parameters_json"))
        row["metrics"] = json.loads(row.pop("metrics_json"))
        return row

    def rerun(self, run_id: str) -> BacktestSummary:
        row = self.get_run(run_id)
        manifest = self.strategy_service.get_family(row["family_id"])
        base_parameters = dict(manifest.parameters)
        parameter_overrides = {
            key: value
            for key, value in row["parameters"].items()
            if base_parameters.get(key) != value
        }
        return self.run_backtest(
            BacktestRunRequest(
                family_id=row["family_id"],
                dataset_id=row["dataset_id"],
                parameter_overrides=parameter_overrides,
            )
        )

    def delete_run(self, run_id: str) -> dict:
        row = self.db.fetch_one(
            "select run_id, artifact_path, report_path from backtest_runs where run_id = ?",
            (run_id,),
        )
        if not row:
            raise AppError(404, "RUN_NOT_FOUND", "unknown backtest run", {"run_id": run_id})
        self.db.delete_run_related(run_id)
        for path_value in [row["artifact_path"], row["report_path"]]:
            if not path_value:
                continue
            path = Path(path_value)
            if path.exists():
                path.unlink()
        return {"run_id": run_id, "deleted": True}

    @staticmethod
    def _parameter_variants(manifest) -> list[dict[str, float | int | bool | str]]:
        defaults = dict(manifest.parameters)
        grid = manifest.optimization_grid or {}
        if not grid:
            return [{}]
        keys = list(grid.keys())
        variants: list[dict[str, float | int | bool | str]] = []
        seen: set[str] = set()
        for combo in product(*[grid[key] for key in keys]):
            merged = dict(defaults)
            merged.update(dict(zip(keys, combo)))
            overrides = {key: value for key, value in merged.items() if defaults.get(key) != value}
            signature = json.dumps(merged, sort_keys=True)
            if signature in seen:
                continue
            seen.add(signature)
            variants.append(overrides)
        default_signature = json.dumps(defaults, sort_keys=True)
        if default_signature not in seen:
            variants.insert(0, {})
        return variants

    def _write_report(self, run_id: str, family_id: str, dataset_id: str, metrics: dict) -> Path:
        report_path = self.config.app_graveyard_dir / f"{run_id}.md"
        out_of_sample = metrics["out_of_sample"]
        body = "\n".join(
            [
                f"# Rejected Strategy Run {run_id}",
                "",
                f"- family: `{family_id}`",
                f"- dataset: `{dataset_id}`",
                f"- verdict: `rejected`",
                f"- oos sharpe: `{out_of_sample['sharpe']}`",
                f"- max drawdown: `{out_of_sample['max_drawdown']}`",
                f"- profit factor: `{out_of_sample['profit_factor']}`",
                f"- expectancy: `{out_of_sample['expectancy']}`",
                "",
                "This run failed the StrategyLab research gate and was preserved in the graveyard for later review.",
            ]
        )
        report_path.write_text(body + "\n", encoding="utf-8")
        return report_path
