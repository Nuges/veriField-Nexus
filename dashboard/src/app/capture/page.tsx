// =============================================================================
// VeriField Nexus — Mobile Field Capture PWA (Standalone)
// =============================================================================
// Standalone mobile interface for clean cooking (cookstove) and hybrid energy (solar)
// asset captures. Supports full offline persistence (IndexedDB queue & drafts),
// auto-save mechanics, and automatic sync.
// =============================================================================

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
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
  ShieldCheck,
  LogOut,
  Sparkles
} from "lucide-react";
import { uploadProof, createActivity } from "@/lib/api";
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
  images: Record<string, { base64: string; name: string; hash: string }>;
}

// ---------------------------------------------------------------------------
// Native IndexedDB Helpers (No external dependencies)
// ---------------------------------------------------------------------------
const openDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("verifield_capture_db", 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("queue")) {
        db.createObjectStore("queue", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("drafts")) {
        db.createObjectStore("drafts", { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
};

const getFromStore = async (storeName: string, id: string): Promise<any> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, "readonly");
    const store = transaction.objectStore(storeName);
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
};

const getAllFromStore = async (storeName: string): Promise<any[]> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, "readonly");
    const store = transaction.objectStore(storeName);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
};

const saveToStore = async (storeName: string, data: any): Promise<void> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, "readwrite");
    const store = transaction.objectStore(storeName);
    const request = store.put(data);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
};

const deleteFromStore = async (storeName: string, id: string): Promise<void> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, "readwrite");
    const store = transaction.objectStore(storeName);
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
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

// Fallback UUID generator for non-secure HTTP contexts
const generateUUID = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

// Fallback simple string hash for non-secure HTTP contexts where crypto.subtle is undefined
const sha256Fallback = (str: string): string => {
  let hash1 = 0x811c9dc5;
  let hash2 = 0x55555555;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash1 ^= char;
    hash1 = Math.imul(hash1, 0x01000193);
    hash2 = (hash2 << 5) - hash2 + char;
    hash2 &= hash2;
  }
  const h1 = (hash1 >>> 0).toString(16).padStart(8, "0");
  const h2 = (hash2 >>> 0).toString(16).padStart(8, "0");
  return "sha256_fallback_" + h1 + h2 + h1 + h2 + h1 + h2 + h1 + h2;
};

// Compress image client side using Canvas to a max size of 1280px maintaining aspect ratio
const compressImage = (
  file: File,
  maxWidth = 1280,
  maxHeight = 1280,
  quality = 0.8
): Promise<{ file: File; base64: string }> => {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("window is undefined"));
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > height) {
          if (width > maxWidth) {
            height = Math.round((height * maxWidth) / width);
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width = Math.round((width * maxHeight) / height);
            height = maxHeight;
          }
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas context is null"));
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Blob is null"));
              return;
            }
            const compressedFile = new File([blob], file.name, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            const readerBase64 = new FileReader();
            readerBase64.readAsDataURL(compressedFile);
            readerBase64.onloadend = () => {
              resolve({
                file: compressedFile,
                base64: readerBase64.result as string,
              });
            };
            readerBase64.onerror = (e) => reject(e);
          },
          "image/jpeg",
          quality
        );
      };
      img.onerror = (err) => reject(err);
      img.src = event.target?.result as string;
    };
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(file);
  });
};

// ---------------------------------------------------------------------------
// Dynamic Schema Specifications Matching Flutter Client
// ---------------------------------------------------------------------------
interface FormFieldDef {
  key: string;
  label: string;
  type: 'string' | 'int' | 'float' | 'enum' | 'boolean';
  required?: boolean;
  options?: string[];
  placeholder?: string;
}

interface PhotoFieldDef {
  key: string;
  label: string;
  required?: boolean;
  prompt: string;
}

interface FormSection {
  title: string;
  fields: FormFieldDef[];
}

const CLEAN_COOKING_SECTIONS: FormSection[] = [
  {
    title: "Stove Details",
    fields: [
      { key: 'stove_id', label: 'Stove ID (QR/BLE ID)', type: 'string', required: true, placeholder: 'e.g. STOVE-2026-NIG' },
      { key: 'stove_model', label: 'Stove Model', type: 'enum', required: true, options: ['baikuc_gen1', 'tlud_forced', 'rocket', 'gasifier', 'jiko', 'lpg_burner', 'electric_ics', 'other'] },
      { key: 'manufacturer', label: 'Manufacturer', type: 'string', placeholder: 'e.g. Burn Manufacturing' },
      { key: 'serial_number', label: 'Serial Number', type: 'string', placeholder: 'e.g. SN-88392-X' },
    ]
  },
  {
    title: "Household Details",
    fields: [
      { key: 'household_id', label: 'Household ID', type: 'string', required: true, placeholder: 'e.g. HH-9920' },
      { key: 'head_name', label: 'Head of Household Name', type: 'string', required: true, placeholder: 'e.g. Abubakar Yusuf' },
      { key: 'phone_number', label: 'Phone Number', type: 'string', placeholder: 'e.g. +234 803 123 4567' },
      { key: 'household_size', label: 'Household Size', type: 'int', required: true, placeholder: 'e.g. 5' },
      { key: 'meals_per_day', label: 'Meals per Day', type: 'enum', required: true, options: ['1', '2', '3', '4+'] },
      { key: 'consent_obtained', label: 'Consent Obtained?', type: 'boolean', required: true },
    ]
  },
  {
    title: "Baseline Data",
    fields: [
      { key: 'baseline_fuel', label: 'Primary Baseline Fuel', type: 'enum', required: true, options: ['wood', 'charcoal', 'crop_residue', 'dung', 'kerosene', 'lpg', 'grid_electric'] },
      { key: 'baseline_stove', label: 'Baseline Stove Type', type: 'enum', required: true, options: ['3_stone_fire', 'traditional_clay', 'metal_grate', 'kerosene_stove', 'gas_burner', 'other'] },
      { key: 'baseline_fuel_consumption', label: 'Monthly Fuel Before (kg/L)', type: 'float', required: true, placeholder: 'e.g. 120' },
      { key: 'baseline_fuel_cost', label: 'Monthly Fuel Cost Before (₦)', type: 'float', required: true, placeholder: 'e.g. 15000' },
      { key: 'baseline_cooking_duration', label: 'Daily Cooking Before (hrs)', type: 'float', required: true, placeholder: 'e.g. 4.5' },
      { key: 'fuel_source', label: 'Fuel Source', type: 'enum', required: true, options: ['collected_free', 'purchased'] },
    ]
  },
  {
    title: "Project Data",
    fields: [
      { key: 'primary_fuel', label: 'Project Primary Fuel', type: 'enum', required: true, options: ['wood', 'pellet', 'charcoal', 'lpg', 'biogas', 'electric'] },
      { key: 'usage_flag', label: 'Currently in Use?', type: 'boolean', required: true },
      { key: 'project_cooking_duration', label: 'Daily Cooking Now (hrs)', type: 'float', required: true, placeholder: 'e.g. 2.5' },
      { key: 'stove_condition', label: 'Stove Condition', type: 'enum', required: true, options: ['good', 'minor_damage', 'needs_repair', 'abandoned'] },
    ]
  }
];

