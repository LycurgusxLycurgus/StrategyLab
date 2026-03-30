const state = {
  strategy: null,
  datasets: [],
  runs: [],
  paperRuns: [],
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.status === 204 ? null : response.json();
}

function el(id) {
  return document.getElementById(id);
}

function setOutput(payload) {
  el("outputBox").textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function renderStrategy() {
  const summary = el("strategySummary");
  if (!state.strategy) {
    summary.textContent = "Loading strategy...";
    return;
  }
  summary.innerHTML = `
    <div class="metric"><span>Strategy</span><strong>${state.strategy.title}</strong></div>
    <div class="metric"><span>Instrument</span><strong>${state.strategy.instrument}</strong></div>
    <div class="metric"><span>Timeframe</span><strong>${state.strategy.timeframe}</strong></div>
    <div class="metric"><span>White-box</span><strong>Explicit</strong></div>
    <div class="metric"><span>Hybrid model</span><strong>Gradient boosted gate</strong></div>
    <div class="metric"><span>Black-box role</span><strong>Scoring only</strong></div>
  `;

  const symbolSelect = el("symbolSelect");
  const profileSelect = el("profileSelect");
  const providerSelect = el("providerSelect");
  symbolSelect.innerHTML = state.strategy.data_options
    .map((item) => `<option value="${item.symbol}">${item.label}</option>`)
    .join("");
  providerSelect.innerHTML = state.strategy.data_providers
    .map((item) => `<option value="${item.provider}">${item.label}</option>`)
    .join("");
  profileSelect.innerHTML = Object.keys(state.strategy.profiles)
    .map((profile) => `<option value="${profile}">${profile}</option>`)
    .join("");
}

function renderDatasets() {
  const datasetSelect = el("datasetSelect");
  const table = el("datasetsTable");
  datasetSelect.innerHTML = state.datasets
    .map((dataset) => `<option value="${dataset.dataset_id}">${dataset.name} (${dataset.rows_count} bars)</option>`)
    .join("");
  table.innerHTML = state.datasets
    .map(
      (dataset) => `
        <tr>
          <td>${dataset.name}</td>
          <td>${dataset.symbol}</td>
          <td>${dataset.rows_count}</td>
          <td>${new Date(dataset.created_at).toLocaleString()}</td>
          <td><button class="danger" data-delete-dataset="${dataset.dataset_id}">Delete</button></td>
        </tr>
      `
    )
    .join("");
}

function renderRuns() {
  const table = el("runsTable");
  table.innerHTML = state.runs
    .map(
      (run) => `
        <tr>
          <td>${run.kind}</td>
          <td>${run.verdict}</td>
          <td>${run.metrics.sharpe}</td>
          <td>${run.metrics.trades}</td>
          <td>
            <div class="stack-actions">
              <a href="/api/artifacts/runs/${run.run_id}.json" target="_blank">artifact</a>
              <a href="/api/artifacts/reports/${run.run_id}.md" target="_blank">report</a>
              <button class="ghost" data-debug-trace="${run.run_id}">debug trace</button>
              <button class="ghost" data-tv-debug="${run.run_id}">tv debug</button>
            </div>
          </td>
          <td><button class="danger" data-delete-run="${run.run_id}">Delete</button></td>
        </tr>
      `
    )
    .join("");
}

function renderPaper() {
  const table = el("paperTable");
  table.innerHTML = state.paperRuns
    .map(
      (run) => `
        <tr>
          <td>${run.paper_id}</td>
          <td>${run.metrics.trades}</td>
          <td>${run.metrics.sharpe}</td>
          <td><a href="/api/artifacts/paper/${run.paper_id}.json" target="_blank">artifact</a></td>
        </tr>
      `
    )
    .join("");
}

async function refresh() {
  const [strategy, datasets, runs, paperRuns] = await Promise.all([
    api("/api/strategies/current"),
    api("/api/data/datasets"),
    api("/api/backtests/runs"),
    api("/api/paper/runs"),
  ]);
  state.strategy = strategy;
  state.datasets = datasets;
  state.runs = runs;
  state.paperRuns = paperRuns;
  renderStrategy();
  renderDatasets();
  renderRuns();
  renderPaper();
}

async function onDownload() {
  el("downloadStatus").textContent = "Downloading 15m market data...";
  try {
    const payload = await api("/api/data/download", {
      method: "POST",
      body: JSON.stringify({
        symbol: el("symbolSelect").value,
        timeframe: "15m",
        lookback_days: Number(el("lookbackSelect").value),
        provider: el("providerSelect").value,
      }),
    });
    el("downloadStatus").textContent = `Dataset ready via ${payload.name.split("-")[0]}: ${payload.name}`;
    setOutput(payload);
    await refresh();
  } catch (error) {
    el("downloadStatus").textContent = `Download failed: ${error.message}`;
  }
}

async function onWhiteBox() {
  el("whiteboxStatus").textContent = "Running white-box baseline...";
  try {
    const payload = await api("/api/backtests/whitebox", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: el("datasetSelect").value,
        profile: el("profileSelect").value,
      }),
    });
    el("whiteboxStatus").textContent = `Baseline ready. Verdict: ${payload.verdict}`;
    setOutput(payload);
    await refresh();
  } catch (error) {
    el("whiteboxStatus").textContent = `Baseline failed: ${error.message}`;
  }
}

