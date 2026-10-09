#!/usr/bin/env python3
"""
VeriField Nexus — Virtual ESP32 Soil Telemetry Runner
=====================================================
Emulates the exact Arduino firmware execution logic locally:
1. Connects to VeriField API (default: http://localhost:8000).
2. Authenticates FIELD_AGENT account (POST /api/v1/auth/login).
3. Reads simulated sensors (Soil ADC potentiometer 0-4095 + DS18B20 digital thermometer).
4. Synchronizes ISO-8601 UTC timestamp (e.g. 2026-10-09T11:14:04Z).
5. Submits SOIL_SENSOR_TELEMETRY payload (POST /api/v1/activities).
6. Displays HTTP status code and pipeline response.

Usage:
  python3 test_local_simulation.py --email wokwifieldtest@gmail.com --password <PASSWORD>
  OR set env vars:
  export VERIFIELD_TEST_PASSWORD="<PASSWORD>"
  python3 test_local_simulation.py
"""

import argparse
import datetime
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error

# 12-bit ADC range matching ESP32 hardware
ADC_MAX = 4095


def calculate_moisture(raw_adc: int) -> float:
    raw_clamped = max(0, min(ADC_MAX, raw_adc))
    pct = ((ADC_MAX - raw_clamped) / ADC_MAX) * 100.0
    return round(pct, 1)


def authenticate(api_url: str, email: str, password: str) -> str:
    url = f"{api_url.rstrip('/')}/api/v1/auth/login"
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token")
            if not token:
                raise ValueError("No access_token returned by login endpoint.")
            print(f"[AUTH] Successfully authenticated {email}. Token acquired.")
            return token
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[AUTH] Error {e.code}: {err_body}", file=sys.stderr)
        raise


def submit_telemetry(
    api_url: str,
    token: str,
    client_id: str,
    soil_raw: int,
    soil_pct: float,
    temp_c: float,
    project_id: str = None,
    captured_at: str = None,
    time_synchronized: bool = True,
) -> dict:
    url = f"{api_url.rstrip('/')}/api/v1/activities"

    if captured_at is None and time_synchronized:
        captured_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "activity_type": "SOIL_SENSOR_TELEMETRY",
        "client_id": client_id,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "activity_data": {
            "device_id": "WOKWI-ESP32-SOIL-01",
            "test_mode": True,
            "simulation_source": "WOKWI_ESP32",
            "soil_moisture_raw": soil_raw,
            "soil_moisture_pct": soil_pct,
            "soil_temperature_c": temp_c,
            "soil_moisture_sensor": "SIMULATED_ANALOG_12BIT",
            "temperature_sensor": "DS18B20",
            "device_time_synchronized": time_synchronized,
            "measurement_authority": "PROVISIONAL_SENSOR_OBSERVATION",
        },
    }
    if captured_at:
        payload["captured_at"] = captured_at
    if project_id:
        payload["project_id"] = project_id

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = json.loads(resp.read().decode("utf-8"))
            print(f"[TELEMETRY] Successfully submitted packet {client_id} (HTTP {resp.status})")
            return resp_body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[TELEMETRY] Error {e.code}: {err_body}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="VeriField Nexus Virtual ESP32 Soil Simulator")
    parser.add_argument("--url", default=os.getenv("VERIFIELD_API_URL", "http://localhost:8000"), help="VeriField API URL")
    parser.add_argument("--email", default=os.getenv("VERIFIELD_TEST_EMAIL", "wokwifieldtest@gmail.com"), help="Field Agent Email")
    parser.add_argument("--password", default=os.getenv("VERIFIELD_TEST_PASSWORD", ""), help="Field Agent Password")
    parser.add_argument("--token", default=os.getenv("VERIFIELD_TEST_TOKEN", ""), help="Direct JWT Bearer Token")
    parser.add_argument("--project-id", default=os.getenv("VERIFIELD_PROJECT_ID", "5688bb11-a431-4f53-b5da-2064436c3aef"), help="Project UUID")
    parser.add_argument("--count", type=int, default=1, help="Number of telemetry packets to stream")
    parser.add_argument("--interval", type=int, default=3, help="Seconds between packets")
    args = parser.parse_args()

    if not args.token and not args.password:
        print("Error: Either --token or --password must be supplied.", file=sys.stderr)
        sys.exit(1)

    print("===================================================================")
    print(" VeriField Nexus — Virtual ESP32 Soil Sensor Telemetry Streamer   ")
    print("===================================================================")
    print(f"Target API:   {args.url}")
    print(f"Field Agent:  {args.email}")
    print(f"Project ID:   {args.project_id}")
    print(f"Packet Count: {args.count}")

    if args.token:
        token = args.token
        print("[AUTH] Using supplied JWT bearer token.")
    else:
        token = authenticate(args.url, args.email, args.password)

    # Sample test parameters to provide distinct readings across packets
    preset_samples = [
        {"raw": 1370, "temp": 28.75}, # ~66.5% moisture, 28.75 °C
        {"raw": 1840, "temp": 29.50}, # ~55.1% moisture, 29.50 °C
        {"raw": 980,  "temp": 27.80}, # ~76.1% moisture, 27.80 °C
    ]

    for i in range(1, args.count + 1):
        client_id = f"wokwi-ds18b20-{int(time.time())}-{i:04d}"
        if i <= len(preset_samples):
            soil_raw = preset_samples[i - 1]["raw"]
            temp_c = preset_samples[i - 1]["temp"]
        else:
            soil_raw = random.randint(1200, 2000)
            temp_c = round(random.uniform(26.0, 31.0), 2)

        soil_pct = calculate_moisture(soil_raw)
        utc_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"\n--- Packet #{i}/{args.count} ---")
        print(f"Timestamp (UTC): {utc_ts}")
        print(f"Soil Raw (12-bit): {soil_raw} (ADC range 0–4095)")
        print(f"Soil Moisture:   {soil_pct}%")
        print(f"Temperature:     {temp_c} °C (DS18B20)")

        submit_telemetry(
            args.url,
            token,
            client_id,
            soil_raw,
            soil_pct,
            temp_c,
            args.project_id,
            captured_at=utc_ts,
            time_synchronized=True,
        )

        if i < args.count:
            time.sleep(args.interval)

    print("\n[COMPLETE] All simulated packets submitted successfully.")


if __name__ == "__main__":
    main()
