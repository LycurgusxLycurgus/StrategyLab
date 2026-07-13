# Mutation Lab

Mutation Lab is a whitebox-first strategy creation, porting, qualification, and mutation workbench. TradingView is the canonical proving ground for chart-based strategies. Mutation Lab receives only a frozen Pine strategy that has passed a strategy-specific checklist and explicit manual user acceptance.

## Lifecycle

1. Define the strategy, research Pine mechanisms and public precedents, and create the Phase 1 criteria/checklist.
2. Create or adapt the Pine strategy and pass screenshot-heavy manual TradingView review.
3. Port the accepted Pine strategy to Mutation Lab Python and prove criterion-level parity.
4. Review fidelity quickly, run the faithful baseline, and perform authorized baseline optimization.
5. Diagnose and test evidence-derived whitebox mutations.
6. Add a bounded hybrid layer only when whitebox work is exhausted and live-engine reproduction succeeds.
7. Use constrained viability discovery or successor reseeding only when the completed lineage justifies it.
8. Complete robustness, execution-feasibility, forward-paper, and operational gates before production claims.

Greenfield Pine and licensed source adaptation are equal creation routes. The route is selected by evidence. Existing strategy families remain available until the user explicitly requests removal.

## Phase Prompts

- `agents/translation and generation/whitebox/01_translation.md`
- `agents/translation and generation/whitebox/01-5_baseline_transformation.md`
- `agents/translation and generation/whitebox/02_baseline.md`
- `agents/translation and generation/whitebox/02-5_baseline_qualification.md`
- `agents/translation and generation/whitebox/03-1_whitebox_diagnostics.md`
- `agents/translation and generation/whitebox/03_full-whitebox.md`
- `agents/translation and generation/whitebox/04-1_hybrid_diagnostics.md`
- `agents/translation and generation/whitebox/04_hybrid-blackbox.md`
- `agents/translation and generation/whitebox/04-2_blackbox_viability.md`
- `agents/translation and generation/whitebox/04-3_successor_baseline.md`
- `agents/docs/universal_mutation_constitution.md`

The operator contract is `agents/translation and generation/agents/codex_phase_operator.md`.

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

- Strategy-development contracts: `artifacts/strategy-development/<strategy_id>/`
- Data: `artifacts/data/`
- Runs: `artifacts/runs/`
- Reports: `artifacts/reports/`
- Diagnostics and preview ledgers: `artifacts/diagnostics/`
- Original source and accepted Pine: `pre-strategies/`
