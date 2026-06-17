"""
Forecasting engine — LightGBM quantile regression with XGBoost fallback.

GPU Acceleration:
  - Training: Uses CUDA/GPU when available (auto-detected).
  - Inference: Always CPU — model.pkl is portable to non-GPU machines.

Provides:
  - QuantileForecaster   : train / predict / save / load for P10 / P50 / P90
  - build_training_targets : compute forward-looking revenue sums for each horizon
"""

import logging
import time
import numpy as np
import pandas as pd
import joblib

from src.utils import (
    QUANTILES, LIGHTGBM_PARAMS, LIGHTGBM_GPU_PARAMS, XGBOOST_GPU_PARAMS,
    RANDOM_SEED, FORECAST_HORIZONS,
    MODEL_FEATURE_COLUMNS, CHANNEL_ENCODING, CAMPAIGN_TYPE_ENCODING,
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_TYPE, COL_REVENUE, COL_SPEND,
    detect_gpu_info,
)

logger = logging.getLogger("forecast.model")

# ---------------------------------------------------------------------------
# Try importing LightGBM; fall back to XGBoost
# ---------------------------------------------------------------------------
_USE_LIGHTGBM = True
try:
    import lightgbm as lgb
except ImportError:
    _USE_LIGHTGBM = False
    logger.warning("LightGBM not available — falling back to XGBoost")

try:
    import xgboost as xgb
except ImportError:
    xgb = None
    if not _USE_LIGHTGBM:
        logger.error("Neither LightGBM nor XGBoost available!")


# ---------------------------------------------------------------------------
# Training-target construction
# ---------------------------------------------------------------------------

