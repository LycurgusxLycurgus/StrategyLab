from __future__ import annotations

import argparse
import json

from app.config import settings
from app.data import DataService
from app.lab import MutationLabService
from app.storage import Repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mutation Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="Download Binance candles")
    download.add_argument("--symbol", default="BTCUSDT")
    download.add_argument("--timeframe", default="15m")
    download.add_argument("--bars", type=int, default=40000)
    download.add_argument("--full-history", action="store_true")
    download.add_argument("--name")

    run_version = sub.add_parser("run-version", help="Run one strategy version")
    run_version.add_argument("--version-id", required=True)
    run_version.add_argument("--dataset-id", required=True)

    gen = sub.add_parser("generate-proposals", help="Generate single-mutation proposals")
    gen.add_argument("--version-id", required=True)
    gen.add_argument("--include-hybrid", action="store_true")

    run_pack = sub.add_parser("run-pack", help="Run all proposed mutations for a version")
    run_pack.add_argument("--version-id", required=True)
    run_pack.add_argument("--dataset-id", required=True)
    run_pack.add_argument("--include-hybrid", action="store_true")

    detail = sub.add_parser("family-detail", help="Print one family bundle")
    detail.add_argument("--family-id", required=True)
    return parser


def main() -> None:
    settings.ensure_dirs()
    repo = Repository()
    data_service = DataService(repo)
    lab = MutationLabService(repo, data_service)
    lab.ensure_seeded()
    args = build_parser().parse_args()

    if args.command == "download":
        payload = data_service.download_binance_dataset(
            symbol=args.symbol,
            timeframe=args.timeframe,
            bars=args.bars,
            full_history=args.full_history,
            name=args.name,
        )
    elif args.command == "run-version":
        payload = lab.run_version(args.version_id, args.dataset_id)
    elif args.command == "generate-proposals":
        payload = lab.generate_proposals(args.version_id, include_hybrid=args.include_hybrid)
    elif args.command == "run-pack":
        payload = lab.run_proposal_pack(args.version_id, args.dataset_id, include_hybrid=args.include_hybrid)
    else:
        payload = lab.family_detail(args.family_id)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
