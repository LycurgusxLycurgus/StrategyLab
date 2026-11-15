I put the full buildout into canvas as **“Project Aurum Execution Plan For Codex.”**

# Project Aurum Execution Plan for Codex

## Hybrid SMC XAUUSD 15m: Backtesting App, Paper-Trading Harness, and Evaluation Pipeline

## 1. What We Are Building

The goal is not to build a giant platform on day one. The goal is to build the smallest serious research system that can do four things correctly.

First, it must express the white-box Smart Money logic in a way that is inspectable, testable, and reproducible outside TradingView. Second, it must allow a black-box confirmation layer to score those white-box setups without contaminating the backtest with leakage. Third, it must produce a research-grade report using the Strategy Evaluation Canon, so the output is not merely profit and loss but also explanatory recoverability, handoff quality, and robustness. Fourth, it must be capable of running for at least one week in paper mode so that the exact same strategy logic can be observed under live incoming data.

That means the first serious version should be designed around a Python source of truth. TradingView is still useful, but not as the canonical engine. TradingView should be used for visual parity, operator visibility, and webhook generation. The actual research truth should live in Python because that is where backtesting, walk-forward validation, feature generation, and model evaluation can be made auditable.

The result should be a small monorepo with one backend app, one backtesting runner, one paper-trading runner, one metrics and reporting pipeline, and one Pine script used as a chart-side detector and alert sender.

## 2. The Core Architectural Decision

Do not start by trying to make Pine Script the main engine and Python the add-on. That will make the project harder to validate, harder to reproduce, and harder to mutate. Instead, make Python the canonical implementation of the strategy and treat Pine Script as a mirror layer.

This means the white-box logic should be implemented twice, but with different purposes. In Python, it exists to backtest, label, and paper-trade. In Pine Script, it exists to visualize the same setup logic on the chart, verify that the chart-side behavior matches the Python engine closely enough, and emit webhooks when live setups occur.

That architectural split reduces future confusion. The Python implementation becomes the research object. The Pine implementation becomes the operator interface.

## 3. The First Version Boundary

The first version should deliberately avoid trying to solve every Smart Money concept in its full subjective richness. It should capture only the subset that can be formalized with acceptable integrity.

For version one, the white-box engine should include a killzone filter, session range tracking, previous day high and low, Asian session high and low, swing-based structure, liquidity sweep detection, a simplified order block definition, a simplified fair value gap definition, a change-of-character trigger, ATR-based stop placement, breakeven at 1R, and either a fixed 2R target or the next opposing liquidity pool when that target is mechanically definable.

If some concept cannot be specified clearly enough to be backtested without hidden discretion, it should either be simplified or omitted from version one. The purpose of version one is not theological purity to ICT language. The purpose is to produce a testable executable conjecture.

## 4. The Research Sequence

The correct execution order is not paper trading first. It is a staged research sequence.

Stage one is data normalization. Acquire and standardize 15-minute XAUUSD data, along with enough auxiliary context for DXY and US10Y if those are intended as black-box features. All timestamps must be normalized into one canonical timezone, and killzone logic must be expressed from that canonical base.

Stage two is white-box engine construction. Build the state machine, detectors, entry planner, risk logic, and management rules in Python. At this stage, there is no ML filter yet. The system should be able to run a full backtest on the white-box logic only.

Stage three is white-box verification. Inspect individual trades and make sure the engine is doing what the strategy claims to do. This is where you catch semantic mismatches such as lookahead in swing detection or order block definitions that only seem valid because future bars are silently leaking into the detector.

Stage four is ML labeling and feature pipeline construction. Only after the white-box logic is stable should you generate the candidate setup dataset and compute black-box context features. The model should score white-box setups, not raw market bars.

Stage five is hybrid validation. Compare three systems: white-box only, filtered hybrid, and a trivial baseline filter. The hybrid should only survive if it improves the quality of the setup stream under out-of-sample testing.

Stage six is paper-trading harness construction. Once the white-box and hybrid paths are stable enough, build the live loop that receives market updates, generates setup candidates, applies the filter, records approvals and rejections, and optionally sends orders to a paper venue.

Stage seven is one-week shadow run. Run the exact same logic for one week in paper mode while logging every white-box candidate, every hybrid decision, every rejected setup, every theoretical trade, and every actual paper-trade result.

## 5. The Repository Structure

The repo should be small and vertical. Do not build by technical layer alone. Build by research function.

A good repository structure is the following.

