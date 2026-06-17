"""
Model training pipeline.

Usage:
    python -m src.train --data-dir ./data --model-path ./pickle/model.pkl

Workflow:
    1. Load & unify CSVs from data_dir
    2. Validate data (non-fatal)
    3. Engineer features at (Date, Channel, CampaignType) grain
    4. Build forward-looking training targets (revenue sums for 30/60/90 days)
    5. Time-based train / validation split (80 / 20)
    6. Train LightGBM quantile models (P10, P50, P90)
    7. Evaluate on holdout
    8. Save model artifact to model_path
"""

import argparse
import json
import logging
import os
import sys
import numpy as np
import pandas as pd

from src.utils import (
    RANDOM_SEED, MODEL_FEATURE_COLUMNS, FORECAST_HORIZONS,
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_TYPE,
    setup_logging, ensure_dir,
)
from src.preprocessing import unify_schema
from src.validation import validate_data
from src.generate_features import engineer_features
from src.forecasting import (
    build_training_targets, QuantileForecaster, evaluate_forecaster,
)

logger = logging.getLogger("forecast.train")

np.random.seed(RANDOM_SEED)


def _time_split(df: pd.DataFrame, train_frac: float = 0.80):
    """Split by date: earliest *train_frac* for training, rest for validation."""
    dates = sorted(df[COL_DATE].unique())
    cutoff_idx = int(len(dates) * train_frac)
    cutoff_date = dates[cutoff_idx]
    train = df[df[COL_DATE] < cutoff_date].copy()
    val = df[df[COL_DATE] >= cutoff_date].copy()
    logger.info(
        f"Time split: train {len(train)} rows (< {cutoff_date}), "
        f"val {len(val)} rows (>= {cutoff_date})"
    )
    return train, val


def _align_features(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Ensure df has exactly the columns in feature_cols (fill missing with 0)."""
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0
    return df[feature_cols]


def train_model(data_dir: str, model_path: str):
    """End-to-end training pipeline."""
    logger.info("=" * 60)
    logger.info("TRAINING PIPELINE START")
    logger.info("=" * 60)

    # ---- Step 1: Load & unify ----
    raw = unify_schema(data_dir)
    if len(raw) == 0:
        logger.error("No data loaded — cannot train")
        sys.exit(1)

    # ---- Step 2: Validate ----
    cleaned, report = validate_data(raw)
    logger.info(f"Validation: {report.get('status')}")

    # ---- Step 3: Feature engineering ----
    features = engineer_features(cleaned)
    if len(features) == 0:
        logger.error("Feature engineering produced empty result — cannot train")
        sys.exit(1)

    # ---- Step 4: Build training targets ----
    training_data = build_training_targets(features)
    if len(training_data) == 0:
        logger.error("No valid training targets — cannot train")
        sys.exit(1)

    logger.info(f"Training data: {len(training_data)} samples")

    # ---- Step 5: Prepare feature matrix ----
    # Determine which MODEL_FEATURE_COLUMNS are actually present
    available_features = [c for c in MODEL_FEATURE_COLUMNS if c in training_data.columns]

    # 'Horizon' is always present from build_training_targets
    if "Horizon" not in available_features:
        available_features.append("Horizon")

    X_all = _align_features(training_data.copy(), available_features)
    y_all = training_data["Target_Revenue"]

    # ---- Step 6: Time-based split ----
    # Add Date back temporarily for splitting
    X_all["_date"] = training_data[COL_DATE].values
    dates = X_all["_date"]

    sorted_dates = sorted(dates.unique())
    cutoff_idx = int(len(sorted_dates) * 0.80)
    cutoff_date = sorted_dates[cutoff_idx]

    train_mask = dates < cutoff_date
    val_mask = dates >= cutoff_date

    X_train = X_all.loc[train_mask, available_features].copy()
    X_val = X_all.loc[val_mask, available_features].copy()
    y_train = y_all[train_mask]
    y_val = y_all[val_mask]

    logger.info(f"Train: {len(X_train)} samples, Val: {len(X_val)} samples")

    # ---- Step 7: Train forecaster ----
    forecaster = QuantileForecaster()
    forecaster.train(X_train, y_train)

    # Store metadata
    forecaster.metadata = {
        "n_train_samples": len(X_train),
        "n_val_samples": len(X_val),
        "feature_columns": available_features,
        "channels_seen": training_data[COL_CHANNEL].unique().tolist()
            if COL_CHANNEL in training_data.columns else [],
        "campaign_types_seen": training_data[COL_CAMPAIGN_TYPE].unique().tolist()
            if COL_CAMPAIGN_TYPE in training_data.columns else [],
        "date_range": [
            str(training_data[COL_DATE].min()),
            str(training_data[COL_DATE].max()),
        ] if COL_DATE in training_data.columns else [],
    }
    forecaster.feature_columns = available_features

    # ---- Step 8: Evaluate ----
    if len(X_val) > 0:
        metrics = evaluate_forecaster(forecaster, X_val, y_val)
        logger.info("Validation metrics:")
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")
        forecaster.metadata["val_metrics"] = metrics
    else:
        logger.warning("No validation data — skipping evaluation")

    # ---- Step 9: Save ----
    ensure_dir(model_path)
    forecaster.save(model_path)
    logger.info(f"Model saved to {model_path}")

    # Save report
    report_path = os.path.join(os.path.dirname(model_path), "training_report.json")
    try:
        with open(report_path, "w") as f:
            json.dump(forecaster.metadata, f, indent=2, default=str)
        logger.info(f"Training report saved to {report_path}")
    except Exception:
        pass

    logger.info("TRAINING PIPELINE COMPLETE")
    return forecaster


def main():
    parser = argparse.ArgumentParser(description="Train revenue forecasting model")
    parser.add_argument("--data-dir", default="./data",
                        help="Directory containing channel CSV files")
    parser.add_argument("--model-path", default="./pickle/model.pkl",
                        help="Path to save trained model")
    args = parser.parse_args()

    setup_logging()
    train_model(args.data_dir, args.model_path)


if __name__ == "__main__":
    main()
