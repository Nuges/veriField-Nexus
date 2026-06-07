"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  Activity as ActivityIcon, 
  MapPin, 
  ShieldCheck, 
  Leaf, 
  Calendar,
  Sparkles,
  Layers,
  Lock,
  Clock
} from "lucide-react";
import { fetchProperty, fetchPropertyActivities } from "@/lib/api";
import type { Property, Activity } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";

export default function AssetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [asset, setAsset] = useState<Property & { total_activities?: number, avg_trust_score?: number, activity_breakdown?: any } | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const id = params.id as string;
        const [assetData, activitiesData] = await Promise.all([
          fetchProperty(id),
          fetchPropertyActivities(id)
        ]);
        setAsset(assetData);
        setActivities(activitiesData);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [params.id]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] space-y-3">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">
          Retrieving asset specifications...
        </p>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="p-12 text-center max-w-md mx-auto">
        <div className="p-3 bg-red-500/10 rounded-full text-red-500 w-fit mx-auto mb-3">
          <ActivityIcon size={28} />
        </div>
        <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Asset Not Found</h3>
        <p className="text-[var(--color-text-secondary)] text-xs mt-1">The specified property ID is invalid or missing in the registry.</p>
        <button onClick={() => router.back()} className="mt-4 px-4 py-2 bg-[#00B47A]/10 text-[#00B47A] rounded-xl text-xs font-bold border border-[#00B47A]/20">
          Return to Registry
        </button>
      </div>
    );
  }

  const metrics = asset.sustainability_metrics as any || {};

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in-up text-[var(--color-text-primary)]">
      
      {/* 🧭 NAVIGATION */}
      <button 
        onClick={() => router.back()}
        className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 text-xs font-extrabold uppercase tracking-wider"
      >
        <ArrowLeft size={14} /> Return to Assets Directory
      </button>

      {/* 👑 EXECUTIVE TITLE & REGIONAL CONTEXT */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-[var(--color-border)] pb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-2 flex-wrap">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/20">
              {asset.property_type.replace(/_/g, ' ')}
            </span>
            <span className="text-[9px] text-[var(--color-text-muted)] font-semibold flex items-center gap-1">
              <Clock size={11} className="text-[#00B47A]" /> Registered {new Date(asset.created_at || Date.now()).toLocaleDateString()}
            </span>
          </div>
          
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] capitalize">
            {asset.name}
          </h1>
          
          <p className="text-[var(--color-text-secondary)] text-xs flex items-center gap-1.5 mt-2 font-semibold">
            <MapPin size={14} className="text-[#00B47A]" /> 
            <span>{asset.address || "No region/address was registered."}</span>
            {asset.latitude && (
              <span className="text-[9px] font-mono opacity-80 bg-[var(--color-surface)] border border-[var(--color-border)] px-1.5 py-0.5 rounded ml-1.5">
                {asset.latitude.toFixed(6)}°, {asset.longitude?.toFixed(6)}°
              </span>
            )}
          </p>
        </div>

        <div className="text-[10px] font-mono bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-1.5 rounded-xl text-[var(--color-text-secondary)] flex items-center gap-1.5 w-fit shrink-0">
          <span className="font-extrabold text-[#00B47A]">ASSET ID:</span>
          <span className="font-medium truncate max-w-[140px] sm:max-w-none">{asset.id}</span>
        </div>
      </div>

      {/* 📊 CORE METRICS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Total Check-ins */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Registry Sync Logs</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {asset.total_activities || 0}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Telemetry transmissions</p>
          </div>
          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
            <ActivityIcon size={18} />
          </div>
        </div>
        
        {/* Average Trust Score */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Telemetry Integrity</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {asset.avg_trust_score ? Math.round(asset.avg_trust_score) : 'N/A'}<span className="text-xs text-[var(--color-text-muted)]">/100</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Average confidence index</p>
          </div>
          <div className="p-3 bg-purple-500/5 border border-purple-500/10 rounded-xl text-purple-400 shrink-0 group-hover:bg-purple-500 group-hover:text-white transition-all duration-300">
            <ShieldCheck size={18} />
          </div>
        </div>

        {/* Dynamic Carbon Offset */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Calculated Avoided CO₂</p>
            <p className="text-2xl font-black text-blue-400 tracking-tight">
              {metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg.toLocaleString()} kg` : 'N/A'}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Registry issued offset credits</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <Leaf size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 ACTIVITY HISTORY TIMELINE */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
          <div className="flex items-center gap-2">
            <Layers size={16} className="text-[#00B47A]" />
            <h2 className="text-xs font-bold uppercase tracking-wider">Telemetry Verification Logs</h2>
          </div>
          <span className="text-[9px] text-[#00B47A] font-extrabold tracking-wider bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
            Live issuance history
          </span>
        </div>
        
        <div className="divide-y divide-[var(--color-border)]">
          {activities.length === 0 ? (
            <div className="p-12 text-center flex flex-col items-center justify-center gap-2">
              <Lock size={28} className="text-[var(--color-text-muted)] animate-pulse" />
              <span className="text-[var(--color-text-secondary)] text-xs font-semibold">No operational logs logged for this asset yet.</span>
            </div>
          ) : (
            activities.map(activity => (
              <div 
                key={activity.id} 
                onClick={() => router.push(`/dashboard/activities/${activity.id}`)}
                className="p-4.5 flex flex-col sm:flex-row gap-4 items-start sm:items-center hover:bg-[var(--color-background)]/35 transition-colors duration-200 cursor-pointer border-l-2 border-l-transparent hover:border-l-[#00B47A]"
              >
                {activity.image_url ? (
                  <img 
                    src={activity.image_url} 
                    alt="Proof" 
                    className="w-14 h-14 rounded-xl object-cover border border-[var(--color-border)] shadow-sm shrink-0" 
                  />
                ) : (
                  <div className="w-14 h-14 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-text-muted)] shrink-0 shadow-inner">
                    <ActivityIcon size={18} />
                  </div>
                )}
                
                <div className="flex-1 overflow-hidden">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-xs font-bold text-[var(--color-text-primary)] capitalize tracking-tight">
                      {activity.activity_type.replace(/_/g, ' ')}
                    </p>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider shrink-0 ${
                      activity.status === "verified"
                        ? "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20"
                        : activity.status === "flagged"
                        ? "bg-red-500/10 text-red-500 border-red-500/20"
                        : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                    }`}>
                      {activity.status === "verified" ? "Verified" : activity.status === "flagged" ? "Flagged" : "Review"}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-medium line-clamp-1 leading-relaxed">
                    {activity.description || "System check-in parameters verified."}
                  </p>
                </div>
                
                <div className="flex sm:flex-col items-start sm:items-end justify-between sm:justify-center w-full sm:w-auto gap-2.5 pt-2 sm:pt-0 border-t border-[var(--color-border)]/5 sm:border-0 shrink-0">
                  <div className="text-[10px] text-[var(--color-text-muted)] font-extrabold uppercase font-mono bg-[var(--color-background)] border border-[var(--color-border)] px-2.5 py-1 rounded-xl flex items-center gap-1.5 shadow-inner">
                    <Calendar size={12} className="text-[#00B47A]" /> 
                    <span>{new Date(activity.captured_at).toLocaleDateString()}</span>
                  </div>
                  <TrustBadge score={activity.trust_score} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}
