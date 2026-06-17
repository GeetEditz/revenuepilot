"""
Generate realistic synthetic advertising data for training.

Creates CSV files matching the EXACT column formats of the real test data:
  - google_ads_campaign_stats.csv  (metrics_cost_micros, segments_date, etc.)
  - meta_ads_campaign_stats.csv    (date_start, conversion, spend, etc.)
  - bing_campaign_stats.csv        (TimePeriod, Revenue, CampaignType, etc.)

Usage:
    python scripts/generate_sample_data.py [--output-dir ./data] [--days 365]
"""

import argparse
import os
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)


def _seasonal_multiplier(day_of_year: int) -> float:
    """Seasonal pattern: Q4 peak, Q1 dip."""
    # Base seasonal curve
    base = 1.0 + 0.3 * np.sin(2 * np.pi * (day_of_year - 90) / 365)
    # Q4 boost (Black Friday, Holiday season)
    if 305 <= day_of_year <= 365:
        base *= 1.4
    return base


def _weekend_factor(day_of_week: int) -> float:
    """Slight dip on weekends for B2B, slight boost for B2C."""
    if day_of_week >= 5:
        return 0.85
    return 1.0


def generate_google_ads(dates: pd.DatetimeIndex, output_dir: str):
    """Generate Google Ads data matching real column format."""
    campaigns = [
        ("Search_TM_Campaign_01", "SEARCH", 90.0),
        ("Search_TM_Campaign_05", "SEARCH", 60.0),
        ("Search_Campaign_01", "SEARCH", 50.0),
        ("Pmax_Campaign_03", "PERFORMANCE_MAX", 150.0),
        ("Pmax_NTM_Campaign_10", "PERFORMANCE_MAX", 120.0),
        ("Pmax_Campaign_04", "PERFORMANCE_MAX", 100.0),
        ("Display_Campaign_01", "DISPLAY", 40.0),
        ("Video_Campaign_01", "VIDEO", 80.0),
        ("Shopping_Campaign_01", "SHOPPING", 70.0),
        ("DemandGen_Campaign_01", "DEMAND_GEN", 60.0),
    ]

    rows = []
    idx = 0
    for date in dates:
        doy = date.timetuple().tm_yday
        dow = date.weekday()
        seasonal = _seasonal_multiplier(doy)
        wknd = _weekend_factor(dow)

        for camp_name, camp_type, budget in campaigns:
            # Base metrics vary by campaign type
            if camp_type == "SEARCH":
                base_spend = budget * 0.8
                base_clicks = np.random.poisson(200)
                base_imps = base_clicks * np.random.uniform(3, 6)
                conv_rate = 0.03
                roas = np.random.uniform(2.5, 5.0)
            elif camp_type == "PERFORMANCE_MAX":
                base_spend = budget * 0.9
                base_clicks = np.random.poisson(150)
                base_imps = base_clicks * np.random.uniform(5, 10)
                conv_rate = 0.025
                roas = np.random.uniform(3.0, 6.0)
            elif camp_type == "SHOPPING":
                base_spend = budget * 0.85
                base_clicks = np.random.poisson(180)
                base_imps = base_clicks * np.random.uniform(4, 8)
                conv_rate = 0.035
                roas = np.random.uniform(3.5, 7.0)
            elif camp_type == "DISPLAY":
                base_spend = budget * 0.7
                base_clicks = np.random.poisson(80)
                base_imps = base_clicks * np.random.uniform(20, 50)
                conv_rate = 0.01
                roas = np.random.uniform(1.0, 3.0)
            elif camp_type == "VIDEO":
                base_spend = budget * 0.75
                base_clicks = np.random.poisson(50)
                base_imps = base_clicks * np.random.uniform(10, 30)
                conv_rate = 0.005
                roas = np.random.uniform(1.5, 3.5)
            else:  # DEMAND_GEN
                base_spend = budget * 0.7
                base_clicks = np.random.poisson(100)
                base_imps = base_clicks * np.random.uniform(8, 15)
                conv_rate = 0.02
                roas = np.random.uniform(2.0, 4.0)

            noise = np.random.uniform(0.7, 1.3)
            spend = base_spend * seasonal * wknd * noise
            clicks = max(0, int(base_clicks * seasonal * wknd * np.random.uniform(0.6, 1.4)))
            imps = max(clicks, int(base_imps * seasonal * wknd * np.random.uniform(0.8, 1.2)))
            conversions = max(0, clicks * conv_rate * np.random.uniform(0.5, 1.5))
            revenue = spend * roas * np.random.uniform(0.8, 1.2)
            video_views = int(imps * 0.3) if camp_type == "VIDEO" else 0

            rows.append({
                "campaign_id": hash(camp_name) % 10**10,
                "segments_date": date.strftime("%Y-%m-%d"),
                "metrics_clicks": clicks,
                "metrics_conversions": round(conversions, 6),
                "metrics_cost_micros": int(spend * 1_000_000),
                "metrics_impressions": imps,
                "metrics_video_views": video_views,
                "metrics_conversions_value": round(revenue, 6),
                "campaign_advertising_channel_type": camp_type,
                "campaign_budget_amount": budget,
                "campaign_name": camp_name,
            })
            idx += 1

    df = pd.DataFrame(rows)
    df.index.name = None
    path = os.path.join(output_dir, "google_ads_campaign_stats.csv")
    df.to_csv(path, index=True)
    print(f"  Google Ads: {len(df)} rows → {path}")


