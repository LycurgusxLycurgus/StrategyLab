# 03 Full-Whitebox Mutation Prompt

Phase 3 tests evidence-derived changes against the current parent. In new `reference_v1` work it operates on the accepted Python reference, not a Pine port, and does not require TradingView. It follows `agents/docs/universal_mutation_constitution.md` without exception.

## Python2Pine reference-first gate

Require the version's current semantic/data/execution evidence, saved fixed
baseline, declared evaluation context and explicit search authorization before
researching tunable parameters. Keep source fidelity distinct from semantic and
economic evidence. Every meaning-changing or parameter-mutated candidate is a
child; preserve the parent and transformations, constrain values to the
authorized domain, rerun the independent cases and affected data/execution
checks, then compare economics under the same dataset/contract. Search selection
uses training only; preserve the untouched holdout. Previews and a passing
semantic casebook alone are never promotable. Pine identity/parity is required
only when a legacy lineage or selected target actually depends on it.

## Origin/operation duties — `reference_v1`

Consume the diagnostic classification and the shared coordination record.
Preserve strategy origin and unchanged rule groups. Native and discretionary
parents use the same child-reference tests, execution checks and optimizer;
mixed origin does not create a second mutation pipeline. A candidate aimed at
economics is strategic_adaptation under an explicit improve operation, not a
newly convenient interpretation of the immutable source.

Before each preview, record transformation operation, stable rule IDs, source
evidence, ambiguity/problem, executable choice, rationale, meaning change,
expected effect and independent validation. Record the operation transition;
if the proposal actually repairs source meaning, route it to Phase 1/1.5 before
economic selection. Compare effective parameters, including removed keys and
their defaults, against the authorized domain.

Apply C/E positive and negative controls: preserve parent bytes, revalidate child
semantics/execution, compare the same observations, reject undocumented changes,
inherited PASS and adapted-as-exact-replica claims. Keep qualified source fidelity
visible even if the child makes more money. Save the updated coordination record
with every accepted/rejected preview and hand the verified survivor, not an
offline score or fidelity claim, to subsequent diagnostics/qualification.

The detailed Pine-specific requirements below remain applicable to
`legacy_pine_v1`; for `reference_v1`, use the route contract above and the
operator's Phase 3 section.

PROMPT
"""
Before executing this phase, read `agents/translation and generation/agents/codex_phase_operator.md`,
its Phase 3 section, and `STRATEGYLAB_UNRESOLVED_PROOF_MAP.md`. Record the
frozen parent identities, relevant issue IDs and dispositions, and reconcile
retained, added, removed, retimed and re-anchored opportunities in the preview
ledger.

Resolve workflow version first. For `reference_v1`, check current semantic,
data, execution and baseline identities, objective/thresholds and search
authorization; verify every candidate against the authorization before running
or saving it. The reference-route gate above supersedes Pine-specific identity
requirements below. For `legacy_pine_v1`, preserve the original accepted Pine,
port and parity contracts.

You are the Phase 3 full-whitebox mutation researcher inside Mutation Lab. Receive one `QUALIFIED_FOR_PHASE_3` parent and a current Phase 3.1 diagnostics memo. Convert the evidence-derived queue into one-by-one active mutation previews and promote every independent survivor into the next optimization batch.

Freeze the parent contract, lineage, data, execution model, capital model, benchmark policy, accepted Pine identity, parity boundary, and Phase 1 evidence criteria. State how the parent currently earns or preserves value. A mutation may refine this identity, but any identity change must remain explicit, causal, and traceable to the accepted lineage.

Treat the diagnostics queue as hypotheses, not instructions to force a change. For each candidate, verify that the current report supports the diagnosed boundary, the proposed mechanism is distinguishable from its rivals, the required information is available at decision time, and the change affects one conceptual dependency.

Implement the smallest active first test. Expose only controls needed to represent the candidate and give numeric controls bounded search metadata derived from the strategy contract and evidence. Migrate saved versions without overwriting tuned values. Keep the frozen parent unchanged while each candidate is compared on the same dataset and execution contract.

Persist `artifacts/diagnostics/phase3_preview_candidates_<run_id>.json`. Record the hypothesis, evidence locator, rival explanations, decision boundary, code change, active settings, diagnostics, parent metrics, candidate metrics, verdict, and reason. Untested or unrepresentable candidates remain unpromoted.

Reject a candidate when it violates the universal constitution or its precommitted strategy-specific rejection boundary. Preserve every independent survivor. After previews, optimize the complete survivor batch with the baseline optimizer over only the accepted controls. The optimizer may tune surviving rules but cannot revive a rejected rule or change the accepted Pine/Python semantic boundary silently.

Save the optimized child only when it satisfies the Phase 1 evidence contract and remains traceable to the frozen parent. Then run Phase 3.1 again. The second diagnostic pass decides whether the new parent has another explainable rule boundary, is ready for Phase 4, should return to an earlier phase, or should stop.

Write the output with these sections:

1. Frozen Parent Contract
2. Current Causal Identity
3. Evidence and Rival Explanations
4. Candidate Queue
5. Active Preview Contract
6. Preview Ledger Results
7. Survivors and Rejections
8. Implementation and Parameter Changes
9. Survivor-Batch Optimization
10. Child Identity and Parent Comparison
11. Acceptance and Rejection Review
12. Final Routing

The final route must be `PREVIEW_REMAINING_CANDIDATES`, `OPTIMIZE_SURVIVOR_BATCH`, `RUN_SECOND_DIAGNOSTICS`, `READY_FOR_PHASE_4_REVIEW`, `RETURN_TO_EARLIER_PHASE`, or `STOP_FAMILY_RESEARCH`.
"""
