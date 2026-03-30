# Project Aurum

Project Aurum is a small Python-first research cockpit for a hybrid Smart Money Concepts workflow on XAUUSD 15-minute bars. The Python engine is the canonical source of truth for white-box logic, candidate generation, hybrid scoring, reports, webhook evaluation, and internal paper simulation.

The app intentionally keeps the operator flow narrow:

1. Download a 15-minute gold dataset from OANDA practice or import a HistData XAUUSD M1 file.
2. Run the white-box backtest baseline.
3. Train and evaluate the hybrid filter against the same candidate stream.
4. Simulate a paper week or evaluate a TradingView webhook against the latest model.

The valuation canon used by the app is summarized in [agents/docs/verdict_criteria.md](/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/docs/verdict_criteria.md). The deeper philosophical sources remain in [agents/docs/codification_boxes.md](/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/docs/codification_boxes.md), [agents/docs/metrics_boxes.md](/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/docs/metrics_boxes.md), and [agents/docs/white_black_boxes-perspectives.md](/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/docs/white_black_boxes-perspectives.md).

## Architecture

The implementation stays monolithic and vertical:

- `app/features/data`: dataset download, storage, and catalog
- `app/features/backtests`: canonical white-box engine, candidate dataset generation, hybrid evaluation
- `app/features/reports`: evaluation canon report writing
- `app/features/paper`: internal paper simulation
- `app/features/webhooks`: TradingView-style signal evaluation
- `app/ui`: vanilla operator shell
- `pine`: chart mirror artifact

## Run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Test

```powershell
python -m unittest discover -s app -p tests.py
```
