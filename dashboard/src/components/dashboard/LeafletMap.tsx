// =============================================================================

// VeriField Nexus — Leaflet Map Component (Client-Only)

// =============================================================================

// Interactive map using Leaflet + OpenStreetMap. Renders asset pins with

// sector-specific colors, trust score indicators, verification radius circles,

// and clustering for dense areas. Must be loaded with dynamic import (ssr: false).

// =============================================================================



"use client";



import React, { useEffect, useRef, useState } from "react";

import L from "leaflet";

import "leaflet/dist/leaflet.css";



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

  onAssetClick,

}: LeafletMapProps) {

  const mapRef = useRef<HTMLDivElement>(null);

  const mapInstanceRef = useRef<L.Map | null>(null);

  const markersRef = useRef<L.LayerGroup | null>(null);



  useEffect(() => {

    if (!mapRef.current || mapInstanceRef.current) return;



    // Determine center from assets

    const validAssets = assets.filter((a) => a.lat && a.lng && !isNaN(a.lat) && !isNaN(a.lng));

    const center: [number, number] =

      validAssets.length > 0 ? [validAssets[0].lat, validAssets[0].lng] : DEFAULT_CENTER;



    const map = L.map(mapRef.current, {

      center,

      zoom: DEFAULT_ZOOM,

      zoomControl: true,

      attributionControl: true,

    });



    // Dark-themed tile layer

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {

      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',

      subdomains: "abcd",

      maxZoom: 19,

    }).addTo(map);



    mapInstanceRef.current = map;

    markersRef.current = L.layerGroup().addTo(map);



    // Fix Leaflet icon path issue in bundlers

    // @ts-ignore

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



  // Update markers when assets change

  useEffect(() => {

    if (!markersRef.current || !mapInstanceRef.current) return;



    markersRef.current.clearLayers();

    const validAssets = assets.filter((a) => a.lat && a.lng && !isNaN(a.lat) && !isNaN(a.lng));



    if (validAssets.length === 0) return;



    const bounds = L.latLngBounds([]);



    validAssets.forEach((asset) => {

      const color = getSectorColor(asset.sector || sectorCode);

      const icon = createMarkerIcon(color, asset.trust);

      const marker = L.marker([asset.lat, asset.lng], { icon });



      // Popup

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

      bounds.extend([asset.lat, asset.lng]);



      // Verification radius circle

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



    // Fit bounds with padding

    if (bounds.isValid()) {

      mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });

    }

  }, [assets, sectorCode, showRadius, radiusMeters, onAssetClick]);



  return (

    <div className="relative rounded-xl overflow-hidden border border-[var(--color-border)]">

      <div ref={mapRef} style={{ height, width: "100%" }} />

      {assets.filter((a) => a.lat && a.lng).length === 0 && (

        <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-background)]/80 backdrop-blur-sm">

          <div className="text-center p-6">

            <div className="text-4xl mb-2">🗺️</div>

            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">No Geospatial Data</h3>

            <p className="text-xs text-[var(--color-text-secondary)] mt-1">

              Assets with GPS coordinates will appear on this map.

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
