// src/inference/src/main.cpp
//
// Phase 6 — 5-channel model (no voltage). Vibration + current + RPM only.
// Model: v3_int8.tflite (5-channel INT8, int8 I/O).
//
// Debounce strategy:
//   - After motor starts (from STANDBY or boot), ignore the first 3 windows
//     (they contain the motor startup surge — current spike, vibration
//     transient — which the model misclassifies).
//   - HEALTHY: 2 consecutive windows to confirm (fast return to safe state).
//   - FAULT (IMBALANCED/FRICTION): 3 consecutive windows to confirm
//     (prevents single-window flicker from noise).

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
constexpr int N_CHANNELS = 5;
constexpr int HOLES_PER_REV = 330;
constexpr float WINDOW_MS = (float)(WINDOW_SIZE * SAMPLE_PERIOD_MS);

// ---------- Motor cycle ----------
constexpr uint32_t MOTOR_ON_MS = 30000;
constexpr uint32_t MOTOR_OFF_MS = 10000;

// ---------- TFLM ----------
constexpr int TENSOR_ARENA_SIZE = 32 * 1024;
uint8_t *tensor_arena = nullptr;

const tflite::Model *tfl_model = nullptr;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *input_tensor = nullptr;
TfLiteTensor *output_tensor = nullptr;

// ---------- Sensors ----------
Adafruit_INA228 ina228;
MPU6500 imu;
calData calib = {0};

// ---------- IR pulse counter (200us debounce) ----------
volatile uint32_t pulse_count = 0;
void IRAM_ATTR onIrPulse()
{
    static uint32_t last_us = 0;
    uint32_t now_us = micros();
    if (now_us - last_us < 200)
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
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
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

    static tflite::MicroMutableOpResolver<24> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddAveragePool2D();
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

    Serial.print("# INPUT: type=");
    Serial.print(input_tensor->type);
    Serial.print(" bytes=");
    Serial.println(input_tensor->bytes);

    Serial.print("# OUTPUT: type=");
    Serial.print(output_tensor->type);
    Serial.print(" bytes=");
    Serial.println(output_tensor->bytes);

    Serial.println("=== SETUP COMPLETE ===");
    Serial.println("timestamp_ms,class,s_healthy,s_imbalanced,s_friction,rpm");

    motorOn();
}

// ============================================================================
void loop()
{
    uint32_t now = millis();

    // ---------- Sample at 50 Hz ----------
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
        window[window_idx][4] = 0.0f; // rpm filled later

        window_idx++;
    }

    if (window_idx < WINDOW_SIZE)
        return;

    // ---------- Compute RPM with voltage compensation ----------
    noInterrupts();
    uint32_t pulses = pulse_count;
    pulse_count = 0;
    interrupts();
    float raw_rpm = pulses * (60000.0f / WINDOW_MS) / HOLES_PER_REV;

    float voltage = ina228.getBusVoltage_V();
    float rpm_scale = 290.0f / 250.0f; // 12V default
    if (voltage > 13.0f) {
        rpm_scale = 1.0f;              // 14V
    } else if (voltage > 12.5f) {
        rpm_scale = 1.08f;             // 13V
    }
    float rpm = raw_rpm * rpm_scale;

    for (int t = 0; t < WINDOW_SIZE; t++)
        window[t][4] = rpm;

    // ---------- RAW diagnostic ----------
    Serial.print("# RAW ax=");
    Serial.print(window[0][0], 3);
    Serial.print(" ay=");
    Serial.print(window[0][1], 3);
    Serial.print(" az=");
    Serial.print(window[0][2], 3);
    Serial.print(" current=");
    Serial.print(window[0][3], 1);
    Serial.print(" voltage=");
    Serial.print(voltage, 2);
    Serial.print(" rpm=");
    Serial.println(rpm, 0);

    // ---------- STANDBY gate + startup grace period ----------
    // State machine:
    //   MOTOR_OFF (rpm~0, current~0)  -> STANDBY after 2 windows
    //   MOTOR_ON                      -> WAITING for first 3 windows (startup surge)
    //   MOTOR_RUNNING                 -> run inference, apply debouncer
    static int standby_count = 0;
    static int on_count = 0;
    const bool motor_off = (rpm < 10.0f) && (window[0][3] < 50.0f);

    if (motor_off) {
        standby_count++;
        on_count = 0;
        if (standby_count >= 2) {
            Serial.printf("%lu,STANDBY,0,0,0,%.0f\n", now, rpm);
            window_idx = 0;
            return;
        }
    } else {
        standby_count = 0;
        on_count++;
        // Ignore first 3 windows after start — startup surge misclassifies
        if (on_count <= 30) {
            Serial.printf("%lu,WAITING,0,0,0,%.0f\n", now, rpm);
            window_idx = 0;
            return;
        }
    }

    // ---------- Normalize + quantize to int8 ----------
    int8_t *input_i8 = (int8_t *)input_tensor->data.int8;
    const float in_scale = input_tensor->params.scale;
    const int32_t in_zero = input_tensor->params.zero_point;
    for (int c = 0; c < N_CHANNELS; c++)
    {
        for (int t = 0; t < WINDOW_SIZE; t++)
        {
            float norm = (window[t][c] - NORM_MEAN[c]) / NORM_STD[c];
            int32_t q = (int32_t)roundf(norm / in_scale) + in_zero;
            if (q < -128) q = -128;
            if (q > 127)  q = 127;
            input_i8[c * WINDOW_SIZE + t] = (int8_t)q;
        }
    }

    // ---------- Invoke ----------
    uint32_t t_infer_start_us = micros();
    if (interpreter->Invoke() != kTfLiteOk)
    {
        Serial.println("ERROR: Invoke failed");
        window_idx = 0;
        return;
    }
    uint32_t t_infer_end_us = micros();
    Serial.printf("# INVOKE_US,%lu\n", t_infer_end_us - t_infer_start_us);

    // ---------- Read int8 output ----------
    int8_t *output_i8 = (int8_t *)output_tensor->data.int8;
    const float out_scale = output_tensor->params.scale;
    const int32_t out_zero = output_tensor->params.zero_point;
    float logits[3] = {
        (float)(output_i8[0] - out_zero) * out_scale,
        (float)(output_i8[1] - out_zero) * out_scale,
        (float)(output_i8[2] - out_zero) * out_scale,
    };

    const char *labels[] = {"HEALTHY", "IMBALANCED", "FRICTION"};
    int best = 0;
    for (int i = 1; i < 3; i++)
        if (logits[i] > logits[best])
            best = i;

    // ---- Debouncer: healthy needs 2, faults need 3 ----
    static int confirmed_class = -1;
    static int streak_count = 0;
    static int last_pred = -1;

    if (best == last_pred) {
        if (streak_count < 3) streak_count++;
    } else {
        streak_count = 1;
        last_pred = best;
    }

    int required_streak = (best == 0) ? 2 : 3;

    if (streak_count >= required_streak && confirmed_class != best) {
        confirmed_class = best;
        Serial.print("# STATE CHANGE -> ");
        Serial.println(labels[confirmed_class]);
    }

    if (confirmed_class == -1)
    {
        Serial.printf("%lu,WAITING,%.2f,%.2f,%.2f,%.0f\n",
                      now, logits[0], logits[1], logits[2], rpm);
    }
    else
    {
        Serial.printf("%lu,%s,%.2f,%.2f,%.2f,%.0f\n",
                      now, labels[confirmed_class],
                      logits[0], logits[1], logits[2], rpm);
    }

    window_idx = 0;
}