def generate_meta_ads(dates: pd.DatetimeIndex, output_dir: str):
    """Generate Meta Ads data matching real column format (no revenue col, no campaign_type)."""
    campaigns = [
        ("Generic_Campaign_02", 85.0),
        ("Generic_Campaign_01", 60.0),
        ("Prospecting_DPA_Campaign_04", 120.0),
        ("Prospecting_DPA_Campaign_02", 100.0),
        ("Prospecting_DPA_Campaign_01", 90.0),
        ("Remarketing_DPA_Campaign_03", 50.0),
        ("Remarketing_DPA_Campaign_02", 45.0),
        ("Remarketing_Brand_Campaign_03", 40.0),
        ("Prospecting_Brand_Campaign_02", 70.0),
        ("Prospecting_Adv_Plus_Campaign_02", 150.0),
    ]

    rows = []
    idx = 0
    for date in dates:
        doy = date.timetuple().tm_yday
        dow = date.weekday()
        seasonal = _seasonal_multiplier(doy)
        wknd = _weekend_factor(dow)

        for camp_name, daily_budget in campaigns:
            noise = np.random.uniform(0.6, 1.4)
            if "remarketing" in camp_name.lower():
                base_spend = daily_budget * 0.7
                roas = np.random.uniform(4.0, 8.0)
                base_clicks = np.random.poisson(40)
            elif "prospecting" in camp_name.lower():
                base_spend = daily_budget * 0.85
                roas = np.random.uniform(2.0, 5.0)
                base_clicks = np.random.poisson(60)
            else:  # generic
                base_spend = daily_budget * 0.75
                roas = np.random.uniform(1.5, 4.0)
                base_clicks = np.random.poisson(50)

            spend = max(0, base_spend * seasonal * wknd * noise)
            clicks = max(0, int(base_clicks * seasonal * wknd * np.random.uniform(0.5, 1.5)))
            imps = max(clicks, int(clicks * np.random.uniform(30, 80)))
            cpc = spend / max(clicks, 1)
            cpm = (spend / max(imps, 1)) * 1000
            ctr = (clicks / max(imps, 1)) * 100
            # 'conversion' in Meta data is actually revenue
            conversion_value = spend * roas * np.random.uniform(0.7, 1.3)

            rows.append({
                "campaign_id": abs(hash(camp_name)) % 10**18,
                "date_start": date.strftime("%Y-%m-%d"),
                "cpc": round(cpc, 6),
                "cpm": round(cpm, 6),
                "ctr": round(ctr, 6),
                "reach": 0.0,
                "spend": round(spend, 2),
                "clicks": float(clicks),
                "impressions": float(imps),
                "conversion": round(conversion_value, 2),
                "daily_budget": daily_budget if np.random.random() > 0.3 else np.nan,
                "campaign_name": camp_name,
            })
            idx += 1

    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "meta_ads_campaign_stats.csv")
    df.to_csv(path, index=True)
    print(f"  Meta Ads:   {len(df)} rows → {path}")


def generate_bing_ads(dates: pd.DatetimeIndex, output_dir: str):
    """Generate Bing/Microsoft Ads data matching real column format."""
    campaigns = [
        ("Search_TM_Campaign_02", "Search", 10.0),
        ("Search_Campaign_03", "Search", 15.0),
        ("Shopping_Campaign_02", "Shopping", 20.0),
        ("PMax_Campaign_01", "PerformanceMax", 25.0),
        ("Audience_Campaign_01", "Audience", 12.0),
    ]

    rows = []
    idx = 0
    for date in dates:
        doy = date.timetuple().tm_yday
        dow = date.weekday()
        seasonal = _seasonal_multiplier(doy)
        wknd = _weekend_factor(dow)

        for camp_name, camp_type, daily_budget in campaigns:
            noise = np.random.uniform(0.5, 1.5)
            base_spend = daily_budget * 0.8
            spend = max(0, base_spend * seasonal * wknd * noise)
            clicks = max(0, int(np.random.poisson(20) * seasonal * wknd))
            imps = max(clicks, int(clicks * np.random.uniform(5, 15)))

            if camp_type == "Search":
                roas = np.random.uniform(1.5, 4.0)
                conv_rate = 0.02
            elif camp_type == "Shopping":
                roas = np.random.uniform(2.0, 5.0)
                conv_rate = 0.03
            elif camp_type == "PerformanceMax":
                roas = np.random.uniform(2.5, 5.5)
                conv_rate = 0.025
            else:
                roas = np.random.uniform(1.0, 3.0)
                conv_rate = 0.015

            conversions = max(0, clicks * conv_rate * np.random.uniform(0.3, 1.7))
            revenue = spend * roas * np.random.uniform(0.6, 1.4)

            rows.append({
                "CampaignId": abs(hash(camp_name)) % 10**9,
                "TimePeriod": date.strftime("%Y-%m-%d"),
                "Revenue": round(revenue, 2),
                "Spend": round(spend, 2),
                "Clicks": clicks,
                "Impressions": imps,
                "Conversions": round(conversions, 1),
                "CampaignType": camp_type,
                "DailyBudget": daily_budget,
                "CampaignName": camp_name,
            })
            idx += 1

    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "bing_campaign_stats.csv")
    df.to_csv(path, index=True)
    print(f"  Bing Ads:   {len(df)} rows → {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic advertising data")
    parser.add_argument("--output-dir", default="./data",
                        help="Directory to write CSV files")
    parser.add_argument("--days", type=int, default=540,
                        help="Number of days of data to generate")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Match real data date range: start ~2024-01-01
    dates = pd.date_range("2024-01-01", periods=args.days, freq="D")
    print(f"Generating {args.days} days of data ({dates[0].date()} to {dates[-1].date()}) ...")

    generate_google_ads(dates, args.output_dir)
    generate_meta_ads(dates, args.output_dir)
    generate_bing_ads(dates, args.output_dir)

    print("Sample data generation complete!")


if __name__ == "__main__":
    main()
