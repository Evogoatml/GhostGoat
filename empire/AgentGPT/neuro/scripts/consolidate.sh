#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CKPT_IN="$ROOT_DIR/ckpts/ssl_pred_moe_lora"
FISHER_OUT="$ROOT_DIR/ckpts/fisher.npz"
TRAIN_FILE=${TRAIN_FILE:-"$ROOT_DIR/data/processed/new_task.txt"}
CKPT_EWC_OUT="$ROOT_DIR/ckpts/consolidated"
CKPT_PRUNED_OUT="$ROOT_DIR/ckpts/pruned"
TARGET_DENSITY=${TARGET_DENSITY:-0.2}

# Fisher + EWC fine-tune
python "$ROOT_DIR/train_with_ewc.py" \
  --model_path "$CKPT_IN" \
  --train_file "$TRAIN_FILE" \
  --fisher_samples 4096 \
  --fisher_out "$FISHER_OUT" \
  --ewc_lambda 5.0 \
  --epochs 1 \
  --output_dir "$CKPT_EWC_OUT"

# Prune
python "$ROOT_DIR/prune_backbone.py" \
  --in "$CKPT_EWC_OUT" \
  --target_density "$TARGET_DENSITY" \
  --out "$CKPT_PRUNED_OUT"

echo "Consolidation complete → $CKPT_PRUNED_OUT"