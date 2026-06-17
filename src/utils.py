"""
Shared utilities, constants, and configuration for the forecasting pipeline.
All encoding dictionaries, column constants, model hyperparameters, and helper
functions live here — the single source of truth for the entire project.
"""

import os
import logging
import subprocess
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Unified Schema Column Names
# ---------------------------------------------------------------------------
COL_DATE = "Date"
COL_CHANNEL = "Channel"
COL_CAMPAIGN_NAME = "CampaignName"
COL_CAMPAIGN_TYPE = "CampaignType"
COL_SPEND = "Spend"
COL_REVENUE = "Revenue"
COL_CLICKS = "Clicks"
COL_IMPRESSIONS = "Impressions"
COL_CONVERSIONS = "Conversions"
COL_BUDGET = "Budget"

UNIFIED_COLUMNS = [
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_NAME, COL_CAMPAIGN_TYPE,
    COL_SPEND, COL_REVENUE, COL_CLICKS, COL_IMPRESSIONS,
    COL_CONVERSIONS, COL_BUDGET,
]

NUMERIC_COLUMNS = [
    COL_SPEND, COL_REVENUE, COL_CLICKS, COL_IMPRESSIONS,
    COL_CONVERSIONS, COL_BUDGET,
]

# ---------------------------------------------------------------------------
# Channel Constants
# ---------------------------------------------------------------------------
CHANNEL_GOOGLE = "Google"
CHANNEL_META = "Meta"
CHANNEL_BING = "Bing"
ALL_CHANNELS = [CHANNEL_GOOGLE, CHANNEL_META, CHANNEL_BING]

CHANNEL_FILE_MAP = {
    "google": CHANNEL_GOOGLE,
    "meta": CHANNEL_META,
    "facebook": CHANNEL_META,
    "bing": CHANNEL_BING,
    "microsoft": CHANNEL_BING,
}

# ---------------------------------------------------------------------------
# Dict-based Encoding — handles unknown values gracefully (unknown → 0)
# ---------------------------------------------------------------------------
CHANNEL_ENCODING = {
    CHANNEL_GOOGLE: 1,
    CHANNEL_META: 2,
    CHANNEL_BING: 3,
}

CAMPAIGN_TYPE_ENCODING = {
    "Search": 1,
    "Shopping": 2,
    "Display": 3,
    "Video": 4,
    "Performance Max": 5,
    "Discovery": 6,
    "App": 7,
    "Conversions": 8,
    "Traffic": 9,
    "Awareness": 10,
    "Engagement": 11,
    "Leads": 12,
    "Reach": 13,
    "Brand": 14,
    "Remarketing": 15,
    "Retargeting": 15,
    "Dynamic Search": 16,
    "Audience": 17,
    "Smart": 18,
    "Local": 19,
    "Call": 20,
    "Lead Generation": 21,
    "App Installs": 22,
    "Video Views": 23,
    "Brand Awareness": 24,
    "Catalog Sales": 25,
    "Store Traffic": 26,
    "Messages": 27,
    "Demand Gen": 28,
    "Prospecting": 29,
    "Generic": 30,
    "DPA": 31,
    "Advantage Plus": 32,
    "PerformanceMax": 5,
    "PERFORMANCE_MAX": 5,
    "DEMAND_GEN": 28,
    "SEARCH": 1,
    "SHOPPING": 2,
    "DISPLAY": 3,
    "VIDEO": 4,
    "Unknown": 0,
}

# ---------------------------------------------------------------------------
# Derived Feature Column Names
# ---------------------------------------------------------------------------
COL_CTR = "CTR"
COL_CPC = "CPC"
COL_CPA = "CPA"
COL_ROAS = "ROAS"

# ---------------------------------------------------------------------------
# Forecast Horizons
# ---------------------------------------------------------------------------
FORECAST_HORIZONS = [30, 60, 90]

# ---------------------------------------------------------------------------
# Model Quantiles
# ---------------------------------------------------------------------------
QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}

# ---------------------------------------------------------------------------
# GPU Configuration
# ---------------------------------------------------------------------------
USE_GPU = True  # Set to False to force CPU-only training


def detect_gpu_info() -> dict:
    """
    Detect NVIDIA GPU availability and return info dict.

    Returns {"available": bool, "name": str, "device": str}.
    This is only used at TRAINING time — inference is always CPU.
    """
    info = {"available": False, "name": "N/A", "device": "cpu"}
    if not USE_GPU:
        return info
    # Method 1: nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            info["available"] = True
            info["name"] = result.stdout.strip().split("\n")[0]
            info["device"] = "gpu"
            return info
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    # Method 2: torch CUDA check (if available)
    try:
        import torch
        if torch.cuda.is_available():
            info["available"] = True
            info["name"] = torch.cuda.get_device_name(0)
            info["device"] = "gpu"
            return info
    except ImportError:
        pass
    return info


# ---------------------------------------------------------------------------
# LightGBM Default Hyperparameters (CPU base — GPU added at train time)
# ---------------------------------------------------------------------------
LIGHTGBM_PARAMS = {
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_samples": 20,
    "random_state": RANDOM_SEED,
    "verbose": -1,
    "n_jobs": -1,
}

# GPU overlay applied at training time only
LIGHTGBM_GPU_PARAMS = {
    "device": "gpu",
    "gpu_use_dp": False,  # single precision is faster
}

# XGBoost GPU params (applied at training time only)
XGBOOST_GPU_PARAMS = {
    "tree_method": "hist",
    "device": "cuda",
}

