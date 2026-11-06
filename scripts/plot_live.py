#!/usr/bin/env python3
"""Live serial monitor for the motor-health-edge-ai rig.

Matches the firmware in src/inference/src/main.cpp, which does on-device
inference and prints BOTH:

  # RAW ax=.. ay=.. az=.. current=.. rpm=..        (debug, 1 Hz)
  <ts_ms>,<CLASS>,<s_h>,<s_i>,<s_f>,<rpm>          (data,  1 Hz)

Layout:
  1. Vibration magnitude  sqrt(ax^2 + ay^2 + az^2)   (from # RAW)
  2. Current (mA)                                     (from # RAW)
  3. RPM                                              (from # RAW / data)
  4. Predicted class + the 3 raw logits               (from data line)

The firmware infers once per 1-second window (50 samples @ 50 Hz), so this
monitor refreshes at ~1 Hz — not 50 Hz. That is expected.

Usage:
    python scripts/plot_live.py healthy --port COM6
    python scripts/plot_live.py friction --port COM6 --window 60
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import serial
import serial.tools.list_ports
from matplotlib.animation import FuncAnimation

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.common.constants import (  # noqa: E402
    LABEL_COLORS,
    LABELS,
    LIVE_WINDOW_SAMPLES,
)

RAW_DIR = REPO_ROOT / "data" / "raw"
FIG_DIR = REPO_ROOT / "results" / "figures"

# Firmware serial settings — see src/inference/src/main.cpp line 74
FIRMWARE_BAUD = 115200

# Data-line class tokens (uppercase) -> canonical lowercase label
FIRMWARE_CLASSES = {"HEALTHY", "IMBALANCED", "FRICTION", "WAITING", "STANDBY"}
# Data line has 6 comma-separated fields
DATA_FIELDS = ["timestamp_ms", "class", "s_healthy", "s_imbalanced", "s_friction", "rpm"]
N_DATA_FIELDS = len(DATA_FIELDS)


def choose_port() -> str:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found. Plug in the ESP32-C3 and retry.")
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    if len(ports) == 1:
        print(f"Auto-selecting {ports[0].device}")
        return ports[0].device
    try:
        idx = int(input("Select port index: ").strip())
        return ports[idx].device
    except (ValueError, IndexError):
        sys.exit("Invalid selection.")


def parse_raw_debug(raw: str) -> dict | None:
    """Parse: '# RAW ax=-0.91 ay=0.14 az=10.99 current=169.5 rpm=306'."""
    if not raw.startswith("# RAW"):
        return None
    try:
        body = raw[len("# RAW "):]
        out = {}
        for tok in body.split():
            k, v = tok.split("=", 1)
            out[k] = float(v)
        for k in ("ax", "ay", "az", "current", "rpm"):
            if k not in out:
                return None
        return out
    except (ValueError, KeyError):
        return None


def parse_data_line(raw: str) -> dict | None:
    """Parse: '<ts_ms>,<CLASS>,<s_h>,<s_i>,<s_f>,<rpm>'."""
    parts = raw.split(",")
    if len(parts) != N_DATA_FIELDS:
        return None
    if parts[1] not in FIRMWARE_CLASSES:
        return None
    try:
        return {
            "timestamp_ms": int(parts[0]),
            "class": parts[1],
            "s_healthy": float(parts[2]),
            "s_imbalanced": float(parts[3]),
            "s_friction": float(parts[4]),
            "rpm": float(parts[5]),
        }
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Live inference monitor for the ESP32-C3 motor rig."
    )
    ap.add_argument("label", choices=LABELS, help="Fault class being exercised")
    ap.add_argument("--port", help="Serial port (e.g. COM6). Interactive if omitted.")
    ap.add_argument(
        "--window",
        type=int,
        default=LIVE_WINDOW_SAMPLES,
        help="Rolling window in WINDOWS (not samples) — default 500 windows "
             f"= {LIVE_WINDOW_SAMPLES} seconds of history",
    )
    ap.add_argument("--no-save", action="store_true", help="Don't save a PNG on exit")
    ap.add_argument("--refresh-ms", type=int, default=500,
                    help="Plot redraw interval in ms (default 500 = 2 Hz)")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    port = args.port or choose_port()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = RAW_DIR / f"{args.label}_live_{stamp}.csv"
    out_png = FIG_DIR / f"live_{args.label}_{stamp}.png"

    print(f"\n✅ Opening {port} @ {FIRMWARE_BAUD} baud")
    print(f"✅ Writing CSV to: {out_csv.absolute()}")
    print(f"✅ Rolling window: {args.window} windows "
          f"(~{args.window} s at 1 Hz inference rate)")
    print(f"✅ Plot redraws every {args.refresh_ms} ms")
    print(f"✅ Class: {args.label}")
    print("👉 Press Ctrl-C to stop.\n")

    n = args.window
    buf_mag = deque(maxlen=n)
    buf_cur = deque(maxlen=n)
    buf_rpm = deque(maxlen=n)
    buf_s_h = deque(maxlen=n)
    buf_s_i = deque(maxlen=n)
    buf_s_f = deque(maxlen=n)
    state = {"raw_count": 0, "pred_count": 0, "last_class": "WAITING",
             "last_rpm": 0.0}

    try:
        ser = serial.Serial(port, FIRMWARE_BAUD, timeout=0.05)
    except serial.SerialException as e:
        sys.exit(
            f"\n❌ Could not open {port}: {e}\n"
            f"   Close Arduino IDE serial monitor / PuTTY / another plot_live.py\n"
            f"   and try again. Only one process can own a COM port on Windows."
        )

    # CSV mirrors the data line exactly, plus a 'label' column for provenance.
    fh = open(out_csv, "w", newline="")
    writer = csv.writer(fh)
    writer.writerow(DATA_FIELDS + ["label"])
    fh.flush()

    matplotlib.rcParams["toolbar"] = "None"
    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=False)
    fig.suptitle(f"Live inference monitor — exercising: {args.label}",
                 fontsize=12)

    # --- Subplot 1: vibration magnitude ---
    (line_mag,) = axes[0].plot([], [], lw=1.2, color="#1f77b4", marker=".")
    axes[0].set_ylabel("|a|  (m/s²)")
    axes[0].set_title("Vibration magnitude  √(ax² + ay² + az²)   "
                      "[1 point per 1 s window]")
    axes[0].grid(alpha=0.3)

    # --- Subplot 2: current ---
    (line_cur,) = axes[1].plot([], [], lw=1.2, color="#ff7f0e", marker=".")
    axes[1].set_ylabel("Current (mA)")
    axes[1].set_title("Motor current")
    axes[1].grid(alpha=0.3)

    # --- Subplot 3: RPM ---
    (line_rpm,) = axes[2].plot([], [], lw=1.2, color="#9467bd", marker=".")
    axes[2].set_ylabel("RPM")
    axes[2].set_title("Motor speed")
    axes[2].grid(alpha=0.3)

    # --- Subplot 4: predicted class + 3 logits over time ---
    ax4 = axes[3]
    (line_h,) = ax4.plot([], [], lw=1.0, label="s_healthy",    color=LABEL_COLORS["healthy"])
    (line_i,) = ax4.plot([], [], lw=1.0, label="s_imbalanced", color=LABEL_COLORS["imbalanced"])
    (line_f,) = ax4.plot([], [], lw=1.0, label="s_friction",   color=LABEL_COLORS["friction"])
    ax4.set_ylabel("logit")
    ax4.set_title("Model output (raw logits; argmax = predicted class)")
    ax4.grid(alpha=0.3)
    ax4.legend(loc="upper right", fontsize=8, ncol=3)

    class_text = ax4.text(
        0.01, 0.92, "waiting for first prediction…",
        transform=ax4.transAxes, ha="left", va="top", fontsize=11,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999", alpha=0.9),
    )

    for ax in axes:
        ax.set_xlabel("windows (1 s each)")

    plt.tight_layout()

    def update(_frame):
        # Drain at most a few hundred lines per frame. At 1 Hz inference
        # rate, this is plenty; the cap just protects against a stuck port.
        for _ in range(500):
            try:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException:
                break
            if not raw:
                break

            # Debug lines -> feed subplots 1–3
            d = parse_raw_debug(raw)
            if d is not None:
                mag = float(np.sqrt(d["ax"] ** 2 + d["ay"] ** 2 + d["az"] ** 2))
                buf_mag.append(mag)
                buf_cur.append(d["current"])
                buf_rpm.append(d["rpm"])
                state["raw_count"] += 1
                continue

            # Data line -> CSV + subplot 4
            p = parse_data_line(raw)
            if p is not None:
                writer.writerow([
                    p["timestamp_ms"], p["class"],
                    f"{p['s_healthy']:.2f}",
                    f"{p['s_imbalanced']:.2f}",
                    f"{p['s_friction']:.2f}",
                    f"{p['rpm']:.0f}",
                    args.label,
                ])
                buf_s_h.append(p["s_healthy"])
                buf_s_i.append(p["s_imbalanced"])
                buf_s_f.append(p["s_friction"])
                state["pred_count"] += 1
                state["last_class"] = p["class"]
                state["last_rpm"] = p["rpm"]
                continue

            # Any other '#' line (Motor ON, STATE CHANGE, boot messages)
            if raw.startswith("#"):
                print(f"  {raw}")

        if state["raw_count"] or state["pred_count"]:
            fh.flush()

        # --- redraw ---
        if buf_mag:
            x = np.arange(len(buf_mag))
            line_mag.set_data(x, np.asarray(buf_mag))
            line_cur.set_data(x, np.asarray(buf_cur))
            line_rpm.set_data(x, np.asarray(buf_rpm))
            for ax in axes[:3]:
                ax.set_xlim(0, max(n - 1, 1))
            axes[0].relim()
            axes[0].autoscale_view(scalex=False, scaley=True)
            axes[1].relim()
            axes[1].autoscale_view(scalex=False, scaley=True)
            axes[2].relim()
            axes[2].autoscale_view(scalex=False, scaley=True)

        if buf_s_h:
            xp = np.arange(len(buf_s_h))
            line_h.set_data(xp, np.asarray(buf_s_h))
            line_i.set_data(xp, np.asarray(buf_s_i))
            line_f.set_data(xp, np.asarray(buf_s_f))
            ax4.set_xlim(0, max(n - 1, 1))
            ax4.relim()
            ax4.autoscale_view(scalex=False, scaley=True)

            cls = state["last_class"]
            color = LABEL_COLORS.get(cls.lower(), "#888")
            class_text.set_text(f"predicted: {cls}   (rpm {state['last_rpm']:.0f})")
            class_text.set_color(color)
            fig.suptitle(
                f"Live inference monitor — exercising: {args.label}   "
                f"|   predicted: {cls}",
                fontsize=12, color=color,
            )
        return ()

    _anim = FuncAnimation(fig, update, interval=args.refresh_ms, blit=False,
                          cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\n🛑 Stopping...")
        try:
            ser.close()
        except Exception:
            pass
        try:
            fh.flush()
            fh.close()
        except Exception:
            pass
        print(f"💾 CSV:  {out_csv.absolute()}  "
              f"({state['pred_count']} predictions, {state['raw_count']} raw)")
        if not args.no_save and (state["pred_count"] or state["raw_count"]):
            try:
                fig.savefig(out_png, dpi=120, bbox_inches="tight")
                print(f"🖼  PNG:  {out_png.absolute()}")
            except Exception as e:
                print(f"⚠  Could not save PNG: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl-C fired inside a Tk/serial C call. main()'s finally block
        # already saved CSV + PNG; just exit quietly.
        print("\n🛑 Interrupted.")
        sys.exit(0)