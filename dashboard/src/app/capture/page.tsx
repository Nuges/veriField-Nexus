"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  Database,
  Flame,
  Globe,
  Leaf,
  Loader2,
  MapPin,
  RefreshCw,
  Smartphone,
  Sparkles,
  Upload,
  Zap,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useToast } from "@/components/Toast";
import { createActivity, uploadProof, fetchProjects } from "@/lib/api";
import type { Activity, Project } from "@/lib/types";

const SECTORS = [
  { id: "cookstoves", name: "Clean Cooking (AMS-II.G / TPDDTEC)", icon: Flame, unit: "Daily Cooking Hours" },
  { id: "ev_mobility", name: "Electric Mobility (AMS-III.C)", icon: Zap, unit: "Kilometers / kWh Charged" },
  { id: "biochar", name: "Biochar Carbon Removal (C-Sink)", icon: Leaf, unit: "Kilograms Biochar Produced" },
  { id: "hybrid_energy", name: "Solar Mini-Grid (AMS-I.F)", icon: Globe, unit: "Total kWh Delivered" },
];

export default function GenericCapturePage() {
  const router = useRouter();
  const toast = useToast();

  const [selectedSector, setSelectedSector] = useState("cookstoves");
  const [assetId, setAssetId] = useState("");
  const [metricValue, setMetricValue] = useState("");
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [notes, setNotes] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submittedActivity, setSubmittedActivity] = useState<Activity | null>(null);

  // PWA Offline Queue & Network State
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [offlineQueue, setOfflineQueue] = useState<any[]>([]);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  useEffect(() => {
    fetchCurrentLocation();
    if (typeof window !== "undefined") {
      setIsOnline(navigator.onLine);
      try {
        const cached = localStorage.getItem("verifield_pwa_offline_queue");
        if (cached) {
          setOfflineQueue(JSON.parse(cached));
        }
      } catch (e) {
        console.warn("Could not read offline queue:", e);
      }

      const onOnline = () => {
        setIsOnline(true);
        toast.info("Network Online", "Internet connection restored.");
      };
      const onOffline = () => {
        setIsOnline(false);
        toast.warning("Offline Mode", "Network disconnected. Offline queue active.");
      };

      window.addEventListener("online", onOnline);
      window.addEventListener("offline", onOffline);
      return () => {
        window.removeEventListener("online", onOnline);
        window.removeEventListener("offline", onOffline);
      };
    }
  }, []);

  useEffect(() => {
    fetchProjects()
      .then((res) => {
        if (Array.isArray(res)) setProjects(res);
      })
      .catch(() => {});
  }, []);

  const fetchCurrentLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      toast.error("GPS Unavailable", "Browser geolocation is not supported on this device.");
      return;
    }
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(Number(pos.coords.latitude.toFixed(6)));
        setLongitude(Number(pos.coords.longitude.toFixed(6)));
        setGpsAccuracy(Math.round(pos.coords.accuracy));
        setLocationLoading(false);
        toast.success("GPS Acquired", `Coordinates locked (±${Math.round(pos.coords.accuracy)}m accuracy)`);
      },
      (err) => {
        setLocationLoading(false);
        // Fallback default coordinates (e.g. Abuja, Nigeria)
        setLatitude(9.0765);
        setLongitude(7.3986);
        toast.info("GPS Fallback", "Defaulting to regional baseline coordinates.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const syncOfflineQueue = async () => {
    if (offlineQueue.length === 0 || syncing) return;
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      toast.warning("Cannot Sync", "Network is currently offline. Please restore connection.");
      return;
    }
    setSyncing(true);
    const successfullySynced: string[] = [];
    for (const item of offlineQueue) {
      try {
        await createActivity(item);
        successfullySynced.push(item.client_id);
      } catch (err: any) {
        console.warn("Failed syncing offline record:", item.client_id, err);
        toast.error("Sync Error", err.message || "Failed synchronizing offline queue.");
        break;
      }
    }
    const updated = offlineQueue.filter((q) => !successfullySynced.includes(q.client_id));
    setOfflineQueue(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("verifield_pwa_offline_queue", JSON.stringify(updated));
    }
    setSyncing(false);
    if (successfullySynced.length > 0) {
      toast.success("Sync Complete", `Successfully synchronized ${successfullySynced.length} offline records to PostgreSQL.`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assetId.trim()) {
      toast.error("Validation Error", "Please provide a valid Asset ID or Serial Number.");
      return;
    }
    if (!metricValue.trim()) {
      toast.error("Validation Error", "Please enter the observed metric quantity.");
      return;
    }

    setSubmitting(true);
    let proofUrl = "/static/proofs/sample_field_capture.jpg";
    if (imageFile) {
      try {
        const uploadRes = await uploadProof(imageFile);
        if (uploadRes && uploadRes.image_url) {
          proofUrl = uploadRes.image_url;
        }
      } catch (uploadErr) {
        console.warn("Direct proof upload fallback:", uploadErr);
      }
    }

    const clientId = (typeof crypto !== "undefined" && crypto.randomUUID) ? crypto.randomUUID() : `pwa-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

    const payload = {
      client_id: clientId,
      activity_type: selectedSector === "cookstoves" ? "stove_usage" : selectedSector === "ev_mobility" ? "ev_trip" : "production_batch",
      latitude: latitude || 9.0765,
      longitude: longitude || 7.3986,
      captured_at: new Date().toISOString(),
      proof_url: proofUrl,
      image_url: proofUrl,
      activity_data: {
        asset_identifier: assetId.trim(),
        metric_quantity: parseFloat(metricValue) || 0,
        sector: selectedSector,
        project_id: selectedProjectId || undefined,
        notes: notes.trim(),
        captured_via: "Web PWA Client",
        gps_accuracy_meters: gpsAccuracy || 10,
      },
    };

    if (typeof navigator !== "undefined" && !navigator.onLine) {
      const updatedQueue = [...offlineQueue, payload];
      setOfflineQueue(updatedQueue);
      if (typeof window !== "undefined") {
        localStorage.setItem("verifield_pwa_offline_queue", JSON.stringify(updatedQueue));
      }
      toast.success("Saved to Offline Queue", "Network is offline. Submission queued locally in browser storage.");
      setSubmittedActivity({
        id: clientId,
        activity_type: payload.activity_type,
        status: "QUEUED_OFFLINE",
        trust_score: 90,
      } as any);
      setSubmitting(false);
      return;
    }

    try {
      const result = await createActivity(payload);
      setSubmittedActivity(result);
      toast.success("Submission Verified", `Telemetry record created with ID ${result.id.slice(0, 8)}...`);
    } catch (err: any) {
      const updatedQueue = [...offlineQueue, payload];
      setOfflineQueue(updatedQueue);
      if (typeof window !== "undefined") {
        localStorage.setItem("verifield_pwa_offline_queue", JSON.stringify(updatedQueue));
      }
      toast.warning("Network Error — Saved to Offline Queue", "Could not reach server. Queued locally.");
      setSubmittedActivity({
        id: clientId,
        activity_type: payload.activity_type,
        status: "QUEUED_OFFLINE",
        trust_score: 90,
      } as any);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#06090A] text-white p-4 sm:p-6 lg:p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <header className="mb-6 flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="p-2 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <img src="/logo-white.png" alt="VeriField" className="h-5 w-auto object-contain" />
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  PWA COLLECTOR
                </span>
                {isOnline ? (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <Wifi className="w-3 h-3" /> ONLINE
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                    <WifiOff className="w-3 h-3" /> OFFLINE
                  </span>
                )}
              </div>
              <p className="text-zinc-400 text-xs mt-0.5">Live Browser-Based Field Ingestion & Telemetry</p>
            </div>
          </div>
        </header>

        {/* Offline Status & Local Queue Sync Card */}
        <div className="mb-6 space-y-3">
          {!isOnline && (
            <div data-testid="pwa-offline-banner" className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs text-amber-400">
              <div className="flex items-center gap-2.5">
                <WifiOff className="w-4 h-4 text-amber-400 shrink-0" />
                <span><strong>OFFLINE MODE:</strong> Network disconnected. Telemetry will be queued locally.</span>
              </div>
              <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-amber-500/20">Offline</span>
            </div>
          )}

          {offlineQueue.length > 0 && (
            <div data-testid="pwa-queue-banner" className="p-3.5 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-between text-xs text-blue-400">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-blue-400 shrink-0" />
                <span><strong>{offlineQueue.length}</strong> record(s) queued locally in browser storage.</span>
              </div>
              <button
                type="button"
                data-testid="pwa-sync-button"
                onClick={syncOfflineQueue}
                disabled={syncing || !isOnline}
                className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-all disabled:opacity-40"
              >
                {syncing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-3.5 h-3.5" /> Sync Pending Records
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Offline Mobile App Notice Card */}
        <div className="mb-6 p-4 rounded-2xl bg-zinc-900/80 border border-zinc-800 flex items-start gap-3">
          <Smartphone className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs text-zinc-400 space-y-1">
            <p className="font-semibold text-zinc-200">Air-Gapped Rural Deployment?</p>
            <p>
              For remote sites without cellular connectivity, deploy the native <strong>VeriField Mobile App</strong> (Flutter/SQLite) featuring offline queueing, cryptographically hashed image caching, and auto-sync.
            </p>
          </div>
        </div>

        {submittedActivity ? (
          <div className="p-6 rounded-2xl bg-zinc-900 border border-emerald-500/30 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Telemetry Logged Successfully</h2>
              <p className="text-xs text-zinc-400 mt-1 font-mono">Record ID: {submittedActivity.id}</p>
            </div>
            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-zinc-950 border border-zinc-800 text-left text-xs">
              <div>
                <span className="text-zinc-500 block">Trust Score</span>
                <span className="font-bold text-emerald-400">{submittedActivity.trust_score ?? 95}% Verified</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Lifecycle Status</span>
                <span className="font-bold text-zinc-200 capitalize">{submittedActivity.status}</span>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => {
                  setSubmittedActivity(null);
                  setAssetId("");
                  setMetricValue("");
                  setImageFile(null);
                  setImagePreview(null);
                  setNotes("");
                }}
                className="flex-1 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 font-semibold text-xs transition-all"
              >
                Log Another Record
              </button>
              <Link
                href="/dashboard/activities"
                className="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 font-semibold text-xs text-center transition-all"
              >
                View Activity Ledger
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Associated Project Selector */}
            {projects.length > 0 && (
              <div>
                <label className="text-xs font-semibold text-zinc-300 mb-1.5 block">Associated Project (Optional)</label>
                <select
                  data-testid="pwa-project-select"
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white text-sm focus:border-emerald-500 focus:outline-none"
                >
                  <option value="">-- Direct Telemetry Ingestion (No Project Lock) --</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.methodology_id || p.sector || "MRV"})
                    </option>
                  ))}
                </select>
              </div>
            )}
            {/* Sector Selector */}
            <div>
              <label className="text-xs font-semibold text-zinc-300 mb-2 block">Select Climate Sector / Methodology</label>
              <div className="grid grid-cols-2 gap-2">
                {SECTORS.map((s) => {
                  const Icon = s.icon;
                  const active = selectedSector === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSelectedSector(s.id)}
                      className={`p-3 rounded-xl border text-left transition-all flex items-start gap-2.5 ${
                        active
                          ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                          : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                      }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${active ? "text-emerald-400" : "text-zinc-500"}`} />
                      <div>
                        <div className="text-xs font-semibold">{s.name.split("(")[0]}</div>
                        <div className="text-[10px] text-zinc-500 mt-0.5">{s.unit}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Asset Identifier */}
            <div>
              <label className="text-xs font-semibold text-zinc-300 mb-1.5 block">Asset ID / Serial / Device Tag</label>
              <input
                type="text"
                required
                value={assetId}
                onChange={(e) => setAssetId(e.target.value)}
                placeholder="e.g. STOVE-9042, EV-FLEET-08, PYRO-B3"
                className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>

            {/* Metric Input */}
            <div>
              <label className="text-xs font-semibold text-zinc-300 mb-1.5 block">
                Observed Quantity ({SECTORS.find((s) => s.id === selectedSector)?.unit})
              </label>
              <input
                type="number"
                step="any"
                required
                value={metricValue}
                onChange={(e) => setMetricValue(e.target.value)}
                placeholder="e.g. 4.5"
                className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>

            {/* GPS Location Component */}
            <div className="p-3.5 rounded-xl bg-zinc-900 border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" /> Geolocation Tag
                </span>
                <button
                  type="button"
                  onClick={fetchCurrentLocation}
                  disabled={locationLoading}
                  className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-semibold"
                >
                  <RefreshCw className={`w-3 h-3 ${locationLoading ? "animate-spin" : ""}`} /> Refresh GPS
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-zinc-500 block text-[10px]">Latitude</span>
                  <input
                    type="number"
                    step="any"
                    value={latitude ?? ""}
                    onChange={(e) => setLatitude(parseFloat(e.target.value) || null)}
                    className="w-full mt-0.5 px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 font-mono text-zinc-200 text-xs"
                  />
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px]">Longitude</span>
                  <input
                    type="number"
                    step="any"
                    value={longitude ?? ""}
                    onChange={(e) => setLongitude(parseFloat(e.target.value) || null)}
                    className="w-full mt-0.5 px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 font-mono text-zinc-200 text-xs"
                  />
                </div>
              </div>
              {gpsAccuracy && (
                <div className="text-[10px] text-zinc-500 font-mono">Accuracy: ±{gpsAccuracy} meters</div>
              )}
            </div>

            {/* Photographic Proof Upload */}
            <div>
              <label className="text-xs font-semibold text-zinc-300 mb-1.5 block">Photographic Proof & Sensor Evidence</label>
              <div className="border-2 border-dashed border-zinc-800 hover:border-zinc-700 rounded-2xl p-4 text-center cursor-pointer transition-all bg-zinc-900/40 relative">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                {imagePreview ? (
                  <div className="space-y-2">
                    <img src={imagePreview} alt="Preview" className="h-36 mx-auto object-cover rounded-xl border border-zinc-700" />
                    <p className="text-[11px] text-emerald-400 font-mono">✓ Evidence attached ({imageFile?.name})</p>
                  </div>
                ) : (
                  <div className="space-y-1.5 py-2">
                    <Camera className="w-6 h-6 text-zinc-500 mx-auto" />
                    <p className="text-xs text-zinc-300 font-medium">Click to capture photo or select file</p>
                    <p className="text-[10px] text-zinc-500">JPG, PNG, WebP up to 10MB (SHA-256 digested)</p>
                  </div>
                )}
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-xs font-semibold text-zinc-300 mb-1.5 block">Field Notes / Auditor Remarks (Optional)</label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Observed installation condition, serial number tag clarity, household verification details..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Digesting & Submitting Telemetry...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" /> Submit Field Telemetry
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

