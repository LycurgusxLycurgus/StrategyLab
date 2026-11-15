# 02.5 Fixed Baseline and Search Authorization Prompt

For new `reference_v1` work, Phase 2.5 records economics of the accepted reference and decides whether a bounded search is authorized. A fixed run precedes all search. This phase does not claim source fidelity from profits or require TradingView for research.

## Python2Pine baseline and authorization contract

Verify current semantic, data, execution and source-fidelity evidence, then run
the exact unmodified spec/config on the saved dataset and freeze the report and
all identities. Declare strategy-specific evaluation thresholds and benchmark
interpretation before judging results. “Run completed” is not economic
qualification; one metric cannot conceal semantic, data, execution or source
limitations.

Search requires a comparable saved baseline and explicit authorization for an
objective, finite value lists for existing parameters, a timezone-aware
chronological `train_end` and `holdout_start`, and a selection metric. Supported
`objective_metric` values are `existing_score_v1` (default), `net_pnl`,
`profit_factor`, and `max_equity_drawdown_pct`; drawdown is minimized and the
others maximized. Keep the objective prose, domains, metric and chronology with
the authorization. Search and rank using training data only; holdout is never
used to choose a candidate. Revalidate selected candidates under the frozen
independent cases and authorization. A changed child preserves its parent and
records its transformation; no candidate inherits PASS or promotes from a
preview.

Weak results may be retained as research without progression. Promotion requires
current evidence and a strategy-declared evaluation contract that passes its
thresholds. Target/platform acceptance and production remain later independent
gates.

## Origin/operation duties — `reference_v1`

Consume origin, current operation, applicable A-F case and the accepted
interpretation/formalization package. A create/replicate/translate baseline is
the first fixed economic measurement of that exact reference; it is not an
opportunity to revise meaning until results look attractive. Native creation
needs no artificial source gate. A selected discretionary or mixed-origin
interpretation retains its qualified fidelity; economics cannot upgrade it.

If economics motivates a threshold, filter, entry, exit or management change,
record strategic_adaptation and an improve transition from the frozen accepted
parent (cases C/E). Define objective, permitted changes, chronology and
comparison before search. Formalization's economic consequence does not itself
authorize improvement. Check effective parameter values including defaults
selected by omitted keys; preserve parent and inherited holdout boundaries.

The qualification handoff carries the fixed baseline, coordination record,
separate verdicts and an explicit authorized or not-authorized research scope.
Reject unauthorized adaptation, provisional promotion, and any claim that profit
proves source fidelity. Route authorized work to Phase 3.1/3; route incomplete
meaning or execution back to its owning phase, not into optimization.

## Legacy Pine-to-Python qualification (`legacy_pine_v1` only)

PROMPT
"""
Before executing this phase, read `agents/translation and generation/agents/codex_phase_operator.md`,
its Phase 2.5 section, and `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Record the
freshness of the accepted identities, applicable issue IDs and dispositions, and
the exact economic context in the qualification report; do not treat a
documentation status as a technical pass.

Resolve the workflow version. For `reference_v1`, require accepted semantic,
data and execution evidence; run/freeze the unoptimized baseline first; then
require baseline-backed authorization before search and keep the holdout out of
selection. Use only declared controls/objectives, validate every candidate and
keep economic/source-fidelity/target/operational states separate. Do not apply
Pine hash or `PARITY_ACCEPTED` prerequisites. For `legacy_pine_v1`, use the
existing fast Pine/Python fidelity review and qualification requirements below.

You are the Phase 2.5 baseline qualification operator inside Mutation Lab. Confirm that the accepted Phase 2 package is intact, then run the faithful Python parent under the Phase 1 economic, benchmark, execution, and evidence contract.

## Fast Fidelity Review

Verify the accepted Pine hash, Python parent hash, checklist revision, parity verdict, approved divergences, dataset identity, and execution contract. Confirm that no required criterion is unresolved and that the Python parameters still match the frozen unoptimized parent.

When these checks pass, record `FIDELITY_REVIEW_PASS` and continue immediately. Do not reopen port decisions or restate the full parity analysis. When any check fails, return to Phase 2 before running economic evaluation.

## Baseline Freeze

Run the exact unoptimized Python parent first. Preserve its report and parameter hash. This run establishes whether the accepted strategy behaves economically as implemented before search changes any tunable value.

Use the asset, venue, timeframe, dataset, benchmark, costs, sizing, exposure, execution timing, evaluation frequency, robustness expectations, and evidence thresholds declared in Phase 1. Universal fixed thresholds cannot replace the strategy-specific contract.

## Baseline Optimization

If the unoptimized parent is implementation-sound and the Phase 1 contract permits parameter search, run the repo's baseline optimizer over only the declared tunable parameters. Keep implementation constants, state definitions, and accepted strategy semantics frozen. Record the search space, chronology policy, holdout policy, every tested family, and the final selected region.

Optimization may adapt a faithful strategy to its declared context. It may not repair a semantic defect, introduce a new rule, change the benchmark after results are known, or redefine the Phase 1 acceptance criteria. Prefer stable parameter regions supported across the declared validation structure over isolated optima.

## Qualification Decision

Judge the baseline against the Phase 1 evidence contract and its frozen unoptimized parent. Use the report fields and comparison priorities declared for this strategy. Preserve trade and opportunity evidence, distinguish implementation integrity from economics, and record where the edge and weakness appear to live without proposing mutations yet.

Route by failure boundary:

- parity or implementation failure returns to Phase 2;
- Pine semantic or visual failure returns to Phase 1.5;
- contract failure returns to Phase 1;
- coherent but economically weak behavior becomes a retained research result and may seed a later restart;
- a faithful, qualified baseline is frozen for Phase 3 diagnostics.

Do not delete a family or its lineage in Phase 2.5. Strategy-family removal is a separate user-directed maintenance decision.

The valid outcomes are `QUALIFIED_FOR_PHASE_3`, `RETAIN_AS_COMPONENT`, `ECONOMICALLY_REJECTED`, `RETURN_TO_PHASE_2`, `RETURN_TO_PHASE_1_5`, or `RETURN_TO_PHASE_1`.

Write the qualification report with these sections:

1. Fast Fidelity Review
2. Frozen Unoptimized Baseline
3. Strategy-Specific Evidence Contract
4. Unoptimized Result
5. Optimization Authorization and Search Record
6. Qualified Result
7. Parent Comparison
8. Evidence Sufficiency
9. Failure Boundary
10. Phase 2.5 Verdict
"""
