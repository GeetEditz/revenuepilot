"""
Data ingestion and schema unification for multi-channel advertising data.

Handles the REAL data formats discovered in test files:

Google Ads:
  - segments_date, metrics_clicks, metrics_conversions, metrics_cost_micros,
    metrics_impressions, metrics_video_views, metrics_conversions_value,
    campaign_advertising_channel_type, campaign_budget_amount, campaign_name
  - cost is in MICROS (divide by 1_000_000)

Meta Ads:
  - date_start, cpc, cpm, ctr, reach, spend, clicks, impressions,
    conversion (= revenue proxy), daily_budget, campaign_name
  - NO explicit campaign_type column — inferred from campaign_name
  - NO explicit revenue column — 'conversion' column IS the revenue

Bing Ads:
  - TimePeriod, Revenue, Spend, Clicks, Impressions, Conversions,
    CampaignType, DailyBudget, CampaignName
"""

import os
import glob
import logging
import re
import pandas as pd
import numpy as np

from src.utils import (
    UNIFIED_COLUMNS, NUMERIC_COLUMNS, CHANNEL_FILE_MAP,
    COL_DATE, COL_CHANNEL, COL_CAMPAIGN_NAME, COL_CAMPAIGN_TYPE,
    COL_SPEND, COL_REVENUE, COL_CLICKS, COL_IMPRESSIONS,
    COL_CONVERSIONS, COL_BUDGET,
)

logger = logging.getLogger("forecast.preprocessing")

# ---------------------------------------------------------------------------
# Column-name aliases → unified schema  (100+ entries covering real data)
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    # ---- Date ----
    "date": COL_DATE, "day": COL_DATE, "report_date": COL_DATE,
    "reporting_date": COL_DATE, "ds": COL_DATE, "report_day": COL_DATE,
    "segments_date": COL_DATE,        # Google Ads
    "date_start": COL_DATE,           # Meta Ads
    "timeperiod": COL_DATE,           # Bing Ads
    "time_period": COL_DATE,
    # ---- Channel ----
    "channel": COL_CHANNEL, "platform": COL_CHANNEL, "source": COL_CHANNEL,
    "ad_platform": COL_CHANNEL, "network": COL_CHANNEL,
    "advertising_channel": COL_CHANNEL,
    # ---- Campaign Name ----
    "campaignname": COL_CAMPAIGN_NAME, "campaign_name": COL_CAMPAIGN_NAME,
    "campaign": COL_CAMPAIGN_NAME, "name": COL_CAMPAIGN_NAME,
    "campaign_title": COL_CAMPAIGN_NAME, "ad_campaign": COL_CAMPAIGN_NAME,
    # ---- Campaign Type ----
    "campaigntype": COL_CAMPAIGN_TYPE, "campaign_type": COL_CAMPAIGN_TYPE,
    "type": COL_CAMPAIGN_TYPE, "campaign_subtype": COL_CAMPAIGN_TYPE,
    "campaign_advertising_channel_type": COL_CAMPAIGN_TYPE,  # Google Ads
    "advertising_channel_type": COL_CAMPAIGN_TYPE,
    "objective": COL_CAMPAIGN_TYPE, "campaign_objective": COL_CAMPAIGN_TYPE,
    # ---- Spend ----
    "spend": COL_SPEND, "cost": COL_SPEND, "amount_spent": COL_SPEND,
    "total_spend": COL_SPEND, "ad_spend": COL_SPEND, "total_cost": COL_SPEND,
    "amount": COL_SPEND,
    # NOTE: metrics_cost_micros handled specially (÷ 1_000_000)
    "metrics_cost_micros": "_cost_micros",  # special sentinel
    # ---- Revenue ----
    "revenue": COL_REVENUE, "conversion_value": COL_REVENUE,
    "conv_value": COL_REVENUE, "total_revenue": COL_REVENUE,
    "purchase_value": COL_REVENUE, "value": COL_REVENUE, "sales": COL_REVENUE,
    "total_conversion_value": COL_REVENUE, "purchase_roas_value": COL_REVENUE,
    "all_conv_value": COL_REVENUE, "conv._value": COL_REVENUE,
    "metrics_conversions_value": COL_REVENUE,  # Google Ads
    "conversion": COL_REVENUE,                 # Meta Ads — conversion IS revenue
    # ---- Clicks ----
    "clicks": COL_CLICKS, "link_clicks": COL_CLICKS,
    "total_clicks": COL_CLICKS, "outbound_clicks": COL_CLICKS,
    "metrics_clicks": COL_CLICKS,              # Google Ads
    # ---- Impressions ----
    "impressions": COL_IMPRESSIONS, "imps": COL_IMPRESSIONS,
    "total_impressions": COL_IMPRESSIONS,
    "metrics_impressions": COL_IMPRESSIONS,     # Google Ads
    # ---- Conversions ----
    "conversions": COL_CONVERSIONS, "total_conversions": COL_CONVERSIONS,
    "purchases": COL_CONVERSIONS, "results": COL_CONVERSIONS,
    "all_conversions": COL_CONVERSIONS, "actions": COL_CONVERSIONS,
    "metrics_conversions": COL_CONVERSIONS,     # Google Ads
    # ---- Budget ----
    "budget": COL_BUDGET, "daily_budget": COL_BUDGET,
    "campaign_budget": COL_BUDGET, "avg_budget": COL_BUDGET,
    "average_budget": COL_BUDGET, "campaign_daily_budget": COL_BUDGET,
    "campaign_budget_amount": COL_BUDGET,       # Google Ads
    "dailybudget": COL_BUDGET,                  # Bing Ads
}

