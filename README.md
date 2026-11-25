# motor-health-edge-ai

Edge AI motor health monitoring on ESP32-C3 with TFLM.

## Project Overview

This project collects vibration, current, and speed signals from a **JGA25-370 gear motor (built-in magnetic encoder)**, trains a 1D-CNN classifier, quantizes it to INT8 TFLite, and deploys it on an ESP32-C3 using TensorFlow Lite Micro.

**Target classifications:** healthy, imbalanced, friction.

> 🔁 **Origins.** This project was first designed and validated on a small **TT DC gear motor** (~6 V bench). It was later rebuilt end-to-end around a **JGA25-370** geared motor with a built-in magnetic encoder. The TT phase produced the key engineering lessons (shortcut learning, lossless quantization, on-device validation); the JGA25 rebuild is the finished, deployed configuration. The TT → JGA25 transfer and retrain is documented in [`docs/phase10_jga25.md`](docs/phase10_jga25.md) and [`docs/phase11_retrain.md`](docs/phase11_retrain.md).

> ℹ️ An earlier 6-channel model that included supply voltage was **abandoned** after deploying to hardware revealed it was learning voltage as a shortcut rather than actual motor fault signatures. Removing voltage (6ch → 5ch) improved accuracy from 92.88% to **96.59%** and made the model robust to supply variation. See [`docs/phase6_deployment.md`](docs/phase6_deployment.md) for the full case study.

### Hardware

| Component | Role |
|-----------|------|
| ESP32-C3 SuperMini | MCU with Wi-Fi/BLE, 4MB flash, on-device INT8 inference |
| MPU6050 (MPU6500 clone) | 3-axis accelerometer (vibration) |
| INA228 | Current sensing (20-bit, I2C). Voltage also measured but **not used as a model input**. |
| JGA25-370 gear motor | Target motor, **built-in magnetic encoder** for the speed signal |
| L298N | Motor driver |
| E-Stop button + mode switch | Safety: latching E-stop, I²t current protection, manual/software mode |

> ℹ️ **Supply voltage.** Early bench bring-up used ~6 V only to sanity-check sensors. All **real data was captured, trained, and tested at 12–14 V**, with the firmware normalizing RPM across that range. Reproduce the fault datasets at 12–14 V.

<img width="10931" height="9147" alt="circuitdiagram-motorhealthedgeai" src="https://github.com/user-attachments/assets/b2d9af9d-9461-4a59-8785-8c72f5ff9357" />

<!-- Portfolio: TT-motor and JGA25-370 photos belong here (kept for the build narrative). -->


### Wiring Summary

- **MPU6050:** SDA → GPIO0, SCL → GPIO1, VCC → 3.3V
- **INA228:** SDA → GPIO0, SCL → GPIO1, VIN → 3.3V,
  VIN+ → supply+, VIN- → L298N +12V, VBUS → supply+ (jumper closed; voltage is measured but not fed to the model)
- **JGA25-370 encoder OUT:** → GPIO10 (interrupt, FALLING)
- **L298N:** IN1 → GPIO4, IN2 → GPIO5, ENA jumper ON, common GND
- **E-Stop:** → GPIO9 (to GND when pressed); **Mode switch:** → GPIO8

> ⚠️ ESP32-C3 GPIOs are 3.3 V only. Never connect 5V sensor outputs directly.

> ℹ️ The INA228 replaced an earlier ACS712 + resistor-divider design. See [`docs/wiring.md`](docs/wiring.md) for the current JGA25 wiring and [`docs/phase1_bringup.md`](docs/phase1_bringup.md) (TT-era, archived) for the rationale.

## Results (JGA25-370)

| Metric | Value |
|--------|-------|
| Test accuracy (5-channel, JGA25) | **100%** (117 / 117) — see Phase 11 caveat |
| INT8 accuracy | **100%** (lossless) |
| Model size (INT8) | 5.6 KB |
| Parameters | 963 |
| RAM (tensor arena) | 32 KB |
| Inference time on ESP32-C3 | **27.9 ms (median, n=104)** |
*Measured on ESP32-C3 @ 160 MHz with INT8 TFLite Micro, 50×5 input window,
serial I/O active. Median of 104 consecutive inferences during steady-state
healthy motor operation; variance <50 µs. See `docs/phase12_inference_time.md`.*

> ⚠️ **Honest caveat (Phase 11).** The 100% figure is measured on a second
> 20-second window from the **same capture session** as training — it proves the
> model did not overfit the training window, **not** that it generalizes across
> sessions/days. True cross-session generalization is the target of Phase 14
> (see [`docs/phase11_retrain.md`](docs/phase11_retrain.md)).

### Confusion matrix (JGA25 test set, 117 windows)
Predicted
healthy imbalanced friction
True healthy [ 39 0 0 ]
True imbalanced [ 0 39 0 ]
True friction [ 0 0 39 ]

### The story behind the numbers

This project produced **two** shortcut-learning lessons:

