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
  activeSector: string; // "cookstove" | "energy" | "transport" | "afolu"
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

// Normalizes sector strings from DB user sector
export function normalizeSector(sec: string): string {
  const s = (sec || "cookstove").toLowerCase();
  if (s.includes("cookstove") || s.includes("clean cooking")) return "cookstove";
  if (s.includes("energy") || s.includes("hybrid")) return "energy";
  if (s.includes("transport") || s.includes("fleet") || s.includes("mobility")) return "transport";
  if (s.includes("afolu") || s.includes("forestry") || s.includes("farming")) return "afolu";
  return "cookstove";
}

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeSector, setActiveSector] = useState<string>("cookstove");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const u = await fetchMe();
      setUser(u);
      const normalized = normalizeSector(u.sector);
      setActiveSector(normalized);
    } catch (err: any) {
      console.error("Workspace Resolver failed to load user profile:", err);
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
    const isStandard = user.role !== "admin" && user.role !== "auditor";
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
    return properties.filter((p) => {
      const type = (p.property_type || "").toLowerCase();
      if (activeSector === "cookstove") {
        return type.includes("cooking") || type.includes("cookstove") || type.includes("residential");
      }
      if (activeSector === "energy") {
        return type.includes("energy") || type.includes("commercial") || type.includes("industrial");
      }
      if (activeSector === "transport") {
        return type.includes("transport") || type.includes("mobility") || type.includes("vehicle");
      }
      if (activeSector === "afolu") {
        return type.includes("afolu") || type.includes("forestry") || type.includes("farming") || type.includes("agricultural");
      }
      return false;
    });
  }, [activeSector]);

  const filterActivities = useCallback((activities: Activity[]): Activity[] => {
    if (!activities || !Array.isArray(activities)) return [];
    return activities.filter((act) => {
      const type = (act.activity_type || "").toLowerCase();
      if (activeSector === "cookstove") {
        return type.includes("cooking") || type.includes("cookstove") || type.includes("biomass");
      }
      if (activeSector === "energy") {
        return type.includes("energy") || type.includes("hybrid_energy");
      }
      if (activeSector === "transport") {
        return type.includes("transport") || type.includes("mobility") || type.includes("vehicle");
      }
      if (activeSector === "afolu") {
        return type.includes("afolu") || type.includes("forestry") || type.includes("farming");
      }
      return false;
    });
  }, [activeSector]);

  const filterCarbonLedger = useCallback((ledger: any[]): any[] => {
    if (!ledger || !Array.isArray(ledger)) return [];
    return ledger.filter((item) => {
      const meth = (item.methodology || item.methodology_used || "").toLowerCase();
      const type = (item.activity_type || "").toLowerCase();
      
      if (activeSector === "cookstove") {
        return meth.includes("tpddtec") || meth.includes("vm0006") || meth.includes("vmr0050") || type.includes("cookstove") || type.includes("cooking");
      }
      if (activeSector === "energy") {
        return meth.includes("ams-i.f") || meth.includes("renewable") || meth.includes("energy") || type.includes("energy");
      }
      if (activeSector === "transport") {
        return meth.includes("vm0038") || meth.includes("ams-iii.c") || type.includes("transport") || type.includes("mobility");
      }
      if (activeSector === "afolu") {
        return meth.includes("vm0007") || meth.includes("ar-acm0003") || type.includes("afolu") || type.includes("forestry") || type.includes("farming");
      }
      return false;
    });
  }, [activeSector]);

  const filterAudits = useCallback((audits: any[]): any[] => {
    if (!audits || !Array.isArray(audits)) return [];
    return audits.filter((item) => {
      const type = (item.property_type || item.activity_type || "").toLowerCase();
      if (activeSector === "cookstove") {
        return type.includes("cooking") || type.includes("cookstove") || type.includes("residential");
      }
      if (activeSector === "energy") {
        return type.includes("energy") || type.includes("commercial") || type.includes("industrial");
      }
      if (activeSector === "transport") {
        return type.includes("transport") || type.includes("mobility") || type.includes("vehicle");
      }
      if (activeSector === "afolu") {
        return type.includes("afolu") || type.includes("forestry") || type.includes("farming") || type.includes("agricultural");
      }
      return false;
    });
  }, [activeSector]);

  const isSandboxed = user ? (user.role !== "admin" && user.role !== "auditor") : true;
  const allowedSectors = isSandboxed && user ? [normalizeSector(user.sector)] : ["cookstove", "energy", "transport", "afolu"];

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
