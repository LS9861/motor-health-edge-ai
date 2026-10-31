#!/usr/bin/env python3
"""
Phase 5.2 — Verify INT8 TFLite accuracy vs float32.

Expected result: INT8 accuracy within 1-2% of float32 (96.2%).
"""

import numpy as np
import tensorflow as tf
from pathlib import Path
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
TFLITE_PATH = REPO_ROOT / "models" / "tflite" / "v2_motor_health_int8.tflite"

LABELS = ["healthy", "imbalanced", "friction"]


# --- Load TFLite interpreter ---
interp = tf.lite.Interpreter(model_path=str(TFLITE_PATH))
interp.allocate_tensors()

input_details = interp.get_input_details()
output_details = interp.get_output_details()

print("Input details:")
for d in input_details:
    print(f"  {d['name']}: shape={d['shape']}, dtype={d['dtype']}")
print("Output details:")
for d in output_details:
    print(f"  {d['name']}: shape={d['shape']}, dtype={d['dtype']}")


# --- Load test data ---
X_test = np.load(PROCESSED_DIR / "X_test.npy").astype(np.float32)   # (N, T, C)
rpm_test = np.load(PROCESSED_DIR / "mean_rpm_test.npy").astype(np.float32)
y_test = np.load(PROCESSED_DIR / "y_test.npy")

# Normalize rpm with train statistics
rpm_train = np.load(PROCESSED_DIR / "mean_rpm_train.npy").astype(np.float32)
rpm_mean = float(rpm_train.mean())
rpm_std = float(rpm_train.std()) or 1.0
rpm_test = (rpm_test - rpm_mean) / rpm_std


# --- Input quantization params ---
# INT8 inputs need to be quantized using the input scale/zero_point.
ts_input = input_details[0]
rpm_input = input_details[1]
ts_scale, ts_zero = ts_input["quantization"]
rpm_scale, rpm_zero = rpm_input["quantization"]

# Output dequantization
out_scale, out_zero = output_details[0]["quantization"]


# --- Run inference on every test sample ---
preds = []
for i in range(len(X_test)):
    # Layout: TFLite expects (batch, channels, timesteps) per our export
    x_ts = X_test[i][None, :, :].transpose(0, 2, 1).astype(np.float32)  # (1, C, T)
    x_rpm = rpm_test[i][None, None].astype(np.float32)                  # (1, 1)

    # Quantize inputs to INT8
    x_ts_q = (x_ts / ts_scale + ts_zero).astype(np.int8)
    x_rpm_q = (x_rpm / rpm_scale + rpm_zero).astype(np.int8)

    interp.set_tensor(ts_input["index"], x_ts_q)
    interp.set_tensor(rpm_input["index"], x_rpm_q)
    interp.invoke()

    logits = interp.get_tensor(output_details[0]["index"])
    logits_deq = (logits.astype(np.float32) - out_zero) * out_scale
    preds.append(int(np.argmax(logits_deq)))

preds = np.array(preds)


# --- Report ---
acc = accuracy_score(y_test, preds)
cm = confusion_matrix(y_test, preds)
report = classification_report(y_test, preds, target_names=LABELS, zero_division=0)

print(f"\nINT8 TFLite test accuracy: {acc:.4f}  (float32 was 0.9623)")
print(f"Confusion matrix:\n{cm}")
print(f"\nClassification report:\n{report}")

delta = acc - 0.9623
print(f"\nAccuracy delta vs float32: {delta:+.4f}")
if delta >= -0.02:
    print("PASS: quantization drop < 2%")
else:
    print("WARN: significant quantization accuracy drop. Investigate representative dataset.")