# Phase 1 Bring-up Log

## Step 1 — Serial / USB-CDC — PASS
- Firmware: `src/inference/src/main.cpp`
- Observed: CSV header + 1 Hz rows, RPM counter incremented cleanly.
- Note: ESP32-C3 SuperMini requires `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1`.

## Step 2 — Voltage divider — PASS (calibrated) [SUPERSEDED in Step 3]

> **Note:** This section documents the divider's bring-up and calibration
> as it was used in Phase 1 Step 2. In Step 3, the INA228 replaced both
> the ACS712 and the divider. The divider hardware has been removed.
> This section is retained for historical record and as evidence of
> the original validation methodology.

### Original hardware (now removed)
- R1 = 100 kΩ, R2 = 20 kΩ → DIV_FACTOR = 6.000
- Divider from L298N +12V to GND, midpoint → GPIO3

### Original calibration methodology
[rest of Step 2 content as written]

### Why the divider was removed
The INA228 measures both current (internal shunt) and voltage (VBUS pin)
over I2C, with ±0.05% accuracy and zero ADC-pin dependency. Keeping the
divider would:
- Waste GPIO3 (a scarce resource on the C3)
- Add analog noise on a signal we no longer need
- Clutter the physical wiring

The divider is stored and may be re-used if a second voltage channel
(e.g., motor terminal voltage after the L298N's drop) is ever needed.

## Reusable engineering knowledge (from Step 2)

ESP32-C3 ADC does not have a precise 3.3 V reference. Empirical measurements
on this specific board showed +7.4% error at 6 V and +9.9% at 9 V (before
calibration). This is documented in the ESP32-C3 datasheet as 5–10%
tolerance and varies chip-to-chip.

**Implication for future designs:** any analog sensor on the C3 requires
either (a) per-board empirical calibration, or (b) a digital sensor like
the INA228 that does its own ADC internally with factory calibration.
For this project, we chose (b) for current/voltage, and there are no
remaining analog channels to calibrate.
  
  ## Step 3 — INA228 current + voltage sensor — PASS

### Hardware
- Adafruit INA228 breakout (PID 5832), 20-bit ADC, 15 mΩ internal shunt
- I2C address 0x40, shares bus with MPU6050 (SDA=GPIO0, SCL=GPIO1)
- Logic supply `VIN` from ESP32 3.3V (NOT 5V)
- High-side measurement: supply (+) → `VIN+` → shunt → `VIN-` → L298N +12V
- `VBUS` tied to `VIN+` for bus voltage sensing

### Sensor selection rationale (design decision)
Switched from ACS712-05B to INA228 for the following reasons:

| Aspect | ACS712-05B | INA228 (chosen) |
|---|---|---|
| Output | Analog (VCC/2 ± swing) | Digital I2C |
| ESP32-C3 ADC compatibility | 5V output saturates 3.3V ADC | No ADC pin needed |
| Resolution | ~12-bit via ESP32 ADC | 20-bit onboard Δ-Σ |
| Accuracy | ±1.5% typical | ±0.05% gain, ±1µV offset |
| Calibration | Manual zero + sensitivity | Digital calibration registers |

Root cause of switch: ACS712 5V-powered output (2.5V quiescent) exceeded
the ESP32-C3's reliable ADC range, producing saturated readings (~16428).
INA228 eliminates the ADC entirely — measurement is done digitally.

### Configuration
- Shunt resistance: 0.015 Ω (on-board, do not change in code)
- Max current: 3.0 A
- Averaging: 16 samples

### Zero-current baseline (motor OFF, L298N inputs LOW)
- Firmware average: **−0.36 mA**
- Jitter: ±0.04 mA (1σ)
- Interpretation: within 2 LSB of true zero. The negative sign indicates
  L298N is fully off (no quiescent draw) and reflects INA228's small
  unipolar offset. This baseline will be subtracted in Python preprocessing
  (Phase 2), not in firmware — keeps raw data honest.

### Bus voltage validation
- Firmware: **9.013 V** (stable to ±0.001 V)
- DMM on supply: ~9.0 V
- Delta: <0.02 V (0.2%) — within INA228's ±0.05% spec

### Motor-on test (to be completed in Step 6)
Motor was not yet enabled during this test. Sensitivity verification will
be performed during full-system capture (Step 6) with expected current
range 150–500 mA at no-load, 1–2 A under load.

### Notes for Phase 2 preprocessing
- Subtract zero baseline: `current_corrected = current_mA − (−0.36)`
- Or, alternatively, compute per-window mean and subtract (removes baseline
  and slow drift simultaneously). This is the preferred approach for
  standardization.
  
  
  ## Step 4 — MPU6500 (MPU6050 clone) — PASS

### Sensor identification
- I2C scanner: device at 0x68 ✅
- WHO_AM_I register (0x75): **0x70**, not 0x68
- Conclusion: module is MPU6500 clone, common in cheap GY-521 boards

### Library decision
- Adafruit MPU6050 library rejects WHO_AM_I ≠ 0x68 during init
  → swapped to FastIMU library (explicitly supports MPU6500)
- Configuration: MPU6500 class, address 0x68, ±8 g range, 50 Hz sample rate

### Unit handling
- FastIMU returns acceleration in g units (not m/s²)
- Firmware multiplies by 9.81 before printing → CSV matches
  configs/sensors.yaml (unit: m_s2)
- Verified: flat board reads az ≈ 9.8 m/s² (≈ 1.0 g) ✅

### Validation
| Test | Expected | Observed |
|---|---|---|
| Boot init | no error | ✅ |
| Flat board, Z axis | ~9.8 m/s² | ~9.9 m/s² |
| Tilt 90° | gravity redistributes smoothly | ✅ |
| Tap | brief spike, settles <200 ms | ✅ |

### Notes for Phase 2
- MPU6500 has the same accel/mag/gyro register map as MPU6050 for
  the axes we use
- ±8 g range gives ±0.244 mg/LSB resolution — sufficient for vibration
  fault signatures expected in imbalance/friction classes
- FastIMU's `update()` must be called before `getAccel()` — noted


  ### Power Budget & Risk Mitigation
- ESP32-C3 SuperMini 3.3V LDO has a practical thermal limit of ~150-250mA.
- Current sensor load (MPU6050 ~4mA, INA228 ~1mA, IR ~10mA) is within limits.
- **Risk:** Motor noise or future sensor additions could exceed LDO capacity, causing I2C bus failures.
- **Mitigation (for final capture):** Consider a dedicated 3.3V buck converter (e.g., MP1584) fed from the 9V rail to power all sensors, keeping the ESP32 LDO for the MCU only.

## Step 5 — IR speed sensor — PASS

### Hardware
- LM393 optical sensor + circular disk with 20 holes
- DO → GPIO10, RISING edge, 1 ms software debounce
- VCC=3.3V

### Validation (motor-driven, 9V through INA228 → L298N)
- 30-second continuous run
- pulses/sec: ~175 (stable ±2)
- rpm: ~525 (stable ±3)
- jitter: ±0.4% — comparable to commercial tachometers
- total count grew monotonically with zero glitches

### Key finding: hand-rotation was misleading
- Hand rotation: bursts of 5-200 pulses/rev (chatter artifact)
- Motor-driven: clean 20 pulses/rev
- Root cause of hand noise: mechanical wobble, not electrical
- Design principle established: validate sensors under operating
  conditions, not by hand

### Anomaly to resolve
- Expected RPM at 7.6V (9V - L298N 1.4V drop): ~255 RPM
- Observed: ~525 RPM (2.06× expected)
- Candidate causes:
    (a) Different gear ratio (e.g., 1:24 instead of 1:48)
    (b) Higher-voltage motor spec than cheap TT
- Resolution: not required for fault classification (relative stability
  matters, not absolute accuracy). Document actual motor as observed.

---

## Status summary

| Step | Sensor | Status |
|---|---|---|
| 1 | USB-CDC | PASS |
| 2 | Voltage divider | SUPERSEDED by INA228 |
| 3 | INA228 | PASS |
| 4 | MPU6500 | PASS |
| 5 | IR encoder | PASS |
| 6 | Full combined capture | IN PROGRESS |

### Next: Step 6
Log all 5 channels at 50 Hz simultaneously. Then run the 3-class data
collection protocol (healthy / imbalanced / friction), 3-5 runs per class,
30-60s each.