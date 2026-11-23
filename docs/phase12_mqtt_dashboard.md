# Phase 12 — MQTT Telemetry + Node-RED Dashboard

> **Phase 12 has two parts:**
> - **12A — On-device inference timing** → [`phase12_inference_time.md`](phase12_inference_time.md)
>   (27.9 ms median forward pass on ESP32-C3).
> - **12B — Remote monitoring (this doc):** MQTT telemetry, Node-RED dashboard,
>   and the safety interlocks (E-Stop, I²t, manual lockout) that the firmware
>   exposes over MQTT.

## Architecture

```
 JGA25 rig                                         your PC / LAN
 ┌──────────────────────┐        Wi-Fi            ┌───────────────────┐
 │ ESP32-C3              │  publish (2 s)          │  Mosquitto broker  │
 │  • TFLM inference (1Hz)│ ───────────────────────▶│  (Docker, :1883)   │
 │  • debounce + STANDBY  │  subscribe: cmd         │                    │
 │  • E-Stop / I²t        │◀─────────────────────── │                    │
 └──────────────────────┘                         └─────────┬──────────┘
                                                            │
                                                   ┌────────▼─────────┐
                                                   │  Node-RED + Dash  │
                                                   │  http://:1880/ui  │
                                                   └───────────────────┘
```

- **ESP32-C3:** runs INT8 TFLite Micro inference and publishes a JSON telemetry
  payload; also subscribes to a command topic for software motor control.
- **Mosquitto:** MQTT broker, runs in Docker (`mqtt/docker-compose.yml`, `:1883`,
  anonymous, no persistence — fine for a bench LAN).
- **Node-RED:** dashboard/subscriber UI (`npx -y node-red`, dashboard at `/ui`).

## Configuration (`src/inference/src/secrets.h`)

Copy `src/inference/src/secrets_example.h` → `secrets.h` (git-ignored) and set:

```c
#define WIFI_SSID     "Your_WiFi_Name"
#define WIFI_PASSWORD "Your_WiFi_Password"
#define MQTT_HOST     "192.168.1.100"   // IP of the PC running Mosquitto/Node-RED
#define MQTT_PORT     1883
#define MQTT_TOPIC    "motor/health/state"
```

`MQTT_HOST` must be the LAN IP of the machine running the broker (Node-RED can
run on the same host). Do **not** point it at `localhost` from the ESP32.

## MQTT topics

| Topic | Direction | Rate | Payload |
|---|---|---|---|
| `motor/health/state` | ESP32 → broker (publish, `MQTT_TOPIC`) | every 2 s | JSON (below) |
| `motor/health/mode` | ESP32 → broker (publish) | every 2 s | `SOFTWARE` \| `MANUAL_LOCKED` |
| `motor/health/estop` | ESP32 → broker (publish) | every 2 s | `ESTOP_ACTIVE` \| `ESTOP_CLEAR` |
| `motor/health/cmd` | broker → ESP32 (subscribe) | on demand | `"1"` = motor ON, `"0"` = motor OFF |

**State payload** (`motor/health/state`):

```json
{"ts":123456,"class":"HEALTHY","s_healthy":4.21,"s_imbalanced":-1.02,
 "s_friction":-3.10,"rpm":292,"current":127.4,"voltage":12.6}
```

- `class` ∈ `HEALTHY | IMBALANCED | FRICTION | WAITING | STANDBY`
  (`WAITING` = debouncer buffering / startup grace; `STANDBY` = motor off).
- `s_*` are **raw logits**, not probabilities (can be negative/unbounded).

Publishing is **rate-limited to once per 2 s** in firmware (`publishIfDue`) so the
network stack never blocks the 50 Hz sampling loop.

## Node-RED flow

No working `flows.json` is committed yet (the dashboard is built locally), but a
starter flow is provided at [`mqtt/flows.json`](../mqtt/flows.json). To use it you
need the standard palette plus `node-red-dashboard`:

