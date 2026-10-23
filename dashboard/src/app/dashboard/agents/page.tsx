// =============================================================================
// VeriField Nexus — Agent Performance Dashboard
// =============================================================================
// Displays per-agent analytics: submission count, avg trust score,
// flagged count, and suspicious agent detection.
// =============================================================================

"use client";

import Link from "next/link";
import { useWorkspace } from "@/context/WorkspaceContext";
import { canPerformAction } from "@/lib/roles";
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
import { fetchAgentPerformance, setAuthToken } from "@/lib/api";
import type { AgentPerformanceResponse } from "@/lib/types";
import { useToast } from "@/components/Toast";


export default function AgentsPage() {
  const { user } = useWorkspace();
  const [data, setData] = useState<AgentPerformanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSuspicious, setFilterSuspicious] = useState(false);
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
          {canPerformAction("users:manage", user?.role) && <Link href="/dashboard/people" className="text-sm text-emerald-700">People & access</Link>}
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
                    <td className="p-4">{canPerformAction("users:manage", user?.role) ? <Link href="/dashboard/people" className="text-sm text-emerald-700">Manage access</Link> : "—"}</td>
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