# ---------------------------------------------------------------------------
# Output Schema for predictions.csv
# ---------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    "Forecast_Horizon",
    "Revenue_P10",
    "Revenue_P50",
    "Revenue_P90",
    "ROAS_P10",
    "ROAS_P50",
    "ROAS_P90",
    "Google_Revenue",
    "Meta_Revenue",
    "Bing_Revenue",
    "Google_ROAS",
    "Meta_ROAS",
    "Bing_ROAS",
    "Confidence_Score",
    "Forecast_Explanation",
]

# ---------------------------------------------------------------------------
# Feature column list used by the model (order matters for alignment)
# This is the canonical feature list. Stored in model.pkl as well.
# ---------------------------------------------------------------------------
MODEL_FEATURE_COLUMNS = [
    # Aggregated base metrics
    "Spend", "Revenue", "Clicks", "Impressions", "Conversions", "Budget",
    # Derived ratios
    "CTR", "CPC", "CPA", "ROAS",
    # Temporal
    "Month", "Quarter", "WeekOfYear", "DayOfYear", "DayOfWeek",
    "IsWeekend", "IsMonthStart", "IsMonthEnd",
    # Seasonality (cyclical encoding)
    "Month_Sin", "Month_Cos", "Week_Sin", "Week_Cos",
    # Lag features
    "Revenue_Lag_7", "Revenue_Lag_14", "Revenue_Lag_30",
    "Spend_Lag_7", "Spend_Lag_14",
    "ROAS_Lag_7",
    # Rolling features
    "Revenue_Rolling_7", "Revenue_Rolling_14", "Revenue_Rolling_30",
    "Spend_Rolling_7", "Spend_Rolling_14",
    "ROAS_Rolling_7", "ROAS_Rolling_14",
    "Revenue_Rolling_Std_7",
    # Trend features
    "Revenue_Trend_14", "Spend_Trend_14", "ROAS_Trend_14",
    # Share features
    "Channel_Revenue_Share", "Channel_Spend_Share",
    # Momentum features
    "Revenue_Momentum_7", "Spend_Momentum_7",
    # Conversion features
    "Conversion_Rate", "Revenue_Per_Conversion",
    # Volatility / stability
    "Revenue_Volatility_14", "ROAS_Stability_14",
    # Saturation
    "Budget_Utilization", "Spend_Per_Impression",
    # Data context
    "DaysOfData",
    # Encodings
    "Channel_Encoded", "CampaignType_Encoded",
    # Horizon (added at prediction / training target construction)
    "Horizon",
]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def safe_divide(numerator, denominator, default=0.0):
    """Division that returns *default* when denominator is zero / NaN."""
    if isinstance(numerator, (pd.Series, np.ndarray)):
        denom = pd.Series(denominator) if not isinstance(denominator, (pd.Series, np.ndarray)) else denominator
        num = pd.Series(numerator) if not isinstance(numerator, (pd.Series, np.ndarray)) else numerator
        result = np.where(
            (denom != 0) & (~np.isnan(denom.astype(float))),
            num / denom,
            default,
        )
        return result
    try:
        if denominator == 0 or (isinstance(denominator, float) and np.isnan(denominator)):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def encode_value(value, mapping: dict, default: int = 0) -> int:
    """Encode a categorical value using a dict, returning *default* for unknowns."""
    if pd.isna(value):
        return default
    val_str = str(value).strip()
    if val_str in mapping:
        return mapping[val_str]
    # Try case-insensitive match
    val_lower = val_str.lower()
    for key, code in mapping.items():
        if key.lower() == val_lower:
            return code
    return default


def setup_logging(level=logging.INFO):
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("forecast")


def ensure_dir(path: str):
    """Create parent directories for *path* if they don't exist."""
    directory = os.path.dirname(path) if "." in os.path.basename(path) else path
    if directory:
        os.makedirs(directory, exist_ok=True)


def format_output(predictions_internal: dict) -> pd.DataFrame:
    """
    Convert the internal predictions dict to the official predictions.csv schema.

    Parameters
    ----------
    predictions_internal : dict
        Keyed by horizon (30, 60, 90).  Each value is a dict with keys:
        - total:    {p10, p50, p90}
        - spend:    {total, Google, Meta, Bing}
        - channels: {Google: {p10,p50,p90}, Meta: ..., Bing: ...}
        - confidence: float
        - explanation: str
    """
    rows = []
    for horizon in FORECAST_HORIZONS:
        p = predictions_internal.get(horizon, {})
        total = p.get("total", {"p10": 0, "p50": 0, "p90": 0})
        spend = p.get("spend", {"total": 1, "Google": 1, "Meta": 1, "Bing": 1})
        channels = p.get("channels", {})

        total_spend = max(spend.get("total", 1), 1e-9)
        row = {
            "Forecast_Horizon": horizon,
            "Revenue_P10": round(max(0, total.get("p10", 0)), 2),
            "Revenue_P50": round(max(0, total.get("p50", 0)), 2),
            "Revenue_P90": round(max(0, total.get("p90", 0)), 2),
            "ROAS_P10": round(max(0, safe_divide(total.get("p10", 0), total_spend)), 4),
            "ROAS_P50": round(max(0, safe_divide(total.get("p50", 0), total_spend)), 4),
            "ROAS_P90": round(max(0, safe_divide(total.get("p90", 0), total_spend)), 4),
        }
        for ch in ALL_CHANNELS:
            ch_rev = channels.get(ch, {}).get("p50", 0.0)
            ch_spend = max(spend.get(ch, 1), 1e-9)
            row[f"{ch}_Revenue"] = round(max(0, ch_rev), 2)
            row[f"{ch}_ROAS"] = round(max(0, safe_divide(ch_rev, ch_spend)), 4)

        row["Confidence_Score"] = round(
            min(1.0, max(0.0, p.get("confidence", 0.5))), 4
        )
        row["Forecast_Explanation"] = p.get("explanation", "Forecast generated from historical data.")
        rows.append(row)

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
