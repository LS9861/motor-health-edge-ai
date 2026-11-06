# Phase 10 — JGA25-370 Data Collection

## How to reproduce the training data

Raw CSVs are **not** committed (see `.gitignore`). To regenerate:

1. Flash `src/inference/src/collect_raw.cpp` (rename `main.cpp` → `main.cpp.disabled` first)
2. Open `data/raw/jga25/` — create if missing
3. For each of the 9 captures, follow this protocol:

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