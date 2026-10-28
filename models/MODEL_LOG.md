# Model version log

Tracks every trained model, its input features, test metrics, and the
reasoning behind the version. Update this file before pushing any new
checkpoint to `models/checkpoints/`.

---

## v1 — 5-channel baseline (Phase 3, DONE)

- **Input**: 5 channels × 100 timesteps = (100, 5)
  - ax, ay, az (m/s²), current_mA (mA), voltage_v (V)
- **Dropped**: `rpm` (1 Hz sample rate; see docs/phase1_bringup.md)
- **Dataset**: 313 train / 159 test windows, 2 s windows @ 50% overlap
- **Normalization**: global per-channel mean/std from train set
  (per-window Z-score replaced — it erased amplitude signatures)
- **Architecture**: 2 conv blocks (16 → 32 filters), GAP, single dense
  - Params: 3,203 (was 61,283 in the pre-fix version)
- **Training**: Adam lr=1e-3, wd=1e-3, CrossEntropy, early stopping (patience=15)
- **Checkpoint**: `models/checkpoints/v1_5ch_baseline.pt`
- **Metrics** (test set, 159 windows):
  - Accuracy: **91.2 %**
  - Healthy:   P=1.00 R=1.00 F1=1.00  (n=62)
  - Imbalanced: P=1.00 R=0.72 F1=0.84  (n=50)
  - Friction:   P=0.77 R=1.00 F1=0.87  (n=47)
  - Confusion matrix:
    [[62  0  0]
     [ 0 36 14]   ← 14 imbalanced predicted as friction
     [ 0  0 47]]
- **Overfitting check**: train_loss=0.14, val_loss=0.16 — no gap. Model
  generalizes; the misclassifications are data overlap, not memorization.
- **Failure analysis**: all errors are imbalanced → friction. Physical
  cause: both faults produce rhythmic vibration at shaft frequency;
  the distinguishing signal is current amplitude, which varies across
  friction captures due to inconsistent hand-applied cardboard pressure.
- **Decision**: accept v1 as baseline. Address the imbalanced/friction
  confusion in v2 with the `mean_rpm` scalar feature.

---

## v2 — 5 + mean_rpm scalar (Phase 4, DONE)

- **Input**: (100, 5) time series + (1,) mean_rpm scalar (per window)
- **New in v2**: mean_rpm = per-window mean of the 1 Hz RPM signal.
  Normalized using train-set mean/std (179.56 / 150.24).
- **Architecture**: two-branch CNN
  - Branch 1: 2 conv blocks (16 → 32 filters) + GAP → 32-dim
  - Branch 2: Linear(1 → 8) + ReLU → 8-dim
  - Concatenate → Dropout(0.5) → Linear(40 → 3)
  - Params: 3,243 (+40 vs v1)
- **Training**: Adam lr=1e-3, wd=1e-3, CrossEntropy, early stopping (patience=15)
- **Checkpoint**: `models/checkpoints/v2_5ch_mean_rpm.pt`
- **Metrics** (test set, 159 windows):
  - Accuracy: **96.2 %** (+5.0 vs v1)
  - Healthy:    P=1.00 R=1.00 F1=1.00  (n=62)
  - Imbalanced: P=0.94 R=0.94 F1=0.94  (n=50)
  - Friction:   P=0.94 R=0.94 F1=0.94  (n=47)
  - Confusion matrix:
    [[62  0  0]
     [ 0 47  3]   ← errors now symmetric (was 14:0)
     [ 0  3 44]]
- **Hypothesis outcome**: CONFIRMED
  - Pre-run analysis suggested mean_rpm had weak univariate signal
    (class means 158/185/200, std ~150 — overlap)
  - Empirically, the CNN learned a joint rule combining vibration
    pattern with mean_rpm to disambiguate imbalanced vs friction
  - Errors dropped from 14 to 6, both classes' F1 rose to 0.94
- **Lesson documented**: multimodal fusion extracts signal from features
  that appear uninformative in isolation. Univariate class statistics do
  not predict a feature's usefulness to a joint classifier.
- **Decision**: PROMOTE v2 as the current best model. Use for
  Phase 5 (quantization and TFLM deployment).

---

## v3 — 6-channel @ 50 Hz RPM (Phase 5+, planned)

- **Input**: (100, 6) time series — adds `rpm` back at 50 Hz sampling
- **Requires**: firmware change
  - `RPM_WINDOW_MS` 1000 → 20
  - `rpm = pulses × 3000 / HOLES_PER_REV` (instead of × 60)
  - Optional: capture pulse timestamps for even higher resolution
- **Requires**: full dataset recapture (9 files, ~30 min)
- **Also requires**: archive current dataset