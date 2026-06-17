"""
Pydantic request / response schemas for the FastAPI backend.
"""

from pydantic import BaseModel, Field
from typing import Optional


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = False
    api_status: Optional[str] = "ONLINE"
    model_status: Optional[str] = "LOADED"
    model_version: Optional[str] = "1.0.0"
    prediction_engine_status: Optional[str] = "ACTIVE"
    feature_count: Optional[int] = 53
    training_date: Optional[str] = "2026-06-16"
    prediction_latency_ms: Optional[float] = 42.0
    forecast_count: Optional[int] = 0
    server_uptime_seconds: Optional[float] = 0.0
    last_prediction_time: Optional[str] = "Never"
    gpu_availability: Optional[bool] = False
    cpu_info: Optional[str] = "Unknown CPU"
    memory_usage: Optional[str] = "Unknown Memory"
    disk_usage: Optional[str] = "Unknown Disk"


class ForecastRequest(BaseModel):
    data_dir: str = Field(default="./data", description="Path to CSV directory")


class BudgetSimulationRequest(BaseModel):
    google_budget: float = Field(default=100.0, ge=0)
    meta_budget: float = Field(default=100.0, ge=0)
    bing_budget: float = Field(default=50.0, ge=0)
    horizon: int = Field(default=30, ge=1, le=365)


class InsightsRequest(BaseModel):
    data_dir: str = Field(default="./data")


class ForecastRow(BaseModel):
    Forecast_Horizon: int
    Revenue_P10: float
    Revenue_P50: float
    Revenue_P90: float
    ROAS_P10: float
    ROAS_P50: float
    ROAS_P90: float
    Google_Revenue: float
    Meta_Revenue: float
    Bing_Revenue: float
    Google_ROAS: float
    Meta_ROAS: float
    Bing_ROAS: float
    Confidence_Score: float
    Forecast_Explanation: str


class ForecastResponse(BaseModel):
    predictions: list[ForecastRow]
    status: str = "success"


class BudgetSimulationResponse(BaseModel):
    channel_curves: dict
    marginal_revenue: dict
    diminishing_return_points: dict
    recommended_allocation: dict
    total_revenue_at_current: float
    status: str = "success"


class InsightsResponse(BaseModel):
    insights: list[str]
    status: str = "success"
