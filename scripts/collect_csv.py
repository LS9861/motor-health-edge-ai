#!/usr/bin/env python3
"""Collect a fixed 20-second raw-sensor capture from the ESP32-C3.

Usage:
    python scripts/collect_csv.py <label> <n>

    <label>  one of: healthy, imbalanced, friction
    <n>      capture number (1, 2, 3, ...) — used only in the filename

Flow:
    1. Flip motor ON, wait ~5 s for RPM to stabilize (RPM ≈ 266).
    2. Run this command. It waits for # COLLECTING, then prompts you.
    3. Press Enter when ready. Script captures 20 s of data.
    4. Script prints "Saved: ..." and exits.
    5. Flip motor OFF. Wait 5 s for coastdown.

Output file:
    data/raw/jga25/<label>_<n>.csv

The 20-second window is fixed so every capture has identical length
(1000 rows at 50 Hz). The script discards nothing — the "first 3 s
spin-up / last 3 s coastdown" are handled by YOU (flip motor on 5 s
before pressing Enter; flip off only after the script exits).
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "jga25"

FIRMWARE_BAUD = 921600
CAPTURE_SECONDS = 20
EXPECTED_HZ = 50
EXPECTED_ROWS = CAPTURE_SECONDS * EXPECTED_HZ   # 1000


def choose_port() -> str:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found. Plug in the ESP32-C3 and retry.")
    if len(ports) == 1:
        print(f"Using {ports[0].device} ({ports[0].description})")
        return ports[0].device
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    try:
        idx = int(input("Select port index: ").strip())
        return ports[idx].device
    except (ValueError, IndexError):
        sys.exit("Invalid selection.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Capture a fixed 20-second raw-sensor CSV from the ESP32-C3."
    )
    ap.add_argument("label", choices=["healthy", "imbalanced", "friction"])
    ap.add_argument("n", type=int, help="Capture number (1, 2, 3, ...)")
    ap.add_argument("--port", help="Serial port (e.g. COM6). Auto-detected if omitted.")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RAW_DIR / f"{args.label}_{args.n}.csv"

    if out_csv.exists():
        sys.exit(
            f"\n❌ {out_csv} already exists.\n"
            f"   Delete it first, or use a different <n>."
        )

    port = args.port or choose_port()

    try:
        ser = serial.Serial(port, FIRMWARE_BAUD, timeout=1)
    except serial.SerialException as e:
        sys.exit(
            f"\n❌ Could not open {port}: {e}\n"
            f"   Close Arduino IDE serial monitor / PuTTY / another capture.\n"
        )

    print(f"\n✅ Opened {port} @ {FIRMWARE_BAUD}")
    print(f"✅ Target file: {out_csv}")

    # Wait for # COLLECTING marker (firmware prints it once after 25s warm-up)
    # Firmware is ready when we see EITHER '# COLLECTING' OR a valid data row.
    # (The marker is printed once at boot; if the script opens the port after
    # that moment, we'll be reading data rows already — that's also ready.)
    print("⏳ Waiting for firmware to be ready (marker OR data row)...")
    t0 = time.monotonic()
    ready = False
    while not ready:
        if time.monotonic() - t0 > 60:
            ser.close()
            sys.exit(
                "\n❌ Timeout: no marker and no data rows within 60s.\n"
                "   Is the firmware flashed (collect_raw.cpp) and running?\n"
                "   Is COM6 the right port?"
            )
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        if line.startswith("# COLLECTING"):
            print("✅ Firmware is ready (marker).")
            ready = True
            break
        if line.startswith("#"):
            print(f"   {line}")
            continue
        # Data row? 6 comma fields, first int, second float
        parts = line.split(",")
        if len(parts) == 6:
            try:
                int(parts[0])
                float(parts[1])
                print("✅ Firmware is ready (data rows flowing).")
                ready = True
                break
            except ValueError:
                continue

    print()
    print("👉 Motor should be running at steady speed (RPM ≈ 266).")
    print("   If not: flip motor ON, wait 5 s, then press Enter.")
    print("   If you made a mistake: Ctrl-C to abort (no file written).")
    input("\n   Press Enter to START 20-second capture... ")

    # Capture loop — write header + 1000 rows
    header = ["timestamp_ms", "ax", "ay", "az", "current_mA", "rpm"]
    rows_written = 0
    start_mono = time.monotonic()

    with open(out_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)

        while rows_written < EXPECTED_ROWS:
            if time.monotonic() - start_mono > CAPTURE_SECONDS + 5:
                # 5-second grace in case serial is slow; but warn if we exceeded
                print(f"\n⚠  Timeout: only got {rows_written}/{EXPECTED_ROWS} rows.")
                break
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException as e:
                print(f"\n⚠  Serial error: {e}")
                break
            if not line:
                continue
            if line.startswith("#"):
                # print firmware markers but don't write to CSV
                continue
            # Expect 6 comma-separated fields
            parts = line.split(",")
            if len(parts) != 6:
                continue
            # Try converting to confirm it's a data row (not a stray header)
            try:
                int(parts[0])
                float(parts[1])
            except ValueError:
                continue
            writer.writerow(parts)
            rows_written += 1
            if rows_written % 100 == 0:
                elapsed = time.monotonic() - start_mono
                print(f"   {rows_written}/{EXPECTED_ROWS} rows ({elapsed:.1f}s)",
                      end="\r")

    ser.close()
    print()
    print(f"\n💾 Saved: {out_csv}")
    print(f"   Rows: {rows_written}")

    # Quick sanity check on data quality
    if rows_written < EXPECTED_ROWS * 0.9:
        print(f"\n⚠  WARNING: only {rows_written} rows "
              f"(expected {EXPECTED_ROWS}). Motor may have stopped early?")
        print(f"   Check with: python -c \"import pandas as pd; "
              f"print(pd.read_csv('{out_csv}').describe())\"")
    else:
        print(f"\n✅ Capture looks complete ({rows_written} rows).")
        print(f"\n👉 Next: flip motor OFF, wait 5 s, then run the next capture.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Aborted. No file written (or partial file if mid-capture).")
        sys.exit(1)