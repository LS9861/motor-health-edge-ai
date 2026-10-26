#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_INA228.h>

Adafruit_INA228 ina228;

// *** CRITICAL: Your Adafruit board has a 15 mΩ built-in shunt ***
const float SHUNT_RESISTANCE = 0.015; // 15 mΩ
const float MAX_CURRENT = 3.0;        // 3A is plenty for your TT motor

void setup()
{
    Serial.begin(115200);
    delay(1500);

    Wire.begin(0, 1); // SDA=0, SCL=1 (shared with MPU6050)

    if (!ina228.begin())
    {
        Serial.println("ERROR: INA228 not found. Check I2C wiring (addr 0x40).");
        while (1)
            delay(10);
    }
    Serial.println("INA228 found.");

    // Configure for the on-board 15mΩ shunt
    ina228.setShunt(SHUNT_RESISTANCE, MAX_CURRENT);
    ina228.setAveragingCount(INA228_COUNT_16);

    Serial.println("timestamp_ms,current_mA,bus_voltage_V");
}

void loop()
{
    uint32_t now = millis();

    float current_mA = ina228.getCurrent_mA();
    float bus_V = ina228.getBusVoltage_V();

    Serial.print(now);
    Serial.print(',');
    Serial.print(current_mA, 2);
    Serial.print(',');
    Serial.println(bus_V, 3);

    delay(1000);
}