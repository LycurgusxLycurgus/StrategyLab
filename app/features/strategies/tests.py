from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.features.strategies.schema import StrategyDraftRequest
from app.features.strategies.service import StrategyService
from app.test_support import make_test_config, write_strategy_family, write_ui_files


class StrategyServiceTests(unittest.TestCase):
    def test_lists_and_creates_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_test_config(root)
            write_ui_files(config)
            write_strategy_family(config, "a_zero_srlc", "1H")
            service = StrategyService(config)
            families = service.list_families()
            self.assertEqual(len(families), 1)
            draft = service.create_draft(
                StrategyDraftRequest(
                    base_family_id="a_zero_srlc",
                    new_family_id="a_zero_clone",
                    title="A Zero Clone",
                    asset="BTCUSDT",
                    timeframe="1H",
                    parameter_overrides={"lookback_days": 75},
                )
            )
            self.assertEqual(draft.parameters["lookback_days"], 75)
            self.assertEqual(len(service.list_families()), 2)


if __name__ == "__main__":
    unittest.main()
