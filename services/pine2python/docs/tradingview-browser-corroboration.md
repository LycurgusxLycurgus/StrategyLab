# TradingView browser corroboration

This runbook standardizes optional agent-assisted TradingView corroboration for
an immutable Pine2Python proof. It uses a user-authenticated interactive browser
session. It does not depend on chart-data export, alerts, webhooks, or browser
scraping. Runtime signatures are only one acceptance dimension: an adaptation
of an existing indicator must also pass source fidelity, protected-behavior,
focused-fixture, and visual-product review.

## Inputs

- Immutable Pine revision ID and source SHA-256.
- Proof evidence ID and exact `instrumented.pine` bytes.
- TradingView symbol, chart timeframe, input settings, proof start/end, expected
  bar count, first/last timestamps, and expected dashboard values.
- A chart with enough indicator capacity for the proof script.
- For an existing-source repair: the immutable baseline revision and a fidelity
  contract containing protected source regions, repair targets, prohibited
  changes, required timeframes, visual requirements, and fixture criteria.

## Fidelity preflight

Before opening TradingView:

1. Register the authoritative existing source unchanged as the baseline
   revision. Do not begin with a reconstruction.
2. Prepare the candidate review package through
   `POST /api/pine-workbench/revisions/{id}/review-package`.
3. Require `SOURCE_FIDELITY_PASS` for every protected region. A mismatch blocks
   browser corroboration unless the user explicitly changes the protected
   contract.
4. Use a bounded local trace to select representative accepted, rejected, state
   transition, and edge-case timestamps when the runtime supports the source.
5. If Pine2Python flags `request.*`, complex drawings, realtime behavior, or
   another unsupported construct, preserve it and route that claim to focused
   TradingView review. Do not rewrite product behavior solely to make PineTS
   execute.
6. Use the fast focused review before generating a full 5,000-bar proof. The
   full proof is reserved for a candidate that already compiles, reads clearly,
   and passes its fixture review.

## Procedure

1. Open the declared TradingView symbol and first review timeframe.
2. If the current plan limit would be exceeded, remove only a stale indicator
   instance that the user has explicitly placed in scope.
3. For an existing-source repair, add the immutable baseline and candidate
   together. Use only the candidate when running the final proof dashboard.
4. Open a clean Pine Editor buffer, paste the exact source, and add it to the
   chart. Do not publish or silently save a modified copy.
5. On each declared review timeframe, inspect the fixed fixture windows,
   protected drawings, event placement, label density, and debug reason codes.
   Capture the minimum focused screenshots required by the fidelity contract.
6. Reject the candidate if a protected calculation or drawing differs, a
   visible event lacks an explainable source level, or the chart is not readable.
7. After focused review passes, load the exact instrumented proof source.
8. Close the editor and wait until the dashboard reaches the expected bar count
   and first/last timestamps. A still-forming candle must not be part of the
   proof dataset or window.
9. Compare every displayed identity, data segment, feature, state, signal,
   rejection, order, and trade field supplied by the proof. Any difference is a
   rejection, even when the chart looks visually plausible.
10. Save one screenshot containing the complete dashboard and visible chart
   context. Compute its SHA-256 and store it beside the proof artifact.
11. Submit a TradingView observation with the displayed values, screenshot hash,
   and verdict `pending`. This may record `TRADINGVIEW_SIGNATURE_MATCH`, but it
   must remain `TRADINGVIEW_REVIEW_REQUIRED`.
12. Ask the user for an explicit `accepted` or `rejected` verdict. Only resubmit
   the same exact proof observation as accepted after that response.

## Iteration discipline

- Diagnose the first divergent prefix or field rather than altering several
  indicator rules at once.
- Preserve one source-fidelity baseline for the workbench. Do not replace it
  when a child fails.
- Preserve one semantic calculation change per immutable child revision.
- Run fast focused fixtures after each child. Do not repeat the full proof until
  the child is a genuine final candidate.
- Instrumentation-only repairs receive a new proof schema/instrumentation
  version and do not require a new Pine calculation revision.
- After a calculation repair, regenerate the full closed-bar proof and repeat
  this gate from the exact new artifact.
- Leave the final chart open for user review.

## Acceptance record

The handoff must name the workbench, baseline revision, candidate revision,
parent, source and settings hashes, fidelity contract, protected-region hashes,
fixture manifest, proof evidence, dataset ID and file hash,
instrumented-source hash, focused and dashboard screenshot paths and SHA-256
values, acceptance status by dimension, user verdict, approved divergences,
unresolved limitations, and exact next phase.
