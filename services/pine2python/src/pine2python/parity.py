from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .errors import Pine2PythonError
from .models import ParityContract
from .version import TRACE_SCHEMA_VERSION


def _value_at(row: dict[str, Any], path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _has_value_at(row: dict[str, Any], path: str) -> bool:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return True


def _key_identity(value: Any, *, side: str, row_index: int, path: str) -> tuple[str, Any]:
    if value is None:
        raise Pine2PythonError(
            "TRACE_KEY_MISSING",
            f"Every trace row must include key '{path}'.",
            {"side": side, "row_index": row_index, "key": path},
        )
    if type(value) is str:
        return ("str", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is float and math.isfinite(value):
        return ("float", value)
    raise Pine2PythonError(
        "TRACE_KEY_INVALID",
        f"Trace key '{path}' must be a finite JSON string or number.",
        {"side": side, "row_index": row_index, "key": path, "value": value},
    )


def _index_rows(
    rows: list[dict[str, Any]], *, side: str, key_path: str
) -> tuple[dict[tuple[str, Any], tuple[Any, dict[str, Any]]], list[tuple[str, Any]]]:
    indexed: dict[tuple[str, Any], tuple[Any, dict[str, Any]]] = {}
    order: list[tuple[str, Any]] = []
    positions: dict[tuple[str, Any], int] = {}
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Pine2PythonError(
                "TRACE_ROW_INVALID",
                "Every trace row must be an object.",
                {"side": side, "row_index": row_index},
            )
        if not _has_value_at(row, key_path):
            raise Pine2PythonError(
                "TRACE_KEY_MISSING",
                f"Every trace row must include key '{key_path}'.",
                {"side": side, "row_index": row_index, "key": key_path},
            )
        value = _value_at(row, key_path)
        identity = _key_identity(value, side=side, row_index=row_index, path=key_path)
        if identity in indexed:
            raise Pine2PythonError(
                "TRACE_DUPLICATE_KEY",
                f"Trace rows must have unique key '{key_path}'.",
                {
                    "side": side,
                    "key": value,
                    "row_indexes": [positions[identity], row_index],
                },
            )
        indexed[identity] = (value, row)
        positions[identity] = row_index
        order.append(identity)
    return indexed, order


def _require_fields(
    rows: list[dict[str, Any]], *, side: str, fields: list[str]
) -> None:
    for row_index, row in enumerate(rows):
        for field in fields:
            if not _has_value_at(row, field):
                raise Pine2PythonError(
                    "TRACE_FIELD_MISSING",
                    f"Required trace field '{field}' is missing.",
                    {"side": side, "row_index": row_index, "field": field},
                )


def _same_exact(left: Any, right: Any) -> bool:
    if (
        isinstance(left, float)
        and isinstance(right, float)
        and math.isnan(left)
        and math.isnan(right)
    ):
        return True
    return left == right


def compare_traces(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    contract: ParityContract,
) -> dict[str, Any]:
    key = contract.key
    reference_by_key, reference_order = _index_rows(
        reference_rows, side="reference", key_path=key
    )
    candidate_by_key, candidate_order = _index_rows(
        candidate_rows, side="candidate", key_path=key
    )
    required_fields = list(dict.fromkeys([*contract.exact_fields, *contract.tolerance_fields]))
    _require_fields(reference_rows, side="reference", fields=required_fields)
    _require_fields(candidate_rows, side="candidate", fields=required_fields)
    reference_keys = set(reference_by_key)
    candidate_keys = set(candidate_by_key)
    missing_ids = [identity for identity in reference_order if identity not in candidate_keys]
    extra_ids = [identity for identity in candidate_order if identity not in reference_keys]
    missing = [reference_by_key[identity][0] for identity in missing_ids]
    extra = [candidate_by_key[identity][0] for identity in extra_ids]
    mismatches: list[dict[str, Any]] = []
    for identity in reference_order:
        if identity not in candidate_by_key:
            continue
        row_key = reference_by_key[identity][0]
        reference = reference_by_key[identity][1]
        candidate = candidate_by_key[identity][1]
        for field in contract.exact_fields:
            left = _value_at(reference, field)
            right = _value_at(candidate, field)
            if not _same_exact(left, right):
                mismatches.append(
                    {
                        "key": row_key,
                        "field": field,
                        "reference": left,
                        "candidate": right,
                        "policy": "exact",
                    }
                )
        for field, tolerance in contract.tolerance_fields.items():
            left = _value_at(reference, field)
            right = _value_at(candidate, field)
            if left is None or right is None:
                same = left is right
                delta = None
            else:
                try:
                    delta = abs(float(left) - float(right))
                    same = delta <= tolerance
                except (TypeError, ValueError):
                    delta = None
                    same = False
            if not same:
                mismatches.append(
                    {
                        "key": row_key,
                        "field": field,
                        "reference": left,
                        "candidate": right,
                        "delta": delta,
                        "tolerance": tolerance,
                        "policy": "tolerance",
                    }
                )
    key_mismatch = bool(missing or extra) and contract.require_same_keys
    alignment_mismatches = []
    if key_mismatch:
        alignment_mismatches = [
            {
                "key": row_key,
                "field": "$alignment",
                "reference": "present",
                "candidate": "missing",
                "policy": "same_keys",
            }
            for row_key in missing
        ] + [
            {
                "key": row_key,
                "field": "$alignment",
                "reference": "missing",
                "candidate": "present",
                "policy": "same_keys",
            }
            for row_key in extra
        ]
    all_mismatches = alignment_mismatches + mismatches
    passed = not all_mismatches
    field_counts = Counter(item["field"] for item in all_mismatches)
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "status": "PARITY_PASS" if passed else "PARITY_FAIL",
        "passed": passed,
        "alignment": {
            "key": key,
            "reference_rows": len(reference_rows),
            "candidate_rows": len(candidate_rows),
            "aligned_rows": len(reference_keys & candidate_keys),
            "missing_candidate_keys": missing[:100],
            "extra_candidate_keys": extra[:100],
        },
        "summary": {
            "mismatch_count": len(all_mismatches),
            "mismatch_fields": dict(sorted(field_counts.items())),
            "first_divergence": all_mismatches[0] if all_mismatches else None,
        },
        "mismatches": all_mismatches[:10_000],
    }
