// src/inference/src/main.cpp
//
// Phase 1 · Step 2 — Voltage divider + ESP32-C3 ADC calibration
//
// The ESP32-C3 ADC reference is not exactly 3.3 V — typical tolerance is
// 5–10%. We empirically calibrate with a DMM at one known supply voltage
// and apply ADC_CAL_FACTOR to all subsequent readings.
//
// Calibration procedure:
//   1. Set supply to 6.0 V (motor disconnected).
//   2. Read DMM at L298N +12V terminal → V_dmm.
//   3. Read average supply_v from Monitor → V_esp (before factor = 1.0).
//   4. Set ADC_CAL_FACTOR = V_dmm / V_esp.
//   5. Re-upload, verify |V_dmm − supply_v| ≤ 0.05 V.

#include <Arduino.h>

// Divider
const float DIV_R1 = 100000.0f;
const float DIV_R2 = 20000.0f;
const float DIV_FACTOR = (DIV_R1 + DIV_R2) / DIV_R2; // = 6.000

// ADC
const int PIN_VOLTAGE = 3;
const float ADC_VREF = 3.3f;
const int ADC_MAX = 4095;

// Calibration — updated from empirical DMM comparison on 2026-10-26.
// DMM supply: 6.00 V, ESP32 reported avg: 6.447 V → factor = 0.9307
const float ADC_CAL_FACTOR = 0.9307f;

uint32_t lastMs = 0;

void setup()
{
    Serial.begin(115200);
    delay(1500);

    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    lastMs = millis();
    Serial.println("timestamp_ms,raw,volts_at_pin,supply_v");
    Serial.println("# boot ok — step 2 voltage divider + ADC calibration");
}

void loop()
{
    uint32_t now = millis();
    if (now - lastMs < 1000)
        return;
    lastMs = now;

    int raw = analogRead(PIN_VOLTAGE);
    float volts = (raw / (float)ADC_MAX) * ADC_VREF;
    float supply = volts * DIV_FACTOR * ADC_CAL_FACTOR;

    Serial.print(now);
    Serial.print(',');
    Serial.print(raw);
    Serial.print(',');
    Serial.print(volts, 3);
    Serial.print(',');
    Serial.println(supply, 3);
}