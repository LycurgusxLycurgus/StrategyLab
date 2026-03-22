# White-Box and Black-Box Perspectives

## Purpose

This file extracts the two modeling perspectives from the original StrategyLab query and turns them into a reusable canon for strategy design, evaluation, and future LLM review.

## White-Box Perspective

### Identity

This is the Dalio-like or systematic macro / interpretable econometric perspective.

### Core belief

Markets are not only noise. They also express causal structures, recurring regimes, incentive shifts, liquidity constraints, and macro relationships that can be described explicitly.

### What a white-box strategy should look like

- Clear causal story or explicit structural hypothesis
- Interpretable state transitions
- Rules that can be inspected bar by bar
- Parameters that map to real concepts, not arbitrary hidden features
- Failure modes that can be explained after a run

### Typical building blocks

- Regime classification
- Market structure
- Range / trend / breakout states
- Liquidity pools
- Order flow proxies
- Killzones / session filters
- Circuit breakers
- Econometric features
- Hidden Markov Models for regime inference

### Strengths

- Easier to debug
- Easier to improve through conjecture and refutation
- Easier to explain why a strategy failed
- Better aligned with graveyard-style postmortems

### Weaknesses

- Can become too rigid
- Can miss weak statistical edges
- Can overfit the story instead of the data if not disciplined

### StrategyLab implication

White-box strategies should be first-class citizens in this app. They fit the current architecture well because the engine logic, parameters, and graveyard explanations are all inspectable.

## Black-Box Perspective

### Identity

This is the Simons-like or pure-quant / statistical pattern extraction perspective.

### Core belief

Interpretability is optional. What matters is whether a model repeatedly extracts risk-adjusted returns from patterns in data.

### What a black-box strategy should look like

- Predictive or ranking model with measurable edge
- Strong validation discipline
- Walk-forward testing
- Regime adaptation if possible
- Model selection based on objective metrics, not intuition

### Typical building blocks

- Ensembles
- Sequence models
- Deep learning
- latent-state inference
- execution policies
- statistical arbitrage features
- reinforcement learning for execution

### Strengths

- Can capture subtle nonlinear patterns
- Can use broader feature spaces
- Can outperform hand-built rules when data and validation are strong

### Weaknesses

- Harder to debug
- Harder to know why performance changed
- Requires stronger data, validation, and model lifecycle tooling
- Much easier to fool yourself with leakage or overfitting

### StrategyLab implication

The current app is not yet a true black-box research platform. It lacks feature stores, train/validation pipelines, model artifacts, inference lifecycle, and leakage defenses. Right now the app is much closer to a white-box and hybrid strategy lab.

## Hybrid Perspective

### Identity

A practical middle ground: explicit structure plus statistical filters.

### Example

- White-box entry zones, but thresholds calibrated statistically
- Explicit market structure, but regime classification assisted by probabilistic models
- Rule-based engine with ML-based ranking or parameter proposal

### StrategyLab implication

This is the strongest next step for the app. It preserves interpretability while allowing LLM- or model-assisted iteration.

## What This Means for Strategy Creation

### Current reality

Today, a new executable strategy still requires code because each family is backed by engine logic in Python. A manifest alone can vary parameters and metadata, but it cannot define a wholly new executable engine.

### What JSON can do today

- Define metadata
- Define parameter defaults
- Define optimization grids
- Define compatibility constraints
- Define class type and description

### What JSON cannot do today

- Define a novel execution engine
- Create a new indicator pipeline
- Create new state transition logic
- Introduce new entry / exit semantics without code

## Recommended Direction

### Near-term default

Treat StrategyLab as a white-box / hybrid strategy evaluation and iteration system.

### Near-term loop

1. Run a strategy family across an approved parameter grid.
2. Evaluate all variants under a strict verdict criterion.
3. Preserve losers in the graveyard.
4. Ask an LLM to explain patterns in winners vs losers.
5. Use those explanations to propose:
   - better parameter ranges
   - rule changes
   - a new coded family if the hypothesis requires new logic

### Longer-term upgrade

If you want true black-box strategy creation, add a second track later:

- feature pipeline
- training jobs
- train / validation / test separation
- model artifacts
- inference contracts
- drift and leakage checks

That is a different product tier from the current monolithic rule-engine app.

## LLM Role Across All Strategy Types

LLMs should not be treated as isolated chatbots that see only one failed run. In StrategyLab they should be context-aware review agents that inspect:

- the app role
- the family manifest
- the latest family sweep results
- the graveyard artifacts
- the verdict criteria
- the white-box / black-box canon
- the original strategy source and query context

### White-box families

LLMs should propose:

- parameter-grid changes
- detector threshold changes
- safer execution or exit refinements
- explanations of why specific parameter regions fail

### Hybrid families

LLMs should propose:

- which white-box states deserve scoring
- which regime filters should be added
- which meta-model features should sit on top of the family

### Black-box families

LLMs should not pretend to explain hidden weights directly. Instead they should examine:

- feature definitions
- validation splits
- regime segmentation
- error clusters
- calibration drift
- whether the family is learning anything stable enough to justify promotion

For black-box families, the LLM role is to generate explanation-based conjectures about training setup, feature space, and selection pressure, not to hallucinate causal certainty about the model internals.
