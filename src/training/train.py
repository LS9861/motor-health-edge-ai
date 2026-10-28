#!/usr/bin/env python3
"""Phase 4 — train v2: 5-channel CNN + mean_rpm scalar."""

import json
import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dataset import get_dataloaders
from model import MotorCNN1DWithRPM

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CKPT_DIR = REPO_ROOT / "models" / "checkpoints"
FIG_DIR = REPO_ROOT / "results" / "figures"
REP_DIR = REPO_ROOT / "results" / "reports"
for d in (CKPT_DIR, FIG_DIR, REP_DIR):
    d.mkdir(parents=True, exist_ok=True)

LABELS = ["healthy", "imbalanced", "friction"]


def evaluate(model, loader, device):
    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for x_ts, x_rpm, y in loader:
            x_ts, x_rpm = x_ts.to(device), x_rpm.to(device)
            preds.append(model(x_ts, x_rpm).argmax(dim=1).cpu().numpy())
            targets.append(y.numpy())
    return np.concatenate(preds), np.concatenate(targets)


def plot_confusion(cm, path, title):
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(LABELS))); ax.set_yticks(range(len(LABELS)))
    ax.set_xticklabels(LABELS, rotation=45, ha="right"); ax.set_yticklabels(LABELS)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(title)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax); fig.tight_layout()
    fig.savefig(path, dpi=150); plt.close(fig)


def plot_loss(history, path, title):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(history["train_loss"], label="train")
    ax.plot(history["val_loss"], label="val")
    ax.set_xlabel("Epoch"); ax.set_ylabel("Loss"); ax.legend(); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main():
    torch.manual_seed(42); np.random.seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    train_loader, test_loader, meta = get_dataloaders(batch_size=32)
    print(f"Train: {meta['n_train']} | Test: {meta['n_test']} | in_channels={meta['in_channels']}")
    print(f"mean_rpm stats: mean={meta['rpm_mean']:.2f} std={meta['rpm_std']:.2f}")

    if meta["in_channels"] != 5:
        raise SystemExit(f"ERROR: expected 5 channels, got {meta['in_channels']}. Re-run preprocess.py.")

    model = MotorCNN1DWithRPM(in_channels=meta["in_channels"], n_classes=3).to(device)
    print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=1e-3, weight_decay=1e-3)

    best_val = float("inf"); best_state = None
    patience = 15; epochs_no_improve = 0; n_epochs = 80
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, n_epochs + 1):
        model.train(); running = 0.0
        for x_ts, x_rpm, y in train_loader:
            x_ts, x_rpm, y = x_ts.to(device), x_rpm.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x_ts, x_rpm), y)
            loss.backward(); optimizer.step()
            running += loss.item() * x_ts.size(0)
        train_loss = running / len(train_loader.dataset)

        model.eval(); val_loss = 0.0
        with torch.no_grad():
            for x_ts, x_rpm, y in test_loader:
                x_ts, x_rpm, y = x_ts.to(device), x_rpm.to(device), y.to(device)
                val_loss += criterion(model(x_ts, x_rpm), y).item() * x_ts.size(0)
        val_loss /= len(test_loader.dataset)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        marker = ""
        if val_loss < best_val - 1e-4:
            best_val = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
            marker = " ← best"
        else:
            epochs_no_improve += 1

        if epoch % 5 == 0 or marker:
            print(f"Epoch {epoch:3d} | train={train_loss:.4f} | val={val_loss:.4f}{marker}")

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch}.")
            break

    ckpt_path = CKPT_DIR / "v2_5ch_mean_rpm.pt"
    torch.save(best_state, ckpt_path)
    print(f"\nSaved checkpoint: {ckpt_path}")

    model.load_state_dict(best_state)
    preds, targets = evaluate(model, test_loader, device)

    acc = accuracy_score(targets, preds)
    cm = confusion_matrix(targets, preds)
    report = classification_report(targets, preds, target_names=LABELS, output_dict=True)

    print(f"\nFinal test accuracy: {acc:.4f}")
    print(f"Confusion matrix:\n{cm}")
    print("\nClassification report:")
    print(classification_report(targets, preds, target_names=LABELS))

    plot_confusion(cm, FIG_DIR / "v2_confusion.png", "Confusion matrix — v2 (5ch + mean_rpm)")
    plot_loss(history, FIG_DIR / "v2_loss_curve.png", "Training curve — v2")

    metrics = {
        "version": "v2_5ch_mean_rpm",
        "accuracy": float(acc),
        "per_class_f1": {k: float(v["f1-score"]) for k, v in report.items() if k in LABELS},
        "confusion_matrix": cm.tolist(),
        "history": history,
        "in_channels": int(meta["in_channels"]),
        "n_train": int(meta["n_train"]),
        "n_test": int(meta["n_test"]),
        "model_params": int(sum(p.numel() for p in model.parameters())),
        "rpm_stats": {"mean": meta["rpm_mean"], "std": meta["rpm_std"]},
    }
    with open(REP_DIR / "v2_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics: {REP_DIR / 'v2_metrics.json'}")


if __name__ == "__main__":
    main()