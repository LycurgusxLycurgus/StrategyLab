# UNIVERSAL BUILD PROTOCOL FOR TRADINGVIEW INDICATORS AND STRATEGIES

Use this protocol when creating, correcting, extending, or refactoring any TradingView Pine Script indicator or strategy. Build in phases. Preserve working logic. Separate calculation, validation, and drawing. Treat chart drawings as the last layer, never as the first layer.

---

## PRIME DIRECTIVE

Create the model first. Verify the model with a dashboard. Draw the model only after the model is confirmed correct.

Every TradingView project must follow this order:

1. Build the logic alone.
2. Display the logic through a dashboard-style table.
3. Let the user, a human tester, or a computer-use agent confirm the values.
4. Research open-source/public Pine scripts that already draw the same kind of visual object correctly.
5. Copy the drawing architecture and object-management pattern from those public scripts as closely as licensing and platform rules allow.
6. Attach that drawing layer to the already-confirmed logic.
7. Preserve the dashboard permanently as the truth-checking layer.

---

## PHASE 1 — LOGIC-FIRST BUILD

Build the indicator or strategy as a calculation engine before drawing anything on the chart.

Use explicit inputs for all model assumptions. Group inputs by purpose. Keep detection logic, averaging logic, projection logic, risk logic, strategy execution logic, and display logic in separate sections.

Use clear state variables for every persistent concept. Store confirmed events separately from candidates. Store current-cycle state separately from historical samples. Store raw values separately from derived averages.

Use arrays only for finalized historical samples. Push values into arrays only when the event is confirmed by the rules. Update the most recent array value only when the same unresolved event is being refined. Shift arrays only after all related arrays have been updated together.

Use confirmed pivots, confirmed bars, confirmed timestamps, confirmed levels, and confirmed session data when the model must avoid repainting. Treat unconfirmed realtime values as candidates.

Use `request.security()` with explicit `barmerge.gaps_off` and `barmerge.lookahead_off` when importing higher-timeframe or external-symbol data. Keep higher-timeframe series separate from chart-timeframe series. Use the imported series directly for calculations that depend on the imported timeframe.

Use formulas that match the model definition exactly. Preserve dimensional consistency. Ratios must compare like quantities. Time intervals must use timestamps and a constant milliseconds-per-day conversion. Price targets must use price ranges, price ratios, or price transforms according to the model definition.

Use the simplest reliable timing model first. Prefer average elapsed time from confirmed historical events when ratio-based timing creates implausible dates. Keep ratio checks secondary until they prove stable across instruments and timeframes.

For strategies, separate signal detection from order execution. Calculate signals first. Calculate filters second. Calculate position sizing third. Submit orders last. Track entries, exits, stops, targets, pyramiding, cooldowns, and risk limits as explicit state.

---

## PHASE 2 — DASHBOARD-ONLY VALIDATION

Create a table dashboard as the first user interface. The dashboard is the model’s audit layer.

The dashboard must show the current input-derived state, sample counts, latest confirmed event, active candidate event, core averages, formulas, current projection, projected price, projected date, and any supporting target values.

The dashboard must show `n/a` for unavailable values. It must never hide missing inputs, missing samples, missing candidates, or incomplete cycles behind fabricated defaults.

The dashboard must display both raw values and derived values when both are necessary to audit the model. Show sample counts beside averages. Show the formula used for central averages. Show current-cycle anchors beside predictions.

The dashboard must remain useful with zero samples, one sample, partial cycles, and fully confirmed cycles.

The dashboard must use stable table dimensions. Increase the table row count before adding rows. Keep row indexes consistent. Keep all `table.cell()` calls syntactically valid and preferably single-line when the Pine editor is sensitive to line continuation.

Do not draw chart objects during the dashboard validation phase. Use no labels, no lines, no boxes, no future drawings, and no decorative objects during this phase. Use only hidden `plot(na)` when Pine requires a plot in an indicator.

Do not proceed to chart drawings until the dashboard values are confirmed correct by the user, a human tester, or a computer-use harness.

---

## PHASE 3 — HUMAN OR AGENT CONFIRMATION

