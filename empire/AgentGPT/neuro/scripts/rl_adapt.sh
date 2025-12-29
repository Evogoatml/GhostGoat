#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
OUT_DIR="$ROOT_DIR/ckpts/rl"
TIMESTEPS=${TIMESTEPS:-200000}
ENV_ID=${ENV_ID:-CartPole-v1}

mkdir -p "$OUT_DIR"

python - "$OUT_DIR" "$TIMESTEPS" "$ENV_ID" <<'PY'
import sys
from stable_baselines3 import PPO
import gymnasium as gym

out_dir, total_steps, env_id = sys.argv[1], int(sys.argv[2]), sys.argv[3]

env = gym.make(env_id)
model = PPO("MlpPolicy", env, n_steps=2048, batch_size=64, learning_rate=3e-4, verbose=1, tensorboard_log=out_dir)
model.learn(total_timesteps=total_steps)
model.save(f"{out_dir}/policy")
print("RL adapter saved")
PY

echo "RL adapter complete → $OUT_DIR/policy.zip"