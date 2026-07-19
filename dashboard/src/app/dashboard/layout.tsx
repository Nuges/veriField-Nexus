// =============================================================================
// VeriField Nexus — Dashboard Layout
// =============================================================================
// Wraps all dashboard pages with the Sidebar navigation and Workspace Resolver.
// Supports mobile responsive spacing offsets and renders the global desktop top header.
// =============================================================================

"use client";

import Sidebar from "@/components/Sidebar";
import TopTabs from "@/components/TopTabs";
import Link from "next/link";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WorkspaceProvider>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </WorkspaceProvider>
  );
}

function DashboardLayoutContent({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useWorkspace();
  const router = useRouter();

  useEffect(() => {
    if (!user) return;

    // Allow FIELD_AGENT in addition to other roles
    if (!["admin", "auditor", "SUPER_ADMIN", "ORG_ADMIN", "FIELD_AGENT", "PORTFOLIO_MANAGER", "IOT_ENGINEER"].includes(user.role)) {
      localStorage.clear();
      router.push("/login?error=unauthorized");
    } else if (user.role === "SUPER_ADMIN") {
      // router.push("/super-admin"); // Let the sidebar handle navigation naturally
    }
  }, [user, router]);

  const { activeSector, changeSector, allowedSectors, moduleRegistry } = useWorkspace();

  if (isLoading && !user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-background)] space-y-3">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">
          Connecting to secure digital MRV ledger...
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[var(--color-background)]">
      {/* Sidebar navigation (Desktop collapsible + Mobile sliding drawer) */}
      <Sidebar />

      {/* Main content area — offset dynamically for responsive breakpoints */}
      <main className="flex-1 ml-0 md:ml-[260px] mt-14 md:mt-0 p-4 md:p-6 overflow-auto">
        {/* Global Desktop Top Header */}
        {user && (
          <div className="hidden md:flex items-center justify-between mb-6 pb-4 border-b border-[var(--color-border)] animate-fade-in-up">
            <div>
              <h2 className="text-lg font-extrabold text-[var(--color-text-primary)]">
                Welcome, <span className="text-emerald-400">{user.full_name || "User"}</span> 👋
              </h2>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Sector / Module Switcher */}
              {allowedSectors.length > 1 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[var(--color-text-secondary)] uppercase">Module:</span>
                  <select 
                    value={activeSector} 
                    onChange={(e) => changeSector(e.target.value)}
                    className="bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-2 outline-none font-semibold cursor-pointer"
                  >
                    {allowedSectors.map((sector) => (
                      <option key={sector} value={sector}>
                        {moduleRegistry[sector]?.name || sector.charAt(0).toUpperCase() + sector.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <Link href="/dashboard/settings" className="flex items-center gap-3 hover:opacity-85 transition-opacity bg-slate-900/10 dark:bg-slate-900/30 border border-[var(--color-border)] px-4 py-2 rounded-xl">
                <div className="text-right">
                  <p className="text-xs font-bold text-[var(--color-text-primary)]">{user.full_name}</p>
                  <p className="text-[9px] text-[var(--color-text-secondary)] font-bold uppercase tracking-wider">
                    {user.role.replace("_", " ")}
                  </p>
                </div>
                <div className="w-9 h-9 rounded-full border border-emerald-500/20 overflow-hidden bg-emerald-500/5 flex items-center justify-center shrink-0 shadow-sm">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-xs font-black text-emerald-400">
                      {user.full_name ? user.full_name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2) : "US"}
                    </span>
                  )}
                </div>
              </Link>
            </div>
          </div>
        )}

        {/* Secondary Navigation Tabs */}
        <TopTabs />
        
        <div key={activeSector}>
          {children}
        </div>
      </main>
    </div>
  );
}
