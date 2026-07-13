// =============================================================================
// VeriField Nexus — Universal Domain View (Level 5 CIOS)
// =============================================================================
// Dynamically renders the list view for any domain (activities, properties, 
// methodologies, etc.) by fetching configuration and data from the backend APIs.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";
import { Loader2, Search, Filter, Download, Plus } from "lucide-react";

export default function UniversalDomainView() {
  const params = useParams();
  const domain = params.domain as string;
  const { user } = useWorkspace();
  
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // In a fully built Level 5 CIOS, this would fetch from a generic API endpoint:
    // /api/v2/{domain} using the access token.
    // For now, we simulate fetching dynamic generic data.
    
    const loadDomainData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Simulated API call delay
        await new Promise((resolve) => setTimeout(resolve, 600));
        
        // Mock dynamic data response based on domain
        setData([
          { id: "1", name: `Sample ${domain} 1`, status: "Active", created_at: new Date().toISOString() },
          { id: "2", name: `Sample ${domain} 2`, status: "Pending", created_at: new Date().toISOString() }
        ]);
      } catch (err: any) {
        setError(err.message || `Failed to load data for domain: ${domain}`);
      } finally {
        setLoading(false);
      }
    };
    
    loadDomainData();
  }, [domain]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="animate-spin text-[#00B47A]" size={32} />
        <p className="text-[var(--color-text-secondary)] text-sm animate-pulse">Loading {domain} data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 max-w-md text-center space-y-3">
          <p className="text-red-500 font-semibold">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)] capitalize">
            {domain.replace("-", " ")}
          </h1>
          <p className="text-[var(--color-text-secondary)] text-sm">
            Manage your {domain.replace("-", " ")} records globally.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)]" size={16} />
            <input 
              type="text" 
              placeholder={`Search ${domain}...`}
              className="pl-9 pr-4 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[#00B47A] transition-colors w-full md:w-64"
            />
          </div>
          <button className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors">
            <Filter size={18} />
          </button>
          <button className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors">
            <Download size={18} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#00B47A] text-black font-semibold text-sm hover:opacity-90 transition-opacity">
            <Plus size={18} />
            <span>New {domain}</span>
          </button>
        </div>
      </div>

      {/* Dynamic Data Grid */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-hover)]">
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">ID</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Name</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Status</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {data.map((row, i) => (
                <tr key={i} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                  <td className="p-4 text-sm text-[var(--color-text)] font-mono">{row.id}</td>
                  <td className="p-4 text-sm text-[var(--color-text)] font-medium">{row.name}</td>
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                      row.status === 'Active' 
                        ? 'bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20' 
                        : 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="p-4 text-sm text-[var(--color-text-secondary)] text-right">
                    {new Date(row.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-[var(--color-text-secondary)] text-sm">
                    No {domain} found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
