"""
Final Backend Audit — comprehensive verification of all submission requirements.

Covers:
  1. Submission guide compliance
  2. Dataset schema compliance
  3. Hidden-test robustness (10 adversarial scenarios)
  4. Model audit
  5. Predictions output audit
  6. Judge pipeline simulation
"""

import os
import sys
import json
import shutil
import tempfile
import traceback
import numpy as np
import pandas as pd

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from src.utils import setup_logging, OUTPUT_COLUMNS, MODEL_FEATURE_COLUMNS, FORECAST_HORIZONS
setup_logging()

RESULTS = []


def check(phase, name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"phase": phase, "name": name, "status": status, "detail": detail})
    tag = "[PASS]" if condition else "[FAIL]"
    msg = f"  {tag} {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


# =====================================================================
# PHASE 1: SUBMISSION GUIDE COMPLIANCE
# =====================================================================
def phase1_submission_compliance():
    print("\n" + "=" * 70)
    print("  PHASE 1: SUBMISSION GUIDE COMPLIANCE")
    print("=" * 70)

    # run.sh
    check(1, "run.sh exists", os.path.exists("run.sh"))
    with open("run.sh", "r") as f:
        content = f.read()
    check(1, "run.sh has bash shebang", content.startswith("#!/bin/bash"))
    check(1, "run.sh accepts DATA_DIR arg", "${1:-" in content)
    check(1, "run.sh accepts MODEL_PATH arg", "${2:-" in content)
    check(1, "run.sh accepts OUTPUT_PATH arg", "${3:-" in content)
    check(1, "run.sh calls generate_features", "generate_features" in content)
    check(1, "run.sh calls src.predict", "src.predict" in content)
    check(1, "run.sh does NOT train", "src.train" not in content)

    # requirements.txt
    check(1, "requirements.txt exists", os.path.exists("requirements.txt"))
    with open("requirements.txt") as f:
        deps = f.read().lower()
    for pkg in ["pandas", "numpy", "lightgbm", "joblib"]:
        check(1, f"  dependency: {pkg}", pkg in deps)

    # model.pkl
    exists = os.path.exists("pickle/model.pkl")
    check(1, "pickle/model.pkl exists", exists)
    if exists:
        size = os.path.getsize("pickle/model.pkl")
        check(1, "model.pkl size > 100KB", size > 100_000, f"{size:,} bytes")

    # Source files
    src_files = [
        "src/utils.py", "src/preprocessing.py", "src/validation.py",
        "src/generate_features.py", "src/forecasting.py", "src/train.py",
        "src/predict.py", "src/budget_simulator.py", "src/ai_insights.py",
        "src/__init__.py",
    ]
    for f in src_files:
        check(1, f"  {f} exists", os.path.exists(f))

    # No TODO/PLACEHOLDER
    import glob
    todo_files = []
    for py in glob.glob("src/*.py"):
        with open(py) as f:
            content = f.read()
        if "TODO" in content or "PLACEHOLDER" in content or "NotImplementedError" in content:
            todo_files.append(os.path.basename(py))
    check(1, "No TODO/PLACEHOLDER in src/", len(todo_files) == 0,
          f"found in: {todo_files}" if todo_files else "")


