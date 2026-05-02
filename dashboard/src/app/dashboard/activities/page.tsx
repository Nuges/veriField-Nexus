// =============================================================================
// VeriField Nexus — Activities Page
// =============================================================================
// Sortable, filterable list of all field activities.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { Search, Filter, RefreshCw, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { fetchActivities } from "@/lib/api";
import type { Activity, ActivityListResponse } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";

export default function ActivitiesPage() {
  const [data, setData] = useState<ActivityListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [page, setPage] = useState(1);
  const [activityType, setActivityType] = useState("");
  const [status, setStatus] = useState("");

  const loadActivities = async () => {
    setIsLoading(true);
    try {
      const res = await fetchActivities({ page, per_page: 20, activity_type: activityType, status });
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();
  }, [page, activityType, status]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Activities</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Review and manage field activity submissions</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={loadActivities} className="p-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 text-emerald-400 font-medium hover:bg-emerald-500/20 transition-colors">
            <Download size={18} /> Export
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-wrap gap-4 items-center animate-fade-in-up animation-delay-100">
        <div className="flex items-center gap-2 text-[var(--color-text-secondary)]">
          <Filter size={18} />
          <span className="text-sm font-medium">Filters:</span>
        </div>
        
        <select 
          value={activityType} 
          onChange={(e) => { setActivityType(e.target.value); setPage(1); }}
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Types</option>
          <option value="cooking">Clean Cooking</option>
          <option value="farming">Agriculture</option>
          <option value="energy">Energy Use</option>
          <option value="sustainability">Sustainability</option>
          <option value="other">Other</option>
        </select>

        <select 
          value={status} 
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Statuses</option>
          <option value="verified">Verified (High Trust)</option>
          <option value="review">Review (Medium Trust)</option>
          <option value="flagged">Flagged (Low Trust)</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {/* Data Table */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-200">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Type</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Date</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">User ID</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Location</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Trust Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading && !data ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--color-text-secondary)]">Loading activities...</td>
                </tr>
              ) : data?.activities.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--color-text-secondary)]">No activities found matching filters.</td>
                </tr>
              ) : (
                data?.activities.map((activity) => (
                  <tr key={activity.id} className="hover:bg-[var(--color-surface)] transition-colors group cursor-pointer">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {activity.image_url ? (
                          <div className="w-10 h-10 rounded-lg bg-[var(--color-border)] overflow-hidden shrink-0">
                            <img src={activity.image_url} alt="Proof" className="w-full h-full object-cover" />
                          </div>
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-[var(--color-border)] flex items-center justify-center shrink-0">
                            <span className="text-[var(--color-text-muted)] text-xs">No img</span>
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-[var(--color-text-primary)] capitalize">{activity.activity_type}</p>
                          <p className="text-xs text-[var(--color-text-secondary)] truncate max-w-[150px]">
                            {activity.description || "No description"}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-sm text-slate-300">
                      {new Date(activity.captured_at).toLocaleDateString()}
                      <span className="block text-xs text-[var(--color-text-muted)]">
                        {new Date(activity.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-[var(--color-text-secondary)] font-mono text-xs">
                      {activity.user_id.substring(0, 8)}...
                    </td>
                    <td className="p-4 text-sm text-slate-300">
                      {activity.latitude ? (
                        <>
                          {activity.latitude.toFixed(4)}, {activity.longitude?.toFixed(4)}
                          <span className="block text-xs text-[var(--color-text-muted)]">
                            ±{activity.gps_accuracy?.toFixed(1)}m
                          </span>
                        </>
                      ) : (
                        <span className="text-[var(--color-text-muted)]">N/A</span>
                      )}
                    </td>
                    <td className="p-4">
                      <TrustBadge score={activity.trust_score} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="p-4 border-t border-[var(--color-border)] flex items-center justify-between">
            <span className="text-sm text-[var(--color-text-secondary)]">
              Showing {(data.page - 1) * data.per_page + 1} to Math.min(data.page * data.per_page, data.total) of {data.total}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
              >
                <ChevronLeft size={18} />
              </button>
              <button
                disabled={page === data.total_pages}
                onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
