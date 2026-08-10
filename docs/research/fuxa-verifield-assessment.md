# FUXA vs. VeriField Nexus: Architectural Assessment & Selective Enhancement Plan

## Executive Summary
This document provides a technical due-diligence assessment of **FUXA** (an open-source SCADA/HMI web platform by frangoteam) as a reference for enhancing **VeriField Nexus** (a production-grade climate MRV and CIOS platform).

FUXA is designed for real-time industrial process supervisory control (PLC, Modbus, OPC-UA, industrial HMIs). VeriField Nexus is an institutional climate MRV platform designed for carbon project origination, IoT telemetry ingestion, automated GHG emission reduction calculations, digital twin validation, VVB audit evidence, and carbon credit issuance.

We **do not** turn VeriField into SCADA, nor do we introduce drag-and-drop HMI canvas editors or industrial tags. Instead, we selectively translate FUXA's most effective operational patterns—**Historical Telemetry Historian controls**, **Data Quality & Anomaly Event streams**, **Asset Operational Health indicators**, and **Multi-angle Project Monitoring views**—into native, production-grade VeriField Nexus features.

---

## 1. Domain Terminology Mapping

| FUXA SCADA Concept | VeriField Nexus Climate MRV Equivalent | Operational Context in VeriField |
| :--- | :--- | :--- |
| **FUXA Device** | **VeriField Asset / Telemetry Node** | Smart cookstove, solar inverter, EV charger, biochar kiln sensor |
| **FUXA Tag / Variable** | **Monitoring Variable / Telemetry Key** | Power output (kW), fuel weight (kg), energy generated (kWh), GPS coordinates |
| **FUXA Historian (DAQ)** | **Historical Monitoring Data & Telemetry Ledger** | Time-series telemetry logs stored with cryptographic hash proofs |
| **FUXA Alarm / Event** | **Data Quality & Verification Event** | Anomaly alert, telemetry drop, tamper flag, trust score penalty |
| **FUXA HMI View** | **Project Monitoring View** | Sector-tailored operational monitoring dashboard |
| **FUXA Project** | **Climate Project** | Carbon credit origination project (Clean Cookstoves, Solar, EV, Biochar) |

---

## 2. Licence & Dependency Review

- **FUXA Core Licence**: MIT Licence (Open Source).
- **Attribution & Usage**: Unrestricted commercial and private reuse permitted under MIT terms.
- **Dependency Decision**: **Zero external FUXA code copied directly.** All enhancements are implemented natively using VeriField's existing Next.js, React, Tailwind CSS, Recharts, Lucide-react, FastAPI, and SQLAlchemy architecture. This guarantees zero bloat, zero security vulnerability exposure, and perfect architectural alignment.

---

## 3. Feature Mapping & Assessment Matrix

| FUXA Feature | VeriField Equivalent | Current VeriField Status | Value | Implementation Approach | Risk | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Historian DAQ & Trend Viewer** | **Historical Telemetry Historian & Time Window Controls** | Partially Implemented (Charts exist, lacking interactive granular controls) | **HIGH** | Native React time-range selector (24h, 7d, 30d, 90d), granularity switcher (Raw, Hourly, Daily), and CSV/JSON exporter in `TelemetryHistorianConsole.tsx` | LOW | **HIGH** |
| **Real-time Alarm Stream** | **Data Quality & Verification Event Stream** | Partially Implemented (Anomalies page exists, lacking inline project dashboard stream) | **HIGH** | Native inline event stream with severity badges (CRITICAL, WARNING, INFO), status toggle (ACTIVE, ACKNOWLEDGED, RESOLVED), and evidence links in `DataQualityEventConsole.tsx` | LOW | **HIGH** |
| **Device Status Indicators** | **Asset Operational Health & Telemetry Status Badges** | Static / Basic | **HIGH** | Real-time health calculation (ONLINE, OFFLINE, STALE, ANOMALY) based on telemetry timestamp delta and trust score | LOW | **HIGH** |
| **Configurable Views** | **Project View Switcher (Overview, Historian, Events, Assets, Audit)** | Fixed Views | **MEDIUM** | Tabbed monitoring view controller in sector dashboards and project detail views | LOW | **MEDIUM** |
| **Drag-and-Drop Canvas Editor** | N/A (SCADA HMI Editor) | Not Needed | **NONE** | **REJECTED**: VeriField is a metadata-driven MRV platform, not a SCADA drawing tool. Canvas builder adds unacceptable complexity without user value. | HIGH | **REJECTED** |
| **Industrial PLC Protocols (Modbus/OPC-UA)** | IIoT Telemetry Ingestion API / MQTT Broker | Backend Ingestion Service Active | **HIGH** | Keep existing FastAPI IIoT endpoints (`/api/v1/iiot/telemetry`). No SCADA protocol changes needed. | LOW | **EXISTING** |

---

## 4. High-Value Enhancements Selected for Implementation

Based on our audit and assessment, we are implementing 3 high-value operational enhancements natively in VeriField Nexus:

1. **Interactive Historical Telemetry Historian (`TelemetryHistorianConsole.tsx`)**:
   - Time-range selector (24 Hours, 7 Days, 30 Days, 90 Days, All-time).
   - Aggregation granularity control (Raw Telemetry, Hourly Averages, Daily Totals).
   - Telemetry metric toggle (CO₂ Avoided, Power/Energy, Fuel Usage, Temperature/Efficiency).
   - Data provenance & cryptographic hash status indicator.
   - One-click CSV and JSON export for VVB auditors.

2. **Data Quality & Verification Event Stream (`DataQualityEventConsole.tsx`)**:
   - Real-time stream of automated data quality flags (e.g. Telemetry Silence, Sensor Calibration Drift, Spatial Outlier, Duplicate Payload).
   - Interactive filtering by Severity (`CRITICAL`, `WARNING`, `INFO`) and Status (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`).
   - Acknowledge & resolve action buttons with audit trail logging.

3. **Asset Operational Health Matrix & Status Badges**:
   - Active status badges (ONLINE, OFFLINE, TELEMETRY STALE, ANOMALY DETECTED).
   - Telemetry freshness indicators (e.g., "Last heartbeat 4m ago").
   - Integrated into Project Monitoring and Asset Directory surfaces.

---

## 5. Verification & Security Compliance
- **Tenant & Project Isolation**: All data queries enforce `organization_id` and `project_id` RBAC scoping.
- **Data Provenance**: All telemetry data links to underlying evidence records and immutable digital twin states.
- **Zero Simulation**: All backend endpoints query real database models (`activities`, `assets`, `projects`, `energy_telemetry_logs`, `cookstove_devices`, `biochar_batches`, `ev_charging_sessions`).
