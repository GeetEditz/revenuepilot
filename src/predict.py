"""
Prediction pipeline — the core of run.sh.

Usage (via run.sh):
    python -m src.predict \\
        --data-dir ./data \\
        --features ./output/features.csv \\
        --model ./pickle/model.pkl \\
        --output ./output/predictions.csv

Workflow:
    1. Load pre-computed features (or generate from raw data)
    2. Load model.pkl
    3. For each (Channel, CampaignType) × horizon, predict revenue P10/P50/P90
    4. Aggregate to channel and total level
    5. Compute ROAS = Revenue / projected spend
    6. Generate rule-based explanation
    7. Write predictions.csv (exactly 3 rows: horizons 30, 60, 90)

Emergency fallback: if model loading fails, use statistical daily-average method.
"""

import argparse
import logging
import os
import sys
import traceback
import numpy as np
import pandas as pd

from src.utils import (
    FORECAST_HORIZONS, ALL_CHANNELS, MODEL_FEATURE_COLUMNS,
    OUTPUT_COLUMNS, COL_DATE, COL_CHANNEL, COL_CAMPAIGN_TYPE,
    COL_SPEND, COL_REVENUE,
    safe_divide, format_output, setup_logging, ensure_dir,
)
from src.preprocessing import unify_schema
from src.validation import validate_data
from src.generate_features import engineer_features
from src.ai_insights import generate_insights

logger = logging.getLogger("forecast.predict")


# ---------------------------------------------------------------------------
# Emergency fallback — always produces valid output
# ---------------------------------------------------------------------------

def _emergency_predictions(data_dir: str) -> dict:
    """
    Statistical fallback using daily averages when the model fails.
    Guarantees a valid predictions.csv is always produced.
    """
    logger.warning("Using EMERGENCY statistical fallback")
    try:
        raw = unify_schema(data_dir)
        if len(raw) == 0:
            raise ValueError("No data")

        daily = raw.groupby([COL_DATE, COL_CHANNEL]).agg({
            COL_REVENUE: "sum", COL_SPEND: "sum"
        }).reset_index()

        channel_daily = daily.groupby(COL_CHANNEL).agg({
            COL_REVENUE: "mean", COL_SPEND: "mean"
        })

        results = {}
        for h in FORECAST_HORIZONS:
            channels_pred = {}
            spend_dict = {}
            total_rev, total_spend = 0.0, 0.0

            for ch in ALL_CHANNELS:
                if ch in channel_daily.index:
                    rev = float(channel_daily.loc[ch, COL_REVENUE]) * h
                    sp = float(channel_daily.loc[ch, COL_SPEND]) * h
                else:
                    rev, sp = 0.0, 0.0
                channels_pred[ch] = {"p10": rev * 0.7, "p50": rev, "p90": rev * 1.3}
                spend_dict[ch] = sp
                total_rev += rev
                total_spend += sp

            spend_dict["total"] = max(total_spend, 1e-9)
            results[h] = {
                "total": {"p10": total_rev * 0.7, "p50": total_rev, "p90": total_rev * 1.3},
                "spend": spend_dict,
                "channels": channels_pred,
                "confidence": 0.3,
                "explanation": "Fallback forecast using historical daily averages.",
            }
        return results

    except Exception:
        logger.error(f"Emergency fallback also failed: {traceback.format_exc()}")
        results = {}
        for h in FORECAST_HORIZONS:
            results[h] = {
                "total": {"p10": 0, "p50": 0, "p90": 0},
                "spend": {"total": 1, "Google": 1, "Meta": 1, "Bing": 1},
                "channels": {ch: {"p10": 0, "p50": 0, "p90": 0} for ch in ALL_CHANNELS},
                "confidence": 0.0,
                "explanation": "Unable to generate forecast - insufficient data.",
            }
        return results


# ---------------------------------------------------------------------------
# Core prediction logic
# ---------------------------------------------------------------------------

