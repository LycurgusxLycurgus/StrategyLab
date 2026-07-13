# Full-Whitebox Diagnostics - run_87fcbd5dd9de

## 1. Frozen Parent Contract

The frozen parent is `run_87fcbd5dd9de`, family `xauusd_ghl_dc`, version `ver_3230ea522e50`, stage `white_box`, verdict `promotion_candidate`. It trades `XAUUSD` on `IC Markets MT5`, timeframe `30m`, dataset `ds_4e109af56413`, source `mt5_csv`, with `100319` bars from `2017-11-02 07:00 UTC` through `2026-05-01 19:00 UTC`.

The engine is `ghl_dc_breakout_v1`. The execution model is `mt5_bar_proxy`, equity is marked to market, and the strategy is long-only: `allow_long=true`, `allow_short=false`. The live parameters are `atr_len=34`, `stop_mode=atr`, `stop_mult=2.5`, `donchian_length=34`, `gann_high_period=21`, `gann_low_period=13`, `max_breakout_bars=12`, `breakeven_stop_enabled=true`, `breakeven_trigger_mfe_r=0.5`, `breakeven_lock_r=0.0`, `time_risk_filter_enabled=true`, and `time_risk_block_utc_hours=[1,7,12,14,21]`.

The capital and execution assumptions are production-comparable inside StrategyLab: `initial_capital=5000`, `sizing_mode=mt5_fixed_risk_lot`, `risk_pct=0.01`, `max_leverage=1.0`, `contract_size=100`, `min_lot=0.01`, `lot_step=0.01`, `max_lot=100`, `skip_below_min_lot=true`, `commission_pct=0.0035`, `slippage_ticks=10`, and `tick_size=0.01`.

Headline metrics define the reference object: net PnL `6539.61`, return `130.79%`, profit factor `1.8493`, max drawdown `4.63%`, expected payoff `5.58`, total trades `1172`, win rate `29.35%`, average win/loss ratio `4.4513`, approximate breakeven win rate `18.34%`, daily Sharpe `2.1956`, daily Sortino `3.0895`, worst daily return `-1.1%`, Calmar `28.2337`, max entry exposure `99.99%`, and max initial risk `0.9866%`. Buy-and-hold returned `263.08%` with `25.96%` max drawdown and Calmar `10.1331`; this parent loses raw return but wins strongly on drawdown-adjusted efficiency with Calmar delta `18.1006`.

## 2. Evidence Sufficiency

The Markdown report is sufficient for Phase 3 diagnostics. It contains the frozen contract, parent comparison, production gates, headline metrics, buy-and-hold comparison, side decomposition, exit-reason decomposition, period decomposition, trade-duration statistics, and MFE/MAE diagnostics. Raw JSON was used only to confirm dataset coverage and to compute exit-specific MFE/MAE details that sharpen the mutation queue.

This run is mature enough for Phase 3 reasoning. It has a full-history dataset, `1172` trades, broad chronological coverage, no production-gate failures, and enough decomposition to localize failure rather than guessing. The report does not yet include a full robustness dossier for this exact child, so robustness remains a later gate, not a reason to block whitebox diagnostics.

## 3. Edge Statement

The edge is not hit-rate driven. The strategy wins through payoff asymmetry and controlled participation: only `29.35%` of trades win, but the average win is `4.4513` times the average loss, so the realized win rate sits meaningfully above the `18.34%` approximate breakeven win rate. The economic engine is the long-side GHL+DC continuation path: entries try to catch directional expansion, ATR stops cap failed attempts, breakeven movement reduces damage after favorable excursion, and Gann state exits harvest the winners.

The Gann exit path is the funding engine. `gann_state_exit` produced `11114.68` net PnL across `554` trades, PF `4.5601`, and win rate `61.91%`. The other exits are damage-control paths: `stop` lost `-4287.72` over `202` trades, and `breakeven_stop` lost only `-290.12` over `415` trades. That means the parent survives by letting the right tails breathe while keeping the wrong entries small. Any mutation that improves win rate by deleting many Gann winners would attack the engine rather than the weakness.

