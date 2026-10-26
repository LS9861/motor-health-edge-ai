// src/inference/src/main.cpp
//
// Phase 1 · Step 6 — Full combined data logger
// Streams all five sensor channels as one CSV line per 20 ms (50 Hz).
//
// Columns: timestamp_ms, ax, ay, az, current_mA, voltage_v, rpm
//   ax, ay, az      — MPU6500 accelerometer (m/s²)
//   current_mA      — INA228 current (milliamps, includes offset baseline)
//   voltage_v       — INA228 bus voltage (volts, at L298N +12V input)
//   rpm             — IR encoder, computed over 1-second window
//
// All sensors share I2C: SDA=GPIO0, SCL=GPIO1
//   MPU6500 (FastIMU)  @ 0x68
//   INA228             @ 0x40
//
// Motor control: L298N IN1=GPIO4, IN2=GPIO5, ENA jumper ON
// Full-speed forward = IN1 HIGH, IN2 LOW
//
// To run: open Monitor at 115200, send 'g' to start a 30-second motor-on
// capture (or 'g' to stop early). Send 'h' for a 30-second motor-off capture.
// Any other key stops the motor.

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_INA228.h>
#include "FastIMU.h"

Adafruit_INA228 ina228;
MPU6500 imu;
calData calib = {0};

const int PIN_IR = 10;
const int PIN_IN1 = 4;
const int PIN_IN2 = 5;
const int HOLES_PER_REV = 20;
const float INA_SHUNT_OHM = 0.015;
const float INA_MAX_CURRENT_A = 3.0;

volatile uint32_t pulseCount = 0;
uint32_t lastRpmWindow = 0;
uint32_t lastSample = 0;
float currentRpm = 0.0f;

// Motor state
bool motorRunning = false;
uint32_t motorStartMs = 0;
uint32_t motorDurationMs = 0;

void IRAM_ATTR onIrPulse()
{
    static uint32_t lastUs = 0;
    uint32_t nowUs = micros();
    if (nowUs - lastUs < 1000)
        return;
    lastUs = nowUs;
    pulseCount++;
}

void motorForward(bool on)
{
    if (on)
    {
        digitalWrite(PIN_IN1, HIGH);
        digitalWrite(PIN_IN2, LOW);
        motorRunning = true;
    }
    else
    {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, LOW);
        motorRunning = false;
    }
}

void setup()
{
    Serial.begin(115200);
    delay(1500);

    // Motor pins first — keep motor off at boot
    pinMode(PIN_IN1, OUTPUT);
    pinMode(PIN_IN2, OUTPUT);
    motorForward(false);

    // IR interrupt
    pinMode(PIN_IR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_IR), onIrPulse, RISING);

    // I2C
    Wire.begin(0, 1);
    Wire.setClock(400000);

    // INA228
    if (!ina228.begin())
    {
        Serial.println("ERROR: INA228 not found (0x40)");
        while (1)
            delay(1000);
    }
    ina228.setShunt(INA_SHUNT_OHM, INA_MAX_CURRENT_A);

    // MPU6500 via FastIMU
    int err = imu.init(calib, 0x68);
    if (err != 0)
    {
        Serial.print("ERROR: MPU6500 init err=");
        Serial.println(err);
        while (1)
            delay(1000);
    }
    imu.setAccelRange(8);

    Serial.println("# Phase 1 Step 6 ready");
    Serial.println("# Commands: g = start motor (30s), s = stop motor, h = motor-off capture (30s)");
    Serial.println("timestamp_ms,ax,ay,az,current_mA,voltage_v,rpm");

    lastRpmWindow = millis();
    lastSample = millis();
}

void loop()
{
    uint32_t now = millis();

    // Serial command handler
    if (Serial.available())
    {
        char c = Serial.read();
        if (c == 'g')
        {
            motorForward(true);
            motorStartMs = now;
            motorDurationMs = 30000; // 30 seconds
            Serial.println("# motor ON for 30s");
        }
        else if (c == 's')
        {
            motorForward(false);
            Serial.println("# motor OFF");
        }
        else if (c == 'h')
        {
            motorForward(false);
            Serial.println("# motor OFF — 30s capture window");
        }
    }

    // Auto-stop motor after duration
    if (motorRunning && (now - motorStartMs >= motorDurationMs))
    {
        motorForward(false);
        Serial.println("# motor auto-off");
    }

    // RPM calculation (1 second window)
    if (now - lastRpmWindow >= 1000)
    {
        noInterrupts();
        uint32_t p = pulseCount;
        pulseCount = 0;
        interrupts();
        currentRpm = (p * 60.0f) / HOLES_PER_REV;
        lastRpmWindow = now;
    }

    // 50 Hz sample
    if (now - lastSample < 20)
        return;
    lastSample = now;

    // Read accelerometer
    imu.update();
    AccelData accel;
    imu.getAccel(&accel);

    // Read current + voltage
    float current_mA = ina228.getCurrent_mA();
    float bus_V = ina228.getBusVoltage_V();

    // CSV row
    Serial.print(now);
    Serial.print(',');
    Serial.print(accel.accelX * 9.81f, 3);
    Serial.print(',');
    Serial.print(accel.accelY * 9.81f, 3);
    Serial.print(',');
    Serial.print(accel.accelZ * 9.81f, 3);
    Serial.print(',');
    Serial.print(current_mA, 2);
    Serial.print(',');
    Serial.print(bus_V, 3);
    Serial.print(',');
    Serial.println(currentRpm, 1);
}