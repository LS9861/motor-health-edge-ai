#!/usr/bin/env python3
"""Capture 120s of # INVOKE_US lines from serial, compute stats."""
import argparse
import statistics
import sys
import time

import serial
import serial.tools.list_ports


def choose_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found.")
    if len(ports) == 1:
        return ports[0].device
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    return ports[int(input("Select: ").strip())].device


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    port = args.port or choose_port()
    print(f"Opening {port} @ {args.baud}, capturing {args.seconds}s...")
    print("Ensure motor is running at steady state (healthy).")

    ser = serial.Serial(port, args.baud, timeout=2)
    times = []
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < args.seconds:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("# INVOKE_US,"):
                try:
                    times.append(int(line.split(",")[1]))
                    print(f"\r  captured {len(times)} samples", end="")
                except ValueError:
                    pass
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()

    print()
    if not times:
        sys.exit("No INVOKE_US lines captured. Is firmware flashed?")

    ts = sorted(times)
    n = len(ts)
    print(f"\n=== Inference time (n={n}) ===")
    print(f"  min:    {ts[0]:>6} us  ({ts[0]/1000:>5.1f} ms)")
    print(f"  median: {int(statistics.median(times)):>6} us  ({statistics.median(times)/1000:>5.1f} ms)")
    print(f"  mean:   {int(statistics.mean(times)):>6} us  ({statistics.mean(times)/1000:>5.1f} ms)")
    print(f"  max:    {ts[-1]:>6} us  ({ts[-1]/1000:>5.1f} ms)")
    print(f"  p95:    {ts[int(n*0.95)]:>6} us  ({ts[int(n*0.95)]/1000:>5.1f} ms)")


if __name__ == "__main__":
    main()