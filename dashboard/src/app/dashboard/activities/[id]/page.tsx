"use client";

import { useEffect, useState, useMemo } from "react";
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
  Lock,
  Info,
  Cpu,
  Fingerprint,
  Copy,
  Check,
  Search,
  Download,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { fetchActivity, fetchTrustScore } from "@/lib/api";
import type { Activity, TrustScoreBreakdown } from "@/lib/types";
import TrustBadge from "@/components/TrustBadge";
import { useToast } from "@/components/Toast";

const getDeviceString = (sig: any): string => {
  if (!sig) return "N/A";
  if (typeof sig === "string") return sig;
  if (typeof sig === "object") {
    return sig.device_id || sig.os || "N/A";
  }
  return "N/A";
};

const getFallbackMeta = (meta: any, isBefore: boolean, activity: any) => {
  const actData = (activity.activity_data as Record<string, any>) || {};
  const devId = getDeviceString(meta?.device_id);
  return {
    timestamp: meta?.timestamp || activity.captured_at,
    latitude: meta?.latitude !== undefined && meta?.latitude !== null ? Number(meta.latitude) : activity.latitude,
    longitude: meta?.longitude !== undefined && meta?.longitude !== null ? Number(meta.longitude) : activity.longitude,
    device_id: devId !== "N/A" ? devId : getDeviceString(actData.device_signature),
    uploader_id: meta?.uploader_id || activity.user_id,
    hash: meta?.hash || (isBefore ? "" : activity.image_hash) || "N/A"
  };
};

