// src/inference/src/collect_raw.cpp
// Raw 50 Hz data collection for JGA25-370 + ESP32-C3.
// NO inference. NO averaging. Prints every sample for preprocess.py.
// Pins: I2C SDA=0 SCL=1, L298N IN1=4 IN2=5, Encoder A=10 B=3
// CPR = 330 (11 PPR x 30 gear, A-phase rising edges)
// Baud: 921600
//
// KEY DIFFERENCES from previous version:
//   - No 25s delay — firmware is ready ~2s after boot.
//   - First RPM value is computed BEFORE first data row is printed.
//   - Motor must be flipped ON manually by user, and stabilized for 5s
//     before running collect_csv.py. This is now a user responsibility,
//     not a firmware responsibility.

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_INA228.h>
#include "FastIMU.h"

#define PIN_I2C_SDA 0
#define PIN_I2C_SCL 1
#define PIN_IN1 4
#define PIN_IN2 5
#define PIN_ENC_A 10
#define PIN_ENC_B 3

constexpr uint32_t SAMPLE_PERIOD_MS = 20; // 50 Hz
constexpr int WINDOW_SIZE = 50;
constexpr float ENCODER_CPR = 330.0f;
constexpr float WINDOW_MS = (float)(WINDOW_SIZE * SAMPLE_PERIOD_MS);

Adafruit_INA228 ina228;
MPU6500 imu;
calData calib = {0};

volatile uint32_t pulses_A = 0;
void IRAM_ATTR onEncA()
{
    static uint32_t last_us = 0;
    uint32_t now = micros();
    if (now - last_us < 200)
        return;
    last_us = now;
    pulses_A++;
}

uint32_t last_sample = 0;
uint32_t last_rpm_calc = 0;
float current_rpm = 0;

void setup()
{
    Serial.begin(921600);
    delay(500);
    Serial.println("# COLLECT_RAW READY");

    pinMode(PIN_IN1, OUTPUT);
    pinMode(PIN_IN2, OUTPUT);
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(400000);

    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), onEncA, RISING);

    if (!ina228.begin())
    {
        Serial.println("# ERROR: INA228 not found");
        while (true)
            delay(1000);
    }
    ina228.setShunt(0.015f, 3.0f);
    Serial.println("# INA228 OK");

    if (imu.init(calib, 0x68) != 0)
    {
        Serial.println("# ERROR: MPU6500 init failed");
        while (true)
            delay(1000);
    }
    imu.setAccelRange(8);
    Serial.println("# MPU6500 OK");

    // Motor ON. User flips physical switch; this is just the L298N direction.
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
    Serial.println("# Motor ON");

    // First 1-second of pulses -> initial RPM.
    // This ensures the very first data row has a real RPM, not 0.
    Serial.println("# Computing initial RPM (1 s)...");
    noInterrupts();
    pulses_A = 0;
    interrupts();
    delay(1000);
    noInterrupts();
    uint32_t pa = pulses_A;
    pulses_A = 0;
    interrupts();
    current_rpm = (pa * (60000.0f / WINDOW_MS)) / ENCODER_CPR;
    Serial.printf("# Initial RPM = %.1f\n", current_rpm);

    last_rpm_calc = millis();
    last_sample = millis();

    Serial.println("timestamp_ms,ax,ay,az,current_mA,rpm");
    Serial.println("# COLLECTING");
}

void loop()
{
    uint32_t now = millis();

    // Compute RPM every 1 s
    if (now - last_rpm_calc >= 1000)
    {
        last_rpm_calc = now;
        noInterrupts();
        uint32_t pa = pulses_A;
        pulses_A = 0;
        interrupts();
        current_rpm = (pa * (60000.0f / WINDOW_MS)) / ENCODER_CPR;
    }

    // Sample at 50 Hz
    if (now - last_sample >= SAMPLE_PERIOD_MS)
    {
        last_sample = now;

        imu.update();
        AccelData acc;
        imu.getAccel(&acc);
        float ax = acc.accelX * 9.81f;
        float ay = acc.accelY * 9.81f;
        float az = acc.accelZ * 9.81f;
        float cur = ina228.getCurrent_mA();

        Serial.printf("%lu,%.3f,%.3f,%.3f,%.1f,%.1f\n",
                      now, ax, ay, az, cur, current_rpm);
    }
}