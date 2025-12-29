# CUDA 12.1 toolkits must already be on PATH
python3.10 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip wheel setuptools

# Torch with CUDA 12.1
pip install --extra-index-url https://download.pytorch.org/whl/cu121 \
  torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121

# The rest
pip install transformers==4.44.2 tokenizers==0.19.1 datasets==2.21.0 \
  flash-attn==2.6.3 --no-build-isolation \
  bitsandbytes==0.43.3 peft==0.11.1 deepspeed==0.14.5 \
  faiss-gpu==1.8.0.post1 pyarrow==17.0.0 pandas==2.2.2 \
  gymnasium==0.29.1 stable-baselines3==2.3.2 \
  wandb==0.17.9 scikit-learn==1.5.2
