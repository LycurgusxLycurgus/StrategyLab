from __future__ import annotations

import math
import socket
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.config import settings
from app.data import Bar, DataService
from app.lab import MutationLabService
from app.storage import Repository


def build_fixture_bars(count: int = 3200) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    price = 30000.0
    previous_close = price
    for index in range(count):
        regime = (index // 220) % 4
        drift = [9.0, -7.0, 5.5, -4.5][regime]
        wave = math.sin(index / 5.0) * 38 + math.sin(index / 19.0) * 66
        impulse = ((index % 87) - 43) * 0.9
        close = price + drift + wave + impulse
        open_price = previous_close + math.sin(index / 3.0) * 9
        high = max(open_price, close) + 18 + abs(math.sin(index / 7.0) * 11)
        low = min(open_price, close) - 18 - abs(math.cos(index / 9.0) * 11)
        volume = 400 + abs(math.sin(index / 11.0) * 180)
        bars.append(
            Bar(
                ts=start + timedelta(minutes=15 * index),
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=round(volume, 4),
                symbol="BTCUSDT",
                timeframe="15m",
            )
        )
        price = close + drift * 0.12
        previous_close = close
    return bars


class MutationLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original = {
            "db_path": settings.db_path,
            "data_dir": settings.data_dir,
            "run_dir": settings.run_dir,
            "report_dir": settings.report_dir,
            "seed_spec_path": settings.seed_spec_path,
        }
        settings.db_path = self.root / "artifacts" / "mutation_lab.sqlite3"
        settings.data_dir = self.root / "artifacts" / "data"
        settings.run_dir = self.root / "artifacts" / "runs"
        settings.report_dir = self.root / "artifacts" / "reports"
        settings.seed_spec_path = self.root / "strategies" / "btc_intraday_parent.json"
        settings.ensure_dirs()
        self.repo = Repository(settings.db_path)
        self.data_service = DataService(self.repo)
        self.lab = MutationLabService(self.repo, self.data_service)
        self.lab.ensure_seeded()

    def tearDown(self) -> None:
        settings.db_path = self.original["db_path"]
        settings.data_dir = self.original["data_dir"]
        settings.run_dir = self.original["run_dir"]
        settings.report_dir = self.original["report_dir"]
        settings.seed_spec_path = self.original["seed_spec_path"]
        self.temp_dir.cleanup()

    def test_seed_family_and_version_exist(self) -> None:
        family = self.repo.get_family("btc_intraday")
        self.assertIsNotNone(family)
        self.assertEqual(family["current_version_id"], "ver_btc_intraday_parent")
        version = self.repo.get_version("ver_btc_intraday_parent")
        self.assertIsNotNone(version)
        self.assertTrue(settings.seed_spec_path.exists())

    def test_run_parent_persists_metrics_and_artifacts(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        payload = self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        self.assertIn(payload["verdict"], {"graveyard", "research_survivor", "promotion_candidate"})
        self.assertGreater(payload["metrics"]["total_trades"], 0)
        self.assertTrue(Path(payload["artifact_path"]).exists())
        self.assertTrue(Path(payload["report_path"]).exists())
        stored_runs = self.repo.list_runs(family_id="btc_intraday")
        self.assertEqual(len(stored_runs), 1)

    def test_generate_white_box_proposals_and_run_pack(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        proposals = self.lab.generate_proposals("ver_btc_intraday_parent", include_hybrid=False)
        self.assertTrue(proposals)
        self.assertTrue(all(proposal["kind"] == "white_box" for proposal in proposals))
        result = self.lab.run_proposal_pack("ver_btc_intraday_parent", dataset["dataset_id"], include_hybrid=False)
        self.assertEqual(result["tested_count"], len(proposals))
        self.assertIsNotNone(result["best_run"])
        self.assertGreaterEqual(len(self.repo.list_runs(family_id="btc_intraday")), len(proposals) + 1)

    def test_tuning_edges_preview_and_save_tuned_child(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        edges = self.lab.list_tuning_edges("ver_btc_intraday_parent")
        self.assertTrue(edges)
        self.assertGreaterEqual(edges[0]["priority"], edges[-1]["priority"])
        preview = self.lab.preview_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["spec"]["parameters"]["stop_mult"], 4.0)
        self.assertIsNotNone(preview["comparison"])
        saved = self.lab.save_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        self.assertNotEqual(saved["version_id"], "ver_btc_intraday_parent")
        child = self.repo.get_version(saved["version_id"])
        self.assertEqual(child["mutation_json"]["origin"], "manual_parameter_tune")
        self.assertEqual(child["spec_json"]["parameters"]["stop_mult"], 4.0)
        child_edges = self.lab.list_tuning_edges(saved["version_id"])
        stop_edge = next(edge for edge in child_edges if edge["lever"] == "stop_mult")
        self.assertEqual(stop_edge["current_value"], 4.0)

    def test_promote_child_updates_current_version(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        proposal = self.lab.generate_proposals("ver_btc_intraday_parent")[0]
        run_payload = self.lab.run_proposal(proposal["proposal_id"], dataset["dataset_id"])
        detail = self.lab.promote_version("btc_intraday", run_payload["version_id"])
        self.assertEqual(detail["family"]["current_version_id"], run_payload["version_id"])

    def test_delete_non_current_child_version_cascades_runs(self) -> None:
        dataset = self.data_service.import_fixture_dataset(
            build_fixture_bars(),
            symbol="BTCUSDT",
            timeframe="15m",
            name="fixture-btc-15m",
        )
        self.lab.run_version("ver_btc_intraday_parent", dataset["dataset_id"])
        saved = self.lab.save_tuned_version(
            "ver_btc_intraday_parent",
            dataset["dataset_id"],
            {"stop_mult": 4.0, "max_no_cross": 4},
        )
        child_version_id = saved["version_id"]
        detail = self.lab.delete_version(child_version_id)
        self.assertEqual(detail["family"]["current_version_id"], "ver_btc_intraday_parent")
        self.assertIsNone(self.repo.get_version(child_version_id))
        child_runs = [run for run in self.repo.list_runs(family_id="btc_intraday") if run["version_id"] == child_version_id]
        self.assertEqual(child_runs, [])

    def test_binance_downloader_uses_explicit_start_time_for_history_window(self) -> None:
        urls: list[str] = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(url, timeout=30):
            del timeout
            urls.append(url)
            return FakeResponse(None)

        payload = [
            [
                1_700_000_000_000,
                "100.0",
                "101.0",
                "99.0",
                "100.5",
                "123.0",
                1_700_000_900_000,
                "0",
                "0",
                "0",
                "0",
                "0",
            ]
        ]
        with patch("app.data.urlopen", side_effect=fake_urlopen), patch("app.data.json.load", return_value=payload):
            bars = self.data_service._download_klines("BTCUSDT", "15m", 40000, full_history=False)
        self.assertEqual(len(bars), 1)
        self.assertTrue(urls)
        self.assertIn("startTime=", urls[0])

    def test_binance_full_history_timeout_is_wrapped_in_operator_friendly_http_error(self) -> None:
        with patch("app.data.urlopen", side_effect=socket.timeout("timed out")), patch("app.data.time.sleep"):
            with self.assertRaises(HTTPException) as ctx:
                self.data_service.download_binance_dataset("BTCUSDT", "15m", 40000, True, None)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("full-history download timed out", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
