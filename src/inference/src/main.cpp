// src/inference/src/main.cpp
//
// Phase 6 — 5-channel model (no voltage). Vibration + current + RPM only.
// Model: v3_int8.tflite (5-channel INT8, int8 I/O).
//
// Debounce strategy:
//   - After motor starts, ignore the first 30 windows (startup surge).
//   - HEALTHY: 2 consecutive windows to confirm (fast return to safe state).
//   - FAULT (IMBALANCED/FRICTION): 3 consecutive windows to confirm.
//
// MQTT: rate-limited to 2s to avoid blocking the sampling loop.

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <Adafruit_INA228.h>
#include "FastIMU.h"

#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"

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
#define PIN_MANUAL_SW 8
#define PIN_ESTOP 9  // E-Stop button (Connect to GND when pressed)

// ---------- Sampling ----------
constexpr uint32_t SAMPLE_PERIOD_MS = 20;
constexpr int WINDOW_SIZE = 50;
constexpr int N_CHANNELS = 5;
constexpr int HOLES_PER_REV = 330;
constexpr float WINDOW_MS = (float)(WINDOW_SIZE * SAMPLE_PERIOD_MS);

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

// ---------- Mode + motor control globals ----------
String requestedMode = "SOFTWARE";
bool softwareMode = true;
bool motorRequestedOn = false;
bool isManualLocked = false;
bool estopTriggered = false;
const float MAX_CURRENT_MA = 1300.0f; // 1.5 Amps threshold for jam 

// ---------- MQTT Globals ----------
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// i^2t currnet controller
float thermalEnergy = 0.0f;          // Accumulated I²t value
const float I2T_TRIP_LIMIT = 4000000;  // Tune this threshold
const float I_RATED_MA = 300.0f;     // Normal running current (e.g., 200mA)
const float I2T_COOLING = 0.95f;     // How fast it "cools" when stopped

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
uint32_t motor_start_time = 0;

void motorOn()
{
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
    motor_is_on = true;
	motor_start_time = millis();
    Serial.println("# Motor ON");
}

void motorOff()
{
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
    motor_is_on = false;
    Serial.println("# Motor OFF");
}

// ---------- WiFi & MQTT Helpers ----------
void setupWiFi() {
    Serial.print("# Connecting to WiFi");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n# WiFi Connected. IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("\n# WiFi Failed. Running offline.");
    }
}

