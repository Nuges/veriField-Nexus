// =============================================================================
// VeriField Nexus — Activities Page
// =============================================================================
// Sortable, filterable list of all field activities.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Search, 
  Filter, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight, 
  Download, 
  MapPin, 
  Calendar, 
  Clock, 
  ShieldCheck, 
  AlertTriangle, 
  TrendingUp, 
  Sparkles, 
  Flame, 
  User as UserIcon,
  Layers,
  ArrowUpRight
} from "lucide-react";
import { fetchActivities } from "@/lib/api";
import type { Activity, ActivityListResponse } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getSectorConfig } from "@/lib/sectorConfig";

export default function ActivitiesPage() {
  const { activeSector } = useWorkspace();
  const sectorConfig = getSectorConfig(activeSector);

  const [data, setData] = useState<ActivityListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [page, setPage] = useState(1);
  const [activityType, setActivityType] = useState("");
  const [status, setStatus] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const router = useRouter();

  // Reset filters when active sector changes
  useEffect(() => {
    setActivityType("");
    setStatus("");
    setPage(1);
    setSearchQuery("");
  }, [activeSector]);

  const loadActivities = async () => {
    setIsLoading(true);
    setError(null);
    try {
      let typeParam = activityType;
      if (!typeParam) {
        if (activeSector === "cookstove") {
          typeParam = "CLEAN_COOKING";
        } else if (activeSector === "energy") {
          typeParam = "HYBRID_ENERGY";
        }
      }
      const res = await fetchActivities({ page, per_page: 20, activity_type: typeParam, status });
      setData(res);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to load installations. Please refresh or re-login.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();
    
    // Auto-refresh the activities list every 5 seconds for near real-time updates
    const interval = setInterval(() => {
      loadActivities();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [page, activityType, status, activeSector]);

  // Client-side search query logic
  const filteredActivities = data?.activities.filter(a => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const agentName = (a.agent_name || "").toLowerCase();
    const userId = (a.user_id || "").toLowerCase();
    const actType = (a.activity_type || "").toLowerCase();
    const idStr = (a.id || "").toLowerCase();
    return agentName.includes(query) || userId.includes(query) || actType.includes(query) || idStr.includes(query);
  }) || [];

  // Derived metrics from current activities view (filtered client-side by query)
  const totalSubmissionsCount = filteredActivities.length;
  const highTrustActivitiesCount = filteredActivities.filter(a => (a.trust_score ?? 0) >= 80).length || 0;
  const flaggedCount = filteredActivities.filter(a => a.status === "flagged" || a.duplicate_flag).length || 0;
  const reviewCount = filteredActivities.filter(a => a.status === "review" || a.status === "pending").length || 0;

  // Dynamic labelling formatter matching Flutter logic
  const formatStoveModel = (model: string) => {
    if (!model) return '';
    return model
      .replace(/_/g, ' ')
      .replace(/-/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getDisplayTitle = (activity: Activity) => {
    let activityData: any = null;
    if (typeof activity.activity_data === 'string') {
      try {
        activityData = JSON.parse(activity.activity_data);
      } catch (_) {}
    } else if (activity.activity_data && typeof activity.activity_data === 'object') {
      activityData = activity.activity_data;
    }

    if (activityData) {
      const headName = activityData.head_name || '';
      const stoveModel = activityData.stove_model || '';
      const serialNumber = activityData.serial_number || '';

      if (headName && stoveModel) {
        return `${formatStoveModel(stoveModel)} • ${headName}`;
      } else if (headName) {
        return `Stove: ${headName}`;
      } else if (stoveModel) {
        return `${formatStoveModel(stoveModel)} Installation`;
      } else if (serialNumber) {
        return `Stove SN: ${serialNumber}`;
      }
    }

    return activity.activity_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  const cleanUrl = (url: string) => {
    if (!url) return "";
    if (url.includes("/static/")) {
      const parts = url.split("/static/");
      return "/static/" + parts[parts.length - 1];
    }
    return url;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10 text-[var(--color-text-primary)]">
      {/* 🧭 SYSTEM HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase">
              {sectorConfig.methodology}
            </span>
            <span className="text-[10px] text-[var(--color-text-secondary)] font-semibold flex items-center gap-1">
              <Sparkles size={11} className="text-[#00B47A]" /> Digital MRV Capture Ledger
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">
            {activeSector === "cookstove" ? "Field Installation Records" : "Energy Telemetry & Site Records"}
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            {activeSector === "cookstove" 
              ? "Review, filter, and audit near real-time field installation uploads, verification logs, and trust scores."
              : "Review, filter, and audit smart hybrid energy inverter telemetry records, solar metrics, and logs."}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-[10px] text-[var(--color-text-muted)] hidden sm:inline-flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] px-2.5 py-1 rounded-lg">
              <Clock size={11} className="text-[#00B47A]" /> Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={loadActivities} 
            className="p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
            title="Refresh Ledger"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#00B47A]/10 text-[#00B47A] text-xs font-bold border border-[#00B47A]/20 hover:bg-[#00B47A]/20 transition-all shadow-sm active:scale-95">
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* 🧭 STRATEGIC HEALTH STATS STRIP */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-up stagger-children">
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 flex flex-col justify-between shadow-sm border-l-4 border-l-[#00B47A] hover:shadow-md transition-all">
          <span className="text-[9px] uppercase font-extrabold tracking-wider text-[var(--color-text-muted)]">Submissions Ledger</span>
          <div className="flex items-baseline gap-1.5 mt-1.5">
            <span className="text-2xl font-black tracking-tight text-[var(--color-text-primary)]">
              {totalSubmissionsCount}
            </span>
            <span className="text-[#00B47A] text-[9px] font-extrabold flex items-center gap-0.5">
              <ArrowUpRight size={10} /> Active
            </span>
          </div>
          <span className="text-[8px] text-[var(--color-text-muted)] mt-1">Registry records synced</span>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 flex flex-col justify-between shadow-sm border-l-4 border-l-emerald-500 hover:shadow-md transition-all">
          <span className="text-[9px] uppercase font-extrabold tracking-wider text-[var(--color-text-muted)]">High Trust Rate</span>
          <div className="flex items-baseline gap-0.5 mt-1.5">
            <span className="text-2xl font-black tracking-tight text-emerald-500">
              {data?.activities.length ? Math.round((highTrustActivitiesCount / data.activities.length) * 100) : 0}%
            </span>
            <span className="text-emerald-500 text-[9px] font-extrabold ml-1">✓ Verified</span>
          </div>
          <span className="text-[8px] text-[var(--color-text-muted)] mt-1">Scored &gt;= 80 index rating</span>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 flex flex-col justify-between shadow-sm border-l-4 border-l-amber-500 hover:shadow-md transition-all">
          <span className="text-[9px] uppercase font-extrabold tracking-wider text-[var(--color-text-muted)]">Pending Audit</span>
          <div className="flex items-baseline gap-1.5 mt-1.5">
            <span className="text-2xl font-black tracking-tight text-amber-500">
              {reviewCount}
            </span>
            <span className="text-amber-500 text-[9px] font-extrabold flex items-center gap-0.5">
              <Clock size={10} /> Review
            </span>
          </div>
          <span className="text-[8px] text-[var(--color-text-muted)] mt-1">Requires manual audit approval</span>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 flex flex-col justify-between shadow-sm border-l-4 border-l-red-500 hover:shadow-md transition-all">
          <span className="text-[9px] uppercase font-extrabold tracking-wider text-[var(--color-text-muted)]">Flagged Risks</span>
          <div className="flex items-baseline mt-1.5">
            <span className="text-2xl font-black tracking-tight text-red-500">
              {flaggedCount}
            </span>
            <span className="text-red-500 text-[9px] font-extrabold ml-2 flex items-center gap-0.5">
              <AlertTriangle size={10} /> Conflict
            </span>
          </div>
          <span className="text-[8px] text-[var(--color-text-muted)] mt-1">Duplicate images or GPS outliers</span>
        </div>
      </div>

      {/* 🧭 FILTER & LIVE SEARCH BAR */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between shadow-sm animate-fade-in-up animation-delay-100">
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#00B47A] bg-[#00B47A]/5 px-2.5 py-1 rounded-lg border border-[#00B47A]/10">
            <Filter size={14} />
            <span>Filter Engine</span>
          </div>
          
          <select 
            value={activityType} 
            onChange={(e) => { setActivityType(e.target.value); setPage(1); }}
            className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] focus:ring-1 focus:ring-[#00B47A]/30 transition-all cursor-pointer"
          >
            {activeSector === "cookstove" ? (
              <>
                <option value="">All Cookstove Types</option>
                <option value="CLEAN_COOKING">Clean Cooking</option>
              </>
            ) : (
              <>
                <option value="">All Energy Types</option>
                <option value="HYBRID_ENERGY">Hybrid Energy</option>
              </>
            )}
          </select>

          <select 
            value={status} 
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] focus:ring-1 focus:ring-[#00B47A]/30 transition-all cursor-pointer"
          >
            <option value="">All Trust Statuses</option>
            <option value="verified">Verified (High Trust)</option>
            <option value="review">Review (Medium Trust)</option>
            <option value="flagged">Flagged (Low Trust)</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        {/* Live Search Input */}
        <div className="relative w-full md:max-w-xs">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--color-text-muted)] group-focus-within:text-[#00B47A]">
            <Search size={14} />
          </div>
          <input
            type="text"
            placeholder="Search by Agent name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl pl-9 pr-4 py-1.5 text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[#00B47A] focus:ring-1 focus:ring-[#00B47A]/30 transition-all"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--color-text-muted)] hover:text-[#00B47A] text-[10px] font-semibold"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* 🧭 DATA LEDGER TABLE */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm animate-fade-in-up animation-delay-200">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-background)] border-b border-[var(--color-border)]">
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">Installation Details</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">Sync Timestamp</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">Reporting Field Agent</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">Geospatial Capture Bounds</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">Immutability Trust</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading && !data ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs text-[var(--color-text-secondary)] font-semibold tracking-wide animate-pulse">Syncing secure MRV registry...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center gap-3 max-w-sm mx-auto">
                      <div className="p-3 bg-red-500/10 rounded-full text-red-500">
                        <AlertTriangle size={24} />
                      </div>
                      <span className="text-red-400 text-xs font-semibold">{error}</span>
                      <button onClick={loadActivities} className="px-4 py-2 rounded-xl bg-[#00B47A]/10 text-[#00B47A] text-xs font-bold border border-[#00B47A]/20 hover:bg-[#00B47A]/20 transition-all">
                        Force Ledger Reload
                      </button>
                    </div>
                  </td>
                </tr>
              ) : filteredActivities.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center gap-2 text-[var(--color-text-secondary)]">
                      <Layers size={20} className="text-[var(--color-text-muted)]" />
                      <span className="text-xs font-semibold">No synchronized field activities matched current parameters.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredActivities.map((activity) => (
                  <tr 
                    key={activity.id} 
                    onClick={() => router.push(`/dashboard/activities/${activity.id}`)}
                    className="hover:bg-[var(--color-background)] transition-all group cursor-pointer border-l-2 border-l-transparent hover:border-l-[#00B47A] relative"
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {activity.image_url ? (
                          <div className="w-10 h-10 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] overflow-hidden shrink-0 group-hover:border-[#00B47A]/40 transition-all">
                            <img src={cleanUrl(activity.image_url)} alt="Proof" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                          </div>
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] flex items-center justify-center shrink-0">
                            <span className="text-[var(--color-text-muted)] text-[9px] font-bold">No img</span>
                          </div>
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-[#00B47A] transition-colors">
                            {getDisplayTitle(activity)}
                          </p>
                          <div className="flex items-center gap-1.5 mt-1">
                            {activity.duplicate_flag && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 font-extrabold border border-red-500/15 flex items-center gap-0.5">
                                <AlertTriangle size={8} /> DUP MATCH
                              </span>
                            )}
                            {activity.environment_type ? (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-secondary)] font-semibold uppercase tracking-wider">
                                {activity.environment_type}
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">
                                Standard
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-xs">
                      <div className="flex items-center gap-1.5 text-[var(--color-text-primary)] font-semibold">
                        <Calendar size={12} className="text-[#00B47A]" />
                        <span>{new Date(activity.captured_at).toLocaleDateString()}</span>
                      </div>
                      <span className="block text-[10px] text-[var(--color-text-muted)] mt-0.5 font-medium ml-4">
                        {new Date(activity.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </td>
                    <td className="p-4 text-xs font-bold text-[var(--color-text-primary)]">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-[#00B47A]/10 border border-[#00B47A]/20 flex items-center justify-center text-[#00B47A] text-[9px] font-extrabold">
                          {activity.agent_name ? activity.agent_name.substring(0, 2).toUpperCase() : "AG"}
                        </div>
                        <div className="overflow-hidden">
                          <span className="block truncate">{activity.agent_name || "Assigned Agent"}</span>
                          <span className="block text-[8px] text-[var(--color-text-muted)] font-mono font-medium tracking-tight">
                            {activity.user_id.substring(0, 16)}...
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-xs">
                      {activity.latitude ? (
                        <div>
                          <div className="flex items-center gap-1 text-[var(--color-text-primary)] font-semibold">
                            <MapPin size={12} className="text-emerald-500" />
                            <span>{activity.latitude.toFixed(5)}, {activity.longitude?.toFixed(5)}</span>
                          </div>
                          <span className="block text-[9px] text-[var(--color-text-muted)] mt-0.5 ml-4 font-semibold">
                            Accuracy Confidence: ±{activity.gps_accuracy?.toFixed(1)}m
                          </span>
                        </div>
                      ) : (
                        <span className="text-[var(--color-text-muted)] text-[10px] font-bold">No Spatial Log</span>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <TrustBadge score={activity.trust_score} />
                        <span className="text-[10px] font-extrabold text-[#00B47A] hidden lg:inline-block bg-[#00B47A]/5 border border-[#00B47A]/15 px-1.5 py-0.5 rounded">
                          {(activity.trust_score ?? 0) >= 80 ? "SECURE" : (activity.trust_score ?? 0) >= 60 ? "AUDIT" : "WARN"}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="p-4 bg-[var(--color-background)] border-t border-[var(--color-border)] flex items-center justify-between">
            <span className="text-xs text-[var(--color-text-secondary)] font-semibold">
              Showing <span className="text-[var(--color-text-primary)]">{(data.page - 1) * data.per_page + 1}</span> to <span className="text-[var(--color-text-primary)]">{Math.min(data.page * data.per_page, data.total)}</span> of <span className="text-[var(--color-text-primary)]">{data.total}</span> assets
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/20 disabled:opacity-40 disabled:hover:text-[var(--color-text-secondary)] disabled:hover:border-[var(--color-border)] transition-all shadow-sm active:scale-95"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                disabled={page === data.total_pages}
                onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                className="p-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/20 disabled:opacity-40 disabled:hover:text-[var(--color-text-secondary)] disabled:hover:border-[var(--color-border)] transition-all shadow-sm active:scale-95"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
