# Mutation Lab

Mutation Lab is a white-box-first strategy mutation workbench for repeatable parent -> single-mutation -> comparison -> promotion loops. It starts from a frozen baseline, downloads real data, generates one-step mutations from the canonical mutation space, and persists every run with report artifacts.

## Core Flow

1. Freeze or register a baseline parent.
2. Download at least `40000` real bars for the target asset and timeframe.
3. Run the promoted parent.
4. Tune one or more live parameters around the current parent.
5. Run a preview without saving.
6. Save only the tuned children that deserve to become real versions.
7. Compare metrics and promote only real winners.

## Seed Family

- Family id: `btc_intraday`
- Seed source: [pre-strategies/BTC-intraday.txt](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/pre-strategies/BTC-intraday.txt)
- Canonical spec: [strategies/btc_intraday_parent.json](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/strategies/btc_intraday_parent.json)

## Prompts

The mutation engine prompt set lives in:
- [01_translation.md](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/translation%20and%20generation/whitebox/01_translation.md)
- [02_baseline.md](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/translation%20and%20generation/whitebox/02_baseline.md)
- [03_full-whitebox.md](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/translation%20and%20generation/whitebox/03_full-whitebox.md)
- [04_hybrid-blackbox.md](C:/Users/Baham/Documents/pre-nexuz/memecorp&starfish/markov_dove-red/StrategyLab/agents/translation%20and%20generation/whitebox/04_hybrid-blackbox.md)

Prompt `03` now assumes one freeform research packet and derives the next white-box mutation from the winning baseline and evidence. Prompt `04` now assumes one surviving white-box parent and derives the first hybrid mutation from that parent’s remaining weakness without canned examples.

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

## Artifacts

Generated runtime artifacts are written to:
- `artifacts/data`
- `artifacts/runs`
- `artifacts/reports`
