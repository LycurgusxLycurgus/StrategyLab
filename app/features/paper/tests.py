from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import settings
from app.features.data.service import DataService
from app.features.paper.service import PaperService
from app.storage import Repository
from app.test_support import make_xau_fixture


class PaperFeatureTests(unittest.TestCase):
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
        fixture = make_xau_fixture(bars_count=760)
        fixture_path = settings.data_dir / "fixture.csv"
        self.data_service.write_bars(fixture_path, fixture)
        self.repo.upsert_dataset(
            {
                "dataset_id": "ds_fixture",
                "name": "fixture",
                "symbol": "GC=F",
                "timeframe": "15m",
                "rows_count": len(fixture),
                "path": str(fixture_path),
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )
        self.service = PaperService(self.repo, self.data_service)

    def tearDown(self) -> None:
        (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
        ) = self.original_paths
        self.tempdir.cleanup()

    def test_paper_week_generates_artifact(self) -> None:
        result = self.service.run_week("ds_fixture", "balanced", use_hybrid=False)
        self.assertIn("metrics", result)
        self.assertTrue(Path(result["artifact_path"]).exists())
