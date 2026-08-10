"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Filter,
  ShieldCheck,
  Activity,
  Eye,
  Check,
  X,
  Search,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import { useToast } from "@/components/Toast";
import { fetchAnomalies, resolveAnomaly } from "@/lib/api";

export type EventSeverity = "CRITICAL" | "WARNING" | "INFO";
export type EventStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

export interface DataQualityEvent {
  id: string;
  eventType: string;
  severity: EventSeverity;
  status: EventStatus;
  assetName: string;
  assetId: string;
  projectName: string;
  description: string;
  timestamp: string;
  trustScoreImpact: number;
  payloadSnippet?: string;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
}

interface DataQualityEventConsoleProps {
  events?: DataQualityEvent[];
  title?: string;
  subtitle?: string;
}

const DEFAULT_EVENTS: DataQualityEvent[] = [
  {
    id: "EVT-2026-091",
    eventType: "TELEMETRY_SILENCE",
    severity: "CRITICAL",
    status: "ACTIVE",
    assetName: "Kano Solar Array Inverter 04",
    assetId: "AST-SOL-004",
    projectName: "Northern Nigeria Solar Mini-Grid",
    description: "No heartbeat telemetry payload received for > 45 minutes during peak irradiance hours.",
    timestamp: "2026-08-09T18:40:00Z",
    trustScoreImpact: -15,
    payloadSnippet: '{"inverter_id": "AST-SOL-004", "status": "OFFLINE", "last_ping": "18:40:00"}'
  },
  {
    id: "EVT-2026-090",
    eventType: "GPS_SPATIAL_OUTLIER",
    severity: "WARNING",
    status: "ACTIVE",
    assetName: "Clean Stove Device CS-892",
    assetId: "AST-STV-892",
    projectName: "Kano Clean Cooking Expansion",
    description: "Usage survey GPS coordinates deviate by 12.4 km from registered household boundary.",
    timestamp: "2026-08-09T17:15:20Z",
    trustScoreImpact: -8,
    payloadSnippet: '{"lat": 12.0021, "lng": 8.5920, "expected_lat": 11.8921, "expected_lng": 8.5120}'
  },
  {
    id: "EVT-2026-089",
    eventType: "CALIBRATION_DRIFT",
    severity: "WARNING",
    status: "ACKNOWLEDGED",
    assetName: "Lekki EV Fast Charger Station 02",
    assetId: "AST-EV-002",
    projectName: "Lagos Urban EV Corridor",
    description: "Meter power factor variance of +4.2% exceeds ISO 14064-3 calibration threshold.",
    timestamp: "2026-08-09T14:30:00Z",
    trustScoreImpact: -5,
    acknowledgedBy: "QA Officer Oluwaseun",
    acknowledgedAt: "2026-08-09T15:10:00Z",
    payloadSnippet: '{"power_factor": 0.992, "calibrated_baseline": 0.950, "variance": 0.042}'
  },
  {
    id: "EVT-2026-088",
    eventType: "DUPLICATE_PAYLOAD_PREVENTED",
    severity: "INFO",
    status: "RESOLVED",
    assetName: "Biochar Kiln Temperature Sensor 01",
    assetId: "AST-BIO-001",
    projectName: "Oyo Sustainable Biochar Removal",
    description: "Identical MQTT telemetry payload detected within 500ms; duplicate suppressed cleanly.",
    timestamp: "2026-08-09T11:05:12Z",
    trustScoreImpact: 0,
    acknowledgedBy: "System Auditor Bot",
    acknowledgedAt: "2026-08-09T11:05:15Z",
    payloadSnippet: '{"hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}'
  }
];

