// =============================================================================
// VeriField Nexus — Community Validation Page
// =============================================================================

"use client";

import { UsersRound, CheckCircle2 } from "lucide-react";

export default function CommunityPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Community Validation</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Review peer-submitted feedback and verifications</p>
        </div>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 text-center animate-fade-in-up animation-delay-100">
        <UsersRound className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No community feedback</h3>
        <p className="text-[var(--color-text-secondary)] mt-1">Wait for community members to validate recent activities.</p>
      </div>
    </div>
  );
}
