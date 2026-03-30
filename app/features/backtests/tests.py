from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.config import settings
from app.features.backtests.service import BacktestService
from app.features.data.service import DataService
from app.storage import Repository
from app.test_support import make_xau_fixture


class BacktestFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.original_paths = (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
        )
        settings.db_path = root / "test.sqlite3"
        settings.data_dir = root / "data"
        settings.run_dir = root / "runs"
        settings.report_dir = root / "reports"
        settings.paper_dir = root / "paper"
        settings.ensure_dirs()
        self.repo = Repository(settings.db_path)
        self.data_service = DataService(self.repo)
        self.service = BacktestService(self.repo, self.data_service)
        fixture = make_xau_fixture()
        fixture_path = settings.data_dir / "fixture.csv"
        self.data_service.write_bars(fixture_path, fixture)
        self.dataset_id = "ds_fixture"
        self.repo.upsert_dataset(
            {
                "dataset_id": self.dataset_id,
                "name": "fixture",
                "symbol": "GC=F",
                "timeframe": "15m",
                "rows_count": len(fixture),
                "path": str(fixture_path),
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )

    def tearDown(self) -> None:
        (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
        ) = self.original_paths
        self.tempdir.cleanup()

    def test_whitebox_run_produces_candidates_and_report(self) -> None:
        result = self.service.run_whitebox(self.dataset_id, "balanced")
        self.assertGreaterEqual(len(result["candidates"]), 1)
        self.assertGreaterEqual(result["metrics"]["trades"], 1)
        self.assertTrue(Path(result["artifact_path"]).exists())
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertTrue(Path(result["trace_path"]).exists())
        trace = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(trace), 1)
        self.assertIn("session", trace[0])
        self.assertIn("rejection_reason", trace[0])

    def test_hybrid_run_writes_model_or_heuristic_artifact(self) -> None:
        result = self.service.run_hybrid(self.dataset_id, "balanced", threshold=0.55)
        self.assertIn("handoff_quality", result)
        self.assertIn("metrics", result)
        self.assertTrue(Path(result["artifact_path"]).exists())
        payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "hybrid")
        self.assertIn("baseline_run_id", payload)

    def test_tv_debug_export_is_created(self) -> None:
        result = self.service.run_whitebox(self.dataset_id, "balanced")
        export = self.service.build_tradingview_debug(result["run_id"])
        self.assertTrue(Path(export["pine_path"]).exists())
        pine_text = Path(export["pine_path"]).read_text(encoding="utf-8")
        self.assertIn("xloc=xloc.bar_time", pine_text)
        self.assertIn("var drawn = false", pine_text)
        self.assertIn("yloc.abovebar", pine_text)
        self.assertIn("yloc.belowbar", pine_text)

    def test_debug_trace_export_is_created_for_hybrid(self) -> None:
        result = self.service.run_hybrid(self.dataset_id, "balanced", threshold=0.55)
        export = self.service.build_debug_trace(result["run_id"])
        self.assertTrue(Path(export["trace_path"]).exists())
        self.assertIn("summary", export)
        self.assertEqual(export["artifact_group"], "reports")

    def test_debug_trace_export_declares_reports_group_for_whitebox(self) -> None:
        result = self.service.run_whitebox(self.dataset_id, "balanced")
        export = self.service.build_debug_trace(result["run_id"])
        self.assertTrue(Path(export["trace_path"]).exists())
        self.assertEqual(export["artifact_group"], "reports")
