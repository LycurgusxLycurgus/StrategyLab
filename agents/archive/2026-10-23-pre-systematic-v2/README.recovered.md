# StrategyLab — Python2Pine

StrategyLab's new default is Python2Pine: create or translate an executable Python reference first, check its meaning and data, freeze a baseline, and research changes under explicit authorization. Pine and TradingView are a late selected-target corroboration step, not a prerequisite for creating a strategy. Existing Pine-first lineages remain available as `legacy_pine_v1`; they are not silently migrated. The migration rationale is in [`agentic/reference-first-migration-plan.md`](agentic/reference-first-migration-plan.md), and the phase contract is [`agents/translation and generation/agents/codex_phase_operator.md`](agents/translation%20and%20generation/agents/codex_phase_operator.md).

## Lifecycle

1. Start a new `reference_v1` lineage from an idea, prior evidence, or an immutable open-source strategy/indicator; record `strategy_origin`, `development_operation`, provenance, ambiguities, and transformations.
2. Specify the rules, states, causal timing, execution/data contracts, independent expected cases, and strategy-specific acceptance criteria. For a novel indicator, validate an indicator-only component first; add order logic in a child.
3. Validate full expected decisions against saved cases; check causality, prefix stability, raw/normalized data integrity, and execution limitations. Save the decision ledger and ledger-derived casebook.
4. Run and preserve the fixed unoptimized baseline. Authorize any search with an objective, finite parameter domains, and a chronological train/holdout split; select on training only.
5. Diagnose and test evidence-derived reference mutations. Each changed child preserves its parent, re-earns affected evidence, and remains within authorization. Unsupported hybrid adapters stay blocked.
6. Implement the selected target late. For Pine, use the compatible Pine2Python service for analysis/feature-signal checks, then make one focused TradingView review on the exact symbol/timeframe and predeclared behaviors.
7. Complete strategy-specific robustness, venue feasibility, forward reconciliation, and operational gates before production claims.

Source fidelity, semantic correctness, data integrity, execution fidelity, economics, target parity, TradingView acceptance, and operational readiness are separate verdicts. TradingView Basic chart-data CSV export is unavailable and is not required; if its feed cannot be shown identical to Python's data, report only the corroboration actually observed rather than claiming full performance parity. Existing strategy families and their legacy evidence remain available until the user explicitly requests removal.

The reference execution contract resolves each explicit parameter over its disclosed default: quantity 1, stop multiplier 2, ATR length 7, initial capital 100000, tick size 0.01, commission 0%, slippage 0 ticks, target R 0 (disabled), and maximum gap 0 bars. Saved specs record this resolution contract and defaults; override values remain part of the strategy parameters.

## Phase Prompts

- `agents/translation and generation/whitebox/01_translation.md`
- `agents/translation and generation/whitebox/01-5_baseline_transformation.md`
- `agents/translation and generation/whitebox/02_baseline.md`
- `agents/translation and generation/whitebox/02-5_baseline_qualification.md`
- `agents/translation and generation/whitebox/03-1_whitebox_diagnostics.md`
- `agents/translation and generation/whitebox/03_full-whitebox.md`
- `agents/translation and generation/whitebox/04-1_hybrid_diagnostics.md`
- `agents/translation and generation/whitebox/04_hybrid-blackbox.md`
- `agents/translation and generation/whitebox/04-2_blackbox_viability.md`
- `agents/translation and generation/whitebox/04-3_successor_baseline.md`
- `agents/docs/universal_mutation_constitution.md`

The operator contract is `agents/translation and generation/agents/codex_phase_operator.md`.

