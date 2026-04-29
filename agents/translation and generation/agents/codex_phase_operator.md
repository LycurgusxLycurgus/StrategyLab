# Codex Phase Operator Guide for Mutation Lab

This guide explains how a human operator and a Codex-like coding agent should run the four Mutation Lab phases in this repository. It is written to be usable by humans and LLM agents. The goal is repeatability: a new strategy idea should move through translation, baseline optimization, full-whitebox improvement, and hybrid/blackbox sharpening without inventing a new workflow each time.

The core rule is simple: each phase must produce evidence before the next phase begins. Do not promote a strategy because it sounds plausible. Promote only after the app or scripts test it against the frozen parent and the same dataset contract. The final research label before live use is not "production-ready"; it is "production robustness candidate." A strategy earns that label only after the saved final candidate passes full-history portfolio gates, chronological walk-forward checks, and execution-cost stress checks.

## Repository Map

The phase prompts live in `agents/translation and generation/whitebox/`.

Use these prompts in order:

| Phase | Prompt | Purpose |
|---:|---|---|
| 1 | `01_translation.md` | Turn a vague strategy request or source strategy into an executable parent candidate. |
| 2 | `02_baseline.md` | Optimize ordinary parameters on broad history until the candidate is either a serious baseline or a graveyard item. |
| 3 | `03_full-whitebox.md` | Convert a serious baseline into an explainable full-whitebox strategy by adding rule-level mutations. |
| 3.1 | `03-1_whitebox_diagnostics.md` | Produce diagnostics from a saved run report before coding full-whitebox mutations. |
| 4 | `04_hybrid-blackbox.md` | Add one narrow hybrid or blackbox mutation to a surviving full-whitebox parent. |
| 4.1 | `04-1_hybrid_diagnostics.md` | Produce the ranked hybrid mutation queue and validation contract before coding phase-4 experiments. |
| Final Gate | App robustness gate | Test the saved final candidate with walk-forward folds and cost/slippage stress before paper trading. |

Generated evidence belongs in `artifacts/`. Saved run JSON files live in `artifacts/runs/`, saved run Markdown reports live in `artifacts/reports/`, and phase diagnostics live in `artifacts/diagnostics/`. Do not put generated diagnostics into `bridgecode/`; that folder is only for execution playbooks such as `EYE.md`.

The default strategy seed is `strategies/btc_intraday_parent.json`. The app also persists versions in SQLite, so any phase upgrade that adds parameters or mutation edges must update both the seed JSON and existing `versions.spec_json` through the repository upgrade path.

## Operating Contract

Always start by reading `AGENTS.md` and the requested bridgecode playbook. For execution work in this repo, the user usually invokes `EYE.md`, so the coding agent must read `bridgecode/EYE.md` and `bridgecode/plan-code-debug.md` before editing.

Keep the implementation vanilla-first and local. The app is intentionally a small Python/FastAPI/vanilla-JS research tool. Do not add frameworks or dependencies to solve process problems that can be solved with explicit Python, JSON, Markdown, and the existing app endpoints.

A report is enough for phase routing when it contains the frozen contract, parent comparison, headline metrics, buy-and-hold comparison, side decomposition, exit-reason decomposition, period decomposition, duration statistics, MFE/MAE, and diagnostic counters. Open the JSON only when the next task requires trade-level rows, exact parameter payloads, exported features, or model labels that are not present in the Markdown.

## Phase 1: Translation

Phase 1 starts with a user idea, source code, open-source strategy, course notes, or a compact strategy description. The agent reads `01_translation.md` and translates the idea into one executable parent candidate. The parent must be explicit enough for Mutation Lab to run: asset, venue, timeframe, signal logic, entry rules, exit rules, risk rules, cost assumptions, parameter schema, and a mutation space for ordinary parameter tuning.

The output of this phase is not a promoted strategy. It is a runnable candidate. If source material is vague, the agent should make the smallest defensible translation and state assumptions in the strategy notes. If the source material is too vague to code honestly, the agent should ask for the specific missing trading rule rather than inventing one.

For this repo, phase-1 coding usually touches the strategy JSON, `app/backtest.py` if a new engine rule is needed, and tests in `app/tests.py`. If the candidate can be expressed with the existing engine, prefer only updating the JSON and mutation space.

The pass gate is that the app can run the candidate on a valid dataset without crashing, produces non-empty metrics, and exposes tunable edges in the Mutation Edges panel.

## Phase 2: Baseline Optimization

Phase 2 uses `02_baseline.md`. The purpose is not to make clever rule changes. It is to optimize ordinary parameters until the translated candidate proves whether it has enough baseline edge to deserve deeper research.

