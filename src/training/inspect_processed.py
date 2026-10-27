#!/usr/bin/env python3
"""Sanity check the preprocessed .npy arrays."""
import numpy as np
from pathlib import Path

PROC = Path("data/processed")
LABELS = ["healthy", "imbalanced", "friction"]

X_train = np.load(PROC / "X_train.npy")
y_train = np.load(PROC / "y_train.npy")
X_test  = np.load(PROC / "X_test.npy")
y_test  = np.load(PROC / "y_test.npy")

print(f"X_train shape: {X_train.shape}, dtype: {X_train.dtype}")
print(f"y_train shape: {y_train.shape}, dtype: {y_train.dtype}")
print(f"X_test shape:  {X_test.shape}, dtype: {X_test.dtype}")
print(f"y_test shape:  {y_test.shape}, dtype: {y_test.dtype}")

print("\nTrain class distribution:")
for i, name in enumerate(LABELS):
    print(f"  {name:12s}: {int((y_train == i).sum()):4d} windows")

print("\nTest class distribution:")
for i, name in enumerate(LABELS):
    print(f"  {name:12s}: {int((y_test == i).sum()):4d} windows")

print("\nPer-channel mean/std across train (should be ≈0 / ≈1 after Z-score):")
channels = ["ax", "ay", "az", "current_mA", "voltage_v", "rpm"]
for i, ch in enumerate(channels):
    m = X_train[:, :, i].mean()
    s = X_train[:, :, i].std()
    print(f"  {ch:12s}: mean={m:+.4f}  std={s:.4f}")

# Check for NaNs
print(f"\nNaNs in X_train: {np.isnan(X_train).sum()}")
print(f"NaNs in X_test:  {np.isnan(X_test).sum()}")