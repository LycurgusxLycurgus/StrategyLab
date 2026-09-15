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


def build_field_group_request(
    request: dict[str, Any], *, source_stream: str, groups: int
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    expressions = list(request.get("stream_expressions", {}).get(source_stream, []))
    if not expressions:
        raise ValueError(f"No expressions found for stream {source_stream!r}")

    target_streams = list(request["stream_expressions"])
    if groups < 2:
        raise ValueError("groups must be at least 2")
    if groups > len(target_streams):
        raise ValueError(f"groups={groups} exceeds available streams={len(target_streams)}")
    if groups > len(expressions):
        raise ValueError(f"groups={groups} exceeds fields={len(expressions)}")

    mapping: dict[str, list[str]] = {}
    field_count = len(expressions)
    for index, stream_name in enumerate(target_streams):
        if index >= groups:
            request["stream_expressions"].pop(stream_name)
            continue
        start = field_count * index // groups
        end = field_count * (index + 1) // groups
        group = expressions[start:end]
        request["stream_expressions"][stream_name] = group
        mapping[stream_name] = [str(item["name"]) for item in group]
    return request, mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split one proof stream's fields across fingerprint streams."
    )
    parser.add_argument("request", type=Path, help="Existing proof request.json")
    parser.add_argument("--source-stream", default="features")
    parser.add_argument("--groups", type=int, default=4)
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
    request_data, mapping = build_field_group_request(
        request_data,
        source_stream=args.source_stream,
        groups=args.groups,
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
                "field_groups": mapping,
                "dashboard_values": proof["dashboard_values"],
                "artifact": proof["artifact"],
                "identity": proof["identity"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
