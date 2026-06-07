"use client";

// =============================================================================
// VeriField Nexus — Energy Displacement MRV Dashboard
// =============================================================================
// Hybrid energy portfolio view: solar/diesel/gas displacement metrics,
// activity monitoring, trust scores, and site-level telemetry inspection.
// =============================================================================

import { useEffect, useState, useCallback, useMemo, Fragment } from "react";
import {
  Zap,
  Leaf,
  RefreshCw,
  DollarSign,
  Layers,
  Sun,
  Fuel,
  Battery,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  X,
  TrendingUp,
  Shield,
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  fetchEnergyPortfolio,
  fetchEnergyActivities,
  fetchSiteTelemetry,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Status badge colour mapping
// ---------------------------------------------------------------------------
const STATUS_STYLES: Record<string, string> = {
  verified: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  review: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  flagged: "bg-red-500/10 text-red-400 border-red-500/20",
  pending: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

// Pie chart colours for energy-mix breakdown
const MIX_COLORS = ["#facc15", "#3b82f6", "#a855f7", "#00B47A"];

export default function EnergyDashboardPage() {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [portfolio, setPortfolio] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedSite, setSelectedSite] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<any[]>([]);
  const [isTelemetryLoading, setIsTelemetryLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState("all"); // 7d | 30d | all
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, dateRange]);

  // ---------------------------------------------------------------------------
  // Data loaders
  // ---------------------------------------------------------------------------
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [portfolioRes, activitiesRes] = await Promise.allSettled([
        fetchEnergyPortfolio(),
        fetchEnergyActivities({ per_page: 50 }),
      ]);
      if (portfolioRes.status === "fulfilled") setPortfolio(portfolioRes.value);
      if (activitiesRes.status === "fulfilled") {
        const val = activitiesRes.value;
        setActivities(val?.activities ?? val?.data ?? (Array.isArray(val) ? val : []));
      }
    } catch (err) {
      console.error("Energy data load error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Fetch telemetry when a site detail modal is opened
  const openSiteDetail = async (activity: any) => {
    setSelectedSite(activity);
    setTelemetry([]);
    const siteId = activity.activity_data?.site_id ?? activity.site_id ?? activity.id;
    if (!siteId) return;
    setIsTelemetryLoading(true);
    try {
      const res = await fetchSiteTelemetry(siteId);
      setTelemetry(res?.readings ?? res?.data ?? (Array.isArray(res) ? res : []));
    } catch {
      /* telemetry may not exist — gracefully degrade */
    } finally {
      setIsTelemetryLoading(false);
    }
  };

  const filteredLogs = useMemo(() => {
    // 1. Sort by date descending
    const sorted = [...telemetry].sort((a: any, b: any) => {
      const dateA = a.date || a.timestamp || "";
      const dateB = b.date || b.timestamp || "";
      return dateB.localeCompare(dateA);
    });

    // 2. Filter by range
    let rangeFiltered = sorted;
    const now = new Date();
    const isWithinDays = (dateStr: string, days: number) => {
      if (!dateStr) return false;
      const date = new Date(dateStr);
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays <= days;
    };

    if (dateRange === "7d") {
      rangeFiltered = sorted.filter(l => isWithinDays(l.date || l.timestamp, 7));
    } else if (dateRange === "30d") {
      rangeFiltered = sorted.filter(l => isWithinDays(l.date || l.timestamp, 30));
    }

    // 3. Search filter
    if (!searchQuery) return rangeFiltered;
    const query = searchQuery.toLowerCase();
    return rangeFiltered.filter(log =>
      JSON.stringify(log).toLowerCase().includes(query)
    );
  }, [telemetry, searchQuery, dateRange]);

  const totalPages = Math.ceil(filteredLogs.length / pageSize) || 1;
  const paginatedLogs = useMemo(() => {
    return filteredLogs.slice(
      (currentPage - 1) * pageSize,
      currentPage * pageSize
    );
  }, [filteredLogs, currentPage, pageSize]);

  const exportToCSV = () => {
    if (filteredLogs.length === 0) return;
    const headers = ["Date", "Solar Generation (kWh)", "Grid (kWh)", "Diesel Backup (hrs)", "Battery SOC (%)", "Uptime (%)", "Inverter Temp (°C)"];
    const csvRows = [
      headers.join(","),
      ...filteredLogs.map((log: any) => [
        log.date || log.timestamp || "—",
        log.solar_kwh != null ? log.solar_kwh : "—",
        log.grid_kwh != null ? log.grid_kwh : "—",
        log.diesel_hrs != null ? log.diesel_hrs : "—",
        log.battery_soc != null ? log.battery_soc : "—",
        log.uptime_pct != null ? log.uptime_pct : "—",
        log.temp_c != null ? log.temp_c : "—"
      ].map(val => `"${val}"`).join(","))
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const siteId = selectedSite?.activity_data?.site_id ?? selectedSite?.site_id ?? selectedSite?.id ?? "export";
    link.setAttribute("href", url);
    link.setAttribute("download", `telemetry_logs_${siteId}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // ---------------------------------------------------------------------------
  // Derived metrics (safe defaults when API hasn't responded yet)
  // ---------------------------------------------------------------------------
  const totalCo2 = portfolio?.total_tco2e_reduced ?? 0;
  const totalMwh = portfolio?.total_energy_mwh ?? 0;
  const totalProjects = portfolio?.total_projects ?? activities.length;
  const portfolioValue = portfolio?.estimated_value_usd ?? 0;

  // Energy-mix helper — build chart data from an activity's activity_data
  const buildMixData = (ad: any) => {
    if (!ad) return [];
    return [
      ad.solar_kwp != null && { name: "Solar", value: Number(ad.solar_kwp) },
      ad.diesel_litres != null && { name: "Diesel", value: Number(ad.diesel_litres) },
      ad.gas_m3 != null && { name: "Gas", value: Number(ad.gas_m3) },
      ad.battery_kwh != null && { name: "Battery", value: Number(ad.battery_kwh) },
    ].filter(Boolean) as { name: string; value: number }[];
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <>
      <div className="space-y-6 max-w-7xl mx-auto pb-10 animate-fade-in-up text-[var(--color-text-primary)]">

        {/* ═══════════════════════════════════════════════════════════════════
            HEADER SECTION
            ═══════════════════════════════════════════════════════════════ */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded bg-amber-400/10 text-amber-400 text-[9px] font-extrabold tracking-wider uppercase border border-amber-400/15 flex items-center gap-1">
                <Zap size={10} /> Energy Displacement MRV
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
              <Zap className="text-amber-400" size={20} /> Hybrid Energy Portfolio
            </h1>
            <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
              Monitor solar, diesel, and gas displacement metrics across all active energy MRV sites.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={loadData}
              className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
              title="Refresh energy data"
            >
              <RefreshCw size={15} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
            </button>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════
            PORTFOLIO METRIC CARDS
            ═══════════════════════════════════════════════════════════════ */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total CO₂ Displaced */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-amber-400/30 transition-all">
            <div className="space-y-1">
              <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Total CO₂ Displaced</p>
              <p className="text-2xl font-black text-amber-400 tracking-tight">
                {isLoading ? "..." : totalCo2.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
              </p>
              <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Verified emission reductions</p>
            </div>
            <div className="p-3 bg-amber-400/5 border border-amber-400/10 rounded-xl text-amber-400 shrink-0 group-hover:bg-amber-400 group-hover:text-white transition-all duration-300">
              <Leaf size={18} />
            </div>
          </div>

          {/* Total Energy Generated */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-400/30 transition-all">
            <div className="space-y-1">
              <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Total Energy Generated</p>
              <p className="text-2xl font-black text-blue-400 tracking-tight">
                {isLoading ? "..." : totalMwh.toLocaleString(undefined, { maximumFractionDigits: 1 })} <span className="text-xs font-bold text-[var(--color-text-muted)]">MWh</span>
              </p>
              <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Cumulative clean generation</p>
            </div>
            <div className="p-3 bg-blue-400/5 border border-blue-400/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-400 group-hover:text-white transition-all duration-300">
              <Zap size={18} />
            </div>
          </div>

          {/* Active Projects */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-400/30 transition-all">
            <div className="space-y-1">
              <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Active Projects</p>
              <p className="text-2xl font-black text-purple-400 tracking-tight">
                {isLoading ? "..." : totalProjects} <span className="text-xs font-bold text-[var(--color-text-muted)]">Sites</span>
              </p>
              <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Monitored energy facilities</p>
            </div>
            <div className="p-3 bg-purple-400/5 border border-purple-400/10 rounded-xl text-purple-400 shrink-0 group-hover:bg-purple-400 group-hover:text-white transition-all duration-300">
              <Layers size={18} />
            </div>
          </div>

          {/* Portfolio Value */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-emerald-400/30 transition-all">
            <div className="space-y-1">
              <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Portfolio Value</p>
              <p className="text-2xl font-black text-emerald-400 tracking-tight">
                {isLoading ? "..." : `$${portfolioValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              </p>
              <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Estimated credit market value</p>
            </div>
            <div className="p-3 bg-emerald-400/5 border border-emerald-400/10 rounded-xl text-emerald-400 shrink-0 group-hover:bg-emerald-400 group-hover:text-white transition-all duration-300">
              <DollarSign size={18} />
            </div>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════
            ENERGY ACTIVITIES TABLE
            ═══════════════════════════════════════════════════════════════ */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
          {/* Table Header */}
          <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
            <h2 className="text-xs font-bold uppercase tracking-wider">Energy Activities</h2>
            <div className="text-[9px] font-extrabold text-amber-400 bg-amber-400/5 border border-amber-400/15 px-2 py-0.5 rounded uppercase">
              {activities.length} records
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Site ID</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Type</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Solar (kWp)</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Data Source</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Trust Score</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]/70">
                {/* Loading spinner */}
                {isLoading && activities.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                        <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Loading energy activities…</p>
                      </div>
                    </td>
                  </tr>
                ) : activities.length === 0 ? (
                  /* Empty state */
                  <tr>
                    <td colSpan={7} className="p-16 text-center">
                      <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                        <div className="w-12 h-12 rounded-full bg-amber-400/10 flex items-center justify-center mb-3 border border-amber-400/15 text-amber-400">
                          <AlertCircle size={22} />
                        </div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">No Activities</h3>
                        <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                          No energy displacement activities have been recorded yet. Add sites to begin monitoring.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  activities.map((act) => {
                    const ad = act.activity_data ?? act;
                    const siteId = act.site_id ?? act.id ?? "—";
                    const isExpanded = expandedId === (act.id ?? siteId);
                    const mixData = buildMixData(ad);
                    const status = (act.status ?? "pending").toLowerCase();

                    return (
                      <Fragment key={act.id ?? siteId}>
                        {/* Main row */}
                        <tr
                          className="hover:bg-[var(--color-background)]/20 transition-colors cursor-pointer group"
                          onClick={() => setExpandedId(isExpanded ? null : (act.id ?? siteId))}
                        >
                          {/* Site ID */}
                          <td className="p-4">
                            <span className="text-xs font-mono font-bold text-[var(--color-text-secondary)] bg-[var(--color-background)] border border-[var(--color-border)] px-2 py-0.5 rounded">
                              {String(siteId).substring(0, 12)}{String(siteId).length > 12 ? "…" : ""}
                            </span>
                          </td>

                          {/* Type */}
                          <td className="p-4">
                            <div className="flex items-center gap-2">
                              <Sun size={13} className="text-amber-400" />
                              <span className="text-xs font-bold text-[var(--color-text-primary)]">
                                {ad.type ?? ad.energy_type ?? "Solar Hybrid"}
                              </span>
                            </div>
                          </td>

                          {/* Solar kWp */}
                          <td className="p-4 text-right">
                            <span className="text-xs font-black text-amber-400 tracking-tight">
                              {ad.solar_kwp != null ? `${Number(ad.solar_kwp).toLocaleString()} kWp` : "—"}
                            </span>
                          </td>

                          {/* Data Source */}
                          <td className="p-4">
                            <span className="text-xs font-semibold text-[var(--color-text-secondary)]">
                              {ad.data_source ?? "Telemetry"}
                            </span>
                          </td>

                          {/* Trust Score */}
                          <td className="p-4 text-center">
                            <div className="inline-flex items-center gap-1">
                              <Shield size={12} className={
                                (act.trust_score ?? 0) >= 80 ? "text-emerald-400" :
                                (act.trust_score ?? 0) >= 50 ? "text-amber-400" : "text-red-400"
                              } />
                              <span className={`text-xs font-black tracking-tight ${
                                (act.trust_score ?? 0) >= 80 ? "text-emerald-400" :
                                (act.trust_score ?? 0) >= 50 ? "text-amber-400" : "text-red-400"
                              }`}>
                                {act.trust_score != null ? `${act.trust_score}%` : "—"}
                              </span>
                            </div>
                          </td>

                          {/* Status */}
                          <td className="p-4 text-center">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider ${
                              STATUS_STYLES[status] ?? STATUS_STYLES.pending
                            }`}>
                              {status}
                            </span>
                          </td>

                          {/* Date */}
                          <td className="p-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <span className="text-xs text-[var(--color-text-secondary)] font-medium">
                                {act.created_at ? new Date(act.created_at).toLocaleDateString() : "—"}
                              </span>
                              {isExpanded ? (
                                <ChevronUp size={14} className="text-[var(--color-text-muted)]" />
                              ) : (
                                <ChevronDown size={14} className="text-[var(--color-text-muted)]" />
                              )}
                            </div>
                          </td>
                        </tr>

                        {/* Expanded detail row */}
                        {isExpanded && (
                          <tr>
                            <td colSpan={7} className="p-0">
                              <div className="bg-[var(--color-background)]/60 border-t border-b border-[var(--color-border)]/50 p-5 space-y-4 animate-fade-in-up">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                  {/* Energy Mix Pie Chart */}
                                  {mixData.length > 0 && (
                                    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
                                      <h4 className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Energy Mix</h4>
                                      <ResponsiveContainer width="100%" height={160}>
                                        <PieChart>
                                          <Pie
                                            data={mixData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={40}
                                            outerRadius={65}
                                            paddingAngle={3}
                                            dataKey="value"
                                          >
                                            {mixData.map((_, i) => (
                                              <Cell key={i} fill={MIX_COLORS[i % MIX_COLORS.length]} />
                                            ))}
                                          </Pie>
                                          <RechartsTooltip
                                            contentStyle={{
                                              background: "var(--color-surface)",
                                              border: "1px solid var(--color-border)",
                                              borderRadius: "12px",
                                              fontSize: "11px",
                                              color: "var(--color-text-primary)",
                                            }}
                                          />
                                        </PieChart>
                                      </ResponsiveContainer>
                                      <div className="flex flex-wrap gap-3 mt-2">
                                        {mixData.map((d, i) => (
                                          <div key={d.name} className="flex items-center gap-1.5">
                                            <span className="w-2 h-2 rounded-full" style={{ background: MIX_COLORS[i % MIX_COLORS.length] }} />
                                            <span className="text-[9px] font-bold text-[var(--color-text-secondary)]">{d.name}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Activity Data Fields */}
                                  <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 md:col-span-2">
                                    <h4 className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Activity Details</h4>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                      {Object.entries(ad)
                                        .filter(([key]) => {
                                          return (
                                            key !== "telemetry_log" &&
                                            key !== "image_metadata" &&
                                            key !== "device_signature" &&
                                            !key.endsWith("_url") &&
                                            !key.endsWith("_image_url")
                                          );
                                        })
                                        .map(([key, value]) => (
                                          <div key={key} className="bg-[var(--color-background)] p-3 rounded-lg border border-[var(--color-border)]">
                                            <p className="text-[8px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-0.5">
                                              {key.replace(/_/g, " ")}
                                            </p>
                                            <p className="text-xs font-bold text-[var(--color-text-primary)] truncate">
                                              {value != null ? String(value) : "—"}
                                            </p>
                                          </div>
                                        ))}
                                    </div>
                                  </div>
                                </div>

                                {/* Quick actions row */}
                                <div className="flex justify-end">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      openSiteDetail(act);
                                    }}
                                    className="text-xs font-extrabold text-[#00B47A] hover:text-[#00B47A]/80 uppercase tracking-wider transition-colors active:scale-95"
                                  >
                                    View Full Telemetry →
                                  </button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          SITE DETAIL MODAL
          ═══════════════════════════════════════════════════════════════ */}
      {selectedSite && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setSelectedSite(null)}
        >
          <div
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4.5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider">Site Telemetry & Detail</h3>
                <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                  SITE: <span className="font-mono text-amber-400 font-bold">{selectedSite.site_id ?? selectedSite.id}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedSite(null)}
                className="p-1.5 rounded-lg hover:bg-[var(--color-surface)] border border-transparent hover:border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-red-500 transition-all"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 flex-1 custom-scrollbar text-xs">
              {/* Activity summary grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: "Type", value: selectedSite.activity_data?.type ?? selectedSite.activity_data?.energy_type ?? "Solar Hybrid", icon: Sun, color: "amber-400" },
                  { label: "Solar Capacity", value: selectedSite.activity_data?.solar_kwp ? `${selectedSite.activity_data.solar_kwp} kWp` : "—", icon: Sun, color: "amber-400" },
                  { label: "Trust Score", value: selectedSite.trust_score != null ? `${selectedSite.trust_score}%` : "—", icon: Shield, color: "emerald-400" },
                  { label: "Status", value: selectedSite.status ?? "pending", icon: TrendingUp, color: "blue-400" },
                ].map((item) => (
                  <div key={item.label} className="bg-[var(--color-background)] p-4 rounded-xl border border-[var(--color-border)]">
                    <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1">{item.label}</p>
                    <p className={`font-bold text-${item.color}`}>{item.value}</p>
                  </div>
                ))}
              </div>

              {/* Energy Mix Breakdown */}
              {(() => {
                const ad = selectedSite.activity_data;
                const mixData = buildMixData(ad);
                if (mixData.length === 0) return null;
                return (
                  <div>
                    <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                      <Battery size={14} className="text-amber-400" /> Energy Mix Breakdown
                    </h4>
                    <div className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-4">
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={mixData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                          <XAxis dataKey="name" tick={{ fill: "var(--color-text-muted)", fontSize: 10 }} />
                          <YAxis tick={{ fill: "var(--color-text-muted)", fontSize: 10 }} />
                          <RechartsTooltip
                            contentStyle={{
                              background: "var(--color-surface)",
                              border: "1px solid var(--color-border)",
                              borderRadius: "12px",
                              fontSize: "11px",
                              color: "var(--color-text-primary)",
                            }}
                          />
                          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                            {mixData.map((_, i) => (
                              <Cell key={i} fill={MIX_COLORS[i % MIX_COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                );
              })()}

              {/* Telemetry Log */}
              <div className="space-y-4">
                {/* Header with Title & Export Button */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--color-border)]/50">
                  <div className="flex items-center gap-2">
                    <Fuel size={16} className="text-blue-400" />
                    <div>
                      <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
                        Telemetry Log
                      </h4>
                      {!isTelemetryLoading && telemetry.length > 0 && (
                        <p className="text-[9px] text-[var(--color-text-muted)] mt-0.5">
                          Showing {filteredLogs.length} total entries
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {!isTelemetryLoading && telemetry.length > 0 && (
                    <button
                      onClick={exportToCSV}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00B47A]/10 hover:bg-[#00B47A]/25 border border-[#00B47A]/20 text-[#00B47A] text-[9px] font-extrabold rounded-lg uppercase tracking-wider transition-all self-start sm:self-auto active:scale-95"
                    >
                      <Download size={12} /> Export CSV
                    </button>
                  )}
                </div>

                {isTelemetryLoading ? (
                  <div className="flex items-center justify-center py-12 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]/50">
                    <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : telemetry.length > 0 ? (
                  <div className="space-y-3">
                    {/* Filter and Search Bar */}
                    <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
                      {/* Search Bar */}
                      <div className="relative flex-1">
                        <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-[var(--color-text-muted)]">
                          <Search size={12} />
                        </span>
                        <input
                          type="text"
                          placeholder="Search logs by date..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full pl-8 pr-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-[10px] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[#00B47A]/40 transition-colors font-mono"
                        />
                      </div>

                      {/* Range Selector */}
                      <div className="flex bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-0.5 self-start sm:self-auto gap-0.5">
                        {[
                          { id: "7d", label: "7 Days" },
                          { id: "30d", label: "30 Days" },
                          { id: "all", label: "All Logs" }
                        ].map((btn) => (
                          <button
                            key={btn.id}
                            onClick={() => setDateRange(btn.id)}
                            className={`px-2.5 py-1 text-[9px] font-extrabold rounded-md uppercase tracking-wider transition-all ${
                              dateRange === btn.id
                                ? "bg-[#00B47A] text-white shadow-sm font-black"
                                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                            }`}
                          >
                            {btn.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* The Table */}
                    {paginatedLogs.length === 0 ? (
                      <p className="text-xs text-[var(--color-text-muted)] italic p-8 text-center bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]/50">
                        No telemetry logs match the selected filters.
                      </p>
                    ) : (
                      <div className="border border-[var(--color-border)]/50 rounded-xl overflow-hidden bg-[var(--color-surface)] shadow-inner">
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-[10px] border-collapse font-mono">
                            <thead>
                              <tr className="bg-[var(--color-background)] border-b border-[var(--color-border)]/50 text-[8px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                                <th className="p-2.5">Date</th>
                                <th className="p-2.5 text-right">Solar</th>
                                <th className="p-2.5 text-right">Grid</th>
                                <th className="p-2.5 text-right">Diesel</th>
                                <th className="p-2.5 text-center">Battery</th>
                                <th className="p-2.5 text-center">Uptime</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--color-border)]/50">
                              {paginatedLogs.map((log: any, idx: number) => (
                                <tr key={idx} className="hover:bg-[var(--color-background)]/20 transition-colors">
                                  <td className="p-2.5 font-bold text-[var(--color-text-secondary)]">
                                    {log.date || log.timestamp || log.ts || "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-amber-500 font-extrabold">
                                    {log.solar_kwh != null ? `${Number(log.solar_kwh).toFixed(1)}` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-[var(--color-text-secondary)] font-semibold">
                                    {log.grid_kwh != null ? `${Number(log.grid_kwh).toFixed(1)}` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-rose-500 font-semibold">
                                    {log.diesel_hrs != null ? `${Number(log.diesel_hrs).toFixed(1)} hrs` : "—"}
                                  </td>
                                  <td className="p-2.5 text-center text-[#00B47A] font-extrabold">
                                    {log.battery_soc != null ? `${Number(log.battery_soc).toFixed(0)}%` : "—"}
                                  </td>
                                  <td className="p-2.5 text-center">
                                    <span className={`inline-flex px-1.5 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider ${
                                      (log.uptime_pct ?? 100) > 80
                                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                        : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                    }`}>
                                      {log.uptime_pct != null ? `${log.uptime_pct}%` : "Online"}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)]/30 text-[9px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
                        <span>
                          Showing {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, filteredLogs.length)} of {filteredLogs.length}
                        </span>
                        
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            className={`p-1.5 rounded-lg border border-[var(--color-border)] transition-all bg-[var(--color-surface)] hover:text-[var(--color-text-primary)] active:scale-95 ${
                              currentPage === 1 ? "opacity-40 cursor-not-allowed" : ""
                            }`}
                          >
                            <ChevronLeft size={10} />
                          </button>
                          
                          <span className="font-mono px-2 py-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)]">
                            {currentPage} / {totalPages}
                          </span>
                          
                          <button
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages}
                            className={`p-1.5 rounded-lg border border-[var(--color-border)] transition-all bg-[var(--color-surface)] hover:text-[var(--color-text-primary)] active:scale-95 ${
                              currentPage === totalPages ? "opacity-40 cursor-not-allowed" : ""
                            }`}
                          >
                            <ChevronRight size={10} />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-[var(--color-text-muted)] bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]/50">
                    <AlertCircle size={20} className="mx-auto mb-2 opacity-40 text-blue-400" />
                    <p className="text-xs font-medium">No telemetry data available for this site.</p>
                  </div>
                )}
              </div>

              {/* Calculation Details / Raw Payload */}
              <div>
                <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5">Raw Activity Payload</h4>
                <pre className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-x-auto text-[10px] text-slate-400 font-mono shadow-inner leading-relaxed max-h-48 overflow-y-auto select-all">
                  {JSON.stringify(selectedSite, null, 2)}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-background)]/50 flex justify-end">
              <button
                onClick={() => setSelectedSite(null)}
                className="px-4 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold hover:bg-[var(--color-background)] transition-all uppercase tracking-wider"
              >
                Close Detail
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


