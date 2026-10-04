// =============================================================================

// VeriField Nexus — Leaflet Map Component (Client-Only)

// =============================================================================

// Interactive map using Leaflet + OpenStreetMap. Renders asset pins with

// sector-specific colors, trust score indicators, verification radius circles,

// and clustering for dense areas. Must be loaded with dynamic import (ssr: false).

// =============================================================================



"use client";



import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { classifyDisplayProvenance } from "@/components/spatial/provenance";



interface MapAsset {

  id: string;

  name: string;

  lat: number;

  lng: number;

  trust?: number;

  status?: string;

  sector?: string;

  radiusCheck?: string;

}



interface LeafletMapProps {

  assets: MapAsset[];

  sectorCode?: string;

  height?: string;

  showRadius?: boolean;

  radiusMeters?: number;

  hideEmptyState?: boolean;
  boundaryGeoJson?: any;
  observationFootprintGeoJson?: any;
  observationMetadata?: any;
  rasterLayerUrl?: string;
  rasterLayerTitle?: string;
  rasterLayerType?: string;
  derivedRasterUrl?: string;
  derivedRasterTitle?: string;
  onAssetClick?: (asset: MapAsset) => void;
}



const SECTOR_COLORS: Record<string, string> = {

  cookstove: "#F59E0B",

  clean_cooking: "#F59E0B",

  ams_ii_g: "#F59E0B",

  hybrid_energy: "#3B82F6",

  energy: "#3B82F6",

  ams_i_f: "#3B82F6",

  biochar: "#8B5CF6",

  ev: "#10B981",
  ev_mobility: "#10B981",
  agriculture_land_use: "#00B47A",
  agriculture: "#00B47A",
  afolu: "#00B47A",
};



const DEFAULT_CENTER: [number, number] = [6.5244, 3.3792]; // Lagos

const DEFAULT_ZOOM = 12;



function getSectorColor(sector?: string): string {

  if (!sector) return "#00B47A";

  const key = sector.toLowerCase().replace(/[\s-]/g, "_");

  return SECTOR_COLORS[key] || "#00B47A";

}



function createMarkerIcon(color: string, trust?: number): L.DivIcon {

  const opacity = trust !== undefined ? Math.max(0.5, trust / 100) : 1;

  const size = trust !== undefined && trust < 70 ? 14 : 10;

  const border = trust !== undefined && trust < 70 ? "2px solid #EF4444" : "2px solid rgba(255,255,255,0.8)";

  return L.divIcon({

    className: "vf-marker",

    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};opacity:${opacity};border:${border};box-shadow:0 0 6px ${color}80;"></div>`,

    iconSize: [size, size],

    iconAnchor: [size / 2, size / 2],

  });

}



