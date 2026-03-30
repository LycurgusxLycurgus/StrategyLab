# Strategy Evaluation Canon

## Metrics, Explanatory Framework, and Postplatonic Improvement Logic for White-Box, Black-Box, and Hybrid Strategies

---

## 1. Why This Document Exists

The codification canon explains how a strategy becomes executable. What it does not yet fully answer is how a strategy should be *judged*, how its strengths and defects should be *explained*, and how those explanations should guide the next iteration. This document exists to supply that missing layer.

A trading strategy is never only an algorithm. It is also a conjecture about reality. Sometimes that conjecture is explicit and structural, as in a white-box strategy that claims a breakout after range compression during a certain session has follow-through because liquidity is trapped and volatility is expanding. Sometimes that conjecture is mostly statistical, as in a black-box strategy that claims a certain feature manifold contains predictive information even if the human cannot narrate every internal pathway. Sometimes the conjecture is split between human-written structure and model-learned refinement, which is the hybrid case.

Because of that, valuation cannot be reduced to a single performance number. Sharpe ratio matters, but it is not enough. Explainability matters, but it is not enough either. A strategy must be judged simultaneously as a return-generating artifact, as a risk-bearing system, as an epistemic object, and as a candidate for future improvement. The same backtest can look excellent under one lens and deeply suspect under another. A strategy with a weaker Sharpe but a stronger explanatory core may deserve promotion over a more profitable but unstable artifact. A black-box model with good returns but obvious leakage risk is not a success. A beautiful white-box narrative with no robust edge is not a success either.

This document therefore introduces a unified evaluation framework in which every strategy is valued along several layers at once: financial performance, robustness, implementation quality, epistemic quality, explanatory recoverability, and improvement potential. It also introduces a postplatonic lens for strategy evaluation. In that lens, a strategy is treated not as a dogma to be justified, but as a provisional conjecture exposed to refutation. Metrics do not exist merely to certify a winner. They exist to locate where reality is resisting the conjecture, where the conjecture remains promising, and what kind of mutation the next version should undergo.

The result is a framework that does four things at once. It tells you whether a strategy is worth keeping. It tells you why it performed as it did. It tells you which kind of strategy it really is from an epistemic point of view. And it tells you what the next iteration should try.

---

## 2. The Core Idea: Strategy Evaluation as Conjecture Testing

The usual language of strategy evaluation is too narrow. It speaks as if the strategy were merely a numerical object and as if the evaluator's job were simply to maximize a metric. That language is insufficient for a serious research system because it collapses together several different questions that should be kept distinct.

The first question is whether the strategy made money after realistic costs. The second is whether its behavior is robust across time, assets, and parameter neighborhoods. The third is whether its internal logic, whether explicit or learned, is coherent enough to be improved rather than merely replaced. The fourth is whether its success can survive critical pressure from rival explanations such as leakage, accidental overfitting, regime luck, structural break, or implementation artifact. The fifth is whether the strategy teaches the lab something reusable even if it is ultimately rejected.

From a postplatonic perspective, these questions belong together because a strategy is a provisional explanatory construction. The white-box strategy advances a more explicit explanation. The black-box strategy advances a more implicit explanation encoded in the behavior of the model. The hybrid strategy advances a layered explanation in which some causes are stated directly and others are inferred statistically. In every case, the strategy should be treated as a conjecture competing against refutations.

This means the evaluation loop should be understood in six movements. First, the strategy states or implies an edge hypothesis. Second, it is instantiated in code and parameters. Third, it is exposed to reality through backtesting, walk-forward testing, and implementation constraints. Fourth, the observed results are compared against rival explanations of success and failure. Fifth, an explanatory verdict is written. Sixth, the system proposes the next mutation.

In this framework, valuation is not only about ranking outputs. It is about improving the quality of conjectures. A good evaluation system is therefore not merely a scoreboard. It is a refutation engine and an explanation engine.

---

## 3. The Objects Being Evaluated

Although all strategies can be placed on the white-box to black-box spectrum, they should not be judged as if they were the same kind of object. The valuation framework has to respect what each box type is trying to do.

A white-box strategy is primarily an explicit explanatory machine. Its core merit lies in the fact that its state transitions, filters, thresholds, and failure modes can be inspected directly. Its evaluation therefore must give substantial weight to explanatory clarity, structural coherence, and postmortem recoverability, in addition to ordinary return metrics.

