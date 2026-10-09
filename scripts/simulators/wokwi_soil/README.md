# VeriField Nexus — Wokwi ESP32 Soil Sensor MRV Simulation

This directory contains the hardware simulation files for an ESP32 IoT node streaming in-situ soil moisture and soil temperature telemetry directly into the VeriField Nexus MRV platform.

---

## 1. Hardware Architecture & Pin Mapping

| Peripheral | Component Type | Interface | ESP32 Pin | Hardware Details |
| :--- | :--- | :--- | :--- | :--- |
| **Soil Moisture** | `wokwi-potentiometer` | Analog ADC1 (CH6) | **GPIO 34** | Simulates capacitive soil moisture probe via 12-bit ADC (0–4095) |
| **Soil Temperature** | Dallas `DS18B20` | OneWire Bus | **GPIO 4** | Digital thermometer (-55°C to +125°C) with 4.7kΩ pull-up resistor to 3V3 |
| **Power** | 3.3V Rail | Power | **3V3 & GND** | Standard 3.3V logic supply rail |

### A. Capacitive Soil Moisture Mapping (12-bit ADC)
The ESP32 uses a 12-bit SAR ADC with values ranging from 0 to 4095 (`ADC_RESOLUTION_MAX = 4095`):
* **Raw ADC 0:** 100.0% soil moisture (maximum saturation)
* **Raw ADC 4095:** 0.0% soil moisture (oven-dry soil limit)
* **Linear Response:** `Moisture % = ((4095 - rawADC) / 4095) * 100.0`
* *Note:* This is a simulated analog response for firmware verification; production calibration curves will require laboratory soil core calibration.

### B. Dallas DS18B20 Digital Thermometer
* Uses the Dallas Temperature and OneWire protocols on GPIO 4.
* Requires a 4.7kΩ pull-up resistor between the DATA line and 3.3V rail.
* Delivers calibrated Celsius temperature readings directly over 1-Wire without analog drift.

---

## 2. Ingestion Protocol & Schema

The ESP32 firmware communicates via HTTP REST over Wi-Fi:

### A. Authentication
* **Endpoint:** `POST /api/v1/auth/login`
* **Format:** JSON
* **Body:**
  ```json
  {
    "email": "wokwifieldtest@gmail.com",
    "password": "<FIELD_AGENT_PASSWORD>"
  }
  ```
* **Response:** Extracts `access_token` (Bearer JWT). The node caches the token and re-authenticates automatically upon HTTP 401.

### B. Telemetry Ingestion
* **Endpoint:** `POST /api/v1/activities`
* **Headers:** `Authorization: Bearer <access_token>`, `Content-Type: application/json`
* **Payload:**
  ```json
  {
    "activity_type": "SOIL_SENSOR_TELEMETRY",
    "client_id": "wokwi-soil-1775736844-000001",
    "project_id": "5688bb11-a431-4f53-b5da-2064436c3aef",
    "captured_at": "2026-10-09T11:14:04Z",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "activity_data": {
      "device_id": "WOKWI-ESP32-SOIL-01",
      "test_mode": true,
      "simulation_source": "WOKWI_ESP32",
      "soil_moisture_raw": 1420,
      "soil_moisture_pct": 66.5,
      "soil_temperature_c": 29.4,
      "soil_moisture_sensor": "SIMULATED_ANALOG_12BIT",
      "temperature_sensor": "DS18B20",
      "device_time_synchronized": true,
      "measurement_authority": "PROVISIONAL_SENSOR_OBSERVATION"
    }
  }
  ```

### C. Client ID Format & Deduplication
To prevent deduplication collisions across ESP32 power cycles or resets, `client_id` combines Unix epoch seconds with a sequential counter:
* Format: `wokwi-soil-<epoch>-<counter>` (e.g., `wokwi-soil-1775736844-000001`)
* If SNTP is not yet synchronized, it falls back to `wokwi-soil-b<bootNonce>-<counter>`.

### D. Evidence Authority & Isolation
* Telemetry ingested from field agents or simulated nodes is tagged as `field_data_authority: PROVISIONAL_OBSERVATION` (`is_authoritative: false`).
* Sensor telemetry does **not** trigger carbon-credit issuance calculations or mutate authoritative SoilSample records.

---

## 3. Localhost & Wokwi Connectivity

Because Wokwi cloud simulations execute inside a browser sandbox, they cannot directly reach `http://localhost:8000` without a local gateway or development tunnel.

### Option 1: Wokwi IoT Gateway (Recommended for Desktop / VS Code)
1. Install and run the official Wokwi IoT Gateway bridge:
   ```bash
   ./wokwi-gateway
   ```
2. In `sketch.ino`, configure:
   ```cpp
   const char* VERIFIELD_API_URL = "http://10.0.2.2:8000"; // Or your LAN IP: http://192.168.x.x:8000
   ```

### Option 2: Ephemeral Development Tunnel (Cloud Wokwi Only)
*For development and simulation only — NEVER use development tunnels for production environments:*
1. Start an ephemeral development tunnel (e.g., cloudflared or ngrok):
   ```bash
   cloudflared tunnel --url http://localhost:8000
   # OR
   ngrok http 8000
   ```
2. Set the resulting tunnel URL as `VERIFIELD_API_URL` in `sketch.ino` or `secrets.h`.

### Option 3: Local Virtual ESP32 Test Runner
For fully automated, 100% offline regression testing:
```bash
python3 scripts/simulators/wokwi_soil/test_local_simulation.py
```

---

## 4. Secret Management & Safety Rules

1. **NEVER** commit live passwords, tokens, or API credentials into `sketch.ino`.
2. For local Arduino IDE / VS Code compilation, copy `secrets.h.template` to `secrets.h` (which is excluded in `.gitignore`):
   ```bash
   cp secrets.h.template secrets.h
   ```
3. In Wokwi Web, enter secrets into the private **Secrets** tab.
