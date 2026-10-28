#!/usr/bin/env python3
"""PyTorch Dataset for motor-health-edge-ai — v2 (time series + mean_rpm scalar)."""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


class MotorWindowDataset(Dataset):
    def __init__(self, X: np.ndarray, mean_rpm: np.ndarray, y: np.ndarray):
        self.X = torch.from_numpy(X).float()                 # (N, T, C)
        self.mean_rpm = torch.from_numpy(mean_rpm).float()   # (N,)
        self.y = torch.from_numpy(y).long()                  # (N,)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        # Conv1d expects (C, T) — permute on the fly
        return self.X[idx].permute(1, 0), self.mean_rpm[idx].unsqueeze(0), self.y[idx]


def get_dataloaders(batch_size: int = 32):
    X_train = np.load(PROCESSED_DIR / "X_train.npy")
    y_train = np.load(PROCESSED_DIR / "y_train.npy")
    rpm_train = np.load(PROCESSED_DIR / "mean_rpm_train.npy")
    X_test = np.load(PROCESSED_DIR / "X_test.npy")
    y_test = np.load(PROCESSED_DIR / "y_test.npy")
    rpm_test = np.load(PROCESSED_DIR / "mean_rpm_test.npy")

    # Normalize mean_rpm using train statistics only (no leakage)
    rpm_mean = float(rpm_train.mean())
    rpm_std = float(rpm_train.std()) or 1.0
    rpm_train_n = (rpm_train - rpm_mean) / rpm_std
    rpm_test_n = (rpm_test - rpm_mean) / rpm_std

    train_ds = MotorWindowDataset(X_train, rpm_train_n, y_train)
    test_ds = MotorWindowDataset(X_test, rpm_test_n, y_test)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    meta = {
        "in_channels": X_train.shape[2],
        "n_train": len(X_train),
        "n_test": len(X_test),
        "rpm_mean": rpm_mean,
        "rpm_std": rpm_std,
    }
    return train_loader, test_loader, meta