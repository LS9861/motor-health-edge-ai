# Documentation Index

## Current build — JGA25-370 (built-in magnetic encoder)

- [`phase10_jga25.md`](phase10_jga25.md) — JGA25-370 rebuild: motor/encoder specs,
  mount, and the 12–14 V data-collection protocol.
- [`phase11_retrain.md`](phase11_retrain.md) — TT→JGA25 transfer failure (30.77%),
  retrain, recovery to 100%, and the cross-session caveat.
- [`phase12_inference_time.md`](phase12_inference_time.md) — on-device inference
  timing (27.9 ms median, 94% CPU headroom).
- [`phase12_mqtt_dashboard.md`](phase12_mqtt_dashboard.md) — MQTT telemetry,
  Node-RED dashboard, and E-Stop / I²t safety interlocks.
- [`wiring.md`](wiring.md) — current wiring (MPU6050 + INA228 + JGA25 encoder + L298N).
- [`visualization.md`](visualization.md) — live inference monitor (`plot_live.py`).

## Archived — TT motor era (kept for the engineering lessons)

- [`phase1_bringup.md`](phase1_bringup.md) — original TT-motor bring-up log, sensor
  calibration, ACS712→INA228 decision, data-collection protocol.
- [`phase6_deployment.md`](phase6_deployment.md) — 1D-CNN training, INT8
  quantization, TFLM deployment, and the **voltage shortcut-learning** case study.

> Phases 2–5 are covered inside `phase6_deployment.md`. The TT→JGA25 migration
> (Phases 10–12) is the current, deployed state; the TT docs remain as the
> narrative that explains *why* the final design is what it is.
