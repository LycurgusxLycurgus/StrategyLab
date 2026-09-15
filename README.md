# Mutation Lab

Mutation Lab is a whitebox-first strategy creation, porting, qualification, and mutation workbench. TradingView is the canonical proving ground for chart-based strategies. Its embedded Pine2Python service automates Pine analysis, supported local execution, proof generation, and Pine/Python trace comparison without pretending to be TradingView.

## Lifecycle

1. Create an immutable greenfield, licensed source-adapted, or indicator-first revision in the pre-Phase 1 Pine Workbench.
2. Define the strategy, research Pine mechanisms and public precedents, and create the Phase 1 criteria/checklist.
3. Consolidate the Pine strategy and pass the one-screen TradingView Parity Proof Dashboard plus any claim-driven focused review.
4. Port the accepted Pine strategy to Mutation Lab Python and prove criterion-level trace parity.
5. Review fidelity quickly, run the faithful baseline, and perform authorized baseline optimization.
6. Diagnose and test evidence-derived whitebox mutations.
7. Add a bounded hybrid layer only when whitebox work is exhausted and live-engine reproduction succeeds.
8. Use constrained viability discovery or successor reseeding only when the completed lineage justifies it.
9. Complete robustness, execution-feasibility, forward-paper, and operational gates before production claims.

Greenfield Pine and licensed source adaptation are equal creation routes. The route is selected by evidence. Existing strategy families remain available until the user explicitly requests removal.

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

## Pine Workbench API

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
access are not required. The normal external action is one screenshot of the
on-chart proof table. Dataset fingerprints must match before execution or
performance parity can pass.

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

## Indicator-first strategy creation

For a strategy whose central indicator does not exist as reusable source, create
and validate it before adding any order logic:

1. When source already exists, register it unchanged as the fidelity baseline
   and declare protected regions, repair targets, prohibited changes, visual
   requirements, and review timeframes. Otherwise freeze the indicator's
   mathematical, state, timeframe, confirmation, warmup, missing-data, reset,
   and no-repaint contracts.
2. Create an immutable `indicator_first` Pine revision that declares
   `indicator()`. Instrument every output and state transition needed later by
   the strategy.
3. Run analysis and supported PineTS evidence. Resolve blockers one semantic
   change per child revision. Unsupported MTF or drawing behavior is preserved
   and routed to focused TradingView review.
4. Prepare a review package that proves protected-source fidelity and selects
   representative event fixtures before spending time on a full proof.
5. Corroborate the exact indicator revision in TradingView on every declared
   review timeframe, then run the final proof dashboard. Freeze its hash only
   after the user accepts the source, visual/state, fixture, and dashboard
   evidence.
6. Create a child strategy revision that initially copies the accepted indicator
   calculations unchanged, then adds explicit entries, exits, sizing, and
   execution semantics. Prove this Pine strategy separately in TradingView.
7. Port only the accepted strategy to Python, compare declared feature, signal,
   state, order, and trade traces, and fix the first divergence until parity
   passes.
8. Freeze the unoptimized Python parent. Asset-specific diagnostics,
   optimization, and mutation begin only in Phases 3–4.

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
.venv\Scripts\python agentic\testscripts\pine2python_vertical.py
```

## Artifacts

- Strategy-development contracts: `artifacts/strategy-development/<strategy_id>/`
- Data: `artifacts/data/`
- Runs: `artifacts/runs/`
- Reports: `artifacts/reports/`
- Diagnostics and preview ledgers: `artifacts/diagnostics/`
- Original source and accepted Pine: `pre-strategies/`
- `artifacts/tg_snapshots/` (immutable imported execution/tick packages)
- `artifacts/tg_experiments/` (JSON, CSV, and Markdown management evidence)
