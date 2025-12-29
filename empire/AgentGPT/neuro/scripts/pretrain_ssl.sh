#!/usr/bin/env bash
set -euo pipefail

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
DATA_DIR="$ROOT_DIR/data/processed"
OUT_DIR="$ROOT_DIR/ckpts/ssl_pred_moe_lora"
CONF_DS="$ROOT_DIR/configs/deepspeed.json"
MODEL_NAME="roberta-base"
SEQ_LEN=${SEQ_LEN:-1024}
EPOCHS=${EPOCHS:-5}
LR=${LR:-2e-4}
BATCH=${BATCH:-8}
ACC=${ACC:-2}

# Ensure data files exist
TRAIN_FILE=${TRAIN_FILE:-"$DATA_DIR/train.txt"}
VAL_FILE=${VAL_FILE:-"$DATA_DIR/val.txt"}
if [[ ! -f "$TRAIN_FILE" ]]; then echo "Missing $TRAIN_FILE"; exit 1; fi
if [[ ! -f "$VAL_FILE" ]]; then echo "Missing $VAL_FILE"; exit 1; fi

# Get Transformers examples locally (for run_mlm.py)
VENDOR_DIR="$ROOT_DIR/vendor"
mkdir -p "$VENDOR_DIR"
if [[ ! -d "$VENDOR_DIR/transformers" ]]; then
  git clone --depth 1 https://github.com/huggingface/transformers.git "$VENDOR_DIR/transformers"
fi
cd "$VENDOR_DIR/transformers/examples/pytorch/language-modeling"

# Train masked language modeling with DeepSpeed + bf16
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1

deepspeed \
  --num_gpus=auto \
  run_mlm.py \
  --model_name_or_path "$MODEL_NAME" \
  --train_file "$TRAIN_FILE" \
  --validation_file "$VAL_FILE" \
  --do_train --do_eval \
  --deepspeed "$CONF_DS" \
  --bf16 \
  --per_device_train_batch_size $BATCH \
  --gradient_accumulation_steps $ACC \
  --learning_rate $LR \
  --num_train_epochs $EPOCHS \
  --weight_decay 0.05 \
  --logging_steps 50 \
  --evaluation_strategy steps \
  --eval_steps 1000 \
  --save_steps 1000 \
  --max_seq_length $SEQ_LEN \
  --report_to wandb \
  --output_dir "$OUT_DIR"

echo "Pretraining complete → $OUT_DIR"