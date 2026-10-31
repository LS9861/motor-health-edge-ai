#!/usr/bin/env python3
"""PyTorch Dataset for the 6-channel motor model (v3)."""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


class MotorWindowDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        # X: (N, 100, 6) → stored as float32 tensor
        self.X = torch.from_numpy(X).float()
        # y: (N,) → stored as int64 tensor
        self.y = torch.from_numpy(y).long()

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        # PyTorch Conv1d expects (channels, timesteps), so permute on the fly
        return self.X[idx].permute(1, 0), self.y[idx]


def get_dataloaders(batch_size: int = 32):
    # Load the preprocessed arrays
    X_train = np.load(PROCESSED_DIR / "X_train.npy")
    y_train = np.load(PROCESSED_DIR / "y_train.npy")
    X_test = np.load(PROCESSED_DIR / "X_test.npy")
    y_test = np.load(PROCESSED_DIR / "y_test.npy")

    train_ds = MotorWindowDataset(X_train, y_train)
    test_ds = MotorWindowDataset(X_test, y_test)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    meta = {
        "in_channels": X_train.shape[2],   # will be 6
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    return train_loader, test_loader, meta