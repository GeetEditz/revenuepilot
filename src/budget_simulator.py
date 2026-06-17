"""
Budget simulation engine.

Given a trained model and current feature state, simulates the effect of
changing spend levels across channels, producing:
  - Budget vs Revenue response curves
  - Marginal revenue estimates (dRevenue / dSpend)
  - Diminishing return detection
  - Optimal budget allocation recommendations
"""

import logging
import numpy as np
import pandas as pd

from src.utils import (
    ALL_CHANNELS, FORECAST_HORIZONS,
    COL_CHANNEL, COL_CAMPAIGN_TYPE, COL_SPEND,
    safe_divide,
)

logger = logging.getLogger("forecast.budget_sim")


def simulate_budget(
    forecaster,
    latest_features: pd.DataFrame,
    channel_budgets: dict,
    horizon: int = 30,
    n_steps: int = 20,
) -> dict:
    """
    Simulate the effect of varying channel budgets on predicted revenue.

    Parameters
    ----------
    forecaster : QuantileForecaster
        Trained model.
    latest_features : pd.DataFrame
        Latest feature rows (one per Channel × CampaignType).
    channel_budgets : dict
        Target daily budgets per channel, e.g. {"Google": 500, "Meta": 300, "Bing": 100}.
    horizon : int
        Forecast horizon in days (30, 60, or 90).
    n_steps : int
        Number of points on the response curve.

    Returns
    -------
    dict with keys:
        - channel_curves: {channel: [(spend, revenue_p50), ...]}
        - marginal_revenue: {channel: [(spend, marginal), ...]}
        - diminishing_return_points: {channel: spend_at_diminishing | None}
        - recommended_allocation: {channel: fraction}
        - total_revenue_at_current: float
        - total_revenue_at_optimal: float
    """
    if len(latest_features) == 0 or forecaster is None:
        return _empty_result()

    model_features = forecaster.feature_columns
    results = {
        "channel_curves": {},
        "marginal_revenue": {},
        "diminishing_return_points": {},
        "recommended_allocation": {},
        "total_revenue_at_current": 0.0,
        "total_revenue_at_optimal": 0.0,
    }

    # For each channel, build a response curve
    for channel in ALL_CHANNELS:
        ch_rows = latest_features[latest_features[COL_CHANNEL] == channel]
        if len(ch_rows) == 0:
            results["channel_curves"][channel] = []
            results["marginal_revenue"][channel] = []
            results["diminishing_return_points"][channel] = None
            results["recommended_allocation"][channel] = 0.0
            continue

        current_budget = channel_budgets.get(channel, 0)
        if current_budget <= 0:
            current_spend = ch_rows[COL_SPEND].mean() if COL_SPEND in ch_rows.columns else 1.0
            current_budget = current_spend

        budget_range = np.linspace(
            max(current_budget * 0.1, 1.0),
            current_budget * 2.5,
            n_steps,
        )

        curve = []
        for budget_val in budget_range:
            scale = budget_val / max(current_budget, 1e-9)
            total_rev = 0.0

            for _, row_data in ch_rows.iterrows():
                row = row_data.to_frame().T.copy()
                row["Horizon"] = horizon

                # Scale spend-related features
                for col in row.columns:
                    col_lower = str(col).lower()
                    if "spend" in col_lower or col == COL_SPEND:
                        if col in row.columns:
                            row[col] = row[col].values * scale
                    if col_lower in ("cpc", "cpa"):
                        row[col] = row[col].values * scale
                    if col_lower == "budget_utilization":
                        row[col] = min(row[col].values[0] * scale, 2.0)

                # Align features
                X = pd.DataFrame(columns=model_features)
                for col in model_features:
                    if col in row.columns:
                        X[col] = row[col].values
                    else:
                        X[col] = [0.0]
                X = X.astype(float)

                try:
                    preds = forecaster.predict(X)
                    total_rev += float(preds["p50"][0])
                except Exception:
                    pass

            curve.append((float(budget_val * horizon), float(total_rev)))

        results["channel_curves"][channel] = curve

        # Compute marginal revenue
        if len(curve) >= 2:
            spends = np.array([c[0] for c in curve])
            revenues = np.array([c[1] for c in curve])
            marginal = np.gradient(revenues, spends)
            results["marginal_revenue"][channel] = list(zip(spends.tolist(), marginal.tolist()))

            # Find diminishing return point (marginal < 1.0)
            dim_idx = np.where(marginal < 1.0)[0]
            if len(dim_idx) > 0:
                results["diminishing_return_points"][channel] = float(spends[dim_idx[0]])
            else:
                results["diminishing_return_points"][channel] = None
        else:
            results["marginal_revenue"][channel] = []
            results["diminishing_return_points"][channel] = None

    # Compute optimal allocation (greedy by marginal return)
    total_budget = sum(channel_budgets.get(ch, 0) for ch in ALL_CHANNELS) * horizon
    if total_budget > 0:
        # Use last marginal values as proxy for channel efficiency
        efficiencies = {}
        for ch in ALL_CHANNELS:
            marg = results["marginal_revenue"].get(ch, [])
            if marg:
                mid_idx = len(marg) // 2
                efficiencies[ch] = max(marg[mid_idx][1], 0.0)
            else:
                efficiencies[ch] = 0.0

        total_eff = sum(efficiencies.values())
        if total_eff > 0:
            for ch in ALL_CHANNELS:
                results["recommended_allocation"][ch] = round(efficiencies[ch] / total_eff, 4)
        else:
            n_ch = max(len([ch for ch in ALL_CHANNELS if ch in channel_budgets]), 1)
            for ch in ALL_CHANNELS:
                results["recommended_allocation"][ch] = round(1.0 / n_ch, 4) if ch in channel_budgets else 0.0

    # Total revenue at current budget
    for ch in ALL_CHANNELS:
        curve = results["channel_curves"].get(ch, [])
        if curve:
            current_spend = channel_budgets.get(ch, 0) * horizon
            closest = min(curve, key=lambda c: abs(c[0] - current_spend))
            results["total_revenue_at_current"] += closest[1]

    return results


def _empty_result() -> dict:
    return {
        "channel_curves": {ch: [] for ch in ALL_CHANNELS},
        "marginal_revenue": {ch: [] for ch in ALL_CHANNELS},
        "diminishing_return_points": {ch: None for ch in ALL_CHANNELS},
        "recommended_allocation": {ch: round(1 / 3, 4) for ch in ALL_CHANNELS},
        "total_revenue_at_current": 0.0,
        "total_revenue_at_optimal": 0.0,
    }
