from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.features.data.schema import BinanceDatasetRequest, DemoDatasetRequest, ImportDatasetRequest
from app.features.data.service import DataService
from app.infra.db import Database
from app.test_support import make_test_config, write_csv, write_ui_files


class DataServiceTests(unittest.TestCase):
    def test_imports_and_lists_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            csv_path = config.app_data_dir / "btc_1h.csv"
            write_csv(csv_path, "1H")
            service = DataService(config, Database(config))
            result = service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="1H", dataset_name="btc-1h")
            )
            self.assertEqual(result.timeframe, "1H")
            datasets = service.list_datasets()
            self.assertEqual(len(datasets), 1)
            self.assertEqual(datasets[0].dataset_id, result.dataset_id)

    def test_creates_demo_dataset_without_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            service = DataService(config, Database(config))
            result = service.create_demo_dataset(
                DemoDatasetRequest(symbol="BTCUSDT", timeframe="1H", dataset_name="demo-btc-1h", bars=240)
            )
            self.assertEqual(result.dataset_name, "demo-btc-1h")
            self.assertTrue(Path(result.source_path).exists())
            self.assertEqual(result.row_count, 240)

    def test_deletes_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            csv_path = config.app_data_dir / "btc_1h.csv"
            write_csv(csv_path, "1H")
            service = DataService(config, Database(config))
            result = service.import_dataset(
                ImportDatasetRequest(path=str(csv_path), symbol="BTCUSDT", timeframe="1H", dataset_name="btc-1h")
            )
            deleted = service.delete_dataset(result.dataset_id)
            self.assertTrue(deleted["deleted"])
            self.assertEqual(service.list_datasets(), [])

    def test_downloads_binance_dataset_without_manual_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            service = DataService(config, Database(config))

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    rows = [
                        [1700000000000 + index * 3600000, "30000", "30100", "29900", "30050", "100", 0, 0, 0, 0, 0, 0]
                        for index in range(120)
                    ]
                    import json

                    return json.dumps(rows).encode("utf-8")

            with patch("app.features.data.service.urlopen", return_value=FakeResponse()):
                result = service.import_binance_dataset(
                    BinanceDatasetRequest(symbol="BTCUSDT", timeframe="1H", dataset_name="binance-btc-1h", bars=120)
                )
            self.assertEqual(result.row_count, 120)
            self.assertTrue(Path(result.source_path).exists())

    def test_downloads_more_than_one_thousand_binance_bars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            service = DataService(config, Database(config))

            payloads = [
                [
                    [1700000000000 + index * 3600000, "30000", "30100", "29900", "30050", "100", 0, 0, 0, 0, 0, 0]
                    for index in range(500, 1500)
                ],
                [
                    [1700000000000 + index * 3600000, "30000", "30100", "29900", "30050", "100", 0, 0, 0, 0, 0, 0]
                    for index in range(500)
                ],
            ]

            class FakeResponse:
                def __init__(self, rows):
                    self.rows = rows

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    import json

                    return json.dumps(self.rows).encode("utf-8")

            def fake_urlopen(url, timeout):
                return FakeResponse(payloads.pop(0))

            with patch("app.features.data.service.urlopen", side_effect=fake_urlopen):
                result = service.import_binance_dataset(
                    BinanceDatasetRequest(symbol="BTCUSDT", timeframe="1H", dataset_name="binance-btc-1h-1500", bars=1500)
                )
            self.assertEqual(result.row_count, 1500)
            self.assertTrue(Path(result.source_path).exists())


if __name__ == "__main__":
    unittest.main()
