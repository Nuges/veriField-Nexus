// =============================================================================
// VeriField Nexus — Settings Page
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { Settings as SettingsIcon, Save, Loader2 } from "lucide-react";
import { fetchSettings, updateSettings } from "@/lib/api";

export default function SettingsPage() {
  const [gpsWeight, setGpsWeight] = useState(30);
  const [imageWeight, setImageWeight] = useState(40);
  const [frequencyWeight, setFrequencyWeight] = useState(30);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setGpsWeight(data.gps_weight);
      setImageWeight(data.image_weight);
      setFrequencyWeight(data.frequency_weight);
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSettings({
        gps_weight: gpsWeight,
        image_weight: imageWeight,
        frequency_weight: frequencyWeight,
      });
      // Optionally reload to get normalized weights if they didn't equal 100
      await loadSettings();
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-emerald-500" size={32} />
      </div>
    );
  }

  const total = gpsWeight + imageWeight + frequencyWeight;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">System Settings</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Configure Trust Engine weights and platform parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up animation-delay-100">
        <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
          <SettingsIcon className="text-emerald-500" size={24} />
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Trust Engine Configurations</h2>
        </div>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2 flex justify-between">
              <span>GPS Verification Weight (%)</span>
              <span className="text-emerald-500 font-semibold">{gpsWeight}%</span>
            </label>
            <input 
              type="range" 
              min="0" max="100" 
              value={gpsWeight} 
              onChange={(e) => setGpsWeight(Number(e.target.value))}
              className="w-full accent-emerald-500" 
            />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>100%</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2 flex justify-between">
              <span>Image Anomaly Detection Weight (%)</span>
              <span className="text-emerald-500 font-semibold">{imageWeight}%</span>
            </label>
            <input 
              type="range" 
              min="0" max="100" 
              value={imageWeight} 
              onChange={(e) => setImageWeight(Number(e.target.value))}
              className="w-full accent-emerald-500" 
            />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>100%</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2 flex justify-between">
              <span>Frequency Heuristic Weight (%)</span>
              <span className="text-emerald-500 font-semibold">{frequencyWeight}%</span>
            </label>
            <input 
              type="range" 
              min="0" max="100" 
              value={frequencyWeight} 
              onChange={(e) => setFrequencyWeight(Number(e.target.value))}
              className="w-full accent-emerald-500" 
            />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0%</span><span>100%</span>
            </div>
          </div>
          
          <div className={`mt-6 p-4 rounded-xl border ${total === 100 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600' : 'bg-amber-500/10 border-amber-500/20 text-amber-600'}`}>
            <p className="text-sm font-medium">Total Weight: {total}%</p>
            {total !== 100 && (
              <p className="text-xs mt-1">Note: Weights will be automatically normalized to equal 100% when saved.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
