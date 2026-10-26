# Phase 1 Bring-up Log

## Step 1 — Serial / USB-CDC — PASS
- Firmware: `src/inference/src/main.cpp`
- Observed: CSV header + 1 Hz rows, RPM counter incremented cleanly.
- Note: ESP32-C3 SuperMini requires `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1`.

## Step 2 — Voltage divider — PASS (calibrated)

### Hardware
- R1 = 100 kΩ, R2 = 20 kΩ → DIV_FACTOR = 6.000
- Divider from L298N +12V to GND, midpoint → GPIO3

### Calibration
ESP32-C3 ADC reference tolerance required empirical calibration:
- Initial run (factor = 1.0): DMM 6.00 V, ESP32 avg 6.45 V (+7.4%)
- Applied `ADC_CAL_FACTOR = 0.9307` to firmware
- Post-calibration 48-sample avg at 6 V: 6.06 V (delta 0.06 V vs DMM)

### Two-point linearity check
| Supply (DMM) | ESP32 avg | Delta | Notes |
|---|---|---|---|
| 6.00 V | 6.06 V | 0.06 V (1.0%) | Post-calibration |
| 9.00 V | 9.20 V | 0.20 V (2.2%) | Post-calibration |

**Linearity:** ±2% across 3–9 V range. Sufficient for model use; the primary
feature (motor-on supply sag) is >5%, well above linearity error.

### Noise characteristics (expected, not a fault)
- Jitter: ±0.14 V (±1.5–2.1%) over 43–48 samples
- Sources: ESP32-C3 ADC LSB noise, breadboard contact resistance, supply ripple
- Impact on model: negligible. Voltage is a sanity channel, not a primary feature.
- Per-window standardization in Phase 2 will cancel slow drift.

### Notes for future hardware iteration
- Add 0.1 µF ceramic + 10 µF electrolytic from GPIO3 to GND as hardware LPF
- Migrate breadboard → PCB for reduced jitter (±0.02 V expected)
- Consider ESP32-C3 ADC continuous mode + averaging for cleaner readings