## 4. Identity Drift Check

The parent has drifted from a plain translated GHL+DC breakout into a long-only, MT5-feasible managed-continuation strategy. The earlier family versions added long-only behavior, ATR stop sizing, time-risk filtering, MT5 lot constraints, and now a breakeven stop plus shorter Donchian horizon. That identity drift is acceptable because it is causal and auditable: the strategy remains a Gann/Donchian breakout-continuation system, but now it is shaped for a `5000` account and broker lot feasibility.

The current identity is not a scalper and not a pure mean-reversion engine. Median holding time is `9` bars, Gann winners average `20.9` bars, and the system depends on preserving enough medium-duration right-tail trades. The mutation process must respect that identity.

## 5. Diagnostic Evidence

The parent improved materially over its saved predecessor: profit factor delta `+0.358`, net PnL delta `+2851.48`, drawdown delta `-0.59` percentage points, and trade count delta `+297`. This is not a fragile improvement from deleting activity; it both improved expectancy and increased the evidence base.

Side decomposition is clean: all `1172` trades are long, with net PnL `6539.61`, PF `1.8493`, and win rate `29.35%`. There is no short-side evidence and therefore no reason to revisit side enablement before solving the long-side failure modes.

Exit decomposition localizes the edge and the damage. Gann exits make `11114.68`; stop exits lose `-4287.72`; breakeven stops lose `-290.12`; one time exit made `2.77`. The raw count is revealing: `415` breakeven stops, `202` stops, and `554` Gann exits. Breakeven movement is active often (`759` moves), and MT5 stop modify rejects occur `37` times, but these rejects are not yet proven to be a primary weakness because the breakeven exit bucket itself is nearly flat rather than catastrophically negative.

Exit-path excursion evidence is more specific. Stop exits average only `3.47` bars, with average MFE/R `0.2328`, median MFE/R `0.1098`, and average MAE/R `-1.3702`. These are true failed entries: they generally do not move enough in favor before violating risk. Breakeven exits average `7.16` bars, with average MFE/R `0.962`, median MFE/R `0.7881`, and average MAE/R `-0.4353`; they are not disasters, but they may be giving back almost-right trades. Gann exits average `20.9` bars, with average MFE/R `1.905` and median MFE/R `1.3411`, which confirms that winners need time and should not be prematurely cut.

Period evidence is broad: every year from `2017` through `2026` is positive. The weakest years are `2018` with PF `1.228`, `2021` with PF `1.1434`, and `2022` with PF `1.2708`. The strongest recent years are `2025` with `1737.0` net PnL and `2026` with `1731.32` net PnL. This is not one lucky year, but the system is not uniformly strong; weaker sideways or less directional periods still deserve attention.

## 6. Failure Localization

**Side-specific weakness.** There is no current side-selection problem. The parent is long-only, and all evidence belongs to the long side. Reintroducing shorts or testing side removal is not relevant.

**Exit-specific weakness.** The primary weakness is failed-entry stop damage. Stop exits are only `202` trades but account for `-4287.72`, about `65.57%` of total net PnL in negative share terms. They occur quickly, average `3.47` bars, and show low favorable excursion before failure. That makes them the clearest whitebox target.

**Breakeven-path weakness.** Breakeven stops fire frequently (`415` exits) but lose only `-290.12`, average `-0.70`. This is not a major PnL leak, though it may affect identity and opportunity cost. Because breakeven was part of the successful saved mutation, changing it again should wait until failed-entry triage is tested.

**Period or regime weakness.** The weaker years `2018`, `2021`, and `2022` show lower PF but remain profitable. This suggests regime friction rather than regime failure. A broad regime gate could help, but it risks removing the right-tail trades that fund the system.

