"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Activity as ActivityIcon, MapPin, ShieldCheck, Leaf, Calendar } from "lucide-react";
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
    return <div className="p-12 text-center text-[var(--color-text-secondary)]">Loading asset details...</div>;
  }

  if (!asset) {
    return <div className="p-12 text-center text-red-400">Asset not found.</div>;
  }

  const metrics = asset.sustainability_metrics as any || {};

  return (
    <div className="space-y-6">
      <button 
        onClick={() => router.back()}
        className="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        <ArrowLeft size={18} /> Back to Assets
      </button>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="px-2.5 py-1 rounded-md bg-[var(--color-card)] text-emerald-400 text-xs font-medium uppercase tracking-wider border border-[var(--color-border)]">
              {asset.property_type}
            </span>
            <span className="text-[var(--color-text-muted)] text-sm font-mono">{asset.id.split('-')[0]}</span>
          </div>
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)] tracking-tight">{asset.name}</h1>
          <p className="text-[var(--color-text-secondary)] flex items-center gap-2 mt-2">
            <MapPin size={16} /> {asset.address || "No precise address"} 
            {asset.latitude && <span className="text-xs ml-2 opacity-60">({asset.latitude.toFixed(4)}, {asset.longitude?.toFixed(4)})</span>}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in-up animation-delay-100">
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <ActivityIcon size={20} className="text-blue-400" />
            <h3 className="text-slate-300 font-medium">Total Check-ins</h3>
          </div>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">{asset.total_activities || 0}</p>
        </div>
        
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck size={20} className="text-emerald-400" />
            <h3 className="text-slate-300 font-medium">Avg Trust Score</h3>
          </div>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">{asset.avg_trust_score ? Math.round(asset.avg_trust_score) : 'N/A'}</p>
        </div>

        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <Leaf size={20} className="text-green-400" />
            <h3 className="text-slate-300 font-medium">Carbon Offset</h3>
          </div>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">{metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg} kg` : 'N/A'}</p>
        </div>
      </div>

      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-200">
        <div className="p-5 border-b border-[var(--color-border)]">
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Activity History</h3>
        </div>
        <div className="divide-y divide-[var(--color-border)]">
          {activities.length === 0 ? (
            <div className="p-8 text-center text-[var(--color-text-secondary)]">No activities logged for this asset yet.</div>
          ) : (
            activities.map(activity => (
              <div key={activity.id} className="p-5 flex flex-col md:flex-row gap-4 items-start md:items-center hover:bg-[var(--color-surface)] transition-colors">
                {activity.image_url ? (
                  <img src={activity.image_url} alt="Proof" className="w-16 h-16 rounded-xl object-cover border border-[var(--color-border)]" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
                    <ActivityIcon size={20} className="text-[var(--color-text-muted)]" />
                  </div>
                )}
                <div className="flex-1">
                  <p className="text-[var(--color-text-primary)] font-medium capitalize">{activity.activity_type}</p>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1">{activity.description || "Routine check-in"}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm">
                    <Calendar size={14} /> {new Date(activity.captured_at).toLocaleDateString()}
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
