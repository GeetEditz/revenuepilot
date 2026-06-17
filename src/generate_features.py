"""
Feature engineering pipeline for revenue forecasting.

Operates on a *unified* DataFrame (output of preprocessing.py), aggregates to
the (Date, Channel, CampaignType) grain, and produces 40+ features including
rolling stats, lags, trends, seasonality, momentum, volatility, share, and
dict-based categorical encodings.

Can be invoked as a CLI:
    python -m src.generate_features --data-dir ./data --output ./output/features.csv
"""

import argparse
import logging
import sys
import numpy as np
import pandas as pd

from src.utils import (
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_TYPE, COL_CAMPAIGN_NAME,
    COL_SPEND, COL_REVENUE, COL_CLICKS, COL_IMPRESSIONS,
    COL_CONVERSIONS, COL_BUDGET, COL_CTR, COL_CPC, COL_CPA, COL_ROAS,
    CHANNEL_ENCODING, CAMPAIGN_TYPE_ENCODING, NUMERIC_COLUMNS,
    safe_divide, encode_value, setup_logging, ensure_dir,
)
from src.preprocessing import unify_schema
from src.validation import validate_data

logger = logging.getLogger("forecast.features")

# Group key used throughout
GROUP_KEYS = [COL_DATE, COL_CHANNEL, COL_CAMPAIGN_TYPE]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw campaign rows to (Date, Channel, CampaignType) grain."""
    agg_map = {
        COL_SPEND: "sum",
        COL_REVENUE: "sum",
        COL_CLICKS: "sum",
        COL_IMPRESSIONS: "sum",
        COL_CONVERSIONS: "sum",
        COL_BUDGET: "mean",  # budget is typically per-campaign, average is safest
    }
    # Keep only columns that exist
    agg_map = {k: v for k, v in agg_map.items() if k in df.columns}
    grouped = df.groupby(GROUP_KEYS, as_index=False).agg(agg_map)
    return grouped.sort_values(GROUP_KEYS).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Derived ratio features
# ---------------------------------------------------------------------------

def add_ratio_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add CTR, CPC, CPA, ROAS."""
    df[COL_CTR] = safe_divide(df[COL_CLICKS], df[COL_IMPRESSIONS])
    df[COL_CPC] = safe_divide(df[COL_SPEND], df[COL_CLICKS])
    df[COL_CPA] = safe_divide(df[COL_SPEND], df[COL_CONVERSIONS])
    df[COL_ROAS] = safe_divide(df[COL_REVENUE], df[COL_SPEND])
    df["Conversion_Rate"] = safe_divide(df[COL_CONVERSIONS], df[COL_CLICKS])
    df["Revenue_Per_Conversion"] = safe_divide(df[COL_REVENUE], df[COL_CONVERSIONS])
    df["Budget_Utilization"] = safe_divide(df[COL_SPEND], df[COL_BUDGET])
    df["Spend_Per_Impression"] = safe_divide(df[COL_SPEND], df[COL_IMPRESSIONS])
    return df


# ---------------------------------------------------------------------------
# Temporal / Seasonality features
# ---------------------------------------------------------------------------

def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract calendar and cyclical seasonality features from Date."""
    dt = pd.to_datetime(df[COL_DATE])
    df["Month"] = dt.dt.month
    df["Quarter"] = dt.dt.quarter
    df["WeekOfYear"] = dt.dt.isocalendar().week.astype(int)
    df["DayOfYear"] = dt.dt.dayofyear
    df["DayOfWeek"] = dt.dt.dayofweek
    df["IsWeekend"] = (df["DayOfWeek"] >= 5).astype(int)
    df["IsMonthStart"] = (dt.dt.day <= 3).astype(int)
    df["IsMonthEnd"] = (dt.dt.day >= 28).astype(int)
    # Cyclical encoding
    df["Month_Sin"] = np.sin(2 * np.pi * df["Month"] / 12)
    df["Month_Cos"] = np.cos(2 * np.pi * df["Month"] / 12)
    df["Week_Sin"] = np.sin(2 * np.pi * df["WeekOfYear"] / 52)
    df["Week_Cos"] = np.cos(2 * np.pi * df["WeekOfYear"] / 52)
    return df


# ---------------------------------------------------------------------------
# Lag features
# ---------------------------------------------------------------------------

def _group_shift(df: pd.DataFrame, col: str, periods: int) -> pd.Series:
    """Shift *col* by *periods* within each (Channel, CampaignType) group."""
    return df.groupby([COL_CHANNEL, COL_CAMPAIGN_TYPE])[col].shift(periods)


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag-7/14/30 features for Revenue, Spend, ROAS."""
    for lag in [7, 14, 30]:
        df[f"Revenue_Lag_{lag}"] = _group_shift(df, COL_REVENUE, lag)
    for lag in [7, 14]:
        df[f"Spend_Lag_{lag}"] = _group_shift(df, COL_SPEND, lag)
    df["ROAS_Lag_7"] = _group_shift(df, COL_ROAS, 7)
    return df


