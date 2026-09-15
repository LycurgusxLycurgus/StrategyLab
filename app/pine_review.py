from __future__ import annotations

import hashlib
from typing import Any


class PineReviewContractError(ValueError):
    pass


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _region(source: str, region: dict[str, Any]) -> dict[str, Any]:
    name = str(region.get("name") or "").strip()
    start_marker = str(region.get("start_marker") or "")
    end_marker = str(region.get("end_marker") or "")
    if not name or not start_marker or not end_marker:
        raise PineReviewContractError(
            "Each protected region requires name, start_marker, and end_marker."
        )
    if source.count(start_marker) != 1:
        raise PineReviewContractError(
            f"Protected region {name!r} start marker must occur exactly once."
        )
    start = source.index(start_marker)
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        raise PineReviewContractError(
            f"Protected region {name!r} end marker was not found after its start."
        )
    payload = source[start:end]
    start_line = source.count("\n", 0, start) + 1
    end_line = source.count("\n", 0, end) + 1
    return {
        "name": name,
        "start_marker": start_marker,
        "end_marker": end_marker,
        "start_line": start_line,
        "end_line_exclusive": end_line,
        "bytes": len(payload.encode("utf-8")),
        "sha256": _sha256_text(payload),
    }


def compare_protected_regions(
    baseline_source: str,
    candidate_source: str,
    protected_regions: list[dict[str, Any]],
) -> dict[str, Any]:
    if not protected_regions:
        raise PineReviewContractError(
            "At least one protected source region is required."
        )
    comparisons: list[dict[str, Any]] = []
    for specification in protected_regions:
        baseline = _region(baseline_source, specification)
        candidate = _region(candidate_source, specification)
        comparisons.append(
            {
                "name": baseline["name"],
                "matches": baseline["sha256"] == candidate["sha256"],
                "baseline": baseline,
                "candidate": candidate,
            }
        )
    return {
        "status": (
            "SOURCE_FIDELITY_PASS"
            if all(item["matches"] for item in comparisons)
            else "SOURCE_FIDELITY_FAIL"
        ),
        "protected_regions": comparisons,
    }


def _path_value(row: dict[str, Any], path: str) -> Any:
    current: Any = row
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _is_match(value: Any, criterion: dict[str, Any]) -> bool:
    if "equals" in criterion:
        return value == criterion["equals"]
    return value not in (None, 0, False, "")


def _fixture_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key, {})
        for key in (
            "features",
            "state",
            "states",
            "signals",
            "rejections",
            "orders",
            "trades",
        )
        if isinstance(row.get(key), dict)
    }


def select_review_fixtures(
    rows: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    *,
    max_fixtures: int = 18,
) -> list[dict[str, Any]]:
    if max_fixtures < 1:
        raise PineReviewContractError("max_fixtures must be positive.")
    fixtures: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for criterion in criteria:
        name = str(criterion.get("name") or "").strip()
        field = str(criterion.get("field") or "").strip()
        if not name or not field:
            raise PineReviewContractError(
                "Each fixture criterion requires name and field."
            )
        matches = [
            index
            for index, row in enumerate(rows)
            if _is_match(_path_value(row, field), criterion)
        ]
        if not matches:
            continue
        sample_indexes = [matches[0]]
        if len(matches) > 2:
            sample_indexes.append(matches[len(matches) // 2])
        if len(matches) > 1:
            sample_indexes.append(matches[-1])
        for index in sample_indexes:
            timestamp = int(rows[index].get("time") or 0)
            identity = (name, timestamp)
            if identity in seen:
                continue
            seen.add(identity)
            fixtures.append(
                {
                    "criterion": name,
                    "field": field,
                    "value": _path_value(rows[index], field),
                    "time": timestamp,
                    "row_index": index,
                    "context_times": [
                        int(rows[item].get("time") or 0)
                        for item in range(
                            max(0, index - 2),
                            min(len(rows), index + 3),
                        )
                    ],
                    "snapshot": _fixture_snapshot(rows[index]),
                }
            )
            if len(fixtures) >= max_fixtures:
                return fixtures
    return fixtures


def build_review_package(
    *,
    baseline_revision_id: str,
    baseline_source: str,
    candidate_revision_id: str,
    candidate_source: str,
    fidelity_contract: dict[str, Any],
    trace_rows: list[dict[str, Any]] | None = None,
    max_fixtures: int = 18,
) -> dict[str, Any]:
    source_fidelity = compare_protected_regions(
        baseline_source,
        candidate_source,
        list(fidelity_contract.get("protected_regions") or []),
    )
    criteria = list(fidelity_contract.get("fixture_criteria") or [])
    fixtures = (
        select_review_fixtures(
            trace_rows,
            criteria,
            max_fixtures=max_fixtures,
        )
        if trace_rows is not None
        else []
    )
    statuses = [source_fidelity["status"]]
    statuses.append(
        "FIXTURE_MANIFEST_COMPLETE"
        if trace_rows is not None and fixtures
        else "FOCUSED_REVIEW_FIXTURES_REQUIRED"
    )
    if fidelity_contract.get("visual_requirements"):
        statuses.append("TRADINGVIEW_VISUAL_REVIEW_REQUIRED")
    if fidelity_contract.get("review_timeframes"):
        statuses.append("MULTI_TIMEFRAME_REVIEW_REQUIRED")
    return {
        "schema_version": "1.0",
        "baseline_revision_id": baseline_revision_id,
        "candidate_revision_id": candidate_revision_id,
        "baseline_source_sha256": _sha256_text(baseline_source),
        "candidate_source_sha256": _sha256_text(candidate_source),
        "status": statuses,
        "source_fidelity": source_fidelity,
        "repair_targets": list(fidelity_contract.get("repair_targets") or []),
        "prohibited_changes": list(
            fidelity_contract.get("prohibited_changes") or []
        ),
        "visual_requirements": list(
            fidelity_contract.get("visual_requirements") or []
        ),
        "review_timeframes": list(
            fidelity_contract.get("review_timeframes") or []
        ),
        "fixture_manifest": {
            "criteria": criteria,
            "fixtures": fixtures,
            "trace_rows_available": len(trace_rows or []),
        },
    }
