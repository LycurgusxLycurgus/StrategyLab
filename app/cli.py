from __future__ import annotations

import argparse
import json

from app.config import settings
from app.data import DataService
from app.lab import MutationLabService
from app.storage import Repository
from app.tg_lab import TgManagementLabService


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

    tg_import = sub.add_parser("tg-import-snapshot", help="Import a finalized offline TgSignalSniper package")
    tg_import.add_argument("--package", required=True)

    tg_coverage = sub.add_parser("tg-coverage", help="Report exact tick coverage by asset")
    tg_coverage.add_argument("--snapshot-id", required=True)

    tg_baseline = sub.add_parser("tg-run-baseline", help="Replay the frozen management baseline")
    tg_baseline.add_argument("--snapshot-id", required=True)
    tg_baseline.add_argument("--asset", required=True)

    tg_optimize = sub.add_parser("tg-optimize", help="Optimize post-fill management for one asset")
    tg_optimize.add_argument("--snapshot-id", required=True)
    tg_optimize.add_argument("--asset", required=True)
    tg_optimize.add_argument("--seed", type=int, default=0)
    tg_optimize.add_argument("--candidate-family", choices=("all", "management", "targets", "joint"), default="all")

    tg_report = sub.add_parser("tg-report", help="Print the persisted experiment and report path")
    tg_report.add_argument("--experiment-id", required=True)
    return parser


def main() -> None:
    settings.ensure_dirs()
    repo = Repository()
    data_service = DataService(repo)
    lab = MutationLabService(repo, data_service)
    tg_lab = TgManagementLabService(repo)
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
    elif args.command == "family-detail":
        payload = lab.family_detail(args.family_id)
    elif args.command == "tg-import-snapshot":
        payload = tg_lab.import_snapshot(args.package)
    elif args.command == "tg-coverage":
        payload = tg_lab.coverage(args.snapshot_id)
    elif args.command == "tg-run-baseline":
        payload = tg_lab.run_baseline(args.snapshot_id, args.asset)
    elif args.command == "tg-optimize":
        payload = tg_lab.optimize_asset(args.snapshot_id, args.asset, args.seed, args.candidate_family)
    else:
        payload = tg_lab.experiment(args.experiment_id)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
