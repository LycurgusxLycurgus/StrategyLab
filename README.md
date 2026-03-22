# StrategyLab

Local-first strategy research lab for deterministic backtests, evaluation, rejection, and optimization of strategy families.

## Run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Test

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
```

## Research Criteria

Verdict criteria for `rejected`, `research_survivor`, and `paper_candidate` runs live in [agents/docs/verdict_criteria.md](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/docs/verdict_criteria.md).
