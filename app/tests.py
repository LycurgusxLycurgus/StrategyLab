from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.main import create_app
from app.test_support import make_test_config, write_strategy_family, write_ui_files


class AppSmokeTests(unittest.TestCase):
    def test_create_app_registers_core_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            write_strategy_family(config, "smart_money_structural", "5m")
            app = create_app(config)
            paths = {route.path for route in app.routes}
            self.assertIn("/health", paths)
            self.assertIn("/", paths)
            self.assertIn("/api/backtests/run", paths)


if __name__ == "__main__":
    unittest.main()
