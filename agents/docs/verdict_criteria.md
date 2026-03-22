# Verdict Criteria

StrategyLab uses these deterministic promotion and rejection gates for parameter sweeps and family reviews.

## Rejected

A run is rejected if any of these are true:

- out-of-sample Sharpe `< 0.75`
- out-of-sample expectancy `<= 0`
- out-of-sample profit factor `< 1.0`
- out-of-sample max drawdown `> 0.35`
- out-of-sample trades `< 10`
- overall trades `< 20`
- walk-forward stability fails

## Research Survivor

A run is a `research_survivor` only if all of these are true:

- out-of-sample Sharpe `>= 1.25`
- out-of-sample max drawdown `<= 0.20`
- out-of-sample profit factor `>= 1.15`
- out-of-sample trades `>= 12`
- overall trades `>= 24`
- walk-forward stability passes

## Paper Candidate

A run is a `paper_candidate` only if all of these are true:

- out-of-sample Sharpe `>= 1.75`
- out-of-sample max drawdown `<= 0.12`
- out-of-sample profit factor `>= 1.30`
- out-of-sample trades `>= 20`
- overall trades `>= 40`
- walk-forward stability passes

## Why these gates exist

These gates are designed for systematic automatic trading from a risk-adjusted return perspective:

- Sharpe remains the primary quality signal
- profitability must survive costs
- sample size must be large enough to matter
- walk-forward stability blocks brittle one-period winners
- drawdown limits prevent promotion of unstable parameter sets
