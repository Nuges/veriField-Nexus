// =============================================================================
// VeriField Nexus — Settings Page
// =============================================================================

"use client";

import { Settings as SettingsIcon, Save } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">System Settings</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Configure Trust Engine weights and platform parameters</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20">
          <Save size={18} /> Save Changes
        </button>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up animation-delay-100">
        <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
          <SettingsIcon className="text-emerald-500" size={24} />
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Trust Engine Configurations</h2>
        </div>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              GPS Verification Weight (%)
            </label>
            <input type="range" min="0" max="100" defaultValue="30" className="w-full accent-emerald-500" />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>30%</span><span>100%</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Image Anomaly Detection Weight (%)
            </label>
            <input type="range" min="0" max="100" defaultValue="40" className="w-full accent-emerald-500" />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>40%</span><span>100%</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Frequency Heuristic Weight (%)
            </label>
            <input type="range" min="0" max="100" defaultValue="30" className="w-full accent-emerald-500" />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>30%</span><span>100%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
