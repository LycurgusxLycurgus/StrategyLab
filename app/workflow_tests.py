from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from app.lab import MutationLabService


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = Path("agents/archive/2026-10-23-pre-systematic-v2")
ACTIVE_PROMPTS = [
    "01_research.md",
    "02_approach_trials.md",
    "03_base_strategy.md",
    "04_optimization.md",
    "05_mutation_optimization.md",
    "06_paper_trading.md",
]
ARCHIVED_SOURCES = [
    "agents/translation and generation/agents/codex_phase_operator.md",
    "agents/translation and generation/whitebox/01_translation.md",
    "agents/translation and generation/whitebox/01-5_baseline_transformation.md",
    "agents/translation and generation/whitebox/02_baseline.md",
    "agents/translation and generation/whitebox/02-5_baseline_qualification.md",
    "agents/translation and generation/whitebox/03-1_whitebox_diagnostics.md",
    "agents/translation and generation/whitebox/03_full-whitebox.md",
    "agents/translation and generation/whitebox/04-1_hybrid_diagnostics.md",
    "agents/translation and generation/whitebox/04_hybrid-blackbox.md",
    "agents/translation and generation/whitebox/04-2_blackbox_viability.md",
    "agents/translation and generation/whitebox/04-3_successor_baseline.md",
    "agents/docs/universal_mutation_constitution.md",
    "agents/docs/production_backtest_engine.md",
    "agents/docs/white_black_boxes-perspectives.md",
    "agents/docs/codification_boxes.md",
    "agents/docs/z_verdict_criteria.md",
    "agents/docs/z_metrics_boxes.md",
    "agents/docs/z_strategy_review_questions.md",
    "README.md",
    "agents/manual_runbook.md",
    "agents/plan.md",
    "agentic/architecture.md",
    "STRATEGYLAB_UNRESOLVED_PROOF_MAP.md",
    "agentic/reference-first-migration-plan.md",
]
ARCHIVED_PROMPTS = ARCHIVED_SOURCES[:11]


class WorkflowPromptTests(unittest.TestCase):
    def test_prompt_discovery_returns_only_the_six_current_phase_prompts(self) -> None:
        service = MutationLabService.__new__(MutationLabService)

        prompts = service.list_prompts()
        names = [prompt["name"] for prompt in prompts]

        self.assertEqual(names, ACTIVE_PROMPTS)
        self.assertTrue(all(prompt["content"].strip() for prompt in prompts))
        self.assertNotIn("discretionary_and_blackbox_roadmap.md", names)
        self.assertFalse(set(names).intersection(Path(path).name for path in ARCHIVED_PROMPTS))

    def test_phase_overview_links_to_the_current_prompts(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        for name in ACTIVE_PROMPTS:
            self.assertIn(name, readme)

    def test_archive_manifest_covers_and_verifies_all_24_snapshots(self) -> None:
        archive_root = (REPOSITORY_ROOT / ARCHIVE_ROOT).resolve()
        manifest_path = archive_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["created_date"], "2026-10-23")
        self.assertEqual(len(manifest["files"]), 24)

        archived_paths: set[str] = set()
        records_by_source: dict[str, dict[str, object]] = {}
        for record in manifest["files"]:
            source_path = record["source_path"]
            archive_path = record["archive_path"]
            self.assertNotIn("..", Path(archive_path).parts)
            archived_file = (REPOSITORY_ROOT / archive_path).resolve()
            self.assertTrue(archived_file.is_relative_to(archive_root))
            self.assertTrue(archived_file.is_file(), archive_path)

            content = archived_file.read_bytes()
            self.assertEqual(len(content), record["bytes"], archive_path)
            self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"], archive_path)
            self.assertNotIn(archive_path, archived_paths)

            archived_paths.add(archive_path)
            records_by_source[source_path] = record

        self.assertEqual(set(records_by_source), set(ARCHIVED_SOURCES))

        for source_path in ARCHIVED_PROMPTS:
            record = records_by_source[source_path]
            self.assertTrue((REPOSITORY_ROOT / record["archive_path"]).is_file(), source_path)


if __name__ == "__main__":
    unittest.main()
