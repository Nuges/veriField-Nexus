// =============================================================================
// VeriField Nexus CIOS — Governance Context Engine
// =============================================================================
// The single source of truth for governance metadata across the platform.
// Connects to the Backend Governance Metadata Resolver to dynamically load
// rules, frameworks, authorities, and methodologies.
// =============================================================================

"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useWorkspace } from "./WorkspaceContext";
import { API_V1 } from "@/lib/api";
import { safeStorage } from "@/lib/storage";

export interface GovernanceContextState {
  jurisdiction_id: string;
  hierarchy: string[];
  metadata: Record<string, any>;
  active_frameworks: any[];
  approved_methodologies: any[];
  registries: any[];
  authorities: any[];
  climate_programmes: any[];
  vvbs: any[];
  spatial_boundary: Record<string, any>;
}

interface GovernanceContextValue {
  governance: GovernanceContextState | null;
  activeJurisdictionId: string | null;
  setActiveJurisdictionId: (id: string | null) => void;
  isLoading: boolean;
  error: string | null;
  refreshGovernance: () => Promise<void>;
}

const GovernanceContext = createContext<GovernanceContextValue | undefined>(undefined);

export const GovernanceProvider = ({ children }: { children: ReactNode }) => {
  const { user, isLoading: workspaceLoading } = useWorkspace();
  const [activeJurisdictionId, setActiveJurisdictionId] = useState<string | null>(null);
  const [governance, setGovernance] = useState<GovernanceContextState | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGovernance = async () => {
    if (workspaceLoading) return;
    
    // If no specific jurisdiction is selected, we might try to infer one from the user's org
    // For now, if activeJurisdictionId is null, we can't load a specific context.
    if (!activeJurisdictionId) {
      setGovernance(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const token = safeStorage.getItem("vf_token") || "";
      const res = await fetch(`${API_V1}/jurisdictions/${activeJurisdictionId}/context`, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        setGovernance(data);
        setError(null);
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to load governance context");
        setGovernance(null);
      }
    } catch (err: any) {
      console.error("Failed to fetch Governance Context:", err);
      setError("Network error fetching governance context.");
      setGovernance(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGovernance();
  }, [activeJurisdictionId, workspaceLoading]);

  return (
    <GovernanceContext.Provider 
      value={{ 
        governance, 
        activeJurisdictionId,
        setActiveJurisdictionId,
        isLoading, 
        error, 
        refreshGovernance: fetchGovernance 
      }}
    >
      {children}
    </GovernanceContext.Provider>
  );
};

export const useGovernance = (): GovernanceContextValue => {
  const context = useContext(GovernanceContext);
  if (context === undefined) {
    throw new Error("useGovernance must be used within a GovernanceProvider");
  }
  return context;
};
