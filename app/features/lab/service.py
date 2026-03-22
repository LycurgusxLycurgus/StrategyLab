from __future__ import annotations

import itertools
import json
import uuid
from pathlib import Path

from app.features.backtests.schema import BacktestRunRequest
from app.features.lab.schema import OptimizeRequest, ProposalRequest, ReviewRequest
from app.shared.errors import AppError


class LabService:
    def __init__(self, config, db, strategy_service, backtest_service):
        self.config = config
        self.db = db
        self.strategy_service = strategy_service
        self.backtest_service = backtest_service

    def optimize(self, payload: OptimizeRequest) -> dict:
        source_run = self.db.fetch_one("select * from backtest_runs where run_id = ?", (payload.source_run_id,))
        if not source_run:
            raise AppError(404, "RUN_NOT_FOUND", "unknown source run", {"run_id": payload.source_run_id})
        if source_run["verdict"] == "rejected":
            raise AppError(400, "RUN_NOT_ELIGIBLE", "only survivor runs can be optimized", {"run_id": payload.source_run_id})
        family = self.strategy_service.get_family(source_run["family_id"])
        base_parameters = json.loads(source_run["parameters_json"])
        grid_items = list(family.optimization_grid.items())[:2]
        combinations: list[dict] = []
        if not grid_items:
            combinations.append(base_parameters)
        else:
            keys = [item[0] for item in grid_items]
            values = [item[1] for item in grid_items]
            for combo in itertools.product(*values):
                variant = dict(base_parameters)
                variant.update(dict(zip(keys, combo)))
                combinations.append(variant)
        rankings: list[dict] = []
        for variant in combinations[: payload.max_variants]:
            summary = self.backtest_service.run_backtest(
                BacktestRunRequest(
                    family_id=family.family_id,
                    dataset_id=source_run["dataset_id"],
                    parameter_overrides=variant,
                ),
                persist=False,
            )
            rankings.append(
                {
                    "parameters": summary.parameters,
                    "verdict": summary.verdict,
                    "sharpe": summary.metrics["out_of_sample"]["sharpe"],
                    "profit_factor": summary.metrics["out_of_sample"]["profit_factor"],
                    "max_drawdown": summary.metrics["out_of_sample"]["max_drawdown"],
                }
            )
        rankings.sort(key=lambda item: (item["sharpe"], item["profit_factor"]), reverse=True)
        artifact_id = f"opt_{uuid.uuid4().hex[:12]}"
        artifact_path = self.config.app_report_dir / f"{artifact_id}.json"
        payload_dict = {"source_run_id": payload.source_run_id, "rankings": rankings}
        artifact_path.write_text(json.dumps(payload_dict, indent=2, sort_keys=True), encoding="utf-8")
        self.db.insert_artifact(
            artifact_id=artifact_id,
            artifact_type="optimization_report",
            family_id=family.family_id,
            dataset_id=source_run["dataset_id"],
            source_run_id=payload.source_run_id,
            path=str(artifact_path),
            payload=payload_dict,
        )
        return {"artifact_id": artifact_id, "artifact_path": str(artifact_path), "rankings": rankings}

    def list_graveyard(self) -> list[dict]:
        return self.db.fetch_all(
            """
            select artifact_id, family_id, dataset_id, source_run_id, path, payload_json, created_at
            from lab_artifacts
            where artifact_type = 'graveyard_report'
            order by created_at desc
            """
        )

    def delete_graveyard(self, artifact_id: str) -> dict:
        row = self.db.fetch_one(
            """
            select artifact_id, artifact_type, source_run_id, path
            from lab_artifacts
            where artifact_id = ?
            """,
            (artifact_id,),
        )
        if not row or row["artifact_type"] != "graveyard_report":
            raise AppError(404, "ARTIFACT_NOT_FOUND", "unknown graveyard artifact", {"artifact_id": artifact_id})
        self.db.delete_artifact(artifact_id)
        if row["source_run_id"]:
            self.db.execute("update backtest_runs set report_path = null where run_id = ?", (row["source_run_id"],))
        path = Path(row["path"])
        if path.exists():
            path.unlink()
        return {"artifact_id": artifact_id, "deleted": True}

    def create_proposal(self, payload: ProposalRequest) -> dict:
        family = self.strategy_service.get_family(payload.family_id)
        artifact_id = f"proposal_{uuid.uuid4().hex[:12]}"
        artifact_path = self.config.app_report_dir / f"{artifact_id}.md"
        body = "\n".join(
            [
                f"# Proposal {artifact_id}",
                "",
                f"- family: `{family.family_id}`",
                f"- proposal_type: `{payload.proposal_type}`",
                "",
                "## Hypothesis",
                payload.hypothesis.strip(),
                "",
                "## Patch",
                "```json",
                json.dumps(payload.patch, indent=2, sort_keys=True),
                "```",
                "",
                "This artifact is intentionally non-executable. It is limited to strategy-data proposals only.",
            ]
        )
        artifact_path.write_text(body + "\n", encoding="utf-8")
        artifact_payload = {
            "family_id": family.family_id,
            "proposal_type": payload.proposal_type,
            "hypothesis": payload.hypothesis,
            "patch": payload.patch,
        }
        self.db.insert_artifact(
            artifact_id=artifact_id,
            artifact_type="proposal",
            family_id=family.family_id,
            path=str(artifact_path),
            payload=artifact_payload,
        )
        return {"artifact_id": artifact_id, "artifact_path": str(artifact_path), **artifact_payload}

    def review_family(self, payload: ReviewRequest) -> dict:
        family = self.strategy_service.get_family(payload.family_id)
        runs = self.db.fetch_all(
            """
            select run_id, verdict, parameters_json, metrics_json, artifact_path, report_path, created_at
            from backtest_runs
            where family_id = ? and dataset_id = ?
            order by created_at desc
            limit 24
            """,
            (payload.family_id, payload.dataset_id),
        )
        if not runs:
            raise AppError(400, "NO_RUNS_FOR_REVIEW", "run a family sweep before requesting an LLM review", payload.model_dump())
        graveyard = self.db.fetch_all(
            """
            select artifact_id, path, payload_json, created_at
            from lab_artifacts
            where artifact_type = 'graveyard_report' and family_id = ? and dataset_id = ?
            order by created_at desc
            limit 12
            """,
            (payload.family_id, payload.dataset_id),
        )
        review_input = {
            "app_role": "StrategyLab is a local-first white-box and hybrid strategy research lab. It runs deterministic backtests, evaluates parameter sweeps, preserves graveyard artifacts, and asks an LLM for explanation-based conjectures and corrections. It does not auto-promote or auto-edit executable strategy code.",
            "family_manifest": family.model_dump(),
            "run_context": [
                {
                    "run_id": row["run_id"],
                    "verdict": row["verdict"],
                    "parameters": json.loads(row["parameters_json"]),
                    "metrics": json.loads(row["metrics_json"]),
                    "artifact_path": row["artifact_path"],
                    "report_path": row["report_path"],
                }
                for row in runs
            ],
            "graveyard_context": [
                {
                    "artifact_id": row["artifact_id"],
                    "path": row["path"],
                    "payload": json.loads(row["payload_json"]),
                }
                for row in graveyard
            ],
            "perspectives": self._read_doc("agents/docs/white_black_boxes-perspectives.md"),
            "query_context": self._read_doc("agents/docs/strategy-labs-query.txt"),
            "source_context": self._read_doc("agents/docs/strategy-labs-source.txt"),
            "verdict_criteria": self._read_doc("agents/docs/verdict_criteria.md"),
        }
        prompt = self._build_review_prompt(review_input)
        response_text = self._call_gemini(prompt)
        review_payload = self._parse_review_payload(response_text)
        artifact_id = f"review_{uuid.uuid4().hex[:12]}"
        artifact_path = self.config.app_report_dir / f"{artifact_id}.json"
        artifact = {
            "artifact_id": artifact_id,
            "artifact_path": str(artifact_path),
            "family_id": payload.family_id,
            "dataset_id": payload.dataset_id,
            "model": self.config.gemini_model,
            "review": review_payload,
            "input_summary": {
                "run_count": len(review_input["run_context"]),
                "graveyard_count": len(review_input["graveyard_context"]),
            },
        }
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        self.db.insert_artifact(
            artifact_id=artifact_id,
            artifact_type="llm_review",
            family_id=payload.family_id,
            dataset_id=payload.dataset_id,
            path=str(artifact_path),
            payload=artifact,
        )
        return artifact

    def _build_review_prompt(self, review_input: dict) -> str:
        output_contract = {
            "family_diagnosis": "short explanation of what the family is doing well or badly",
            "parameter_grid_patch": {
                "keep": {},
                "expand": {},
                "drop": [],
                "reason": "why these grid changes should be coded next"
            },
            "conjectures": [
                {
                    "title": "short hypothesis",
                    "explanation": "causal explanation grounded in results and family logic",
                    "expected_effect": "what should improve",
                    "confidence": "low|medium|high"
                }
            ],
            "black_box_meta_notes": [
                "how an eventual black-box or hybrid meta-model should inspect this family without replacing the family logic"
            ],
            "coding_agent_brief": {
                "priority": "what should be coded first",
                "safe_changes": ["changes that can be implemented without changing strategy identity"],
                "avoid": ["changes that would mutate the family into a different strategy"]
            }
        }
        return "\n".join(
            [
                "You are an aware strategy research agent operating inside StrategyLab.",
                "Your task is to review one strategy family using the full app role, verdict criteria, perspective canon, family manifest, recent parameter sweep results, and graveyard context.",
                "You must think like an explanation-first hybrid researcher: preserve white-box logic, propose better parameter grids, and describe how black-box meta-models could later examine the family without replacing it.",
                "Do not propose direct code patches. Propose only a parameter-grid patch and a coding-agent brief.",
                "Return valid JSON only.",
                "JSON schema example:",
                json.dumps(output_contract, indent=2, sort_keys=True),
                "Review input:",
                json.dumps(review_input, indent=2, sort_keys=True),
            ]
        )

    def _call_gemini(self, prompt: str) -> str:
        if not self.config.gemini_api_key:
            raise AppError(400, "GEMINI_API_KEY_MISSING", "set GEMINI_API_KEY before requesting an LLM review")
        try:
            from google import genai
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise AppError(500, "GEMINI_SDK_UNAVAILABLE", "google-genai is not installed", {"error": str(exc)}) from exc
        client = genai.Client(api_key=self.config.gemini_api_key)
        response = client.models.generate_content(model=self.config.gemini_model, contents=prompt)
        return getattr(response, "text", "") or ""

    @staticmethod
    def _parse_review_payload(response_text: str) -> dict:
        text = response_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = next((part for part in parts if part.strip() and not part.strip().lower().startswith("json")), text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(502, "GEMINI_INVALID_JSON", "Gemini review did not return valid JSON", {"response_text": response_text}) from exc

    def _read_doc(self, relative_path: str) -> str:
        path = self.config.root_dir / relative_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
