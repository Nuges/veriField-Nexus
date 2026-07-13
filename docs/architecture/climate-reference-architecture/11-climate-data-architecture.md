# Climate Data Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Climate Data Universe

VeriField Nexus is a massive data ingestion and transformation engine. The Climate Data Architecture maps every major source of data that feeds the MRV and Compliance engines.

## 2. Primary Data Sources

### 2.1 Hardware & Edge Data
- **IoT & Sensors:** Smart meters (electricity), thermal couples (cookstoves), flow meters (water). These stream high-frequency time-series data (e.g., 1 reading per minute) via MQTT/HTTP.
- **Drones (UAVs):** High-resolution localized aerial imagery, used for sampling forest plots or inspecting solar arrays.
- **Mobile GPS / Manual Entry:** The VeriField Nexus Field App. Used when IoT is unviable. Captures offline-first structured surveys, barcodes, and geo-tagged photos.

### 2.2 Remote Sensing Data
- **Satellite Imagery:** Multi-spectral data (Sentinel-1 SAR, Sentinel-2 Optical) used for continuous monitoring over massive geographical areas without deploying human agents.
- **Weather / Meteorological Data:** APIs (e.g., NOAA, OpenWeatherMap) providing historical rainfall, temperature, and solar irradiance data necessary for calculating baselines (e.g., calculating expected vs actual solar yield).

### 2.3 Institutional & Enterprise Data
- **Global Registries:** Master ledger states, methodology parameter updates, and global buffer pool metrics fetched via REST APIs.
- **Government APIs:** National grid emission factors, protected area boundaries, and demographic data.
- **Corporate ERPs / ESG Platforms:** (e.g., SAP Sustainability Control Tower, Salesforce Net Zero Cloud). Direct API integrations allowing corporates to sync their Scope 1/2/3 footprints against the carbon credits retired in Nexus.
- **Utility Systems:** Integration with national grid operators to prove energy was successfully dispatched to the grid from a renewable energy project.

### 2.4 Financial Data
- **Payment Gateways & Escrow Services:** Real-time sync of fiat or stablecoin transactions to trigger the automated benefit-sharing waterfalls.

## 3. Data Ingestion Architecture

Because data arrives in radically different shapes and frequencies, the platform employs a specialized ingestion pipeline.

1. **The Edge Layer:** Mobile apps and IoT devices push data. If the network is down, they queue locally.
2. **The Ingestion Gateway:** A high-throughput, low-latency API endpoint specifically designed to accept raw payloads and push them immediately to an Event Broker (e.g., Kafka).
3. **The Normalization Layer:** Background workers pull from the broker, standardize the schema (e.g., converting all timestamps to UTC, all coordinates to WGS84), and hash the payload.
4. **The Persistence Layer:** 
   - Time-series data (IoT) -> Time-Series Database (e.g., TimescaleDB).
   - Blobs (Photos/Drones) -> Object Storage (S3).
   - Structured Metadata -> Relational Database (PostgreSQL).

## 4. Architecture Traceability
- **Dependent Documents:** `04-digital-mrv-architecture.md`, `07-spatial-architecture.md`.
- **Primary Technologies:** Kafka, TimescaleDB, S3, PostGIS.
