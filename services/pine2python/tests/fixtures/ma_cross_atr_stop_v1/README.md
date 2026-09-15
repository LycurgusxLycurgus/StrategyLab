# MA crossover / ATR stop golden fixture

`fixture.json` is the source-controlled contract for the first complete
StrategyLab adapter. Tests generate its candles deterministically so the
repository does not carry a redundant market-data dump. The fixture deliberately
uses `next_bar_open`; the generator rejects the distinct `mt5_bar_proxy`
contract.

`parity-contract.json` defines the first common Pine/Python trace level. Market
bars and position lifecycle are exact. Feature and signal comparison is added
only after the StrategyLab Python engine exposes those fields directly; it is
not inferred from outcomes.
