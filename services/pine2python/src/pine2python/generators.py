from __future__ import annotations

from typing import Any, Literal

from .errors import Pine2PythonError
from .hashing import sha256_bytes, sha256_json
from .models import GenerateRequest, ProofRequest, ProofStreamExpression
from .proof import generate_dashboard_source

ADAPTERS = {
    "ma_cross_atr_stop_v1": {
        "description": "StrategyLab MA crossover/noise gate/ATR-stop adapter for the next-bar-open execution contract.",
        "parameters": {
            "ma_kind": {"type": "string", "enum": ["sma", "ema"]},
            "fast_len": {"type": "integer", "minimum": 2, "maximum": 500},
            "slow_len": {"type": "integer", "minimum": 3, "maximum": 1000},
            "atr_len": {"type": "integer", "minimum": 1, "maximum": 500},
            "noise_lookback": {"type": "integer", "minimum": 1, "maximum": 1000},
            "max_no_cross": {"type": "integer", "minimum": 0, "maximum": 1000},
            "stop_mult": {"type": "number", "exclusiveMinimum": 0},
            "quantity": {"type": "number", "exclusiveMinimum": 0},
        },
        "execution_contract": "next_bar_open",
    },
    "ma_cross_v1": {
        "description": "Long-only simple moving-average crossover with close-on-crossunder.",
        "parameters": {
            "fast_length": {"type": "integer", "minimum": 2, "maximum": 500},
            "slow_length": {"type": "integer", "minimum": 3, "maximum": 1000},
            "quantity": {"type": "number", "exclusiveMinimum": 0},
        },
    },
}


def generate_adapter(adapter_id: str, request: GenerateRequest) -> dict[str, Any]:
    if adapter_id == "ma_cross_atr_stop_v1":
        return _generate_ma_cross_atr_stop(request)
    if adapter_id != "ma_cross_v1":
        raise Pine2PythonError(
            "UNKNOWN_ADAPTER",
            f"Unknown Pine generator adapter '{adapter_id}'.",
            {"available": sorted(ADAPTERS)},
            404,
        )
    fast = int(request.parameters.get("fast_length", 10))
    slow = int(request.parameters.get("slow_length", 30))
    quantity = float(request.parameters.get("quantity", 1.0))
    if not 2 <= fast <= 500:
        raise Pine2PythonError("INVALID_PARAMETER", "fast_length must be 2..500.")
    if not 3 <= slow <= 1000 or fast >= slow:
        raise Pine2PythonError(
            "INVALID_PARAMETER",
            "slow_length must be 3..1000 and greater than fast_length.",
        )
    if quantity <= 0:
        raise Pine2PythonError("INVALID_PARAMETER", "quantity must be positive.")
    safe_title = request.title.replace("\\", "\\\\").replace('"', '\\"')
    source = f"""//@version=6
strategy("{safe_title}", overlay=true, pyramiding=0, process_orders_on_close=true, initial_capital=10000)
fastLength = input.int({fast}, "Fast SMA", minval=2)
slowLength = input.int({slow}, "Slow SMA", minval=3)
quantity = input.float({quantity:g}, "Quantity", minval=0.000001)
fastSma = ta.sma(close, fastLength)
slowSma = ta.sma(close, slowLength)
longSignal = ta.crossover(fastSma, slowSma)
exitSignal = ta.crossunder(fastSma, slowSma)
if longSignal
    strategy.entry("L", strategy.long, qty=quantity)
if exitSignal
    strategy.close("L")
plot(fastSma, "Fast SMA", color=color.aqua)
plot(slowSma, "Slow SMA", color=color.orange)
plot(longSignal ? 1 : 0, "p2p__signal__long", display=display.none)
plot(exitSignal ? 1 : 0, "p2p__signal__exit", display=display.none)
plot(strategy.position_size, "p2p__state__position_size", display=display.none)
"""
    settings = {
        "adapter_id": adapter_id,
        "fast_length": fast,
        "slow_length": slow,
        "quantity": quantity,
        "process_orders_on_close": True,
        "pyramiding": 0,
        "initial_capital": 10_000,
    }
    expressions: dict[
        Literal["features", "states", "signals", "rejections", "orders"],
        list[ProofStreamExpression],
    ] = {
        "signals": [
            ProofStreamExpression(
                name="signals.long", expression="longSignal", kind="bool"
            ),
            ProofStreamExpression(
                name="signals.exit", expression="exitSignal", kind="bool"
            ),
        ],
        "states": [
            ProofStreamExpression(
                name="state.position_size",
                expression="strategy.position_size",
                kind="float",
                scale=1_000_000,
            )
        ],
    }
    proof_request = ProofRequest(
        source=source,
        source_name=f"{adapter_id}.pine",
        settings=settings,
        profile=request.profile,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_ms=request.start_ms,
        end_ms=request.end_ms,
        mintick=request.mintick,
        candles=[],
        stream_expressions=expressions,
        declaration_kind="strategy",
    )
    source_hash = sha256_bytes(source.encode("utf-8"))
    settings_hash = sha256_json(settings)
    instrumented = generate_dashboard_source(
        proof_request,
        base_source_sha256=source_hash,
        settings_sha256=settings_hash,
    )
    return {
        "schema_version": "1.0",
        "adapter_id": adapter_id,
        "status": "TRADINGVIEW_REVIEW_REQUIRED",
        "settings": settings,
        "source_sha256": source_hash,
        "instrumented_source_sha256": sha256_bytes(instrumented.encode("utf-8")),
        "source": source,
        "preview_instrumented_source": instrumented,
        "trace_contract": {
            name: [item.model_dump() for item in items]
            for name, items in expressions.items()
        },
        "warnings": [
            "Generated source is a candidate and requires TradingView proof plus Python parity before optimization.",
        ],
    }


