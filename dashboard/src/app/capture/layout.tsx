// =============================================================================
// VeriField Nexus — Standalone Mobile Capture Layout
// =============================================================================
// Provides isolated Workspace Context and clean mobile styling guidelines
// without desktop sidebar offsets or layout boundaries.
// =============================================================================

"use client";

import { WorkspaceProvider } from "@/context/WorkspaceContext";
import type { ReactNode } from "react";

export default function CaptureLayout({ children }: { children: ReactNode }) {
  return (
    <WorkspaceProvider>
      <div className="min-h-screen bg-[#090F10] text-zinc-100 antialiased selection:bg-emerald-500/30 selection:text-white pb-safe pt-safe">
        {children}
      </div>
    </WorkspaceProvider>
  );
}