`apps/api/` should contain the FastAPI service. This service will expose health endpoints, a webhook endpoint for TradingView alerts, a signal-evaluation endpoint, and a report retrieval endpoint.

`apps/web/` should contain the thin operator dashboard. This can be very simple at first. It only needs to show recent signals, approvals, rejections, open paper trades, last seven days performance, and the current evaluation profile.

`strategy/whitebox/` should contain the canonical Python implementation of the Smart Money logic. This includes session tracking, structure logic, sweep logic, POI detection, trigger logic, and risk rules.

`strategy/hybrid/` should contain the feature pipeline, labeler, trained model artifacts, calibration helpers, and the inference interface that scores a white-box setup.

`research/backtests/` should contain the batch backtesting runner, walk-forward runner, parameter sweep runner, and perturbation tests for slippage and spread.

`research/reports/` should contain the metrics engine and the explanatory review writer that produces the Strategy Evaluation Canon outputs.

`execution/paper/` should contain the live paper-trading runner, the order adapter, and the trade-state reconciler.

`execution/adapters/` should contain broker or platform adapters such as `paper_simulator.py`, `oanda_adapter.py`, or `mt5_adapter.py`.

`pine/` should contain the Pine Script v6 mirror indicator or strategy used for chart-side visualization and webhook alerts.

`data/` should contain raw and normalized datasets, but large data artifacts should be ignored from version control and tracked by a local data manifest.

`tests/` should contain deterministic scenario tests for the white-box engine, feature pipeline tests, and regression tests for labeled setup generation.

## 6. The Minimal App You Want Codex to Build

The app should be intentionally modest. It should not pretend to be a full broker platform. It should be a research cockpit.

The home screen should show the current strategy version, box type, last model version, and whether the live loop is running. It should show the last twenty white-box setup candidates, which ones were approved by the filter, which ones were rejected, and which ones became paper trades.

A second view should show backtest summaries. This view should include net return, Sharpe, Sortino, max drawdown, win rate, expectancy, number of trades, and the handoff comparison between white-box and hybrid.

A third view should show the evaluation canon output. This view should not only show metrics but also the six valuation layers, the five explanatory paragraphs, the failure taxonomy label, and the current recommended destination: promote, incubate, graveyard, or bury.

A fourth view should show the current paper-trading week, including each trade’s reason string, entry, stop, target, model score, exit reason, and realized R-multiple.

This app can be built as a small React frontend over a FastAPI backend, but even a minimal server-rendered interface is sufficient for version one. The real value is in the strategy engine and the reporting pipeline, not in heavy frontend work.

## 7. The White-Box Engine Specification

The canonical Python engine should be built around event-time bars, not around broker ticks for version one. The core unit is the 15-minute bar. The state machine should be explicit and logged.

A bar should first be passed through session classification. The engine should know whether the bar belongs to the Asian build-up, London killzone, New York killzone, or none of the above. It should know the current Asian session high and low, the previous day high and low, and the latest confirmed swing points.

The sweep detector should work only on information available at that bar. A long candidate occurs when price pierces a defined liquidity level from below, does not exceed the maximum excursion threshold, and closes back above the level within the rules. A short candidate mirrors that logic.

The point-of-interest logic should remain simplified. A valid order block can be represented as the last opposing candle before an impulsive move exceeding a configurable ATR threshold. A valid FVG can be represented using the classic three-candle imbalance definition. The engine should record which POI type was involved and at which price band.

The trigger logic should require a change of character or market structure shift expressed in a mechanically consistent way. This should be defined through minor swing violation, not subjective eye-balling.

The entry planner should define limit-order placement, time-to-live for the order, stop placement, target placement, and breakeven promotion. Every trade object must carry a full reason payload.

## 8. The First Black-Box Layer

The black-box layer should be intentionally conservative in version one. Do not start with sequence models, transformers, or reinforcement learning. The first model should be a gradient-boosted tree model such as XGBoost or LightGBM because the objective is not maximal sophistication. The objective is a disciplined hybrid handoff.

The unit of modeling should be the white-box setup candidate, not every bar. That means each row in the model dataset corresponds to a candidate detected by the white-box engine. Each row should include only features known at the moment of candidate creation.

The target should be whether the candidate reached 2R before stop or not. That aligns the modeling task with the hybrid decision you actually care about.

Feature design should remain sparse and interpretable in the first pass. Include volatility ratios, time features, sweep depth relative to ATR, distance to POI midpoint, prior-session range context, DXY short-horizon return, US10Y short-horizon return, and spread or slippage proxies if available. Do not add dozens of weak features merely because you can.

