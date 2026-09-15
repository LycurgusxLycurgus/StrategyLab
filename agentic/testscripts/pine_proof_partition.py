from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PINE2PYTHON_SRC = ROOT / "services" / "pine2python" / "src"
if str(PINE2PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PINE2PYTHON_SRC))

from pine2python.config import Settings
from pine2python.models import ProofRequest
from pine2python.service import Pine2PythonService


def _nested_value(row: dict[str, Any], path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"Trace row is missing {path!r} at {part!r}")
        value = value[part]
    return value


def build_partition_request(
    request: dict[str, Any],
    *,
    trace_field: str,
    pine_expression: str,
    partitions: int,
    row_start: int = 0,
    row_end: int | None = None,
) -> tuple[dict[str, Any], list[int], tuple[int, int]]:
    rows = request.get("trace_rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("The proof request must contain non-empty trace_rows")

    stream_names = list(request.get("stream_expressions", {}))
    if partitions < 2:
        raise ValueError("partitions must be at least 2")
    if partitions > len(stream_names):
        raise ValueError(
            f"partitions={partitions} exceeds available streams={len(stream_names)}"
        )

    row_end = len(rows) if row_end is None else row_end
    if not 0 <= row_start < row_end <= len(rows):
        raise ValueError(
            f"Invalid row slice [{row_start}:{row_end}] for {len(rows)} rows"
        )
    if row_end - row_start < partitions:
        raise ValueError("The selected row slice is smaller than the partition count")

    times = [int(row["time"]) for row in rows]
    selected_count = row_end - row_start
    boundaries = [
        times[row_start + selected_count * index // partitions]
        for index in range(1, partitions)
    ]
    range_start = times[row_start]
    range_end = (
        times[row_end]
        if row_end < len(rows)
        else int(request.get("end_ms", times[-1] + 1))
    )
    trace_values = [_nested_value(row, trace_field) for row in rows]

    def condition(index: int) -> str:
        if index == 0:
            return f"time >= {range_start} and time < {boundaries[0]}"
        if index == partitions - 1:
            return f"time >= {boundaries[-1]} and time < {range_end}"
        return f"time >= {boundaries[index - 1]} and time < {boundaries[index]}"

    for index, stream_name in enumerate(stream_names):
        if index >= partitions:
            request["stream_expressions"].pop(stream_name)
            continue
        field_name = f"partition_{index + 1}"
        request["stream_expressions"][stream_name] = [
            {
                "name": f"{stream_name}.{field_name}",
                "expression": f"({condition(index)}) and ({pine_expression})",
                "kind": "bool",
                "scale": 1_000_000,
            }
        ]

    for row, trace_value in zip(rows, trace_values, strict=True):
        timestamp = int(row["time"])
        for index, stream_name in enumerate(stream_names[:partitions]):
            active = (
                range_start <= timestamp < boundaries[0]
                if index == 0
                else boundaries[-1] <= timestamp < range_end
                if index == partitions - 1
                else boundaries[index - 1] <= timestamp < boundaries[index]
            )
            row[stream_name] = {f"partition_{index + 1}": bool(trace_value) and active}

    return request, boundaries, (range_start, range_end)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split one boolean Pine/Python proof field across fingerprint streams."
    )
    parser.add_argument("request", type=Path, help="Existing proof request.json")
    parser.add_argument("--trace-field", required=True, help="Nested trace row field")
    parser.add_argument("--pine-expression", required=True)
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--row-start", type=int, default=0)
    parser.add_argument("--row-end", type=int)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / "artifacts" / "strategy-development" / "pine2python-artifacts",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=ROOT / "artifacts" / "strategy-development" / "pine2python-work",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request_data = json.loads(args.request.read_text(encoding="utf-8"))
    request_data, boundaries, selected_range = build_partition_request(
        request_data,
        trace_field=args.trace_field,
        pine_expression=args.pine_expression,
        partitions=args.partitions,
        row_start=args.row_start,
        row_end=args.row_end,
    )
    service = Pine2PythonService(
        Settings(
            artifact_root=args.artifact_root.resolve(),
            work_root=args.work_root.resolve(),
        )
    )
    proof = service.proof(ProofRequest.model_validate(request_data))
    print(
        json.dumps(
            {
                "boundaries": boundaries,
                "selected_range": selected_range,
                "dashboard_values": proof["dashboard_values"],
                "artifact": proof["artifact"],
                "identity": proof["identity"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