# ---------------------------------------------------------------------------
# Rolling features
# ---------------------------------------------------------------------------

def _group_rolling(df: pd.DataFrame, col: str, window: int,
                   func: str = "mean") -> pd.Series:
    """Rolling aggregation within each (Channel, CampaignType) group."""
    grp = df.groupby([COL_CHANNEL, COL_CAMPAIGN_TYPE])[col]
    if func == "mean":
        return grp.transform(lambda s: s.rolling(window, min_periods=1).mean())
    elif func == "std":
        return grp.transform(lambda s: s.rolling(window, min_periods=1).std().fillna(0))
    return grp.transform(lambda s: s.rolling(window, min_periods=1).mean())


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling-7/14/30 mean (and std) features."""
    for w in [7, 14, 30]:
        df[f"Revenue_Rolling_{w}"] = _group_rolling(df, COL_REVENUE, w, "mean")
    for w in [7, 14]:
        df[f"Spend_Rolling_{w}"] = _group_rolling(df, COL_SPEND, w, "mean")
    for w in [7, 14]:
        df[f"ROAS_Rolling_{w}"] = _group_rolling(df, COL_ROAS, w, "mean")
    df["Revenue_Rolling_Std_7"] = _group_rolling(df, COL_REVENUE, 7, "std")
    return df


# ---------------------------------------------------------------------------
# Trend features  (slope = (current – value_N_days_ago) / N)
# ---------------------------------------------------------------------------

def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """14-day trend (simple slope approximation) for Revenue, Spend, ROAS."""
    window = 14
    for col, name in [(COL_REVENUE, "Revenue_Trend_14"),
                      (COL_SPEND, "Spend_Trend_14"),
                      (COL_ROAS, "ROAS_Trend_14")]:
        lagged = _group_shift(df, col, window)
        df[name] = safe_divide(df[col] - lagged.fillna(df[col]), window)
    return df


# ---------------------------------------------------------------------------
# Share features  (channel's proportion of total on that date)
# ---------------------------------------------------------------------------

def add_share_features(df: pd.DataFrame) -> pd.DataFrame:
    """Channel revenue & spend share relative to daily totals."""
    daily_total_rev = df.groupby(COL_DATE)[COL_REVENUE].transform("sum")
    daily_total_spend = df.groupby(COL_DATE)[COL_SPEND].transform("sum")
    df["Channel_Revenue_Share"] = safe_divide(df[COL_REVENUE], daily_total_rev)
    df["Channel_Spend_Share"] = safe_divide(df[COL_SPEND], daily_total_spend)
    return df


# ---------------------------------------------------------------------------
# Momentum features
# ---------------------------------------------------------------------------

def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """Short-term / long-term rolling ratio (>1 means acceleration)."""
    rev7 = df.get("Revenue_Rolling_7", pd.Series(0, index=df.index))
    rev30 = df.get("Revenue_Rolling_30", pd.Series(1, index=df.index))
    df["Revenue_Momentum_7"] = safe_divide(rev7, rev30, default=1.0)

    sp7 = df.get("Spend_Rolling_7", pd.Series(0, index=df.index))
    sp14 = df.get("Spend_Rolling_14", pd.Series(1, index=df.index))
    df["Spend_Momentum_7"] = safe_divide(sp7, sp14, default=1.0)
    return df


# ---------------------------------------------------------------------------
# Volatility / stability
# ---------------------------------------------------------------------------

def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """Coefficient of variation for Revenue and ROAS over 14-day window."""
    rev_std = _group_rolling(df, COL_REVENUE, 14, "std")
    rev_mean = _group_rolling(df, COL_REVENUE, 14, "mean")
    df["Revenue_Volatility_14"] = safe_divide(rev_std, rev_mean)

    roas_std = _group_rolling(df, COL_ROAS, 14, "std")
    roas_mean = _group_rolling(df, COL_ROAS, 14, "mean")
    df["ROAS_Stability_14"] = safe_divide(roas_std, roas_mean)
    return df


# ---------------------------------------------------------------------------
# Encoding features
# ---------------------------------------------------------------------------

def add_encoding_features(df: pd.DataFrame) -> pd.DataFrame:
    """Dict-based categorical encoding with unknown → 0 fallback."""
    df["Channel_Encoded"] = df[COL_CHANNEL].apply(
        lambda v: encode_value(v, CHANNEL_ENCODING)
    )
    df["CampaignType_Encoded"] = df[COL_CAMPAIGN_TYPE].apply(
        lambda v: encode_value(v, CAMPAIGN_TYPE_ENCODING)
    )
    return df


# ---------------------------------------------------------------------------
# Data-context feature
# ---------------------------------------------------------------------------

def add_data_context(df: pd.DataFrame) -> pd.DataFrame:
    """Number of unique dates in the dataset (constant for all rows)."""
    n_days = df[COL_DATE].nunique() if COL_DATE in df.columns else 1
    df["DaysOfData"] = n_days
    return df


# ---------------------------------------------------------------------------
# Master feature-engineering pipeline
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full feature-engineering pipeline.

    Input:  unified DataFrame (raw campaign rows).
    Output: aggregated DataFrame at (Date, Channel, CampaignType) grain
            with 40+ features.  NaN values are filled with 0.
    """
    if len(df) == 0:
        logger.warning("Empty DataFrame passed to engineer_features")
        return df

    logger.info("Aggregating to (Date, Channel, CampaignType) grain ...")
    df = aggregate_daily(df)

    logger.info("Computing ratio features ...")
    df = add_ratio_features(df)

    logger.info("Computing temporal features ...")
    df = add_temporal_features(df)

    logger.info("Computing lag features ...")
    df = add_lag_features(df)

    logger.info("Computing rolling features ...")
    df = add_rolling_features(df)

    logger.info("Computing trend features ...")
    df = add_trend_features(df)

    logger.info("Computing share features ...")
    df = add_share_features(df)

    logger.info("Computing momentum features ...")
    df = add_momentum_features(df)

    logger.info("Computing volatility features ...")
    df = add_volatility_features(df)

    logger.info("Adding encoding features ...")
    df = add_encoding_features(df)

    logger.info("Adding data context ...")
    df = add_data_context(df)

    # Fill any remaining NaN with 0 (lag/rolling warmup)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0.0)

    # Replace infinities
    df.replace([np.inf, -np.inf], 0.0, inplace=True)

    logger.info(f"Feature engineering complete: {df.shape[1]} columns, {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate features from raw advertising data")
    parser.add_argument("--data-dir", required=True, help="Directory containing channel CSV files")
    parser.add_argument("--output", required=True, help="Path to write features CSV")
    args = parser.parse_args()

    setup_logging()
    logger.info(f"=== Feature Generation: data_dir={args.data_dir} ===")

    # Step 1: Load & unify
    raw = unify_schema(args.data_dir)
    if len(raw) == 0:
        logger.error("No data loaded — writing empty features file")
        pd.DataFrame().to_csv(args.output, index=False)
        sys.exit(0)

    # Step 2: Validate
    cleaned, report = validate_data(raw)
    logger.info(f"Validation report: {report.get('status', 'UNKNOWN')}")

    # Step 3: Engineer features
    features = engineer_features(cleaned)

    # Step 4: Write
    ensure_dir(args.output)
    features.to_csv(args.output, index=False)
    logger.info(f"Features written to {args.output} ({len(features)} rows)")


if __name__ == "__main__":
    main()
