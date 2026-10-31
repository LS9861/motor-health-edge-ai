// src/inference/src/main.cpp
//
// PHASE 6 — Full firmware. Motor + sensors + TFLM inference.
// Debug RAW print removed.
//
// Motor cycle: 30s ON (forward) → 10s OFF → repeat.
// Model: v3_motor_health_int8.tflite (13.3 KB, dynamic-range INT8, float32 I/O).
//
// Float buffers accessed via data.raw because this TFLM build's
// TfLitePtrUnion does not expose 'f32'.

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <Adafruit_INA228.h>
#include "FastIMU.h"

#include "model_data.h"
#include "norm_params.h"

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// ---------- Pins ----------
#define PIN_I2C_SDA 0
#define PIN_I2C_SCL 1
#define PIN_IR 10
#define PIN_IN1 4
#define PIN_IN2 5

// ---------- Sampling ----------
constexpr uint32_t SAMPLE_PERIOD_MS = 20;
constexpr int WINDOW_SIZE = 50;
constexpr int N_CHANNELS = 6;
constexpr int HOLES_PER_REV = 20;
constexpr float WINDOW_MS = (float)(WINDOW_SIZE * SAMPLE_PERIOD_MS);

// ---------- Motor cycle ----------
constexpr uint32_t MOTOR_ON_MS = 30000;
constexpr uint32_t MOTOR_OFF_MS = 10000;

// ---------- TFLM ----------
constexpr int TENSOR_ARENA_SIZE = 16 * 1024;
uint8_t *tensor_arena = nullptr;

const tflite::Model *tfl_model = nullptr;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *input_tensor = nullptr;
TfLiteTensor *output_tensor = nullptr;

// ---------- Sensors ----------
Adafruit_INA228 ina228;
MPU6500 imu;
calData calib = {0};

// ---------- IR with 1 ms debounce ----------
volatile uint32_t pulse_count = 0;
void IRAM_ATTR onIrPulse()
{
    static uint32_t last_us = 0;
    uint32_t now_us = micros();
    if (now_us - last_us < 1000)
        return;
    last_us = now_us;
    pulse_count++;
}

// ---------- Window buffer ----------
float window[WINDOW_SIZE][N_CHANNELS];
int window_idx = 0;

// ---------- Motor state ----------
bool motor_is_on = false;
uint32_t motor_since = 0;

void motorOn()
{
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, HIGH);
    motor_is_on = true;
    motor_since = millis();
    Serial.println("# Motor ON");
}

void motorOff()
{
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
    motor_is_on = false;
    motor_since = millis();
    Serial.println("# Motor OFF");
}

void motorCycle()
{
    uint32_t elapsed = millis() - motor_since;
    if (motor_is_on && elapsed >= MOTOR_ON_MS)
        motorOff();
    if (!motor_is_on && elapsed >= MOTOR_OFF_MS)
        motorOn();
}

