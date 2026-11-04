# Live Visualization

Real-time monitoring of the ESP32-C3 motor rig during data collection and
Phase 7 verification. The firmware runs on-device inference; `plot_live.py`
displays what the device is actually predicting, while simultaneously
logging every prediction to disk.

![Live inference monitor](../results/figures/live_friction_20261104_140029.png)

*Four subplots: vibration magnitude, motor current, motor speed, and the
model's raw logits over time. The text box in the bottom plot shows the
current predicted class.*

## What the firmware actually sends

The firmware (`src/inference/src/main.cpp`) does on-device inference once per
**1-second window** (50 samples @ 50 Hz). It prints two lines per window:

    # RAW ax=<..> ay=<..> az=<..> current=<..> rpm=<..>   ← debug line, one per window
    <timestamp_ms>,<CLASS>,<s_h>,<s_i>,<s_f>,<rpm>       ← data line, one per window

- `<CLASS>` is `HEALTHY`, `IMBALANCED`, `FRICTION`, or `WAITING` (the first 3
  windows before the firmware's debouncer has confirmed a class).
- `<s_h>, <s_i>, <s_f>` are the raw logits for the three classes. They are
  **not** softmax probabilities — they can be negative and unbounded. The
  predicted class is `argmax` of these three values.
- The firmware also prints `# STATE CHANGE -> <CLASS>` when the debouncer
  changes state, and `# Motor ON` / `# Motor OFF` around the motor cycle.
  These are echoed to the terminal but not plotted.

**Baud rate is 115200** — this is set by `Serial.begin(115200)` in the
firmware. This differs from `log_data.py`'s hardcoded `921600`, which is
stale against the current firmware build.

## How to run

Close Arduino IDE serial monitor / PuTTY / miniterm first — only one process
can own a COM port on Windows.

    python scripts/plot_live.py <label> --port COM6

`<label>` must be one of `healthy`, `imbalanced`, `friction`. It records
**which physical condition you are exercising**, not what the firmware is
allowed to output. The firmware always runs full inference; the label is
written into the CSV so you can later verify "under real friction, the model
predicted FRICTION 94% of the time."

Examples:

    python scripts/plot_live.py healthy    --port COM6   # motor running normally
    python scripts/plot_live.py imbalanced --port COM6   # added unbalanced mass
    python scripts/plot_live.py friction   --port COM6   # added drag/friction load

Press Ctrl-C (or close the window) to stop. On a clean exit, the script
prints something like:

    Stopping...
    CSV:  data/raw/<label>_live_<timestamp>.csv  (N predictions, M raw)
    PNG:  results/figures/live_<label>_<timestamp>.png

## Interpreting each subplot

| # | Signal | Source | What it tells you |
|---|---|---|---|
| 1 | Vibration magnitude sqrt(ax^2+ay^2+az^2) | # RAW debug line | Overall vibration energy. Should stay roughly constant under steady load. |
| 2 | Motor current (mA) | # RAW debug line | Motor load. Friction raises current; imbalance causes small periodic variation. |
| 3 | Motor RPM | # RAW debug line | Confirms the motor is spinning during capture. Should track ~300 RPM under normal drive. |
| 4 | Model output (3 logits) + predicted class | data line | What the model is actually deciding. The higher the gap between s_healthy and s_friction, the more confident the prediction. |

The top suptitle updates to `predicted: <CLASS>` in the class color (HEALTHY =
green, IMBALANCED = orange, FRICTION = red) so you can read the current
prediction at a glance.

## Why it updates ~once per second

The firmware infers once per 50-sample window (1 second at 50 Hz). The plot
refreshes at 2 Hz so the GUI stays responsive, but new points only arrive at
1 Hz. **This is expected.** It is not a plot slowdown.

If you want a faster-looking monitor in the future, the fix is firmware-side:
print the # RAW debug line every sample (50 Hz) while keeping inference at
1 Hz. That is a separate change and not currently planned.

## CSV format

The CSV written by `plot_live.py` mirrors the data line exactly, plus a
provenance column:

    timestamp_ms, class, s_healthy, s_imbalanced, s_friction, rpm, label

Where `label` is the CLI argument (the physical condition you exercised).
This CSV is **not** the same format as `log_data.py`'s output — `log_data.py`
was written for a previous firmware that sent 7-field raw samples. See
"Known issues" below.

## Known issues

1. **`log_data.py` does not work with the current firmware.** The firmware
   now sends `timestamp_ms,class,s_h,s_i,s_f,rpm` (6 fields) plus # RAW ...
   debug lines, at 115200 baud. `log_data.py` expects 7 comma-separated
   fields at 921600 baud. Against the current binary it produces 0 rows.
   `plot_live.py` is the supported path for live capture.
2. **STATE CHANGE can flap during steady-state captures.** The firmware's
   debouncer requires 3 consecutive same-class windows; borderline logits can
   flip HEALTHY -> FRICTION -> HEALTHY for a few seconds. This is a real
   property of the model on ambiguous windows and is the sort of thing Phase 7
   extended verification should quantify (e.g. "under steady healthy load,
   how often does the predicted class flap, and how long until it settles?").
3. **Ctrl-C on Windows can print a Tkinter traceback.** The script catches
   `KeyboardInterrupt` at the top level; if you still see one, the `finally`
   block has already saved the CSV and PNG, so nothing is lost.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Could not open COM6: Access is denied | Another process owns the port | Close Arduino IDE serial monitor / PuTTY / another plot_live.py, then retry |
| Plot opens but stays empty | No data arriving | Check the motor is spinning (firmware calls motorOn() in setup); confirm baud 115200 in plot_live.py |
| Text box stays on WAITING | Firmware debouncer still buffering | Wait 3 s — the firmware confirms a class only after 3 same predictions in a row |
| Predicted class wrong despite correct label | Actual fault not induced, or sensors mis-mounted | Re-check the physical setup; the label records what you intended, not what the model should report |
| Plot feels sluggish | Expected at 1 Hz inference; ser.readline() timeout causes frame stalls | Already mitigated via timeout=0.05 in ser.readline(); see "Why it updates ~once per second" |