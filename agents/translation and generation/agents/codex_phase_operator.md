# Codex Phase Operator Guide for Mutation Lab

This guide is the active human and agent workflow for creating, validating, porting, qualifying, mutating, and hardening strategies in Mutation Lab. Each phase owns one evidence boundary. A later phase cannot compensate for an earlier phase that did not pass.

## Repository Map

Phase prompts live in `agents/translation and generation/whitebox/`.

| Phase | Prompt | Owned outcome |
|---:|---|---|
| 1 | `01_translation.md` | Strategy-specific research record and criteria/checklist. |
| 1.5 | `01-5_baseline_transformation.md` | Complete Pine strategy, screenshot-heavy manual TradingView acceptance, and frozen portability package. |
| 2 | `02_baseline.md` | Faithful Mutation Lab Python port with criterion-level parity evidence. |
| 2.5 | `02-5_baseline_qualification.md` | Fast fidelity review, baseline run, authorized optimization, and qualification decision. |
| 3.1 | `03-1_whitebox_diagnostics.md` | Evidence-derived whitebox diagnosis and mutation hypotheses. |
| 3 | `03_full-whitebox.md` | One-by-one whitebox previews and an optimized survivor batch. |
| 4.1 | `04-1_hybrid_diagnostics.md` | Hybrid justification and strategy-specific information, target, representation, and validation contracts. |
| 4 | `04_hybrid-blackbox.md` | Offline previews, live-engine reproduction, and an optimized hybrid survivor batch. |
| 4.2 | `04-2_blackbox_viability.md` | Optional constrained discovery and live reproduction of stable decision-time relationships. |
| 4.3 | `04-3_successor_baseline.md` | Optional evidence-preserving reseed into Phase 1 or Pine revision through Phase 1.5. |

Phases 3 through 4.3 also require `agents/docs/universal_mutation_constitution.md`.

Strategy-development artifacts belong under `artifacts/strategy-development/<strategy_id>/`. Run evidence remains under `artifacts/runs/`, `artifacts/reports/`, and `artifacts/diagnostics/`. Original inspectable source and accepted canonical Pine versions belong under `pre-strategies/` with distinct filenames.

## Operating Constitution

- The Phase 1 criteria/checklist defines correctness before code exists.
- TradingView is the canonical proving ground for chart-based strategies.
- Greenfield Pine and source-derived Pine are equal routes selected by evidence.
- Official TradingView documentation and open-source precedent research are mandatory for both routes.
- The user alone approves the manual TradingView gate.
- Screenshots are required evidence and must map to stable checklist IDs.
- Mutation Lab receives only a frozen, manually accepted Pine strategy.
- Phase 2 proves parity before economics or optimization are interpreted.
- Phase 2.5 reviews successful parity quickly and never repeats the port without a discrepancy.
- Later mutations are derived from the current strategy evidence, never from reusable catalogs.
- Every test preserves the frozen parent and comparable context.
- Offline evidence cannot promote live behavior.
- Production claims require robustness, execution feasibility, forward reconciliation, and operational controls beyond the mutation phases.
- Strategy families remain in the repo until the user explicitly requests removal.

## Phase 1: Strategy Definition and Research

Begin with a strategy idea, explanation, inspectable source, or completed-lineage research brief. Freeze one asset, venue, timeframe contract, execution context, and business objective.

Create:

- `artifacts/strategy-development/<strategy_id>/phase1_criteria_checklist.md`
- `artifacts/strategy-development/<strategy_id>/phase1_research_record.md`

The criteria/checklist must assign stable IDs, scope class, pass condition, evidence method, artifact locator, status, and blocking severity to every in-scope requirement. It owns the semantic, visual, execution, economic, benchmark, regression, screenshot, and port-parity contracts.

Research current official Pine behavior for every nontrivial mechanism. Research inspectable public code for implementation precedent and record provenance and reuse status. Then select `GREENFIELD_PINE` or `SOURCE_DERIVED_PINE` from fit, auditability, and license evidence. A source-derived route cannot continue until the actual source is preserved under `pre-strategies/`.

Phase 1 passes only as `READY_FOR_PINE_CREATION`. It cannot create a Python parent or qualify economics.

## Phase 1.5: TradingView Creation and Manual Acceptance

Build or adapt the complete Pine strategy against the frozen criteria. Keep calculations, state, chart objects, diagnostics, and orders aligned. Make one semantic change per testable revision and preserve known-good versions.

Prepare `phase1_5_manual_review.md` and a screenshot manifest. Freeze the Pine hash, chart environment, complete inputs, strategy properties, execution settings, checklist revision, and fixture locations.

The user tests the exact candidate on the declared asset and timeframe. Required screenshot evidence must prove the strategy-specific accepted and rejected behavior, visual contract, settings, tester result, and state persistence demanded by Phase 1. Each image maps to checklist IDs and a reviewer verdict.

Phase 1.5 reaches 100 percent only when every required item passes, audit-only evidence exists, deferred behavior is isolated, hard failures are absent, and the user accepts the exact Pine hash. Save that script as `pre-strategies/<strategy_id>_accepted.pine` and create the portability package.

