# ruff: noqa: I001
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = (
    Path(os.environ["STRATEGYLAB_ROOT"]).resolve()
    if "STRATEGYLAB_ROOT" in os.environ
    else Path(__file__).resolve().parents[2]
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backtest import BacktestEngine
from app.data import Bar
from pine2python.config import Settings
from pine2python.generators import generate_adapter
from pine2python.models import AnalyzeRequest, Candle, GenerateRequest, ProofRequest
from pine2python.parity import compare_traces
from pine2python.models import ParityContract
from pine2python.service import Pine2PythonService


FIXTURE_ROOT = (
    ROOT / "services" / "pine2python" / "tests" / "fixtures" / "ma_cross_atr_stop_v1"
)
REMOTE_URL = os.environ.get("PINE2PYTHON_TEST_URL", "").rstrip("/")


def remote_post(path: str, payload: dict) -> dict:
    request = Request(
        f"{REMOTE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            return json.load(response)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {body}") from exc


def build_candles(contract: dict) -> list[Candle]:
    dataset = contract["dataset"]
    candles: list[Candle] = []
    previous = 100.0
    for index in range(dataset["bars"]):
        center = (
            100.0
            + index * 0.015
            + math.sin(index / 7.0) * 5.0
            + math.sin(index / 19.0) * 2.5
        )
        open_price = previous + math.sin(index / 5.0) * 0.35
        close = center + math.sin(index / 3.0) * 0.6
        candles.append(
            Candle(
                time=dataset["start_ms"] + index * dataset["step_ms"],
                open=round(open_price, 2),
                high=round(max(open_price, close) + 0.85, 2),
                low=round(min(open_price, close) - 0.85, 2),
                close=round(close, 2),
                volume=1_000 + index,
            )
        )
        previous = close
    return candles


def python_spec(contract: dict) -> dict:
    parameters = {
        **contract["parameters"],
        "tick_size": contract["dataset"]["mintick"],
        "sizing_mode": "fixed_quantity",
        "risk_pct": 0.005,
        "notional_pct": 0.25,
        "max_leverage": 1.0,
    }
    return {
        "engine_id": "ma_cross_atr_stop_v1",
        "asset": contract["dataset"]["symbol"],
        "venue": "fixture",
        "timeframe": contract["dataset"]["timeframe"],
        "metadata": {
            "family_id": "ma_cross_atr_stop_v1_fixture",
            "title": "MA crossover ATR stop fixture",
        },
        "parameters": parameters,
        "evaluation": {},
        "mutation_space": [],
    }


def main() -> int:
    fixture = json.loads((FIXTURE_ROOT / "fixture.json").read_text(encoding="utf-8"))
    parity_contract = json.loads(
        (FIXTURE_ROOT / "parity-contract.json").read_text(encoding="utf-8")
    )
    candles = build_candles(fixture)
    dataset = fixture["dataset"]
    generation_request = GenerateRequest(
        parameters=fixture["parameters"],
        title="StrategyLab golden MA / ATR parity fixture",
        symbol=dataset["symbol"],
        timeframe=dataset["timeframe"],
        mintick=dataset["mintick"],
        start_ms=candles[0].time,
        end_ms=candles[-1].time + dataset["step_ms"],
    )
    generated = generate_adapter(fixture["adapter_id"], generation_request)
    analysis_request = AnalyzeRequest(source=generated["source"], name="fixture.pine")
    proof_request = ProofRequest(
        source=generated["source"],
        source_name="fixture.pine",
        source_id="ma_cross_atr_stop_v1_fixture",
        settings=generated["settings"],
        profile="basic_v1",
        symbol=dataset["symbol"],
        timeframe=dataset["timeframe"],
        start_ms=candles[0].time,
        end_ms=candles[-1].time + dataset["step_ms"],
        mintick=dataset["mintick"],
        candles=candles,
        stream_expressions=generated["trace_contract"],
        declaration_kind="strategy",
    )
    if REMOTE_URL:
        analysis = remote_post("/v1/analyses", analysis_request.model_dump(mode="json"))
        proof = remote_post("/v1/proofs", proof_request.model_dump(mode="json"))
    else:
        with tempfile.TemporaryDirectory(prefix="p2p-vertical-") as temp_name:
            temp_root = Path(temp_name)
            service = Pine2PythonService(
                Settings(
                    artifact_root=temp_root / "artifacts",
                    work_root=temp_root / "work",
                )
            )
            analysis = service.analyze(analysis_request)
            proof = service.proof(proof_request)
    bars = [
        Bar(
            ts=datetime.fromtimestamp(candle.time / 1_000, UTC),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            symbol=dataset["symbol"],
            timeframe=dataset["timeframe"],
        )
        for candle in candles
    ]
    python_result = BacktestEngine().run(
        python_spec(fixture),
        bars,
        collect_trace=True,
    )
    parity_request = {
        "reference_rows": proof["local_trace"]["rows"],
        "candidate_rows": python_result["trace"]["rows"],
        "contract": parity_contract,
    }
    if REMOTE_URL:
        comparison = remote_post("/v1/parity-comparisons", parity_request)
    else:
        comparison = compare_traces(
            parity_request["reference_rows"],
            parity_request["candidate_rows"],
            ParityContract.model_validate(parity_contract),
        )
    report = {
        "fixture": fixture["adapter_id"],
        "transport": "http" if REMOTE_URL else "local",
        "analysis_status": analysis["status"],
        "local_proof_status": proof["local_runtime"]["status"],
        "tradingview_status": proof["status"],
        "pine_trace_rows": len(proof["local_trace"]["rows"]),
        "python_trace_rows": len(python_result["trace"]["rows"]),
        "parity": comparison,
        "sample_artifact": proof["artifact"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
