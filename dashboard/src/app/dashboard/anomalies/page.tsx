"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Filter, AlertCircle, RefreshCw, ShieldAlert, Clock, MapPin, Activity, Check, X } from "lucide-react";
import { fetchAnomalies, resolveAnomaly } from "@/lib/api";

export default function AnomaliesPage() {
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
      // Optimistic UI update or full reload
      await loadData();
    } catch (err) {
      console.error("Failed to resolve:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getSeverityStyle = (severity: string) => {
    switch(severity) {
      case 'critical': return "bg-red-500/10 text-red-500 border-red-500/20";
      case 'high': return "bg-orange-500/10 text-orange-500 border-orange-500/20";
      case 'medium': return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      default: return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    }
  };

  const getFlagIcon = (type: string) => {
    if (type.includes("gps") || type.includes("travel")) return <MapPin size={16} />;
    if (type.includes("time") || type.includes("pattern")) return <Clock size={16} />;
    if (type.includes("image")) return <AlertCircle size={16} />;
    return <Activity size={16} />;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight flex items-center gap-2">
            <ShieldAlert className="text-red-500" /> Anomalies
          </h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Review and resolve AI-flagged suspicious entries</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadData}
            className="p-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
            <Filter size={18} /> Filter
          </button>
        </div>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-100">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface)]">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Detected Threats</h2>
          <div className="text-xs font-medium text-[var(--color-text-secondary)] bg-[var(--color-background)] px-3 py-1 rounded-full border border-[var(--color-border)]">
            {anomalies.length} Flagged Activities
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Detection Time</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Severity</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Flag Type</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Description</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Activity Status</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-center">Resolution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading && anomalies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[var(--color-text-secondary)]">Scanning network...</td>
                </tr>
              ) : anomalies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-16 text-center">
                    <div className="flex flex-col items-center justify-center">
                      <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 border border-emerald-500/20">
                        <ShieldAlert className="text-emerald-500" size={32} />
                      </div>
                      <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No anomalies detected</h3>
                      <p className="text-[var(--color-text-secondary)] mt-1">The Trust Engine hasn't flagged any recent activities.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                anomalies.map((flag) => (
                  <tr key={flag.id} className="hover:bg-[var(--color-surface)] transition-colors group">
                    <td className="p-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-[var(--color-text-primary)]">
                        {new Date(flag.created_at).toLocaleDateString()}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">
                        {new Date(flag.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border uppercase tracking-wider ${getSeverityStyle(flag.severity)}`}>
                        {flag.severity}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="text-[var(--color-text-muted)]">
                          {getFlagIcon(flag.flag_type)}
                        </div>
                        <span className="text-sm font-medium text-[var(--color-text-primary)] font-mono">{flag.flag_type}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <p className="text-sm text-[var(--color-text-secondary)] max-w-md">{flag.description}</p>
                    </td>
                    <td className="p-4 text-right">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                        flag.activity_status === "flagged" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                        flag.activity_status === "review" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                        "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)]"
                      }`}>
                        {flag.activity_status}
                      </span>
                      <div className="text-xs text-[var(--color-text-muted)] mt-1 font-mono">
                        {flag.activity_id.substring(0,8)}
                      </div>
                    </td>
                    <td className="p-4 text-center">
                      {flag.resolved ? (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                          RESOLVED
                        </span>
                      ) : (
                        <div className="flex items-center justify-center gap-2">
                          <button 
                            onClick={() => handleResolve(flag.id, "verify")}
                            className="p-1.5 rounded-md bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                            title="Verify Activity (Approve)"
                          >
                            <Check size={16} />
                          </button>
                          <button 
                            onClick={() => handleResolve(flag.id, "reject")}
                            className="p-1.5 rounded-md bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 transition-colors"
                            title="Reject Activity"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      )}
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