A black-box strategy is primarily a predictive extraction machine. Its merit lies in whether it repeatedly turns a feature space into risk-adjusted returns under strong validation discipline. Its evaluation therefore must give greater weight to out-of-sample performance, calibration, leakage resistance, regime durability, and lifecycle stability. It should not be punished merely for lacking line-by-line human-readable reasons, but it should be punished heavily for validation weakness or for signs that its gains are illusory.

A hybrid strategy is primarily a layered system. It claims that explicit structure can be improved by statistical refinement without collapsing into full opacity. Its evaluation must therefore judge not only performance and robustness, but also whether the boundary between explicit and learned components is well chosen. A hybrid can fail because the rule layer is bad, because the model layer is bad, or because the interface between them is bad. The framework must be able to distinguish those cases.

This implies a first principle: there should be universal metrics that apply to all strategies, and box-specific metrics that apply mainly to one family. Universal metrics allow comparison across the lab. Box-specific metrics preserve fairness.

---

## 4. The Six Layers of Valuation

Every strategy should be evaluated across six layers. These layers should not be collapsed into one number too early, because they answer different questions.

The first layer is **economic performance**. This asks whether the strategy creates sufficiently attractive returns after realistic assumptions. It includes expectancy, Sharpe ratio, Sortino ratio, Calmar ratio, profit factor, return on capital, turnover-adjusted return, and capacity-aware return if relevant.

The second layer is **risk and survivability**. This asks whether the strategy remains tolerable while producing those returns. It includes maximum drawdown, average drawdown, drawdown duration, tail loss behavior, skew, exposure concentration, leverage stress, correlation-to-book, and kill-switch dependence.

The third layer is **robustness**. This asks whether the strategy is a fragile local accident or a durable pattern. It includes out-of-sample persistence, walk-forward stability, parameter neighborhood stability, sensitivity to transaction costs, sensitivity to slippage, sensitivity to execution delay, and cross-regime performance dispersion.

The fourth layer is **implementation integrity**. This asks whether the strategy is operationally real rather than fictional. It includes leakage checks, timestamp integrity, fill realism, data sufficiency, survivorship-bias control, lookahead resistance, train/validation/test separation, inference reproducibility, and model artifact versioning where applicable.

The fifth layer is **epistemic quality**. This asks whether the strategy is a good conjecture rather than a merely lucky artifact. It includes edge explicitness, causal plausibility, rival-explanation resistance, explanatory recoverability, graveyard usefulness, and mutation clarity. This is where the postplatonic dimension enters most strongly.

The sixth layer is **improvement potential**. This asks whether the strategy teaches the lab where to go next. It includes failure localization, modularity of defects, availability of meaningful mutation directions, feature gap detectability, and whether the strategy belongs in the graveyard as a dead end or in the incubator as a near-miss.

A mature research system should write a verdict for each layer before writing a final promotion decision.

---

## 5. Universal Quantitative Metrics

The first responsibility of the framework is to preserve metric seriousness. No strategy should be protected from ordinary numerical pressure merely because its story is elegant. At the same time, metrics must be interpreted in context rather than fetishized in isolation.

### 5.1 Return and efficiency metrics

At the most basic level, every strategy should report net return, annualized return, volatility, Sharpe ratio, Sortino ratio, Calmar ratio, profit factor, expectancy per trade, average win, average loss, hit rate, turnover, average holding period, and return per unit of gross exposure. These numbers form the base surface of comparison.

Sharpe ratio remains a central summary because it compresses risk-adjusted performance into a tractable quantity. Yet it should not be treated as a sovereign number. A medium-frequency strategy with a strong Sharpe but brutal tail clustering may still be inferior to a somewhat lower-Sharpe strategy with shallower drawdowns and stronger robustness. Expectancy should therefore always be read alongside trade count, turnover, and cost sensitivity. A strategy that survives only under generous execution assumptions has not demonstrated real expectancy.

For systems that trade infrequently, return per trade and return per unit of time should both be shown. For portfolio strategies, marginal Sharpe contribution and correlation-to-book should be reported, because a good standalone strategy can still be a poor addition to the broader system.

### 5.2 Risk and damage metrics

Risk metrics should not be reduced to a single maximum drawdown number. A strategy can show a moderate maximum drawdown while still being psychologically and operationally unbearable because it spends too long underwater or because losses arrive in hostile clusters.

