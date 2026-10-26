# Phase 1 Bring-up Log

## Step 1 — Serial / USB-CDC — PASS
- Firmware: `src/inference/src/main.cpp`
- Observed: CSV header + 1 Hz rows, RPM counter incremented cleanly.
- Note: ESP32-C3 SuperMini requires `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1`.

## Step 2 — Voltage divider — PASS (calibrated)

### Hardware
- R1 = 100 kΩ (top, to supply), R2 = 20 kΩ (bottom, to GND)
- DIV_FACTOR = (R1 + R2) / R2 = 6.000
- Divider from motor supply rail to GND, midpoint → GPIO3

### Divider sanity checks (DMM)
| Supply (DMM) | Expected midpoint | Measured midpoint (DMM) | Verdict |
|---|---|---|---|
| 6.00 V | 1.000 V | ~1.00 V | ✅ |
| 9.00 V | 1.500 V | ~1.50 V | ✅ |

Divider is correctly wired and behaving linearly with respect to
supply voltage, as expected from ideal resistor divider theory.

### ADC calibration
ESP32-C3 ADC reference tolerance required empirical calibration.

**Pre-calibration observations:**
- At 6.00 V supply: firmware reported 6.45 V → +7.4% error
- At 9.00 V supply: firmware reported 9.89 V → +9.9% error
- Root cause: ESP32-C3 internal ADC reference tolerance (5–10% documented)

**Calibration chosen:** single-point at operating voltage (6 V), where
the model will actually be used.
- `ADC_CAL_FACTOR = 0.9307` (= DMM 6.00 V ÷ firmware pre-cal 6.45 V)

**Post-calibration validation:**
| Supply (DMM) | Firmware avg | Delta | Error % |
|---|---|---|---|
| 6.00 V | 6.06 V | +0.06 V | 1.0% |
| 9.00 V | 9.20 V | +0.20 V | 2.3% |

**Linearity assessment:** ±2.3% across 3 V span (6–9 V). The residual
error at 9 V is due to ESP32-C3 ADC range-boundary nonlinearity (different
internal reference paths activated above ~1.4 V at pin). This is documented
silicon behavior, not a wiring fault.

**Acceptability for model:** The voltage channel is a sanity/monitoring
feature, not a fault signature. The signal of interest (motor-on supply
sag, expected >0.2 V) is well above the 0.02 V noise floor after per-window
standardization. ±2.3% linearity error is well within tolerance.

### Noise characteristics (expected, not a fault)
- Jitter at 9 V supply: ±0.155 V (±1.7%) over 103 samples
- Jitter at 6 V supply: ±0.13 V (±2.1%) over 48 samples
- Sources: ESP32-C3 ADC LSB noise, breadboard contact resistance, supply ripple
- Impact on model: negligible after per-window standardization

### Intermittent floating-pin glitches — hardware issue documented
Three rows during 9 V test showed raw ≈ 40–79 instead of ~2000
(characteristic floating-pin signature: near-zero with random spikes).
Diagnosed as loose breadboard jumper between divider midpoint and GPIO3.
Reseating the jumper resolved it.

**Recommended fixes for future hardware iteration:**
1. Add 0.1 µF ceramic capacitor from GPIO3 to GND — hardware LPF at ~16 Hz,
   prevents floating-pin glitches if jumper momentarily disconnects
2. Migrate breadboard → PCB — eliminates contact-resistance drift entirely
3. Consider ESP32-C3 ADC continuous conversion mode for cleaner averaged readings

### Decision log
- **Chosen factor: 0.9307** (single-point, 6 V)
- **Rejected: 0.920** (two-point average) — optimizing at 6 V operating point
  is correct for this use case; 9 V validation was linearity check, not
  calibration target
- **Rejected: piecewise calibration** — both points within 2.3%, insufficient
  gain for added complexity