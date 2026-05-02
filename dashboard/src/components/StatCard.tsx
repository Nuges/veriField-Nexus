// =============================================================================
// VeriField Nexus — Stat Card Component
// =============================================================================
// Animated stat card with icon, value, and trend indicator.
// =============================================================================

import { type ReactNode } from "react";
import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  color?: string; // Tailwind color class
}

export default function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  color = "emerald",
}: StatCardProps) {
  const colorMap: Record<string, { bg: string; text: string; icon: string }> = {
    emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", icon: "text-emerald-500" },
    blue: { bg: "bg-blue-500/10", text: "text-blue-400", icon: "text-blue-500" },
    amber: { bg: "bg-amber-500/10", text: "text-amber-400", icon: "text-amber-500" },
    red: { bg: "bg-red-500/10", text: "text-red-400", icon: "text-red-500" },
    purple: { bg: "bg-purple-500/10", text: "text-purple-400", icon: "text-purple-500" },
  };

  const colors = colorMap[color] || colorMap.emerald;

  return (
    <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 hover:border-[#475569] transition-all duration-300">
      <div className="flex items-start justify-between">
        {/* Icon container */}
        <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center`}>
          <Icon size={20} className={colors.icon} />
        </div>

        {/* Trend indicator */}
        {trend && (
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-lg ${
              trendUp
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400"
            }`}
          >
            {trend}
          </span>
        )}
      </div>

      {/* Value */}
      <div className="mt-4">
        <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">{value}</p>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">{title}</p>
      </div>
    </div>
  );
}
