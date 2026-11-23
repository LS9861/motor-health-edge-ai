# Phase 10 — JGA25-370 Rebuild & Data Collection

## What changed vs the TT motor

The project originally used a small **TT DC gear motor** with a separate LM393
reflective sensor on a 20-hole disk (see [`phase1_bringup.md`](phase1_bringup.md),
archived). Phase 10 rebuilt the rig around a **JGA25-370 geared motor**:

- **Motor:** JGA25-370 with a **built-in magnetic encoder** (replaces the TT motor
  + external reflective disk). The encoder pulse train feeds GPIO10.
- **Mount:** the MPU6050 was re-mounted on the new gearbox — this mount change is
  the root cause of the TT→JGA25 transfer failure documented in
  [`phase11_retrain.md`](phase11_retrain.md).
- **Supply:** **12–14 V** for all real captures. The earlier ~6 V was only a
  bench sanity-check, never training data.

## How to reproduce the training data

Raw CSVs are **not** committed (see `.gitignore`). To regenerate:

1. Flash `src/inference/src/collect_raw.cpp` (rename `main.cpp` → `main.cpp.disabled` first)
2. Open `data/raw/jga25/` — create if missing
3. For each of the 9 captures, follow this protocol (run the motor at **12–14 V**):

| File | Fault setup |
|---|---|
| `healthy_1..3.csv` | Stock JGA25-370, no added mass, no added load |
| `imbalanced_1..3.csv` | Small washer (~3 g) taped off-center to output shaft |
| `friction_1..3.csv` | Finger pressed on shaft OR load strap — motor visibly slowed |

4. For each capture:
   - Reset ESP32 (RST button)
   - Flip motor ON, wait 5 s
   - `python scripts/collect_csv.py <label> <n>`
   - Press Enter when prompted, wait 20 s
   - Flip motor OFF, wait 5 s
   - Repeat

## Captured data summary (for the committed results)

Confirmed at collection time:
- 9 files, 1000 rows each, at 50 Hz = 20 s per capture
- Healthy/imbalanced: rpm ≈ 274, current ≈ 127 mA
- Friction: rpm ≈ 245, current ≈ 320 mA
- Imbalanced: az_std ≈ 0.37 (4.4× healthy) — the imbalance vibration signature
- Healthy: az_std ≈ 0.086

Run `python scripts/check_jga25_data.py` to verify these numbers if re-collecting.