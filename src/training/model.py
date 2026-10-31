#!/usr/bin/env python3
"""
Simple 6-channel 1D-CNN for motor fault classification (v3).

Input:  (batch, 6, 100)  — 5 sensor channels + mean_rpm (repeated)
Output: (batch, 3)       — logits for [healthy, imbalanced, friction]

No branches, no concat, no multi-input. Easiest possible model to
convert to TFLite.
"""

import torch
import torch.nn as nn


class MotorCNN1D(nn.Module):
    def __init__(self, in_channels: int = 6, n_classes: int = 3, dropout: float = 0.5):
        super().__init__()

        # A small reusable conv block: Conv → BatchNorm → ReLU → MaxPool
        def block(c_in, c_out, kernel=5):
            return nn.Sequential(
                nn.Conv1d(c_in, c_out, kernel_size=kernel, padding=kernel // 2),
                nn.BatchNorm1d(c_out),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(kernel_size=2),
            )

                # Two conv blocks: 6 → 8 → 16 channels (smaller for ESP32)
        self.features = nn.Sequential(
            block(in_channels, 8),
            block(8, 16),
        )

        # Global average pooling: reduces (batch, 32, 25) → (batch, 32, 1)
        self.gap = nn.AdaptiveAvgPool1d(1)

        # Final classifier: dropout then one dense layer
        self.classifier = nn.Sequential(
            nn.Flatten(),          # (batch, 32)
            nn.Dropout(dropout),
            nn.Linear(16, n_classes),
        )

    def forward(self, x):
        # x: (batch, channels, timesteps)
        x = self.features(x)
        x = self.gap(x)
        return self.classifier(x)


# Quick self-test when running this file directly
if __name__ == "__main__":
    m = MotorCNN1D(in_channels=6)
    print("Params:", sum(p.numel() for p in m.parameters()))
    print("Output:", m(torch.randn(8, 6, 100)).shape)