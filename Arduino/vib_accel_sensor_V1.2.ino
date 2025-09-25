#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

// ==============================
// Configuração (mantendo sua base)
// ==============================
constexpr uint32_t BAUD_RATE    = 1000000;  // 1 Mbps
constexpr uint8_t  PIN_LOUDNESS = A0;
constexpr float    ADC_REF_V    = 5.0f;     // (se usar conversão do A0)

// JSON buffer pequeno e eficiente (mantido)
StaticJsonDocument<192> jsonDoc;

// Acelerômetro ADXL345 (mantido)
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);

// ==============================
// Temporização: 1600 Hz
// ==============================
constexpr uint32_t I2C_CLOCK_HZ    = 400000;      // I²C rápido (400 kHz)
constexpr uint32_t SAMPLE_PERIOD_US= 625;         // 1/1600 s ≈ 625 µs
constexpr float    DT              = 0.000625f;   // 625 µs em segundos

uint32_t lastSampleUs = 0;

// **Opcional**: publicar a cada N amostras para não saturar a Serial
constexpr uint16_t PUB_DECIMATION  = 16;          // 1600/16 = 100 Hz de saída
uint32_t sampleCount = 0;

// ==============================
// Vibração: passa-alta + RMS (mantendo sua ideia de RSS)
// ==============================
// Passa-alta por remoção de bias (LP exponencial do sinal)
// Corte em Hz — 0.5–2 Hz tira gravidade e drift sem afetar vibração útil
constexpr float F_HP_HZ   = 1.0f;
constexpr float TAU_HP    = 1.0f / (2.0f * PI * F_HP_HZ);
// Coeficiente fixo para o DT escolhido
const float ALPHA_LP = 1.0f - expf(-DT / TAU_HP);

// RMS exponencial (potência média do RSS)
// Constante de tempo (s): 0.3–1.0 s é comum para “nível global”
constexpr float TAU_RMS   = 0.6f;
const float BETA_RMS = 1.0f - expf(-DT / TAU_RMS);

// Estados (mantendo nomes próximos)
float gBiasX = 0.0f, gBiasY = 0.0f, gBiasZ = 1.0f; // ~1 g no Z
float msExp  = 0.0f;                               // média exp do quadrado (g^2)

// ==============================
// Setup (mantendo sua estrutura)
// ==============================
void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {}

  Wire.begin();
  Wire.setClock(I2C_CLOCK_HZ);

  if (!accel.begin()) {
    Serial.println(F("{\"err\":\"ADXL345 not found\"}"));
    while (1);
  }
  accel.setRange(ADXL345_RANGE_16_G);
  accel.setDataRate(ADXL345_DATARATE_1600_HZ); // 1.6 kHz real

  lastSampleUs = micros();
}

// ==============================
// Loop principal (mantendo JSON igual ao seu)
// ==============================
void loop() {
  // Agenda leitura a cada 625 µs exatos
  const uint32_t now = micros();
  if ((now - lastSampleUs) < SAMPLE_PERIOD_US) return;
  lastSampleUs += SAMPLE_PERIOD_US;

  // Leitura do acelerômetro
  sensors_event_t evt;
  accel.getEvent(&evt);

  // Converte m/s² → g (mantido)
  const float ax = evt.acceleration.x / SENSORS_GRAVITY_EARTH;
  const float ay = evt.acceleration.y / SENSORS_GRAVITY_EARTH;
  const float az = evt.acceleration.z / SENSORS_GRAVITY_EARTH;

  // Passa-alta via remoção de bias (LP exponencial do sinal)
  gBiasX += ALPHA_LP * (ax - gBiasX);
  gBiasY += ALPHA_LP * (ay - gBiasY);
  gBiasZ += ALPHA_LP * (az - gBiasZ);

  const float hx = ax - gBiasX;
  const float hy = ay - gBiasY;
  const float hz = az - gBiasZ;

  // ------ Magnitude (RSS) ------
  // Para RMS correto e barato, opere em potência (sem sqrt por amostra):
  const float mag2 = hx*hx + hy*hy + hz*hz; // (g^2)

  // ------ RMS exponencial da vibração ------
  // Potência média (média do quadrado)
  msExp += BETA_RMS * (mag2 - msExp);
  // RMS final (em g RMS)
  const float vibRms = sqrtf(msExp);

  // Leitura do sensor de som (mantida)
  const int loudRaw = analogRead(PIN_LOUDNESS);

  // Publicação (JSON igual ao seu; decimação opcional)
  sampleCount++;
  if (sampleCount % PUB_DECIMATION == 0) {
    jsonDoc.clear();
    jsonDoc["t"] = millis();               // timestamp em ms
    JsonObject d = jsonDoc.createNestedObject("d");
    d["ax"]  = ax;
    d["ay"]  = ay;
    d["az"]  = az;
    d["vib"] = vibRms;                     // g RMS (3 eixos combinados)
    d["l"]   = loudRaw;

    serializeJson(jsonDoc, Serial);
    Serial.println();
  }
}