The model output should be calibrated probability, not just raw ranking score. The threshold for execution can start near 0.65, but the true threshold should be tuned on validation data and checked for calibration.

## 9. The Backtesting Script You Actually Need

You do not need one giant backtesting script that does everything. You need three research scripts.

The first script should run the white-box engine across historical bars and emit every candidate, every order, every fill, and every final trade result. This script gives you the baseline strategy.

The second script should build the hybrid dataset by taking the white-box candidate stream and generating labeled rows for model training and evaluation. This script should perform strict temporal splits and should never allow future market information to enter the features.

The third script should run the hybrid backtest using a frozen model on held-out data and produce the head-to-head comparison between white-box and hybrid.

These scripts should all write structured artifacts. At minimum they should emit a trade log CSV or parquet, a candidate log, a summary JSON, and a canon report markdown file.

## 10. The Metrics and Evaluation Layer

The reporting layer should be built directly from the Strategy Evaluation Canon and not as a generic quant report.

Every run should produce the standard performance metrics such as net return, Sharpe, Sortino, Calmar, max drawdown, win rate, expectancy, average R, and trade count. It should also produce robustness slices, including train, validation, test, and walk-forward summaries, plus friction sensitivity.

For the hybrid system, the critical additional metric is handoff quality. This should be formalized as the difference between the full white-box candidate stream and the approved hybrid stream. The report should tell you whether the filter improved Sharpe, expectancy, drawdown profile, and out-of-sample stability, and whether the improvement came from better trade selection or from over-filtering the sample into insignificance.

The explanatory report should then write the five paragraphs required by the canon: edge statement, survival statement, failure statement, rival-explanation statement, and mutation statement.

## 11. The Paper-Trading Loop

For the one-week paper run, the live loop should not depend on backtest code that only works in batch. The paper runner should use the same canonical strategy package but advance incrementally as new bars arrive.

The live runner should do the following. It should ingest new 15-minute bars. It should update session state, structure state, and liquidity levels. It should detect whether a white-box candidate has formed. If it has, it should compute the hybrid feature vector using only current information. It should score the candidate, decide whether to approve it, and then send the trade either to an internal paper simulator or to a real demo venue adapter.

Every one of those steps should be logged. Even rejected setups must be written to the paper-trading log because handoff quality cannot be judged only from executed trades.

The safest first paper mode is an internal paper simulator driven by live or near-live bars. The second step is a real demo adapter such as OANDA demo or MetaTrader 5 demo. The internal simulator is easier to build and more controllable. The external demo adapter is useful once you want order-state realism.

## 12. Paper Venue Recommendation

The cleanest recommendation is to support two paper modes.

The default paper mode should be an internal paper simulator. This guarantees that the one-week run can happen even if broker integration is delayed. It also gives you complete control over fill assumptions, state transitions, and reporting.

The optional broker-backed paper mode should support either OANDA demo or MetaTrader 5 demo through a thin adapter. This should be treated as an execution adapter, not as the strategy engine itself.

That separation matters. If the adapter fails, the strategy should still continue producing signal logs and internal paper fills. Execution infrastructure should not be allowed to erase research visibility.

## 13. The Pine Script Mirror

The Pine Script should be written in Pine Script v6 and should be treated as a mirror, not as the canonical backtester. Its job is to render killzones, session highs and lows, previous day levels, detected sweeps, POIs, trigger markers, and the reason text for operator visibility.

It should also emit a webhook JSON payload when a white-box candidate reaches the confirmation state. The payload should include symbol, timeframe, timestamp, direction, sweep type, liquidity level, POI type, planned entry, stop, target, ATR, and reason string.

Do not try to encode the entire black-box layer in Pine. Pine should only emit the white-box event, and the backend should decide whether that event becomes an approved trade.

## 14. What Codex Should Build First

The best way to use Codex is not to ask for the entire project in one giant prompt. You should ask for a sequence of implementation blocks that can each be tested.

First ask Codex to scaffold the repository and the canonical domain objects. You need bars, sessions, sweeps, POIs, setup candidates, orders, positions, and trade results.

Second ask it to build the white-box engine only, with deterministic tests using hand-crafted bar sequences. This is where most semantic mistakes will be found.

Third ask it to build the historical backtester and trade logger.

Fourth ask it to build the hybrid dataset generator, feature pipeline, and gradient-boosted model training script.

Fifth ask it to build the hybrid backtest comparison runner and evaluation report generator.

