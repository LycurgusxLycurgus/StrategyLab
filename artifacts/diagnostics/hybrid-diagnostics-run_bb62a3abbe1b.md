# Hybrid-Blackbox Diagnostics: `run_bb62a3abbe1b`

## 1. Frozen Whitebox Parent Contract

The frozen parent is `run_bb62a3abbe1b`, family `btc_intraday`, stage `white_box`, verdict `promotion_candidate`, dataset `ds_d14d74e36d0d`. It runs `ma_cross_atr_stop_v1` on `BTCUSDT`, `Binance Spot`, `15m`, with both long and short participation enabled. The live contract is a crossover-only SMA/ATR strategy with full-whitebox management rules already active: `fast_len=30`, `slow_len=104`, `max_no_cross=1`, `atr_len=70`, `stop_mult=5.1`, `time_decay_exit_enabled=true`, `time_decay_bars=40`, `time_decay_min_mfe_r=0.35`, `short_quality_gate_enabled=true`, `short_quality_gate_rule=block_below_sma`, `short_quality_gate_len_bars=24960`, `breakeven_stop_enabled=true`, `breakeven_trigger_mfe_r=0.25`, `breakeven_lock_r=1.0`, `time_risk_filter_enabled=true`, `time_risk_block_weekdays=[6]`, and `time_risk_block_utc_hours=[13, 15, 21]`.

The cost and execution assumptions are `initial_capital=100000`, `quantity=1`, `commission_pct=0.04`, `slippage_ticks=2`, and `tick_size=0.01`. The headline metrics are strong enough to freeze this version as the phase-4 parent: net PnL `369712.51`, return `369.71%`, profit factor `4.3941`, max drawdown `2.13%`, expected payoff `472.78`, total trades `782`, win rate `73.4%`, average win/loss ratio `1.5923`, breakeven win rate `38.58%`, buy-and-hold return `70.69%`, and outperformance `299.03%`.

This hybrid diagnostic uses only the Markdown report. The report contains enough evidence to decide phase-4 readiness and the first hybrid hypothesis. Raw JSON is not needed for this decision.

## 2. Evidence Sufficiency

The report is sufficient for phase-4 diagnostics because it includes the frozen contract, the parent comparison, headline metrics, buy-and-hold comparison, diagnostic counters, side decomposition, exit-reason decomposition, period decomposition, trade-duration quantiles, and MFE/MAE summary. These are the fields needed to decide whether the parent is alive, whether it is robust enough for hybrid work, and where the remaining weakness lives.

The report is not sufficient for model training, but that is not a report defect. Training a hybrid layer requires a separate trade-level or candidate-level export. The report can justify the first experiment; the implementation step must then export one row per decision point with decision-time features and future outcome labels separated cleanly.

## 3. Why Hybrid Is Justified or Not

Hybrid work is justified. This parent is not a dead or underdiagnosed strategy. It has `782` trades, broad period participation from `2017` through `2026`, positive net PnL in every reported year, strong drawdown control, strong profit factor, and meaningful buy-and-hold outperformance. Both sides are profitable: longs produce `230605.69` net PnL with `4.3814` PF over `500` trades, while shorts produce `139106.82` net PnL with `4.4154` PF over `282` trades.

That matters because phase 4 should not be used to rescue a weak system. It should be used only when the whitebox parent already works and the remaining improvement is better framed as a scoring problem than as another obvious hand-written rule. Here, the obvious whitebox mutations have already done their job: time decay, short-quality gating, breakeven stop movement, and time-risk blocking transformed the parent into a high-quality full-whitebox candidate. The next improvement should be narrow and diagnostic, not another broad rule stack.

## 4. Whitebox Causal Identity

The parent is no longer just a medium-horizon moving-average trend follower. After phase-3 mutations, its causal identity is better described as a short-cycle managed-trade trend system. It enters on fast/slow SMA crossover conditions with anti-chop constraints, manages risk with ATR stops, moves many trades into protected stop states after small favorable movement, blocks known weak timing pockets, gates shorts through long-context trend quality, and cuts failed trades after a fixed time-decay window.

The system now appears to make money through frequent managed stop/reversal behavior rather than through a small number of very long trend captures. Median trade duration is `11` bars, the 75th percentile is `27` bars, and the 90th/95th percentiles are both `40` bars, exactly matching the time-decay ceiling. The stop-exit bucket is now the main profit engine, not the main damage source: `634` stop exits produce `401335.56` net PnL with `6.3937` PF and `88.01%` win rate. This is a changed but coherent whitebox identity.

## 5. Remaining Weakness to Solve

The clearest remaining weakness is failed-trade quality before or during the time-decay path. The `time_decay` exit bucket has `116` trades, `-26307.01` net PnL, `0.0255` PF, `12.93%` win rate, and exactly `40.0` average bars. That is not automatically bad, because time decay may be preventing worse losses elsewhere. But it is the strongest candidate for hybrid scoring because it is a repeated, measurable failure mode with enough examples to begin testing.

