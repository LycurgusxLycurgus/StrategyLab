from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .errors import Pine2PythonError
from .models import (
    AnalyzeRequest,
    GenerateRequest,
    ParityRequest,
    ProofRequest,
    RuntimeRequest,
    TradingViewObservationRequest,
)
from .service import Pine2PythonService


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pine2python")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Analyze a Pine source file.")
    analyze.add_argument("source")
    for command in ("proof", "observe", "runtime", "parity"):
        item = sub.add_parser(command, help=f"Run {command} from a JSON request.")
        item.add_argument("request")
    generate = sub.add_parser("generate", help="Run a registered Pine adapter.")
    generate.add_argument("adapter_id")
    generate.add_argument("request")
    sub.add_parser("capabilities", help="Print service capabilities.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = Pine2PythonService()
    try:
        if args.command == "analyze":
            source_path = Path(args.source)
            result = service.analyze(
                AnalyzeRequest(
                    source=source_path.read_text(encoding="utf-8"),
                    name=source_path.name,
                )
            )
        elif args.command == "proof":
            result = service.proof(
                ProofRequest.model_validate(_read_json(args.request))
            )
        elif args.command == "observe":
            result = service.observe(
                TradingViewObservationRequest.model_validate(_read_json(args.request))
            )
        elif args.command == "runtime":
            result = service.runtime(
                RuntimeRequest.model_validate(_read_json(args.request))
            )
        elif args.command == "parity":
            result = service.parity(
                ParityRequest.model_validate(_read_json(args.request))
            )
        elif args.command == "generate":
            result = service.generate(
                args.adapter_id,
                GenerateRequest.model_validate(_read_json(args.request)),
            )
        else:
            result = service.capabilities()
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except Pine2PythonError as exc:
        json.dump(exc.envelope(), sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
