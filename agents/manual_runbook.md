# 1. Context

- Current environment/project ID: `Project Aurum` in `C:\Users\Baham\Documents\pre-nexuz\memecorp&starfish\markov_dove-red\StrategyLab`
- Current service name: `FastAPI app served by uvicorn`
- Task/Blocker: `Install dependencies, boot the local service, verify the research cockpit, and optionally trigger the webhook evaluator manually`

# 2. Prerequisites

- [ ] Required Shell: `PowerShell`
- [ ] Required runtimes: `Python 3.12.x`
- [ ] Required CLIs installed: `python`, `pip`
- [ ] Required external API keys/accounts: `Optional: a free OANDA practice account plus API token for XAU_USD candles`

# 3. Manual UI Actions

1. Open a browser after the server starts and go to `http://127.0.0.1:8000`.
2. If OANDA is ready, go to [OANDA](https://www.oanda.com/) and create a free `Practice` account.
3. In the OANDA portal, generate an API token for the practice environment.
4. In `1. Acquire Data`, choose `Gold CFD (OANDA Practice)` and `Provider = OANDA Practice`.
5. If OANDA is not ready, use `Manual CSV Import` with your HistData XAUUSD M1 file.
6. After the dataset appears in the `Datasets` table, click `Run baseline`, then `Run hybrid comparison`, then `Simulate week`.

# 4. Local Setup and Verification

1. Open your terminal and navigate to the project root:

```powershell
cd "C:\Users\Baham\Documents\pre-nexuz\memecorp&starfish\markov_dove-red\StrategyLab"
```

2. Verify Python is installed:

```powershell
python --version
```

Expected success signal: version information similar to `Python 3.12.7` is printed.

3. Create the virtual environment:

```powershell
python -m venv .venv
```

4. Install dependencies:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

Expected success signal: pip finishes without errors and prints installed package names.

5. Run the full local test suite:

```powershell
.venv\Scripts\python -m unittest discover -s app -p tests.py
```

Expected success signal: the suite ends with `OK`.

# 5. Secret Variables (Current Shell Session)

Put the OANDA practice token into the current shell before starting `uvicorn`:

```powershell
$env:APP_OANDA_API_TOKEN = "paste-the-practice-token-you-generated-in-the-oanda-portal"
```

Verify it is populated:

```powershell
echo $env:APP_OANDA_API_TOKEN
```

Expected success signal: the token prints to the terminal.

If you are using the manual HistData import fallback, no secret variables are required.

# 6. Infrastructure / Cloud Authentication

No cloud authentication is required for the current local workflow.

# 7. Remote Deployment

No remote deployment is required for the current local workflow. The service is intended to run locally first.

# 8. Safe Read-Only Verification

1. Start the app:

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Expected success signal: uvicorn prints `Uvicorn running on http://127.0.0.1:8000`.

2. In a second PowerShell window, verify health:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected success signal: PowerShell prints an object whose `status` is `ok`.

3. Manual CSV formats accepted by the app:

```csv
timestamp,open,high,low,close,volume
2026-03-01T00:00:00Z,2850.1,2851.2,2849.8,2850.9,100
2026-03-01T00:15:00Z,2850.9,2852.0,2850.2,2851.7,120
```

Or the raw HistData ASCII M1 format:

```text
20250101 180000;2625.098000;2626.005000;2624.355000;2625.048000;0
20250101 180100;2625.055000;2625.148000;2624.425000;2624.955000;0
```

Expected success signal: the app accepts either a headered OHLCV CSV or the raw HistData M1 ASCII file and stores a normalized 15m dataset.

# 9. Smoke Tests

1. Check the strategy summary endpoint:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/strategies/current" | ConvertTo-Json -Depth 6
```

Expected success signal: JSON is returned with `family_id` equal to `aurum_smc_hybrid`.

2. Trigger a manual webhook evaluation after at least one hybrid run exists:

```powershell
$body = @{
  symbol = "XAUUSD"
  timeframe = "15m"
  timestamp = "2026-03-30T14:00:00+00:00"
  direction = "long"
  entry = 2660.0
  stop = 2655.0
  target = 2670.0
  session_ny = 1
  sweep_depth_atr = 0.3
  body_atr = 0.9
  fvg_size_atr = 0.5
  bias = 1
  distance_to_prev_day_atr = 0.7
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/webhooks/tradingview" -Method Post -ContentType "application/json" -Body $body
```

Expected success signal: JSON is returned with `action`, `score`, and `threshold`.

# 10. Troubleshooting / Fallbacks

- If OANDA returns `401` or `403`: the token is missing, invalid, or not a practice token for the practice base URL.
- Fix:
  1. Generate a fresh practice token in the OANDA portal.
  2. Re-set `$env:APP_OANDA_API_TOKEN`.
  3. Restart uvicorn and retry the download.

- If you need to proceed before OANDA is ready:
- Fix:
  1. Use the raw HistData XAUUSD M1 file in `Manual CSV Import`.
  2. The app will aggregate the minute bars into 15m automatically.
  3. Use the imported dataset for baseline, hybrid, and paper runs.

- If `White-box baseline produced no trades` occurs during hybrid comparison: the current dataset did not yield enough valid white-box candidates.
- Fix:
  1. Download a longer or different gold dataset.
  2. Re-run `Run baseline`.
  3. Only then run `Run hybrid comparison`.

- If the browser appears stale after code changes:
  1. Stop and restart uvicorn.
  2. Hard-refresh the browser window.
  3. Re-run the health check.
