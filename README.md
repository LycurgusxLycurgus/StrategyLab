# StrategyLab — Python2Pine

StrategyLab's new default is Python2Pine: create or translate an executable Python reference first, check its meaning and data, freeze a baseline, and research changes under explicit authorization. Pine and TradingView are a late selected-target corroboration step, not a prerequisite for creating a strategy. Existing Pine-first lineages remain available as `legacy_pine_v1`; they are not silently migrated. The migration rationale is in [`agentic/reference-first-migration-plan.md`](agentic/reference-first-migration-plan.md), and the phase contract is [`agents/translation and generation/agents/codex_phase_operator.md`](agents/translation%20and%20generation/agents/codex_phase_operator.md).

## Strategy Research Lifecycle

The active research sequence is systematic and Python-reference-first. Define
one research envelope—asset or asset universe, venue/data source, timeframe and
direction choices, hypothesis, and risk constraints—then move through these six phases:

1. **Research and candidate selection:** [01_research.md](agents/translation%20and%20generation/whitebox/01_research.md) first classifies the requested approach as systematic or discretionary. It researches original sources and complete mechanical formulations, including a two-step formalization/formulation investigation for discretionary requests, then prepares at least three fresh, complete evidence-supported hypotheses (target 3–4). Meaningful revisions require a new causal test; minor variants and controls do not pad the count. Fewer than three means incomplete research, not a ready batch.
2. **Controlled comparison:** [02_approach_trials.md](agents/translation%20and%20generation/whitebox/02_approach_trials.md) requires approval of the new batch/protocol, validates measurement meaning and predictive increment separately from full-strategy economics, then compares a preregistered bounded asset/timeframe/direction matrix under common costs, risk and chronology. Unspecified settings receive justified choices before testing. Advance only a candidate meeting every predeclared requirement; if none qualifies, return failure evidence and retained components to Phase 1, propose at least three fresh candidates with a justified new/meaningful-revision/mixed direction, and state that their testing needs new-batch approval. Relative rank alone never establishes qualification. “Ensemble” means candidate comparison, not variations of a preselected winner or automatic signal combination.
3. **Base strategy:** [03_base_strategy.md](agents/translation%20and%20generation/whitebox/03_base_strategy.md) consolidates the qualifying candidate's tested rules and contexts as a causal, independently testable Python reference and freezes its unoptimized baseline. A mechanical source analogue is not proof of faithful replication of discretionary reasoning.
4. **Optimization:** [04_optimization.md](agents/translation%20and%20generation/whitebox/04_optimization.md) searches all legitimate, explicitly declared tunable parameters within a bounded budget and chronological development/holdout controls.
5. **Unified mutation and optimization:** [05_mutation_optimization.md](agents/translation%20and%20generation/whitebox/05_mutation_optimization.md) tests admissible, evidence-derived structural changes and re-optimizes their legitimate parameters in one controlled loop. Preserve parent versions, account for all trials, and do not tune on a consumed final holdout.
6. **Paper trading:** [06_paper_trading.md](agents/translation%20and%20generation/whitebox/06_paper_trading.md) evaluates a frozen finalist against explicit paper-adapter, coverage, reconciliation, risk, and operational gates; the result is graduate or do not graduate, with reasons.

Phase 1 is research-only by default: a ready specification has no new tested trades, validated signal or economic acceptance. Phase 2 performs the actual initial testing/stress comparison that decides Phase 3 or another research return. Explicit approval of a bounded research-and-test batch permits both stages together with a visible transition; readiness or approval of an older failed batch does not.

The [phase operator](agents/translation%20and%20generation/agents/codex_phase_operator.md) defines the shared handoffs and evidence boundaries. Python is the canonical research reference. Pine is an optional selected target; when used, check target behavior and corroborate in TradingView before paper evaluation, without treating a chart comparison as data or execution parity unless the inputs and semantics support that claim. Documentation and phase completion do not themselves provide a paper-trading connector. Graduation is eligibility for a separate live-readiness review, never permission to place live orders.

This sequence is the documentation-level `systematic_v2` schedule only; it does not add or rename a runtime workflow enum. Discretionary-origin indicator-to-decision-model work and the ML/social/CLEF/white-box/black-box assessment remain [PLAN ONLY](agents/plans/discretionary_and_blackbox_roadmap.md); this roadmap does not enable a model, connector, or integration.

The former phase schedule and prompts are preserved for historical recovery in [`agents/archive/2026-10-23-pre-systematic-v2/`](agents/archive/2026-10-23-pre-systematic-v2/). This documentation change does not rename existing runtime APIs, persisted workflow IDs, or strategy lineages; existing `reference_v1` and `legacy_pine_v1` behavior remains governed by its implemented contracts.

The [research-quality audit](agentic/research/phase1-phase2-quality-audit-2026-10-29.md) explains the Bitcoin campaign failures and the distinction between unsupported proxies, scoped noise/no useful effect, inconclusive evidence, promising components and supported signals. A retained good component never promotes a failed full strategy.

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
.venv\Scripts\python -m unittest app.workflow_tests
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
