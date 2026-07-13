"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function TopTabs() {
  const pathname = usePathname();
  const { activeSector, user } = useWorkspace();
  
  const roleStr = user?.role || "";

  // Define the secondary navigation tabs dynamically based on role
  const TAB_GROUPS: Record<string, any[]> = {
    overview: [
      { href: "/dashboard", label: "Dashboard" },
    ],
    field_assets: [
      { href: "/dashboard/properties", label: "Assets" },
      { href: "/dashboard/activities", label: "Activities" },
      { href: "/dashboard/map", label: "Map View" },
    ],
    verification: [
      { href: "/dashboard/audits", label: "Pending Audits" },
      { href: "/dashboard/anomalies", label: "Anomalies" },
      { href: "/dashboard/verifications", label: "Cross-Checks" },
      { href: "/dashboard/trust-scores", label: "Trust Scores" },
      { href: "/dashboard/community", label: "Community" },
    ],
    carbon: [
      { href: "/dashboard/carbon", label: "Carbon Ledger" },
      { href: "/dashboard/registry", label: "Registry Export" },
    ],
    settings: [
      { href: "/dashboard/settings", label: "General Settings" },
    ],
  };

  // Only project developers (admins) and platform operators manage field agents
  if (["admin", "ORG_ADMIN", "SUPER_ADMIN"].includes(roleStr)) {
    TAB_GROUPS.settings.push({ href: "/dashboard/agents", label: "Team & Agents" });
  }
  
  // Find which group the current route belongs to
  let activeGroup = null;
  for (const group of Object.values(TAB_GROUPS)) {
    // Check if current path matches any tab's href exactly, or if it's a sub-route
    // Exception: /dashboard is a prefix for everything, so handle it carefully
    if (group.some(tab => {
        if (!pathname) return false;
        if (tab.href === "/dashboard") return pathname === "/dashboard";
        return pathname === tab.href || pathname.startsWith(tab.href + "/");
    })) {
      activeGroup = group;
      break;
    }
  }

  // If no group is found or the group only has 1 item, don't render tabs
  if (!activeGroup || activeGroup.length <= 1) return null;

  return (
    <div className="flex items-center gap-2 mb-6 border-b border-[var(--color-border)] overflow-x-auto custom-scrollbar pb-px">
      {activeGroup.map(tab => {
        const isActive = pathname ? (pathname === tab.href || (tab.href !== "/dashboard" && pathname.startsWith(tab.href + "/"))) : false;
        return (
          <Link
            key={tab.href}
            href={`${tab.href}?workspace=${activeSector}`}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              isActive 
                ? "border-emerald-500 text-emerald-700 dark:text-emerald-400 bg-emerald-500/5 rounded-t-lg" 
                : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface)] rounded-t-lg"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
