# Architecture

## System Overview

```
Raw CSVs → Preprocessing → Validation → Feature Engineering → Model Inference → Output Formatting → predictions.csv
```

## Data Flow

1. **Ingestion**: `glob("*.csv")` discovers files dynamically from data directory
2. **Normalisation**: 100+ column aliases map to unified schema (Date, Channel, CampaignName, CampaignType, Spend, Revenue, Clicks, Impressions, Conversions, Budget)
3. **Platform-specific handling**:
   - Google: `metrics_cost_micros ÷ 1,000,000`, `metrics_conversions_value` → Revenue
   - Meta: `conversion` → Revenue, campaign type inferred from name
   - Bing: Direct mapping (TimePeriod → Date, DailyBudget → Budget)
4. **Validation**: Non-fatal checks with in-place cleaning
5. **Aggregation**: Raw campaign rows → `(Date, Channel, CampaignType)` grain
6. **Feature Engineering**: 44+ features computed per group
7. **Prediction**: Latest features × 3 horizons → P10/P50/P90 revenue
8. **Aggregation**: Channel-level → total-level predictions
9. **Output**: Formatted to predictions.csv schema

## Model Architecture

- 3 LightGBM models (P10, P50, P90 quantile regression)
- Single model per quantile with `Horizon` as feature
- Trained on forward revenue sums: `target = SUM(Revenue from t+1 to t+h)`
- XGBoost fallback if LightGBM unavailable
- GPU acceleration for training; CPU-only inference

## Safety Design

- Emergency statistical fallback if model fails
- Dict-based encoding with unknown=0 (no LabelEncoder crash)
- All rolling features use `min_periods=1`
- All NaN filled with 0 after feature computation
- Output always produces exactly 3 rows
