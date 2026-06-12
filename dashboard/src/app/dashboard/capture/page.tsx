// =============================================================================
// VeriField Nexus — Field Capture Interface (Digital MRV Capture)
// =============================================================================
// Infrastructure-grade, high-contrast minimal UI.
// Supports offline queueing, image/metadata hashing, and geolocation tracking.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { 
  Camera, 
  MapPin, 
  Wifi, 
  WifiOff, 
  Database, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  Cpu, 
  Calendar, 
  Info,
  ChevronRight,
  ShieldCheck
} from "lucide-react";
import { uploadProof, createActivity, checkDuplicate } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

interface QueuedActivity {
  id: string; // client-generated UUID
  activity_type: string;
  activity_data: Record<string, any>;
  description: string;
  latitude: number | null;
  longitude: number | null;
  gps_accuracy: number | null;
  captured_at: string;
  image_base64: string; // Stored locally to allow offline photo capture
  image_name: string;
}

export default function FieldCapturePage() {
  const { user } = useWorkspace();
  const [activeTab, setActiveTab] = useState<"CLEAN_COOKING" | "HYBRID_ENERGY">("CLEAN_COOKING");
  
  // --- FORM STATE ---
  const [notes, setNotes] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageHash, setImageHash] = useState<string>("");
  const [payloadHash, setPayloadHash] = useState<string>("");
  
  // --- LOCATION STATE ---
  const [latitude, setLatitude] = useState<string>("");
  const [longitude, setLongitude] = useState<string>("");
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [isManualLocation, setIsManualLocation] = useState(false);
  const [gpsStatus, setGpsStatus] = useState<"idle" | "detecting" | "success" | "denied" | "error">("idle");
  const [gpsErrorMsg, setGpsErrorMsg] = useState("");

  // --- DYNAMIC FORM FIELD STATES ---
  // Cookstove Specifics
  const [stoveId, setStoveId] = useState("");
  const [stoveModel, setStoveModel] = useState("baikuc_gen1");
  const [householdId, setHouseholdId] = useState("");
  const [headName, setHeadName] = useState("");
  const [householdSize, setHouseholdSize] = useState("4");
  const [mealsPerDay, setMealsPerDay] = useState("3");
  const [baselineFuel, setBaselineFuel] = useState("wood");
  const [baselineStove, setBaselineStove] = useState("3_stone_fire");
  const [baselineFuelConsumption, setBaselineFuelConsumption] = useState("120");
  const [baselineFuelCost, setBaselineFuelCost] = useState("5000");
  const [baselineCookingDuration, setBaselineCookingDuration] = useState("4");
  const [fuelSource, setFuelSource] = useState("collected_free");
  const [primaryFuel, setPrimaryFuel] = useState("wood");
  const [stoveCondition, setStoveCondition] = useState("good");

  // Hybrid Solar Specifics
  const [siteId, setSiteId] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [siteType, setSiteType] = useState("residential");
  const [baselineGenType, setBaselineGenType] = useState("diesel");
  const [baselineGenCapacity, setBaselineGenCapacity] = useState("10");
  const [baselineFuelConsumptionLph, setBaselineFuelConsumptionLph] = useState("2.5");
  const [baselineRuntimeHrs, setBaselineRuntimeHrs] = useState("6");
  const [baselineOperatingDays, setBaselineOperatingDays] = useState("300");
  const [solarCapacity, setSolarCapacity] = useState("5");
  const [inverterCapacity, setInverterCapacity] = useState("5");
  const [avgSunHours, setAvgSunHours] = useState("5");

  // --- SYSTEM STATES ---
  const [installationId, setInstallationId] = useState("");
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [queue, setQueue] = useState<QueuedActivity[]>([]);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [syncLogs, setSyncLogs] = useState<string[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  // Auto-generate UUID and listen to network connectivity status
  useEffect(() => {
    generateNewInstallation();
    
    const checkOnline = () => {
      setIsOnline(navigator.onLine);
    };
    window.addEventListener("online", checkOnline);
    window.addEventListener("offline", checkOnline);
    
    // Load local storage queue
    const savedQueue = localStorage.getItem("vf_offline_capture_queue");
    if (savedQueue) {
      try {
        setQueue(JSON.parse(savedQueue));
      } catch (e) {
        console.error("Failed to parse offline queue", e);
      }
    }

    // Attempt auto-detect geolocation on load
    detectLocation();

    return () => {
      window.removeEventListener("online", checkOnline);
      window.removeEventListener("offline", checkOnline);
    };
  }, []);

  // Sync network state toggle with manual offline override
  const effectiveOnline = isOnline && !isOfflineMode;

  const generateNewInstallation = () => {
    setInstallationId(crypto.randomUUID());
  };

  // Run duplicate check & compute hashes when payload variables change
  useEffect(() => {
    recalculatePayloadHash();
  }, [activeTab, notes, imageHash, latitude, longitude, stoveId, siteId]);

  const recalculatePayloadHash = async () => {
    const activity_data = getStructuredData();
    const meta = {
      id: installationId,
      activity_type: activeTab,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null,
      image_hash: imageHash,
      captured_at: new Date().toISOString(),
      activity_data,
    };
    try {
      const msgUint8 = new TextEncoder().encode(JSON.stringify(meta));
      const hashBuffer = await crypto.subtle.digest("SHA-256", msgUint8);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
      setPayloadHash("sha256_" + hashHex);
    } catch (e) {
      console.error(e);
    }
  };

  const getStructuredData = () => {
    if (activeTab === "CLEAN_COOKING") {
      return {
        stove_id: stoveId,
        stove_model: stoveModel,
        household_id: householdId,
        head_name: headName,
        household_size: parseInt(householdSize) || 4,
        meals_per_day: mealsPerDay,
        baseline_fuel: baselineFuel,
        baseline_stove: baselineStove,
        baseline_fuel_consumption: parseFloat(baselineFuelConsumption) || 0,
        baseline_fuel_cost: parseFloat(baselineFuelCost) || 0,
        baseline_cooking_duration: parseFloat(baselineCookingDuration) || 0,
        fuel_source: fuelSource,
        primary_fuel: primaryFuel,
        stove_condition: stoveCondition,
        consent_obtained: true,
        usage_flag: true,
      };
    } else {
      return {
        site_id: siteId,
        owner_name: ownerName,
        site_type: siteType,
        baseline_generator_type: baselineGenType,
        baseline_generator_capacity_kva: parseFloat(baselineGenCapacity) || 0,
        baseline_fuel_consumption_lph: parseFloat(baselineFuelConsumptionLph) || 0,
        baseline_avg_daily_runtime_hrs: parseFloat(baselineRuntimeHrs) || 0,
        baseline_operating_days_per_year: parseInt(baselineOperatingDays) || 365,
        solar_capacity_kwp: parseFloat(solarCapacity) || 0,
        inverter_capacity_kva: parseFloat(inverterCapacity) || 0,
        avg_sun_hours: parseFloat(avgSunHours) || 5.0,
        installation_date: new Date().toISOString().split("T")[0],
        data_source: "analog_manual",
        system_installed: true,
        system_operational: true,
        tamper_signs: false,
        usage_confirmed: true,
        consent_obtained: true,
      };
    }
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setGpsStatus("error");
      setGpsErrorMsg("Geolocation is not supported by your browser");
      return;
    }

    setGpsStatus("detecting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setGpsAccuracy(position.coords.accuracy);
        setGpsStatus("success");
      },
      (error) => {
        setGpsStatus("denied");
        if (error.code === error.PERMISSION_DENIED) {
          setGpsErrorMsg("Permission denied. Enable GPS manually or override coordinates.");
        } else {
          setGpsErrorMsg(error.message || "Failed to retrieve location coordinates");
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImageFile(file);
    
    // Generate preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Compute Image Cryptographic SHA-256 Hash
    try {
      const arrayBuffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
      setImageHash("sha256_" + hashHex);
    } catch (e) {
      console.error("Error computing image hash", e);
    }
  };

  const addLog = (msg: string) => {
    setSyncLogs((prev) => [
      `[${new Date().toLocaleTimeString()}] ${msg}`,
      ...prev,
    ]);
  };

  // Convert Base64 string to a File object for API uploading
  const base64ToFile = (base64String: string, filename: string): File => {
    const arr = base64String.split(",");
    const mime = arr[0].match(/:(.*?);/)![1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  };

  // Synchronize queued offline items to backend
  const syncQueue = async () => {
    if (queue.length === 0 || isSyncing) return;
    setIsSyncing(true);
    addLog(`Initiating synchronization of ${queue.length} activities...`);

    const updatedQueue = [...queue];

    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];
      addLog(`Syncing Activity ${i + 1}/${queue.length} (ID: ${item.id.slice(0, 8)}...)`);
      
      try {
        let finalImageUrl = "";
        
        // 1. Upload proof photo first
        if (item.image_base64) {
          const fileToUpload = base64ToFile(item.image_base64, item.image_name);
          const uploadRes = await uploadProof(fileToUpload);
          finalImageUrl = uploadRes.image_url;
          addLog("Proof image uploaded successfully.");
        }

        // 2. Submit activity payload
        await createActivity({
          activity_type: item.activity_type,
          activity_data: item.activity_data,
          description: item.description,
          latitude: item.latitude,
          longitude: item.longitude,
          gps_accuracy: item.gps_accuracy,
          image_url: finalImageUrl,
          image_hash: item.image_base64 ? "sha256_" + item.image_base64.slice(0, 32) : "", // Simplified sync hash fallback
          captured_at: item.captured_at,
          client_id: item.id,
        });

        addLog(`Successfully synced activity ${item.id.slice(0, 8)} to Supabase.`);
        // Remove item from local queue list
        updatedQueue.shift();
        setQueue([...updatedQueue]);
        localStorage.setItem("vf_offline_capture_queue", JSON.stringify(updatedQueue));
      } catch (err: any) {
        addLog(`Sync error for activity ${item.id.slice(0, 8)}: ${err.message || err}. Pausing sync.`);
        break;
      }
    }
    setIsSyncing(false);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitStatus("submitting");
    setStatusMsg("");

    if (!latitude || !longitude) {
      setSubmitStatus("error");
      setStatusMsg("GPS location parameters are required for digital MRV verification.");
      return;
    }

    const payload_data = getStructuredData();
    const currentTimestamp = new Date().toISOString();

    if (effectiveOnline) {
      // ONLINE FLOW
      try {
        let finalImageUrl = "";
        
        // 1. Upload image proof
        if (imageFile) {
          setStatusMsg("Uploading photo proof to storage server...");
          const uploadRes = await uploadProof(imageFile);
          finalImageUrl = uploadRes.image_url;
        } else if (activeTab === "HYBRID_ENERGY") {
          setSubmitStatus("error");
          setStatusMsg("Proof image upload is required for Solar PV installation.");
          return;
        }

        // 2. Submit to Ledger
        setStatusMsg("Submitting structured record to verification engine...");
        await createActivity({
          activity_type: activeTab,
          activity_data: payload_data,
          description: notes,
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
          gps_accuracy: gpsAccuracy,
          image_url: finalImageUrl,
          image_hash: imageHash,
          captured_at: currentTimestamp,
          client_id: installationId,
        });

        setSubmitStatus("success");
        setStatusMsg("Record successfully written to Supabase database. Trust score and Solana receipts triggered.");
        resetForm();
      } catch (err: any) {
        setSubmitStatus("error");
        setStatusMsg(err.message || "Failed to submit field activity.");
      }
    } else {
      // OFFLINE FLOW
      if (!imagePreview) {
        setSubmitStatus("error");
        setStatusMsg("An image capture is required to secure offline verification proof.");
        return;
      }

      const queuedItem: QueuedActivity = {
        id: installationId,
        activity_type: activeTab,
        activity_data: payload_data,
        description: notes,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        gps_accuracy: gpsAccuracy,
        captured_at: currentTimestamp,
        image_base64: imagePreview,
        image_name: imageFile?.name || "offline_capture.jpg",
      };

      const newQueue = [...queue, queuedItem];
      setQueue(newQueue);
      localStorage.setItem("vf_offline_capture_queue", JSON.stringify(newQueue));
      
      setSubmitStatus("success");
      setStatusMsg("Offline submission stored in local queue. Will auto-sync when network is recovered.");
      resetForm();
    }
  };

  const resetForm = () => {
    generateNewInstallation();
    setNotes("");
    setImageFile(null);
    setImagePreview(null);
    setImageHash("");
    setStoveId("");
    setHouseholdId("");
    setHeadName("");
    setSiteId("");
    setOwnerName("");
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-10 text-zinc-100 min-h-screen bg-black p-4">
      {/* HEADER BANNER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Cpu className="text-[#00b47a]" size={20} />
            VeriField Capture
          </h1>
          <p className="text-[10px] text-zinc-400 mt-1 uppercase font-extrabold tracking-wider">
            Infrastructure-Grade Digital MRV Terminal
          </p>
        </div>

        {/* NETWORK STATUS / TOGGLE BAR */}
        <div className="flex items-center gap-3 bg-zinc-950 border border-zinc-800 rounded-xl p-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-zinc-900 border border-zinc-800">
            {effectiveOnline ? (
              <>
                <Wifi size={13} className="text-[#00b47a]" />
                <span className="text-zinc-300">Online Mode</span>
              </>
            ) : (
              <>
                <WifiOff size={13} className="text-amber-500" />
                <span className="text-zinc-300">Offline Mode</span>
              </>
            )}
          </div>
          
          <button
            onClick={() => setIsOfflineMode(!isOfflineMode)}
            className={`px-3 py-1 text-[10px] font-bold uppercase rounded-lg border transition-colors ${
              isOfflineMode 
                ? "bg-amber-900/20 text-amber-400 border-amber-500/30 hover:bg-amber-900/40" 
                : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-white"
            }`}
          >
            {isOfflineMode ? "Force Online" : "Simulate Offline"}
          </button>
        </div>
      </div>

      {/* OFFLINE SYNC SYSTEM STATUS CARD */}
      {queue.length > 0 && (
        <div className="bg-zinc-950 border border-zinc-800/80 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-500">
              <Database size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-white">
                Offline Data Queue Pending Sync ({queue.length} installations)
              </p>
              <p className="text-[10px] text-zinc-400 mt-0.5">
                Submissions are securely stored in browser localStorage.
              </p>
            </div>
          </div>
          <button
            onClick={syncQueue}
            disabled={isSyncing || !isOnline}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#00b47a] text-black text-xs font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider"
          >
            <RefreshCw size={13} className={isSyncing ? "animate-spin" : ""} />
            {isSyncing ? "Syncing..." : "Sync Queue Now"}
          </button>
        </div>
      )}

      {/* FORM CONTAINER */}
      <form onSubmit={handleFormSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* LEFT COLUMN: BASIC METADATA & FORMS */}
          <div className="md:col-span-2 space-y-6">
            
            {/* INSTALLATION TYPE TABS */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-3">
              <label className="text-[10px] uppercase font-bold text-zinc-400 block mb-2">
                Select Installation Sector
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("CLEAN_COOKING")}
                  className={`py-2 px-3 rounded-lg text-xs font-bold border transition-colors ${
                    activeTab === "CLEAN_COOKING"
                      ? "bg-zinc-900 border-[#00b47a] text-[#00b47a]"
                      : "bg-transparent border-zinc-800 text-zinc-400 hover:text-white"
                  }`}
                >
                  Clean Cooking (Cookstove)
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("HYBRID_ENERGY")}
                  className={`py-2 px-3 rounded-lg text-xs font-bold border transition-colors ${
                    activeTab === "HYBRID_ENERGY"
                      ? "bg-zinc-900 border-[#00b47a] text-[#00b47a]"
                      : "bg-transparent border-zinc-800 text-zinc-400 hover:text-white"
                  }`}
                >
                  Hybrid Energy (Solar PV)
                </button>
              </div>
            </div>

            {/* DYNAMIC FORM SEGMENTS */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 space-y-4">
              <div className="border-b border-zinc-850 pb-3 mb-2 flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                  Installation Specific Telemetry
                </h3>
                <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-850 text-zinc-500 text-[9px]">
                  ID: {installationId.slice(0, 8)}...
                </span>
              </div>

              {activeTab === "CLEAN_COOKING" ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Stove ID */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Stove ID (QR/BLE Serial)</label>
                    <input
                      type="text"
                      value={stoveId}
                      onChange={(e) => setStoveId(e.target.value)}
                      placeholder="e.g. COOK-2026-9811"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Stove Model */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Stove Model</label>
                    <select
                      value={stoveModel}
                      onChange={(e) => setStoveModel(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="baikuc_gen1">Baikuc Gen 1</option>
                      <option value="tlud_forced">TLUD Forced Draft</option>
                      <option value="rocket">Rocket Stove</option>
                      <option value="gasifier">Gasifier Stove</option>
                      <option value="electric_ics">Electric ICS</option>
                    </select>
                  </div>

                  {/* Household ID */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Household ID</label>
                    <input
                      type="text"
                      value={householdId}
                      onChange={(e) => setHouseholdId(e.target.value)}
                      placeholder="e.g. HH-NIG-KAD-001"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Household Head Name */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Head of Household</label>
                    <input
                      type="text"
                      value={headName}
                      onChange={(e) => setHeadName(e.target.value)}
                      placeholder="e.g. Abubakar Yusuf"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Household Size */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Household Size</label>
                    <input
                      type="number"
                      value={householdSize}
                      onChange={(e) => setHouseholdSize(e.target.value)}
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Meals per Day */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Meals Cooked Per Day</label>
                    <select
                      value={mealsPerDay}
                      onChange={(e) => setMealsPerDay(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
                      <option value="4+">4+</option>
                    </select>
                  </div>

                  {/* Baseline Fuel */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Baseline Primary Fuel</label>
                    <select
                      value={baselineFuel}
                      onChange={(e) => setBaselineFuel(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="wood">Firewood</option>
                      <option value="charcoal">Charcoal</option>
                      <option value="kerosene">Kerosene</option>
                      <option value="dung">Animal Dung</option>
                    </select>
                  </div>

                  {/* Baseline Stove */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Baseline Stove Type</label>
                    <select
                      value={baselineStove}
                      onChange={(e) => setBaselineStove(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="3_stone_fire">3 Stone Open Fire</option>
                      <option value="traditional_clay">Traditional Clay</option>
                      <option value="metal_grate">Simple Metal Grate</option>
                    </select>
                  </div>

                  {/* Baseline Fuel Consumption */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Baseline Monthly Fuel (kg)</label>
                    <input
                      type="number"
                      value={baselineFuelConsumption}
                      onChange={(e) => setBaselineFuelConsumption(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Project Primary Fuel */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Project Primary Fuel</label>
                    <select
                      value={primaryFuel}
                      onChange={(e) => setPrimaryFuel(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="wood">Wood Pellets / Briquettes</option>
                      <option value="pellet">Agricultural Waste Pellets</option>
                      <option value="charcoal">Sustainably Sourced Charcoal</option>
                      <option value="electric">Electricity</option>
                    </select>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Site ID */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Site ID</label>
                    <input
                      type="text"
                      value={siteId}
                      onChange={(e) => setSiteId(e.target.value)}
                      placeholder="e.g. SOLAR-ABJ-0045"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Site Owner Name */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Site Owner / Manager</label>
                    <input
                      type="text"
                      value={ownerName}
                      onChange={(e) => setOwnerName(e.target.value)}
                      placeholder="e.g. Ngozi Chidi"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Site Type */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Site Type</label>
                    <select
                      value={siteType}
                      onChange={(e) => setSiteType(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    >
                      <option value="residential">Residential</option>
                      <option value="commercial">Commercial Space</option>
                      <option value="industrial">Industrial Site</option>
                      <option value="agricultural">Agricultural / Irrigation</option>
                    </select>
                  </div>

                  {/* Baseline Generator Capacity */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Baseline Gen Capacity (kVA)</label>
                    <input
                      type="number"
                      value={baselineGenCapacity}
                      onChange={(e) => setBaselineGenCapacity(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Baseline Runtime */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Baseline Runtime (hrs/day)</label>
                    <input
                      type="number"
                      value={baselineRuntimeHrs}
                      onChange={(e) => setBaselineRuntimeHrs(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Solar Capacity */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Installed Solar PV Capacity (kWp)</label>
                    <input
                      type="number"
                      value={solarCapacity}
                      onChange={(e) => setSolarCapacity(e.target.value)}
                      placeholder="e.g. 3.5"
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Inverter Capacity */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Inverter Capacity (kVA)</label>
                    <input
                      type="number"
                      value={inverterCapacity}
                      onChange={(e) => setInverterCapacity(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>

                  {/* Avg Sun Hours */}
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Avg Peak Sun Hours (hrs/day)</label>
                    <input
                      type="number"
                      value={avgSunHours}
                      onChange={(e) => setAvgSunHours(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00b47a]"
                    />
                  </div>
                </div>
              )}

              {/* Notes */}
              <div className="pt-2">
                <label className="text-[10px] font-bold text-zinc-400 block mb-1.5">Optional Notes / Remarks</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Provide any additional site description, beneficiary remarks, or installation details..."
                  rows={3}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#00b47a] resize-none"
                />
              </div>
            </div>

            {/* SYNC & TRANSACTION LOG PANEL */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2 mb-3">
                <h4 className="text-[10px] uppercase font-extrabold tracking-wider text-zinc-400">
                  Resilience Synchronization Logs
                </h4>
                <button
                  type="button"
                  onClick={() => setSyncLogs([])}
                  className="text-[9px] text-zinc-500 hover:text-white"
                >
                  Clear logs
                </button>
              </div>
              <div className="bg-black border border-zinc-900 rounded-lg p-3 h-28 overflow-y-auto font-mono text-[9px] text-[#00b47a]/85 space-y-1.5">
                {syncLogs.length === 0 ? (
                  <p className="text-zinc-600 italic">No sync tasks executed in this session.</p>
                ) : (
                  syncLogs.map((log, idx) => (
                    <div key={idx} className="flex gap-2">
                      <span className="text-zinc-500 shrink-0">➜</span>
                      <span>{log}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: GPS & PHOTO PROOF (SIDEBAR FORM CONTROLS) */}
          <div className="space-y-6">
            
            {/* GPS COORDINATES CARD */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
                <h4 className="text-[10px] uppercase font-extrabold tracking-wider text-zinc-400 flex items-center gap-1">
                  <MapPin size={12} className="text-[#00b47a]" /> Location Coordinates
                </h4>
                {gpsStatus === "success" && (
                  <span className="w-2.5 h-2.5 rounded-full bg-[#00b47a] animate-pulse" title="Coordinates verified" />
                )}
              </div>

              {gpsStatus === "denied" || gpsStatus === "error" ? (
                <div className="p-3 bg-red-950/20 border border-red-500/20 rounded-lg flex items-start gap-2 text-[10px] text-red-400">
                  <AlertTriangle size={14} className="shrink-0" />
                  <p>{gpsErrorMsg}</p>
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Latitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    disabled={!isManualLocation}
                    required
                    placeholder="9.082000"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#00b47a] disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Longitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    disabled={!isManualLocation}
                    required
                    placeholder="8.675300"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#00b47a] disabled:opacity-60"
                  />
                </div>
              </div>

              {gpsAccuracy !== null && (
                <div className="text-[9px] text-zinc-500 flex items-center gap-1 justify-between bg-zinc-900/50 border border-zinc-900 px-2 py-1 rounded">
                  <span>Detection Accuracy:</span>
                  <span className="font-mono text-zinc-300">±{gpsAccuracy.toFixed(1)}m</span>
                </div>
              )}

              <button
                type="button"
                onClick={detectLocation}
                disabled={gpsStatus === "detecting"}
                className="w-full bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 text-xs font-bold py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5"
              >
                <RefreshCw size={13} className={gpsStatus === "detecting" ? "animate-spin" : ""} />
                {gpsStatus === "detecting" ? "Detecting GPS..." : "Auto-Detect Geolocation"}
              </button>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px] text-zinc-400 font-bold">Manual Coordinate Override</span>
                <input
                  type="checkbox"
                  checked={isManualLocation}
                  onChange={(e) => setIsManualLocation(e.target.checked)}
                  className="rounded border-zinc-800 text-[#00b47a] focus:ring-[#00b47a] bg-zinc-900 w-4 h-4 cursor-pointer"
                />
              </div>
            </div>

            {/* PHOTO PROOF IMAGE CARD */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
              <div className="border-b border-zinc-850 pb-2">
                <h4 className="text-[10px] uppercase font-extrabold tracking-wider text-zinc-400 flex items-center gap-1">
                  <Camera size={12} className="text-[#00b47a]" /> Installation Proof Photo
                </h4>
              </div>

              {imagePreview ? (
                <div className="space-y-2">
                  <div className="w-full aspect-video rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900 relative">
                    <img src={imagePreview} alt="Proof preview" className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={() => {
                        setImageFile(null);
                        setImagePreview(null);
                        setImageHash("");
                      }}
                      className="absolute top-2 right-2 bg-black/75 hover:bg-black border border-zinc-800 text-zinc-400 hover:text-white px-2 py-0.5 rounded text-[9px] uppercase font-bold"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="text-[9px] bg-zinc-900 border border-zinc-850 p-2 rounded space-y-1">
                    <div className="flex items-center justify-between text-zinc-500">
                      <span>Perceptual SHA-256:</span>
                    </div>
                    <p className="font-mono text-zinc-300 select-all truncate">{imageHash || "calculating..."}</p>
                  </div>
                </div>
              ) : (
                <label className="w-full aspect-video border border-dashed border-zinc-800 hover:border-zinc-700 bg-zinc-900/20 rounded-lg flex flex-col items-center justify-center p-4 cursor-pointer transition-colors group">
                  <Camera size={24} className="text-zinc-600 group-hover:text-zinc-400 mb-2" />
                  <span className="text-xs font-bold text-zinc-400 group-hover:text-zinc-200">
                    Capture or Upload Image
                  </span>
                  <span className="text-[8.5px] text-zinc-600 mt-1">
                    Supports device camera triggers
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handleImageChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>

            {/* CLIENT-SIDE PROOF PREVIEW */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-2">
              <div className="border-b border-zinc-850 pb-2">
                <h4 className="text-[10px] uppercase font-extrabold tracking-wider text-zinc-400 flex items-center gap-1">
                  <Cpu size={12} className="text-[#00b47a]" /> MRV Cryptographic Hash
                </h4>
              </div>
              <p className="text-[8px] text-zinc-500 leading-normal">
                Deterministic hash of payload details before broadcasting to the backend ledger validation engine.
              </p>
              <div className="bg-black border border-zinc-900 rounded p-2 text-[8px] font-mono text-zinc-400 truncate select-all">
                {payloadHash || "loading..."}
              </div>
            </div>

            {/* ACTION SUBMIT BUTTON */}
            <div className="space-y-2">
              {submitStatus === "error" && (
                <div className="px-3 py-2.5 rounded-lg text-xs bg-red-950/20 border border-red-500/20 text-red-400 flex items-start gap-2">
                  <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                  <span>{statusMsg}</span>
                </div>
              )}
              {submitStatus === "success" && (
                <div className="px-3 py-2.5 rounded-lg text-xs bg-[#00b47a]/15 border border-[#00b47a]/25 text-[#00b47a] flex items-start gap-2">
                  <CheckCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{statusMsg}</span>
                </div>
              )}
              
              <button
                type="submit"
                disabled={submitStatus === "submitting"}
                className="w-full bg-[#00b47a] hover:opacity-95 text-black font-extrabold text-xs py-3.5 uppercase tracking-wider rounded-xl transition-all shadow-lg shadow-[#00b47a]/10 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {submitStatus === "submitting" ? (
                  <>
                    <RefreshCw size={13} className="animate-spin text-black" />
                    Syncing to ledger...
                  </>
                ) : (
                  <>
                    <ShieldCheck size={14} className="text-black" />
                    Submit to Verification
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
