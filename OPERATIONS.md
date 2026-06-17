# Operational Engineering Guide

A complete operations, observability, and debugging manual for the **Probabilistic Revenue Forecasting Platform**. This guide details how to install, configure, verify, monitor, and troubleshoot the unified Next.js + FastAPI system on Windows 11.

---

## 📂 Repository Architecture & Structure

```
.
├── backend/                  # FastAPI Application Gateway
│   ├── main.py               # API endpoints, middleware, and platform observability metrics
│   └── schemas.py            # Pydantic request / response validation models
├── data/                     # Raw and dynamic ecommerce marketing CSV dataset storage
├── docs/                     # Documentation files
├── frontend/                 # Next.js 15 Client Web Application
│   ├── app/                  # App Router views (/forecast, /simulator, /insights, /health)
│   ├── components/           # UI Elements (Shadcn wrappers & DashboardShell sidebar layout)
│   ├── lib/                  # API client fetchers and robust fallbacks
│   ├── package.json          # Node dependencies (Next.js 15, Recharts, Framer Motion, tailwindcss v4)
│   └── tsconfig.json         # TypeScript compiler config
├── logs/                     # observabilty directory (auto-created on backend startup)
│   ├── app.log               # Unified main application runtime events log
│   ├── errors.log            # Warning and error alert logs
│   ├── forecast.log          # Forecaster generation specific pipeline stats
│   └── api.log               # FastAPI gateway request and latency logs
├── output/                   # CSV results directory (predictions_api.csv generated dynamically)
├── pickle/                   # Model serialized binary weights
│   └── model.pkl             # Primary Quantile LightGBM serialized model
├── requirements.txt          # Python packages (fastapi, lightgbm, xgboost, pandas)
├── run.sh                    # Offline shell entrypoint for pipeline training/inference
├── scripts/                  # Final backend audit and automated sanity test scripts
└── src/                      # ML Forecasting Core Engine
    ├── preprocessing.py      # Schema unification & normalizer (Google/Meta/Bing)
    ├── forecasting.py        # LightGBM Quantile Regression model logic
    ├── predict.py            # Prediction pipeline & emergency model fallback handler
    └── utils.py              # Constants, file handlers, logging formatters
```

### Communication Model
1. **Frontend to Backend**: Next.js client-side pages query the FastAPI Gateway via fetch calls (`lib/api.ts`) pointing to `http://localhost:8000`. The API requests map to:
   - `GET /health` (Gateway metrics & telemetry specs)
   - `POST /forecast` (Runs pipeline prediction generation)
   - `POST /simulate-budget` (Triggers dynamic budget response curves simulation)
   - `POST /insights` (Extracts AI consultant summaries)
2. **Backend to ML Forecasting Engine**: FastAPI invokes the `src.predict` and `src.budget_simulator` modules directly. The backend validates parameters using Pydantic, unifies datasets via `src.preprocessing`, and feeds inputs to `QuantileForecaster` or redirects to `_emergency_predictions` fallback models if weights are missing.

---

## ⚙️ Local Development & Installation

### Prerequisite Checklist
- **Operating System**: Windows 11 (64-bit)
- **Node.js**: `v18.x` or higher installed
- **Python**: `v3.10` or higher installed
- **GPU Accelerator**: NVIDIA RTX 4050 (CUDA toolkit v12.x recommended for model training)

### Step 1: Backend Setup
Open PowerShell as Administrator:
```powershell
# 1. Create a Python Virtual Environment
python -m venv .venv

# 2. Activate Environment
.venv\Scripts\Activate.ps1

# 3. Upgrade Pip & Install Dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify Model Pickle Binary Exists
# (Expect True output)
Test-Path .\pickle\model.pkl

# 5. Launch FastAPI Observability Gateway
python -m backend.main
```

### Step 2: Frontend Setup
Open a second PowerShell window:
```powershell
# 1. Navigate to Frontend Folder
cd frontend

# 2. Install Packages
npm install

# 3. Launch Development Server
npm run dev
```

---

## 🚀 Full Project Startup Sequence

For a complete dashboard test run, launch operations in the following sequence:

### Terminal 1: Backend Gateway
```powershell
.venv\Scripts\Activate.ps1
$env:MODEL_PATH=".\pickle\model.pkl"
$env:DATA_DIR=".\data"
python -m backend.main
```

### Terminal 2: Web Client
```powershell
cd frontend
npm run dev
```

### Verification Flow
1. **Open Web Browser**: Navigate to `http://localhost:3000`.
2. **Gateway Check**: Confirm the top navbar displays the green **"Backend Connected"** pill and **"Model Ready"** badge.
3. **Check console logs**: Right-click -> Inspect -> Console. Look for:
   `[DIAGNOSTICS] API Connected: SUCCESS | Model Ready: true`
