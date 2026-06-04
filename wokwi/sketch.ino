/*
 * ============================================================
 *  IoT-Enabled Urban Flood Early Warning and Alert System
 *  MSc AI – Cloud and IoT Module | Assignment 2
 * ============================================================
 *  Hardware (simulated via WOKWI):
 *    - ESP32 DevKit V1
 *    - HC-SR04 Ultrasonic  → Water Level  (TRIG=D5,  ECHO=D18)
 *    - DHT22               → Temp/Humidity (DATA=D4)
 *    - Potentiometer 1     → Rain Sensor   (SIG=D34, simulated)
 *    - Potentiometer 2     → Soil Moisture (SIG=D35, simulated)
 *    - Green LED           → LOW RISK      (D26)
 *    - Yellow LED          → MODERATE RISK (D27)
 *    - Red LED             → HIGH RISK     (D14)
 *    - Buzzer              → Audible Alarm (D12)
 *    - LCD1602 (I2C)       → Real-time display (SDA=D21, SCL=D22)
 *
 *  Data Flow:
 *    ESP32 → HTTP POST → Flask API  (flood/node1/data)
 *    ESP32 → MQTT PUB  → HiveMQ Broker → Azure / Dashboard
 * ============================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <ArduinoJson.h>

// ─── WiFi (Wokwi guest network – no password needed in simulation) ─────────
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// ─── Flask API endpoint (update IP for your local machine in deployment) ───
const char* FLASK_API_URL = "http://192.168.8.105:5000/api/sensor-data";

// ─── MQTT Broker (HiveMQ public broker – works in Wokwi simulation) ────────
const char* MQTT_BROKER        = "broker.hivemq.com";
const int   MQTT_PORT          = 1883;
const char* MQTT_TOPIC_DATA    = "flood/node1/data";
const char* MQTT_TOPIC_ALERTS  = "flood/alerts/local";
const char* MQTT_CLIENT_PREFIX = "ESP32FloodNode1-";

// ─── Pin Definitions ────────────────────────────────────────────────────────
#define TRIG_PIN      5
#define ECHO_PIN      18
#define DHT_PIN       4
#define RAIN_PIN      34
#define SOIL_PIN      35
#define LED_GREEN     26
#define LED_YELLOW    27
#define LED_RED       14
#define BUZZER_PIN    12

#define DHT_TYPE      DHT22
#define LCD_I2C_ADDR  0x27
#define LCD_COLS      16
#define LCD_ROWS      2

// ─── Risk Thresholds ────────────────────────────────────────────────────────
// Water level: HC-SR04 measures distance to water surface.
// Shorter distance  = higher water = greater flood risk.
#define WATER_HIGH_CM      15.0   // < 15 cm  → HIGH  risk
#define WATER_MODERATE_CM  30.0   // < 30 cm  → MODERATE risk

// Rain / Soil: ADC 0–4095.
// Potentiometer simulates sensor: high value = heavy rain / saturated soil.
#define RAIN_HIGH_ADC      3000   // > 3000  → heavy rain
#define RAIN_MODERATE_ADC  1500   // > 1500  → moderate rain
#define SOIL_HIGH_ADC      3000   // > 3000  → saturated soil
#define SOIL_MODERATE_ADC  1500   // > 1500  → damp soil

// Temperature as an additional risk amplifier
#define TEMP_HIGH_C        35.0

// Humidity as a risk amplifier (high humidity = reduced evaporation = more runoff)
#define HUMIDITY_HIGH_PCT   95.0   // > 95%  → +2 pts
#define HUMIDITY_MOD_PCT    85.0   // > 85%  → +1 pt

// Risk scoring thresholds
#define SCORE_HIGH_RISK    5
#define SCORE_MOD_RISK     2

// Publish / transmit interval
#define PUBLISH_INTERVAL_MS  5000UL

// ─── Globals ────────────────────────────────────────────────────────────────
DHT              dht(DHT_PIN, DHT_TYPE);
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);
WiFiClient       wifiClient;
PubSubClient     mqttClient(wifiClient);

unsigned long lastPublishTime = 0;

enum RiskLevel { RISK_LOW = 0, RISK_MODERATE = 1, RISK_HIGH = 2 };

// ─── Sensor Reads ────────────────────────────────────────────────────────────

float readWaterLevelCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);  // 30 ms timeout
  if (duration == 0) return 999.0;                   // No echo → sensor clear
  return (duration * 0.034f) / 2.0f;
}

// ─── Risk Evaluation ─────────────────────────────────────────────────────────

RiskLevel evaluateFloodRisk(float waterCm, int rain, int soil, float temp, float humidity) {
  int score = 0;

  // Water level (highest weight)
  if (waterCm < WATER_HIGH_CM)          score += 3;
  else if (waterCm < WATER_MODERATE_CM) score += 1;

  // Rainfall
  if (rain > RAIN_HIGH_ADC)             score += 3;
  else if (rain > RAIN_MODERATE_ADC)    score += 1;

  // Soil saturation
  if (soil > SOIL_HIGH_ADC)             score += 2;
  else if (soil > SOIL_MODERATE_ADC)    score += 1;

  // Temperature (minor amplifier)
  if (temp > TEMP_HIGH_C)               score += 1;

  // Humidity (reduced evaporation increases runoff risk)
  if (humidity > HUMIDITY_HIGH_PCT)     score += 2;
  else if (humidity > HUMIDITY_MOD_PCT) score += 1;

  if (score >= SCORE_HIGH_RISK) return RISK_HIGH;
  if (score >= SCORE_MOD_RISK)  return RISK_MODERATE;
  return RISK_LOW;
}

// ─── Alert Indicators ────────────────────────────────────────────────────────

void setAlertIndicators(RiskLevel risk) {
  digitalWrite(LED_GREEN,  LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED,    LOW);
  noTone(BUZZER_PIN);

  switch (risk) {
    case RISK_LOW:
      digitalWrite(LED_GREEN, HIGH);
      break;
    case RISK_MODERATE:
      digitalWrite(LED_YELLOW, HIGH);
      tone(BUZZER_PIN, 800, 300);  // Short 300 ms beep at 800 Hz
      break;
    case RISK_HIGH:
      digitalWrite(LED_RED, HIGH);
      tone(BUZZER_PIN, 1200);      // Continuous alarm at 1200 Hz
      break;
  }
}

// ─── LCD Update ──────────────────────────────────────────────────────────────

void updateLCD(float waterCm, float temp, float humidity, RiskLevel risk) {
  const char* riskLabel[] = { "LOW     ", "MODERATE", "HIGH!!! " };  // index matches RISK_LOW/MODERATE/HIGH

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WL:");
  lcd.print(waterCm, 1);
  lcd.print("cm ");
  lcd.print(riskLabel[risk]);

  lcd.setCursor(0, 1);
  lcd.print("T:");
  lcd.print(temp, 1);
  lcd.print("C H:");
  lcd.print((int)humidity);
  lcd.print("%");
}

// ─── WiFi ────────────────────────────────────────────────────────────────────

void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.print(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 20) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected. IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Connection failed – running offline.");
  }
}

// ─── MQTT ────────────────────────────────────────────────────────────────────

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("[MQTT] Received on " + String(topic) + ": " + msg);
}

void connectMQTT() {
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  String clientId = String(MQTT_CLIENT_PREFIX) + String(random(0xffff), HEX);
  Serial.print("[MQTT] Connecting as " + clientId + " ...");

  if (mqttClient.connect(clientId.c_str())) {
    Serial.println(" connected.");
    mqttClient.subscribe(MQTT_TOPIC_ALERTS);
  } else {
    Serial.println(" failed. State=" + String(mqttClient.state()));
  }
}

void ensureMQTTConnected() {
  if (!mqttClient.connected()) {
    connectMQTT();
  }
}

// ─── Payload Builder (shared by MQTT and Flask) ──────────────────────────────

String buildJsonPayload(float waterCm, int rain, int soil,
                        float temp, float humidity, RiskLevel risk) {
  const char* riskStr[] = { "LOW", "MODERATE", "HIGH" };  // index matches RISK_LOW/MODERATE/HIGH

  StaticJsonDocument<256> doc;
  doc["node_id"]           = "flood_node_1";
  doc["water_level_cm"]    = serialized(String(waterCm, 2));
  doc["rain_raw"]          = rain;
  doc["soil_moisture_raw"] = soil;
  doc["temperature_c"]     = serialized(String(temp, 2));
  doc["humidity_pct"]      = serialized(String(humidity, 2));
  doc["risk_level"]        = riskStr[risk];
  doc["timestamp_ms"]      = millis();

  String out;
  serializeJson(doc, out);
  return out;
}

// ─── MQTT Publish ─────────────────────────────────────────────────────────────

void publishToMQTT(const String& payload, RiskLevel risk) {
  ensureMQTTConnected();

  if (mqttClient.publish(MQTT_TOPIC_DATA, payload.c_str())) {
    Serial.println("[MQTT] Published to " + String(MQTT_TOPIC_DATA));
  } else {
    Serial.println("[MQTT] Publish failed.");
  }

  // Publish a lightweight alert message on the alert topic for HIGH/MODERATE
  if (risk >= RISK_MODERATE) {
    const char* alert = (risk == RISK_HIGH) ? "{\"alert\":\"FLOOD_HIGH\"}"
                                            : "{\"alert\":\"FLOOD_MODERATE\"}";
    mqttClient.publish(MQTT_TOPIC_ALERTS, alert);
    Serial.println("[MQTT] Alert published: " + String(alert));
  }
}

// ─── Flask HTTP POST ──────────────────────────────────────────────────────────

void sendToFlaskAPI(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi not connected – skipping Flask POST.");
    return;
  }

  HTTPClient http;
  http.begin(FLASK_API_URL);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    Serial.println("[HTTP] Flask API response code: " + String(httpCode));
    if (httpCode == 200 || httpCode == 201) {
      Serial.println("[HTTP] Response: " + http.getString());
    }
  } else {
    Serial.println("[HTTP] Flask API error: " + http.errorToString(httpCode));
  }
  http.end();
}

// ─── Setup ───────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Flood Early Warning System Booting ===");

  // Output pins
  pinMode(TRIG_PIN,   OUTPUT);
  pinMode(LED_GREEN,  OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED,    OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // Input pins
  pinMode(ECHO_PIN,  INPUT);
  pinMode(RAIN_PIN,  INPUT);
  pinMode(SOIL_PIN,  INPUT);

  // Initial state – all off
  digitalWrite(LED_GREEN,  LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED,    LOW);

  // DHT sensor
  dht.begin();

  // LCD (I2C on GPIO21=SDA, GPIO22=SCL)
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Flood Monitor");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");

  connectWiFi();
  connectMQTT();

  // Boot indicator – blink green LED once
  digitalWrite(LED_GREEN, HIGH);
  delay(500);
  digitalWrite(LED_GREEN, LOW);

  Serial.println("=== System Ready ===\n");
}

// ─── Main Loop ───────────────────────────────────────────────────────────────

void loop() {
  mqttClient.loop();  // Keep MQTT connection alive and process callbacks

  unsigned long now = millis();
  if (now - lastPublishTime >= PUBLISH_INTERVAL_MS) {
    lastPublishTime = now;

    // ── Read all sensors ──
    float waterCm   = readWaterLevelCm();
    float tempC     = dht.readTemperature();
    float humidity  = dht.readHumidity();
    int   rainRaw   = analogRead(RAIN_PIN);
    int   soilRaw   = analogRead(SOIL_PIN);

    // Guard against DHT read failures
    if (isnan(tempC))    tempC    = -1.0;
    if (isnan(humidity)) humidity = -1.0;

    // ── Evaluate flood risk ──
    RiskLevel risk = evaluateFloodRisk(waterCm, rainRaw, soilRaw, tempC, humidity);

    // ── Drive actuators ──
    setAlertIndicators(risk);
    updateLCD(waterCm, tempC, humidity, risk);

    // ── Serial debug output ──
    const char* riskStr[] = { "LOW", "MODERATE", "HIGH" };  // index matches RISK_LOW/MODERATE/HIGH
    Serial.printf(
      "[SENSOR] WL=%.1f cm | Rain=%d | Soil=%d | Temp=%.1f°C | Hum=%.0f%% | Risk=%s\n",
      waterCm, rainRaw, soilRaw, tempC, humidity, riskStr[risk]
    );

    // ── Transmit data ──
    String payload = buildJsonPayload(waterCm, rainRaw, soilRaw,
                                      tempC, humidity, risk);
    publishToMQTT(payload, risk);
    sendToFlaskAPI(payload);
  }
}
