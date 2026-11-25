#!/usr/bin/env python3
"""Generate simple, friendly illustrations (PNG) for the ML_info beginner guide.

Writes into ML_info/img/. Uses matplotlib + numpy only.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
os.makedirs(IMG, exist_ok=True)

BLUE = "#1f6feb"
DARK = "#0b3d91"
AMBER = "#e0a800"
GREEN = "#2ea043"
RED = "#d1242f"
GREY = "#8b949e"

plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})


def save(fig, name):
    path = os.path.join(IMG, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", path)


def box(ax, x, y, w, h, text, color=BLUE, fc="#eef4ff", fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=2, edgecolor=color, facecolor=fc))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=DARK, fontweight="bold", wrap=True)


def arrow(ax, x1, y1, x2, y2, color=GREY):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=18, linewidth=2, color=color))


# ---------------------------------------------------------------- 1. What is ML
def fig_ml_concept():
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    # traditional
    box(ax, 0.2, 2.4, 2.6, 1.1, "Rules\n(written by you)", color=GREY, fc="#f6f8fa")
    box(ax, 3.6, 2.4, 2.4, 1.1, "Data", color=GREY, fc="#f6f8fa")
    box(ax, 6.9, 2.4, 2.6, 1.1, "Answers", color=GREY, fc="#f6f8fa")
    arrow(ax, 2.8, 2.95, 3.6, 2.95); arrow(ax, 6.0, 2.95, 6.9, 2.95)
    ax.text(5, 3.75, "Traditional programming", ha="center", fontsize=12,
            fontweight="bold", color=GREY)
    # ML
    box(ax, 0.2, 0.4, 2.6, 1.1, "Data\n+ Answers\n(examples)", color=BLUE)
    box(ax, 3.6, 0.4, 2.4, 1.1, "Learner", color=BLUE)
    box(ax, 6.9, 0.4, 2.6, 1.1, "Rules\n(the model)", color=GREEN, fc="#e6f7ea")
    arrow(ax, 2.8, 0.95, 3.6, 0.95, BLUE); arrow(ax, 6.0, 0.95, 6.9, 0.95, BLUE)
    ax.text(5, 1.75, "Machine learning", ha="center", fontsize=12,
            fontweight="bold", color=BLUE)
    save(fig, "01_ml_concept.png")


# ---------------------------------------------------------------- 2. Training loop
def fig_training_loop():
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.set_xlim(0, 8); ax.set_ylim(0, 8); ax.axis("off")
    cx, cy, r = 4, 4, 2.4
    nodes = [("Make a\nprediction", 90), ("Measure\nthe error", 0),
             ("Nudge the\nweights", 270), ("Repeat\n(many times)", 180)]
    for text, ang in nodes:
        a = np.deg2rad(ang)
        x, y = cx + r * np.cos(a), cy + r * np.sin(a)
        ax.add_patch(Circle((x, y), 0.95, facecolor="#eef4ff", edgecolor=BLUE,
                            linewidth=2, zorder=2))
        ax.text(x, y, text, ha="center", va="center", fontsize=10,
                fontweight="bold", color=DARK, zorder=3)
    for ang in [45, 135, 225, 315]:
        a = np.deg2rad(ang)
        x, y = cx + (r + 0.05) * np.cos(a), cy + (r + 0.05) * np.sin(a)
        ax.annotate("", xy=(x, y), xytext=(
            cx + (r + 0.05) * np.cos(a + 0.25),
            cy + (r + 0.05) * np.sin(a + 0.25)),
            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=2, mutation_scale=16))
    ax.text(cx, cy, "TRAINING\nLOOP", ha="center", va="center", fontsize=12,
            fontweight="bold", color=BLUE)
    save(fig, "02_training_loop.png")


# ---------------------------------------------------------------- 3. A signal
def fig_signal():
    fig, ax = plt.subplots(figsize=(8, 3))
    t = np.linspace(0, 6, 600)
    healthy = 0.25 * np.sin(2 * np.pi * 3 * t) + 0.04 * np.random.randn(t.size)
    imbal = 1.0 * np.sin(2 * np.pi * 3 * t) + 0.15 * np.random.randn(t.size)
    ax.plot(t, healthy + 2, color=GREEN, lw=1.6, label="Healthy vibration")
    ax.plot(t, imbal - 1.5, color=RED, lw=1.6, label="Imbalanced vibration")
    ax.axhline(2, color=GREY, lw=0.6, ls="--"); ax.axhline(-1.5, color=GREY, lw=0.6, ls="--")
    ax.set_yticks([]); ax.set_xlabel("time (seconds)")
    ax.set_title("The same motor, two health states", fontsize=12, color=DARK)
    ax.legend(loc="upper right", fontsize=9)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    save(fig, "03_signals.png")


# ---------------------------------------------------------------- 4. Windowing
def fig_windowing():
    fig, ax = plt.subplots(figsize=(8, 3))
    t = np.linspace(0, 10, 1000)
    y = 0.5 * np.sin(1.6 * t) + 0.2 * np.sin(4.1 * t) + 0.05 * np.random.randn(t.size)
    ax.plot(t, y, color=DARK, lw=1.2)
    for start in [1, 2.2, 3.4, 4.6]:
        ax.axvspan(start, start + 1.8, color=BLUE, alpha=0.12 if start % 2 else 0.22)
        ax.annotate("window", xy=(start + 0.9, 0.95), fontsize=8, ha="center", color=BLUE)
    ax.set_xlabel("time (seconds)"); ax.set_yticks([])
    ax.set_title("Chop the stream into overlapping 1-second windows", fontsize=12, color=DARK)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    save(fig, "04_windowing.png")


# ---------------------------------------------------------------- 5. Normalise
def fig_normalise():
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    np.random.seed(3)
    raw = np.concatenate([np.random.normal(127, 30, 400), np.random.normal(320, 40, 400)])
    axes[0].hist(raw, bins=30, color=AMBER, edgecolor="white")
    axes[0].set_title("Raw values (current: mA)", fontsize=11, color=DARK)
    axes[0].set_xlabel("milliamps")
    norm = (raw - raw.mean()) / raw.std()
    axes[1].hist(norm, bins=30, color=BLUE, edgecolor="white")
    axes[1].set_title("After normalisation (mean 0, spread 1)", fontsize=11, color=DARK)
    axes[1].set_xlabel("standardised")
    save(fig, "05_normalise.png")


# ---------------------------------------------------------------- 6. Layers of a CNN
def fig_cnn_layers():
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    layers = [("Input\n5x50", BLUE), ("Conv\n(patterns)", GREEN),
              ("Pool\n(shrink)", AMBER), ("Conv+Pool\n(deeper)", GREEN),
              ("Flatten", GREY), ("Class\nscores", RED)]
    n = len(layers)
    for i, (txt, col) in enumerate(layers):
        x = 0.3 + i * 1.6
        box(ax, x, 1.2, 1.35, 1.3, txt, color=col, fc="#ffffff", fs=8.5)
        if i < n - 1:
            arrow(ax, x + 1.35, 1.85, x + 1.6, 1.85)
    ax.text(5, 3.3, "A small 1D CNN: find patterns \u2192 shrink \u2192 decide",
            ha="center", fontsize=12, color=DARK, fontweight="bold")
    save(fig, "06_cnn_layers.png")


# ---------------------------------------------------------------- 7. Overfitting
def fig_overfitting():
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    e = np.arange(1, 31)
    train = 1.1 * np.exp(-e / 8) + 0.04
    val = 1.1 * np.exp(-e / 6) + 0.12 + 0.004 * np.maximum(0, e - 14) ** 1.4
    ax.plot(e, train, color=BLUE, lw=2, label="training error")
    ax.plot(e, val, color=RED, lw=2, label="validation error")
    best = 14
    ax.axvline(best, color=GREY, ls="--", lw=1)
    ax.annotate("stop here\n(early stopping)", xy=(best, val[best - 1]),
                xytext=(best + 2, 0.55), fontsize=9, color=GREY,
                arrowprops=dict(arrowstyle="->", color=GREY))
    ax.set_xlabel("epochs (passes over the data)"); ax.set_ylabel("error")
    ax.set_title("Overfitting: training keeps improving, validation gets worse",
                 fontsize=10.5, color=DARK)
    ax.legend(fontsize=9)
    save(fig, "07_overfitting.png")


# ---------------------------------------------------------------- 8. Pipeline
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(9, 2.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis("off")
    steps = ["Collect\ndata", "Clean &\nwindow", "Train\nmodel", "Evaluate",
             "Compress\n(INT8)", "Deploy to\nESP32"]
    colors = [BLUE, BLUE, GREEN, AMBER, AMBER, RED]
    for i, (txt, col) in enumerate(zip(steps, colors)):
        x = 0.2 + i * 1.6
        box(ax, x, 0.8, 1.4, 1.3, txt, color=col, fc="#ffffff", fs=9)
        if i < len(steps) - 1:
            arrow(ax, x + 1.4, 1.45, x + 1.6, 1.45)
    ax.text(5, 2.55, "The ML pipeline \u2014 from raw sensor files to a working device",
            ha="center", fontsize=12, color=DARK, fontweight="bold")
    save(fig, "08_pipeline.png")


# ---------------------------------------------------------------- 9. Feature leakage
def fig_leakage():
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    np.random.seed(1)
    healthy_v = np.random.normal(6.020, 0.008, 60)
    fault_v = np.random.normal(6.002, 0.008, 60)
    ax.scatter(healthy_v, np.random.uniform(2.6, 3.4, 60), color=GREEN,
               label="Healthy (voltage ~6.02 V)", alpha=0.7, s=25)
    ax.scatter(fault_v, np.random.uniform(0.6, 1.4, 60), color=RED,
               label="Fault (voltage ~6.00 V)", alpha=0.7, s=25)
    ax.axvline(6.01, color=GREY, ls="--", lw=1)
    ax.annotate("model drew a line here\ninstead of learning vibration!",
                xy=(6.011, 2.0), xytext=(6.015, 1.9), fontsize=8.5, color=GREY)
    ax.set_yticks([]); ax.set_xlabel("supply voltage (V)")
    ax.set_title("Shortcut learning: voltage 'predicted' the fault", fontsize=11, color=DARK)
    ax.legend(fontsize=8.5, loc="center right")
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    save(fig, "09_leakage.png")


# ---------------------------------------------------------------- 10. Confusion matrix
def fig_confusion():
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    # rows = true, cols = predicted; a realistic 3-class result
    cm = np.array([[39, 0, 0],
                   [3, 36, 0],
                   [0, 2, 37]])
    labels = ["healthy", "imbalanced", "friction"]
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual (true)")
    for i in range(3):
        for j in range(3):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    fontsize=14, color=color, fontweight="bold")
    ax.set_title("Confusion matrix \u2014 every cell is a count", fontsize=11, color=DARK)
    save(fig, "10_confusion.png")


# ---------------------------------------------------------------- 11. Precision vs recall
def fig_precision_recall():
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
    # all items as dots: some truly faulty (red), some truly healthy (grey)
    positions = [(1, 4), (2, 4), (3, 4), (1, 3), (2, 3),
                 (6, 4), (7, 4), (8, 4), (6, 3), (7, 3), (8, 3), (9, 3)]
    faulty = {(1, 4), (2, 4), (6, 4), (7, 3), (9, 3)}
    for (x, y) in positions:
        c = RED if (x, y) in faulty else GREY
        ax.scatter(x, y, s=260, color=c, alpha=0.85, edgecolor="white", zorder=2)
    # the "model flagged" circle
    ax.add_patch(Circle((1.9, 3.9), 1.5, fill=False, edgecolor=BLUE, lw=2.2, ls="--"))
    ax.text(1.9, 1.7, "model said 'faulty'\n(this is what it flagged)", ha="center",
            fontsize=8.5, color=BLUE)
    ax.text(5, 4.7, "Precision: of the ones I flagged, how many were truly faulty?",
            ha="center", fontsize=9.5, color=DARK, fontweight="bold")
    ax.text(5, 0.4, "Recall: of all the truly faulty ones, how many did I catch?",
            ha="center", fontsize=9.5, color=DARK, fontweight="bold")
    ax.scatter([], [], s=120, color=RED, label="truly faulty")
    ax.scatter([], [], s=120, color=GREY, label="truly healthy")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    save(fig, "11_precision_recall.png")


# ---------------------------------------------------------------- 12. Data split
def fig_data_split():
    fig, ax = plt.subplots(figsize=(8, 1.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0.25), 70, 0.5, boxstyle="round,pad=0.01",
                                facecolor=GREEN, alpha=0.35, edgecolor=GREEN, lw=2))
    ax.add_patch(FancyBboxPatch((70.5, 0.25), 15, 0.5, boxstyle="round,pad=0.01",
                                facecolor=AMBER, alpha=0.35, edgecolor=AMBER, lw=2))
    ax.add_patch(FancyBboxPatch((86, 0.25), 14, 0.5, boxstyle="round,pad=0.01",
                                facecolor=RED, alpha=0.35, edgecolor=RED, lw=2))
    ax.text(35, 0.5, "TRAINING  (~70%)", ha="center", va="center", fontweight="bold", color="#1a7f37")
    ax.text(78, 0.5, "VALIDATION\n~15%", ha="center", va="center", fontweight="bold", color="#9a6700", fontsize=9)
    ax.text(93, 0.5, "TEST\n~15%", ha="center", va="center", fontweight="bold", color="#a40e26", fontsize=9)
    ax.text(50, 0.95, "Split your data: learn on one part, tune on another, judge on a third",
            ha="center", fontsize=10, color=DARK, fontweight="bold")
    ax.text(35, 0.1, "the model studies these", ha="center", fontsize=8, color=GREY)
    ax.text(78, 0.1, "check progress", ha="center", fontsize=8, color=GREY)
    ax.text(93, 0.1, "final exam", ha="center", fontsize=8, color=GREY)
    save(fig, "12_data_split.png")


# ---------------------------------------------------------------- 13. Learning rate
def fig_learning_rate():
    fig, axes = plt.subplots(1, 3, figsize=(9, 2.8))
    e = np.linspace(0, 10, 100)
    axes[0].plot(e, np.exp(-e * 1.2) * 1.0 + 0.02, color=GREEN, lw=2)
    axes[0].set_title("Good learning rate", fontsize=9.5, color="#1a7f37")
    axes[1].plot(e, np.exp(-e * 0.08) * 1.0 + 0.6, color=AMBER, lw=2)
    axes[1].set_title("Too small (slow, stuck)", fontsize=9.5, color="#9a6700")
    axes[2].plot(e, np.abs(np.sin(e * 2.2)) + 0.4, color=RED, lw=2)
    axes[2].set_title("Too big (bouncing, unstable)", fontsize=9.5, color="#a40e26")
    for ax in axes:
        ax.set_xlabel("training time"); ax.set_yticks([])
        ax.set_ylim(0, 2.0)
    axes[0].set_ylabel("error")
    fig.suptitle("The learning rate controls step size", fontsize=11, color=DARK,
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "13_learning_rate.png")


if __name__ == "__main__":
    fig_ml_concept()
    fig_training_loop()
    fig_signal()
    fig_windowing()
    fig_normalise()
    fig_cnn_layers()
    fig_overfitting()
    fig_pipeline()
    fig_leakage()
    fig_confusion()
    fig_precision_recall()
    fig_data_split()
    fig_learning_rate()
    print("all illustrations done")
