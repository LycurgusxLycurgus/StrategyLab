# Pine2Python integration decisions

## Product boundary

Pine2Python is embedded at `services/pine2python/` and remains independently
buildable. StrategyLab owns datasets, Pine revision lineage, user acceptance,
Python versions, promotion, and mutation. Pine2Python owns source analysis,
capability-gated PineTS execution, proof instrumentation, registered generators,
standard Pine traces, and first-divergence comparison.

## TradingView Basic corroboration

Paid chart-data export is not part of the workflow. StrategyLab selects the
latest explicit window of at most 5,000 bars, hashes the exact dataset CSV bytes,
and creates a Pine dashboard containing source/settings identity, time bounds,
bar count, three independent OHLC fingerprints, eight segment fingerprints, and
declared strategy-stream fingerprints. The normal operator action is to paste the
instrumented source into the exact TradingView symbol/timeframe and capture one
complete dashboard screenshot.

`TRADINGVIEW_SIGNATURE_MATCH` means the submitted dashboard values match.
`TRADINGVIEW_ACCEPTED` is added only with an explicit user verdict and a
64-character screenshot SHA-256. Neither PineTS nor the LLM awards acceptance.

## Reference-stream ownership

When caller-supplied trace rows exist, local stream fingerprints are independently
computed from them and may earn `LOCAL_PROOF_PARITY_PASS`. When they do not,
PineTS captures the declared streams and earns
`LOCAL_PROOF_CAPTURE_COMPLETE`; this is a reproducible reference capture, not an
independent parity claim. TradingView must still corroborate it.

## First production adapter

`ma_cross_atr_stop_v1` is the first StrategyLab adapter. Its current generated
contract is deliberately limited to `next_bar_open`, fixed quantity, SMA/EMA
crosses, the price/fast-MA noise gate, and a static ATR stop. Requests for
`mt5_bar_proxy` are rejected as unsupported instead of being approximated. The
golden fixture proves exact market and position-lifecycle parity over 240 bars.

## End-of-window settlement

StrategyLab closes open positions at end-of-data to finish backtest metrics.
Pine/TradingView leaves the last position open. The standard Python trace records
the decision-time position on the final bar and records the synthetic
`time_exit` settlement as an event afterward. This preserves both the engine's
metric behavior and comparable in-window position state.

## Runtime and licensing

The fixed Node worker uses caller-supplied candles, `shell=False`, bounded input
and output, a timeout, and no user-selected executable. `request.*`, `varip`,
imports, and other unverified constructs block local execution. Compose places
the services on an internal network and runs Pine2Python read-only, non-root,
with all Linux capabilities dropped.

PineTS 0.9.29 is AGPL-3.0-only unless separately licensed; therefore the embedded
service is AGPL-3.0-only under the current dependency posture. Pynescript 0.3.0
is LGPL-3.0-or-later. Full direct-dependency license texts are retained under
`services/pine2python/third_party/`.

## Current external prerequisite

Docker Desktop 4.83.0, Docker CLI 29.6.2, and Compose 5.3.1 are installed.
Container execution remains blocked on this workstation until AMD SVM is enabled
in the MSI B450M PRO-VDH MAX firmware; the current OS probe reports firmware
virtualization disabled. Direct virtualenv and Node execution are fully usable in
the meantime.
