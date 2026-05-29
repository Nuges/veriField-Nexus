"use client";

import { useEffect, useState } from "react";
import { 
  AlertTriangle, 
  Filter, 
  AlertCircle, 
  RefreshCw, 
  ShieldAlert, 
  Clock, 
  MapPin, 
  Activity, 
  Check, 
  X,
  ShieldCheck,
  TrendingUp,
  Layers
} from "lucide-react";
import { fetchAnomalies, resolveAnomaly } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function AnomaliesPage() {
  const toast = useToast();
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAnomalies();
      setAnomalies(res.anomalies);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async (flagId: string, action: "verify" | "reject") => {
    try {
      await resolveAnomaly(flagId, action, `Admin ${action}ed manually`);
      toast.success(
        action === "verify" ? "Anomaly Cleared" : "Anomaly Rejected",
        action === "verify" ? "The activity has been manually approved and cleared of suspicious threats." : "The activity has been formally rejected from the ledger."
      );
      await loadData();
    } catch (err) {
      console.error("Failed to resolve:", err);
      toast.error("Override Failed", "Could not commit manual override to the ledger.");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getSeverityStyle = (severity: string) => {
    switch(severity) {
      case 'critical': return "bg-red-500/10 text-red-500 border-red-500/25";
      case 'high': return "bg-orange-500/10 text-orange-500 border-orange-500/25";
      case 'medium': return "bg-amber-500/10 text-amber-500 border-amber-500/25";
      default: return "bg-blue-500/10 text-blue-400 border-blue-500/25";
    }
  };

  const getFlagIcon = (type: string) => {
    if (type.includes("gps") || type.includes("travel")) return <MapPin size={14} className="text-blue-400" />;
    if (type.includes("time") || type.includes("pattern")) return <Clock size={14} className="text-amber-400" />;
    if (type.includes("image")) return <AlertCircle size={14} className="text-red-400" />;
    return <Activity size={14} className="text-[#00B47A]" />;
  };

  // Derive dynamic metrics
  const activeThreatsCount = anomalies.filter(a => !a.resolved).length;
  const criticalThreatsCount = anomalies.filter(a => a.severity === "critical" && !a.resolved).length;
  const resolvedCount = anomalies.filter(a => a.resolved).length;

  return (
    <div className="space-y-6 animate-fade-in-up">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] font-extrabold tracking-wider uppercase border border-red-500/15">
              Threat Analytics Center
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
            <ShieldAlert className="text-red-500" size={20} /> AI Anomaly Detection Logs
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit AI-flagged suspicious uploads, review biometric inconsistencies, and execute manual overrides.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button 
            onClick={loadData}
            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
            title="Reload ledger"
          >
            <RefreshCw size={15} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
        </div>
      </div>

      {/* 📊 DYNAMIC STATS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Active Threats */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-red-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Active Threats</p>
            <p className="text-2xl font-black text-red-400 tracking-tight">
              {isLoading ? "..." : activeThreatsCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Unresolved AI anomaly triggers</p>
          </div>
          <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl text-red-500 shrink-0 group-hover:bg-red-500 group-hover:text-white transition-all duration-300">
            <AlertTriangle size={18} />
          </div>
        </div>

        {/* Critical Risks */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-orange-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Critical Failures</p>
            <p className="text-2xl font-black text-orange-400 tracking-tight">
              {isLoading ? "..." : criticalThreatsCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Severe geometric or image duplicates</p>
          </div>
          <div className="p-3 bg-orange-500/5 border border-orange-500/10 rounded-xl text-orange-400 shrink-0 group-hover:bg-orange-500 group-hover:text-white transition-all duration-300">
            <ShieldAlert size={18} />
          </div>
        </div>

        {/* Override Clearances */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Resolved Clearances</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {isLoading ? "..." : resolvedCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Manually overridden entries</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <ShieldCheck size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 ANOMALIES TABLE LEDGER */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
          <h2 className="text-xs font-bold uppercase tracking-wider">Threat Log Roster</h2>
          <div className="text-[9px] font-extrabold text-red-400 bg-red-500/5 border border-red-500/15 px-2 py-0.5 rounded uppercase">
            {anomalies.length} Flagged Activities
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Detection Timestamp</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Severity Level</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Telemetry Flag</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Suspicion Description</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Verification Status</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Resolutions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]/70">
              {isLoading && anomalies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                      <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Running security scans...</p>
                    </div>
                  </td>
                </tr>
              ) : anomalies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-16 text-center">
                    <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                      <div className="w-12 h-12 rounded-full bg-[#00B47A]/10 flex items-center justify-center mb-3 border border-[#00B47A]/15 text-[#00B47A]">
                        <ShieldCheck size={22} />
                      </div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">System Secured</h3>
                      <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                        The Trust Engine reports clean signals across all monitoring sectors. No anomalous inputs detected.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                anomalies.map((flag) => (
                  <tr key={flag.id} className="hover:bg-[var(--color-background)]/20 transition-colors group">
                    
                    {/* Timestamp */}
                    <td className="p-4 whitespace-nowrap">
                      <div className="text-xs font-bold text-[var(--color-text-primary)]">
                        {new Date(flag.created_at).toLocaleDateString()}
                      </div>
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
                        {new Date(flag.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>

                    {/* Severity */}
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-[9px] font-extrabold uppercase tracking-wider border ${getSeverityStyle(flag.severity)}`}>
                        {flag.severity}
                      </span>
                    </td>

                    {/* Telemetry Flag */}
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {getFlagIcon(flag.flag_type)}
                        <span className="text-xs font-bold text-[var(--color-text-primary)] font-mono uppercase tracking-tight">
                          {flag.flag_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </td>

                    {/* Description */}
                    <td className="p-4">
                      <p className="text-xs text-[var(--color-text-secondary)] max-w-xs md:max-w-md font-medium leading-relaxed">
                        {flag.description}
                      </p>
                    </td>

                    {/* Status */}
                    <td className="p-4 text-right">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider ${
                        flag.activity_status === "flagged" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                        flag.activity_status === "review" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                        "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)]"
                      }`}>
                        {flag.activity_status}
                      </span>
                      <div className="text-[9px] text-[var(--color-text-muted)] mt-1 font-mono">
                        ID: {flag.activity_id.substring(0,8)}...
                      </div>
                    </td>

                    {/* Resolution Override */}
                    <td className="p-4">
                      <div className="flex items-center justify-center">
                        {flag.resolved ? (
                          <span className="text-[9px] font-extrabold px-2.5 py-0.5 rounded bg-[var(--color-background)] text-slate-500 border border-[var(--color-border)] uppercase tracking-wider">
                            Resolved
                          </span>
                        ) : (
                          <div className="flex items-center justify-center gap-1.5 shrink-0">
                            <button 
                              onClick={() => handleResolve(flag.id, "verify")}
                              className="p-1.5 rounded-lg bg-[#00B47A]/10 text-[#00B47A] hover:bg-[#00B47A] hover:text-white border border-[#00B47A]/25 transition-all active:scale-90"
                              title="Clear Anomaly & Verify"
                            >
                              <Check size={13} />
                            </button>
                            <button 
                              onClick={() => handleResolve(flag.id, "reject")}
                              className="p-1.5 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white border border-red-500/25 transition-all active:scale-90"
                              title="Reject Activity"
                            >
                              <X size={13} />
                            </button>
                          </div>
                        )}
                      </div>
                    </td>

                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
