"""
FastAPI backend for the Revenue Forecasting Dashboard.

Endpoints:
    POST /upload         — Upload CSV files
    POST /forecast       — Generate revenue forecasts
    POST /simulate-budget — Run budget simulation
    POST /insights       — Generate AI insights
    GET  /health         — Health check
"""

import os
import shutil
import tempfile
import logging
import logging.handlers
import time
import platform
import ctypes
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    HealthResponse, ForecastRequest, ForecastResponse, ForecastRow,
    BudgetSimulationRequest, BudgetSimulationResponse,
    InsightsRequest, InsightsResponse,
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import (
    FORECAST_HORIZONS, ALL_CHANNELS, COL_CHANNEL, COL_SPEND,
    setup_logging, format_output,
)
from src.preprocessing import unify_schema
from src.validation import validate_data
from src.generate_features import engineer_features
from src.forecasting import QuantileForecaster
from src.predict import predict as run_predict, _emergency_predictions
from src.budget_simulator import simulate_budget
from src.ai_insights import generate_insights

# Observability telemetry counters
START_TIME = time.time()
FORECAST_COUNT = 0
LAST_PREDICTION_LATENCY = 0.0
LAST_PREDICTION_TIME = "Never"

# Production Logger Configuration
def setup_production_logging():
    # Force console encoding to UTF-8 to prevent CP1252 errors on Windows terminals
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # fallback for older python environments where reconfigure does not exist

    os.makedirs("./logs", exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    # Remove default handlers
    for h in list(root.handlers):
        root.removeHandler(h)
        
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 1. Console Handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    root.addHandler(console)
    
    # 2. app.log (main log file)
    app_h = logging.handlers.RotatingFileHandler("./logs/app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    app_h.setFormatter(formatter)
    app_h.setLevel(logging.INFO)
    root.addHandler(app_h)
    
    # 3. errors.log (errors and warnings)
    err_h = logging.handlers.RotatingFileHandler("./logs/errors.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    err_h.setFormatter(formatter)
    err_h.setLevel(logging.WARNING)
    root.addHandler(err_h)
    
    # 4. forecast.log (forecast activity only)
    f_logger = logging.getLogger("forecast")
    f_logger.setLevel(logging.INFO)
    f_handler = logging.handlers.RotatingFileHandler("./logs/forecast.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    f_handler.setFormatter(formatter)
    f_logger.addHandler(f_handler)
    f_logger.propagate = True
    
    # 5. api.log (http requests)
    api_logger = logging.getLogger("api")
    api_logger.setLevel(logging.INFO)
    api_handler = logging.handlers.RotatingFileHandler("./logs/api.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    api_handler.setFormatter(formatter)
    api_logger.addHandler(api_handler)
    api_logger.propagate = False
    
    return logging.getLogger("forecast")

logger = setup_production_logging()

app = FastAPI(
    title="Revenue Forecasting API",
    version="1.0.0",
    description="Probabilistic Revenue Forecasting for Ecommerce Marketing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logger middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    api_logger = logging.getLogger("api")
    start = time.time()
    api_logger.info(f"API Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        api_logger.info(f"API Response: {request.method} {request.url.path} | Status: {response.status_code} | Latency: {duration:.2f}ms")
        return response
    except Exception as e:
        duration = (time.time() - start) * 1000
        api_logger.error(f"API Request Error: {request.method} {request.url.path} | Latency: {duration:.2f}ms | Error: {str(e)}")
        raise e

MODEL_PATH = os.environ.get("MODEL_PATH", "./pickle/model.pkl")
DATA_DIR = os.environ.get("DATA_DIR", "./data")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./data")

_forecaster = None

def _get_forecaster():
    global _forecaster
    if _forecaster is None:
        try:
            if os.path.exists(MODEL_PATH):
                _forecaster = QuantileForecaster.load(MODEL_PATH)
                logger.info("Model loaded successfully")
            else:
                logger.warning(f"Model path {MODEL_PATH} not found. Fallback activated.")
        except Exception as e:
            logger.error(f"Model load failed: {e}. Fallback activated.")
    return _forecaster

# Platform and resource query helpers
def get_cpu_info():
    try:
        return f"{platform.processor()} ({os.cpu_count()} Cores)"
    except:
        return f"Unknown processor ({os.cpu_count()} Cores)"

def get_gpu_availability():
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False

def get_memory_usage():
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedPhys", ctypes.c_uint64),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_gb = stat.ullTotalPhys / (1024 ** 3)
        avail_gb = stat.ullAvailPhys / (1024 ** 3)
        used_gb = total_gb - avail_gb
        return f"{used_gb:.1f} GB / {total_gb:.1f} GB ({stat.dwMemoryLoad}% Load)"
    except:
        return "Unknown Memory Usage"

def get_disk_usage():
    try:
        usage = shutil.disk_usage(os.getcwd())
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        return f"{used_gb:.1f} GB used / {total_gb:.1f} GB total ({free_gb:.1f} GB free)"
    except:
        return "Unknown Disk Usage"

logger.info("Application starting up...")

@app.get("/health", response_model=HealthResponse)
def health():
    f = _get_forecaster()
    uptime = time.time() - START_TIME
    
    return HealthResponse(
        status="ok",
        model_loaded=(f is not None),
        api_status="ONLINE",
        model_status="LOADED" if f is not None else "FALLBACK",
        model_version="1.2.0-stable",
        prediction_engine_status="ACTIVE",
        feature_count=53,
        training_date="2026-06-16",
        prediction_latency_ms=LAST_PREDICTION_LATENCY,
        forecast_count=FORECAST_COUNT,
        server_uptime_seconds=uptime,
        last_prediction_time=LAST_PREDICTION_TIME,
        gpu_availability=get_gpu_availability(),
        cpu_info=get_cpu_info(),
        memory_usage=get_memory_usage(),
        disk_usage=get_disk_usage()
    )

@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    saved = []
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Uploading {len(files)} file(s)...")
    for f in files:
        if not f.filename.endswith(".csv"):
            logger.warning(f"Skipped non-CSV upload file: {f.filename}")
            continue
        dest = os.path.join(UPLOAD_DIR, f.filename)
        with open(dest, "wb") as out:
            content = await f.read()
            out.write(content)
        saved.append(f.filename)
        logger.info(f"File uploaded and saved: {f.filename}")
    return {"uploaded": saved, "status": "success"}

@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest = ForecastRequest()):
    global FORECAST_COUNT, LAST_PREDICTION_LATENCY, LAST_PREDICTION_TIME
    data_dir = req.data_dir or DATA_DIR
    output_path = "./output/predictions_api.csv"
    
    logger.info(f"Forecast generation request received for directory: {data_dir}")
    start_time = time.time()
    
    try:
        # Preprocessing validation logs
        raw = unify_schema(data_dir)
        cleaned, report = validate_data(raw)
        
        # Log validation warnings
        if report and "warnings" in report and report["warnings"]:
            for warn in report["warnings"]:
                logger.warning(f"Validation Warning: {warn}")
        
        logger.info("Feature generation started")
        run_predict(data_dir, "", MODEL_PATH, output_path)
        
        import pandas as pd
        df = pd.read_csv(output_path)
        rows = [ForecastRow(**row) for row in df.to_dict(orient="records")]
        
        FORECAST_COUNT += 1
        LAST_PREDICTION_LATENCY = (time.time() - start_time) * 1000
        LAST_PREDICTION_TIME = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Log forecast summaries
        p50_total = df.iloc[-1]["Revenue_P50"] if not df.empty else 0
        logger.info(f"Forecast generated | Horizon={len(df)} | Revenue_P50={p50_total:.0f} | Latency={LAST_PREDICTION_LATENCY:.2f}ms")
        
        return ForecastResponse(predictions=rows)
    except Exception as e:
        logger.error(f"Forecast generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate-budget", response_model=BudgetSimulationResponse)
def simulate(req: BudgetSimulationRequest):
    f = _get_forecaster()
    if f is None:
        logger.error("Simulation request rejected: Model not loaded")
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    logger.info(f"Budget simulation request: Google={req.google_budget} Meta={req.meta_budget} Bing={req.bing_budget} Horizon={req.horizon}")
    try:
        raw = unify_schema(DATA_DIR)
        cleaned, _ = validate_data(raw)
        features = engineer_features(cleaned)

        from src.predict import _get_latest_features
        latest = _get_latest_features(features)

        budgets = {"Google": req.google_budget, "Meta": req.meta_budget, "Bing": req.bing_budget}
        result = simulate_budget(f, latest, budgets, req.horizon)
        
        logger.info("Budget simulation completed successfully")
        return BudgetSimulationResponse(**result)
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insights", response_model=InsightsResponse)
def insights(req: InsightsRequest = InsightsRequest()):
    data_dir = req.data_dir or DATA_DIR
    logger.info(f"AI Insights requested for directory: {data_dir}")
    try:
        import pandas as pd
        output_path = "./output/predictions_api.csv"
        if not os.path.exists(output_path):
            run_predict(data_dir, "", MODEL_PATH, output_path)
        df = pd.read_csv(output_path)

        from src.ai_insights import generate_structured_insights
        insight_texts = generate_structured_insights(df)
            
        logger.info("AI insights generation completed successfully")
        return InsightsResponse(insights=insight_texts)
    except Exception as e:
        logger.error(f"Insights generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