def _compute_projected_spend(features_df: pd.DataFrame, horizon: int) -> dict:
    """
    Project spend for each channel over the next *horizon* days using
    the average daily spend from the most recent 14 days of data.
    """
    if len(features_df) == 0 or COL_DATE not in features_df.columns:
        return {"total": 1, **{ch: 0 for ch in ALL_CHANNELS}}

    max_date = features_df[COL_DATE].max()
    lookback = pd.Timedelta(days=14)
    recent = features_df[features_df[COL_DATE] >= (max_date - lookback)]

    if len(recent) == 0:
        recent = features_df

    spend = {}
    total = 0.0
    for ch in ALL_CHANNELS:
        ch_data = recent[recent[COL_CHANNEL] == ch]
        if len(ch_data) > 0:
            n_days = ch_data[COL_DATE].nunique()
            n_days = max(n_days, 1)
            daily_spend = ch_data[COL_SPEND].sum() / n_days
            projected = daily_spend * horizon
        else:
            projected = 0.0
        spend[ch] = projected
        total += projected

    spend["total"] = max(total, 1e-9)
    return spend


def _get_latest_features(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the latest date's feature rows for each (Channel, CampaignType).
    These serve as the input state for forecasting.

    Uses each group's own most-recent date so that channels whose data
    ends on different days are all represented.
    """
    if len(features_df) == 0:
        return features_df

    if COL_CHANNEL not in features_df.columns or COL_CAMPAIGN_TYPE not in features_df.columns:
        max_date = features_df[COL_DATE].max()
        return features_df[features_df[COL_DATE] == max_date].copy()

    # Per-group latest: each (Channel, CampaignType) keeps its own max date row
    idx = features_df.groupby([COL_CHANNEL, COL_CAMPAIGN_TYPE])[COL_DATE].idxmax()
    latest = features_df.loc[idx].copy()

    if len(latest) == 0:
        latest = features_df.copy()

    return latest


def predict(data_dir: str, features_path: str, model_path: str, output_path: str):
    """Full prediction pipeline."""
    logger.info("=" * 60)
    logger.info("PREDICTION PIPELINE START")
    logger.info("=" * 60)

    # ---- Step 1: Load features ----
    features_df = None
    if features_path and os.path.exists(features_path):
        try:
            features_df = pd.read_csv(features_path)
            if COL_DATE in features_df.columns:
                features_df[COL_DATE] = pd.to_datetime(features_df[COL_DATE], errors="coerce")
            logger.info(f"Loaded features from {features_path}: {len(features_df)} rows")
        except Exception as exc:
            logger.warning(f"Failed to load features file: {exc}")

    # Fallback: generate features from raw data
    if features_df is None or len(features_df) == 0:
        logger.info("Generating features from raw data ...")
        raw = unify_schema(data_dir)
        if len(raw) == 0:
            logger.error("No data - using emergency fallback")
            preds = _emergency_predictions(data_dir)
            _write_output(preds, output_path)
            return
        cleaned, _ = validate_data(raw)
        features_df = engineer_features(cleaned)

    if len(features_df) == 0:
        logger.error("Empty features - using emergency fallback")
        preds = _emergency_predictions(data_dir)
        _write_output(preds, output_path)
        return

    # ---- Step 2: Load model ----
    try:
        from src.forecasting import QuantileForecaster
        forecaster = QuantileForecaster.load(model_path)
        model_features = forecaster.feature_columns
        logger.info(f"Model loaded: {len(model_features)} features")
    except Exception as exc:
        logger.error(f"Model loading failed: {exc} - using emergency fallback")
        preds = _emergency_predictions(data_dir)
        _write_output(preds, output_path)
        return

    # ---- Step 3: Prepare prediction inputs ----
    latest = _get_latest_features(features_df)
    logger.info(f"Latest feature rows: {len(latest)}")

    # Identify (Channel, CampaignType) groups
    groups = latest.groupby([COL_CHANNEL, COL_CAMPAIGN_TYPE])

    # ---- Step 4: Predict per (channel, type, horizon) ----
    predictions_internal = {}

    for horizon in FORECAST_HORIZONS:
        channel_revenue = {ch: {"p10": 0.0, "p50": 0.0, "p90": 0.0} for ch in ALL_CHANNELS}
        total_revenue = {"p10": 0.0, "p50": 0.0, "p90": 0.0}

        for (channel, ctype), gdf in groups:
            # Build feature vector for this group
            row = gdf.iloc[[0]].copy()  # take first row (one per group at latest date)
            row["Horizon"] = horizon

            # Align to model features
            X = pd.DataFrame(columns=model_features)
            for col in model_features:
                if col in row.columns:
                    X[col] = row[col].values
                else:
                    X[col] = [0.0]

            # Convert all to float
            X = X.astype(float)

            try:
                preds = forecaster.predict(X)
                p10 = float(preds["p10"][0])
                p50 = float(preds["p50"][0])
                p90 = float(preds["p90"][0])
            except Exception as exc:
                logger.warning(f"Prediction failed for {channel}/{ctype}: {exc}")
                p10, p50, p90 = 0.0, 0.0, 0.0

            # Accumulate channel-level
            ch_key = channel if channel in ALL_CHANNELS else "Google"
            channel_revenue[ch_key]["p10"] += p10
            channel_revenue[ch_key]["p50"] += p50
            channel_revenue[ch_key]["p90"] += p90

            total_revenue["p10"] += p10
            total_revenue["p50"] += p50
            total_revenue["p90"] += p90

        # Compute projected spend
        spend = _compute_projected_spend(features_df, horizon)

        # Compute confidence score
        width = total_revenue["p90"] - total_revenue["p10"]
        median = max(total_revenue["p50"], 1e-9)
        confidence = max(0.0, min(1.0, 1.0 - (width / (2 * median))))

        predictions_internal[horizon] = {
            "total": total_revenue,
            "spend": spend,
            "channels": channel_revenue,
            "confidence": confidence,
            "explanation": "",  # filled below
        }

    # ---- Step 5: Generate insights ----
    try:
        # Collect data stats for insights
        data_stats = {
            "n_rows": len(features_df),
            "channels": features_df[COL_CHANNEL].unique().tolist()
                if COL_CHANNEL in features_df.columns else [],
            "date_range": [
                str(features_df[COL_DATE].min()),
                str(features_df[COL_DATE].max()),
            ] if COL_DATE in features_df.columns else [],
        }
        for horizon in FORECAST_HORIZONS:
            explanation = generate_insights(predictions_internal[horizon], data_stats)
            predictions_internal[horizon]["explanation"] = explanation
    except Exception as exc:
        logger.warning(f"Insight generation failed: {exc}")
        for horizon in FORECAST_HORIZONS:
            p = predictions_internal[horizon]
            predictions_internal[horizon]["explanation"] = (
                f"{horizon}-day forecast: Revenue expected ${p['total']['p50']:,.0f} "
                f"(range: ${p['total']['p10']:,.0f} - ${p['total']['p90']:,.0f})."
            )

    # ---- Step 6: Write output ----
    _write_output(predictions_internal, output_path)
    logger.info("PREDICTION PIPELINE COMPLETE")


def _write_output(predictions_internal: dict, output_path: str):
    """Format and write predictions.csv."""
    ensure_dir(output_path)
    df = format_output(predictions_internal)
    df.to_csv(output_path, index=False)
    logger.info(f"Predictions written to {output_path} ({len(df)} rows)")
    # Print summary
    for _, row in df.iterrows():
        h = int(row["Forecast_Horizon"])
        logger.info(
            f"  {h}d: Rev=${row['Revenue_P50']:,.0f} "
            f"[${row['Revenue_P10']:,.0f}-${row['Revenue_P90']:,.0f}], "
            f"ROAS={row['ROAS_P50']:.2f}"
        )


def main():
    parser = argparse.ArgumentParser(description="Generate revenue forecasts")
    parser.add_argument("--data-dir", default="./data",
                        help="Directory containing channel CSV files")
    parser.add_argument("--features", default="",
                        help="Path to pre-computed features CSV (optional)")
    parser.add_argument("--model", default="./pickle/model.pkl",
                        help="Path to trained model")
    parser.add_argument("--output", default="./output/predictions.csv",
                        help="Path to write predictions CSV")
    args = parser.parse_args()

    setup_logging()
    predict(args.data_dir, args.features, args.model, args.output)


if __name__ == "__main__":
    main()
