// =============================================================================
// VeriField Nexus — Sector-Aware Enterprise Spatial Boundary Map
// =============================================================================
// Production-grade geospatial map component implementing:
// 1. Basemap selector (Street / Dark Map vs Real Satellite Imagery)
// 2. Sector-aware MRV Overlays (Agriculture, Biochar, Hybrid, EV, Cookstoves)
// 3. Earth Observation integration (Sentinel-2, Sentinel-1 SAR, Landsat)
//    with cryptographic provenance metadata panel and scene date selection
// 4. Invariant compliance:
//    - Satellite spectral index != Carbon
//    - SAR backscatter is a physical proxy, never direct soil moisture
//    - No hardcoded pins, fake locations, or mock commercial scenes
// 5. Parity with data tables and dynamic extent fitting
// =============================================================================

"use client";

import React, { useEffect, useState, useMemo, useRef, useCallback, useSyncExternalStore } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Layers,
  Map as MapIcon,
  Satellite,
  Info,
  Calendar,
  ShieldCheck,
  ChevronDown,
  Eye,
  EyeOff
} from "lucide-react";
import {
  getSectorSpatialConfig,
  BasemapType
} from "@/components/spatial/SectorSpatialConfig";
import {
  fetchActivities,
  fetchProperties,
  fetchLandUnits,
  fetchSoilSamples,
  fetchTreeObservations,
  fetchSatelliteObservations,
  fetchProductionFacilities,
  fetchBiocharSources,
  fetchBiocharEndUses,
  SatelliteObservationRecord,
  LandUnitRecord,
  SoilSampleRecord,
  TreeObservationRecord,
  ProductionFacilityRecord,
  FeedstockSourceRecord,
  BiocharEndUseItem
} from "@/lib/api";

// Fix Leaflet Default Icon prototype issue in Next.js
if (typeof window !== "undefined") {
  delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
  });
}

export interface MapMarkerItem {
  id: string;
  name: string;
  layerId: string;
  type: string;
  lat: number;
  lng: number;
  status: string;
  subtitle?: string;
  attributes?: Record<string, unknown>;
  color: string;
}

export interface SpatialBoundaryMapProps {
  sectorCode?: string;
  projectId?: string | null;
  activeScope?: "SITE" | "REGIONAL" | "NATIONAL" | "GLOBAL";
  activeTab?: string; // backwards compatibility
  data?: { boundary_geojson?: GeoJSON.GeoJsonObject; [key: string]: unknown } | null;
  onSelectEntity?: (entity: MapMarkerItem) => void;
  height?: string;
}

// Controller to dynamically adjust viewport based on features and scope
const MapViewController = ({
  activeScope,
  markers,
  geojsons,
  hasLoaded
}: {
  activeScope: string;
  markers: MapMarkerItem[];
  geojsons: GeoJSON.GeoJsonObject[];
  hasLoaded: boolean;
}) => {
  const map = useMap();
  const initialFitDone = useRef(false);

  useEffect(() => {
    if (!map || !hasLoaded) return;

    try {
      if (activeScope === "GLOBAL") {
        map.flyTo([15.0, 10.0], 2, { duration: 1.2 });
        return;
      }

      if (activeScope === "NATIONAL") {
        if (markers.length > 0) {
          const lats = markers.map(m => m.lat);
          const lngs = markers.map(m => m.lng);
          const avgLat = lats.reduce((a, b) => a + b, 0) / lats.length;
          const avgLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;
          map.flyTo([avgLat, avgLng], 6, { duration: 1.2 });
        } else {
          // Neutral continental/regional center without hardcoding a single host country
          map.flyTo([0.0, 20.0], 4, { duration: 1.2 });
        }
        return;
      }

      if (activeScope === "REGIONAL") {
        if (markers.length > 0) {
          const lats = markers.map(m => m.lat);
          const lngs = markers.map(m => m.lng);
          const avgLat = lats.reduce((a, b) => a + b, 0) / lats.length;
          const avgLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;
          map.flyTo([avgLat, avgLng], 8, { duration: 1.2 });
        } else {
          // Neutral regional fallback
          map.flyTo([0.0, 20.0], 5, { duration: 1.2 });
        }
        return;
      }

      // SITE SCOPE: Fit tightly to actual features
      const bounds = L.latLngBounds([]);
      let pointCount = 0;

      markers.forEach(m => {
        if (!isNaN(m.lat) && !isNaN(m.lng)) {
          bounds.extend([m.lat, m.lng]);
          pointCount++;
        }
      });

      geojsons.forEach(gj => {
        try {
          const layer = L.geoJSON(gj);
          const b = layer.getBounds();
          if (b.isValid()) {
            bounds.extend(b);
            pointCount++;
          }
        } catch {}
      });

      if (pointCount > 0 && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16, duration: 1.2 });
      } else if (!initialFitDone.current) {
        // Neutral fallback without implying a fake project location
        map.setView([0.0, 20.0], 3);
      }
      initialFitDone.current = true;
    } catch (err) {
      console.warn("Map flyTo navigation notice:", err);
    }
  }, [activeScope, markers, geojsons, hasLoaded, map]);

  return null;
};

