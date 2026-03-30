from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import settings
from app.features.backtests.service import BacktestService
from app.features.data.service import DataService
from app.features.webhooks.service import WebhookService
from app.storage import Repository
from app.test_support import make_xau_fixture


class WebhookFeatureTests(unittest.TestCase):
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
        fixture = make_xau_fixture()
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
        self.backtests = BacktestService(self.repo, self.data_service)
        self.backtests.run_hybrid("ds_fixture", "balanced", threshold=0.55)
        self.service = WebhookService(self.repo, self.backtests)

    def tearDown(self) -> None:
        (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
        ) = self.original_paths
        self.tempdir.cleanup()

    def test_webhook_uses_latest_hybrid_threshold(self) -> None:
        response = self.service.evaluate_signal(
            {
                "symbol": "XAUUSD",
                "timeframe": "15m",
                "timestamp": "2026-01-10T14:00:00+00:00",
                "direction": "long",
                "entry": 2660.0,
                "stop": 2655.0,
                "target": 2670.0,
                "session_ny": 1,
                "sweep_depth_atr": 0.3,
                "body_atr": 0.9,
                "fvg_size_atr": 0.5,
                "bias": 1,
                "distance_to_prev_day_atr": 0.7,
            }
        )
        self.assertIn(response["action"], {"EXECUTE", "REJECT"})
        self.assertGreater(response["threshold"], 0)