**Duration weakness.** The duration split supports an early failed-entry mutation. Stop exits are short-duration failures, while Gann exits need longer holding. A rule that acts only after a small number of bars and only when the trade has failed to show favorable excursion is more targeted than a global time exit.

**Execution and lot feasibility.** MT5 invalid lot skips are only `1`, so the earlier 5k lot-minimum problem is not dominant here. MT5 stop modify rejects are `37`, which should be monitored, but the report does not show enough evidence that they are causing the main performance drag.

## 7. Rival Explanations

One rival explanation is that the stop loss is simply too tight. The evidence does not support making that the first mutation. Winners have meaningful adverse movement too: Gann exits average MAE/R `-0.4257`, and the 25th percentile MAE/R reaches `-0.7319`. Tightening stops globally could destroy the Gann winners that make the strategy profitable.

Another explanation is that breakeven should be disabled or delayed. The parent comparison argues against treating breakeven as an obvious defect: the saved child with breakeven enabled improved PF, net PnL, drawdown, and trade count. Breakeven exits are frequent, but their total loss is small relative to stop-exit damage.

A third explanation is that the time-risk filter should be re-optimized. Time-risk blocks `228` long signals and the current filter is part of the working parent. Because all years are positive and the main failure is exit-specific, another time-filter mutation should wait unless failed-entry triage fails.

## 8. Mutation Queue

1. **Failed-entry early triage exit.** The hypothesis is that the worst stop exits can be reduced by exiting early when a trade has been open for a small number of bars and still has not achieved a minimum favorable excursion. The measured weakness is specific: stop exits average `3.47` bars and median MFE/R only `0.1098`. The rule should use only decision-time-safe information after entry: bars held, current unrealized R, best favorable excursion so far, current price relative to entry/stop, and current Gann state. The smallest active first test should exit a long after `3` or `4` bars if `MFE/R < 0.20-0.25` and current unrealized R is negative or not meaningfully positive. Rejection happens if it cuts Gann winners, reduces total trades too aggressively, lowers net PnL, or improves PF only by deleting activity.

2. **Breakeven quality refinement.** The hypothesis is that some breakeven moves occur before the trade has earned enough structure confirmation. The measured weakness is smaller: `415` breakeven exits lose only `-290.12`, but `759` stop moves and `37` modify rejects show this rule is highly active. A first test could require a slightly stronger trigger or a small positive lock only after enough MFE, but this must not be tested before failed-entry triage because breakeven is already part of the successful parent.

3. **Weak-regime time-risk refinement.** The hypothesis is that certain time or regime pockets create low-quality long entries in weaker years such as `2018`, `2021`, and `2022`. The evidence is real but less localized than the stop-exit evidence. A first test would need hourly or weekday decomposition before changing blocked hours again. It waits because a broad gate could remove the same right-tail trades that drive `2025` and `2026`.

4. **MT5 stop-modify feasibility guard.** The hypothesis is that some stop replacement attempts are invalid or too close to market, producing `37` modify rejects and occasional path divergence versus MT5. This is important for translation fidelity, but the report does not prove it is a profit leak. It should be treated as an implementation audit after the next rule mutation, not the first alpha mutation.

## 9. Preview Test Ledger

Preview evidence was generated after implementing the failed-entry triage rule and saved to `artifacts/diagnostics/phase3_preview_candidates_run_87fcbd5dd9de.json`. The frozen parent remains `6539.61` net PnL, PF `1.8493`, drawdown `4.63%`, `1172` trades, and Gann exit net PnL `11114.68`.

Every failed-entry triage preview was rejected. The rule successfully reduced ordinary stop exits, but it also cut too many developing trades that would later become Gann exits, which is exactly the damage the acceptance rule was designed to prevent.

