from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.config import settings


class ReportService:
    def verdict(self, metrics: dict[str, float], handoff_quality: dict[str, float] | None = None) -> dict[str, Any]:
        trades = metrics["trades"]
        sharpe = metrics["sharpe"]
        expectancy = metrics["expectancy"]
        drawdown = metrics["max_drawdown"]

        economic = 0
        if sharpe > 0 and expectancy > 0:
            economic = 2
        if sharpe >= 0.75 and expectancy > 0.15:
            economic = 3
        if sharpe >= 1.25 and expectancy > 0.25:
            economic = 4
        if sharpe >= 1.75 and expectancy > 0.4:
            economic = 5

        survivability = 1 if trades >= 3 else 0
        if trades >= 8 and drawdown <= 2.5:
            survivability = 3
        if trades >= 15 and drawdown <= 1.8:
            survivability = 4
        if trades >= 25 and drawdown <= 1.2:
            survivability = 5

        robustness = 1 if trades >= 5 else 0
        if trades >= 10 and sharpe >= 0.5:
            robustness = 3
        if trades >= 16 and sharpe >= 1.0:
            robustness = 4
        if trades >= 24 and sharpe >= 1.5:
            robustness = 5

        implementation = 4
        epistemic = 3 if trades > 0 else 2
        if handoff_quality and handoff_quality.get("delta_sharpe", 0.0) > 0 and handoff_quality.get("approval_rate", 1.0) < 0.9:
            epistemic = 4
        improvement = 4 if trades > 0 else 3

        total = economic + survivability + robustness + implementation + epistemic + improvement
        if economic == 0 or survivability == 0:
            destination = "bury" if trades == 0 else "graveyard"
            failure = "no_edge" if trades > 0 else "logic_starvation"
        elif total >= 24:
            destination = "promote"
            failure = "none"
        elif total >= 18:
            destination = "incubate"
            failure = "parameter_or_regime_refinement"
        else:
            destination = "graveyard"
            failure = "fragile_edge"

        return {
            "scores": {
                "economic_performance": economic,
                "risk_survivability": survivability,
                "robustness": robustness,
                "implementation_integrity": implementation,
                "epistemic_quality": epistemic,
                "improvement_potential": improvement,
            },
            "total_score": total,
            "destination": destination,
            "primary_failure_type": failure,
            "review_confidence": 0.7 if trades >= 10 else 0.45,
        }

    def explanation(
        self,
        run_kind: str,
        metrics: dict[str, float],
        handoff_quality: dict[str, float] | None = None,
    ) -> dict[str, str]:
        edge = (
            f"The {run_kind} system is currently expressing a session-liquidity reversal conjecture on 15m gold: "
            f"killzone sweeps of Asian or previous-day levels, structural confirmation, and retracement-based entry."
        )
        survival = (
            f"It produced {metrics['trades']} realized trades with Sharpe {metrics['sharpe']} and expectancy {metrics['expectancy']}R. "
            f"The current drawdown footprint is {metrics['max_drawdown']}R."
        )
        failure = (
            "The main current defect is insufficient robust edge under the observed sample. "
            "If the hybrid layer is present, the critical question is whether it improves selection without collapsing trade count."
        )
        rival = (
            "The strongest rival explanations remain regime luck, over-filtering, and pattern simplification error rather than pure leakage, "
            "because the engine records candidates and trades from timestamp-safe bars only."
        )
        mutation = (
            "The next mutation should target either better POI/confirmation quality or better candidate-level scoring features. "
            "Do not widen thresholds blindly unless the failure mode is clearly participation starvation."
        )
        if handoff_quality:
            mutation = (
                f"The hybrid handoff changed Sharpe by {round(handoff_quality.get('delta_sharpe', 0.0), 4)} and expectancy by "
                f"{round(handoff_quality.get('delta_expectancy', 0.0), 4)}. The next mutation should focus on feature quality and threshold calibration."
            )
        return {
            "edge_statement": edge,
            "survival_statement": survival,
            "failure_statement": failure,
            "rival_explanation_statement": rival,
            "mutation_statement": mutation,
        }

    def write_report(
        self,
        run_id: str,
        run_kind: str,
        payload: dict[str, Any],
        handoff_quality: dict[str, float] | None = None,
    ) -> str:
        verdict = self.verdict(payload["metrics"], handoff_quality)
        explanation = self.explanation(run_kind, payload["metrics"], handoff_quality)
        report_path = settings.report_dir / f"{run_id}.md"
        lines = [
            f"# {run_kind} report",
            "",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            f"Destination: **{verdict['destination']}**",
            f"Primary failure: `{verdict['primary_failure_type']}`",
            "",
            "## Metrics",
            "```json",
            json.dumps(payload["metrics"], indent=2),
            "```",
            "",
            "## Scorecard",
            "```json",
            json.dumps(verdict, indent=2),
            "```",
            "",
            "## Canon Narrative",
        ]
        for key in (
            "edge_statement",
            "survival_statement",
            "failure_statement",
            "rival_explanation_statement",
            "mutation_statement",
        ):
            lines.append("")
            lines.append(explanation[key])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return str(report_path)
