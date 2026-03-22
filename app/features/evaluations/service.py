from __future__ import annotations

import json
import math

from app.features.evaluations.schema import EvaluationSummary, MetricSet
from app.infra.db import Database
from app.shared.errors import AppError


TIMEFRAME_PERIODS = {"5m": 12 * 24 * 365, "1H": 24 * 365, "4H": 6 * 365}
MIN_OOS_TRADES = 10
MIN_TOTAL_TRADES = 20
RESEARCH_SURVIVOR_OOS_TRADES = 12
RESEARCH_SURVIVOR_TOTAL_TRADES = 24
PAPER_CANDIDATE_OOS_TRADES = 20
PAPER_CANDIDATE_TOTAL_TRADES = 40


class EvaluationService:
    def __init__(self, db: Database):
        self.db = db

    def evaluate(self, timeframe: str, equity_curve: list[dict], trades: list[dict]) -> EvaluationSummary:
        if timeframe not in TIMEFRAME_PERIODS:
            raise AppError(400, "INVALID_TIMEFRAME", "unsupported timeframe", {"timeframe": timeframe})
        returns = self._returns_from_equity(equity_curve)
        split_at = int(len(returns) * 0.7) if returns else 0
        oos_returns = returns[split_at:] if split_at < len(returns) else returns
        overall = self._metric_set(returns, trades, equity_curve, timeframe)
        out_of_sample = self._metric_set(oos_returns, self._oos_trades(trades, equity_curve, split_at), equity_curve[split_at:], timeframe)
        fold_sharpes = self._fold_sharpes(oos_returns, timeframe)
        stable = len(fold_sharpes) == 3 and sum(1 for value in fold_sharpes if value > 0.25) >= 2 and min(fold_sharpes) > -0.5
        verdict = self._verdict(overall, out_of_sample, stable)
        return EvaluationSummary(
            overall=overall,
            out_of_sample=out_of_sample,
            fold_sharpes=fold_sharpes,
            stable_walk_forward=stable,
            verdict=verdict,
        )

    def get_run_evaluation(self, run_id: str) -> dict:
        row = self.db.fetch_one("select run_id, metrics_json, verdict from backtest_runs where run_id = ?", (run_id,))
        if not row:
            raise AppError(404, "RUN_NOT_FOUND", "unknown backtest run", {"run_id": run_id})
        payload = json.loads(row["metrics_json"])
        payload["run_id"] = row["run_id"]
        payload["verdict"] = row["verdict"]
        return payload

    def _metric_set(self, returns: list[float], trades: list[dict], equity_curve: list[dict], timeframe: str) -> MetricSet:
        mean = sum(returns) / len(returns) if returns else 0.0
        variance = sum((item - mean) ** 2 for item in returns) / len(returns) if returns else 0.0
        downside = [item for item in returns if item < 0]
        downside_variance = sum(item**2 for item in downside) / len(downside) if downside else 0.0
        stdev = math.sqrt(variance)
        downside_stdev = math.sqrt(downside_variance)
        annualizer = math.sqrt(TIMEFRAME_PERIODS[timeframe])
        sharpe = annualizer * mean / stdev if stdev > 0 else 0.0
        sortino = annualizer * mean / downside_stdev if downside_stdev > 0 else 0.0
        gross_profit = sum(max(trade["pnl"], 0.0) for trade in trades)
        gross_loss = abs(sum(min(trade["pnl"], 0.0) for trade in trades))
        wins = sum(1 for trade in trades if trade["pnl"] > 0)
        max_drawdown = max((point["drawdown"] for point in equity_curve), default=0.0)
        total_return = equity_curve[-1]["equity"] / equity_curve[0]["equity"] - 1 if len(equity_curve) > 1 else 0.0
        return MetricSet(
            sharpe=round(sharpe, 4),
            sortino=round(sortino, 4),
            max_drawdown=round(max_drawdown, 4),
            profit_factor=round(gross_profit / gross_loss, 4) if gross_loss > 0 else round(gross_profit, 4),
            expectancy=round(sum(trade["pnl"] for trade in trades) / len(trades), 4) if trades else 0.0,
            win_rate=round(wins / len(trades), 4) if trades else 0.0,
            trades=len(trades),
            total_return=round(total_return, 4),
        )

    @staticmethod
    def _returns_from_equity(equity_curve: list[dict]) -> list[float]:
        returns: list[float] = []
        for previous, current in zip(equity_curve, equity_curve[1:]):
            if previous["equity"] == 0:
                returns.append(0.0)
            else:
                returns.append((current["equity"] - previous["equity"]) / previous["equity"])
        return returns

    @staticmethod
    def _oos_trades(trades: list[dict], equity_curve: list[dict], split_at: int) -> list[dict]:
        if not equity_curve or split_at >= len(equity_curve):
            return trades
        threshold_ts = equity_curve[0]["ts"] if split_at == 0 else equity_curve[split_at]["ts"]
        return [trade for trade in trades if trade["exit_ts"] >= threshold_ts]

    @staticmethod
    def _fold_sharpes(returns: list[float], timeframe: str) -> list[float]:
        if len(returns) < 9:
            return []
        size = len(returns) // 3
        annualizer = math.sqrt(TIMEFRAME_PERIODS[timeframe])
        values: list[float] = []
        for start in range(0, size * 3, size):
            fold = returns[start : start + size]
            if not fold:
                continue
            mean = sum(fold) / len(fold)
            variance = sum((item - mean) ** 2 for item in fold) / len(fold)
            stdev = math.sqrt(variance)
            values.append(round(annualizer * mean / stdev, 4) if stdev > 0 else 0.0)
        return values

    @staticmethod
    def _verdict(overall: MetricSet, out_of_sample: MetricSet, stable_walk_forward: bool) -> str:
        if (
            out_of_sample.sharpe < 0.75
            or out_of_sample.expectancy <= 0
            or out_of_sample.profit_factor < 1.0
            or out_of_sample.max_drawdown > 0.35
            or out_of_sample.trades < MIN_OOS_TRADES
            or overall.trades < MIN_TOTAL_TRADES
            or not stable_walk_forward
        ):
            return "rejected"
        if (
            out_of_sample.sharpe >= 1.75
            and out_of_sample.max_drawdown <= 0.12
            and out_of_sample.profit_factor >= 1.30
            and out_of_sample.trades >= PAPER_CANDIDATE_OOS_TRADES
            and overall.trades >= PAPER_CANDIDATE_TOTAL_TRADES
        ):
            return "paper_candidate"
        if (
            out_of_sample.sharpe >= 1.25
            and out_of_sample.max_drawdown <= 0.20
            and out_of_sample.profit_factor >= 1.15
            and out_of_sample.trades >= RESEARCH_SURVIVOR_OOS_TRADES
            and overall.trades >= RESEARCH_SURVIVOR_TOTAL_TRADES
        ):
            return "research_survivor"
        return "rejected"
