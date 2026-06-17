#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Probabilistic Revenue Forecasting — Pipeline Entrypoint
#
# Usage:
#   ./run.sh [DATA_DIR] [MODEL_PATH] [OUTPUT_PATH]
#
# Defaults:
#   DATA_DIR    = ./data
#   MODEL_PATH  = ./pickle/model.pkl
#   OUTPUT_PATH = ./output/predictions.csv
# ---------------------------------------------------------------------------

DATA_DIR="${1:-./data}"
MODEL_PATH="${2:-./pickle/model.pkl}"
OUTPUT_PATH="${3:-./output/predictions.csv}"

echo "=============================================="
echo "  Probabilistic Revenue Forecasting Pipeline"
echo "=============================================="
echo "  DATA_DIR:    $DATA_DIR"
echo "  MODEL_PATH:  $MODEL_PATH"
echo "  OUTPUT_PATH: $OUTPUT_PATH"
echo "=============================================="

# Ensure output directories exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Step 1: Generate features from raw data
echo "[1/2] Generating features from $DATA_DIR ..."
python -m src.generate_features \
    --data-dir "$DATA_DIR" \
    --output "$(dirname "$OUTPUT_PATH")/features.csv"

# Step 2: Load model and generate predictions
echo "[2/2] Generating predictions ..."
python -m src.predict \
    --data-dir "$DATA_DIR" \
    --features "$(dirname "$OUTPUT_PATH")/features.csv" \
    --model "$MODEL_PATH" \
    --output "$OUTPUT_PATH"

echo "=============================================="
echo "  Pipeline complete!"
echo "  Output: $OUTPUT_PATH"
echo "=============================================="
