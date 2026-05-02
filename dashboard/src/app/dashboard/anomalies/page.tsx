// =============================================================================
// VeriField Nexus — Anomalies Page
// =============================================================================

"use client";

import { AlertTriangle, Filter } from "lucide-react";

export default function AnomaliesPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Anomalies</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Review and resolve AI-flagged suspicious entries</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
            <Filter size={18} /> Filter
          </button>
        </div>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 text-center animate-fade-in-up animation-delay-100">
        <AlertTriangle className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No anomalies detected</h3>
        <p className="text-[var(--color-text-secondary)] mt-1">The Trust Engine hasn't flagged any recent activities.</p>
      </div>
    </div>
  );
}
