# motor-health-edge-ai

Edge AI motor health monitoring on ESP32-C3 with TFLM.

## Project Overview

This project collects vibration, current, and speed signals from a TT DC gear motor, trains a 1D-CNN classifier, quantizes it to INT8 TFLite, and deploys it on an ESP32-C3 using TensorFlow Lite Micro.

**Target classifications:** healthy, imbalanced, friction.

> ℹ️ An earlier 6-channel model that included supply voltage was **abandoned** after deploying to hardware revealed it was learning voltage as a shortcut rather than actual motor fault signatures. Removing voltage (6ch → 5ch) improved accuracy from 92.88% to **96.59%** and made the model robust to supply variation. See [`docs/phase6_deployment.md`](docs/phase6_deployment.md) for the full case study.

### Hardware

| Component | Role |
|-----------|------|
| ESP32-C3 SuperMini | MCU with Wi-Fi/BLE, 4MB flash |
| MPU6050 | 3-axis accelerometer (vibration) |
| INA228 | Current sensing (20-bit, I2C). Voltage also measured but **not used as a model input**. |
| IR reflective sensor | Motor speed (RPM) |
| TT DC gear motor | Target motor |
| L298N | Motor driver |

### Wiring Summary

- **MPU6050:** SDA → GPIO0, SCL → GPIO1, VCC → 3.3V
- **INA228:** SDA → GPIO0, SCL → GPIO1, VIN → 3.3V,
  VIN+ → supply+, VIN- → L298N +12V, VBUS → supply+ (jumper closed; voltage is measured but not fed to the model)
- **IR sensor:** OUT → GPIO10
- **L298N:** IN1 → GPIO4, IN2 → GPIO5, ENA jumper ON, common GND

> ⚠️ ESP32-C3 GPIOs are 3.3 V only. Never connect 5V sensor outputs directly.

> ℹ️ The INA228 replaced an earlier ACS712 + resistor-divider design. See [`docs/phase1_bringup.md`](docs/phase1_bringup.md) for the rationale.

## Results

| Metric | Value |
|--------|-------|
| Test accuracy (5-channel) | **96.59%** (312 / 323) |
| INT8 accuracy | **96.59%** (lossless) |
| Model size (INT8) | 5.6 KB |
| Parameters | 963 |
| RAM (tensor arena) | 32 KB |
| Inference time on ESP32-C3 | **27.9 ms (median, n=104)** |
*Measured on ESP32-C3 @ 160 MHz with INT8 TFLite Micro, 50×5 input window,
serial I/O active. Median of 104 consecutive inferences during steady-state
healthy motor operation; variance <50 µs. See `docs/phase12_inference_time.md`.*

### Confusion matrix (5-channel model, test set)
Predicted
healthy imbalanced friction
True healthy [ 125 0 1 ]
True imbalanced [ 0 95 6 ]
True friction [ 0 4 92 ]


Precision — healthy 1.00, imbalanced 0.96, friction 0.93. Macro F1 = 0.96.

### The story behind the numbers

The original 6-channel model achieved **92.88% offline accuracy** but produced garbage predictions on hardware — **every** healthy motor was classified as FRICTION. Root cause: the model was classifying faults based on a **20 mV supply voltage difference** between training and inference, not the actual vibration/current signatures. After removing voltage (6ch → 5ch), accuracy rose to **96.59%** and the model became robust to supply variation.

Full diagnostic: [`docs/phase6_deployment.md`](docs/phase6_deployment.md).

## Repository Structure
motor-health-edge-ai/
├── data/ # raw, processed, synthetic datasets
├── src/
│ ├── training/ # preprocess, train, evaluate, export
│ ├── deployment/ # quantization, header generation
│ ├── inference/ # ESP32-C3 firmware (TFLM)
│ └── common/ # shared Python helpers
├── scripts/ # data logger, utilities, pipeline
├── models/ # checkpoints, onnx, tflite, headers
├── results/ # figures, reports, logs
├── docs/ # bring-up logs, deployment report
├── tests/ # unit and parity tests
├── configs/ # sensors.yaml, train.yaml, quant.yaml
└── .github/workflows/ # CI/CD


## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Hardware bring-up | ✅ Done | ESP32-C3, MPU6050, INA228, LM393 encoder, L298N |
| Phase 2 — Data collection | ✅ Done | 9 CSVs (3 healthy, 3 imbalanced, 3 friction), ~1500 samples each |
| Phase 3 — Preprocessing | ✅ Done | 50-sample windows, 5 channels, per-channel standardization |
| Phase 4 — Training | ✅ Done | 1D-CNN, 963 params, **96.59% test accuracy** |
| Phase 5 — Quantization | ✅ Done | INT8 TFLite, **96.59% (lossless)**, 5.6 KB model |
| Phase 6 — Deployment | ✅ Done | TFLM on ESP32-C3, verified on hardware |
| Phase 7 — Verification | 🟡 In progress | Extended fault-cycle testing + debouncing (blocked on JGA25 hardware) |