1. **TT era — voltage leak.** A 6-channel model (with supply voltage) hit 92.88%
   offline but classified every healthy motor as FRICTION on hardware — it was
   keying on a 20 mV supply difference, not the faults. Dropping voltage
   (6ch → 5ch) raised accuracy to **96.59%** and made the model robust to supply
   variation. Full case study: [`docs/phase6_deployment.md`](docs/phase6_deployment.md).

2. **TT → JGA25 — mount leak.** The TT-trained model fell to **30.77%** when run
   on the JGA25 rig: healthy↔imbalanced swapped completely, while friction (a
   current-dominant signature) still transferred at ~92%. Changing the motor and
   mount invalidated the learned vibration features. Retraining on JGA25 data
   recovered to **100%** (same-session). Details:
   [`docs/phase11_retrain.md`](docs/phase11_retrain.md).

## Repository Structure
motor-health-edge-ai/
├── data/ # raw (TT + jga25/), processed, synthetic datasets
├── src/
│ ├── training/ # preprocess, train, evaluate, export
│ ├── deployment/ # quantization, header generation
│ ├── inference/ # ESP32-C3 firmware (TFLM)
│ └── common/ # shared Python helpers
├── scripts/ # data logger, utilities, pipeline
├── models/ # checkpoints, tflite, headers, MODEL_LOG.md
├── results/ # figures, reports, logs
├── docs/ # bring-up logs, deployment + phase docs
├── tests/ # unit and parity tests
├── configs/ # sensors.yaml, train.yaml, quant.yaml
└── .github/workflows/ # CI/CD


## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Hardware bring-up | ✅ Done | TT-era bring-up (archived); JGA25 rebuild in Phase 10 |
| Phase 2 — Data collection | ✅ Done | TT: 9 CSVs; JGA25: 9 CSVs @ 12–14 V |
| Phase 3 — Preprocessing | ✅ Done | 50-sample windows, 5 channels (ax, ay, az, current, rpm) |
| Phase 4 — Training | ✅ Done | 1D-CNN, 963 params |
| Phase 5 — Quantization | ✅ Done | INT8 TFLite, lossless, ~5.6 KB |
| Phase 6 — Deployment | ✅ Done | TFLM on ESP32-C3; shortcut-learning fix |
| Phase 7 — Verification | ✅ Done | Extended fault-cycle testing + debouncing |
| Phase 8 — CI/CD | ✅ Done | GitHub Actions |
| Phase 9 — Live visualization | ✅ Done | `plot_live.py` + [`docs/visualization.md`](docs/visualization.md) |
| Phase 10 — JGA25 rebuild + data | ✅ Done | Magnetic-encoder JGA25-370, 12–14 V — [`docs/phase10_jga25.md`](docs/phase10_jga25.md) |
| Phase 11 — Retrain on new hardware | ✅ Done | 30.77% → 100% same-session (cross-session pending) — [`docs/phase11_retrain.md`](docs/phase11_retrain.md) |
| Phase 12a — On-device inference time | ✅ Done | 27.9 ms median — [`docs/phase12_inference_time.md`](docs/phase12_inference_time.md) |
| Phase 12b — MQTT telemetry + dashboard | ✅ Done | Mosquitto + Node-RED, E-Stop/I²t interlocks — [`docs/phase12_mqtt_dashboard.md`](docs/phase12_mqtt_dashboard.md) |
| Phase 13 — State machine + STANDBY | ✅ Done | Debounce, STANDBY/WAITING, E-stop, I²t |
| Phase 14 — Extended fault-cycle testing | ✅ Done | 3 cycles × 3 states |
| Phase 15 — Public write-up | ⬜ Open | LinkedIn post + portfolio update |

## Hardware Bring-up & Data Collection

- **Current (JGA25-370):** [`docs/wiring.md`](docs/wiring.md), [`docs/phase10_jga25.md`](docs/phase10_jga25.md)
- **TT-era bring-up (archived, kept for the lessons):** [`docs/phase1_bringup.md`](docs/phase1_bringup.md)

## What was learned

Building and debugging this project surfaced four engineering lessons that matter for any deployed ML system.

### 1. Feature leakage is invisible offline

A 6-channel model (with supply voltage) reached **92.88% offline accuracy** on held-out test data. Deployed to real hardware, it classified **every healthy motor as FRICTION** — a complete collapse.

Root cause: the model was classifying based on a **20 mV supply voltage difference** between training data (6.02 V) and inference (6.00 V), not on the actual vibration/current signatures. Because the voltage normalizer had a 25 mV standard deviation, this tiny drift amplified to 0.8σ — enough to flip every prediction.

This is a textbook case of **shortcut learning** in industrial ML: the model finds the easiest correlation in the training data, which happens to be a spurious one, and collapses when the environment changes. The **same phenomenon reappeared** when the TT-trained model was moved to the JGA25 rig: the learned vibration features no longer matched the new mount, and accuracy dropped to 30.77% (see [`docs/phase11_retrain.md`](docs/phase11_retrain.md)).

### 2. Removing a bad feature beats adding a good one

After dropping voltage from the input (6ch → 5ch), accuracy **increased** from 92.88% to **96.59%**, and the model became robust to supply-voltage variation. The 3.7-point accuracy gain came from the model spending all of its weights on real physics instead of fitting noise.

