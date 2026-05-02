// =============================================================================
// VeriField Nexus — Dashboard Overview Page
// =============================================================================
// Main dashboard with stat cards, daily submissions chart,
// and recent activity feed.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Users,
  Home,
  ShieldCheck,
  AlertTriangle,
  TrendingUp,
  Calendar,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import StatCard from "@/components/StatCard";
import TrustBadge from "@/components/TrustBadge";
import {
  fetchAnalyticsOverview,
  fetchTrends,
  setAuthToken,
} from "@/lib/api";
import type {
  AnalyticsOverview,
  AnalyticsTrends,
} from "@/lib/types";

// Trust distribution colors
const TRUST_COLORS = ["#10B981", "#F59E0B", "#EF4444", "#64748B"];

export default function DashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Restore auth token from localStorage
    const token = localStorage.getItem("vf_token");
    if (token) setAuthToken(token);

    loadData();
  }, []);

  async function loadData() {
    try {
      const [overviewData, trendsData] = await Promise.all([
        fetchAnalyticsOverview(),
        fetchTrends(30),
      ]);
      setOverview(overviewData);
      setTrends(trendsData);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
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

  // Prepare trust distribution data for pie chart
  const trustPieData = trends
    ? [
        { name: "High (80-100)", value: trends.trust_distribution.high },
        { name: "Medium (50-79)", value: trends.trust_distribution.medium },
        { name: "Low (0-49)", value: trends.trust_distribution.low },
        { name: "Unscored", value: trends.trust_distribution.unscored },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* --- Page Header --- */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
          Dashboard Overview
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Monitor field activity submissions and trust verification
        </p>
      </div>

      {/* --- Stat Cards Grid --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <StatCard
          title="Total Submissions"
          value={overview?.total_submissions ?? 0}
          icon={Activity}
          color="emerald"
        />
        <StatCard
          title="Field Agents"
          value={overview?.total_users ?? 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Avg Trust Score"
          value={
            overview?.avg_trust_score
              ? `${Math.round(overview.avg_trust_score)}/100`
              : "—"
          }
          icon={ShieldCheck}
          color="emerald"
        />
        <StatCard
          title="Flagged Activities"
          value={overview?.flagged_activities ?? 0}
          icon={AlertTriangle}
          color="red"
        />
      </div>

      {/* --- Charts Row --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Daily Submissions Chart */}
        <div className="lg:col-span-2 bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[var(--color-text-primary)] font-semibold">Daily Submissions</h3>
              <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">Last 30 days</p>
            </div>
            <TrendingUp size={18} className="text-emerald-400" />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trends?.daily_submissions ?? []}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="date"
                tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
                tickFormatter={(v) => v.split("-").slice(1).join("/")}
              />
              <YAxis tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "12px",
                  color: "var(--color-text-primary)",
                  fontSize: "13px",
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#10B981"
                strokeWidth={2}
                fill="url(#colorCount)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Trust Distribution Pie */}
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
          <h3 className="text-[var(--color-text-primary)] font-semibold mb-4">Trust Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={trustPieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {trustPieData.map((_, i) => (
                  <Cell key={i} fill={TRUST_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "12px",
                  color: "var(--color-text-primary)",
                  fontSize: "13px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="space-y-2 mt-2">
            {trustPieData.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: TRUST_COLORS[i] }}
                  />
                  <span className="text-[var(--color-text-secondary)]">{item.name}</span>
                </div>
                <span className="text-[var(--color-text-primary)] font-medium">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* --- Quick Stats --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 stagger-children">
        <StatCard
          title="Today's Submissions"
          value={overview?.submissions_today ?? 0}
          icon={Calendar}
          color="blue"
        />
        <StatCard
          title="This Week"
          value={overview?.submissions_this_week ?? 0}
          icon={TrendingUp}
          color="purple"
        />
        <StatCard
          title="Assets"
          value={overview?.total_properties ?? 0}
          icon={Home}
          color="amber"
        />
      </div>
    </div>
  );
}