Pause after the dashboard-only version. Ask the tester to verify that the model values make sense on the intended symbol, timeframe, session settings, and data source.

The tester must verify the detected anchors, candidate state, sample counts, averages, formulas, projections, and dates. The tester must compare the dashboard against visible chart history and known market structure.

Treat dashboard disagreements as logic bugs. Fix logic bugs in the dashboard-only version before adding drawings.

Treat implausible projections as model-design issues. Change formulas, filters, event definitions, or averaging methods before adding drawings.

Treat missing values as state or sample issues. Fix event confirmation, sample pushing, or projection conditions before adding drawings.

Treat drawing requests during this phase as deferred work. The logic remains the priority.

---

## PHASE 4 — OPEN-SOURCE DRAWING RESEARCH

After the dashboard logic is confirmed, search public/open-source Pine scripts that draw the same drawing category correctly.

Research scripts that successfully draw the specific required object classes: moving averages, bands, fills, horizontal targets, projected levels, vertical date markers, future projections, boxes, labels, anchored paths, strategy markers, risk zones, session ranges, trendlines, channels, or tables.

Study drawing architecture, not trading logic. Extract object-management patterns, anchoring choices, update timing, x-coordinate conventions, label placement, line extension rules, object deletion rules, and visual toggles.

Use public scripts to guide how drawings are created, updated, moved, hidden, and deleted. Preserve licensing and platform rules. Do not copy protected trading logic. Do not republish third-party code in violation of its license or platform rules.

Prefer public scripts that use persistent objects, `barstate.islast`, `xloc.bar_time` for timestamp-based future drawings, `plot()` for continuous series, `fill()` for bands, and controlled object counts.

Avoid public scripts that recreate objects on every bar, leak labels, exceed object limits, repaint historical drawings, use unstable future bar-index offsets, or mix calculation logic with decorative drawing logic.

---

## PHASE 5 — DRAWING-LAYER DESIGN

Add chart drawings as a separate layer attached to the confirmed dashboard logic.

Use `plot()` for continuous historical series. Use `fill()` between continuous series. Use persistent `line`, `label`, and `box` objects for finite projections, future levels, event markers, and zones.

Use `xloc.bar_time` for drawings anchored to timestamps, especially future dates. Use bar index anchoring only when the drawing must attach to confirmed historical bars and never needs to extend far into the future.

Create each persistent drawing object once. Update it on the last bar. Delete it when its display condition becomes false. Reset its variable to `na` after deletion.

Gate drawing updates with `barstate.islast` unless a drawing must exist historically. Keep historical markers minimal and tied to confirmed events only.

Keep drawing conditions explicit. A drawing must appear only when the required underlying model values exist. A drawing must disappear when the projection mode changes, when samples are missing, when the candidate state changes, or when the user disables that drawing group.

Use separate toggles for major drawing families. Provide toggles for model plots, bands, target lines, date markers, labels, paths, zones, and strategy-specific visuals.

Use visual hierarchy. The primary model output gets the clearest line. Secondary checks get weaker style. Historical anchors get small labels. Projection zones use transparent fills. Date markers use vertical lines with timestamp-based anchors.

Keep the dashboard and drawings connected to the same variables. The chart must never draw a value that differs from the dashboard. The dashboard remains the authority for debugging.

---

## PHASE 6 — PINE SYNTAX AND COMPILER RULES

Use the Pine version deliberately. Keep the whole script in one Pine version. Use syntax supported by that version.

Keep complex function calls on one line when the Pine editor or user environment shows line-continuation parser errors. Prefer one-line calls for `indicator()`, `strategy()`, `request.security()`, `plot()`, `plotshape()`, `line.new()`, `label.new()`, `box.new()`, `table.new()`, and `table.cell()` when stability matters.

Use helper functions for repeated formatting and calculations. Keep helper functions short and type-stable.

Declare persistent objects with `var`. Declare persistent arrays with `var`. Declare state variables with explicit types when initialized as `na`.

Use bounds checks before reading arrays. Check sample count before `array.get()`. Shift related arrays together. Maintain equal lengths for arrays that describe the same historical samples.

