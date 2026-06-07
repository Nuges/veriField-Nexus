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

    if (!["admin", "auditor"].includes(user.role)) {
      localStorage.clear();
      router.push("/login?error=unauthorized");
    }
  }, [user, router]);

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
              <p className="text-[10px] text-[var(--color-text-secondary)] font-medium">
                Tenant Sandboxed: <span className="text-emerald-500 font-bold">{user.organization || "VeriField"}</span>
              </p>
            </div>
            
            <Link href="/dashboard/settings" className="flex items-center gap-3 hover:opacity-85 transition-opacity bg-slate-900/10 dark:bg-slate-900/30 border border-[var(--color-border)] px-4 py-2 rounded-xl">
              <div className="text-right">
                <p className="text-xs font-bold text-[var(--color-text-primary)]">{user.full_name}</p>
                <p className="text-[9px] text-[var(--color-text-secondary)] font-bold uppercase tracking-wider">
                  {user.role === "admin" ? "Org Admin" : user.role === "auditor" ? "Auditor" : "Field Agent"}
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
        )}

        {/* Secondary Navigation Tabs */}
        <TopTabs />
        
        {children}
      </main>
    </div>
  );
}