Sixth ask it to build the FastAPI app that exposes the last run summaries and receives TradingView webhook alerts.

Seventh ask it to build the paper runner and internal paper simulator.

Eighth ask it to build the Pine Script mirror.

That order keeps the strategy logic in control of the project instead of letting infrastructure complexity take over.

## 15. The Concrete Deliverables You Want by the End of the First Cycle

By the end of the first cycle, you should demand these concrete outputs.

You should have a Python backtester that runs the white-box strategy over historical XAUUSD 15-minute data and produces a trade log.

You should have a hybrid training and evaluation script that can compare white-box versus hybrid on temporally separated data.

You should have a FastAPI backend with a webhook endpoint and a simple dashboard endpoint.

You should have an internal paper-trading runner that can run for one week and write every candidate, decision, and outcome.

You should have a Pine Script v6 chart mirror that produces matching white-box alerts and sends webhook payloads.

You should have a markdown report generator that writes the Strategy Evaluation Canon verdict for each run.

If those six things exist, you have the foundation of a real research system rather than a fragile prototype.

## 16. The Acceptance Criteria

The project should not be declared successful merely because code runs. It should only be accepted if the following conditions hold.

The white-box engine must pass deterministic scenario tests for sessions, sweeps, FVG detection, order block identification, CHoCH confirmation, and breakeven logic.

The historical backtester must produce reproducible outputs from the same dataset and parameters.

The hybrid dataset generator must prove that all features are timestamp-safe and that labels are derived only from future path after the setup time.

The hybrid comparison must show separate metrics for white-box and hybrid, including candidate counts, approval rates, win rate, expectancy, Sharpe, drawdown, and handoff quality.

The one-week paper runner must log every detected candidate regardless of approval, so that rejected setups remain available for review.

The canon report must classify the strategy by failure taxonomy if results are weak and must produce mutation guidance rather than only a metric table.

## 17. The Biggest Risks

The biggest risk is not coding difficulty. It is semantic leakage. Smart Money concepts can easily become backtest theater if swing points, FVGs, or structure shifts are defined using future information.

The second major risk is hidden discretion. If a concept only works because the human silently picks the “best-looking” level, the Python engine will either fail or become overfit when forced to choose mechanically.

The third risk is an over-ambitious hybrid layer. If you add too many features or too much model complexity before the white-box baseline is stable, you will not know whether the system works because of the rules, the filter, or accidental noise.

The fourth risk is execution confusion. If the project tries to bind itself too early to a specific broker or paper-trading platform, infrastructure will dominate the research. Keep the internal simulator as the guaranteed baseline.

## 18. The Codex Master Prompt

Use this as the top-level instruction to Codex after you create the repository.

"Build a small but serious research system for a hybrid Smart Money Concepts strategy on XAUUSD 15-minute bars. Python is the canonical source of truth. The system must include: a deterministic white-box strategy engine with explicit state machine and reason strings; a historical backtester; a candidate dataset generator for hybrid modeling; a gradient-boosted classifier that scores white-box candidates; a hybrid backtest comparison runner; a FastAPI app with webhook endpoint and simple dashboard; an internal paper-trading simulator that can run incrementally for one week; and a Pine Script v6 mirror indicator that emits webhook JSON when a white-box candidate is confirmed. Implement with minimal dependencies, clear domain objects, reproducible tests, and markdown reports following the Strategy Evaluation Canon. Do not hide ambiguity. If a Smart Money concept is too subjective to encode safely, simplify it and document the simplification."

## 19. The Codex Task Sequence

After that master prompt, issue the tasks one by one.

Task one should ask for the repository scaffold, the domain model, and the configuration system.

Task two should ask for the white-box engine plus deterministic scenario tests.

Task three should ask for the historical backtester and trade logging.

Task four should ask for the hybrid dataset generator and training script.

Task five should ask for the hybrid evaluation runner and canon report writer.

Task six should ask for the FastAPI app and webhook endpoint.

Task seven should ask for the internal paper simulator and live runner.

Task eight should ask for the Pine Script v6 mirror.

Each task should include acceptance tests, so Codex cannot skip the hard parts by writing vague scaffolding.

## 20. Final Recommendation

Start with the Python truth, not the Pine truth. Start with the white-box baseline, not the hybrid prestige layer. Start with internal paper simulation, not broker automation. Only after those pieces are solid should the project graduate into a broker-backed paper adapter and more ambitious model experimentation.