The framework should therefore include maximum drawdown, median drawdown, average drawdown depth, drawdown duration, time-to-recovery, worst week, worst month, downside deviation, left-tail percentile loss, and loss streak statistics. Tail metrics should be reported both in absolute and volatility-normalized terms. A strategy that appears acceptable at low volatility but explodes during volatility expansion is structurally weaker than headline performance suggests.

### 5.3 Robustness metrics

Robustness metrics are what separate a plausible edge from a localized historical accident. Every strategy should be exposed to at least three kinds of robustness stress.

The first is temporal stress. Performance should be segmented into in-sample, validation, test, and walk-forward periods. The key quantity here is not merely whether the strategy remains profitable, but how badly its distribution of returns deteriorates after each boundary crossing.

The second is perturbation stress. Costs, slippage, delays, and missed fills should be worsened gradually to observe the slope of degradation. A genuine edge may weaken under harsher assumptions but should not immediately evaporate. If a tiny increase in friction collapses the strategy, the edge is operationally fragile.

The third is parameter stress. Small neighboring parameter values should be tested around the chosen configuration. If the chosen point is surrounded by similar results, the strategy likely sits on a broad plateau. If it is surrounded by collapse, then the system has located a needle rather than a durable structure. Plateau width is therefore a crucial robustness metric.

### 5.4 Box-agnostic structural metrics

Some metrics apply regardless of whether the strategy is white-box or black-box because they describe the outer shape of behavior. These include trade frequency stability, directional balance, asset concentration, time-of-day concentration, regime concentration, and dependency concentration. A strategy that earns all its profits from one specific quarter, one instrument, or one narrow volatility environment may still be useful, but its description should reflect that narrowness.

---

## 6. The Postplatonic Epistemic Layer

The previous section dealt with numbers that most systematic shops would recognize. The postplatonic layer adds a different demand. It asks not only whether the strategy works, but what kind of explanation it embodies and how it should be treated in a conjecture-refutation culture.

In this view, the central mistake is justificationalism. A strategy is not promoted because one has found enough reasons to feel comfortable with it. It is promoted only provisionally, because it has survived a sufficiently strong battery of refutations relative to the alternatives. Likewise, a strategy is not rejected merely because it failed. It is rejected because the best available explanation of its failure leaves too little reason to keep mutating that line, or because its failure teaches that the conjecture is currently weaker than rivals.

This leads to several epistemic metrics that ordinary quant dashboards rarely formalize.

### 6.1 Edge explicitness

Edge explicitness measures how clearly the strategy states what it believes the market is doing. For a white-box strategy, this asks whether the rule system corresponds to an articulated hypothesis such as trend continuation under expansion, liquidity reversion after exhaustion, or cross-asset repricing under macro surprise. For a black-box strategy, it asks whether the team can at least state the target relation, the data domain, and the nature of the prediction problem with clarity, even if the internal mapping remains opaque. For a hybrid strategy, it asks whether the explicit and learned layers each have a clear function.

Low edge explicitness does not automatically disqualify a strategy, especially in black-box work, but it reduces the explanatory leverage of results. A profitable but poorly framed system teaches the lab less than a similarly profitable system whose conjecture surface is clear.

### 6.2 Causal or structural plausibility

This metric asks whether the strategy's core idea has a credible relation to market structure, incentives, behavior, flow, or statistical mechanism. It does not demand certainty, and it does not require naive storytelling. Rather, it asks whether the conjecture is at least anchored in something more disciplined than post hoc pattern worship.

A white-box strategy that claims to exploit session-based liquidity dynamics may score high here if its assumptions correspond to known market behavior. A black-box feature set may also score high if the features plausibly relate to order flow, volatility transitions, or cross-sectional mispricing, even if the exact learned mapping is opaque. A model built on arbitrary, semantically empty correlations should score poorly even if backtests look good, because its main rival explanation is likely accidental fit.

### 6.3 Rival-explanation resistance

This is one of the most important epistemic metrics in the entire framework. It asks how well the apparent success survives alternative explanations. The main rivals are usually leakage, overfitting, regime luck, execution fantasy, hidden concentration, silent data revisions, and narrative overinterpretation.

A strategy scores well when the evaluation process has actively tried to kill it with these rivals and failed. In other words, the strategy is not strong because its own story sounds persuasive. It is strong because the main non-edge explanations have been critically weakened.

### 6.4 Explanatory recoverability

