#!/usr/bin/env python3
"""1D-CNN with two branches: time series + mean_rpm scalar (v2)."""

import torch
import torch.nn as nn


class MotorCNN1DWithRPM(nn.Module):
    def __init__(self, in_channels: int = 5, n_classes: int = 3, dropout: float = 0.5):
        super().__init__()

        def conv_block(c_in, c_out, kernel=5):
            return nn.Sequential(
                nn.Conv1d(c_in, c_out, kernel_size=kernel, padding=kernel // 2),
                nn.BatchNorm1d(c_out),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(kernel_size=2),
            )

        # Branch 1: time series (5, 100) -> (32, 25) -> GAP -> (32,)
        self.features = nn.Sequential(
            conv_block(in_channels, 16),
            conv_block(16, 32),
        )
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.cnn_out_dim = 32

        # Branch 2: mean_rpm scalar (1,) -> (8,)
        self.rpm_branch = nn.Sequential(
            nn.Linear(1, 8),
            nn.ReLU(inplace=True),
        )

        # Fusion + head
        fused_dim = self.cnn_out_dim + 8
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(fused_dim, n_classes),
        )

    def forward(self, x_ts, x_rpm):
        # x_ts:  (B, C, T)   time series
        # x_rpm: (B, 1)      scalar per sample
        h_ts = self.gap(self.features(x_ts)).flatten(1)   # (B, 32)
        h_rpm = self.rpm_branch(x_rpm)                     # (B, 8)
        h = torch.cat([h_ts, h_rpm], dim=1)                # (B, 40)
        return self.classifier(h)


if __name__ == "__main__":
    m = MotorCNN1DWithRPM(in_channels=5)
    print("Params:", sum(p.numel() for p in m.parameters()))
    x_ts = torch.randn(8, 5, 100)
    x_rpm = torch.randn(8, 1)
    print("Output:", m(x_ts, x_rpm).shape)