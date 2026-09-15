from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .errors import Pine2PythonError
from .hashing import sha256_bytes, sha256_json
from .models import (
    Candle,
    ProofRequest,
    ProofStreamExpression,
    TradingViewObservationRequest,
)
from .version import PROOF_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class FingerprintLane:
    seed: int
    modulus: int
    multiplier: int


LANES = (
    FingerprintLane(17, 1_000_003, 257),
    FingerprintLane(19, 1_000_033, 263),
    FingerprintLane(23, 1_000_037, 269),
)
NULL_SENTINEL = -2_000_000_011
BASIC_PROFILE_MAX_BARS = 5_000
TRADINGVIEW_PLOT_LIMIT = 64
TRADINGVIEW_INSTRUMENTATION_VERSION = "tv_table_v2_12"
DASHBOARD_VERSION = "v2.12"
ROUND_TIES_UP_EPSILON = 1e-9


def _positive_mod(value: int, modulus: int) -> int:
    return ((value % modulus) + modulus) % modulus


def _mix(current: int, value: int, lane: FingerprintLane, tag: int) -> int:
    return _positive_mod(
        _positive_mod(current * lane.multiplier, lane.modulus)
        + _positive_mod(value, lane.modulus)
        + tag * 17,
        lane.modulus,
    )


def _fingerprint(values: Iterable[tuple[int, int]]) -> tuple[int, int, int]:
    states = [lane.seed for lane in LANES]
    for tag, value in values:
        for index, lane in enumerate(LANES):
            states[index] = _mix(states[index], value, lane, tag)
    return states[0], states[1], states[2]


def _format_fingerprint(value: tuple[int, int, int] | list[int]) -> str:
    return "-".join(f"{item:07d}" for item in value)


def _round_ties_up(value: float) -> int:
    """Match Pine math.round while absorbing sub-ULP cross-runtime drift."""
    return math.floor(value + 0.5 + ROUND_TIES_UP_EPSILON)


def _to_int(value: Any, expression: ProofStreamExpression, mintick: float) -> int:
    if value is None:
        return NULL_SENTINEL
    if expression.kind == "bool":
        return 1 if bool(value) else 0
    if expression.kind == "price":
        return _round_ties_up(float(value) / mintick)
    if expression.kind == "float":
        return _round_ties_up(float(value) * expression.scale)
    return _round_ties_up(float(value))


