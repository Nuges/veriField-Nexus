"use client";

import { useEffect, useState } from "react";
import { 
  ClipboardCheck, 
  Plus, 
  Filter, 
  RefreshCw, 
  Calendar, 
  MapPin, 
  User, 
  Play, 
  CheckCircle, 
  XCircle, 
  MoreVertical,
  Clock,
  ShieldAlert,
  Layers,
  ArrowRight
} from "lucide-react";
import { fetchAudits, updateAuditStatus, createAuditTask, fetchProperties, fetchAgentPerformance } from "@/lib/api";
import type { AuditTask } from "@/lib/api";
import type { Property, AgentPerformance } from "@/lib/types";
import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";

export default function AuditsPage() {
  const { activeSector, filterAudits, filterProperties } = useWorkspace();
  const toast = useToast();
  const [audits, setAudits] = useState<AuditTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  
  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [properties, setProperties] = useState<Property[]>([]);
  const [agents, setAgents] = useState<AgentPerformance[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    asset_id: "",
    assigned_agent: "",
    deadline: "",
  });

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [res, propsRes, agentsRes] = await Promise.all([
        fetchAudits(),
        fetchProperties(),
        fetchAgentPerformance()
      ]);
      const auditsWithProps = res.audits.map((a: AuditTask) => {
        const property = propsRes.properties.find((p: Property) => p.id === a.asset_id);
        const agent = agentsRes.agents?.find((ag: any) => ag.id === a.assigned_agent);
        return {
          ...a,
          property,
          property_address: property?.address,
          agent_name: agent?.full_name || agent?.name
        };
      });
      setAudits(auditsWithProps);
      setProperties(propsRes.properties);
      setAgents(agentsRes.agents || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    async function init() {
      try {
        const [res, propsRes, agentsRes] = await Promise.all([
          fetchAudits(),
          fetchProperties(),
          fetchAgentPerformance()
        ]);
        if (active) {
          const auditsWithProps = res.audits.map((a: AuditTask) => {
            const property = propsRes.properties.find((p: Property) => p.id === a.asset_id);
            const agent = agentsRes.agents?.find((ag: any) => ag.id === a.assigned_agent);
            return {
              ...a,
              property,
              property_address: property?.address,
              agent_name: agent?.full_name || agent?.name
            };
          });
          setAudits(auditsWithProps);
          setProperties(propsRes.properties);
          setAgents(agentsRes.agents || []);
          setIsLoading(false);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setIsLoading(false);
        }
      }
    }
    init();
    return () => {
      active = false;
    };
  }, []);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.asset_id || !formData.assigned_agent) {
      toast.warning("Missing Fields", "Please select both an asset and an agent.");
      return;
    }
    
    setIsSubmitting(true);
    try {
      await createAuditTask(formData);
      setShowModal(false);
      setFormData({ asset_id: "", assigned_agent: "", deadline: "" });
      toast.success("Audit Task Assigned", "The new MRV field task has been registered on the ledger.");
      await loadData();
    } catch (err) {
      console.error(err);
      toast.error("Assignment Failed", "Unable to commit the new audit to the ledger.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStatusChange = async (auditId: string, newStatus: string) => {
    setUpdating(auditId);
    setOpenMenu(null);
    try {
      await updateAuditStatus(auditId, newStatus);
      toast.success("Audit Status Saved", `Audit status has been transitioned to ${newStatus.replace("_", " ")}.`);
      await loadData();
    } catch (err) {
      console.error(err);
      toast.error("Failed Update", "Could not synchronize the audit state with the ledger.");
    } finally {
      setUpdating(null);
    }
  };

  const handleReassignAgent = async (auditId: string, agentId: string) => {
    setUpdating(auditId);
    setOpenMenu(null);
    try {
      await updateAuditStatus(auditId, undefined, undefined, agentId);
      toast.success("Agent Reassigned", "The manual audit task has been successfully routed to the new agent.");
      await loadData();
    } catch (err) {
      console.error(err);
      toast.error("Reassignment Failed", "Could not synchronize the new agent allocation with the ledger.");
    } finally {
      setUpdating(null);
    }
  };

  // Filter audits based on active workspace sector context
  const isolatedAudits = filterAudits(audits);

  // Derive dynamic counts for statistics strip
  const totalTasks = isolatedAudits.length;
  const inProgressTasks = isolatedAudits.filter(a => a.status === "in_progress").length;
  const completedTasks = isolatedAudits.filter(a => a.status === "completed").length;

  return (
    <div className="space-y-6 animate-fade-in-up" onClick={() => setOpenMenu(null)}>
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              Field Operations
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">
            Manual Audit Tasks
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Assign, schedule, and review manual field validations for low-trust telemetry outputs.
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
          
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#00B47A] text-white text-xs font-bold hover:bg-[#00B47A]/95 transition-all shadow-md shadow-[#00B47A]/20 active:scale-95 shrink-0"
          >
            <Plus size={15} /> Assign New Audit
          </button>
        </div>
      </div>

      {/* 📊 STATISTICS STRIP */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Active Assignments */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Active Assignments</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {isLoading ? "..." : totalTasks}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Scheduled manual check-ins</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <Layers size={18} />
          </div>
        </div>

        {/* Operational In-Progress */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">In Progress</p>
            <p className="text-2xl font-black text-blue-400 tracking-tight">
              {isLoading ? "..." : inProgressTasks}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Agents currently in the field</p>
          </div>
          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
            <Clock size={18} />
          </div>
        </div>

        {/* Resolved Audits */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Completed Tasks</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {isLoading ? "..." : completedTasks}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Verified field completions</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-purple-500 group-hover:text-white transition-all duration-300">
            <CheckCircle size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 ASSIGNMENT LEDGER */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
          <h2 className="text-xs font-bold uppercase tracking-wider">Active Assignment Roster</h2>
          <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
            {isolatedAudits.length} Registered Tasks
          </div>
        </div>
        
        <div className="overflow-x-auto pb-24">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
                  {activeSector === "cookstove" ? "Target Asset / Cookstove" :
                   "Target Asset / Energy System"}
                </th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Assigned Agent</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Ledger Status</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Scheduled Deadline</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]/70">
              {isLoading && audits.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                      <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Synchronizing audit allocations...</p>
                    </div>
                  </td>
                </tr>
              ) : isolatedAudits.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-16 text-center">
                    <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                      <div className="w-12 h-12 rounded-full bg-[#00B47A]/10 flex items-center justify-center mb-3 border border-[#00B47A]/15 text-[#00B47A]">
                        <ClipboardCheck size={22} />
                      </div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">All clear on Audits</h3>
                      <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                        All audit queries are closed. There are currently no pending tasks requiring manual verification.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                isolatedAudits.map((audit) => (
                  <tr key={audit.id} className="hover:bg-[var(--color-background)]/20 transition-colors group">
                    
                    {/* Target Cookstove */}
                    <td className="p-4">
                      <div className="font-bold text-xs text-[var(--color-text-primary)] group-hover:text-[#00B47A] transition-colors">
                        {audit.property?.name || "Unknown Asset Spec"}
                      </div>
                      <div className="text-[10px] text-[var(--color-text-secondary)] mt-1.5 flex items-center gap-1.5 font-medium">
                        <MapPin size={12} className="text-[#00B47A]" /> 
                        <span>{audit.property_address || "No precise address was registered."}</span>
                      </div>
                    </td>

                    {/* Agent Profile */}
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-[#00B47A]/10 border border-[#00B47A]/15 text-[#00B47A] flex items-center justify-center">
                          <User size={11} />
                        </div>
                        <span className="text-xs font-semibold text-[var(--color-text-primary)]">
                          {audit.agent_name || "Unallocated"}
                        </span>
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-[9px] font-extrabold uppercase tracking-wider border ${
                        audit.status === "pending" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                        audit.status === "in_progress" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                        audit.status === "completed" ? "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20" :
                        "bg-red-500/10 text-red-400 border-red-500/20"
                      }`}>
                        {audit.status.replace("_", " ")}
                      </span>
                    </td>

                    {/* Date Deadline */}
                    <td className="p-4">
                      <div className="flex items-center gap-2 text-xs font-mono font-medium text-[var(--color-text-secondary)]">
                        <Calendar size={13} className="text-[#00B47A]" />
                        {audit.deadline ? new Date(audit.deadline).toLocaleDateString() : "Open Schedule"}
                      </div>
                    </td>

                    {/* Options Drawer */}
                    <td className="p-4 text-right">
                      <div className="relative inline-block text-left">
                        {updating === audit.id ? (
                          <div className="p-1.5"><RefreshCw size={14} className="animate-spin text-[#00B47A]" /></div>
                        ) : (
                          <button
                            onClick={(e) => { e.stopPropagation(); setOpenMenu(openMenu === audit.id ? null : audit.id); }}
                            className="text-[var(--color-text-secondary)] hover:text-[#00B47A] transition-colors p-1.5 rounded-lg hover:bg-[var(--color-surface)] border border-transparent hover:border-[var(--color-border)]"
                          >
                            <MoreVertical size={16} />
                          </button>
                        )}
                        
                        {openMenu === audit.id && (
                          <div
                            onClick={(e) => e.stopPropagation()}
                            className={`absolute right-0 w-44 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-xl z-50 py-1.5 animate-fade-in text-left overflow-hidden ${
                              audits.indexOf(audit) === audits.length - 1 ? "bottom-full mb-1" : "top-full mt-1"
                            }`}
                          >
                            {audit.status === "pending" && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "in_progress")}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-bold text-blue-400 hover:bg-blue-500/5 transition-colors border-b border-[var(--color-border)]/40"
                              >
                                <Play size={13} /> Deploy Agent
                              </button>
                            )}
                            {(audit.status === "pending" || audit.status === "in_progress") && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "completed")}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-bold text-[#00B47A] hover:bg-[#00B47A]/5 transition-colors border-b border-[var(--color-border)]/40"
                              >
                                <CheckCircle size={13} /> Complete Audit
                              </button>
                            )}
                            {audit.status !== "cancelled" && (
                              <button
                                onClick={() => handleStatusChange(audit.id, "cancelled")}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-bold text-red-400 hover:bg-red-500/5 transition-colors border-b border-[var(--color-border)]/40"
                              >
                                <XCircle size={13} /> Cancel Assignment
                              </button>
                            )}
                            {(audit.status === "pending" || audit.status === "in_progress") && (
                              <div className="px-3 py-2 bg-[var(--color-background)]/10">
                                <p className="text-[9px] uppercase tracking-wider font-extrabold text-[var(--color-text-muted)] mb-1">
                                  Reassign Agent
                                </p>
                                <select
                                  value={audit.assigned_agent || ""}
                                  onChange={async (e) => {
                                    const newAgentId = e.target.value;
                                    if (!newAgentId) return;
                                    await handleReassignAgent(audit.id, newAgentId);
                                  }}
                                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] font-bold rounded-lg px-1.5 py-1 text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] cursor-pointer"
                                >
                                  <option value="">Choose Agent...</option>
                                  {agents.map(a => (
                                    <option key={a.id} value={a.id}>{a.full_name}</option>
                                  ))}
                                </select>
                              </div>
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

      {/* 🧭 NEW AUDIT TASK MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div 
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-md shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
              <div className="flex items-center gap-2">
                <ClipboardCheck size={16} className="text-[#00B47A]" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Assign New Audit Task</h3>
              </div>
              
              <button 
                onClick={() => setShowModal(false)}
                className="text-[var(--color-text-secondary)] hover:text-red-500 transition-colors p-1 rounded-lg hover:bg-[var(--color-surface)] border border-transparent hover:border-[var(--color-border)]"
              >
                <XCircle size={16} />
              </button>
            </div>
            
            {/* Modal Form */}
            <form onSubmit={handleCreateTask} className="p-4.5 space-y-4">
              
              <div>
                <label className="block text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
                  {activeSector === "cookstove" ? "Target Clean Cookstove Spec" :
                   activeSector ? `Target ${activeSector} Spec` : "Target Asset Spec"}
                </label>
                <select 
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text-primary)] outline-none focus:border-[#00B47A]/50 transition-all font-semibold"
                  value={formData.asset_id}
                  onChange={(e) => setFormData({...formData, asset_id: e.target.value})}
                  required
                >
                  <option value="">Select monitored asset...</option>
                  {filterProperties(properties).map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({p.address || "Unspecified"})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
                  Field Agent Assignment
                </label>
                <select 
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text-primary)] outline-none focus:border-[#00B47A]/50 transition-all font-semibold"
                  value={formData.assigned_agent}
                  onChange={(e) => setFormData({...formData, assigned_agent: e.target.value})}
                  required
                >
                  <option value="">Select registered agent...</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.full_name || a.email}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
                  Submission Deadline
                </label>
                <input 
                  type="date"
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text-primary)] outline-none focus:border-[#00B47A]/50 transition-all font-semibold"
                  value={formData.deadline}
                  onChange={(e) => setFormData({...formData, deadline: e.target.value})}
                />
              </div>

              <div className="pt-3.5 border-t border-[var(--color-border)]/40 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-background)] transition-all uppercase tracking-wider"
                >
                  Discard
                </button>
                
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-[#00B47A] text-white hover:bg-[#00B47A]/95 transition-all shadow-md shadow-[#00B47A]/25 disabled:opacity-50 flex items-center gap-2 uppercase tracking-wider"
                >
                  {isSubmitting ? <RefreshCw size={14} className="animate-spin" /> : null}
                  Commit Assignment
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