def _generate_ma_cross_atr_stop(request: GenerateRequest) -> dict[str, Any]:
    parameters = request.parameters
    ma_kind = str(parameters.get("ma_kind", "sma")).lower()
    fast = int(parameters.get("fast_len", 10))
    slow = int(parameters.get("slow_len", 30))
    atr_length = int(parameters.get("atr_len", 14))
    noise_lookback = int(parameters.get("noise_lookback", 25))
    max_no_cross = int(parameters.get("max_no_cross", 5))
    stop_mult = float(parameters.get("stop_mult", 3.0))
    quantity = float(parameters.get("quantity", 1.0))
    initial_capital = float(parameters.get("initial_capital", 100_000.0))
    commission_pct = float(parameters.get("commission_pct", 0.0))
    slippage_ticks = int(parameters.get("slippage_ticks", 0))
    allow_long = bool(parameters.get("allow_long", True))
    allow_short = bool(parameters.get("allow_short", True))
    execution_model = str(parameters.get("execution_model", "next_bar_open"))
    if execution_model != "next_bar_open":
        raise Pine2PythonError(
            "UNSUPPORTED_GENERATOR_SEMANTICS",
            "ma_cross_atr_stop_v1 generation currently requires execution_model='next_bar_open'.",
            {
                "requested": execution_model,
                "supported": ["next_bar_open"],
            },
        )
    if ma_kind not in {"sma", "ema"}:
        raise Pine2PythonError("INVALID_PARAMETER", "ma_kind must be sma or ema.")
    if not 2 <= fast <= 500:
        raise Pine2PythonError("INVALID_PARAMETER", "fast_len must be 2..500.")
    if not 3 <= slow <= 1000 or fast >= slow:
        raise Pine2PythonError(
            "INVALID_PARAMETER",
            "slow_len must be 3..1000 and greater than fast_len.",
        )
    if not 1 <= atr_length <= 500:
        raise Pine2PythonError("INVALID_PARAMETER", "atr_len must be 1..500.")
    if not 1 <= noise_lookback <= 1000:
        raise Pine2PythonError("INVALID_PARAMETER", "noise_lookback must be 1..1000.")
    if not 0 <= max_no_cross <= 1000:
        raise Pine2PythonError("INVALID_PARAMETER", "max_no_cross must be 0..1000.")
    if stop_mult <= 0 or quantity <= 0:
        raise Pine2PythonError(
            "INVALID_PARAMETER", "stop_mult and quantity must be positive."
        )
    if initial_capital <= 0 or commission_pct < 0 or slippage_ticks < 0:
        raise Pine2PythonError(
            "INVALID_PARAMETER",
            "initial_capital must be positive; commission and slippage cannot be negative.",
        )
    safe_title = request.title.replace("\\", "\\\\").replace('"', '\\"')
    ma_expression = "ta.sma" if ma_kind == "sma" else "ta.ema"
    source = f"""//@version=6
strategy("{safe_title}", overlay=true, pyramiding=0, initial_capital={initial_capital:g}, commission_type=strategy.commission.percent, commission_value={commission_pct:g}, slippage={slippage_ticks})
fastLength = input.int({fast}, "Fast MA", minval=2)
slowLength = input.int({slow}, "Slow MA", minval=3)
atrLength = input.int({atr_length}, "ATR length", minval=1)
noiseLookback = input.int({noise_lookback}, "Noise lookback", minval=1)
maxNoCross = input.int({max_no_cross}, "Maximum price/fast-MA crosses", minval=0)
stopMult = input.float({stop_mult:g}, "ATR stop multiple", minval=0.000001)
quantity = input.float({quantity:g}, "Quantity", minval=0.000001)
fastMa = {ma_expression}(close, fastLength)
slowMa = {ma_expression}(close, slowLength)
atrValue = ta.atr(atrLength)
priceCrossFast = ta.cross(close, fastMa)
crossCum = ta.cum(priceCrossFast ? 1.0 : 0.0)
crossCount = crossCum - nz(crossCum[noiseLookback], 0.0)
crossCountOk = crossCount <= maxNoCross
warm = bar_index >= math.max(math.max(slowLength, atrLength), noiseLookback + 1)
longSignal = warm and ta.crossover(fastMa, slowMa) and crossCountOk
shortSignal = warm and ta.crossunder(fastMa, slowMa) and crossCountOk
if longSignal and {str(allow_long).lower()}
    strategy.entry("L", strategy.long, qty=quantity)
if shortSignal and {str(allow_short).lower()}
    strategy.entry("S", strategy.short, qty=quantity)
var float activeStop = na
newLong = strategy.position_size > 0 and strategy.position_size[1] <= 0
newShort = strategy.position_size < 0 and strategy.position_size[1] >= 0
if newLong
    activeStop := strategy.position_avg_price - atrValue[1] * stopMult
if newShort
    activeStop := strategy.position_avg_price + atrValue[1] * stopMult
if strategy.position_size > 0
    strategy.exit("L-stop", "L", stop=activeStop)
if strategy.position_size < 0
    strategy.exit("S-stop", "S", stop=activeStop)
if strategy.position_size == 0
    activeStop := na
plot(fastMa, "Fast MA", color=color.aqua)
plot(slowMa, "Slow MA", color=color.orange)
plot(activeStop, "ATR stop", color=color.red, style=plot.style_linebr)
plot(longSignal ? 1 : 0, "p2p__signal__long", display=display.none)
plot(shortSignal ? 1 : 0, "p2p__signal__short", display=display.none)
plot(strategy.position_size, "p2p__state__position_size", display=display.none)
"""
    settings = {
        "adapter_id": "ma_cross_atr_stop_v1",
        "ma_kind": ma_kind,
        "fast_len": fast,
        "slow_len": slow,
        "atr_len": atr_length,
        "noise_lookback": noise_lookback,
        "max_no_cross": max_no_cross,
        "stop_mult": stop_mult,
        "quantity": quantity,
        "allow_long": allow_long,
        "allow_short": allow_short,
        "initial_capital": initial_capital,
        "commission_pct": commission_pct,
        "slippage_ticks": slippage_ticks,
        "tick_size": request.mintick,
        "execution_model": execution_model,
        "pyramiding": 0,
    }
    expressions: dict[
        Literal["features", "states", "signals", "rejections", "orders"],
        list[ProofStreamExpression],
    ] = {
        "features": [
            ProofStreamExpression(
                name="features.fast_ma", expression="fastMa", kind="price"
            ),
            ProofStreamExpression(
                name="features.slow_ma", expression="slowMa", kind="price"
            ),
            ProofStreamExpression(
                name="features.atr", expression="atrValue", kind="price"
            ),
            ProofStreamExpression(
                name="features.cross_count",
                expression="crossCount",
                kind="int",
            ),
        ],
        "signals": [
            ProofStreamExpression(
                name="signals.long", expression="longSignal", kind="bool"
            ),
            ProofStreamExpression(
                name="signals.short", expression="shortSignal", kind="bool"
            ),
        ],
        "states": [
            ProofStreamExpression(
                name="states.position_size",
                expression="strategy.position_size",
                kind="float",
                scale=1_000_000,
            ),
            ProofStreamExpression(
                name="states.active_stop",
                expression="activeStop",
                kind="price",
            ),
        ],
    }
    proof_request = ProofRequest(
        source=source,
        source_name="ma_cross_atr_stop_v1.pine",
        settings=settings,
        profile=request.profile,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_ms=request.start_ms,
        end_ms=request.end_ms,
        mintick=request.mintick,
        candles=[],
        stream_expressions=expressions,
        declaration_kind="strategy",
    )
    source_hash = sha256_bytes(source.encode("utf-8"))
    settings_hash = sha256_json(settings)
    instrumented = generate_dashboard_source(
        proof_request,
        base_source_sha256=source_hash,
        settings_sha256=settings_hash,
    )
    return {
        "schema_version": "1.0",
        "adapter_id": "ma_cross_atr_stop_v1",
        "status": "TRADINGVIEW_REVIEW_REQUIRED",
        "settings": settings,
        "source_sha256": source_hash,
        "instrumented_source_sha256": sha256_bytes(instrumented.encode("utf-8")),
        "source": source,
        "preview_instrumented_source": instrumented,
        "trace_contract": {
            name: [item.model_dump() for item in items]
            for name, items in expressions.items()
        },
        "warnings": [
            "This adapter targets StrategyLab's next_bar_open contract only.",
            "Generated source requires TradingView proof and Python trace parity before optimization.",
        ],
    }
