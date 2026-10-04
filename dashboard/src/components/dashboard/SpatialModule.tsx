// =============================================================================
// VeriField Nexus — Spatial Module (with Earth Observation & MRV Integration)
// =============================================================================
// Sector-aware geospatial view combining:
// 1. Interactive Leaflet Map with WGS84 geodesic boundary polygons & asset pins
// 2. Truthful AOI Boundary Status ("NO_AOI" alert if unconfigured)
// 3. Earth Observation Scenes, Derived Layers (NDVI/EVI/NDWI/SAR), and Provenance
// 4. Factual Spatial Anomalies with Field Review Recommendations
// 5. MRV Evidence Manifest Export
// =============================================================================

"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import {
  MapPin,
  List,
  Map as MapIcon,
  Satellite,
  AlertTriangle,
  Layers,
  Download,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { getSectorSpatialConfig } from "@/components/spatial/SectorSpatialConfig";
import {
  fetchProjectActiveAOI,
  fetchProjectObservations,
  fetchDerivedLayers,
  fetchProjectSpatialAnomalies,
  fetchMRVManifest,
  corroborateSpatialAnomaly,
  verifyCOGAsset,
  EOObservationItem,
  EODerivedLayerItem,
  EOSpatialAnomalyItem,
} from "@/lib/api";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });

interface SpatialAsset {
  id: string;
  name: string;
  lat?: number | string;
  lng?: number | string;
  latitude?: number;
  longitude?: number;
  trust?: number;
  trust_score?: number;
  status?: string;
  sector?: string;
  radiusCheck?: string;
}

function parseCoord(val: unknown): number {
  if (typeof val === "number") return val;
  if (typeof val === "string") {
    const cleaned = val.replace(/[NSEW°]/gi, "").trim();
    return parseFloat(cleaned) || 0;
  }
  return 0;
}

function normalizeAsset(a: SpatialAsset, sectorCode?: string) {
  return {
    id: a.id,
    name: a.name,
    lat: parseCoord(a.lat ?? a.latitude),
    lng: parseCoord(a.lng ?? a.longitude),
    trust: a.trust ?? a.trust_score ?? 100,
    status: a.status || "PENDING",
    sector: a.sector || sectorCode,
    radiusCheck: a.radiusCheck,
  };
}