```
npm i -g node-red node-red-dashboard
```

The dashboard has these pieces:

| Widget / node | Type | Topic / source | Notes |
|---|---|---|---|
| **Class indicator** | `ui_text` (or `ui_template`) | subscribe `motor/health/state` | Show `msg.payload.class`, colour it: HEALTHY=green, IMBALANCED=orange, FRICTION=red, WAITING/STANDBY=grey |
| **Current gauge** | `ui_gauge` | `motor/health/state` → `current` | Range 0–1500 mA; red zone > 1000 mA |
| **RPM gauge** | `ui_gauge` | `motor/health/state` → `rpm` | Range 0–400; expect ~250–300 under load |
| **Voltage gauge** | `ui_gauge` | `motor/health/state` → `voltage` | Range 10–15 V |
| **Mode LED** | `ui_text` | subscribe `motor/health/mode` | `SOFTWARE`=blue, `MANUAL_LOCKED`=purple |
| **E-Stop LED** | `ui_text` | subscribe `motor/health/estop` | `ESTOP_CLEAR`=green, `ESTOP_ACTIVE`=red |
| **Motor ON / OFF** | `ui_button` → `mqtt out` | publish `motor/health/cmd` | ON sends `"1"`, OFF sends `"0"`; disable while `MANUAL_LOCKED` or `ESTOP_ACTIVE` |

Import [`mqtt/flows.json`](../mqtt/flows.json) (Node-RED menu → Import → Clipboard),
then set the broker IP in the `mosquitto` broker config node to match `MQTT_HOST`.

## Hardware interlocks (exposed via MQTT + local GPIO)

| Input | GPIO | Behaviour |
|---|---|---|
| **Manual switch** | GPIO8 (to GND) | **Absolute priority.** Forces `MANUAL_LOCKED`; disables software/MQTT motor commands. |
| **E-Stop button** | GPIO9 (to GND) | Latched stop; instantly cuts the motor. Clears only when the switch is released **and** thermal energy has cooled below 50% of trip. |
| **Software cmd** | MQTT `motor/health/cmd` | Motor ON/OFF when in SOFTWARE mode and E-Stop clear; blocked while `estopTriggered`. |

## Safety features

- **I²t thermal / jam protection.** Above the rated current
  (`I_RATED_MA = 300 mA`), the firmware accumulates `excess²` per loop
  (`I2T_TRIP_LIMIT = 4,000,000`) and **latches the E-Stop** when tripped — a
  jammed motor cuts out in ~3.3 s to protect the L298N. Cooling (`×0.95`/loop)
  drains the accumulator when current is normal.
- **Startup grace period.** The first **1.5 s** after motor start is excluded
  from I²t integration, so inrush current does not cause a false trip.
- **Debounce before acting.** Fault classes require 3 consecutive windows,
  HEALTHY requires 2 — plus `STANDBY`/`WAITING` gating, this is what makes the
  2 s MQTT stream stable enough for a dashboard.

## Running it

```bash
# 1. Install Node-RED + dashboard (once)
npm i -g node-red node-red-dashboard

# 2. Start the broker
cd mqtt && docker compose up -d

# 3. Start Node-RED (dashboard at http://localhost:1880/ui)
node-red

# 4. Flash firmware with your secrets.h, then watch telemetry:
mosquitto_sub -h <broker-ip> -t 'motor/health/#' -v
```

Open the dashboard from your PC (`http://localhost:1880/ui`) or from a phone on
the same LAN (`http://<pc-lan-ip>:1880/ui`).

## Future work

- Standalone web server on the ESP32 itself (offline local control, no PC).
- Persist telemetry to InfluxDB for long-term trend logging.
- Push alerts (Telegram / email) on `FRICTION` / `IMBALANCED` states.
- Broker authentication (currently anonymous — bench-LAN only).
- Commit the working `flows.json` so the dashboard is one-click reproducible.
