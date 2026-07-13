# Enterprise Integration Catalogue

VeriField Nexus is not an isolated silo. It must seamlessly and securely federate data with global climate standards, financial institutions, and physical IoT hardware.

## 1. Integration Patterns

- **API Gateways & Webhooks (Real-Time):** Used for instant notifications (e.g., notifying a Developer's ERP system that an Audit was approved).
- **Asynchronous Batch Sync (Scheduled):** Used for bulk data alignment (e.g., nightly reconciliation of issued credits with the National Registry).
- **IoT MQTT Brokers (Streaming):** High-throughput ingestion of raw telemetry from smart meters and remote sensors.

## 2. Core Integrations

### 2.1 Carbon Registries (Verra, Gold Standard, UN CDM)
- **Purpose:** Synchronize project statuses and issue/retire carbon credits on the master ledger.
- **Protocol:** REST APIs (JSON) or gRPC.
- **Authentication:** Mutual TLS (mTLS) + OAuth2 Client Credentials.
- **Sync Direction:** Bi-directional.
- **Retry Strategy:** Exponential backoff with jitter up to 5 times, then route to Dead Letter Queue (DLQ) for manual intervention.
- **Error Handling:** Compensating transactions (e.g., if Nexus mints a credit but Verra API rejects it, Nexus executes a rollback event).

### 2.2 National GIS / Cadastral Systems
- **Purpose:** Fetch authoritative shapefiles and land rights data for Jurisdictions and Project overlapping detection.
- **Protocol:** WFS (Web Feature Service) or GeoJSON APIs.
- **Authentication:** API Keys + IP Whitelisting.
- **Sync Direction:** Inbound only (Pull).
- **Frequency:** Weekly or On-Demand Cache Invalidation.

### 2.3 IoT / Hardware Networks (Smart Cookstoves, Inverters)
- **Purpose:** Continuous ingestion of asset telemetry (e.g., liters of water boiled, kWh produced).
- **Protocol:** MQTT via AWS IoT Core or Azure IoT Hub.
- **Authentication:** X.509 Device Certificates.
- **Sync Direction:** Inbound only (Push).
- **Error Handling:** Discard malformed payloads; trigger `DeviceAnomaly` event for persistent drop-offs.

### 2.4 External ERP / ESG Platforms (Salesforce, SAP, ServiceNow)
- **Purpose:** Allow Corporate Buyers or Developers to sync their inventory, asset deployments, and retired credits directly into their corporate systems.
- **Protocol:** Outbound Webhooks.
- **Authentication:** HMAC SHA-256 Signature verification.
- **Retry Strategy:** Up to 3 attempts, alerting the Tenant Admin on failure.

## 3. Webhook Architecture

Nexus provides a robust outbound webhook engine.
1. Developers register an endpoint URL in their Tenant Settings.
2. The `notification-module` subscribes to the central Event Bus.
3. When a matching event occurs (e.g., `CreditRetired`), a background worker fetches the Tenant's webhook configuration.
4. The payload is signed with a secret key.
5. The worker dispatches the HTTP POST and logs the response code for auditability.
