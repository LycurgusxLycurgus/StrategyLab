# Hybrid-Blackbox Diagnostics: run_2a0d6927ded3

## 1. Frozen Whitebox Parent Contract

The frozen whitebox parent is `ver_56fff7af18be`, run `run_2a0d6927ded3`, family `usdjpy_ghl_dc`, named **USDJPY GHL+DC H1 | robustness repair UTC 1,19,20**. It runs `ghl_dc_breakout_v1` on USDJPY at IC Markets MT5, H1, using dataset `ds_64d994c1b98b`: 52,808 bars from 2017-11-02 through 2026-05-01.

The parent uses completed-bar Gann setup, pending Donchian stop entry from the following bar, gap- and spread-aware fills, stop activation after fill, mark-to-market equity, and next-open market exits. Both sides are enabled. Its live rules are Gann 21/21, Donchian 34, maximum breakout age 12, ATR 21, bar-extreme stop, two-bar Gann exit confirmation, adverse escape at -0.75R, and entry vetoes at UTC 01, 19, and 20.

The account contract is 5,000 USD, 0.25% current-equity risk, maximum leverage 1.0, standard FX contract size 100,000, 0.01 minimum/step lot, below-minimum orders skipped, 3.50 USD commission per lot per side, 0.8 pip spread, and 0.2 pip slippage.

The verdict is `production_robustness_candidate`: PnL 2,634.27, return 52.69%, PF 1.5040, 905 trades, drawdown 3.09%, daily Sharpe 1.6937, daily Sortino 1.9529, worst day -0.79%, and Calmar 17.0485. It passes walk-forward 4/4, anchored OOS 3/3, and corrected cost stress 3/3.

## 2. Evidence Sufficiency

Evidence is sufficient for phase-4 diagnostics and a small offline experiment. The Markdown report fully defines the strategy and robustness contract. Raw JSON supplies 905 executed trade rows with complete decision-time entry features; none of the selected feature fields is missing.

The proposed binary label produces 702 worthwhile trades (77.6%), 180 bad trades (19.9%), and 23 ambiguous trades (2.5%). Across four chronological quarters, each fold contains 38 to 48 bad trades and 169 to 182 worthwhile trades. Long and short samples are balanced: bad labels are 91 long and 89 short. The label is therefore imperfect but trainable for a transparent low-capacity model.

## 3. Why Hybrid Is Justified or Not

Hybrid work is justified as an optional sharpening experiment, not as a rescue. The whitebox parent already survives every robustness gate. Phase 3 repeatedly demonstrated a specific residual weakness: many losing trades show little favorable excursion, but deterministic failed-entry triage and breakeven rules also cut future winners and materially reduce portfolio quality.

A narrow score may combine entry geometry, volatility, trend state, and timing more carefully than a single threshold. Because the parent is already strong, the burden of proof is high: failure of the hybrid experiment means keeping the whitebox parent unchanged and proceeding to MT5 parity validation.

## 4. Whitebox Causal Identity

The strategy remains a Gann-state and Donchian-breakout trend continuation system. It earns through payoff asymmetry and patient confirmed exits rather than high hit rate. The hybrid layer must not predict USDJPY direction, replace the entry engine, move stops, or alter exits. Its only permitted role is to estimate entry quality and modestly reduce intended risk for the weakest score band.

## 5. Remaining Weakness to Solve

The localized weakness is **candidate entries that later become low/no-excursion losses**. Hard stops lose 3,314.84, yet simple early-exit rules repeatedly damage the right tail. The target is not every losing trade. It is the subset whose decision-time context suggests weak breakout quality and a low probability of developing sufficient favorable excursion.

The label must preserve recoverable trades. A losing trade that reaches at least 0.25R MFE is treated as worthwhile for the first experiment because it demonstrated potentially manageable movement. A loss below 0.20R MFE is treated as bad. The small gap between thresholds becomes an ambiguous class excluded from training.

## 6. Ranked Hybrid Mutation Queue