async function onImportCsv() {
  const file = el("csvFileInput").files[0];
  if (!file) {
    el("importStatus").textContent = "Choose a CSV file first.";
    return;
  }
  el("importStatus").textContent = "Importing CSV dataset...";
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("symbol", el("symbolSelect").value);
    form.append("timeframe", "15m");
    form.append("name", el("csvNameInput").value || file.name.replace(/\.csv$/i, ""));
    const response = await fetch("/api/data/import-csv", {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const payload = await response.json();
    el("importStatus").textContent = `CSV imported: ${payload.name}`;
    setOutput(payload);
    await refresh();
  } catch (error) {
    el("importStatus").textContent = `CSV import failed: ${error.message}`;
  }
}

async function onHybrid() {
  el("hybridStatus").textContent = "Training and evaluating hybrid gate...";
  try {
    const payload = await api("/api/backtests/hybrid", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: el("datasetSelect").value,
        profile: el("profileSelect").value,
      }),
    });
    el("hybridStatus").textContent = `Hybrid ready. Verdict: ${payload.verdict}`;
    setOutput(payload);
    await refresh();
  } catch (error) {
    el("hybridStatus").textContent = `Hybrid failed: ${error.message}`;
  }
}

async function onPaper() {
  el("paperStatus").textContent = "Simulating paper week...";
  try {
    const payload = await api("/api/paper/run", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: el("datasetSelect").value,
        profile: el("profileSelect").value,
      }),
    });
    el("paperStatus").textContent = `Paper week ready. Trades: ${payload.metrics.trades}`;
    setOutput(payload);
    await refresh();
  } catch (error) {
    el("paperStatus").textContent = `Paper week failed: ${error.message}`;
  }
}

async function onTvDebug(runId) {
  try {
    const payload = await api(`/api/backtests/runs/${runId}/tv-debug`, {
      method: "POST",
    });
    setOutput(payload);
    window.open(`/api/artifacts/reports/${runId}_tv_debug.pine`, "_blank");
  } catch (error) {
    setOutput(`TradingView debug export failed: ${error.message}`);
  }
}

async function onDebugTrace(runId) {
  try {
    const payload = await api(`/api/backtests/runs/${runId}/debug-trace`, {
      method: "POST",
    });
    setOutput(payload);
    const filename = payload.trace_path.split(/[\\/]/).pop();
    window.open(`/api/artifacts/${payload.artifact_group || "reports"}/${filename}`, "_blank");
  } catch (error) {
    setOutput(`Debug trace export failed: ${error.message}`);
  }
}

document.addEventListener("click", async (event) => {
  const target = event.target;
  if (target.dataset.deleteDataset) {
    await api(`/api/data/datasets/${target.dataset.deleteDataset}`, { method: "DELETE" });
    await refresh();
    return;
  }
  if (target.dataset.deleteRun) {
    await api(`/api/backtests/runs/${target.dataset.deleteRun}`, { method: "DELETE" });
    await refresh();
    return;
  }
  if (target.dataset.debugTrace) {
    await onDebugTrace(target.dataset.debugTrace);
    return;
  }
  if (target.dataset.tvDebug) {
    await onTvDebug(target.dataset.tvDebug);
  }
});

el("downloadButton").addEventListener("click", onDownload);
el("importCsvButton").addEventListener("click", onImportCsv);
el("whiteboxButton").addEventListener("click", onWhiteBox);
el("hybridButton").addEventListener("click", onHybrid);
el("paperButton").addEventListener("click", onPaper);
el("refreshButton").addEventListener("click", refresh);

refresh().catch((error) => {
  setOutput(`Failed to boot UI: ${error.message}`);
});
