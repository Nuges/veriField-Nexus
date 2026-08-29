// =============================================================================
// VeriField Nexus — Agent Performance Dashboard
// =============================================================================
// Displays per-agent analytics: submission count, avg trust score,
// flagged count, and suspicious agent detection.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import {
  Users,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  Search,
  Plus,
  ShieldAlert,
  CheckCircle2,
  Ban,
  X,
  Key,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import StatCard from "@/components/StatCard";
import { fetchAgentPerformance, setAuthToken, createAgent, updateAgentStatus, resetAgentPassword } from "@/lib/api";
import type { AgentPerformance, AgentPerformanceResponse } from "@/lib/types";
import { useToast } from "@/components/Toast";


export default function AgentsPage() {
  const toast = useToast();
  const [data, setData] = useState<AgentPerformanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSuspicious, setFilterSuspicious] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newAgentEmail, setNewAgentEmail] = useState("");
  const [newAgentName, setNewAgentName] = useState("");
  const [newAgentPassword, setNewAgentPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Password reset states
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [resetAgent, setResetAgent] = useState<AgentPerformance | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [isResetting, setIsResetting] = useState(false);

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    if (!resetAgent) return;
    if (resetPasswordValue.length < 8) {
      toast.error("Validation Error", "Password must be at least 8 characters long.");
      return;
    }
    setIsResetting(true);
    try {
      await resetAgentPassword(resetAgent.id, resetPasswordValue);
      toast.success("Password Reset", `Password for agent ${resetAgent.full_name} has been successfully updated.`);
      setIsResetModalOpen(false);
      setResetAgent(null);
      setResetPasswordValue("");
    } catch (err: any) {
      console.error("Failed to reset password", err);
      toast.error("Reset Failed", err.message || "Could not reset agent password. Please try again.");
    } finally {
      setIsResetting(false);
    }
  }


  useEffect(() => {
    const token = localStorage.getItem("vf_token");
    if (token) setAuthToken(token);
    loadData();
  }, []);

  async function loadData() {
    try {
      const result = await fetchAgentPerformance();
      setData(result);
    } catch (err) {
      console.error("Failed to load agent data:", err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleStatusChange(userId: string, status: "active" | "suspended" | "revoked") {
    try {
      await updateAgentStatus(userId, status);
      toast.success("Status Updated", `Agent status successfully set to ${status}.`);
      await loadData();
    } catch (err) {
      console.error("Failed to update status", err);
      toast.error("Update Failed", "Could not update agent status.");
    }
  }

  async function handleAddAgent(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await createAgent({
        email: newAgentEmail,
        password: newAgentPassword,
        full_name: newAgentName,
        role: "field_agent"
      });
      setIsAddModalOpen(false);
      setNewAgentName("");
      setNewAgentEmail("");
      setNewAgentPassword("");
      toast.success("Agent Provisioned", `Field agent ${newAgentName} has been successfully provisioned.`);
      await loadData();
    } catch (err: any) {
      console.error("Failed to create agent", err);
      toast.error("Provisioning Failed", err.message || "Could not provision new agent. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const agents = data?.agents ?? [];
  const filtered = agents.filter((a) => {
    const matchesSearch =
      !searchQuery ||
      a.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.email?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSuspicious = !filterSuspicious || a.suspicious;
    return matchesSearch && matchesSuspicious;
  });

  // Chart data: top 10 agents by submission count
  const chartData = [...agents]
    .sort((a, b) => b.total_submissions - a.total_submissions)
    .slice(0, 10)
    .map((a) => ({
      name: a.full_name?.split(" ")[0] || "Agent",
      submissions: a.total_submissions,
      trust: a.avg_trust_score ?? 0,
      suspicious: a.suspicious,
    }));

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
          Agent Performance
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Monitor field agent activity, trust scores, and flag suspicious behavior
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <StatCard
          title="Total Agents"
          value={data?.total_agents ?? 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Suspicious Agents"
          value={data?.suspicious_count ?? 0}
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          title="Avg Trust Score"
          value={
            agents.filter((a) => a.avg_trust_score !== null).length > 0
              ? `${Math.round(agents.reduce((sum, a) => sum + (a.avg_trust_score ?? 0), 0) / agents.filter((a) => a.avg_trust_score !== null).length)}/100`
              : "—"
          }
          icon={ShieldCheck}
          color="emerald"
        />
        <StatCard
          title="Total Submissions"
          value={agents.reduce((sum, a) => sum + a.total_submissions, 0)}
          icon={TrendingUp}
          color="purple"
        />
      </div>

      {/* Chart: Top Agents by Submissions */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs animate-fade-in-up">
        <h3 className="text-[var(--color-text-primary)] font-bold text-sm mb-4">
          Top Agents by Submissions
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <defs>
              <linearGradient id="submissionsGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#008A5E" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#005A3E" stopOpacity={0.2}/>
              </linearGradient>
              <linearGradient id="suspiciousGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#b91c1c" stopOpacity={0.2}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
              axisLine={{ stroke: "var(--color-border)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
              axisLine={{ stroke: "var(--color-border)" }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "12px",
                color: "var(--color-text-primary)",
                fontSize: "13px",
              }}
              cursor={{ fill: "rgba(0, 0, 0, 0.04)" }}
            />
            <Bar dataKey="submissions" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.suspicious ? "url(#suspiciousGradient)" : "url(#submissionsGradient)"}
                  stroke={entry.suspicious ? "#ef4444" : "#008A5E"}
                  strokeWidth={1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Filters */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-wrap gap-4 items-center shadow-xs animate-fade-in-up">
        <div className="flex items-center gap-2 flex-1 min-w-[250px]">
          <div className="relative w-full">
            <Search
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
              size={16}
            />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] transition-colors"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFilterSuspicious(!filterSuspicious)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all border cursor-pointer ${
              filterSuspicious
                ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700 shadow-xs"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            <ShieldAlert size={14} />
            {filterSuspicious ? "Showing Suspicious" : "Show Suspicious Only"}
          </button>
          <button 
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-[#008A5E] hover:bg-[#00734E] text-white transition-all shadow-xs cursor-pointer"
          >
            <Plus size={14} />
            Add New Agent
          </button>
        </div>
      </div>

      {/* Agent Table */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs animate-fade-in-up">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] text-xs uppercase tracking-wider">
                <th className="text-left p-4 font-bold">Agent</th>
                <th className="text-left p-4 font-bold">Role</th>
                <th className="text-center p-4 font-bold">Submissions</th>
                <th className="text-center p-4 font-bold">Avg Trust</th>
                <th className="text-center p-4 font-bold">Flagged</th>
                <th className="text-center p-4 font-bold">Flag Rate</th>
                <th className="text-center p-4 font-bold">Status</th>
                <th className="text-center p-4 font-bold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="text-center py-12 text-[var(--color-text-muted)] text-xs"
                  >
                    <Users className="mx-auto mb-2 text-[var(--color-text-muted)]" size={32} />
                    No agents match your filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((agent) => (
                  <tr
                    key={agent.id}
                    className={`hover:bg-[var(--color-surface-subtle)] transition-colors ${
                      agent.suspicious ? "bg-red-50/50 dark:bg-red-950/20" : ""
                    }`}
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${
                            agent.suspicious
                              ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-700"
                              : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
                          }`}
                        >
                          {agent.full_name?.[0] || "?"}
                        </div>
                        <div>
                          <p className="text-[var(--color-text-primary)] font-bold text-xs">
                            {agent.full_name || "Unknown"}
                          </p>
                          <p className="text-[var(--color-text-secondary)] font-mono text-[11px]">
                            {agent.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                        {agent.role.replace("_", " ")}
                      </span>
                    </td>
                    <td className="p-4 text-center text-[var(--color-text-primary)] font-bold text-xs">
                      {agent.total_submissions}
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`font-bold text-xs ${
                          (agent.avg_trust_score ?? 0) >= 80
                            ? "text-emerald-800 dark:text-emerald-300"
                            : (agent.avg_trust_score ?? 0) >= 50
                            ? "text-amber-800 dark:text-amber-300"
                            : "text-red-800 dark:text-red-300"
                        }`}
                      >
                        {agent.avg_trust_score ?? "—"}
                      </span>
                    </td>
                    <td className="p-4 text-center text-red-800 dark:text-red-300 font-bold text-xs">
                      {agent.flagged_count}
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`text-xs font-bold ${
                          agent.flag_rate > 20 ? "text-red-800 dark:text-red-300" : "text-[var(--color-text-secondary)]"
                        }`}
                      >
                        {agent.flag_rate}%
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      {agent.status === "suspended" || agent.status === "revoked" ? (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-700">
                          <Ban size={10} />
                          {agent.status}
                        </div>
                      ) : agent.suspicious ? (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                          <AlertTriangle size={10} />
                          Suspicious
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                          <CheckCircle2 size={10} />
                          Clean
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-center gap-1.5">
                        {agent.status !== "active" ? (
                          <button 
                            onClick={() => handleStatusChange(agent.id, "active")}
                            className="p-1.5 text-emerald-800 dark:text-emerald-300 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 rounded-lg border border-emerald-300 dark:border-emerald-700 transition-colors cursor-pointer"
                            title="Activate Agent"
                          >
                            <CheckCircle2 size={14} />
                          </button>
                        ) : (
                          <button 
                            onClick={() => handleStatusChange(agent.id, "suspended")}
                            className="p-1.5 text-amber-800 dark:text-amber-300 bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 rounded-lg border border-amber-300 dark:border-amber-700 transition-colors cursor-pointer"
                            title="Suspend Agent"
                          >
                            <Ban size={14} />
                          </button>
                        )}
                        <button 
                          onClick={() => handleStatusChange(agent.id, "revoked")}
                          className="p-1.5 text-rose-800 dark:text-rose-300 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 rounded-lg border border-rose-300 dark:border-rose-700 transition-colors cursor-pointer"
                          title="Revoke Access"
                        >
                          <X size={14} />
                        </button>
                        <button 
                          onClick={() => {
                            setResetAgent(agent);
                            setResetPasswordValue("");
                            setIsResetModalOpen(true);
                          }}
                          className="p-1.5 text-purple-800 dark:text-purple-300 bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 rounded-lg border border-purple-300 dark:border-purple-700 transition-colors cursor-pointer"
                          title="Reset Agent Password"
                        >
                          <Key size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Agent Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-xl w-full max-w-md p-6 animate-scale-in">
            <div className="flex justify-between items-center mb-5 border-b border-[var(--color-border)] pb-3">
              <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                Provision New Agent
              </h3>
              <button 
                onClick={() => setIsAddModalOpen(false)} 
                className="p-1 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            
            <form onSubmit={handleAddAgent} className="space-y-4 text-xs">
              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Full Name *
                </label>
                <input 
                  type="text" 
                  required 
                  placeholder="e.g. John Doe"
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-2.5 text-xs text-[var(--color-text-primary)] font-semibold placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] shadow-xs"
                  value={newAgentName}
                  onChange={(e) => setNewAgentName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Email Address *
                </label>
                <input 
                  type="email" 
                  required 
                  placeholder="johndoe@example.com"
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-2.5 text-xs text-[var(--color-text-primary)] font-mono placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] shadow-xs"
                  value={newAgentEmail}
                  onChange={(e) => setNewAgentEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Temporary Password *
                </label>
                <input 
                  type="password" 
                  required 
                  minLength={8}
                  placeholder="Minimum 8 characters"
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-2.5 text-xs text-[var(--color-text-primary)] font-mono placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] shadow-xs"
                  value={newAgentPassword}
                  onChange={(e) => setNewAgentPassword(e.target.value)}
                />
              </div>
              
              <div className="pt-3 flex justify-end gap-2 border-t border-[var(--color-border)]">
                <button 
                  type="button" 
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer shadow-xs"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#008A5E] hover:bg-[#00734E] transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
                >
                  {isSubmitting ? "Provisioning..." : "Provision Agent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Agent Password Modal */}
      {isResetModalOpen && resetAgent && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-xl w-full max-w-md p-6 animate-scale-in">
            <div className="flex justify-between items-center mb-5 border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center gap-2">
                <Key className="text-purple-800 dark:text-purple-300" size={18} />
                <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Reset Agent Password
                </h3>
              </div>
              <button 
                onClick={() => {
                  setIsResetModalOpen(false);
                  setResetAgent(null);
                }} 
                className="p-1 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            
            <form onSubmit={handleResetPassword} className="space-y-4 text-xs">
              <div className="p-3 bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl space-y-1">
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Agent: <strong className="text-[var(--color-text-primary)]">{resetAgent.full_name}</strong>
                </p>
                <p className="text-xs text-[var(--color-text-secondary)] font-mono">
                  Email: {resetAgent.email}
                </p>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  New Password *
                </label>
                <input 
                  type="password" 
                  required 
                  minLength={8}
                  placeholder="Enter new agent password (min 8 chars)"
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-2.5 text-xs text-[var(--color-text-primary)] font-mono placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] shadow-xs"
                  value={resetPasswordValue}
                  onChange={(e) => setResetPasswordValue(e.target.value)}
                />
              </div>
              
              <div className="pt-3 flex justify-end gap-2 border-t border-[var(--color-border)]">
                <button 
                  type="button" 
                  onClick={() => {
                    setIsResetModalOpen(false);
                    setResetAgent(null);
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer shadow-xs"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isResetting}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#008A5E] hover:bg-[#00734E] transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
                >
                  {isResetting ? "Resetting..." : "Reset Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

