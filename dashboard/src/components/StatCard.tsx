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
    emerald: { bg: "bg-emerald-50 dark:bg-emerald-950/40", text: "text-[#008A5E] dark:text-emerald-400", icon: "text-[#008A5E]" },
    blue: { bg: "bg-blue-50 dark:bg-blue-950/40", text: "text-blue-600 dark:text-blue-400", icon: "text-blue-600" },
    amber: { bg: "bg-amber-50 dark:bg-amber-950/40", text: "text-amber-700 dark:text-amber-400", icon: "text-amber-600" },
    red: { bg: "bg-red-50 dark:bg-red-950/40", text: "text-red-600 dark:text-red-400", icon: "text-red-600" },
    purple: { bg: "bg-purple-50 dark:bg-purple-950/40", text: "text-purple-600 dark:text-purple-400", icon: "text-purple-600" },
  };

  const colors = colorMap[color] || colorMap.emerald;

  return (
    <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-lg p-4 transition-colors hover:border-slate-300 dark:hover:border-slate-700">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--color-text-secondary)] truncate">{title}</span>
        <div className={`w-8 h-8 rounded-md ${colors.bg} flex items-center justify-center shrink-0`}>
          <Icon size={16} className={colors.icon} />
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">{value}</p>
        {trend && (
          <span
            className={`text-[11px] font-semibold px-1.5 py-0.5 rounded ${
              trendUp
                ? "bg-emerald-50 dark:bg-emerald-950/50 text-[#008A5E] dark:text-emerald-400"
                : "bg-red-50 dark:bg-red-950/50 text-red-600 dark:text-red-400"
            }`}
          >
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
