let state = {
  datasets: [],
  families: [],
  runs: [],
  graveyard: [],
};

async function requestJson(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.message || JSON.stringify(body));
  }
  return body;
}

async function requestDelete(path) {
  const response = await fetch(path, { method: "DELETE" });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.message || JSON.stringify(body));
  }
  return body;
}

function writeOutput(value) {
  document.getElementById("output").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function familyById(familyId) {
  return state.families.find((item) => item.family_id === familyId);
}

function compatibleDatasets(familyId) {
  const family = familyById(familyId);
  if (!family) {
    return state.datasets;
  }
  return state.datasets.filter((dataset) => (family.supported_timeframes || [family.timeframe]).includes(dataset.timeframe));
}

function buildBinanceName() {
  const symbol = document.getElementById("binance-symbol").value.trim().toLowerCase();
  const timeframe = document.getElementById("binance-timeframe").value.trim().toLowerCase();
  return `binance-${symbol}-${timeframe}`;
}

function classExplanation(classType) {
  if (classType === "white_box") {
    return "White-box: explicit, interpretable rules.";
  }
  if (classType === "hybrid") {
    return "Hybrid: explicit rules plus statistical filters.";
  }
  return "Black-box: model-driven signals with low interpretability.";
}

function minimumBarsText(family) {
  const supported = family.supported_timeframes || [family.timeframe];
  return supported.map((timeframe) => `${timeframe}: ${family.min_bars_by_timeframe[timeframe] || "?"}`).join(", ");
}

function parameterSummary(parameters) {
  return Object.entries(parameters || {}).map(([key, value]) => `${key}=${value}`).join(", ");
}

function listHtml(items) {
  if (!items || !items.length) {
    return "<p>None.</p>";
  }
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function objectHtml(obj) {
  const entries = Object.entries(obj || {});
  if (!entries.length) {
    return "<p>None.</p>";
  }
  return `<ul>${entries.map(([key, value]) => `<li><strong>${escapeHtml(key)}:</strong> ${escapeHtml(Array.isArray(value) ? value.join(", ") : JSON.stringify(value))}</li>`).join("")}</ul>`;
}

function renderReview(reviewArtifact) {
  const panel = document.getElementById("review-panel");
  const summary = document.getElementById("review-summary");
  const content = document.getElementById("review-content");
  if (!reviewArtifact || !reviewArtifact.review) {
    panel.hidden = true;
    panel.open = false;
    content.innerHTML = "";
    summary.textContent = "> Show review";
    return;
  }
  const review = reviewArtifact.review;
  const conjectures = (review.conjectures || []).map((item) => (
    `<li><strong>${escapeHtml(item.title || "Untitled")}</strong> (${escapeHtml(item.confidence || "unknown")} confidence): `
    + `${escapeHtml(item.explanation || "")} Expected effect: ${escapeHtml(item.expected_effect || "")}</li>`
  )).join("");
  const safeChanges = listHtml(review.coding_agent_brief?.safe_changes || []);
  const avoidChanges = listHtml(review.coding_agent_brief?.avoid || []);
  panel.hidden = false;
  summary.textContent = `> Show review (${reviewArtifact.artifact_id})`;
  content.innerHTML = `
    <p><strong>Family diagnosis:</strong> ${escapeHtml(review.family_diagnosis || "No diagnosis returned.")}</p>
    <p><strong>Grid patch reason:</strong> ${escapeHtml(review.parameter_grid_patch?.reason || "No parameter-grid reason returned.")}</p>
    <h3>Parameter Grid</h3>
    <p><strong>Keep</strong></p>
    ${objectHtml(review.parameter_grid_patch?.keep || {})}
    <p><strong>Expand</strong></p>
    ${objectHtml(review.parameter_grid_patch?.expand || {})}
    <p><strong>Drop</strong></p>
    ${listHtml(review.parameter_grid_patch?.drop || [])}
    <h3>Conjectures</h3>
    ${conjectures ? `<ul>${conjectures}</ul>` : "<p>None.</p>"}
    <h3>Black-Box Notes</h3>
    ${listHtml(review.black_box_meta_notes || [])}
    <h3>Coding Agent Brief</h3>
    <p><strong>Priority:</strong> ${escapeHtml(review.coding_agent_brief?.priority || "No priority returned.")}</p>
    <p><strong>Safe changes</strong></p>
    ${safeChanges}
    <p><strong>Avoid</strong></p>
    ${avoidChanges}
    <p><strong>Artifact path:</strong> ${escapeHtml(reviewArtifact.artifact_path || "")}</p>
  `;
}

function optimizationGridSummary(family) {
  const grid = family.optimization_grid || {};
  const entries = Object.entries(grid);
  if (!entries.length) {
    return "default-only";
  }
  return entries.map(([key, values]) => `${key}[${values.join(", ")}]`).join("; ");
}

function sweepVariantCount(family) {
  const grid = family.optimization_grid || {};
  const entries = Object.values(grid);
  if (!entries.length) {
    return 1;
  }
  return entries.reduce((total, values) => total * values.length, 1);
}

function updateFamilyHelp() {
  const family = familyById(document.getElementById("guided-family").value);
  const help = document.getElementById("guided-family-help");
  if (!family) {
    help.textContent = "Select a family to see its category, compatible timeframes, and minimum bars.";
    return;
  }
  const timeframeNotes = (family.supported_timeframes || [family.timeframe])
    .map((timeframe) => `${timeframe} requires at least ${family.min_bars_by_timeframe[timeframe] || "?"} bars`)
    .join("; ");
  help.textContent = `${family.title}. ${family.class_description || classExplanation(family.class_type)} Compatible timeframes: ${(family.supported_timeframes || [family.timeframe]).join(", ")}. ${timeframeNotes} Sweep variants: ${sweepVariantCount(family)}.`;
}

function updateCurrentDatasetText() {
  const target = document.getElementById("dataset-current");
  const datasetId = document.getElementById("guided-dataset").value;
  const dataset = state.datasets.find((item) => item.dataset_id === datasetId) || state.datasets[0];
  if (!dataset) {
    target.textContent = "No active dataset selected yet.";
    return;
  }
  target.textContent = `Current dataset: ${dataset.dataset_name} (${dataset.symbol}, ${dataset.timeframe}, ${dataset.row_count} bars).`;
}

function updateNextAction() {
  const target = document.getElementById("next-action");
  if (!state.datasets.length) {
    target.textContent = "Download real market data first.";
    return;
  }
  if (!state.runs.length) {
    target.textContent = "Pick a family, confirm the compatible dataset, and click Run Family Sweep.";
    return;
  }
  const latestRun = state.runs[0];
  if (latestRun.verdict === "rejected") {
    target.textContent = `Latest run ${latestRun.run_id} was rejected. Review the sweep and graveyard, then request an LLM review.`;
    return;
  }
  target.textContent = `Latest run ${latestRun.run_id} survived. Review the family with Gemini before changing the coded family.`;
}

function updateGuidedDatasetOptions(preferredDatasetId = "") {
  const familyId = document.getElementById("guided-family").value;
  const datasets = compatibleDatasets(familyId);
  const select = document.getElementById("guided-dataset");
  renderDatasetOptions(select, datasets, preferredDatasetId, "run-status", "No compatible dataset is available for this strategy yet.");
  updateCurrentDatasetText();
}

function updateReviewDatasetOptions(preferredDatasetId = "") {
  const familyId = document.getElementById("review-family").value;
  const datasets = compatibleDatasets(familyId);
  const select = document.getElementById("review-dataset");
  renderDatasetOptions(select, datasets, preferredDatasetId, "review-status", "No compatible dataset is available for this review yet.");
}

function renderDatasetOptions(select, datasets, preferredDatasetId, statusId, emptyMessage) {
  if (!datasets.length) {
    select.innerHTML = "";
    document.getElementById(statusId).textContent = emptyMessage;
    return;
  }
  select.innerHTML = datasets.map((item) => `<option value="${item.dataset_id}">${item.dataset_name} (${item.timeframe})</option>`).join("");
  const datasetIds = datasets.map((item) => item.dataset_id);
  if (preferredDatasetId && datasetIds.includes(preferredDatasetId)) {
    select.value = preferredDatasetId;
  }
}

async function refresh(preferredDatasetId = "") {
  const [datasets, families, runs, graveyard] = await Promise.all([
    requestJson("/api/data/datasets"),
    requestJson("/api/strategies/families"),
    requestJson("/api/backtests/runs"),
    requestJson("/api/lab/graveyard"),
  ]);
  state = { datasets, families, runs, graveyard };

  document.getElementById("guided-family").innerHTML = families.map((item) => `<option value="${item.family_id}">${item.family_id}</option>`).join("");
  document.getElementById("review-family").innerHTML = families.map((item) => `<option value="${item.family_id}">${item.family_id}</option>`).join("");
  updateGuidedDatasetOptions(preferredDatasetId);
  updateFamilyHelp();
  updateReviewDatasetOptions(preferredDatasetId);

  document.getElementById("datasets-table").innerHTML = datasets.map((item) => (
    `<tr><td>${item.dataset_id}</td><td>${item.dataset_name}</td><td>${item.symbol}</td><td>${item.timeframe}</td><td>${item.row_count}</td><td><button type="button" data-dataset-delete="${item.dataset_id}">Delete</button></td></tr>`
  )).join("");
  document.getElementById("families-table").innerHTML = families.map((item) => (
    `<tr><td>${item.family_id}</td><td>${item.title}</td><td>${item.class_type}<br>${classExplanation(item.class_type)}</td><td>${item.asset}</td><td>${(item.supported_timeframes || [item.timeframe]).join(", ")}</td><td>${minimumBarsText(item)}</td><td>${optimizationGridSummary(item)}</td></tr>`
  )).join("");
  document.getElementById("runs-table").innerHTML = runs.map((item) => (
    `<tr><td>${item.run_id}</td><td>${item.family_id}</td><td>${item.dataset_id}</td><td>${parameterSummary(item.parameters)}</td><td>${item.verdict}</td><td>${item.metrics.out_of_sample.sharpe}</td><td><button type="button" data-run-rerun="${item.run_id}">Rerun</button> <button type="button" data-run-delete="${item.run_id}">Delete</button></td></tr>`
  )).join("");
  document.getElementById("graveyard-table").innerHTML = graveyard.map((item) => (
    `<tr><td>${item.artifact_id}</td><td>${item.family_id || ""}</td><td>${item.source_run_id || ""}</td><td>${item.path}</td><td><button type="button" data-graveyard-delete="${item.artifact_id}">Delete</button></td></tr>`
  )).join("");

  document.querySelectorAll("[data-dataset-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const datasetId = button.getAttribute("data-dataset-delete");
        const result = await requestDelete(`/api/data/datasets/${datasetId}`);
        writeOutput(result);
        await refresh();
      } catch (error) {
        writeOutput(error.message);
      }
    });
  });

  document.querySelectorAll("[data-run-rerun]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const runId = button.getAttribute("data-run-rerun");
        const result = await requestJson(`/api/backtests/runs/${runId}/rerun`, { method: "POST" });
        writeOutput(result);
        await refresh(result.dataset_id);
        document.getElementById("run-status").textContent = `Rerun finished. Run id: ${result.run_id}. Verdict: ${result.verdict}. Trades: ${result.metrics.overall.trades}.`;
      } catch (error) {
        writeOutput(error.message);
      }
    });
  });

  document.querySelectorAll("[data-run-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const runId = button.getAttribute("data-run-delete");
        const result = await requestDelete(`/api/backtests/runs/${runId}`);
        writeOutput(result);
        await refresh();
      } catch (error) {
        writeOutput(error.message);
      }
    });
  });

  document.querySelectorAll("[data-graveyard-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const artifactId = button.getAttribute("data-graveyard-delete");
        const result = await requestDelete(`/api/lab/graveyard/${artifactId}`);
        writeOutput(result);
        await refresh();
      } catch (error) {
        writeOutput(error.message);
      }
    });
  });

  updateCurrentDatasetText();
  updateNextAction();
}

