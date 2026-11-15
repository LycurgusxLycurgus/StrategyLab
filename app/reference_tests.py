"""Independent expected cases for the two registered reference consumers.

The candles and decision expectations below are authored from the frozen rule
contract. They are intentionally not generated from ``run_reference`` output.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.data import INTERVAL_MS, Bar, DataService
from app.lab import MutationLabService
from app.reference import (
    EXECUTION_CONTRACT,
    audit_ledger,
    effective_parameters,
    run_reference,
    simulate,
)
from app.reference_evidence import EvidenceService, provenance
from app.storage import Repository


def _serialized_bars(
    closes: list[float],
    *,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> list[dict[str, Any]]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    output: list[dict[str, Any]] = []
    previous_close = closes[0]
    for index, close in enumerate(closes):
        open_price = closes[0] if index == 0 else previous_close
        high = highs[index] if highs else max(open_price, close) + 1
        low = lows[index] if lows else min(open_price, close) - 1
        output.append(
            {
                "ts": (start + timedelta(minutes=15 * index)).isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 100.0,
                "symbol": "CASE",
                "timeframe": "15m",
            }
        )
        previous_close = close
    return output


def _bars(case_bars: list[dict[str, Any]]) -> list[Bar]:
    return [Bar(**{**row, "ts": datetime.fromisoformat(row["ts"])}) for row in case_bars]


def _spec(engine_id: str, **parameters: Any) -> dict[str, Any]:
    return {
        "workflow_version": "reference_v1",
        "engine_id": engine_id,
        "timeframe": "15m",
        "strategy_origin": "systematic_native",
        "development_operation": "create",
        "translation_objective": "not_applicable",
        "execution_contract": dict(EXECUTION_CONTRACT),
        "parameters": parameters,
    }


def _execution_bars(rows: list[tuple[float, float, float, float]]) -> list[Bar]:
    start = datetime(2024, 2, 1, tzinfo=UTC)
    return [
        Bar(
            ts=start + timedelta(minutes=15 * index),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=100,
            symbol="CASE",
            timeframe="15m",
        )
        for index, (open_price, high, low, close) in enumerate(rows)
    ]


def _intent(bars: list[Bar], index: int, direction: int, risk_distance: float) -> dict[str, Any]:
    decision_at = int(
        (bars[index].ts + timedelta(minutes=15)).timestamp() * 1000
    )
    return {
        "intent_id": f"fixture:{index}:{direction}",
        "bar_index": index,
        "direction": direction,
        "source_at": decision_at,
        "known_at": decision_at,
        "decision_at": decision_at,
        "earliest_submission": decision_at,
        "risk_distance": risk_distance,
    }


def reference_expected_cases() -> list[dict[str, Any]]:
    """Return serialized bars and independently written decision expectations."""
    ma_bars = _serialized_bars([10, 9, 8, 9, 10, 11, 10, 9, 8, 7, 8, 9])
    pivot_bars = _serialized_bars(
        [10, 11, 12, 13, 12, 16, 17], highs=[12, 13, 15, 14, 13, 17, 18]
    )
    equal_high_bars = _serialized_bars(
        [10, 11, 12, 13, 12, 14, 15], highs=[12, 13, 15, 15, 13, 16, 17]
    )
    replacement_bars = _serialized_bars(
        [10, 11, 12, 13, 12, 14, 13, 14, 14, 13, 16, 19, 20],
        highs=[12, 13, 15, 14, 13, 15, 14, 18, 15, 14, 17, 20, 21],
    )
    ttl_bars = _serialized_bars(
        [10, 11, 12, 13, 12, 13, 14, 16],
        highs=[12, 13, 15, 14, 13, 14, 15, 17],
    )
    return [
        {
            "name": "ma_cross_sma_accepts_each_crossover_once",
            "bars": ma_bars,
            "expected_decisions": [
                {"bar_index": 4, "direction": 1, "reason": "accepted"},
                {"bar_index": 7, "direction": -1, "reason": "accepted"},
                {"bar_index": 11, "direction": 1, "reason": "accepted"},
            ],
        },
        {
            "name": "ma_cross_atr_gate_rejects_candidates",
            "bars": ma_bars,
            "expected_decisions": [
                {"bar_index": 4, "direction": 0, "reason": "atr_gate"},
                {"bar_index": 7, "direction": 0, "reason": "atr_gate"},
                {"bar_index": 11, "direction": 0, "reason": "atr_gate"},
            ],
        },
        {
            "name": "ma_cross_disabled_direction_is_recorded_as_rejected",
            "bars": ma_bars,
            "expected_decisions": [
                {"bar_index": 4, "direction": 0, "reason": "direction_disabled"},
                {"bar_index": 7, "direction": -1, "reason": "accepted"},
                {"bar_index": 11, "direction": 0, "reason": "direction_disabled"},
            ],
        },
        {
            "name": "pivot_bos_waits_for_right_confirmation_and_consumes_once",
            "bars": pivot_bars,
            "expected_decisions": [
                {"bar_index": 5, "direction": 1, "reason": "accepted"}
            ],
        },
        {
            "name": "pivot_equal_neighbor_is_not_a_strict_pivot",
            "bars": equal_high_bars,
            "expected_decisions": [],
        },
        {
            "name": "pivot_replacement_invalidates_old_level",
            "bars": replacement_bars,
            "expected_decisions": [
                {"bar_index": 11, "direction": 1, "reason": "accepted"}
            ],
        },
        {
            "name": "pivot_level_expires_before_late_bos",
            "bars": ttl_bars,
            "expected_decisions": [],
        },
    ]


class ReferenceExpectedCaseTests(unittest.TestCase):
    def test_ma_cross_matches_independent_acceptance_and_gate_cases(self) -> None:
        cases = reference_expected_cases()[:3]
        specs = [
            _spec(
                "reference_ma_cross_v1",
                fast_len=2,
                slow_len=3,
                atr_len=2,
                min_atr=0,
            ),
            _spec(
                "reference_ma_cross_v1",
                fast_len=2,
                slow_len=3,
                atr_len=2,
                min_atr=1000,
            ),
            _spec(
                "reference_ma_cross_v1",
                fast_len=2,
                slow_len=3,
                atr_len=2,
                min_atr=0,
                allow_long=False,
            ),
        ]
        for case, spec in zip(cases, specs, strict=True):
            with self.subTest(case=case["name"]):
                result = run_reference(spec, _bars(case["bars"]))
                self.assertEqual(case["expected_decisions"], result["decisions"])

    def test_pivot_expected_cases_reject_early_equal_replaced_and_expired_levels(
        self,
    ) -> None:
        cases = reference_expected_cases()[3:]
        specs = [
            _spec(
                "reference_pivot_bos_v1", pivot_left=2, pivot_right=2, atr_len=2
            ),
            _spec(
                "reference_pivot_bos_v1", pivot_left=2, pivot_right=2, atr_len=2
            ),
            _spec(
                "reference_pivot_bos_v1", pivot_left=2, pivot_right=2, atr_len=2
            ),
            _spec(
                "reference_pivot_bos_v1",
                pivot_left=2,
                pivot_right=2,
                atr_len=2,
                level_ttl=2,
            ),
        ]
        for case, spec in zip(cases, specs, strict=True):
            with self.subTest(case=case["name"]):
                result = run_reference(spec, _bars(case["bars"]))
                self.assertEqual(case["expected_decisions"], result["decisions"])

    def test_bos_before_or_on_confirmation_fails_and_prefix_is_censored(self) -> None:
        case = reference_expected_cases()[3]
        spec = _spec(
            "reference_pivot_bos_v1", pivot_left=2, pivot_right=2, atr_len=2
        )
        bars = _bars(case["bars"])
        complete = run_reference(spec, bars)
        prefix = run_reference(spec, bars[:5])

        # The high at index 2 is not knowable until index 4 closes; BOS at 5
        # is the first eligible decision. A detector that leaks earlier fails.
        self.assertEqual(case["expected_decisions"], complete["decisions"])
        self.assertFalse(prefix["decisions"])
        self.assertTrue(any(event["event_type"] == "censored" for event in prefix["ledger"]))
        confirmed = next(
            event
            for event in complete["ledger"]
            if event["event_type"] == "confirmed" and event["reason"] == "pivot_confirmed"
        )
        consumed = next(
            event for event in complete["ledger"] if event["event_type"] == "consumed"
        )
        self.assertLess(confirmed["source_at"], confirmed["known_at"])
        self.assertEqual(confirmed["known_at"], consumed["known_at"])
        self.assertLess(confirmed["known_at"], consumed["decision_at"])
        self.assertEqual(1, sum(e["event_type"] == "consumed" for e in complete["ledger"]))

    def test_direct_reference_run_rejects_blocked_raw_data_audit(self) -> None:
        case = reference_expected_cases()[0]
        bars = _bars(case["bars"])
        bars[3] = Bar(
            ts=bars[3].ts,
            open=bars[3].open,
            high=bars[3].close - 1,
            low=bars[3].low,
            close=bars[3].close,
            volume=bars[3].volume,
            symbol=bars[3].symbol,
            timeframe=bars[3].timeframe,
        )
        with self.assertRaises(HTTPException) as context:
            run_reference(
                _spec(
                    "reference_ma_cross_v1",
                    fast_len=2,
                    slow_len=3,
                    atr_len=2,
                ),
                bars,
            )
        self.assertEqual("REFERENCE_DATA_INVALID", context.exception.detail["code"])

    def test_trace_collection_does_not_change_decisions_or_execution(self) -> None:
        case = reference_expected_cases()[0]
        spec = _spec(
            "reference_ma_cross_v1",
            fast_len=2,
            slow_len=3,
            atr_len=2,
        )
        bars = _bars(case["bars"])
        traced = run_reference(spec, bars, collect_ledger=True)
        untraced = run_reference(spec, bars, collect_ledger=False)

        for field in (
            "decisions",
            "order_intents",
            "trades",
            "equity_curve",
            "trace",
        ):
            with self.subTest(field=field):
                self.assertEqual(traced[field], untraced[field])
        self.assertTrue(traced["ledger"])
        self.assertFalse(untraced["ledger"])

        cost_spec = {
            **spec,
            "parameters": {
                **spec["parameters"],
                "commission_pct": 1,
                "slippage_ticks": 2,
            },
        }
        costly = run_reference(cost_spec, bars)
        self.assertEqual(traced["decisions"], costly["decisions"])
        self.assertNotEqual(traced["trades"], costly["trades"])

    def test_execution_next_open_gap_cost_ambiguity_cutoff_and_single_position(self) -> None:
        # A decision at bar 0's close fills at bar 1's opening gap, then the
        # next opening gap crosses the stop and receives the gap price.
        gap_bars = _execution_bars(
            [(100, 101, 99, 100), (105, 106, 104, 105), (100, 101, 98, 99)]
        )
        gap_result = simulate(
            [_intent(gap_bars, 0, 1, 4)],
            gap_bars,
            {"quantity": 1, "stop_mult": 2, "tick_size": 0.01},
            INTERVAL_MS["15m"],
        )
        first_open = next(
            event
            for event in gap_result["ledger"]
            if event["event_type"] == "fill" and event["status"] == "opened"
        )
        self.assertEqual(1, first_open["bar_index"])
        self.assertEqual("next_open", first_open["reason"])
        self.assertEqual(105, first_open["price"])
        self.assertEqual("stop_gap", gap_result["trades"][0]["reason"])
        self.assertEqual(100, gap_result["trades"][0]["exit_price"])

        # One OHLC bar touches both target and stop; adverse stop-first wins.
        ambiguous_bars = _execution_bars(
            [(100, 101, 99, 100), (100, 106, 94, 100)]
        )
        ambiguous = simulate(
            [_intent(ambiguous_bars, 0, 1, 5)],
            ambiguous_bars,
            {
                "quantity": 1,
                "tick_size": 0.5,
                "slippage_ticks": 2,
                "commission_pct": 1,
                "target_r": 1,
            },
            INTERVAL_MS["15m"],
        )
        trade = ambiguous["trades"][0]
        self.assertEqual("ambiguous_stop_first", trade["reason"])
        self.assertEqual(95, trade["exit_price"])
        self.assertEqual(1.96, trade["commission"])
        self.assertEqual(-6, trade["gross_pnl"])
        self.assertEqual(-7.96, trade["net_pnl"])

        # Same-direction overlap is canceled; opposite direction closes then
        # reverses. The cutoff leaves the final open position censored.
        position_bars = _execution_bars(
            [(100, 101, 99, 100)] * 5
        )
        positions = simulate(
            [
                _intent(position_bars, 0, 1, 50),
                _intent(position_bars, 1, 1, 50),
                _intent(position_bars, 2, -1, 50),
            ],
            position_bars,
            {"quantity": 1, "tick_size": 0.01},
            INTERVAL_MS["15m"],
        )
        self.assertEqual([0, 1, 1, -1, -1], positions["positions"])
        self.assertEqual("reverse", positions["trades"][0]["reason"])
        self.assertIn(
            "position_concurrency",
            [event["reason"] for event in positions["ledger"]],
        )
        self.assertIn(
            "position_open_at_cutoff",
            [event["reason"] for event in positions["ledger"]],
        )

        pending = simulate(
            [_intent(position_bars, len(position_bars) - 1, 1, 50)],
            position_bars,
            {"quantity": 1},
            INTERVAL_MS["15m"],
        )
        self.assertIn(
            "intent_pending_at_cutoff",
            [event["reason"] for event in pending["ledger"]],
        )

    def test_causality_audit_rejects_an_early_decision(self) -> None:
        event = {
            "event_id": "early-bos",
            "source_at": 1_704_067_200_000,
            "known_at": 1_704_067_560_000,
            "decision_at": 1_704_067_380_000,
            "earliest_submission": None,
            "fill_at": None,
        }
        with self.assertRaises(HTTPException) as raised:
            audit_ledger([event])
        self.assertEqual("CAUSALITY_VIOLATION", raised.exception.detail["code"])


class ReferenceEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original = {
            "db_path": settings.db_path,
            "data_dir": settings.data_dir,
            "run_dir": settings.run_dir,
            "report_dir": settings.report_dir,
            "diagnostic_dir": settings.diagnostic_dir,
            "tg_snapshot_dir": settings.tg_snapshot_dir,
            "tg_experiment_dir": settings.tg_experiment_dir,
            "strategy_specs_dir": settings.strategy_specs_dir,
            "pine_development_dir": settings.pine_development_dir,
        }
        settings.db_path = self.root / "artifacts" / "lab.sqlite3"
        settings.data_dir = self.root / "artifacts" / "data"
        settings.run_dir = self.root / "artifacts" / "runs"
        settings.report_dir = self.root / "artifacts" / "reports"
        settings.diagnostic_dir = self.root / "artifacts" / "diagnostics"
        settings.tg_snapshot_dir = self.root / "artifacts" / "tg-snapshots"
        settings.tg_experiment_dir = self.root / "artifacts" / "tg-experiments"
        settings.strategy_specs_dir = self.root / "strategies"
        settings.pine_development_dir = self.root / "artifacts" / "strategy-development"
        settings.ensure_dirs()
        self.repo = Repository(settings.db_path)
        self.data = DataService(self.repo)
        self.lab = MutationLabService(self.repo, self.data)
        self.cases = [reference_expected_cases()[2]]
        self.bars = _bars(self.cases[0]["bars"])
        self.dataset = self.data.import_fixture_dataset(
            self.bars, "CASE", "15m", "reference-evidence-fixture"
        )
        self.dataset_id = self.dataset["dataset_id"]
        self.source_code = "systematic-native reference fixture"
        self.spec = _spec(
            "reference_ma_cross_v1",
            fast_len=2,
            slow_len=3,
            atr_len=2,
            allow_long=False,
            stop_mult=2,
        )
        self.version = {
            "version_id": "ver_reference_fixture",
            "family_id": "family_reference_fixture",
            "parent_version_id": None,
            "name": "Reference fixture",
            "stage": "reference_spec",
            "source_code": self.source_code,
            "spec_json": self.spec,
            "causal_story": "Independent crossover fixture.",
            "mutation_json": {},
            "notes": "test fixture",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_family(
            {
                "family_id": self.version["family_id"],
                "title": "Reference fixture",
                "asset": "CASE",
                "venue": "Fixture",
                "timeframe": "15m",
                "current_version_id": self.version["version_id"],
                "created_at": self.version["created_at"],
            }
        )
        self.repo.put_version(self.version)
        self.evidence = EvidenceService(self.repo, self.data)

    def tearDown(self) -> None:
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.temp_dir.cleanup()

    def assert_error_code(self, expected: str, action: Any) -> None:
        with self.assertRaises(HTTPException) as context:
            action()
        detail = context.exception.detail
        self.assertEqual(
            expected, detail.get("code") if isinstance(detail, dict) else None
        )

    @staticmethod
    def _transformation(*, changed: bool = False) -> dict[str, Any]:
        return {
            "parent_rule_id": "entry.selection",
            "child_rule_id": "entry.selection",
            "operation": "formalize" if not changed else "substitute",
            "rationale": "Make selection executable and testable.",
            "source_evidence": "source locator or parent version",
            "ambiguity_or_problem": "Selection timing requires explicit treatment.",
            "executable_choice": "Use a confirmed pivot and later close break.",
            "meaning_change": changed,
            "expected_effect": "Changes which observations can trigger an entry.",
            "validation_evidence": "Independent bar cases rerun on child spec.",
        }

    def test_origin_operation_scenarios_a_through_f_and_negative_controls(self) -> None:
        native_create = _spec("reference_ma_cross_v1", fast_len=2, slow_len=3)
        provenance(native_create)

        native_replicate = {
            **native_create,
            "development_operation": "replicate",
            "source_mapping": [
                {"source_rule_id": "cross", "reference_rule_id": "cross"}
            ],
        }
        provenance(native_replicate)

        parent = {"spec_json": native_create, "version_id": "parent-create"}
        native_improve = {
            **native_create,
            "development_operation": "improve",
            "development_authorization": "authorized test objective",
            "operation_transition": {"from": "create", "to": "improve"},
            "transformations": [self._transformation(changed=True)],
        }
        provenance(native_improve, parent)

        discretionary_translate = {
            **native_create,
            "strategy_origin": "discretionary_origin",
            "development_operation": "translate",
            "translation_objective": "fidelity_oriented",
            "interpretation": {
                "selection": "strict pivot confirmation then later close break"
            },
            "ambiguities": ["Displacement threshold is not defined in source."],
            "transformations": [self._transformation()],
        }
        provenance(discretionary_translate)

        discretionary_adapt = {
            **discretionary_translate,
            "development_operation": "improve",
            "translation_objective": "performance_oriented",
            "development_authorization": "frequency objective with fixed holdout",
            "operation_transition": {"from": "translate", "to": "improve"},
            "transformations": [self._transformation(changed=True)],
        }
        provenance(discretionary_adapt, {"spec_json": discretionary_translate})

        hybrid_translate = {
            **discretionary_translate,
            "strategy_origin": "hybrid",
            "rule_group_origins": {
                "indicator": "systematic_native",
                "selection": "discretionary_origin",
            },
        }
        provenance(hybrid_translate)

        missing_ambiguity = {**discretionary_translate, "ambiguities": []}
        self.assert_error_code(
            "INTERPRETATION_REQUIRED", lambda: provenance(missing_ambiguity)
        )
        undocumented_child = {**native_improve, "operation_transition": None}
        self.assert_error_code(
            "OPERATION_TRANSITION_REQUIRED",
            lambda: provenance(undocumented_child, parent),
        )
        false_equivalence = {
            **discretionary_translate,
            "claim_exact_source": True,
            "transformations": [self._transformation(changed=True)],
        }
        self.assert_error_code(
            "FALSE_SOURCE_EQUIVALENCE", lambda: provenance(false_equivalence)
        )
        self.assert_error_code(
            "PROVISIONAL_REFERENCE",
            lambda: provenance({**native_create, "provisional": True}),
        )

    def test_evidence_requires_semantics_baseline_authorization_and_holdout_split(self) -> None:
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(self.version, self.dataset_id, "run"),
        )
        saved = self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", saved["gates"]["semantic"]["status"])
        self.assertEqual("PASSED", saved["gates"]["data"]["status"])
        self.assertIn("execution", saved["gates"])
        self.evidence.require(self.version, self.dataset_id, "run")
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(self.version, self.dataset_id, "search"),
        )

        self.evidence.baseline(
            self.version,
            self.dataset_id,
            {"run_id": "run-fixture", "metrics": {"net_pnl": 0}},
        )
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(self.version, self.dataset_id, "search"),
        )
        bars = self.data.load_bars(self.dataset_id)
        train_end = bars[7].ts + timedelta(minutes=15)
        holdout_start = bars[8].ts + timedelta(minutes=15)
        authorization = {
            "objective": "bounded test mutation",
            "objective_metric": "existing_score_v1",
            "parameters": {"fast_len": [1, 2]},
            "train_end": train_end.isoformat(),
            "holdout_start": holdout_start.isoformat(),
        }
        self.evidence.authorize(
            self.version["version_id"], self.dataset_id, authorization
        )
        self.assertEqual(
            authorization,
            self.evidence.require(self.version, self.dataset_id, "search"),
        )
        expanded = {
            **authorization,
            "train_end": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.assert_error_code(
            "SEARCH_AUTHORIZATION_INVALID",
            lambda: self.evidence.authorize(
                self.version["version_id"], self.dataset_id, expanded
            ),
        )
        training = self.evidence.training_bars(self.version, self.dataset_id, bars)
        self.assertTrue(training)
        self.assertLess(training[-1].ts, holdout_start)
        outside = {
            **self.spec,
            "parameters": {**self.spec["parameters"], "fast_len": 9},
        }
        self.assert_error_code(
            "SEARCH_DOMAIN_UNAUTHORIZED",
            lambda: self.evidence.require(
                self.version, self.dataset_id, "search", outside
            ),
        )

    def test_evidence_artifact_tampering_is_detected(self) -> None:
        saved = self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        artifact_path = Path(saved["artifact_path"])
        artifact_path.write_bytes(artifact_path.read_bytes() + b"tamper")
        self.assert_error_code(
            "EVIDENCE_TAMPERED",
            lambda: self.evidence.require(self.version, self.dataset_id, "run"),
        )

    def test_casebook_hash_is_checked_on_api_readback(self) -> None:
        import html
        from unittest.mock import patch

        import app.main as api

        saved = self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        casebook_path = Path(saved["casebook_path"])
        casebook_record = next(
            record
            for record in self.repo.list_workflow_evidence(
                self.version["version_id"], self.dataset_id
            )
            if record["kind"] == "validation"
        )
        payload = json.loads(Path(casebook_record["artifact_path"]).read_text("utf-8"))
        self.assertEqual(
            hashlib.sha256(casebook_path.read_bytes()).hexdigest(),
            payload["casebook_sha256"],
        )
        casebook_html = casebook_path.read_text("utf-8")
        saved_event = payload["ledger"][0]
        self.assertTrue(
            {"prior_state", "next_state", "rule_id", "evidence"}.issubset(
                saved_event
            )
        )
        escaped_event = html.escape(
            json.dumps(saved_event, sort_keys=True, indent=2)
        )
        self.assertIn(
            f"<details><summary>Full event</summary><pre>{escaped_event}</pre></details>",
            casebook_html,
        )
        for field in ("prior_state", "next_state", "rule_id", "evidence"):
            self.assertIn(f"&quot;{field}&quot;", escaped_event)
        with patch.object(api, "lab", self.lab):
            self.assertEqual(casebook_path.resolve(), api.reference_casebook(
                self.version["version_id"], self.dataset_id
            ).path.resolve())
            casebook_path.write_bytes(casebook_path.read_bytes() + b"tamper")
            self.assert_error_code(
                "CASEBOOK_TAMPERED",
                lambda: api.reference_casebook(
                    self.version["version_id"], self.dataset_id
                ),
            )

    def test_changed_dataset_or_quality_identity_stales_prior_validation(self) -> None:
        self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        dataset_path = Path(self.dataset["path"])
        dataset_path.write_bytes(dataset_path.read_bytes() + b"\n")
        self.assertEqual(
            "STALE", self.data.dataset_quality_manifest(self.dataset_id)["status"]
        )
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(self.version, self.dataset_id, "run"),
        )
        self.assert_error_code(
            "RAW_DATA_AUDIT_STALE",
            lambda: self.evidence.validate(
                self.version["version_id"], self.dataset_id, self.cases
            ),
        )

    def test_malformed_quality_sidecar_blocks_instead_of_becoming_unverified(self) -> None:
        manifest = self.data.dataset_quality_manifest(self.dataset_id)
        Path(manifest["artifact_path"]).write_bytes(b"[]")
        self.assertEqual(
            "STALE", self.data.dataset_quality_manifest(self.dataset_id)["status"]
        )
        self.assert_error_code(
            "RAW_DATA_AUDIT_STALE",
            lambda: self.evidence.validate(
                self.version["version_id"], self.dataset_id, self.cases
            ),
        )

    def test_indicator_first_reference_has_no_orders_then_child_revalidates(self) -> None:
        indicator_spec = {**self.spec, "component_kind": "indicator"}
        indicator_result = run_reference(indicator_spec, self.bars)
        self.assertTrue(indicator_result["decisions"])
        self.assertFalse(indicator_result["order_intents"])
        self.assertFalse(indicator_result["trades"])
        indicator_version = {
            **self.version,
            "version_id": "ver_indicator_parent",
            "name": "Indicator first",
            "spec_json": indicator_spec,
        }
        self.repo.put_version(indicator_version)
        self.evidence.validate(
            indicator_version["version_id"], self.dataset_id, self.cases
        )
        self.lab.run_version(indicator_version["version_id"], self.dataset_id)
        self.evidence.authorize(
            indicator_version["version_id"],
            self.dataset_id,
            {
                "objective": "Add a strategy rule while preserving the accepted indicator parameters.",
                "parameters": {"stop_mult": [2]},
                "train_end": (self.bars[7].ts + timedelta(minutes=15)).isoformat(),
                "holdout_start": (self.bars[8].ts + timedelta(minutes=15)).isoformat(),
            },
        )
        child_spec = {
            **indicator_spec,
            "component_kind": "strategy",
            "development_operation": "improve",
            "development_authorization": "Add a first execution rule after indicator acceptance.",
            "operation_transition": {"from": "create", "to": "improve"},
            "transformations": [self._transformation(changed=True)],
        }
        child = self.lab.create_reference_child(
            indicator_version["version_id"],
            self.dataset_id,
            child_spec,
            "Indicator strategy child",
        )
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(child, self.dataset_id, "run"),
        )
        child_evidence = self.evidence.validate(
            child["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", child_evidence["gates"]["semantic"]["status"])

    def test_replication_fidelity_requires_hashed_source_oracle_not_proxy_status(self) -> None:
        source = "original deterministic source bytes"
        replicate_spec = {
            **self.spec,
            "development_operation": "replicate",
            "source_mapping": [
                {"source_rule_id": "cross", "reference_rule_id": "cross"}
            ],
        }
        replica = {
            **self.version,
            "version_id": "ver_replica_missing_oracle",
            "source_code": source,
            "spec_json": replicate_spec,
        }
        self.repo.put_version(replica)
        self.assert_error_code(
            "SOURCE_EQUIVALENCE_REQUIRED",
            lambda: self.evidence.validate(
                replica["version_id"], self.dataset_id, self.cases
            ),
        )

        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        oracle = {
            "authority": "proxy_status_only",
            "source_hash": source_hash,
            "cases": self.cases,
        }
        encoded = json.dumps(oracle, sort_keys=True, separators=(",", ":")).encode()
        oracle_path = settings.pine_development_dir / "oracles" / "replica.json"
        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_bytes(encoded)
        replica["spec_json"] = {
            **replicate_spec,
            "source_oracle": {
                "artifact_path": str(oracle_path),
                "artifact_sha256": hashlib.sha256(encoded).hexdigest(),
            },
        }
        self.repo.put_version(replica)
        self.assert_error_code(
            "SOURCE_EQUIVALENCE_REQUIRED",
            lambda: self.evidence.validate(
                replica["version_id"], self.dataset_id, self.cases
            ),
        )

        oracle["authority"] = "expert_adjudication"
        encoded = json.dumps(oracle, sort_keys=True, separators=(",", ":")).encode()
        oracle_path.write_bytes(encoded)
        replica["spec_json"]["source_oracle"]["artifact_sha256"] = hashlib.sha256(
            encoded
        ).hexdigest()
        self.repo.put_version(replica)
        accepted = self.evidence.validate(
            replica["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", accepted["gates"]["source_fidelity"]["status"])
        oracle_path.write_bytes(encoded + b"tamper")
        self.assert_error_code(
            "SOURCE_ORACLE_TAMPERED",
            lambda: self.evidence.validate(
                replica["version_id"], self.dataset_id, self.cases
            ),
        )

    def test_discretionary_translation_is_semantic_but_not_source_equivalence(self) -> None:
        translated_spec = {
            **self.spec,
            "strategy_origin": "discretionary_origin",
            "development_operation": "translate",
            "translation_objective": "fidelity_oriented",
            "interpretation": {"entry": "Use only confirmed MA crossover decisions."},
            "ambiguities": ["The source leaves long-side selection subjective."],
            "transformations": [self._transformation()],
        }
        translated = {
            **self.version,
            "version_id": "ver_discretionary_translation",
            "spec_json": translated_spec,
        }
        self.repo.put_version(translated)
        result = self.evidence.validate(
            translated["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", result["gates"]["semantic"]["status"])
        self.assertEqual(
            "PASS_WITH_LIMITATIONS",
            result["gates"]["source_fidelity"]["status"],
        )
        self.assertNotEqual(
            "PASSED", result["gates"]["source_fidelity"]["status"]
        )

    def test_lab_and_api_mutation_routes_cannot_bypass_gates(self) -> None:
        from unittest.mock import patch

        import app.main as api

        self.assertTrue(
            any(route.path == "/api/python2pine/status" for route in api.app.routes)
        )
        proposal = {
            "proposal_id": "prop_reference_blocked",
            "family_id": self.version["family_id"],
            "parent_version_id": self.version["version_id"],
            "status": "proposed",
            "kind": "white_box",
            "lever": "stop_mult",
            "summary": "increase stop distance",
            "rationale": "test gate",
            "patch_json": {"path": "parameters.stop_mult", "value": 3},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repo.put_proposal(proposal)
        blocked_actions = [
            lambda: self.lab.run_version(self.version["version_id"], self.dataset_id),
            lambda: self.lab.optimize_all(self.version["version_id"], self.dataset_id),
            lambda: self.lab.preview_tuned_version(
                self.version["version_id"], self.dataset_id, {"stop_mult": 3}
            ),
            lambda: self.lab.run_proposal(proposal["proposal_id"], self.dataset_id),
            lambda: self.lab.run_proposal_pack(self.version["version_id"], self.dataset_id),
            lambda: self.lab.save_tuned_version(
                self.version["version_id"], self.dataset_id, {"stop_mult": 3}
            ),
        ]
        for index, action in enumerate(blocked_actions):
            with self.subTest(blocked_action=index):
                self.assert_error_code("EVIDENCE_REQUIRED", action)

        with patch.object(api, "lab", self.lab):
            self.assert_error_code(
                "EVIDENCE_REQUIRED",
                lambda: api.start_optimize_all_job(
                    self.version["version_id"],
                    api.OptimizeAllRequest(dataset_id=self.dataset_id),
                ),
            )
            initial_status = api.workflow_status(
                self.version["version_id"], self.dataset_id
            )
            self.assertTrue(initial_status["blockers"])
            api.validate_reference(
                self.version["version_id"],
                api.ReferenceValidationRequest(
                    dataset_id=self.dataset_id, cases=self.cases
                ),
            )
            refreshed_status = api.workflow_status(
                self.version["version_id"], self.dataset_id
            )
            self.assertEqual(
                "PASSED", refreshed_status["gates"]["semantic"]["status"]
            )

    def test_registration_selector_defaults_to_reference_and_preserves_legacy(self) -> None:
        from unittest.mock import patch

        import app.main as api

        common = {
            "family_id": "family_registration_route_fixture",
            "title": "Registration workflow fixture",
            "asset": "CASE",
            "venue": "Fixture",
            "timeframe": "15m",
            "version_name": "Baseline",
            "source_code": "Fixture source.",
            "spec_json": self.spec,
            "causal_story": "Reference-first registration contract.",
        }
        reference_request = api.RegisterBaselineRequest(**common)
        legacy_request = api.RegisterBaselineRequest(
            **{
                **common,
                "family_id": "family_legacy_registration_route_fixture",
            },
            workflow_version="legacy_pine_v1",
        )
        self.assertEqual("reference_v1", reference_request.workflow_version)
        self.assertEqual("legacy_pine_v1", legacy_request.workflow_version)
        with patch.object(api, "lab", self.lab), patch.object(
            self.lab, "register_baseline", return_value={}
        ) as register:
            api.register_family(reference_request)
            self.assertEqual(
                "reference_v1", register.call_args.kwargs["spec_json"]["workflow_version"]
            )
            api.register_family(legacy_request)
            self.assertEqual(
                "legacy_pine_v1", register.call_args.kwargs["spec_json"]["workflow_version"]
            )

    def test_reference_objective_metric_changes_ranking_and_rejects_unknown_metric(self) -> None:
        self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        self.lab.run_version(self.version["version_id"], self.dataset_id)
        bars = self.data.load_bars(self.dataset_id)
        boundary = {
            "objective": "Compare two declared candidate outcomes.",
            "parameters": {"stop_mult": [2, 3]},
            "train_end": (bars[7].ts + timedelta(minutes=15)).isoformat(),
            "holdout_start": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.evidence.authorize(
            self.version["version_id"],
            self.dataset_id,
            {**boundary, "objective_metric": "existing_score_v1"},
        )
        high_pf = {
            "total_trades": 5,
            "max_equity_drawdown_pct": 0,
            "profit_factor": 3,
            "net_pnl": 10,
            "return_pct": 0,
            "outperformance_pct": 0,
            "calmar": 0,
            "calmar_delta": 0,
            "daily_sharpe": 0,
            "percent_profitable": 0,
            "expected_payoff": 0,
            "worst_daily_return_pct": 0,
        }
        high_pnl = {**high_pf, "profit_factor": 1, "net_pnl": 20}
        default_a = self.lab._search_score_components(
            self.version["version_id"], self.dataset_id, self.spec, high_pf
        )
        default_b = self.lab._search_score_components(
            self.version["version_id"], self.dataset_id, self.spec, high_pnl
        )
        self.assertGreater(default_a["score"], default_b["score"])

        self.evidence.authorize(
            self.version["version_id"],
            self.dataset_id,
            {**boundary, "objective_metric": "net_pnl"},
        )
        explicit_a = self.lab._search_score_components(
            self.version["version_id"], self.dataset_id, self.spec, high_pf
        )
        explicit_b = self.lab._search_score_components(
            self.version["version_id"], self.dataset_id, self.spec, high_pnl
        )
        self.assertEqual("net_pnl", explicit_a["objective_metric"])
        self.assertEqual(10, explicit_a["metric_value"])
        self.assertLess(explicit_a["score"], explicit_b["score"])
        self.assert_error_code(
            "SEARCH_AUTHORIZATION_INVALID",
            lambda: self.evidence.authorize(
                self.version["version_id"],
                self.dataset_id,
                {**boundary, "objective_metric": "unlisted_metric"},
            ),
        )

    def test_hybrid_reference_adapters_reject_before_loading_data_or_running_engine(self) -> None:
        from unittest.mock import patch

        self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        baseline = self.lab.run_version(self.version["version_id"], self.dataset_id)
        self.assert_error_code(
            "REFERENCE_VENUE_ADAPTER_UNIMPLEMENTED",
            lambda: self.lab.execution_feasibility_audit(baseline["run_id"]),
        )
        with (
            patch.object(self.data, "load_bars") as load_bars,
            patch.object(self.lab.engine, "run") as engine_run,
        ):
            adapters = (
                self.lab.run_hybrid_entry_quality_experiment,
                self.lab.run_hybrid_entry_sizing_experiment,
                self.lab.run_hybrid_time_decay_triage_experiment,
            )
            for adapter in adapters:
                with self.subTest(adapter=adapter.__name__):
                    self.assert_error_code(
                        "REFERENCE_HYBRID_ADAPTER_UNSUPPORTED",
                        lambda adapter=adapter: adapter(baseline["run_id"]),
                    )
            load_bars.assert_not_called()
            engine_run.assert_not_called()

    def test_reference_production_defaults_preserve_fixed_execution_contract(self) -> None:
        self.assertEqual(
            "explicit_parameters_override_declared_defaults",
            self.spec["execution_contract"]["parameter_resolution"],
        )
        self.assertEqual(
            {
                "quantity": 1,
                "stop_mult": 2,
                "atr_len": 7,
                "initial_capital": 100000,
                "tick_size": 0.01,
                "commission_pct": 0,
                "slippage_ticks": 0,
                "target_r": 0,
                "max_gap_bars": 0,
            },
            self.spec["execution_contract"]["parameter_defaults"],
        )
        overrides = {
            "execution_model": "next_bar_open",
            "sizing_mode": "fixed_quantity",
        }
        result = self.lab._production_baseline_overrides(self.spec, overrides)
        self.assertEqual(overrides, result)

    def test_run_baseline_authorized_child_save_and_cross_family_rejection(self) -> None:
        self.evidence.validate(
            self.version["version_id"], self.dataset_id, self.cases
        )
        run = self.lab.run_version(self.version["version_id"], self.dataset_id)
        self.assertTrue(run["run_id"])
        self.assertTrue(self.repo.list_workflow_evidence(self.version["version_id"], self.dataset_id))
        with self.assertRaises(HTTPException) as undeclared_economics:
            self.lab.promote_version(
                self.version["family_id"], self.version["version_id"]
            )
        self.assertEqual(409, undeclared_economics.exception.status_code)

        weak_version = {
            **self.version,
            "version_id": "ver_reference_weak_economics",
            "name": "Reference with failed declared economics",
            "spec_json": {**self.spec, "evaluation": {"minimum_net_pnl": 1e12}},
        }
        self.repo.put_version(weak_version)
        self.evidence.validate(
            weak_version["version_id"], self.dataset_id, self.cases
        )
        self.lab.run_version(weak_version["version_id"], self.dataset_id)
        with self.assertRaises(HTTPException) as weak_economics:
            self.lab.promote_version(
                self.version["family_id"], weak_version["version_id"]
            )
        self.assertEqual(409, weak_economics.exception.status_code)
        self.assertEqual(
            self.version["version_id"],
            self.repo.get_family(self.version["family_id"])["current_version_id"],
        )
        bars = self.data.load_bars(self.dataset_id)
        baseline_artifact = json.loads(Path(run["artifact_path"]).read_text("utf-8"))
        self.assertEqual("fixed_baseline", baseline_artifact["data_scope"])
        authorization = {
            "objective": "increase stop distance without changing entries",
            "parameters": {"stop_mult": [2, 3]},
            "train_end": (bars[7].ts + timedelta(minutes=15)).isoformat(),
            "holdout_start": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.evidence.authorize(
            self.version["version_id"], self.dataset_id, authorization
        )
        out_of_domain_spec = {
            **self.spec,
            "development_operation": "improve",
            "development_authorization": "Use only the parent's authorized stop-distance values.",
            "operation_transition": {"from": "create", "to": "improve"},
            "parameters": {**self.spec["parameters"], "stop_mult": 999},
            "transformations": [self._transformation(changed=True)],
        }
        out_of_domain_child = self.lab.create_reference_child(
            self.version["version_id"],
            self.dataset_id,
            out_of_domain_spec,
            "Out-of-domain child candidate",
        )
        self.assert_error_code(
            "SEARCH_DOMAIN_UNAUTHORIZED",
            lambda: self.evidence.validate(
                out_of_domain_child["version_id"], self.dataset_id, self.cases
            ),
        )
        training_bars = self.evidence.training_bars(
            self.version, self.dataset_id, bars
        )
        from unittest.mock import patch

        with patch.object(
            self.lab.engine, "run", wraps=self.lab.engine.run
        ) as child_engine:
            child_run = self.lab.save_tuned_version(
                self.version["version_id"],
                self.dataset_id,
                {"stop_mult": 3},
                name="Authorized stop-distance child",
            )
        self.assertEqual(2, child_engine.call_count)
        for call in child_engine.call_args_list:
            self.assertEqual(training_bars, call.args[1])
        self.assertEqual("training", child_run["data_scope"])
        self.assertEqual("same_observations", child_run["comparison"]["comparison_scope"])
        child_artifact = json.loads(
            Path(child_run["artifact_path"]).read_text("utf-8")
        )
        self.assertEqual("training", child_artifact["data_scope"])
        child = self.repo.get_version(child_run["version_id"])
        self.assertEqual("improve", child["spec_json"]["development_operation"])
        self.assertEqual(3, child["spec_json"]["parameters"]["stop_mult"])
        self.assertNotEqual(
            child["version_id"], self.repo.get_family(self.version["family_id"])["current_version_id"]
        )
        self.assertTrue(
            self.evidence.require(child, self.dataset_id, "run")["gates"]["semantic"]
        )
        reset_child_holdout = {
            **authorization,
            "train_end": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.assert_error_code(
            "SEARCH_AUTHORIZATION_INVALID",
            lambda: self.evidence.authorize(
                child["version_id"], self.dataset_id, reset_child_holdout
            ),
        )
        with patch.object(
            self.lab.engine, "run", wraps=self.lab.engine.run
        ) as preview_engine:
            preview = self.lab.preview_tuned_version(
                self.version["version_id"],
                self.dataset_id,
                {"stop_mult": 3},
            )
        self.assertEqual(2, preview_engine.call_count)
        for call in preview_engine.call_args_list:
            self.assertEqual(training_bars, call.args[1])
        self.assertEqual("training", preview["data_scope"])
        self.assertFalse(preview["promotable"])

        narrower_authorization = {
            **authorization,
            "train_end": (bars[6].ts + timedelta(minutes=15)).isoformat(),
        }
        self.evidence.authorize(
            self.version["version_id"], self.dataset_id, narrower_authorization
        )
        self.assert_error_code(
            "EVIDENCE_REQUIRED",
            lambda: self.evidence.require(child, self.dataset_id, "run"),
        )

        other_family_id = "family_reference_other"
        self.repo.put_family(
            {
                "family_id": other_family_id,
                "title": "Other family",
                "asset": "CASE",
                "venue": "Fixture",
                "timeframe": "15m",
                "current_version_id": "ver_other_family",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        with self.assertRaises(HTTPException) as cross_family:
            self.lab.promote_version(other_family_id, child["version_id"])
        self.assertEqual(409, cross_family.exception.status_code)

    def test_improved_child_authorization_checks_resolved_default_changes(self) -> None:
        bars = self.data.load_bars(self.dataset_id)
        parent_spec = {
            **self.spec,
            "parameters": {
                **self.spec["parameters"],
                "quantity": 1,
                "stop_mult": 9,
            },
        }
        parent = {
            **self.version,
            "version_id": "ver_effective_default_parent",
            "spec_json": parent_spec,
        }
        self.repo.put_version(parent)
        self.evidence.validate(parent["version_id"], self.dataset_id, self.cases)
        self.lab.run_version(parent["version_id"], self.dataset_id)
        authorization = {
            "objective": "Preserve behavior while checking omitted stop defaults.",
            "parameters": {"quantity": [1, 2]},
            "train_end": (bars[7].ts + timedelta(minutes=15)).isoformat(),
            "holdout_start": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.evidence.authorize(parent["version_id"], self.dataset_id, authorization)

        child_spec = {
            **parent_spec,
            "development_operation": "improve",
            "development_authorization": "Only parent-authorized effective parameters may change.",
            "operation_transition": {"from": "create", "to": "improve"},
            "parameters": {
                key: value
                for key, value in parent_spec["parameters"].items()
                if key != "stop_mult"
            },
            "transformations": [self._transformation(changed=True)],
        }
        child = self.lab.create_reference_child(
            parent["version_id"],
            self.dataset_id,
            child_spec,
            "Omitted stop default child",
        )
        self.assertNotIn("stop_mult", child["spec_json"]["parameters"])
        self.assert_error_code(
            "SEARCH_DOMAIN_UNAUTHORIZED",
            lambda: self.evidence.validate(
                child["version_id"], self.dataset_id, self.cases
            ),
        )

        authorized = {
            **authorization,
            "parameters": {"quantity": [1, 2], "stop_mult": [9, 2]},
        }
        self.evidence.authorize(parent["version_id"], self.dataset_id, authorized)
        evidence = self.evidence.validate(
            child["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", evidence["gates"]["semantic"]["status"])
        self.assertEqual(2, effective_parameters(child["spec_json"])["stop_mult"])
        implicit_result = run_reference(child["spec_json"], self.bars)
        explicit_default_result = run_reference(
            {
                **child["spec_json"],
                "parameters": {
                    **child["spec_json"]["parameters"],
                    "stop_mult": 2,
                },
            },
            self.bars,
        )
        self.assertEqual(implicit_result["trades"], explicit_default_result["trades"])
        self.assertEqual(
            implicit_result["equity_curve"], explicit_default_result["equity_curve"]
        )

    def test_omitting_an_explicit_default_is_not_an_effective_change(self) -> None:
        bars = self.data.load_bars(self.dataset_id)
        parent_spec = {
            **self.spec,
            "parameters": {**self.spec["parameters"], "quantity": 1},
        }
        parent = {
            **self.version,
            "version_id": "ver_explicit_default_parent",
            "spec_json": parent_spec,
        }
        self.repo.put_version(parent)
        self.evidence.validate(parent["version_id"], self.dataset_id, self.cases)
        self.lab.run_version(parent["version_id"], self.dataset_id)
        authorization = {
            "objective": "Preserve the explicit default while normalizing the spec.",
            "parameters": {"quantity": [1, 2]},
            "train_end": (bars[7].ts + timedelta(minutes=15)).isoformat(),
            "holdout_start": (bars[8].ts + timedelta(minutes=15)).isoformat(),
        }
        self.evidence.authorize(
            parent["version_id"], self.dataset_id, authorization
        )
        child_spec = {
            **parent_spec,
            "development_operation": "improve",
            "development_authorization": "Preserve all effective rule values.",
            "operation_transition": {"from": "create", "to": "improve"},
            "parameters": {
                key: value
                for key, value in parent_spec["parameters"].items()
                if key != "stop_mult"
            },
            "transformations": [
                {
                    **self._transformation(),
                    "expected_effect": "Represent the existing default without changing behavior.",
                    "meaning_change": False,
                }
            ],
        }
        child = self.lab.create_reference_child(
            parent["version_id"],
            self.dataset_id,
            child_spec,
            "Explicit-default omission child",
        )
        evidence = self.evidence.validate(
            child["version_id"], self.dataset_id, self.cases
        )
        self.assertEqual("PASSED", evidence["gates"]["semantic"]["status"])
        self.assertEqual(2, effective_parameters(child["spec_json"])["stop_mult"])


if __name__ == "__main__":
    unittest.main()
