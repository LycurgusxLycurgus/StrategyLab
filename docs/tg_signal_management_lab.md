# Offline TgSignalSniper management lab

This subsystem evaluates provider targets, post-fill management policies, and
bounded joint target/management policies for real TgSignalSniper
executions. It is deliberately disconnected from AutoKraken, MetaTrader, Telegram,
and every live or demo account. A package must be generated and finalized outside
StrategyLab before import.

## Package contract

A package is a directory containing `manifest.json` and finalized source files.
StrategyLab rejects SQLite sources with `-wal` or `-shm` sidecars and opens accepted
files using SQLite read-only/query-only immutable mode. It never checkpoints or
migrates a source.

Minimal manifest:

```json
{
  "manifest_schema_version": 1,
  "snapshot_state": "FINALIZED",
  "broker_name": "Axi Demo Pro",
  "broker_profile": "AXI_DEMO_PRO",
  "cohort": {
    "cohort_id": "axi-demo-pro-20260810",
    "published_from_utc": "2026-08-10T05:00:00+00:00",
    "original_timezone": "America/Bogota",
    "assets": ["XAUUSD", "EURUSD", "BTCUSD", "NASDAQ", "US30"]
  },
  "versions": {
    "operational_migration": 20,
    "tick_archive_schema": 2
  },
  "files": {
    "operational_sqlite": "tg_signal.sqlite3",
    "tick_sqlite": "tg_ticks.sqlite3",
    "trades_csv": "tg_signal_trades.csv",
    "shadow_csv": "tg_signal_shadow.csv",
    "deals_csv": "broker_deals.csv",
    "policy_registry": "policies.json",
    "symbol_specs": "symbol_specs.json"
  }
}
```

`policy_registry` is keyed by the exact `management_policy_version`. Each policy
may carry the frozen configuration fingerprint and must declare only post-fill
management. `symbol_specs` is keyed by MT5 symbol and must be captured from the
broker snapshot; at minimum it supplies `contract_size`, `volume_min`, and
`volume_step`. FIXED_R research additionally requires broker-captured `digits`
and `trade_tick_size`; StrategyLab never infers them. Deals identify `execution_id` and expose profit, commission, swap,
and fee. Missing policy, broker economics, lot constraints, or costs makes the
evidence research-only/non-comparable.

The importer supports operational migrations 16–22 through an explicit allowlist.
Fields introduced by later migrations are not inferred for older packages; their
absence closes the promotion gate. Tick archives must use schema 2 and codec
`zlib-struct-qddI-v1`, with SHA-256 over every compressed chunk.

Operational migration 20 must contain these columns in `sentinel_executions`:
`execution_venue`, `provider_entry_price`, `provider_stop_loss`, `provider_tp1`,
`provider_tp2`, `provider_tp3`, `venue_price_delta`, `reference_quote_bid`,
`reference_quote_ask`, `destination_quote_bid`, `destination_quote_ask`,
`quote_skew_seconds`, `quote_acquisition_seconds`, `venue_order_id`, and
`venue_position_key`. `sentinel_execution_legs` must contain `venue_order_id`.
StrategyLab rejects a migration-20 database missing any of these columns and
rejects disagreement between the manifest and SQLite migration number.

These values are preserved under each operation's immutable
`venue_translation` metadata and exported in experiment JSON/CSV diagnostics.
When the migration-20 provider entry, stop, and targets are populated, they form
the frozen provider geometry. Historical migration 16–19 operations continue to
use their legacy frozen signal/execution fields without reinterpretation. In all
versions, `entry_actual` remains the economic replay entry; venue prices and
quotes never replace the broker fill.

## Commands

```powershell
# Create the package outside StrategyLab using the offline AutoKraken close workflow.
# StrategyLab begins at registration/import:
.venv\Scripts\python -m app.cli tg-import-snapshot --package D:\offline-snapshots\axi-demo-pro-close

.venv\Scripts\python -m app.cli tg-coverage --snapshot-id tgsnap_<checksum>

.venv\Scripts\python -m app.cli tg-run-baseline --snapshot-id tgsnap_<checksum> --asset XAUUSD

.venv\Scripts\python -m app.cli tg-optimize --snapshot-id tgsnap_<checksum> --asset XAUUSD --seed 0 --candidate-family all

.venv\Scripts\python -m app.cli tg-report --experiment-id tgexp_<checksum>
```

