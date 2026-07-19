// =============================================================================
// VeriField Nexus — Sensors Page
// =============================================================================

"use client";

import { Radio, RefreshCw } from "lucide-react";

export default function SensorsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Sensor Data</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">IoT readings and corroboration metrics</p>
        </div>
        <button className="p-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
          <RefreshCw size={18} />
        </button>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 text-center animate-fade-in-up animation-delay-100">
        <Radio className="mx-auto text-[var(--color-text-muted)] mb-3" size={40} />
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Awaiting Sensor Telemetry</h3>
        <p className="text-[var(--color-text-secondary)] mt-1">Connect IoT devices to visualize real-time environmental data.</p>
      </div>
    </div>
  );
}