# =====================================================================
# PHASE 2: DATASET SCHEMA COMPLIANCE
# =====================================================================
def phase2_schema_compliance():
    print("\n" + "=" * 70)
    print("  PHASE 2: DATASET SCHEMA COMPLIANCE")
    print("=" * 70)

    from src.preprocessing import load_channel_data, unify_schema

    # Google Ads: metrics_cost_micros conversion
    g = pd.read_csv("test-files/google_ads_campaign_stats.csv", nrows=5)
    raw_micros = g["metrics_cost_micros"].iloc[1]
    df_g = load_channel_data("test-files/google_ads_campaign_stats.csv", "Google")
    unified_spend = df_g["Spend"].iloc[1]  # Row order preserved after load
    # Find the matching row
    expected_spend = raw_micros / 1_000_000
    # Check any spend value matches the micros conversion
    check(2, "Google cost_micros -> Spend conversion",
          abs(expected_spend - unified_spend) < 0.01,
          f"micros={raw_micros}, expected=${expected_spend:.2f}, got=${unified_spend:.2f}")

    # Google revenue mapping
    raw_rev = g["metrics_conversions_value"].iloc[1]
    unified_rev = df_g["Revenue"].iloc[1]
    check(2, "Google metrics_conversions_value -> Revenue",
          abs(raw_rev - unified_rev) < 0.01,
          f"raw={raw_rev:.2f}, unified={unified_rev:.2f}")

    # Google campaign type
    types_g = df_g["CampaignType"].unique().tolist()
    check(2, "Google campaign types normalized",
          "Search" in types_g and "Performance Max" in types_g,
          f"types={types_g}")

    # Meta Ads: conversion = Revenue
    m = pd.read_csv("test-files/meta_ads_campaign_stats.csv", nrows=5)
    df_m = load_channel_data("test-files/meta_ads_campaign_stats.csv", "Meta")
    raw_conv = m["conversion"].iloc[1]
    unified_rev_m = df_m["Revenue"].iloc[1]
    check(2, "Meta conversion -> Revenue mapping",
          abs(raw_conv - unified_rev_m) < 0.01,
          f"raw conversion={raw_conv}, unified Revenue={unified_rev_m}")

    # Meta: no campaign_type column -> inferred
    check(2, "Meta has no campaign_type column", "campaign_type" not in [c.lower() for c in m.columns])
    types_m = df_m["CampaignType"].unique().tolist()
    check(2, "Meta campaign types inferred from names",
          len(types_m) > 1 and "Unknown" not in types_m,
          f"inferred types={types_m}")

    # Meta: Conversions default to 0
    check(2, "Meta Conversions defaults to 0",
          (df_m["Conversions"] == 0).all(),
          f"nonzero count={int((df_m['Conversions'] != 0).sum())}")

    # Bing: PerformanceMax normalization
    b = pd.read_csv("test-files/bing_campaign_stats.csv", nrows=5)
    df_b = load_channel_data("test-files/bing_campaign_stats.csv", "Bing")
    types_b = df_b["CampaignType"].unique().tolist()
    check(2, "Bing PerformanceMax -> Performance Max",
          "Performance Max" in types_b and "PerformanceMax" not in types_b,
          f"types={types_b}")

    # Date normalization
    for name, df in [("Google", df_g), ("Meta", df_m), ("Bing", df_b)]:
        check(2, f"{name} dates parsed to datetime",
              pd.api.types.is_datetime64_any_dtype(df["Date"]))

    # Full unification
    unified = unify_schema("test-files")
    check(2, "Unified schema has 10 columns", len(unified.columns) == 10,
          f"columns={unified.columns.tolist()}")
    check(2, "All 3 channels present",
          set(["Google", "Meta", "Bing"]).issubset(set(unified["Channel"].unique())))
    check(2, "Unified row count matches sum",
          len(unified) == len(df_g) + len(df_m) + len(df_b),
          f"unified={len(unified)}, sum={len(df_g)+len(df_m)+len(df_b)}")


