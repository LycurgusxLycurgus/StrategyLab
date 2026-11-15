# Phase 1 / Phase 2 research-quality audit

Date: 2026-10-29. Scope: the [Create Bitcoin SMC strategy chat](codex://threads/01a18373-ca00-7313-8118-ff7d021d7f1d), its saved research/results, relevant implementation boundaries and current phase instructions. This is a process correction and bounded evidence audit, not a new strategy comparison. No historical verdict, strategy rule or protected market window was changed.

## Bottom line

The evidence supports failures of the tested executable formulations. It does **not** establish that all SMC, flow or funding information is noise, or that enough related trials guarantee a profitable candidate. The main correctable weakness is research transfer: source findings, convenient available inputs and fully designed trading wrappers were sometimes separated by material changes without a direct test establishing which component retained information.

The workflow also allowed returns with one candidate, and its readiness wording left research completion confused with tested strategy quality. Those are instruction/handoff defects, independent of whether the saved calculations are correct.

## What the other chat actually did

The first SMC creation ran three prototypes, 210 evaluations and reported zero qualifying contexts. Later research proposed three successor hypotheses and stopped before tests; the user explicitly questioned why there were no trades. The chat correctly explained that Phase 1 was research only, then ran Phase 2 after approval. Subsequent information-driven and funding returns selected only one candidate each, plus controls and multiple contexts. This was permitted by the old smaller-shortlist rule but does not satisfy the new minimum-three contract.

“Ready for Phase 2” meant rules/data/protocol readiness, not a high-quality signal or profit. Testing authorization was separate. New prompts make that distinction explicit in every research handoff and failure return.

## Observations from saved evidence

| Evidence | Observed result | What it establishes—and does not |
| --- | --- | --- |
| [Initial corrected liquidity comparison](../../artifacts/strategy-development/btc-liquidity-20261023/runs/comparison-v2/REPORT.md) | All 18 candidate contexts failed the screen; contexts share underlying formulations and data | Negative evidence for those rules/costs, not 18 independent mechanisms or a universal rejection of the methodology |
| [SMC prototype report](../../artifacts/strategy-development/btc-smc-20261028/PHASE_REPORT.md) | All 15 candidate contexts failed; one detector produced only 12 signals, with a favorable short PF based on five trades | Sparse favorable metrics do not establish a validated signal; low power is not proof of pure noise |
| [Successor comparison](../../artifacts/strategy-development/btc-successor-phase2-20261028/PHASE2.md) | Nine contexts failed; all lost in 2025; pooled net PF roughly 0.57–0.75 | The exact adaptations fail, but their source families are not universally falsified |
| [Executed-flow comparison](../../artifacts/strategy-development/btc-flow-phase2-20261028/PHASE2.md) | Six contexts failed. Both-direction saved raw-price PnL was −8,793.89 and −6,729.95 before modeled slippage/fees. Filtered recent losses were smaller than price-only losses | This exact fade was weak before costs. Reduced participation/exposure can explain lower losses; matched incremental information remains unestablished |
| [Funding-state comparison](../../artifacts/strategy-development/btc-funding-state-phase2-20261028/PHASE2.md) | Pooled PF 1.244/1.335 and positive 2022–2024 folds, but negative 2025 and January–August 2026 results; both contexts failed recent/stress/control gates | Historical aggregate association exists in this implementation, not a demonstrated current executable edge. The cause of deterioration is unproven |

The latest cumulative record is 1,020 economic evaluations, including 240 earlier validation replays. It includes strategies, controls, annual folds, execution grids and cost scenarios—not 1,020 independently researched strategies. Funding alone has 1,542 candidate trade records across repeated grids/costs but only 257 distinct triggers. Repeated selection on shared history increases false-discovery risk rather than guaranteeing eventual discovery. [Bailey et al., primary backtest-overfitting paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)

### Research-transfer problems

The [research-reset diagnosis](../../artifacts/strategy-development/btc-research-reset-phase1-20261028/PHASE1.md) documents changes from source market/session and multiday evidence into a different market or much shorter management horizon. A named concept or paper does not validate those adaptations.

That diagnosis reports mean raw saved movement of approximately −2.975, 0.540 and 1.952 bps for the three both-direction successors, against nominal base round-trip friction near 16 bps. These are arithmetic saved-trade price diagnostics, not size-weighted net returns or zero-cost counterfactual reruns. Wider initial stops did not create more captured movement. A cost-to-stop admission guard is not evidence that a timed/trailing exit can monetize a signal.

The [information-source research](../../artifacts/strategy-development/btc-information-phase1-20261028/PHASE1.md) explicitly states that candle aggregates cannot identify forced liquidations or reproduce a finer first-seconds feature. The later flow detector measures executed signed quote pressure instead. That can be an honest new observable, but must not inherit the unavailable liquidation mechanism's credibility or the original feature's effect size.

The [funding research](../../artifacts/strategy-development/btc-information-reset-phase1-20261028/PHASE1.md) relies on a reported gross spot-return association, while the test changes instrument, entry delay, event overlap/occupancy, sizing, exits and cash-flow costs. It also uses overlapping exposed history. These are documented limitations, not proof of a deceptive source; the adaptation needs its own discrimination evidence.

### Bugs versus unsuccessful hypotheses

A historical bug was found and fixed: the original liquidity broker could charge intrabar funding after an opening stop-gap exit. The [supersession note](../../artifacts/strategy-development/btc-liquidity-20261023/runs/comparison-v1/SUPERSEDED.md) and [correction evidence](../../artifacts/strategy-development/btc-liquidity-20261023/CORRECTION_EVIDENCE.json) record 240 identical corrected payloads because the historical dataset did not exercise that defect. Therefore it does not explain the recorded losses. The intermediate correction evidence retains a PENDING review field, but the later [final acceptance](../../artifacts/strategy-development/btc-liquidity-20261023/ACCEPTANCE.json) explicitly records terminal review PASS for comparison-v2. Those distinct records must not be conflated; this audit leaves both unchanged.

The root reran the existing funding/flow/liquidity/SMC/successor suites: **186 tests passed**. The bounded review found no additional confirmed implementation defect explaining the later failures. Passing tests support covered implementation behavior, not predictor quality, real fills or complete absence of bugs. No new economic simulation was run.

## Universal correction

Phase 1 now requires a research-quality dossier, not just literature plus complete rules:

- The measured observable and the claimed mechanism must match, with explicit point-in-time availability and source-to-target changes.
- Evidence must be relevant to the actual instrument, entry timing and holding horizon; gross correlations are not executable net returns.
- Captured-effect plausibility must be compared with all-in costs. Stop/target distance and volatility cannot stand in for expected profit.
- Each candidate needs competing explanations and a bounded falsification/control plan, including independent sample coverage and selection exposure.
- Every attempt targets at least three fresh complete candidates. Meaningful variants need failure-specific new predictions; threshold tweaks, controls and duplicate contexts cannot pad the count. Fewer than three supported candidates means incomplete research, not fabricated readiness.

Phase 2 separates three axes: measurement validity, signal evidence and full-strategy economics. Invalid or unsupported proxies are vetoed. Evidence against a useful effect vetoes only the tested formulation/context. Insufficient coverage stays INCONCLUSIVE. Promising or supported components are preserved for bounded research even if their strategy wrapper fails; none receives Phase 3 promotion unless the complete strategy passes its frozen requirements.

Controls must address exposure, turnover, timing, direction and regime confounding where relevant. Signal tests, ablations and exploratory analyses enter the trial ledger and use development partitions only. The final holdout stays untouched. Neither positive aggregate PF nor losing less than a control substitutes for the required evidence.

## Approval and next-batch behavior

Default to **research-only Phase 1**, explicitly labeled. It ends with unvalidated candidates and a request to approve the bounded Phase 2 test. If the user explicitly authorizes research and testing together for a new bounded batch, announce the transition and execute Phase 2 once prerequisites pass; do not stop at “ready.”

A failed Phase 2 report must explain the next research direction—new mechanisms, meaningful revisions or a justified mix—and say that at least three fresh candidates will be tested only after approval of the new batch/protocol. Unresearched proposals stay provisional. No automatic repeat-until-profitable loop or post-failure gate relaxation is authorized.

## Verification and limits

Root review passed for this instruction correction under the user's root-owned review hierarchy. Manual contract review covered: failed-batch return and new approval; fewer-than-three incomplete research; complete research-only handoff; already-approved combined execution; invalid proxy veto; underpowered evidence; reduced-exposure confounding; and supported-component retention without failed-strategy promotion. These are instruction-contract checks, not executed model-behavior evaluations.

The existing production prompt-discovery and README-link checks passed (two tests), alongside the 186 research-engine regressions. Local Markdown links and diff whitespace checks passed. No runtime API, strategy code or test implementation changed. The unrelated earlier README archive-integrity failure remains recorded and untouched; this is not a claim that every repository test passes.

This audit does not choose or test the next Bitcoin batch. It improves the mechanism by which that separately approved work must earn its evidence.
