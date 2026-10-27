#!/usr/bin/env python3
"""Phase 3 — train v1 1D-CNN on 5-channel preprocessed windows."""

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
from model import MotorCNN1D

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CKPT_DIR = REPO_ROOT / "models" / "checkpoints"
FIG_DIR  = REPO_ROOT / "results" / "figures"
REP_DIR  = REPO_ROOT / "results" / "reports"
for d in (CKPT_DIR, FIG_DIR, REP_DIR):
    d.mkdir(parents=True, exist_ok=True)

LABELS = ["healthy", "imbalanced", "friction"]


def evaluate(model, loader, device):
    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            preds.append(model(x).argmax(dim=1).cpu().numpy())
            targets.append(y.numpy())
    return np.concatenate(preds), np.concatenate(targets)


def plot_confusion(cm, path):
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(LABELS))); ax.set_yticks(range(len(LABELS)))
    ax.set_xticklabels(LABELS, rotation=45, ha="right"); ax.set_yticklabels(LABELS)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Confusion matrix — v1 (5ch)")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax); fig.tight_layout()
    fig.savefig(path, dpi=150); plt.close(fig)


def plot_loss(history, path):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(history["train_loss"], label="train")
    ax.plot(history["val_loss"], label="val")
    ax.set_xlabel("Epoch"); ax.set_ylabel("Loss"); ax.legend()
    ax.set_title("Training curve — v1")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main():
    torch.manual_seed(42); np.random.seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    train_loader, test_loader, (X_train, y_train, X_test, y_test) = get_dataloaders(batch_size=32)

    # --- Guard against stale .npy ---
    in_channels = X_train.shape[2]
    print(f"Train: {len(X_train)} | Test: {len(X_test)} | in_channels={in_channels}")
    if in_channels != 5:
        raise SystemExit(
            f"ERROR: in_channels={in_channels}, expected 5. "
            f"You are loading stale .npy files. Run preprocess.py first."
        )

    model = MotorCNN1D(in_channels=in_channels, n_classes=3).to(device)
    print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=1e-3, weight_decay=1e-3)

    best_val = float("inf"); best_state = None
    patience = 15; epochs_no_improve = 0; n_epochs = 80
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, n_epochs + 1):
        model.train(); running = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward(); optimizer.step()
            running += loss.item() * x.size(0)
        train_loss = running / len(train_loader.dataset)

        model.eval(); val_loss = 0.0
        with torch.no_grad():
            for x, y in test_loader:
                x, y = x.to(device), y.to(device)
                val_loss += criterion(model(x), y).item() * x.size(0)
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

    ckpt_path = CKPT_DIR / "v1_5ch_baseline.pt"
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

    plot_confusion(cm, FIG_DIR / "v1_confusion.png")
    plot_loss(history, FIG_DIR / "v1_loss_curve.png")

    metrics = {
        "version": "v1_5ch_baseline",
        "accuracy": float(acc),
        "per_class_f1": {k: float(v["f1-score"]) for k, v in report.items() if k in LABELS},
        "confusion_matrix": cm.tolist(),
        "history": history,
        "in_channels": int(in_channels),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "model_params": int(sum(p.numel() for p in model.parameters())),
    }
    with open(REP_DIR / "v1_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics: {REP_DIR / 'v1_metrics.json'}")


if __name__ == "__main__":
    main()