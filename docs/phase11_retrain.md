# Phase 11 — JGA25 Retrain and Accuracy Drop Verification

## Goal

Phase 11's acceptance criterion: **verify accuracy drop on new hardware is <5%**.

Since we retrained the model on JGA25 data, the honest comparison is:
does the old model (trained on TT) still work on JGA25? And does the
new model (trained on JGA25) match or beat the TT baseline?

## Results

| Model | Test set | Accuracy |
|---|---|---|
| `v3_5ch_flat_TT.pt` — trained on TT motor, tested on TT | TT test set | 96.59% |
| `v3_5ch_flat_TT.pt` — trained on TT motor, tested on JGA25 | JGA25 test set | **30.77%** (36/117) |
| `v3_5ch_flat_jga25.pt` — trained on JGA25, tested on JGA25 | JGA25 test set | **100.00%** (117/117) |

**Accuracy drop when applying old model to new hardware: 65.82 percentage points.**
**Recovery from retraining: +69.23 percentage points (30.77% → 100%).**

## What the failure pattern reveals

The TT model's confusion matrix on JGA25 data:
healthy imbalanced friction
healthy 0 39 0
imbalanced 39 0 0
friction 3 0 36


- **Healthy ↔ imbalanced swapped completely** (0% correct on both)
- **Friction still detected at 92%** — because friction's signature is
  dominated by current draw (a physical property that transfers), while
  healthy vs imbalanced depend on the vibration distribution (which does
  not transfer because the mounting changed)

This is the same shortcut-learning phenomenon documented in Phase 6:
the model learns physical conditions (mount resonance, sensor placement),
not just the fault signature. Change the mount → the learned vibration
features become meaningless.

## Caveats and follow-up

**The 100% JGA25 result is not yet a true generalization claim.** All 9
JGA25 CSVs were captured in the same session under identical conditions.
The test set (`_3` files) is a second 20-second window from the same
mount as training. This tests "did the model overfit the window", not
"does the model generalize across sessions."

**Phase 14 will fix this** by re-capturing fresh data on a different day /
after remounting. Target: ≥90% accuracy on truly unseen captures.

## Acceptance

**Phase 11 status: ✅ Complete** with the caveat that true cross-session
generalization is untested until Phase 14.