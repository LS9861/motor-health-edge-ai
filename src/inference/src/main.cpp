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

bool motorStarted = false;
bool motorStopped = false;
uint32_t bootTime = 0;
uint32_t motorStartTime = 0;

void IRAM_ATTR onIrPulse()
{
    static uint32_t lastUs = 0;
    uint32_t nowUs = micros();
    if (nowUs - lastUs < 1000)
        return;
    lastUs = nowUs;
    pulseCount++;
}

void setup()
{
    Serial.begin(921600); // FASTER BAUD RATE (Update Python script to 921600)
    delay(1000);

    pinMode(PIN_IN1, OUTPUT);
    pinMode(PIN_IN2, OUTPUT);
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);

    pinMode(PIN_IR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_IR), onIrPulse, RISING);

    Wire.begin(0, 1);
    Wire.setClock(400000);

    if (!ina228.begin())
    {
        Serial.println("ERROR: INA228 not found!");
        while (1)
            delay(1000);
    }
    ina228.setShunt(INA_SHUNT_OHM, INA_MAX_CURRENT_A);

    int err = imu.init(calib, 0x68);
    if (err != 0)
    {
        Serial.print("ERROR: MPU6500 init err=");
        Serial.println(err);
        while (1)
            delay(1000);
    }
    imu.setAccelRange(8);

    // Increase the wait to 10 seconds! This gives you time to start Python.
    Serial.println("# Setup complete. Waiting 10 seconds...");
    Serial.println("timestamp_ms,ax,ay,az,current_mA,voltage_v,rpm");

    bootTime = millis();
    lastRpmWindow = millis();
    lastSample = millis();
}

void loop()
{
    uint32_t now = millis();

    // Start motor after 10 seconds
    if (!motorStarted && (now - bootTime > 10000))
    {
        digitalWrite(PIN_IN1, HIGH);
        digitalWrite(PIN_IN2, LOW);
        motorStartTime = millis();
        motorStarted = true;
        Serial.println("# Motor ON (30s capture)");
    }

    // Stop motor after 30 seconds
    if (motorStarted && !motorStopped && (now - motorStartTime > 30000))
    {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, LOW);
        motorStopped = true;
        Serial.println("# Motor OFF (spin-down)");
    }

    // RPM calculation
    if (now - lastRpmWindow >= 1000)
    {
        noInterrupts();
        uint32_t p = pulseCount;
        pulseCount = 0;
        interrupts();
        currentRpm = (p * 60.0f) / HOLES_PER_REV;
        lastRpmWindow = now;
    }

    // 50 Hz sample rate
    if (now - lastSample < 20)
        return;
    lastSample = now;

    imu.update();
    AccelData accel;
    imu.getAccel(&accel);
    float current_mA = ina228.getCurrent_mA();
    float bus_V = ina228.getBusVoltage_V();

    Serial.print(now);
    Serial.print(',');
    Serial.print(accel.accelX * 9.81f, 2);
    Serial.print(','); // 2 decimals instead of 3
    Serial.print(accel.accelY * 9.81f, 2);
    Serial.print(',');
    Serial.print(accel.accelZ * 9.81f, 2);
    Serial.print(',');
    Serial.print(current_mA, 1);
    Serial.print(',');
    Serial.print(bus_V, 2);
    Serial.print(',');
    Serial.println(currentRpm, 1);
}