export default function SpatialBoundaryMap({
  sectorCode = "COOKSTOVES",
  projectId = null,
  activeScope: propScope,
  activeTab,
  data,
  onSelectEntity,
  height = "100%"
}: SpatialBoundaryMapProps) {
  const isMounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const [loading, setLoading] = useState(true);

  // Basemap selector: map (dark canvas) vs satellite (Esri World Imagery)
  const [basemap, setBasemap] = useState<BasemapType>("map");

  // Normalized active scope
  const activeScope = useMemo(() => {
    const raw = propScope || activeTab || "SITE";
    if (raw === "MICRO" || raw === "SITE") return "SITE";
    if (raw === "REGIONAL") return "REGIONAL";
    if (raw === "NATIONAL") return "NATIONAL";
    if (raw === "GLOBAL") return "GLOBAL";
    return "SITE";
  }, [propScope, activeTab]);

  // Sector Spatial Configuration
  const sectorConfig = useMemo(() => getSectorSpatialConfig(sectorCode), [sectorCode]);

  // Layer Visibility State (defaults derived from sector config, overrides stored in state)
  const [layerOverrides, setLayerOverrides] = useState<Record<string, boolean>>({});
  const [showLayerMenu, setShowLayerMenu] = useState(false);
  const [showLegend, setShowLegend] = useState(true);

  // Derive active layers from sector config and overrides
  const activeLayers = useMemo(() => {
    const state: Record<string, boolean> = {};
    sectorConfig.availableLayers.forEach(l => {
      state[l.id] = layerOverrides[l.id] ?? l.enabledByDefault;
    });
    return state;
  }, [sectorConfig, layerOverrides]);

  // Loaded Spatial Datasets
  const [markers, setMarkers] = useState<MapMarkerItem[]>([]);
  const [landUnits, setLandUnits] = useState<LandUnitRecord[]>([]);
  const [eoObservations, setEoObservations] = useState<SatelliteObservationRecord[]>([]);
  const [selectedEoScene, setSelectedEoScene] = useState<SatelliteObservationRecord | null>(null);
  const [showEoPanel, setShowEoPanel] = useState(false);

  // Fetch real sector-specific geospatial entities
  useEffect(() => {
    let isCancelled = false;

    async function loadSectorSpatialData() {
      setLoading(true);
      try {
        const canon = sectorConfig.sectorCode;
        const newMarkers: MapMarkerItem[] = [];
        let newLandUnits: LandUnitRecord[] = [];
        let newEoObs: SatelliteObservationRecord[] = [];

        if (canon === "AGRICULTURE_LAND_USE" || canon === "AFOLU") {
          const [luRes, soilRes, treeRes, eoRes, actRes] = await Promise.all([
            fetchLandUnits(projectId || undefined).catch(() => []),
            fetchSoilSamples(projectId || undefined).catch(() => []),
            fetchTreeObservations(projectId || undefined).catch(() => []),
            fetchSatelliteObservations(projectId || undefined).catch(() => []),
            fetchActivities({ per_page: 500, project_id: projectId || undefined }).catch(() => null)
          ]);

          newLandUnits = luRes || [];
          newEoObs = eoRes || [];

          // Soil Samples
          (soilRes || []).forEach((s: SoilSampleRecord) => {
            if (s.latitude && s.longitude) {
              newMarkers.push({
                id: s.id,
                name: `Soil Sample: ${s.sample_code}`,
                layerId: "soil_samples",
                type: "SOIL_SAMPLE",
                lat: s.latitude,
                lng: s.longitude,
                status: s.organic_carbon_pct ? `${s.organic_carbon_pct}% SOC` : "Analyzed",
                subtitle: `Depth: ${s.depth_top_cm}-${s.depth_bottom_cm}cm • ${s.collection_date || ""}`,
                attributes: s as unknown as Record<string, unknown>,
                color: "#3B82F6"
              });
            }
          });

          // Tree Observations
          (treeRes || []).forEach((t: TreeObservationRecord) => {
            if (t.latitude && t.longitude) {
              newMarkers.push({
                id: t.id,
                name: `Tree: ${t.tree_tag || "Observation"}`,
                layerId: "tree_observations",
                type: "TREE_OBSERVATION",
                lat: t.latitude,
                lng: t.longitude,
                status: "VERIFIED",
                subtitle: `DBH: ${t.dbh_cm}cm ${t.species_name ? `• ${t.species_name}` : ""}`,
                attributes: t as unknown as Record<string, unknown>,
                color: "#059669"
              });
            }
          });

          // Field activities with GPS
          if (actRes?.activities && Array.isArray(actRes.activities)) {
            actRes.activities.forEach(a => {
              if (a.latitude !== null && a.latitude !== undefined && a.longitude !== null && a.longitude !== undefined) {
                const lat = Number(a.latitude);
                const lng = Number(a.longitude);
                if (!isNaN(lat) && !isNaN(lng)) {
                  const aData = a.activity_data as Record<string, unknown> | null;
                  const rawA = a as unknown as Record<string, unknown>;
                  newMarkers.push({
                    id: a.id,
                    name: (aData?.title as string) || (rawA.name as string) || `Activity ${a.id.substring(0, 6)}`,
                    layerId: "field_activities",
                    type: "FIELD_ACTIVITY",
                    lat,
                    lng,
                    status: ((rawA.status as string) || "COMPLETED").toUpperCase(),
                    subtitle: a.activity_type || "Conservation Action",
                    attributes: a as unknown as Record<string, unknown>,
                    color: "#EC4899"
                  });
                }
              }
            });
          }
        } else if (canon === "BIOCHAR") {
          const [facRes, srcRes, endRes, luRes, eoRes] = await Promise.all([
            fetchProductionFacilities(projectId || undefined).catch(() => []),
            fetchBiocharSources(projectId || undefined).catch(() => []),
            fetchBiocharEndUses(projectId || undefined).catch(() => []),
            fetchLandUnits().catch(() => []), // For linked agricultural land
            fetchSatelliteObservations(projectId || undefined).catch(() => [])
          ]);

          newLandUnits = luRes || [];
          newEoObs = eoRes || [];

          // Production Facilities
          (facRes || []).forEach((f: ProductionFacilityRecord) => {
            // Check if coordinates stored in permits_json or location
            const lat = f.permits_json?.latitude || f.permits_json?.lat;
            const lng = f.permits_json?.longitude || f.permits_json?.lng;
            if (lat && lng) {
              newMarkers.push({
                id: f.id,
                name: f.facility_name,
                layerId: "facilities",
                type: "PRODUCTION_FACILITY",
                lat: parseFloat(lat),
                lng: parseFloat(lng),
                status: f.facility_status || "OPERATIONAL",
                subtitle: `${f.technology_type} • ${f.location || ""}`,
                attributes: f as unknown as Record<string, unknown>,
                color: "#8B5CF6"
              });
            }
          });

          // Feedstock Sources
          (srcRes || []).forEach((s: FeedstockSourceRecord) => {
            const lat = s.metadata_json?.latitude || s.metadata_json?.lat;
            const lng = s.metadata_json?.longitude || s.metadata_json?.lng;
            if (lat && lng) {
              newMarkers.push({
                id: s.id,
                name: s.source_name,
                layerId: "feedstock_sources",
                type: "FEEDSTOCK_SOURCE",
                lat: parseFloat(lat),
                lng: parseFloat(lng),
                status: s.waste_status || "CONFIRMED_WASTE",
                subtitle: `${s.source_type} • ${s.biomass_type}`,
                attributes: s as unknown as Record<string, unknown>,
                color: "#10B981"
              });
            }
          });

          // End-Use Sites
          (endRes || []).forEach((e: BiocharEndUseItem) => {
            if (e.gps_coordinates) {
              const parts = e.gps_coordinates.split(",").map((p: string) => parseFloat(p.trim()));
              if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                newMarkers.push({
                  id: e.id,
                  name: `End Use: ${e.end_use_type}`,
                  layerId: "end_use_sites",
                  type: "END_USE_SITE",
                  lat: parts[0],
                  lng: parts[1],
                  status: e.verification_status || "VERIFIED",
                  subtitle: `${e.applied_quantity_tonnes}t applied • ${e.application_method || ""}`,
                  attributes: e as unknown as Record<string, unknown>,
                  color: "#EC4899"
                });
              }
            }
          });
        } else if (canon === "HYBRID_ENERGY" || canon === "ENERGY") {
          const propRes = await fetchProperties(100).catch(() => null);
          const items = propRes?.properties || [];
          items.forEach(item => {
            if (item.latitude !== null && item.latitude !== undefined && item.longitude !== null && item.longitude !== undefined) {
              const lat = Number(item.latitude);
              const lng = Number(item.longitude);
              if (!isNaN(lat) && !isNaN(lng)) {
                const rawItem = item as unknown as Record<string, unknown>;
                const type = item.property_type || "GENERATION_ASSET";
                const isMeter = type.toLowerCase().includes("meter") || type.toLowerCase().includes("inverter");
                const isGen = type.toLowerCase().includes("diesel") || type.toLowerCase().includes("generator");
                const layerId = isMeter ? "inverters_meters" : isGen ? "generators" : "generation_assets";
                const color = isMeter ? "#10B981" : isGen ? "#F59E0B" : "#3B82F6";

                newMarkers.push({
                  id: item.id,
                  name: item.name || "Energy Installation",
                  layerId,
                  type: type.toUpperCase(),
                  lat,
                  lng,
                  status: (rawItem.status as string) || "ACTIVE",
                  subtitle: `${rawItem.capacity_kw ? `${rawItem.capacity_kw} kW • ` : ""}${(item.address as string) || ""}`,
                  attributes: item as unknown as Record<string, unknown>,
                  color
                });
              }
            }
          });
        } else if (canon === "EV_MOBILITY" || canon === "EV") {
          const propRes = await fetchProperties(100).catch(() => null);
          const items = propRes?.properties || [];
          items.forEach(item => {
            if (item.latitude !== null && item.latitude !== undefined && item.longitude !== null && item.longitude !== undefined) {
              const lat = Number(item.latitude);
              const lng = Number(item.longitude);
              if (!isNaN(lat) && !isNaN(lng)) {
                const rawItem = item as unknown as Record<string, unknown>;
                newMarkers.push({
                  id: item.id,
                  name: item.name || "Charging Station",
                  layerId: "charging_stations",
                  type: "CHARGING_STATION",
                  lat,
                  lng,
                  status: (rawItem.status as string) || "ONLINE",
                  subtitle: `${rawItem.chargers_count || 1} outlets • ${(item.address as string) || ""}`,
                  attributes: item as unknown as Record<string, unknown>,
                  color: "#10B981"
                });
              }
            }
          });
        } else {
          // COOKSTOVES (privacy-safe clustering)
          const actRes = await fetchActivities({ per_page: 500, project_id: projectId || undefined }).catch(() => null);
          if (actRes?.activities && Array.isArray(actRes.activities)) {
            const isCluster = sectorConfig.privacySafeClustering;
            if (isCluster) {
              // Group individual household coordinates by generalized grid cells (~1.1km / 2 decimals)
              const clusterMap = new Map<string, { lat: number; lng: number; location: string; count: number; ids: string[] }>();
              actRes.activities.forEach((a) => {
                if (a.latitude !== null && a.latitude !== undefined && a.longitude !== null && a.longitude !== undefined) {
                  const rawLat = Number(a.latitude);
                  const rawLng = Number(a.longitude);
                  if (!isNaN(rawLat) && !isNaN(rawLng)) {
                    const gridLat = Math.round(rawLat * 100) / 100;
                    const gridLng = Math.round(rawLng * 100) / 100;
                    const key = `${gridLat.toFixed(2)},${gridLng.toFixed(2)}`;
                    const data = a.activity_data as Record<string, unknown> | null;
                    const loc = (data?.location_name as string) || (data?.address as string) || "Community Area";
                    const existing = clusterMap.get(key);
                    if (existing) {
                      existing.count += 1;
                      existing.ids.push(a.id);
                    } else {
                      clusterMap.set(key, { lat: gridLat, lng: gridLng, location: loc, count: 1, ids: [a.id] });
                    }
                  }
                }
              });
              clusterMap.forEach((cl, key) => {
                newMarkers.push({
                  id: `cluster-${key}`,
                  name: `Cluster • ${cl.location} (${cl.count} ${cl.count === 1 ? "Device" : "Devices"})`,
                  layerId: "deployment_clusters",
                  type: "COOKSTOVE_CLUSTER",
                  lat: cl.lat,
                  lng: cl.lng,
                  status: "VERIFIED",
                  subtitle: `Privacy Aggregated Grid • ${cl.count} units`,
                  attributes: { grid_key: key, device_count: cl.count, device_ids: cl.ids },
                  color: "#F59E0B"
                });
              });
            } else {
              // Exact coordinate mapping for authorized forensic audits
              actRes.activities.forEach((a, idx: number) => {
                if (a.latitude !== null && a.latitude !== undefined && a.longitude !== null && a.longitude !== undefined) {
                  const lat = Number(a.latitude);
                  const lng = Number(a.longitude);
                  if (!isNaN(lat) && !isNaN(lng)) {
                    const data = a.activity_data as Record<string, unknown> | null;
                    const rawA = a as unknown as Record<string, unknown>;
                    const locationName = (data?.location_name as string) || (data?.address as string) || "Field Location";
                    const title = (data?.burner_name as string) || (data?.title as string) || (rawA.name as string) || `Stove • ${(a.id || "").substring(0, 8)}`;
                    newMarkers.push({
                      id: a.id || `act-${idx}`,
                      name: title,
                      layerId: "devices",
                      type: (a.activity_type || "CLEAN_COOKSTOVE").toUpperCase(),
                      lat,
                      lng,
                      status: ((rawA.status as string) || "VERIFIED").toUpperCase(),
                      subtitle: `${locationName} • Verified Unit`,
                      attributes: a as unknown as Record<string, unknown>,
                      color: "#10B981"
                    });
                  }
                }
              });
            }
          }
        }

        if (!isCancelled) {
          setMarkers(newMarkers);
          setLandUnits(newLandUnits);
          setEoObservations(newEoObs);
          if (newEoObs.length > 0) {
            setSelectedEoScene(newEoObs[0]);
          } else {
            setSelectedEoScene(null);
          }
        }
      } catch (err) {
        console.warn("SpatialBoundaryMap data query warning:", err);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    }

    loadSectorSpatialData();
    return () => {
      isCancelled = true;
    };
  }, [sectorConfig, projectId]);

  // Toggle layer
  const toggleLayer = useCallback((layerId: string) => {
    setLayerOverrides(prev => {
      const current = prev[layerId] ?? sectorConfig.availableLayers.find(l => l.id === layerId)?.enabledByDefault ?? true;
      return {
        ...prev,
        [layerId]: !current
      };
    });
  }, [sectorConfig]);

  // Filter visible markers based on active layer toggles
  const visibleMarkers = useMemo(() => {
    return markers.filter(m => activeLayers[m.layerId] !== false);
  }, [markers, activeLayers]);

  // Boundary polygons to render
  const boundaryGeoJsons = useMemo(() => {
    const list: GeoJSON.GeoJsonObject[] = [];
    if (data?.boundary_geojson && activeLayers["boundaries"] !== false) {
      list.push(data.boundary_geojson as GeoJSON.GeoJsonObject);
    }
    return list;
  }, [data, activeLayers]);

  // Land units polygons to render
  const visibleLandUnits = useMemo(() => {
    if (activeLayers["land_units"] === false && activeLayers["linked_land_units"] === false) {
      return [];
    }
    return landUnits.filter(u => u.boundary_geojson);
  }, [landUnits, activeLayers]);

  if (!isMounted) {
    return <div className="h-full w-full bg-slate-900 animate-pulse rounded-xl" />;
  }

  const hasAnyFeatures = visibleMarkers.length > 0 || visibleLandUnits.length > 0 || boundaryGeoJsons.length > 0;
  const isEoActive = activeLayers["sentinel_2"] || activeLayers["sentinel_1"] || activeLayers["landsat"];

  return (
    <div className="h-full w-full relative isolate rounded-xl overflow-hidden border border-[var(--color-border)] shadow-sm bg-slate-950">
      {/* ─── Top Map Controls: Basemap Selector & Layer Control Button ─── */}
      <div className="absolute top-3 left-3 z-[600] flex items-center gap-2">
        {/* Basemap Toggle: Map vs Real Satellite */}
        <div className="flex items-center p-0.5 rounded-lg bg-slate-900/90 backdrop-blur-md border border-slate-700/60 shadow-lg text-[11px] font-semibold">
          <button
            type="button"
            aria-label="Select Map Basemap"
            onClick={() => setBasemap("map")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all ${
              basemap === "map"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-slate-300 hover:text-white"
            }`}
          >
            <MapIcon size={12} />
            <span>Map</span>
          </button>
          <button
            type="button"
            aria-label="Select Satellite Basemap"
            onClick={() => setBasemap("satellite")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all ${
              basemap === "satellite"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-slate-300 hover:text-white"
            }`}
          >
            <Satellite size={12} />
            <span>Satellite</span>
          </button>
        </div>

        {/* Layers Button */}
        <div className="relative">
          <button
            type="button"
            aria-label="Toggle Layer Control Menu"
            aria-expanded={showLayerMenu}
            onClick={() => setShowLayerMenu(!showLayerMenu)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all backdrop-blur-md border shadow-lg ${
              showLayerMenu
                ? "bg-slate-800 text-white border-[var(--color-primary)]/50"
                : "bg-slate-900/90 text-slate-300 hover:text-white border-slate-700/60"
            }`}
          >
            <Layers size={13} className="text-[var(--color-primary)]" />
            <span>Layers</span>
            <ChevronDown size={11} className={`transition-transform ${showLayerMenu ? "rotate-180" : ""}`} />
          </button>

          {/* Layer Menu Dropdown */}
          {showLayerMenu && (
            <div className="absolute top-8 left-0 w-64 p-3 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 shadow-2xl text-xs space-y-3 z-[700] text-slate-200">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-semibold text-xs text-slate-300">
                  {sectorConfig.sectorName} Layers
                </span>
                <span className="text-[11px] font-medium text-[var(--color-primary)]">
                  {Object.values(activeLayers).filter(Boolean).length} Active
                </span>
              </div>

              {/* Project & Evidence Layers */}
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                {sectorConfig.availableLayers.map(layer => {
                  const isChecked = activeLayers[layer.id] !== false;
                  return (
                    <label
                      key={layer.id}
                      className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-800/80 cursor-pointer transition-colors text-[11px]"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: layer.color || "var(--color-primary)" }}
                        />
                        <span className="truncate">{layer.name}</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleLayer(layer.id)}
                        className="rounded border-slate-700 bg-slate-950 text-[var(--color-primary)] focus:ring-[var(--color-primary)] shrink-0 cursor-pointer"
                      />
                    </label>
                  );
                })}
              </div>

              {/* Invariant Note */}
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[9px] text-slate-400 space-y-0.5 leading-snug">
                <div className="font-semibold text-emerald-400 flex items-center gap-1">
                  <ShieldCheck size={10} />
                  <span>Ground-Coupled MRV Invariant</span>
                </div>
                <div>Satellite imagery provides spatial context. Never direct proof of carbon removal.</div>
              </div>
            </div>
          )}
        </div>

        {/* Legend Toggle */}
        <button
          type="button"
          aria-label="Toggle Map Legend"
          onClick={() => setShowLegend(!showLegend)}
          className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold backdrop-blur-md border shadow-lg transition-all ${
            showLegend
              ? "bg-slate-800 text-white border-slate-700"
              : "bg-slate-900/90 text-slate-400 hover:text-white border-slate-700/60"
          }`}
        >
          {showLegend ? <Eye size={12} /> : <EyeOff size={12} />}
          <span className="hidden sm:inline">Legend</span>
        </button>
      </div>

      {/* ─── Top Right Status Pill: Scope & Data Status ─── */}
      <div className="absolute top-3 right-3 z-[600] flex items-center gap-2">
        <div className="px-3 py-1 rounded-lg bg-slate-900/90 backdrop-blur-md border border-slate-700/60 text-xs text-slate-300 shadow-md flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] shrink-0" />
          <span className="font-medium">{activeScope ? activeScope.charAt(0) + activeScope.slice(1).toLowerCase() : "Site"} view</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-300 font-semibold">{visibleMarkers.length + visibleLandUnits.length} features</span>
        </div>
      </div>

      {/* ─── Leaflet Map Container ─── */}
      <MapContainer
        center={[0.0, 20.0]}
        zoom={3}
        style={{ height, width: "100%" }}
        className="z-0"
        zoomControl={true}
        attributionControl={true}
      >
        {/* Basemap Tile Layer */}
        {basemap === "map" ? (
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url={process.env.NEXT_PUBLIC_MAP_TILE_URL || "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"}
            maxZoom={19}
            className="map-tiles"
          />
        ) : (
          <TileLayer
            attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={18}
          />
        )}

        {/* Viewport & Extent Controller */}
        <MapViewController
          activeScope={activeScope}
          markers={visibleMarkers}
          geojsons={visibleLandUnits.map(u => u.boundary_geojson).concat(boundaryGeoJsons)}
          hasLoaded={!loading}
        />

        {/* Project Boundaries */}
        {boundaryGeoJsons.map((geo, idx) => (
          <GeoJSON
            key={`bound-${idx}`}
            data={geo}
            style={{
              color: "#00B47A",
              weight: 2.5,
              fillColor: "#059669",
              fillOpacity: 0.2,
            }}
          />
        ))}

        {/* Land Units / Agricultural Parcels */}
        {visibleLandUnits.map(unit => (
          <GeoJSON
            key={unit.id}
            data={unit.boundary_geojson}
            style={{
              color: unit.unit_type === "MONITORING_PLOT" ? "#F59E0B" : "#10B981",
              weight: unit.unit_type === "MONITORING_PLOT" ? 2 : 2.5,
              fillColor: unit.unit_type === "MONITORING_PLOT" ? "#D97706" : "#059669",
              fillOpacity: 0.25,
              dashArray: unit.unit_type === "MONITORING_PLOT" ? "4, 4" : undefined,
            }}
          >
            <Popup className="custom-dark-popup">
              <div className="p-3 space-y-1 text-xs bg-slate-950 text-white rounded-lg font-mono">
                <div className="font-bold text-emerald-400">{unit.name}</div>
                <div className="text-slate-300">Type: {unit.unit_type}</div>
                <div className="text-slate-300">Area: {unit.area_ha.toFixed(2)} ha</div>
                <div className="text-emerald-300">Status: {unit.is_active ? "ACTIVE" : "INACTIVE"}</div>
              </div>
            </Popup>
          </GeoJSON>
        ))}

        {/* Point Markers (Facilities, Samples, Activities, Assets) */}
        {visibleMarkers.map(m => (
          <React.Fragment key={m.id}>
            <CircleMarker
              center={[m.lat, m.lng]}
              radius={7}
              pathOptions={{
                color: m.color,
                fillColor: m.color,
                fillOpacity: 0.85,
                weight: 2,
              }}
            >
              <Popup className="custom-dark-popup">
                <div className="p-3.5 space-y-2 text-xs bg-slate-950 text-white rounded-xl shadow-2xl border border-slate-800 max-w-[280px]">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                    <span className="font-bold text-emerald-400 font-mono text-[11px] truncate">{m.name}</span>
                    <span
                      className="text-[9px] font-extrabold px-2 py-0.5 rounded uppercase font-mono shrink-0"
                      style={{ backgroundColor: `${m.color}20`, color: m.color }}
                    >
                      {m.status}
                    </span>
                  </div>

                  <div className="space-y-1 text-[10px] text-slate-300 font-mono leading-relaxed">
                    <div><strong className="text-slate-400">Layer:</strong> {m.type}</div>
                    {m.subtitle && <div><strong className="text-slate-400">Detail:</strong> {m.subtitle}</div>}
                    <div><strong className="text-slate-400">Coordinates:</strong> {m.lat.toFixed(6)}, {m.lng.toFixed(6)}</div>
                  </div>

                  {onSelectEntity && (
                    <button
                      type="button"
                      onClick={() => onSelectEntity(m)}
                      className="w-full mt-2 py-1 px-2 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 text-[10px] font-bold transition-all text-center"
                    >
                      Inspect Evidence Dossier
                    </button>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          </React.Fragment>
        ))}
      </MapContainer>

      {/* ─── Empty State Overlay (when 0 features registered) ─── */}
      {!loading && !hasAnyFeatures && (
        <div
          data-testid="map-empty-state"
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[500] max-w-sm w-full mx-auto px-4 pointer-events-none"
        >
          <div className="p-4 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/60 shadow-lg text-center space-y-1.5 pointer-events-auto">
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[var(--color-primary)] flex items-center justify-center mx-auto">
              <Info size={16} />
            </div>
            <h3 className="text-xs font-semibold text-slate-200">
              {sectorConfig.emptyTitle}
            </h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {sectorConfig.emptySubtitle}
            </p>
          </div>
        </div>
      )}

      {/* ─── Earth Observation Scene Provenance Panel ─── */}
      {isEoActive && (
        <div className="absolute bottom-3 left-3 z-[600] max-w-sm w-full">
          {eoObservations.length > 0 ? (
            <div className="p-3 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 shadow-2xl text-xs space-y-2 text-slate-200">
              <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                <div className="flex items-center gap-1.5 text-[var(--color-primary)] font-semibold text-[11px]">
                  <Satellite size={14} />
                  <span>EO Provenance: {selectedEoScene?.provider || "Sentinel-2"}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowEoPanel(!showEoPanel)}
                  className="text-[10px] text-slate-400 hover:text-white"
                >
                  {showEoPanel ? "Collapse" : "Expand"}
                </button>
              </div>

              {/* Date & Scene Picker */}
              <div className="flex items-center gap-2 text-[10px]">
                <Calendar size={12} className="text-slate-400 shrink-0" />
                <select
                  aria-label="Select satellite scene acquisition date"
                  value={selectedEoScene?.id || ""}
                  onChange={(e) => {
                    const found = eoObservations.find(o => o.id === e.target.value);
                    if (found) setSelectedEoScene(found);
                  }}
                  className="bg-slate-950 border border-slate-800 rounded px-2 py-0.5 text-slate-300 text-[10px] focus:ring-1 focus:ring-[var(--color-primary)] w-full"
                >
                  {eoObservations.map(obs => (
                    <option key={obs.id} value={obs.id}>
                      {new Date(obs.acquisition_timestamp).toISOString().split("T")[0]} • {obs.scene_id.substring(0, 18)}...
                    </option>
                  ))}
                </select>
              </div>

              {showEoPanel && selectedEoScene && (
                <div className="space-y-1 text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                  <div className="flex justify-between">
                    <span>Scene ID:</span>
                    <span className="text-slate-200 truncate max-w-[170px] font-mono">{selectedEoScene.scene_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Resolution:</span>
                    <span className="text-slate-200">{selectedEoScene.spatial_resolution_m}m</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Level:</span>
                    <span className="text-slate-200">{selectedEoScene.processing_level}</span>
                  </div>
                  {selectedEoScene.cloud_coverage_pct !== null && selectedEoScene.cloud_coverage_pct !== undefined && (
                    <div className="flex justify-between">
                      <span>Cloud Cover:</span>
                      <span className="text-slate-200">{selectedEoScene.cloud_coverage_pct}%</span>
                    </div>
                  )}
                  <div className="flex justify-between items-center pt-1 border-t border-slate-800">
                    <span title="Cryptographic SHA-256 digest of canonical scene metadata manifest">Manifest Digest:</span>
                    <span className="text-emerald-400 font-mono text-[9px]" title={selectedEoScene.provenance_hash}>
                      {selectedEoScene.provenance_hash.substring(0, 14)}...
                    </span>
                  </div>
                  <div className="text-[9px] text-slate-400 font-normal">
                    Algorithm: SHA-256 (Canonical Metadata Manifest)
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-2.5 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/60 text-[11px] text-slate-300 flex items-center gap-2 shadow-lg">
              <Info size={14} className="text-amber-400 shrink-0" />
              <span>No Earth Observation data available for this project / area.</span>
            </div>
          )}
        </div>
      )}

      {/* ─── Collapsible Map Legend ─── */}
      {showLegend && (
        <div className="absolute bottom-3 right-3 z-[600] p-3 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/60 shadow-md text-xs space-y-2 text-slate-300 max-w-[220px]">
          <div className="font-medium text-xs text-slate-300 border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span>Map legend</span>
            <span className="text-[11px] text-slate-400 font-normal">{sectorConfig.sectorName}</span>
          </div>
          <div className="space-y-1">
            {sectorConfig.legend.map(item => (
              <div key={item.id} className="flex items-center gap-2">
                {item.shape === "polygon" ? (
                  <span
                    className="w-3 h-2 rounded-xs border shrink-0"
                    style={{ borderColor: item.color, backgroundColor: `${item.color}40` }}
                  />
                ) : item.shape === "dashed_polygon" ? (
                  <span
                    className="w-3 h-2 rounded-xs border border-dashed shrink-0"
                    style={{ borderColor: item.color, backgroundColor: `${item.color}30` }}
                  />
                ) : (
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                )}
                <span className="truncate text-slate-300">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
