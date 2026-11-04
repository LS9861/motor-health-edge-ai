"""Single source of truth for shared constants across the pipeline.

Import these instead of hardcoding channel names, label lists, or colors
in individual scripts. If any of these values change, change them here only.
"""

# Raw CSV columns emitted by firmware and written by log_data.py / plot_live.py.
# Order MUST match the firmware's Serial.println line and log_data.py's header.
CSV_COLUMNS = [
    "timestamp_ms",
    "ax",
    "ay",
    "az",
    "current_mA",
    "voltage_v",
    "rpm",
]

# Model input channels (Phase 6): voltage_v intentionally excluded.
# 5-channel model — see docs/phase6_deployment.md for why voltage was dropped.
MODEL_CHANNELS = ["ax", "ay", "az", "current_mA", "rpm"]

# Backwards-compatible alias for scripts that still expect CHANNELS.
CHANNELS = MODEL_CHANNELS

# Fault class labels
LABELS = ["healthy", "imbalanced", "friction"]

# Plot colors per class (used by plot_live and plot_offline)
LABEL_COLORS = {
    "healthy":    "#2ca02c",   # green
    "imbalanced": "#ff7f0e",   # orange
    "friction":   "#d62728",   # red
}

# Samples per second (must match firmware SAMPLE_PERIOD_MS = 20)
SAMPLE_HZ = 50

# Number of samples shown in the live plot window (10 s at 50 Hz)
LIVE_WINDOW_SAMPLES = 500

# Serial baud rate — MUST match firmware and log_data.py
BAUDRATE = 115200

# Number of fields in one CSV row (excluding the 'label' column we append)
EXPECTED_CSV_FIELDS = len(CSV_COLUMNS)  # 7