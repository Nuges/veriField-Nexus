// =============================================================================
// VeriField Nexus — Analytics Page
// =============================================================================
// Deep dive analytics and data export.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { Download, FileText, FileSpreadsheet, Calendar } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fetchTrends, exportData } from "@/lib/api";
import type { AnalyticsTrends } from "@/lib/types";

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchTrends(90); // 90 days for deep analytics
        setTrends(res);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleExport = async (format: 'csv' | 'json') => {
    setIsExporting(true);
    try {
      const res = await exportData({ format, include_flagged: true }) as { download_url?: string };
      
      // Handle file download
      if (res.download_url) {
        window.open(res.download_url, '_blank');
      } else {
        alert("Export successful. Check your email or downloads.");
      }
    } catch (err) {
      alert("Export failed: " + err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Analytics & Reports</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">Deep insights into field data collection</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* --- Activity Types Breakdown --- */}
        <div className="lg:col-span-2 bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up animation-delay-100">
          <h3 className="text-[var(--color-text-primary)] font-semibold mb-6">Activity Volume by Type</h3>
          <div className="h-[300px]">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-[var(--color-text-muted)]">Loading chart...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trends?.activity_types || []} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={true} vertical={false} />
                  <XAxis type="number" tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }} />
                  <YAxis dataKey="activity_type" type="category" tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)", borderRadius: "8px", color: "var(--color-text-primary)" }}
                    cursor={{ fill: "var(--color-border)", opacity: 0.4 }}
                  />
                  <Bar dataKey="count" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={24} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* --- Export Panel --- */}
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up animation-delay-200 flex flex-col">
          <h3 className="text-[var(--color-text-primary)] font-semibold mb-2">Data Export</h3>
          <p className="text-[var(--color-text-secondary)] text-sm mb-6">Download your verification data for external analysis.</p>
          
          <div className="space-y-4 flex-1">
            <button 
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="w-full flex items-center gap-3 p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-emerald-500 hover:bg-[#131C2C] transition-all group disabled:opacity-50"
            >
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500 group-hover:scale-110 transition-transform">
                <FileSpreadsheet size={20} />
              </div>
              <div className="text-left">
                <p className="text-[var(--color-text-primary)] font-medium text-sm">Export as CSV</p>
                <p className="text-[var(--color-text-secondary)] text-xs">Best for Excel or Sheets</p>
              </div>
              <Download size={16} className="ml-auto text-[var(--color-text-muted)] group-hover:text-emerald-400" />
            </button>

            <button 
              onClick={() => handleExport('json')}
              disabled={isExporting}
              className="w-full flex items-center gap-3 p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-blue-500 hover:bg-[#131C2C] transition-all group disabled:opacity-50"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
                <FileText size={20} />
              </div>
              <div className="text-left">
                <p className="text-[var(--color-text-primary)] font-medium text-sm">Export as JSON</p>
                <p className="text-[var(--color-text-secondary)] text-xs">Best for API integrations</p>
              </div>
              <Download size={16} className="ml-auto text-[var(--color-text-muted)] group-hover:text-blue-400" />
            </button>
          </div>
          
          <div className="mt-6 pt-4 border-t border-[var(--color-border)] flex items-center gap-2 text-[var(--color-text-muted)] text-xs">
            <Calendar size={14} />
            <span>Last exported: {new Date().toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
