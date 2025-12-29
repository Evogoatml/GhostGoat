#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
STORE_DIR="$ROOT_DIR/memory_store"
CKPT_DIR="$ROOT_DIR/ckpts/ssl_pred_moe_lora"
DATA_DIR="$ROOT_DIR/data/processed"
DIM=${DIM:-768}
NLIST=${NLIST:-4096}
MAX_TOKS=${MAX_TOKS:-512}

mkdir -p "$STORE_DIR"

python - "$CKPT_DIR" "$DATA_DIR" "$STORE_DIR" "$DIM" "$NLIST" "$MAX_TOKS" <<'PY'
import os, sys, glob, numpy as np, pandas as pd
import pyarrow as pa, pyarrow.parquet as pq
import torch, faiss
from transformers import AutoModel, AutoTokenizer

ckpt, data_dir, store_dir, dim, nlist, max_toks = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])

model = AutoModel.from_pretrained(ckpt).eval().cuda() if torch.cuda.is_available() else AutoModel.from_pretrained(ckpt).eval()
tok = AutoTokenizer.from_pretrained(ckpt)

# IVF index
quantizer = faiss.IndexFlatIP(dim)
index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)

vecs = []
metas = []
files = sorted(glob.glob(os.path.join(data_dir, '*.txt')))
if not files:
    raise SystemExit(f"No .txt files in {data_dir}")

with torch.no_grad():
    for fn in files:
        text = open(fn, 'r', encoding='utf-8', errors='ignore').read()
        if not text.strip():
            continue
        ids = tok(text, return_tensors='pt', truncation=True, max_length=max_toks)
        if torch.cuda.is_available():
            ids = {k: v.cuda() for k, v in ids.items()}
        h = model(**ids).last_hidden_state[:, 0, :].detach().cpu().numpy()
        faiss.normalize_L2(h)
        vecs.append(h)
        metas.append(pd.DataFrame({
            'file': [os.path.basename(fn)] * h.shape[0],
            'len': [len(text)] * h.shape[0]
        }))

X = np.concatenate(vecs, axis=0)
index.train(X)
index.add(X)
faiss.write_index(index, os.path.join(store_dir, 'episodic.faiss'))

meta = pd.concat(metas, ignore_index=True)
pq.write_table(pa.Table.from_pandas(meta), os.path.join(store_dir, 'meta.parquet'))
print(f"Built FAISS index with {X.shape[0]} vectors → {store_dir}")
PY

echo "Memory built → $STORE_DIR/episodic.faiss"