Explanatory recoverability asks how well a postmortem can reconstruct the logic of a run. In a white-box strategy, this should be very high. One should be able to say which state transition fired, which filter passed, which parameter mattered, and which exit logic ended the trade. In a black-box strategy, recoverability does not mean pretending to read hidden weights like transparent rules. It means being able to recover enough of the surrounding explanation to diagnose behavior: which feature families dominated, where calibration drift emerged, which regimes failed, whether rank-order power weakened, and whether errors clustered around specific contexts. In a hybrid strategy, the evaluator should be able to attribute failure to the rule layer, the model layer, or the handoff between them.

### 6.5 Mutation clarity

Mutation clarity measures whether the evaluation outcome points toward intelligible next moves. Some failed strategies fail in a fertile way. Their defects are localized, their edge seems partially real, and the next mutation is obvious. Other strategies fail in a dead way. Everything is diffuse, nothing localizes, and any proposed improvement would be mere random churn.

A good research system should privilege strategies with high mutation clarity, because they convert failure into knowledge rather than into noise.

### 6.6 Graveyard value

Not every failed strategy is equally valuable in the graveyard. A graveyard-worthy strategy is one whose failure teaches a transferable lesson. Perhaps it reveals that a certain regime classifier is too slow, that a particular feature family leaks future information, or that a certain class of session breakout logic is too friction-sensitive. A failed strategy with high graveyard value improves the lab even in defeat.

---

## 7. Box-Specific Metrics

Universal metrics create comparability, but serious valuation requires metrics tailored to the epistemic type of the strategy.

### 7.1 White-box metrics

A white-box strategy should be judged partly by performance and robustness, but also by the quality of its explicit explanation. The first white-box-specific metric is **state coherence**. This asks whether the strategy's state machine genuinely reflects a meaningful progression rather than a pile of ad hoc gates. Good white-box systems have states that correspond to distinct market situations and transitions that reflect real changes rather than arbitrary clutter.

The second metric is **semantic parameter integrity**. White-box parameters should map to real concepts. A stop defined as a volatility multiple near an invalidation level has higher semantic integrity than an unexplained integer chosen because it optimized well. A white-box strategy whose parameters no longer mean anything has drifted toward pseudo-interpretability.

The third metric is **bar-by-bar explainability density**. This measures how often a trade and its non-trades can be narrated precisely. A strong white-box system should let the evaluator answer not only why a trade happened, but also why other apparent opportunities were rejected.

The fourth metric is **postmortem precision**. After a bad period, can the system point to which filters, which regimes, which transitions, or which exit rules failed? If not, then its white-box claim is weaker than it appears.

The fifth metric is **story-discipline ratio**. White-box strategies often fail by becoming ornate stories disguised as rules. This ratio asks whether the narrative complexity is justified by robust incremental performance. A highly elaborate rule tree that adds little beyond a simpler version is epistemically suspicious.

### 7.2 Black-box metrics

A black-box strategy should be judged less by human readability and more by scientific discipline. The first black-box-specific metric is **validation hardness**. This measures how severe the train/validation/test and walk-forward regime really was. Easy validation should count for little. Hard validation should count for much.

The second metric is **calibration quality**. If the model outputs probabilities or scores, these should bear a stable relation to realized outcomes. A model with decent returns but broken calibration is harder to govern and harder to improve.

The third metric is **feature legitimacy**. This asks whether the feature space is economically or operationally defensible, timestamp-correct, and free from obvious leakage pathways. It is possible for the model internals to be opaque while the input universe remains highly disciplined.

The fourth metric is **error-cluster intelligibility**. Even if the exact internal path is not visible, the evaluator should still be able to observe where errors accumulate. Do failures cluster in volatility transitions, macro event windows, low-liquidity conditions, or structural breaks? A black-box strategy becomes much more usable when its error surface is intelligible.

The fifth metric is **lifecycle stability**. This includes drift rate, retraining dependence, feature-distribution shift resistance, and model replacement turnover. A strategy that only works under constant retraining with large instability is epistemically weaker than one with slower degradation and more stable ranking power.

### 7.3 Hybrid metrics

The hybrid system deserves its own metrics because its main danger lies in boundary confusion. The first metric is **boundary clarity**. This asks whether it is obvious what the rule layer is responsible for and what the model layer is responsible for. Without that clarity, hybrid evaluation degenerates into blame diffusion.

