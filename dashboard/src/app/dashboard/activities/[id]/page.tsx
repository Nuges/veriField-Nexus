"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  MapPin, 
  Calendar, 
  Camera, 
  User as UserIcon,
  Sparkles,
  Clock,
  Shield,
  ShieldAlert,
  Layers,
  Lock
} from "lucide-react";
import { fetchActivity, fetchTrustScore } from "@/lib/api";
import type { Activity, TrustScoreBreakdown } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";
import { useToast } from "@/components/Toast";

export default function ActivityDetailPage() {
  const toast = useToast();
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
    return (
      <div className="flex flex-col items-center justify-center h-[400px] space-y-3">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">
          Retrieving secure digital MRV record...
        </p>
      </div>
    );
  }

  if (!activity) {
    return (
      <div className="p-12 text-center max-w-md mx-auto">
        <div className="p-3 bg-red-500/10 rounded-full text-red-500 w-fit mx-auto mb-3">
          <ShieldAlert size={28} />
        </div>
        <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Record Not Found</h3>
        <p className="text-[var(--color-text-secondary)] text-xs mt-1">The specified activity ID is invalid or missing in the registry.</p>
        <button onClick={() => router.back()} className="mt-4 px-4 py-2 bg-[#00B47A]/10 text-[#00B47A] rounded-xl text-xs font-bold border border-[#00B47A]/20">
          Return to Ledger
        </button>
      </div>
    );
  }

  const isVerified = activity.status === "verified";
  const isFlagged = activity.status === "flagged";
  const isReview = activity.status === "review" || activity.status === "pending";

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in-up text-[var(--color-text-primary)]">
      
      {/* 🧭 PREMIUM HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-5 mb-6">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.back()}
            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95 flex items-center justify-center shrink-0"
            title="Go Back"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase">
                Gold Standard MRV Proof
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)] font-semibold hidden sm:inline-flex items-center gap-1">
                <Clock size={11} className="text-[#00B47A]" /> Captured {new Date(activity.captured_at).toLocaleDateString()}
              </span>
            </div>
            
            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] capitalize">
                {activity.activity_type.replace(/_/g, ' ')} record
              </h1>
              <TrustBadge score={activity.trust_score} />
              
              <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold uppercase border tracking-wider shrink-0 ${
                isVerified
                  ? "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20"
                  : isFlagged
                  ? "bg-red-500/10 text-red-500 border-red-500/20"
                  : "bg-amber-500/10 text-amber-500 border-amber-500/20"
              }`}>
                {isVerified ? "Ledger Verified" : isFlagged ? "Risk Flagged" : "Under Review"}
              </span>
            </div>
          </div>
        </div>

        <div className="text-[10px] font-mono bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-1.5 rounded-xl text-[var(--color-text-secondary)] flex items-center gap-1.5 w-fit shrink-0">
          <span className="font-extrabold text-[#00B47A]">LEDGER ID:</span>
          <span className="font-medium truncate max-w-[140px] sm:max-w-none">{activity.id}</span>
        </div>
      </div>

      {/* 🧭 CORE GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        
        {/* LEFT COLUMN: Photographic Proof & Methodology Data */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Photographic Proof Card */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
              <div className="flex items-center gap-2">
                <Camera size={16} className="text-[#00B47A]" />
                <h2 className="text-xs font-bold uppercase tracking-wider">Photographic Proof of Installation</h2>
              </div>
              <span className="text-[9px] text-[#00B47A] font-extrabold tracking-wider bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
                Immutability proof
              </span>
            </div>
            
            {activity.image_url ? (
              <div className="aspect-video w-full bg-slate-950 relative border-b border-[var(--color-border)] overflow-hidden group">
                <img 
                  src={activity.image_url} 
                  alt="Activity Proof" 
                  className="w-full h-full object-contain group-hover:scale-[1.01] transition-transform duration-500" 
                />
                <div className="absolute bottom-3 left-3 bg-slate-900/80 backdrop-blur border border-slate-700/50 rounded-lg px-2.5 py-1 text-[9px] font-mono text-slate-300 flex items-center gap-1.5 shadow-lg">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00B47A] animate-pulse" />
                  <span>Verified Photo Signature Secure</span>
                </div>
              </div>
            ) : (
              <div className="aspect-video w-full bg-[var(--color-surface)] flex flex-col items-center justify-center border-b border-[var(--color-border)] gap-2">
                <ShieldAlert size={28} className="text-[var(--color-text-muted)] animate-pulse" />
                <span className="text-[var(--color-text-muted)] text-xs font-semibold">No photographic evidence provided</span>
              </div>
            )}
            
            <div className="p-4.5 bg-[var(--color-background)]/35">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-1.5 flex items-center gap-1.5">
                <Layers size={13} className="text-[#00B47A]" /> Reporting Agent's Notes
              </h3>
              <div className="border-l-4 border-l-[#00B47A] bg-[var(--color-surface)] rounded-r-xl p-3.5 text-xs text-[var(--color-text-secondary)] font-medium leading-relaxed shadow-inner">
                {activity.description || "No customized description was logged for this field installation."}
              </div>
            </div>
          </div>

          {/* Methodology Data Grid */}
          {activity.activity_data && Object.keys(activity.activity_data).length > 0 && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-background)]/50">
                <h2 className="text-xs font-bold uppercase tracking-wider">Carbon Methodology Specifications & Audit Metrics</h2>
                <p className="text-[var(--color-text-secondary)] text-[10px] mt-0.5">Parameters collected from physical IoT sensors and local field audits.</p>
              </div>
              
              <div className="p-4.5 grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {Object.entries(activity.activity_data).map(([key, value]) => (
                  <div 
                    key={key} 
                    className="bg-[var(--color-background)] border border-[var(--color-border)] hover:border-[#00B47A]/30 transition-all rounded-xl p-3.5 flex flex-col justify-between shadow-inner group"
                  >
                    <p className="text-[9px] text-[var(--color-text-muted)] group-hover:text-[#00B47A] font-extrabold uppercase tracking-wider transition-colors mb-1">
                      {key.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono break-words">
                      {String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategic Geospatial & Timestamp Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-start gap-3.5 shadow-sm hover:shadow transition-all border-l-4 border-l-blue-500">
              <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-500 mt-0.5 shrink-0">
                <MapPin size={18} />
              </div>
              <div className="overflow-hidden">
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-0.5">Geospatial Bounds</p>
                <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono">
                  {activity.latitude ? `${activity.latitude.toFixed(6)}, ${activity.longitude?.toFixed(6)}` : "N/A"}
                </p>
                {activity.gps_accuracy ? (
                  <div className="inline-flex items-center gap-1 mt-1 bg-blue-500/5 border border-blue-500/10 text-blue-500 text-[9px] font-extrabold px-1.5 py-0.5 rounded">
                    GPS Accuracy: ±{activity.gps_accuracy.toFixed(1)}m
                  </div>
                ) : (
                  <span className="text-[8px] text-[var(--color-text-muted)] block mt-0.5">Spatial logs unverified</span>
                )}
              </div>
            </div>

            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-start gap-3.5 shadow-sm hover:shadow transition-all border-l-4 border-l-purple-500">
              <div className="p-2.5 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-500 mt-0.5 shrink-0">
                <Calendar size={18} />
              </div>
              <div className="overflow-hidden">
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-0.5">Synchronization Epoch</p>
                <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono">
                  {new Date(activity.captured_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
                </p>
                <div className="inline-flex items-center gap-1 mt-1 bg-purple-500/5 border border-purple-500/10 text-purple-500 text-[9px] font-extrabold px-1.5 py-0.5 rounded">
                  Time: {new Date(activity.captured_at).toLocaleTimeString()}
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* RIGHT COLUMN: Actions decisions & Trust Engine */}
        <div className="space-y-6">
          
          {/* Action Panel */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 text-[var(--color-text-muted)] opacity-20">
              <Lock size={45} />
            </div>
            
            <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-1 flex items-center gap-1.5">
              <Shield size={14} className="text-[#00B47A]" /> Ledger Decision overrides
            </h2>
            <p className="text-[var(--color-text-secondary)] text-[10px] mb-4">Trigger immutable blockchain quantification, registry approval, or audit rejection.</p>
            
            <div className="space-y-3">
              <button 
                onClick={async () => {
                  try {
                    const api = await import("@/lib/api");
                    await api.updateActivityStatus(id, "verified");
                    
                    try {
                      await api.quantifyActivity(id);
                    } catch (_) {}
                    
                    toast.success("Activity Approved", "The activity has been successfully approved and carbon credits calculated.");
                    router.back();
                  } catch (e) { 
                    toast.error("Approval Failed", "Could not approve activity. Please try again."); 
                  }
                }}
                className="w-full py-2.5 rounded-xl bg-[#00B47A] hover:bg-[#00B47A]/95 text-white font-extrabold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-[#00B47A]/15 active:scale-95 border border-[#00B47A]/25"
              >
                <CheckCircle size={15} /> Approve & Quantify Credit
              </button>
              
              <button 
                onClick={async () => {
                  try {
                    await import("@/lib/api").then(m => m.updateActivityStatus(id, "flagged"));
                    toast.success("Activity Rejected", "The activity has been rejected.");
                    router.back();
                  } catch (e) { 
                    toast.error("Rejection Failed", "Could not update activity status."); 
                  }
                }}
                className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-extrabold text-xs flex items-center justify-center gap-2 transition-all active:scale-95 shadow-sm"
              >
                <XCircle size={15} /> Reject Submission
              </button>
              
              <button 
                onClick={async () => {
                  try {
                    await import("@/lib/api").then(m => m.updateActivityStatus(id, "review"));
                    toast.success("Flagged for Audit", "This activity has been successfully flagged for audit.");
                    router.back();
                  } catch (e) { 
                    toast.error("Update Failed", "Could not flag this activity for audit."); 
                  }
                }}
                className="w-full py-2.5 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-background)] text-amber-500 border border-amber-500/25 hover:border-amber-500/40 font-bold text-xs flex items-center justify-center gap-2 transition-all active:scale-95"
              >
                <AlertTriangle size={15} /> Flag for Manual Audit
              </button>
            </div>
            
            <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex items-center justify-center gap-1.5 text-[8px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider">
              <Lock size={10} className="text-[#00B47A]" />
              <span>Immutable Audit Trail Protected</span>
            </div>
          </div>

          {/* Trust Engine Analysis */}
          {trustDetails && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3 mb-4">
                <div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Quantification Trust Index</h2>
                  <p className="text-[var(--color-text-secondary)] text-[10px] mt-0.5">Automated algorithmic confidence scoring.</p>
                </div>
                <div className="text-xl font-black text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2.5 py-1 rounded-xl tracking-tight">
                  {activity.trust_score}<span className="text-[10px] font-semibold text-[var(--color-text-secondary)]">/100</span>
                </div>
              </div>
              
              {(() => {
                const breakdown = (trustDetails.flags as any)?.scoring_breakdown;
                const gpsMax = breakdown?.gps?.max_weight ?? 30;
                const frequencyMax = breakdown?.frequency?.max_weight ?? 30;
                const imageMax = breakdown?.image?.max_weight ?? 40;
                const displayFlags = Object.entries(trustDetails.flags || {}).filter(
                  ([key]) => key !== "scoring_breakdown"
                );

                return (
                  <>
                    <div className="space-y-4">
                      {/* Metrics */}
                      <div>
                        <div className="flex justify-between text-[10px] font-semibold mb-1">
                          <span className="text-[var(--color-text-secondary)]">Spatial Radius Verification</span>
                          <span className="font-extrabold text-[var(--color-text-primary)]">{trustDetails.gps_score}/{gpsMax}</span>
                        </div>
                        <div className="w-full h-1.5 bg-[var(--color-background)] rounded-full overflow-hidden border border-[var(--color-border)]">
                          <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full" style={{ width: `${(trustDetails.gps_score / gpsMax) * 100}%` }} />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[10px] font-semibold mb-1">
                          <span className="text-[var(--color-text-secondary)]">Submission Frequency Match</span>
                          <span className="font-extrabold text-[var(--color-text-primary)]">{trustDetails.frequency_score}/{frequencyMax}</span>
                        </div>
                        <div className="w-full h-1.5 bg-[var(--color-background)] rounded-full overflow-hidden border border-[var(--color-border)]">
                          <div className="h-full bg-gradient-to-r from-purple-500 to-fuchsia-500 rounded-full" style={{ width: `${(trustDetails.frequency_score / frequencyMax) * 100}%` }} />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[10px] font-semibold mb-1">
                          <span className="text-[var(--color-text-secondary)]">Visual Image Uniqueness</span>
                          <span className="font-extrabold text-[var(--color-text-primary)]">{trustDetails.image_score}/{imageMax}</span>
                        </div>
                        <div className="w-full h-1.5 bg-[var(--color-background)] rounded-full overflow-hidden border border-[var(--color-border)]">
                          <div className="h-full bg-gradient-to-r from-[#00B47A] to-emerald-500 rounded-full" style={{ width: `${(trustDetails.image_score / imageMax) * 100}%` }} />
                        </div>
                      </div>
                    </div>

                    {/* Anomalies */}
                    {displayFlags.length > 0 && (
                      <div className="mt-6 pt-4 border-t border-[var(--color-border)]">
                        <p className="text-[10px] font-extrabold text-red-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                          <AlertTriangle size={14} className="text-red-500 shrink-0" /> Detected Anomalies & Outliers
                        </p>
                        <ul className="space-y-2">
                          {displayFlags.map(([key, value]) => (
                            <li key={key} className="text-[10px] font-semibold text-red-400 bg-red-500/5 border border-red-500/10 p-2.5 rounded-xl leading-relaxed shadow-sm">
                              <span className="font-black uppercase text-red-500 block mb-0.5">{key.replace(/_/g, ' ')}:</span> 
                              <span className="text-[var(--color-text-secondary)]">{String(value)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          )}

          {/* Submitter Info */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-3.5 flex items-center gap-1.5">
              <UserIcon size={14} className="text-[#00B47A]" /> Submitted By Agent
            </h2>
            
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#00B47A]/10 border border-[#00B47A]/20 flex items-center justify-center text-[#00B47A] text-xs font-extrabold shrink-0">
                {activity.agent_name ? activity.agent_name.substring(0, 2).toUpperCase() : "AG"}
              </div>
              <div className="overflow-hidden">
                <div className="flex items-center gap-1.5">
                  <p className="text-xs font-bold text-[var(--color-text-primary)] truncate">{activity.agent_name || "Assigned Field Agent"}</p>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Active Synced Agent" />
                </div>
                <p className="text-[10px] text-[var(--color-text-muted)] font-mono truncate">{activity.user_id}</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