def _path_value(row: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = row
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _included_candles(request: ProofRequest) -> list[Candle]:
    candles = [
        candle
        for candle in request.candles
        if request.start_ms <= candle.time < request.end_ms
    ]
    candles.sort(key=lambda candle: candle.time)
    if not candles:
        raise Pine2PythonError(
            "EMPTY_PROOF_WINDOW",
            "No supplied candles fall inside the requested proof window.",
        )
    if request.profile == "basic_v1" and len(candles) > BASIC_PROFILE_MAX_BARS:
        raise Pine2PythonError(
            "TRADINGVIEW_PROFILE_LIMIT",
            f"basic_v1 accepts at most {BASIC_PROFILE_MAX_BARS} bars.",
            {"bars": len(candles), "limit": BASIC_PROFILE_MAX_BARS},
        )
    previous = None
    for candle in candles:
        if previous is not None and candle.time <= previous:
            raise Pine2PythonError(
                "NON_MONOTONIC_CANDLES",
                "Candle timestamps must be strictly increasing inside the proof window.",
            )
        previous = candle.time
    return candles


def _bar_values(candles: list[Candle], mintick: float) -> list[list[tuple[int, int]]]:
    rows: list[list[tuple[int, int]]] = []
    for number, candle in enumerate(candles, start=1):
        rows.append(
            [
                (1, number),
                (2, candle.time // 1000),
                (3, _round_ties_up(candle.open / mintick)),
                (4, _round_ties_up(candle.high / mintick)),
                (5, _round_ties_up(candle.low / mintick)),
                (6, _round_ties_up(candle.close / mintick)),
            ]
        )
    return rows


def _segment_index(time_ms: int, start_ms: int, end_ms: int, segments: int) -> int:
    width = max(end_ms - start_ms, 1)
    return min(segments - 1, max(0, ((time_ms - start_ms) * segments) // width))


def _stream_fingerprint(
    name: str,
    candles: list[Candle],
    trace_by_time: dict[int, dict[str, Any]],
    expressions: list[ProofStreamExpression],
    mintick: float,
) -> tuple[int, int, int]:
    values: list[tuple[int, int]] = []
    for number, candle in enumerate(candles, start=1):
        row = trace_by_time.get(candle.time)
        if row is None:
            raise Pine2PythonError(
                "TRACE_ALIGNMENT_MISSING",
                f"Trace stream '{name}' has no row for candle {candle.time}.",
            )
        values.extend(((1, number), (2, candle.time // 1000)))
        for offset, expression in enumerate(expressions, start=10):
            found, raw = _path_value(row, expression.name)
            if not found:
                raise Pine2PythonError(
                    "TRACE_FIELD_MISSING",
                    f"Trace field '{expression.name}' required by stream '{name}' is missing.",
                    {"time": candle.time},
                )
            values.append((offset, _to_int(raw, expression, mintick)))
    return _fingerprint(values)


def _pine_mix_lines(
    target: str, value: str, tag: int, indent: str = "    "
) -> list[str]:
    return [
        f"{indent}{target}1 := p2p_mix({target}1, {value}, 1000003, 257, {tag})",
        f"{indent}{target}2 := p2p_mix({target}2, {value}, 1000033, 263, {tag})",
        f"{indent}{target}3 := p2p_mix({target}3, {value}, 1000037, 269, {tag})",
    ]


def _pine_mix_value_lines(target: str, value: str, tag: int) -> list[str]:
    """Mix one expression without repeating it once per fingerprint lane.

    Complex Pine expressions contribute heavily to TradingView's compiled-token
    budget. Cache the expression once, then mix that integer through all three
    lanes. This preserves the v2 fingerprint exactly while materially reducing
    generated proof size for large indicators.
    """
    return [
        f"    p2p_value := {value}",
        *_pine_mix_lines(target, "p2p_value", tag),
    ]


def _pine_mix_array_value_lines(target: str, value: str, tag: int) -> list[str]:
    """Mix one expression through a three-lane Pine array helper."""
    return [
        f"    p2p_value := {value}",
        f"    p2p_mix3({target}, p2p_value, {tag})",
    ]


def _pine_value(expression: ProofStreamExpression) -> str:
    if expression.kind == "bool":
        return f"({expression.expression} ? 1 : 0)"
    if expression.kind == "price":
        return (
            f"(na({expression.expression}) ? {NULL_SENTINEL} : "
            f"p2p_round(({expression.expression}) / p2p_mintick))"
        )
    if expression.kind == "float":
        return (
            f"(na({expression.expression}) ? {NULL_SENTINEL} : "
            f"p2p_round(({expression.expression}) * {expression.scale}))"
        )
    return (
        f"(na({expression.expression}) ? {NULL_SENTINEL} : "
        f"p2p_round({expression.expression}))"
    )


def _trace_plot_title(stream_name: str, expression: ProofStreamExpression) -> str:
    prefix = {
        "features": "feature",
        "signals": "signal",
        "states": "state",
        "rejections": "rejection",
        "orders": "order",
    }[stream_name]
    field = expression.name.split(".", 1)[-1]
    safe_field = re.sub(r"[^A-Za-z0-9_.-]", "_", field)
    return f"p2p__{prefix}__{safe_field}"


def _trace_plot_value(expression: ProofStreamExpression) -> str:
    if expression.kind == "bool":
        return f"({expression.expression} ? 1 : 0)"
    return expression.expression


def _source_exposes_trace_title(source: str, title: str) -> bool:
    return f'"{title}"' in source or f"'{title}'" in source


_HIDDEN_TRACE_PLOT = re.compile(
    r"^\s*plot\(.*[\"']p2p__[^\"']+[\"'].*display\s*=\s*display\.none.*\)\s*$"
)
_COMPACT_BEGIN = re.compile(
    r"^\s*//\s*P2P_PROOF_COMPACT_BEGIN\s+([A-Za-z][A-Za-z0-9_]*)\s*$"
)
_COMPACT_END = re.compile(
    r"^\s*//\s*P2P_PROOF_COMPACT_END\s+([A-Za-z][A-Za-z0-9_]*)\s*$"
)


def _compact_table_proof_source(
    source: str,
) -> tuple[str, list[str], list[str]]:
    """Remove source-owned hidden trace exports from a table-only proof.

    A table proof hashes the declared expressions directly, so standalone
    ``display.none`` plots whose titles begin with ``p2p__`` are redundant.
    Removing only those single-line exports frees Pine main-body and plot
    budget without changing calculations, state transitions, or visible
    chart output. Assigned plots and any non-P2P plot remain untouched.
    """
    kept: list[str] = []
    removed: list[str] = []
    compacted_blocks: list[str] = []
    source_lines = source.splitlines()
    index = 0
    while index < len(source_lines):
        line = source_lines[index]
        compact_match = _COMPACT_BEGIN.fullmatch(line)
        if compact_match:
            block_name = compact_match.group(1)
            block: list[str] = []
            index += 1
            while index < len(source_lines):
                end_match = _COMPACT_END.fullmatch(source_lines[index])
                if end_match:
                    if end_match.group(1) != block_name:
                        raise ValueError(
                            f"proof compaction marker mismatch: {block_name} / {end_match.group(1)}"
                        )
                    break
                block.append(source_lines[index])
                index += 1
            else:
                raise ValueError(
                    f"unterminated proof compaction block: {block_name}"
                )
            if not block:
                raise ValueError(f"empty proof compaction block: {block_name}")
            function_name = f"p2p_source_compact_{block_name}"
            kept.append(line)
            kept.append(f"{function_name}() =>")
            kept.extend(f"    {block_line}" for block_line in block)
            kept.append(f"{function_name}()")
            kept.append(source_lines[index])
            compacted_blocks.append(block_name)
            index += 1
            continue
        if _HIDDEN_TRACE_PLOT.fullmatch(line):
            removed.append(line)
        else:
            kept.append(line)
        index += 1
    compacted = "\n".join(kept)
    if source.endswith("\n"):
        compacted += "\n"
    return compacted, removed, compacted_blocks


def _wrap_table_dashboard_body(
    lines: list[str], request: ProofRequest
) -> list[str]:
    """Split proof hashing/rendering into bounded helpers.

    Persistent proof state remains global. Keeping arrays out of a single
    orchestration UDF avoids Pine's per-function local-variable ceiling, while
    the hash and dashboard helpers keep the global main body compact.
    """
    body_start = lines.index("var p2p_meta = array.from(0, int(na), int(na))")
    cell_start = lines.index("p2p_cell(int row, string label, string value) =>")
    prefix = [
        line
        for line in lines[:body_start]
        if line != "p2p_in_window = time >= p2p_start and time < p2p_end"
    ]
    cell_helper = [
        "p2p_cell(table target, int row, string label, string value) =>",
        "    table.cell(target, 0, row, label, text_color=color.silver, text_halign=text.align_left)",
        "    table.cell(target, 1, row, value, text_color=color.white, text_halign=text.align_right)",
    ]
    source_body = lines[body_start:cell_start]
    hash_start = source_body.index("if p2p_in_window")
    table_start = next(
        index
        for index, line in enumerate(source_body)
        if line.startswith("var table p2p_table")
    )
    declarations = [
        line
        for line in source_body[:hash_start]
        if line != "int p2p_value = 0"
    ]
    window_header = source_body[hash_start : hash_start + 5]
    hash_lines = source_body[hash_start + 5 : table_start]

    dataset_line_count = 43
    dataset_lines = hash_lines[:dataset_line_count]
    cursor = dataset_line_count
    helpers = [
        (
            "p2p_hash_data(matrix<int> p2p_hashes, int p2p_bar_count) =>"
        ),
        "    int p2p_value = 0",
        *dataset_lines,
    ]
    stream_calls: list[str] = [
        "p2p_hash_data(p2p_hashes, p2p_bar_count)"
    ]
    for stream_name, expressions in request.stream_expressions.items():
        stream_line_count = 4 + 2 * len(expressions)
        stream_lines = hash_lines[cursor : cursor + stream_line_count]
        cursor += stream_line_count
        helpers.extend(
            [
                f"p2p_hash_{stream_name}(matrix<int> p2p_hashes, int p2p_bar_count) =>",
                "    int p2p_value = 0",
                *stream_lines,
            ]
        )
        stream_calls.append(
            f"p2p_hash_{stream_name}(p2p_hashes, p2p_bar_count)"
        )

    strategy_call: list[str] = []
    if request.declaration_kind == "strategy":
        trade_lines = hash_lines[cursor:]
        helpers.extend(
            [
                "p2p_hash_trades(matrix<int> p2p_hashes) =>",
                "    int p2p_value = 0",
                *(f"    {line}" for line in trade_lines),
            ]
        )
        strategy_call = ["p2p_hash_trades(p2p_hashes)"]
    elif cursor != len(hash_lines):
        raise ValueError("unexpected table-proof hash body remainder")

    dashboard = [
        line.replace("p2p_cell(", "p2p_cell(p2p_table, ")
        for line in lines[cell_start + 3 :]
    ]
    render_parameters = [
        "table p2p_table",
        "array<int> p2p_meta",
        "matrix<int> p2p_hashes",
    ]
    render_arguments = [
        "p2p_table",
        "p2p_meta",
        "p2p_hashes",
    ]
    return [
        *prefix,
        *cell_helper,
        *helpers,
        f"p2p_render_dashboard({', '.join(render_parameters)}) =>",
        *dashboard[1:],
        *declarations,
        "p2p_in_window = time >= p2p_start and time < p2p_end",
        *window_header,
        *(f"    {line}" for line in stream_calls),
        *strategy_call,
        source_body[table_start],
        "if barstate.islast",
        f"    p2p_render_dashboard({', '.join(render_arguments)})",
    ]


def generate_dashboard_source(
    request: ProofRequest,
    *,
    base_source_sha256: str,
    settings_sha256: str,
    emit_runtime_plots: bool = False,
) -> str:
    stream_names = list(request.stream_expressions)
    data_row = 0
    segment_row_start = 1
    stream_rows = {
        name: segment_row_start + request.segments + index
        for index, name in enumerate(stream_names)
    }
    trades_row = segment_row_start + request.segments + len(stream_names)
    hash_row_count = trades_row + (
        1 if request.declaration_kind == "strategy" else 0
    )
    row_count = 9 + len(stream_names) + request.segments
    if request.declaration_kind == "strategy":
        row_count += 5
    packed_proof = not emit_runtime_plots
    if packed_proof:
        mix_helpers = [
            "p2p_mix3(matrix<int> target, int row, int value, int tag) =>",
            "    matrix.set(target, row, 0, p2p_mix(matrix.get(target, row, 0), value, 1000003, 257, tag))",
            "    matrix.set(target, row, 1, p2p_mix(matrix.get(target, row, 1), value, 1000033, 263, tag))",
            "    matrix.set(target, row, 2, p2p_mix(matrix.get(target, row, 2), value, 1000037, 269, tag))",
            "p2p_init_hashes(int rows) =>",
            "    result = matrix.new<int>(rows, 3, 0)",
            "    for row = 0 to rows - 1",
            "        matrix.set(result, row, 0, 17)",
            "        matrix.set(result, row, 1, 19)",
            "        matrix.set(result, row, 2, 23)",
            "    result",
        ]
        row_triplet_helper = [
            "p2p_triplet_row(matrix<int> target, int row) =>",
            "    p2p_triplet(matrix.get(target, row, 0), matrix.get(target, row, 1), matrix.get(target, row, 2))",
        ]
        state_lines = [
            "var p2p_meta = array.from(0, int(na), int(na))",
            f"var p2p_hashes = p2p_init_hashes({hash_row_count})",
        ]
        window_lines = [
            "if p2p_in_window",
            "    p2p_bar_count = array.get(p2p_meta, 0) + 1",
            "    array.set(p2p_meta, 0, p2p_bar_count)",
            "    array.set(p2p_meta, 1, na(array.get(p2p_meta, 1)) ? time : array.get(p2p_meta, 1))",
            "    array.set(p2p_meta, 2, time)",
        ]
    else:
        mix_helpers = [
            "p2p_mix3(array<int> target, int value, int tag) =>",
            "    array.set(target, 0, p2p_mix(array.get(target, 0), value, 1000003, 257, tag))",
            "    array.set(target, 1, p2p_mix(array.get(target, 1), value, 1000033, 263, tag))",
            "    array.set(target, 2, p2p_mix(array.get(target, 2), value, 1000037, 269, tag))",
        ]
        row_triplet_helper = []
        state_lines = [
            "var int p2p_bar_count = 0",
            "var int p2p_first_time = na",
            "var int p2p_last_time = na",
            "var p2p_data_h = array.from(17, 19, 23)",
            f"var p2p_seg_h1 = array.new_int({request.segments}, 17)",
            f"var p2p_seg_h2 = array.new_int({request.segments}, 19)",
            f"var p2p_seg_h3 = array.new_int({request.segments}, 23)",
            *(f"var p2p_{name}_h = array.from(17, 19, 23)" for name in stream_names),
            *(
                ["var p2p_trades_h = array.from(17, 19, 23)"]
                if request.declaration_kind == "strategy"
                else []
            ),
        ]
        window_lines = [
            "if p2p_in_window",
            "    p2p_bar_count += 1",
            "    p2p_first_time := na(p2p_first_time) ? time : p2p_first_time",
            "    p2p_last_time := time",
        ]
    lines = [
        "",
        "// === Pine2Python TradingView Parity Proof Dashboard v2 ===",
        f'p2p_start = input.time({request.start_ms}, "P2P proof start")',
        f'p2p_end = input.time({request.end_ms}, "P2P proof end")',
        f'p2p_mintick = input.float({request.mintick:.12g}, "P2P expected minimum tick", minval=0.000000000001)',
        "p2p_in_window = time >= p2p_start and time < p2p_end",
            "p2p_posmod(int value, int modulus) =>",
            "    ((value % modulus) + modulus) % modulus",
            "p2p_round(float value) =>",
            "    int(math.floor(value + 0.500000001))",
            "p2p_mix(int current, int value, int modulus, int multiplier, int tag) =>",
        "    p2p_posmod(p2p_posmod(current * multiplier, modulus) + p2p_posmod(value, modulus) + tag * 17, modulus)",
        *mix_helpers,
        "p2p_triplet(int h1, int h2, int h3) =>",
        '    str.tostring(h1, "0000000") + "-" + str.tostring(h2, "0000000") + "-" + str.tostring(h3, "0000000")',
        *row_triplet_helper,
        *state_lines,
        "int p2p_value = 0",
    ]
    lines.extend(window_lines)
    dataset_values = [
        ("p2p_bar_count", 1),
        ("int(time / 1000)", 2),
        ("p2p_round(open / p2p_mintick)", 3),
        ("p2p_round(high / p2p_mintick)", 4),
        ("p2p_round(low / p2p_mintick)", 5),
        ("p2p_round(close / p2p_mintick)", 6),
    ]
    data_target = (
        f"p2p_hashes, {data_row}" if packed_proof else "p2p_data_h"
    )
    for value, tag in dataset_values:
        lines.extend(_pine_mix_array_value_lines(data_target, value, tag))
    if packed_proof:
        lines.extend(
            [
                f"    p2p_seg = {segment_row_start} + math.min({request.segments - 1}, math.max(0, int((time - p2p_start) * {request.segments} / math.max(p2p_end - p2p_start, 1))))",
                "    p2p_s1 = matrix.get(p2p_hashes, p2p_seg, 0)",
                "    p2p_s2 = matrix.get(p2p_hashes, p2p_seg, 1)",
                "    p2p_s3 = matrix.get(p2p_hashes, p2p_seg, 2)",
            ]
        )
    else:
        lines.extend(
            [
                f"    p2p_seg = math.min({request.segments - 1}, math.max(0, int((time - p2p_start) * {request.segments} / math.max(p2p_end - p2p_start, 1))))",
                "    p2p_s1 = array.get(p2p_seg_h1, p2p_seg)",
                "    p2p_s2 = array.get(p2p_seg_h2, p2p_seg)",
                "    p2p_s3 = array.get(p2p_seg_h3, p2p_seg)",
            ]
        )
    for value, tag in dataset_values:
        lines.extend(_pine_mix_value_lines("p2p_s", value, tag))
    lines.extend(
        (
            [
                "    matrix.set(p2p_hashes, p2p_seg, 0, p2p_s1)",
                "    matrix.set(p2p_hashes, p2p_seg, 1, p2p_s2)",
                "    matrix.set(p2p_hashes, p2p_seg, 2, p2p_s3)",
            ]
            if packed_proof
            else [
                "    array.set(p2p_seg_h1, p2p_seg, p2p_s1)",
                "    array.set(p2p_seg_h2, p2p_seg, p2p_s2)",
                "    array.set(p2p_seg_h3, p2p_seg, p2p_s3)",
            ]
        )
    )
    for stream_name, expressions in request.stream_expressions.items():
        stream_target = (
            f"p2p_hashes, {stream_rows[stream_name]}"
            if packed_proof
            else f"p2p_{stream_name}_h"
        )
        lines.extend(
            _pine_mix_array_value_lines(
                stream_target, "p2p_bar_count", 1
            )
        )
        lines.extend(
            _pine_mix_array_value_lines(
                stream_target, "int(time / 1000)", 2
            )
        )
        for tag, expression in enumerate(expressions, start=10):
            lines.extend(
                _pine_mix_array_value_lines(
                    stream_target, _pine_value(expression), tag
                )
            )
    if request.declaration_kind == "strategy":
        lines.extend(
            [
                "if strategy.closedtrades > nz(strategy.closedtrades[1])",
                "    p2p_ti = strategy.closedtrades - 1",
            ]
        )
        trade_values = [
            ("strategy.closedtrades.entry_time(p2p_ti) / 1000", 30),
            ("strategy.closedtrades.exit_time(p2p_ti) / 1000", 31),
            (
                "p2p_round(strategy.closedtrades.entry_price(p2p_ti) / p2p_mintick)",
                32,
            ),
            (
                "p2p_round(strategy.closedtrades.exit_price(p2p_ti) / p2p_mintick)",
                33,
            ),
            ("p2p_round(strategy.closedtrades.size(p2p_ti) * 1000000)", 34),
            ("p2p_round(strategy.closedtrades.profit(p2p_ti) * 1000000)", 35),
        ]
        for value, tag in trade_values:
            trade_target = (
                f"p2p_hashes, {trades_row}"
                if packed_proof
                else "p2p_trades_h"
            )
            lines.extend(
                _pine_mix_array_value_lines(
                    trade_target, f"int({value})", tag
                )
            )
    bars_expression = (
        "array.get(p2p_meta, 0)" if packed_proof else "p2p_bar_count"
    )
    first_expression = (
        "array.get(p2p_meta, 1)" if packed_proof else "p2p_first_time"
    )
    last_expression = (
        "array.get(p2p_meta, 2)" if packed_proof else "p2p_last_time"
    )
    data_triplet = (
        f"p2p_triplet_row(p2p_hashes, {data_row})"
        if packed_proof
        else "p2p_triplet(array.get(p2p_data_h, 0), array.get(p2p_data_h, 1), array.get(p2p_data_h, 2))"
    )
    lines.extend(
        [
            # Keep proof evidence out of the conventional top-right location
            # used by many source-owned status dashboards. A hidden/cleared
            # source table can still cover another table at the same anchor.
            f"var table p2p_table = table.new(position.bottom_right, 2, {row_count}, bgcolor=color.new(color.black, 5), frame_color=color.gray, frame_width=1)",
            "p2p_cell(int row, string label, string value) =>",
            "    table.cell(p2p_table, 0, row, label, text_color=color.silver, text_halign=text.align_left)",
            "    table.cell(p2p_table, 1, row, value, text_color=color.white, text_halign=text.align_right)",
            "if barstate.islast",
            f'    p2p_cell(0, "P2P PROOF", "{request.profile} / {DASHBOARD_VERSION}")',
            f'    p2p_cell(1, "SOURCE", "{base_source_sha256[:16]}")',
            f'    p2p_cell(2, "SETTINGS", "{settings_sha256[:16]}")',
            f'    p2p_cell(3, "EXPECTED CONTEXT", "{request.symbol} / {request.timeframe}")',
            '    p2p_cell(4, "WINDOW", str.tostring(p2p_start) + ".." + str.tostring(p2p_end))',
            f'    p2p_cell(5, "BARS", str.tostring({bars_expression}))',
            f'    p2p_cell(6, "FIRST/LAST", str.tostring({first_expression}) + "/" + str.tostring({last_expression}))',
            f'    p2p_cell(7, "DATA", {data_triplet})',
            '    p2p_cell(8, "MINTICK", str.tostring(p2p_mintick))',
        ]
    )
    row = 9
    for stream_name in stream_names:
        stream_triplet = (
            f"p2p_triplet_row(p2p_hashes, {stream_rows[stream_name]})"
            if packed_proof
            else f"p2p_triplet(array.get(p2p_{stream_name}_h, 0), array.get(p2p_{stream_name}_h, 1), array.get(p2p_{stream_name}_h, 2))"
        )
        lines.append(
            f'    p2p_cell({row}, "{stream_name.upper()}", {stream_triplet})'
        )
        row += 1
    for segment in range(request.segments):
        segment_triplet = (
            f"p2p_triplet_row(p2p_hashes, {segment_row_start + segment})"
            if packed_proof
            else f"p2p_triplet(array.get(p2p_seg_h1, {segment}), array.get(p2p_seg_h2, {segment}), array.get(p2p_seg_h3, {segment}))"
        )
        lines.append(
            f'    p2p_cell({row}, "DATA SEG {segment + 1}", {segment_triplet})'
        )
        row += 1
    if request.declaration_kind == "strategy":
        trades_triplet = (
            f"p2p_triplet_row(p2p_hashes, {trades_row})"
            if packed_proof
            else "p2p_triplet(array.get(p2p_trades_h, 0), array.get(p2p_trades_h, 1), array.get(p2p_trades_h, 2))"
        )
        lines.extend(
            [
                f'    p2p_cell({row}, "TRADES", {trades_triplet})',
                f'    p2p_cell({row + 1}, "CLOSED/W/L", str.tostring(strategy.closedtrades) + "/" + str.tostring(strategy.wintrades) + "/" + str.tostring(strategy.losstrades))',
                f'    p2p_cell({row + 2}, "NET PROFIT", str.tostring(strategy.netprofit))',
                f'    p2p_cell({row + 3}, "MAX DRAWDOWN", str.tostring(strategy.max_drawdown))',
                f'    p2p_cell({row + 4}, "FINAL POSITION", str.tostring(strategy.position_size))',
            ]
        )
    if emit_runtime_plots:
        lines.extend(
            [
                'plot(array.get(p2p_data_h, 0), "p2p__proof__data_h1", display=display.none)',
                'plot(array.get(p2p_data_h, 1), "p2p__proof__data_h2", display=display.none)',
                'plot(array.get(p2p_data_h, 2), "p2p__proof__data_h3", display=display.none)',
            ]
        )
        for stream_name in stream_names:
            lines.extend(
                [
                    f'plot(array.get(p2p_{stream_name}_h, 0), "p2p__proof__{stream_name}_h1", display=display.none)',
                    f'plot(array.get(p2p_{stream_name}_h, 1), "p2p__proof__{stream_name}_h2", display=display.none)',
                    f'plot(array.get(p2p_{stream_name}_h, 2), "p2p__proof__{stream_name}_h3", display=display.none)',
                ]
            )
        for stream_name, expressions in request.stream_expressions.items():
            for expression in expressions:
                title = _trace_plot_title(stream_name, expression)
                if not _source_exposes_trace_title(request.source, title):
                    lines.append(
                        f'plot({_trace_plot_value(expression)}, "{title}", display=display.none)'
                    )
        for segment in range(request.segments):
            for lane in range(1, 4):
                lines.append(
                    f'plot(array.get(p2p_seg_h{lane}, {segment}), "p2p__proof__segment_{segment + 1}_h{lane}", display=display.none)'
                )
    else:
        lines = _wrap_table_dashboard_body(lines, request)
    if emit_runtime_plots:
        proof_source = request.source
    else:
        proof_source, _, _ = _compact_table_proof_source(request.source)
    return proof_source.rstrip() + "\n" + "\n".join(lines) + "\n"


def create_proof(request: ProofRequest) -> dict[str, Any]:
    source_bytes = request.source.encode("utf-8")
    base_source_sha256 = sha256_bytes(source_bytes)
    source_id = request.source_id or base_source_sha256[:20]
    settings_sha256 = sha256_json(request.settings)
    candles = _included_candles(request)
    rows = _bar_values(candles, request.mintick)
    dataset_values = [value for row in rows for value in row]
    data_fp = _fingerprint(dataset_values)
    segment_values: list[list[tuple[int, int]]] = [[] for _ in range(request.segments)]
    for candle, row in zip(candles, rows, strict=True):
        segment_values[
            _segment_index(
                candle.time, request.start_ms, request.end_ms, request.segments
            )
        ].extend(row)
    segment_fps = [_fingerprint(values) for values in segment_values]
    trace_by_time = {
        int(row["time"]): row for row in request.trace_rows if "time" in row
    }
    stream_fps: dict[str, tuple[int, int, int]] = {}
    for stream_name, expressions in request.stream_expressions.items():
        if not expressions or not request.trace_rows:
            continue
        stream_fps[stream_name] = _stream_fingerprint(
            stream_name,
            candles,
            trace_by_time,
            expressions,
            request.mintick,
        )
    dashboard_values = {
        "PROFILE": f"{request.profile} / {DASHBOARD_VERSION}",
        "SOURCE": base_source_sha256[:16],
        "SETTINGS": settings_sha256[:16],
        "WINDOW": f"{request.start_ms}..{request.end_ms}",
        "BARS": str(len(candles)),
        "FIRST/LAST": f"{candles[0].time}/{candles[-1].time}",
        "DATA": _format_fingerprint(data_fp),
        **{
            stream_name.upper(): _format_fingerprint(fp)
            for stream_name, fp in stream_fps.items()
        },
        **{
            f"DATA SEG {index + 1}": _format_fingerprint(fp)
            for index, fp in enumerate(segment_fps)
        },
    }
    instrumented_source = generate_dashboard_source(
        request,
        base_source_sha256=base_source_sha256,
        settings_sha256=settings_sha256,
    )
    (
        _,
        removed_hidden_trace_plots,
        compacted_source_blocks,
    ) = _compact_table_proof_source(request.source)
    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "status": "TRADINGVIEW_REVIEW_REQUIRED",
        "profile": {
            "id": request.profile,
            "instrumentation_version": request.instrumentation_version,
            "max_bars": BASIC_PROFILE_MAX_BARS
            if request.profile == "basic_v1"
            else None,
            "tradingview_plot_limit": TRADINGVIEW_PLOT_LIMIT,
            "appended_tradingview_plot_calls": 0,
            "removed_hidden_trace_plot_calls": len(removed_hidden_trace_plots),
            "compacted_source_blocks": compacted_source_blocks,
            "instrumentation_transforms": [
                "pack proof fingerprints into one hash matrix and one metadata array",
                "split hashing and rendering into bounded helper functions",
                *(
                    [
                        "move explicitly marked source-owned rendering blocks into proof-only helpers"
                    ]
                    if compacted_source_blocks
                    else []
                ),
                *(
                    [
                        "remove standalone p2p__ display.none trace plots for table-only proof"
                    ]
                    if removed_hidden_trace_plots
                    else []
                ),
            ],
            "manual_steps": [
                "Open the exact TradingView symbol and timeframe.",
                "Paste/add the table-only instrumented frozen Pine and set the supplied proof window and strategy inputs.",
                "Capture the complete parity-proof dashboard in one screenshot.",
                "Submit the displayed values and screenshot hash to StrategyLab.",
            ],
        },
        "identity": {
            "source_id": source_id,
            "source_sha256": base_source_sha256,
            "settings_sha256": settings_sha256,
            "instrumentation_version": request.instrumentation_version,
            "instrumented_source_sha256": sha256_bytes(
                instrumented_source.encode("utf-8")
            ),
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "dataset_file_sha256": request.dataset_sha256,
        },
        "window": {
            "start_ms": request.start_ms,
            "end_ms": request.end_ms,
            "bar_count": len(candles),
            "first_time_ms": candles[0].time,
            "last_time_ms": candles[-1].time,
            "mintick": request.mintick,
        },
        "dataset": {
            "fingerprint": list(data_fp),
            "segments": [list(value) for value in segment_fps],
            "volume_included": False,
        },
        "streams": {
            name: {"fingerprint": list(value)} for name, value in stream_fps.items()
        },
        "dashboard_values": dashboard_values,
        "instrumented_source": instrumented_source,
    }


def compare_tradingview_observation(
    request: TradingViewObservationRequest,
) -> dict[str, Any]:
    expected_values = request.expected.get("dashboard_values", request.expected)
    observed_values = request.observed.get("dashboard_values", request.observed)
    if not isinstance(expected_values, dict) or not isinstance(observed_values, dict):
        raise Pine2PythonError(
            "INVALID_OBSERVATION",
            "Expected and observed dashboard values must be mappings.",
        )
    mismatches = []
    for key, expected in expected_values.items():
        observed = observed_values.get(key)
        if str(observed) != str(expected):
            mismatches.append(
                {"field": key, "expected": str(expected), "observed": observed}
            )
    extras = sorted(set(observed_values) - set(expected_values))
    data_match = not any(
        item["field"] in {"DATA", "BARS", "FIRST/LAST", "WINDOW"} for item in mismatches
    )
    exact_match = not mismatches
    if request.user_verdict == "accepted":
        if not request.screenshot_sha256 or len(request.screenshot_sha256) != 64:
            raise Pine2PythonError(
                "SCREENSHOT_EVIDENCE_REQUIRED",
                "An accepted TradingView observation requires a 64-character screenshot SHA-256.",
            )
        if not exact_match:
            raise Pine2PythonError(
                "CANNOT_ACCEPT_MISMATCH",
                "TradingView evidence cannot be accepted while dashboard values mismatch.",
                {"mismatches": mismatches[:25]},
            )
    statuses = [
        "TRADINGVIEW_SIGNATURE_MATCH"
        if exact_match
        else "TRADINGVIEW_SIGNATURE_MISMATCH"
    ]
    if request.user_verdict == "accepted":
        statuses.append("TRADINGVIEW_ACCEPTED")
    elif request.user_verdict == "rejected":
        statuses.append("TRADINGVIEW_REJECTED")
    elif request.user_verdict == "pending":
        statuses.append("TRADINGVIEW_REVIEW_REQUIRED")
    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "status": statuses,
        "exact_match": exact_match,
        "dataset_match": data_match,
        "mismatches": mismatches,
        "extra_observed_fields": extras,
        "screenshot_sha256": request.screenshot_sha256,
        "user_verdict": request.user_verdict,
        "next_action": (
            "accept_or_review_remaining_visual_claims"
            if exact_match
            else (
                "fix_symbol_timeframe_window_or_feed"
                if not data_match
                else "inspect_first_mismatching_stream_and_segment"
            )
        ),
    }
