// =============================================================================
// VeriField Nexus — Agents Page
// =============================================================================

"use client";

import { useState } from "react";
import { Users, Search, Plus, ShieldCheck } from "lucide-react";

export default function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Field Agents</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Manage field agents, accounts, and performance ratings</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 text-emerald-400 font-medium hover:bg-emerald-500/20 transition-colors">
            <Plus size={18} /> Add Agent
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-wrap gap-4 items-center animate-fade-in-up animation-delay-100">
        <div className="flex items-center gap-2 flex-1 min-w-[250px]">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" size={18} />
            <input 
              type="text" 
              placeholder="Search by name, email or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl pl-10 pr-4 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>
        <select className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500">
          <option value="">All Regions</option>
          <option value="north">North Region</option>
          <option value="south">South Region</option>
        </select>
      </div>

      {/* Placeholder Data */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 text-center animate-fade-in-up animation-delay-200">
        <Users className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">No agents found</h3>
        <p className="text-[var(--color-text-secondary)] mt-1">Start by inviting agents to the platform or check back later.</p>
      </div>
    </div>
  );
}
