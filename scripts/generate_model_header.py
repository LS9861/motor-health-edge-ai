#!/usr/bin/env python3
"""Convert v3_int8.tflite → model_data.h for TFLM compilation."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TFLITE = REPO_ROOT / "models" / "tflite" / "v3_int8.tflite"
HEADER = REPO_ROOT / "src" / "inference" / "include" / "model_data.h"

if not TFLITE.exists():
    raise FileNotFoundError(f"Model not found: {TFLITE}")

data = TFLITE.read_bytes()
print(f"Loading {TFLITE.name}: {len(data)} bytes")

lines = [
    "// Auto-generated from v3_int8.tflite — do not edit",
    "// Regenerate with: python scripts/gen_model_header.py",
    "#ifndef MODEL_DATA_H",
    "#define MODEL_DATA_H",
    "",
    f"// Model size: {len(data)} bytes",
    "",
    "static const unsigned char model_data[] = {",
]

for i in range(0, len(data), 12):
    chunk = data[i:i + 12]
    hex_str = ", ".join(f"0x{b:02x}" for b in chunk)
    lines.append(f"  {hex_str},")

lines += [
    "};",
    f"static const unsigned int model_data_len = {len(data)};",
    "",
    "#endif  // MODEL_DATA_H",
]

HEADER.write_text("\n".join(lines) + "\n")
print(f"✅ Wrote {HEADER}")
print(f"   Size on disk: {HEADER.stat().st_size / 1024:.1f} KB")