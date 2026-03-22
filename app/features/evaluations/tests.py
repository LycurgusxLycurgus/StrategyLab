from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.features.evaluations.service import EvaluationService
from app.infra.db import Database
from app.test_support import make_test_config


class EvaluationServiceTests(unittest.TestCase):
    def test_evaluates_equity_curve(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = make_test_config(Path(temp_dir))
            service = EvaluationService(Database(config))
            equity_curve = [{"ts": index, "equity": 10000 + index * 25, "drawdown": 0.01 if index % 7 == 0 else 0.0} for index in range(30)]
            trades = [{"exit_ts": index, "pnl": 25 if index % 3 else -10} for index in range(15)]
            result = service.evaluate("1H", equity_curve, trades)
            self.assertIn(result.verdict, {"rejected", "research_survivor", "paper_candidate"})
            self.assertGreaterEqual(len(result.fold_sharpes), 0)


if __name__ == "__main__":
    unittest.main()
