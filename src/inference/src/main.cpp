// src/inference/src/main.cpp
//
// Phase 1 · Step 1 — "Hello, CSV" bring-up test
// Goal: prove USB-CDC serial works on the ESP32-C3 SuperMini.
// No sensors, no motor, no extra libraries.
//
// Success criteria:
//   • Header line appears immediately after upload.
//   • One new CSV row every ~1 second.
//   • The last field (fake "rpm") increments: 1.0, 2.0, 3.0, ...

#include <Arduino.h>

uint32_t lastMs = 0;
uint32_t rowId = 0;

void setup()
{
    Serial.begin(115200);

    // Native USB-CDC needs a moment for the host to attach.
    // Without this delay the first prints can be lost.
    delay(1500);

    lastMs = millis();

    // Same header shape as the real firmware — keeps downstream
    // logger/preprocessing code compatible later.
    Serial.println("timestamp_ms,ax,ay,az,current_a,voltage_v,rpm");
    Serial.println("# boot ok — step 1 serial test");
}

void loop()
{
    uint32_t now = millis();

    if (now - lastMs >= 1000)
    {
        lastMs = now;
        rowId++;

        Serial.print(now);
        Serial.print(',');
        Serial.print(0.000, 3);
        Serial.print(',');
        Serial.print(0.000, 3);
        Serial.print(',');
        Serial.print(9.810, 3);
        Serial.print(',');
        Serial.print(0.000, 3);
        Serial.print(',');
        Serial.print(0.000, 3);
        Serial.print(',');
        Serial.println(rowId, 1);
    }
}