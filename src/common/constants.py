# src/common/constants.py
CHANNELS = ["ax", "ay", "az", "current_mA", "rpm"]
LABELS = ["healthy", "imbalanced", "friction"]
LABEL_COLORS = {
    "healthy":    "#2ca02c",
    "imbalanced": "#ff7f0e",
    "friction":   "#d62728",
}
SAMPLE_HZ = 50