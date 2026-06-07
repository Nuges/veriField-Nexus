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
import { fetchAgentPerformance, setAuthToken, createAgent, updateAgentStatus } from "@/lib/api";
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
    } catch (err) {
      console.error("Failed to create agent", err);
      toast.error("Provisioning Failed", "Could not provision new agent. Please try again.");
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
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
        <h3 className="text-[var(--color-text-primary)] font-semibold mb-4">
          Top Agents by Submissions
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <defs>
              <linearGradient id="submissionsGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#059669" stopOpacity={0.2}/>
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
              cursor={{ fill: "rgba(255, 255, 255, 0.03)" }}
            />
            <Bar dataKey="submissions" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.suspicious ? "url(#suspiciousGradient)" : "url(#submissionsGradient)"}
                  stroke={entry.suspicious ? "#ef4444" : "#10b981"}
                  strokeWidth={1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Filters */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-wrap gap-4 items-center animate-fade-in-up">
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
              className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFilterSuspicious(!filterSuspicious)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all border ${
              filterSuspicious
                ? "bg-red-500/10 text-red-400 border-red-500/30 shadow-lg shadow-red-500/5"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20"
            }`}
          >
            <ShieldAlert size={14} />
            {filterSuspicious ? "Showing Suspicious" : "Show Suspicious Only"}
          </button>
          <button 
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-emerald-500 text-white hover:bg-emerald-600 hover:border-emerald-400 transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
          >
            <Plus size={14} />
            Add New Agent
          </button>
        </div>
      </div>

      {/* Agent Table */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="text-left p-4 text-[var(--color-text-secondary)] font-medium">Agent</th>
                <th className="text-left p-4 text-[var(--color-text-secondary)] font-medium">Role</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Submissions</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Avg Trust</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Flagged</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Flag Rate</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Status</th>
                <th className="text-center p-4 text-[var(--color-text-secondary)] font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="text-center py-12 text-[var(--color-text-muted)]"
                  >
                    <Users className="mx-auto mb-2" size={32} />
                    No agents found
                  </td>
                </tr>
              ) : (
                filtered.map((agent) => (
                  <tr
                    key={agent.id}
                    className={`border-b border-[var(--color-border)] hover:bg-[var(--color-surface)]/50 transition-colors ${
                      agent.suspicious ? "bg-red-500/10" : ""
                    }`}
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                            agent.suspicious
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          }`}
                        >
                          {agent.full_name?.[0] || "?"}
                        </div>
                        <div>
                          <p className="text-[var(--color-text-primary)] font-medium">
                            {agent.full_name || "Unknown"}
                          </p>
                          <p className="text-[var(--color-text-muted)] text-xs">
                            {agent.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {agent.role.replace("_", " ")}
                      </span>
                    </td>
                    <td className="p-4 text-center text-[var(--color-text-primary)] font-medium">
                      {agent.total_submissions}
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`font-bold ${
                          (agent.avg_trust_score ?? 0) >= 80
                            ? "text-emerald-400"
                            : (agent.avg_trust_score ?? 0) >= 50
                            ? "text-amber-400"
                            : "text-red-400"
                        }`}
                      >
                        {agent.avg_trust_score ?? "—"}
                      </span>
                    </td>
                    <td className="p-4 text-center text-red-400 font-medium">
                      {agent.flagged_count}
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`text-xs font-medium ${
                          agent.flag_rate > 20 ? "text-red-400" : "text-[var(--color-text-secondary)]"
                        }`}
                      >
                        {agent.flag_rate}%
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      {agent.status === "suspended" || agent.status === "revoked" ? (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/25">
                          <Ban size={10} />
                          {agent.status}
                        </div>
                      ) : agent.suspicious ? (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/25">
                          <AlertTriangle size={10} />
                          Suspicious
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                          <CheckCircle2 size={10} />
                          Clean
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-center gap-2">
                        {agent.status !== "active" ? (
                          <button 
                            onClick={() => handleStatusChange(agent.id, "active")}
                            className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors cursor-pointer"
                            title="Activate Agent"
                          >
                            <CheckCircle2 size={16} />
                          </button>
                        ) : (
                          <button 
                            onClick={() => handleStatusChange(agent.id, "suspended")}
                            className="p-1.5 text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors cursor-pointer"
                            title="Suspend Agent"
                          >
                            <Ban size={16} />
                          </button>
                        )}
                        <button 
                          onClick={() => handleStatusChange(agent.id, "revoked")}
                          className="p-1.5 text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer"
                          title="Revoke Access"
                        >
                          <X size={16} />
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl shadow-xl w-full max-w-md p-6 animate-scale-in">
            <div className="flex justify-between items-center mb-6 border-b border-[var(--color-border)] pb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                Provision New Agent
              </h3>
              <button 
                onClick={() => setIsAddModalOpen(false)} 
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
            
            <form onSubmit={handleAddAgent}>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                    Full Name
                  </label>
                  <input 
                    type="text" 
                    required 
                    placeholder="e.g. John Doe"
                    className="w-full text-xs bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 transition-colors"
                    value={newAgentName}
                    onChange={(e) => setNewAgentName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                    Email Address
                  </label>
                  <input 
                    type="email" 
                    required 
                    placeholder="johndoe@example.com"
                    className="w-full text-xs bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 transition-colors"
                    value={newAgentEmail}
                    onChange={(e) => setNewAgentEmail(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                    Temporary Password
                  </label>
                  <input 
                    type="password" 
                    required 
                    placeholder="••••••••"
                    className="w-full text-xs bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 transition-colors"
                    value={newAgentPassword}
                    onChange={(e) => setNewAgentPassword(e.target.value)}
                  />
                </div>
              </div>
              
              <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-[var(--color-border)]">
                <button 
                  type="button" 
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-emerald-500 hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? "Provisioning..." : "Provision Agent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
