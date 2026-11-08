#!/usr/bin/env python3
"""
Phase 2 (v3): Preprocessing for the 5-channel model
(ax, ay, az, current, rpm).

Creates X_train.npy of shape (N, 50, 5).
RPM is included as the 5th channel — voltage compensation happens in firmware
(main.cpp scales RPM based on measured supply voltage, so the model sees
a consistent RPM regardless of 12V/13V/14V supply).

Train/test split: fixed per-class test file (13V capture), everything else
trains. Excludes *_live_*.csv captures from plot_live.py.

Data augmentation: training windows are augmented with ±10% vibration scaling
to simulate day-to-day physical drift (temperature, screw tension, mounting
torque). This prevents Healthy/Imbalanced confusion from small physical
variations. Test windows are NOT augmented.
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = Path(os.environ.get("MHE_RAW_DIR", REPO_ROOT / "data" / "raw"))
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_PATH = REPO_ROOT / "configs" / "sensors.yaml"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

FEATURE_COLS = CFG["features"]["time_series"]
RPM_AS_CHANNEL = CFG["features"].get("rpm_as_channel", False)
WINDOW_SIZE = CFG["sampling"]["window_samples"]  # 50
STEP_SIZE = CFG["sampling"]["step_samples"]      # 25
RPM_COL = "rpm"

LABELS = ["healthy", "imbalanced", "friction"]
LABEL_MAP = {label: idx for idx, label in enumerate(LABELS)}

# Fixed test set — 13V captures (unseen midpoint voltage)
TEST_FILES = {
    "healthy": "healthy_7.csv",       # 13V
    "imbalanced": "imbalanced_9.csv", # 13V
    "friction": "friction_9.csv",     # 13V
}


def load_and_clean_csv(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required = FEATURE_COLS + [RPM_COL, "label"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in {filepath}")
    df = df[required].copy()
    df[RPM_COL] = df[RPM_COL].ffill().bfill().fillna(0.0)
    return df.dropna()


def create_windows(df: pd.DataFrame, is_train: bool = False):
    """Slice a DataFrame into 50-sample windows.

    If is_train=True, generate augmented copies with vibration scaled
    ±5-15% to simulate day-to-day physical drift. Test windows are clean.
    """
    data = df[FEATURE_COLS].values
    rpm = df[RPM_COL].values
    label_idx = LABEL_MAP[df["label"].iloc[0]]

    X, y = [], []
    n_feature_ch = len(FEATURE_COLS)

    for start in range(0, len(data) - WINDOW_SIZE + 1, STEP_SIZE):
        window_feat = data[start : start + WINDOW_SIZE]  # (50, n_feature_ch)

        if RPM_AS_CHANNEL:
            rpm_mean = float(np.mean(rpm[start : start + WINDOW_SIZE]))
            rpm_channel = np.full((WINDOW_SIZE, 1), rpm_mean, dtype=np.float32)
            window = np.concatenate([window_feat, rpm_channel], axis=1)
        else:
            window = window_feat

        X.append(window)
        y.append(label_idx)

        if is_train:
            # Aug 1: vibration amplified (cold motor, loose screw)
            aug_plus = window.copy()
            aug_plus[:, 0:3] *= np.random.uniform(1.05, 1.15)
            X.append(aug_plus)
            y.append(label_idx)

            # Aug 2: vibration attenuated (warm motor, tight screw)
            aug_minus = window.copy()
            aug_minus[:, 0:3] *= np.random.uniform(0.85, 0.95)
            X.append(aug_minus)
            y.append(label_idx)

    return np.array(X, dtype=np.float32), np.array(y)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    train_X, train_y = [], []
    test_X, test_y = [], []

    n_ch = len(FEATURE_COLS) + (1 if RPM_AS_CHANNEL else 0)
    print(f"Window size: {WINDOW_SIZE} | Channels: {n_ch}")
    print(f"Data augmentation: {'ON' if True else 'OFF'} (training only)")
    print("Auditing data/raw folder...\n")

    for label in LABELS:
        all_files = sorted(glob.glob(str(RAW_DIR / f"{label}_*.csv")))
        files = [f for f in all_files if "_live_" not in Path(f).name]

        if len(files) < 1:
            raise ValueError(f"No files found for '{label}' in {RAW_DIR}.")

        print(f"\n[{label}] found {len(files)} files")

        target_test = str(RAW_DIR / TEST_FILES[label])
        test_files = [f for f in files if f == target_test]
        train_files = [f for f in files if f != target_test]

        if not test_files:
            raise ValueError(f"Test file {TEST_FILES[label]} not found for {label}")
        print(f"  🎯 TEST: {TEST_FILES[label]} (unseen voltage)")

        for fpath in train_files:
            df = load_and_clean_csv(Path(fpath))
            X, y = create_windows(df, is_train=True)
            train_X.append(X)
            train_y.append(y)
            print(f"  [TRAIN] {Path(fpath).name} → {len(X)} windows (aug)")

        for fpath in test_files:
            df = load_and_clean_csv(Path(fpath))
            X, y = create_windows(df, is_train=False)
            test_X.append(X)
            test_y.append(y)
            print(f"  [TEST ] {Path(fpath).name} → {len(X)} windows (clean)")

    X_train = np.concatenate(train_X, axis=0)
    y_train = np.concatenate(train_y, axis=0)
    X_test = np.concatenate(test_X, axis=0)
    y_test = np.concatenate(test_y, axis=0)

    train_mean = X_train.mean(axis=(0, 1))
    train_std = X_train.std(axis=(0, 1))
    train_std[train_std == 0] = 1.0

    X_train = (X_train - train_mean) / train_std
    X_test = (X_test - train_mean) / train_std

    np.save(PROCESSED_DIR / "X_train.npy", X_train)
    np.save(PROCESSED_DIR / "y_train.npy", y_train)
    np.save(PROCESSED_DIR / "X_test.npy", X_test)
    np.save(PROCESSED_DIR / "y_test.npy", y_test)
    np.save(PROCESSED_DIR / "train_mean.npy", train_mean)
    np.save(PROCESSED_DIR / "train_std.npy", train_std)

    print("\n--- SUCCESS ---")
    print(f"X_train shape: {X_train.shape}  (3× due to augmentation)")
    print(f"X_test shape:  {X_test.shape}   (clean, not augmented)")
    print(f"\nNORM_MEAN: {np.round(train_mean, 4)}")
    print(f"NORM_STD:  {np.round(train_std, 4)}")
    print("\nSaved to data/processed/")


if __name__ == "__main__":
    main()