The secondary weakness is reverse-exit quality. The `reverse` bucket has only `32` trades but loses `-5316.04` with `0.2935` PF and `3.12%` win rate. Because the sample is small, reverse exits are less attractive as the first hybrid target. A model trained primarily on `32` events would be more fragile than a model trained around the `116` time-decay failures plus the broader set of successful stop-managed trades.

The hybrid layer should therefore attack entry or early-trade quality for trades likely to become time-decay failures, not the whole strategy. It should not remove the long side, remove the short side, rewrite stop logic, or predict BTC direction. The parent already has strong side balance and strong period robustness.

## 6. Chosen Hybrid Role

The first hybrid role should be an entry-quality veto layer for likely time-decay failures.

The layer should score each candidate entry at decision time and veto only the lowest-quality subset that resembles the trades later ending in failed time-decay outcomes or low/no favorable excursion. The role is deliberately narrow: it does not choose entries independently, does not move stops, does not alter exits, and does not replace the SMA/ATR parent. It only asks whether a valid whitebox entry has enough context quality to be admitted.

This is preferable to a broad regime model because the strategy already performs across years, including difficult periods. It is also preferable to side removal because both long and short books are strong. The first hybrid experiment should focus on filtering avoidable failed entries while preserving the high-performing stop-managed engine.

## 7. Feature Contract

All features must be available at the entry decision point. The feature table should explicitly mark each field as a decision-time feature, label, outcome diagnostic, or grouping key. No future exit reason, future MFE/MAE, future return, full-trade duration, or post-entry path information may be used as an input feature.

The first feature set should be intentionally small and auditable:

| Feature family | Decision-time examples | Why it is allowed |
|---|---|---|
| Parent identity | side, entry timestamp, weekday, UTC hour, active whitebox parameter values | Known before entry and useful for timing/side pockets. |
| Trend geometry | fast SMA, slow SMA, fast-minus-slow distance, normalized MA distance, fast slope, slow slope | Derived from bars completed before entry. |
| Volatility context | ATR, ATR percentile/rank over prior window, recent true-range compression/expansion | Uses only prior bars and helps distinguish stalled entries from energetic entries. |
| Chop/noise context | `max_no_cross` state, recent crossing count, recent return variance, distance from recent local range | Available from pre-entry bars and aligned with the parent thesis. |
| Stop/risk context | entry-to-stop distance, stop distance in ATR, stop distance as percent of price | Known when the trade is created. |
| Recent price behavior | prior N-bar returns, prior N-bar high/low range, prior N-bar candle body/range summaries | Uses completed bars only. |
| Calendar context | hour, weekday, month/year grouping for validation diagnostics | Known at entry; must not become a hidden memorization of future periods. |

The feature contract should start simple. If a scorecard or logistic regression cannot improve the parent, only then should a shallow tree be tried. The first objective is not maximum predictive power; it is a leak-free test of whether time-decay failures have a detectable pre-entry signature.

## 8. Label Contract

The first label should be binary and tied to the chosen role: `bad_entry_quality = 1` when an admitted whitebox trade later becomes a failed trade that the hybrid layer would ideally veto.

A defensible initial label definition is:

`bad_entry_quality = 1` if the trade exits by `time_decay`, or if realized R/PnL is negative and MFE/R is below the time-decay threshold needed to justify staying in the trade.

`bad_entry_quality = 0` if the trade produces positive realized outcome or reaches enough favorable excursion to justify the parent’s management logic.

Ambiguous trades should be excluded from the first model rather than forced into noisy labels. For example, a tiny positive trade with almost no MFE, or a small negative trade that had meaningful favorable excursion, may be better treated as neutral until the first experiment proves useful. Outcome diagnostics such as exit reason, MFE/R, MAE/R, realized R, duration, and year must be available for labeling and analysis, but not as decision-time input features.

The first label should not be "profitable versus unprofitable" alone. The parent already has high win rate and strong PF; the more precise question is whether the model can identify entries likely to become stale, non-progressing, low-quality trades.

## 9. Model Contract

The first model should be transparent and CPU-friendly. Start with logistic regression or a simple scorecard. If the relationship is visibly nonlinear, test a shallow decision tree as a second model family, but not before the simpler model gives a baseline.

No deep learning, no GPU dependence, no sequence transformer, no opaque market predictor, and no model that replaces the parent’s entry/exit logic. The model output should be a probability or score for `bad_entry_quality`. The operational rule should be a thresholded veto, for example: veto only the worst X% or only trades above a calibrated bad-quality probability threshold.

The model must be auditable. The diagnostics should report feature importance or coefficients, retained/vetoed trade counts, and the outcome of vetoed trades versus retained trades. If the model cannot be explained to a human operator, it is too complex for the first phase-4 experiment.

## 10. Validation Contract

Validation must be chronological. Random train/test split is invalid because it leaks regime structure across time. The first implementation should use either walk-forward validation or a strict chronological train/validation/test split.

A pragmatic first split:

| Segment | Purpose |
|---|---|
| Early history through 2022 | Fit candidate model and initial threshold. |
| 2023-2024 | Validate threshold and check robustness. |
| 2025-2026 | Final out-of-sample comparison against frozen whitebox parent. |

