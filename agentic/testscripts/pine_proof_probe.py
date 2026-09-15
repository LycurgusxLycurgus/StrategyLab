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


def build_probe_request(
    request: dict[str, Any], *, timestamp: int, probes: list[str]
) -> tuple[dict[str, Any], dict[str, str]]:
    streams = list(request.get("stream_expressions", {}))
    if not 1 <= len(probes) <= len(streams):
        raise ValueError(f"Provide between 1 and {len(streams)} probes")

    mapping: dict[str, str] = {}
    for index, stream in enumerate(streams):
        if index >= len(probes):
            request["stream_expressions"].pop(stream)
            continue
        if "=" not in probes[index]:
            raise ValueError("Probe format is NAME=PINE_BOOLEAN_EXPRESSION")
        name, expression = probes[index].split("=", 1)
        field_name = f"probe_{index + 1}"
        request["stream_expressions"][stream] = [
            {
                "name": f"{stream}.{field_name}",
                "expression": f"time == {timestamp} and ({expression})",
                "kind": "bool",
                "scale": 1_000_000,
            }
        ]
        mapping[stream] = name

    for row in request["trace_rows"]:
        for index, stream in enumerate(streams[: len(probes)]):
            row[stream] = {f"probe_{index + 1}": False}
    return request, mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fingerprint up to four Pine boolean expressions at one bar."
    )
    parser.add_argument("request", type=Path, help="Existing proof request.json")
    parser.add_argument("--time", type=int, required=True)
    parser.add_argument(
        "--probe",
        action="append",
        required=True,
        help="NAME=PINE_BOOLEAN_EXPRESSION; repeat up to four times",
    )
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
    request_data, mapping = build_probe_request(
        request_data,
        timestamp=args.time,
        probes=args.probe,
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
                "time": args.time,
                "probes": mapping,
                "false_baselines": proof["dashboard_values"],
                "artifact": proof["artifact"],
                "identity": proof["identity"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
