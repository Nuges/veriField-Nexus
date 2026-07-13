"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix leaflet icon issues in nextjs
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
});

const MapFitter = ({ geojson }: { geojson: any }) => {
  const map = useMap();
  useEffect(() => {
    if (geojson && Object.keys(geojson).length > 0) {
      try {
        const layer = L.geoJSON(geojson);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [20, 20] });
        }
      } catch (e) {
        console.error("Invalid GeoJSON for bounds calculation:", e);
      }
    }
  }, [geojson, map]);
  return null;
};

export default function SpatialBoundaryMap({ data }: { data: any }) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return <div className="h-full w-full bg-slate-100 dark:bg-slate-800 animate-pulse rounded-lg" />;

  const hasData = data && Object.keys(data).length > 0;
  
  return (
    <div className="h-full w-full relative z-0 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
      <MapContainer 
        center={[0, 0]} 
        zoom={2} 
        style={{ height: "100%", width: "100%" }}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="map-tiles"
        />
        {hasData && (
          <>
            <GeoJSON 
              data={data} 
              style={{
                fillColor: "#3b82f6",
                weight: 2,
                opacity: 1,
                color: "#2563eb",
                fillOpacity: 0.2
              }}
            />
            <MapFitter geojson={data} />
          </>
        )}
      </MapContainer>
    </div>
  );
}