# Campaign type normalisation: raw → canonical
CAMPAIGN_TYPE_NORMALISATION = {
    "SEARCH": "Search",
    "SHOPPING": "Shopping",
    "DISPLAY": "Display",
    "VIDEO": "Video",
    "PERFORMANCE_MAX": "Performance Max",
    "PERFORMANCEMAX": "Performance Max",
    "DEMAND_GEN": "Demand Gen",
    "DEMAND GEN": "Demand Gen",
    "DEMANDGEN": "Demand Gen",
    "DISCOVERY": "Discovery",
    "APP": "App",
    "SMART": "Smart",
    "LOCAL": "Local",
    "AUDIENCE": "Audience",
    "BRAND": "Brand",
    "REMARKETING": "Remarketing",
    "RETARGETING": "Remarketing",
}

# Patterns for inferring campaign type from campaign name (Meta fallback)
_CAMPAIGN_TYPE_PATTERNS = [
    (re.compile(r"search", re.I), "Search"),
    (re.compile(r"shop", re.I), "Shopping"),
    (re.compile(r"display", re.I), "Display"),
    (re.compile(r"video", re.I), "Video"),
    (re.compile(r"pmax|performance.?max", re.I), "Performance Max"),
    (re.compile(r"demand.?gen", re.I), "Demand Gen"),
    (re.compile(r"discovery", re.I), "Discovery"),
    (re.compile(r"remarketing|retarget|dpa.*remarketing|remarketing.*dpa", re.I), "Remarketing"),
    (re.compile(r"prospecting|prospect", re.I), "Prospecting"),
    (re.compile(r"brand", re.I), "Brand"),
    (re.compile(r"awareness", re.I), "Awareness"),
    (re.compile(r"traffic", re.I), "Traffic"),
    (re.compile(r"conversion", re.I), "Conversions"),
    (re.compile(r"lead", re.I), "Leads"),
    (re.compile(r"app", re.I), "App"),
    (re.compile(r"engagement|engage", re.I), "Engagement"),
    (re.compile(r"reach", re.I), "Reach"),
    (re.compile(r"generic", re.I), "Generic"),
    (re.compile(r"dpa|dynamic.?product", re.I), "DPA"),
    (re.compile(r"adv.?plus|advantage", re.I), "Advantage Plus"),
]


