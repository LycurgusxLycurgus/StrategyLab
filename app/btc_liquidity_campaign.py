"""Run the preregistered fixed BTC approach comparison; never fetch final data."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from app.btc_liquidity import Execution, Parameters, Signal, detect, simulate
from app.btc_liquidity_data import load_candles, load_funding, resample_15m


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def timestamp(year: int) -> int:
    return int(datetime(year, 1, 1, tzinfo=UTC).timestamp() * 1000)


def combined(folds: list[dict]) -> dict:
    profit = sum(x["gross_profit"] for x in folds)
    loss = sum(x["gross_loss"] for x in folds)
    returns = [x["net_return_pct"] for x in folds]
    return {"sum_fold_return_pct": sum(returns),
            "mean_fold_return_pct": sum(returns) / len(returns),
            "worst_fold_return_pct": min(returns),
            "closed_trades": sum(x["closed_trades"] for x in folds),
            "profit_factor": profit / loss if loss else None,
            "max_fold_drawdown_pct": max(x["max_drawdown_pct"] for x in folds),
            "max_fold_adverse_drawdown_pct": max(x["adverse_drawdown_pct"] for x in folds),
            "fees": sum(x["fees"] for x in folds),
            "funding": sum(x["funding"] for x in folds)}


def qualifies(row: dict, protocol: dict) -> tuple[bool, list[str]]:
    s = protocol["screen"]
    failures = []
    recent = [row["base"][str(y)] for y in s["positive_years"]]
    for year, fold in zip(s["positive_years"], recent):
        if fold["net_return_pct"] <= 0:
            failures.append(f"{year}: nonpositive base return")
        if fold["closed_trades"] < s["minimum_each_recent_closed_trades"]:
            failures.append(f"{year}: insufficient closed trades")
    if sum(x["closed_trades"] for x in recent) < s["minimum_recent_total_closed_trades"]:
        failures.append("insufficient recent total closed trades")
    pf = row["combined"]["profit_factor"]
    if pf is None or pf < s["minimum_combined_profit_factor"]:
        failures.append("combined profit factor below screen or undefined")
    if row["combined"]["max_fold_drawdown_pct"] > s["maximum_fold_close_drawdown_pct"]:
        failures.append("annual close drawdown above ceiling")
    if sum(row["stress"][str(y)]["net_return_pct"] for y in s["positive_years"]) <= 0:
        failures.append("recent stress return nonpositive")
    return not failures, failures


def rank_key(row: dict) -> tuple:
    return (row["qualified"], row["combined"]["worst_fold_return_pct"],
            row["combined"]["mean_fold_return_pct"])


def comparison(root: Path, run_id: str) -> Path:
    protocol_path = root / "protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    p = Parameters(**protocol["parameters"])
    e = Execution(**protocol["execution"])
    output = root / "runs" / run_id
    output.mkdir(parents=True, exist_ok=False)
    identities = {str(path): sha(path) for path in
                  (protocol_path, Path(__file__), Path("app/btc_liquidity.py"),
                   Path("app/btc_liquidity_data.py"), Path("app/btc_liquidity_tests.py"))}
    write_json(output / "identities_before_run.json", identities)
    bars5 = load_candles(root / "raw")
    bars15 = resample_15m(bars5)
    funding = load_funding(root / "raw")
    if bars5[0].t != timestamp(2022) or bars5[-1].t + 300000 != int(
            datetime(2026, 9, 1, tzinfo=UTC).timestamp() * 1000):
        raise ValueError("Development dataset must match frozen protocol exactly")
    if any(f["ts"] >= bars5[-1].t + 300000 for f in funding):
        raise ValueError("Reserved funding leaked into development data")
    identities.update({str(path): sha(path) for path in sorted((root / "raw").glob("*.json"))})
    write_json(output / "identities.json", identities)
    ledger_path = output / "trials.jsonl"
    all_rows = []
    for minutes, bars in ((5, bars5), (15, bars15)):
        for approach in [*protocol["approaches"], protocol["control"]]:
            signals, events = detect(bars, minutes, approach, p)
            # Save the independent detector funnel, including all suppressed setups.
            funnel = dict(Counter(x["kind"] for x in events))
            with gzip.open(output / f"detector-{minutes}-{approach}.json.gz", "wt", encoding="utf-8", compresslevel=1) as f:
                json.dump({"signals": [asdict(s) for s in signals], "events": events}, f, allow_nan=False)
            for direction in protocol["directions"]:
                trial_id = f"{minutes}m-{approach}-{direction}"
                row = {"id": trial_id, "minutes": minutes, "approach": approach,
                       "direction": direction, "detector_funnel": funnel,
                       "base": {}, "stress": {}, "control": approach == protocol["control"]}
                for year in protocol["annual_folds"]:
                    start, end = timestamp(year), timestamp(year + 1)
                    indices = [i for i, b in enumerate(bars) if start <= b.t < end]
                    left, right = max(0, indices[0] - p.lookback_minutes // minutes), indices[-1] + 1
                    part = bars[left:right]
                    intents = [replace(s, index=s.index - left, sweep_index=s.sweep_index - left)
                               for s in signals if indices[0] <= s.index < right]
                    fs = [x for x in funding if part[0].t <= x["ts"] < part[-1].t + minutes * 60000]
                    for condition in ("base", "stress"):
                        ex = e if condition == "base" else replace(e, slip_bps=protocol["stress_slip_bps"])
                        result = simulate(part, intents, minutes, direction, fs, p, ex)
                        row[condition][str(year)] = result["metrics"]
                        saved = output / f"{trial_id}-{year}-{condition}.json.gz"
                        with gzip.open(saved, "wt", encoding="utf-8", compresslevel=1) as f:
                            json.dump(result, f, separators=(",", ":"), allow_nan=False)
                        entry = {"trial_id": trial_id, "year": year, "condition": condition,
                                 "artifact": saved.name, "sha256": sha(saved),
                                 "metrics": result["metrics"], "parameters": asdict(p),
                                 "execution": asdict(ex)}
                        with ledger_path.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(entry, allow_nan=False) + "\n")
                        print(f"{trial_id} {year} {condition}: {result['metrics']['net_return_pct']:.3f}% "
                              f"{result['metrics']['closed_trades']} trades", flush=True)
                        if condition == "base":
                            # Raw original candle context for the first two realized trades.
                            with (output / "visual_ledger.csv").open("a", newline="", encoding="utf-8") as f:
                                w = csv.writer(f)
                                for trade in result["trades"][:2]:
                                    for index in range(max(0, trade["signal_index"] - 2),
                                                       min(len(part), trade["exit_index"] + 2)):
                                        b = part[index]
                                        w.writerow([trial_id, year, trade["entry_at"], index,
                                                    b.t, b.open, b.high, b.low, b.close,
                                                    trade["stop"], trade["target"], trade["reason"]])
                row["combined"] = combined(list(row["base"].values()))
                row["qualified"], row["screen_failures"] = qualifies(row, protocol)
                all_rows.append(row)
                write_json(output / "comparison.partial.json", all_rows)
    if any(sha(Path(path)) != value for path, value in identities.items()):
        raise ValueError("Code, protocol, or data identity changed during comparison")
    candidates = sorted([r for r in all_rows if not r["control"]], key=rank_key, reverse=True)
    controls = sorted([r for r in all_rows if r["control"]], key=rank_key, reverse=True)
    qualified = [r for r in candidates if r["qualified"]]
    summary = {"campaign_id": protocol["campaign_id"], "run_id": run_id,
               "created_at": datetime.now(UTC).isoformat(),
               "status": "PHASE_3_CANDIDATE_REQUIRES_ACCEPTANCE" if qualified else "RETURN_TO_PHASE_1",
               "reserved_status": "UNFETCHED_UNEVALUATED",
               "selected": qualified[0]["id"] if qualified else None,
               "best_observed": candidates[0]["id"], "candidates": candidates, "controls": controls,
               "completed_annual_runs": len(all_rows) * 5 * 2,
               "benchmark": "Cash: zero return, zero drawdown. Breakout controls use identical sizing and execution.",
               "identities": identities, "limitations": protocol["limitations"]}
    write_json(output / "comparison.json", summary)
    (output / "comparison.partial.json").unlink()
    write_report(output, summary, protocol)
    return output


def write_report(output: Path, summary: dict, protocol: dict) -> None:
    lines = ["# BTC liquidity-excursion campaign", "", f"Status: **{summary['status']}**.", "",
             f"Best observed fixed candidate: **{summary['best_observed']}**. "
             f"Qualified selection: **{summary['selected'] or 'none'}**.", "",
             "These are development comparisons, not final out-of-sample performance. "
             "The final September–October 2026 window remains unfetched and unevaluated. "
             "Annual folds reset capital; summed returns are not a continuous compounded portfolio return.", "",
             "## Fixed rules", "",
             "Use the prior completed six-hour high/low and two-hour mean true range. "
             "A long sweep trades at least 0.1 ATR below the prior low and closes above it; shorts mirror this. "
             "Reclaim enters next open. Confirm waits at most 45 minutes for a close beyond the sweep candle's "
             "opposite extreme with a directional body of at least 0.5 ATR. Confirm+FVG additionally requires "
             "a strict directional three-candle gap on that confirmation bar. A new extreme invalidates pending "
             "confirmation. A new single-sided sweep replaces a remaining pending sweep. Dual sweeps are excluded. "
             "Stops sit 0.1 ATR beyond the sweep; targets are 2R; time exit follows six hours. "
             "The breakout control removes the sweep requirement and enters a close beyond the prior range.", "",
             "One position, no pyramiding/reversals, 0.25% nominal equity risk including modeled stop costs, "
             "maximum 1× entry exposure. Fees are assumed at 6 bps per fill, adverse slippage at 2 bps "
             "(4 bps stress), plus historical signed funding. Missing historical API funding marks use official "
             "5m mark-price opening quotes with a fixed 1% adverse funding-payment buffer. Exact settlement "
             "marks remain unverified. This fee is a research assumption, not a verified account quote.", "",
             "## All 18 candidates", "",
             "| Candidate | 2022 % | 2023 % | 2024 % | 2025 % | Jan–Aug 2026 % | PF | Trades | Max fold DD % | Qualified |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in summary["candidates"]:
        m = row["combined"]
        pf = f"{m['profit_factor']:.3f}" if m["profit_factor"] is not None else "undefined"
        returns = " | ".join(f"{row['base'][str(y)]['net_return_pct']:.2f}" for y in protocol["annual_folds"])
        lines.append(f"| {row['id']} | {returns} | {pf} | {m['closed_trades']} | "
                     f"{m['max_fold_drawdown_pct']:.2f} | {'yes' if row['qualified'] else 'no'} |")
    lines += ["", "## Direction and timeframe", "",
              "Each cell below is the best observed approach for that context under the frozen worst-fold/mean-fold ranking. "
              "Selecting the best of three remains selection exposure; it does not establish an edge.", "",
              "| Context | Best observed approach | Worst fold return % | Mean fold return % | Qualified |",
              "|---|---|---:|---:|---|"]
    for minutes in protocol["timeframes_minutes"]:
        for direction in protocol["directions"]:
            row = max((x for x in summary["candidates"] if x["minutes"] == minutes and
                       x["direction"] == direction), key=rank_key)
            m = row["combined"]
            lines.append(f"| {minutes}m {direction} | {row['approach']} | "
                         f"{m['worst_fold_return_pct']:.2f} | {m['mean_fold_return_pct']:.2f} | {row['qualified']} |")
    lines += ["", "## Screening failures", ""]
    for row in summary["candidates"]:
        lines.append(f"- {row['id']}: {'; '.join(row['screen_failures']) or 'passed research screen'}.")
    lines += ["", "## Controls", ""]
    for row in summary["controls"]:
        m = row["combined"]
        lines.append(f"- {row['id']}: worst fold {m['worst_fold_return_pct']:.2f}%; "
                     f"mean fold {m['mean_fold_return_pct']:.2f}%; {m['closed_trades']} closed trades.")
    lines += ["", "## Phase gate and evidence", "",
              "Phase 1 formalized a liquidity-excursion hypothesis; Phase 2 compared its three fixed approaches. "
              "A failed research screen returns to Phase 1. No Phase 4 search, Phase 5 mutation/final test, "
              "or Phase 6 paper graduation is implied. A qualifying prototype still requires Phase 3 acceptance "
              "and existing runtime authorization before optimization; this research engine is not registered with Mutation Lab.", "",
              "`comparison.json` contains every fold, stress result, failure reason, detector funnel and code/data identities. "
              "`trials.jsonl` records all 240 annual economic evaluations. Each compressed result retains all trades, "
              "order/funding/censor events and bar-close marked equity. `visual_ledger.csv` joins original OHLC "
              "with the first two trades of each base fold; columns: trial, year, entry timestamp, local index, "
              "bar timestamp, O, H, L, C, stop, target, exit reason. Detector files preserve independent setup accounting.", "",
              "Screen: both recent folds positive; at least 30 closed trades each and 100 combined; overall PF ≥1.05; "
              "no annual close drawdown above 10%; summed recent stress return positive. These are preliminary "
              "research rejection criteria, not a significance test. Serial dependence, 18-candidate selection, "
              "historical filter uncertainty and OHLC execution approximations remain relevant.", "", "## Limitations", ""]
    lines.extend(f"- {x}" for x in protocol["limitations"])
    lines += ["", "## Sources", "",
              "- [Binance public data and checksums](https://github.com/binance/binance-public-data).",
              "- [Binance funding history schema](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).",
              "- [Binance instrument filter schema](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information).",
              "- [Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). "
              "This supports trial accounting and caution, not profitability of this strategy.", ""]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/strategy-development/btc-liquidity-20261023"))
    parser.add_argument("--run-id", required=True, help="New evidence directory; existing runs are never overwritten")
    args = parser.parse_args()
    if not args.run_id or Path(args.run_id).name != args.run_id or args.run_id in (".", ".."):
        parser.error("run-id must be a single directory name")
    print(comparison(args.root, args.run_id))


if __name__ == "__main__":
    main()
