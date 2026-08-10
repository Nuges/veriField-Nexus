// =============================================================================
// VeriField Nexus — Help & Knowledge Centre Dashboard Page
// =============================================================================

"use client";

import { Suspense } from "react";
import HelpKnowledgeCenter from "@/components/help/HelpKnowledgeCenter";

export default function DashboardHelpPage() {
  return (
    <div className="w-full h-full">
      <Suspense fallback={<div className="p-8 text-xs text-zinc-400 font-mono">Loading Help & Knowledge Centre...</div>}>
        <HelpKnowledgeCenter />
      </Suspense>
    </div>
  );
}