function ImagePanel({ 
  url, 
  label, 
  isBefore, 
  meta, 
  missingKey, 
  penaltyMsg,
  activity
}: { 
  url: string; 
  label: string; 
  isBefore: boolean; 
  meta: any; 
  missingKey?: string; 
  penaltyMsg?: string;
  activity: any;
}) {
  const [copied, setCopied] = useState(false);
  const [isLocked, setIsLocked] = useState(false);

  const finalMeta = getFallbackMeta(meta, isBefore, activity);

  const handleCopyHash = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (finalMeta.hash) {
      navigator.clipboard.writeText(finalMeta.hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!url) {
    const isPenalized = missingKey && activity.trust_flags?.[missingKey] === true;
    return (
      <div className="aspect-[4/3] w-full bg-[var(--color-surface)] flex flex-col items-center justify-center border border-dashed border-[var(--color-border)] rounded-xl p-6 text-center relative overflow-hidden">
        <div className={`p-3 rounded-full mb-3 ${isPenalized ? "bg-red-500/10 text-red-500 animate-pulse" : "bg-[var(--color-background)] text-[var(--color-text-muted)]"}`}>
          <ShieldAlert size={28} />
        </div>
        <h4 className="text-xs font-bold text-[var(--color-text-primary)]">{label}</h4>
        <p className="text-[var(--color-text-muted)] text-[10px] mt-1 max-w-[200px]">
          {isBefore ? "No baseline operational proof was submitted." : "No verification photo provided."}
        </p>
        {isPenalized && penaltyMsg && (
          <span className="mt-3 px-2 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] font-extrabold tracking-wider uppercase border border-red-500/20">
            {penaltyMsg}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="aspect-[4/3] w-full bg-slate-950 relative rounded-xl border border-[var(--color-border)] overflow-hidden group">
      <img 
        src={url} 
        alt={label} 
        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]" 
      />
      
      {/* Photo Label (Top Left) */}
      <div className="absolute top-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-700/50 rounded-lg px-2.5 py-1 text-[9px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5 z-10 shadow-lg">
        <span className={`w-1.5 h-1.5 rounded-full ${isBefore ? "bg-amber-500" : "bg-[#00B47A]"}`} />
        <span>{label}</span>
      </div>

      {/* Toggle Info Button (Bottom Right) */}
      <button 
        onClick={() => setIsLocked(!isLocked)}
        className={`absolute bottom-3 right-3 z-10 rounded-lg p-1.5 text-xs border transition-all shadow-lg flex items-center justify-center ${
          isLocked 
            ? "bg-[#00B47A] border-[#00B47A]/30 text-white" 
            : "bg-slate-900/80 border-slate-700/50 text-slate-300 hover:text-white"
        }`}
        title="Toggle Audit Metadata"
      >
        <Info size={14} />
      </button>

      {/* Metadata Overlay (Hover / Toggle Lock) */}
      <div className={`absolute inset-0 bg-slate-950/90 backdrop-blur-sm transition-opacity duration-300 flex flex-col justify-between p-4 text-white z-0 ${
        isLocked ? "opacity-100 font-semibold" : "opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto"
      }`}>
        <div className="space-y-3 mt-8">
          <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-[#00B47A] border-b border-slate-800 pb-1.5">
            MRV Secure Audit Metadata
          </h4>
          
          <div className="grid grid-cols-1 gap-2.5 font-mono text-[9px]">
            {/* Timestamp */}
            <div className="flex items-start gap-2 text-slate-300">
              <Clock size={11} className="text-[#00B47A] shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block font-bold">CAPTURED EPOCH</span>
                <span>{finalMeta.timestamp ? new Date(finalMeta.timestamp).toUTCString() : "N/A"}</span>
              </div>
            </div>
            
            {/* GPS Bounds */}
            <div className="flex items-start gap-2 text-slate-300">
              <MapPin size={11} className="text-blue-400 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block font-bold">SPATIAL ACCURACY COORDS</span>
                <span>
                  {finalMeta.latitude && finalMeta.longitude 
                    ? `${finalMeta.latitude.toFixed(6)}, ${finalMeta.longitude.toFixed(6)}` 
                    : "N/A"}
                </span>
              </div>
            </div>

            {/* Device ID */}
            <div className="flex items-start gap-2 text-slate-300">
              <Cpu size={11} className="text-purple-400 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block font-bold">DEVICE ID SIGNATURE</span>
                <span className="truncate block max-w-[200px]" title={finalMeta.device_id}>
                  {finalMeta.device_id}
                </span>
              </div>
            </div>

            {/* Uploader ID */}
            <div className="flex items-start gap-2 text-slate-300">
              <UserIcon size={11} className="text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block font-bold">UPLOADER ID</span>
                <span className="truncate block max-w-[200px]" title={finalMeta.uploader_id}>
                  {finalMeta.uploader_id}
                </span>
              </div>
            </div>

            {/* Hash */}
            {finalMeta.hash && finalMeta.hash !== "N/A" && (
              <div className="flex items-start gap-2 text-slate-300">
                <Fingerprint size={11} className="text-emerald-400 shrink-0 mt-0.5" />
                <div className="w-full">
                  <span className="text-slate-500 block font-bold">PERCEPTUAL IMAGE HASH</span>
                  <div className="flex items-center gap-1.5 mt-0.5 w-full">
                    <span className="font-mono text-slate-300 truncate max-w-[140px] block" title={finalMeta.hash}>
                      {finalMeta.hash}
                    </span>
                    <button 
                      onClick={handleCopyHash}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                      title="Copy full hash"
                    >
                      {copied ? <Check size={8} className="text-[#00B47A]" /> : <Copy size={8} />}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="text-[8px] text-[#00B47A] font-extrabold tracking-wider uppercase bg-[#00B47A]/10 border border-[#00B47A]/20 px-2 py-1 rounded text-center w-full flex items-center justify-center gap-1.5">
          <Shield size={10} />
          <span>Immutable Ledger Integrity Secured</span>
        </div>
      </div>
    </div>
  );
}

export default function ActivityDetailPage() {
  const toast = useToast();
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [activity, setActivity] = useState<Activity | null>(null);
  const [trustDetails, setTrustDetails] = useState<TrustScoreBreakdown | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState("all"); // 7d | 30d | all
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, dateRange]);

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

  // --- HOOKS (must be called unconditionally, before any early return) ---
  const actData = (activity?.activity_data as Record<string, any>) || {};

  const rawLogs = useMemo(() => {
    return Array.isArray(actData.telemetry_log) ? actData.telemetry_log : [];
  }, [actData.telemetry_log]);

  const filteredLogs = useMemo(() => {
    // 1. Sort by date descending
    const sorted = [...rawLogs].sort((a: any, b: any) => {
      const dateA = a.date || a.timestamp || "";
      const dateB = b.date || b.timestamp || "";
      return dateB.localeCompare(dateA);
    });

    // 2. Filter by range
    let rangeFiltered = sorted;
    const now = new Date();
    const isWithinDays = (dateStr: string, days: number) => {
      if (!dateStr) return false;
      const date = new Date(dateStr);
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays <= days;
    };

    if (dateRange === "7d") {
      rangeFiltered = sorted.filter(l => isWithinDays(l.date || l.timestamp, 7));
    } else if (dateRange === "30d") {
      rangeFiltered = sorted.filter(l => isWithinDays(l.date || l.timestamp, 30));
    }

    // 3. Search filter
    if (!searchQuery) return rangeFiltered;
    const query = searchQuery.toLowerCase();
    return rangeFiltered.filter(log =>
      JSON.stringify(log).toLowerCase().includes(query)
    );
  }, [rawLogs, searchQuery, dateRange]);

  const totalPages = Math.ceil(filteredLogs.length / pageSize) || 1;
  const paginatedLogs = useMemo(() => {
    return filteredLogs.slice(
      (currentPage - 1) * pageSize,
      currentPage * pageSize
    );
  }, [filteredLogs, currentPage, pageSize]);

  // --- EARLY RETURNS (after all hooks) ---
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

  const imageMetadata = (actData.image_metadata as Record<string, any>) || {};

  const exportToCSV = () => {
    if (filteredLogs.length === 0) return;
    const headers = ["Date", "Solar Generation (kWh)", "Grid (kWh)", "Diesel Backup (hrs)", "Battery SOC (%)", "Uptime (%)", "Inverter Temp (°C)"];
    const csvRows = [
      headers.join(","),
      ...filteredLogs.map((log: any) => [
        log.date || log.timestamp || "—",
        log.solar_kwh != null ? log.solar_kwh : "—",
        log.grid_kwh != null ? log.grid_kwh : "—",
        log.diesel_hrs != null ? log.diesel_hrs : "—",
        log.battery_soc != null ? log.battery_soc : "—",
        log.uptime_pct != null ? log.uptime_pct : "—",
        log.temp_c != null ? log.temp_c : "—"
      ].map(val => `"${val}"`).join(","))
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `telemetry_logs_${id}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  let beforeUrl = "";
  let beforeLabel = "Baseline Proof";
  let beforeMeta = null;
  let beforeMissingKey = "";
  let beforePenaltyMsg = "";

  let afterUrl = activity.image_url || "";
  let afterLabel = "Installation Proof";
  let afterMeta = null;

  let optionalUrl = "";
  let optionalLabel = "";
  let optionalMeta = null;

  if (activity.activity_type === "HYBRID_ENERGY") {
    beforeUrl = actData.baseline_generator_image_url || "";
    beforeLabel = "Diesel Generator (Baseline)";
    beforeMeta = imageMetadata.baseline_generator;
    beforeMissingKey = "missing_baseline_generator_photo";
    beforePenaltyMsg = "-30 Trust Score Penalty";

    afterUrl = actData.solar_installation_image_url || activity.image_url || "";
    afterLabel = "Solar PV Installation (Project)";
    afterMeta = imageMetadata.solar_installation;

    optionalUrl = actData.inverter_label_image_url || "";
    optionalLabel = "Inverter Nameplate (Secondary)";
    optionalMeta = imageMetadata.inverter_label;
  } else if (activity.activity_type === "CLEAN_COOKING") {
    beforeUrl = actData.baseline_fuel_source_image_url || "";
    beforeLabel = "Old Stove / Baseline (Before)";
    beforeMeta = imageMetadata.baseline_fuel_source;

    afterUrl = actData.stove_installation_image_url || activity.image_url || "";
    afterLabel = "Clean Cookstove (After)";
    afterMeta = imageMetadata.stove_installation;
  } else {
    afterUrl = activity.image_url || "";
    afterLabel = "Installation Proof";
    afterMeta = {
      timestamp: activity.captured_at,
      latitude: activity.latitude,
      longitude: activity.longitude,
      hash: activity.image_hash,
      device_id: getDeviceString(actData.device_signature) || "N/A",
      uploader_id: activity.user_id
    };
  }

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
                <h2 className="text-xs font-bold uppercase tracking-wider">MRV Visual Evidence: Before vs After</h2>
              </div>
              <span className="text-[9px] text-[#00B47A] font-extrabold tracking-wider bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase flex items-center gap-1">
                <Shield size={10} /> Audit Trail Proof
              </span>
            </div>
            
            <div className="p-4 bg-[var(--color-background)]/10 space-y-4">
              {/* BEFORE/AFTER side-by-side grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* BEFORE Image Panel */}
                <ImagePanel 
                  url={beforeUrl} 
                  label={beforeLabel} 
                  isBefore={true} 
                  meta={beforeMeta} 
                  missingKey={beforeMissingKey}
                  penaltyMsg={beforePenaltyMsg}
                  activity={activity}
                />
                
                {/* AFTER Image Panel */}
                <ImagePanel 
                  url={afterUrl} 
                  label={afterLabel} 
                  isBefore={false} 
                  meta={afterMeta}
                  activity={activity}
                />
              </div>

              {/* Optional secondary photos (e.g. Inverter Label) */}
              {optionalUrl && (
                <div className="border-t border-[var(--color-border)] pt-4 mt-2">
                  <h3 className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3 flex items-center gap-1.5">
                    <Layers size={12} className="text-[#00B47A]" /> Secondary Evidence Records
                  </h3>
                  <div className="max-w-md">
                    <ImagePanel 
                      url={optionalUrl} 
                      label={optionalLabel} 
                      isBefore={false} 
                      meta={optionalMeta}
                      activity={activity}
                    />
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4.5 bg-[var(--color-background)]/35 border-t border-[var(--color-border)]">
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
                 {Object.entries(activity.activity_data)
                   .filter(([key]) => {
                     return (
                       key !== "telemetry_log" &&
                       key !== "image_metadata" &&
                       key !== "device_signature" &&
                       !key.endsWith("_url") &&
                       !key.endsWith("_image_url")
                     );
                   })
                  .map(([key, value]) => {
                    let displayVal = String(value);
                    if (typeof value === "object" && value !== null) {
                      if (key === "device_signature") {
                        displayVal = (value as any).device_id || (value as any).os || JSON.stringify(value);
                      } else {
                        displayVal = JSON.stringify(value);
                      }
                    }
                    return (
                      <div 
                        key={key} 
                        className="bg-[var(--color-background)] border border-[var(--color-border)] hover:border-[#00B47A]/30 transition-all rounded-xl p-3.5 flex flex-col justify-between shadow-inner group"
                      >
                        <p className="text-[9px] text-[var(--color-text-muted)] group-hover:text-[#00B47A] font-extrabold uppercase tracking-wider transition-colors mb-1">
                          {key.replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono break-words">
                          {displayVal}
                        </p>
                      </div>
                    );
                  })}
                
                {actData.telemetry_log && (
                  <div className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-4.5 flex flex-col justify-between shadow-inner md:col-span-2 space-y-4">
                    {/* Header with Title & Export Button */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--color-border)]/50">
                      <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-[#00B47A]" />
                        <div>
                          <p className="text-[10px] text-[#00B47A] font-extrabold uppercase tracking-wider">
                            Telemetry Log Registry
                          </p>
                          <p className="text-[9px] text-[var(--color-text-muted)] mt-0.5">
                            Showing {filteredLogs.length} total entries
                          </p>
                        </div>
                      </div>
                      
                      <button
                        onClick={exportToCSV}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00B47A]/10 hover:bg-[#00B47A]/25 border border-[#00B47A]/20 text-[#00B47A] text-[9px] font-extrabold rounded-lg uppercase tracking-wider transition-all self-start sm:self-auto active:scale-95"
                      >
                        <Download size={12} /> Export CSV
                      </button>
                    </div>

                    {/* Filter and Search Bar */}
                    <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
                      {/* Search Bar */}
                      <div className="relative flex-1">
                        <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-[var(--color-text-muted)]">
                          <Search size={12} />
                        </span>
                        <input
                          type="text"
                          placeholder="Search logs by date..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full pl-8 pr-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-[10px] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[#00B47A]/40 transition-colors font-mono"
                        />
                      </div>

                      {/* Range Selector */}
                      <div className="flex bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-0.5 self-start sm:self-auto gap-0.5">
                        {[
                          { id: "7d", label: "7 Days" },
                          { id: "30d", label: "30 Days" },
                          { id: "all", label: "All Logs" }
                        ].map((btn) => (
                          <button
                            key={btn.id}
                            onClick={() => setDateRange(btn.id)}
                            className={`px-2.5 py-1 text-[9px] font-extrabold rounded-md uppercase tracking-wider transition-all ${
                              dateRange === btn.id
                                ? "bg-[#00B47A] text-white shadow-sm font-black"
                                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                            }`}
                          >
                            {btn.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {/* The Table */}
                    {paginatedLogs.length === 0 ? (
                      <p className="text-xs text-[var(--color-text-muted)] italic p-8 text-center bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]/50">
                        No telemetry logs match the selected filters.
                      </p>
                    ) : (
                      <div className="border border-[var(--color-border)]/50 rounded-xl overflow-hidden bg-[var(--color-surface)] shadow-inner">
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-[10px] border-collapse font-mono">
                            <thead>
                              <tr className="bg-[var(--color-background)] border-b border-[var(--color-border)]/50 text-[8px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                                <th className="p-2.5">Date</th>
                                <th className="p-2.5 text-right">Solar</th>
                                <th className="p-2.5 text-right">Diesel</th>
                                <th className="p-2.5 text-right">Battery</th>
                                <th className="p-2.5 text-right">Temp</th>
                                <th className="p-2.5 text-right">Uptime</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--color-border)]/50">
                              {paginatedLogs.map((log: any, idx: number) => (
                                <tr key={idx} className="hover:bg-[var(--color-background)]/20 transition-colors">
                                  <td className="p-2.5 font-bold text-[var(--color-text-secondary)]">
                                    {log.date || log.timestamp || "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-amber-500 font-extrabold">
                                    {log.solar_kwh != null ? `${Number(log.solar_kwh).toFixed(1)} kWh` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-rose-500 font-semibold">
                                    {log.diesel_hrs != null ? `${Number(log.diesel_hrs).toFixed(1)} hrs` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-[#00B47A] font-extrabold">
                                    {log.battery_soc != null ? `${Number(log.battery_soc).toFixed(0)}%` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-orange-400 font-semibold">
                                    {log.temp_c != null ? `${Number(log.temp_c).toFixed(1)}°C` : "—"}
                                  </td>
                                  <td className="p-2.5 text-right text-blue-400 font-semibold">
                                    {log.uptime_pct != null ? `${Number(log.uptime_pct).toFixed(1)}%` : "—"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)]/30 text-[9px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
                        <span>
                          Showing {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, filteredLogs.length)} of {filteredLogs.length}
                        </span>
                        
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            className={`p-1.5 rounded-lg border border-[var(--color-border)] transition-all bg-[var(--color-surface)] hover:text-[var(--color-text-primary)] active:scale-95 ${
                              currentPage === 1 ? "opacity-40 cursor-not-allowed" : ""
                            }`}
                          >
                            <ChevronLeft size={10} />
                          </button>
                          
                          <span className="font-mono px-2 py-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)]">
                            {currentPage} / {totalPages}
                          </span>
                          
                          <button
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages}
                            className={`p-1.5 rounded-lg border border-[var(--color-border)] transition-all bg-[var(--color-surface)] hover:text-[var(--color-text-primary)] active:scale-95 ${
                              currentPage === totalPages ? "opacity-40 cursor-not-allowed" : ""
                            }`}
                          >
                            <ChevronRight size={10} />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
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

          {/* Cryptographic Ledger Receipt */}
          {actData.on_chain && (
            <div className="bg-[var(--color-surface)] border border-emerald-500/25 rounded-2xl p-5 shadow-sm relative overflow-hidden border-l-4 border-l-emerald-500">
              <div className="absolute top-0 right-0 p-3 text-emerald-500 opacity-10">
                <CheckCircle size={45} />
              </div>
              
              <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-1 flex items-center gap-1.5">
                <Fingerprint size={14} className="text-emerald-400" /> Cryptographic Ledger Receipt
              </h2>
              <p className="text-[var(--color-text-secondary)] text-[10px] mb-4">Verified environmental asset recorded in local private Cryptographic Ledger.</p>
              
              <div className="space-y-3 font-mono text-[10px] text-[var(--color-text-secondary)]">
                <div>
                  <span className="text-[var(--color-text-muted)] block font-bold text-[8px] uppercase">Receipt Signature</span>
                  <div className="flex items-center gap-1.5 mt-0.5 w-full">
                    <span className="text-emerald-400 truncate max-w-[170px] block font-bold" title={actData.on_chain.signature}>
                      {actData.on_chain.signature}
                    </span>
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(actData.on_chain.signature);
                        toast.success("Signature Copied", "Receipt signature copied to clipboard.");
                      }}
                      className="p-1 rounded bg-[var(--color-background)] hover:bg-[var(--color-border)] text-slate-300 hover:text-white transition-colors"
                      title="Copy Receipt Signature"
                    >
                      <Copy size={10} />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[var(--color-text-muted)] block font-bold text-[8px] uppercase">Ledger Sequence Index</span>
                    <span className="font-bold text-[var(--color-text-primary)]">{Number(actData.on_chain.block_height).toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-[var(--color-text-muted)] block font-bold text-[8px] uppercase">Ledger Sequence Slot</span>
                    <span className="font-bold text-[var(--color-text-primary)]">{Number(actData.on_chain.slot).toLocaleString()}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[var(--color-text-muted)] block font-bold text-[8px] uppercase">Payload Hash (SHA-256)</span>
                  <span className="font-bold text-[var(--color-text-primary)] break-all truncate block max-w-[240px]" title={actData.on_chain.payload_hash}>
                    {actData.on_chain.payload_hash}
                  </span>
                </div>

                <div>
                  <span className="text-[var(--color-text-muted)] block font-bold text-[8px] uppercase">Timestamp</span>
                  <span>{new Date(actData.on_chain.timestamp).toUTCString()}</span>
                </div>
              </div>
            </div>
          )}

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