# =====================================================================
# PHASE 3: HIDDEN-TEST ROBUSTNESS
# =====================================================================
def phase3_robustness():
    print("\n" + "=" * 70)
    print("  PHASE 3: HIDDEN-TEST ROBUSTNESS (10 adversarial scenarios)")
    print("=" * 70)

    from src.preprocessing import unify_schema
    from src.validation import validate_data
    from src.generate_features import engineer_features
    from src.predict import predict

    tmpdir = os.path.join(ROOT, "output", "_audit_tmp")
    os.makedirs(tmpdir, exist_ok=True)

    def _run_scenario(scenario_name, csv_dfs, expect_predictions=True):
        """Write CSVs to a temp dir and run the full predict pipeline."""
        scenario_dir = os.path.join(tmpdir, scenario_name.replace(" ", "_"))
        os.makedirs(scenario_dir, exist_ok=True)
        for fname, df in csv_dfs.items():
            df.to_csv(os.path.join(scenario_dir, fname), index=False)

        output_path = os.path.join(scenario_dir, "predictions.csv")
        try:
            predict(scenario_dir, "", "pickle/model.pkl", output_path)
            if os.path.exists(output_path):
                result = pd.read_csv(output_path)
                ok = len(result) == 3
                check(3, scenario_name,
                      ok,
                      f"rows={len(result)}, cols={len(result.columns)}")
                # Verify non-negative
                numeric_cols = [c for c in result.columns if c != "Forecast_Explanation" and c != "Forecast_Horizon"]
                for c in numeric_cols:
                    if result[c].dtype in [np.float64, np.int64, float, int]:
                        if (result[c] < 0).any():
                            check(3, f"  {scenario_name}: {c} >= 0", False,
                                  f"min={result[c].min()}")
                return True
            else:
                check(3, scenario_name, False, "No output file produced")
                return False
        except Exception as exc:
            check(3, scenario_name, False, f"Exception: {exc}")
            return False

    # Base data for scenarios
    base_bing = pd.read_csv("test-files/bing_campaign_stats.csv")
    base_google = pd.read_csv("test-files/google_ads_campaign_stats.csv")
    base_meta = pd.read_csv("test-files/meta_ads_campaign_stats.csv")

    # Scenario 1: Missing campaign types
    s1_bing = base_bing.copy()
    s1_bing["CampaignType"] = np.nan
    _run_scenario("1. Missing campaign types", {"bing_campaign_stats.csv": s1_bing})

    # Scenario 2: Missing budgets
    s2_google = base_google.copy()
    s2_google["campaign_budget_amount"] = np.nan
    _run_scenario("2. Missing budgets", {"google_ads_campaign_stats.csv": s2_google})

    # Scenario 3: Missing conversions (all zero)
    s3_bing = base_bing.copy()
    s3_bing["Conversions"] = 0.0
    s3_bing["Revenue"] = 0.0
    _run_scenario("3. Zero revenue/conversions", {"bing_campaign_stats.csv": s3_bing})

    # Scenario 4: Additional campaigns (unseen names)
    s4_bing = base_bing.copy()
    extra = s4_bing.head(20).copy()
    extra["CampaignName"] = "Totally_New_Unknown_Campaign_99"
    extra["CampaignType"] = "SomeNewType"
    s4_bing = pd.concat([s4_bing, extra], ignore_index=True)
    _run_scenario("4. Additional unknown campaigns", {"bing_campaign_stats.csv": s4_bing})

    # Scenario 5: Additional dates (future dates)
    s5_bing = base_bing.copy()
    future = s5_bing.tail(10).copy()
    future["TimePeriod"] = pd.date_range("2027-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    s5_bing = pd.concat([s5_bing, future], ignore_index=True)
    _run_scenario("5. Future dates", {"bing_campaign_stats.csv": s5_bing})

    # Scenario 6: Unknown campaign names only
    s6_bing = base_bing.copy()
    s6_bing["CampaignName"] = "x_unknown_" + s6_bing.index.astype(str)
    _run_scenario("6. All unknown campaign names", {"bing_campaign_stats.csv": s6_bing})

    # Scenario 7: Empty channel (only one file, very small)
    s7_bing = base_bing.head(5).copy()
    _run_scenario("7. Tiny dataset (5 rows)", {"bing_campaign_stats.csv": s7_bing})

    # Scenario 8: Large dataset (duplicated 3x)
    s8_google = pd.concat([base_google] * 3, ignore_index=True)
    _run_scenario("8. Large dataset (3x duplication)", {"google_ads_campaign_stats.csv": s8_google})

    # Scenario 9: Corrupted rows (NaN everywhere in some rows)
    s9_bing = base_bing.copy()
    corrupt_idx = s9_bing.sample(n=min(50, len(s9_bing)), random_state=42).index
    for col in ["Revenue", "Spend", "Clicks", "Impressions"]:
        s9_bing.loc[corrupt_idx, col] = np.nan
    _run_scenario("9. Corrupted rows (50 NaN rows)", {"bing_campaign_stats.csv": s9_bing})

    # Scenario 10: Single channel only (Meta only)
    _run_scenario("10. Single channel (Meta only)", {"meta_ads_campaign_stats.csv": base_meta})

    # Cleanup
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


# =====================================================================
# PHASE 4: MODEL AUDIT
# =====================================================================
def phase4_model_audit():
    print("\n" + "=" * 70)
    print("  PHASE 4: MODEL AUDIT")
    print("=" * 70)

    from src.forecasting import QuantileForecaster

    # Load model
    try:
        forecaster = QuantileForecaster.load("pickle/model.pkl")
        check(4, "Model loads successfully", True)
    except Exception as exc:
        check(4, "Model loads successfully", False, str(exc))
        return

    # Check quantile models exist
    for label in ["p10", "p50", "p90"]:
        check(4, f"  {label} model present", label in forecaster.models and forecaster.models[label] is not None)

    # Feature columns
    feat_cols = forecaster.feature_columns
    check(4, "Feature columns stored", len(feat_cols) > 0, f"count={len(feat_cols)}")
    check(4, "Horizon in features", "Horizon" in feat_cols)

    # No training leakage: target columns should NOT be features
    for bad_col in ["Target_Revenue", "Target_Spend", "_valid"]:
        check(4, f"  No leakage: {bad_col} not in features", bad_col not in feat_cols)

    # No dependency on campaign names (CampaignName should not be a feature)
    check(4, "No CampaignName dependency", "CampaignName" not in feat_cols)
    check(4, "No Date dependency", "Date" not in feat_cols)

    # Encodings stored
    import joblib
    artifact = joblib.load("pickle/model.pkl")
    check(4, "Channel encoding stored", "channel_encoding" in artifact)
    check(4, "CampaignType encoding stored", "campaign_type_encoding" in artifact)

    # CPU inference test: predict with dummy data
    try:
        X_dummy = pd.DataFrame(np.zeros((1, len(feat_cols))), columns=feat_cols)
        X_dummy["Horizon"] = 30
        preds = forecaster.predict(X_dummy)
        check(4, "CPU inference works", True,
              f"p10={preds['p10'][0]:.2f}, p50={preds['p50'][0]:.2f}, p90={preds['p90'][0]:.2f}")

        # Monotonicity check
        check(4, "Quantile monotonicity (P10 <= P50 <= P90)",
              preds["p10"][0] <= preds["p50"][0] <= preds["p90"][0])

        # Non-negativity
        check(4, "All predictions >= 0",
              all(preds[q][0] >= 0 for q in ["p10", "p50", "p90"]))
    except Exception as exc:
        check(4, "CPU inference works", False, str(exc))


# =====================================================================
# PHASE 5: PREDICTIONS OUTPUT AUDIT
# =====================================================================
def phase5_output_audit():
    print("\n" + "=" * 70)
    print("  PHASE 5: PREDICTIONS OUTPUT AUDIT")
    print("=" * 70)

    from src.predict import predict, _emergency_predictions
    from src.utils import format_output

    # Test 1: Normal prediction
    output_path = os.path.join("output", "_audit_normal.csv")
    try:
        predict("test-files", "", "pickle/model.pkl", output_path)
        df = pd.read_csv(output_path)
        check(5, "Normal prediction produces output", os.path.exists(output_path))
        check(5, "  Exactly 3 rows", len(df) == 3, f"actual={len(df)}")
        check(5, "  All 15 columns present",
              all(c in df.columns for c in OUTPUT_COLUMNS),
              f"missing={[c for c in OUTPUT_COLUMNS if c not in df.columns]}")
        check(5, "  Horizons are 30/60/90",
              sorted(df["Forecast_Horizon"].tolist()) == [30, 60, 90])

        # Non-negative check
        num_cols = [c for c in df.columns if c not in ["Forecast_Horizon", "Forecast_Explanation"]]
        all_nonneg = True
        for c in num_cols:
            if df[c].dtype in [np.float64, np.int64, float, int]:
                if (df[c] < 0).any():
                    all_nonneg = False
        check(5, "  All numeric values >= 0", all_nonneg)

        # No NaN
        has_nan = df[num_cols].isnull().any().any()
        check(5, "  No NaN in numeric columns", not has_nan)

        # Explanation not empty
        check(5, "  Forecast_Explanation not empty",
              all(len(str(x).strip()) > 10 for x in df["Forecast_Explanation"]))

        # All channels have revenue
        for ch in ["Google", "Meta", "Bing"]:
            col = f"{ch}_Revenue"
            if col in df.columns:
                check(5, f"  {ch}_Revenue > 0 for at least one horizon",
                      (df[col] > 0).any(),
                      f"values={df[col].tolist()}")

    except Exception as exc:
        check(5, "Normal prediction produces output", False, str(exc))
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

    # Test 2: Emergency fallback (bad model path)
    output_path2 = os.path.join("output", "_audit_emergency.csv")
    try:
        predict("test-files", "", "pickle/nonexistent_model.pkl", output_path2)
        df2 = pd.read_csv(output_path2)
        check(5, "Emergency fallback produces output", os.path.exists(output_path2))
        check(5, "  Fallback has 3 rows", len(df2) == 3)
        check(5, "  Fallback has all columns",
              all(c in df2.columns for c in OUTPUT_COLUMNS))
    except Exception as exc:
        check(5, "Emergency fallback produces output", False, str(exc))
    finally:
        if os.path.exists(output_path2):
            os.remove(output_path2)

    # Test 3: Empty data dir
    empty_dir = os.path.join("output", "_audit_empty")
    os.makedirs(empty_dir, exist_ok=True)
    output_path3 = os.path.join("output", "_audit_empty_pred.csv")
    try:
        predict(empty_dir, "", "pickle/model.pkl", output_path3)
        df3 = pd.read_csv(output_path3)
        check(5, "Empty data dir produces output", os.path.exists(output_path3))
        check(5, "  Empty data fallback has 3 rows", len(df3) == 3)
    except Exception as exc:
        check(5, "Empty data dir produces output", False, str(exc))
    finally:
        if os.path.exists(output_path3):
            os.remove(output_path3)
        shutil.rmtree(empty_dir, ignore_errors=True)


# =====================================================================
# PHASE 6: JUDGE PIPELINE SIMULATION
# =====================================================================
def phase6_judge_simulation():
    print("\n" + "=" * 70)
    print("  PHASE 6: JUDGE PIPELINE SIMULATION")
    print("=" * 70)

    from src.predict import predict

    # Simulate: clone -> install -> replace data -> run.sh -> predictions.csv
    judge_dir = os.path.join("output", "_audit_judge")
    judge_data = os.path.join(judge_dir, "data")
    judge_output = os.path.join(judge_dir, "predictions.csv")

    os.makedirs(judge_data, exist_ok=True)

    # Copy test-files to simulated data dir (simulating "replace data")
    for f in os.listdir("test-files"):
        if f.endswith(".csv"):
            shutil.copy2(os.path.join("test-files", f), os.path.join(judge_data, f))

    check(6, "Judge data directory created", os.path.isdir(judge_data))
    csvs = [f for f in os.listdir(judge_data) if f.endswith(".csv")]
    check(6, "Judge data has CSV files", len(csvs) > 0, f"count={len(csvs)}")

    # Run prediction (simulating run.sh without bash)
    try:
        predict(judge_data, "", "pickle/model.pkl", judge_output)
        check(6, "Judge pipeline executes", True)
    except Exception as exc:
        check(6, "Judge pipeline executes", False, str(exc))

    if os.path.exists(judge_output):
        df = pd.read_csv(judge_output)
        check(6, "Judge predictions.csv produced", True)
        check(6, "Judge output has 3 rows", len(df) == 3)
        check(6, "Judge output has all 15 columns",
              all(c in df.columns for c in OUTPUT_COLUMNS))

        # Validate content
        check(6, "Judge horizons correct",
              sorted(df["Forecast_Horizon"].tolist()) == [30, 60, 90])

        num_cols = [c for c in df.columns if c not in ["Forecast_Horizon", "Forecast_Explanation"]]
        all_ok = not df[num_cols].isnull().any().any()
        check(6, "Judge no NaN values", all_ok)

        all_nonneg = True
        for c in num_cols:
            if df[c].dtype in [np.float64, np.int64]:
                if (df[c] < 0).any():
                    all_nonneg = False
        check(6, "Judge all values >= 0", all_nonneg)

        # Print predictions
        print("\n  Judge Pipeline Output:")
        for _, row in df.iterrows():
            h = int(row["Forecast_Horizon"])
            rev = row["Revenue_P50"]
            roas = row["ROAS_P50"]
            print(f"    {h}d: Revenue=${rev:,.0f}, ROAS={roas:.2f}")
    else:
        check(6, "Judge predictions.csv produced", False)

    # Cleanup
    shutil.rmtree(judge_dir, ignore_errors=True)


# =====================================================================
# FINAL SUMMARY
# =====================================================================
def print_summary():
    print("\n" + "=" * 70)
    print("  FINAL AUDIT SUMMARY")
    print("=" * 70)

    phases = {}
    for r in RESULTS:
        p = r["phase"]
        if p not in phases:
            phases[p] = {"pass": 0, "fail": 0, "failures": []}
        if r["status"] == "PASS":
            phases[p]["pass"] += 1
        else:
            phases[p]["fail"] += 1
            phases[p]["failures"].append(r["name"])

    phase_names = {
        1: "Submission Compliance",
        2: "Schema Compliance",
        3: "Hidden-Test Robustness",
        4: "Model Audit",
        5: "Predictions Output",
        6: "Judge Simulation",
    }

    total_pass = sum(p["pass"] for p in phases.values())
    total_fail = sum(p["fail"] for p in phases.values())
    total = total_pass + total_fail

    for p_id in sorted(phases.keys()):
        p = phases[p_id]
        name = phase_names.get(p_id, f"Phase {p_id}")
        status = "PASS" if p["fail"] == 0 else "FAIL"
        print(f"  [{status}] Phase {p_id}: {name} -- {p['pass']}/{p['pass']+p['fail']}")
        if p["failures"]:
            for f in p["failures"]:
                print(f"         [FAIL] {f}")

    print(f"\n  TOTAL: {total_pass}/{total} checks passed")
    pct = (total_pass / max(total, 1)) * 100

    if total_fail == 0:
        print(f"\n  *** BACKEND PRODUCTION-READY ***")
        print(f"  Confidence: {pct:.0f}%")
        print(f"  Risk: LOW")
        print(f"  Remaining issues: NONE")
    else:
        print(f"\n  *** ISSUES FOUND ***")
        print(f"  Confidence: {pct:.0f}%")
        print(f"  Failures: {total_fail}")
        all_failures = [r for r in RESULTS if r["status"] == "FAIL"]
        for f in all_failures:
            print(f"    - {f['name']}: {f['detail']}")

    print("=" * 70)
    return total_fail == 0


# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    phase1_submission_compliance()
    phase2_schema_compliance()
    phase3_robustness()
    phase4_model_audit()
    phase5_output_audit()
    phase6_judge_simulation()
    all_pass = print_summary()
    sys.exit(0 if all_pass else 1)
