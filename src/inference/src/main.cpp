// src/inference/src/main.cpp
//
// Phase 1 · Step 4 — MPU6500 (MPU6050 clone) vibration sensor
//
// Hardware: GY-521 module with MPU6500 chip (WHO_AM_I = 0x70, not 0x68).
// Adafruit MPU6050 library rejects clones; FastIMU handles them.
//
// Units: FastIMU returns acceleration in g. Firmware converts to m/s²
// so CSV column names match configs/sensors.yaml (unit: m_s2).
//
// Shared I2C bus with INA228 (0x40), SDA=GPIO0, SCL=GPIO1.

#include <Arduino.h>
#include <Wire.h>
#include "FastIMU.h"

calData calib = {0};
MPU6500 imu;

uint32_t lastMs = 0;

void setup()
{
    Serial.begin(115200);
    delay(1500);

    Wire.begin(0, 1);
    Wire.setClock(400000);

    int err = imu.init(calib, 0x68);
    if (err != 0)
    {
        Serial.print("IMU init error: ");
        Serial.println(err);
        while (true)
            delay(1000);
    }
    Serial.println("MPU6500 initialized (FastIMU).");

    // ±8 g range — matches configs/sensors.yaml
    imu.setAccelRange(8);

    lastMs = millis();
    Serial.println("timestamp_ms,ax,ay,az");
}

void loop()
{
    uint32_t now = millis();
    if (now - lastMs < 20)
        return; // 50 Hz
    lastMs = now;

    imu.update();
    AccelData accel;
    imu.getAccel(&accel);

    // Convert g → m/s² to match sensors.yaml declaration
    Serial.print(now);
    Serial.print(',');
    Serial.print(accel.accelX * 9.81f, 3);
    Serial.print(',');
    Serial.print(accel.accelY * 9.81f, 3);
    Serial.print(',');
    Serial.println(accel.accelZ * 9.81f, 3);
}