1. **Conservative entry-quality size modifier.** Reduce risk to 0.5x only for the worst 10% of out-of-sample scores. This preserves every trade and directly tests whether the score identifies a costly tail.
2. **Extreme-tail entry veto.** Veto only the worst 5% if sizing shows strong separation but insufficient impact. This waits because hard deletion has repeatedly harmed the parent.
3. **Side-calibrated entry-quality modifier.** Use the same feature contract but calibrate score thresholds separately for long and short candidates. This waits because the bad-label counts are balanced and a common model is simpler.
4. **Bar-three failed-path score.** Score open trades after three completed bars using only path information available then. This requires a separate snapshot export and waits because deterministic three-bar triage failed repeatedly.

## 7. Chosen First Hybrid Role

The chosen role is a **conservative entry-quality position-size modifier**. At the exact moment the parent has already approved an entry, a transparent model produces a bad-trade probability. The bottom-quality decile receives half the parent's intended risk; every other candidate receives normal risk. No trade is vetoed in the first experiment.

This is the smallest hybrid role consistent with the evidence. It preserves the parent as the strategy and tests score usefulness without confusing classification quality with trade deletion.

## 8. Feature Contract

Allowed features are available at entry and exported from the frozen parent:

- identity and timing: `side`, `weekday`, `utc_hour`, `month`
- Gann state: `gann_state`, `gann_high_slope`, `gann_low_slope`, `normalized_ma_distance`, `bars_since_gann_flip`
- breakout geometry: `breakout_age_bars`, `donchian_channel_width_pct`, `donchian_breakout_distance_atr`
- volatility and recent path: `atr_pct`, `recent_return_20`, `recent_range_20`, `recent_volatility_20`, `recent_cross_count`
- risk geometry and execution: `stop_distance_atr`, `stop_distance_pct`, `gap_fill`

All fields are known when quantity is calculated. The model must not use exit reason, PnL, MFE/R, MAE/R, duration, future return, future stop movement, or any value updated after entry.

To reduce overfitting, price-level fields such as raw entry price and raw stop price are excluded from the first model. Calendar year is a grouping key, not a feature.

## 9. Label Contract

Use a binary training label with an excluded ambiguous band:

```text
worthwhile = 1 when net_pnl > 0 OR mfe_r >= 0.25
bad = 1 when net_pnl < 0 AND mfe_r < 0.20
ambiguous when neither rule applies
```

The model predicts `bad`, while worthwhile trades form the negative class. The 23 ambiguous rows are excluded from fitting but retained for accounting. PnL, MFE/R, MAE/R, exit reason, and duration are outcome diagnostics only.

This label is deliberately conservative: it does not teach the model that every eventual loser was a bad entry, which would recreate the failed whitebox triage logic.

## 10. Model Contract

Use logistic regression with standardized numeric inputs and one-hot encoding for side, weekday, UTC hour, month, Gann state, and gap-fill status. Use class weighting based only on the training window to address the roughly 20/80 class balance. Limit regularization selection to a tiny fixed grid chosen inside each training window.

No deep learning, random forest, boosted trees, GPU, random train/test split, or large feature search is allowed. Coefficients, preprocessing constants, feature order, and model version must be exported so a future live-engine score can be reproduced exactly.

## 11. Validation Contract

Validation is expanding-window chronological:

1. Train on chronological fold 1, validate on fold 2.
2. Train on folds 1–2, validate on fold 3.
3. Train on folds 1–3, test once on fold 4.

Within each out-of-sample fold, compute the score using only the preceding training window. Reduce risk to 0.5x for the worst 10% of scores in that fold; all other trades stay at 1.0x. Thresholds must come from training-score quantiles, not from the future fold.

Compare against the exact frozen parent on retained trade count, reduced-size count, PnL, PF, drawdown, expected payoff, win rate, daily Sharpe, daily Sortino, worst day, Calmar, exposure, initial risk, sides, exits, years, walk-forward folds, anchored OOS, and corrected fixed-commission/slippage stresses.