## Phase 2: Pine-to-Python Port and Parity

Port only the accepted Pine version. Build a criterion-to-code map before implementation. The map connects every required behavior to Pine code, Python code, parent schema, diagnostics, fixtures, and comparison rules.

Create a parity ledger and report. Exact semantic behavior must match exactly. Numerical tolerance is valid only when Phase 1 declared it before implementation. Intentional platform divergence requires a documented mechanism, preserved causal identity, and explicit approval.

No required item may remain failed or blocked. No optimization, mutation, or economic rescue is allowed during parity work. Freeze the unoptimized Python parent and route only `PARITY_ACCEPTED` ports to Phase 2.5.

## Phase 2.5: Fast Review and Baseline Qualification

First verify hashes, checklist revision, parity status, approved divergences, dataset identity, and execution contract. A complete package receives `FIDELITY_REVIEW_PASS` without repeating Phase 2.

Run the exact unoptimized parent and preserve its report. If the Phase 1 contract authorizes search, use the baseline optimizer only over declared tunable parameters. State definitions, implementation constants, and accepted semantics remain frozen.

Judge results using the strategy-specific evidence and benchmark contract. Fixed universal thresholds cannot replace that contract. A faithful, qualified parent advances to Phase 3. A parity defect returns to Phase 2, a Pine acceptance defect returns to Phase 1.5, and a contract defect returns to Phase 1. Economically rejected families remain preserved as research until the user directs cleanup.

## Phases 3 and 3.1: Whitebox Research

Run Phase 3.1 before mutation code. Diagnose the frozen parent, its economic engine, the decision boundary that departs from the declared objective, and rival causal explanations. Generate no candidate when evidence cannot distinguish a testable mechanism.

Phase 3 implements each justified candidate as the smallest active one-dependency test. Persist all preview results. Promote every independent survivor into one optimization batch, save the child only when it satisfies the strategy contract, and run Phase 3.1 again on materially changed behavior.

Phase 4 becomes eligible only when no explainable rule hypothesis has a better evidence-to-complexity ratio than a bounded statistical layer.

## Phases 4 and 4.1: Hybrid Research

Phase 4.1 defines one diagnosed decision boundary, the information available before that decision, the target, ambiguity handling, representation, chronology, acceptance conditions, and live-engine contract. It chooses no feature or model from a stock catalog.

Phase 4 tests offline candidates, then implements every offline survivor through an explicit live-engine control. Only live reproduction permits promotion. Optimize the live survivor batch under the Phase 1 evidence contract and preserve the whitebox parent outside the bounded decision layer.

## Phase 4.2: Constrained Viability Discovery

Use Phase 4.2 only when a strong parent has an unresolved boundary that earlier phases cannot express cleanly. Freeze the admissible decision-time information and untouched validation boundary before inspecting outcomes. Complexity is earned by evidence and constrained by the current sample and operational budget.

Discovery promotes nothing. Every viable relationship must become an auditable live-engine contract and reproduce its evidence against the frozen parent.

## Phase 4.3: Successor Reseed

Use Phase 4.3 when a completed lineage is informative but structurally unable to meet its production objective. Convert the lineage into supported constraints, rejected assumptions, unresolved questions, and a comparable evaluation contract.

Choose a greenfield Phase 1 route, source-derived Phase 1 route, or Phase 1.5 revision from evidence. A material identity change always creates a new Phase 1 criteria/checklist. Every accepted successor repeats manual TradingView acceptance, Python parity, baseline qualification, and all later gates.

Carry constraints and questions forward. Do not carry tuned strategy content automatically.

## Final Production Gates

Freeze one exact final candidate, dataset, parameter set, execution model, and strategy contract. Run chronological robustness and adverse execution scenarios derived from the declared market and venue uncertainty. A universal stress multiplier is not a substitute for a context-specific stress design.

Audit whether every intended action can become a legal venue order under the declared account and instrument constraints. Then run forward paper reconciliation until the strategy-specific calendar coverage, event coverage, trade evidence, regime exposure, and operational confidence requirements are met. A universal paper duration or trade count is not valid.

Production readiness requires aligned backtest intent, forward decisions, submitted orders, venue responses, fills, position state, risk controls, and monitoring.

## Running the App and Tests

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
```

Run the regression suite after engine, schema, migration, API, or report-generation changes. Prompt-only changes require reference and contract validation.

## Codex Execution Checklist

1. Read `AGENTS.md`, the active Bridgecode route, the phase prompt, and the universal mutation constitution when applicable.
2. Verify the previous phase artifact and verdict before acting.
3. Freeze the current strategy, data, and execution contracts.
4. Read the Markdown evidence first and request raw data only for a named missing question.
5. Make the smallest complete change for the active phase.
6. Persist accepted and rejected evidence.
7. Run focused validation and the full suite when implementation contracts changed.
8. Report the exact verdict, evidence, unresolved boundary, and next phase.
9. Preserve strategy families unless the user explicitly selects them for removal.

The workflow prevents false progress by separating strategy definition, manual semantic proof, port fidelity, economic qualification, explainable mutation, bounded statistical discovery, and production validation.
