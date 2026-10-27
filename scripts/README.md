# scripts/

Host-side utilities for **motor-health-edge-ai**. These run on the PC (not the ESP32-C3) and support data collection, calibration, and pipeline automation.

## `log_data.py` — CSV logger

Reads the CSV stream emitted by the ESP32-C3 firmware over USB-CDC serial and writes it to `data/raw/<label>_<timestamp>.csv`.

### Usage

```bash
python scripts/log_data.py <label>