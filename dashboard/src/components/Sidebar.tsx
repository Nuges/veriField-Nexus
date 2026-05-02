// =============================================================================
// VeriField Nexus — Sidebar Navigation Component
// =============================================================================
// Collapsible sidebar with icons and active route highlighting.
// =============================================================================

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  MapPin,
  Home,
  ShieldCheck,
  BarChart3,
  Download,
  LogOut,
  Menu,
  X,
  FileCheck,
  Users,
  ClipboardCheck,
  AlertTriangle,
  Radio,
  UsersRound,
  Settings,
} from "lucide-react";
import { useState } from "react";

// Sidebar navigation items
const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/activities", label: "Activities", icon: Activity },
  { href: "/dashboard/map", label: "Map View", icon: MapPin },
  { href: "/dashboard/properties", label: "Assets", icon: Home },
  { href: "/dashboard/trust-scores", label: "Trust Scores", icon: ShieldCheck },
  { href: "/dashboard/verifications", label: "Cross-Verifications", icon: FileCheck },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/agents", label: "Agents", icon: Users },
  { href: "/dashboard/audits", label: "Audits", icon: ClipboardCheck },
  { href: "/dashboard/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/dashboard/sensors", label: "Sensors", icon: Radio },
  { href: "/dashboard/community", label: "Community", icon: UsersRound },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-[var(--color-surface)] border-r border-[var(--color-border)] z-50 
        transition-all duration-300 flex flex-col
        ${isCollapsed ? "w-[68px]" : "w-[260px]"}`}
    >
      {/* --- Header / Logo --- */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-[var(--color-border)]">
        {!isCollapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
              <ShieldCheck size={18} className="text-[var(--color-text-primary)]" />
            </div>
            <span className="text-[var(--color-text-primary)] font-semibold text-sm tracking-tight">
              VeriField Nexus
            </span>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg hover:bg-[var(--color-card)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          {isCollapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>

      {/* --- Navigation Links --- */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${
                  isActive
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-slate-200"
                }`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon
                size={20}
                className={isActive ? "text-emerald-400" : "text-[var(--color-text-muted)]"}
              />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* --- Footer --- */}
      <div className="p-3 border-t border-[var(--color-border)]">
        <button
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium 
            text-[var(--color-text-secondary)] hover:bg-red-500/10 hover:text-red-400 transition-all w-full"
          onClick={() => {
            localStorage.removeItem("vf_token");
            window.location.href = "/login";
          }}
        >
          <LogOut size={20} />
          {!isCollapsed && <span>Sign Out</span>}
        </button>
      </div>
    </aside>
  );
}