The recoverable project context and current unresolved proof obligations are
maintained in `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Read it with the operator
guide when resuming work after a lost conversation; it distinguishes local
evidence, TradingView/user acceptance, cross-strategy transfer, and economic
qualification.

## Run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
npm ci --prefix services\pine2python
.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Python2Pine API and workflow status

New reference work uses these additive API boundaries. The registry is bounded
to the supported MA crossover/ATR and confirmed-pivot/BOS references; unsupported
decision or broker semantics must remain blocked rather than being approximated
silently.

| Endpoint | Purpose |
|---|---|
| `GET /api/python2pine/status` | Public-name alias for workflow/runtime readiness; old Pine2Python route remains valid |
| `GET /api/versions/{id}/workflow?dataset_id=...` | Independent current semantic, data, execution, economics, target, platform, and operational states |
| `POST /api/versions/{id}/reference-validation` | Validate independently authored serialized cases and save ledger/casebook evidence |
| `GET /api/versions/{id}/reference-casebook?dataset_id=...` | Read current hash-verified HTML generated only from the saved ledger |
| `POST /api/versions/{id}/search-authorization` | Freeze objective, allowed parameter values, metric, and chronological training/holdout boundaries after baseline |
| `POST /api/versions/{id}/reference-children` | Create an explicit provenance-preserving reference child that must earn its own evidence |
| `POST /api/versions/{id}/pine-target` | Late Pine target generation and feature/signal comparison; never a fabricated TradingView or broker verdict |

Each new version selects `reference_v1` by default. Select `legacy_pine_v1`
explicitly to continue the older Pine-first contract. Existing stored lineages
without the field keep their existing route.

## Legacy and selected-target Pine APIs

| Endpoint | Purpose |
|---|---|
| `GET /api/pine2python/status` | Integration readiness and capabilities |
| `POST /api/pine-workbench/revisions` | Create an immutable Pine revision |
| `POST /api/pine-workbench/generate/{adapter_id}` | Generate a registered starter revision |
| `GET /api/datasets/{id}/pine-proof-window` | Select and hash a Basic-compatible 5,000-bar window |
| `POST /api/pine-workbench/revisions/{id}/proofs` | Create expected proof and paste-ready Pine |
| `POST /api/pine-workbench/revisions/{id}/review-package` | Compare protected baseline regions and select focused review fixtures |
| `POST /api/pine-workbench/revisions/{id}/tradingview-observations` | Record dashboard values, screenshot hash, and verdict |
| `POST /api/versions/{id}/python-trace` | Emit a standard StrategyLab Python trace |
| `POST /api/pine2python/parity-comparisons` | Compare traces and report the first divergence |

TradingView chart-data export, Premium, alerts, webhooks, and automated account
access are not required. For a selected Pine target, the normal human check is a
focused chart/replay review against predeclared ledger events, with a screenshot
of the observed behavior and Strategy Tester only for the separately declared
execution claim. Dataset fingerprints must match before full execution or
performance parity can be claimed. A screenshot or similar summary totals on a
different/unverified feed support only the narrower visual behavior observed.

The two-container topology is:

```powershell
docker compose up --build --wait
```

Docker Desktop on AMD systems requires SVM/virtualization enabled in BIOS/UEFI and
the Windows Virtual Machine Platform/WSL 2 prerequisites. Direct virtualenv use
continues to work without Docker.

Open `http://127.0.0.1:8000`. StrategyLab is the only host-published service;
Pine2Python remains reachable only through the private Compose network. Stop the
stack without deleting its evidence volumes with:

```powershell
docker compose down
```

## Indicator-first reference creation

When a required indicator is novel, establish the component before adding order
logic:

1. Freeze its equations, inputs, outputs, state, timing/confirmation, warmup,
   missing-data behavior, invalidation/reset, and no-future-information rules.
   Preserve an open-source source and provenance unchanged where one exists.
2. Implement it as a Python `reference_v1` indicator component with independently
   authored accepted/rejected/boundary cases. An accepted indicator has decisions
   and features but zero order intents/trades.
3. Validate the exact decision stream, ledger causality, prefix behavior, and
   data/execution scope; save its evidence and casebook.
4. Create a child strategy that preserves the accepted indicator parameters and
   records the new order-rule transformation. Validate the child independently;
   no semantic or economic evidence transfers automatically.
5. Freeze the fixed baseline before authorized asset-specific search. Pine and
   TradingView remain optional until selected as the late target.

If a user selects Pine, use the Pine Workbench APIs below and keep that evidence
separate from the accepted reference. A Pine indicator or strategy screenshot
does not replace reference expectations or raw-data identity.

When a user-authenticated TradingView tab is available, Codex can perform the
paste/add/wait/capture steps interactively. The generated dashboard remains the
comparison contract, and the user still owns the final accept/reject verdict.
See `services/pine2python/docs/tradingview-browser-corroboration.md`.

## Offline Telegram management lab

The UI also includes an offline TgSignalSniper target-geometry and post-fill
management lab. Its snapshot contract and commands are documented in
[`docs/tg_signal_management_lab.md`](docs/tg_signal_management_lab.md). It has
no MT5, Telegram, AutoKraken, demo, or live connector. Finalized AutoKraken
operational migrations 16–22 are imported through an explicit versioned,
capability-compatible contract.

## Test

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
.venv\Scripts\python -m unittest app.reference_tests
.venv\Scripts\python agentic\testscripts\pine2python_vertical.py
.venv\Scripts\python agentic\testscripts\reference_vertical.py --pine-target
```

The reference vertical writes an isolated, ignored run under
`artifacts/strategy-development/reference-demo/`. Its Pine target check reports
local feature/signal comparison separately from broker semantics and the
still-required TradingView review; it cannot mark the target or production
accepted.

## Artifacts

- Strategy-development contracts: `artifacts/strategy-development/<strategy_id>/`
- Data: `artifacts/data/`
- Runs: `artifacts/runs/`
- Reports: `artifacts/reports/`
- Diagnostics and preview ledgers: `artifacts/diagnostics/`
- Original source and accepted Pine: `pre-strategies/`
- `artifacts/tg_snapshots/` (immutable imported execution/tick packages)
- `artifacts/tg_experiments/` (JSON, CSV, and Markdown management evidence)