export default function SpatialModule({
  sectorCode,
  assets,
  projectId,
}: {
  sectorCode?: string;
  assets?: SpatialAsset[];
  projectId?: string;
}) {
  const [viewMode, setViewMode] = useState<"map" | "table" | "eo">("map");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);

  // EO state
  const [aoiState, setAoiState] = useState<{
    status: "NO_AOI" | "CONFIGURED" | "LOADING";
    aoi?: any;
    message?: string;
  }>({ status: "LOADING" });
  const [observations, setObservations] = useState<EOObservationItem[]>([]);
  const [derivedLayers, setDerivedLayers] = useState<EODerivedLayerItem[]>([]);
  const [anomalies, setAnomalies] = useState<EOSpatialAnomalyItem[]>([]);
  const [isExportingManifest, setIsExportingManifest] = useState(false);
  const [corroboratingId, setCorroboratingId] = useState<string | null>(null);
  const [selectedObservation, setSelectedObservation] = useState<EOObservationItem | null>(null);
  const [cogTestResult, setCogTestResult] = useState<any>(null);
  const [isTestingCog, setIsTestingCog] = useState(false);

  const handleTestCog = async (obs: EOObservationItem) => {
    if (!projectId || !obs.id) return;
    // Determine the best asset key to test
    const assetKey = obs.raw_band_uris
      ? (Object.keys(obs.raw_band_uris).find(k => ["visual", "nir", "red", "vv"].includes(k))
        || Object.keys(obs.raw_band_uris)[0]
        || "visual")
      : "visual";
    setIsTestingCog(true);
    setCogTestResult(null);
    try {
      const res = await verifyCOGAsset(projectId, obs.id, assetKey);
      setCogTestResult(res);
    } catch (err: any) {
      setCogTestResult({ error: err.message || "Failed to verify COG Range access" });
    } finally {
      setIsTestingCog(false);
    }
  };

  const sectorConfig = useMemo(() => getSectorSpatialConfig(sectorCode), [sectorCode]);
  const assetLabel = sectorConfig.assetPlural.toLowerCase();
  const emptyTitle = sectorConfig.emptyTitle;
  const emptySubtitle = sectorConfig.emptySubtitle;

  // Fetch AOI and EO data when projectId changes
  const loadProjectEOData = useCallback(async () => {
    setSelectedObservation(null);
    setSelectedAsset(null);
    setCogTestResult(null);

    if (!projectId) {
      setAoiState({ status: "NO_AOI", message: "No active project selected." });
      setObservations([]);
      setDerivedLayers([]);
      setAnomalies([]);
      return;
    }

    setAoiState({ status: "LOADING" });
    try {
      const aoiRes = await fetchProjectActiveAOI(projectId);
      if (aoiRes.status === "CONFIGURED" && aoiRes.aoi) {
        setAoiState({ status: "CONFIGURED", aoi: aoiRes.aoi });
        const [obsList, layList, anomList] = await Promise.all([
          fetchProjectObservations(projectId),
          fetchDerivedLayers(projectId),
          fetchProjectSpatialAnomalies(projectId),
        ]);
        setObservations(Array.isArray(obsList) ? obsList : []);
        setDerivedLayers(Array.isArray(layList) ? layList : []);
        setAnomalies(Array.isArray(anomList) ? anomList : []);
      } else {
        setAoiState({ status: "NO_AOI", message: aoiRes.message || "No boundary configured." });
        setObservations([]);
        setDerivedLayers([]);
        setAnomalies([]);
      }
    } catch {
      setAoiState({ status: "NO_AOI", message: "Failed to load project boundary." });
    }
  }, [projectId]);

  useEffect(() => {
    loadProjectEOData();
  }, [loadProjectEOData]);

  // Reset EO observation selection on sector change
  useEffect(() => {
    setSelectedObservation(null);
    setSelectedAsset(null);
    setCogTestResult(null);
  }, [sectorCode]);

  // Handle Export Manifest
  const handleExportManifest = async () => {
    if (!projectId) return;
    setIsExportingManifest(true);
    try {
      const manifest = await fetchMRVManifest(projectId);
      const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mrv-manifest-${projectId.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export manifest failed:", err);
    } finally {
      setIsExportingManifest(false);
    }
  };

  // Handle Anomaly Corroboration
  const handleCorroborate = async (anomalyId: string, corroborated: boolean) => {
    setCorroboratingId(anomalyId);
    try {
      await corroborateSpatialAnomaly(anomalyId, {
        corroborated,
        notes: corroborated ? "Corroborated by ground audit" : "Dismissed after field review",
      });
      if (projectId) {
        const updated = await fetchProjectSpatialAnomalies(projectId);
        setAnomalies(updated);
      }
    } catch (err) {
      console.error("Corroboration failed:", err);
    } finally {
      setCorroboratingId(null);
    }
  };

  // Normalize assets for map
  const normalizedAssets = useMemo(() => {
    const raw = assets && assets.length > 0 ? assets : [];
    return raw.map((a) => normalizeAsset(a, sectorCode));
  }, [assets, sectorCode]);

  const filteredAssets = useMemo(() => {
    if (statusFilter === "all") return normalizedAssets;
    return normalizedAssets.filter(
      (a) => a.status.toUpperCase() === statusFilter.toUpperCase()
    );
  }, [normalizedAssets, statusFilter]);

  const statCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    normalizedAssets.forEach((a) => {
      const s = a.status.toUpperCase();
      counts[s] = (counts[s] || 0) + 1;
    });
    return counts;
  }, [normalizedAssets]);

  const rasterLayerUrl = useMemo(() => {
    if (!selectedObservation) return undefined;
    if (projectId) {
      return `/api/v1/earth-observation/projects/${projectId}/observations/${selectedObservation.id}/raster`;
    }
    return (
      (selectedObservation.raw_band_uris && selectedObservation.raw_band_uris["thumbnail"]) ||
      selectedObservation.asset_uri ||
      (selectedObservation.raw_band_uris
        ? selectedObservation.raw_band_uris["visual"] ||
          selectedObservation.raw_band_uris["red"] ||
          selectedObservation.raw_band_uris["vv"] ||
          Object.values(selectedObservation.raw_band_uris)[0]
        : undefined)
    );
  }, [selectedObservation, projectId]);

  const rasterLayerTitle = useMemo(() => {
    if (!selectedObservation) return undefined;
    const acqDate = selectedObservation.acquisition_timestamp
      ? new Date(selectedObservation.acquisition_timestamp).toLocaleDateString()
      : "N/A";
    if (
      selectedObservation.observation_type === "SAR_C_BAND_BACKSCATTER" ||
      selectedObservation.platform?.includes("Sentinel-1")
    ) {
      return `Sentinel-1 Dual-Pol SAR Quicklook (VV/VH) / Acquired: ${acqDate} (Soil Moisture Model NOT_CONFIGURED)`;
    }
    if (
      selectedObservation.platform?.includes("Landsat") ||
      selectedObservation.is_baseline
    ) {
      return `${selectedObservation.platform} Optical Preview / Historical Baseline / Acquired: ${acqDate}`;
    }
    return `${selectedObservation.platform} Optical Preview / Acquired: ${acqDate}`;
  }, [selectedObservation]);

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Spatial View — {assetLabel}
          </h3>
          <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border border-[var(--color-border)]">
            {filteredAssets.length} {assetLabel}
          </span>
          {aoiState.status === "CONFIGURED" && aoiState.aoi && (
            <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <CheckCircle2 size={11} /> {aoiState.aoi.area_ha.toFixed(1)} ha AOI
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {viewMode !== "eo" && (
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs font-medium bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-2.5 py-1 text-[var(--color-text-primary)]"
            >
              <option value="all">All statuses ({normalizedAssets.length})</option>
              {Object.entries(statCounts).map(([s, c]) => (
                <option key={s} value={s}>{s} ({c})</option>
              ))}
            </select>
          )}

          {/* View toggle */}
          <div className="flex items-center border border-[var(--color-border)] rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode("map")}
              className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                viewMode === "map"
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <MapIcon size={12} /> Map
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                viewMode === "table"
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <List size={12} /> Table
            </button>
            <button
              onClick={() => setViewMode("eo")}
              className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                viewMode === "eo"
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <Satellite size={12} /> EO & MRV
            </button>
          </div>
        </div>
      </div>

      {/* AOI Status Banner (Truthful State) */}
      {aoiState.status === "NO_AOI" && projectId && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs flex items-center justify-between gap-3 text-amber-300">
          <div className="flex items-center gap-2">
            <AlertTriangle size={15} className="shrink-0 text-amber-400" />
            <span>
              <strong>Spatial Invariant Notice:</strong> No authoritative boundary configured for this project. Earth Observation scene ingestion and MRV baseline queries require a defined Area of Interest (AOI).
            </span>
          </div>
        </div>
      )}

      {/* Active Observation Scene Overlay Banner */}
      {selectedObservation && (
        <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/25 flex items-center justify-between text-xs text-blue-300">
          <div className="flex items-center gap-2">
            <Satellite size={14} className="text-blue-400 shrink-0" />
            <span>
              <strong>Active Footprint:</strong> <span className="font-mono text-blue-200">{selectedObservation.scene_id}</span> ({selectedObservation.platform} • {new Date(selectedObservation.acquisition_timestamp).toLocaleDateString()})
            </span>
          </div>
          <button
            type="button"
            onClick={() => setSelectedObservation(null)}
            className="text-xs text-blue-400 hover:text-blue-200 underline cursor-pointer"
          >
            Clear Overlay
          </button>
        </div>
      )}

      {/* Map View */}
      {viewMode === "map" && (
        <div className="relative isolate rounded-xl overflow-hidden">
          <LeafletMap
            assets={filteredAssets}
            sectorCode={sectorCode}
            boundaryGeoJson={aoiState.aoi?.geometry_geojson}
            observationFootprintGeoJson={selectedObservation?.geometry_geojson}
            observationMetadata={selectedObservation}
            rasterLayerUrl={rasterLayerUrl}
            rasterLayerTitle={rasterLayerTitle}
            rasterLayerType={selectedObservation?.observation_type}
            height="500px"
            showRadius={true}
            radiusMeters={50}
            hideEmptyState={true}
            onAssetClick={(a) => setSelectedAsset(a.id)}
          />

          {filteredAssets.length === 0 && !aoiState.aoi && (
            <div
              className="absolute inset-0 flex items-center justify-center pointer-events-none z-[500]"
              role="status"
            >
              <div className="max-w-[380px] w-full mx-4 px-6 py-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm text-center pointer-events-none">
                <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {emptyTitle}
                </p>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                  {emptySubtitle}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Table View */}
      {viewMode === "table" && (
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[var(--color-surface)] text-[var(--color-text-secondary)] text-left">
                <th className="p-3 font-bold">Asset</th>
                <th className="p-3 font-bold">Latitude</th>
                <th className="p-3 font-bold">Longitude</th>
                <th className="p-3 font-bold">Trust</th>
                <th className="p-3 font-bold">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssets.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSelectedAsset(a.id)}
                  className={`border-t border-[var(--color-border)] hover:bg-[var(--color-surface)]/50 cursor-pointer transition-colors ${
                    selectedAsset === a.id ? "bg-[var(--color-primary)]/5" : ""
                  }`}
                >
                  <td className="p-3 font-semibold text-[var(--color-text-primary)]">
                    <MapPin size={12} className="inline mr-1 text-[var(--color-primary)]" />
                    {a.name}
                  </td>
                  <td className="p-3 font-mono text-[var(--color-text-secondary)]">{a.lat.toFixed(4)}</td>
                  <td className="p-3 font-mono text-[var(--color-text-secondary)]">{a.lng.toFixed(4)}</td>
                  <td className="p-3">
                    <span className={`font-bold ${
                      (a.trust ?? 100) >= 80 ? "text-emerald-400" : (a.trust ?? 100) >= 50 ? "text-yellow-400" : "text-red-400"
                    }`}>
                      {a.trust ?? 100}%
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      a.status === "VERIFIED" ? "bg-emerald-500/20 text-emerald-400" :
                      a.status === "PENDING" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-gray-500/20 text-gray-400"
                    }`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredAssets.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-[var(--color-text-secondary)]">
                    No {assetLabel} with geospatial data. Deploy field agents to begin location capture.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Earth Observation & MRV Panel */}
      {viewMode === "eo" && (
        <div className="space-y-4">
          {/* Header & Export Action */}
          <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                <Satellite size={16} className="text-[var(--color-primary)]" />
                Earth Observation & Satellite MRV Pipeline
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Multi-spectral (Sentinel-2, Landsat) & SAR C-Band backscatter (Sentinel-1) with SHA-256 provenance.
              </p>
            </div>
            {aoiState.status === "CONFIGURED" && (
              <button
                type="button"
                onClick={handleExportManifest}
                disabled={isExportingManifest}
                className="px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white text-xs font-medium flex items-center gap-1.5 shadow-xs hover:opacity-90 disabled:opacity-50 cursor-pointer"
              >
                <Download size={13} />
                {isExportingManifest ? "Exporting..." : "MRV Evidence Manifest"}
              </button>
            )}
          </div>

          {/* Scientific & Sector Disclaimer Notice */}
          <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[11px] text-[var(--color-text-muted)] space-y-1.5 leading-relaxed">
            {sectorConfig.sectorDisclaimer && (
              <div className="text-[var(--color-text-secondary)] font-medium pb-1 border-b border-[var(--color-border)]/50">
                • <strong>{sectorConfig.sectorName} Scope:</strong> {sectorConfig.sectorDisclaimer}
              </div>
            )}
            <div>
              • <strong>Spectral Indices:</strong> NDVI & EVI indicate canopy photosynthetic vigor; they do <em>not</em> directly quantify carbon stocks without a calibrated biogeochemical or allometric model.
            </div>
            <div>
              • <strong>SAR Microwave Radar:</strong> Sentinel-1 C-band backscatter reflects radar reflectivity. Soil moisture / SOC models report <em>NOT_CONFIGURED</em> without calibrated ground sensors.
            </div>
          </div>

          {/* Ingested Observations */}
          <div className="rounded-xl border border-[var(--color-border)] overflow-hidden bg-[var(--color-surface)]">
            <div className="p-3 border-b border-[var(--color-border)] font-semibold text-xs text-[var(--color-text-primary)] flex items-center justify-between">
              <span>Ingested Remote Sensing Scenes ({observations.length})</span>
              <span className="text-[11px] font-normal text-[var(--color-text-muted)]">
                Copernicus & USGS Archives
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] text-left">
                    <th className="p-2.5 font-bold">Acquisition</th>
                    <th className="p-2.5 font-bold">Platform / Sensor</th>
                    <th className="p-2.5 font-bold">Scene ID</th>
                    <th className="p-2.5 font-bold">Cloud QA</th>
                    <th className="p-2.5 font-bold">Provenance Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {(Array.isArray(observations) ? observations : []).map((obs) => {
                    const isSelected = selectedObservation?.id === obs.id;
                    return (
                      <tr
                        key={obs.id}
                        onClick={() => setSelectedObservation(isSelected ? null : obs)}
                        className={`border-t border-[var(--color-border)] cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-[var(--color-primary)]/15 border-l-4 border-l-[var(--color-primary)]"
                            : "hover:bg-[var(--color-surface)]/60"
                        }`}
                      >
                        <td className="p-2.5 font-medium text-[var(--color-text-primary)]">
                          {new Date(obs.acquisition_timestamp).toLocaleDateString()}
                        </td>
                        <td className="p-2.5">
                          <span className="font-semibold">{obs.platform}</span> ({obs.sensor})
                        </td>
                        <td className="p-2.5 font-mono text-[11px] text-[var(--color-text-secondary)]">
                          {obs.scene_id}
                        </td>
                        <td className="p-2.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            obs.quality_status === "USABLE"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : obs.quality_status === "PARTIALLY_USABLE"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-red-500/20 text-red-400"
                          }`}>
                            {obs.quality_status} ({obs.cloud_cover_pct !== null && obs.cloud_cover_pct !== undefined ? `${obs.cloud_cover_pct.toFixed(1)}%` : "0%"})
                          </span>
                        </td>
                        <td className="p-2.5 font-mono text-[11px] text-emerald-400" title={obs.provenance_hash}>
                          {obs.provenance_hash.slice(0, 12)}...
                        </td>
                      </tr>
                    );
                  })}
                  {observations.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-[var(--color-text-secondary)]">
                        No satellite scenes currently ingested for this AOI.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Selected Observation & COG Verification Panel */}
            {selectedObservation && (
              <div className="p-4 bg-[var(--color-background)] border-t border-[var(--color-border)] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--color-text-primary)]">
                      Inspecting Scene:
                    </span>
                    <span className="font-mono text-xs text-[var(--color-primary)] font-bold">
                      {selectedObservation.scene_id}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      selectedObservation.quality_status === "USABLE"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {selectedObservation.quality_status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setViewMode("map")}
                      className="px-2.5 py-1 rounded bg-[var(--color-primary)] text-white text-xs font-medium hover:opacity-90 transition-opacity flex items-center gap-1 cursor-pointer"
                    >
                      <MapIcon size={12} /> View on Map
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedObservation(null)}
                      className="text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"
                    >
                      Clear Selection
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-muted)] block">Platform & Sensor</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{selectedObservation.platform} ({selectedObservation.sensor})</span>
                  </div>
                  <div className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-muted)] block">Acquired</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{new Date(selectedObservation.acquisition_timestamp).toLocaleString()}</span>
                  </div>
                  <div className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-muted)] block">Cloud QA</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{selectedObservation.cloud_cover_pct !== null && selectedObservation.cloud_cover_pct !== undefined ? `${selectedObservation.cloud_cover_pct.toFixed(2)}%` : "0%"}</span>
                  </div>
                  <div className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-muted)] block">Footprint Geometry</span>
                    <span className="font-mono text-[11px] text-emerald-400">
                      {selectedObservation.geometry_geojson ? "GeoJSON Active on Map" : "Bounding Box Extent"}
                    </span>
                  </div>
                </div>

                {/* COG Range Verification */}
                <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <span className="text-xs font-semibold text-[var(--color-text-primary)] block">
                        Cloud-Optimized GeoTIFF (COG) HTTP Range Partial-Read Test
                      </span>
                      <span className="text-[11px] text-[var(--color-text-muted)]">
                        Authoritative verification that remote raster assets support HTTP Range requests without downloading full granules.
                      </span>
                    </div>
                    <button
                      onClick={() => handleTestCog(selectedObservation)}
                      disabled={isTestingCog}
                      className="px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5 shrink-0 self-start sm:self-center"
                    >
                      {isTestingCog ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" />
                          Testing HTTP 206...
                        </>
                      ) : (
                        "Verify COG Range Access"
                      )}
                    </button>
                  </div>

                  {cogTestResult && (
                    <div className={`p-2.5 rounded text-xs border ${
                      cogTestResult.error || cogTestResult.status >= 400
                        ? "bg-red-500/10 border-red-500/30 text-red-400"
                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                    }`}>
                      {cogTestResult.error ? (
                        <div><strong>Error:</strong> {cogTestResult.error}</div>
                      ) : (
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-emerald-400">
                              HTTP {cogTestResult.status} Partial Content Confirmed
                            </span>
                            {cogTestResult.is_cog && (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px]">
                                TIFF/COG MAGIC BYTES VERIFIED
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-[11px] text-[var(--color-text-secondary)] break-all">
                            Asset: {cogTestResult.url?.split("?")[0]}
                          </div>
                          <div className="flex flex-wrap gap-4 text-[10px] text-[var(--color-text-muted)] font-mono">
                            <span>Magic Bytes: {cogTestResult.magic_bytes}</span>
                            <span>Range: {cogTestResult.content_range || "bytes 0-1023"}</span>
                            <span>Bytes Read: {cogTestResult.bytes_read}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Derived Layers & Anomalies */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Derived Layers */}
            <div className="rounded-xl border border-[var(--color-border)] p-4 bg-[var(--color-surface)] space-y-3">
              <h5 className="text-xs font-semibold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <Layers size={14} className="text-[var(--color-primary)]" />
                Verified Spectral Layers ({derivedLayers.length})
              </h5>
              {!sectorConfig.supportsVegetationIndices ? (
                <div className="p-3.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)] space-y-2">
                  <p className="font-semibold text-[var(--color-text-secondary)]">
                    Sector Scope: {sectorConfig.sectorName}
                  </p>
                  <p className="leading-relaxed">
                    Vegetation indices (NDVI/EVI/NDWI) and photosynthetic canopy analytics are not applicable to the {sectorConfig.sectorName} sector. Spatial infrastructure is configured for facility perimeter, site boundary, and geographic context.
                  </p>
                  {sectorConfig.allowCrossSectorLinking && (
                    <p className="text-[11px] text-purple-400 font-medium">
                      * Cross-sector linking to verified Agriculture Land Units is enabled for biochar soil application MRV.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {(Array.isArray(derivedLayers) ? derivedLayers : []).map((layer) => (
                    <div key={layer.id} className="p-2.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[var(--color-text-primary)]">{layer.layer_type}</span>
                        <span className="font-mono text-[10px] text-emerald-400">
                          {layer.provenance_hash.slice(0, 8)}...
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--color-text-muted)] font-mono">
                        {layer.formula_identifier}
                      </div>
                      {layer.statistics?.mean !== undefined && (
                        <div className="text-[11px] text-[var(--color-text-secondary)] flex gap-3">
                          <span>Mean: {layer.statistics.mean.toFixed(3)}</span>
                          {layer.statistics.min !== undefined && <span>Min: {layer.statistics.min.toFixed(2)}</span>}
                          {layer.statistics.max !== undefined && <span>Max: {layer.statistics.max.toFixed(2)}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                  {(Array.isArray(derivedLayers) ? derivedLayers : []).length === 0 && (
                    <p className="text-xs text-[var(--color-text-secondary)] text-center py-4">
                      No derived layers computed yet.
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Spatial Anomalies */}
            <div className="rounded-xl border border-[var(--color-border)] p-4 bg-[var(--color-surface)] space-y-3">
              <h5 className="text-xs font-semibold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-amber-400" />
                Spatial Change Signals ({(Array.isArray(anomalies) ? anomalies : []).length})
              </h5>
              <div className="space-y-2">
                {(Array.isArray(anomalies) ? anomalies : []).map((anom) => (
                  <div key={anom.id} className="p-2.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-amber-400">{anom.anomaly_type}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        anom.status === "CORROBORATED" ? "bg-emerald-500/20 text-emerald-400" :
                        anom.status === "DISMISSED" ? "bg-gray-500/20 text-gray-400" :
                        "bg-amber-500/20 text-amber-400"
                      }`}>
                        {anom.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">{anom.description}</p>
                    <div className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] text-[var(--color-text-muted)]">
                      <strong>Recommendation:</strong> {anom.review_recommendation}
                    </div>
                    {anom.status === "OBSERVED" && (
                      <div className="flex gap-2 pt-1">
                        <button
                          type="button"
                          disabled={corroboratingId === anom.id}
                          onClick={() => handleCorroborate(anom.id, true)}
                          className="px-2 py-1 rounded bg-emerald-600 text-white text-[10px] font-medium hover:bg-emerald-500 cursor-pointer disabled:opacity-50"
                        >
                          Corroborate
                        </button>
                        <button
                          type="button"
                          disabled={corroboratingId === anom.id}
                          onClick={() => handleCorroborate(anom.id, false)}
                          className="px-2 py-1 rounded bg-zinc-700 text-zinc-300 text-[10px] font-medium hover:bg-zinc-600 cursor-pointer disabled:opacity-50"
                        >
                          Dismiss
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {anomalies.length === 0 && (
                  <p className="text-xs text-[var(--color-text-secondary)] text-center py-4">
                    No spatial disturbance or vegetation change signals observed.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
