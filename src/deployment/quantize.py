#!/usr/bin/env python3
"""
Phase 5.1 — Export v2 to ONNX, convert to SavedModel via onnx2tf,
then quantize SavedModel -> INT8 TFLite.
"""

import numpy as np
import torch
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CKPT_PATH = REPO_ROOT / "models" / "checkpoints" / "v2_5ch_mean_rpm.pt"
ONNX_DIR = REPO_ROOT / "models" / "onnx"
TFLITE_DIR = REPO_ROOT / "models" / "tflite"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
ONNX_DIR.mkdir(parents=True, exist_ok=True)
TFLITE_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(REPO_ROOT / "src" / "training"))
from model import MotorCNN1DWithRPM

# --- Step 1: Load trained model ---
print("[1/4] Loading trained model...")
model = MotorCNN1DWithRPM(in_channels=5, n_classes=3)
model.load_state_dict(torch.load(CKPT_PATH, map_location="cpu"))
model.eval()

# --- Step 2: Export to ONNX ---
print("[2/4] Exporting to ONNX...")
x_ts_dummy = torch.randn(1, 5, 100)
x_rpm_dummy = torch.randn(1, 1)

onnx_path = ONNX_DIR / "v2_motor_health.onnx"
torch.onnx.export(
    model,
    (x_ts_dummy, x_rpm_dummy),
    str(onnx_path),
    input_names=["x_ts", "x_rpm"],
    output_names=["logits"],
    dynamic_axes={"x_ts": {0: "batch"}, "x_rpm": {0: "batch"}, "logits": {0: "batch"}},
    opset_version=17,   # <-- bumped from 13
    do_constant_folding=True,
)
print(f"      Saved: {onnx_path}")

# --- Step 3: ONNX -> SavedModel via onnx2tf (with the -osd flag equivalent) ---
print("[3/4] Converting ONNX -> SavedModel (onnx2tf)...")
import onnx2tf

saved_model_dir = ONNX_DIR / "v2_saved_model"
onnx2tf.convert(
    input_onnx_file_path=str(onnx_path),
    output_folder_path=str(saved_model_dir),
    non_verbose=True,
    flatbuffer_direct_output_saved_model=True,   # <-- forces saved_model.p
)
print(f"      Saved: {saved_model_dir}")

# Verify the .pb file exists before proceeding
pb_file = saved_model_dir / "saved_model.pb"
if not pb_file.exists():
    raise SystemExit(
        f"ERROR: SavedModel .pb not found at {pb_file}. "
        f"onnx2tf did not produce a SavedModel. Check the folder contents."
    )

# --- Step 4: Quantize SavedModel -> INT8 TFLite ---
print("[4/4] Quantizing to INT8 TFLite...")
import tensorflow as tf

X_train = np.load(PROCESSED_DIR / "X_train.npy").astype(np.float32)
rpm_train = np.load(PROCESSED_DIR / "mean_rpm_train.npy").astype(np.float32)
rpm_mean = float(rpm_train.mean())
rpm_std = float(rpm_train.std()) or 1.0
rpm_train = (rpm_train - rpm_mean) / rpm_std

n_repr = min(200, len(X_train))
indices = np.random.RandomState(42).choice(len(X_train), n_repr, replace=False)

def representative_dataset():
    for idx in indices:
        x_ts = X_train[idx][None, :, :]       # (1, T, C) — NHWC for TF
        x_rpm = rpm_train[idx][None, None]     # (1, 1)
        yield [x_ts.astype(np.float32), x_rpm.astype(np.float32)]

converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_model = converter.convert()
tflite_path = TFLITE_DIR / "v2_motor_health_int8.tflite"
tflite_path.write_bytes(tflite_model)

print(f"\nDone.")
print(f"ONNX      : {onnx_path}  ({onnx_path.stat().st_size / 1024:.1f} KB)")
print(f"TFLite INT8: {tflite_path}  ({tflite_path.stat().st_size / 1024:.1f} KB)")