document.getElementById("refresh-button").addEventListener("click", async () => {
  try {
    await refresh();
    writeOutput("refreshed");
  } catch (error) {
    writeOutput(error.message);
  }
});

document.getElementById("guided-family").addEventListener("change", () => {
  updateGuidedDatasetOptions();
  updateFamilyHelp();
});

document.getElementById("review-family").addEventListener("change", () => {
  updateReviewDatasetOptions();
});

document.getElementById("guided-dataset").addEventListener("change", updateCurrentDatasetText);

document.getElementById("binance-dataset-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    document.getElementById("binance-status").textContent = "Downloading real market candles from Binance...";
    const payload = {
      symbol: document.getElementById("binance-symbol").value,
      timeframe: document.getElementById("binance-timeframe").value,
      dataset_name: buildBinanceName(),
      bars: Number(document.getElementById("binance-bars").value),
    };
    const result = await requestJson("/api/data/binance", { method: "POST", body: JSON.stringify(payload) });
    writeOutput(result);
    await refresh(result.dataset_id);
    document.getElementById("binance-status").textContent = `Downloaded ${result.row_count} real candles. Dataset ${result.dataset_name} is ready.`;
        document.getElementById("run-status").textContent = `Dataset ${result.dataset_name} is selected. Next: click Run Family Sweep.`;
  } catch (error) {
    document.getElementById("binance-status").textContent = `Download failed: ${error.message}`;
    writeOutput(error.message);
  }
});

