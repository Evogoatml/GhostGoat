#!/usr/bin/env python
import argparse, os
import torch
import torch.nn.utils.prune as prune
from transformers import AutoModelForMaskedLM


def global_magnitude_prune(model, target_density: float):
    """Prune to target density by L1 magnitude across Linear layers."""
    assert 0 < target_density <= 1.0
    modules = []
    for name, m in model.named_modules():
        if isinstance(m, torch.nn.Linear):
            modules.append((m, 'weight'))
    # Calculate total weights
    total = sum(getattr(m, name).numel() for m, name in modules)
    keep = int(total * target_density)
    prune.global_unstructured(
        modules,
        pruning_method=prune.L1Unstructured,
        amount=max(0, total - keep)
    )
    # Remove reparametrization
    for m, _ in modules:
        prune.remove(m, 'weight')
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--target_density', type=float, required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    model = AutoModelForMaskedLM.from_pretrained(args.inp)
    pruned = global_magnitude_prune(model, args.target_density)
    os.makedirs(args.out, exist_ok=True)
    pruned.save_pretrained(args.out)
    print(f"Pruned and saved → {args.out}")

if __name__ == '__main__':
    main()