// ============================================================================
void setup()
{
    Serial.begin(115200);
    delay(2000);
    Serial.println("\n=== BOOT START ===");

    pinMode(PIN_IN1, OUTPUT);
    pinMode(PIN_IN2, OUTPUT);
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(400000);

    pinMode(PIN_IR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_IR), onIrPulse, FALLING);

    if (!ina228.begin())
    {
        Serial.println("ERROR: INA228 not found");
        while (true)
            delay(1000);
    }
    ina228.setShunt(0.015f, 3.0f);
    Serial.println("INA228 OK");

    if (imu.init(calib, 0x68) != 0)
    {
        Serial.println("ERROR: MPU6500 init failed");
        while (true)
            delay(1000);
    }
    imu.setAccelRange(8);
    Serial.println("MPU6500 OK");

    tensor_arena = (uint8_t *)malloc(TENSOR_ARENA_SIZE);
    if (tensor_arena == nullptr)
    {
        Serial.println("ERROR: Cannot allocate tensor arena");
        while (true)
            delay(1000);
    }
    Serial.println("Arena OK");

    tfl_model = tflite::GetModel(model_data);
    if (tfl_model->version() != TFLITE_SCHEMA_VERSION)
    {
        Serial.println("ERROR: TFLite schema version mismatch");
        while (true)
            delay(1000);
    }
    Serial.println("Model OK");

    static tflite::MicroMutableOpResolver<16> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddFullyConnected();
    resolver.AddReshape();
    resolver.AddRelu();
    resolver.AddQuantize();
    resolver.AddDequantize();
    resolver.AddSoftmax();
    resolver.AddTranspose();
    resolver.AddMean();
    resolver.AddAdd();
    resolver.AddMul();

    static tflite::MicroInterpreter static_interp(
        tfl_model, resolver, tensor_arena, TENSOR_ARENA_SIZE);
    interpreter = &static_interp;

    if (interpreter->AllocateTensors() != kTfLiteOk)
    {
        Serial.println("ERROR: AllocateTensors failed");
        while (true)
            delay(1000);
    }
    Serial.println("Tensors OK");

    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);

    if (input_tensor->type != kTfLiteFloat32 || output_tensor->type != kTfLiteFloat32)
    {
        Serial.println("ERROR: tensor types not float32");
        while (true)
            delay(1000);
    }
    Serial.println("Tensors confirmed float32.");

    Serial.println("=== SETUP COMPLETE ===");
    Serial.println("timestamp_ms,class,s_healthy,s_imbalanced,s_friction,rpm");

    motorOn();
}

// ============================================================================
void loop()
{
    motorCycle();

    uint32_t now = millis();

    static uint32_t last_sample_ms = 0;
    if (now - last_sample_ms >= SAMPLE_PERIOD_MS)
    {
        last_sample_ms = now;

        imu.update();
        AccelData acc;
        imu.getAccel(&acc);
        window[window_idx][0] = acc.accelX * 9.81f;
        window[window_idx][1] = acc.accelY * 9.81f;
        window[window_idx][2] = acc.accelZ * 9.81f;

        window[window_idx][3] = ina228.getCurrent_mA();
        window[window_idx][4] = ina228.getBusVoltage_V();
        window[window_idx][5] = 0.0f;

        window_idx++;
    }

    if (window_idx < WINDOW_SIZE)
        return;

    noInterrupts();
    uint32_t pulses = pulse_count;
    pulse_count = 0;
    interrupts();
    float rpm = pulses * (60000.0f / WINDOW_MS) / HOLES_PER_REV;

    for (int t = 0; t < WINDOW_SIZE; t++)
        window[t][5] = rpm;

    float *input_f32 = (float *)input_tensor->data.raw;
    for (int c = 0; c < N_CHANNELS; c++)
    {
        for (int t = 0; t < WINDOW_SIZE; t++)
        {
            float v = (window[t][c] - NORM_MEAN[c]) / NORM_STD[c];
            input_f32[c * WINDOW_SIZE + t] = v;
        }
    }

    // DEBUG
    Serial.print("# IN[0..5] = ");
    for (int k = 0; k < 6; k++)
    {
        Serial.print(input_f32[k], 4);
        Serial.print(' ');
    }
    Serial.println();
    Serial.printf("# RAW_DBG window[0][0]=%.4f mean=%.4f std=%.4f\n",
                  window[0][0], NORM_MEAN[0], NORM_STD[0]);

    if (interpreter->Invoke() != kTfLiteOk)
    {
        Serial.println("ERROR: Invoke failed");
        window_idx = 0;
        return;
    }

    float *output_f32 = (float *)output_tensor->data.raw;
    float logits[3];
    for (int i = 0; i < 3; i++)
        logits[i] = output_f32[i];

    const char *labels[] = {"HEALTHY", "IMBALANCED", "FRICTION"};
    int best = 0;
    for (int i = 1; i < 3; i++)
        if (logits[i] > logits[best])
            best = i;

    Serial.printf("%lu,%s,%.2f,%.2f,%.2f,%.0f\n",
                  now, labels[best], logits[0], logits[1], logits[2], rpm);

    window_idx = 0;
}