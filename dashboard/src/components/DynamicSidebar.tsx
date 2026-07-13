// =============================================================================
// VeriField Nexus — Dynamic Sidebar Component (Level 5 CIOS)
// =============================================================================
// This sidebar dynamically fetches its navigation items and layout from
// the backend based on the active workspace and its configured methodology.
// =============================================================================

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  ShieldCheck,
  Zap,
  FileText,
  Settings,
  Users,
  LayoutDashboard
} from "lucide-react";
import { useState, useEffect } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";

const ICON_MAP: Record<string, any> = {
  Home,
  ShieldCheck,
  Zap,
  FileText,
  Settings,
  Users,
  LayoutDashboard
};

interface NavItem {
  label: string;
  icon: string;
  href: string;
}

export default function DynamicSidebar() {
  const pathname = usePathname();
  const { user, isSidebarCollapsed } = useWorkspace();
  const [navItems, setNavItems] = useState<NavItem[]>([]);

  useEffect(() => {
    // In a full implementation, this fetches from /api/v2/workspaces/{id}/ui
    // For now, we mock the fetch or use a generic default if no workspace is selected
    // Let's assume a generic universal dashboard entry point.
    setNavItems([
      { label: "Overview", icon: "Home", href: "/dashboard" },
      { label: "Telemetry", icon: "Zap", href: "/dashboard/telemetry" },
      { label: "Evidence", icon: "FileText", href: "/dashboard/evidence" },
      { label: "Verification", icon: "ShieldCheck", href: "/dashboard/verification" },
    ]);
  }, []);

  const getIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <>
      <aside
        className={`hidden md:flex flex-col bg-[#FAFAFA] dark:bg-[var(--color-surface)] border-r border-[var(--color-border)] h-screen sticky top-0 transition-all duration-300 z-50 ${
          isSidebarCollapsed ? "w-20" : "w-64"
        }`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-[var(--color-border)]">
          {!isSidebarCollapsed && (
            <div className="flex items-center gap-2">
              <img
                src="/logo-black.png"
                alt="VeriField Nexus"
                className="h-8 w-auto object-contain block dark:hidden"
              />
              <img
                src="/logo-green.png"
                alt="VeriField Nexus"
                className="h-8 w-auto object-contain hidden dark:block"
              />
            </div>
          )}
          {isSidebarCollapsed && (
            <div className="w-full flex justify-center">
              <div className="w-8 h-8 rounded-lg bg-[#00B47A]/10 flex items-center justify-center border border-[#00B47A]/20">
                <span className="text-[#00B47A] font-bold text-lg leading-none">V</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-3 custom-scrollbar flex flex-col gap-1">
          {navItems.map((item, idx) => {
            const Icon = ICON_MAP[item.icon] || Home;
            const active = getIsActive(item.href);
            return (
              <Link
                key={idx}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                  active
                    ? "bg-[#00B47A]/10 text-[#00B47A] font-semibold dark:bg-[#00B47A]/20"
                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
                }`}
              >
                <Icon size={18} className={active ? "text-[#00B47A]" : ""} />
                {!isSidebarCollapsed && (
                  <span className="text-sm tracking-wide">{item.label}</span>
                )}
              </Link>
            );
          })}
        </div>

        <div className="p-4 border-t border-[var(--color-border)]">
          <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center' : 'gap-3'} p-2 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]`}>
             <div className="w-8 h-8 rounded-full border border-emerald-500/20 overflow-hidden bg-emerald-500/5 flex items-center justify-center shrink-0">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <span className="text-[10px] font-bold text-emerald-400">
                  {user?.full_name ? user.full_name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2) : "AD"}
                </span>
              )}
            </div>
            {!isSidebarCollapsed && (
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-[var(--color-text)] truncate">
                  {user?.full_name || "Admin"}
                </span>
                <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider truncate">
                  {user?.role || "Global Workspace"}
                </span>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
