const state = {
  families: [],
  datasets: [],
  familyDetail: null,
  prompts: [],
  workingParameters: {},
  previewResult: null,
  previewRequestToken: 0,
  optimizationProgressJobId: null,
  optimizationProgressHighWater: 0,
};

const outputBox = document.getElementById("outputBox");
const summaryGrid = document.getElementById("summaryGrid");
const metricsGrid = document.getElementById("metricsGrid");
const gateBadge = document.getElementById("gateBadge");
const familySelect = document.getElementById("familySelect");
const versionSelect = document.getElementById("versionSelect");
const datasetSelect = document.getElementById("datasetSelect");
const optimizeResearchButton = document.getElementById("optimizeResearchButton");
const optimizeAllButton = document.getElementById("optimizeAllButton");
const optimizeRobustnessButton = document.getElementById("optimizeRobustnessButton");
const optimizationStatus = document.getElementById("optimizationStatus");
const barsInput = document.getElementById("barsInput");
const fullHistoryInput = document.getElementById("fullHistoryInput");
const familyMeta = document.getElementById("familyMeta");
const datasetsTable = document.getElementById("datasetsTable");
const proposalsTable = document.getElementById("proposalsTable");
const runsTable = document.getElementById("runsTable");
const versionsTable = document.getElementById("versionsTable");
const promptsList = document.getElementById("promptsList");
let previewTimer = null;
let optimizationProgressTimer = null;
const MIN_DATASET_BARS = 40000;
const FULL_HISTORY_SENTINEL_BARS = 1000000;
const OUTPUT_ARRAY_LIMIT = 20;
const OUTPUT_MAX_CHARS = 60000;
const OPTIMIZATION_POLL_MS = 2500;
let optimizationInFlight = false;

function updateClock() {
  const node = document.getElementById("clock");
  if (!node) {
    return;
  }
  node.textContent = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

updateClock();
window.setInterval(updateClock, 1000);

function setStatus(elementId, message, tone = "") {
  const node = document.getElementById(elementId);
  node.textContent = message;
  node.className = `status ${tone}`.trim();
}

function summarizeForOutput(value, depth = 0, key = "") {
  if (depth > 5) {
    return "[nested object omitted]";
  }
  if (Array.isArray(value)) {
    if (["trades", "equity_curve", "candidates", "steps"].includes(key) && value.length > OUTPUT_ARRAY_LIMIT) {
      return {
        omitted: value.length,
        note: `${key} array omitted from UI output to keep the browser responsive.`,
        sample: value.slice(0, 3).map((item) => summarizeForOutput(item, depth + 1)),
      };
    }
    if (value.length > OUTPUT_ARRAY_LIMIT) {
      return [
        ...value.slice(0, OUTPUT_ARRAY_LIMIT).map((item) => summarizeForOutput(item, depth + 1)),
        `[${value.length - OUTPUT_ARRAY_LIMIT} more items omitted]`,
      ];
    }
    return value.map((item) => summarizeForOutput(item, depth + 1));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([entryKey, entryValue]) => [
        entryKey,
        summarizeForOutput(entryValue, depth + 1, entryKey),
      ]),
    );
  }
  return value;
}

function showOutput(payload) {
  const text = typeof payload === "string" ? payload : JSON.stringify(summarizeForOutput(payload), null, 2);
  outputBox.textContent =
    text.length > OUTPUT_MAX_CHARS
      ? `${text.slice(0, OUTPUT_MAX_CHARS)}\n\n[output truncated to keep the browser responsive]`
      : text;
}

function setOptimizationStatus(message, tone = "working", progress = null) {
  optimizationStatus.className = `optimization-status visible ${tone}`.trim();
  const progressHtml = progress
    ? `
      <div class="optimization-progress">
        <div class="optimization-progress-line">
          <span>${progress.label}</span>
          <span>${progress.percent}%</span>
        </div>
        <div class="optimization-progress-track" aria-hidden="true">
          <span style="width: ${progress.percent}%"></span>
        </div>
        ${progress.detail ? `<div class="optimization-progress-detail">${progress.detail}</div>` : ""}
      </div>
    `
    : "";
  optimizationStatus.innerHTML = `
    <span class="optimization-spinner" aria-hidden="true"></span>
    <span class="optimization-message">${message}</span>
    ${progressHtml}
  `;
}

function clearOptimizationStatus(delayMs = 0) {
  if (!delayMs) {
    optimizationStatus.className = "optimization-status";
    optimizationStatus.textContent = "";
    return;
  }
  window.setTimeout(() => clearOptimizationStatus(), delayMs);
}

function progressPercent(done, total) {
  if (!total || total <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((Number(done || 0) / Number(total)) * 100)));
}

