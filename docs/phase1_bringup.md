# Phase 1 — Hardware Bring-up Log

Project: motor-health-edge-ai
Hardware: ESP32-C3 SuperMini, MPU6500 (GY-521), INA228, LM393 + 20-hole disk, TT DC gearmotor, L298N
Supply: 6.0 V, bench PSU current-limited to 1.5 A

---

## Step 1 — Serial / USB-CDC — PASS

- Firmware flashed via PlatformIO to ESP32-C3 SuperMini.
- CSV header + 1 Hz rows observed in Serial Monitor.
- Required build flags: `-DARDUINO_USB_MODE=1`, `-DARDUINO_USB_CDC_ON_BOOT=1`
  (without these, Serial goes to a nonexistent UART and Monitor stays silent).

---

## Step 2 — Voltage divider — SUPERSEDED

- Original design: R1 = 100 kΩ, R2 = 20 kΩ on the motor supply, midpoint → GPIO3.
- ESP32-C3 ADC reference tolerance required empirical calibration
  (`ADC_CAL_FACTOR = 0.9307` at 6 V; ~2.3 % linearity error at 9 V).
- **Superseded in Step 3**: INA228 provides bus-voltage measurement digitally,
  eliminating the ADC and its calibration entirely.
- The divider was removed from the final firmware.

---

## Step 3 — INA228 current + voltage — PASS

### Hardware
- Adafruit INA228 (PID 5832), 20-bit Δ-Σ, on-board 15 mΩ shunt
- I2C address 0x40 (shares bus with MPU6500)
- Logic supply `VIN` from ESP32 3.3 V (not 5 V)
- High-side measurement: supply (+) → `VIN+` → shunt → `VIN-` → L298N `+12V`
- `VBUS` tied to `VIN+` (jumper closed) for bus-voltage sensing

### Design decision — ACS712 → INA228
The original plan used an ACS712-05B. Problem discovered during bring-up:
the ACS712's quiescent output is VCC/2 (2.5 V at 5 V supply, 1.65 V at
3.3 V). When powered from 5 V, the output exceeds the ESP32-C3's reliable
ADC range, producing saturated readings (~16428). Working around it with
a voltage divider would add error.

**Chosen solution**: switch to the INA228, which reports current and
voltage digitally over I2C. ADC constraints disappear; resolution is
20-bit; accuracy is ±0.05 % gain.

### Zero-current baseline (motor OFF, L298N inputs LOW)
- Firmware average: **−0.36 mA**
- Jitter: ±0.04 mA (1σ)
- Within 2 LSB of true zero. Baseline subtracted in Phase 2 preprocessing.

### Bus voltage validation
- Firmware: **9.013 V** (stable to ±0.001 V) at 9 V supply
- DMM: ~9.0 V → delta <0.02 V

---

## Step 4 — MPU6050 / MPU6500 vibration — PASS

### Sensor identification
- I2C scanner: device responds at 0x68 ✅
- `WHO_AM_I` register (0x75) returned **0x70** → MPU6500 clone
  (common in cheap GY-521 boards)
- Adafruit MPU6050 library rejects clones; **switched to FastIMU**, which
  explicitly supports MPU6500.

### Configuration
- MPU6500 via FastIMU, ±8 g range, 21 Hz LPF, 50 Hz sample rate
- Units: FastIMU returns g; firmware multiplies by 9.81 → m/s²

### Validation
| Test | Expected | Observed |
|---|---|---|
| Boot init | no error | OK |
| Flat board, Z axis | ~9.81 m/s² | az ≈ 9.93 |
| Magnitude √(ax²+ay²+az²) | 9.4–10.2 | 10.37 (5 % over, in spec) |
| Tilt response | smooth redistribution | ✅ |
| Jitter (static) | <0.1 m/s² | ~0.03 |

### Mount
- Sensor glued to the top of the yellow TT-motor gearbox for direct
  mechanical coupling (documented for Phase 6 reproducibility).

---

## Step 5 — IR speed sensor — PASS (with documented limitation)

### Hardware
- LM393 optical sensor + circular disk (20 holes)
- `DO` → GPIO10, RISING edge interrupt, 1 ms software debounce

### Hand-rotation vs motor-driven (key finding)
- **Hand rotation**: 8–11× pulses per hole (comparator chatter)
- **Motor-driven**: 20 pulses/rev clean, ±2 RPM jitter

**Conclusion**: hand testing was invalid. The sensor and firmware were
always correct; the noise was mechanical (hand wobble). Validate sensors
under their operating conditions.

### Motor-driven validation
- 30-second continuous run at 6 V supply
- Pulses/sec: ~175 stable
- RPM: ~525 stable (±3), jitter ±0.4 %

