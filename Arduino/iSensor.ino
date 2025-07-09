#include <ArduinoJson.h>

// Version and hardware configuration
constexpr char VERSION[]               = "1.0.0";
constexpr uint32_t BAUD_RATE           = 115200;
constexpr uint8_t  PIN_CURRENT_1       = A0;
constexpr uint8_t  PIN_CURRENT_2       = A1;
constexpr uint8_t  PIN_CURRENT_3       = A2;

// Timing constants
constexpr unsigned long MICRO_DELAY    = 50UL;    // µs between loop iterations
constexpr unsigned long TIME_STEP_MS   = 160UL;   // ms between samples

// JSON field name
constexpr char JSON_DATA_FIELD[]       = "data";

// JSON document and output buffer
StaticJsonDocument<128> jsonDoc;
String jsonString;

// State for timing and LED blink
unsigned long previousTimeUs = 0;
bool ledState             = LOW;

// Conversion factor from analog reading to current (A)
constexpr float CURRENT_CONVERSION_FACTOR = 
    (5.0f     // ADC reference voltage (V)
   /1024.0f   // ADC resolution
   / 2.8f     // sensor internal gain/divider
   ) * 30.0f; // AC Current Sensor tention range (5A,10A,20A,30A)
void setup() {
  Serial.begin(BAUD_RATE);
  Serial.print(F("# Starting power meter v"));
  Serial.println(VERSION);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  unsigned long currentTimeUs = micros();
  const unsigned long stepUs = TIME_STEP_MS * 1000UL;

  if (currentTimeUs - previousTimeUs >= stepUs) {
    // Toggle onboard LED
    ledState = !ledState;
    digitalWrite(LED_BUILTIN, ledState);

    // Build JSON payload
    jsonDoc.clear();
    jsonDoc["millis"] = millis();
    JsonObject data = jsonDoc.createNestedObject(JSON_DATA_FIELD);
    data["I1"] = analogRead(PIN_CURRENT_1) * CURRENT_CONVERSION_FACTOR;
    data["I2"] = analogRead(PIN_CURRENT_2) * CURRENT_CONVERSION_FACTOR;
    data["I3"] = analogRead(PIN_CURRENT_3) * CURRENT_CONVERSION_FACTOR;

    // Serialize and send over Serial
    serializeJson(jsonDoc, jsonString);
    Serial.println(jsonString);

    previousTimeUs = currentTimeUs;
  }

  delayMicroseconds(MICRO_DELAY);
}
