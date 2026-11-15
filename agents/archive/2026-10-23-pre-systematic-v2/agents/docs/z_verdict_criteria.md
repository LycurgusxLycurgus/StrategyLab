# Project Aurum Verdict Criteria

Project Aurum does not judge runs by PnL alone. Every run is scored across six layers that come from the strategy evaluation canon and are simplified into an operator-facing rule set.

The first layer is economic performance. A run needs positive expectancy and positive Sharpe before it is treated as anything other than a failed conjecture. Sharpe above `0.75` with expectancy above `0.15R` is the first real sign of life. Sharpe above `1.25` with expectancy above `0.25R` is treated as strong enough to keep incubating. Sharpe above `1.75` with expectancy above `0.40R` is promotion territory if the other layers agree.

The second layer is survivability. A strategy with too few trades or too much drawdown does not graduate even if one metric spikes. Project Aurum expects at least `8` trades with max drawdown at or below `2.5R` before a run looks materially survivable. The stronger tiers require at least `15` trades and drawdown at or below `1.8R`, then `25` trades and drawdown at or below `1.2R`.

The third layer is robustness. The first version uses trade count and Sharpe as a proxy for whether the edge has enough sample to matter. Fewer than `5` trades means robustness is effectively unscored. Around `10` trades with Sharpe above `0.5` is a minimal robustness pass. Around `16` trades with Sharpe above `1.0` is materially better. Around `24` trades with Sharpe above `1.5` is the current best tier.

The fourth layer is implementation integrity. The app assumes this layer starts from a good baseline because the engine, labels, and hybrid comparison are timestamp-safe, deterministic, and persisted with artifacts. This layer only gets downgraded later if a concrete implementation problem is discovered.

The fifth layer is epistemic quality. A run gets more credit here when the white-box or hybrid explanation survives contact with reality and remains diagnostically useful. Hybrid runs get extra credit when the approval gate improves Sharpe without simply deleting the entire sample.

The sixth layer is improvement potential. A run with localized failure and clear mutation direction scores better than one with diffuse noise. Project Aurum prefers a strategy that fails in an informative way over a strategy that is merely chaotic.

These six layers roll into the current destinations:

- `promote`: total score at least `24`, with no economic or survivability failure
- `incubate`: total score at least `18`, with a living edge but more work needed
- `graveyard`: some evidence exists, but the edge is too fragile or the sample too weak
- `bury`: no trades or no meaningful edge signal at all

This means the app is explicitly closer to a white-box or hybrid research lab than a pure-quant Sharpe-only optimizer. A run can make money and still stay in the graveyard if its explanation is weak, its robustness is narrow, or its sample is too small to trust.