void reconnectMQTT() {
    if (WiFi.status() != WL_CONNECTED) return;
    if (mqttClient.connected()) return;
    static uint32_t last_mqtt_attempt = 0;
    if (millis() - last_mqtt_attempt < 5000) return;
    last_mqtt_attempt = millis();
    Serial.print("# Attempting MQTT connection...");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
        Serial.println("connected");
        mqttClient.subscribe("motor/health/cmd");
    } else {
        Serial.print("failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" (will try again later)");
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
    String topicStr = String(topic);
    
    if (topicStr == "motor/health/cmd") {
        // Block software commands if E-Stop is active
        if (estopTriggered) {
            Serial.println("# BLOCKED: E-Stop is active!");
            return;
        }
        if (msg == "1") {
            motorRequestedOn = true;
            Serial.println("# SW: Motor ON command received");
        } else if (msg == "0") {
            motorRequestedOn = false;
            Serial.println("# SW: Motor OFF command received");
        }
    }
}

// Helper: publish a JSON payload, rate-limited.
static uint32_t last_publish_ms = 0;
void publishIfDue(const char *cls, float s_h, float s_i, float s_f,
                  float rpm, float current, float voltage, uint32_t now)
{
    if (now - last_publish_ms < 2000) return;
    last_publish_ms = now;
    if (!mqttClient.connected()) return;
    char json[256];
    snprintf(json, sizeof(json),
        "{\"ts\":%lu,\"class\":\"%s\",\"s_healthy\":%.2f,\"s_imbalanced\":%.2f,"
        "\"s_friction\":%.2f,\"rpm\":%.0f,\"current\":%.1f,\"voltage\":%.2f}",
        now, cls, s_h, s_i, s_f, rpm, current, voltage);
    mqttClient.publish(MQTT_TOPIC, json);
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
    
    pinMode(PIN_ESTOP, INPUT_PULLUP);
    pinMode(PIN_MANUAL_SW, INPUT_PULLUP);

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(400000);

    pinMode(PIN_IR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_IR), onIrPulse, FALLING);

    if (!ina228.begin()) {
        Serial.println("ERROR: INA228 not found");
        while (true) delay(1000);
    }
    ina228.setShunt(0.015f, 3.0f);
    Serial.println("INA228 OK");

    if (imu.init(calib, 0x68) != 0) {
        Serial.println("ERROR: MPU6500 init failed");
        while (true) delay(1000);
    }
    imu.setAccelRange(8);
    Serial.println("MPU6500 OK");

    tensor_arena = (uint8_t *)malloc(TENSOR_ARENA_SIZE);
    if (tensor_arena == nullptr) {
        Serial.println("ERROR: Cannot allocate tensor arena");
        while (true) delay(1000);
    }
    Serial.println("Arena OK");

    tfl_model = tflite::GetModel(model_data);
    if (tfl_model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("ERROR: TFLite schema version mismatch");
        while (true) delay(1000);
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

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.println("ERROR: AllocateTensors failed");
        while (true) delay(1000);
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

    setupWiFi();
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(512);

    motorOff();
}

// ============================================================================
void loop()
{
    uint32_t now = millis();

    // --- 0. KEEP MQTT ALIVE ---
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    // --- 1. PUBLISH MODE STATUS (every 2s) ---
    static uint32_t last_mode_publish = 0;
    if (now - last_mode_publish > 2000) {
        last_mode_publish = now;
        if (mqttClient.connected()) {
            const char* modeStr = isManualLocked ? "MANUAL_LOCKED" : requestedMode.c_str();
            mqttClient.publish("motor/health/mode", modeStr);
            const char* estopStr = estopTriggered ? "ESTOP_ACTIVE" : "ESTOP_CLEAR";
            mqttClient.publish("motor/health/estop", estopStr);
        }
    }

    // ---------- 2. SAMPLE AT 50 Hz ----------
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
        window[window_idx][4] = 0.0f;
        window_idx++;
    }

    if (window_idx < WINDOW_SIZE)
        return;

    // ---------- 3. COMPUTE RPM WITH VOLTAGE COMPENSATION ----------
    static uint32_t last_rpm_read_ms = 0;
    uint32_t rpm_elapsed_ms = now - last_rpm_read_ms;
    last_rpm_read_ms = now;

    noInterrupts();
    uint32_t pulses = pulse_count;
    pulse_count = 0;
    interrupts();

    float raw_rpm = 0.0f;
    if (rpm_elapsed_ms >= 500 && rpm_elapsed_ms <= 3000) {
        raw_rpm = pulses * (60000.0f / (float)rpm_elapsed_ms) / HOLES_PER_REV;
    }

    float voltage = ina228.getBusVoltage_V();
    float rpm_scale = 290.0f / 250.0f; // 12V default
    if (voltage > 13.0f) {
        rpm_scale = 1.0f;
    } else if (voltage > 12.5f) {
        rpm_scale = 1.08f;
    }
    float rpm = raw_rpm * rpm_scale;

    for (int t = 0; t < WINDOW_SIZE; t++)
        window[t][4] = rpm;

    // ---------- 4. RAW DIAGNOSTIC ----------
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

    // ---------- 5. MOTOR CONTROL & STATE MACHINE ----------
    static int standby_count = 0;
    static int on_count = 0;

        // --- EMERGENCY STOP & I²t CURRENT PROTECTION ---
    bool estopButtonPressed = (digitalRead(PIN_ESTOP) == LOW);
    bool physicalSwitchOn = (digitalRead(PIN_MANUAL_SW) == LOW);
    bool currentJam = false; // <--- DECLARE THIS HERE

    // Read current
    float current_mA = window[0][3];

    // I²t Integration
    if (motor_is_on) {
        if (millis() - motor_start_time > 1500) {
            float current_mA = window[0][3];
            float excess = current_mA - I_RATED_MA;
            
            // DEBUG PRINT
            Serial.print("# DBG current=");
            Serial.print(current_mA);
            Serial.print(" rated=");
            Serial.print(I_RATED_MA);
            Serial.print(" excess=");
            Serial.print(excess);
            
            if (excess > 0.0f) {
                thermalEnergy += (excess * excess) * 1.0f; 
                Serial.println(" -> HEATING");
            } else {
                thermalEnergy *= I2T_COOLING; 
                if (thermalEnergy < 1000.0f) {
                    thermalEnergy = 0.0f; // Reset to zero if it's safe
                }
                Serial.println(" -> COOLING");
            }
            
            Serial.print("# I2T Energy: ");
            Serial.println(thermalEnergy);

            if (thermalEnergy > I2T_TRIP_LIMIT) {
                currentJam = true; 
                thermalEnergy = I2T_TRIP_LIMIT; 
            }
        }
    } else {
        thermalEnergy *= 0.90f;
        if (thermalEnergy < 1.0f) thermalEnergy = 0.0f;
    }

    // 1. Trigger E-Stop (Latching)
    if (estopButtonPressed || currentJam) {
        if (!estopTriggered) {
            estopTriggered = true;
            Serial.println("# EMERGENCY STOP TRIGGERED (E-Stop or Jam)!");
        }
    }

    // 2. Clear E-Stop (Only if the toggle is OFF AND current is normal AND thermal energy has cooled)
    if (estopTriggered) {
        if (!estopButtonPressed && thermalEnergy < (I2T_TRIP_LIMIT * 0.5f)) {
            estopTriggered = false;
            Serial.println("# EMERGENCY STOP CLEARED");
        }
    }

    // 3. Manual Switch Override
    if (physicalSwitchOn) {
        softwareMode = false;
        requestedMode = "MANUAL";
        isManualLocked = true;
        motorRequestedOn = false;
    } else {
        softwareMode = true;
        requestedMode = "SOFTWARE";
        isManualLocked = false;
    }

    // 4. Decide if motor should run
    bool shouldRun = false;
    if (estopTriggered) {
        shouldRun = false; // FORCE MOTOR OFF
        motorRequestedOn = false;
        thermalEnergy = 0.0f; // Reset energy on hard stop (optional)
    } else if (softwareMode) {
        shouldRun = motorRequestedOn; 
    } else {
        shouldRun = physicalSwitchOn; 
    }

    if (shouldRun && !motor_is_on) {
        motorOn();
    } else if (!shouldRun && motor_is_on) {
        motorOff();
    }

    // ---------- 6. STANDBY / WAITING gate ----------
    const bool motor_off = (rpm < 10.0f) && (window[0][3] < 50.0f);

    if (motor_off) {
        standby_count++;
        on_count = 0;
        if (standby_count >= 2) {
            Serial.printf("%lu,STANDBY,0,0,0,%.0f\n", now, rpm);
            publishIfDue("STANDBY", 0, 0, 0, rpm, 0, 0, now);
            window_idx = 0;
            return;
        }
    } else {
        standby_count = 0;
        on_count++;
        if (on_count <= 30) {
            Serial.printf("%lu,WAITING,0,0,0,%.0f\n", now, rpm);
            publishIfDue("WAITING", 0, 0, 0, rpm, window[0][3], voltage, now);
            window_idx = 0;
            return;
        }
    }

    // ---------- 7. NORMALIZE + QUANTIZE TO INT8 ----------
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

    // ---------- 8. INVOKE MODEL ----------
    uint32_t t_infer_start_us = micros();
    if (interpreter->Invoke() != kTfLiteOk)
    {
        Serial.println("ERROR: Invoke failed");
        window_idx = 0;
        return;
    }
    uint32_t t_infer_end_us = micros();
    Serial.printf("# INVOKE_US,%lu\n", t_infer_end_us - t_infer_start_us);

    // ---------- 9. READ INT8 OUTPUT & DEBOUNCE ----------
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

    if (confirmed_class == -1) {
        Serial.printf("%lu,WAITING,%.2f,%.2f,%.2f,%.0f\n",
                      now, logits[0], logits[1], logits[2], rpm);
    } else {
        Serial.printf("%lu,%s,%.2f,%.2f,%.2f,%.0f\n",
                      now, labels[confirmed_class],
                      logits[0], logits[1], logits[2], rpm);
    }

    // ---------- 10. PUBLISH PREDICTION ----------
    publishIfDue(
        (confirmed_class == -1) ? "WAITING" : labels[confirmed_class],
        logits[0], logits[1], logits[2],
        rpm, window[0][3], voltage, now
    );

    window_idx = 0;
}