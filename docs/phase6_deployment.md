# Phase 6 — Deployment and Shortcut Learning Discovery

## TL;DR

The original 6-channel model achieved 92.88% offline accuracy but produced
garbage predictions on hardware (every window classified as FRICTION).
Root cause: the model was using supply voltage as a shortcut feature.
Removing voltage (5-channel model) raised accuracy to **96.59%** and
produced a robust, deployable model.

---

## The Bug: Feature Leakage via Voltage

### Symptoms

After deploying the 6-channel INT8 model to ESP32-C3, every healthy motor
window classified as `FRICTION` with ~90% confidence. Confusion matrix
was perfectly diagonal in offline testing but completely collapsed on
hardware.

### Diagnostic Path

1. **Verified model bytes**: `model_data.h` was byte-identical to
   `v3_int8.tflite` (same MD5).
2. **Verified input tensor**: The float tensor fed to the model matched
   Python's computation exactly (`input_f32[0]`, `[250]` matched).
3. **Verified model outputs in Python**: Feeding the exact `# F:` tensor
   from the ESP32 serial log into Python's TFLite interpreter produced
   the SAME prediction (`FRICTION`).

   **This proved the model itself was wrong, not the C++ code.**

4. **Sweep test**: Systematically varied each input channel and measured
   prediction changes. Only `voltage_v` flipped the prediction, and it
   flipped sharply:

   | Voltage | Prediction |
   |---------|-----------|
   | 5.95 V  | FRICTION  |
   | 6.00 V  | FRICTION  |
   | 6.02 V  | **HEALTHY** |
   | 6.05 V  | HEALTHY   |

   Training data voltage mean = **6.02 V**, std = **0.025 V**.
   On-device reading = **6.00 V**. That 20 mV difference, amplified by
   the tiny normalizer std, produced a 0.8σ shift in the normalized input.

### Root Cause: Shortcut Learning

The 6-channel model learned to discriminate faults based on the small
voltage difference between training and fault data, not the actual
vibration/current signatures. This is a known failure mode called
**shortcut learning** or **feature leakage**.

Why it happened:
- The bench supply happened to be extremely stable (~6.02 V) during
  healthy data collection.
- Fault captures had slightly different voltage (L298N drew different
  current, causing ~10–30 mV sag).
- The model found this correlation easiest to fit.

Why it's dangerous:
- Any voltage drift (battery, different supply, temperature) breaks the
  model completely.
- The 92.88% offline accuracy was an illusion — real accuracy at 6.00 V
  was **48.92%** (worse than random).

### Diagnostic: Accuracy Under Voltage Perturbation

| Model | Baseline | Voltage = 6.00 V | Voltage = mean |
|-------|----------|------------------|----------------|
| 6-channel | 90.40% | **48.92%** | 57.28% |
| 5-channel | 96.59% | 96.59% | 96.59% |

The 5-channel model is **insensitive to supply voltage** — exactly as
expected for a model that learns motor health from vibration, current,
and RPM.

---

## The Fix: Retrain Without Voltage

**Change:** `configs/sensors.yaml` — removed `voltage_v` from
`features.time_series`.

**Result:** new 5-channel model (`ax, ay, az, current_mA, rpm`) with:

- 963 params (was 1003)
- 5.6 KB TFLite file (was 5.8 KB)
- 96.59% test accuracy (was 92.88%)
- INT8 quantization: **lossless** (96.59% → 96.59%)

---

## Deployment Verification

Model deployed to ESP32-C3 SuperMini and tested with physical fault
injection:

| Motor State | Predicted Class | Confidence |
|-------------|-----------------|------------|
| Off | HEALTHY | HIGH (logit +4 to +5) |
| On, no fault | HEALTHY | HIGH |
| On, cardboard friction | FRICTION | MEDIUM-HIGH |
| On, coin imbalance | IMBALANCED | MEDIUM |

**Known limitations:**

- **1-second lag** between physical fault change and prediction change
  (one full window must fill before reclassification).
- **Occasional single-window noise** during transitions (model sees a
  mixed signal in the buffer).
- **No confirmation debouncing** — a single window drives the output.
  Production systems should require 3–5 consecutive windows of the same
  class before reporting a state change.

**These are expected behaviors**, not bugs. They are addressable in
firmware with a moving-window state machine.

---

## Lessons for Industrial ML

1. **Validate models under varied operating conditions**, not just
   held-out test splits from the same setup.
2. **Feature engineering matters more than architecture** — removing
   one bad feature improved accuracy and robustness simultaneously.
3. **Cross-check "too good" results** — the 6-channel model's 90%
   accuracy hid a fatal dependency.
4. **The C++ was innocent** — spend time on data forensics before
   blaming embedded code.

This case study is a real demonstration of feature leakage, shortcut
learning, and the importance of end-to-end validation.

---

## Files

- Model: `models/checkpoints/v3_5ch_flat.pt` (PyTorch)
- Model: `models/tflite/v3_int8.tflite` (INT8, 5.6 KB)
- Firmware: `src/inference/src/main.cpp`
- Header: `src/inference/include/model_data.h`
- Config: `src/inference/include/norm_params.h`
- Metrics: `results/reports/v3_metrics.json`