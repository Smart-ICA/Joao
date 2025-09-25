/*
This is a multi-sensor Arduino sketch that reads temperature, accelerometer data,
vibration, and loudness, then sends the data as a JSON string over Serial.

This code is designed to work with the MCP9808 high precision temperature sensor (I2C),
ADXL-345 Grove accelerometer (I2C), and an Grove analog loudness sensor (A0).
*/

#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_MCP9808.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

// ==============================
// Version and hardware
// ==============================
constexpr char     VERSION[]         = "1.1.0";
constexpr uint32_t BAUD_RATE         = 115200;

// Pins
constexpr uint8_t  PIN_LOUDNESS      = A0;     // Analog loudness sensor

// ADC reference (adjust if using 3.3V boards)
constexpr float    ADC_REF_V         = 5.0f;

// ==============================
// Timing
// ==============================
constexpr unsigned long MICRO_DELAY  = 100UL;   // µs between loop iterations
constexpr unsigned long TIME_STEP_MS = 100UL;   // ms between samples (10 Hz output)

// ==============================
// JSON
// ==============================
constexpr char JSON_DATA_FIELD[] = "data";
StaticJsonDocument<256> jsonDoc;   // a bit larger for extra fields
String jsonString;

// ==============================
// Sensors
// ==============================
Adafruit_MCP9808          tempSensor;
Adafruit_ADXL345_Unified  accel(12345);

// ==============================
// Vibration (high-pass + RMS)
// ==============================
// Exponential moving average to estimate gravity per axis (in g)
float gBiasX = 0.0f, gBiasY = 0.0f, gBiasZ = 1.0f;  // start near 1 g on Z
constexpr float BIAS_ALPHA = 0.02f;                 // EMA coefficient (smaller = slower)

// RMS window for high-passed acceleration magnitude (in g)
constexpr uint8_t VIB_WIN = 16;                     // ~1.6 s at 10 Hz
float vibSqBuf[VIB_WIN] = {0};
uint8_t vibIdx = 0;
float vibSqSum = 0.0f;

// ==============================
// State
// ==============================
unsigned long previousTimeUs = 0;
bool ledState = LOW;

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) { delay(1); }

  Serial.print(F("# Starting multi-sensor node v"));
  Serial.println(VERSION);
  pinMode(LED_BUILTIN, OUTPUT);

  // --- MCP9808 (Temperature) ---
  if (!tempSensor.begin(0x18)) {
    Serial.println(F("{\"error\":\"MCP9808 not found. Check I2C wiring.\"}"));
    while (1) { delay(10); }
  }
  // Highest resolution for best precision: 0.0625 °C (conversion time ~250 ms)
  tempSensor.setResolution(3);

  // --- ADXL345 (Accelerometer) ---
  if (!accel.begin()) {
    Serial.println(F("{\"error\":\"ADXL345 not found. Check I2C wiring.\"}"));
    while (1) { delay(10); }
  }
  accel.setRange(ADXL345_RANGE_16_G);
  // Reasonable data rate; library exposes common steps
  accel.setDataRate(ADXL345_DATARATE_200_HZ);
}

void pushVibrationSample(float hpMagG) {
  const float sq = hpMagG * hpMagG;
  // Remove oldest, add newest (circular buffer)
  vibSqSum -= vibSqBuf[vibIdx];
  vibSqBuf[vibIdx] = sq;
  vibSqSum += sq;
  vibIdx = (vibIdx + 1) % VIB_WIN;
}

float readTemperatureC_precise() {
  // Optional light averaging to reduce jitter while keeping precision
  // (MCP9808 already precise; this smooths last-bit flicker)
  float t = 0.0f;
  constexpr uint8_t N = 2;
  for (uint8_t i = 0; i < N; ++i) t += tempSensor.readTempC();
  return t / N;
}

void loop() {
  const unsigned long nowUs = micros();
  const unsigned long stepUs = TIME_STEP_MS * 1000UL;

  if (nowUs - previousTimeUs >= stepUs) {
    previousTimeUs = nowUs;

    // Blink LED
    ledState = !ledState;
    digitalWrite(LED_BUILTIN, ledState);

    // --- Temperature (°C) with high precision ---
    const float tC = readTemperatureC_precise();

    // --- Accelerometer (read, convert to g, high-pass, vibration) ---
    sensors_event_t evt;
    accel.getEvent(&evt);

    // Convert from m/s^2 to g
    const float xg = evt.acceleration.x / SENSORS_GRAVITY_EARTH;
    const float yg = evt.acceleration.y / SENSORS_GRAVITY_EARTH;
    const float zg = evt.acceleration.z / SENSORS_GRAVITY_EARTH;

    // Update gravity bias (EMA) and compute high-pass components
    gBiasX = (1.0f - BIAS_ALPHA) * gBiasX + BIAS_ALPHA * xg;
    gBiasY = (1.0f - BIAS_ALPHA) * gBiasY + BIAS_ALPHA * yg;
    gBiasZ = (1.0f - BIAS_ALPHA) * gBiasZ + BIAS_ALPHA * zg;

    const float hx = xg - gBiasX;
    const float hy = yg - gBiasY;
    const float hz = zg - gBiasZ;

    // High-pass magnitude (g)
    const float hpMag = sqrtf(hx*hx + hy*hy + hz*hz);

    // Maintain RMS window
    pushVibrationSample(hpMag);
    const float vibRms = sqrtf(vibSqSum / VIB_WIN);

    // --- Loudness (raw + volts) ---
    const int   loudRaw = analogRead(PIN_LOUDNESS);
    const float loudV   = loudRaw * (ADC_REF_V / 1023.0f);

    // --- Build JSON payload (same structure as your example) ---
    jsonDoc.clear();
    jsonDoc["millis"] = millis();

    JsonObject data = jsonDoc.createNestedObject(JSON_DATA_FIELD);
    data["temp_c"]        = tC;                 // precise temperature
    data["accel_x_g"]     = xg;                 // raw accel in g
    data["accel_y_g"]     = yg;
    data["accel_z_g"]     = zg;
    data["vibration_g_rms"]= vibRms;            // vibration indicator (RMS, high-pass)
    data["loud_raw"]      = loudRaw;            // loudness sensor
    data["loud_v"]        = loudV;

    // Serialize and send
    serializeJson(jsonDoc, jsonString);
    Serial.println(jsonString);
  }

  delayMicroseconds(MICRO_DELAY);
}