## 12. Acceptance Rule

The offline modifier survives only if:

- all 905 trades remain present and only their risk differs
- approximately 5%–15% of out-of-sample trades receive reduced size
- test-fold PnL is no worse than 98% of the frozen parent
- full-history PF is at least 1.50 and drawdown does not exceed 3.09%
- daily Sharpe is at least 1.69, daily Sortino at least 1.95, worst day no worse than -0.79%, and Calmar at least 17.05
- both sides remain profitable and short PF remains above 1.20
- walk-forward remains 4/4, anchored OOS 3/3, and corrected cost stress 3/3
- the reduced-size band has materially worse realized expectancy than the normal-size band in every validation/test fold

An improvement in classification metrics alone is not acceptance.

## 13. Rejection Rule

Reject the hybrid if it needs leaky fields, random splits, a broad model search, or more than the declared feature set. Reject it if the score separation disappears in fold 4, if PnL falls beyond tolerance, if most gains come from one period, if either side becomes weak, if the reduced-size group is not consistently worse out of sample, or if robustness loses any current pass.

Also reject it if live-engine reproduction cannot match the offline risk assignments trade by trade. In that case keep `ver_56fff7af18be` unchanged and proceed to MT5 parity.

## 14. Live-Engine Promotion Contract

Offline success is only gate one. Gate two requires implementing the score as explicit deterministic strategy parameters and preprocessing constants inside the causal backtest engine. The engine must calculate the same entry-time features before lot sizing and apply the multiplier before broker rounding.

Required controls are:

```text
hybrid_entry_quality_sizing_enabled
hybrid_entry_quality_bad_score_threshold
hybrid_entry_quality_low_score_risk_mult
hybrid_entry_quality_model_version
hybrid_entry_quality_feature_order
hybrid_entry_quality_coefficients
hybrid_entry_quality_scaler
```

Reports must include score band, original risk, adjusted risk, rounded lot, reduced-size count, invalid-lot consequences, side split, and chronological performance. The live-engine child must then repeat production optimization only for threshold and multiplier, followed by the full robustness gate.

## 15. Required Data Export

The required export has been generated at `artifacts/diagnostics/hybrid-entry-quality-run_2a0d6927ded3.csv`. It contains 905 rows.

Grouping keys are `trade_id`, `chronological_fold`, `entry_ts`, and `exit_ts`. Decision-time features are the fields listed in section 8 plus direction, entry exposure, and initial risk. The training label is `quality_label`. Outcome-only diagnostics are `net_pnl`, `gross_pnl`, `return_on_equity_pct`, `mfe_r`, `mae_r`, `bars_held`, and `exit_reason`.

The export contains 702 worthwhile, 180 bad, and 23 ambiguous rows. Feature completeness is 100% for the selected first-model contract.

## 16. First Hybrid Experiment

Train the chronological logistic model described above and apply a 0.5x risk multiplier to the worst training-defined 10% score band in each out-of-sample fold. Produce one offline accounting artifact with parent and modified equity metrics, coefficient stability, score-band outcomes, chronological fold results, side decomposition, and robustness-compatible summaries.

Do not use the existing hard-veto experiment as the first test because the evidence specifically favors preserving trades. Do not implement a live branch until this sizing preview survives.

## 17. Fallback Candidate If First Test Fails

If conservative sizing fails, do not immediately try a larger model. The only fallback is an extreme-tail veto of at most 5%, using the same logistic model and chronological contract. If that also fails, reject hybrid work and route the frozen whitebox parent directly to MT5 parity validation.

## 18. Final Routing

**Proceed to the first hybrid experiment from the queue.** The data contract is complete and chronologically adequate for a transparent entry-quality sizing score. Keep `ver_56fff7af18be` frozen. The next action is an offline 0.5x bottom-decile sizing experiment; no strategy code or saved child should be created until that experiment meets the acceptance rule.
