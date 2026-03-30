from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.features.backtests.service import BacktestService
from app.storage import Repository


class WebhookService:
    def __init__(self, repo: Repository | None = None, backtest_service: BacktestService | None = None) -> None:
        self.repo = repo or Repository()
        self.backtest_service = backtest_service or BacktestService(self.repo)

    def evaluate_signal(self, payload: dict[str, Any]) -> dict[str, Any]:
        features = {
            "session_ny": payload["session_ny"],
            "sweep_depth_atr": payload["sweep_depth_atr"],
            "body_atr": payload["body_atr"],
            "fvg_size_atr": payload["fvg_size_atr"],
            "bias": payload["bias"],
            "distance_to_prev_day_atr": payload["distance_to_prev_day_atr"],
        }
        model, feature_names, threshold = self.backtest_service.latest_hybrid_model()
        if model:
            vector = [[features[name] for name in feature_names]]
            score = round(float(model.predict_proba(vector)[0][1]), 4)
            mode = "model"
        else:
            score = self.backtest_service.heuristic_score(features)
            mode = "heuristic"
        response = {
            "action": "EXECUTE" if score >= threshold else "REJECT",
            "score": score,
            "threshold": threshold,
            "mode": mode,
            "reason": (
                "Hybrid approval passed the current threshold."
                if score >= threshold
                else "Hybrid approval failed the current threshold."
            ),
        }
        self.repo.store_webhook(
            {
                "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                "payload_json": payload,
                "response_json": response,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return response
