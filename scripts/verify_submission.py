"""
Verification script — simulates the hackathon evaluation pipeline.

Usage:
    python scripts/verify_submission.py [--data-dir ./data]

Tests:
    1. requirements.txt exists
    2. run.sh exists
    3. pickle/model.pkl exists
    4. data/ contains CSVs
    5. run.sh executes without error
    6. output/predictions.csv is produced
    7. predictions.csv has exactly 3 rows
    8. predictions.csv has all required columns
    9. All numeric values are non-negative
   10. No NaN values in critical columns
"""

import argparse
import os
import subprocess
import sys

import pandas as pd


REQUIRED_COLUMNS = [
    "Forecast_Horizon",
    "Revenue_P10", "Revenue_P50", "Revenue_P90",
    "ROAS_P10", "ROAS_P50", "ROAS_P90",
    "Google_Revenue", "Meta_Revenue", "Bing_Revenue",
    "Google_ROAS", "Meta_ROAS", "Bing_ROAS",
    "Confidence_Score", "Forecast_Explanation",
]

NUMERIC_COLUMNS = [
    "Revenue_P10", "Revenue_P50", "Revenue_P90",
    "ROAS_P10", "ROAS_P50", "ROAS_P90",
    "Google_Revenue", "Meta_Revenue", "Bing_Revenue",
    "Google_ROAS", "Meta_ROAS", "Bing_ROAS",
    "Confidence_Score",
]


def check(name, condition, detail=""):
    status = "[PASS]" if condition else "[FAIL]"
    msg = f"  {status}: {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


def main():
    parser = argparse.ArgumentParser(description="Verify hackathon submission")
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--model-path", default="./pickle/model.pkl")
    parser.add_argument("--output-path", default="./output/predictions.csv")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    print("=" * 60)
    print("  HACKATHON SUBMISSION VERIFICATION")
    print("=" * 60)
    print()

    passed = 0
    total = 10

    # 1. requirements.txt
    ok = check("requirements.txt exists", os.path.exists("requirements.txt"))
    passed += ok

    # 2. run.sh
    ok = check("run.sh exists", os.path.exists("run.sh"))
    passed += ok

    # 3. model.pkl
    ok = check("pickle/model.pkl exists",
               os.path.exists(args.model_path),
               f"path={args.model_path}")
    passed += ok

    # 4. data/ has CSVs
    csvs = [f for f in os.listdir(args.data_dir) if f.endswith(".csv")] if os.path.isdir(args.data_dir) else []
    ok = check("data/ contains CSV files", len(csvs) > 0, f"found {len(csvs)} files")
    passed += ok

    # 5. Run pipeline
    print()
    print("  Running pipeline ...")
    try:
        result = subprocess.run(
            ["python", "-m", "src.predict",
             "--data-dir", args.data_dir,
             "--model", args.model_path,
             "--output", args.output_path],
            capture_output=True, text=True, timeout=300,
            cwd=root,
        )
        pipeline_ok = result.returncode == 0
        if not pipeline_ok:
            print(f"  STDERR: {result.stderr[:500]}")
    except Exception as e:
        pipeline_ok = False
        print(f"  ERROR: {e}")

    ok = check("Pipeline executes without error", pipeline_ok)
    passed += ok

    # 6. predictions.csv produced
    output_exists = os.path.exists(args.output_path)
    ok = check("predictions.csv produced", output_exists)
    passed += ok

    if not output_exists:
        print(f"\n  FATAL: No output file. {passed}/{total} checks passed.")
        sys.exit(1)

    # Load output
    df = pd.read_csv(args.output_path)

    # 7. Exactly 3 rows
    ok = check("predictions.csv has 3 rows", len(df) == 3, f"actual={len(df)}")
    passed += ok

    # 8. Required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    ok = check("All required columns present",
               len(missing_cols) == 0,
               f"missing={missing_cols}" if missing_cols else "")
    passed += ok

    # 9. Non-negative numerics
    all_positive = True
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            if (df[col] < 0).any():
                all_positive = False
                break
    ok = check("All numeric values >= 0", all_positive)
    passed += ok

    # 10. No NaN in critical columns
    has_nan = False
    for col in NUMERIC_COLUMNS:
        if col in df.columns and df[col].isna().any():
            has_nan = True
            break
    ok = check("No NaN in numeric columns", not has_nan)
    passed += ok

    # Summary
    print()
    print("=" * 60)
    print(f"  RESULT: {passed}/{total} checks passed")
    if passed == total:
        print("  [OK] SUBMISSION READY")
    else:
        print("  [!!] FIX FAILURES BEFORE SUBMITTING")
    print("=" * 60)

    # Print predictions summary
    if output_exists:
        print()
        print("  Predictions Summary:")
        for _, row in df.iterrows():
            h = int(row.get("Forecast_Horizon", 0))
            rev = row.get("Revenue_P50", 0)
            roas = row.get("ROAS_P50", 0)
            print(f"    {h}d: Revenue=${rev:,.0f}, ROAS={roas:.2f}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
