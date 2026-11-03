"""
Smoke tests for the fixture-based pipeline.
Runs fast (~10s), no real data, no GPU. Designed for CI.
"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd, env=None, timeout=120):
    """Run a command from repo root, return (returncode, stdout+stderr)."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout + result.stderr


def test_preprocess_fixtures():
    """Preprocess.py should run on fixtures and produce 5-channel arrays."""
    rc, out = run(
        [sys.executable, "src/training/preprocess.py"],
        env={"MHE_RAW_DIR": "tests/fixtures"},
    )
    assert rc == 0, f"preprocess failed:\n{out}"

    X_train = np.load(REPO_ROOT / "data/processed/X_train.npy")
    X_test = np.load(REPO_ROOT / "data/processed/X_test.npy")

    # 3 classes × 7 windows each = 21 windows
    assert X_train.shape == (21, 50, 5), f"Unexpected X_train shape: {X_train.shape}"
    assert X_test.shape == (21, 50, 5), f"Unexpected X_test shape: {X_test.shape}"

    assert not np.isnan(X_train).any(), "X_train contains NaN"
    assert not np.isnan(X_test).any(), "X_test contains NaN"


def test_train_2_epochs():
    """train.py should complete 2 epochs on fixtures without crashing."""
    rc, out = run(
        [sys.executable, "src/training/train.py"],
        env={"MHE_EPOCHS": "2"},
    )
    assert rc == 0, f"train failed:\n{out}"

    # Checkpoint should exist
    ckpt = REPO_ROOT / "models/checkpoints/v3_5ch_flat.pt"
    assert ckpt.exists(), f"Checkpoint not created: {ckpt}"
    assert ckpt.stat().st_size > 1000, "Checkpoint suspiciously small"

    # Metrics file should exist
    metrics = REPO_ROOT / "results/reports/v3_metrics.json"
    assert metrics.exists(), "Metrics JSON not created"