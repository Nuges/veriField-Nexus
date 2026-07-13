# Enterprise Spatial Architecture

**Architecture Version:** v2.0.0
**Status:** Approved
**Highest Authority Document:** `00-climate-operating-model.md`

---

## 1. The Necessity of Spatial Context

Climate impact does not occur in a vacuum; it is fundamentally tied to physical geography. Whether tracking the prevention of deforestation (REDD+), installing a solar micro-grid, or managing a clean cookstove distribution, spatial data dictates compliance, baseline measurements, and leakage tracking.

## 2. Spatial Hierarchy & Inheritance

The CIOS maintains a rigorous geospatial hierarchy using PostGIS (PostgreSQL spatial extension) and standardized GeoJSON vectors.

### 2.1 The Spatial Layers
1. **Global/Continental Layer:** Defined by international treaties (e.g., LDC - Least Developed Countries boundaries).
2. **National Layer:** Sovereign country borders (Administrative Level 0).
3. **Regional/State Layer:** Administrative Level 1 and 2 boundaries.
4. **Jurisdiction Layer:** Custom polygons defined by Regulators where specific climate policies apply.
5. **Community/Village Layer:** Micro-level boundaries used for socio-economic baselining and benefit sharing.
6. **Project Area / Accounting Area:** The specific polygon defining the boundary of a climate project.
7. **Asset Point:** The exact GPS coordinate (Latitude/Longitude) of a physical installation (e.g., a single tree or cookstove).

### 2.2 Spatial Inheritance
Entities inherit metadata based on spatial containment (e.g., `ST_Contains` or `ST_Intersects`).
- If an `Asset Point` is registered at `[-1.9403, 29.8739]` (Rwanda), the system automatically traverses the spatial index upward.
- It detects the Asset falls within `Project Alpha`.
- `Project Alpha` falls within `Jurisdiction: Rwanda National Clean Cooking Initiative`.
- Therefore, the Asset automatically inherits the emission factors and compliance rules of that Jurisdiction without the field agent needing to select it manually.

## 3. Spatial Validation & Compliance

Geospatial overlap is the primary vector for fraudulent double-counting in the carbon market.

### 3.1 Duplicate Prevention
When a new Project Area is submitted, the Spatial Engine executes a collision query against the entire federated registry index. If the new polygon overlaps with an existing registered project of the same sector, the system rejects the submission with a `SpatialOverlapAnomaly`.

### 3.2 GPS Spoofing Detection
Field agents collecting data via the mobile app are subject to strict anti-spoofing checks:
- The app requests raw, high-accuracy GPS satellite locks (disabling mock locations and cellular triangulation overrides).
- The location is cross-referenced with the device's IP geolocation and network tower data.
- If an Asset is registered outside the Project's permitted Spatial Boundary, the Trust Engine flags the Evidence as `QUARANTINED`.

## 4. Remote Sensing & Raster Data

While Project and Asset boundaries are stored as Vector data (Polygons/Points), the MRV engine frequently relies on Raster data (satellite imagery).

- **Integrations:** Nexus integrates with ESA Sentinel or commercial providers (Planet) to retrieve time-series raster imagery for specific project polygons.
- **AI Processing:** Rather than storing terabytes of pixel data in the CIOS operational database, raster imagery is processed by edge AI or cloud GIS pipelines to produce vectors (e.g., tracing a newly deforested patch) or scalar metrics (e.g., NDVI biomass indices). These resulting vectors/metrics are ingested into the Nexus MRV Engine.

## 5. Architecture Traceability
- **Dependent Documents:** `04-digital-mrv-architecture.md`, `11-climate-data-architecture.md`.
- **Primary Technologies:** PostGIS, Turf.js, Mapbox GL.
- **Primary Entities:** `SpatialBoundary`, `Asset`, `Jurisdiction`.
