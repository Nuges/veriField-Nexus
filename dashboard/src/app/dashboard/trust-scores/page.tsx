// =============================================================================
// VeriField Nexus — Trust Scores Page
// =============================================================================
// Specialized view for reviewing flagged activities and trust breakdowns.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { ShieldAlert, CheckCircle, AlertTriangle, XCircle, Search } from "lucide-react";
import { fetchActivities } from "@/lib/api";
import type { Activity } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";

export default function TrustScoresPage() {
  const [flaggedActivities, setFlaggedActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadFlagged() {
      try {
        // Load activities with low trust scores or flagged status
        const res = await fetchActivities({ status: "flagged", per_page: 50 });
        setFlaggedActivities(res.activities);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadFlagged();
  }, []);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Trust Verification Hub</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">Review flagged activities and AI anomaly detections</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in-up animation-delay-100">
        <div className="bg-[var(--color-card)] border border-red-500/20 rounded-2xl p-5 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10"><ShieldAlert size={80} /></div>
          <p className="text-[var(--color-text-secondary)] text-sm mb-1">Needs Review</p>
          <p className="text-3xl font-bold text-red-400">{flaggedActivities.length}</p>
        </div>
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <p className="text-[var(--color-text-secondary)] text-sm mb-1">Avg Resolution Time</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">2.4h</p>
        </div>
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <p className="text-[var(--color-text-secondary)] text-sm mb-1">AI Detection Rate</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">98.2%</p>
        </div>
      </div>

      {/* Flagged Queue */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-200">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Review Queue</h2>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input 
              type="text" 
              placeholder="Search by ID or user..." 
              className="pl-9 pr-4 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] focus:border-emerald-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="divide-y divide-[var(--color-border)]">
          {isLoading ? (
            <div className="p-8 text-center text-[var(--color-text-secondary)]">Loading review queue...</div>
          ) : flaggedActivities.length === 0 ? (
            <div className="p-12 text-center flex flex-col items-center">
              <CheckCircle size={48} className="text-emerald-500 mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Queue Empty</h3>
              <p className="text-[var(--color-text-secondary)] text-sm mt-1">No flagged activities require review at this time.</p>
            </div>
          ) : (
            flaggedActivities.map((activity) => (
              <div key={activity.id} className="p-5 hover:bg-[var(--color-surface)] transition-colors flex flex-col md:flex-row gap-6">
                {/* Image */}
                <div className="w-full md:w-48 h-32 rounded-xl bg-[var(--color-border)] overflow-hidden shrink-0 border border-[#475569]">
                  {activity.image_url ? (
                    <img src={activity.image_url} alt="Proof" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[var(--color-text-muted)]">No Image</div>
                  )}
                </div>

                {/* Details */}
                <div className="flex-1 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="capitalize font-semibold text-[var(--color-text-primary)]">{activity.activity_type}</span>
                        <span className="text-xs text-[var(--color-text-muted)] font-mono">ID: {activity.id.substring(0, 8)}</span>
                      </div>
                      <p className="text-sm text-[var(--color-text-secondary)]">{new Date(activity.captured_at).toLocaleString()}</p>
                    </div>
                    <TrustBadge score={activity.trust_score} size="lg" />
                  </div>

                  {/* Trust Flags Map */}
                  {activity.trust_flags && Object.keys(activity.trust_flags).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {Object.keys(activity.trust_flags).map((flag) => (
                        <span key={flag} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-red-500/10 text-red-400 text-xs font-medium border border-red-500/20">
                          <AlertTriangle size={12} />
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    <button className="px-4 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-sm font-medium rounded-lg transition-colors flex items-center gap-2">
                      <CheckCircle size={16} /> Approve Override
                    </button>
                    <button className="px-4 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg transition-colors flex items-center gap-2">
                      <XCircle size={16} /> Reject Submission
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
