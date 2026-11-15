# Future decision-model and learned-strategy roadmap

Status: **PLAN ONLY — 2026-10-23.** No model integration, training, account creation, social collection, RL or order execution is authorized by this document. Implement only after the systematic workflow works and a later task explicitly authorizes the selected experiment. The active workflow is [the systematic operator](../translation%20and%20generation/agents/codex_phase_operator.md).

## Decisions and answers

Keep two product roads: explicit-rule systematic strategies now, and indicator-triggered decision-model strategies later. A discretionary source can also inspire a separate mechanical strategy in the active road. That is an adaptation/new hypothesis, not proof that the source trader's judgment was replicated.

Whitebox/blackbox is a useful description of **policy inspectability**, but is not a complete strategy taxonomy. A transparent indicator followed by an opaque decision model is a mixed architecture, not an end-to-end whitebox. A frozen learned policy can run systematically, even if it originated from discretionary ideas. Name the requested future road “discretionary-origin decision-model” and describe each component honestly.

ML and alternative/social data make sense as research hypotheses. They do not establish an edge, turn a retail bot into Citadel, or remove the need for execution engineering, capital/risk controls and independent evidence. This plan recommends beginning with a small matched comparison, not an institutional imitation project.

## Keep these axes separate

| Axis | Examples | Consequence |
| --- | --- | --- |
| Strategy origin | systematic-native, discretionary-origin, mixed components | Determines source interpretation and fidelity duties |
| Development operation | create, replicate, translate, improve | Determines baseline and transformation provenance |
| Decision governance | explicit rules, frozen model, human judgment, online adaptation | Determines reproducibility and permission boundaries |
| Policy interpretability | transparent rules, interpretable learned model, opaque model, mixed | Describes what can actually be inspected |
| Data | market, fundamentals, alternative/social | Determines availability, rights and leakage risks |
| Learning mode | none, offline supervised, offline RL, online learning | Determines experimental and change-control requirements |

A model's repeatable deployment is not the same as interpretable reasoning. A human-sounding explanation is not proof of a model's decision mechanism. Existing runtime origin values remain compatibility interfaces; this table is conceptual, not a new API schema.

## What CLEF establishes—and does not

