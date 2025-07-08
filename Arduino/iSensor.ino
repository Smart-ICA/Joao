// Sensor type: SEN0211 (AC current sensor, 30 A range).
// Board type: Arduino Uno (ATmega328P).

#include <ArduinoJson.h>

// --- Configuration ---------------------------------------------------------

// Analog input pins for the three SEN0211 sensors
const int sensorPins[] = { A0, A1, A2 };
const int numSensors = sizeof(sensorPins) / sizeof(sensorPins[0]);

// Sensor and ADC parameters
#define SENSOR_RANGE_AMPS  30.0f   // sensor detection range (5, 10, or 20 A → set to 30 for SEN0211)
#define ADC_REF_VOLTAGE    5.0f    // analogReference voltage (V)
#define NUM_SAMPLES        5       // number of readings to average
#define PEAK_TO_RMS_FACTOR 0.707f  // conversion factor

// JSON document capacity (adjust if you add more fields)
StaticJsonDocument<256> jsonDoc;

// --- Functions -------------------------------------------------------------

// Read one sensor on the given analog pin and return current in amps (float)
float readAcCurrent(int pin) {
  uint32_t total = 0;
  for (int i = 0; i < NUM_SAMPLES; ++i) {
    total += analogRead(pin);
  }
  float averageReading = total / float(NUM_SAMPLES);

  // Convert ADC reading to Vrms (divide by 2× amplifier gain, scale for 10-bit ADC)
  float vrms = (averageReading * PEAK_TO_RMS_FACTOR / 1024.0f) * ADC_REF_VOLTAGE / 2.0f;

  // Scale to current based on sensor range
  return vrms * SENSOR_RANGE_AMPS;
}

// --- Setup & Main Loop ----------------------------------------------------

void setup() {
  Serial.begin(115200);
  analogReference(DEFAULT);
}

void loop() {
  // 1) Read all three currents
  float currents[numSensors];
  for (int i = 0; i < numSensors; ++i) {
    currents[i] = readAcCurrent(sensorPins[i]);
  }

  // 2) Build JSON: {"millis":1234,"data":{"I1":...,"I2":...,"I3":...}}
  jsonDoc.clear();
  jsonDoc["millis"] = millis();
  JsonObject data = jsonDoc.createNestedObject("data");

  for (int i = 0; i < numSensors; ++i) {
    char key[4];
    snprintf(key, sizeof(key), "I%d", i + 1);
    data[key] = currents[i];
  }

  // 3) Serialize and send over Serial
  serializeJson(jsonDoc, Serial);
  Serial.println();

  // 4) Small delay so host can keep up
  delay(100);
}
