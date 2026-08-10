// =============================================================================
// VeriField Nexus — Root Help Route
// =============================================================================

"use client";

import { Suspense } from "react";
import HelpKnowledgeCenter from "@/components/help/HelpKnowledgeCenter";

export default function RootHelpPage() {
  return (
    <div className="w-full min-h-screen bg-[var(--color-background)]">
      <Suspense fallback={<div className="p-8 text-xs text-zinc-400 font-mono">Loading Help & Knowledge Centre...</div>}>
        <HelpKnowledgeCenter />
      </Suspense>
    </div>
  );
}
