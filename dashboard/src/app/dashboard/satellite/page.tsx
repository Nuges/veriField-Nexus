// =============================================================================
// VeriField Nexus — Satellite NDVI Dashboard
// =============================================================================
// Displays vegetation monitoring data from Sentinel-2 satellite imagery.
// Allows admins to fetch NDVI scores per asset and view trends.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import {
  Satellite,
  TrendingUp,
  TrendingDown,
  Minus,
  Leaf,
  RefreshCw,
  MapPin,
  Loader2,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchProperties, fetchNdvi, fetchNdviHistory, setAuthToken } from "@/lib/api";
import type { Property } from "@/lib/types";

interface NdviData {
  asset_id: string;
  ndvi_score: number;
  trend: string;
  observation_date: string;
  source: string;
  cached?: boolean;
}

interface NdviHistoryRecord {
  ndvi_score: number;
  trend: string;
  observation_date: string;
  source: string;
}

export default function SatellitePage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [ndviData, setNdviData] = useState<NdviData | null>(null);
  const [history, setHistory] = useState<NdviHistoryRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("vf_token");
    if (token) setAuthToken(token);
    loadProperties();
  }, []);

  async function loadProperties() {
    try {
      const result = await fetchProperties();
      setProperties(result.properties || []);
    } catch (err) {
      console.error("Failed to load properties:", err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleFetchNdvi(assetId: string) {
    setSelectedAsset(assetId);
    setIsFetching(true);
    try {
      const [ndvi, hist] = await Promise.all([
        fetchNdvi(assetId),
        fetchNdviHistory(assetId),
      ]);
      setNdviData(ndvi);
      setHistory(hist.records || []);
    } catch (err) {
      console.error("Failed to fetch NDVI:", err);
    } finally {
      setIsFetching(false);
    }
  }

  const trendIcon = (trend: string) => {
    if (trend === "increasing") return <TrendingUp size={16} className="text-emerald-400" />;
    if (trend === "decreasing") return <TrendingDown size={16} className="text-red-400" />;
    return <Minus size={16} className="text-amber-400" />;
  };

  const trendColor = (trend: string) => {
    if (trend === "increasing") return "text-emerald-400";
    if (trend === "decreasing") return "text-red-400";
    return "text-amber-400";
  };

  const ndviQuality = (score: number) => {
    if (score >= 0.6) return { label: "Dense Vegetation", color: "text-emerald-400", bg: "bg-emerald-500/15" };
    if (score >= 0.4) return { label: "Moderate Vegetation", color: "text-green-400", bg: "bg-green-500/15" };
    if (score >= 0.2) return { label: "Sparse Vegetation", color: "text-amber-400", bg: "bg-amber-500/15" };
    return { label: "Bare/Urban", color: "text-red-400", bg: "bg-red-500/15" };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Only show assets with GPS
  const gpsAssets = properties.filter((p) => p.latitude && p.longitude);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
          Satellite NDVI Monitoring
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Track vegetation health using Sentinel-2 satellite imagery across all registered assets
        </p>
      </div>

      {/* Current NDVI Display */}
      {ndviData && (
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-green-600/20 flex items-center justify-center">
                <Satellite size={28} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-[var(--color-text-muted)] text-xs">Current NDVI Score</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-4xl font-black text-[var(--color-text-primary)]">
                    {ndviData.ndvi_score.toFixed(2)}
                  </span>
                  <div className="flex items-center gap-1">
                    {trendIcon(ndviData.trend)}
                    <span className={`text-sm font-medium capitalize ${trendColor(ndviData.trend)}`}>
                      {ndviData.trend}
                    </span>
                  </div>
                </div>
                <p className="text-[var(--color-text-muted)] text-xs mt-1">
                  {ndviData.observation_date} • {ndviData.source}
                  {ndviData.cached && " • Cached"}
                </p>
              </div>
            </div>

            {/* NDVI Quality Badge */}
            {(() => {
              const q = ndviQuality(ndviData.ndvi_score);
              return (
                <div className={`px-4 py-2 rounded-xl ${q.bg}`}>
                  <div className="flex items-center gap-2">
                    <Leaf size={16} className={q.color} />
                    <span className={`font-semibold text-sm ${q.color}`}>{q.label}</span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* NDVI Scale Bar */}
          <div className="mt-5">
            <div className="relative h-3 rounded-full overflow-hidden bg-gradient-to-r from-red-500 via-amber-400 via-green-400 to-emerald-600">
              <div
                className="absolute top-0 w-1 h-full bg-white rounded-full shadow-lg shadow-white/50 transition-all duration-500"
                style={{ left: `${Math.max(0, Math.min(100, ndviData.ndvi_score * 100))}%` }}
              />
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-[var(--color-text-muted)]">
              <span>0.0 Bare</span>
              <span>0.2</span>
              <span>0.4</span>
              <span>0.6</span>
              <span>0.8+ Dense</span>
            </div>
          </div>
        </div>
      )}

      {/* NDVI History Chart */}
      {history.length > 0 && (
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
          <h3 className="text-[var(--color-text-primary)] font-semibold mb-4">
            NDVI Trend History
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={[...history].reverse()}>
              <defs>
                <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="observation_date"
                tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "12px",
                  color: "var(--color-text-primary)",
                  fontSize: "13px",
                }}
                formatter={(val: any) => [Number(val).toFixed(2), "NDVI"]}
              />
              <Line
                type="monotone"
                dataKey="ndvi_score"
                stroke="#10B981"
                strokeWidth={2.5}
                dot={{ fill: "#10B981", strokeWidth: 0, r: 4 }}
                activeDot={{ r: 6, fill: "#10B981" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Asset List */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up">
        <div className="p-5 border-b border-[var(--color-border)]">
          <h3 className="text-[var(--color-text-primary)] font-semibold">
            Assets with GPS Coordinates
          </h3>
          <p className="text-[var(--color-text-muted)] text-xs mt-1">
            Select an asset to fetch its NDVI score from Sentinel-2 data
          </p>
        </div>

        {gpsAssets.length === 0 ? (
          <div className="p-12 text-center">
            <MapPin className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
            <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No GPS-enabled assets</h3>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Assets need GPS coordinates to fetch satellite NDVI data.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {gpsAssets.map((asset) => (
              <div
                key={asset.id}
                className={`flex items-center justify-between p-4 hover:bg-[var(--color-surface)] transition-colors ${
                  selectedAsset === asset.id ? "bg-emerald-500/5" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                    <MapPin size={18} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-[var(--color-text-primary)] font-medium text-sm">
                      {asset.name}
                    </p>
                    <p className="text-[var(--color-text-muted)] text-xs">
                      {asset.property_type} •{" "}
                      {asset.latitude?.toFixed(4)}, {asset.longitude?.toFixed(4)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleFetchNdvi(asset.id)}
                  disabled={isFetching && selectedAsset === asset.id}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-500/10 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-all disabled:opacity-50"
                >
                  {isFetching && selectedAsset === asset.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <RefreshCw size={14} />
                  )}
                  Fetch NDVI
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
        <h3 className="text-[var(--color-text-primary)] font-semibold mb-2">
          About NDVI
        </h3>
        <p className="text-[var(--color-text-secondary)] text-sm leading-relaxed">
          NDVI (Normalized Difference Vegetation Index) measures vegetation health from satellite
          imagery. Values range from -1 to 1, where higher values indicate denser, healthier
          vegetation. Data is sourced from Sentinel-2 satellites via the Copernicus Data Space
          Ecosystem. Scores are computed monthly and cached for efficiency. In Nigerian agriculture
          and agroforestry projects, NDVI trends help validate carbon sequestration claims.
        </p>
        <div className="grid grid-cols-4 gap-3 mt-4">
          <div className="text-center p-2 rounded-lg bg-red-500/10">
            <p className="text-red-400 font-bold text-sm">&lt; 0.2</p>
            <p className="text-[var(--color-text-muted)] text-[10px]">Bare/Urban</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-amber-500/10">
            <p className="text-amber-400 font-bold text-sm">0.2–0.4</p>
            <p className="text-[var(--color-text-muted)] text-[10px]">Sparse</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-green-500/10">
            <p className="text-green-400 font-bold text-sm">0.4–0.6</p>
            <p className="text-[var(--color-text-muted)] text-[10px]">Moderate</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-emerald-500/10">
            <p className="text-emerald-400 font-bold text-sm">&gt; 0.6</p>
            <p className="text-[var(--color-text-muted)] text-[10px]">Dense</p>
          </div>
        </div>
      </div>
    </div>
  );
}