def _detect_channel(filename: str) -> str:
    """Infer the advertising channel from a filename or string."""
    fname_lower = filename.lower()
    for keyword, channel in CHANNEL_FILE_MAP.items():
        if keyword in fname_lower:
            return channel
    return "Unknown"


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw column names to the unified schema via alias lookup."""
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "_")
        if key in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[key]
        elif col.strip() in UNIFIED_COLUMNS:
            rename_map[col] = col.strip()
    return df.rename(columns=rename_map)


def _infer_campaign_type_from_name(name: str) -> str:
    """Infer campaign type from campaign name using regex patterns."""
    if not isinstance(name, str) or not name.strip():
        return "Unknown"
    for pattern, ctype in _CAMPAIGN_TYPE_PATTERNS:
        if pattern.search(name):
            return ctype
    return "Generic"


def _normalise_campaign_type(val) -> str:
    """Normalise a raw campaign type string to a canonical form."""
    if pd.isna(val) or str(val).strip() == "":
        return "Unknown"
    s = str(val).strip()
    upper = s.upper().replace(" ", "_")
    if upper in CAMPAIGN_TYPE_NORMALISATION:
        return CAMPAIGN_TYPE_NORMALISATION[upper]
    # Try without underscores
    no_under = upper.replace("_", "")
    for k, v in CAMPAIGN_TYPE_NORMALISATION.items():
        if k.replace("_", "") == no_under:
            return v
    return s  # keep original if no mapping


def load_channel_data(filepath: str, channel_name: str = None) -> pd.DataFrame:
    """
    Load a single CSV, normalise columns, handle platform-specific quirks,
    and tag with *channel_name*.
    """
    if channel_name is None:
        channel_name = _detect_channel(os.path.basename(filepath))

    logger.info(f"Loading {os.path.basename(filepath)} as channel={channel_name}")

    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as exc:
        logger.error(f"Failed to read {filepath}: {exc}")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    if df.empty:
        logger.warning(f"File {filepath} is empty")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    # Drop pandas index artefact columns
    for col in list(df.columns):
        if col.startswith("Unnamed"):
            df = df.drop(columns=[col])

    # Normalise column names
    df = _normalise_columns(df)

    # ---- Platform-specific transforms ----

    # Google Ads: cost is in micros → convert to dollars
    if "_cost_micros" in df.columns:
        df[COL_SPEND] = pd.to_numeric(df["_cost_micros"], errors="coerce").fillna(0.0) / 1_000_000
        df = df.drop(columns=["_cost_micros"])

    # If spend column already existed AND _cost_micros was also processed,
    # prefer the micros conversion (already done above). Otherwise keep spend.

    # ---- Channel ----
    if COL_CHANNEL not in df.columns:
        df[COL_CHANNEL] = channel_name
    else:
        df[COL_CHANNEL] = df[COL_CHANNEL].fillna(channel_name).astype(str)
        for keyword, canonical in CHANNEL_FILE_MAP.items():
            mask = df[COL_CHANNEL].str.lower().str.contains(keyword, na=False)
            df.loc[mask, COL_CHANNEL] = canonical
        unknown_mask = ~df[COL_CHANNEL].isin(["Google", "Meta", "Bing"])
        df.loc[unknown_mask, COL_CHANNEL] = channel_name

    # ---- Campaign Type ----
    if COL_CAMPAIGN_TYPE not in df.columns:
        # Infer from campaign name (critical for Meta Ads which lacks this column)
        if COL_CAMPAIGN_NAME in df.columns:
            df[COL_CAMPAIGN_TYPE] = df[COL_CAMPAIGN_NAME].apply(
                _infer_campaign_type_from_name
            )
            logger.info(f"  Inferred campaign types from names: {df[COL_CAMPAIGN_TYPE].unique().tolist()}")
        else:
            df[COL_CAMPAIGN_TYPE] = "Unknown"
    else:
        # Normalise existing campaign types (e.g. SEARCH → Search)
        df[COL_CAMPAIGN_TYPE] = df[COL_CAMPAIGN_TYPE].apply(_normalise_campaign_type)

    # ---- Ensure all unified columns exist ----
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            if col in NUMERIC_COLUMNS:
                df[col] = 0.0
            elif col == COL_CAMPAIGN_NAME:
                df[col] = "Unknown_Campaign"
            elif col == COL_CAMPAIGN_TYPE:
                df[col] = "Unknown"
            else:
                df[col] = np.nan

    # Keep only unified columns
    df = df[[c for c in UNIFIED_COLUMNS if c in df.columns]]

    # ---- Parse dates ----
    if COL_DATE in df.columns:
        df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce", dayfirst=False)

    # ---- Coerce numerics ----
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    logger.info(f"  -> {len(df)} rows loaded, types: {df[COL_CAMPAIGN_TYPE].unique().tolist()}")
    return df


def unify_schema(data_dir: str) -> pd.DataFrame:
    """
    Discover all CSVs in *data_dir*, load them, and concatenate into a single
    DataFrame with a guaranteed unified schema sorted by date.
    """
    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    logger.info(f"Found {len(csv_files)} CSV file(s) in {data_dir}")

    frames = []
    for fp in csv_files:
        df = load_channel_data(fp)
        if len(df) > 0:
            frames.append(df)

    if not frames:
        logger.warning("No data loaded from any file")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    unified = pd.concat(frames, ignore_index=True)

    # Drop rows where date could not be parsed
    if COL_DATE in unified.columns:
        unified = unified.dropna(subset=[COL_DATE])
        unified = unified.sort_values(COL_DATE).reset_index(drop=True)

    channels = unified[COL_CHANNEL].unique().tolist() if COL_CHANNEL in unified.columns else []
    types = unified[COL_CAMPAIGN_TYPE].unique().tolist() if COL_CAMPAIGN_TYPE in unified.columns else []
    logger.info(f"Unified dataset: {len(unified)} rows, channels: {channels}, types: {types}")
    return unified
