const state = {
  families: [],
  datasets: [],
  familyDetail: null,
  prompts: [],
  workingParameters: {},
  previewResult: null,
  previewRequestToken: 0,
};

const outputBox = document.getElementById("outputBox");
const summaryGrid = document.getElementById("summaryGrid");
const metricsGrid = document.getElementById("metricsGrid");
const familySelect = document.getElementById("familySelect");
const versionSelect = document.getElementById("versionSelect");
const datasetSelect = document.getElementById("datasetSelect");
const familyMeta = document.getElementById("familyMeta");
const datasetsTable = document.getElementById("datasetsTable");
const proposalsTable = document.getElementById("proposalsTable");
const runsTable = document.getElementById("runsTable");
const versionsTable = document.getElementById("versionsTable");
const promptsList = document.getElementById("promptsList");
let previewTimer = null;

function setStatus(elementId, message, tone = "") {
  const node = document.getElementById(elementId);
  node.textContent = message;
  node.className = `status ${tone}`.trim();
}

function showOutput(payload) {
  outputBox.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
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
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
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
  return selectedVersionRuns()[0]?.metrics_json || null;
}

function activeMetricSource() {
  return state.previewResult ? "Live preview" : "Saved run";
}

function renderMetrics() {
  const metrics = activeMetrics();
  if (!metrics) {
    metricsGrid.innerHTML = `<div class="empty-state">Run the selected version or change a tuning value to populate the performance panel.</div>`;
    return;
  }
  const comparison = state.previewResult?.comparison || null;
  const items = [
    ["Source", activeMetricSource()],
    ["Net PnL", formatNumber(metrics.net_pnl)],
    ["Return %", `${formatNumber(metrics.return_pct)}%`],
    ["Profit Factor", formatNumber(metrics.profit_factor, 4)],
    ["Expected Payoff", formatNumber(metrics.expected_payoff)],
    ["Trades", formatNumber(metrics.total_trades, 0)],
    ["Win Rate", `${formatNumber(metrics.percent_profitable)}%`],
    ["Max Drawdown %", `${formatNumber(metrics.max_equity_drawdown_pct)}%`],
    ["Sharpe", formatNumber(metrics.sharpe, 4)],
    ["Sortino", formatNumber(metrics.sortino, 4)],
    ["PF Delta", comparison ? formatNumber(comparison.profit_factor_delta, 4) : "n/a"],
    ["DD Delta", comparison ? `${formatNumber(comparison.drawdown_pct_delta)}%` : "n/a"],
  ];
  metricsGrid.innerHTML = items
    .map(
      ([label, value]) => `
        <article class="metric-card">
          <span>${label}</span>
          <strong class="numeric">${value}</strong>
        </article>
      `,
    )
    .join("");
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
  const latestRun = selectedVersionRuns()[0];
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
    proposalsTable.innerHTML = `<tr><td colspan="6" class="empty-state">No tuning edges for this family yet.</td></tr>`;
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
      } else if (edge.value_type === "enum") {
        const choices = [current, ...edge.alternatives].filter((value, index, arr) => arr.indexOf(value) === index);
        control = `
          <select data-working-key="${edge.lever}">
            ${choices
              .map((value) => `<option value="${value}" ${String(working) === String(value) ? "selected" : ""}>${value}</option>`)
              .join("")}
          </select>
        `;
      } else {
        const step = edge.value_type === "float" ? "0.1" : "1";
        control = `<input data-working-key="${edge.lever}" type="number" step="${step}" value="${working}" />`;
      }
      const downButton =
        edge.suggested_down !== null
          ? `<button class="ghost" data-action="apply-edge" data-key="${edge.lever}" data-value="${edge.suggested_down}">Use ${edge.suggested_down}</button>`
          : "";
      const upButton =
        edge.suggested_up !== null
          ? `<button class="ghost" data-action="apply-edge" data-key="${edge.lever}" data-value="${edge.suggested_up}">Use ${edge.suggested_up}</button>`
          : "";
      return `
        <tr>
          <td class="numeric">${edge.priority}</td>
          <td>
            <strong>${edge.lever}</strong>
            <div>${edge.rationale}</div>
          </td>
          <td class="numeric">${current}</td>
          <td>${edge.suggested_down ?? "n/a"}</td>
          <td>${edge.suggested_up ?? "n/a"}</td>
          <td>
            <div class="form-stack">
              ${control}
              <div class="table-actions">
                ${downButton}
                ${upButton}
                <button class="ghost" data-action="reset-edge" data-key="${edge.lever}" data-value="${current}">Reset</button>
              </div>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
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
                <button class="danger" data-action="delete-run" data-id="${run.run_id}">Delete</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderPrompts() {
  const prompts = state.prompts.length ? state.prompts : state.familyDetail?.prompts || [];
  promptsList.innerHTML = prompts
    .map(
      (prompt) => `
        <details>
          <summary>${prompt.name}</summary>
          <pre>${escapeHtml(prompt.content)}</pre>
        </details>
      `,
    )
    .join("");
}

function castValue(raw, currentValue) {
  if (typeof currentValue === "boolean") {
    return raw === true || raw === "true";
  }
  if (typeof currentValue === "number") {
    return Number(raw);
  }
  return raw;
}

function collectOverrides() {
  const version = currentVersion();
  if (!version) {
    return {};
  }
  const base = version.spec_json?.parameters || {};
  const overrides = {};
  for (const [key, value] of Object.entries(state.workingParameters)) {
    if (String(value) !== String(base[key])) {
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
  const payload = {
    symbol: document.getElementById("symbolInput").value.trim().toUpperCase(),
    timeframe: document.getElementById("timeframeSelect").value,
    bars: Number(document.getElementById("barsInput").value),
    full_history: document.getElementById("fullHistoryInput").checked,
    name: document.getElementById("datasetNameInput").value.trim() || null,
  };
  try {
    const result = await fetchJson("/api/datasets/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showOutput(result);
    setStatus("downloadStatus", `Dataset ready: ${result.name} (${result.rows_count} rows).`, "success");
    await refreshAll();
    datasetSelect.value = result.dataset_id;
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
  if (!Object.keys(overrides).length) {
    state.previewResult = null;
    renderSummary();
    renderRuns();
    if (showMessage) {
      setStatus("familyStatus", "Working values match the frozen parent.", "success");
    }
    return;
  }
  const requestToken = ++state.previewRequestToken;
  if (showMessage) {
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
  renderTuningEdges();
  renderRuns();
  setStatus("familyStatus", "Working parameters reset to the selected mutation base.", "success");
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
    }
  } catch (error) {
    setStatus("familyStatus", error.message, "error");
    showOutput({ error: error.message });
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
  state.workingParameters[key] = castValue(control.value, current);
  schedulePreview();
}

document.getElementById("refreshButton").addEventListener("click", refreshAll);
document.getElementById("downloadButton").addEventListener("click", downloadDataset);
document.getElementById("runParentButton").addEventListener("click", runParent);
document.getElementById("resetTuneButton").addEventListener("click", resetTune);
document.getElementById("saveTuneButton").addEventListener("click", saveTune);
document.getElementById("registerButton").addEventListener("click", registerBaseline);
familySelect.addEventListener("change", refreshFamilyDetail);
versionSelect.addEventListener("change", refreshSelectedVersion);
datasetSelect.addEventListener("change", () => schedulePreview(true));
datasetsTable.addEventListener("click", handleTableClick);
proposalsTable.addEventListener("click", handleTableClick);
proposalsTable.addEventListener("input", handleWorkingInput);
proposalsTable.addEventListener("change", handleWorkingInput);
runsTable.addEventListener("click", handleTableClick);
versionsTable.addEventListener("click", handleTableClick);

refreshAll().catch((error) => {
  showOutput({ error: error.message });
  setStatus("familyStatus", error.message, "error");
});
