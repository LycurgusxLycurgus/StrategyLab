from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings
from app.features.backtests.engine import compute_metrics
from app.features.backtests.service import BacktestService
from app.features.data.service import DataService
from app.features.strategies.service import StrategyService
from app.storage import Repository


class PaperService:
    def __init__(
        self,
        repo: Repository | None = None,
        data_service: DataService | None = None,
        strategy_service: StrategyService | None = None,
        backtest_service: BacktestService | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.data_service = data_service or DataService(self.repo)
        self.strategy_service = strategy_service or StrategyService()
        self.backtest_service = backtest_service or BacktestService(self.repo, self.data_service, self.strategy_service)

    def list_runs(self) -> list[dict[str, Any]]:
        return self.repo.list_paper_runs()

    def run_week(self, dataset_id: str, profile_name: str, use_hybrid: bool = True) -> dict[str, Any]:
        bars = self.data_service.load_bars(dataset_id)
        if not bars:
            raise ValueError("Dataset is empty.")
        cutoff = bars[-1].ts - timedelta(days=7)
        paper_window = [bar for bar in bars if bar.ts >= cutoff]
        if len(paper_window) < 40:
            paper_window = bars[-min(len(bars), 160) :]

        baseline = self.backtest_service.run_whitebox(dataset_id, profile_name)
        model = None
        feature_names: list[str] = []
        threshold = settings.hybrid_threshold
        if use_hybrid:
            model, feature_names, threshold = self.backtest_service.latest_hybrid_model()

        approvals: list[dict[str, Any]] = []
        for candidate in baseline["candidates"]:
            candidate_ts = datetime.fromisoformat(candidate["ts"])
            if candidate_ts < cutoff:
                continue
            features = candidate["features"]
            if model:
                vector = [[features[name] for name in feature_names]]
                score = round(float(model.predict_proba(vector)[0][1]), 4)
            else:
                score = self.backtest_service.heuristic_score(features)
            approvals.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "score": score,
                    "approved": score >= threshold,
                    "reason": candidate["reason"],
                }
            )

        approved_candidate_ids = {item["candidate_id"] for item in approvals if item["approved"]}
        approved_trades = [trade for trade in baseline["trades"] if trade["candidate_id"] in approved_candidate_ids]
        metric_trades = [
            type("PaperTrade", (), {"outcome_r": trade["outcome_r"]})()
            for trade in approved_trades
        ]
        metrics = compute_metrics(metric_trades)

        paper_id = f"paper_{uuid.uuid4().hex[:12]}"
        artifact_path = settings.paper_dir / f"{paper_id}.json"
        payload = {
            "paper_id": paper_id,
            "dataset_id": dataset_id,
            "profile": profile_name,
            "use_hybrid": use_hybrid,
            "paper_bars": len(paper_window),
            "metrics": metrics,
            "approvals": approvals,
            "approved_trades": approved_trades,
        }
        artifact_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        self.repo.store_paper_run(
            {
                "paper_id": paper_id,
                "dataset_id": dataset_id,
                "status": "completed",
                "metrics_json": metrics,
                "artifact_path": str(artifact_path),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        payload["artifact_path"] = str(artifact_path)
        return payload