4. **Interact with Budget Simulator**: Navigate to `/simulator` and drag the sliders. Observe instant curves update in `<LineChart>` sections and dynamic calculations of **Net Revenue Lift**.

---

## 📊 Observability & Logging System

Our logging system outputs formatted, rotating logs to the `./logs/` folder to capture all pipeline events.

### Log Categories
1. **`app.log`**: Unified file tracking all core pipeline steps, normalizations, and configurations.
2. **`errors.log`**: Standard error collector trapping validation warnings, missing parameters, and tracebacks.
3. **`forecast.log`**: Isolated logger logging predict execution benchmarks, model sizes, and output locations.
4. **`api.log`**: Gateway server logs documenting HTTP methods, paths, status codes, and latency measurements in milliseconds.

### Structured Log Format
Logs follow a unified platform pattern:
```
[2026-06-17 20:10:12] INFO    Application starting up...
[2026-06-17 20:10:13] INFO    Model loaded successfully
[2026-06-17 20:10:15] WARNING Validation Warning: Missing campaign type column | Rows=14
[2026-06-17 20:10:16] INFO    API Request Started: POST /forecast
[2026-06-17 20:10:17] INFO    Feature generation started
[2026-06-17 20:10:18] INFO    Forecast generated | Horizon=30 | Revenue_P50=754020 | Latency=120.50ms
[2026-06-17 20:10:18] INFO    API Request Completed: POST /forecast | Status: 200 | Latency: 121.20ms
[2026-06-17 20:10:25] ERROR   Model load failed: File not found. Fallback activated.
```

---

## 🖥️ System Health Dashboard & Telemetry

The extended `/health` endpoint exposes real-time telemetry specs, hardware states, and performance stats:
- **`status`**: Current endpoint state (`"ok"`).
- **`model_loaded`**: Boolean flag showing if primary pickle models are active.
- **`api_status`**: API Gateway status (`"ONLINE"`).
- **`model_status`**: Model state (`"LOADED"` or `"FALLBACK"`).
- **`model_version`**: Platform model version (`"1.2.0-stable"`).
- **`prediction_engine_status`**: Prediction engine state (`"ACTIVE"`).
- **`feature_count`**: Number of engineered input dimensions (`53`).
- **`training_date`**: Model baseline training timestamp (`"2026-06-16"`).
- **`prediction_latency_ms`**: Latency in ms of the last query execution.
- **`forecast_count`**: Total forecasts generated since server startup.
- **`server_uptime_seconds`**: Server uptime calculation.
- **`last_prediction_time`**: Date timestamp of the last generated predictions.
- **`gpu_availability`**: Boolean CUDA hardware check.
- **`cpu_info`**: Details on host processor cores.
- **`memory_usage`**: Free vs Allocated physical system memory.
- **`disk_usage`**: Disk footprint summary.

---

## 🛠️ Diagnostics & Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| **Backend won't start** | Port `8000` is locked by another process. | Kill lock: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force` |
| **Model status displays "Fallback Ready"** | Serialized weight file `pickle/model.pkl` is missing or corrupted. | Run validation script: `python scripts/verify_submission.py`. If model is missing, execute training pipeline. |
| **API Connection Failed** | Next.js API client is querying incorrect URL or port. | Verify `.env.local` or environment variable `NEXT_PUBLIC_API_URL` points to `http://localhost:8000`. |
| **CUDA / GPU Unavailable** | PyTorch/LightGBM cannot detect CUDA on the RTX 4050. | Verify NVIDIA drivers are current. Run `nvidia-smi` in shell to check CUDA support level. |
| **Empty Forecasts** | Data directory `./data` contains zero marketing CSVs. | Copy test files from `test-files/` to `data/` and re-query. |
| **Windows Path Syntax Error** | Python parsing scripts crash on backslash characters. | Normalize all file path strings to use forward slashes (`/`) or wrap as raw string blocks (`r"path\to\file"`). |

---

## 📋 Operations Cheat Sheet

### Startup Commands
```bash
# Start backend gateway
python -m backend.main

# Start frontend dev mode
cd frontend && npm run dev

# Run project build
cd frontend && npm run build

# Start frontend production server
cd frontend && npm start
```

### Pipeline Actions
```bash
# Generate CSV predictions manually
python -m src.predict --data-dir ./data --features ./output/features.csv --model ./pickle/model.pkl --output ./output/predictions.csv

# Run pipeline audit checks
python scripts/verify_submission.py
```

### Observability Logs Inspection
```bash
# Live tail API request logs in PowerShell
Get-Content -Path .\logs\api.log -Wait

# Show warning and error logs only
Get-Content -Path .\logs\errors.log
```
