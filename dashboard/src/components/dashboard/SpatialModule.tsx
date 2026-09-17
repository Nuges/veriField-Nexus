// =============================================================================

// VeriField Nexus — Spatial Module (with Real Interactive Map)

// =============================================================================

// Sector-aware geospatial view combining an interactive Leaflet map with an

// asset data table. Replaces the previous static table-only view.

// Uses dynamic import to avoid SSR issues with Leaflet.

// =============================================================================



"use client";



import React, { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { MapPin, List, Map as MapIcon } from "lucide-react";
import { canonicalSectorCode } from "@/lib/moduleRegistry";



// Dynamic import of LeafletMap (client-only — Leaflet can't run on server)

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

}: {

  sectorCode?: string;

  assets?: SpatialAsset[];

}) {

  const [viewMode, setViewMode] = useState<"map" | "table">("map");

  const [statusFilter, setStatusFilter] = useState<string>("all");

  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);



  const canonCode = canonicalSectorCode(sectorCode || "").toUpperCase();

  const assetLabel = canonCode === "COOKSTOVES"
    ? "cookstoves"
    : canonCode === "HYBRID_ENERGY"
    ? "hybrid energy systems"
    : canonCode === "BIOCHAR"
    ? "biochar facilities"
    : canonCode === "EV_MOBILITY"
    ? "charging stations"
    : canonCode === "AGRICULTURE_LAND_USE"
    ? "land units"
    : "assets";

  const isAgriculture = canonCode === "AGRICULTURE_LAND_USE";
  const emptyTitle = isAgriculture ? "No land boundaries registered." : `No ${assetLabel} registered.`;
  const emptySubtitle = isAgriculture
    ? "Add or capture a land unit to establish the project map."
    : canonCode === "COOKSTOVES"
    ? "Add or capture a device to establish the project map."
    : canonCode === "BIOCHAR"
    ? "Add or capture a facility to establish the project map."
    : canonCode === "EV_MOBILITY"
    ? "Add or capture a charging station to establish the project map."
    : canonCode === "HYBRID_ENERGY"
    ? "Add or capture an energy system to establish the project map."
    : "Add or capture an asset to establish the project map.";



  // Normalize assets for the map

  const normalizedAssets = useMemo(() => {

    const raw = assets && assets.length > 0 ? assets : [];

    return raw.map((a) => normalizeAsset(a, sectorCode));

  }, [assets, sectorCode]);



  // Filter by status

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



  return (

    <div className="space-y-4">

      {/* Controls Bar */}

      <div className="flex flex-wrap items-center justify-between gap-3">

        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Spatial view — {assetLabel}
          </h3>
          <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border border-[var(--color-border)]">
            {filteredAssets.length} {assetLabel}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Status filter */}
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
          </div>

        </div>

      </div>



      {/* Map View */}

      {viewMode === "map" && (

        <div className="relative isolate rounded-xl overflow-hidden">

          <LeafletMap
            assets={filteredAssets}
            sectorCode={sectorCode}
            height="500px"
            showRadius={true}
            radiusMeters={50}
            hideEmptyState={true}
            onAssetClick={(a) => setSelectedAsset(a.id)}
          />

          {filteredAssets.length === 0 && (
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

    </div>

  );

}
