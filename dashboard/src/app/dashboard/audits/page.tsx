// =============================================================================
// VeriField Nexus — Audits Page
// =============================================================================

"use client";

import { useState } from "react";
import { ClipboardCheck, Plus, Filter } from "lucide-react";

export default function AuditsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Audit Tasks</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Assign and track manual audits for low-trust activities</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20">
            <Plus size={18} /> New Audit Task
          </button>
        </div>
      </div>

      {/* Placeholder Data */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 text-center animate-fade-in-up animation-delay-100">
        <ClipboardCheck className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No pending audits</h3>
        <p className="text-[var(--color-text-secondary)] mt-1">All audit tasks have been completed or none are assigned.</p>
      </div>
    </div>
  );
}