If the app supports walk-forward, prefer walk-forward because the dataset covers multiple BTC regimes. Each validation fold must compare the hybrid child against the frozen whitebox parent on the same period.

The hybrid report must include retained trade count, vetoed trade count, retained percentage, PF, net PnL, max drawdown, expected payoff, win rate, side decomposition, exit decomposition, period decomposition, buy-and-hold comparison, and parent deltas. It must also show whether the vetoed trades were genuinely low quality. If the model improves headline metrics only by deleting most trades, it fails.

## 11. Acceptance Rule

Accept the first hybrid mutation only if it improves the frozen parent in a meaningful way while preserving activity and robustness. A good acceptance rule for this parent is:

| Metric | Minimum acceptable behavior |
|---|---|
| Retained activity | Keep at least `70%` of parent trades unless the improvement is extraordinary and stable. |
| Profit factor | Improve PF over `4.3941` or keep it roughly equal while improving drawdown/net PnL quality. |
| Drawdown | Keep max drawdown near or below `2.13%`; any increase requires a clear compensating gain. |
| Net PnL | Preserve or improve net PnL relative to `369712.51`; do not accept a high-PF low-PnL artifact. |
| Period robustness | Avoid turning any formerly positive major period into a structural failure. |
| Side robustness | Do not damage either the long book or short book enough to erase the balanced parent identity. |
| Failure targeting | Vetoed trades should be enriched for time-decay failures, low MFE, or poor realized outcome. |

The hybrid layer survives only if it sharpens the parent. It should reduce stale/failed entries without mutating the strategy into a low-activity curve-fit.

## 12. Rejection Rule

Reject the hybrid mutation if it deletes too many trades, improves only in-sample, relies on leaky features, damages the best periods, damages either side materially, worsens drawdown, or cannot explain why vetoed trades were lower quality than retained trades.

Reject it immediately if any feature uses future path information at entry time. Future exit reason, future MFE/R, future MAE/R, realized return, duration, and final outcome are labels or diagnostics only. They are never input features.

Reject it if the model is effectively a year memorizer. The model may use calendar fields for timing context, but it must not survive only by learning that one historical period was good or bad.

## 13. Required Data Export

The Markdown report is enough for diagnostics, but the first hybrid experiment needs a new trade-level export. This is not a weakness of the report; it is a different artifact with a different purpose.

The export should be created at the trade or candidate-entry level, preferably one row per admitted trade first. A later version can add rejected parent candidates if the engine records candidate state.

Required columns:

| Field group | Columns | Role |
|---|---|---|
| Identity | run_id, trade_id, family_id, version_id, dataset_id | Grouping key |
| Time | entry_ts, exit_ts, year, month, weekday, utc_hour | Feature/grouping key; exit_ts is diagnostic only |
| Parent state | side, entry_price, stop_price, stop_distance, stop_distance_atr, current parameters | Decision-time feature |
| Trend context | fast_sma, slow_sma, fast_minus_slow, normalized_ma_distance, fast_slope, slow_slope | Decision-time feature |
| Volatility context | atr, atr_rank, prior_range_n, prior_return_n, prior_volatility_n | Decision-time feature |
| Chop context | recent_cross_count, no_cross_state, noise_lookback_state | Decision-time feature |
| Outcome | exit_reason, pnl, return_pct, realized_r, duration_bars | Label/outcome diagnostic |
| Excursion | mfe_r, mae_r | Label/outcome diagnostic only |
| Labels | bad_entry_quality, time_decay_failure, low_mfe_failure | Label |

The export must explicitly separate feature columns from label/outcome columns to prevent leakage. If the app cannot yet export this table, the next implementation step should be data export generation before model training.

## 14. First Hybrid Experiment

Run an entry-quality veto experiment for likely time-decay failures.

First, export all trades from `run_bb62a3abbe1b` with the feature and label contract above. Train a logistic regression or scorecard to estimate `bad_entry_quality` using only decision-time features. Validate chronologically, with the frozen whitebox parent as the baseline. Convert the model score into a conservative veto threshold: start by vetoing only the worst `10%` to `20%` of candidate trades by bad-quality probability, then compare retained performance against the frozen parent.

The first experiment should answer one question: do time-decay and low-MFE failures have a detectable pre-entry signature that can be used to veto a small subset of trades without damaging the strong stop-managed engine?

If the answer is yes, the hybrid child can be tested as a live unsaved preview and then optimized only around the veto threshold. If the answer is no, do not escalate to deeper models immediately. Route back to diagnostics and ask whether the remaining weakness is actually an exit-management issue rather than a pre-entry quality issue.

## 15. Final Routing

Proceed to first hybrid experiment, but implement the trade-level export first. The report is good enough for the phase-4 diagnostic decision; no run JSON was needed. The next required artifact is not a better Markdown report, but a leak-safe trade-feature dataset that separates decision-time inputs from outcome labels.

The first hybrid mutation should be an entry-quality veto layer trained to identify likely time-decay or low-MFE failures, validated chronologically against the frozen `run_bb62a3abbe1b` parent, and accepted only if it improves the parent without collapsing trade count or hiding the strategy’s whitebox logic.
