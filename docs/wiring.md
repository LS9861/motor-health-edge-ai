# Wiring — ESP32-C3 SuperMini

> ESP32-C3 GPIOs are **3.3 V only** and its ADC saturates at ~3.3 V.
> Never feed 5 V sensor outputs into a GPIO.

## 1. MPU6050 — I2C

| MPU6050 | ESP32-C3 | Note |
|---|---|---|
| VCC | 3V3 | **not 5 V** |
| GND | GND | |
| SDA | GPIO0 | onboard pull-ups OK; add 4.7k if bare chip |
| SCL | GPIO1 | same |

## 2. ACS712 current sensor

**Preferred:** power ACS712 from **3.3 V**, output sits near 1.65 V at 0 A and stays inside the ADC range.
**If you must use 5 V:** add a 1:1 resistor divider (e.g. 10k/10k) on OUT before the ADC pin.

| ACS712 | ESP32-C3 |
|---|---|
| VCC | 3V3 (see above) |
| GND | GND |
| OUT | GPIO2 (ADC1_CH2) |
| IP+ / IP- | in series with motor supply (high side) |

## 3. Voltage divider (motor supply)

R1 = 100 kΩ from V+ to midpoint, R2 = 22 kΩ from midpoint to GND.
Vout = V+ · R2/(R1+R2) → 12 V supply ≈ 2.16 V at GPIO3. Safe.

## 4. IR speed sensor

| Module | ESP32-C3 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| OUT | GPIO10 (interrupt, FALLING) |

One reflective marker on the shaft → one pulse/rev → RPM as computed in firmware.

## 5. L298N motor driver

| L298N | ESP32-C3 / supply |
|---|---|
| VCC (logic) | 3V3 |
| GND | **common with ESP32 GND** |
| IN1 | GPIO4 |
| IN2 | GPIO5 |
| ENA | jumper ON (full speed) |
| +12V | motor battery + |
| GND (power) | motor battery − / common GND |

## 6. ACS712 zero calibration (do this once)

1. Wire everything. **Do not power the motor.**
2. Flash firmware, open Serial Monitor @ 115200.
3. Read `current_a` — with no load it must be ≈ 0.000.
   If not, adjust `ACS712_ZERO_V` in `src/inference/src/main.cpp`
   (and `configs/sensors.yaml`) until it does.

## 7. Motor safety

- Don't stall the motor. For "friction", press cardboard **lightly** — the motor must still turn.
- L298N gets hot; ventilate or heatsink.
- 30–60 s per capture, then rest.
- Separate motor supply preferred; **common GND is mandatory**.