Cloudflare describes Clef as a decision-model family that takes a state and typed questions and returns probabilities over permitted answers. This is a plausible interface for approve/reject/abstain or categorical setup assessment, rather than unconstrained trading instructions. [Official model documentation](https://developers.cloudflare.com/workers-ai/models/clef/)

The user's [RL interest page](https://www.cloudflare.com/resource/clef-rl-interest/) describes a service opportunity, not an installed trading component. The original announcement describes RL fine-tuning support/design partnerships; later family updates changed available capabilities. Verify current access, licensing, deployment options, data handling, price and version guarantees when implementation is authorized. Do not assume an interest registration grants a self-service RL pipeline. [Cloudflare launch](https://blog.cloudflare.com/clef-decision-models/), [official release](https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/), [later family update](https://blog.cloudflare.com/clef-faster-cheaper-multimodal/)

Inference: CLEF is a candidate decision interface, not a demonstrated trading advantage. Vendor benchmark latency and classification accuracy do not establish end-to-end trading latency, profitable decisions or calibrated probability of trade profit. Compare it with a simple explicit gate, a small supervised model and other suitable decision models before committing to new technology. RL is not a prerequisite for the first experiment.

## Road A: discretionary-origin decision-model experiment

### 1. Define what judgment must add

Choose one asset/venue/timeframe/direction and one discretionary methodology. Identify observable setups, contextual judgments and abstention reasons. Preserve original sources, licenses, expert examples and unresolved ambiguities. Obtain genuine expert labels if fidelity to expert behavior is claimed; distinguish those labels from hindsight profit labels.

Research the closest mechanical analogue as the control. If no expert evidence exists, evaluate a proposed model policy as a new hypothesis, not as a faithful discretionary replica.

### 2. Build the indicator before the model

Create a causal configurable indicator for the necessary primitives only: for example confirmed structure, liquidity sweeps, displacement and valid/expired FVGs. It must expose the timestamp when each fact becomes knowable, invalidations, state transitions and candidate setup identity. Test independent positive/negative cases and no-future-data behavior.

Candidate generation must be fixed before comparing decision policies. Model approval cannot repair an indicator whose historical events repaint or whose information was unavailable at decision time.

### 3. Proposed event and response contracts

These are **proposed experimental fields**, not implemented endpoints:

- Candidate event: setup ID, instrument/venue/timeframe/direction, event time, information-available time, data-ready time, indicator/code/settings version, allowed context snapshot, entry/exit/risk proposal, expiry and data-quality status.
- Decision request: candidate identity, immutable point-in-time snapshot, policy/model/prompt/schema version, allowed decisions, deadline and deterministic risk limits visible for context only.
- Decision response: matching setup ID, approve/reject/abstain, allowed direction, schema-constrained criterion results, confidence with defined meaning, response time, model/version identity and validation result.
- Audit record: input/output hashes, raw captured response under appropriate data retention, decision latency, validation/risk disposition, paper action or no-action reason, subsequent execution and outcome.

Do not let the model invent an unrestricted order, symbol, size or risk limit. Treat news/social text as untrusted data, not instructions. No broker secrets, trading tools or permission to change the risk gateway belong in model context.

### 4. Separate judgment from deterministic execution

```text
causal indicator -> valid candidate -> point-in-time snapshot
  -> model approve/reject/abstain before deadline
  -> schema, identity, freshness and permission checks
  -> deterministic risk gateway
  -> shadow / paper adapter only
```

Risk controls own sizing, exposure, loss ceilings, permissible markets, order legality, protective exits, cooldowns and kill switches. Invalid responses, missing data, expiry, timeout, unavailable model or unresolved reconciliation mean **no new entry**. Protective exits and position reconciliation remain active; abstention must not strand an existing position.

Duplicate/out-of-order events require idempotent handling. Approvals expire; a delayed approval cannot become a new entry on changed conditions. Fix concurrency and capital-allocation rules before comparing policies.

### 5. Compare under identical conditions

Use the same candidate universe, information snapshots, market windows, costs, execution/risk constraints and latency accounting for:

1. Mechanical analogue/full explicit strategy.
2. Indicator plus simplest explicit accept/reject gate.
3. Indicator plus small supervised decision policy where legitimate labels exist.
4. Indicator plus proposed decision model.

Compare selection/abstention, net return, drawdown, turnover, rejected/late decisions, coverage, compute cost and uncertainty. A no-filter control and relevant removed-context ablations test whether model judgment adds anything. Predeclare selection budgets and chronological partitions; keep final holdout and forward evidence separate. All viewed windows and prompt/model variations enter the trial ledger.

Historical foundation-model evaluation risks knowledge contamination: the model may know later prices/events from training even when the input snapshot is causal. Prefer genuinely forward captured decisions; document cutoff uncertainty and never call prompt-only historical replay uncontaminated proof. Capture responses and replay those for execution tests rather than assuming repeat calls reproduce decisions.

Confidence means whatever the model was trained/calibrated to predict; it is not automatically P(profitable trade). Calibrate on untouched eligible evidence before using it for thresholds or sizing. In the first experiment, keep sizing deterministic and independent of confidence.

### 6. Verify latency, versions and failure behavior

Measure the whole path—data arrival, indicator computation, queue/network/model, validation and adapter—not vendor inference alone. Predeclare deadlines appropriate to the strategy; very low latency remains unproven until measured. Include service/data/compute costs and rate/outage limits.

Freeze model weights or provider version where available, prompt, schema, sampling settings and indicator code. If a provider cannot guarantee identity, record that uncertainty and require fresh acceptance on material changes. Test timeouts, stale events, malformed answers, duplicate approvals, reconnects and drift in shadow before paper.

### 7. Later learning milestones

First establish whether a frozen model beats simpler controls forward. Only then consider supervised adaptation or offline RL with a separate authorization and plan. RL needs defensible state/action/reward definitions, realistic delayed costs/fills, offline policy evaluation and protection against reward leakage or simulator exploitation. No live exploration, autonomous risk-limit changes or online self-modification is authorized. Online learning is a separate governance decision, not an automatic next step.

Milestones: accepted causal indicator -> matched offline experiment with limitations -> forward shadow -> paper reconciliation -> independent evidence review. Failure at a milestone stops or returns to its owning hypothesis; it does not automatically justify a larger model.

## Road B: learned/blackbox and social-data research

### Does it make sense?

Yes, as a disciplined experimental road. Citadel itself describes alternative-data research using statistical and AI/ML methods in collaboration with investment teams. That supports the legitimacy of the research category, not access to its proprietary methods or evidence that a social bot replicates its performance. [Citadel's account of its data research](https://www.citadel.com/careers/career-perspectives/real-people-real-impact-how-alternative-data-powers-investment-decisions-at-citadel/)

Social information may be inaccurate, incomplete, stale or manipulated. A collection bot is an ingestion component, not an alpha strategy. Do not use social sentiment as sole investment evidence. [FINRA/SEC investor bulletin](https://www.finra.org/investors/insights/social-sentiment-investing-tools)

Inference: pursue a narrow falsifiable information-advantage hypothesis, such as whether a specified timely signal improves a fixed baseline after delay and costs. Do not start with “build Citadel,” generic market prediction or a giant unbounded scraping/model search.

### Minimum future experiment

1. Define target, horizon, event universe, baseline, economic mechanism and legally available data. Verify licensing/terms, privacy, retention and redistribution before collection; no new collectors/accounts are implemented here.
2. Store publication, ingestion, revision and usable-at times. Handle deletions, edits, reposts, bot activity, duplicate stories and missing/outage periods. Backfilled sentiment scores are not point-in-time evidence by default.
3. Build an as-of dataset, causal labels, chronological splits and overlap purging where applicable. Prevent survivorship bias, future revisions and entity/universe leakage. Include acquisition, inference, execution and funding costs.
4. Start with interpretable features and simple regularized baselines. Add opaque models only for a concrete question with comparable budgets. Record all datasets/features/models/searches and failed trials.
5. Test incremental value beyond market-only controls; run ablations, cost/delay stress, drift and coverage analysis, reserved evaluation and forward shadow. Repeated backtests can produce false discoveries; a holdout alone is not a cure for unlimited selection. [Bailey et al., primary backtest-overfitting paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
6. Require a causal engine/policy adapter, deterministic risk gateway, reproducible versioning and paper reconciliation before any graduation consideration. Regulatory/venue feasibility and separately authorized live review remain necessary.

## Boundary with the active six phases

The systematic lifecycle can research mechanical analogues of discretionary sources now. It does not require model judgment, RL or alternative-data infrastructure. Future authorized learned components would still owe the same semantic/data/execution/economic and forward evidence, plus model-specific requirements above; “blackbox” is not an exemption.

For BTCUSDT 5m, Turtle Soup with confirmed sweeps, BOS/displacement/retest and sweep+MSS/FVG retest remain research candidates. Simplicity or resemblance to SMC is not a demonstrated profitability ranking. No strategy is promoted, trained or executed by this roadmap.