The second metric is **handoff quality**. This measures how well the explicit layer feeds the learned layer, or vice versa. A white-box candidate generator followed by a black-box ranker should generate candidates rich enough for the model to discriminate meaningfully. An ML regime classifier feeding rule-based execution should create regime labels that the rules can actually use.

The third metric is **layer contribution separability**. This asks whether one can measure the marginal contribution of each layer. A hybrid should be testable in versions such as rule-only, model-only where meaningful, and full combination. If the evaluator cannot tell which layer adds value, the architecture is too entangled.

The fourth metric is **interpretability preservation**. A hybrid exists partly to gain statistical power without surrendering explanatory grip. If the added model layer destroys almost all postmortem clarity while contributing little robust performance, then the hybrid move was not worth it.

---

## 8. From Metrics to Verdicts: The Explanatory Framework

Metrics alone do not yet give a usable research verdict. They must be organized into an explanatory narrative. The framework therefore needs a standardized way of turning observations into judgments.

Every strategy review should culminate in five explanatory paragraphs.

The first paragraph is the **edge statement**. It should say, in disciplined language, what the strategy appears to be exploiting. In the white-box case this can often mirror the original hypothesis, perhaps refined by the data. In the black-box case it may speak in terms of feature families and predictive context rather than exact rules. In the hybrid case it should describe how the explicit and learned parts cooperate.

The second paragraph is the **survival statement**. This should explain where the strategy held up: across which periods, which regimes, which cost assumptions, and which perturbations. It is here that the evaluator says whether the strategy survived serious pressure or merely friendly conditions.

The third paragraph is the **failure statement**. This should explain where and how the strategy broke. Strong reviews do not say only that performance declined. They specify whether decline came from edge decay, execution friction, parameter fragility, misclassification, model drift, crowding, or something else.

The fourth paragraph is the **rival-explanation statement**. This paragraph explicitly names the strongest rival explanations for the observed results and explains which of them remain plausible after the tests. This step is crucial because it prevents premature triumph. A strategy with impressive performance but unresolved leakage suspicion must be written differently from one that survived leakage scrutiny.

The fifth paragraph is the **mutation statement**. This explains what the next version should do. It should not be generic. It should say whether to widen a plateau search, simplify a rule family, split by regime, replace a feature domain, recalibrate thresholds, isolate a failing state, or bury the line entirely.

These five paragraphs turn evaluation into a disciplined explanatory act rather than a mere ranking exercise.

---

## 9. A Unified Scoring System

Although the framework should preserve separate layers, the lab still needs a portable scoring scheme for promotion, triage, and graveyard routing. The scoring system should therefore combine quantitative seriousness with epistemic seriousness.

A useful approach is to score each strategy on a 0-5 scale across the six valuation layers introduced earlier, then produce both a total and a profile. The total gives ranking convenience, while the profile preserves meaning.

### 9.1 Economic performance

A score of 0 indicates no real edge after costs or a clearly negative expectancy. A score of 1 indicates weak and unstable profitability. A score of 2 indicates marginal profitability with notable caveats. A score of 3 indicates respectable profitability with credible but imperfect support. A score of 4 indicates strong net performance sustained under realistic assumptions. A score of 5 indicates exceptional performance that also survives hard stress and capacity review.

### 9.2 Risk and survivability

A score of 0 indicates intolerable drawdown, tail risk, or concentration. A score of 3 indicates a survivable but imperfect profile. A score of 5 indicates controlled downside, acceptable recovery time, and good behavior under stress.

### 9.3 Robustness

A score of 0 indicates collapse outside the friendly slice or violent sensitivity to small perturbations. A score of 3 indicates partial persistence but meaningful fragility. A score of 5 indicates broad plateau behavior, realistic friction tolerance, and durable out-of-sample survival.

### 9.4 Implementation integrity

A score of 0 indicates major leakage or realism defects. A score of 3 indicates competent but incomplete discipline. A score of 5 indicates strong timestamp hygiene, realistic fills, clear validation boundaries, and reproducible execution.

### 9.5 Epistemic quality

A score of 0 indicates a muddled conjecture, weak rival-explanation resistance, and poor postmortem value. A score of 3 indicates a respectable conjecture with meaningful but incomplete explanatory strength. A score of 5 indicates high edge clarity, strong recoverability, strong refutation pressure survived, and excellent graveyard or mutation value.

### 9.6 Improvement potential

