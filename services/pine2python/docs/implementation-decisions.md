# Implementation decisions

## In-place monorepo package

Pine2Python was built directly at `services/pine2python/`, not in a temporary
external repository. It owns its Python/Node dependencies, API, CLI, tests,
artifacts, notices, and Dockerfile while StrategyLab owns lifecycle state.

## TradingView Basic proof

Paid CSV export was removed from the contract. The normal external gate is one
screenshot of an on-chart table containing exact window, OHLC, stream, segment,
trade, and Strategy Tester evidence. The Python and Pine implementations use
small-modulus triple rolling fingerprints over integer ticks. They are comparison
fingerprints, not cryptographic hashes.

## Agent-assisted browser corroboration

A Codex agent may operate a user-authenticated TradingView tab to paste the exact
instrumented bytes, add the script, wait for the declared closed-bar window, and
save the dashboard screenshot. This is interactive UI corroboration, not chart
scraping: the generated dashboard remains the only machine-comparable payload.
The agent records a matching observation as pending, and only the user's explicit
accept/reject verdict can promote it to `TRADINGVIEW_ACCEPTED`. The reusable
operator contract is documented in
`services/pine2python/docs/tradingview-browser-corroboration.md`.

## Existing-source fidelity gate

An adaptation or repair of existing Pine begins with an immutable unchanged
baseline. StrategyLab's review-package operation compares caller-declared
protected source regions by exact UTF-8 SHA-256, records repair targets and
prohibited changes, and derives focused review fixtures from supplied or
persisted trace rows. A protected mismatch is reported independently from
runtime parity.

This gate prevents an executable reconstruction from silently replacing the
indicator the user asked to repair. It also keeps unsupported `request.*`,
drawing, or realtime behavior intact and routes it to TradingView instead of
rewarding a rewrite that merely fits PineTS's supported subset. Full 5,000-bar
proofs are reserved for candidates that first pass source fidelity and bounded
focused review.

## Cross-runtime numeric quantization

Proof schema `1.2` / instrumentation `tv_table_v2_12` owns integer quantization
instead of delegating it to runtime-specific rounding implementations. Pine
documents `math.round` ties as rounding up, so both Python and generated Pine use
an explicit floor-of-value-plus-one-half rule with a sub-ULP tolerance. This is
especially important for midpoint and retracement features that can fall exactly
between two ticks.

## TradingView proof table placement and body size

Instrumentation `tv_table_v2_12` anchors the generated proof table at bottom
right so a conventional source-owned top-right dashboard cannot cover it even
when that source table is cleared or hidden. Table proofs pack bar metadata into
one integer array and all three-lane fingerprints into one matrix. Dataset,
stream, and dashboard work is split into bounded helpers, while the global body
owns only two proof-state objects and a small set of calls. Standalone source
plots titled `p2p__*` with `display.none` are removed from table-only proof bytes
because the dashboard hashes those expressions directly.

Very large sources may explicitly mark a pure rendering block with matching
`P2P_PROOF_COMPACT_BEGIN <name>` / `P2P_PROOF_COMPACT_END <name>` comments. The
table-proof derivative moves that block into a helper and records the transform;
the immutable readable source remains unchanged. This is never applied to an
unmarked block or to calculations/state transitions.

PineTS runtime proofs intentionally retain the array-based accumulator and the
exact source-owned hidden plots because PineTS does not execute matrices and
needs those exports for stream capture. Runtime-only plots stay in global scope
because Pine requires `plot()` there. The generator evaluates each quantified
expression once and mixes it through three lanes in both representations. Any
future change to these emitted bytes must bump the instrumentation version to
prevent immutable artifact collisions.

## Local runtime boundary

PineTS runs in a short-lived fixed Node worker. Arbitrary source is Pine source,
not JavaScript. Requests involving `request.*`, `varip`, imports, or external data
are blocked from local execution and routed to focused TradingView review.
When an immutable revision already records those static runtime blockers,
StrategyLab passes them into the proof request and Pine2Python records
`LOCAL_RUNTIME_SKIPPED_FROM_REVISION_ANALYSIS` instead of reparsing the same
large source before every proof window. This changes only local execution
attempt policy; proof settings, trace fingerprints, and TradingView acceptance
remain unchanged.

## Stateful proof runtime boundary

A stateful revision may declare `settings.state_start_ms` only when its Pine
source resets every calculation state needed by the proof at that timestamp. The
service then executes candles from that boundary through the proof end rather
than serializing irrelevant older history. The declared boundary cannot be later
than the dashboard window start and is recorded in `local_runtime.runtime_window`.
Without this declaration, dataset history remains the runtime basis.

StrategyLab keeps the exact TradingView ticker and Pine timeframe in revision
settings separately from dataset shorthand such as `BTCUSDT` and `15m`. The
dashboard context uses the TradingView values; the dataset ID and file SHA-256
continue to own local candle identity.

## Byte-exact workbench artifacts

Immutable revision and proof paths write UTF-8 bytes in binary mode. Existing
files are compared byte-for-byte, not through universal-newline text reads. This
prevents Windows CRLF translation from producing a saved `source.pine` or
`instrumented.pine` whose actual SHA-256 differs from the recorded source or
instrumented-source hash.

## PineTS custom-data context

The proof dashboard uses an explicit expected minimum-tick input and hard-coded
expected context label. PineTS custom arrays do not reliably populate all
`syminfo` fields. The TradingView screenshot is accepted only when the visible
chart context and dashboard contract agree and the data fingerprints match.

## Stream capture versus parity

If proof callers provide aligned trace rows, Python computes the expected stream
fingerprints independently and a local match is labeled
`LOCAL_PROOF_PARITY_PASS`. Without those rows, PineTS captures the declared
streams and the result is labeled `LOCAL_PROOF_CAPTURE_COMPLETE`. The captured
trace is still valuable input for TradingView corroboration and later Python
translation, but it is not described as independent parity.

## StrategyLab golden adapter

`ma_cross_atr_stop_v1` implements only the explicit `next_bar_open` contract.
`mt5_bar_proxy` and advanced optional engine features are rejected or left
unsupported until their Pine lifecycle is implemented and proven. The golden
fixture compares exact OHLCV and decision-time position lifecycle over 240 bars.
