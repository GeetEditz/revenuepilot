"""
Data validation rules for the forecasting pipeline.

Every check is **non-fatal**: issues are logged, cleaned where possible,
and a structured report is returned.  The pipeline never crashes on data
quality problems — it degrades gracefully.
"""

import logging
import numpy as np
import pandas as pd

from src.utils import (
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_NAME, COL_CAMPAIGN_TYPE,
    COL_SPEND, COL_REVENUE, COL_CLICKS, COL_IMPRESSIONS,
    COL_CONVERSIONS, COL_BUDGET, NUMERIC_COLUMNS,
)

logger = logging.getLogger("forecast.validation")


def _check_missing_values(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Flag and fill missing values in critical columns."""
    missing = df.isnull().sum()
    missing_pct = (missing / max(len(df), 1) * 100).round(2)
    issues = {col: f"{cnt} ({missing_pct[col]}%)" for col, cnt in missing.items() if cnt > 0}
    report["missing_values"] = issues if issues else "No missing values"

    if issues:
        logger.warning(f"Missing values detected: {issues}")

    # Fill numeric columns with 0
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    # Fill categorical columns with defaults
    if COL_CAMPAIGN_NAME in df.columns:
        df[COL_CAMPAIGN_NAME] = df[COL_CAMPAIGN_NAME].fillna("Unknown_Campaign")
    if COL_CAMPAIGN_TYPE in df.columns:
        df[COL_CAMPAIGN_TYPE] = df[COL_CAMPAIGN_TYPE].fillna("Unknown")
    if COL_CHANNEL in df.columns:
        df[COL_CHANNEL] = df[COL_CHANNEL].fillna("Unknown")

    return df


def _check_duplicates(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Remove exact duplicate rows."""
    n_before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    n_dupes = n_before - len(df)
    report["duplicates_removed"] = n_dupes
    if n_dupes > 0:
        logger.warning(f"Removed {n_dupes} duplicate rows")
    return df


def _check_negative_spend(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Clamp negative spend values to zero."""
    if COL_SPEND not in df.columns:
        report["negative_spend"] = "Column not present"
        return df
    neg_mask = df[COL_SPEND] < 0
    n_neg = neg_mask.sum()
    report["negative_spend"] = int(n_neg)
    if n_neg > 0:
        logger.warning(f"Found {n_neg} rows with negative spend - clamped to 0")
        df.loc[neg_mask, COL_SPEND] = 0.0
    return df


def _check_revenue_anomalies(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Detect extreme revenue outliers — report only, do NOT clip.

    Revenue in advertising data has natural heavy tails. Clipping destroys
    signal and tanks model coverage. Instead, log the outlier count for
    awareness but leave the data intact.
    """
    if COL_REVENUE not in df.columns or len(df) < 10:
        report["revenue_anomalies"] = "Insufficient data for outlier detection"
        return df

    q1 = df[COL_REVENUE].quantile(0.25)
    q3 = df[COL_REVENUE].quantile(0.75)
    iqr = q3 - q1
    upper_bound = q3 + 5.0 * iqr  # Very generous — for reporting only
    lower_bound = max(0, q1 - 5.0 * iqr)

    outlier_mask = (df[COL_REVENUE] > upper_bound) | (df[COL_REVENUE] < lower_bound)
    n_outliers = outlier_mask.sum()
    report["revenue_anomalies"] = {
        "count": int(n_outliers),
        "upper_bound": round(upper_bound, 2),
        "lower_bound": round(lower_bound, 2),
        "action": "reported_only",
    }
    if n_outliers > 0:
        logger.info(
            f"Revenue outliers: {n_outliers} rows outside [{lower_bound:.0f}, {upper_bound:.0f}] "
            f"(kept — natural variance)"
        )
    return df


def _check_missing_dates(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Report gaps in the date series (informational only)."""
    if COL_DATE not in df.columns or len(df) < 2:
        report["date_gaps"] = "Insufficient data"
        return df

    dates = pd.to_datetime(df[COL_DATE], errors="coerce").dropna()
    if len(dates) < 2:
        report["date_gaps"] = "Insufficient valid dates"
        return df

    date_range = pd.date_range(dates.min(), dates.max(), freq="D")
    missing_dates = date_range.difference(dates.dt.normalize().unique())
    report["date_gaps"] = {
        "missing_days": len(missing_dates),
        "date_range": f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}",
    }
    if len(missing_dates) > 0:
        logger.info(f"Date gaps: {len(missing_dates)} missing day(s) in range")
    return df


def _check_missing_campaign_names(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Report rows with missing or placeholder campaign names."""
    if COL_CAMPAIGN_NAME not in df.columns:
        report["missing_campaign_names"] = "Column not present"
        return df
    placeholders = {"Unknown_Campaign", "unknown", "", "nan", "None"}
    mask = df[COL_CAMPAIGN_NAME].astype(str).isin(placeholders)
    n_missing = mask.sum()
    report["missing_campaign_names"] = int(n_missing)
    if n_missing > 0:
        logger.info(f"{n_missing} rows have missing/placeholder campaign names")
    return df


def _check_negative_metrics(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    """Clamp negative clicks, impressions, conversions to zero."""
    clamped = {}
    for col in [COL_CLICKS, COL_IMPRESSIONS, COL_CONVERSIONS]:
        if col in df.columns:
            neg_mask = df[col] < 0
            n_neg = neg_mask.sum()
            if n_neg > 0:
                df.loc[neg_mask, col] = 0.0
                clamped[col] = int(n_neg)
    report["negative_metrics_clamped"] = clamped if clamped else "None"
    return df


def validate_data(df: pd.DataFrame) -> tuple:
    """
    Run all validation rules on the unified DataFrame.

    Returns
    -------
    (cleaned_df, report) : tuple
        cleaned_df — DataFrame with issues fixed in-place.
        report     — dict summarising every check.
    """
    report = {"total_rows_input": len(df)}
    logger.info(f"Validating {len(df)} rows ...")

    if len(df) == 0:
        report["status"] = "EMPTY_DATA"
        logger.warning("Empty dataset - skipping validation")
        return df, report

    df = _check_missing_values(df, report)
    df = _check_duplicates(df, report)
    df = _check_negative_spend(df, report)
    df = _check_negative_metrics(df, report)
    df = _check_revenue_anomalies(df, report)
    df = _check_missing_dates(df, report)
    df = _check_missing_campaign_names(df, report)

    report["total_rows_output"] = len(df)
    report["status"] = "OK"
    logger.info(f"Validation complete - {len(df)} rows retained")
    return df, report
