#!/usr/bin/env python3
"""Live inference monitor for the motor-health-edge-ai rig (v7).

Changes vs v6:
  - All 5 subplots share the same x-axis (time in seconds/windows).
  - The state timeline scrolls with the sensor data (rolling window).
  - Can now visually correlate a fault spike in the timeline with the
    exact vibration/current sample that caused it.
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
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.common.constants import LABEL_COLORS, LABELS

RAW_DIR = REPO_ROOT / "data" / "raw" / "live"
FIG_DIR = REPO_ROOT / "results" / "figures"

FIRMWARE_BAUD = 115200
FIRMWARE_CLASSES = {"HEALTHY", "IMBALANCED", "FRICTION", "WAITING", "STANDBY"}
DATA_FIELDS = ["timestamp_ms", "class", "s_healthy", "s_imbalanced", "s_friction", "rpm"]
N_DATA_FIELDS = len(DATA_FIELDS)

# How many windows to show on the x-axis (e.g., 200 = ~3.3 mins)
HISTORY_WINDOWS = 200


def choose_port() -> str:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found.")
    if len(ports) == 1:
        print(f"Using {ports[0].device}")
        return ports[0].device
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    try:
        idx = int(input("Select port index: ").strip())
        return ports[idx].device
    except (ValueError, IndexError):
        sys.exit("Invalid selection.")


def parse_raw_debug(raw: str) -> dict | None:
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
        out.setdefault("voltage", float("nan"))
        return out
    except (ValueError, KeyError):
        return None


def parse_data_line(raw: str) -> dict | None:
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
    ap = argparse.ArgumentParser()
    ap.add_argument("label", choices=LABELS)
    ap.add_argument("--port")
    ap.add_argument("--window", type=int, default=HISTORY_WINDOWS,
                    help="Number of 1-second windows to show on all plots")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--refresh-ms", type=int, default=500)
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    port = args.port or choose_port()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = RAW_DIR / f"{args.label}_live_{stamp}.csv"
    out_png = FIG_DIR / f"live_{args.label}_{stamp}.png"

    print(f"\n✅ Opening {port} @ {FIRMWARE_BAUD}")
    print(f"✅ CSV: {out_csv}")
    print(f"✅ Showing last {args.window} windows (~{args.window}s)")

    # Rollings buffers
    n = args.window
    buf_mag = deque(maxlen=n)
    buf_cur = deque(maxlen=n)
    buf_vol = deque(maxlen=n)
    buf_rpm = deque(maxlen=n)
    # Timeline buffer stores the class STRING for the last N windows
    buf_class = deque(maxlen=n)
    state = {"raw": 0, "pred": 0, "last_class": "WAITING"}

    try:
        ser = serial.Serial(port, FIRMWARE_BAUD, timeout=0.05)
    except serial.SerialException as e:
        sys.exit(f"\n❌ Could not open {port}: {e}\n")

    fh = open(out_csv, "w", newline="")
    writer = csv.writer(fh)
    writer.writerow(DATA_FIELDS + ["voltage", "label"])
    fh.flush()

    matplotlib.rcParams["toolbar"] = "None"
    # Share X axis across ALL 5 subplots!
    fig, axes = plt.subplots(5, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"Live inference monitor — {args.label}", fontsize=12)

    color_map = {
        "HEALTHY": LABEL_COLORS["healthy"],
        "IMBALANCED": LABEL_COLORS["imbalanced"],
        "FRICTION": LABEL_COLORS["friction"],
        "WAITING": "#888888",
        "STANDBY": "#333333",
    }

    (line_mag,) = axes[0].plot([], [], lw=0.9, color="#1f77b4", marker=".")
    axes[0].set_ylabel("|a| (m/s²)"); axes[0].set_title("Vibration magnitude")
    axes[0].grid(alpha=0.3)

    (line_cur,) = axes[1].plot([], [], lw=0.9, color="#ff7f0e", marker=".")
    axes[1].set_ylabel("Current (mA)"); axes[1].set_title("Motor current")
    axes[1].grid(alpha=0.3)

    (line_vol,) = axes[2].plot([], [], lw=0.9, color="#2ca02c", marker=".")
    axes[2].set_ylabel("Voltage (V)"); axes[2].set_title("Supply voltage")
    axes[2].grid(alpha=0.3)

    (line_rpm,) = axes[3].plot([], [], lw=0.9, color="#9467bd", marker=".")
    axes[3].set_ylabel("RPM"); axes[3].set_title("Motor speed")
    axes[3].grid(alpha=0.3)

    # Subplot 5: state timeline
    axes[4].set_ylim(0, 1)
    axes[4].set_yticks([])
    axes[4].set_xlabel("window index (1 s each)")
    axes[4].set_title("State timeline (aligned with sensor plots above)")
    axes[4].grid(alpha=0.3, axis="x")

    # Legend for timeline
    legend_handles = [
        Patch(facecolor=color_map["HEALTHY"], label="HEALTHY"),
        Patch(facecolor=color_map["IMBALANCED"], label="IMBALANCED"),
        Patch(facecolor=color_map["FRICTION"], label="FRICTION"),
        Patch(facecolor=color_map["WAITING"], label="WAITING"),
        Patch(facecolor=color_map["STANDBY"], label="STANDBY"),
    ]
    axes[4].legend(handles=legend_handles, loc="upper right", ncol=5, fontsize=8, framealpha=0.95)

    # Status text
    status_text = axes[4].text(
        0.01, 0.85, "", transform=axes[4].transAxes,
        ha="left", va="top", fontsize=11, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#666", alpha=0.95),
    )

    for ax in axes[:4]:
        ax.set_xlabel("windows (1 s each)")

    def update(_frame):
        for _ in range(500):
            try:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException:
                break
            if not raw:
                break

            d = parse_raw_debug(raw)
            if d is not None:
                mag = float(np.sqrt(d["ax"] ** 2 + d["ay"] ** 2 + d["az"] ** 2))
                buf_mag.append(mag)
                buf_cur.append(d["current"])
                buf_vol.append(d["voltage"])
                buf_rpm.append(d["rpm"])
                state["raw"] += 1
                continue

            p = parse_data_line(raw)
            if p is not None:
                writer.writerow([
                    p["timestamp_ms"], p["class"],
                    f"{p['s_healthy']:.2f}", f"{p['s_imbalanced']:.2f}",
                    f"{p['s_friction']:.2f}", f"{p['rpm']:.0f}",
                    f"{buf_vol[-1] if buf_vol else 0.0:.2f}",
                    args.label,
                ])
                buf_class.append(p["class"])
                state["pred"] += 1
                state["last_class"] = p["class"]
                continue

            if raw.startswith("#"):
                print(f"  {raw}")

        if state["raw"] or state["pred"]:
            fh.flush()

        # Redraw all data plots
        if buf_mag:
            # Align X-axis: if we have N samples, X goes from 0 to N-1
            # For the timeline, we need to align the class boxes with the same X.
            x = np.arange(len(buf_mag))
            line_mag.set_data(x, np.asarray(buf_mag))
            line_cur.set_data(x, np.asarray(buf_cur))
            line_vol.set_data(x, np.asarray(buf_vol))
            line_rpm.set_data(x, np.asarray(buf_rpm))
            
            # Set X lim for all axes to the current length of data
            # Note: Because `sharex=True`, setting it on axes[0] affects all.
            axes[0].set_xlim(0, max(n - 1, 1))
            
            axes[0].relim(); axes[0].autoscale_view(scalex=False, scaley=True)
            axes[1].relim(); axes[1].autoscale_view(scalex=False, scaley=True)
            axes[2].relim(); axes[2].autoscale_view(scalex=False, scaley=True)
            axes[3].relim(); axes[3].autoscale_view(scalex=False, scaley=True)

        # Redraw state timeline
        if len(buf_class) > 0:
            # Clear old bars
            for patch in axes[4].patches:
                patch.remove()
                
            # Draw new bars aligned with X-axis
            # (We iterate over the buffer and draw a colored rectangle for each)
            x_start = 0
            current_cls = buf_class[0]
            for i in range(1, len(buf_class)):
                if buf_class[i] != current_cls:
                    # Draw block for the previous class
                    width = i - x_start
                    axes[4].barh(0.5, width=width, left=x_start, height=0.7,
                                 color=color_map.get(current_cls, "#888888"))
                    x_start = i
                    current_cls = buf_class[i]
            
            # Draw the last block
            width = len(buf_class) - x_start
            axes[4].barh(0.5, width=width, left=x_start, height=0.7,
                         color=color_map.get(current_cls, "#888888"))

            # Update status text
            cls = state["last_class"]
            color = color_map.get(cls, "#333")
            status_text.set_text(f"Now: {cls}")
            status_text.set_color(color)

        # Suptitle
        cls = state["last_class"]
        color = color_map.get(cls, "#333")
        fig.suptitle(
            f"Live inference monitor — {args.label}   |   predicted: {cls}",
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
        try: ser.close()
        except Exception: pass
        try: fh.flush(); fh.close()
        except Exception: pass
        print(f"💾 CSV: {out_csv}  ({state['pred']} predictions, {state['raw']} raw)")
        if not args.no_save and (state["pred"] or state["raw"]):
            try:
                fig.savefig(out_png, dpi=120, bbox_inches="tight")
                print(f"🖼  PNG: {out_png}")
            except Exception as e:
                print(f"⚠  PNG save failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
        sys.exit(0)