#include <ArduinoJson.h>

// ==============================
// Configuration
// ==============================
#define VERSION     "1.2.0"
#define BAUD_RATE   1000000     // 1 Mbps

// Sensor pins
#define AI_SPN A5               // Spindle motor current (SEN0211)
#define AI_MAC A4               // Machine total current (SEN0211)
#define AI_SND A0               // Sound (DFR0034)

// Small delay in loop (saves CPU / reduces noise)
#define DELAY_US   10UL         // microseconds (can reduce to 1–5)

// Default sampling period (µs) — 500 µs = 2 kHz
#define TIMESTEP_US_DEFAULT 500UL

// Root field in JSON
#define DATA_FIELD "d"

// If you want to convert current to Amperes here (costs CPU and JSON bytes), uncomment:
// Acquisition frequency drops to ~1.06 kHz, which is OK per datasheet.
#define CONVERT_TO_AMP
#ifdef CONVERT_TO_AMP
const float to_V = 5.0f / 1024.0f;
const float to_A = 20.0f / 2.8f;        // your calibration factor
#endif

// ==============================
// Global state/objects
// ==============================
StaticJsonDocument<192> doc;   // Enough for {"t":...,"d":{"s":...,"m":...,"n":...}}
String out;                    // We always send ONE string per line

template<typename T>
T threshold_value(T value, T threshold) {
  return value > threshold ? value : 0;
}

// ==============================
// Setup
// ==============================
void setup() {
  Serial.begin(BAUD_RATE);
  Serial.print(F("# JSON fast v" VERSION " @ "));
  Serial.print(BAUD_RATE);
  Serial.println(F(" baud"));

  pinMode(AI_SPN, INPUT);
  pinMode(AI_MAC, INPUT);
  pinMode(AI_SND, INPUT);

  out.reserve(128);   // avoids String reallocations
}

// ==============================
// Loop
// ==============================
void loop() {
  static unsigned long prev_time = 0;
  static unsigned long timestep_us = TIMESTEP_US_DEFAULT;
  static unsigned long delay_us = DELAY_US;
  static unsigned int  threshold = 0;   // 0 = send everything
  static bool pause = false, raw = false;
  static unsigned long v = 0;           // numeric accumulator for commands

  const unsigned long now = micros();

  // --------- Serial command parsing ----------
  while (Serial.available()) {
    char ch = (char)Serial.read();
    switch (ch) {
      case '0'...'9': v = v * 10 + (ch - '0'); break;
      case 'p': // sampling period in microseconds
        timestep_us = constrain(v, 100UL, 1000000UL);
        v = 0;
        break;
      case 'd': // loop delay in microseconds
        delay_us = constrain(v, 0UL, timestep_us / 4UL);
        v = 0;
        break;
      case 't': // ADC threshold (0..1023)
        threshold = constrain(v, 0UL, 1023UL);
        v = 0;
        break;
      case 'k': // set rate in kHz (e.g. "2k" = 2 kHz -> period 500 us)
        if (v == 0) v = 1;
        timestep_us = constrain((unsigned long)(1000UL / v) * 1000UL, 100UL, 1000000UL);
        v = 0;
        break;
      case 'x': pause = !pause;         break;
      case 'r': raw   = !raw;           break;
      case '?':
        Serial.println(F("Help:"));
        Serial.print (F("- p  : period in us (ex: 500p -> ")); Serial.print(timestep_us); Serial.println(F(" us)"));
        Serial.print (F("- k  : rate in kHz (ex: 2k -> "));     Serial.print(1000000UL / timestep_us); Serial.println(F(" samples/s)"));
        Serial.print (F("- d  : loop delay in us (ex: 5d -> ")); Serial.print(delay_us); Serial.println(F(" us)"));
        Serial.print (F("- t  : ADC threshold 0..1023 (ex: 50t -> ")); Serial.print(threshold); Serial.println(F(")"));
        Serial.println(F("- x  : pause/resume"));
        Serial.println(F("- r  : raw/JSON"));
        break;
      default: v = 0; break;
    }
  }
  if (pause) { delayMicroseconds(delay_us); return; }

  // --------- Timed sampling ----------
  if ((now - prev_time) >= timestep_us) {
    prev_time = now;

    // Read channels
    int s = analogRead(AI_SPN);  // spindle
    int m = analogRead(AI_MAC);  // machine
    int n = analogRead(AI_SND);  // noise (sound)

    // Simple threshold
    s = threshold_value(s, (int)threshold);
    m = threshold_value(m, (int)threshold);
    n = threshold_value(n, (int)threshold);

    // --------- Output ---------
    if (raw) {
      // One simple line (single string) with raw values
      Serial.print(s); Serial.print(' ');
      Serial.print(m); Serial.print(' ');
      Serial.print(n); Serial.print('\n');
    } else {
      // Build compact JSON in ONE string and send
      doc.clear();
      doc["t"] = millis();
      JsonObject d = doc.createNestedObject(DATA_FIELD);
#ifdef CONVERT_TO_AMP
      d["s"] = (float)s * to_V * to_A;  // spindle (A)
      d["m"] = (float)m * to_V * to_A;  // machine (A)
      d["n"] = n;                       // sound (raw)
#else
      d["s"] = s;   // spindle (raw ADC)
      d["m"] = m;   // machine (raw ADC)
      d["n"] = n;   // noise / sound (raw ADC)
#endif
      out.remove(0);                    // clear the String
      serializeJson(doc, out);          // SERIALIZE INTO A STRING
      Serial.println(out);              // SEND ONE SINGLE STRING
    }
  }

  // Short delay to ease CPU load
  if (delay_us) delayMicroseconds(delay_us);
}
