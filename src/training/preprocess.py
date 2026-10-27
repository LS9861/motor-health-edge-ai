#!/usr/bin/env python3
"""
Phase 2 (v2): Preprocessing & Windowing for motor-health-edge-ai.

What changed vs v1:
  - Per-window Z-score replaced by global-per-channel standardization
    computed from the TRAIN set only. This preserves amplitude differences
    (imbalance = larger vibration amplitude; Z-score erased that).
  - mean_rpm per window is saved for Phase 4 (not used in Phase 3).
  - Uses configs/sensors.yaml for feature list and window sizes.

Split: explicit file assignment (2 train / 1 test per class).
"""

import yaml
import numpy as np
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_PATH = REPO_ROOT / "configs" / "sensors.yaml"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

FEATURE_COLS = CFG["features"]["time_series"]     # 5 channels
WINDOW_SIZE = CFG["sampling"]["window_samples"]    # 100
STEP_SIZE = CFG["sampling"]["step_samples"]        # 50
RPM_COL = "rpm"

LABELS = ["healthy", "imbalanced", "friction"]
LABEL_MAP = {label: idx for idx, label in enumerate(LABELS)}

TRAIN_FILES = {
    "healthy":    ["healthy_20261027_141457.csv",
                   "healthy_20261027_142041.csv"],
    "imbalanced": ["imbalanced_20261027_143406.csv",
                   "imbalanced_20261027_143504.csv"],
    "friction":   ["friction_20261027_144310.csv",
                   "friction_20261027_144401.csv"],
}
TEST_FILES = {
    "healthy":    ["healthy_20261027_142334.csv"],
    "imbalanced": ["imbalanced_20261027_143557.csv"],
    "friction":   ["friction_20261027_144451.csv"],
}


def load_and_clean_csv(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required = FEATURE_COLS + [RPM_COL, "label"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in {filepath}")
    df = df[FEATURE_COLS + [RPM_COL, "label"]].copy()
    df[RPM_COL] = df[RPM_COL].ffill().bfill().fillna(0.0)
    return df.dropna()


def create_windows(df: pd.DataFrame):
    """Slice into overlapping windows. Returns raw X (unnormalized)."""
    data = df[FEATURE_COLS].values
    rpm = df[RPM_COL].values
    label_idx = LABEL_MAP[df["label"].iloc[0]]

    X, y, mean_rpm = [], [], []
    for start in range(0, len(data) - WINDOW_SIZE + 1, STEP_SIZE):
        X.append(data[start : start + WINDOW_SIZE])
        y.append(label_idx)
        mean_rpm.append(float(np.mean(rpm[start : start + WINDOW_SIZE])))

    return np.array(X, dtype=np.float32), np.array(y), np.array(mean_rpm, dtype=np.float32)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    buckets = {"train": {"X": [], "y": [], "rpm": []},
               "test":  {"X": [], "y": [], "rpm": []}}

    def process(label, fname, split):
        fpath = RAW_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing: {fpath}")
        df = load_and_clean_csv(fpath)
        X, y, rpm = create_windows(df)
        buckets[split]["X"].append(X)
        buckets[split]["y"].append(y)
        buckets[split]["rpm"].append(rpm)
        print(f"  [{label}] {fname} → {len(X)} windows ({split})")

    print("Processing raw CSVs...")
    for label in LABELS:
        for f in TRAIN_FILES[label]: process(label, f, "train")
        for f in TEST_FILES[label]:  process(label, f, "test")

    X_train = np.concatenate(buckets["train"]["X"], axis=0)
    y_train = np.concatenate(buckets["train"]["y"], axis=0)
    rpm_train = np.concatenate(buckets["train"]["rpm"], axis=0)

    X_test = np.concatenate(buckets["test"]["X"], axis=0)
    y_test = np.concatenate(buckets["test"]["y"], axis=0)
    rpm_test = np.concatenate(buckets["test"]["rpm"], axis=0)

    # --- Global per-channel standardization (TRAIN stats only) ---
    train_mean = X_train.mean(axis=(0, 1))   # shape (C,)
    train_std  = X_train.std(axis=(0, 1))    # shape (C,)
    train_std[train_std == 0] = 1.0

    X_train = (X_train - train_mean) / train_std
    X_test  = (X_test  - train_mean) / train_std   # same stats, no leakage

    print("\nGlobal normalization stats (per channel, from train):")
    for i, ch in enumerate(FEATURE_COLS):
        print(f"  {ch:12s} mean={train_mean[i]:+.4f}  std={train_std[i]:.4f}")

    np.save(PROCESSED_DIR / "X_train.npy", X_train)
    np.save(PROCESSED_DIR / "y_train.npy", y_train)
    np.save(PROCESSED_DIR / "mean_rpm_train.npy", rpm_train)
    np.save(PROCESSED_DIR / "X_test.npy", X_test)
    np.save(PROCESSED_DIR / "y_test.npy", y_test)
    np.save(PROCESSED_DIR / "mean_rpm_test.npy", rpm_test)
    np.save(PROCESSED_DIR / "train_mean.npy", train_mean)
    np.save(PROCESSED_DIR / "train_std.npy", train_std)

    print(f"\nShapes:")
    print(f"  X_train: {X_train.shape}  (windows, timesteps, channels)")
    print(f"  y_train: {y_train.shape}")
    print(f"  X_test:  {X_test.shape}")
    print(f"  y_test:  {y_test.shape}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()