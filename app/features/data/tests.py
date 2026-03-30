from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from app.features.data.service import DataService
from app.storage import Repository


class DataFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.original_paths = (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
            settings.oanda_api_token,
        )
        settings.db_path = root / "test.sqlite3"
        settings.data_dir = root / "data"
        settings.run_dir = root / "runs"
        settings.report_dir = root / "reports"
        settings.paper_dir = root / "paper"
        settings.oanda_api_token = ""
        settings.ensure_dirs()
        self.service = DataService(Repository(settings.db_path))

    def tearDown(self) -> None:
        (
            settings.db_path,
            settings.data_dir,
            settings.run_dir,
            settings.report_dir,
            settings.paper_dir,
            settings.oanda_api_token,
        ) = self.original_paths
        self.tempdir.cleanup()

    def test_auto_provider_prefers_oanda_for_gold_when_token_exists(self) -> None:
        settings.oanda_api_token = "practice-token"
        self.assertEqual(self.service._resolve_provider("XAU_USD", "auto"), "oanda")

    def test_oanda_requires_token(self) -> None:
        with self.assertRaises(HTTPException):
            self.service._resolve_provider("XAU_USD", "oanda")

    def test_import_csv_dataset_accepts_common_ohlcv_headers(self) -> None:
        content = (
            "timestamp,open,high,low,close,volume\n"
            "2026-03-01T00:00:00Z,2850.1,2851.2,2849.8,2850.9,100\n"
            "2026-03-01T00:15:00Z,2850.9,2852.0,2850.2,2851.7,120\n"
        ).encode("utf-8")
        record = self.service.import_csv_dataset(
            content=content,
            filename="xau.csv",
            symbol="XAU_USD",
            timeframe="15m",
            name="manual-test",
        )
        self.assertEqual(record["rows_count"], 2)
        self.assertTrue(record["name"].startswith("manual-"))

    def test_import_histdata_ascii_m1_aggregates_to_15m(self) -> None:
        content = (
            "20250101 180000;2625.098000;2626.005000;2624.355000;2625.048000;0\n"
            "20250101 180100;2625.055000;2625.148000;2624.425000;2624.955000;0\n"
            "20250101 181400;2624.100000;2624.500000;2623.900000;2624.300000;0\n"
            "20250101 181500;2624.400000;2624.900000;2624.200000;2624.700000;0\n"
        ).encode("utf-8")
        record = self.service.import_csv_dataset(
            content=content,
            filename="DAT_ASCII_XAUUSD_M1_2025.csv",
            symbol="XAU_USD",
            timeframe="15m",
            name="histdata-test",
        )
        self.assertEqual(record["rows_count"], 2)
