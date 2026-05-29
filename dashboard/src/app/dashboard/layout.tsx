// =============================================================================
// VeriField Nexus — Dashboard Layout
// =============================================================================
// Wraps all dashboard pages with the sidebar navigation.
// Supports mobile responsive spacing offsets and renders the global desktop top header.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import TopTabs from "@/components/TopTabs";
import { fetchMe } from "@/lib/api";
import Link from "next/link";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    loadUser();
    
    if (typeof window !== "undefined") {
      const handleUpdate = () => loadUser();
      window.addEventListener("vf_profile_updated", handleUpdate);
      return () => window.removeEventListener("vf_profile_updated", handleUpdate);
    }
  }, []);

  const loadUser = async () => {
    try {
      const u = await fetchMe();
      setUser(u);
    } catch (_) {}
  };

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
                  {user.role === "admin" ? "Org Admin" : "Field Agent"}
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
