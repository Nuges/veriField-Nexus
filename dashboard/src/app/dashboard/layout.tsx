// =============================================================================
// VeriField Nexus — Dashboard Layout
// =============================================================================
// Wraps all dashboard pages with the sidebar navigation.
// =============================================================================

import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[var(--color-background)]">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main content area — offset by sidebar width */}
      <main className="flex-1 ml-[260px] p-6 overflow-auto">
        {children}
      </main>
    </div>
  );
}
