#!/usr/bin/env python3
"""Regenerate src/inference/include/norm_params.h from data/processed/train_*.npy.

The 5 channels are [ax, ay, az, current_mA, rpm] — voltage is intentionally
excluded (see docs/phase6_deployment.md: voltage caused shortcut learning).
"""
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
MEAN_FILE = REPO_ROOT / "data" / "processed" / "train_mean.npy"
STD_FILE = REPO_ROOT / "data" / "processed" / "train_std.npy"
HEADER = REPO_ROOT / "src" / "inference" / "include" / "norm_params.h"

CHANNELS = ["ax", "ay", "az", "current_mA", "rpm"]

mean = np.load(MEAN_FILE).astype(np.float32)
std = np.load(STD_FILE).astype(np.float32)

if mean.shape != (5,):
    raise SystemExit(f"Expected 5-channel mean, got shape {mean.shape}")
if std.shape != (5,):
    raise SystemExit(f"Expected 5-channel std, got shape {std.shape}")

lines = [
    "// src/inference/include/norm_params.h",
    "//",
    "// Auto-generated. DO NOT EDIT. Regenerate with:",
    "//   python scripts/generate_norm_params.py",
    "//",
    "// Source: data/processed/train_mean.npy, train_std.npy",
    "// Channels: [ax, ay, az, current_mA, rpm]  (voltage intentionally excluded)",
    "",
    "#ifndef NORM_PARAMS_H",
    "#define NORM_PARAMS_H",
    "",
    "static const float NORM_MEAN[5] = {",
]
for i, ch in enumerate(CHANNELS):
    lines.append(f"    {mean[i]:.6f}f,  // {ch}")
lines += [
    "};",
    "",
    "static const float NORM_STD[5] = {",
]
for i, ch in enumerate(CHANNELS):
    lines.append(f"    {std[i]:.6f}f,  // {ch}")
lines += [
    "};",
    "",
    "#endif  // NORM_PARAMS_H",
]

HEADER.write_text("\n".join(lines) + "\n")
print(f"✅ Wrote {HEADER}")
print(f"   Channels: {CHANNELS}")
print(f"   Mean: {mean.round(4).tolist()}")
print(f"   Std:  {std.round(4).tolist()}")