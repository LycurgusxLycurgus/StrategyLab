# Full-Whitebox Diagnostics: run_e5a7e6407c8d

This memo treats `run_e5a7e6407c8d` as the frozen parent for the next full-whitebox phase. The strategy is `ma_cross_atr_stop_v1` on `BTCUSDT`, Binance Spot, `15m`, with `SMA 30/104`, `max_no_cross=1`, `ATR 70`, `stop_mult=5.1`, `crossover_only`, long and short enabled, realistic commission and slippage, and the full available Binance history loaded in the current dataset.

The parent is a real research survivor, not a promotion candidate. It produced `1,103` trades across `303,723` bars, `139.3%` return, `1.3069` profit factor, `2.4366` Sharpe, `5.8595` Sortino, `10.44%` max drawdown, and `68.62%` outperformance versus buy-and-hold. The low win rate is not by itself the failure. The strategy wins through payoff asymmetry: its average win/loss ratio is `2.9706`, which implies an approximate breakeven win rate of `25.19%`, while the realized win rate is `30.55%`. The research problem is therefore to preserve the right-tail capture while removing avoidable churn, weak-side exposure, and expensive stop-outs.

## Primary Localization

The first major weakness is side-specific. Long trades carry most of the strategy. Longs produced `547` trades, `121,120.49` net PnL, `1.5633` profit factor, and `33.64%` win rate. Shorts produced `556` trades, only `18,181.00` net PnL, `1.0761` profit factor, and `27.52%` win rate. This does not mean shorts must be deleted immediately, because some years rely on short-side profits, especially `2022`; it means shorts require a stricter context contract than longs.

The second major weakness is exit-specific. Reverse exits are the whole economic engine: `592` reverse exits produced `515,719.19` net PnL with `7.6577` profit factor and `56.93%` win rate. Stop exits are the damage center: `510` stop exits produced `-376,069.86` net PnL, average loss `-737.39`, and average hold `116.02` bars. This strongly suggests that the strategy should not be redesigned around fixed targets. The edge comes from remaining in trends until reversal. Any mutation that cuts long-duration winners is dangerous.

The third major weakness is duration-specific. Trades held `<=6h` lost `-95,437.96`, and trades held `6h-1d` lost `-213,619.99`. Trades held `1d-3d` made `57,052.59`, trades held `3d-7d` made `202,057.64`, and trades held `>7d` made `189,249.21`. This is not a scalping system even though it runs on 15m bars. It is a medium-horizon trend-continuation system whose short-duration trades are mostly failed attempts. The next mutations should respect that identity.

The fourth weakness is period-specific. `2017` was negative, `2018` was weak, `2022` was weak but positive, and `2026` is nearly flat. Strong periods include `2019`, `2021`, `2023`, `2024`, and `2025`. This points toward regime sensitivity, but the first mutation should not be a complex regime model yet. Full-whitebox should test simple explainable regime gates before any hybrid layer.

## Secondary Localization

The short side is especially weak below the 200-day SMA. Above the 200-day SMA, shorts produced `27,805.69` net PnL and `1.1993` profit factor. Below the 200-day SMA, shorts produced `-8,767.96` net PnL and `0.9039` profit factor. This is counterintuitive if one assumes shorts should work better in bearish regimes, but it is plausible for BTC: below long-term trend, short entries may be late, crowded, or entering after exhaustion. This makes a simple “only short in bear regime” rule a bad first mutation unless it is tested carefully.

Entry timing also has pockets of clear weakness. Sunday entries lost `-3,944.77`, while Tuesday entries made `72,700.09`. UTC hours `13`, `15`, and `21` were strongly negative, while hours `01`, `06`, `07`, `10`, and `14` were strong. These are useful diagnostics, but they should not be the first mutation because time filters can overfit quickly and may encode historical liquidity quirks rather than a durable causal mechanism.

Excursion diagnostics show that stop trades often had some favorable movement before failing. Stop trades had average `MFE/R 0.9376`, while reverse exits had average `MFE/R 3.0526`. Among stopped trades, `146` reached at least `1.0R` favorable excursion before eventually stopping out. This supports testing breakeven or partial stop-management logic, but it must be done cautiously because `203` winners also experienced at least `-0.25R` adverse movement, `109` winners experienced at least `-0.5R`, and `47` winners experienced at least `-0.75R`. A tighter stop could destroy winners if applied too early.

## Mutation Test Queue

The first proposed mutation is a time-decay or failed-entry exit. The evidence is strong because the strategy's short-duration trades are structurally bad while medium-duration and long-duration trades fund the edge. The mutation should be narrow: if a trade has not reached a minimum favorable excursion after a fixed number of bars, exit early. The first candidate rule should be something like: after `96` bars, if `MFE/R < 0.5`, exit at market. This attacks non-progressing trades while trying not to disturb trades that already show trend potential. The acceptance rule should require better profit factor and drawdown with no severe damage to net PnL and with trade count still comfortably above the evidence threshold.

The second proposed mutation is a short-side quality gate, but not a naive bearish-regime filter. The diagnostics show that shorts are weak overall and especially weak below the 200-day SMA, so a promising first short-side test is either to disable shorts below the 200-day SMA or to require stronger confirmation for shorts below the 200-day SMA. This is counter to the obvious “short only in bear regime” intuition, which is exactly why the diagnostic matters. The acceptance rule should require short-side PF to improve materially without deleting the short contribution from genuinely useful years.

The third proposed mutation is breakeven stop management after favorable movement. Because many stopped trades reached at least `1R` before failing, a breakeven move after `1R` may reduce stop damage. This should not be tested first unless the implementation can confirm that the rule is decision-time safe and does not introduce intrabar fantasy fills. The risk is that breakeven logic may remove the adverse-movement tolerance needed by the biggest winners.

The fourth proposed mutation is a simple time-risk filter, probably Sunday exclusion or specific UTC-hour exclusion. This should wait until after structural mutations because calendar filters can be fragile. If tested, it should be validated as a single mutation and judged harshly for trade deletion and period overfit.

## Recommended First Test

The best first full-whitebox mutation is the time-decay failed-entry exit. It is the most directly supported by the evidence, it attacks a localized defect, and it does not begin by changing the core entry signal or the right-tail reverse-exit identity. The test should compare the frozen parent against one child with exactly one added rule: exit trades that fail to reach a minimum favorable excursion within a fixed bar window. The first grid should be small and interpretable, for example `bars_wait = 96 or 144` and `minimum_mfe_r = 0.25 or 0.5`, but each tested child must still be treated as a single rule-family mutation rather than a parameter-optimization rescue.

If this mutation improves PF and drawdown while preserving most net PnL and enough trade count, it becomes the new full-whitebox parent candidate. If it reduces right-tail capture or merely improves win rate by deleting the strategy's economic engine, reject it and move to the short-side quality gate.