const HYBRID_ENERGY_SECTIONS: FormSection[] = [
  {
    title: "Site & Owner Identity",
    fields: [
      { key: 'site_id', label: 'Site ID', type: 'string', required: true, placeholder: 'e.g. SOLAR-ABJ-0045' },
      { key: 'owner_name', label: 'Site Owner / Manager Name', type: 'string', required: true, placeholder: 'e.g. Ngozi Chidi' },
      { key: 'owner_phone', label: 'Owner Phone Number', type: 'string', placeholder: 'e.g. +234 802 987 6543' },
      { key: 'site_type', label: 'Site Type', type: 'enum', required: true, options: ['residential', 'commercial', 'industrial', 'institutional', 'telecom_tower', 'agricultural'] },
      { key: 'consent_obtained', label: 'Owner Consent Obtained?', type: 'boolean', required: true },
    ]
  },
  {
    title: "Baseline Generator Details",
    fields: [
      { key: 'baseline_generator_type', label: 'Baseline Generator Type', type: 'enum', required: true, options: ['diesel', 'petrol', 'heavy_fuel_oil'] },
      { key: 'baseline_generator_capacity_kva', label: 'Generator Capacity (kVA)', type: 'float', required: true, placeholder: 'e.g. 15.0' },
      { key: 'baseline_fuel_consumption_lph', label: 'Fuel Consumption Rate (L/hr)', type: 'float', required: true, placeholder: 'e.g. 2.5' },
      { key: 'baseline_avg_daily_runtime_hrs', label: 'Avg Daily Runtime (hrs)', type: 'float', required: true, placeholder: 'e.g. 8.0' },
      { key: 'baseline_operating_days_per_year', label: 'Operating Days Per Year', type: 'int', required: true, placeholder: 'e.g. 300' },
      { key: 'baseline_monthly_fuel_cost', label: 'Monthly Fuel Cost (₦)', type: 'float', placeholder: 'e.g. 250000' },
    ]
  },
  {
    title: "Post-Installation Hybrid System",
    fields: [
      { key: 'solar_capacity_kwp', label: 'Solar PV Capacity (kWp)', type: 'float', required: true, placeholder: 'e.g. 10.0' },
      { key: 'battery_capacity_kwh', label: 'Battery Storage (kWh)', type: 'float', placeholder: 'e.g. 15.0' },
      { key: 'inverter_capacity_kva', label: 'Inverter Capacity (kVA)', type: 'float', required: true, placeholder: 'e.g. 8.0' },
      { key: 'gas_generator_capacity_kva', label: 'Gas Generator (kVA)', type: 'float', placeholder: 'e.g. 0.0' },
      { key: 'diesel_backup_capacity_kva', label: 'Diesel Backup (kVA)', type: 'float', placeholder: 'e.g. 15.0' },
      { key: 'installer_name', label: 'Installer / EPC Company', type: 'string', placeholder: 'e.g. Solarthon Energy' },
      { key: 'installation_date', label: 'Installation Date', type: 'string', required: true, placeholder: 'YYYY-MM-DD' },
    ]
  },
  {
    title: "Data Source Configuration",
    fields: [
      { key: 'data_source', label: 'Primary Data Source', type: 'enum', required: true, options: ['smart_inverter_api', 'hybrid_inverter_manual', 'analog_manual'] },
      { key: 'inverter_brand', label: 'Inverter Brand / Model', type: 'string', placeholder: 'e.g. Growatt SPF 5000 ES' },
      { key: 'inverter_serial_number', label: 'Inverter Serial Number', type: 'string', placeholder: 'e.g. GRW-2026-X88' },
      { key: 'avg_sun_hours', label: 'Average Peak Sun Hours (hrs/day)', type: 'float', required: true, placeholder: 'e.g. 5.2' },
      { key: 'system_efficiency', label: 'System Efficiency Factor (0-1)', type: 'float', placeholder: 'e.g. 0.85' },
    ]
  },
  {
    title: "Verification Checklist",
    fields: [
      { key: 'system_installed', label: 'System Installed & Commissioned?', type: 'boolean', required: true },
      { key: 'system_operational', label: 'System Currently Operational?', type: 'boolean', required: true },
      { key: 'tamper_signs', label: 'Tampering Signs Detected?', type: 'boolean', required: true },
      { key: 'usage_confirmed', label: 'Active Usage Confirmed?', type: 'boolean', required: true },
    ]
  }
];

const CLEAN_COOKING_PHOTOS: PhotoFieldDef[] = [
  { key: 'stove_installation', label: 'Stove Installation Photo', required: true, prompt: 'Take a clear photo of the newly installed clean cookstove in the kitchen.' },
  { key: 'baseline_fuel_source', label: 'Old Stove / Baseline Fuel Photo', required: false, prompt: 'Capture the traditional open fire or old cooking device (if present).' }
];

const HYBRID_ENERGY_PHOTOS: PhotoFieldDef[] = [
  { key: 'solar_installation', label: 'Solar PV Installation Photo', required: true, prompt: 'Take a wide-angle shot of the newly installed solar panels or hybrid system.' },
  { key: 'baseline_generator', label: 'Baseline Diesel Generator Photo', required: true, prompt: 'Capture the old baseline diesel or petrol generator for displacement proof.' },
  { key: 'inverter_label', label: 'Inverter Nameplate Photo', required: false, prompt: 'Capture the brand/serial number printed on the inverter unit.' }
];

