// =============================================================================
// VeriField Nexus — Universal Digital Twin Viewer (Level 5 CIOS)
// =============================================================================
// Dynamically renders the detailed view of a specific entity (twin) in any domain.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";
import { Loader2, ArrowLeft, Settings, Activity as ActivityIcon, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function UniversalTwinViewer() {
  const params = useParams();
  const domain = params.domain as string;
  const id = params.id as string;
  const { user } = useWorkspace();
  
  const [twin, setTwin] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTwinData = async () => {
      setLoading(true);
      setError(null);
      try {
        await new Promise((resolve) => setTimeout(resolve, 800));
        
        setTwin({
          id: id,
          name: `Sample ${domain} ${id}`,
          status: "Active",
          metadata: {
            manufacturer: "Nexus Corp",
            firmware_version: "v2.4.1",
            location: "Site Alpha",
            telemetry_status: "Online"
          },
          created_at: new Date().toISOString()
        });
      } catch (err: any) {
        setError(err.message || `Failed to load digital twin: ${id}`);
      } finally {
        setLoading(false);
      }
    };
    
    loadTwinData();
  }, [domain, id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="animate-spin text-[#00B47A]" size={32} />
        <p className="text-[var(--color-text-secondary)] text-sm animate-pulse">Loading Digital Twin...</p>
      </div>
    );
  }

  if (error || !twin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 max-w-md text-center space-y-3">
          <p className="text-red-500 font-semibold">{error || "Twin not found"}</p>
          <Link href={`/dashboard/${domain}`} className="text-sm text-[#00B47A] hover:underline">
            Back to {domain}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link 
          href={`/dashboard/${domain}`}
          className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[var(--color-text)]">{twin.name}</h1>
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#00B47A]/10 text-[#00B47A] border border-[#00B47A]/20">
              {twin.status}
            </span>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm font-mono mt-1">ID: {twin.id}</p>
        </div>
        
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors text-sm font-semibold">
            <Settings size={16} />
            <span>Configure</span>
          </button>
        </div>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Metadata & Details */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5">
            <h3 className="text-sm font-bold text-[var(--color-text-secondary)] uppercase tracking-wider mb-4">
              Digital Twin Metadata
            </h3>
            <div className="space-y-4">
              {Object.entries(twin.metadata).map(([key, value]) => (
                <div key={key}>
                  <p className="text-xs text-[var(--color-text-secondary)] capitalize">{key.replace("_", " ")}</p>
                  <p className="text-sm text-[var(--color-text)] font-medium mt-0.5">{String(value)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Telemetry & Activity */}
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#00B47A]/10 flex items-center justify-center text-[#00B47A]">
                <ActivityIcon size={24} />
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider font-semibold">Telemetry Status</p>
                <p className="text-xl font-bold text-[var(--color-text)]">{twin.metadata.telemetry_status}</p>
              </div>
            </div>
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-500">
                <ShieldCheck size={24} />
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider font-semibold">Compliance Status</p>
                <p className="text-xl font-bold text-[var(--color-text)]">Verified</p>
              </div>
            </div>
          </div>

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 min-h-[300px] flex flex-col items-center justify-center text-center">
             <div className="w-16 h-16 rounded-full bg-[var(--color-surface-hover)] flex items-center justify-center text-[var(--color-text-secondary)] mb-4">
               <ActivityIcon size={32} />
             </div>
             <h4 className="text-[var(--color-text)] font-semibold">Live Telemetry Feed</h4>
             <p className="text-[var(--color-text-secondary)] text-sm max-w-sm mt-2">
               Connect the DynamicTelemetryConsole here to stream MQTT payload data for this twin in real-time.
             </p>
          </div>
        </div>

      </div>
    </div>
  );
}
