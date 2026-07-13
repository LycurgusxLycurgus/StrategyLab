# Full-Whitebox Single Mutation - Breakeven Maturity Gate - run_87fcbd5dd9de

## 1. Frozen Parent Contract

Frozen parent: `run_87fcbd5dd9de` / `ver_3230ea522e50`, family `xauusd_ghl_dc`, asset `XAUUSD`, venue `IC Markets MT5`, timeframe `30m`, dataset `ds_4e109af56413`, engine `ghl_dc_breakout_v1`, execution model `mt5_bar_proxy`, sizing mode `mt5_fixed_risk_lot`, initial capital `5000`, risk `1%`, max leverage `1.0`, commission `0.0035%` per side, slippage `10` ticks, tick size `0.01`.

Parent metrics: net PnL `6539.61`, return `130.79%`, PF `1.8493`, max DD `4.63%`, expected payoff `5.58`, trades `1172`, daily Sharpe `2.1956`, daily Sortino `3.0895`, worst daily return `-1.1%`, Calmar `28.2337`, max initial risk `0.9866%`.

## 2. Current Causal Identity

The parent is a long-only GHL+DC managed-continuation strategy. Gann state exits are the economic engine, producing `11114.68` net PnL over `554` trades. Breakeven exits are a management layer, not the engine: `415` exits, net `-290.12`, and `759` breakeven stop moves. The mutation must improve management quality without removing the continuation winners.

## 3. Evidence Behind the Mutation

The failed-entry triage mutation was previewed first and rejected because it cut too many Gann winners. The next evidenced weakness is breakeven churn and stop-modification timing. Breakeven exits are frequent and only mildly negative, while `37` MT5 stop modify rejects show the rule is active in places where the bar-close proxy cannot always apply a replacement stop.

The smallest useful rule change is not disabling breakeven. It is requiring a minimum trade age before the breakeven replacement is allowed.

## 4. Chosen Single Mutation

Chosen mutation: **breakeven maturity gate**.

New rule: when `breakeven_stop_enabled=true`, the engine may only move the stop to breakeven/profit lock after `bars_held >= breakeven_min_bars`. A value of `0` preserves the parent exactly.

## 5. Why Competing Mutations Wait

Time-risk refinement waits because the period evidence is broad and positive. Stop tightening waits because Gann winners require adverse movement tolerance. Failed-entry triage has already been rejected as a preview. Hybrid work waits because a whitebox management rule still has evidence and is cheap to test.

## 6. Implementation Brief

Add parameter `breakeven_min_bars`, default `0`. In `ghl_dc_breakout_v1`, after a position updates excursion and before calculating the replacement stop, compute `bars_held = index - position.entry_index`. If the trigger MFE/R is reached but `bars_held < breakeven_min_bars`, do not move the stop; increment `breakeven_maturity_blocks`. All other stop, Gann, entry, sizing, and time-risk logic remains unchanged.

The rule uses only decision-time-safe state: current bar, position entry index, running excursion, entry price, stop price, and configured threshold. It does not use future MFE/MAE or final exit reason.

## 7. New Parameters and Mutation Space

`breakeven_min_bars`:

- path: `parameters.breakeven_min_bars`
- default: `0`
- first active survivor: `2`
- search mode: `range`
- search min/max/step: `0 / 5 / 1`
- rationale: require a minimum trade age before moving the GHL+DC stop to breakeven, reducing immature stop modifications.

## 8. First Unsaved Preview

Preview ledger: `artifacts/diagnostics/phase3_breakeven_preview_candidates_run_87fcbd5dd9de.json`.

The best preview was `breakeven_min_bars=2`:

| Metric | Parent | Preview |
|---|---:|---:|
| Net PnL | `6539.61` | `7155.56` |
| PF | `1.8493` | `1.8496` |
| Max DD % | `4.63` | `5.16` |
| Trades | `1172` | `1170` |
| Daily Sharpe | `2.1956` | `2.2840` |
| Daily Sortino | `3.0895` | `3.2080` |
| Worst Daily Return % | `-1.10` | `-1.04` |
| Calmar | `28.2337` | `27.7387` |
| Breakeven exits | `415` | `361` |
| Stop exits | `202` | `224` |
| Gann exits | `554` | `584` |
| MT5 modify rejects | `37` | `29` |

This is a survivor with a drawdown tradeoff, not an automatic promotion.

## 9. Post-Survival Optimization Plan

Run `Optimize Baseline Twice` with `breakeven_min_bars` available as a whitebox lever. The optimizer may keep `2`, return to `0`, or combine it with existing breakeven controls such as `breakeven_trigger_mfe_r` and `breakeven_lock_r`. Do not use strict Phase 4 production optimization yet.

## 10. Acceptance Rule

Accept only if optimization preserves or improves the parent on net PnL, PF, daily Sharpe/Sortino, worst daily return, and Calmar without pushing max DD beyond a reasonable low-single-digit range or damaging Gann exit PnL. Trade count should remain close to the parent, and the improvement must not come from deleting activity.

## 11. Rejection Rule

Reject if optimization only increases net PnL by accepting worse drawdown, lowers PF materially, worsens daily Sortino, increases stop damage, damages Gann exits, or concentrates gains into only recent years.

## 12. Final Routing

Route: **optimize a survived mutation**.

Practical next step: set or optimize `breakeven_min_bars`, starting from `2`, and run `Optimize Baseline Twice` on `run_87fcbd5dd9de` / `ver_3230ea522e50`. If the optimized child survives, save it as the next Phase 3 parent and rerun `03-1`.
