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
  activeSector: string; // Dynamic sector based on methodology config
  isSandboxed: boolean;
  allowedSectors: string[];
  moduleRegistry: Record<string, any>;
  isLoading: boolean;
  error: string | null;
  changeSector: (sector: string) => void;
  filterProperties: (properties: Property[]) => Property[];
  filterActivities: (activities: Activity[]) => Activity[];
  filterCarbonLedger: (ledger: any[]) => any[];
  filterAudits: (audits: any[]) => any[];
  refreshUser: () => Promise<void>;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (collapsed: boolean) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);
import { normalizeSector, mapToWorkspace, getRecordSector } from "@/lib/moduleRegistry";
import { safeStorage } from "@/lib/storage";
import { fetchMethodologies } from "@/lib/api";

export { normalizeSector, mapToWorkspace, getRecordSector };

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeSector, setActiveSector] = useState<string>("generic");
  const [moduleRegistry, setModuleRegistry] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const loadUser = useCallback(async (retryCount = 0) => {
    // Only query backend if token exists to avoid useless 401s and console error spam
    const token = typeof window !== "undefined" ? safeStorage.getItem("vf_token") : null;
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
        safeStorage.setItem("vf_user", JSON.stringify(u));
      }
      // Read workspace query parameter from URL on load
      const userSectorNormalized = normalizeSector(u.sector);
      let initialSector = userSectorNormalized;

      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        const wsKey = `vf_workspace_${u.id}`;
        const ws = params.get("workspace") || safeStorage.getItem(wsKey);
        if (ws) {
          const normWs = normalizeSector(ws);
          const allowed = u.role === "SUPER_ADMIN" || (Array.isArray(u.licensed_sectors) && u.licensed_sectors.map(normalizeSector).includes(normWs));
          if (allowed) {
            initialSector = normWs;
            safeStorage.setItem(wsKey, initialSector);
          }
        }
      }
      setActiveSector(initialSector);
    } catch (err: any) {
      const isAuthError = err?.message === "Not authenticated" || err?.message?.includes("Not authenticated") || err?.message?.includes("401");
      if (isAuthError) {
        console.warn(`Workspace Resolver: User is not authenticated.`);
        setUser(null);
        if (typeof window !== "undefined") {
          safeStorage.removeItem("vf_user");
          safeStorage.removeItem("vf_token");
        }
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
      
      // Offline fallback: try loading the last successfully loaded user profile from cache (only if not an auth error)
      if (!isAuthError && typeof window !== "undefined") {
        const cachedUserStr = safeStorage.getItem("vf_user");
        if (cachedUserStr) {
          try {
            const cachedUser = JSON.parse(cachedUserStr);
            setUser(cachedUser);
            let normalized = normalizeSector(cachedUser.sector);
            const isSuperAdmin = cachedUser.role === "SUPER_ADMIN";
            
            if (isSuperAdmin && typeof window !== "undefined") {
              const params = new URLSearchParams(window.location.search);
              const wsKey = `vf_workspace_${cachedUser.id}`;
              const ws = params.get("workspace") || safeStorage.getItem(wsKey);
              if (ws) {
                normalized = normalizeSector(ws);
                safeStorage.setItem(wsKey, normalized);
              }
            }
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

  // Load Methodologies dynamically
  useEffect(() => {
    async function loadMethodologies() {
      try {
        const data = await fetchMethodologies();
        const registry: Record<string, any> = {};
        
        // Handle both new array format and legacy {modules: []} format during migration
        const methodologiesList = Array.isArray(data) ? data : (data.modules || []);
        
        for (const mod of methodologiesList) {
          registry[mod.code] = {
            ...mod.ui_config,
            form_schema: mod.form_schema,
            id: mod.id,
            name: mod.name,
            description: mod.description
          };
        }
        setModuleRegistry(registry);
      } catch (err) {
        console.error("Failed to load methodologies dynamically:", err);
      }
    }
    loadMethodologies();
  }, []);

  // Listen for changes to workspace URL parameters
  useEffect(() => {
    if (typeof window !== "undefined") {
      const handlePopState = () => {
        if (user && user.role === "field_agent") return;
        const params = new URLSearchParams(window.location.search);
        const ws = params.get("workspace");
        if (ws) {
          setActiveSector(normalizeSector(ws));
        }
      };
      window.addEventListener("popstate", handlePopState);
      return () => window.removeEventListener("popstate", handlePopState);
    }
  }, [user]);

  const changeSector = (sector: string) => {
    if (!user) return;
    
    const normalized = normalizeSector(sector);
    
    // Check if user has access to the target sector via organization licensing
    if (!allowedSectors.includes(normalized)) {
      console.warn("Access Denied: Sector is not licensed or permitted for your organization.");
      return;
    }

    setActiveSector(normalized);

    // Sync workspace parameter with the URL query parameters
    if (typeof window !== "undefined") {
      safeStorage.setItem(`vf_workspace_${user.id}`, normalized);
      const url = new URL(window.location.href);
      url.searchParams.set("workspace", normalized);
      window.history.pushState({}, "", url.toString());
    }
  };

  // Sector Data Isolation helpers
  const filterProperties = useCallback((properties: Property[]): Property[] => {
    if (!properties || !Array.isArray(properties)) return [];
    return properties.filter((record) => record && getRecordSector(record) === activeSector);
  }, [activeSector]);

  const filterActivities = useCallback((activities: Activity[]): Activity[] => {
    if (!activities || !Array.isArray(activities)) return [];
    return activities.filter((record) => record && getRecordSector(record) === activeSector);
  }, [activeSector]);

  const filterCarbonLedger = useCallback((ledger: any[]): any[] => {
    if (!ledger || !Array.isArray(ledger)) return [];
    return ledger.filter((record) => record && getRecordSector(record) === activeSector);
  }, [activeSector]);

  const filterAudits = useCallback((audits: any[]): any[] => {
    if (!audits || !Array.isArray(audits)) return [];
    return audits.filter((record) => {
      if (!record) return false;
      const propSector = record.property ? getRecordSector(record.property) : null;
      const recordSector = getRecordSector(record);
      return propSector === activeSector || recordSector === activeSector;
    });
  }, [activeSector]);

  const isSandboxed = user ? (user.role !== "SUPER_ADMIN") : true;
  const allowedSectors = isSandboxed && user
    ? (Array.isArray(user.licensed_sectors) ? user.licensed_sectors.map(normalizeSector) : [normalizeSector(user.sector)])
    : Object.keys(moduleRegistry);

  return (
    <WorkspaceContext.Provider
      value={{
        user,
        activeSector,
        isSandboxed,
        allowedSectors,
        moduleRegistry,
        isLoading,
        error,
        changeSector,
        filterProperties,
        filterActivities,
        filterCarbonLedger,
        filterAudits,
        refreshUser: loadUser,
        isSidebarCollapsed,
        setIsSidebarCollapsed
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
