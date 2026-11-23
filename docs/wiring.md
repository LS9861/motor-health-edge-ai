# Wiring — ESP32-C3 SuperMini + JGA25-370

> ESP32-C3 GPIOs are **3.3 V only** and its ADC saturates at ~3.3 V.
> Never feed 5 V sensor outputs into a GPIO.

> 🔁 This reflects the **current JGA25-370 build**. The original design used an
> ACS712 + resistor divider on the motor supply; that was retired in favour of
> the INA228 (see [`phase1_bringup.md`](phase1_bringup.md), archived).
> **Do not build the ACS712 version.**

## 1. MPU6050 — I2C (vibration)

| MPU6050 | ESP32-C3 | Note |
|---|---|---|
| VCC | 3V3 | **not 5 V** |
| GND | GND | |
| SDA | GPIO0 | onboard pull-ups OK; add 4.7k if bare chip |
| SCL | GPIO1 | same |

## 2. INA228 — current (and bus voltage, measured-but-unused)

| INA228 | ESP32-C3 / supply |
|---|---|
| VIN (logic) | 3V3 |
| GND | GND |
| SDA / SCL | GPIO0 / GPIO1 (shared I2C) |
| VIN+ | supply + (12–14 V) |
| VIN− | L298N +12V |
| VBUS | VIN+ (jumper closed) — voltage is measured but **not** a model input |

High-side measurement through the on-board 15 mΩ shunt. I2C address 0x40.

## 3. JGA25-370 built-in magnetic encoder — speed

| Signal | ESP32-C3 |
|---|---|
| Encoder VCC | 3V3 (check motor datasheet) |
| Encoder GND | GND |
| Encoder OUT (channel A) | GPIO10 (interrupt, FALLING) |

The magnetic encoder emits a pulse train as the shaft turns; RPM is computed in
firmware by counting pulses over a fixed window and dividing by pulses-per-rev.
**Confirm the pulses-per-rev constant (`HOLES_PER_REV` in `main.cpp`) against the
motor datasheet** — it must match the encoder you actually have or RPM will be
off by that ratio.

## 4. L298N motor driver

| L298N | ESP32-C3 / supply |
|---|---|
| VCC (logic) | 3V3 |
| GND | **common with ESP32 GND** |
| IN1 / IN2 | GPIO4 / GPIO5 |
| ENA | jumper ON (full speed) |
| +12V | motor supply + (12–14 V, via INA228) |
| GND (power) | supply − / common GND |

## 5. Safety inputs

| Signal | ESP32-C3 | Behaviour |
|---|---|---|
| E-Stop button | GPIO9 (INPUT_PULLUP, to GND) | Latching stop; also tripped by I²t overcurrent |
| Mode switch | GPIO8 (INPUT_PULLUP, to GND) | Manual lockout vs software (MQTT) control |

## 6. INA228 sanity check

1. Wire everything, motor off.
2. Flash firmware, open Serial Monitor @ 115200.
3. `current_mA` ≈ 0 with no load; `voltage_v` should read your 12–14 V rail.

## 7. Motor safety

- Don't stall the motor. For "friction", press **lightly** — the motor must still turn.
- L298N gets hot; ventilate or heatsink.
- 30–60 s per capture, then rest.
- Separate motor supply preferred; **common GND is mandatory**.
