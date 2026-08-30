// =============================================================================

// VeriField Nexus — Dashboard Layout (CIOS Level 5 AI-Native)

// =============================================================================

// Embeds Dynamic Sidebar, Enterprise Breadcrumb, AI Notification Center, and

// Universal Contextual AI Assistant across all 4 climate sectors & 38 pages.

// Safe hydration mount-gated for SSR compatibility.

// =============================================================================



"use client";



import Sidebar from "@/components/DynamicSidebar";
import { isDashboardRoleAllowed } from "@/lib/roles";

import EnterpriseBreadcrumb from "@/components/EnterpriseBreadcrumb";

import AINotificationCenter from "@/components/AINotificationCenter";

import UniversalAIAssistant from "@/components/UniversalAIAssistant";

import InlineGuidance from "@/components/InlineGuidance";
import { fetchUsers } from "@/lib/api";
import Link from "next/link";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Bot } from "lucide-react";

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
  const { user, isLoading, activeSector } = useWorkspace();
  const router = useRouter();
  const pathname = usePathname();
  const [isAINotificationsOpen, setIsAINotificationsOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [guidanceData, setGuidanceData] = useState<{ activeUsers?: number; pendingApprovals?: number }>({});

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!user) return;

    if (!isDashboardRoleAllowed(user.role)) {
      localStorage.clear();
      router.push("/login?error=unauthorized");
      return;
    }

    // Dynamically fetch live active users & pending approvals for administrative guidance
    fetchUsers()
      .then((users) => {
        if (Array.isArray(users)) {
          const activeCount = users.filter((u) => u.is_active !== false && u.status !== "suspended" && u.status !== "decommissioned").length;
          const pendingCount = users.filter((u) => u.status === "pending" || u.status === "pending_approval").length;
          setGuidanceData({ activeUsers: Math.max(1, activeCount), pendingApprovals: pendingCount });
        }
      })
      .catch(() => {
        setGuidanceData({ activeUsers: 1, pendingApprovals: 0 });
      });
  }, [user, router]);



  // SSR-safe hydration gate

  if (!isMounted || (isLoading && !user)) {

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

    <div className="flex min-h-screen bg-[var(--color-background)] transition-colors duration-300">

      {/* Sidebar navigation */}

      <Sidebar />



      {/* Main content area */}

      <div className="flex-1 flex flex-col min-w-0 bg-[var(--color-background)] transition-colors duration-300">

        {/* Header Enterprise Contextual Breadcrumb */}

        {user && <EnterpriseBreadcrumb />}



        <main className="flex-1 min-w-0 p-4 md:p-6 overflow-auto">

          {/* Global Top Greeting, AI Bell & Profile Header */}

          {user && (

            <div className="hidden md:flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-border)]">

              <div>

                <h2 className="text-lg font-extrabold text-[var(--color-text-primary)]">

                  Welcome, <span className="text-[#00B47A]">{user.full_name || "User"}</span> 👋

                </h2>

              </div>



              <div className="flex items-center gap-3">

                {/* AI Notification Center Trigger */}

                <button

                  onClick={() => setIsAINotificationsOpen(true)}

                  className="relative px-3.5 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] transition-all shadow-xs cursor-pointer flex items-center gap-1.5"

                  title="Open AI Notification Center"

                >

                  <span className="text-xs font-bold text-[var(--color-text-primary)]">AI Alerts</span>

                </button>



                {/* Profile Link */}

                <Link href="/dashboard/settings" className="flex items-center gap-3 hover:opacity-85 transition-opacity bg-[var(--color-surface)] border border-[var(--color-border)] px-4 py-2 rounded-xl shadow-xs">

                  <div className="text-right">

                    <p className="text-xs font-bold text-[var(--color-text-primary)]">{user.full_name}</p>

                    <p className="text-[9px] text-[var(--color-text-secondary)] font-bold uppercase tracking-wider">

                      {user.role.replace("_", " ")}

                    </p>

                  </div>

                  <div className="w-8 h-8 rounded-full border border-emerald-500/20 overflow-hidden bg-emerald-500/10 flex items-center justify-center shrink-0 shadow-sm">

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



          {/* Inline Role Guidance */}
          <InlineGuidance role={user?.role} page={pathname} data={guidanceData} />



          {/* Contextual AI Assistant Present Across Every Page */}

          <UniversalAIAssistant />



          <div key={activeSector}>

            {children}

          </div>

        </main>



        {/* AI Notification Center Slide-over Drawer */}

        <AINotificationCenter

          isOpen={isAINotificationsOpen}

          onClose={() => setIsAINotificationsOpen(false)}

        />

      </div>

    </div>

  );

}
