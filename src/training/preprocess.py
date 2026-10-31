#!/usr/bin/env python3
"""
Phase 2 (v3): Preprocessing for the 6-channel model.

Creates X_train.npy of shape (N, 50, 6) -> (samples, timesteps, channels).
Automatically loads 3 files per class from data/raw based on filename prefix.
"""

import yaml
import numpy as np
import pandas as pd
from pathlib import Path
import glob

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_PATH = REPO_ROOT / "configs" / "sensors.yaml"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

FEATURE_COLS = CFG["features"]["time_series"]
RPM_AS_CHANNEL = CFG["features"].get("rpm_as_channel", False)
WINDOW_SIZE = CFG["sampling"]["window_samples"]  # Should be 50
STEP_SIZE = CFG["sampling"]["step_samples"]      # Should be 25
RPM_COL = "rpm"

LABELS = ["healthy", "imbalanced", "friction"]
LABEL_MAP = {label: idx for idx, label in enumerate(LABELS)}

def load_and_clean_csv(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required = FEATURE_COLS + [RPM_COL, "label"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in {filepath}")
    
    df = df[required].copy()
    df[RPM_COL] = df[RPM_COL].ffill().bfill().fillna(0.0)
    return df.dropna()

def create_windows(df: pd.DataFrame):
    data = df[FEATURE_COLS].values          
    rpm = df[RPM_COL].values                
    label_idx = LABEL_MAP[df["label"].iloc[0]]

    X, y = [], []
    for start in range(0, len(data) - WINDOW_SIZE + 1, STEP_SIZE):
        window_5ch = data[start : start + WINDOW_SIZE]        # shape (50, 5)

        if RPM_AS_CHANNEL:
            rpm_mean = float(np.mean(rpm[start : start + WINDOW_SIZE]))
            rpm_channel = np.full((WINDOW_SIZE, 1), rpm_mean, dtype=np.float32)
            window = np.concatenate([window_5ch, rpm_channel], axis=1) # (50, 6)
        else:
            window = window_5ch

        X.append(window)
        y.append(label_idx)

    return np.array(X, dtype=np.float32), np.array(y)

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    train_X, train_y = [], []
    test_X, test_y = [], []

    print(f"Window size: {WINDOW_SIZE} | Channels: {6 if RPM_AS_CHANNEL else 5}")
    print("Auditing data/raw folder...\n")

    for label in LABELS:
        # Find all CSVs for this label
        files = sorted(glob.glob(str(RAW_DIR / f"{label}_*.csv")))
        
        if len(files) < 3:
            raise ValueError(f"Found {len(files)} files for '{label}'. Need at least 3.")

        # Use the last file alphabetically as the test set, first two as train
        test_files = files[-1:]
        train_files = files[:-1]

        for fpath in train_files:
            df = load_and_clean_csv(Path(fpath))
            X, y = create_windows(df)
            train_X.append(X)
            train_y.append(y)
            print(f"  [TRAIN] {Path(fpath).name} → {len(X)} windows")

        for fpath in test_files:
            df = load_and_clean_csv(Path(fpath))
            X, y = create_windows(df)
            test_X.append(X)
            test_y.append(y)
            print(f"  [TEST ] {Path(fpath).name} → {len(X)} windows")

    X_train = np.concatenate(train_X, axis=0)
    y_train = np.concatenate(train_y, axis=0)
    X_test = np.concatenate(test_X, axis=0)
    y_test = np.concatenate(test_y, axis=0)

    # Standardize using TRAIN stats ONLY
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

    print(f"\n--- SUCCESS ---")
    print(f"X_train shape: {X_train.shape}") # Should be (N, 50, 6)
    print(f"X_test shape:  {X_test.shape}")
    print(f"\nNORM_MEAN: {np.round(train_mean, 4)}")
    print(f"NORM_STD:  {np.round(train_std, 4)}")
    print("\nSaved to data/processed/")

if __name__ == "__main__":
    main()