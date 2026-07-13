// =============================================================================
// VeriField Nexus — Sidebar Navigation Component
// =============================================================================
// Responsive sidebar with collapsible desktop mode and slide-out mobile drawer.
// Dynamically toggles logo-black and logo-green for light and dark modes.
// =============================================================================

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Home,
  ShieldCheck,
  Leaf,
  Zap,
  Settings,
  Menu,
  X,
  Compass,
  Camera,
  TrendingUp,
  Globe,
  Building,
  Users,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
// Helper to resolve dynamic sidebar nav items based on role
function getNavItems(role: string | null) {
  const items = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];

  const roleStr = role || "";

  // 1. OPERATIONAL MODULES (Field Agents, Auditors, Developers, Super Admin)
  // Regulators and Compliance Admins DO NOT see these low-level field data forms
  if (["field_agent", "auditor", "admin", "ORG_ADMIN", "SUPER_ADMIN"].includes(roleStr)) {
    items.push({ href: "/dashboard/properties", label: "Field Data", icon: Home });
    items.push({ href: "/dashboard/audits", label: "Verification", icon: ShieldCheck });
    items.push({ href: "/dashboard/carbon", label: "Reports", icon: Leaf });
  }

  // 2. PORTFOLIO MODULES (Auditors, Developers, Regulators, Super Admin)
  // Field Agents DO NOT see these aggregation views
  if (["auditor", "admin", "ORG_ADMIN", "SUPER_ADMIN", "COMPLIANCE_ADMIN", "JURISDICTION_ADMIN"].includes(roleStr)) {
    items.push({ href: "/dashboard/executive", label: "Executive Portfolio", icon: TrendingUp });
    items.push({ href: "/dashboard/poa", label: "POA Portfolio", icon: Compass });
  }

  // 3. ENTERPRISE & GOVERNANCE MODULES (Regulators, Super Admin)
  // Field Agents, Auditors, and Org Admins DO NOT see these macro governance tools
  if (["SUPER_ADMIN", "COMPLIANCE_ADMIN", "JURISDICTION_ADMIN"].includes(roleStr)) {
    items.push({ href: "/dashboard/jurisdictions", label: "Compliance & Jurisdictions", icon: Globe });
    items.push({ href: "/dashboard/regulator", label: "Governance Portal", icon: Building });
    items.push({ href: "/dashboard/methodologies", label: "Methodologies", icon: Leaf });
  }

  // 4. ADMINISTRATION (Everyone gets profile/tenant settings)
  if (["ORG_ADMIN", "SUPER_ADMIN", "SYSTEM_ADMIN"].includes(roleStr)) {
    items.push({ href: "/dashboard/access-control", label: "Access Control", icon: Users });
  }
  items.push({ href: "/dashboard/settings", label: "Settings", icon: Settings });
  
  return items;
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, activeSector, changeSector, allowedSectors, moduleRegistry, isSandboxed, isSidebarCollapsed, setIsSidebarCollapsed } = useWorkspace();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const navItems = getNavItems(user ? user.role : null);

  // Close mobile drawer automatically when route changes
  useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  const getIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/dashboard") {
      return pathname === "/dashboard" || pathname.startsWith("/dashboard/analytics");
    } else if (href === "/dashboard/executive") {
      return pathname.startsWith("/dashboard/executive");
    } else if (href === "/dashboard/properties") {
      return pathname.startsWith("/dashboard/properties") || 
             pathname.startsWith("/dashboard/activities") || 
             pathname.startsWith("/dashboard/map");
    } else if (href === "/dashboard/audits") {
      return pathname.startsWith("/dashboard/audits") || 
             pathname.startsWith("/dashboard/anomalies") || 
             pathname.startsWith("/dashboard/verifications") || 
             pathname.startsWith("/dashboard/trust-scores") || 
             pathname.startsWith("/dashboard/community");
    } else if (href === "/dashboard/carbon") {
      return pathname.startsWith("/dashboard/carbon") || pathname.startsWith("/dashboard/registry");
    } else if (href === "/dashboard/poa") {
      return pathname.startsWith("/dashboard/poa");
    } else if (href === "/dashboard/jurisdictions") {
      return pathname.startsWith("/dashboard/jurisdictions");
    } else if (href === "/dashboard/regulator") {
      return pathname.startsWith("/dashboard/regulator");
    } else if (href === "/dashboard/methodologies") {
      return pathname.startsWith("/dashboard/methodologies");
    } else if (href === "/dashboard/energy") {
      return pathname.startsWith("/dashboard/energy");
    } else if (href === "/dashboard/access-control") {
      return pathname.startsWith("/dashboard/access-control");
    } else if (href === "/dashboard/settings") {
      return pathname.startsWith("/dashboard/settings");
    }
    return false;
  };

  return (
    <>
      {/* =======================================================================
          1. STICKY MOBILE TOP NAVBAR (Visible only on mobile/tablet)
          ======================================================================= */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-14 bg-[var(--color-surface)] border-b border-[var(--color-border)] z-40 flex items-center justify-between px-4">
        {/* Logo on the far left responsive to Light/Dark mode */}
        <div className="flex items-center gap-1.5 h-10">
          <img
            src="/logo-black.png"
            alt="VeriField Nexus"
            className="h-10 w-auto object-contain block dark:hidden"
          />
          <img
            src="/logo-green.png"
            alt="VeriField Nexus"
            className="h-10 w-auto object-contain hidden dark:block"
          />
        </div>

        {/* Right side container: Profile (left) and Hamburger (right) */}
        <div className="flex items-center gap-2.5">
          {/* Profile / avatar placeholder */}
          <div className="w-8 h-8 rounded-full border border-emerald-500/20 overflow-hidden bg-emerald-500/5 flex items-center justify-center shrink-0">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
            ) : (
              <span className="text-[10px] font-bold text-emerald-400">
                {user?.full_name ? user.full_name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2) : "AD"}
              </span>
            )}
          </div>

          {/* Hamburger button on the far right */}
          <button
            onClick={() => setIsMobileOpen(true)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-card)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors shrink-0"
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>
        </div>
      </header>

      {/* =======================================================================
          2. MOBILE DRAWER OVERLAY & BACKGROUND BLUR
          ======================================================================= */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 md:hidden transition-opacity duration-300"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* =======================================================================
          3. MOBILE DRAWER SIDEBAR (Slides in on mobile)
          ======================================================================= */}
      <aside
        className={`fixed left-0 top-0 h-screen w-[260px] bg-[var(--color-surface)] border-r border-[var(--color-border)] z-[60] md:hidden 
          transition-transform duration-300 ease-out flex flex-col
          ${isMobileOpen ? "translate-x-0 pointer-events-auto" : "-translate-x-full pointer-events-none"}`}
      >
        <div className="flex items-center justify-between px-4 h-16 border-b border-[var(--color-border)] shrink-0">
          <div className="flex items-center gap-2 h-12">
            <img
              src="/logo-black.png"
              alt="VeriField Nexus"
              className="h-12 w-auto object-contain block dark:hidden"
            />
            <img
              src="/logo-green.png"
              alt="VeriField Nexus"
              className="h-12 w-auto object-contain hidden dark:block"
            />
          </div>
          <button
            onClick={() => setIsMobileOpen(false)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-card)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Mobile Workspace Select Switcher */}
        {allowedSectors.length > 1 && (
          <div className="px-4 py-3 border-b border-[var(--color-border)] bg-slate-900/10 dark:bg-slate-900/30 shrink-0">
            <span className="text-[9px] uppercase font-extrabold text-[var(--color-text-secondary)] tracking-wider block mb-1.5">Workspace</span>
            <select
              value={activeSector}
              onChange={(e) => changeSector(e.target.value)}
              className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs px-2.5 py-1.5 font-bold outline-none focus:border-emerald-500 transition-colors cursor-pointer"
            >
              {allowedSectors.filter(sec => sec !== "all").map((sec) => {
                const mod = moduleRegistry[sec];
                const emoji = mod?.badge || "🌍 ";
                return (
                  <option key={sec} value={sec}>
                    {emoji}{mod?.name || sec}
                  </option>
                );
              })}
            </select>
          </div>
        )}

        <nav className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const isActive = getIsActive(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={`${item.href}?workspace=${activeSector}`}
                className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${
                    isActive
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-slate-900 dark:hover:text-slate-200"
                  }`}
              >
                <Icon
                  size={20}
                  className={`shrink-0 ${isActive ? "text-emerald-700 dark:text-emerald-400" : "text-[var(--color-text-muted)]"}`}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* =======================================================================
          4. DESKTOP SIDEBAR (Visible only on desktop md and up)
          ======================================================================= */}
      <aside
         className={`fixed left-0 top-0 h-screen bg-[var(--color-surface)] border-r border-[var(--color-border)] z-50 
          transition-all duration-300 flex flex-col hidden md:flex
          ${isSidebarCollapsed ? "w-[68px]" : "w-[260px]"}`}
      >
        <div className="flex items-center justify-between px-4 h-16 border-b border-[var(--color-border)] shrink-0">
          {!isSidebarCollapsed && (
            <div className="flex items-center gap-3 overflow-hidden max-w-[185px]">
              <img
                src="/logo-black.png"
                alt="VeriField Nexus"
                className="h-[68px] w-auto object-contain block dark:hidden"
              />
              <img
                src="/logo-green.png"
                alt="VeriField Nexus"
                className="h-[68px] w-auto object-contain hidden dark:block"
              />
            </div>
          )}
          <button
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-card)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors shrink-0 mx-auto"
            aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isSidebarCollapsed ? <Menu size={18} /> : <X size={18} />}
          </button>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const isActive = getIsActive(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={`${item.href}?workspace=${activeSector}`}
                className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${
                    isActive
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-slate-900 dark:hover:text-slate-200"
                  }`}
                title={isSidebarCollapsed ? item.label : undefined}
              >
                <Icon
                  size={22}
                  className={`shrink-0 ${isActive ? "text-emerald-700 dark:text-emerald-400" : "text-[var(--color-text-muted)]"}`}
                />
                {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