## Hardware Bring-up & Data Collection

See [`docs/phase1_bringup.md`](docs/phase1_bringup.md) for the full bring-up log (sensor wiring, calibration, ADC characteristics, encoder validation, and data-collection protocol).

## What was learned

Building and debugging this project surfaced four engineering lessons that matter for any deployed ML system.

### 1. Feature leakage is invisible offline

A 6-channel model (with supply voltage) reached **92.88% offline accuracy** on held-out test data. Deployed to real hardware, it classified **every healthy motor as FRICTION** — a complete collapse.

Root cause: the model was classifying based on a **20 mV supply voltage difference** between training data (6.02 V) and inference (6.00 V), not on the actual vibration/current signatures. Because the voltage normalizer had a 25 mV standard deviation, this tiny drift amplified to 0.8σ — enough to flip every prediction.

This is a textbook case of **shortcut learning** in industrial ML: the model finds the easiest correlation in the training data, which happens to be a spurious one, and collapses when the environment changes.

### 2. Removing a bad feature beats adding a good one

After dropping voltage from the input (6ch → 5ch), accuracy **increased** from 92.88% to **96.59%**, and the model became robust to supply-voltage variation. The 3.7-point accuracy gain came from the model spending all of its weights on real physics instead of fitting noise.

The intuition is uncomfortable at first: how can removing a feature *improve* a model? But it's the same reason a decision tree with `n` features outperforms one with `n+1` when the extra feature is pure noise. The feature was carrying variance that fought against the signal.

### 3. INT8 quantization of a small 1D-CNN is effectively free

The 5-channel model:
- Float32: **96.59%** accuracy, 5.6 KB
- INT8:    **96.59%** accuracy, 5.6 KB

Lossless. No accuracy drop, no tuning. This is a general property of small CNNs with well-distributed representative datasets: the INT8 quantization noise is well below the model's decision margin.

The trade-off to worry about isn't quantization accuracy — it's **quantization robustness to distribution shift**. If a model is already on the edge of a decision boundary, INT8 rounding can push it over. This model wasn't; hence 96.59% survived intact.

### 4. Deployment verification must include physical conditions

Held-out test splits don't catch distribution shift. The 6-channel model's test accuracy was excellent *because the test split came from the same physical setup as training*. The real validation is running the model on hardware with the same physical conditions that inference will see — different supply voltage, different ambient temperature, different motor speed, different sensor mounting.

**Practical rule:** for every model you ship, validate at least one physical parameter outside the training envelope (voltage ±5%, ambient temperature ±10°C, motor speed ±20%). If the model is sensitive to that parameter, that parameter is a leak — remove it or retrain to be robust to it.

## Reproducing this project

To reproduce the 5-channel model from scratch:

 `bash
# 1. Preprocess raw CSVs (5 channels, 50-sample windows)
python src/training/preprocess.py

# 2. Train the model (~3 min on CPU)
python src/training/train.py

# 3. Export to INT8 TFLite
python scripts/export_v3_tflite.py

# 4. Generate C header for TFLM
python scripts/generate_model_header.py

# 5. Flash the ESP32-C3
cd src/inference && pio run -t upload

## Roadmap

    ☑Phase 1 — Hardware bring-up (ESP32-C3 + MPU6050 + INA228 + LM393 + L298N)
    ☑Phase 2 — Data collection (9 CSV files across 3 fault classes)
    ☑hase 3 — Preprocessing (windowing + per-channel standardization)
    ☑Phase 4 — 1D-CNN training (96.59% test accuracy)
    ☑Phase 5 — INT8 quantization (lossless, 5.6 KB model)
    ☑Phase 6 — TFLM deployment on ESP32-C3
    ☑Shortcut-learning diagnosis and fix (voltage → 5-channel model)
    ☑Phase 7 — Extended verification and state-machine debouncing
    ☑Phase 8 — CI/CD (GitHub Actions)
	☑Phase 9 — Live visualization (plot_live.py + docs/visualization.md)
    □ Phase 10 — JGA25 hardware rebuild + fresh data collection
    □ Phase 11 — Retrain on new hardware (target: <5% accuracy drop)
    □ Phase 12 — On-device inference time measurement
    □ Phase 13 — State-machine debouncing + STANDBY state
    □ Phase 14 — Extended fault-cycle testing (3 cycles × 3 states)
    □ Phase 15 — LinkedIn post + portfolio update
	
## Documentation Index

    docs/phase1_bringup.md — hardware bring-up log

    docs/phase6_deployment.md — training, quantization, deployment, and the shortcut-learning case study