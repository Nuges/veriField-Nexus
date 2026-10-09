/**
 * VeriField Nexus — Wokwi ESP32 Soil Telemetry Firmware
 *
 * Hardware:
 * - ESP32-WROOM DevKit v4
 * - Soil Moisture: Potentiometer simulating capacitive soil sensor on GPIO 34 (ADC1_CH6, 12-bit 0-4095)
 * - Soil Temperature: Dallas DS18B20 1-Wire Digital Thermometer on GPIO 4
 *
 * Time Synchronization:
 * - SNTP synchronization via pool.ntp.org (canonical UTC: GMT+0, no DST).
 * - If SNTP succeeds: submits ISO-8601 UTC timestamp (e.g. 2026-10-09T11:14:04Z).
 * - If SNTP fails: fails safely with captured_at = null, device_time_synchronized = false.
 *
 * Networking & Auth:
 * - Wi-Fi SSID: "Wokwi-GUEST" (unsecured for Wokwi simulation)
 * - Authenticates against VeriField API (POST /api/v1/auth/login) as FIELD_AGENT
 * - Submits telemetry to VeriField Activity Pipeline (POST /api/v1/activities)
 *
 * NOTE ON SECRETS:
 * - Placeholders are used below. For live simulation, supply credentials via:
 *   1) Wokwi Secrets tab, or
 *   2) A local untracked 'secrets.h' file.
 * - NEVER commit real credentials to source control.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <time.h>

// If secrets.h exists locally, include it; otherwise use placeholders
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  const char* VERIFIELD_API_URL       = "http://10.0.2.2:8000";     // or your tunnel/local IP URL
  const char* VERIFIELD_TEST_EMAIL    = "wokwifieldtest@gmail.com";  // FIELD_AGENT account
  const char* VERIFIELD_TEST_PASSWORD = "VERIFIELD_TEST_PASSWORD";   // Supply via secrets.h or Wokwi Secrets
#endif

// Wi-Fi Configuration for Wokwi
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// Hardware Pin Assignments
const int SOIL_ADC_PIN   = 34; // GPIO 34 (ADC1_CH6)
const int ONE_WIRE_BUS   = 4;  // GPIO 4 (DS18B20 OneWire Data)

// 1-Wire & Dallas Temperature Instances
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// 12-Bit ADC Range Constants
const int ADC_RESOLUTION_MAX = 4095;

// Project & Device Metadata
const char* DEVICE_ID = "WOKWI-ESP32-SOIL-01";
const char* PROJECT_ID = "5688bb11-a431-4f53-b5da-2064436c3aef"; // Deepak Farm Soil Sensor Pilot
const float TEST_LATITUDE = 28.6139;  // Deepak Farm pilot coordinates
const float TEST_LONGITUDE = 77.2090;

// SNTP Time Configuration
const char* NTP_SERVER_1        = "pool.ntp.org";
const char* NTP_SERVER_2        = "time.nist.gov";
const long  GMT_OFFSET_SEC      = 0;  // Canonical UTC
const int   DAYLIGHT_OFFSET_SEC = 0;  // Canonical UTC (no DST)

bool isNtpSynchronized = false;

// State Variables
String jwtToken = "";
unsigned long lastReadingTime = 0;
const unsigned long READING_INTERVAL_MS = 15000; // 15 seconds between telemetry posts
unsigned long sequenceCounter = 1;
uint32_t bootNonce = 0;

// ============================================================================
// SNTP Time Synchronization
// ============================================================================
void initNtpTime() {
  Serial.println(F("[NTP] Initializing SNTP time synchronization (canonical UTC)..."));
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER_1, NTP_SERVER_2);

  struct tm timeinfo;
  for (int retry = 0; retry < 10; retry++) {
    if (getLocalTime(&timeinfo, 500)) {
      if (timeinfo.tm_year > (2020 - 1900)) { // Valid year after 2020
        isNtpSynchronized = true;
        char buf[32];
        strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        Serial.printf("[NTP] Time synchronized successfully: %s\n", buf);
        return;
      }
    }
    delay(200);
  }

  Serial.println(F("[NTP] Warning: SNTP time synchronization timed out. Failing safely."));
  isNtpSynchronized = false;
}

bool getIsoUtcTimestamp(char* outBuffer, size_t maxLen) {
  if (!isNtpSynchronized) {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 100) && timeinfo.tm_year > (2020 - 1900)) {
      isNtpSynchronized = true;
    } else {
      return false; // NTP failed/not synchronized
    }
  }

  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 500)) {
    return false;
  }
  strftime(outBuffer, maxLen, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return true;
}

// ============================================================================
// Sensor Readers
// ============================================================================
float readDS18B20Temperature() {
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);
  if (tempC == DEVICE_DISCONNECTED_C) {
    Serial.println(F("[SENSOR] Warning: DS18B20 sensor disconnected!"));
    return -999.0;
  }
  return tempC;
}

float calculateSoilMoisture(int rawAdc) {
  if (rawAdc < 0) rawAdc = 0;
  if (rawAdc > ADC_RESOLUTION_MAX) rawAdc = ADC_RESOLUTION_MAX;
  // Capacitive response: lower raw ADC = higher moisture (100%), higher raw ADC = dry (0%)
  float pct = ((float)(ADC_RESOLUTION_MAX - rawAdc) / (float)ADC_RESOLUTION_MAX) * 100.0;
  return round(pct * 10.0) / 10.0;
}

// ============================================================================
// Authentication Flow (POST /api/v1/auth/login)
// ============================================================================
bool authenticateWithVeriField() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[AUTH] Cannot authenticate: Wi-Fi disconnected."));
    return false;
  }

  Serial.println(F("[AUTH] Authenticating FIELD_AGENT against VeriField API..."));
  HTTPClient http;
  String loginEndpoint = String(VERIFIELD_API_URL) + "/api/v1/auth/login";

  http.begin(loginEndpoint);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> reqDoc;
  reqDoc["email"] = VERIFIELD_TEST_EMAIL;
  reqDoc["password"] = VERIFIELD_TEST_PASSWORD;

  String reqBody;
  serializeJson(reqDoc, reqBody);

  int httpCode = http.POST(reqBody);
  if (httpCode == 200) {
    String respBody = http.getString();
    StaticJsonDocument<1024> respDoc;
    DeserializationError error = deserializeJson(respDoc, respBody);
    if (!error && respDoc.containsKey("access_token")) {
      jwtToken = respDoc["access_token"].as<String>();
      Serial.println(F("[AUTH] Success! JWT token received."));
      http.end();
      return true;
    } else {
      Serial.println(F("[AUTH] Failed to parse access_token from response."));
    }
  } else {
    Serial.printf("[AUTH] Login failed with HTTP status: %d\n", httpCode);
    Serial.printf("[AUTH] Response: %s\n", http.getString().c_str());
  }

  http.end();
  return false;
}

// ============================================================================
// Telemetry Ingestion (POST /api/v1/activities)
// ============================================================================
bool submitSoilTelemetry(int soilRaw, float soilPct, float tempC) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[TELEMETRY] Error: Wi-Fi disconnected."));
    return false;
  }

  if (jwtToken.length() == 0) {
    Serial.println(F("[TELEMETRY] No JWT token; authenticating first..."));
    if (!authenticateWithVeriField()) {
      return false;
    }
  }

  HTTPClient http;
  String endpoint = String(VERIFIELD_API_URL) + "/api/v1/activities";
  http.begin(endpoint);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + jwtToken);

  // Generate unique client_id for offline-first deduplication (incorporating epoch/boot nonce to prevent reboot collision)
  char clientId[64];
  time_t currentEpoch = time(nullptr);
  if (currentEpoch > 1600000000) {
    snprintf(clientId, sizeof(clientId), "wokwi-soil-%lu-%06lu", (unsigned long)currentEpoch, sequenceCounter++);
  } else {
    snprintf(clientId, sizeof(clientId), "wokwi-soil-b%08lx-%06lu", (unsigned long)bootNonce, sequenceCounter++);
  }

  // Format ISO-8601 UTC timestamp from SNTP if synchronized
  char isoTimestamp[32];
  bool timeSync = getIsoUtcTimestamp(isoTimestamp, sizeof(isoTimestamp));

  StaticJsonDocument<1024> payload;
  payload["activity_type"] = "SOIL_SENSOR_TELEMETRY";
  payload["client_id"] = clientId;
  if (PROJECT_ID != nullptr && strlen(PROJECT_ID) > 0) {
    payload["project_id"] = PROJECT_ID;
  }

  if (timeSync) {
    payload["captured_at"] = isoTimestamp;
  } else {
    payload["captured_at"] = (char*)nullptr; // Fail-safe: backend assigns canonical UTC
  }

  payload["latitude"] = TEST_LATITUDE;
  payload["longitude"] = TEST_LONGITUDE;

  JsonObject data = payload.createNestedObject("activity_data");
  data["device_id"] = DEVICE_ID;
  data["test_mode"] = true;
  data["simulation_source"] = "WOKWI_ESP32";
  data["soil_moisture_raw"] = soilRaw;
  data["soil_moisture_pct"] = soilPct;
  data["soil_temperature_c"] = tempC;
  data["soil_moisture_sensor"] = "SIMULATED_ANALOG_12BIT";
  data["temperature_sensor"] = "DS18B20";
  data["device_time_synchronized"] = timeSync;
  data["measurement_authority"] = "PROVISIONAL_SENSOR_OBSERVATION";

  String body;
  serializeJson(payload, body);

  Serial.printf("[TELEMETRY] Sending observation (%s, captured_at=%s)...\n",
                clientId, timeSync ? isoTimestamp : "NULL");
  int httpCode = http.POST(body);

  if (httpCode == 200 || httpCode == 201) {
    Serial.printf("[TELEMETRY] Ingested successfully (HTTP %d). Response:\n%s\n",
                  httpCode, http.getString().c_str());
    http.end();
    return true;
  } else if (httpCode == 401) {
    Serial.println(F("[TELEMETRY] HTTP 401 Unauthorized — token expired. Resetting token."));
    jwtToken = "";
    http.end();
    return false;
  } else {
    Serial.printf("[TELEMETRY] Server returned HTTP %d: %s\n", httpCode, http.getString().c_str());
    http.end();
    return false;
  }
}

// ============================================================================
// Arduino Setup & Main Loop
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  bootNonce = (uint32_t)esp_random();
  Serial.println(F("\n========================================================"));
  Serial.println(F(" VeriField Nexus — ESP32 Wokwi Soil MRV Firmware Starting"));
  Serial.println(F("========================================================"));

  // Configure pins
  pinMode(SOIL_ADC_PIN, INPUT);

  // Initialize DS18B20
  sensors.begin();
  Serial.printf("[SENSOR] DS18B20 1-Wire bus initialized on GPIO %d\n", ONE_WIRE_BUS);

  // Connect to Wi-Fi
  Serial.printf("Connecting to Wi-Fi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(F("\n[WIFI] Connected! IP Address: "));
  Serial.println(WiFi.localIP());

  // Initialize SNTP Time
  initNtpTime();

  // Initial authentication
  authenticateWithVeriField();
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadingTime >= READING_INTERVAL_MS) {
    lastReadingTime = now;

    // 1. Read Soil Moisture Potentiometer (ADC1, 0-4095)
    int rawSoil = analogRead(SOIL_ADC_PIN);
    float soilPct = calculateSoilMoisture(rawSoil);

    // 2. Read DS18B20 Digital Thermometer
    float tempC = readDS18B20Temperature();

    // 3. Print Local Diagnostics
    Serial.printf("\n--- SENSOR READINGS ---\n");
    Serial.printf("Soil Moisture: Raw=%d (12-bit)  Mapped=%.1f %%\n", rawSoil, soilPct);
    Serial.printf("Temperature:   %.2f °C (DS18B20)\n", tempC);

    // 4. Submit to VeriField Nexus Pipeline
    submitSoilTelemetry(rawSoil, soilPct, tempC);
  }

  delay(100);
}