document.getElementById("guided-sweep-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const family = familyById(document.getElementById("guided-family").value);
    document.getElementById("run-status").textContent = "Running family sweep...";
    const payload = {
      family_id: family.family_id,
      dataset_id: document.getElementById("guided-dataset").value,
    };
    const result = await requestJson("/api/backtests/sweep", { method: "POST", body: JSON.stringify(payload) });
    writeOutput(result);
    await refresh(payload.dataset_id);
    document.getElementById("run-status").textContent = `Sweep finished. Variants: ${result.total_variants}. Survivors: ${result.research_survivors}. Paper candidates: ${result.paper_candidates}. Best OOS Sharpe: ${result.best_oos_sharpe}.`;
  } catch (error) {
    document.getElementById("run-status").textContent = `Sweep failed: ${error.message}`;
    writeOutput(error.message);
  }
});

document.getElementById("review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      family_id: document.getElementById("review-family").value,
      dataset_id: document.getElementById("review-dataset").value,
    };
    document.getElementById("review-status").textContent = "Requesting Gemini review...";
    renderReview(null);
    const result = await requestJson("/api/lab/review", { method: "POST", body: JSON.stringify(payload) });
    writeOutput(result);
    document.getElementById("review-status").textContent = `Review ready. Artifact: ${result.artifact_id}. Use the arrow below to inspect it.`;
    renderReview(result);
  } catch (error) {
    document.getElementById("review-status").textContent = `Review failed: ${error.message}`;
    renderReview(null);
    writeOutput(error.message);
  }
});

refresh().catch((error) => writeOutput(error.message));
