#!/usr/bin/env python3
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
import serial
import serial.tools.list_ports

REPO_ROOT  = Path(__file__).resolve().parent.parent
RAW_DIR    = REPO_ROOT / "data" / "raw"
BAUDRATE   = 921600
EXPECTED_N = 7

def choose_port() -> str:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found.")
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    if len(ports) == 1:
        return ports[0].device
    try:
        idx = int(input("Select port index: ").strip())
        return ports[idx].device
    except (ValueError, IndexError):
        sys.exit("Invalid selection.")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("label", choices=["healthy", "imbalanced", "friction"])
    ap.add_argument("--port", help="Override serial port")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    port = args.port or choose_port()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RAW_DIR / f"{args.label}_{stamp}.csv"
    
    print(f"\n✅ Opening {port} @ {BAUDRATE} baud")
    print(f"✅ Writing to: {out_path.absolute()}")
    print("👉 Press Ctrl-C to stop logging.\n")

    rows = 0
    try:
        with serial.Serial(port, BAUDRATE, timeout=1) as ser, \
             open(out_path, "w", newline="") as fh:
            
            writer = csv.writer(fh)
            
            # Write the header immediately
            writer.writerow(["timestamp_ms", "ax", "ay", "az", "current_mA", "voltage_v", "rpm", "label"])
            print("Header written. Listening for data...")

            while True:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                
                # If the ESP32 prints the header again, skip it
                if raw.startswith("timestamp_ms"):
                    continue
                
                # If the ESP32 prints a comment like "# Motor ON", skip it
                if raw.startswith("#"):
                    print(f"\n{raw}")
                    continue

                parts = raw.split(",")
                if len(parts) != EXPECTED_N:
                    continue
                
                writer.writerow(parts + [args.label])
                fh.flush()
                rows += 1
                print(f"\rSaving... {rows} rows", end="")

    except KeyboardInterrupt:
        print(f"\n\n🛑 Logging stopped.")
    finally:
        print(f"💾 File saved with {rows} rows to:\n   {out_path.absolute()}")

if __name__ == "__main__":
    main()