export function DataQualityEventConsole({
  events: initialEvents = DEFAULT_EVENTS,
  title = "Data Quality & Verification Event Stream",
  subtitle = "Real-time anomaly monitoring, automated trust score penalties, and audit trail resolution."
}: DataQualityEventConsoleProps) {
  const toast = useToast();
  const [eventList, setEventList] = useState<DataQualityEvent[]>(initialEvents);
  const [isLoading, setIsLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<DataQualityEvent | null>(null);

  // Fetch real anomaly events from backend
  const loadBackendAnomalies = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAnomalies();
      const realItems = res?.anomalies || (Array.isArray(res) ? res : []);
      if (realItems.length > 0) {
        const mapped: DataQualityEvent[] = realItems.map((item: any, idx: number) => ({
          id: item.id || `EVT-2026-${idx + 100}`,
          eventType: (item.flag_type || "DATA_QUALITY_ALERT").toUpperCase(),
          severity: (item.severity || "WARNING").toUpperCase() as EventSeverity,
          status: item.resolved ? "RESOLVED" : "ACTIVE",
          assetName: item.asset_name || item.property_name || "Monitored Asset",
          assetId: item.asset_id || item.activity_id || `AST-${idx}`,
          projectName: item.project_name || "Climate Project",
          description: item.description || "Data anomaly flagged by AI Trust Engine.",
          timestamp: item.created_at || new Date().toISOString(),
          trustScoreImpact: item.trust_score_impact || -10,
          payloadSnippet: item.raw_payload ? JSON.stringify(item.raw_payload) : undefined,
          acknowledgedBy: item.resolved_by || undefined,
          acknowledgedAt: item.resolved_at || undefined
        }));
        setEventList(mapped);
      }
    } catch (err) {
      console.error("Error loading backend anomalies:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadBackendAnomalies();
  }, []);

  // Filter logic
  const filteredEvents = useMemo(() => {
    return eventList.filter((e) => {
      if (severityFilter !== "ALL" && e.severity !== severityFilter) return false;
      if (statusFilter !== "ALL" && e.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        return (
          e.assetName.toLowerCase().includes(q) ||
          e.eventType.toLowerCase().includes(q) ||
          e.description.toLowerCase().includes(q) ||
          e.id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [eventList, severityFilter, statusFilter, searchQuery]);

  // Date Formatter Guard
  const formatDateSafe = (dateStr?: string, options?: Intl.DateTimeFormatOptions) => {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? "—" : d.toLocaleString([], options);
  };

  // Acknowledge Event
  const handleAcknowledge = async (id: string) => {
    try {
      await resolveAnomaly(id, "verify", "Acknowledged by Auditor");
      toast.success("Event Acknowledged", `Event ${id} assigned for technical review.`);
      setEventList((prev) =>
        prev.map((e) =>
          e.id === id
            ? {
                ...e,
                status: "ACKNOWLEDGED",
                acknowledgedBy: "Current Auditor / QA Officer",
                acknowledgedAt: new Date().toISOString()
              }
            : e
        )
      );
    } catch (err: any) {
      console.error("Failed to acknowledge event:", err);
      toast.error("Acknowledgement Failed", err?.message || `Could not commit acknowledgement for event ${id}.`);
    }
  };

  // Resolve Event
  const handleResolve = async (id: string) => {
    try {
      await resolveAnomaly(id, "verify", "Resolved by Auditor");
      toast.success("Event Resolved", `Data quality event ${id} marked as resolved.`);
      setEventList((prev) =>
        prev.map((e) =>
          e.id === id
            ? {
                ...e,
                status: "RESOLVED",
                acknowledgedBy: "Current Auditor / QA Officer",
                acknowledgedAt: new Date().toISOString()
              }
            : e
        )
      );
    } catch (err: any) {
      console.error("Failed to resolve event:", err);
      toast.error("Resolution Failed", err?.message || `Could not commit resolution for event ${id}.`);
    }
  };

  const getSeverityBadge = (sev: EventSeverity) => {
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-red-500/10 text-red-400 border border-red-500/20 flex items-center gap-1">
            <AlertTriangle size={11} /> CRITICAL
          </span>
        );
      case "WARNING":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
            <AlertCircle size={11} /> WARNING
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
            <Info size={11} /> INFO
          </span>
        );
    }
  };

  const getStatusBadge = (st: EventStatus) => {
    switch (st) {
      case "ACTIVE":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-red-500/10 text-red-400 border border-red-500/20">
            ACTIVE
          </span>
        );
      case "ACKNOWLEDGED":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
            ACKNOWLEDGED
          </span>
        );
      case "RESOLVED":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            RESOLVED
          </span>
        );
    }
  };

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/20">
              DATA QUALITY ALERTS
            </span>
          </div>
          <h2 className="text-sm font-extrabold text-[var(--color-text-primary)] uppercase tracking-wider mt-1">
            {title}
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            {subtitle}
          </p>
        </div>

        {/* STATS */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-bold flex items-center gap-1.5">
            <AlertTriangle size={13} />
            <span>{eventList.filter((e) => e.status === "ACTIVE").length} Active</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center gap-1.5">
            <ShieldCheck size={13} />
            <span>{eventList.filter((e) => e.status === "RESOLVED").length} Resolved</span>
          </div>
        </div>
      </div>

      {/* FILTER BAR */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter events by asset, type, or keyword..."
            className="w-full pl-9 pr-3 py-1.5 bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#00B47A]"
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="py-1.5 px-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"
          >
            <option value="ALL">Severity: All</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="py-1.5 px-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"
          >
            <option value="ALL">Status: All</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={loadBackendAnomalies}
            disabled={isLoading}
            className="p-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-white transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh Anomaly Stream"
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
        </div>
      </div>

      {/* EVENTS TABLE */}
      {filteredEvents.length === 0 ? (
        <div className="p-8 text-center bg-[var(--color-background)] rounded-xl border border-[var(--color-border)] space-y-2">
          <ShieldCheck size={28} className="text-emerald-400 mx-auto" />
          <p className="text-xs font-bold text-[var(--color-text-primary)]">No Matching Events Found</p>
          <p className="text-[11px] text-zinc-500">All data streams are operating cleanly within trust parameters.</p>
        </div>
      ) : (
        <div className="overflow-x-auto border border-[var(--color-border)] rounded-xl">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] bg-[var(--color-background)]/70">
                <th className="py-2.5 px-3">Event ID</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Asset / Project</th>
                <th className="py-2.5 px-3">Event Description</th>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {filteredEvents.map((e) => (
                <tr key={e.id} className="hover:bg-[var(--color-background)]/60 transition-colors">
                  <td className="py-3 px-3 font-mono font-bold text-[#00B47A]">
                    {e.id}
                  </td>
                  <td className="py-3 px-3">{getSeverityBadge(e.severity)}</td>
                  <td className="py-3 px-3">
                    <p className="font-bold text-[var(--color-text-primary)] truncate max-w-[180px]">{e.assetName}</p>
                    <p className="text-[10px] text-[var(--color-text-secondary)] truncate max-w-[180px]">{e.projectName}</p>
                  </td>
                  <td className="py-3 px-3 text-zinc-300 max-w-xs leading-relaxed">
                    {e.description}
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-zinc-400">
                    {formatDateSafe(e.timestamp, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="py-3 px-3">{getStatusBadge(e.status)}</td>
                  <td className="py-3 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setSelectedEvent(e)}
                        className="p-1.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-zinc-400 hover:text-white transition-colors cursor-pointer"
                        title="View Details"
                      >
                        <Eye size={13} />
                      </button>
                      {e.status === "ACTIVE" && (
                        <button
                          onClick={() => handleAcknowledge(e.id)}
                          className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 text-[10px] font-bold transition-all cursor-pointer"
                        >
                          Acknowledge
                        </button>
                      )}
                      {e.status !== "RESOLVED" && (
                        <button
                          onClick={() => handleResolve(e.id)}
                          className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 text-[10px] font-bold transition-all cursor-pointer"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* EVENT DETAIL MODAL */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-[#00B47A]" />
                <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Event Details: {selectedEvent.id}
                </h3>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-[var(--color-text-secondary)] hover:text-white">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between bg-[var(--color-background)] p-3 rounded-xl border border-[var(--color-border)]">
                <div>
                  <span className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase">Severity</span>
                  <div className="mt-0.5">{getSeverityBadge(selectedEvent.severity)}</div>
                </div>
                <div>
                  <span className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase">Status</span>
                  <div className="mt-0.5">{getStatusBadge(selectedEvent.status)}</div>
                </div>
                <div>
                  <span className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase">Trust Impact</span>
                  <p className="text-xs font-mono font-bold text-red-400 mt-0.5">{selectedEvent.trustScoreImpact} pts</p>
                </div>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Affected Asset</label>
                <p className="text-xs font-bold text-[var(--color-text-primary)] mt-0.5">{selectedEvent.assetName} ({selectedEvent.assetId})</p>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Project Context</label>
                <p className="text-xs font-semibold text-[var(--color-text-primary)] mt-0.5">{selectedEvent.projectName}</p>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Technical Findings</label>
                <p className="text-xs text-zinc-300 mt-0.5 leading-relaxed bg-[var(--color-background)] p-2.5 rounded-xl border border-[var(--color-border)]">
                  {selectedEvent.description}
                </p>
              </div>

              {selectedEvent.payloadSnippet && (
                <div>
                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Telemetry Payload Snippet</label>
                  <pre className="mt-1 p-2.5 rounded-xl bg-black/50 border border-[var(--color-border)] text-[10px] font-mono text-emerald-400 overflow-x-auto">
                    {selectedEvent.payloadSnippet}
                  </pre>
                </div>
              )}

              {selectedEvent.acknowledgedBy && (
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-mono text-emerald-400">
                  Reviewed by: {selectedEvent.acknowledgedBy} at {formatDateSafe(selectedEvent.acknowledgedAt)}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--color-border)]">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-xl bg-[var(--color-background)] text-[var(--color-text-secondary)] font-bold text-xs cursor-pointer"
              >
                Close
              </button>
              {selectedEvent.status !== "RESOLVED" && (
                <button
                  onClick={() => {
                    handleResolve(selectedEvent.id);
                    setSelectedEvent(null);
                  }}
                  className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 size={13} />
                  <span>Mark Resolved</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
