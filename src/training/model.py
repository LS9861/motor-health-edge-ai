#!/usr/bin/env python3
"""Compact 1D-CNN for motor fault classification (v1, 5 channels)."""

import torch
import torch.nn as nn


class MotorCNN1D(nn.Module):
    def __init__(self, in_channels: int = 5, n_classes: int = 3, dropout: float = 0.5):
        super().__init__()

        def block(c_in, c_out, kernel=5):
            return nn.Sequential(
                nn.Conv1d(c_in, c_out, kernel_size=kernel, padding=kernel // 2),
                nn.BatchNorm1d(c_out),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(kernel_size=2),
            )

        self.features = nn.Sequential(
            block(in_channels, 16),   # (B, 16, 50)
            block(16, 32),            # (B, 32, 25)
        )
        self.gap = nn.AdaptiveAvgPool1d(1)

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(32, n_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.gap(x)
        return self.classifier(x)


if __name__ == "__main__":
    m = MotorCNN1D(in_channels=5)
    print("Params:", sum(p.numel() for p in m.parameters()))
    print("Output:", m(torch.randn(8, 5, 100)).shape)