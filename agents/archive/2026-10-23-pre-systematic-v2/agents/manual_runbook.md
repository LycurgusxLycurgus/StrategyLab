# Mutation Lab Manual Runbook

## Purpose

Use this runbook when you want to operate Mutation Lab locally without guessing the flow. The app is intentionally narrow:

1. load at least `40000` bars of real market data
2. run the current promoted parent
3. tune the current parent parameter by parameter
4. preview the tuned profile against the dataset
5. save only tuned children that actually improve the parent

## Local Setup

```powershell
cd "C:\Users\Baham\Documents\pre-nexuz\memecorp&starfish\markov_dove-red\StrategyLab"
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Start The Service

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Expected signal:
- `Uvicorn running on http://127.0.0.1:8000`

## Fast Health Check

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected signal:
- `status = ok`

## Default Operator Flow

1. Open `http://127.0.0.1:8000`.
2. In `Step 1`, leave:
   - `Symbol = BTCUSDT`
   - `Timeframe = 15m`
   - `Bars = 40000` or higher
   - or use `Full history`
3. Click `Download Dataset`.
4. In `Step 2`, keep the seeded family `btc_intraday`.
5. Choose the downloaded dataset.
6. Click `Run Current Parent`.
7. In `Mutation Edges`, use the suggested up/down values as directional hints, then adjust the working values manually.
8. Click `Run Tuned Preview`.
9. If the preview is better, click `Save Tuned Child`.
10. In `Runs`, compare:
   - profit factor
   - total trades
   - max drawdown %
   - net pnl
11. Promote a child only if it actually beats the parent on the criteria you care about.

## CLI Shortcuts

Download the default dataset:

```powershell
.venv\Scripts\python -m app.cli download --symbol BTCUSDT --timeframe 15m --bars 40000
```

Inspect the current family:

```powershell
.venv\Scripts\python -m app.cli family-detail --family-id btc_intraday
```

## Advanced: Register A New Baseline

Only use the advanced panel when you already have:
- the baseline source code
- a canonical spec JSON
- a causal story

Do not register a new family without all three, or the mutation queue will be low quality.

## No Extra Human Steps Required

Mutation Lab does not require:
- paid APIs
- broker credentials
- TradingView login

The default BTC path works with Binance public candles only.