### Anomaly — expected vs observed RPM
- Expected at 7.6 V effective (9 V minus L298N drop): ~255 RPM
- Observed: ~525 RPM (~2× expected)
- Suspected cause: gear ratio variant (1:24 instead of 1:48) **or**
  disk has 40 holes, not 20
- **Not blocking** — recorded for the model card; absolute RPM value does
  not affect the fault classifier, only the relative stability

---

## Step 6 — Full system capture — PASS

### Capture protocol
- 9 captures total, 3 per class: `healthy`, `imbalanced`, `friction`
- 6.0 V supply, current-limited at 1.5 A
- Each capture: ~50–65 s wall clock (10 s pre-motor wait, 30 s motor-on,
  remainder spin-down and post-stop)
- 2436–3197 rows per CSV, 50 Hz sampling

### Fault definitions
- **healthy**: stock motor, no modification
- **imbalanced**: 1-cent coin taped to the non-encoder shaft
- **friction**: cardboard pressed gently against the shaft, no coin
  (one file `friction_imbalanced_*.csv` was accidentally captured with
  both fault types; **excluded from training** and moved to
  `data/raw/archive/`)

### Raw data quality
- Zero nulls across all 9 CSVs
- Monotonic `timestamp_ms`
- No dropped I2C reads
- 100 % of rows valid for windowing

---

## Cross-cutting: RPM channel dropped in Phase 2

### Observation
After per-window Z-score standardization, per-channel std on the training
set was 1.0000 for ax/ay/az/current/voltage, but **0.7037 for rpm**.

### Root cause
The firmware computes RPM once per **1000 ms window** (1 Hz). The CSV
sampling rate is 50 Hz. Each 100-sample window (2 s at 50 Hz) therefore
contains at most **2 distinct RPM values**, and 92 % of windows contain a
single constant value.

After per-window Z-score, constant windows normalize to all zeros;
transition windows normalize to a small step. The channel carries
essentially no information for a CNN at this temporal scale.

### Decision
- **Phase 3 (current)**: exclude `rpm` from `FEATURE_COLS`.
  Model trains on 5 channels: ax, ay, az, current_mA, voltage_v.
- **Phase 4**: add window-level `mean_rpm` as a scalar feature, concatenated
  after the CNN. No recapture needed; uses data already in the CSVs.
- **Phase 5+**: modify firmware to sample RPM at 50 Hz, recapture dataset,
  train a v3 model, and report accuracy delta vs v1.

### Impact
RPM is not a primary fault signature for imbalance or friction at 1 Hz.
Excluding it is a defensible engineering trade-off for the prototype.
The decision, the reasoning, and the roadmap to re-introduce RPM are
documented in `models/MODEL_LOG.md`.

---

## Final hardware state (as of end of Phase 1)

| Component | Connection | Notes |
|---|---|---|
| MPU6500 | SDA=GPIO0, SCL=GPIO1, VCC=3.3 V | Glued to motor housing |
| INA228 | SDA=GPIO0, SCL=GPIO1, VIN=3.3 V, VIN+/VBUS=supply+, VIN−=L298N +12V | High-side measurement |
| LM393 | DO=GPIO10, VCC=3.3 V | 20-hole disk, disk-side shaft |
| L298N | IN1=GPIO4, IN2=GPIO5, ENA jumper ON | 6 V motor supply via INA228 |
| ESP32-C3 | USB-C power + data | Single-board operation |

---

## Phase 1 → Phase 2 handoff

- Raw CSVs: `data/raw/*.csv` (8 files; 1 archived)
- Preprocessing: `src/training/preprocess.py`
  - Window: 100 samples (2 s), step 50 (50 % overlap)
  - Per-window Z-score normalization
  - Split by file: 2 train / 1 test per class
  - Features: ax, ay, az, current_mA, voltage_v (5 channels)
- Processed outputs: `data/processed/{X_train,y_train,X_test,y_test}.npy`
- Shapes: X_train (313, 100, 5), X_test (159, 100, 5)

---

## Lessons learned (carry into Phase 3+)

1. **Bring up sensors one at a time.** Every bug we hit (ADC saturation,
   MPU clone, encoder chatter) would have been masked if all six channels
   were live on the first power-on.
2. **Validate under operating conditions, not by hand.** Hand-rotating the
   encoder showed 8–11× noise that vanished entirely under motor drive.
3. **Document trade-offs as you make them.** The ACS712 → INA228 switch
   and the RPM drop were both judgment calls; without the log, they'd
   look like bugs to a future reader.
4. **Absolute values matter less than relative stability.** The RPM
   reading (~525) may not match the TT-motor datasheet, but it is stable
   to ±0.4 %, which is what the classifier needs.