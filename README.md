# motor-health-edge-ai

Edge AI motor health monitoring on ESP32-C3 with TFLM.

## Project Overview

This project collects vibration, current, voltage, and speed signals from a TT DC gear motor, trains a 1D-CNN classifier, quantizes it to INT8 TFLite, and deploys it on an ESP32-C3 using TensorFlow Lite Micro.

**Target classifications:** healthy, imbalanced, friction/wear.

## Hardware

| Component | Role |
|-----------|------|
| ESP32-C3 SuperMini | MCU with Wi-Fi/BLE, 4MB flash |
| MPU6050 | 3-axis accelerometer (vibration) |
| ACS712 | Motor current sensing |
| Resistor divider | Motor supply voltage sensing |
| IR reflective sensor | Motor speed (RPM) |
| TT DC gear motor | Target motor |
| L298N | Motor driver |

### Wiring Summary

- **MPU6050:** SDA → GPIO0, SCL → GPIO1, VCC → 3.3V
- **ACS712:** OUT → GPIO2, VCC → 3.3V (or use a divider if 5V)
- **Voltage divider:** midpoint → GPIO3
- **IR sensor:** OUT → GPIO10
- **L298N:** IN1 → GPIO4, IN2 → GPIO5, ENA jumper ON, common GND

> ⚠️ ESP32-C3 GPIOs are 3.3V only. Never connect 5V sensor outputs directly.

## Repository Structure
motor-health-edge-ai/
├── data/ # raw, processed, synthetic datasets
├── src/
│ ├── training/ # preprocess, train, evaluate, export
│ ├── deployment/ # quantization, header generation
│ ├── inference/ # ESP32-C3 firmware (TFLM)
│ └── common/ # shared Python helpers
├── scripts/ # data logger, utilities
├── models/ # checkpoints, onnx, tflite, headers
├── results/ # figures, reports, logs
├── docs/ # schematics, datasheets, model card
├── tests/ # unit and parity tests
├── configs/ # train.yaml, quant.yaml, sensors.yaml
└── .github/workflows/ # CI/CD


## Phase 1: Data Collection

### 1. Flash Firmware

Open `src/inference/main/main.cpp` (or `firmware/motor_logger/motor_logger.ino` if using Arduino IDE) and flash to the ESP32-C3.

Dependencies: `Adafruit MPU6050`, `Adafruit Unified Sensor`.

### 2. Calibrate ACS712 Zero Point

With the motor stopped, open Serial Monitor (115200 baud). Note the `current_a` value. Adjust `ACS712_ZERO_V` in the firmware until it reads near `0.000`.

### 3. Log Data

```bash
pip install pyserial
python scripts/log_data.py healthy

Run for 30–60 seconds. Repeat for imbalanced and friction states.
4. Safety Notes

    Do not stall the motor for extended periods.

    Keep L298N heatsinked or ventilated.

    Let the motor rest between runs.

    Use a separate motor supply if possible; common ground is mandatory.

Roadmap

    ☑ Phase 1: Hardware bring-up and data collection
    □  Phase 2: Preprocessing and windowing
    □  Phase 3: 1D-CNN training and evaluation
    □  Phase 4: INT8 quantization and TFLM deployment
    □  Phase 5: On-device inference and CI/CD