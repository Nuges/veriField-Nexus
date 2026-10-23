// =============================================================================
// VeriField Nexus — Enterprise Dynamic Sidebar Component (Level 5 CIOS)
// =============================================================================
// Standardized Enterprise Navigation Hierarchy.
// Strictly segregated navigation tailored to each canonical role persona.
// Unknown roles fail closed to the least-privileged VIEWER workspace.
// =============================================================================

"use client";

import Link from "next/link";
import { ThemeLogo } from "@/components/common/ThemeLogo";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  Briefcase,
  Activity,
  Users,
  Settings,
  Globe,
  Sliders,
  Layers,
  ShieldCheck,
  Zap,
  Bot,
  FileText,
  HelpCircle,
  Lock,
  DollarSign,
  TrendingUp,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
  LucideIcon,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchActivities } from "@/lib/api";
import { getNavigationGroups } from "@/lib/navigation";
import { normalizeRole } from "@/lib/roles";

interface ActivityBadgeItem {
  trust_status?: string;
  trust_score?: number;
  verification_status?: string;
  status?: string;
}

const ICON_MAP: Record<string, LucideIcon> = {
  LayoutDashboard,
  Radio,
  Briefcase,
  Activity,
  Users,
  Settings,
  Globe,
  Sliders,
  Layers,
  ShieldCheck,
  Zap,
  Bot,
  FileText,
  HelpCircle,
  Lock,
  DollarSign,
  TrendingUp,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
};

export function DynamicSidebar({ mobileOpen = false, onNavigate }: { mobileOpen?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user } = useWorkspace();
  const [flaggedCount, setFlaggedCount] = useState<number | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  const canonicalRole = normalizeRole(user?.role);

  useEffect(() => {
    async function loadRealTimeCounts() {
      try {
        const res = await fetchActivities();
        const activities = Array.isArray(res) ? res : res?.activities || [];
        if (activities.length > 0) {
          const flagged = activities.filter(
            (a: ActivityBadgeItem) =>
              a.trust_status === "REVIEW" ||
              a.trust_status === "FLAGGED" ||
              (a.trust_score !== undefined && a.trust_score < 80)
          ).length;
          const pending = activities.filter(
            (a: ActivityBadgeItem) =>
              a.verification_status === "PENDING" ||
              a.trust_status === "REVIEW" ||
              a.status === "audit"
          ).length;
          setFlaggedCount(flagged);
          setPendingCount(pending);
        }
      } catch (err) {
        console.error("Failed to load real-time sidebar badges", err);
      }
    }
    if (["SUPER_ADMIN", "ORG_ADMIN", "PROJECT_MANAGER", "FIELD_SUPERVISOR", "FIELD_AGENT", "QA_OFFICER", "VERIFIER", "AUDITOR"].includes(canonicalRole)) loadRealTimeCounts();
  }, [canonicalRole]);

  // ─── Purpose-Built Navigation Per Canonical Persona ────────────────────────
  const navGroups = getNavigationGroups(user?.role, flaggedCount, pendingCount);

  const getIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <aside aria-label="Main navigation" className={`${mobileOpen ? "flex" : "hidden"} md:flex w-64 bg-[var(--color-surface)] border-r border-[var(--color-border)] flex flex-col h-screen fixed left-0 top-0 z-30 select-none shadow-sm transition-colors duration-200`}>
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-[var(--color-border)] gap-3 bg-[var(--color-surface)]">
        <ThemeLogo className="h-8 w-auto" />
      </div>

      {/* Scrollable Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5 scrollbar-thin scrollbar-thumb-[var(--color-border)]">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            <div className="px-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1.5 opacity-80">
              {group.title}
            </div>
            {group.items.map((item, iIdx) => {
              const Icon = ICON_MAP[item.icon] || LayoutDashboard;
              const active = getIsActive(item.href);

              return (
                <Link
                  key={iIdx}
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                    active
                      ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)] font-semibold border border-[var(--color-primary)]/20 shadow-xs"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className={`w-4 h-4 shrink-0 ${active ? "text-[var(--color-primary)]" : "text-[var(--color-text-secondary)]"}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                        item.badge === "Live"
                          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
                          : "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-[var(--color-border)] bg-[var(--color-background)] text-[11px] text-[var(--color-text-muted)]">
        <span>VeriField Nexus</span>
      </div>
    </aside>
  );
}

export default DynamicSidebar;


