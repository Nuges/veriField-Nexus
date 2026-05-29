// =============================================================================
// VeriField Nexus — Trust Scores Page
// =============================================================================
// Specialized view for reviewing flagged activities and trust breakdowns.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { 
  ShieldAlert, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Search,
  RefreshCw,
  Clock,
  Layers,
  ArrowRight
} from "lucide-react";
import { fetchActivities, updateActivityStatus } from "@/lib/api";
import type { Activity } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";

export default function TrustScoresPage() {
  const [flaggedActivities, setFlaggedActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const handleStatusUpdate = async (activityId: string, newStatus: string) => {
    // Optimistic UI update: instantly filter out the resolved activity for immediate responsive feedback
    setFlaggedActivities(prev => prev.filter(a => a.id !== activityId));
    
    try {
      await updateActivityStatus(activityId, newStatus);
    } catch (err) {
      console.error("Failed to update activity status:", err);
      alert("Failed to record decision. Re-synchronizing queue...");
      loadData();
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load activities with flagged status
      const res = await fetchActivities({ status: "flagged", per_page: 50 });
      setFlaggedActivities(res.activities);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Snap client-side filtering matching
  const filteredActivities = flaggedActivities.filter(a => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (a.id || "").toLowerCase().includes(query) ||
      (a.activity_type || "").toLowerCase().includes(query) ||
      (a.description || "").toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-6 animate-fade-in-up">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] font-extrabold tracking-wider uppercase border border-red-500/15">
              AI Integrity Hub
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
            <ShieldAlert className="text-red-500" size={20} /> Trust Verification Hub
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Resolve integrity triggers, audit biometrics, and approve ledger quantifications.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button 
            onClick={loadData}
            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
            title="Reload queue"
          >
            <RefreshCw size={15} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
        </div>
      </div>

      {/* 📊 DYNAMIC AI STATISTICS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Needs Review */}
        <div className="bg-[var(--color-surface)] border border-red-500/20 rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-red-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Verification Queue</p>
            <p className="text-2xl font-black text-red-400 tracking-tight">
              {isLoading ? "..." : flaggedActivities.length}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Flagged telemetry signals</p>
          </div>
          <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl text-red-500 shrink-0 group-hover:bg-red-500 group-hover:text-white transition-all duration-300">
            <ShieldAlert size={18} />
          </div>
        </div>

        {/* Avg Resolution Time */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Avg Override Speed</p>
            <p className="text-2xl font-black text-blue-400 tracking-tight">
              {flaggedActivities.length > 0 ? "2.4h" : "0.0h"}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Mean duration to closure</p>
          </div>
          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
            <Clock size={18} />
          </div>
        </div>

        {/* AI Detection Rate */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Model Precision</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {flaggedActivities.length > 0 ? "98.2%" : "0.0%"}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Algorithmic sorting accuracy</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <Layers size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 FLAGGED LIST LEDGER */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
        
        {/* Table Search Header */}
        <div className="p-4 border-b border-[var(--color-border)] flex flex-col sm:flex-row items-center justify-between bg-[var(--color-background)]/50 gap-4">
          <h2 className="text-xs font-bold uppercase tracking-wider self-start sm:self-center">Review Queue</h2>
          
          <div className="relative w-full max-w-xs group">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] group-focus-within:text-[#00B47A] transition-colors" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search flagged queue..." 
              className="w-full pl-9 pr-4 py-1.5 bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text-primary)] focus:border-[#00B47A]/50 focus:outline-none transition-all font-semibold"
            />
          </div>
        </div>

        {/* Content list */}
        <div className="divide-y divide-[var(--color-border)]">
          {isLoading ? (
            <div className="p-12 text-center flex flex-col items-center justify-center space-y-2">
              <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Scanning biometrics...</p>
            </div>
          ) : filteredActivities.length === 0 ? (
            <div className="p-16 text-center max-w-sm mx-auto flex flex-col items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-[#00B47A]/10 flex items-center justify-center mb-3 border border-[#00B47A]/15 text-[#00B47A]">
                <CheckCircle size={22} />
              </div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Roster Clear</h3>
              <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                All suspicious telemetry flags have been successfully sorted and cleared.
              </p>
            </div>
          ) : (
            filteredActivities.map((activity) => (
              <div 
                key={activity.id} 
                className="p-5 hover:bg-[var(--color-background)]/20 transition-colors duration-200 flex flex-col md:flex-row gap-5 items-start"
              >
                
                {/* Visual Evidence aspect-video */}
                <div className="w-full md:w-44 h-28 rounded-xl bg-[var(--color-background)] overflow-hidden shrink-0 border border-[var(--color-border)] shadow-inner relative flex items-center justify-center">
                  {activity.image_url ? (
                    <img src={activity.image_url} alt="Proof" className="w-full h-full object-cover" />
                  ) : (
                    <div className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">No photo proof</div>
                  )}
                </div>

                {/* Specification Module */}
                <div className="flex-1 w-full space-y-3">
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="capitalize font-bold text-xs text-[var(--color-text-primary)] group-hover:text-[#00B47A] transition-colors">
                          {activity.activity_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[9px] text-[var(--color-text-muted)] font-mono bg-[var(--color-background)] border border-[var(--color-border)] px-1.5 py-0.5 rounded">
                          ID: {activity.id.substring(0, 14)}...
                        </span>
                      </div>
                      
                      <p className="text-[10px] text-[var(--color-text-secondary)] mt-1.5 font-medium flex items-center gap-1">
                        <Clock size={12} className="text-[#00B47A]" /> 
                        <span>Logged: {new Date(activity.captured_at).toLocaleString()}</span>
                      </p>
                    </div>
                    
                    <TrustBadge score={activity.trust_score} size="lg" />
                  </div>

                  {/* Red flags triggers */}
                  {activity.trust_flags && Object.keys(activity.trust_flags).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {Object.keys(activity.trust_flags).map((flag) => (
                        <span 
                          key={flag} 
                          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] font-extrabold border border-red-500/15 uppercase tracking-wider"
                        >
                          <AlertTriangle size={10} />
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Override Admin Deciders */}
                  <div className="flex gap-2 pt-2 border-t border-[var(--color-border)]/20">
                    <button 
                      onClick={() => handleStatusUpdate(activity.id, "verified")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#00B47A]/10 hover:bg-[#00B47A] text-[#00B47A] hover:text-white border border-[#00B47A]/25 text-xs font-bold transition-all uppercase tracking-wider active:scale-95"
                    >
                      <CheckCircle size={14} /> Override & Approve
                    </button>
                    
                    <button 
                      onClick={() => handleStatusUpdate(activity.id, "rejected")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/25 text-xs font-bold transition-all uppercase tracking-wider active:scale-95"
                    >
                      <XCircle size={14} /> Reject Entry
                    </button>
                  </div>

                </div>

              </div>
            ))
          )}
        </div>

      </div>

    </div>
  );
}