Use `na()` checks around every optional value. Avoid calculations that depend on missing anchors, missing ranges, zero denominators, or unavailable higher-timeframe values.

Use explicit integer casts for timestamps produced by arithmetic. Use a constant milliseconds-per-day value for date projections.

Do not mix object creation and object update in ways that create duplicates. Do not create labels or lines on every bar without deletion. Do not allow hidden old objects to remain after mode changes.

Do not exceed declared object limits. Set realistic `max_labels_count`, `max_lines_count`, and `max_boxes_count` only when those object types are used.

Do not use lookahead for predictive convenience. Do not use future data in historical calculations. Do not let confirmed historical samples depend on information unavailable at that bar.

---

## PHASE 7 — MODEL VALIDATION RULES

Validate every model with internal consistency checks.

Sample counts must match visible finalized events. Averages must use the intended samples only. Current candidates must not enter historical averages until finalized. Current projections must update from current confirmed state and current active candidates.

Price projections must use the proper anchor. High projections must originate from the latest confirmed low or the model’s defined bullish anchor. Low projections must originate from the candidate high or the model’s defined bearish anchor.

Date projections must use the proper timestamp anchor. Future high dates must originate from the low that begins the current advance. Future low dates must originate from the high that begins the current decline.

Detection filters must match the model. Macro filters, trend filters, volatility filters, liquidity filters, session filters, timeframe filters, and strategy filters must remain independent unless the model explicitly combines them.

When a model has both detection thresholds and statistical averages, distinguish them visually and textually. A detection band qualifies events. An average line estimates typical behavior. A target line projects the active cycle.

---

## PHASE 8 — STRATEGY-SPECIFIC RULES

When the project is a strategy, build the indicator logic first and the strategy execution second.

Keep signal state visible in the dashboard before enabling orders. Show active direction, entry condition, exit condition, stop logic, target logic, invalidation logic, risk amount, position size, and active trade state.

Use strategy orders only after signals are validated. Keep entries, exits, stops, and targets traceable to dashboard values.

Use realistic execution assumptions. Set commission, slippage, pyramiding, order type assumptions, initial capital, and position sizing explicitly.

Do not optimize strategy parameters before the logic is confirmed. Do not hide poor logic behind curve-fitting. Do not use future-looking pivots as executable realtime entries unless the strategy explicitly waits for confirmation.

---

## PHASE 9 — DRAWING QA

After adding drawings, compare every visible object to the dashboard.

The moving average plot must match the dashboard moving average. Bands must match the dashboard or input definitions. Average lines must match historical average values. Target lines must match target rows. Date markers must match date rows. Labels must print the same formatted value as the dashboard.

Pan, zoom, reload, change timeframe, change symbol, change projection mode, toggle drawings, and replay bars. Drawings must remain anchored. Future date lines must stay attached to timestamps. Persistent objects must update rather than multiply. Hidden objects must delete cleanly.

When drawings look correct and dashboard values remain correct, treat the drawing layer as accepted. Future edits must preserve the confirmed drawing architecture.

---

## PHASE 10 — CHANGE MANAGEMENT

Make one logical change at a time. Preserve the last working version. Rename versions clearly.

When fixing logic, edit the calculation layer first and verify the dashboard. When fixing visuals, edit only the drawing layer and verify the dashboard stays unchanged.

Do not refactor working logic during drawing changes. Do not change formulas while changing visual styling. Do not change detection rules while changing object anchoring.

When the user requests a narrow change, modify only that area. Keep every confirmed behavior intact.

---

## FINAL DELIVERY RULES

Deliver the complete script every time the user asks for a testable version. Avoid partial patches unless the user explicitly asks for a patch.

Keep the script self-contained. Include all inputs, helpers, calculations, dashboard code, and drawing code needed to run.

Keep important function calls syntactically safe for Pine. Avoid fragile multiline argument blocks where the editor may reject them.

Preserve the dashboard as a permanent diagnostic layer. Preserve drawing toggles. Preserve confirmed logic. Preserve confirmed drawing patterns.

The finished TradingView script must be readable, testable, auditable, and stable across chart reloads, panning, zooming, symbol changes, timeframe changes, and projection-mode changes.