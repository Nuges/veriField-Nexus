"use client";

import { useEffect, useState } from "react";
import { ClipboardCheck, Plus, Filter, RefreshCw, Calendar, MapPin, User, Play, CheckCircle, XCircle, MoreVertical } from "lucide-react";
import { fetchAudits, updateAuditStatus } from "@/lib/api";

export default function AuditsPage() {
  const [audits, setAudits] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await fetchAudits();
      setAudits(res.audits);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStatusChange = async (auditId: string, newStatus: string) => {
    setUpdating(auditId);
    setOpenMenu(null);
    try {
      await updateAuditStatus(auditId, newStatus);
      await loadData();
    } catch (err) {
      console.error(err);
      alert("Failed to update audit status");
    } finally {
      setUpdating(null);
    }
  };

  return (
    <div className="space-y-6" onClick={() => setOpenMenu(null)}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Audit Tasks</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Assign and track manual audits for low-trust activities</p>
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
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20">
            <Plus size={18} /> New Audit Task
          </button>
        </div>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-100">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface)]">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Field Assignments</h2>
          <div className="text-xs font-medium text-[var(--color-text-secondary)] bg-[var(--color-background)] px-3 py-1 rounded-full border border-[var(--color-border)]">
            {audits.length} Tasks
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Property / Asset</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Assigned Agent</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Status</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Deadline</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading && audits.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--color-text-secondary)]">Fetching assigned tasks...</td>
                </tr>
              ) : audits.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-16 text-center">
                    <div className="flex flex-col items-center justify-center">
                      <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 border border-emerald-500/20">
                        <ClipboardCheck className="text-emerald-500" size={32} />
                      </div>
                      <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No pending audits</h3>
                      <p className="text-[var(--color-text-secondary)] mt-1">All audit tasks have been completed or none are assigned.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                audits.map((audit) => (
                  <tr key={audit.id} className="hover:bg-[var(--color-surface)] transition-colors group">
                    <td className="p-4">
                      <div className="font-medium text-[var(--color-text-primary)]">{audit.property_name || "Unknown Asset"}</div>
                      <div className="text-xs text-[var(--color-text-muted)] mt-1 flex items-center gap-1">
                        <MapPin size={12} /> {audit.property_address || "No address provided"}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center">
                          <User size={12} className="text-slate-400" />
                        </div>
                        <span className="text-sm font-medium text-[var(--color-text-primary)]">{audit.agent_name || "Unassigned"}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                        audit.status === "pending" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                        audit.status === "in_progress" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                        audit.status === "completed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                        "bg-red-500/10 text-red-400 border-red-500/20"
                      }`}>
                        {audit.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                        <Calendar size={14} />
                        {new Date(audit.deadline).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="relative inline-block">
                        {updating === audit.id ? (
                          <div className="p-2"><RefreshCw size={16} className="animate-spin text-emerald-400" /></div>
                        ) : (
                          <button
                            onClick={(e) => { e.stopPropagation(); setOpenMenu(openMenu === audit.id ? null : audit.id); }}
                            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors p-2 rounded-lg hover:bg-[var(--color-surface)]"
                          >
                            <MoreVertical size={18} />
                          </button>
                        )}
                        {openMenu === audit.id && (
                          <div
                            onClick={(e) => e.stopPropagation()}
                            className="absolute right-0 top-full mt-1 w-44 bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-xl z-20 py-1"
                          >
                            {audit.status === "pending" && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "in_progress")}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-blue-400 hover:bg-blue-500/10 transition-colors"
                              >
                                <Play size={14} /> Start Audit
                              </button>
                            )}
                            {(audit.status === "pending" || audit.status === "in_progress") && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "completed")}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                              >
                                <CheckCircle size={14} /> Mark Complete
                              </button>
                            )}
                            {audit.status !== "cancelled" && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "cancelled")}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                              >
                                <XCircle size={14} /> Cancel Task
                              </button>
                            )}
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
