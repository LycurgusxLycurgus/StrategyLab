from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from pynescript.ast import dump as dump_ast
from pynescript.ast import parse as parse_pine
from pynescript.ast import unparse as unparse_pine

from .errors import Pine2PythonError
from .hashing import sha256_bytes
from .version import SCHEMA_VERSION

CALL_RE = re.compile(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\s*\(")
INPUT_RE = re.compile(
    r"(?m)^\s*(?:var\s+|varip\s+)?([A-Za-z_]\w*)\s*=\s*input(?:\.[A-Za-z_]\w*)?\s*\("
)
FUNCTION_RE = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*\([^=\n]*\)\s*=>")
STATE_RE = re.compile(
    r"(?m)^\s*(varip|var)\s+(?:(?:int|float|bool|string|color|line|label|box|table)\s+)?([A-Za-z_]\w*)"
)
HISTORY_RE = re.compile(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\[\s*([^\]]+)\s*\]")
DECLARATION_RE = re.compile(r"\b(strategy|indicator|library)\s*\(")
VERSION_RE = re.compile(r"(?m)^\s*//@version\s*=\s*(\d+)\s*$")
PLOT_BUDGET_CALL_RE = re.compile(
    r"(?m)^\s*(plot|plotshape|plotchar|plotarrow|plotbar|plotcandle|"
    r"alertcondition|bgcolor|barcolor|fill)\s*\("
)
LOOKAHEAD_SECURITY_RE = re.compile(
    r"request\.security\((?P<call>[^\n]*?barmerge\.lookahead_on[^\n]*?)\)"
)
CONFIRMED_SOURCE_OFFSET_RE = re.compile(r"\[\s*[1-9]\d*\s*\]")
PINE_PLOT_LIMIT = 64

DRAWING_PREFIXES = ("line.", "label.", "box.", "table.", "polyline.")
STRATEGY_PREFIXES = ("strategy.",)
REQUEST_PREFIXES = ("request.",)
ALERT_PREFIXES = ("alert", "alertcondition")


def _sorted_calls(source: str) -> list[str]:
    return sorted(set(CALL_RE.findall(source)))


@lru_cache(maxsize=32)
def analyze_source(
    source: str,
    *,
    name: str = "strategy.pine",
    max_source_bytes: int = 1_000_000,
) -> dict[str, Any]:
    original = source.encode("utf-8")
    if not source.strip():
        raise Pine2PythonError("EMPTY_SOURCE", "Pine source is empty.")
    if len(original) > max_source_bytes:
        raise Pine2PythonError(
            "SOURCE_TOO_LARGE",
            f"Pine source exceeds {max_source_bytes} bytes.",
            {"bytes": len(original), "limit": max_source_bytes},
            413,
        )
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    normalized_bytes = normalized.encode("utf-8")
    calls = _sorted_calls(normalized)
    declaration_match = DECLARATION_RE.search(normalized)
    version_match = VERSION_RE.search(normalized)
    parser_status = "PARSE_COMPLETE"
    parser_error: str | None = None
    ast_dump: str | None = None
    normalized_unparse: str | None = None
    try:
        node = parse_pine(normalized, name)
        ast_dump = dump_ast(node, indent=2)
        normalized_unparse = unparse_pine(node)
    except Exception as exc:  # Pynescript exposes several generated exception types.
        parser_status = "PARSE_PARTIAL"
        parser_error = f"{type(exc).__name__}: {exc}"

    stateful = [
        {"kind": match.group(1), "name": match.group(2)}
        for match in STATE_RE.finditer(normalized)
    ]
    history = [
        {"series": match.group(1), "offset": match.group(2).strip()}
        for match in HISTORY_RE.finditer(normalized)
    ]
    strategy_calls = [call for call in calls if call.startswith(STRATEGY_PREFIXES)]
    request_calls = [call for call in calls if call.startswith(REQUEST_PREFIXES)]
    drawing_calls = [call for call in calls if call.startswith(DRAWING_PREFIXES)]
    alert_calls = [
        call
        for call in calls
        if call.startswith(ALERT_PREFIXES) or call == "alertcondition"
    ]
    plot_budget_call_counts: dict[str, int] = {}
    for match in PLOT_BUDGET_CALL_RE.finditer(normalized):
        call_name = match.group(1)
        plot_budget_call_counts[call_name] = (
            plot_budget_call_counts.get(call_name, 0) + 1
        )
    minimum_plot_count = sum(plot_budget_call_counts.values())
    tradingview_blockers: list[dict[str, str]] = []
    if minimum_plot_count > PINE_PLOT_LIMIT:
        tradingview_blockers.append(
            {
                "code": "TRADINGVIEW_PLOT_LIMIT_EXCEEDED",
                "message": (
                    f"Source declares at least {minimum_plot_count} plot-count "
                    f"calls; TradingView permits {PINE_PLOT_LIMIT}."
                ),
            }
        )
    temporal_findings: list[dict[str, str]] = []
    if any(item["kind"] == "varip" for item in stateful):
        temporal_findings.append(
            {
                "code": "VARIP_REALTIME_STATE",
                "severity": "high",
                "message": "varip persists within realtime bars and cannot be proven from close-only history.",
            }
        )
    if "barmerge.lookahead_on" in normalized:
        lookahead_calls = [
            match.group("call")
            for match in LOOKAHEAD_SECURITY_RE.finditer(normalized)
        ]
        safe_confirmed_calls = [
            call
            for call in lookahead_calls
            if CONFIRMED_SOURCE_OFFSET_RE.search(call)
        ]
        if (
            lookahead_calls
            and len(safe_confirmed_calls) == len(lookahead_calls)
        ):
            temporal_findings.append(
                {
                    "code": "CONFIRMED_HTF_LOOKAHEAD_PATTERN",
                    "severity": "low",
                    "message": (
                        "Every request.security lookahead_on call uses a "
                        "positive source-history offset; TradingView review "
                        "must still confirm timeframe ownership."
                    ),
                }
            )
        else:
            temporal_findings.append(
                {
                    "code": "LOOKAHEAD_ON",
                    "severity": "high",
                    "message": (
                        "request lookahead_on can expose future "
                        "higher-timeframe values."
                    ),
                }
            )
    if 56 <= minimum_plot_count <= PINE_PLOT_LIMIT:
        temporal_findings.append(
            {
                "code": "TRADINGVIEW_PLOT_LIMIT_NEAR_CAPACITY",
                "severity": "medium",
                "message": (
                    f"The script declares at least {minimum_plot_count} of "
                    "64 TradingView plot-count calls. Series-valued colors or "
                    "other parameters can consume additional counts; new plots "
                    "or alertconditions require consolidation."
                ),
            }
        )
    elif minimum_plot_count > PINE_PLOT_LIMIT:
        temporal_findings.append(
            {
                "code": "TRADINGVIEW_PLOT_LIMIT_EXCEEDED",
                "severity": "high",
                "message": tradingview_blockers[0]["message"],
            }
        )
    if "barstate.isrealtime" in normalized or "barstate.isconfirmed" in normalized:
        temporal_findings.append(
            {
                "code": "BARSTATE_DEPENDENCE",
                "severity": "medium",
                "message": "Behavior depends on historical/realtime confirmation state.",
            }
        )
    if re.search(r"\bcalc_on_every_tick\s*=\s*true\b", normalized):
        temporal_findings.append(
            {
                "code": "INTRABAR_RECALCULATION",
                "severity": "high",
                "message": "calc_on_every_tick requires focused TradingView realtime review.",
            }
        )
    if request_calls:
        temporal_findings.append(
            {
                "code": "TIME_OWNERSHIP_REQUEST",
                "severity": "medium",
                "message": "request.* changes symbol/timeframe ownership and is not locally assumed safe.",
            }
        )

    runtime_blockers: list[dict[str, str]] = []
    if request_calls:
        runtime_blockers.append(
            {
                "code": "REQUEST_RUNTIME_UNVERIFIED",
                "message": "Network-free local runtime does not execute request.* by default.",
            }
        )
    if any(item["kind"] == "varip" for item in stateful):
        runtime_blockers.append(
            {
                "code": "VARIP_RUNTIME_UNVERIFIED",
                "message": "Historical PineTS execution cannot establish realtime varip behavior.",
            }
        )
    if re.search(r"\b(import|request\.seed)\b", normalized):
        runtime_blockers.append(
            {
                "code": "EXTERNAL_CODE_OR_DATA",
                "message": "Imported libraries and request.seed are outside the local execution boundary.",
            }
        )

    inventory = {
        "pine_version": int(version_match.group(1)) if version_match else None,
        "declaration": declaration_match.group(1) if declaration_match else None,
        "inputs": sorted(set(INPUT_RE.findall(normalized))),
        "functions": sorted(set(FUNCTION_RE.findall(normalized))),
        "stateful_variables": stateful,
        "history_references": history,
        "request_calls": request_calls,
        "strategy_calls": strategy_calls,
        "drawing_calls": drawing_calls,
        "alert_calls": alert_calls,
        "plot_budget": {
            "minimum_count": minimum_plot_count,
            "limit": PINE_PLOT_LIMIT,
            "remaining_minimum": PINE_PLOT_LIMIT - minimum_plot_count,
            "call_counts": dict(sorted(plot_budget_call_counts.items())),
        },
        "all_namespace_calls": calls,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": [
            "SOURCE_ACCEPTED",
            parser_status,
            "STATIC_REVIEW_COMPLETE",
            "LOCAL_RUNTIME_SUPPORTED"
            if not runtime_blockers
            else "TRADINGVIEW_REVIEW_REQUIRED",
        ],
        "source": {
            "name": name,
            "bytes": len(original),
            "sha256": sha256_bytes(original),
            "normalized_sha256": sha256_bytes(normalized_bytes),
        },
        "parser": {
            "adapter": "pynescript",
            "version": "0.3.0",
            "status": parser_status,
            "error": parser_error,
            "ast_dump": ast_dump,
            "normalized_source": normalized_unparse,
        },
        "inventory": inventory,
        "temporal_findings": temporal_findings,
        "capabilities": {
            "static_analysis": "supported",
            "local_runtime": "supported" if not runtime_blockers else "blocked",
            "runtime_blockers": runtime_blockers,
            "tradingview_compile": "external_required",
            "tradingview_blockers": tradingview_blockers,
            "tradingview_parity_proof": "instrumentation_supported",
            "arbitrary_python_translation": "unsupported",
        },
    }
