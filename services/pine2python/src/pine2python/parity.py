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
    reference_by_key = {_value_at(row, key): row for row in reference_rows}
    candidate_by_key = {_value_at(row, key): row for row in candidate_rows}
    if None in reference_by_key or None in candidate_by_key:
        raise Pine2PythonError(
            "TRACE_KEY_MISSING", f"Every trace row must include key '{key}'."
        )
    reference_keys = set(reference_by_key)
    candidate_keys = set(candidate_by_key)
    missing = sorted(reference_keys - candidate_keys)
    extra = sorted(candidate_keys - reference_keys)
    mismatches: list[dict[str, Any]] = []
    for row_key in sorted(reference_keys & candidate_keys):
        reference = reference_by_key[row_key]
        candidate = candidate_by_key[row_key]
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
    passed = not key_mismatch and not mismatches
    field_counts = Counter(item["field"] for item in mismatches)
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
            "mismatch_count": len(mismatches),
            "mismatch_fields": dict(sorted(field_counts.items())),
            "first_divergence": mismatches[0] if mismatches else None,
        },
        "mismatches": mismatches[:10_000],
    }