const getDefaultValues = (tab: "CLEAN_COOKING" | "HYBRID_ENERGY") => {
  if (tab === "CLEAN_COOKING") {
    return {
      stove_model: 'baikuc_gen1',
      meals_per_day: '3',
      baseline_fuel: 'wood',
      baseline_stove: '3_stone_fire',
      fuel_source: 'collected_free',
      primary_fuel: 'wood',
      stove_condition: 'good',
      consent_obtained: true,
      usage_flag: true,
    };
  } else {
    return {
      site_type: 'residential',
      baseline_generator_type: 'diesel',
      data_source: 'smart_inverter_api',
      system_installed: true,
      system_operational: true,
      tamper_signs: false,
      usage_confirmed: true,
      consent_obtained: true,
    };
  }
};

export default function StandaloneCapturePage() {
  const { user, isLoading, error, refreshUser } = useWorkspace();
  const router = useRouter();

  // --- TAB STATE ---
  const [activeTab, setActiveTab] = useState<"CLEAN_COOKING" | "HYBRID_ENERGY">("CLEAN_COOKING");
  
  // --- FORM STATE ---
  const [notes, setNotes] = useState("");
  const [formValues, setFormValues] = useState<Record<string, any>>(() => getDefaultValues("CLEAN_COOKING"));
  
  // Dynamic Photo States mapping field keys (e.g. 'stove_installation')
  const [imagePreviews, setImagePreviews] = useState<Record<string, string>>({});
  const [imageHashes, setImageHashes] = useState<Record<string, string>>({});
  const [imageFiles, setImageFiles] = useState<Record<string, File>>({});

  const [payloadHash, setPayloadHash] = useState<string>("");
  const [draftSavedTime, setDraftSavedTime] = useState<string>("");
  const [isDraftSaving, setIsDraftSaving] = useState(false);
  
  // --- LOCATION STATE ---
  const [latitude, setLatitude] = useState<string>("");
  const [longitude, setLongitude] = useState<string>("");
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [isManualLocation, setIsManualLocation] = useState(false);
  const [gpsStatus, setGpsStatus] = useState<"idle" | "detecting" | "success" | "denied" | "error">("idle");
  const [gpsErrorMsg, setGpsErrorMsg] = useState("");

  // --- SYSTEM STATES ---
  const [installationId, setInstallationId] = useState("");
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [queue, setQueue] = useState<QueuedActivity[]>([]);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [syncLogs, setSyncLogs] = useState<string[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  // --- REFS FOR AUTO-SAVE AVOIDANCE ---
  const initialLoadDone = useRef(false);

  // Redirect to login if user is not authenticated
  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      window.location.href = "/login?redirect=/capture";
    }
  }, [user, isLoading]);

  // Initialize network listeners, fetch queue, and reload draft
  useEffect(() => {
    generateNewInstallation();
    
    const checkOnline = () => {
      setIsOnline(navigator.onLine);
    };
    window.addEventListener("online", checkOnline);
    window.addEventListener("offline", checkOnline);
    
    // Load IndexedDB queue
    getAllFromStore("queue").then((savedQueue) => {
      setQueue(savedQueue);
    }).catch(e => console.error("Failed to load IndexedDB queue", e));

    // Load active draft
    getFromStore("drafts", "active_draft").then((savedDraft) => {
      if (savedDraft) {
        const restoredTab = savedDraft.activeTab || "CLEAN_COOKING";
        setActiveTab(restoredTab);
        setNotes(savedDraft.notes || "");
        
        // Restore photos maps
        const previews = savedDraft.imagePreviews || {};
        const hashes = savedDraft.imageHashes || {};
        const names = savedDraft.imageNames || {};
        
        setImagePreviews(previews);
        setImageHashes(hashes);
        
        setLatitude(savedDraft.latitude || "");
        setLongitude(savedDraft.longitude || "");
        setGpsAccuracy(savedDraft.gpsAccuracy || null);
        setIsManualLocation(savedDraft.isManualLocation || false);
        setFormValues(savedDraft.formValues || getDefaultValues(restoredTab));

        // Re-create virtual files for uploads
        const files: Record<string, File> = {};
        Object.keys(previews).forEach((key) => {
          try {
            if (previews[key]) {
              const file = base64ToFile(previews[key], names[key] || `${key}_photo.jpg`);
              files[key] = file;
            }
          } catch(e) {
            console.error(`Failed to restore draft image file for ${key}:`, e);
          }
        });
        setImageFiles(files);

        addLog("Restored draft save state from IndexedDB.");
        setDraftSavedTime(new Date(savedDraft.updated_at).toLocaleTimeString());
      }
      initialLoadDone.current = true;
    }).catch(err => {
      console.error("Failed to load IndexedDB draft:", err);
      initialLoadDone.current = true;
    });

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
    setInstallationId(generateUUID());
  };

  // Structured payload builder with schema-based dynamic type casting
  const getStructuredData = useCallback(() => {
    const data: Record<string, any> = {};
    
    // First, merge defaults for the current tab to make sure required fields are not empty
    const defaults = getDefaultValues(activeTab) as Record<string, any>;
    const mergedValues = { ...defaults, ...formValues };

    const sections = activeTab === "CLEAN_COOKING" ? CLEAN_COOKING_SECTIONS : HYBRID_ENERGY_SECTIONS;
    
    for (const section of sections) {
      for (const field of section.fields) {
        const rawValue = mergedValues[field.key];
        if (rawValue === undefined || rawValue === null || rawValue === "") {
          if (field.type === 'boolean') {
            data[field.key] = false;
          } else if (field.type === 'int' || field.type === 'float') {
            data[field.key] = 0;
          } else {
            data[field.key] = "";
          }
          continue;
        }

        if (field.type === 'int') {
          data[field.key] = parseInt(rawValue) || 0;
        } else if (field.type === 'float') {
          data[field.key] = parseFloat(rawValue) || 0;
        } else if (field.type === 'boolean') {
          data[field.key] = rawValue === true || rawValue === 'true';
        } else {
          data[field.key] = String(rawValue);
        }
      }
    }

    return data;
  }, [activeTab, formValues]);

  // Recalculate Cryptographic SHA-256 Payload Hash
  const recalculatePayloadHash = useCallback(async () => {
    const activity_data = getStructuredData();
    const primaryKey = activeTab === "CLEAN_COOKING" ? "stove_installation" : "solar_installation";
    const primaryHash = imageHashes[primaryKey] || "";

    const meta = {
      id: installationId,
      activity_type: activeTab,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null,
      image_hash: primaryHash,
      captured_at: new Date().toISOString(),
      activity_data,
    };
    try {
      if (typeof crypto !== "undefined" && crypto.subtle) {
        const msgUint8 = new TextEncoder().encode(JSON.stringify(meta));
        const hashBuffer = await crypto.subtle.digest("SHA-256", msgUint8);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
        setPayloadHash("sha256_" + hashHex);
      } else {
        setPayloadHash(sha256Fallback(JSON.stringify(meta)));
      }
    } catch (e) {
      console.error("Payload hash calculation failed:", e);
      setPayloadHash(sha256Fallback(JSON.stringify(meta)));
    }
  }, [activeTab, imageHashes, latitude, longitude, getStructuredData, installationId]);

  useEffect(() => {
    recalculatePayloadHash();
  }, [activeTab, imageHashes, latitude, longitude, recalculatePayloadHash]);

  // --- AUTO-SAVE FORM STATE EVERY 5 SECONDS ---
  useEffect(() => {
    const interval = setInterval(async () => {
      if (!initialLoadDone.current) return;
      
      setIsDraftSaving(true);
      const draftData = {
        id: "active_draft",
        activeTab,
        notes,
        imagePreviews,
        imageHashes,
        imageNames: Object.keys(imageFiles).reduce((acc, key) => {
          acc[key] = imageFiles[key]?.name || "photo.jpg";
          return acc;
        }, {} as Record<string, string>),
        latitude,
        longitude,
        gpsAccuracy,
        isManualLocation,
        formValues,
        updated_at: new Date().toISOString()
      };
      
      try {
        await saveToStore("drafts", draftData);
        setDraftSavedTime(new Date().toLocaleTimeString());
      } catch (e) {
        console.error("PWA Auto-save failed:", e);
      } finally {
        setTimeout(() => setIsDraftSaving(false), 800);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [
    activeTab, notes, imagePreviews, imageHashes, imageFiles, latitude, longitude,
    gpsAccuracy, isManualLocation, formValues
  ]);

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
          setGpsErrorMsg("Location permission denied. Enable GPS in settings.");
        } else {
          setGpsErrorMsg(error.message || "Failed to retrieve coordinates.");
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  const handleImageChange = async (key: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      addLog(`Compressing image "${file.name}"...`);
      const compressed = await compressImage(file);
      const compressedFile = compressed.file;
      const base64Data = compressed.base64;

      setImageFiles((prev) => ({ ...prev, [key]: compressedFile }));
      setImagePreviews((prev) => ({ ...prev, [key]: base64Data }));

      // Compute Image Cryptographic SHA-256 Hash of compressed image
      if (typeof crypto !== "undefined" && crypto.subtle) {
        const arrayBuffer = await compressedFile.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
        setImageHashes((prev) => ({ ...prev, [key]: "sha256_" + hashHex }));
      } else {
        const rawString = `${compressedFile.name}-${compressedFile.size}-${compressedFile.lastModified}`;
        setImageHashes((prev) => ({ ...prev, [key]: sha256Fallback(rawString) }));
      }
      addLog(`Image "${file.name}" compressed successfully (size reduced to ${Math.round(compressedFile.size / 1024)} KB).`);
    } catch (err: any) {
      console.error("Failed to compress image, using original:", err);
      addLog(`Failed to compress image: ${err.message || err}. Using original file.`);
      
      setImageFiles((prev) => ({ ...prev, [key]: file }));
      
      // Generate preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreviews((prev) => ({ ...prev, [key]: reader.result as string }));
      };
      reader.readAsDataURL(file);

      // Compute Image Cryptographic SHA-256 Hash of original image
      try {
        if (typeof crypto !== "undefined" && crypto.subtle) {
          const arrayBuffer = await file.arrayBuffer();
          const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
          const hashArray = Array.from(new Uint8Array(hashBuffer));
          const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
          setImageHashes((prev) => ({ ...prev, [key]: "sha256_" + hashHex }));
        } else {
          const rawString = `${file.name}-${file.size}-${file.lastModified}`;
          setImageHashes((prev) => ({ ...prev, [key]: sha256Fallback(rawString) }));
        }
      } catch (hashErr) {
        const rawString = `${file.name}-${file.size}-${file.lastModified}`;
        setImageHashes((prev) => ({ ...prev, [key]: sha256Fallback(rawString) }));
      }
    }
  };

  const addLog = (msg: string) => {
    setSyncLogs((prev) => [
      `[${new Date().toLocaleTimeString()}] ${msg}`,
      ...prev,
    ]);
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
        const uploadedUrls: Record<string, string> = {};
        let primaryUrl = "";
        
        // Upload each image in the item
        const imageKeys = Object.keys(item.images || {});
        for (const key of imageKeys) {
          const img = item.images[key];
          if (img && img.base64) {
            addLog(`Uploading photo: ${key}...`);
            const fileToUpload = base64ToFile(img.base64, img.name || `${key}_photo.jpg`);
            const uploadRes = await uploadProof(fileToUpload);
            uploadedUrls[`${key}_image_url`] = uploadRes.image_url;
            
            const primaryKey = item.activity_type === "CLEAN_COOKING" ? "stove_installation" : "solar_installation";
            if (key === primaryKey) {
              primaryUrl = uploadRes.image_url;
            }
          }
        }

        // Merge uploaded photo URLs into activity_data
        const finalActivityData = {
          ...item.activity_data,
          ...uploadedUrls
        };

        const primaryKey = item.activity_type === "CLEAN_COOKING" ? "stove_installation" : "solar_installation";
        const primaryHash = item.images?.[primaryKey]?.hash || "";

        // Submit activity payload
        await createActivity({
          activity_type: item.activity_type,
          activity_data: finalActivityData,
          description: item.description,
          latitude: item.latitude,
          longitude: item.longitude,
          gps_accuracy: item.gps_accuracy,
          image_url: primaryUrl,
          image_hash: primaryHash,
          captured_at: item.captured_at,
          client_id: item.id,
        });

        addLog(`Successfully synced activity ${item.id.slice(0, 8)} to database.`);
        
        // Remove item from IndexedDB queue
        await deleteFromStore("queue", item.id);
        updatedQueue.shift();
        setQueue([...updatedQueue]);
      } catch (err: any) {
        addLog(`Sync error for activity ${item.id.slice(0, 8)}: ${err.message || err}. Pausing sync.`);
        break;
      }
    }
    setIsSyncing(false);
  };

  // Submit capture form
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitStatus("submitting");
    setStatusMsg("");

    if (!latitude || !longitude) {
      setSubmitStatus("error");
      setStatusMsg("GPS coordinates are required for verification.");
      return;
    }

    // Check that required photos are present
    const photos = activeTab === "CLEAN_COOKING" ? CLEAN_COOKING_PHOTOS : HYBRID_ENERGY_PHOTOS;
    for (const photo of photos) {
      if (photo.required && !imagePreviews[photo.key]) {
        setSubmitStatus("error");
        setStatusMsg(`The photo "${photo.label}" is required.`);
        return;
      }
    }

    const payload_data = getStructuredData();
    const currentTimestamp = new Date().toISOString();

    if (effectiveOnline) {
      // ONLINE PIPELINE INGESTION
      try {
        const uploadedUrls: Record<string, string> = {};
        let primaryUrl = "";

        const keys = Object.keys(imagePreviews);
        for (const key of keys) {
          const file = imageFiles[key];
          const preview = imagePreviews[key];
          if (file || preview) {
            setStatusMsg(`Uploading photo "${key}" to storage...`);
            const fileToUpload = file || base64ToFile(preview, `${key}_photo.jpg`);
            const uploadRes = await uploadProof(fileToUpload);
            uploadedUrls[`${key}_image_url`] = uploadRes.image_url;
            
            const primaryKey = activeTab === "CLEAN_COOKING" ? "stove_installation" : "solar_installation";
            if (key === primaryKey) {
              primaryUrl = uploadRes.image_url;
            }
          }
        }

        const primaryKey = activeTab === "CLEAN_COOKING" ? "stove_installation" : "solar_installation";
        const primaryHash = imageHashes[primaryKey] || "";

        // Merge photos into activity_data
        const finalActivityData = {
          ...payload_data,
          ...uploadedUrls
        };

        setStatusMsg("Submitting structured record to verification engine...");
        await createActivity({
          activity_type: activeTab,
          activity_data: finalActivityData,
          description: notes,
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
          gps_accuracy: gpsAccuracy,
          image_url: primaryUrl,
          image_hash: primaryHash,
          captured_at: currentTimestamp,
          client_id: installationId,
        });

        setSubmitStatus("success");
        setStatusMsg("Activity written to Supabase successfully. Live metrics updated.");
        
        // Clean draft upon successful submit
        await deleteFromStore("drafts", "active_draft");
        resetForm();
      } catch (err: any) {
        setSubmitStatus("error");
        setStatusMsg(err.message || "Failed to submit field activity.");
      }
    } else {
      // OFFLINE QUEUE PIPELINE (INDEXEDDB)
      const queueImages: Record<string, { base64: string; name: string; hash: string }> = {};
      const keys = Object.keys(imagePreviews);
      for (const key of keys) {
        queueImages[key] = {
          base64: imagePreviews[key],
          name: imageFiles[key]?.name || `${key}_photo.jpg`,
          hash: imageHashes[key] || "",
        };
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
        images: queueImages,
      };

      try {
        await saveToStore("queue", queuedItem);
        const savedQueue = await getAllFromStore("queue");
        setQueue(savedQueue);
        
        setSubmitStatus("success");
        setStatusMsg("Offline submission saved! Draft will sync automatically when Wi-Fi is restored.");
        
        // Clean active draft upon queuing
        await deleteFromStore("drafts", "active_draft");
        resetForm();
      } catch (err) {
        setSubmitStatus("error");
        setStatusMsg("Failed to store capture offline in IndexedDB.");
      }
    }
  };

  const resetForm = () => {
    generateNewInstallation();
    setNotes("");
    setImagePreviews({});
    setImageHashes({});
    setImageFiles({});
    setFormValues(getDefaultValues(activeTab));
  };

  const handleSignOut = () => {
    localStorage.removeItem("vf_token");
    router.push("/login?redirect=/capture");
  };

  const sections = activeTab === "CLEAN_COOKING" ? CLEAN_COOKING_SECTIONS : HYBRID_ENERGY_SECTIONS;
  const photos = activeTab === "CLEAN_COOKING" ? CLEAN_COOKING_PHOTOS : HYBRID_ENERGY_PHOTOS;

  // --- LOADING TIMEOUT: Escape hatch for stale service worker caches ---
  const [loadingTooLong, setLoadingTooLong] = useState(false);
  useEffect(() => {
    if (!isLoading) {
      setLoadingTooLong(false);
      return;
    }
    const timer = setTimeout(() => setLoadingTooLong(true), 8000);
    return () => clearTimeout(timer);
  }, [isLoading]);

  const handleClearCacheAndRetry = async () => {
    try {
      // Purge all service worker caches
      if ("caches" in window) {
        const cacheNames = await caches.keys();
        for (const name of cacheNames) {
          await caches.delete(name);
        }
      }
      // Unregister all service workers
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const reg of registrations) {
          await reg.unregister();
        }
      }
    } catch (e) {
      console.error("Cache clear failed:", e);
    }
    // Hard reload bypassing any cache
    window.location.reload();
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#090F10] space-y-3 px-4">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-[#8E9E9B] text-xs font-semibold tracking-tight animate-pulse text-center">
          Connecting to secure digital MRV ledger...
        </p>
        {loadingTooLong && (
          <div className="mt-6 w-full max-w-xs space-y-3 animate-fade-in-up">
            <p className="text-[10px] text-amber-400 text-center font-medium">
              Connection is taking longer than expected. This may be caused by stale cached data on your device.
            </p>
            <button
              onClick={handleClearCacheAndRetry}
              className="w-full py-2.5 bg-[#00B47A] text-black text-xs font-extrabold rounded-xl hover:opacity-90 transition-opacity"
            >
              Clear Cache &amp; Retry
            </button>
            <button
              onClick={() => { localStorage.removeItem("vf_token"); window.location.href = "/login?redirect=/capture"; }}
              className="w-full py-2.5 bg-[#141F20] border border-[#213233] text-white text-xs font-bold rounded-xl hover:bg-[#1c2a2b] transition-colors"
            >
              Go to Login
            </button>
          </div>
        )}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#090F10] px-4 space-y-4">
        <div className="bg-[#0E1617] border border-[#213233] p-6 rounded-2xl max-w-sm w-full text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center mx-auto text-red-400">
            <AlertTriangle size={24} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Ledger Connection Failed</h3>
            <p className="text-xs text-[#8E9E9B] mt-2 leading-relaxed">
              {error || "Unable to authenticate session. Please ensure your device can reach the host server."}
            </p>
          </div>
          <div className="pt-2 space-y-2">
            <button
              onClick={() => refreshUser()}
              className="w-full py-2.5 bg-[#00B47A] text-black text-xs font-extrabold rounded-xl hover:opacity-90 transition-opacity"
            >
              Retry Connection
            </button>
            <button
              onClick={handleSignOut}
              className="w-full py-2.5 bg-[#141F20] border border-[#213233] text-white text-xs font-bold rounded-xl hover:bg-[#1c2a2b] transition-colors"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto min-h-screen flex flex-col justify-between bg-[#090F10] pb-24 relative select-none">
      
      {/* 1. STANDALONE MOBILE PWA HEADER */}
      <header className="sticky top-0 z-40 bg-[#0E1617]/90 backdrop-blur-md border-b border-[#213233] px-4 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#00B47A]/10 border border-[#00B47A]/30 flex items-center justify-center">
            <Cpu size={15} className="text-[#00B47A]" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white tracking-tight leading-none">
              VeriField Capture
            </h1>
            <p className="text-[9px] text-[#8E9E9B] uppercase font-bold tracking-wider mt-0.5">
              Edge Terminal
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status Badge */}
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[9px] font-extrabold transition-all duration-300 ${
            effectiveOnline 
              ? "bg-[#00B47A]/10 border-[#00B47A]/25 text-[#00B47A]"
              : "bg-amber-500/10 border-amber-500/25 text-amber-500"
          }`}>
            {effectiveOnline ? (
              <>
                <Wifi size={10} />
                <span>ONLINE</span>
              </>
            ) : (
              <>
                <WifiOff size={10} />
                <span>OFFLINE</span>
              </>
            )}
          </div>

          {/* Sign Out Button */}
          <button 
            type="button"
            onClick={handleSignOut}
            className="p-1.5 rounded-lg bg-[#141F20] border border-[#213233] text-[#8E9E9B] hover:text-white"
            title="Log out"
          >
            <LogOut size={13} />
          </button>
        </div>
      </header>

      {/* 2. AUTO-SAVE & QUEUE SYNC MICRO BAR */}
      <div className="px-4 pt-3 flex items-center justify-between text-[9px] text-[#5F6F6C]">
        <div className="flex items-center gap-1">
          <Database size={10} />
          <span>Queue size: <b>{queue.length}</b></span>
        </div>
        
        <div className="flex items-center gap-1">
          <Sparkles size={9} className={isDraftSaving ? "animate-spin text-[#00B47A]" : ""} />
          <span>
            {isDraftSaving ? "Saving draft..." : draftSavedTime ? `Saved: ${draftSavedTime}` : "No draft saved"}
          </span>
        </div>
      </div>

      <main className="flex-1 px-4 py-4 space-y-5">

        {/* OFFLINE SYNC PANEL */}
        {queue.length > 0 && (
          <div className="bg-[#141F20] border border-amber-500/25 rounded-xl p-3.5 flex items-center justify-between gap-3 animate-fade-in-up">
            <div>
              <p className="text-xs font-bold text-white flex items-center gap-1.5">
                <Database size={12} className="text-amber-500" />
                Offline drafts pending upload
              </p>
              <p className="text-[9.5px] text-[#8E9E9B] mt-0.5">
                Your captures are securely buffered in device memory.
              </p>
            </div>
            <button
              onClick={syncQueue}
              disabled={isSyncing || !isOnline}
              className="px-3.5 py-1.5 bg-[#00B47A] text-black text-[10px] font-extrabold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 uppercase tracking-wider shrink-0"
            >
              <RefreshCw size={11} className={isSyncing ? "animate-spin" : ""} />
              {isSyncing ? "Syncing" : "Sync"}
            </button>
          </div>
        )}

        {/* MANUAL OFFLINE SIMULATOR TOGGLE */}
        <div className="bg-[#0E1617] border border-[#213233] rounded-xl p-2.5 flex items-center justify-between">
          <span className="text-[10px] text-[#8E9E9B] font-bold">Simulate Offline Mode (Field Test)</span>
          <button
            type="button"
            onClick={() => setIsOfflineMode(!isOfflineMode)}
            className={`px-3 py-1 rounded-lg text-[9px] font-black uppercase border transition-colors ${
              isOfflineMode 
                ? "bg-amber-950/20 text-amber-500 border-amber-500/30"
                : "bg-[#141F20] text-[#8E9E9B] border-[#213233] hover:text-white"
            }`}
          >
            {isOfflineMode ? "Force Online" : "Simulate Offline"}
          </button>
        </div>

        {/* FORM CONTAINER */}
        <form onSubmit={handleFormSubmit} className="space-y-4">
          
          {/* SECTOR PICKER TABS */}
          <div className="bg-[#0E1617] border border-[#213233] rounded-xl p-1.5 flex gap-1">
            <button
              type="button"
              onClick={() => {
                setActiveTab("CLEAN_COOKING");
                setFormValues(getDefaultValues("CLEAN_COOKING"));
                setImagePreviews({});
                setImageHashes({});
                setImageFiles({});
              }}
              className={`flex-1 text-center py-2 text-[11px] font-black rounded-lg transition-all ${
                activeTab === "CLEAN_COOKING"
                  ? "bg-[#141F20] text-[#00B47A] border border-[#00B47A]/30"
                  : "text-[#8E9E9B] hover:text-white"
              }`}
            >
              Cookstove Module
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab("HYBRID_ENERGY");
                setFormValues(getDefaultValues("HYBRID_ENERGY"));
                setImagePreviews({});
                setImageHashes({});
                setImageFiles({});
              }}
              className={`flex-1 text-center py-2 text-[11px] font-black rounded-lg transition-all ${
                activeTab === "HYBRID_ENERGY"
                  ? "bg-[#141F20] text-[#00B47A] border border-[#00B47A]/30"
                  : "text-[#8E9E9B] hover:text-white"
              }`}
            >
              Solar Hybrid PV
            </button>
          </div>

          {/* DYNAMIC TELEMETRY FORM */}
          <div className="bg-[#0E1617] border border-[#213233] rounded-2xl p-4 space-y-4">
            
            <div className="flex items-center justify-between border-b border-[#213233] pb-2">
              <span className="text-[10px] font-black uppercase tracking-wider text-[#8E9E9B]">
                Installation Telemetry
              </span>
              <span className="text-[8px] font-mono text-[#5F6F6C]">
                ID: {installationId.slice(0, 8)}
              </span>
            </div>

            {sections.map((section, sIdx) => (
              <div key={sIdx} className="space-y-3 pt-2">
                <h3 className="text-[10px] font-black uppercase tracking-wider text-[#00B47A]/90 border-b border-[#213233]/60 pb-1 flex items-center justify-between">
                  <span>{section.title}</span>
                </h3>
                <div className="grid grid-cols-1 gap-3">
                  {section.fields.map((field) => {
                    const value = formValues[field.key] !== undefined ? formValues[field.key] : ((getDefaultValues(activeTab) as Record<string, any>)[field.key] || "");
                    
                    return (
                      <div key={field.key} className="space-y-1">
                        <label className="text-[9px] font-bold text-[#8E9E9B] block">
                          {field.label} {field.required && <span className="text-amber-500">*</span>}
                        </label>
                        
                        {field.type === 'enum' ? (
                          <select
                            value={value}
                            onChange={(e) => setFormValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                            className="w-full bg-[#141F20] border border-[#213233] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00B47A]"
                          >
                            {field.options?.map((opt) => (
                              <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
                            ))}
                          </select>
                        ) : field.type === 'boolean' ? (
                          <div className="flex items-center justify-between bg-[#141F20] border border-[#213233] px-3 py-2 rounded-lg">
                            <span className="text-xs text-[#8E9E9B]">
                              {value === true || value === 'true' ? 'Yes' : 'No'}
                            </span>
                            <input
                              type="checkbox"
                              checked={value === true || value === 'true'}
                              onChange={(e) => setFormValues((prev) => ({ ...prev, [field.key]: e.target.checked }))}
                              className="w-4 h-4 rounded border-[#213233] bg-[#0E1617] text-[#00B47A] focus:ring-0 cursor-pointer"
                            />
                          </div>
                        ) : (
                          <input
                            type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
                            step={field.type === 'float' ? '0.0001' : undefined}
                            value={value}
                            onChange={(e) => setFormValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                            placeholder={field.placeholder}
                            required={field.required}
                            className="w-full bg-[#141F20] border border-[#213233] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5F6F6C] focus:outline-none focus:border-[#00B47A]"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {/* Optional notes */}
            <div>
              <label className="text-[9px] font-bold text-[#8E9E9B] block mb-1">Remarks / On-site Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Describe site accessibility or installation status..."
                rows={2}
                className="w-full bg-[#141F20] border border-[#213233] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5F6F6C] focus:outline-none focus:border-[#00B47A] resize-none"
              />
            </div>
          </div>

          {/* GPS AND GEOLOCATION CARD */}
          <div className="bg-[#0E1617] border border-[#213233] rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-[#213233] pb-2">
              <span className="text-[10px] font-black uppercase tracking-wider text-[#8E9E9B] flex items-center gap-1">
                <MapPin size={11} className="text-[#00B47A]" /> GPS Geolocation
              </span>
              {gpsStatus === "success" && (
                <span className="w-2 h-2 rounded-full bg-[#00B47A] animate-pulse" />
              )}
            </div>

            {gpsErrorMsg && (
              <div className="p-2.5 bg-red-950/20 border border-red-500/20 rounded-lg text-[10px] text-red-400 flex items-start gap-1.5">
                <AlertTriangle size={13} className="shrink-0 mt-0.5" />
                <p className="leading-normal">{gpsErrorMsg}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-[8.5px] font-bold text-[#5F6F6C] block mb-0.5">LATITUDE</span>
                <input
                  type="number"
                  step="0.000001"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  disabled={!isManualLocation}
                  required
                  placeholder="e.g. 9.0820"
                  className="w-full bg-[#141F20] border border-[#213233] rounded-lg px-3 py-2 text-xs text-white disabled:opacity-60 focus:outline-none focus:border-[#00B47A]"
                />
              </div>
              <div>
                <span className="text-[8.5px] font-bold text-[#5F6F6C] block mb-0.5">LONGITUDE</span>
                <input
                  type="number"
                  step="0.000001"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  disabled={!isManualLocation}
                  required
                  placeholder="e.g. 8.6753"
                  className="w-full bg-[#141F20] border border-[#213233] rounded-lg px-3 py-2 text-xs text-white disabled:opacity-60 focus:outline-none focus:border-[#00B47A]"
                />
              </div>
            </div>

            {gpsAccuracy !== null && (
              <div className="text-[8.5px] text-[#8E9E9B] flex items-center justify-between bg-[#141F20] px-2 py-1 rounded">
                <span>Accuracy:</span>
                <span className="font-mono font-bold text-white">±{gpsAccuracy.toFixed(1)}m</span>
              </div>
            )}

            <button
              type="button"
              onClick={detectLocation}
              disabled={gpsStatus === "detecting"}
              className="w-full py-2 bg-[#141F20] hover:bg-[#1c2a2b] border border-[#213233] text-white text-[11px] font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <RefreshCw size={11} className={gpsStatus === "detecting" ? "animate-spin" : ""} />
              {gpsStatus === "detecting" ? "Locking GPS Coordinates..." : "Lock GPS Location"}
            </button>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[9.5px] text-[#8E9E9B] font-bold">Manual Coordinate Override</span>
              <input
                type="checkbox"
                checked={isManualLocation}
                onChange={(e) => setIsManualLocation(e.target.checked)}
                className="w-4 h-4 rounded border-[#213233] bg-[#141F20] text-[#00B47A] focus:ring-0 cursor-pointer"
              />
            </div>
          </div>

          {/* IMAGE PHOTO PROOFS CARD */}
          <div className="space-y-4">
            <div className="flex items-center gap-1 border-b border-[#213233] pb-2">
              <Camera size={11} className="text-[#00B47A]" />
              <span className="text-[10px] font-black uppercase tracking-wider text-[#8E9E9B]">
                Installation Proof Photos
              </span>
            </div>

            {photos.map((photo) => {
              const preview = imagePreviews[photo.key];
              const hash = imageHashes[photo.key];
              
              return (
                <div key={photo.key} className="bg-[#0E1617] border border-[#213233] rounded-2xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-white flex items-center gap-1.5">
                      {photo.label}
                      {photo.required ? (
                        <span className="text-[8px] bg-amber-500/10 text-amber-500 px-1.5 py-0.5 rounded border border-amber-500/20 font-extrabold uppercase tracking-wide">Required</span>
                      ) : (
                        <span className="text-[8px] bg-zinc-500/10 text-zinc-500 px-1.5 py-0.5 rounded border border-zinc-500/20 font-extrabold uppercase tracking-wide">Optional</span>
                      )}
                    </span>
                  </div>
                  
                  <p className="text-[9.5px] text-[#8E9E9B] leading-relaxed">
                    {photo.prompt}
                  </p>

                  {preview ? (
                    <div className="space-y-2">
                      <div className="w-full aspect-video rounded-xl overflow-hidden border border-[#213233] relative bg-black">
                        <img src={preview} alt={photo.label} className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => {
                            setImageFiles((prev) => {
                              const next = { ...prev };
                              delete next[photo.key];
                              return next;
                            });
                            setImagePreviews((prev) => {
                              const next = { ...prev };
                              delete next[photo.key];
                              return next;
                            });
                            setImageHashes((prev) => {
                              const next = { ...prev };
                              delete next[photo.key];
                              return next;
                            });
                          }}
                          className="absolute top-2.5 right-2.5 px-2.5 py-1 rounded-lg bg-black/80 hover:bg-black text-[9px] font-extrabold uppercase border border-[#213233] text-[#8E9E9B]"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="text-[8.5px] bg-[#141F20] border border-[#213233] p-2 rounded-lg space-y-0.5">
                        <div className="text-[#5F6F6C]">IMAGE SHA-256 HASH</div>
                        <div className="font-mono text-zinc-300 truncate select-all">{hash || "computing..."}</div>
                      </div>
                    </div>
                  ) : (
                    <label className="w-full aspect-video border border-dashed border-[#213233] hover:border-[#00B47A]/30 bg-[#141F20]/30 rounded-xl flex flex-col items-center justify-center cursor-pointer transition-colors group">
                      <Camera size={24} className="text-[#5F6F6C] group-hover:text-[#8E9E9B] mb-1.5" />
                      <span className="text-[10px] font-extrabold text-[#8E9E9B] group-hover:text-white">
                        Capture {photo.label}
                      </span>
                      <span className="text-[8px] text-[#5F6F6C] mt-0.5">
                        Launches native camera feed
                      </span>
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        onChange={(e) => handleImageChange(photo.key, e)}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>
              );
            })}
          </div>

          {/* CRYPTOGRAPHIC LEDGER HASH CARD */}
          <div className="bg-[#0E1617] border border-[#213233] rounded-2xl p-4 space-y-2">
            <span className="text-[9px] font-black uppercase tracking-wider text-[#8E9E9B] block">
              MRV Deterministic Hash
            </span>
            <p className="text-[8.5px] text-[#5F6F6C] leading-relaxed">
              Calculates payload hashes locally before submitting, ensuring data integrity.
            </p>
            <div className="bg-[#090F10] border border-[#213233] rounded px-2.5 py-1.5 text-[8.5px] font-mono text-[#8E9E9B] truncate select-all">
              {payloadHash || "loading..."}
            </div>
          </div>

          {/* ACTION SUBMIT CONTAINER */}
          <div className="space-y-2">
            {submitStatus === "error" && (
              <div className="p-3 bg-red-950/20 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-start gap-2">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{statusMsg}</span>
              </div>
            )}
            {submitStatus === "success" && (
              <div className="p-3 bg-[#00B47A]/15 border border-[#00B47A]/25 rounded-xl text-xs text-[#00B47A] flex items-start gap-2 animate-fade-in-up">
                <CheckCircle size={15} className="shrink-0 mt-0.5" />
                <span>{statusMsg}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitStatus === "submitting"}
              className="w-full bg-[#00B47A] text-black font-extrabold text-[12px] py-4 uppercase tracking-widest rounded-xl hover:opacity-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-[#00B47A]/10"
            >
              {submitStatus === "submitting" ? (
                <>
                  <RefreshCw size={13} className="animate-spin text-black" />
                  Recording Telemetry...
                </>
              ) : (
                <>
                  <ShieldCheck size={14} className="text-black" />
                  Submit Installation
                </>
              )}
            </button>
          </div>

        </form>

        {/* LOGS WINDOW */}
        <div className="bg-[#0E1617] border border-[#213233] rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-[#213233] pb-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-[#8E9E9B]">
              Sync logs
            </span>
            <button 
              type="button" 
              onClick={() => setSyncLogs([])}
              className="text-[9px] text-[#5F6F6C] hover:text-[#8E9E9B]"
            >
              Clear
            </button>
          </div>
          <div className="bg-[#090F10] border border-[#213233] rounded-xl p-3 h-28 overflow-y-auto font-mono text-[9px] text-[#00B47A] space-y-1.5">
            {syncLogs.length === 0 ? (
              <p className="text-[#5F6F6C] italic text-center pt-8">No terminal logs recorded.</p>
            ) : (
              syncLogs.map((log, i) => (
                <div key={i} className="flex gap-1.5">
                  <span className="text-[#5F6F6C]">➜</span>
                  <span className="break-all">{log}</span>
                </div>
              ))
            )}
          </div>
        </div>

      </main>

    </div>
  );
}