In the app, choose the family, choose the dataset, and run live tuning or automated lever optimization. Use broad history whenever possible. For BTCUSDT 15m, use the full Binance history dataset rather than a small 40k-bar sample once the candidate becomes serious.

The agent should treat `Optimize` and `Optimize All Twice` as parameter search tools, not as proof of generalization. If a strategy cannot become at least a survivor after two full optimization passes over the main parameter space, route it to graveyard and test another translation candidate. Do not proceed to phase 3 with a strategy that only has a small-sample artifact or a low-trade high-PF result.

The minimum evidence gate should include trade count, profit factor, max drawdown, net PnL, outperformance versus buy-and-hold, and chronological period decomposition. Raw profit factor is not enough. A high PF with too few trades or narrow-period concentration is not a serious baseline.

The output of phase 2 is a saved run report in `artifacts/reports/` and JSON in `artifacts/runs/`. The saved run becomes the frozen parent for phase 3.

## Phase 3: Full-Whitebox Diagnostics and Rule Mutations

Phase 3 starts by running `03-1_whitebox_diagnostics.md` against the saved phase-2 run report. The diagnostics memo should go to `artifacts/diagnostics/full-whitebox-diagnostics-<run_id>.md`. The diagnostics should identify localized weaknesses rather than proposing generic improvements.

A good phase-3 diagnostic asks: is the weakness side-specific, exit-specific, period-specific, duration-specific, timing-specific, or excursion-specific? It then proposes rule-level single mutations that preserve the parent contract. Examples are side-specific gates, time-decay exits, breakeven or trailing stop logic, timing filters, volatility-context gates, or separate long/short management. Do not jump to hybrid models in phase 3.

Test each mutation one at a time as an unsaved preview. If a mutation survives against the frozen parent, implement it as explicit strategy parameters and mutation-space edges. After all proposed mutations are tested, run app optimization again. Phase 3 is not complete when the parameters merely exist; it is complete only after the new rule parameters have been optimized and the saved child still survives or improves on broad history.

When phase-3 rule mutations are added, default behavior matters. A newly added rule can start enabled if it is intentionally becoming the next parent branch and the operator will optimize it immediately. If uncertainty remains, keep it disabled and expose it in Mutation Edges. In all cases, saved child versions and the seed JSON must both inherit the new parameters and mutation edges.

The output of phase 3 is a full-whitebox saved run. Its report must be rich enough that phase 4 can decide whether hybrid work is justified without opening JSON. If the report lacks frozen contract, parent comparison, side decomposition, exit decomposition, period decomposition, duration, MFE/MAE, and buy-and-hold comparison, improve report generation before continuing.

## Phase 4: Hybrid/Blackbox Diagnostics and Mutations

Phase 4 begins only after the full-whitebox parent is already strong. Use `04-1_hybrid_diagnostics.md` first, not `04_hybrid-blackbox.md` directly. The diagnostic must decide whether hybrid work is justified and produce a ranked queue of narrow candidates. The hybrid layer is not the strategy. The whitebox parent remains the strategy; the hybrid layer can only score, filter, rank, size, or triage one bounded decision point.

The phase-4 diagnostic must state a feature contract, label contract, model contract, validation contract, acceptance rule, rejection rule, and live-engine promotion contract. The most important practical rule is that there are two gates:

First, an offline preview can decide whether the idea deserves code. This preview may use exported trade rows, decision-time features, scorecards, labels, or counterfactual accounting.

Second, a live-engine test decides whether the idea deserves promotion. The offline survivor must be converted into explicit strategy parameters, exposed in Mutation Edges, optimized in the app, and compared against the frozen parent. If the live implementation does not reproduce the offline edge, keep it disabled or reject it.

For the BTCUSDT intraday parent, the phase-4 process produced this practical lesson: a time-decay triage preview can look good offline but the first live proxy can be too broad and destructive. The correct response is not to blindly promote the proxy. Keep the branch tunable, optimize its thresholds, and only save the child when the optimized live result improves the parent. The saved run `run_0c1bc044944d` is an example of a successful optimized phase-4 child: it improved PF, net PnL, drawdown, and buy-and-hold outperformance while preserving trade count.

The output of phase 4 is a saved hybrid/full strategy run. If it becomes the best current strategy, it can be promoted as the new parent for later research. Any rejected hybrid experiments should remain as disposable diagnostic artifacts only; do not add failed branches to the app unless they are useful disabled controls for future optimization.

## Final Research Gate: Robustness and Paper Trading

After phase 4 is complete, or after hybrid work is explicitly skipped because no narrow hybrid candidate is justified, the operator must freeze one exact saved version and dataset. Run the app's robustness gate on that exact candidate. The gate must pass chronological walk-forward folds and execution-cost stress scenarios. The current required stress scenarios are doubled commission, doubled slippage, and combined doubled commission plus doubled slippage.