| Candidate | Net PnL | PF | DD% | Trades | Triage Exits | Stop Exits | Gann Exits | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `3bar_mfe025_r0` | `3619.64` | `1.5569` | `6.45` | `1180` | `264` | `151` | `387` | rejected |
| `4bar_mfe025_r0` | `3705.75` | `1.5549` | `6.30` | `1180` | `201` | `175` | `413` | rejected |
| `3bar_mfe020_r0` | `3680.28` | `1.5618` | `6.33` | `1180` | `223` | `157` | `410` | rejected |
| `3bar_mfe025_r010` | `3555.35` | `1.5552` | `6.69` | `1180` | `281` | `149` | `377` | rejected |
| `3bar_mfe015_rneg025` | `4162.87` | `1.6000` | `4.25` | `1179` | `158` | `163` | `452` | rejected |
| `4bar_mfe015_rneg025` | `4195.73` | `1.5988` | `4.70` | `1177` | `116` | `180` | `470` | rejected |
| `5bar_mfe015_rneg025` | `4398.59` | `1.6181` | `4.81` | `1177` | `99` | `185` | `480` | rejected |
| `3bar_mfe010_rneg050` | `5656.60` | `1.7498` | `4.66` | `1174` | `82` | `173` | `505` | rejected |

## 10. Survivor Selection or Recommended First Test

There is no survivor from the failed-entry triage preview set. The implemented rule is causal and decision-time-safe, and it records `failed_entry_triage_exit`, `failed_entry_triage_exits`, and `failed_entry_triage_candidates`, but the preview evidence says it should not be promoted or optimized as the next parent mutation.

The practical next whitebox test should move to the second queue item: breakeven quality refinement. That candidate is more subtle because breakeven exits are only mildly negative, but the parent has `759` breakeven stop moves, `415` breakeven exits, and `37` MT5 stop modify rejects. The next mutation should not disable breakeven wholesale; it should test whether activation quality can be improved without increasing ordinary stop damage.

## 11. Acceptance Rule

The mutation survives only if it improves the frozen parent without damaging the evidence base. It should improve net PnL or materially reduce max drawdown while keeping PF at or above the parent neighborhood, preserving at least roughly `85-90%` of parent trade count, and keeping the Gann exit bucket healthy. The Gann exit net PnL must not be materially reduced, and annual decomposition must remain broadly positive rather than shifting gains into only `2025-2026`.

Portfolio metrics matter more than trade cosmetics. Daily Sharpe, daily Sortino, worst daily return, Calmar, max initial risk, exposure, and benchmark Calmar delta should stay stable or improve. A higher win rate alone is not acceptance.

## 12. Rejection Rule

Reject the mutation if it wins by deleting the evidence base, cuts many Gann winners, reduces total net PnL, increases drawdown, worsens daily Sortino, concentrates returns in only one or two years, or depends on future information such as eventual exit reason or full-trade MFE/MAE. Also reject it if it merely converts stop losses into early exits with similar or worse total loss while adding complexity.

For this parent specifically, reject failed-entry triage if the stop bucket improves but `gann_state_exit` PnL falls enough to reduce total PnL, or if trade count collapses below a credible sample for full-history evaluation.

## 13. Phase-4 Readiness

This parent is not ready for Phase 4 yet. It has enough life, strong drawdown control, positive period breadth, and production-comparable capital assumptions, but the first obvious whitebox mutation failed preview. Phase 4 should wait until the next defensible whitebox mutation, breakeven quality refinement, is previewed or rejected with evidence.

It also still needs the Mutation Lab robustness gate for this exact saved child before any production-readiness language: chronological walk-forward folds and execution-cost stress including doubled commission, doubled slippage, and combined doubled execution costs.

## 14. Final Routing

Route to **reject failed-entry triage and test the next whitebox mutation**.

Practical next step: run a single-mutation Phase 3 prompt for breakeven quality refinement on `run_87fcbd5dd9de` / `ver_3230ea522e50`. Do not save or promote the failed-entry triage child. Do not run `Optimize Baseline Twice` on failed-entry triage because the active previews all underperformed the frozen parent.