That path gives you something far more valuable than a flashy prototype. It gives you a research machine that can actually tell you whether your SMC conjecture on gold survives reality.



The most important decision in that plan is this: **do not make TradingView the source of truth**. Make **Python** the canonical strategy engine, backtester, and paper-trading runner, and use **TradingView only as the chart-side mirror and webhook emitter**. That is the cleanest way to keep your white-box logic auditable, your hybrid filter testable, and your one-week paper run comparable to the backtest. TradingView’s official webhook flow is outbound only, from alerts to your app, and requires 2FA to use. I did not find official documentation for programmatically placing trades into TradingView’s own Paper Trading simulator, so I would not architect around TradingView Paper Trading as the execution sink. That is an inference from their webhook and paper-trading docs, not a categorical claim about every unofficial workaround. ([TradingView][1])

I also shifted the plan to **Pine Script v6**, not v5, because TradingView’s current documentation says Pine has graduated to v6 and future updates apply there. ([TradingView][2])

For the one-week paper phase, the plan recommends **two execution modes**. The default should be an **internal paper simulator** inside your own Python app, because that guarantees the experiment can run even if broker integration is delayed or flaky. Then, as an optional adapter, support either **OANDA demo** or **MetaTrader 5 demo**. OANDA currently documents demo accounts and a REST v20 API for creating orders, and MetaTrader 5 officially documents Python integration and `order_send`, so both are realistic paths for XAUUSD-style demo execution. ([hub.oanda.com][3])

I also kept Render in the architecture, but with a warning: it is fine as a lightweight webhook receiver and dashboard host, yet free services come with real constraints. Render’s docs describe free web services as having feature limitations, and official docs also note free instances can spin down after inactivity; their pricing page shows the current free tier as a 30-day free limit. That makes Render acceptable for a first webhook/API layer, but not something you should treat as operationally stable infrastructure without expecting cold starts and lifecycle constraints. ([Render][4])

The execution order I designed is strict because it keeps the project from becoming infrastructure theater. First build the **canonical Python white-box engine** for sessions, sweeps, FVGs, simplified order blocks, CHoCH, entries, stops, breakeven, and targets. Then build the **historical backtester** and verify trades bar by bar. Only after that should you generate the **hybrid candidate dataset** and train a conservative first model such as XGBoost or LightGBM on **white-box setup candidates**, not on every raw bar. Then build the **hybrid comparison runner** so you can measure white-box versus filtered hybrid cleanly. Only after that should you add the **FastAPI webhook app**, the **internal paper simulator**, and finally the **Pine mirror** that emits live chart alerts into the backend.

That order matters because your biggest risk is not syntax; it is **semantic leakage**. Smart Money concepts become fake very easily if swings, CHoCH, FVG confirmation, or POI selection silently depend on future bars. By making Python the truth and requiring deterministic scenario tests first, you force those ambiguities into the open before you ever reach the paper week.

The app in the plan is intentionally small. It is not a broker terminal. It is a **research cockpit**. It should show recent white-box candidates, hybrid approvals and rejections, current paper trades, last-run metrics, and a Strategy Evaluation Canon report with handoff quality, failure taxonomy, and mutation guidance. That is enough to make the system useful without getting buried in frontend vanity.

The plan in canvas also includes a **repository layout**, **acceptance criteria**, the **Codex master prompt**, and the **task sequence** you should give Codex in blocks instead of asking it to build everything in one shot. That last part is important: Codex should be asked for scaffold first, then white-box engine plus tests, then backtester, then hybrid dataset and model, then evaluation layer, then API, then paper runner, then Pine mirror. If you ask for the whole thing at once, the likely outcome is pretty scaffolding around weak strategy semantics.

The shortest summary is this: build a **Python-first hybrid research system** with TradingView as the alerting mirror, not the judge; validate **white-box first**, then the hybrid handoff; run the one-week forward phase against your **internal paper simulator** first and an **OANDA or MT5 demo adapter** second; and make every run produce both trade metrics and a postplatonic explanatory review.

The next useful move is to turn that canvas plan into the exact sequence of Codex prompts, one prompt per implementation block.

[1]: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/?utm_source=chatgpt.com "How to configure webhook alerts"
[2]: https://www.tradingview.com/pine-script-docs/release-notes/?utm_source=chatgpt.com "Release notes"
[3]: https://hub.oanda.com/apply/demo/?utm_source=chatgpt.com "Apply for a demo - Open a Forex Account - OANDA"
[4]: https://render.com/docs/free?utm_source=chatgpt.com "Deploy for Free"
