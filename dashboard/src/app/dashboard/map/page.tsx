// =============================================================================
// VeriField Nexus — Map View Page
// =============================================================================
// Interactive map showing activity locations color-coded by trust score.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { APIProvider, Map, AdvancedMarker, Pin } from "@vis.gl/react-google-maps";
import { fetchActivities } from "@/lib/api";
import type { Activity } from "@/lib/types";

// Requires NEXT_PUBLIC_GOOGLE_MAPS_KEY in .env.local
const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || "";

export default function MapPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

  useEffect(() => {
    async function loadLocations() {
      try {
        // Fetch a large batch of recent activities for the map
        const res = await fetchActivities({ per_page: 500 });
        // Filter out activities without GPS data
        setActivities(res.activities.filter(a => a.latitude !== null && a.longitude !== null));
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadLocations();
  }, []);

  const getPinColor = (score: number | null) => {
    if (score === null) return "#64748B"; // slate
    if (score >= 80) return "#10B981"; // emerald
    if (score >= 50) return "#F59E0B"; // amber
    return "#EF4444"; // red
  };

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col space-y-4">
      <div className="animate-fade-in-up shrink-0">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Geospatial View</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">Map of verified climate activities</p>
      </div>

      <div className="flex-1 bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden relative animate-fade-in-up animation-delay-100">
        {!MAPS_KEY ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-[var(--color-surface)]/80 z-10">
            <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
              <span className="text-red-500 text-2xl font-bold">!</span>
            </div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">Google Maps Key Required</h3>
            <p className="text-[var(--color-text-secondary)] max-w-md text-sm">
              Please add <code className="bg-[var(--color-card)] px-1 py-0.5 rounded text-emerald-400">NEXT_PUBLIC_GOOGLE_MAPS_KEY</code> to your .env.local file to enable the map view.
            </p>
          </div>
        ) : (
          <APIProvider apiKey={MAPS_KEY}>
            <Map
              defaultCenter={{ lat: 0, lng: 0 }}
              defaultZoom={2}
              mapId="verifield_nexus_map"
              disableDefaultUI={true}
              className="w-full h-full"
            >
              {activities.map((activity) => (
                <AdvancedMarker
                  key={activity.id}
                  position={{ lat: activity.latitude!, lng: activity.longitude! }}
                  onClick={() => setSelectedActivity(activity)}
                >
                  <Pin 
                    background={getPinColor(activity.trust_score)} 
                    borderColor={getPinColor(activity.trust_score)} 
                    glyphColor="#fff"
                  />
                </AdvancedMarker>
              ))}
            </Map>
          </APIProvider>
        )}

        {/* Legend Overlay */}
        <div className="absolute bottom-6 right-6 bg-[var(--color-card)]/90 backdrop-blur border border-[var(--color-border)] rounded-xl p-4 shadow-xl z-10">
          <h4 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">Trust Legend</h4>
          <div className="space-y-2">
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500"></div><span className="text-sm text-slate-200">Verified (80-100)</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-amber-500"></div><span className="text-sm text-slate-200">Review (50-79)</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-red-500"></div><span className="text-sm text-slate-200">Flagged (0-49)</span></div>
          </div>
        </div>

        {/* Selected Activity Detail Overlay */}
        {selectedActivity && (
          <div className="absolute top-6 right-6 w-80 bg-[var(--color-card)]/95 backdrop-blur border border-[var(--color-border)] rounded-2xl shadow-2xl z-20 overflow-hidden animate-fade-in-up">
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
              <h3 className="font-semibold text-[var(--color-text-primary)] capitalize">{selectedActivity.activity_type} Activity</h3>
              <button onClick={() => setSelectedActivity(null)} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">✕</button>
            </div>
            {selectedActivity.image_url && (
              <img src={selectedActivity.image_url} alt="Activity" className="w-full h-40 object-cover" />
            )}
            <div className="p-4 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--color-text-secondary)]">Score</span>
                <span className="font-bold text-emerald-400">{selectedActivity.trust_score ? Math.round(selectedActivity.trust_score) : 'N/A'}/100</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--color-text-secondary)]">Date</span>
                <span className="text-sm text-slate-200">{new Date(selectedActivity.captured_at).toLocaleDateString()}</span>
              </div>
              {selectedActivity.description && (
                <div className="pt-2 border-t border-[var(--color-border)]">
                  <p className="text-xs text-[var(--color-text-secondary)]">{selectedActivity.description}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
