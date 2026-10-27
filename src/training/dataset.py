#!/usr/bin/env python3
"""PyTorch Dataset for motor-health-edge-ai (v1, 5 channels)."""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


class MotorWindowDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.from_numpy(X).float()   # (N, T, C)
        self.y = torch.from_numpy(y).long()

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        # Conv1d expects (C, T)
        return self.X[idx].permute(1, 0), self.y[idx]


def get_dataloaders(batch_size: int = 32):
    X_train = np.load(PROCESSED_DIR / "X_train.npy")
    y_train = np.load(PROCESSED_DIR / "y_train.npy")
    X_test  = np.load(PROCESSED_DIR / "X_test.npy")
    y_test  = np.load(PROCESSED_DIR / "y_test.npy")

    train_ds = MotorWindowDataset(X_train, y_train)
    test_ds  = MotorWindowDataset(X_test,  y_test)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False)
    return train_loader, test_loader, (X_train, y_train, X_test, y_test)