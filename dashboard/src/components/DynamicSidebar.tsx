// =============================================================================

// VeriField Nexus — Enterprise Dynamic Sidebar Component (Level 5 CIOS)

// =============================================================================

// Standardized Enterprise Navigation Hierarchy following global ERP standards.

// Dynamic badges and role-based navigation sequence.

// Projects is the consolidated main entry point for both Projects and Asset Fleets.

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

  HelpCircle

} from "lucide-react";

import { useState, useEffect } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";

import { fetchActivities } from "@/lib/api";
import { getSectorTerminology } from "@/lib/moduleRegistry";



const ICON_MAP: Record<string, any> = {

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

  HelpCircle

};



interface WorkspaceNavItem {

  label: string;

  icon: string;

  href: string;

  badge?: string;

}



interface NavGroup {
  title: string;
  items: WorkspaceNavItem[];
}

export default function DynamicSidebar() {
  const pathname = usePathname();
  const { user, isSidebarCollapsed, setIsSidebarCollapsed, activeSector } = useWorkspace();
  const toggleSidebar = () => setIsSidebarCollapsed(!isSidebarCollapsed);
  const sectorTerms = getSectorTerminology(activeSector);
  const [flaggedCount, setFlaggedCount] = useState<number | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  // Fetch real-time activity counts from the database
  useEffect(() => {
    async function loadRealTimeCounts() {
      try {
        const res = await fetchActivities();
        const activities = Array.isArray(res) ? res : (res?.activities || []);
        if (activities.length > 0) {
          const flagged = activities.filter((a: any) =>
            a.trust_status === "REVIEW" || a.trust_status === "FLAGGED" || (a.trust_score !== undefined && a.trust_score < 80)
          ).length;
          const pending = activities.filter((a: any) =>
            a.verification_status === "PENDING" || a.trust_status === "REVIEW" || a.status === "audit"
          ).length;
          setFlaggedCount(flagged);
          setPendingCount(pending);
        }
      } catch (err) {
        console.error("Failed to load real-time sidebar badges", err);
      }
    }
    loadRealTimeCounts();
  }, []);

  const userRole = (user?.role || "ADMIN").toUpperCase();

  // Categorized Navigation Groups
  const getNavGroups = (): NavGroup[] => {
    if (userRole === "FIELD_AGENT") {
      return [
        {
          title: "Operations",
          items: [
            { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
            {
              label: "Field Operations",
              icon: "Radio",
              href: "/dashboard/operations",
              badge: flaggedCount !== null && flaggedCount > 0 ? `${flaggedCount}` : undefined
            },
            { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
          ]
        },
        {
          title: "Intelligence & Guides",
          items: [
            { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
            { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
            { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
          ]
        }
      ];
    }

    if (userRole === "AUDITOR" || userRole === "VVB" || userRole === "VERIFIER") {
      return [
        {
          title: "Operations",
          items: [
            { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
            { label: "Monitoring", icon: "Activity", href: "/dashboard/monitoring" },
          ]
        },
        {
          title: "MRV & Verification",
          items: [
            {
              label: "Verification",
              icon: "ShieldCheck",
              href: "/dashboard/verifications",
              badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount}` : undefined
            },
            { label: "Programmes (PoA)", icon: "Globe", href: "/dashboard/poa" },
            { label: "Carbon Ledger", icon: "Sliders", href: "/dashboard/carbon" },
            { label: "Compliance", icon: "Globe", href: "/dashboard/command-center" },
            { label: "MRV Reports", icon: "FileText", href: "/dashboard/analytics" },
          ]
        },
        {
          title: "Intelligence & Guides",
          items: [
            { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai" },
            { label: "Settings", icon: "Settings", href: "/dashboard/settings" },
            { label: "Help & Guides", icon: "HelpCircle", href: "/dashboard/help" },
          ]
        }
      ];
    }

    // Default & Admin-level categorized groups
    return [
      {
        title: "Operations",
        items: [
          { label: "Mission Control", icon: "LayoutDashboard", href: "/dashboard" },
          { label: sectorTerms.projectsNavLabel, icon: "Briefcase", href: "/dashboard/projects" },
          { label: "Programmes (PoA)", icon: "Globe", href: "/dashboard/poa" },
          {
            label: "Field Operations",
            icon: "Radio",
            href: "/dashboard/operations",
            badge: flaggedCount !== null && flaggedCount > 0 ? `${flaggedCount}` : undefined
          },
          { label: "Live Telemetry", icon: "Activity", href: "/dashboard/monitoring" },
        ]
      },
      {
        title: "MRV & Registry",
        items: [
          { label: "Methodology & PDD", icon: "Layers", href: "/dashboard/methodologies" },
          {
            label: "Verification & Audit",
            icon: "ShieldCheck",
            href: "/dashboard/verifications",
            badge: pendingCount !== null && pendingCount > 0 ? `${pendingCount}` : undefined
          },
          { label: "Carbon Ledger", icon: "Sliders", href: "/dashboard/carbon" },
          { label: "Compliance Center", icon: "Globe", href: "/dashboard/command-center" },
          { label: "Reports & Certificates", icon: "FileText", href: "/dashboard/analytics" },
        ]
      },
      {
        title: "Administration",
        items: [
          { label: "People & Access", icon: "Users", href: "/dashboard/people" },
          { label: "System Settings", icon: "Settings", href: "/dashboard/settings" },
        ]
      },
      {
        title: "Intelligence & Guides",
        items: [
          { label: "AI Assistant", icon: "Bot", href: "/dashboard/ai", badge: "Live" },
          { label: "Help & Knowledge", icon: "HelpCircle", href: "/dashboard/help" },
        ]
      }
    ];
  };

  const navGroups = getNavGroups();

  const getIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <>
      <aside
        className={`hidden md:flex flex-col bg-[var(--color-surface)] border-r border-[var(--color-border)] h-screen sticky top-0 transition-all duration-200 z-40 select-none ${
          isSidebarCollapsed ? "w-16" : "w-60"
        }`}
      >
        {/* Brand Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-[var(--color-border)] shrink-0">
          {!isSidebarCollapsed ? (
            <div className="flex items-center gap-2.5">
              <ThemeLogo className="h-6 w-auto object-contain" />
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <div className="w-7 h-7 rounded-md bg-[#008A5E] flex items-center justify-center text-white font-bold text-sm">
                V
              </div>
            </div>
          )}
        </div>

        {/* Navigation Categories */}
        <div className="flex-1 overflow-y-auto py-3 px-2 space-y-4 custom-scrollbar">
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {!isSidebarCollapsed && (
                <p className="px-2.5 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  {group.title}
                </p>
              )}
              {group.items.map((item, iIdx) => {
                const Icon = ICON_MAP[item.icon] || LayoutDashboard;
                const active = getIsActive(item.href);

                return (
                  <Link
                    key={iIdx}
                    href={item.href}
                    title={isSidebarCollapsed ? item.label : undefined}
                    className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg transition-colors text-xs ${
                      active
                        ? "bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E] dark:text-emerald-400 font-semibold border border-emerald-200/60 dark:border-emerald-800/40"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)] font-medium"
                    }`}
                  >
                    <Icon size={16} className={`shrink-0 ${active ? "text-[#008A5E] dark:text-emerald-400" : "text-[var(--color-text-secondary)]"}`} />
                    {!isSidebarCollapsed && (
                      <div className="flex items-center justify-between w-full min-w-0">
                        <span className="truncate">{item.label}</span>
                        {item.badge && (
                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full ${
                            active
                              ? "bg-[#008A5E] text-white"
                              : "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300"
                          }`}>
                            {item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer Workspace Context & User */}
        <div className="p-2.5 border-t border-[var(--color-border)] bg-[var(--color-surface)] shrink-0">
          {!isSidebarCollapsed ? (
            <div className="flex items-center justify-between px-1">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                  {user?.full_name || "Enterprise User"}
                </p>
                <p className="text-[10px] text-[var(--color-text-muted)] truncate font-mono uppercase">
                  {userRole.replace("_", " ")}
                </p>
              </div>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 dark:bg-emerald-950 text-[#008A5E] dark:text-emerald-300">
                CIOS
              </span>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-950 text-[#008A5E] text-[10px] font-bold flex items-center justify-center">
                {(user?.full_name || "U")[0].toUpperCase()}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
