"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle, XCircle, AlertTriangle, MapPin, Calendar, Camera, User as UserIcon } from "lucide-react";
import { fetchActivity, fetchTrustScore } from "@/lib/api";
import type { Activity, TrustScoreBreakdown } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";

export default function ActivityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [activity, setActivity] = useState<Activity | null>(null);
  const [trustDetails, setTrustDetails] = useState<TrustScoreBreakdown | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [activityData, trustData] = await Promise.all([
          fetchActivity(id),
          fetchTrustScore(id).catch(() => null)
        ]);
        setActivity(activityData);
        setTrustDetails(trustData);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [id]);

  if (isLoading) {
    return <div className="p-8 text-center text-[var(--color-text-secondary)]">Loading activity details...</div>;
  }

  if (!activity) {
    return <div className="p-8 text-center text-red-500">Activity not found.</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button 
          onClick={() => router.back()}
          className="p-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] transition-colors"
        >
          <ArrowLeft size={20} className="text-[var(--color-text-primary)]" />
        </button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight capitalize">
              {activity.activity_type} Activity
            </h1>
            <TrustBadge score={activity.trust_score} />
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm font-mono mt-1">ID: {activity.id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Media & Core Data */}
        <div className="lg:col-span-2 space-y-6">
          {/* Media Evidence */}
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
            <div className="p-4 border-b border-[var(--color-border)] flex items-center gap-2">
              <Camera size={18} className="text-[var(--color-text-secondary)]" />
              <h2 className="font-semibold text-[var(--color-text-primary)]">Photographic Evidence</h2>
            </div>
            {activity.image_url ? (
              <div className="aspect-video w-full bg-black relative">
                <img src={activity.image_url} alt="Activity Proof" className="w-full h-full object-contain" />
              </div>
            ) : (
              <div className="aspect-video w-full bg-[var(--color-surface)] flex items-center justify-center">
                <span className="text-[var(--color-text-muted)]">No image provided</span>
              </div>
            )}
            <div className="p-4 bg-[var(--color-surface)]">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">Agent's Notes</h3>
              <p className="text-[var(--color-text-secondary)] text-sm">{activity.description || "No description provided."}</p>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-4 flex items-start gap-3">
              <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500 mt-0.5"><MapPin size={18} /></div>
              <div>
                <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1">GPS Location</p>
                <p className="text-sm text-[var(--color-text-primary)]">
                  {activity.latitude ? `${activity.latitude.toFixed(6)}, ${activity.longitude?.toFixed(6)}` : "N/A"}
                </p>
                {activity.gps_accuracy && (
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1">Accuracy: ±{activity.gps_accuracy.toFixed(1)}m</p>
                )}
              </div>
            </div>

            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-4 flex items-start gap-3">
              <div className="p-2 bg-purple-500/10 rounded-lg text-purple-500 mt-0.5"><Calendar size={18} /></div>
              <div>
                <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Timestamp</p>
                <p className="text-sm text-[var(--color-text-primary)]">{new Date(activity.captured_at).toLocaleDateString()}</p>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1">{new Date(activity.captured_at).toLocaleTimeString()}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Trust Engine & Actions */}
        <div className="space-y-6">
          
          {/* Action Panel */}
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6">
            <h2 className="font-semibold text-[var(--color-text-primary)] mb-4">Review Action</h2>
            <div className="space-y-3">
              <button 
                onClick={async () => {
                  try {
                    await import("@/lib/api").then(m => m.updateActivityStatus(id, "verified"));
                    alert("Activity approved!");
                    router.back();
                  } catch (e) { alert("Failed to update"); }
                }}
                className="w-full py-3 rounded-xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 hover:bg-emerald-500/20 flex items-center justify-center gap-2 transition-colors font-medium"
              >
                <CheckCircle size={18} /> Approve
              </button>
              <button 
                onClick={async () => {
                  try {
                    await import("@/lib/api").then(m => m.updateActivityStatus(id, "flagged"));
                    alert("Activity rejected!");
                    router.back();
                  } catch (e) { alert("Failed to update"); }
                }}
                className="w-full py-3 rounded-xl bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 flex items-center justify-center gap-2 transition-colors font-medium"
              >
                <XCircle size={18} /> Reject
              </button>
              <button 
                onClick={async () => {
                  try {
                    await import("@/lib/api").then(m => m.updateActivityStatus(id, "review"));
                    alert("Flagged for audit");
                    router.back();
                  } catch (e) { alert("Failed to update"); }
                }}
                className="w-full py-3 rounded-xl bg-amber-500/10 text-amber-500 border border-amber-500/20 hover:bg-amber-500/20 flex items-center justify-center gap-2 transition-colors font-medium"
              >
                <AlertTriangle size={18} /> Flag for Audit
              </button>
            </div>
          </div>

          {/* Trust Engine Analysis */}
          {trustDetails && (
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-[var(--color-text-primary)]">Trust Analysis</h2>
                <span className="text-2xl font-bold text-[var(--color-text-primary)]">{activity.trust_score}</span>
              </div>
              
              <div className="space-y-4">
                {/* Metrics */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--color-text-secondary)]">Location Trust</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{trustDetails.location_score}/30</span>
                  </div>
                  <div className="w-full h-1.5 bg-[var(--color-surface)] rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(trustDetails.location_score / 30) * 100}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--color-text-secondary)]">Time Trust</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{trustDetails.time_score}/20</span>
                  </div>
                  <div className="w-full h-1.5 bg-[var(--color-surface)] rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(trustDetails.time_score / 20) * 100}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--color-text-secondary)]">Image Uniqueness</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{trustDetails.image_score}/30</span>
                  </div>
                  <div className="w-full h-1.5 bg-[var(--color-surface)] rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${(trustDetails.image_score / 30) * 100}%` }} />
                  </div>
                </div>
              </div>

              {/* Anomalies */}
              {trustDetails.flags.length > 0 && (
                <div className="mt-6 pt-4 border-t border-[var(--color-border)]">
                  <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-1">
                    <AlertTriangle size={14} /> Detected Anomalies
                  </p>
                  <ul className="space-y-2">
                    {trustDetails.flags.map((flag, idx) => (
                      <li key={idx} className="text-xs text-[var(--color-text-secondary)] bg-red-500/5 border border-red-500/10 p-2 rounded-lg">
                        • {flag}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Submitter Info */}
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6">
            <h2 className="font-semibold text-[var(--color-text-primary)] mb-4">Submitted By</h2>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-text-secondary)]">
                <UserIcon size={18} />
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">Agent</p>
                <p className="text-xs text-[var(--color-text-muted)] font-mono truncate">{activity.user_id}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