A score of 0 indicates a dead end or pure noise. A score of 3 indicates a mixed but still informative line. A score of 5 indicates a very fertile research object whose next mutations are clear and promising.

The total score is useful, but the profile matters more. Two strategies with the same total may deserve very different treatment. One may be promotable now. Another may be non-promotable but highly fertile for further research.

---

## 10. Promotion, Incubation, and Burial

The framework should not force every strategy into the same binary of pass or fail. There are at least four legitimate destinations.

The first is **promotion**. A promoted strategy has shown acceptable strength across performance, robustness, and implementation integrity, and it has no unresolved rival explanation severe enough to block deployment.

The second is **incubation**. An incubated strategy has not yet earned promotion, but it has enough epistemic strength and mutation clarity to justify another research cycle. Many good white-box and hybrid strategies will live here for a long time.

The third is **graveyard retention**. This is for failed strategies with high lesson value. They are not active candidates, but their artifacts, postmortems, and error clusters should remain searchable because they inform future conjectures.

The fourth is **burial** in the strict sense. This is for strategies whose failure is diffuse, low-information, and not worth further mutation. Their preservation cost should be minimal.

A postplatonic lab should resist the temptation to think that only promoted strategies matter. Graveyard quality is part of research quality because the graveyard stores refutations. A lab that forgets its refutations will relearn them expensively.

---

## 11. The Improvement Logic by Box Type

The framework must not only judge strategies; it must tell the next iteration how to move.

### 11.1 Improving white-box strategies

White-box improvement should begin with localization. The evaluator should ask whether the weakness lives in context detection, setup logic, entry timing, exits, trade management, or position sizing. It should then ask whether the defect is conceptual or merely parametric. A conceptual defect means the story itself is weak, perhaps because the hypothesized market behavior is not actually present or is present only in a narrower regime. A parametric defect means the story may still be right but the thresholds, windows, or state boundaries are misaligned.

In white-box systems, the best mutations are usually simplifications, regime splits, or improved state definitions. Complexity should be added reluctantly. The default question should be whether one can *remove* a weak gate before adding a new one. Postplatonic discipline favors stronger explanations, not larger piles of exceptions.

### 11.2 Improving black-box strategies

Black-box improvement should begin with validation scrutiny before feature creativity. If a black-box strategy fails, the first suspicion should be that the evaluation or data regime was too weak, not that the model simply needs more sophistication. Once integrity is secured, the next questions concern target definition, feature domain quality, calibration, regime segmentation, sample sufficiency, and drift.

In black-box systems, the most valuable improvements often come from better target framing, better train-test discipline, and better feature legitimacy rather than from larger architectures. A more complex model is not automatically a deeper explanation; it is often a more efficient way of fooling oneself.

### 11.3 Improving hybrid strategies

Hybrid improvement should begin by isolating the layer where value is being created or destroyed. Does the rule layer produce meaningful candidates but the model reject poorly? Does the model classify regimes well but the rule layer fail to exploit them? Does the hybrid outperform the rule-only baseline but lose too much explainability in return? These are boundary questions.

The best hybrid mutations usually sharpen the division of labor. The explicit layer should own what humans can state clearly. The learned layer should own what is too subtle, high-dimensional, or unstable for hand-built rules. When a hybrid becomes messy, the remedy is often to make the border clearer, not to add another learned patch.

---

## 12. Failure Taxonomy

A serious evaluation framework should name failure types precisely, because improvement depends on the type of failure.

One class is **false edge failure**. The conjecture itself appears wrong. The pattern does not persist, or it never existed beyond noise.

Another is **fragility failure**. The edge may be real but too narrow to survive realistic friction, parameter perturbation, or small environmental changes.

Another is **translation failure**. The underlying idea may be sound, but the codification is poor. This is common when discretionary intuitions are translated into rigid rules too crudely.

Another is **regime failure**. The strategy works, but only in a limited state of the world that has not been sufficiently isolated.

Another is **implementation failure**. The apparent edge is contaminated by leakage, unrealistic fills, bad timestamps, or an invalid training pipeline.

Another is **governance failure**. The strategy may be profitable, but the system around it cannot monitor, explain, or safely operate it.

Every review should classify failure in these terms before proposing changes. Without failure taxonomy, mutations become random.

---

## 13. Suggested Review Template for StrategyLab

