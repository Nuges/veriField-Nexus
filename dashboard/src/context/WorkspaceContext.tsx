// =============================================================================
// VeriField Nexus — Workspace Resolver & Context Engine
// =============================================================================
// Centralized state engine for loading the user profile, determining the sector
// context, enforcing role-based access control, and providing filtered datasets
// to ensure strict sector isolation.
// =============================================================================

"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { fetchMe } from "@/lib/api";
import type { User, Property, Activity } from "@/lib/types";

export interface WorkspaceContextType {
  user: User | null;
  activeSector: string; // "cookstove" | "energy"
  isSandboxed: boolean;
  allowedSectors: string[];
  isLoading: boolean;
  error: string | null;
  changeSector: (sector: string) => void;
  filterProperties: (properties: Property[]) => Property[];
  filterActivities: (activities: Activity[]) => Activity[];
  filterCarbonLedger: (ledger: any[]) => any[];
  filterAudits: (audits: any[]) => any[];
  refreshUser: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

const normalize = (value?: string) =>
  (value || "").toLowerCase().trim();

// Normalizes sector strings from DB user sector
export function normalizeSector(sec: string): string {
  const s = (sec || "cookstove").toLowerCase().trim();
  if (s.includes("cookstove") || s.includes("clean cooking")) return "cookstove";
  if (s.includes("energy") || s.includes("hybrid")) return "energy";
  if (s.includes("transport") || s.includes("fleet") || s.includes("mobility")) return "energy"; // Fallback to energy
  if (s.includes("afolu") || s.includes("forestry") || s.includes("farming") || s.includes("agri") || s.includes("agriculture")) return "cookstove"; // Fallback to cookstove
  return "cookstove";
}

// Smart classification mapping layer
export function mapToWorkspace(record: any): "cookstove" | "energy" | null {
  if (!record) return null;

  const normalizeVal = (value?: any) => {
    if (typeof value !== "string") return "";
    return value.toLowerCase().trim();
  };

  const methodology = normalizeVal(record.methodology || record.methodology_used);
  const type = normalizeVal(record.property_type || record.activity_type || record.type);
  const category = normalizeVal(record.category);
  const desc = normalizeVal(record.description || record.name || record.address || "");
  
  // Extract tags if present
  let tagsStr = "";
  if (record.tags) {
    if (Array.isArray(record.tags)) {
      tagsStr = record.tags.map((t: any) => normalizeVal(String(t))).join(" ");
    } else {
      tagsStr = normalizeVal(record.tags);
    }
  }

  // ─── STEP 1: Explicit property_type / activity_type (highest priority) ───
  // These are the authoritative DB fields — check them first before any heuristics.
  if (
    type === "clean_cooking" ||
    type === "cookstove" ||
    type === "clean cooking"
  ) {
    return "cookstove";
  }

  if (
    type === "hybrid_energy" ||
    type === "energy" ||
    type === "solar" ||
    type === "energy_displacement"
  ) {
    return "energy";
  }

  // ─── STEP 2: Methodology-based (reliable secondary signal) ───
  const allText = `${type} ${category} ${desc} ${tagsStr} ${methodology}`.toLowerCase();

  if (
    methodology.includes("gs_mecd") ||
    methodology.includes("mecd") ||
    methodology.includes("tpddtec") ||
    methodology.includes("vmr0050") ||
    methodology.includes("vm0006") ||
    allText.includes("gs_mecd") ||
    allText.includes("mecd") ||
    allText.includes("tpddtec") ||
    allText.includes("vmr0050") ||
    allText.includes("vm0006")
  ) {
    return "cookstove";
  }

  if (
    methodology.includes("ams-i.f") ||
    methodology.includes("renewable") ||
    methodology.includes("energy_displacement") ||
    allText.includes("ams-i.f") ||
    allText.includes("renewable") ||
    allText.includes("energy_displacement")
  ) {
    return "energy";
  }

  // Reject transport / afolu methodologies
  if (
    methodology.includes("vm0038") ||
    methodology.includes("ams-iii.c") ||
    allText.includes("vm0038") ||
    allText.includes("ams-iii.c")
  ) {
    return null;
  }

  if (
    methodology.includes("vm0007") ||
    methodology.includes("ar-acm0003") ||
    allText.includes("vm0007") ||
    allText.includes("ar-acm0003")
  ) {
    return null;
  }

  // Reject transport sector keywords
  if (
    allText.includes("transport") ||
    allText.includes("mobility") ||
    allText.includes("vehicle") ||
    allText.includes("fleet") ||
    allText.includes("electric vehicle") ||
    category.includes("transport") ||
    category.includes("mobility")
  ) {
    return null;
  }

  // Reject afolu sector keywords
  if (
    allText.includes("afolu") ||
    allText.includes("forestry") ||
    allText.includes("farming") ||
    allText.includes("agricultural") ||
    allText.includes("tree") ||
    allText.includes("canopy") ||
    allText.includes("ndvi") ||
    category.includes("afolu") ||
    category.includes("forestry")
  ) {
    return null;
  }

  // ─── STEP 3: Keyword-based heuristics (only reached if type field was unrecognized) ───
  const hasCookstoveKeywords = 
    allText.includes("cookstove") || 
    allText.includes("biomass") || 
    allText.includes("clean cooking") ||
    allText.includes("cooking") ||
    allText.includes("stove");

  if (hasCookstoveKeywords) {
    return "cookstove";
  }

  const hasEnergyKeywords = 
    allText.includes("solar") || 
    allText.includes("inverter") || 
    allText.includes("battery") || 
    allText.includes("mini-grid") || 
    allText.includes("hybrid") ||
    allText.includes("energy") ||
    allText.includes("diesel") ||
    allText.includes("infrastructure") ||
    allText.includes("electricity") ||
    allText.includes("power");

  if (hasEnergyKeywords) {
    return "energy";
  }

  // Default fallback: return null to avoid incorrect auto-mapping
  return null;
}

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeSector, setActiveSector] = useState<string>("cookstove");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUser = useCallback(async (retryCount = 0) => {
    // Only query backend if token exists to avoid useless 401s and console error spam
    const token = typeof window !== "undefined" ? localStorage.getItem("vf_token") : null;
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const u = await fetchMe();
      setUser(u);
      if (typeof window !== "undefined") {
        localStorage.setItem("vf_user", JSON.stringify(u));
      }
      const normalized = normalizeSector(u.sector);
      setActiveSector(normalized);
    } catch (err: any) {
      const isAuthError = err?.message === "Not authenticated" || err?.message?.includes("Not authenticated") || err?.message?.includes("401");
      if (isAuthError) {
        console.warn(`Workspace Resolver: User is not authenticated.`);
      } else {
        console.error(`Workspace Resolver failed to load user profile (attempt ${retryCount + 1}):`, err);
      }
      
      // Auto-retry once on timeout (common with ngrok/tunnel latency)
      if (retryCount < 1 && err?.message?.includes("timed out")) {
        console.log("Workspace Resolver: retrying fetchMe after timeout...");
        setIsLoading(true);
        setTimeout(() => loadUser(retryCount + 1), 2000);
        return;
      }
      
      // Offline fallback: try loading the last successfully loaded user profile from cache
      if (typeof window !== "undefined") {
        const cachedUserStr = localStorage.getItem("vf_user");
        if (cachedUserStr) {
          try {
            const cachedUser = JSON.parse(cachedUserStr);
            setUser(cachedUser);
            const normalized = normalizeSector(cachedUser.sector);
            setActiveSector(normalized);
            console.log("Workspace Resolver restored cached user profile offline.");
            setIsLoading(false);
            return;
          } catch (parseErr) {
            console.error("Failed to parse cached user profile:", parseErr);
          }
        }
      }
      
      setError(err?.message || "Failed to load workspace context.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();

    // Listen for global profile updates
    if (typeof window !== "undefined") {
      const handleUpdate = () => {
        loadUser();
      };
      window.addEventListener("vf_profile_updated", handleUpdate);
      return () => window.removeEventListener("vf_profile_updated", handleUpdate);
    }
  }, [loadUser]);

  const changeSector = (sector: string) => {
    if (!user) return;
    
    // RBAC: Standard user cannot change sector manually
    const isStandard = user.role !== "admin" && user.role !== "auditor" && user.role !== "ORG_ADMIN" && user.role !== "SUPER_ADMIN";
    if (isStandard) {
      console.warn("Access Denied: Standard user cannot switch workspaces manually.");
      return;
    }

    const normalized = normalizeSector(sector);
    setActiveSector(normalized);
  };

  // Sector Data Isolation helpers
  const filterProperties = useCallback((properties: Property[]): Property[] => {
    if (!properties || !Array.isArray(properties)) return [];
    
    console.log("TOTAL RECORDS:", properties.length);
    
    const activeWorkspace = activeSector;
    const filtered = properties.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeWorkspace;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeWorkspace ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    
    console.log("AFTER FILTER:", filtered.length);
    return filtered;
  }, [activeSector]);

  const filterActivities = useCallback((activities: Activity[]): Activity[] => {
    if (!activities || !Array.isArray(activities)) return [];
    
    console.log("TOTAL RECORDS:", activities.length);
    
    const activeWorkspace = activeSector;
    const filtered = activities.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeWorkspace;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeWorkspace ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    
    console.log("AFTER FILTER:", filtered.length);
    return filtered;
  }, [activeSector]);

  const filterCarbonLedger = useCallback((ledger: any[]): any[] => {
    if (!ledger || !Array.isArray(ledger)) return [];
    
    console.log("TOTAL RECORDS:", ledger.length);
    
    const activeWorkspace = activeSector;
    const filtered = ledger.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeWorkspace;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeWorkspace ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    
    console.log("AFTER FILTER:", filtered.length);
    return filtered;
  }, [activeSector]);

  const filterAudits = useCallback((audits: any[]): any[] => {
    if (!audits || !Array.isArray(audits)) return [];
    
    console.log("TOTAL RECORDS:", audits.length);
    
    const activeWorkspace = activeSector;
    const filtered = audits.filter((record) => {
      const mapped = mapToWorkspace(record);
      console.log("RECORD MAPPED:", record.id, mapped);
      
      const keep = mapped === activeWorkspace;
      if (!keep) {
        console.log("DROPPED RECORD:", {
          id: record.id,
          reason: mapped !== activeWorkspace ? "workspace_mismatch" : "null_mapping"
        });
      }
      return keep;
    });
    
    console.log("AFTER FILTER:", filtered.length);
    return filtered;
  }, [activeSector]);

  const isSandboxed = user ? (user.role !== "admin" && user.role !== "auditor" && user.role !== "ORG_ADMIN" && user.role !== "SUPER_ADMIN") : true;
  const allowedSectors = isSandboxed && user ? [normalizeSector(user.sector)] : ["cookstove", "energy"];

  return (
    <WorkspaceContext.Provider
      value={{
        user,
        activeSector,
        isSandboxed,
        allowedSectors,
        isLoading,
        error,
        changeSector,
        filterProperties,
        filterActivities,
        filterCarbonLedger,
        filterAudits,
        refreshUser: loadUser
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
};
