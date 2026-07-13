# Phase 2B Baseline Routing - run_87fcbd5dd9de

## 1. Report Inputs

Reviewed report: `artifacts/reports/run_87fcbd5dd9de.md`.

The report is sufficient for Phase 2B routing. It includes the frozen strategy contract, production gate, parent comparison, portfolio metrics, buy-and-hold comparison, side decomposition, exit-reason decomposition, period decomposition, duration statistics, and MFE/MAE diagnostics. Raw JSON was checked only to confirm fields already present in the report.

## 2. Baseline Evidence

This run tests `ver_3230ea522e50`, a saved `xauusd_ghl_dc` white-box parent on `XAUUSD`, `IC Markets MT5`, `30m`, dataset `ds_4e109af56413`. The strategy engine is `ghl_dc_breakout_v1` under `mt5_bar_proxy` execution, mark-to-market equity, `mt5_fixed_risk_lot` sizing, `initial_capital=5000`, `risk_pct=0.01`, `max_leverage=1.0`, `min_lot=0.01`, `lot_step=0.01`, `commission_pct=0.0035`, `slippage_ticks=10`, and `tick_size=0.01`.

The optimized result is active and non-trivial: `1172` trades, net PnL `6539.61`, return `130.79%`, profit factor `1.8493`, max drawdown `4.63%`, expected payoff `5.58`, win rate `29.35%`, average win/loss ratio `4.4513`, and approximate breakeven win rate `18.34%`. The low hit rate is acceptable because the payoff asymmetry is large enough and the realized win rate remains above breakeven.

Portfolio evidence is strong enough for baseline survival: daily Sharpe `2.1956`, daily Sortino `3.0895`, worst daily return `-1.1%`, Calmar `28.2337`, average entry exposure `83.12%`, max entry exposure `99.99%`, average initial risk `0.3378%`, and max initial risk `0.9866%`. Production gates show no core, benchmark, or live-execution review failures.

The benchmark comparison is mixed but acceptable under the lab policy. Buy-and-hold made `13154.17` or `263.08%`, so the strategy underperformed raw buy-and-hold by `-132.29%`. However, buy-and-hold max drawdown was `25.96%` versus the strategy's `4.63%`, and Calmar was `10.1331` versus strategy Calmar `28.2337`, producing a positive Calmar delta of `18.1006`. This is a valid production-comparable baseline under the rule that a strategy may advance if it loses raw return but wins strongly on drawdown-adjusted efficiency while satisfying core gates.

The strategy is long-only. Side decomposition is therefore simple: `1172` long trades, `6539.61` net PnL, PF `1.8493`; no short-side evidence exists. Exit decomposition shows the economic engine clearly. Gann state exits fund the strategy with `554` trades, `11114.68` net PnL, PF `4.5601`, and `61.91%` win rate. Stop exits lose `-4287.72` across `202` trades, and breakeven stop exits lose `-290.12` across `415` trades. That means the parent is not a high-hit-rate scalper; it is a right-tail continuation engine whose Gann exits must be protected.

Period decomposition is broad enough for Phase 3: every year from `2017` through `2026` is positive. The weaker years are `2018` with PF `1.228`, `2021` with PF `1.1434`, and `2022` with PF `1.2708`; the strongest recent years are `2025` with `1737.0` net PnL and `2026` with `1731.32` net PnL. This is not a one-year artifact.

Execution diagnostics are mostly clean but should stay visible in Phase 3: `1437` long signals, `1172` entries, `228` time-risk filter blocks, `759` breakeven stop moves, `37` MT5 stop modify rejects, and only `1` MT5 invalid lot skip. The lot-constraint problem that hurt earlier 5k MT5 tests is not prominent in this StrategyLab run.

## 3. Optimization Interpretation

Baseline optimization found real life, not merely a less-bad graveyard result. Compared with its parent, this version improved profit factor by `0.358`, net PnL by `2851.48`, reduced drawdown by `0.59` percentage points, and added `297` trades. The move to `breakeven_stop_enabled=True` and `donchian_length=34` did not simply delete evidence; it increased activity and improved expectancy.

The result is production-comparable inside StrategyLab's current research engine because it uses MT5-style lot rounding, bounded leverage, realistic cost proxy, slippage, mark-to-market equity, and benchmark comparison. It should not be called production-ready. It has not yet been validated as a final MT5 executable candidate, has not passed a fresh robustness dossier from this exact run, and has not gone through Phase 3 diagnostics.

## 4. Mutation Potential

The preserved mutation potential is still meaningful, but it must be handled carefully. The parent makes money through Gann state exits and large average wins. Any Phase 3 mutation that cuts too many trades or suppresses Gann exits to improve cosmetic win rate should be rejected.

The strongest localized weakness is exit-path waste. Breakeven exits are frequent and slightly negative (`415` trades, `-290.12`), while stop exits are materially negative (`202` trades, `-4287.72`) and occur quickly on average (`3.47` bars). The first diagnostic question is not "tighten stops"; it is whether a decision-time-safe rule can distinguish failed entries or poor early path behavior without removing the Gann exits that fund the system.

Secondary mutation candidates may include a failed-entry triage rule, a more precise breakeven activation/lock rule, or a context-aware time-risk refinement. However, Phase 3 must start with diagnostics before selecting a mutation. The report shows enough evidence to justify Phase 3, but not enough to code a new rule blindly.

## 5. Route Decision

Move to Phase 3 full-whitebox diagnostics.

Frozen parent for Phase 3: `run_87fcbd5dd9de` / `ver_3230ea522e50`.

Run next prompt: `03-1 Full-Whitebox Diagnostics Prompt` against `artifacts/reports/run_87fcbd5dd9de.md`.

Do not proceed directly to Phase 4 and do not translate this version to MT5 as a final candidate yet. The practical next step is to diagnose the exit-path and failed-entry evidence, choose exactly one whitebox mutation if justified, preview it against this frozen parent, and only then decide whether to save/promote.
