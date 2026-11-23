## motor-health-edge-ai {VERSION}

Motor health classifier for the **ESP32-C3**, using a 5-channel 1D-CNN
(vibration `ax/ay/az` + current + RPM) quantised to INT8 TFLite and deployed via
TensorFlow Lite Micro on a **JGA25-370** gear motor with a built-in magnetic
encoder (12–14 V).

### Artifacts
- **merged_firmware-*.bin** — **flash this** (bootloader + partitions + app; flash at `0x0`)
- **model_data-*.h** — C header for rebuilding from source
- **v3_int8-*.tflite** — quantised INT8 model for external use

### Model (deployed: `v3_5ch_flat_jga25`)
- 1D-CNN, 963 params, ~5.6 KB INT8
- Test accuracy **100% (117/117)** — INT8 lossless
- Inference **27.9 ms median** on ESP32-C3 @ 160 MHz (~94% CPU headroom)

> ⚠️ **Generalization caveat.** The 100% figure is measured on a second
> 20-second window from the **same capture session** as training — it proves the
> model did not overfit the training window, **not** cross-session/day
> generalization. See `docs/phase11_retrain.md`. Cross-session validation is the
> Phase 14 target.

### Highlights
- **TT → JGA25-370 migration.** The project began on a ~6 V TT motor; rebuilt
  around the JGA25-370 (magnetic encoder, 12–14 V). A TT-trained model dropped to
  30.77% on the new rig and was retrained back to 100% — see
  `docs/phase11_retrain.md`.
- **Shortcut-learning diagnosis.** An earlier 6-channel model leaked supply
  voltage and collapsed on hardware; dropping voltage (6ch → 5ch) raised accuracy
  and robustness — see `docs/phase6_deployment.md`.
- **Safety interlocks.** Latching E-Stop, I²t overcurrent protection, and
  manual/software mode — plus MQTT telemetry and a Node-RED dashboard
  (`docs/phase12_mqtt_dashboard.md`, `mqtt/flows.json`).

### Flashing instructions

```bash
# 1. Erase (recommended when switching firmware)
python -m esptool --chip esp32c3 --port COM6 erase-flash

# 2. Flash the merged binary at 0x0
python -m esptool --chip esp32c3 --port COM6 -b 460800 write-flash 0x0 merged_firmware-{VERSION}.bin
