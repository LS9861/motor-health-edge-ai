#!/usr/bin/env python3
"""Evaluate a saved v3 checkpoint on the current data/processed/ test set.

Usage:
    python scripts/eval_checkpoint.py models/checkpoints/v3_5ch_flat_TT.pt
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "training"))
from model import MotorCNN1D  # noqa: E402

LABELS = ["healthy", "imbalanced", "friction"]


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/eval_checkpoint.py <checkpoint.pt>")
        sys.exit(1)

    ckpt_path = Path(sys.argv[1])
    if not ckpt_path.exists():
        print(f"Checkpoint not found: {ckpt_path}")
        sys.exit(1)

    X_test = np.load(REPO_ROOT / "data/processed/X_test.npy")
    y_test = np.load(REPO_ROOT / "data/processed/y_test.npy")

    model = MotorCNN1D(in_channels=5, n_classes=3)
    model.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
    model.eval()

    # X_test is (N, 50, 5) — seq_len, channels. Conv1d wants (N, channels, seq_len).
    X_test_t = np.transpose(X_test, (0, 2, 1))  # (N, 5, 50)
    with torch.no_grad():
        logits = model(torch.tensor(X_test_t, dtype=torch.float32))
        preds = logits.argmax(dim=1).numpy()

    acc = (preds == y_test).mean()
    print(f"\n=== {ckpt_path.name} on JGA25 test set ===")
    print(f"Accuracy: {acc:.4f} ({int(acc * len(y_test))}/{len(y_test)})")

    print("\nPer-class accuracy:")
    for c, name in enumerate(LABELS):
        mask = y_test == c
        if mask.sum() > 0:
            per_class = (preds[mask] == c).mean()
            print(f"  {name:<12} {per_class:.4f} "
                  f"({int((preds[mask] == c).sum())}/{int(mask.sum())})")

    print("\nConfusion matrix (rows=true, cols=pred):")
    print(f"{'':>12} " + " ".join(f"{n:>10}" for n in LABELS))
    for i, name in enumerate(LABELS):
        row = [int(((y_test == i) & (preds == j)).sum()) for j in range(3)]
        print(f"{name:>12} " + " ".join(f"{v:>10}" for v in row))


if __name__ == "__main__":
    main()