The same operations are available under `/api/tg-management`. The browser UI has
an “Offline Execution Research” panel for import, coverage, baseline, family
selection, asynchronous progress, comparison, and artifact downloads. There is intentionally no publish, sync,
MT5, Telegram, or AutoKraken action.

## Replay and evidence

`tg_signal_management_v2` freezes the real entry, direction, initial volume and
provider stop. `PROVIDER_ORIGINAL` freezes targets too. `FIXED_R` changes only
TP1/TP2/TP3 from `abs(provider_entry - initial_provider_sl)`, normalizes them with
the captured broker tick contract, and never moves the actual fill or SL. BUY exits use BID and SELL exits use ASK. Tick order is
`time_msc`, preserved decoded `source_ordinal`, ticket, then leg. Natural periods
without ticks are valid when the archive declares complete coverage and zero gaps.
Invalid checksums, broken coverage, an event outside coverage, or an
outcome-changing ordering ambiguity censor the execution. A target at or behind
the actual fill is `INVALID_TARGET_AT_FILL`. One-second marks can
guide research but never establish exact promotional evidence.

Baseline evidence retains manual/anomalous operations as explicit quality flags;
it never silently improves a metric by dropping them. Censored or cost-incomplete
operations remain listed and cannot enter a promotional comparable set.
For the unmodified parent policy, exact broker deals are the authoritative source
of realized baseline P&L, including entry/exit commission, swap, and fees. Tick
replay remains authoritative for counterfactual candidates and stress variants.
Its individual tolerance is `max(USD 0.01, 0.01 × initial_risk_amount)` and its
aggregate tolerance is `max(USD 1, 0.0025 × sum(abs(actual_net_pnl)))`.

Candidate replay may continue beyond the real broker close only when the archive
declares a complete post-close horizon. The terminal event is the first original
TP3, original SL, applicable daily/weekly forced close, or 48 accumulated market
hours. An incomplete/future horizon or a candidate still open at the completed
horizon is `CENSORED_TARGET_HORIZON`, with pending targets and execution IDs for
backfill; it is never marked to market as a completed advantage. Native TP
fills use their requested broker level rather than a later tick overshoot.

The versioned target grid contains the 106 strict combinations of TP1
`{0.5,.75,1,1.25,1.5,2}`, TP2 `{1,1.5,2,2.5,3,4}`, and TP3
`{1.5,2,3,4,5,6}` R. Management-only evaluates the bounded 13-policy mutation
set. Joint search takes the three best target geometries selected using WF only
and combines each with those 13 management policies, for at most 39 candidates.

Operations are sorted chronologically. The first 75% is development data with
expanding walk-forward windows; the final 25% is untouched holdout. Search,
ranking, family selection, bootstrap equivalence, and parameter changes cannot
read holdout. One global finalist is selected by WF and evaluates holdout exactly
once; stress then runs only baseline and that finalist. The paired chronological
95% block bootstrap is deterministic and only resolves equivalence in favor of
lower complexity. Its seed, resamples, and block length are persisted; it never
replaces mandatory gates. Fewer than 20
complete comparable operations yields `INSUFFICIENT_TRADES`; 20–39 yields
`RESEARCH_ONLY`. At 40 or more, a policy can become `PROMOTION_CANDIDATE` only if
it increases `gross_profit_net` and net P&L, decreases `gross_loss_net`, does not
lower PF or raise drawdown in both aggregated WF OOS and holdout, preserves the
exact operation set, and passes every declared stress. Any invalid target, new
censoring, or exclusion rejects promotion. This status is statistical advice only.

When a snapshot contains several immutable statistical/configuration versions,
every closed cohort trade from the declared publication boundary is evaluated.
Immutable version sets remain visible as diagnostic strata and never become
`VERSION_SET_MISMATCH` exclusions. Actual broker performance uses every trade;
exact BID/ASK paths are promotion-grade, while imported one-second position-price
paths remain explicitly approximate research evidence
exclusions instead of being mixed or rewritten. A missing exact policy registry
entry fails baseline parity for that selected set.

## Artifacts and backfill diagnosis

Canonical content-addressed snapshots live under `artifacts/tg_snapshots/`.
Experiment JSON, CSV, and Markdown reports live under
`artifacts/tg_experiments/`. Coverage output lists the exact execution IDs whose
archive is missing, incomplete, gapped, or does not span the required interval.

The locally observed 22-row statistics CSV is fixture/reference material only. It
is not the final VPS cohort. Promotion evaluation requires the finalized post-close
operational database, exact tick archive, shadow/statistics exports, and available
broker costs/deals.