function progressNumber(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function renderOptimizationProgress(progress) {
  if (!progress || !progress.active) {
    return;
  }
  const isOptimizeAll = ["optimize_all", "optimize_robustness_repair"].includes(progress.mode);
  const total = isOptimizeAll
    ? progressNumber(progress.total_overall)
    : progressNumber(progress.total_candidates);
  const done = isOptimizeAll
    ? progressNumber(progress.overall_index)
    : progressNumber(progress.candidate_index);
  const percent = progressPercent(done, total);
  if (progress.job_id !== state.optimizationProgressJobId) {
    state.optimizationProgressJobId = progress.job_id || null;
    state.optimizationProgressHighWater = 0;
  }
  if (percent < state.optimizationProgressHighWater) {
    return;
  }
  state.optimizationProgressHighWater = percent;
  const currentLever = progress.current_lever || progress.lever || "lever";
  const isFullRobustnessFinalist = progress.stage === "full_robustness_finalists";
  const label = isFullRobustnessFinalist
    ? `Full robustness finalist ${progress.finalist_index || 0}/${progress.finalist_total || "?"}`
    : isOptimizeAll
      ? `Overall ${done}/${total || "?"}`
      : `${currentLever} ${progress.candidate_index || 0}/${progress.total_candidates || "?"}`;
  const detailParts = [];
  if (isFullRobustnessFinalist) {
    detailParts.push("walk-forward 4 folds");
    detailParts.push("anchored OOS 3 folds");
    detailParts.push("cost stress 3 scenarios");
  } else if (isOptimizeAll) {
    detailParts.push(`pass ${progress.current_pass || 1}/${progress.passes || 1}`);
    detailParts.push(`lever ${progress.current_lever_index || 0}/${progress.total_levers || 0}: ${currentLever}`);
    detailParts.push(`candidate ${progress.candidate_index || 0}/${progress.total_candidates || "?"}`);
  }
  setOptimizationStatus(progress.message || "Optimization running...", "working", {
    label,
    percent,
    detail: detailParts.join(" | "),
  });
}

function stopOptimizationProgressPolling() {
  if (optimizationProgressTimer) {
    window.clearInterval(optimizationProgressTimer);
    optimizationProgressTimer = null;
  }
}

function startOptimizationProgressPolling() {
  stopOptimizationProgressPolling();
  const poll = async () => {
    try {
      const progress = await fetchJson("/api/optimization-progress");
      if (!progress.active) {
        if (progress.error) {
          setStatus("familyStatus", progress.error, "error");
          setOptimizationStatus(`Optimization failed: ${progress.error}`, "error");
          setOptimizationBusy(false);
          return;
        }
        if (progress.result_available && optimizationInFlight) {
          const recovered = await recoverOptimizationResult();
          setOptimizationBusy(false);
          if (recovered) {
            return;
          }
        }
        if (optimizationInFlight) {
          return;
        }
        if (progress.message) {
          setOptimizationStatus(progress.message, "success");
        }
        return;
      }
      renderOptimizationProgress(progress);
      if (!progress.active && !optimizationInFlight) {
        stopOptimizationProgressPolling();
      }
    } catch {
      // Progress polling is informational; the main optimization request owns success/failure.
    }
  };
  poll();
  optimizationProgressTimer = window.setInterval(poll, 1000);
}

function applyOptimizeAllResult(result, recovered = false) {
  const baseParameters = currentVersion().spec_json.parameters;
  state.workingParameters = { ...baseParameters, ...result.parameter_overrides };
  state.previewResult = result.preview;
  renderSummary();
  renderTuningEdges();
  renderRuns();
  showOutput(result);
  const tunedCount = Object.entries(result.parameter_overrides).filter(
    ([key, value]) => JSON.stringify(value) !== JSON.stringify(baseParameters[key]),
  ).length;
  const selectedCount = Object.keys(result.parameter_overrides).length;
  const fallbackCount = Number(result.research_fallback_steps || 0);
  const eligibleCount = Number(result.eligible_steps || 0);
  const modeNote = fallbackCount
    ? `${fallbackCount} research fallback steps, ${eligibleCount} production-eligible steps`
    : `${eligibleCount} production-eligible steps`;
  const selectedNote = selectedCount === tunedCount ? "" : `; ${selectedCount} selected values matched or filled the base`;
  const recoveredNote = recovered ? " Recovered completed preview from backend." : "";
  const rejectedNote = result.final_candidate_rejected
    ? " Optimized candidate failed production gates, so the starting values were kept."
    : "";
  const message = `Optimization complete. Applied ${tunedCount} changed values (${modeNote}${selectedNote}).${rejectedNote}${recoveredNote}`;
  setStatus("familyStatus", message, "success");
  setOptimizationStatus(message, "success");
  clearOptimizationStatus(9000);
}

async function recoverOptimizationResult() {
  try {
    const result = await fetchJson("/api/optimization-result");
    const version = currentVersion();
    const datasetId = selectedDatasetId();
    if (!version || result.base_version_id !== version.version_id || result.dataset_id !== datasetId) {
      return false;
    }
    applyOptimizeAllResult(result, true);
    return true;
  } catch {
    return false;
  }
}

function setOptimizationBusy(isBusy, activeLever = "") {
  optimizationInFlight = isBusy;
  optimizeResearchButton.disabled = isBusy;
  optimizeAllButton.disabled = isBusy;
  optimizeRobustnessButton.disabled = isBusy;
  proposalsTable.querySelectorAll('[data-action="optimize-lever"]').forEach((button) => {
    button.disabled = isBusy && button.dataset.key !== activeLever;
  });
  proposalsTable.querySelectorAll("[data-working-key], [data-action='reset-edge']").forEach((control) => {
    control.disabled = isBusy;
  });
}

function syncFullHistoryBars() {
  if (fullHistoryInput.checked) {
    barsInput.value = String(FULL_HISTORY_SENTINEL_BARS);
    barsInput.disabled = true;
    barsInput.title = "Full history ignores manual bar count. The backend will page exchange history until completion or safety cap.";
    return;
  }
  barsInput.disabled = false;
  barsInput.title = "";
  if (!Number(barsInput.value) || Number(barsInput.value) < MIN_DATASET_BARS) {
    barsInput.value = String(MIN_DATASET_BARS);
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const raw = await response.text();
  let payload = raw;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = raw;
  }
  if (!response.ok) {
    const detail = payload?.detail || raw || `Request failed with status ${response.status}`;
    const error = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function attachActiveOptimizationIfAny() {
  try {
    const progress = await fetchJson("/api/optimization-progress");
    if (!progress.active) {
      return false;
    }
    setOptimizationBusy(true);
    renderOptimizationProgress(progress);
    setStatus("familyStatus", "An optimization is already running. Reattached to progress updates.", "");
    startOptimizationProgressPolling();
    return true;
  } catch {
    return false;
  }
}

function selectedFamilyId() {
  return familySelect.value || state.families[0]?.family_id || "";
}

function selectedDatasetId() {
  return datasetSelect.value || state.datasets[0]?.dataset_id || "";
}

function currentVersion() {
  const selected = versionSelect.value;
  if (!selected) {
    return state.familyDetail?.current_version || null;
  }
  return (
    state.familyDetail?.versions?.find((version) => version.version_id === selected) ||
    state.familyDetail?.current_version ||
    null
  );
}

function currentRuns() {
  return state.familyDetail?.runs || [];
}

function tuningEdges() {
  return state.familyDetail?.tuning_edges || [];
}

function selectedVersionRuns() {
  const version = currentVersion();
  if (!version) {
    return [];
  }
  return currentRuns().filter((run) => run.version_id === version.version_id);
}

function savedRunForSelection() {
  const datasetId = selectedDatasetId();
  return selectedVersionRuns().find((run) => run.dataset_id === datasetId) || null;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function verdictBadge(verdict) {
  const tone = verdict === "promotion_candidate" ? "good" : verdict === "graveyard" ? "bad" : "";
  return `<span class="badge ${tone}">${verdict}</span>`;
}

function activeMetrics() {
  if (state.previewResult?.metrics) {
    return state.previewResult.metrics;
  }
  return savedRunForSelection()?.metrics_json || null;
}

function activeMetricSource() {
  if (state.previewResult) {
    return "Live preview";
  }
  return savedRunForSelection() ? "Saved run" : "No saved run";
}

function activeSpec() {
  if (state.previewResult?.spec) {
    return state.previewResult.spec;
  }
  return currentVersion()?.spec_json || null;
}

function capitalModelWarnings(spec, metrics) {
  if (!spec || !metrics) {
    return [];
  }
  const parameters = spec.parameters || {};
  const warnings = [];
  const mode = parameters.sizing_mode || "fixed_quantity";
  if (mode === "fixed_notional_pct") {
    const pct = Number(parameters.notional_pct ?? 1);
    warnings.push(`${formatNumber(pct * 100)}% of current equity is deployed on every new trade, then compounded.`);
    if (pct >= 1) {
      warnings.push("This is an all-in 1x compounding scenario, not a conservative production default.");
    }
  }
  if (mode === "fixed_risk_pct") {
    const pct = Number(parameters.risk_pct ?? 0);
    warnings.push(`${formatNumber(pct * 100, 4)}% of current equity is the intended stop-loss budget per trade.`);
  }
  if (Number(metrics.max_initial_risk_pct || 0) > 10) {
    warnings.push(`Max initial risk reached ${formatNumber(metrics.max_initial_risk_pct, 4)}% of equity on at least one trade.`);
  }
  return warnings;
}

function productionGateSummary(spec, metrics) {
  if (!spec || !metrics) {
    return "n/a";
  }
  const parameters = spec.parameters || {};
  const rules = spec.evaluation || {};
  const mode = parameters.sizing_mode || "fixed_quantity";
  const allowed = rules.production_sizing_modes || ["fixed_notional_pct", "fixed_risk_pct"];
  const corePass =
    Number(metrics.total_trades || 0) >= Number(rules.minimum_trades || 0) &&
    Number(metrics.profit_factor || 0) >= Number(rules.minimum_profit_factor || 0) &&
    Number(metrics.max_equity_drawdown_pct || 0) <= Number(rules.maximum_drawdown_pct || 100) &&
    Number(metrics.net_pnl || 0) > Number(rules.minimum_net_pnl ?? -Infinity) &&
    Number(metrics.sharpe || 0) >= Number(rules.minimum_sharpe ?? -Infinity) &&
    Number(metrics.sortino || 0) >= Number(rules.minimum_sortino ?? -Infinity) &&
    Number(metrics.daily_sharpe || 0) >= Number(rules.minimum_daily_sharpe ?? -Infinity) &&
    Number(metrics.daily_sortino || 0) >= Number(rules.minimum_daily_sortino ?? -Infinity) &&
    Number(metrics.calmar || 0) >= Number(rules.minimum_calmar ?? -Infinity) &&
    Number(metrics.max_initial_risk_pct || 0) <= Number(rules.maximum_initial_risk_pct || 100) &&
    Number(metrics.max_entry_exposure_pct || 0) <= Number(rules.maximum_entry_exposure_pct || 100) &&
    Number(metrics.avg_entry_exposure_pct || 0) <= Number(rules.maximum_avg_exposure_pct || 100) &&
    Math.abs(Math.min(Number(metrics.worst_daily_return_pct || 0), 0)) <= Number(rules.maximum_worst_daily_loss_pct || 100);
  if (!corePass) {
    return "Core gates failed";
  }
  if (!allowed.includes(mode)) {
    return "Diagnostic capital model";
  }
  const benchmarkPass = Number(metrics.outperformance_pct || 0) > 0 || Number(metrics.calmar_delta || 0) > 0;
  return benchmarkPass ? "Production candidate" : "Weak vs benchmark";
}

function renderMetrics() {
  const metrics = activeMetrics();
  if (!metrics) {
    if (gateBadge) {
      gateBadge.textContent = "Awaiting Evidence";
      gateBadge.className = "gate-badge";
    }
    metricsGrid.innerHTML = `<div class="empty-state">Run the selected version or change a tuning value to populate the performance panel.</div>`;
    return;
  }
  const spec = activeSpec();
  const comparison = state.previewResult?.comparison || null;
  const warnings = capitalModelWarnings(spec, metrics);
  const gateSummary = productionGateSummary(spec, metrics);
  if (gateBadge) {
    gateBadge.textContent = gateSummary;
    gateBadge.className = `gate-badge ${gateSummary === "Production candidate" ? "pass" : ""}`.trim();
  }
  const warningText = warnings.length
    ? warnings.map((warning) => escapeHtml(warning)).join(" ")
    : "Capital model is compatible with the selected evaluation contract.";
  const majorLines = [
    ["Net PnL", formatNumber(metrics.net_pnl), "major"],
    ["Return %", `${formatNumber(metrics.return_pct)}%`, "major"],
    ["Profit Factor", formatNumber(metrics.profit_factor, 4), "major"],
    ["Trades", formatNumber(metrics.total_trades, 0), ""],
    ["Win Rate", `${formatNumber(metrics.percent_profitable)}%`, ""],
    ["Max Drawdown", `${formatNumber(metrics.max_equity_drawdown_pct)}%`, "risk"],
  ];
  const detailLines = [
    ["Daily Sharpe", formatNumber(metrics.daily_sharpe, 4)],
    ["Daily Sortino", formatNumber(metrics.daily_sortino, 4)],
    ["Trade Sharpe", formatNumber(metrics.sharpe, 4)],
    ["Trade Sortino", formatNumber(metrics.sortino, 4)],
    ["Daily Vol %", `${formatNumber(metrics.daily_volatility_pct)}%`],
    ["Worst Day %", `${formatNumber(metrics.worst_daily_return_pct)}%`],
    ["Calmar", formatNumber(metrics.calmar, 4)],
    ["B&H Calmar", formatNumber(metrics.buy_hold_calmar, 4)],
    ["Calmar Delta", formatNumber(metrics.calmar_delta, 4)],
    ["Avg Exposure %", `${formatNumber(metrics.avg_entry_exposure_pct)}%`],
    ["Max Exposure %", `${formatNumber(metrics.max_entry_exposure_pct)}%`],
    ["Max Risk %", `${formatNumber(metrics.max_initial_risk_pct, 4)}%`],
    ["B&H Asset %", `${formatNumber(metrics.buy_hold_return_pct)}%`],
    ["Alpha vs B&H %", `${formatNumber(metrics.outperformance_pct)}%`],
    ["Base PF Delta", comparison ? formatNumber(comparison.profit_factor_delta, 4) : "n/a"],
    ["Base DD Delta", comparison ? `${formatNumber(comparison.drawdown_pct_delta)}%` : "n/a"],
  ];
  metricsGrid.innerHTML = `
    <section class="metrics-warning">
      <span class="metric-label">Capital Model</span>
      <strong>${warningText}</strong>
    </section>
    <section class="metrics-pair-grid">
      <div>
        <span class="metric-label">Source</span>
        <strong class="metric-value">${activeMetricSource()}</strong>
      </div>
      <div>
        <span class="metric-label">Sizing Mode</span>
        <strong class="metric-value accent">${spec?.parameters?.sizing_mode || "fixed_quantity"}</strong>
      </div>
    </section>
    <section>
      ${majorLines
        .map(
          ([label, value, tone]) => `
            <div class="metric-line ${tone}">
              <span class="metric-label">${label}</span>
              <strong class="metric-value numeric">${value}</strong>
            </div>
          `,
        )
        .join("")}
    </section>
    <section class="metric-detail-grid">
      ${detailLines
        .map(
          ([label, value]) => `
            <div class="metric-detail">
              <span>${label}</span>
              <span class="numeric">${value}</span>
            </div>
          `,
        )
        .join("")}
    </section>
  `;
}

function syncWorkingParameters() {
  const version = currentVersion();
  if (!version) {
    state.workingParameters = {};
    return;
  }
  const parameters = version.spec_json?.parameters || {};
  const next = {};
  for (const [key, value] of Object.entries(parameters)) {
    next[key] = state.workingParameters[key] ?? value;
  }
  state.workingParameters = next;
}

function renderSummary() {
  const family = state.familyDetail?.family;
  const runCount = currentRuns().length;
  const edgeCount = tuningEdges().length;
  const version = currentVersion();
  const latestRun = savedRunForSelection();
  const cards = [
    ["Families", state.families.length, "Reusable strategy families in the lab"],
    ["Datasets", state.datasets.length, "Research datasets available for mutation work"],
    ["Edges", edgeCount, "Ordered tuning edges around the selected mutation base"],
    ["Runs", runCount, "Persisted parent/child backtests for the selected family"],
    ["Current Family", family?.family_id || "n/a", family?.title || "No family selected"],
    ["Mutation Base", version?.version_id || "n/a", version?.name || "Select a version"],
    ["Best Saved PF", latestRun ? formatNumber(latestRun.metrics_json.profit_factor, 4) : "n/a", latestRun ? latestRun.verdict : "Run this version first"],
  ];
  summaryGrid.innerHTML = cards
    .map(
      ([label, value, note]) => `
        <article class="summary-card">
          <span>${label}</span>
          <strong class="numeric">${value}</strong>
          <span>${note}</span>
        </article>
      `,
    )
    .join("");
}

function renderFamilySelect() {
  const previous = selectedFamilyId();
  familySelect.innerHTML = state.families
    .map((family) => `<option value="${family.family_id}">${family.title} (${family.family_id})</option>`)
    .join("");
  if (state.families.some((family) => family.family_id === previous)) {
    familySelect.value = previous;
  }
}

function renderVersionSelect(preferredVersionId = "") {
  const versions = [...(state.familyDetail?.versions || [])].sort((left, right) => right.created_at.localeCompare(left.created_at));
  versionSelect.innerHTML = versions
    .map((version) => {
      const isCurrent = version.version_id === state.familyDetail?.family?.current_version_id;
      const label = `${version.name} (${version.version_id})${isCurrent ? " [current]" : ""}`;
      return `<option value="${version.version_id}">${label}</option>`;
    })
    .join("");
  const fallback = preferredVersionId || state.familyDetail?.family?.current_version_id || versions[0]?.version_id || "";
  if (versions.some((version) => version.version_id === fallback)) {
    versionSelect.value = fallback;
  }
}

function renderDatasets() {
  const previous = selectedDatasetId();
  datasetSelect.innerHTML = state.datasets
    .map(
      (dataset) =>
        `<option value="${dataset.dataset_id}">${dataset.name} | ${dataset.symbol} | ${dataset.timeframe} | ${dataset.rows_count} rows</option>`,
    )
    .join("");
  if (state.datasets.some((dataset) => dataset.dataset_id === previous)) {
    datasetSelect.value = previous;
  }

  if (!state.datasets.length) {
    datasetsTable.innerHTML = `<tr><td colspan="5" class="empty-state">No datasets yet. Download at least 40000 BTCUSDT bars first.</td></tr>`;
    return;
  }

  datasetsTable.innerHTML = state.datasets
    .map(
      (dataset) => `
        <tr>
          <td>${dataset.name}</td>
          <td>${dataset.symbol}</td>
          <td>${dataset.timeframe}</td>
          <td class="numeric">${formatNumber(dataset.rows_count, 0)}</td>
          <td>
            <div class="table-actions">
              <button class="ghost" data-action="use-dataset" data-id="${dataset.dataset_id}">Use</button>
              <button class="danger" data-action="delete-dataset" data-id="${dataset.dataset_id}">Delete</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderFamilyMeta() {
  const family = state.familyDetail?.family;
  const version = currentVersion();
  if (!family || !version) {
    familyMeta.innerHTML = `<div class="empty-state">Select a family to inspect its current parent and tuning contract.</div>`;
    return;
  }
  const rules = version.spec_json?.evaluation || {};
  const parameters = version.spec_json?.parameters || {};
  familyMeta.innerHTML = `
    <article class="meta-box">
      <h3>Identity</h3>
      <p><strong>${family.title}</strong></p>
      <p>${family.asset} | ${family.venue} | ${family.timeframe}</p>
      <p>Selected mutation base: ${version.name}</p>
    </article>
    <article class="meta-box">
      <h3>Causal Story</h3>
      <p>${version.causal_story}</p>
    </article>
    <article class="meta-box">
      <h3>Evaluation</h3>
      <pre>${JSON.stringify(rules, null, 2)}</pre>
    </article>
    <article class="meta-box">
      <h3>Frozen Parent Parameters</h3>
      <pre>${JSON.stringify(parameters, null, 2)}</pre>
    </article>
  `;
}

function renderTuningEdges() {
  const edges = tuningEdges();
  if (!edges.length) {
    proposalsTable.innerHTML = `<tr><td colspan="5" class="empty-state">No tuning edges for this family yet.</td></tr>`;
    return;
  }
  proposalsTable.innerHTML = edges
    .map((edge) => {
      const current = edge.current_value;
      const working = state.workingParameters[edge.lever];
      let control = "";
      if (edge.value_type === "bool") {
        control = `
          <select data-working-key="${edge.lever}">
            <option value="true" ${String(working) === "true" ? "selected" : ""}>true</option>
            <option value="false" ${String(working) === "false" ? "selected" : ""}>false</option>
          </select>
        `;
      } else if (edge.value_type === "enum" || edge.value_type === "list") {
        const seen = new Set();
        const choices = [current, ...edge.alternatives].filter((value) => {
          const token = valueToken(value);
          if (seen.has(token)) {
            return false;
          }
          seen.add(token);
          return true;
        });
        control = `
          <select data-working-key="${edge.lever}">
            ${choices
              .map((value) => {
                const token = valueToken(value);
                return `<option value="${token}" ${valueToken(working) === token ? "selected" : ""}>${displayValue(value)}</option>`;
              })
              .join("")}
          </select>
        `;
      } else {
        const step = edge.value_type === "float" ? "0.1" : "1";
        const minAttr = edge.search_min !== null && edge.search_min !== undefined ? ` min="${edge.search_min}"` : "";
        const maxAttr = edge.search_max !== null && edge.search_max !== undefined ? ` max="${edge.search_max}"` : "";
        const stepAttr = edge.search_step !== null && edge.search_step !== undefined ? edge.search_step : step;
        control = `<input data-working-key="${edge.lever}" type="number" step="${stepAttr}"${minAttr}${maxAttr} value="${working}" />`;
      }
      const optimizeControl = edge.optimizable === false
        ? `<span class="manual-only">Manual</span>`
        : `<button class="ghost" data-action="optimize-lever" data-key="${edge.lever}">Optimize</button>`;
      return `
        <tr>
          <td>
            <strong>${edge.lever}</strong>
            <div>${edge.rationale}</div>
          </td>
          <td class="numeric">${displayValue(current)}</td>
          <td>
            ${control}
          </td>
          <td>
            <div class="table-actions">
              ${optimizeControl}
              <button class="ghost" data-action="reset-edge" data-key="${edge.lever}" data-value="${valueToken(current)}">Reset</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
  if (optimizationInFlight) {
    setOptimizationBusy(true);
  }
}

function renderVersions() {
  const versions = [...(state.familyDetail?.versions || [])].sort((left, right) => right.created_at.localeCompare(left.created_at));
  if (!versions.length) {
    versionsTable.innerHTML = `<tr><td colspan="5" class="empty-state">No saved versions yet.</td></tr>`;
    return;
  }
  const currentVersionId = state.familyDetail?.family?.current_version_id;
  versionsTable.innerHTML = versions
    .map((version) => {
      const parentLabel = version.parent_version_id || "seed";
      const isCurrent = version.version_id === currentVersionId;
      const isSelected = version.version_id === currentVersion()?.version_id;
      return `
        <tr>
          <td>
            <strong>${version.name}</strong>
            <div class="numeric">${version.version_id}</div>
          </td>
          <td>${version.stage}${isCurrent ? ' <span class="badge good">current</span>' : ""}${isSelected ? ' <span class="badge">selected</span>' : ""}</td>
          <td class="numeric">${parentLabel}</td>
          <td class="numeric">${version.created_at.replace("T", " ").slice(0, 16)}</td>
          <td>
            <div class="table-actions">
              <button class="ghost" data-action="pick-version" data-version="${version.version_id}">Use As Base</button>
              ${isCurrent ? "" : `<button class="danger" data-action="delete-version" data-version="${version.version_id}">Delete</button>`}
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderRuns() {
  const versions = Object.fromEntries((state.familyDetail?.versions || []).map((version) => [version.version_id, version]));
  const runs = currentRuns();
  let previewRow = "";
  if (state.previewResult) {
    previewRow = `
      <tr>
        <td>
          <strong>Unsaved tuning preview</strong>
          <div>live parameter changes</div>
        </td>
        <td>${verdictBadge(state.previewResult.verdict)}</td>
        <td class="numeric">${formatNumber(state.previewResult.metrics.profit_factor, 4)}</td>
        <td class="numeric">${formatNumber(state.previewResult.metrics.total_trades, 0)}</td>
        <td class="numeric">${formatNumber(state.previewResult.metrics.max_equity_drawdown_pct)}%</td>
        <td class="numeric">${formatNumber(state.previewResult.metrics.net_pnl)}</td>
        <td>
          <div class="artifact-links">
            <span class="badge">unsaved</span>
          </div>
        </td>
        <td>
          <div class="table-actions">
            <button data-action="save-preview-now">Save</button>
          </div>
        </td>
      </tr>
    `;
  }

  if (!runs.length && !previewRow) {
    runsTable.innerHTML = `<tr><td colspan="8" class="empty-state">No runs yet. Run the selected version after downloading data.</td></tr>`;
    renderMetrics();
    return;
  }

  renderMetrics();
  runsTable.innerHTML =
    previewRow +
    runs
      .map((run) => {
        const version = versions[run.version_id];
        const artifactName = run.artifact_path.split(/[/\\\\]/).pop();
        const reportName = run.report_path.split(/[/\\\\]/).pop();
        const promoteButton =
          state.familyDetail?.family?.current_version_id !== run.version_id
            ? `<button class="ghost" data-action="promote-version" data-family="${run.family_id}" data-version="${run.version_id}">Promote</button>`
            : "";
        return `
          <tr>
            <td>
              <strong>${version?.name || run.version_id}</strong>
              <div>${version?.stage || "unknown"}</div>
            </td>
            <td>${verdictBadge(run.verdict)}</td>
            <td class="numeric">${formatNumber(run.metrics_json.profit_factor, 4)}</td>
            <td class="numeric">${formatNumber(run.metrics_json.total_trades, 0)}</td>
            <td class="numeric">${formatNumber(run.metrics_json.max_equity_drawdown_pct)}%</td>
            <td class="numeric">${formatNumber(run.metrics_json.net_pnl)}</td>
            <td>
              <div class="artifact-links">
                <a href="/api/artifacts/runs/${artifactName}" target="_blank" rel="noreferrer">artifact</a>
                <a href="/api/artifacts/reports/${reportName}" target="_blank" rel="noreferrer">report</a>
              </div>
            </td>
            <td>
              <div class="table-actions">
                <button class="ghost" data-action="select-version" data-version="${run.version_id}">Tune</button>
                ${promoteButton}
                <button class="ghost" data-action="execution-audit" data-id="${run.run_id}">Audit Execution</button>
                <button class="danger" data-action="delete-run" data-id="${run.run_id}">Delete</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}

function renderPrompts() {
  const prompts = [...(state.prompts.length ? state.prompts : state.familyDetail?.prompts || [])].sort(
    (left, right) => promptSortKey(left.name).localeCompare(promptSortKey(right.name)),
  );
  promptsList.innerHTML = prompts
    .map(
      (prompt, index) => `
        <details>
          <summary>
            <span>${escapeHtml(prompt.name)}</span>
            <button class="icon-button prompt-copy-button" data-action="copy-prompt" data-prompt-index="${index}" title="Copy prompt to clipboard" aria-label="Copy ${escapeAttribute(prompt.name)} to clipboard">Copy</button>
          </summary>
          <pre>${escapeHtml(prompt.content)}</pre>
        </details>
      `,
    )
    .join("");
  promptsList._visiblePrompts = prompts;
}

function promptSortKey(name) {
  const match = String(name).match(/^(\d+)(?:-(\d+))?[_-]/);
  if (!match) {
    return String(name);
  }
  const phase = match[1].padStart(2, "0");
  const subphase = match[2] ? `.${match[2].padStart(2, "0")}` : ".00";
  return `${phase}${subphase}-${name}`;
}

function valueToken(value) {
  return Array.isArray(value) ? JSON.stringify(value) : String(value);
}

function displayValue(value) {
  return Array.isArray(value) ? `[${value.join(", ")}]` : String(value);
}

function castValue(raw, currentValue) {
  if (typeof currentValue === "boolean") {
    return raw === true || raw === "true";
  }
  if (Array.isArray(currentValue)) {
    return Array.isArray(raw) ? raw : JSON.parse(raw);
  }
  if (typeof currentValue === "number") {
    return Number(raw);
  }
  return raw;
}

function edgeForKey(key) {
  return tuningEdges().find((edge) => edge.lever === key) || null;
}

function clampToEdge(value, edge) {
  if (!edge || typeof value !== "number" || Number.isNaN(value)) {
    return value;
  }
  let next = value;
  if (edge.search_min !== null && edge.search_min !== undefined) {
    next = Math.max(next, Number(edge.search_min));
  }
  if (edge.search_max !== null && edge.search_max !== undefined) {
    next = Math.min(next, Number(edge.search_max));
  }
  return next;
}

function collectOverrides() {
  const version = currentVersion();
  if (!version) {
    return {};
  }
  const base = version.spec_json?.parameters || {};
  const overrides = {};
  for (const [key, value] of Object.entries(state.workingParameters)) {
    if (valueToken(value) !== valueToken(base[key])) {
      overrides[key] = value;
    }
  }
  return overrides;
}

async function refreshAll() {
  const familyId = selectedFamilyId();
  const preferredVersionId = versionSelect.value;
  const [families, datasets, prompts] = await Promise.all([
    fetchJson("/api/families"),
    fetchJson("/api/datasets"),
    fetchJson("/api/prompts"),
  ]);
  state.families = families;
  state.datasets = datasets;
  state.prompts = prompts;
  renderFamilySelect();
  renderDatasets();
  const targetFamilyId = state.families.some((family) => family.family_id === familyId)
    ? familyId
    : state.families[0]?.family_id;
  if (targetFamilyId) {
    familySelect.value = targetFamilyId;
    state.familyDetail = await fetchJson(`/api/families/${targetFamilyId}`);
  } else {
    state.familyDetail = null;
  }
  renderVersionSelect(preferredVersionId);
  if (versionSelect.value) {
    state.familyDetail.tuning_edges = await fetchJson(`/api/versions/${versionSelect.value}/tuning`);
  }
  state.previewResult = null;
  state.workingParameters = {};
  syncWorkingParameters();
  renderSummary();
  renderFamilyMeta();
  renderTuningEdges();
  renderRuns();
  renderVersions();
  renderPrompts();
}

async function refreshFamilyDetail() {
  const familyId = selectedFamilyId();
  const preferredVersionId = versionSelect.value;
  if (!familyId) {
    return;
  }
  state.familyDetail = await fetchJson(`/api/families/${familyId}`);
  renderVersionSelect(preferredVersionId);
  if (versionSelect.value) {
    state.familyDetail.tuning_edges = await fetchJson(`/api/versions/${versionSelect.value}/tuning`);
  }
  state.previewResult = null;
  state.workingParameters = {};
  syncWorkingParameters();
  renderSummary();
  renderFamilyMeta();
  renderTuningEdges();
  renderRuns();
  renderVersions();
  renderPrompts();
}

async function refreshSelectedVersion() {
  if (!state.familyDetail || !versionSelect.value) {
    return;
  }
  state.familyDetail.tuning_edges = await fetchJson(`/api/versions/${versionSelect.value}/tuning`);
  state.previewResult = null;
  state.workingParameters = {};
  syncWorkingParameters();
  renderSummary();
  renderFamilyMeta();
  renderTuningEdges();
  renderRuns();
  renderVersions();
}

async function downloadDataset() {
  setStatus("downloadStatus", "Downloading Binance dataset...", "");
  syncFullHistoryBars();
  const fullHistory = fullHistoryInput.checked;
  const payload = {
    symbol: document.getElementById("symbolInput").value.trim().toUpperCase(),
    timeframe: document.getElementById("timeframeSelect").value,
    bars: fullHistory ? MIN_DATASET_BARS : Number(barsInput.value),
    full_history: fullHistory,
    name: document.getElementById("datasetNameInput").value.trim() || null,
  };
  try {
    const result = await fetchJson("/api/datasets/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showOutput(result);
    const suffix =
      result.download_mode === "full_history"
        ? result.history_truncated
          ? ` Full history hit the safety cap at ${result.history_cap_bars} bars, so this dataset is still truncated.`
          : " Full history download completed."
        : "";
    setStatus("downloadStatus", `Dataset ready: ${result.name} (${result.rows_count} rows).${suffix}`, "success");
    await refreshAll();
    datasetSelect.value = result.dataset_id;
    state.previewResult = null;
    renderSummary();
    renderRuns();
    schedulePreview(true);
  } catch (error) {
    setStatus("downloadStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function importMt5Dataset() {
  setStatus("downloadStatus", "Importing MT5 CSV...", "");
  const fileInput = document.getElementById("mt5CsvFileInput");
  const selectedFile = fileInput.files?.[0] || null;
  const common = {
    symbol: document.getElementById("mt5SymbolInput").value.trim().toUpperCase(),
    timeframe: document.getElementById("mt5TimeframeSelect").value,
    name: document.getElementById("mt5DatasetNameInput").value.trim() || null,
  };
  try {
    let endpoint = "/api/datasets/import-mt5";
    let payload = {
      ...common,
      source_path: document.getElementById("mt5CsvPathInput").value.trim(),
    };
    if (selectedFile) {
      endpoint = "/api/datasets/import-mt5-content";
      setStatus("downloadStatus", `Reading ${selectedFile.name}...`, "");
      payload = {
        ...common,
        filename: selectedFile.name,
        content: await selectedFile.text(),
      };
    }
    const result = await fetchJson(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showOutput(result);
    setStatus("downloadStatus", `Dataset ready: ${result.name} (${result.rows_count} rows).`, "success");
    await refreshAll();
    datasetSelect.value = result.dataset_id;
    state.previewResult = null;
    renderSummary();
    renderRuns();
    schedulePreview(true);
  } catch (error) {
    setStatus("downloadStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function runParent() {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    setStatus("familyStatus", "Select a family and dataset first.", "error");
    return;
  }
  setStatus("familyStatus", "Running selected version...", "");
  const versionLabel = version.name || version.version_id;
  try {
    const result = await fetchJson(`/api/versions/${version.version_id}/run?dataset_id=${encodeURIComponent(datasetId)}`, {
      method: "POST",
    });
    showOutput(result);
    setStatus("familyStatus", `${versionLabel} run complete: ${result.verdict}.`, "success");
    await refreshFamilyDetail();
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function executePreview(showMessage = false) {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    return;
  }
  const overrides = collectOverrides();
  const savedRun = savedRunForSelection();
  if (!Object.keys(overrides).length) {
    if (savedRun) {
      state.previewResult = null;
      renderSummary();
      renderRuns();
      if (showMessage) {
        setStatus("familyStatus", "Showing the saved run for the selected dataset.", "success");
      }
      return;
    }
    if (showMessage) {
      setStatus("familyStatus", "No saved run for this dataset. Generating a live preview...", "");
    }
  }
  const requestToken = ++state.previewRequestToken;
  state.previewResult = null;
  renderSummary();
  renderRuns();
  if (showMessage && Object.keys(overrides).length) {
    setStatus("familyStatus", "Refreshing live preview...", "");
  }
  try {
    const result = await fetchJson(`/api/versions/${version.version_id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        parameter_overrides: overrides,
      }),
    });
    if (requestToken !== state.previewRequestToken) {
      return;
    }
    state.previewResult = result;
    renderSummary();
    renderRuns();
    showOutput(result);
    setStatus("familyStatus", `Live preview updated: ${result.verdict}.`, "success");
  } catch (error) {
    if (requestToken !== state.previewRequestToken) {
      return;
    }
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function optimizeLever(lever) {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    setStatus("familyStatus", "Select a mutation base and dataset first.", "error");
    return;
  }
  if (optimizationInFlight) {
    return;
  }
  setOptimizationBusy(true, lever);
  setOptimizationStatus(`Optimizing ${lever}. Testing candidate values against the selected dataset...`);
  try {
    const result = await fetchJson(`/api/versions/${version.version_id}/optimize-lever`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        lever,
        parameter_overrides: collectOverrides(),
      }),
    });
    const current = currentVersion().spec_json.parameters[lever];
    state.workingParameters[lever] = castValue(result.best.value, current);
    state.previewResult = {
      mode: "preview",
      family_id: result.family_id,
      base_version_id: result.base_version_id,
      dataset_id: result.dataset_id,
      parameter_overrides: result.best.parameter_overrides,
      spec: result.best_spec,
      metrics: result.best.metrics,
      comparison: result.best.comparison,
      verdict: result.best.verdict,
    };
    renderSummary();
    renderTuningEdges();
    renderRuns();
    showOutput(result);
    const search = result.search || {};
    const rangeText =
      search.min !== null && search.min !== undefined ? ` across ${search.min}-${search.max}` : "";
    const eligibleText =
      result.eligible_count !== undefined
        ? ` ${result.eligible_count} met the evidence gates. Selection: ${result.selection_mode}.`
        : "";
    setStatus(
      "familyStatus",
      `${lever} optimized to ${result.best.value}. Tested ${result.candidates.length} candidates${rangeText}.${eligibleText}`,
      "success",
    );
    setOptimizationStatus(
      `${lever} optimized to ${result.best.value}. Tested ${result.candidates.length} candidates${rangeText}.${eligibleText}`,
      "success",
    );
    clearOptimizationStatus(9000);
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
    setOptimizationStatus(`${lever} optimization failed: ${error.message}`, "error");
  } finally {
    setOptimizationBusy(false);
  }
}

function applyOptimizeAllResult(result, recovered = false, startingParameters = null) {
  const baseParameters = startingParameters || currentVersion().spec_json.parameters;
  state.workingParameters = { ...baseParameters, ...result.parameter_overrides };
  state.previewResult = result.preview;
  renderSummary();
  renderTuningEdges();
  renderRuns();
  showOutput(result);

  const tunedCount = Object.entries(result.parameter_overrides).filter(
    ([key, value]) => JSON.stringify(value) !== JSON.stringify(baseParameters[key]),
  ).length;
  const selectedCount = Object.keys(result.parameter_overrides).length;
  const fallbackCount = Number(result.research_fallback_steps || 0);
  const eligibleCount = Number(result.eligible_steps || 0);
  const modeNote = fallbackCount
    ? `${fallbackCount} research fallback steps, ${eligibleCount} production-eligible steps`
    : `${eligibleCount} production-eligible steps`;
  const selectedNote =
    selectedCount === tunedCount ? "" : `; ${selectedCount} selected values matched or filled the base`;
  const recoveredNote = recovered ? " Recovered completed preview from backend." : "";
  const rejectedNote = result.final_candidate_rejected
    ? " Optimized candidate failed production gates, so the starting values were kept."
    : "";
  const robustness = result.robustness_evidence;
  const robustnessSummary = robustness?.summary;
  const robustnessNote = robustnessSummary
    ? ` Full robustness: walk-forward ${robustnessSummary.walk_forward_passed}/${robustnessSummary.walk_forward_total}, anchored OOS ${robustnessSummary.anchored_train_test_passed}/${robustnessSummary.anchored_train_test_total}, cost stress ${robustnessSummary.cost_stress_passed}/${robustnessSummary.cost_stress_total}; ${robustnessSummary.passed ? "survived" : "best finalist still needs review"}.`
    : robustness
      ? ` Cost stress ${robustness.cost_stress_passed}/${robustness.cost_stress_total}${robustness.all_cost_stress_passed ? "; repair survived available checks" : "; best available repair still needs review"}.`
      : "";
  const message = `Optimization complete. Applied ${tunedCount} changed values (${modeNote}${selectedNote}).${rejectedNote}${robustnessNote}${recoveredNote}`;
  const completionTone = robustnessSummary && !robustnessSummary.passed ? "error" : "success";
  setStatus("familyStatus", message, completionTone);
  setOptimizationStatus(message, completionTone);
  clearOptimizationStatus(9000);
}

function optimizationProgressMessage(job) {
  const startedAt = job.created_at ? new Date(job.created_at).toLocaleTimeString() : "unknown time";
  const progress = job.progress || {};
  const progressText = progress.lever
    ? ` Pass ${progress.pass}/${progress.passes}, parameter ${progress.edge_index}/${progress.total_edges}: optimizing ${progress.lever}${progress.next_lever ? `; next ${progress.next_lever}` : "; final parameter in pass"}.`
    : " Waiting for first parameter...";
  return `Optimization job ${job.job_id} is ${job.status}. Started ${startedAt}.${progressText}`;
}

async function optimizeAll(optimizationMode = "production") {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    setStatus("familyStatus", "Select a mutation base and dataset first.", "error");
    return;
  }
  if (optimizationInFlight) {
    return;
  }
  let reattachedExistingJob = false;
  setOptimizationBusy(true);
  const startingParameters = { ...currentVersion().spec_json.parameters, ...collectOverrides() };
  const modeLabel = optimizationMode === "research"
    ? "baseline research"
    : optimizationMode === "robustness_repair"
      ? "robustness repair"
      : "production";
  setOptimizationStatus(`Starting background two-pass ${modeLabel} optimization...`);
  try {
    const job = await fetchJson(`/api/versions/${version.version_id}/optimize-all/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        parameter_overrides: collectOverrides(),
        passes: 2,
        optimization_mode: optimizationMode,
      }),
    });
    setOptimizationStatus(optimizationProgressMessage(job));
    const result = await waitForOptimizationJob(job.job_id);
    applyOptimizeAllResult(result, false, startingParameters);
  } catch (error) {
    if (error.status === 409) {
      setStatus("familyStatus", "An optimization is already running. Reattached to progress updates.", "");
      setOptimizationStatus(error.message, "working");
      await attachActiveOptimizationIfAny();
      reattachedExistingJob = true;
      return;
    }
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
    setOptimizationStatus(`Optimization failed: ${error.message}`, "error");
  } finally {
    if (!reattachedExistingJob) {
      setOptimizationBusy(false);
    }
  }
}

async function waitForOptimizationJob(jobId) {
  let connectionFailures = 0;
  while (true) {
    await wait(OPTIMIZATION_POLL_MS);
    let job;
    try {
      job = await fetchJson(`/api/optimization-jobs/${jobId}`);
      connectionFailures = 0;
    } catch (error) {
      connectionFailures += 1;
      setOptimizationStatus(
        `Optimization job ${jobId} is still being tracked, but the browser lost contact (${connectionFailures}). Retrying...`,
        "working",
      );
      continue;
    }
    if (job.status === "completed") {
      return job.result;
    }
    if (job.status === "failed") {
      throw new Error(job.error || "Optimization job failed.");
    }
    if (job.progress) {
      renderOptimizationProgress({ ...job.progress, active: true, job_id: job.job_id });
    } else {
      setOptimizationStatus(optimizationProgressMessage(job));
    }
  }
}

async function runRobustnessGate() {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    setStatus("familyStatus", "Select a mutation base and dataset first.", "error");
    return;
  }
  setStatus("familyStatus", "Running walk-forward and cost-stress robustness checks...", "");
  try {
    const result = await fetchJson(`/api/versions/${version.version_id}/robustness`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        parameter_overrides: collectOverrides(),
      }),
    });
    showOutput(result);
    const summary = result.summary || {};
    setStatus(
      "familyStatus",
      `Robustness: ${summary.label}. Walk-forward ${summary.walk_forward_passed}/${summary.walk_forward_total}; anchored OOS ${summary.anchored_train_test_passed}/${summary.anchored_train_test_total}; cost stress ${summary.cost_stress_passed}/${summary.cost_stress_total}.`,
      summary.passed ? "success" : "error",
    );
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

function schedulePreview(immediate = false) {
  if (previewTimer) {
    clearTimeout(previewTimer);
  }
  if (immediate) {
    executePreview(true);
    return;
  }
  setStatus("familyStatus", "Refreshing live preview...", "");
  previewTimer = setTimeout(() => executePreview(false), 350);
}

function resetTune() {
  syncWorkingParameters();
  state.previewResult = null;
  renderSummary();
  renderTuningEdges();
  renderRuns();
  setStatus("familyStatus", "Working parameters reset to the selected mutation base.", "success");
}

function applyProductionDefaults() {
  const version = currentVersion();
  if (!version) {
    setStatus("familyStatus", "Select a mutation base first.", "error");
    return;
  }
  state.workingParameters = {
    ...state.workingParameters,
    sizing_mode: "fixed_risk_pct",
    execution_model: "mt5_bar_proxy",
    risk_pct: 0.005,
    max_leverage: 1,
    notional_pct: 0.25,
  };
  renderTuningEdges();
  schedulePreview(true);
  setStatus("familyStatus", "Production defaults applied: MT5 proxy execution, fixed risk 0.5%, max exposure 1x.", "success");
}

async function saveTune() {
  const version = currentVersion();
  const datasetId = selectedDatasetId();
  if (!version || !datasetId) {
    setStatus("familyStatus", "Select a family and dataset first.", "error");
    return;
  }
  const overrides = collectOverrides();
  if (!Object.keys(overrides).length) {
    setStatus("familyStatus", "There is no parameter change to save.", "error");
    return;
  }
  setStatus("familyStatus", "Saving tuned child and persisting its run...", "");
  try {
    const result = await fetchJson(`/api/versions/${version.version_id}/save-tuned`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        parameter_overrides: overrides,
      }),
    });
    showOutput(result);
    setStatus("familyStatus", `Tuned child saved: ${result.version_id}.`, "success");
    await refreshFamilyDetail();
    versionSelect.value = result.version_id;
    await refreshSelectedVersion();
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function registerBaseline() {
  setStatus("registerStatus", "Registering baseline...", "");
  try {
    const payload = {
      family_id: document.getElementById("registerFamilyId").value.trim(),
      title: document.getElementById("registerTitle").value.trim(),
      asset: document.getElementById("registerAsset").value.trim(),
      venue: document.getElementById("registerVenue").value.trim(),
      timeframe: document.getElementById("registerTimeframe").value.trim(),
      version_name: document.getElementById("registerVersionName").value.trim(),
      source_code: document.getElementById("registerSourceCode").value,
      spec_json: JSON.parse(document.getElementById("registerSpecJson").value),
      causal_story: document.getElementById("registerCausalStory").value.trim(),
      notes: document.getElementById("registerNotes").value.trim(),
    };
    const result = await fetchJson("/api/families/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showOutput(result);
    setStatus("registerStatus", `Registered family ${payload.family_id}.`, "success");
    await refreshAll();
    familySelect.value = payload.family_id;
    await refreshFamilyDetail();
  } catch (error) {
    setStatus("registerStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function handleTableClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }
  const action = button.dataset.action;
  try {
    if (action === "use-dataset") {
      datasetSelect.value = button.dataset.id;
      setStatus("familyStatus", "Dataset selected.", "success");
      schedulePreview(true);
      return;
    }
    if (action === "delete-dataset") {
      await fetchJson(`/api/datasets/${button.dataset.id}`, { method: "DELETE" });
      await refreshAll();
      showOutput({ status: "deleted", dataset_id: button.dataset.id });
      return;
    }
    if (action === "apply-edge") {
      const key = button.dataset.key;
      const current = currentVersion().spec_json.parameters[key];
      state.workingParameters[key] = castValue(button.dataset.value, current);
      renderTuningEdges();
      schedulePreview();
      return;
    }
    if (action === "reset-edge") {
      const key = button.dataset.key;
      const current = currentVersion().spec_json.parameters[key];
      state.workingParameters[key] = castValue(button.dataset.value, current);
      renderTuningEdges();
      schedulePreview();
      return;
    }
    if (action === "optimize-lever") {
      await optimizeLever(button.dataset.key);
      return;
    }
    if (action === "save-preview-now") {
      await saveTune();
      return;
    }
    if (action === "pick-version") {
      versionSelect.value = button.dataset.version;
      await refreshSelectedVersion();
      setStatus("familyStatus", "Mutation base switched to the selected saved version.", "success");
      return;
    }
    if (action === "select-version") {
      versionSelect.value = button.dataset.version;
      await refreshSelectedVersion();
      setStatus("familyStatus", "Mutation base switched to the selected saved version.", "success");
      return;
    }
    if (action === "promote-version") {
      const result = await fetchJson(
        `/api/families/${button.dataset.family}/promote/${button.dataset.version}`,
        { method: "POST" },
      );
      showOutput(result);
      await refreshAll();
      return;
    }
    if (action === "delete-version") {
      await fetchJson(`/api/versions/${button.dataset.version}`, { method: "DELETE" });
      await refreshFamilyDetail();
      showOutput({ status: "deleted", version_id: button.dataset.version });
      setStatus("familyStatus", "Saved version deleted.", "success");
      return;
    }
    if (action === "delete-run") {
      await fetchJson(`/api/runs/${button.dataset.id}`, { method: "DELETE" });
      await refreshFamilyDetail();
      showOutput({ status: "deleted", run_id: button.dataset.id });
      return;
    }
    if (action === "execution-audit") {
      setStatus("familyStatus", "Running execution feasibility audit for the saved run...", "");
      const result = await fetchJson(`/api/runs/${button.dataset.id}/execution-audit`, { method: "POST" });
      showOutput(result);
      setStatus(
        "familyStatus",
        `Execution audit ${result.status}. ${result.failures?.length || 0} failures; ${result.warnings?.length || 0} warnings.`,
        result.passed ? "success" : "error",
      );
    }
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
  }
}

async function handlePromptClick(event) {
  const button = event.target.closest("[data-action='copy-prompt']");
  if (!button) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  const prompt = promptsList._visiblePrompts?.[Number(button.dataset.promptIndex)];
  if (!prompt) {
    setStatus("familyStatus", "Prompt not found.", "error");
    return;
  }
  const originalLabel = button.textContent;
  try {
    await copyTextToClipboard(prompt.content);
    button.textContent = "Copied";
    setStatus("familyStatus", `${prompt.name} copied to clipboard.`, "success");
    window.setTimeout(() => {
      button.textContent = originalLabel;
    }, 1400);
  } catch (error) {
    setStatus("familyStatus", `Clipboard copy failed: ${error.message}`, "error");
  }
}

function bindClick(id, handler) {
  const node = document.getElementById(id);
  if (node) {
    node.addEventListener("click", handler);
  }
}

function handleWorkingInput(event) {
  const control = event.target.closest("[data-working-key]");
  if (!control) {
    return;
  }
  const key = control.dataset.workingKey;
  const current = currentVersion()?.spec_json?.parameters?.[key];
  if (current === undefined) {
    return;
  }
  const edge = edgeForKey(key);
  const nextValue = clampToEdge(castValue(control.value, current), edge);
  state.workingParameters[key] = nextValue;
  if (typeof nextValue === "number" && String(nextValue) !== control.value) {
    control.value = nextValue;
  }
  schedulePreview();
}

bindClick("refreshButton", refreshAll);
bindClick("downloadButton", downloadDataset);
bindClick("importMt5Button", importMt5Dataset);
bindClick("runParentButton", runParent);
bindClick("productionDefaultsButton", applyProductionDefaults);
bindClick("robustnessButton", runRobustnessGate);
bindClick("resetTuneButton", resetTune);
bindClick("saveTuneButton", saveTune);
optimizeResearchButton.addEventListener("click", () => optimizeAll("research"));
optimizeAllButton.addEventListener("click", () => optimizeAll("production"));
optimizeRobustnessButton.addEventListener("click", () => optimizeAll("robustness_repair"));
bindClick("registerButton", registerBaseline);
familySelect.addEventListener("change", refreshFamilyDetail);
versionSelect.addEventListener("change", refreshSelectedVersion);
datasetSelect.addEventListener("change", () => schedulePreview(true));
fullHistoryInput.addEventListener("change", syncFullHistoryBars);
datasetsTable.addEventListener("click", handleTableClick);
proposalsTable.addEventListener("click", handleTableClick);
proposalsTable.addEventListener("input", handleWorkingInput);
proposalsTable.addEventListener("change", handleWorkingInput);
runsTable.addEventListener("click", handleTableClick);
versionsTable.addEventListener("click", handleTableClick);
promptsList.addEventListener("click", handlePromptClick);

syncFullHistoryBars();

refreshAll().catch((error) => {
  showOutput({ error: error.message });
  setStatus("familyStatus", error.message, "error");
});
attachActiveOptimizationIfAny();