If the robustness gate fails, do not paper trade. Use the failed fold or failed stress scenario as the next research target. A candidate that cannot survive cost stress or chronological splits is still a research artifact even if the full-history metrics look excellent.

If the robustness gate passes, label the strategy a production robustness candidate and create a candidate dossier. The dossier should reference the saved run report, saved run JSON, dataset id, parameter set, robustness output, capital model, benchmark comparison, known remaining risks, and paper-trading plan. This freeze step prevents accidental continued tuning after the strategy has already passed the research gate.

Paper trading should not be "a few days" by default. Choose the duration from historical trade frequency. For a strategy with hundreds of trades over many years but only around one or two trades per week on average, paper trading should usually run for several weeks to a few months, or until at least 20 to 30 live paper trades are observed, whichever takes longer. A few days is acceptable only for much higher-frequency systems that can generate a meaningful sample quickly. During paper trading, track live frequency, fills, slippage, stop behavior, exposure, drawdown rhythm, execution errors, and whether the observed trades resemble the backtest diagnostics.

Paper trading can end in three ways. If behavior is aligned and the sample is meaningful, move to operational integration or tiny-capital/live-sandbox planning. If behavior is aligned but the sample is too small, continue paper trading. If behavior breaks the thesis, route back to diagnostics or graveyard depending on the failure.

## Running the App and Tests

Use the project virtual environment:

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Run the regression suite after changing strategy engine logic, report generation, mutation-space schema, version migration, or API behavior:

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
```

If the app is already running, reload the browser after backend code changes. If tuning edges do not show a newly added parameter, check both the seed JSON and the SQLite `versions.spec_json` migration path. The app reads persisted versions, not only the file under `strategies/`.

## How to Use Reports

Use the Markdown report first. It should answer these routing questions:

Is the strategy profitable after costs? Does it beat buy-and-hold? Does it have enough trades? Is max drawdown acceptable? Are both sides useful or is one side degrading the parent? Which exit reason makes or loses money? Are weak years still survivable? Are losses caused by poor entries, poor exits, time decay, reverse exits, or regime pockets?

Open JSON only if you need exact trade rows, exact parameters for reproduction, exported features for a model, or fields not summarized in the report. If a future diagnostics prompt cannot operate from the Markdown report, improve report generation rather than making every phase depend on raw JSON.

## Promotion Rules

A candidate can move from phase 2 to phase 3 when it is at least a serious survivor on broad history, with credible trade count, acceptable drawdown, and evidence that weaknesses are localizable.

A candidate can move from phase 3 to phase 4 when it is a strong full-whitebox parent, already explainable, chronologically robust, and not obviously missing a simpler hand-written rule mutation.

A phase-4 mutation can be saved only after live-engine optimization confirms the edge. Offline previews are not enough. A saved phase-4 child should show meaningful improvement in at least one major metric without damaging the others: PF, net PnL, max drawdown, expected payoff, trade count, buy-and-hold outperformance, side decomposition, and period robustness.

A saved final candidate can move to paper trading only after the robustness gate passes. Passing the robustness gate means "production robustness candidate," not "production-ready." Production readiness requires paper-trading evidence and operational controls.

Reject a branch if it improves only by deleting most trades, relies on future information, concentrates gains in one short period, worsens drawdown materially, damages the best side, or cannot be explained as a narrow layer on top of the whitebox parent.

## Codex Execution Checklist

When asked to operate this repo, Codex should:

1. Read `AGENTS.md`.
2. Read the invoked bridgecode playbook, usually `bridgecode/EYE.md` and `bridgecode/plan-code-debug.md`.
3. Read the relevant phase prompt.
4. Read the latest saved run report before opening JSON.
5. Decide whether the report is enough. If not, state what exact JSON/export field is required.
6. Make the smallest local code or prompt change needed.
7. If adding parameters, update engine logic, seed spec, migration path, API/UI exposure if necessary, and tests.
8. Run focused validation first if available, then the full test suite for engine/schema changes.
9. If the strategy is being routed beyond phase 4, run or instruct the operator to run the robustness gate on the exact saved version/dataset/parameters.
10. Report exactly what survived, what failed, what was promoted, and whether the next action is more research, robustness repair, candidate freeze, paper trading, or operational integration.

This workflow is deliberately strict because Mutation Lab is vulnerable to false progress. A strategy research app can look productive while merely overfitting, deleting trades, or hiding broken assumptions. The phase structure exists to prevent that: translate honestly, optimize broadly, mutate one whitebox rule at a time, and add hybrid logic only after a living strategy gives enough evidence for a narrow diagnosable layer.