The intuition is uncomfortable at first: how can removing a feature *improve* a model? But it's the same reason a decision tree with `n` features outperforms one with `n+1` when the extra feature is pure noise. The feature was carrying variance that fought against the signal.

### 3. INT8 quantization of a small 1D-CNN is effectively free

The shipped 5-channel model:
- Float32: **100%** accuracy (JGA25 test set)
- INT8:    **100%** accuracy (lossless)

Lossless. No accuracy drop, no tuning. This is a general property of small CNNs with well-distributed representative datasets: the INT8 quantization noise is well below the model's decision margin. The same lossless result held for the earlier TT model (96.59% → 96.59%).

The trade-off to worry about isn't quantization accuracy — it's **quantization robustness to distribution shift**. If a model is already on the edge of a decision boundary, INT8 rounding can push it over.

### 4. Deployment verification must include physical conditions

Held-out test splits don't catch distribution shift. The 6-channel model's test accuracy was excellent *because the test split came from the same physical setup as training*. The real validation is running the model on hardware with the same physical conditions that inference will see — different supply voltage, different ambient temperature, different motor speed, different sensor mounting.

**Practical rule:** for every model you ship, validate at least one physical parameter outside the training envelope (voltage ±5%, ambient temperature ±10°C, motor speed ±20%). If the model is sensitive to that parameter, that parameter is a leak — remove it or retrain to be robust to it. Moving from the TT motor to the JGA25-370 (a new motor **and** a new sensor mount) is the canonical proof of this rule.

## Reproducing this project

To reproduce the 5-channel JGA25 model from scratch:

```bash
# 1. Preprocess JGA25 raw CSVs (5 channels, 50-sample windows)
#    data lives in data/raw/jga25/  → point MHE_RAW_DIR at it
MHE_RAW_DIR=data/raw/jga25 python src/training/preprocess.py

# 2. Train the model (~3 min on CPU)
python src/training/train.py

# 3. Export to INT8 TFLite
python scripts/export_v3_tflite.py

# 4. Generate C header for TFLM
python scripts/generate_model_header.py

# 5. Flash the ESP32-C3
cd src/inference && pio run -t upload
```

## Roadmap

    ☑ Phase 1 — Hardware bring-up (ESP32-C3 + MPU6050 + INA228 + L298N) — TT motor
    ☑ Phase 2 — Data collection (9 CSV files across 3 fault classes) — TT motor
    ☑ Phase 3 — Preprocessing (windowing + per-channel standardization)
    ☑ Phase 4 — 1D-CNN training (96.59% test accuracy) — TT motor
    ☑ Phase 5 — INT8 quantization (lossless, 5.6 KB model)
    ☑ Phase 6 — TFLM deployment on ESP32-C3
    ☑ Shortcut-learning diagnosis and fix (voltage → 5-channel model)
    ☑ Phase 7 — Extended verification and state-machine debouncing
    ☑ Phase 8 — CI/CD (GitHub Actions)
    ☑ Phase 9 — Live visualization (plot_live.py + docs/visualization.md)
    ☑ Phase 10 — JGA25-370 hardware rebuild + fresh data collection (12–14 V)
    ☑ Phase 11 — Retrain on new hardware (30.77% → 100%, same-session)
    ☑ Phase 12a — On-device inference time measurement (27.9 ms)
    ☑ Phase 12b — MQTT telemetry + Node-RED dashboard
    ☑ Phase 13 — State-machine debouncing + STANDBY state
    ☑ Phase 14 — Extended fault-cycle testing (3 cycles × 3 states)
    ☐ Phase 15 — LinkedIn post + portfolio update

## Documentation Index

- [`docs/phase1_bringup.md`](docs/phase1_bringup.md) — TT-era hardware bring-up log (archived)
- [`docs/phase6_deployment.md`](docs/phase6_deployment.md) — training, quantization, deployment, and the voltage shortcut-learning case study
- [`docs/phase10_jga25.md`](docs/phase10_jga25.md) — JGA25-370 rebuild + data collection
- [`docs/phase11_retrain.md`](docs/phase11_retrain.md) — TT→JGA25 transfer, retrain, and accuracy recovery
- [`docs/phase12_inference_time.md`](docs/phase12_inference_time.md) — on-device inference timing
- [`docs/phase12_mqtt_dashboard.md`](docs/phase12_mqtt_dashboard.md) — MQTT telemetry + Node-RED dashboard
- [`docs/wiring.md`](docs/wiring.md) — current JGA25-370 wiring
- [`docs/visualization.md`](docs/visualization.md) — live inference monitor

### Guides

- [`ML_info/`](ML_info/) — two companion documents:
  - [`ML_Guide_for_Motor_Health.pdf`](ML_info/ML_Guide_for_Motor_Health.pdf) — 10-page technical walkthrough of this build (architecture choice, quantisation, the leakage case study)
  - [`ML_Primer_for_Beginners.pdf`](ML_info/ML_Primer_for_Beginners.pdf) — 19-page illustrated ML primer taught from zero, using this project as the running example