def build_training_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute forward-looking revenue sums for each (Channel, CampaignType) group.

    For each row at date *t*, for each horizon *h*, the target is::

        SUM(Revenue from t+1 … t+h)   within the same (Channel, CampaignType)

    Also computes forward spend sums (used at prediction time for ROAS).

    Returns a new DataFrame with columns:
        - all original columns
        - Horizon          (int: 30, 60, 90)
        - Target_Revenue   (float)
        - Target_Spend     (float)

    Rows where the target cannot be computed (not enough future data) are
    dropped automatically.
    """
    frames = []
    groups = df.groupby([COL_CHANNEL, COL_CAMPAIGN_TYPE])

    for (channel, ctype), gdf in groups:
        gdf = gdf.sort_values(COL_DATE).reset_index(drop=True)
        rev = gdf[COL_REVENUE].values
        spend = gdf[COL_SPEND].values
        n = len(rev)

        # Cumulative sums for O(1) range-sum queries
        cum_rev = np.concatenate([[0], np.cumsum(rev)])
        cum_spend = np.concatenate([[0], np.cumsum(spend)])

        for h in FORECAST_HORIZONS:
            targets = []
            spend_targets = []
            valid_mask = []
            for i in range(n):
                end = min(i + h, n)  # i+1 … i+h  →  cumsum indices i+1 … end
                if end <= i:
                    valid_mask.append(False)
                    targets.append(0)
                    spend_targets.append(0)
                else:
                    targets.append(cum_rev[end] - cum_rev[i + 1] if i + 1 <= end else 0)
                    spend_targets.append(cum_spend[end] - cum_spend[i + 1] if i + 1 <= end else 0)
                    # Only count as valid if we have at least half the horizon
                    valid_mask.append((end - i) >= max(h * 0.5, 1))

            tmp = gdf.copy()
            tmp["Horizon"] = h
            tmp["Target_Revenue"] = targets
            tmp["Target_Spend"] = spend_targets
            tmp["_valid"] = valid_mask
            frames.append(tmp[tmp["_valid"]].drop(columns=["_valid"]))

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    logger.info(f"Training targets built: {len(result)} samples across {len(FORECAST_HORIZONS)} horizons")
    return result


# ---------------------------------------------------------------------------
# QuantileForecaster
# ---------------------------------------------------------------------------

class QuantileForecaster:
    """Manages three quantile models (P10, P50, P90) with GPU training support."""

    def __init__(self):
        self.models = {}
        self.feature_columns = []
        self.metadata = {}
        self._gpu_info = None

    # ---- Training --------------------------------------------------------

    def train(self, X: pd.DataFrame, y: pd.Series):
        """
        Train P10, P50, P90 quantile models.

        Automatically detects GPU and uses CUDA acceleration when available.
        Falls back to CPU transparently. Saved models are always CPU-portable.

        Parameters
        ----------
        X : DataFrame   feature matrix (must include 'Horizon' column)
        y : Series      target (forward revenue sum)
        """
        self.feature_columns = list(X.columns)

        # ---- GPU detection ----
        self._gpu_info = detect_gpu_info()
        gpu_available = self._gpu_info["available"]

        if gpu_available:
            logger.info("=" * 50)
            logger.info(f"  GPU DETECTED: {self._gpu_info['name']}")
            logger.info(f"  Training will use CUDA acceleration")
            logger.info("=" * 50)
        else:
            logger.info("No GPU detected — training on CPU")

        self.metadata["gpu_used"] = gpu_available
        self.metadata["gpu_name"] = self._gpu_info["name"]

        total_start = time.time()

        for label, alpha in QUANTILES.items():
            logger.info(f"Training {label.upper()} model (alpha={alpha}) ...")
            t0 = time.time()

            # Try GPU first, fallback to CPU
            model = None
            used_gpu = False

            if gpu_available:
                try:
                    model = self._make_model(alpha, use_gpu=True)
                    model.fit(X, y)
                    used_gpu = True
                    logger.info(f"  {label.upper()} trained on GPU")
                except Exception as exc:
                    logger.warning(f"  GPU training failed for {label.upper()}: {exc}")
                    logger.info(f"  Falling back to CPU for {label.upper()} ...")
                    model = None

            if model is None:
                model = self._make_model(alpha, use_gpu=False)
                model.fit(X, y)
                if gpu_available:
                    logger.info(f"  {label.upper()} trained on CPU (GPU fallback)")
                else:
                    logger.info(f"  {label.upper()} trained on CPU")

            elapsed = time.time() - t0
            logger.info(f"  {label.upper()} complete in {elapsed:.1f}s (GPU={used_gpu})")
            self.models[label] = model

        total_elapsed = time.time() - total_start
        logger.info(f"All quantile models trained in {total_elapsed:.1f}s")
        self.metadata["training_time_seconds"] = round(total_elapsed, 2)
        self.metadata["cpu_fallback"] = not gpu_available

    # ---- Prediction (ALWAYS CPU) -----------------------------------------

    def predict(self, X: pd.DataFrame) -> dict:
        """
        Predict revenue for each quantile.

        ALWAYS runs on CPU — no GPU dependency at inference time.
        Returns dict  {"p10": array, "p50": array, "p90": array}.
        Enforces non-negativity and monotonicity (P10 ≤ P50 ≤ P90).
        """
        preds = {}
        for label in ["p10", "p50", "p90"]:
            raw = self.models[label].predict(X)
            preds[label] = np.maximum(0.0, raw)

        # Enforce quantile monotonicity
        stacked = np.stack([preds["p10"], preds["p50"], preds["p90"]], axis=0)
        stacked = np.sort(stacked, axis=0)
        preds["p10"] = stacked[0]
        preds["p50"] = stacked[1]
        preds["p90"] = stacked[2]
        return preds

    # ---- Persistence -----------------------------------------------------

    def save(self, path: str):
        """Serialise models + metadata to *path* using joblib (CPU-portable)."""
        artifact = {
            "p10_model": self.models.get("p10"),
            "p50_model": self.models.get("p50"),
            "p90_model": self.models.get("p90"),
            "feature_columns": self.feature_columns,
            "channel_encoding": CHANNEL_ENCODING,
            "campaign_type_encoding": CAMPAIGN_TYPE_ENCODING,
            "metadata": self.metadata,
        }
        joblib.dump(artifact, path, protocol=4)
        logger.info(f"Model saved to {path} (CPU-portable, protocol=4)")

    @classmethod
    def load(cls, path: str) -> "QuantileForecaster":
        """Load a saved model artifact. Works on any machine (no GPU required)."""
        artifact = joblib.load(path)
        forecaster = cls()
        forecaster.models = {
            "p10": artifact["p10_model"],
            "p50": artifact["p50_model"],
            "p90": artifact["p90_model"],
        }
        forecaster.feature_columns = artifact.get("feature_columns", MODEL_FEATURE_COLUMNS)
        forecaster.metadata = artifact.get("metadata", {})
        logger.info(f"Model loaded from {path} ({len(forecaster.feature_columns)} features)")
        return forecaster

    # ---- Internal --------------------------------------------------------

    @staticmethod
    def _make_model(alpha: float, use_gpu: bool = False):
        """
        Create a single quantile model.

        LightGBM preferred, XGBoost fallback.
        GPU params are applied only when use_gpu=True (training only).
        The resulting model object is CPU-portable after training.
        """
        if _USE_LIGHTGBM:
            params = {**LIGHTGBM_PARAMS, "objective": "quantile", "alpha": alpha}
            if use_gpu:
                params.update(LIGHTGBM_GPU_PARAMS)
            return lgb.LGBMRegressor(**params)
        elif xgb is not None:
            xgb_params = {
                "objective": "reg:quantileerror",
                "quantile_alpha": alpha,
                "n_estimators": LIGHTGBM_PARAMS["n_estimators"],
                "max_depth": LIGHTGBM_PARAMS["max_depth"],
                "learning_rate": LIGHTGBM_PARAMS["learning_rate"],
                "subsample": LIGHTGBM_PARAMS["subsample"],
                "colsample_bytree": LIGHTGBM_PARAMS["colsample_bytree"],
                "random_state": RANDOM_SEED,
                "verbosity": 0,
                "n_jobs": -1,
            }
            if use_gpu:
                xgb_params.update(XGBOOST_GPU_PARAMS)
            return xgb.XGBRegressor(**xgb_params)
        else:
            raise RuntimeError("No ML backend available (need lightgbm or xgboost)")


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def quantile_loss(y_true, y_pred, alpha):
    """Pinball / quantile loss."""
    residual = y_true - y_pred
    return np.mean(np.where(residual >= 0, alpha * residual, (alpha - 1) * residual))


def evaluate_forecaster(forecaster: QuantileForecaster,
                        X_val: pd.DataFrame,
                        y_val: pd.Series) -> dict:
    """Compute evaluation metrics on a validation set."""
    preds = forecaster.predict(X_val)
    metrics = {}

    # Point forecast metrics (P50)
    p50 = preds["p50"]
    metrics["mae"] = float(np.mean(np.abs(y_val - p50)))
    metrics["rmse"] = float(np.sqrt(np.mean((y_val - p50) ** 2)))
    nonzero = y_val > 0
    if nonzero.sum() > 0:
        metrics["mape"] = float(np.mean(np.abs((y_val[nonzero] - p50[nonzero]) / y_val[nonzero])) * 100)
    else:
        metrics["mape"] = 0.0

    # Quantile losses
    for label, alpha in QUANTILES.items():
        metrics[f"qloss_{label}"] = float(quantile_loss(y_val.values, preds[label], alpha))

    # Coverage: fraction of actuals within P10–P90 band
    in_band = (y_val.values >= preds["p10"]) & (y_val.values <= preds["p90"])
    metrics["coverage_p10_p90"] = float(np.mean(in_band))

    # Average interval width
    metrics["interval_width"] = float(np.mean(preds["p90"] - preds["p10"]))

    return metrics
