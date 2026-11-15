# Strategy Review Questions

Use these questions with another LLM that has access to the full source material of the strategy you want to adopt.

## Instructions

Answer only these questions. Be concrete and detailed. Tie every answer to the source strategy definitions, not generic trading advice.

## Questions

1. For this strategy, which 3 to 5 state variables are most likely missing, over-constrained, or incorrectly translated into our current executable rules, such that the strategy loses its real edge when turned into a backtest engine?

2. For this strategy, which parameter families should actually control behavior in a meaningful way?
   Focus on parameters that should change trade frequency, setup quality, and regime selectivity.
   Reject cosmetic parameters that only rename thresholds without changing the strategy thesis.

3. For this strategy, what are the minimum valid execution conditions that must be preserved from the source?
   Answer in strict rule form.
   Distinguish between:
   - mandatory structural conditions
   - optional filters
   - optimization knobs

4. Given the source material, is this strategy best represented in StrategyLab as:
   - a white-box coded family
   - a hybrid coded family with LLM-assisted parameter evolution
   - or a schema-defined strategy language that could realistically be expressed in JSON
   Explain the boundary between what can stay declarative and what still requires engine code.
   - below you can read the difference between a white-box and a black-box to respond this answer.

## Expected Output Format

For this strategy:

- `edge thesis`
- `likely mistranslated rules`
- `parameters that should matter`
- `minimum executable rule set`
- `recommended representation in StrategyLab`
