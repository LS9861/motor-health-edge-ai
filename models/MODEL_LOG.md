# Model version log

Tracks every trained model, its input features, test metrics, and the
reasoning behind the version. Update this file before pushing any new
checkpoint to `models/checkpoints/`.

---

## v1 — 5-channel baseline (Phase 3, in progress)

- **Input**: 5 channels × 100 timesteps = (100, 5)
  - ax, ay, az (m/s²)
  - current_mA (mA)
  - voltage_v (V)
- **Dropped**: `rpm` (see `docs/phase1_bringup.md` → "RPM channel dropped")
- **Dataset**: 313 train / 159 test windows, 2 s window, 50 % overlap,
  per-window Z-score
- **Split**: by file (2 train / 1 test per class)
- **Classes**: healthy (0), imbalanced (1), friction (2)
- **Architecture**: TBD (1D-CNN, 3 conv blocks, GlobalAvgPool, 2 dense)
- **Training**: TBD (Adam, cross-entropy, early stopping)
- **Checkpoint**: `models/checkpoints/v1_5ch_baseline.pt`
- **Test metrics**:
  - Accuracy: TBD
  - Per-class F1: TBD
  - Confusion matrix: `results/figures/v1_confusion.png`
- **Rationale**: baseline for the fault classifier. RPM excluded due to
  1 Hz sampling vs 50 Hz window mismatch — see Step 6 of
  `docs/phase1_bringup.md`.

---

## v2 — 5 + mean_rpm scalar (Phase 4, planned)

- **Input**: (100, 5) time series **+** (1,) mean_rpm scalar
- **New in v2**: `mean_rpm` = per-window mean of the raw RPM staircase,
  broadcast as a scalar. Fed through a small Dense branch and
  concatenated with the CNN features before the classification head.
- **Requires**: minor `preprocess.py` change (save `mean_rpm_*.npy`);
  minor `train.py` change (two-branch model).
- **No recapture needed** — uses the existing CSVs.
- **Hypothesis**: imbalance and friction cause RPM *reductions* or
  *oscillations* that the 1 Hz signal cannot capture, but the
  window-mean still captures magnitude (motor running vs. bogged down).
  Expected accuracy delta: 0–5 %.
- **Checkpoint (planned)**: `models/checkpoints/v2_5ch_mean_rpm.pt`
- **Decision criterion**: promote v2 only if it beats v1 by ≥2 % test
  accuracy **and** per-class F1 does not degrade on any class.

---

## v3 — 6-channel @ 50 Hz RPM (Phase 5+, planned)

- **Input**: (100, 6) time series — adds `rpm` back at 50 Hz sampling
- **Requires**: firmware change
  - `RPM_WINDOW_MS` 1000 → 20
  - `rpm = pulses × 3000 / HOLES_PER_REV` (instead of × 60)
  - Optional: capture pulse timestamps for even higher resolution
- **Requires**: full dataset recapture (9 files, ~30 min)
- **Also requires**: archive current dataset