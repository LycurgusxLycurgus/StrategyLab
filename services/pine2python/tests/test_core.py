from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pine2python.analyzer import analyze_source
from pine2python.artifacts import ArtifactStore
from pine2python.config import Settings
from pine2python.errors import Pine2PythonError
from pine2python.generators import generate_adapter
from pine2python.models import (
    Candle,
    GenerateRequest,
    ParityContract,
    ProofRequest,
    TradingViewObservationRequest,
)
from pine2python.parity import compare_traces
from pine2python.proof import (
    _round_ties_up,
    compare_tradingview_observation,
    create_proof,
)
from pine2python.service import Pine2PythonService

INDICATOR = """//@version=6
indicator("Fixture")
fast = ta.sma(close, 2)
plot(fast)
"""


class AnalyzerTests(unittest.TestCase):
    def test_pynescript_parses_v6_and_inventory_is_stable(self) -> None:
        result = analyze_source(INDICATOR)
        self.assertEqual("PARSE_COMPLETE", result["parser"]["status"])
        self.assertEqual(6, result["inventory"]["pine_version"])
        self.assertEqual("indicator", result["inventory"]["declaration"])
        self.assertIn("ta.sma", result["inventory"]["all_namespace_calls"])

    def test_realtime_and_request_constructs_block_local_runtime(self) -> None:
        source = """//@version=6
indicator("Risk")
varip int ticks = 0
x = request.security(syminfo.tickerid, "60", close, lookahead=barmerge.lookahead_on)
plot(x)
"""
        result = analyze_source(source)
        codes = {item["code"] for item in result["capabilities"]["runtime_blockers"]}
        self.assertIn("REQUEST_RUNTIME_UNVERIFIED", codes)
        self.assertIn("VARIP_RUNTIME_UNVERIFIED", codes)
        self.assertEqual("blocked", result["capabilities"]["local_runtime"])

    def test_confirmed_htf_lookahead_pattern_is_not_flagged_as_future_leak(
        self,
    ) -> None:
        source = """//@version=6
indicator("Confirmed HTF")
x = request.security(syminfo.tickerid, "240", close[1], barmerge.gaps_off, barmerge.lookahead_on)
plot(x)
"""
        result = analyze_source(source)
        findings = {
            item["code"]: item for item in result["temporal_findings"]
        }
        self.assertIn("CONFIRMED_HTF_LOOKAHEAD_PATTERN", findings)
        self.assertNotIn("LOOKAHEAD_ON", findings)

    def test_plot_budget_preflight_reports_tradingview_limit(self) -> None:
        source = (
            '//@version=6\nindicator("Plot budget")\n'
            + "\n".join(f"plot(close, title=\"p{index}\")" for index in range(65))
            + "\n"
        )
        result = analyze_source(source)
        self.assertEqual(65, result["inventory"]["plot_budget"]["minimum_count"])
        blocker_codes = {
            item["code"]
            for item in result["capabilities"]["tradingview_blockers"]
        }
        self.assertIn("TRADINGVIEW_PLOT_LIMIT_EXCEEDED", blocker_codes)


class ProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candles = [
            Candle(time=1_704_067_200_000, open=100, high=102, low=99, close=101),
            Candle(time=1_704_067_260_000, open=101, high=103, low=100, close=102),
            Candle(time=1_704_067_320_000, open=102, high=104, low=101, close=103),
        ]
        self.request = ProofRequest(
            source=INDICATOR,
            symbol="TEST",
            timeframe="1",
            start_ms=self.candles[0].time,
            end_ms=self.candles[-1].time + 60_000,
            mintick=1,
            candles=self.candles,
            declaration_kind="indicator",
        )

    def test_proof_is_deterministic_and_contains_dashboard(self) -> None:
        first = create_proof(self.request)
        second = create_proof(self.request)
        self.assertEqual(first["dataset"], second["dataset"])
        self.assertEqual(first["dashboard_values"], second["dashboard_values"])
        self.assertIn(
            "TradingView Parity Proof Dashboard", first["instrumented_source"]
        )
        self.assertNotIn("p2p__proof__data_h1", first["instrumented_source"])
        self.assertIn(
            "table.new(position.bottom_right", first["instrumented_source"]
        )
        self.assertEqual(
            INDICATOR.count("plot("),
            first["instrumented_source"].count("plot("),
        )
        self.assertIn("p2p_render_dashboard(", first["instrumented_source"])
        self.assertNotIn("p2p_proof_run() =>", first["instrumented_source"])
        self.assertIn("p2p_hash_data(", first["instrumented_source"])
        self.assertIn("p2p_value := p2p_bar_count", first["instrumented_source"])
        self.assertIn("p2p_mix3(p2p_hashes", first["instrumented_source"])
        self.assertIn("if barstate.islast", first["instrumented_source"])
        self.assertEqual("basic_v1 / v2.12", first["dashboard_values"]["PROFILE"])
        self.assertEqual(
            0,
            first["profile"]["appended_tradingview_plot_calls"],
        )

    def test_table_proof_removes_only_standalone_hidden_trace_exports(self) -> None:
        source = """//@version=5
indicator("Trace compaction", overlay=true)
visible = plot(close, "Visible")
plot(close, "p2p__feature__close", display=display.none)
assigned = plot(open, "p2p__feature__assigned", display=display.none)
"""
        request = self.request.model_copy(update={"source": source})
        proof = create_proof(request)
        instrumented = proof["instrumented_source"]
        self.assertIn('visible = plot(close, "Visible")', instrumented)
        self.assertIn('assigned = plot(open, "p2p__feature__assigned"', instrumented)
        self.assertNotIn('plot(close, "p2p__feature__close"', instrumented)
        self.assertEqual(1, proof["profile"]["removed_hidden_trace_plot_calls"])
        self.assertTrue(proof["profile"]["instrumentation_transforms"])

    def test_table_proof_compacts_explicit_source_render_block(self) -> None:
        source = """//@version=5
indicator("Render compaction", overlay=true)
var table dashboard = table.new(position.top_right, 1, 1)
// P2P_PROOF_COMPACT_BEGIN status_dashboard
if barstate.islast
    table.cell(dashboard, 0, 0, str.tostring(close))
// P2P_PROOF_COMPACT_END status_dashboard
"""
        request = self.request.model_copy(update={"source": source})
        proof = create_proof(request)
        instrumented = proof["instrumented_source"]
        self.assertIn("p2p_source_compact_status_dashboard() =>", instrumented)
        self.assertIn("p2p_source_compact_status_dashboard()", instrumented)
        self.assertEqual(
            ["status_dashboard"], proof["profile"]["compacted_source_blocks"]
        )

    def test_proof_accepts_present_nested_null_and_rounds_ties_like_pine(self) -> None:
        request = ProofRequest.model_validate(
            {
                **self.request.model_dump(),
                "trace_rows": [
                    {
                        "time": candle.time,
                        "features": {"nullable_price": None},
                    }
                    for candle in self.candles
                ],
                "stream_expressions": {
                    "features": [
                        {
                            "name": "features.nullable_price",
                            "expression": "na",
                            "kind": "price",
                        }
                    ]
                },
            }
        )
        proof = create_proof(request)
        self.assertIn("FEATURES", proof["dashboard_values"])
        self.assertEqual(2, _round_ties_up(1.5))
        self.assertEqual(-1, _round_ties_up(-1.5))
        self.assertIn("p2p_round", proof["instrumented_source"])

    def test_proof_can_reuse_immutable_static_runtime_blockers(self) -> None:
        blocker = {
            "code": "REQUEST_RUNTIME_UNVERIFIED",
            "message": "request.* requires TradingView corroboration.",
        }
        request = ProofRequest.model_validate(
            {
                **self.request.model_dump(),
                "local_runtime_policy": "skip_static_blockers",
                "local_runtime_blockers": [blocker],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = Pine2PythonService(
                Settings(
                    artifact_root=root / "artifacts",
                    work_root=root / "work",
                )
            )
            result = service.proof(request)
        self.assertEqual(
            "LOCAL_PROOF_RUNTIME_UNAVAILABLE",
            result["local_runtime"]["status"],
        )
        self.assertEqual(
            "LOCAL_RUNTIME_SKIPPED_FROM_REVISION_ANALYSIS",
            result["local_runtime"]["error"]["code"],
        )
        self.assertEqual(
            [blocker],
            result["local_runtime"]["error"]["details"]["blockers"],
        )

    def test_basic_profile_rejects_oversized_window(self) -> None:
        request = self.request.model_copy(
            update={
                "candles": [
                    Candle(
                        time=1_700_000_000_000 + index * 60_000,
                        open=1,
                        high=1,
                        low=1,
                        close=1,
                    )
                    for index in range(5_001)
                ],
                "start_ms": 1_700_000_000_000,
                "end_ms": 1_700_000_000_000 + 5_002 * 60_000,
            }
        )
        with self.assertRaises(Pine2PythonError) as context:
            create_proof(request)
        self.assertEqual("TRADINGVIEW_PROFILE_LIMIT", context.exception.code)

    def test_observation_requires_dataset_match_and_explicit_evidence(self) -> None:
        proof = create_proof(self.request)
        observed = dict(proof["dashboard_values"])
        observed["DATA"] = "0000001-0000002-0000003"
        mismatch = compare_tradingview_observation(
            TradingViewObservationRequest(
                expected=proof,
                observed=observed,
                user_verdict="pending",
            )
        )
        self.assertFalse(mismatch["dataset_match"])
        self.assertEqual("TRADINGVIEW_SIGNATURE_MISMATCH", mismatch["status"][0])
        rejected = compare_tradingview_observation(
            TradingViewObservationRequest(
                expected=proof,
                observed=proof["dashboard_values"],
                screenshot_sha256="a" * 64,
                user_verdict="rejected",
            )
        )
        self.assertIn("TRADINGVIEW_REJECTED", rejected["status"])
        with self.assertRaises(Pine2PythonError):
            compare_tradingview_observation(
                TradingViewObservationRequest(
                    expected=proof,
                    observed=proof["dashboard_values"],
                    user_verdict="accepted",
                )
            )


class ParityTests(unittest.TestCase):
    def test_first_divergence_is_precise(self) -> None:
        reference = [
            {"time": 1, "signal": False, "feature": 1.0},
            {"time": 2, "signal": True, "feature": 2.0},
        ]
        candidate = [
            {"time": 1, "signal": False, "feature": 1.0},
            {"time": 2, "signal": False, "feature": 2.01},
        ]
        result = compare_traces(
            reference,
            candidate,
            ParityContract(
                exact_fields=["signal"],
                tolerance_fields={"feature": 0.001},
            ),
        )
        self.assertFalse(result["passed"])
        self.assertEqual("signal", result["summary"]["first_divergence"]["field"])


class ArtifactAndGenerationTests(unittest.TestCase):
    def test_content_addressed_bundle_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(Path(temp_dir))
            first = store.put_bundle("test", {"a": 1}, {"result.json": {"b": 2}})
            second = store.put_bundle("test", {"a": 1}, {"result.json": {"b": 2}})
            self.assertEqual(first, second)

    def test_registered_adapter_generates_instrumented_candidate(self) -> None:
        result = generate_adapter(
            "ma_cross_v1",
            GenerateRequest(
                parameters={"fast_length": 5, "slow_length": 20},
                start_ms=1_700_000_000_000,
                end_ms=1_700_086_400_000,
            ),
        )
        self.assertIn("strategy.entry", result["source"])
        self.assertIn("P2P PROOF", result["preview_instrumented_source"])
        self.assertEqual("TRADINGVIEW_REVIEW_REQUIRED", result["status"])

    def test_strategylab_ma_atr_adapter_is_explicitly_next_bar_open(self) -> None:
        result = generate_adapter(
            "ma_cross_atr_stop_v1",
            GenerateRequest(
                parameters={
                    "fast_len": 5,
                    "slow_len": 20,
                    "atr_len": 7,
                    "noise_lookback": 10,
                    "max_no_cross": 3,
                    "stop_mult": 2.5,
                    "execution_model": "next_bar_open",
                },
                start_ms=1_700_000_000_000,
                end_ms=1_700_086_400_000,
            ),
        )
        self.assertIn('strategy.exit("L-stop"', result["source"])
        self.assertEqual("next_bar_open", result["settings"]["execution_model"])
        self.assertIn("features", result["trace_contract"])
        with self.assertRaises(Pine2PythonError) as context:
            generate_adapter(
                "ma_cross_atr_stop_v1",
                GenerateRequest(
                    parameters={"execution_model": "mt5_bar_proxy"},
                    start_ms=1_700_000_000_000,
                    end_ms=1_700_086_400_000,
                ),
            )
        self.assertEqual(
            "UNSUPPORTED_GENERATOR_SEMANTICS",
            context.exception.code,
        )

    def test_generated_streams_are_captured_when_no_reference_trace_exists(
        self,
    ) -> None:
        generated = generate_adapter(
            "ma_cross_atr_stop_v1",
            GenerateRequest(
                parameters={
                    "fast_len": 3,
                    "slow_len": 8,
                    "atr_len": 3,
                    "noise_lookback": 4,
                    "max_no_cross": 4,
                    "stop_mult": 2,
                    "execution_model": "next_bar_open",
                },
                start_ms=1_700_000_000_000,
                end_ms=1_700_003_600_000,
            ),
        )
        candles = [
            Candle(
                time=1_700_000_000_000 + index * 60_000,
                open=100 + index + ((index % 7) - 3) * 2,
                high=105 + index,
                low=95 + index,
                close=101 + index + ((index % 7) - 3) * 2,
            )
            for index in range(60)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = Pine2PythonService(
                Settings(
                    artifact_root=root / "artifacts",
                    work_root=root / "work",
                )
            )
            result = service.proof(
                ProofRequest(
                    source=generated["source"],
                    source_name="generated.pine",
                    settings=generated["settings"],
                    symbol="TEST",
                    timeframe="1",
                    start_ms=candles[0].time,
                    end_ms=candles[-1].time + 60_000,
                    mintick=1,
                    candles=candles,
                    stream_expressions=generated["trace_contract"],
                    declaration_kind="strategy",
                )
            )
        self.assertEqual(
            "LOCAL_PROOF_CAPTURE_COMPLETE",
            result["local_runtime"]["status"],
        )
        self.assertEqual(
            "pinets_stream_capture",
            result["local_runtime"]["validation_basis"],
        )
        self.assertIn("SIGNALS", result["dashboard_values"])
        self.assertIn("STATES", result["dashboard_values"])
        self.assertIn("FEATURES", result["dashboard_values"])
        self.assertEqual(60, len(result["local_trace"]["rows"]))
        self.assertIn(
            "fast_ma",
            result["local_trace"]["rows"][-1]["features"],
        )
        self.assertTrue(result["local_trace"]["capabilities"]["signals"])
        self.assertNotEqual(
            result["identity"]["instrumented_source_sha256"],
            result["local_runtime"]["instrumented_source_sha256"],
        )
        self.assertIn(
            "local-runtime-instrumented.pine",
            {item["path"] for item in result["artifact"]["files"]},
        )

    def test_declared_state_start_bounds_proof_runtime_history(self) -> None:
        candles = [
            Candle(
                time=1_700_000_000_000 + index * 60_000,
                open=100 + index,
                high=102 + index,
                low=99 + index,
                close=101 + index,
            )
            for index in range(10)
        ]
        proof_start = candles[5].time
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = Pine2PythonService(
                Settings(
                    artifact_root=root / "artifacts",
                    work_root=root / "work",
                )
            )
            result = service.proof(
                ProofRequest(
                    source=INDICATOR,
                    settings={"state_start_ms": proof_start},
                    symbol="TEST",
                    timeframe="1",
                    start_ms=proof_start,
                    end_ms=candles[-1].time + 60_000,
                    mintick=1,
                    candles=candles,
                    declaration_kind="indicator",
                )
            )
        self.assertEqual(
            "LOCAL_PROOF_CAPTURE_COMPLETE",
            result["local_runtime"]["status"],
        )
        self.assertEqual(
            "declared_state_reset",
            result["local_runtime"]["runtime_window"]["basis"],
        )
        self.assertEqual(
            5,
            result["local_runtime"]["runtime_window"]["bar_count"],
        )
        self.assertEqual(5, len(result["local_trace"]["rows"]))


if __name__ == "__main__":
    unittest.main()