export default function LeafletMap({

  assets,

  sectorCode,

  height = "500px",

  showRadius = true,

  radiusMeters = 50,

  hideEmptyState = false,
  boundaryGeoJson,
  observationFootprintGeoJson,
  observationMetadata,
  rasterLayerUrl,
  rasterLayerTitle,
  derivedRasterUrl,
  derivedRasterTitle,
  onAssetClick,
}: LeafletMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const polygonsRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const rasterLayerRef = useRef<L.Layer | null>(null);
  const derivedLayerRef = useRef<L.Layer | null>(null);
  const [basemap, setBasemap] = React.useState<"canvas" | "satellite">("canvas");
  const [showEoRaster, setShowEoRaster] = React.useState<boolean>(true);
  const [eoRasterOpacity, setEoRasterOpacity] = React.useState<number>(0.85);
  const [showDerivedRaster, setShowDerivedRaster] = React.useState<boolean>(false);
  const [derivedRasterOpacity, setDerivedRasterOpacity] = React.useState<number>(0.8);
  const [rasterDimensions, setRasterDimensions] = React.useState<{ width: number; height: number } | null>(null);
  const [prevRasterUrl, setPrevRasterUrl] = React.useState<string | undefined>(rasterLayerUrl);
  const [showInspector, setShowInspector] = React.useState<boolean>(false);

  if (prevRasterUrl !== rasterLayerUrl) {
    setPrevRasterUrl(rasterLayerUrl);
    setRasterDimensions(null);
  }

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Determine center from assets or default
    const validAssets = assets.filter((a) => a.lat && a.lng && !isNaN(a.lat) && !isNaN(a.lng));
    const center: [number, number] =
      validAssets.length > 0 ? [validAssets[0].lat, validAssets[0].lng] : DEFAULT_CENTER;

    const map = L.map(mapRef.current, {
      center,
      zoom: DEFAULT_ZOOM,
      zoomControl: true,
      attributionControl: true,
    });

    const canvasUrl = process.env.NEXT_PUBLIC_MAP_TILE_URL || "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
    const tileAttribution = '&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

    const tile = L.tileLayer(canvasUrl, {
      attribution: tileAttribution,
      maxZoom: 19,
    }).addTo(map);

    tileLayerRef.current = tile;
    mapInstanceRef.current = map;
    markersRef.current = L.layerGroup().addTo(map);
    polygonsRef.current = L.layerGroup().addTo(map);



    // Fix Leaflet icon path issue in bundlers

    // @ts-expect-error Leaflet prototype override
    delete L.Icon.Default.prototype._getIconUrl;

    L.Icon.Default.mergeOptions({

      iconRetinaUrl: "",

      iconUrl: "",

      shadowUrl: "",

    });



    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  // Switch basemap tile layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (tileLayerRef.current) {
      mapInstanceRef.current.removeLayer(tileLayerRef.current);
    }
    const tileUrl =
      basemap === "satellite"
        ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        : process.env.NEXT_PUBLIC_MAP_TILE_URL ||
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
    const tileAttribution =
      basemap === "satellite"
        ? '&copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics'
        : '&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

    const tile = L.tileLayer(tileUrl, {
      attribution: tileAttribution,
      maxZoom: 19,
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current = tile;
  }, [basemap]);

  // Render / Update Actual EO Raster Layer (COG XYZ Tiles or Georeferenced Scene Image Overlay)
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (rasterLayerRef.current) {
      mapInstanceRef.current.removeLayer(rasterLayerRef.current);
      rasterLayerRef.current = null;
      if (mapRef.current) {
        mapRef.current.removeAttribute("data-eo-raster-active");
      }
    }

    if (!showEoRaster || !rasterLayerUrl) return;

    if (rasterLayerUrl.includes("{z}") && rasterLayerUrl.includes("{x}") && rasterLayerUrl.includes("{y}")) {
      const tile = L.tileLayer(rasterLayerUrl, {
        opacity: eoRasterOpacity,
        maxZoom: 19,
        attribution: "EO Satellite Raster",
      }).addTo(mapInstanceRef.current);
      rasterLayerRef.current = tile;
      if (mapRef.current) {
        mapRef.current.setAttribute("data-eo-raster-active", "true");
      }
    } else if (observationFootprintGeoJson) {
      try {
        const tempGeo = L.geoJSON(observationFootprintGeoJson);
        const b = tempGeo.getBounds();
        if (b.isValid()) {
          const overlay = L.imageOverlay(rasterLayerUrl, b, {
            opacity: eoRasterOpacity,
            interactive: true,
            className: "vf-eo-raster-overlay",
          }).addTo(mapInstanceRef.current);
          overlay.on("load", () => {
            const el = overlay.getElement();
            if (el) {
              el.setAttribute("data-raster-loaded", "true");
              el.setAttribute("data-natural-width", String(el.naturalWidth || 0));
              el.setAttribute("data-natural-height", String(el.naturalHeight || 0));
              if (el.naturalWidth && el.naturalHeight) {
                setRasterDimensions({ width: el.naturalWidth, height: el.naturalHeight });
              }
            }
            if (mapRef.current) {
              mapRef.current.setAttribute("data-eo-raster-active", "true");
            }
          });
          overlay.on("error", (e) => {
            console.warn("EO raster image failed to load:", e);
            if (mapRef.current) {
              mapRef.current.setAttribute("data-eo-raster-error", "true");
            }
          });
          rasterLayerRef.current = overlay;
        }
      } catch (err) {
        console.warn("Failed to overlay raster image:", err);
      }
    }
  }, [rasterLayerUrl, showEoRaster, eoRasterOpacity, observationFootprintGeoJson]);

  // Render / Update Derived Index Raster Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (derivedLayerRef.current) {
      mapInstanceRef.current.removeLayer(derivedLayerRef.current);
      derivedLayerRef.current = null;
    }

    if (!showDerivedRaster || !derivedRasterUrl) return;

    if (derivedRasterUrl.includes("{z}") && derivedRasterUrl.includes("{x}") && derivedRasterUrl.includes("{y}")) {
      const tile = L.tileLayer(derivedRasterUrl, {
        opacity: derivedRasterOpacity,
        maxZoom: 19,
        attribution: "Derived Index Raster",
      }).addTo(mapInstanceRef.current);
      derivedLayerRef.current = tile;
    } else if (boundaryGeoJson || observationFootprintGeoJson) {
      try {
        const tempGeo = L.geoJSON(observationFootprintGeoJson || boundaryGeoJson);
        const b = tempGeo.getBounds();
        if (b.isValid()) {
          const overlay = L.imageOverlay(derivedRasterUrl, b, {
            opacity: derivedRasterOpacity,
            interactive: true,
          }).addTo(mapInstanceRef.current);
          derivedLayerRef.current = overlay;
        }
      } catch (err) {
        console.warn("Failed to overlay derived raster image:", err);
      }
    }
  }, [derivedRasterUrl, showDerivedRaster, derivedRasterOpacity, boundaryGeoJson, observationFootprintGeoJson]);

  // Update markers and boundary polygons when assets or boundaryGeoJson change
  useEffect(() => {
    if (!markersRef.current || !polygonsRef.current || !mapInstanceRef.current) return;

    markersRef.current.clearLayers();
    polygonsRef.current.clearLayers();

    const aoiBounds = L.latLngBounds([]);
    const fullBounds = L.latLngBounds([]);

    // 1. Render Boundary GeoJSON if present
    if (boundaryGeoJson) {
      try {
        const geoLayer = L.geoJSON(boundaryGeoJson, {
          style: {
            color: "#00B47A",
            weight: 2.5,
            fillColor: "#00B47A",
            fillOpacity: 0.12,
            dashArray: "4 4",
          },
          onEachFeature: (_feature, layer) => {
            layer.bindPopup(
              `<div style="font-family:system-ui;font-size:12px;">
                <div style="font-weight:700;color:#00B47A;margin-bottom:2px;">Project Boundary</div>
                <div style="color:#aaa;font-size:11px;">Authoritative Area of Interest (WGS84)</div>
              </div>`,
              { className: "vf-popup" }
            );
          },
        });
        geoLayer.addTo(polygonsRef.current);
        const geoBounds = geoLayer.getBounds();
        if (geoBounds.isValid()) {
          aoiBounds.extend(geoBounds);
          fullBounds.extend(geoBounds);
        }
      } catch (err) {
        console.error("Failed to render boundary GeoJSON:", err);
      }
    }

    // 2. Render Satellite Observation Footprint if present (Distinct Electric Blue Layer)
    if (observationFootprintGeoJson) {
      try {
        const obsLayer = L.geoJSON(observationFootprintGeoJson, {
          style: {
            color: "#3B82F6",
            weight: 2,
            fillColor: "#3B82F6",
            fillOpacity: 0.16,
            dashArray: "6 3",
          },
          onEachFeature: (_feature, layer) => {
            const m = observationMetadata || {};
            layer.bindPopup(
              `<div style="font-family:system-ui;font-size:12px;min-width:210px;">
                <div style="font-weight:700;color:#3B82F6;margin-bottom:3px;display:flex;align-items:center;gap:4px;">
                  <span>Satellite Scene Footprint</span>
                </div>
                <div style="color:#eee;font-weight:600;font-size:11px;font-family:monospace;word-break:break-all;">
                  ${m.scene_id || "Scene"}
                </div>
                <div style="display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:11px;margin-top:6px;border-top:1px solid #334155;padding-top:4px;">
                  <span style="color:#94a3b8;">Platform:</span> <span style="font-weight:600;color:#f8fafc;">${m.platform || "Unknown"} (${m.sensor || ""})</span>
                  <span style="color:#94a3b8;">Acquired:</span> <span style="color:#f8fafc;">${m.acquisition_timestamp ? new Date(m.acquisition_timestamp).toLocaleDateString() : "N/A"}</span>
                  <span style="color:#94a3b8;">Cloud QA:</span> <span style="color:${(m.cloud_cover_pct ?? 0) > 20 ? "#f59e0b" : "#10b981"};font-weight:600;">${m.cloud_cover_pct !== undefined && m.cloud_cover_pct !== null ? `${m.cloud_cover_pct.toFixed(1)}%` : "0%"} (${m.quality_status || "USABLE"})</span>
                  <span style="color:#94a3b8;">Resolution:</span> <span style="color:#f8fafc;">${m.spatial_resolution_m || 10}m</span>
                </div>
              </div>`,
              { className: "vf-popup" }
            );
          },
        });
        obsLayer.addTo(polygonsRef.current);
        const obsBounds = obsLayer.getBounds();
        if (obsBounds.isValid()) {
          fullBounds.extend(obsBounds);
        }
      } catch (err) {
        console.error("Failed to render observation footprint GeoJSON:", err);
      }
    }

    // 3. Render Asset Pins
    const validAssets = assets.filter((a) => a.lat && a.lng && !isNaN(a.lat) && !isNaN(a.lng));

    validAssets.forEach((asset) => {
      const color = getSectorColor(asset.sector || sectorCode);
      const icon = createMarkerIcon(color, asset.trust);
      const marker = L.marker([asset.lat, asset.lng], { icon });

      const trustBadge =
        asset.trust !== undefined
          ? `<span style="color:${asset.trust >= 80 ? "#10B981" : asset.trust >= 50 ? "#F59E0B" : "#EF4444"};font-weight:bold;">${asset.trust}%</span>`
          : "N/A";
      const statusBadge = asset.status || "Unknown";

      marker.bindPopup(
        `<div style="font-family:system-ui;font-size:12px;min-width:180px;">
          <div style="font-weight:700;font-size:13px;margin-bottom:4px;">${asset.name}</div>
          <div style="display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:11px;">
            <span style="color:#999;">Trust:</span> ${trustBadge}
            <span style="color:#999;">Status:</span> <span style="font-weight:600;">${statusBadge}</span>
            <span style="color:#999;">Lat:</span> <span>${asset.lat.toFixed(4)}</span>
            <span style="color:#999;">Lng:</span> <span>${asset.lng.toFixed(4)}</span>
          </div>
        </div>`,
        { className: "vf-popup" }
      );

      if (onAssetClick) {
        marker.on("click", () => onAssetClick(asset));
      }

      marker.addTo(markersRef.current!);
      aoiBounds.extend([asset.lat, asset.lng]);
      fullBounds.extend([asset.lat, asset.lng]);

      if (showRadius && asset.trust !== undefined) {
        const circle = L.circle([asset.lat, asset.lng], {
          radius: radiusMeters,
          color: color,
          fillColor: color,
          fillOpacity: 0.08,
          weight: 1,
          dashArray: "4 4",
        });
        circle.addTo(markersRef.current!);
      }
    });

    const targetBounds = aoiBounds.isValid() ? aoiBounds : fullBounds;
    if (targetBounds.isValid() && mapInstanceRef.current) {
      try {
        mapInstanceRef.current.fitBounds(targetBounds, { padding: [40, 40], maxZoom: 15, animate: false });
      } catch {
        // Safe against async unmount races
      }
    }
  }, [assets, boundaryGeoJson, observationFootprintGeoJson, observationMetadata, sectorCode, showRadius, radiusMeters, onAssetClick]);

  const hasData = assets.some((a) => a.lat && a.lng) || Boolean(boundaryGeoJson) || Boolean(observationFootprintGeoJson);

  const obs = observationMetadata || {};
  const prov = classifyDisplayProvenance(obs, rasterDimensions);

  const isS2 = obs.platform?.includes("Sentinel-2") || obs.provider_code === "SENTINEL_2";
  const isLandsat = obs.platform?.includes("Landsat") || obs.provider_code === "LANDSAT";
  const isS1 = obs.platform?.includes("Sentinel-1") || obs.observation_type === "SAR_C_BAND_BACKSCATTER";

  const eoLayerName = isS2
    ? `Sentinel-2 Optical Preview (${obs.spatial_resolution_m || 10}m)`
    : isLandsat
    ? `${obs.platform || "Landsat"} Optical Preview (${obs.spatial_resolution_m || 30}m)`
    : isS1
    ? `Sentinel-1 Dual-Pol SAR Quicklook (${obs.spatial_resolution_m || 10}m)`
    : (rasterLayerTitle || "Earth Observation Layer");

  const eoAcquiredDate = obs.acquisition_timestamp
    ? new Date(obs.acquisition_timestamp).toISOString().split("T")[0]
    : undefined;

  const eoCloudCover = obs.cloud_cover_pct !== undefined && obs.cloud_cover_pct !== null
    ? `${Number(obs.cloud_cover_pct).toFixed(1)}%`
    : (isS1 ? "N/A (Radar)" : "0.0%");

  return (
    <div className="relative rounded-xl overflow-hidden border border-[var(--color-border)]">
      {/* Remote Sensing Map Controls */}
      <div className="absolute top-3 right-3 z-[1050] flex flex-col items-end gap-1.5 pointer-events-auto max-w-[280px]">
        {/* Layer 1 & 2: Basemap Switcher */}
        <div className="flex items-center bg-[var(--color-surface)]/95 backdrop-blur-md border border-[var(--color-border)] rounded-lg p-0.5 shadow-sm text-xs">
          <button
            type="button"
            data-basemap="map"
            onClick={() => setBasemap("canvas")}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              basemap === "canvas"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            Map
          </button>
          <button
            type="button"
            data-basemap="satellite"
            onClick={() => setBasemap("satellite")}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              basemap === "satellite"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            Satellite
          </button>
        </div>
        {basemap === "satellite" && (
          <div className="px-2 py-0.5 rounded text-[10px] bg-black/75 text-zinc-300 border border-zinc-700 backdrop-blur-xs text-right">
            Geographic context only
          </div>
        )}

        {/* Layer 4: Actual EO Raster Layer Control */}
        {rasterLayerUrl && (
          <div className="w-full bg-[var(--color-surface)]/95 backdrop-blur-md border border-blue-500/30 rounded-lg p-2.5 shadow-sm text-xs text-[var(--color-text-primary)] space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-blue-400 text-xs truncate" title={eoLayerName}>
                {eoLayerName}
              </span>
              <button
                type="button"
                onClick={() => setShowEoRaster(!showEoRaster)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide transition-colors shrink-0 ${
                  showEoRaster
                    ? "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                    : "bg-gray-500/20 text-gray-400 border border-gray-500/30"
                }`}
              >
                {showEoRaster ? "VISIBLE" : "HIDDEN"}
              </button>
            </div>

            {eoAcquiredDate && (
              <div className="text-[11px] text-[var(--color-text-secondary)]">
                Acquired: {eoAcquiredDate}
              </div>
            )}

            {showEoRaster && (
              <div className="flex items-center gap-2 pt-0.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-medium">Opacity:</span>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={eoRasterOpacity}
                  onChange={(e) => setEoRasterOpacity(parseFloat(e.target.value))}
                  className="w-full h-1 bg-[var(--color-surface-hover)] rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <span className="text-[10px] font-mono text-[var(--color-text-secondary)] w-8 text-right">
                  {Math.round(eoRasterOpacity * 100)}%
                </span>
              </div>
            )}

            {/* Secondary Technical Metadata */}
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1.5 border-t border-[var(--color-border)]/50 text-[10px] text-[var(--color-text-muted)]">
              <div>Source: <span className="text-[var(--color-text-secondary)] font-mono">{prov.sourceLabel}</span></div>
              <div>Sensor Res: <span className="text-[var(--color-text-secondary)] font-mono">{prov.sensorResolution}</span></div>
              <div>Preview Res: <span className="text-[var(--color-text-secondary)] font-mono">{prov.previewDimensions}</span></div>
              <div>Cloud Cover: <span className="text-[var(--color-text-secondary)] font-mono">{eoCloudCover}</span></div>
              <div>CRS: <span className="text-[var(--color-text-secondary)] font-mono">EPSG:4326</span></div>
              {prov.channels ? (
                <div className="col-span-2">Channels: <span className="text-[var(--color-text-secondary)] font-mono">{prov.channels}</span></div>
              ) : prov.bandRecipe ? (
                <div className="col-span-2">Band Recipe: <span className="text-[var(--color-text-secondary)] font-mono">{prov.bandRecipe}</span></div>
              ) : isLandsat ? (
                <div className="col-span-2">Product: <span className="text-[var(--color-text-secondary)] font-mono">Landsat C2 L2 Baseline</span></div>
              ) : (
                <div className="col-span-2">Display: <span className="text-[var(--color-text-secondary)] font-mono">{prov.displayDescription}</span></div>
              )}
            </div>

            {prov.disclaimer && (
              <div className="p-1.5 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] text-amber-300 leading-tight">
                {prov.disclaimer}
              </div>
            )}

            {/* Technical Lineage Drawer Toggle */}
            <div className="pt-1 border-t border-[var(--color-border)]/30 flex items-center justify-between text-[10px]">
              <button
                type="button"
                onClick={() => setShowInspector(!showInspector)}
                className="text-blue-400 hover:text-blue-300 font-medium underline flex items-center gap-1 cursor-pointer"
              >
                {showInspector ? "Hide Technical Lineage" : "View Technical Lineage"}
              </button>
              {obs.scene_id && (
                <span className="font-mono text-[9px] text-[var(--color-text-muted)] truncate max-w-[120px]" title={obs.scene_id}>
                  {obs.scene_id}
                </span>
              )}
            </div>

            {/* Expanded Inspector Drawer */}
            {showInspector && (
              <div className="p-2 rounded bg-black/60 border border-blue-500/20 text-[9px] font-mono space-y-1 text-zinc-300">
                <div>Provider: <span className="text-white">{prov.providerName}</span></div>
                <div>Scene: <span className="text-white break-all">{obs.scene_id || "N/A"}</span></div>
                <div>Asset Key: <span className="text-white">{prov.assetKey}</span></div>
                <div>Sensor Res: <span className="text-white">{prov.sensorResolution}</span></div>
                <div>Preview Dim: <span className="text-white">{prov.previewDimensions}</span></div>
                <div>Acquisition: <span className="text-white">{obs.acquisition_timestamp ? new Date(obs.acquisition_timestamp).toISOString() : "N/A"}</span></div>
                <div>Cloud QA: <span className="text-white">{eoCloudCover}</span></div>
                <div>CRS: <span className="text-white">{prov.crs}</span></div>
                <div>Level: <span className="text-white">{prov.processingLevel}</span></div>
                <div>Quality: <span className="text-emerald-400">{obs.quality_status || "USABLE"}</span></div>
                {obs.provenance_hash ? (
                  <div>SHA-256: <span className="text-emerald-400 break-all">{obs.provenance_hash}</span></div>
                ) : (
                  <div>SHA-256: <span className="text-zinc-500">Unverified</span></div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Layer 5: Derived Index Raster Layer Control */}
        {derivedRasterUrl && (
          <div className="w-full bg-[var(--color-surface)]/95 backdrop-blur-md border border-emerald-500/30 rounded-lg p-2.5 shadow-sm text-xs text-[var(--color-text-primary)] space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-emerald-400 text-xs truncate">
                {derivedRasterTitle || "Derived Layer"}
              </span>
              <button
                type="button"
                onClick={() => setShowDerivedRaster(!showDerivedRaster)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide transition-colors shrink-0 ${
                  showDerivedRaster
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : "bg-gray-500/20 text-gray-400 border border-gray-500/30"
                }`}
              >
                {showDerivedRaster ? "VISIBLE" : "HIDDEN"}
              </button>
            </div>
            {showDerivedRaster && (
              <div className="flex items-center gap-2 pt-0.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-medium">Opacity:</span>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={derivedRasterOpacity}
                  onChange={(e) => setDerivedRasterOpacity(parseFloat(e.target.value))}
                  className="w-full h-1 bg-[var(--color-surface-hover)] rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
                <span className="text-[10px] font-mono text-[var(--color-text-secondary)] w-8 text-right">
                  {Math.round(derivedRasterOpacity * 100)}%
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <div ref={mapRef} style={{ height, width: "100%" }} />

      {!hideEmptyState && !hasData && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10" role="status">
          <div className="max-w-[380px] w-full mx-4 px-6 py-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm text-center">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">No Geospatial Data</h3>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
              Boundaries and assets with GPS coordinates will appear on this map.
            </p>
          </div>
        </div>
      )}

      <style jsx global>{`

        .vf-marker {

          background: transparent !important;

          border: none !important;

        }

        .vf-popup .leaflet-popup-content-wrapper {

          background: #1a1a2e;

          color: #e2e8f0;

          border-radius: 12px;

          border: 1px solid rgba(0, 180, 122, 0.3);

          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);

        }

        .vf-popup .leaflet-popup-tip {

          background: #1a1a2e;

          border: 1px solid rgba(0, 180, 122, 0.3);

        }

        .leaflet-control-attribution {

          background: rgba(0,0,0,0.6) !important;

          color: #666 !important;

          font-size: 9px !important;

        }

        .leaflet-control-attribution a {

          color: #888 !important;

        }

      `}</style>

    </div>

  );

}