A strategy review inside the app should read like a disciplined research memo rather than a vague model summary. It should begin with the strategy identity, box type, version, and edge statement. It should then describe the test universe, validation regime, and implementation assumptions. After that it should report the six valuation layers in prose, not merely as a dashboard.

The review should then write the five explanatory paragraphs already introduced: edge, survival, failure, rival explanations, and mutation. Finally, it should assign the destination of promotion, incubation, graveyard retention, or burial.

The point of this structure is not bureaucracy. It is memory. Over time the lab accumulates not only runs but explanations of runs. Those explanations become part of the system's usable intelligence.

---

## 14. What the LLM Should Do Inside This Framework

An LLM operating inside StrategyLab should not behave like a cheerleader for recent winners. It should behave like a conjecture critic and mutation designer.

For white-box strategies, it should analyze which states, thresholds, and structural assumptions are pulling their weight, and which appear ornamental or brittle. It should propose simplifications when complexity outruns evidence. It should prefer explanations that increase postmortem clarity.

For black-box strategies, it should resist hallucinating access to hidden internals. Its job is not to fake mechanistic certainty. Its job is to examine feature legitimacy, validation hardness, calibration behavior, regime segmentation, error clusters, and drift patterns, then generate disciplined conjectures about what the model is or is not learning.

For hybrid strategies, it should examine whether the chosen border between explicit and learned logic is good. It should ask whether the rule layer is too weak, whether the model is compensating for bad structure, or whether the model layer adds only cosmetic gains at the cost of too much opacity.

Across all types, the LLM should write reviews in the language of provisionalism. It should avoid saying that the strategy is proven. It should say that the strategy has survived certain refutations, failed others, and therefore deserves a certain next move.

---

## 15. Final Principle

The deepest purpose of this framework is to prevent confusion between profitability, explanation, and knowledge. Profitability matters because the lab exists to produce viable strategies. Explanation matters because only explained systems can be improved intelligently. Knowledge matters because the lab should accumulate conjectures and refutations rather than merely churn through backtests.

A strategy is therefore best understood as a temporary settlement between market reality and human or model-generated explanation. White-box, black-box, and hybrid systems are simply different ways of constructing that settlement. The evaluation framework must be broad enough to judge all three honestly, and strict enough to refuse both empty stories and empty metrics.

The practical outcome is simple. Measure the strategy numerically. Attack it with rival explanations. Recover as much explanation as its box type honestly permits. Write the postmortem so that the next mutation becomes clearer. Then either promote it, incubate it, preserve it as a useful refutation, or bury it.

That is what it means to evaluate strategies in a postplatonic research lab.

---

## Appendix A. Compact Scorecard Schema

A compact schema can sit beside the prose review for sorting and filtering inside the app. The schema should never replace the explanation, but it can compress the decision surface.

`economic_performance: 0-5`

`risk_survivability: 0-5`

`robustness: 0-5`

`implementation_integrity: 0-5`

`epistemic_quality: 0-5`

`improvement_potential: 0-5`

`box_specific_bonus_or_penalty: -2 to +2`

`total_score: 0-32`

`destination: promote | incubate | graveyard | bury`

`primary_failure_type: false_edge | fragility | translation | regime | implementation | governance`

`mutation_priority: low | medium | high`

`review_confidence: low | medium | high`

---

## Appendix B. One-Sentence Definitions for the Most Important Meta-Metrics

**Explanatory recoverability** is the degree to which a run can be reconstructed into a useful postmortem without pretending to know more than the box type actually allows.

**Rival-explanation resistance** is the degree to which alternative non-edge explanations have been actively attacked and weakened.

**Mutation clarity** is the degree to which the evaluation points toward intelligible next modifications rather than random tinkering.

**Graveyard value** is the degree to which a failed strategy improves the lab's future reasoning.

**Validation hardness** is the severity and realism of the conditions under which a strategy was allowed to prove itself.

**Story-discipline ratio** is the proportion between explanatory complexity and robust incremental gain.

---

## Appendix C. Default Comparison Principle

When two strategies are close in headline performance, the framework should generally prefer the one with stronger robustness, stronger implementation integrity, and stronger epistemic quality. When one strategy clearly dominates economically and robustly, it may still lose priority if unresolved rival explanations remain severe. When a weaker strategy is far more explainable and mutationally fertile, it may deserve incubation over a superficially stronger but opaque and unstable rival.

The lab should therefore optimize not only for present Sharpe, but for durable explainability-adjusted research value.
