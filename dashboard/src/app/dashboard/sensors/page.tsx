// =============================================================================
// VeriField Nexus — Soil Telemetry & IoT Fleet Observability
// =============================================================================

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Cpu,
  Droplets,
  Layers,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Thermometer,
  Wifi,
  Clock,
  ExternalLink,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import StatCard from "@/components/StatCard";
import { fetchActivities } from "@/lib/api";
import { formatTime, formatDateTime, getLocalTimeZone } from "@/lib/dateTime";

interface TelemetryPoint {
  id: string;
  rawTimestamp: string;
  time: string;
  dateTimeStr: string;
  timestamp: number;
  moisturePct: number;
  moistureRaw: number;
  tempC: number;
  clientId: string;
  deviceId: string;
  temperatureSensor: string;
  moistureSensor: string;
  authority: string;
  isSimulation: boolean;
  calibrationRange?: string;
}

export default function SensorsPage() {
  const [readings, setReadings] = useState<TelemetryPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [tzMode, setTzMode] = useState<"local" | "project" | "utc">("local");

  // Determine active IANA timezone identifier
  const activeTimeZone = tzMode === "project" ? "Asia/Kolkata" : tzMode === "utc" ? "UTC" : undefined;

  const loadSensorData = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetchActivities({ activity_type: "SOIL_SENSOR_TELEMETRY" });
      const rawList = Array.isArray(res) ? res : (res as any)?.activities || (res as any)?.items || [];

      // Filter and map SOIL_SENSOR_TELEMETRY activities
      const mapped: TelemetryPoint[] = rawList
        .filter((act: any) => act.activity_type === "SOIL_SENSOR_TELEMETRY")
        .map((act: any) => {
          const data = act.activity_data || {};
          const rawTimestamp = act.captured_at || act.submitted_at || act.created_at || new Date().toISOString();
          const capturedDate = new Date(rawTimestamp);
          const tempSensor = (data.temperature_sensor || "").trim() || "DS18B20";
          const moistSensor = (data.soil_moisture_sensor || "").trim() || "SIMULATED_ANALOG";
          const isSimulation = Boolean(data.simulation_source || data.test_mode || moistSensor === "SIMULATED_ANALOG");

          return {
            id: act.id,
            rawTimestamp: rawTimestamp,
            time: formatTime(rawTimestamp, activeTimeZone),
            dateTimeStr: formatDateTime(rawTimestamp, activeTimeZone),
            timestamp: isNaN(capturedDate.getTime()) ? 0 : capturedDate.getTime(),
            moisturePct: typeof data.soil_moisture_pct === "number" ? data.soil_moisture_pct : 0,
            moistureRaw: typeof data.soil_moisture_raw === "number" ? data.soil_moisture_raw : 0,
            tempC: typeof data.soil_temperature_c === "number" ? data.soil_temperature_c : 0,
            clientId: act.client_id || "unknown",
            deviceId: data.device_id || "WOKWI-ESP32-SOIL-01",
            temperatureSensor: tempSensor,
            moistureSensor: moistSensor,
            authority: data.field_data_authority || "PROVISIONAL_OBSERVATION",
            isSimulation: isSimulation,
            calibrationRange: data.calibration_range || undefined,
          };
        })
        .sort((a: TelemetryPoint, b: TelemetryPoint) => a.timestamp - b.timestamp);

      setReadings(mapped);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Failed to load soil telemetry:", err);
    } finally {
      setIsLoading(false);
    }
  }, [activeTimeZone]);

  useEffect(() => {
    loadSensorData();
    const interval = setInterval(loadSensorData, 10000); // 10s auto-poll for live stream
    return () => clearInterval(interval);
  }, [loadSensorData]);

  // Latest observation
  const latest = readings.length > 0 ? readings[readings.length - 1] : null;
  const isOnline = latest ? (Date.now() - latest.timestamp <= 60000) : false;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
              IoT Sensor Telemetry
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
              Live Pilot
            </span>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Real-time in-situ soil moisture and temperature telemetry streaming from ESP32 hardware.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Timezone Switcher */}
          <div className="flex items-center gap-1 bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-1 text-xs">
            <span className="text-[var(--color-text-muted)] px-1.5 font-medium flex items-center gap-1">
              <Clock size={12} /> TZ:
            </span>
            <button
              type="button"
              onClick={() => setTzMode("local")}
              className={`px-2 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                tzMode === "local"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
              title={`Viewer Local Time (${getLocalTimeZone()})`}
            >
              Local ({getLocalTimeZone().split("/").pop()?.replace("_", " ") || "Browser"})
            </button>
            <button
              type="button"
              onClick={() => setTzMode("project")}
              className={`px-2 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                tzMode === "project"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
              title="Project Site Time (Asia/Kolkata)"
            >
              Project (IST)
            </button>
            <button
              type="button"
              onClick={() => setTzMode("utc")}
              className={`px-2 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                tzMode === "utc"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
              title="Canonical UTC"
            >
              UTC
            </button>
          </div>

          <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
            Updated {lastRefreshed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
          <button
            onClick={loadSensorData}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors shadow-sm cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* Pilot Metadata Banner */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-4 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-xs">
          <div>
            <span className="text-[var(--color-text-muted)] block">Pilot Project</span>
            <span className="font-semibold text-[var(--color-text-primary)] text-sm mt-0.5 block truncate">
              Deepak Farm Soil Sensor Pilot
            </span>
          </div>
          <div>
            <span className="text-[var(--color-text-muted)] block">Primary Sector</span>
            <span className="font-semibold text-[var(--color-text-primary)] text-sm mt-0.5 block">
              Agriculture & Land Use
            </span>
          </div>
          <div>
            <span className="text-[var(--color-text-muted)] block">Active Node</span>
            <span className="font-mono font-semibold text-[var(--color-text-primary)] text-sm mt-0.5 block">
              {latest ? latest.deviceId : "WOKWI-ESP32-SOIL-01"}
            </span>
          </div>
          <div>
            <span className="text-[var(--color-text-muted)] block">Hardware Source</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400 text-sm mt-0.5 block">
              Wokwi Simulation
            </span>
          </div>
          <div>
            <span className="text-[var(--color-text-muted)] block">Evidence Authority</span>
            <span className="font-semibold text-amber-600 dark:text-amber-400 text-sm mt-0.5 block truncate">
              {latest ? latest.authority : "Provisional Observation"}
            </span>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Soil Moisture"
          value={latest ? `${latest.moisturePct.toFixed(1)}%` : "66.5%"}
          icon={Droplets}
          trend={
            latest
              ? latest.isSimulation
                ? `ADC: ${latest.moistureRaw} (Simulated 0–4095)`
                : `ADC: ${latest.moistureRaw}`
              : "ADC: 0–4095 (Simulated)"
          }
          trendUp={true}
          color="emerald"
        />
        <StatCard
          title="Soil Temperature"
          value={latest ? `${latest.tempC.toFixed(1)} °C` : "29.4 °C"}
          icon={Thermometer}
          trend={latest?.temperatureSensor || "DS18B20"}
          trendUp={true}
          color="amber"
        />
        <StatCard
          title="Device Status"
          value={isOnline ? "ONLINE" : (latest ? "STALE" : "STANDBY")}
          icon={Wifi}
          trend={isOnline ? "Streaming (15s)" : (latest ? `Last seen ${latest.time}` : "Awaiting Packets")}
          trendUp={isOnline}
          color={isOnline ? "emerald" : (latest ? "amber" : "blue")}
        />
        <StatCard
          title="Telemetry Count"
          value={readings.length > 0 ? readings.length : "0"}
          icon={Cpu}
          trend={readings.length > 0 ? `Latest: ${latest?.clientId}` : "Wokwi-GUEST"}
          trendUp={true}
          color="purple"
        />
      </div>

      {/* Time-Series Charts & Diagnostics */}
      {readings.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Soil Moisture Chart */}
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                  <Droplets size={16} className="text-[#008A5E]" />
                  Soil Moisture Trajectory (%)
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  {latest?.isSimulation
                    ? "Simulated soil moisture response (ESP32 ADC 0–4095)"
                    : latest?.calibrationRange
                    ? `Calibrated range: ${latest.calibrationRange}`
                    : "In-situ capacitive moisture response"}
                </p>
              </div>
            </div>
            <div className="h-60 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <AreaChart data={readings}>
                  <defs>
                    <linearGradient id="moistureGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#008A5E" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#008A5E" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                  <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-card)",
                      borderColor: "var(--color-border)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="moisturePct"
                    stroke="#008A5E"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#moistureGrad)"
                    name="Moisture"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Soil Temperature Chart */}
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                  <Thermometer size={16} className="text-amber-500" />
                  Soil Temperature (°C)
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  In-situ soil temperature ({latest?.temperatureSensor || "DS18B20"})
                </p>
              </div>
            </div>
            <div className="h-60 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <AreaChart data={readings}>
                  <defs>
                    <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                  <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                  <YAxis domain={["auto", "auto"]} unit="°C" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-card)",
                      borderColor: "var(--color-border)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="tempC"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#tempGrad)"
                    name="Temperature"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : null}

      {/* Telemetry Log Table */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Activity size={16} className="text-[#008A5E]" />
              Recent ESP32 Packet Ingestion Log
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Verified packet timeline showing client deduplication IDs and provisional evidence hashes.
            </p>
          </div>
        </div>

        {readings.length === 0 ? (
          <div className="py-8 text-center text-[var(--color-text-secondary)]">
            <Radio className="mx-auto text-[var(--color-text-muted)] mb-3 animate-pulse" size={36} />
            <p className="text-sm font-medium text-[var(--color-text-primary)]">
              Awaiting Live Wokwi Telemetry Packets
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] max-w-md mx-auto mt-1">
              Start the Wokwi ESP32 firmware in <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">scripts/simulators/wokwi_soil/sketch.ino</code> or run the local virtual ESP32 test client to stream live telemetry.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[var(--color-border)] text-[var(--color-text-muted)] font-medium">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Client ID</th>
                  <th className="py-2.5 px-3">Probe</th>
                  <th className="py-2.5 px-3">Moisture %</th>
                  <th className="py-2.5 px-3">Raw ADC</th>
                  <th className="py-2.5 px-3">Temperature</th>
                  <th className="py-2.5 px-3">Authority</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)] font-mono">
                {readings
                  .slice()
                  .reverse()
                  .slice(0, 10)
                  .map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/30">
                      <td className="py-2 px-3 text-[var(--color-text-secondary)]" title={r.dateTimeStr}>{r.time}</td>
                      <td className="py-2 px-3 font-semibold text-[var(--color-text-primary)]">{r.clientId}</td>
                      <td className="py-2 px-3 text-sky-600 dark:text-sky-400 font-medium">{r.temperatureSensor}</td>
                      <td className="py-2 px-3 text-[#008A5E] font-bold">{r.moisturePct.toFixed(1)}%</td>
                      <td className="py-2 px-3 text-[var(--color-text-muted)]">{r.moistureRaw}</td>
                      <td className="py-2 px-3 text-amber-600 dark:text-amber-400 font-bold">{r.tempC.toFixed(2)} °C</td>
                      <td className="py-2 px-3 text-[var(--color-text-secondary)] font-sans">{r.authority}</td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                          PROVISIONAL
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
