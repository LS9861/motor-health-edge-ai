#!/usr/bin/env python3
"""
Export v3_5ch_flat.pt → v3_float.tflite + v3_int8.tflite

5 channels: ax, ay, az, current_mA, rpm  (voltage REMOVED)
Uses opset 17 + onnx2tf -kat to properly handle AdaptiveAvgPool1d.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "training"))
from model import MotorCNN1D

# NOTE: new checkpoint name (5-channel)
CKPT = REPO_ROOT / "models" / "checkpoints" / "v3_5ch_flat_jga25.pt"
ONNX_OUT = REPO_ROOT / "models" / "onnx" / "v3_export.onnx"
TFLITE_DIR = REPO_ROOT / "models" / "tflite"
PROCESSED = REPO_ROOT / "data" / "processed"

ONNX_OUT.parent.mkdir(parents=True, exist_ok=True)
TFLITE_DIR.mkdir(parents=True, exist_ok=True)

CLASSES = ["healthy", "imbalanced", "friction"]
N_CHANNELS = 5  # ← no voltage, Rpm drop


def get_tflite_shape(interp):
    d = interp.get_input_details()[0]['shape']
    return tuple(d.tolist())


def run_tflite_float(interp, input_array):
    """Feed float32 input, get float32 output. For float models only."""
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]
    interp.set_tensor(inp['index'], input_array.astype(np.float32))
    interp.invoke()
    return interp.get_tensor(out['index'])[0]


def predict_int8(interp, inp, out, x_float):
    """Manually quantize input, run, dequantize output. For int8-in/int8-out models."""
    iscale, izero = inp['quantization']
    oscale, ozero = out['quantization']
    x_int8 = np.clip(
        np.round(x_float / iscale + izero), -128, 127,
    ).astype(np.int8)
    interp.set_tensor(inp['index'], x_int8)
    interp.invoke()
    y_raw = interp.get_tensor(out['index'])[0]
    return (y_raw.astype(np.float32) - ozero) * oscale


# ============================================================
# 1. Load PyTorch model
# ============================================================
print("=" * 60)
print("STEP 1: Load PyTorch model (5-channel, no voltage)")
print("=" * 60)

model = MotorCNN1D(in_channels=N_CHANNELS, n_classes=3)
model.load_state_dict(torch.load(CKPT, map_location="cpu", weights_only=True))
model.eval()
print(f"✅ Loaded ({sum(p.numel() for p in model.parameters()):,} params)")

# ============================================================
# 2. Load real healthy window
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: Load real healthy window")
print("=" * 60)

X_train = np.load(PROCESSED / "X_train.npy").astype(np.float32)
y_train = np.load(PROCESSED / "y_train.npy")
healthy_idx = int(np.where(y_train == 0)[0][0])
healthy_ntc = X_train[healthy_idx:healthy_idx + 1]  # (1, 50, 5) — TFLite format
healthy_nct = np.transpose(healthy_ntc, (0, 2, 1))  # (1, 5, 50) — PyTorch format
print(f"Using X_train[{healthy_idx}], shape={healthy_ntc.shape}")

# PyTorch reference prediction
with torch.no_grad():
    ref_logits = model(torch.from_numpy(healthy_nct)).numpy()[0]
ref_class = CLASSES[ref_logits.argmax()]
print(f"PyTorch logits: {ref_logits.round(4)}")
print(f"PyTorch class : {ref_class}")

if ref_class != "healthy":
    print("❌ PyTorch predicts wrong class")
    sys.exit(1)
print("✅ PyTorch OK")

# ============================================================
# 3. Export ONNX (opset 17 for AdaptiveAvgPool1d)
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: Export PyTorch → ONNX")
print("=" * 60)

torch.onnx.export(
    model,
    torch.from_numpy(healthy_nct),
    str(ONNX_OUT),
    input_names=["input"],
    output_names=["output"],
    opset_version=17,
    do_constant_folding=True,
    dynamic_axes=None,
    verbose=False,
    dynamo=False,
)
print(f"✅ Saved {ONNX_OUT.name} ({ONNX_OUT.stat().st_size / 1024:.1f} KB)")

# ============================================================
# 4. Verify ONNX
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: Verify ONNX")
print("=" * 60)

import onnxruntime as ort

onnx_out = ort.InferenceSession(str(ONNX_OUT), providers=["CPUExecutionProvider"]).run(
    None, {"input": healthy_nct}
)[0][0]
diff = np.abs(onnx_out - ref_logits).max()
print(f"ONNX logits : {onnx_out.round(4)}")
print(f"max diff    : {diff:.6f}")
if diff > 1e-4:
    print("❌ ONNX diverged")
    sys.exit(1)
print("✅ ONNX matches PyTorch")

# ============================================================
# 5. ONNX → TFLite (with -kat to preserve shapes)
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: ONNX → TFLite")
print("=" * 60)

tflite_dir = TFLITE_DIR / "float_export"
if tflite_dir.exists():
    shutil.rmtree(tflite_dir)

cmd = [
    "onnx2tf",
    "-i", str(ONNX_OUT),
    "-o", str(tflite_dir),
    "-nuo",
    "-kat", "input",
    "--non_verbose",
]
print(f"Running: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("❌ onnx2tf failed")
    print(result.stdout[-3000:])
    print(result.stderr[-3000:])
    sys.exit(1)

tflite_files = list(tflite_dir.glob("*.tflite"))
if not tflite_files:
    print("❌ No .tflite")
    sys.exit(1)

final_float = TFLITE_DIR / "v3_float.tflite"
shutil.copy(tflite_files[0], final_float)
print(f"✅ Saved {final_float.name} ({final_float.stat().st_size / 1024:.1f} KB)")

# ============================================================
# 6. Verify TFLite float
# ============================================================
print("\n" + "=" * 60)
print("STEP 6: Verify TFLite float")
print("=" * 60)

interp = tf.lite.Interpreter(model_path=str(final_float))
interp.allocate_tensors()
shape = get_tflite_shape(interp)
print(f"TFLite input shape: {shape}")

# Auto-select the right input based on shape — 5 channels now
if shape == (1, 50, 5):
    input_data = healthy_ntc
elif shape == (1, 5, 50):
    input_data = healthy_nct
else:
    print(f"❌ Unexpected input shape: {shape}")
    sys.exit(1)

tflite_logits = run_tflite_float(interp, input_data)
diff = np.abs(tflite_logits - ref_logits).max()
print(f"TFLite logits : {tflite_logits.round(4)}")
print(f"max diff      : {diff:.6f}")
print(f"TFLite class  : {CLASSES[tflite_logits.argmax()]}")

if tflite_logits.argmax() != 0:
    print("❌ TFLite predicts wrong class")
    sys.exit(1)
if diff > 1e-2:
    print(f"❌ TFLite diff too high ({diff:.4f})")
    sys.exit(1)
print("✅ TFLite float matches PyTorch")

# ============================================================
# 7. INT8 quantization (pure int8 in/out — no float wrapper)
# ============================================================
print("\n" + "=" * 60)
print("STEP 7: INT8 quantization")
print("=" * 60)

# Representative dataset must match model's expected input layout.
# Use ALL training windows (all 3 classes) — not just the first 200.
if shape == (1, 50, 5):
    rep_data = X_train
else:
    rep_data = np.transpose(X_train, (0, 2, 1))


def rep_gen():
    for i in range(len(rep_data)):
        yield [rep_data[i:i + 1].astype(np.float32)]


converter = tf.lite.TFLiteConverter.from_saved_model(str(tflite_dir))
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = rep_gen
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
# Pure int8 in/out: no float<->int8 wrapper ops that can be misconfigured
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
int8_bytes = converter.convert()

final_int8 = TFLITE_DIR / "v3_int8.tflite"
final_int8.write_bytes(int8_bytes)
print(f"✅ Saved {final_int8.name} ({len(int8_bytes) / 1024:.1f} KB)")

# ============================================================
# 8. Verify INT8
# ============================================================
print("\n" + "=" * 60)
print("STEP 8: Verify INT8")
print("=" * 60)

interp8 = tf.lite.Interpreter(model_path=str(final_int8))
interp8.allocate_tensors()
inp8 = interp8.get_input_details()[0]
out8 = interp8.get_output_details()[0]
shape8 = tuple(inp8['shape'].tolist())
print(f"INT8 input shape: {shape8}")
print(f"INT8 input dtype: {inp8['dtype'].__name__}")
print(f"INT8 output dtype: {out8['dtype'].__name__}")

input8_float = healthy_ntc if shape8 == (1, 50, 5) else healthy_nct
int8_logits = predict_int8(interp8, inp8, out8, input8_float)
diff8 = np.abs(int8_logits - ref_logits).max()
print(f"INT8 logits : {int8_logits.round(4)}")
print(f"max diff    : {diff8:.6f}")
print(f"INT8 class  : {CLASSES[int8_logits.argmax()]}")

if int8_logits.argmax() != 0:
    print("❌ INT8 predicts wrong class")
    sys.exit(1)
print("✅ INT8 OK")

# ============================================================
# 9. Full test set accuracy
# ============================================================
print("\n" + "=" * 60)
print("STEP 9: INT8 accuracy on test set")
print("=" * 60)

X_test = np.load(PROCESSED / "X_test.npy").astype(np.float32)
y_test = np.load(PROCESSED / "y_test.npy")

if shape8 == (1, 50, 5):
    X_test_in = X_test
else:
    X_test_in = np.transpose(X_test, (0, 2, 1))

correct = 0
for i in range(len(X_test_in)):
    out = predict_int8(interp8, inp8, out8, X_test_in[i:i + 1])
    if out.argmax() == y_test[i]:
        correct += 1

acc = correct / len(X_test_in)
print(f"INT8 accuracy: {acc * 100:.2f}%  ({correct}/{len(X_test_in)})")

smoke_mode = "--smoke" in sys.argv

if not smoke_mode and acc < 0.70:
    print("❌ INT8 accuracy dropped below 70%")
    sys.exit(1)
elif smoke_mode:
    print(f"⚠️  Smoke mode: skipping accuracy gate (acc={acc:.2%})")

print("\n" + "=" * 60)
print("🎉 EXPORT COMPLETE")
print("=" * 60)
print(f"Float model : {final_float} ({final_float.stat().st_size / 1024:.1f} KB)")
print(f"INT8 model  : {final_int8} ({len(int8_bytes) / 1024:.1f} KB)")
print(f"INT8 acc    : {acc * 100:.2f}%")