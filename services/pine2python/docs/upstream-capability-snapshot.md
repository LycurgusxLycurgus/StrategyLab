# Upstream capability snapshot — 2026-07-23

## Locked dependencies

| Dependency | Version | License | Observed role |
|---|---:|---|---|
| Pynescript | 0.3.0 | LGPL-3.0-or-later | Pine v5/v6 AST parse, dump, unparse |
| PineTS / `pinets` | 0.9.29 | AGPL-3.0-only | Native Pine transpilation and local runtime |
| ANTLR4 Python runtime | 4.13.2 | BSD-3-Clause | Pynescript parser runtime |

`package-lock.json` and `requirements-lock.txt` are the machine-readable pins.

## Executable observations

- Pynescript parsed the repository's representative Pine v6 indicator and
  strategy fixtures and produced an AST/unparse result.
- PineTS accepted custom caller-supplied OHLCV arrays without selecting a network
  provider.
- PineTS returned named plot series for a hidden instrumented plot.
- PineTS executed `strategy.entry`, `strategy.close`, and exposed strategy state
  including `closedtrades`.
- The Pine implementation of the proof fingerprint, executed by PineTS, matched
  the independent Python implementation for dataset and segmented fingerprints.
- The registered `ma_cross_atr_stop_v1` adapter executed 240 deterministic bars
  and its standard PineTS trace matched StrategyLab Python exactly for OHLCV and
  decision-time position lifecycle.
- `request.*`, `varip`, imports, and external datasets remain capability blockers
  by policy even where an upstream release may partially implement them.
- The Python parent launches a fixed Node module with `shell=False`, a timeout,
  bounded files, and no user-selected executable or module.

Run:

```powershell
npm test --prefix services/pine2python
.venv\Scripts\python -m unittest discover -s services/pine2python/tests -p "test_*.py"
.venv\Scripts\python agentic/testscripts/pine2python_vertical.py
```

## Known gaps

PineTS calls native Pine v5/v6 support experimental. Its results are local
supported-subset evidence and are never promoted to official TradingView truth.
Pynescript labels itself pre-alpha. A parser recovery or upstream runtime change
must remain visible in the analysis artifact. Exact chart-feed identity is proven
through the on-chart dashboard rather than symbol-name inference.
