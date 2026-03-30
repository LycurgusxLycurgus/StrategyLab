from __future__ import annotations

import json
import pickle
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sklearn.ensemble import GradientBoostingClassifier

from app.config import settings
from app.domain import Trade
from app.features.backtests.engine import WhiteBoxEngine, compute_metrics
from app.features.data.service import DataService
from app.features.reports.service import ReportService
from app.features.strategies.service import StrategyService
from app.storage import Repository


class BacktestService:
    def __init__(
        self,
        repo: Repository | None = None,
        data_service: DataService | None = None,
        strategy_service: StrategyService | None = None,
        report_service: ReportService | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.data_service = data_service or DataService(self.repo)
        self.strategy_service = strategy_service or StrategyService()
        self.report_service = report_service or ReportService()

    def list_runs(self) -> list[dict[str, Any]]:
        return self.repo.list_runs()

    def delete_run(self, run_id: str) -> None:
        self.repo.delete_run(run_id)

    def build_debug_trace(self, run_id: str) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifact = Path(run["artifact_path"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        if run["kind"] == "white_box":
            trace_path = Path(payload["trace_path"])
            if not trace_path.exists():
                raise HTTPException(status_code=404, detail="Trace artifact not found.")
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            compact = self._compact_trace(trace)
            debug_path = settings.report_dir / f"{run_id}_debug_trace.json"
            debug_path.write_text(json.dumps(compact, indent=2), encoding="utf-8")
            return {
                "run_id": run_id,
                "kind": run["kind"],
                "artifact_group": "reports",
                "trace_path": str(debug_path),
                "summary": compact["summary"],
            }

        baseline_run_id = payload.get("baseline_run_id")
        if not baseline_run_id:
            raise HTTPException(status_code=400, detail="Hybrid run is missing its baseline run reference.")
        baseline = self.repo.get_run(baseline_run_id)
        if not baseline:
            raise HTTPException(status_code=404, detail="Baseline run not found for this hybrid run.")
        baseline_payload = json.loads(Path(baseline["artifact_path"]).read_text(encoding="utf-8"))
        baseline_trace_path = Path(baseline_payload["trace_path"])
        trace = json.loads(baseline_trace_path.read_text(encoding="utf-8"))
        score_map = {item["candidate_id"]: item for item in payload.get("test_decisions", [])}
        for row in trace:
            candidate_id = row.get("candidate_id")
            if candidate_id and candidate_id in score_map:
                row["hybrid_decision"] = score_map[candidate_id]
        compact = self._compact_trace(trace)
        debug_path = settings.report_dir / f"{run_id}_debug_trace.json"
        debug_path.write_text(json.dumps(compact, indent=2), encoding="utf-8")
        return {
            "run_id": run_id,
            "kind": run["kind"],
            "artifact_group": "reports",
            "trace_path": str(debug_path),
            "baseline_run_id": baseline_run_id,
            "summary": compact["summary"],
        }

    def build_tradingview_debug(self, run_id: str) -> dict[str, str]:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifact = Path(run["artifact_path"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        pine_text = self._make_pine_debug_script(payload)
        pine_path = settings.report_dir / f"{run_id}_tv_debug.pine"
        pine_path.write_text(pine_text, encoding="utf-8")
        return {
            "run_id": run_id,
            "pine_path": str(pine_path),
            "instructions": (
                "Open TradingView on XAUUSD 15m, open Pine Editor, paste this script, save, and add it to chart. "
                "Blue labels are candidates, green/red labels are realized exits."
            ),
        }

    def run_whitebox(self, dataset_id: str, profile_name: str) -> dict[str, Any]:
        bars = self.data_service.load_bars(dataset_id)
        strategy = self.strategy_service.current()
        self._assert_dataset_compatibility(dataset_id, strategy["timeframe"])
        profile = self.strategy_service.profiles()[profile_name]
        engine_result = WhiteBoxEngine(profile).run(bars)
        run_id = f"wb_{uuid.uuid4().hex[:12]}"
        artifact_path = settings.run_dir / f"{run_id}.json"
        trace_path = settings.run_dir / f"{run_id}_trace.json"
        trace = engine_result.pop("trace")
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        payload = {
            "run_id": run_id,
            "kind": "white_box",
            "strategy_id": strategy["family_id"],
            "dataset_id": dataset_id,
            "profile": profile_name,
            "parameters": profile,
            "metrics": engine_result["metrics"],
            "diagnostics": engine_result["diagnostics"],
            "candidates": engine_result["candidates"],
            "trades": engine_result["trades"],
            "trace_path": str(trace_path),
        }
        artifact_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        report_path = self.report_service.write_report(run_id, "white_box", payload)
        verdict = self.report_service.verdict(payload["metrics"])["destination"]
        self.repo.store_run(
            {
                "run_id": run_id,
                "kind": "white_box",
                "dataset_id": dataset_id,
                "status": "completed",
                "verdict": verdict,
                "metrics_json": payload["metrics"],
                "artifact_path": str(artifact_path),
                "report_path": report_path,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        payload["verdict"] = verdict
        payload["artifact_path"] = str(artifact_path)
        payload["report_path"] = report_path
        payload["trace_path"] = str(trace_path)
        return payload

    def run_hybrid(self, dataset_id: str, profile_name: str, threshold: float | None = None) -> dict[str, Any]:
        baseline = self.run_whitebox(dataset_id, profile_name)
        candidates = baseline["candidates"]
        trades = baseline["trades"]
        if not trades:
            raise HTTPException(status_code=400, detail="White-box baseline produced no trades, so the hybrid layer has nothing to learn from.")
        rows = self._candidate_rows(candidates, trades)
        if len(rows) < 8:
            raise HTTPException(status_code=400, detail="Need at least 8 labeled trades for the hybrid comparison.")
        threshold = threshold if threshold is not None else settings.hybrid_threshold
        model_info = self._train_or_fallback(rows, threshold)
        approved_trades = [row["trade"] for row in model_info["test_rows"] if row["approved"]]
        baseline_test_trades = [row["trade"] for row in model_info["test_rows"]]
        hybrid_metrics = compute_metrics(approved_trades)
        whitebox_test_metrics = compute_metrics(baseline_test_trades)
        handoff_quality = {
            "approval_rate": round(len(approved_trades) / len(model_info["test_rows"]), 4),
            "delta_sharpe": round(hybrid_metrics["sharpe"] - whitebox_test_metrics["sharpe"], 4),
            "delta_expectancy": round(hybrid_metrics["expectancy"] - whitebox_test_metrics["expectancy"], 4),
            "delta_drawdown": round(hybrid_metrics["max_drawdown"] - whitebox_test_metrics["max_drawdown"], 4),
        }
        run_id = f"hy_{uuid.uuid4().hex[:12]}"
        artifact_path = settings.run_dir / f"{run_id}.json"
        model_path = settings.run_dir / f"{run_id}.pkl"
        payload = {
            "run_id": run_id,
            "kind": "hybrid",
            "strategy_id": self.strategy_service.current()["family_id"],
            "dataset_id": dataset_id,
            "baseline_run_id": baseline["run_id"],
            "baseline_trace_path": baseline["trace_path"],
            "profile": profile_name,
            "threshold": threshold,
            "baseline_metrics": baseline["metrics"],
            "metrics": hybrid_metrics,
            "whitebox_test_metrics": whitebox_test_metrics,
            "handoff_quality": handoff_quality,
            "model": {
                "mode": model_info["mode"],
                "feature_names": model_info["feature_names"],
                "train_rows": len(model_info["train_rows"]),
                "test_rows": len(model_info["test_rows"]),
                "threshold": threshold,
            },
            "test_decisions": [
                {
                    "candidate_id": row["candidate"]["candidate_id"],
                    "score": row["score"],
                    "approved": row["approved"],
                    "label": row["label"],
                    "reason": row["candidate"]["reason"],
                }
                for row in model_info["test_rows"]
            ],
        }
        artifact_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        if model_info["mode"] == "model":
            with model_path.open("wb") as handle:
                pickle.dump(model_info["model"], handle)
            payload["model_path"] = str(model_path)
        report_path = self.report_service.write_report(run_id, "hybrid", payload, handoff_quality)
        verdict = self.report_service.verdict(payload["metrics"], handoff_quality)["destination"]
        self.repo.store_run(
            {
                "run_id": run_id,
                "kind": "hybrid",
                "dataset_id": dataset_id,
                "status": "completed",
                "verdict": verdict,
                "metrics_json": payload["metrics"],
                "artifact_path": str(artifact_path),
                "report_path": report_path,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        payload["verdict"] = verdict
        payload["artifact_path"] = str(artifact_path)
        payload["report_path"] = report_path
        return payload

    def latest_hybrid_model(self) -> tuple[Any | None, list[str], float]:
        for run in self.repo.list_runs():
            if run["kind"] != "hybrid":
                continue
            artifact = Path(run["artifact_path"])
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            model_path = artifact.with_suffix(".pkl")
            if model_path.exists():
                with model_path.open("rb") as handle:
                    return pickle.load(handle), payload["model"]["feature_names"], payload["model"]["threshold"]
            return None, payload["model"]["feature_names"], payload["model"]["threshold"]
        return None, ["session_ny", "sweep_depth_atr", "body_atr", "fvg_size_atr", "bias", "distance_to_prev_day_atr"], settings.hybrid_threshold

    def heuristic_score(self, features: dict[str, float]) -> float:
        raw = (
            0.55
            + (0.12 * features.get("session_ny", 0))
            + (0.08 * features.get("bias", 0))
            - (0.18 * abs(features.get("sweep_depth_atr", 0) - 0.35))
            + (0.12 * min(features.get("fvg_size_atr", 0), 1.4))
            + (0.10 * min(features.get("body_atr", 0), 1.2))
            - (0.08 * min(features.get("distance_to_prev_day_atr", 0), 3.0))
        )
        return round(max(0.01, min(0.99, raw / 1.3)), 4)

    def _candidate_rows(self, candidates: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        trade_map = {trade["candidate_id"]: trade for trade in trades}
        rows: list[dict[str, Any]] = []
        for candidate in candidates:
            trade = trade_map.get(candidate["candidate_id"])
            if not trade:
                continue
            rows.append(
                {
                    "candidate": candidate,
                    "features": candidate["features"],
                    "label": 1 if trade["outcome_r"] > 0 else 0,
                    "trade": Trade(
                        trade_id=trade["trade_id"],
                        candidate_id=trade["candidate_id"],
                        direction=trade["direction"],
                        entry_ts=datetime.fromisoformat(trade["entry_ts"]),
                        exit_ts=datetime.fromisoformat(trade["exit_ts"]),
                        entry=trade["entry"],
                        exit=trade["exit"],
                        stop=trade["stop"],
                        target=trade["target"],
                        risk_r=trade["risk_r"],
                        outcome_r=trade["outcome_r"],
                        exit_reason=trade["exit_reason"],
                        reason=trade["reason"],
                    ),
                    "ts": datetime.fromisoformat(candidate["ts"]),
                }
            )
        rows.sort(key=lambda row: row["ts"])
        return rows

    def _train_or_fallback(self, rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
        feature_names = ["session_ny", "sweep_depth_atr", "body_atr", "fvg_size_atr", "bias", "distance_to_prev_day_atr"]
        split_index = max(5, int(len(rows) * 0.7))
        train_rows = rows[:split_index]
        test_rows = rows[split_index:]
        labels = {row["label"] for row in train_rows}
        if len(test_rows) < 3:
            raise HTTPException(status_code=400, detail="Need more held-out trades to evaluate the hybrid layer.")

        if len(labels) < 2:
            for row in test_rows:
                row["score"] = self.heuristic_score(row["features"])
                row["approved"] = row["score"] >= threshold
            return {
                "mode": "heuristic",
                "feature_names": feature_names,
                "train_rows": train_rows,
                "test_rows": test_rows,
            }

        model = GradientBoostingClassifier(random_state=42)
        train_x = [[row["features"][name] for name in feature_names] for row in train_rows]
        train_y = [row["label"] for row in train_rows]
        model.fit(train_x, train_y)
        test_x = [[row["features"][name] for name in feature_names] for row in test_rows]
        probs = model.predict_proba(test_x)[:, 1]
        for row, score in zip(test_rows, probs, strict=True):
            row["score"] = round(float(score), 4)
            row["approved"] = row["score"] >= threshold
        return {
            "mode": "model",
            "feature_names": feature_names,
            "train_rows": train_rows,
            "test_rows": test_rows,
            "model": model,
        }

    def _assert_dataset_compatibility(self, dataset_id: str, expected_timeframe: str) -> None:
        dataset = self.repo.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        if dataset["timeframe"] != expected_timeframe:
            raise HTTPException(status_code=400, detail=f"Dataset timeframe must be {expected_timeframe}.")

    def _make_pine_debug_script(self, payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates", [])
        trades = payload.get("trades", [])
        candidate_times = [self._pine_time_ms(item["ts"]) for item in candidates]
        candidate_prices = [float(item["entry"]) for item in candidates]
        candidate_texts = [f"{item['direction'][0].upper()} {item['sweep_level']}" for item in candidates]
        exit_times = [self._pine_time_ms(item["exit_ts"]) for item in trades]
        exit_prices = [float(item["exit"]) for item in trades]
        exit_texts = [f"{item['direction'][0].upper()} {item['exit_reason']} {item['outcome_r']}R" for item in trades]

        def num_array(name: str, values: list[float | int]) -> str:
            joined = ", ".join(str(value) for value in values)
            return f"var {name} = array.from({joined})" if values else f"var {name} = array.new_float()"

        def str_array(name: str, values: list[str]) -> str:
            joined = ", ".join(json.dumps(value) for value in values)
            return f"var {name} = array.from({joined})" if values else f"var {name} = array.new_string()"

        return "\n".join(
            [
                "//@version=6",
                f'indicator("Aurum Run Debug {payload["run_id"]}", overlay=true, max_labels_count=500)',
                "",
                num_array("candidateTimes", candidate_times),
                num_array("candidatePrices", candidate_prices),
                str_array("candidateTexts", candidate_texts),
                num_array("exitTimes", exit_times),
                num_array("exitPrices", exit_prices),
                str_array("exitTexts", exit_texts),
                "",
                "showCandidates = input.bool(true, 'Show candidates')",
                "showExits = input.bool(true, 'Show exits')",
                "var drawn = false",
                "",
                "if barstate.islast and not drawn",
                "    if showCandidates",
                "        for i = 0 to array.size(candidateTimes) - 1",
                "            candidateText = array.get(candidateTexts, i)",
                "            candidateYloc = str.startswith(candidateText, 'S ') ? yloc.abovebar : yloc.belowbar",
                "            candidateStyle = str.startswith(candidateText, 'S ') ? label.style_label_down : label.style_label_up",
                "            label.new(int(array.get(candidateTimes, i)), na, candidateText, xloc=xloc.bar_time, yloc=candidateYloc, style=candidateStyle, color=color.new(color.blue, 0), textcolor=color.white)",
                "    if showExits",
                "        for i = 0 to array.size(exitTimes) - 1",
                "            exitText = array.get(exitTexts, i)",
                "            exitColor = str.contains(exitText, 'target') ? color.new(color.green, 0) : color.new(color.red, 0)",
                "            exitDirectionShort = str.startswith(exitText, 'S ')",
                "            exitIsTarget = str.contains(exitText, 'target')",
                "            exitYloc = exitIsTarget ? (exitDirectionShort ? yloc.belowbar : yloc.abovebar) : (exitDirectionShort ? yloc.abovebar : yloc.belowbar)",
                "            exitStyle = exitYloc == yloc.abovebar ? label.style_label_down : label.style_label_up",
                "            label.new(int(array.get(exitTimes, i)), na, exitText, xloc=xloc.bar_time, yloc=exitYloc, style=exitStyle, color=exitColor, textcolor=color.white)",
                "    drawn := true",
            ]
        )

    @staticmethod
    def _pine_time_ms(raw: str) -> int:
        return int(datetime.fromisoformat(raw).timestamp() * 1000)

    @staticmethod
    def _summarize_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
        sessions = {}
        rejections = {}
        candidates = 0
        hybrid_scored = 0
        for row in trace:
            sessions[row["session"]] = sessions.get(row["session"], 0) + 1
            reason = row.get("rejection_reason")
            if reason:
                rejections[reason] = rejections.get(reason, 0) + 1
            if row.get("candidate_id"):
                candidates += 1
            if row.get("hybrid_decision"):
                hybrid_scored += 1
        top_rejections = sorted(rejections.items(), key=lambda item: item[1], reverse=True)[:10]
        return {
            "bars": len(trace),
            "sessions": sessions,
            "candidate_bars": candidates,
            "hybrid_scored_candidates": hybrid_scored,
            "top_rejections": top_rejections,
        }

    def _compact_trace(self, trace: list[dict[str, Any]]) -> dict[str, Any]:
        confirmation_blockers: dict[str, int] = {}
        rejection_samples: dict[str, list[dict[str, Any]]] = {}
        candidate_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        state_rows: list[dict[str, Any]] = []

        for row in trace:
            confirmation = row.get("confirmation") or {}
            for blocker in confirmation.get("blockers", []):
                confirmation_blockers[blocker] = confirmation_blockers.get(blocker, 0) + 1

            reason = row.get("rejection_reason")
            if reason:
                samples = rejection_samples.setdefault(reason, [])
                if len(samples) < 12:
                    samples.append(
                        {
                            "ts": row["ts"],
                            "session": row["session"],
                            "bar": row["bar"],
                            "active_setup": row.get("active_setup"),
                            "confirmation": confirmation or None,
                        }
                    )

            if row.get("candidate_id"):
                candidate_rows.append(
                    {
                        "ts": row["ts"],
                        "session": row["session"],
                        "candidate_id": row["candidate_id"],
                        "sweep": row.get("sweep") or row.get("active_setup"),
                        "planned_order": row.get("planned_order"),
                        "hybrid_decision": row.get("hybrid_decision"),
                    }
                )

            if row.get("active_trade") or any(event.startswith("trade_closed:") for event in row.get("events", [])):
                state_rows.append(
                    {
                        "ts": row["ts"],
                        "session": row["session"],
                        "state": row["state"],
                        "events": row["events"],
                        "active_trade": row.get("active_trade"),
                        "planned_order": row.get("planned_order"),
                    }
                )

            for event in row.get("events", []):
                if event.startswith("trade_closed:"):
                    trade_rows.append(
                        {
                            "ts": row["ts"],
                            "session": row["session"],
                            "event": event,
                            "candidate_id": row.get("candidate_id"),
                        }
                    )

        return {
            "summary": {
                **self._summarize_trace(trace),
                "top_confirmation_blockers": sorted(
                    confirmation_blockers.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:10],
            },
            "candidate_rows": candidate_rows,
            "trade_rows": trade_rows,
            "state_rows_sample": state_rows[:200],
            "rejection_samples": rejection_samples,
        }
