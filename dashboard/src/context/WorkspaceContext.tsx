// =============================================================================

// VeriField Nexus — Workspace Resolver & Context Engine (CIOS-Compliant)

// =============================================================================

// Deterministic, metadata-driven workspace resolution.

// Resolution chain: User → Organisation → Licensed Methodologies →

//   Methodology Family → Workspace Metadata → UI Schema → Dashboard Config

// Synchronously hydrated state prevents workspace flicker or generic fallback.

// =============================================================================



"use client";



import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";

import { fetchMe } from "@/lib/api";

import type { User, Property, Activity } from "@/lib/types";

import {

  buildWorkspaceRegistry,

  buildMethodologyToFamilyMap,

  resolveUserWorkspace,

  validateCachedWorkspace,

  classifyRecord,

  normalizeSector,

  type WorkspaceConfig,

  type APIMethodology,

  type APIFamily

} from "@/lib/moduleRegistry";

import { safeStorage } from "@/lib/storage";

import { fetchMethodologies, fetchMethodologyFamilies } from "@/lib/api";



// ─── Public API Types ────────────────────────────────────────────────────────



export interface WorkspaceContextType {

  user: User | null;

  activeSector: string;

  activeMethodology: string;

  activeProject: string | null;

  isSandboxed: boolean;

  allowedSectors: string[];

  moduleRegistry: Record<string, any>;

  isLoading: boolean;

  error: string | null;

  changeSector: (sector: string) => void;

  changeMethodology: (methodology: string) => void;

  changeProject: (projectId: string | null) => void;

  filterProperties: (properties: Property[]) => Property[];

  filterActivities: (activities: Activity[]) => Activity[];

  filterCarbonLedger: (ledger: any[]) => any[];

  filterAudits: (audits: any[]) => any[];

  refreshUser: () => Promise<void>;

  isSidebarCollapsed: boolean;

  setIsSidebarCollapsed: (collapsed: boolean) => void;

  // New diagnostic fields

  methToFamily: Record<string, string>;

  workspaceError: string | null;

}



const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);



// Re-export for backward compatibility

export { normalizeSector };

export { classifyRecord as getRecordSector_v2 };

// Legacy re-exports (kept for components that still import them)

export { getRecordSector, mapToWorkspace } from "@/lib/moduleRegistry";



// ─── Storage Keys ────────────────────────────────────────────────────────────



const STORAGE_KEY_USER = "vf_user";

const STORAGE_KEY_TOKEN = "vf_token";

const workspaceStorageKey = (userId: string) => `vf_workspace_${userId}`;



// ─── Provider ────────────────────────────────────────────────────────────────



export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {

  // Synchronously hydrate initial state from storage to prevent generic workspace flash

  const [user, setUser] = useState<User | null>(() => {

    if (typeof window === "undefined") return null;

    try {

      const cached = safeStorage.getItem(STORAGE_KEY_USER);

      return cached ? JSON.parse(cached) : null;

    } catch {

      return null;

    }

  });



  const [activeSector, setActiveSector] = useState<string>(() => {

    if (typeof window === "undefined") return "cookstoves";

    try {

      const params = new URLSearchParams(window.location.search);

      const urlWs = params.get("workspace");

      if (urlWs) return urlWs;



      const cachedUserStr = safeStorage.getItem(STORAGE_KEY_USER);

      if (cachedUserStr) {

        const u = JSON.parse(cachedUserStr);

        const cachedWs = safeStorage.getItem(workspaceStorageKey(u.id));

        if (cachedWs && cachedWs !== "generic") return cachedWs;



        const licensed = Array.isArray(u.licensed_sectors) ? u.licensed_sectors : [];

        if (licensed.length > 0) return licensed[0].toLowerCase().trim();

      }

    } catch {}

    return "cookstoves";

  });



  const [activeMethodology, setActiveMethodology] = useState<string>(() => {

    if (typeof window === "undefined") return "AMS-II.G";

    try {

      const cachedUserStr = safeStorage.getItem(STORAGE_KEY_USER);

      if (cachedUserStr) {

        const u = JSON.parse(cachedUserStr);

        const licensedMeths = Array.isArray(u.licensed_methodologies) ? u.licensed_methodologies : [];

        if (licensedMeths.length > 0) return licensedMeths[0];

      }

    } catch {}

    return "AMS-II.G";

  });



  const [activeProject, setActiveProject] = useState<string | null>(null);

  const [moduleRegistry, setModuleRegistry] = useState<Record<string, any>>({});

  const [isLoading, setIsLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [workspaceError, setWorkspaceError] = useState<string | null>(null);



  // Metadata maps (built from API data, not hardcoded)

  const methToFamilyRef = useRef<Record<string, string>>({});

  const [methToFamily, setMethToFamily] = useState<Record<string, string>>({});

  const registryReadyRef = useRef(false);

  const pendingUserRef = useRef<User | null>(null);



  // ─── Cache Management ───────────────────────────────────────────

  const clearStaleWorkspaceCache = useCallback((userId?: string) => {

    if (typeof window === "undefined") return;

  }, []);



  // ─── Resolve workspace AFTER registry is ready ─────────────────────────

  const resolveWorkspaceForUser = useCallback((u: User, registry: Record<string, any>, methMap: Record<string, string>) => {

    const isSuperAdmin = u.role === "SUPER_ADMIN";



    if (isSuperAdmin) {

      const allWorkspaces = Object.keys(registry).filter(k => {

        const config = registry[k];

        return config && config.kpis && config.kpis.length > 0;

      });



      let activeWorkspace = allWorkspaces[0] || "cookstoves";

      const allowedWorkspaces = allWorkspaces.length > 0 ? allWorkspaces : ["cookstoves"];



      if (typeof window !== "undefined") {

        const wsKey = workspaceStorageKey(u.id);

        const params = new URLSearchParams(window.location.search);

        const cached = params.get("workspace") || safeStorage.getItem(wsKey);

        const validated = validateCachedWorkspace(cached, allowedWorkspaces, methMap, true);

        if (validated && registry[validated]) {

          activeWorkspace = validated;

        }

        safeStorage.setItem(wsKey, activeWorkspace);

      }



      setActiveSector(activeWorkspace);

      return;

    }



    // Non-super-admin: deterministic resolution from metadata

    const licensedSectors = Array.isArray(u.licensed_sectors) ? u.licensed_sectors : [];

    const licensedMethodologies = Array.isArray(u.licensed_methodologies) ? u.licensed_methodologies : [];



    const { activeWorkspace, allowedWorkspaces } = resolveUserWorkspace(

      licensedSectors,

      licensedMethodologies,

      methMap,

      registry

    );



    let finalWorkspace = activeWorkspace;

    if (finalWorkspace === "generic" && allowedWorkspaces.length > 0 && allowedWorkspaces[0] !== "generic") {

      finalWorkspace = allowedWorkspaces[0];

    }

    if (finalWorkspace === "generic") {

      finalWorkspace = "cookstoves";

    }



    if (typeof window !== "undefined") {

      const wsKey = workspaceStorageKey(u.id);

      const params = new URLSearchParams(window.location.search);

      const cached = params.get("workspace") || safeStorage.getItem(wsKey);

      const validated = validateCachedWorkspace(cached, allowedWorkspaces, methMap, false);

      if (validated && validated !== "generic") {

        finalWorkspace = validated;

      }

      safeStorage.setItem(wsKey, finalWorkspace);

    }



    setWorkspaceError(null);

    setActiveSector(finalWorkspace);



    if (registry[finalWorkspace]) {

      const methodologies = registry[finalWorkspace].methodologyCodes || [];

      if (methodologies.length > 0) {

        setActiveMethodology(methodologies[0]);

      }

    }

  }, []);



  // ─── Load methodologies & families ────────────────────────────────────

  useEffect(() => {

    async function loadMethodologies() {

      try {

        const [data, families] = await Promise.all([

          fetchMethodologies(),

          fetchMethodologyFamilies().catch(() => [])

        ]);



        const methodologiesList: APIMethodology[] = Array.isArray(data) ? data : (data.modules || []);

        const familiesList: APIFamily[] = Array.isArray(families) ? families : [];



        const registry = buildWorkspaceRegistry(methodologiesList, familiesList);

        const methMap = buildMethodologyToFamilyMap(methodologiesList, familiesList);



        methToFamilyRef.current = methMap;

        setMethToFamily(methMap);

        setModuleRegistry(registry);

        registryReadyRef.current = true;



        if (pendingUserRef.current) {

          resolveWorkspaceForUser(pendingUserRef.current, registry, methMap);

          pendingUserRef.current = null;

        }

      } catch (err) {

        console.error("Failed to load methodologies dynamically:", err);

      }

    }

    loadMethodologies();

  }, [resolveWorkspaceForUser]);



  // ─── Load user profile ─────────────────────────────────────────────────

  const loadUser = useCallback(async (retryCount = 0) => {

    const token = typeof window !== "undefined" ? safeStorage.getItem(STORAGE_KEY_TOKEN) : null;

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

        safeStorage.setItem(STORAGE_KEY_USER, JSON.stringify(u));

      }



      clearStaleWorkspaceCache(u.id);



      if (registryReadyRef.current) {

        resolveWorkspaceForUser(u, moduleRegistry, methToFamilyRef.current);

      } else {

        pendingUserRef.current = u;

      }

    } catch (err: any) {

      const isAuthError = err?.message === "Not authenticated" || err?.message?.includes("Not authenticated") || err?.message?.includes("401");

      if (isAuthError) {

        console.warn(`Workspace Resolver: User is not authenticated.`);

        setUser(null);

        if (typeof window !== "undefined") {

          safeStorage.removeItem(STORAGE_KEY_USER);

          safeStorage.removeItem(STORAGE_KEY_TOKEN);

        }

      } else {

        console.error(`Workspace Resolver failed to load user profile (attempt ${retryCount + 1}):`, err);

      }



      if (retryCount < 1 && err?.message?.includes("timed out")) {

        setIsLoading(true);

        setTimeout(() => loadUser(retryCount + 1), 2000);

        return;

      }



      if (!isAuthError && typeof window !== "undefined") {

        const cachedUserStr = safeStorage.getItem(STORAGE_KEY_USER);

        if (cachedUserStr) {

          try {

            const cachedUser = JSON.parse(cachedUserStr);

            setUser(cachedUser);



            if (registryReadyRef.current) {

              resolveWorkspaceForUser(cachedUser, moduleRegistry, methToFamilyRef.current);

            } else {

              pendingUserRef.current = cachedUser;

            }



            setIsLoading(false);

            return;

          } catch (parseErr) {

            console.error("Failed to parse cached user profile:", parseErr);

          }

        }

      }



      const msg = typeof err?.message === "string" ? err.message : null;

      setError(msg || "Failed to load workspace context.");

    } finally {

      setIsLoading(false);

    }

  }, [clearStaleWorkspaceCache, resolveWorkspaceForUser, moduleRegistry]);



  useEffect(() => {

    loadUser();



    if (typeof window !== "undefined") {

      const handleUpdate = () => { loadUser(); };

      window.addEventListener("vf_profile_updated", handleUpdate);

      return () => window.removeEventListener("vf_profile_updated", handleUpdate);

    }

  }, [loadUser]);



  useEffect(() => {

    if (typeof window === "undefined") return;

    const handlePopState = () => {

      const params = new URLSearchParams(window.location.search);

      const ws = params.get("workspace");

      if (ws && ws !== activeSector) {

        setActiveSector(ws);

      }

    };

    window.addEventListener("popstate", handlePopState);

    return () => window.removeEventListener("popstate", handlePopState);

  }, [activeSector]);



  const changeSector = useCallback((sector: string) => {

    const normalized = normalizeSector(sector);

    setActiveSector(normalized);



    if (moduleRegistry[normalized]) {

      const methodologies = moduleRegistry[normalized].methodologyCodes || [];

      if (methodologies.length > 0) {

        setActiveMethodology(methodologies[0]);

      }

    }



    if (typeof window !== "undefined" && user) {

      safeStorage.setItem(workspaceStorageKey(user.id), normalized);



      const url = new URL(window.location.href);

      url.searchParams.set("workspace", normalized);

      window.history.pushState({}, "", url.toString());

    }

  }, [user, moduleRegistry]);



  const changeMethodology = useCallback((methodology: string) => {

    setActiveMethodology(methodology);

    const familyCode = methToFamily[methodology.toLowerCase().trim()];

    if (familyCode && familyCode !== activeSector) {

      changeSector(familyCode);

    }

  }, [methToFamily, activeSector, changeSector]);



  const changeProject = useCallback((projectId: string | null) => {

    setActiveProject(projectId);

  }, []);



  const refreshUser = useCallback(async () => {

    await loadUser();

  }, [loadUser]);



  const allowedSectors = React.useMemo(() => {

    if (!user) return [activeSector];

    if (user.role === "SUPER_ADMIN") {

      const all = Object.keys(moduleRegistry).filter(k => moduleRegistry[k]?.kpis?.length > 0);

      return all.length > 0 ? all : [activeSector];

    }

    const licensedSectors = Array.isArray(user.licensed_sectors) ? user.licensed_sectors : [];

    const licensedMethodologies = Array.isArray(user.licensed_methodologies) ? user.licensed_methodologies : [];



    const { allowedWorkspaces } = resolveUserWorkspace(

      licensedSectors,

      licensedMethodologies,

      methToFamily,

      moduleRegistry

    );



    const validAllowed = allowedWorkspaces.filter(w => w !== "generic");

    return validAllowed.length > 0 ? validAllowed : [activeSector];

  }, [user, moduleRegistry, methToFamily, activeSector]);



  const isSandboxed = React.useMemo(() => {

    if (!user) return false;

    return user.role !== "SUPER_ADMIN";

  }, [user]);



  const filterProperties = useCallback((properties: Property[]): Property[] => {

    if (!Array.isArray(properties)) return [];

    return properties.filter(p => classifyRecord(p, methToFamily, activeSector, isSandboxed));

  }, [methToFamily, activeSector, isSandboxed]);



  const filterActivities = useCallback((activities: Activity[]): Activity[] => {

    if (!Array.isArray(activities)) return [];

    return activities.filter(a => classifyRecord(a, methToFamily, activeSector, isSandboxed));

  }, [methToFamily, activeSector, isSandboxed]);



  const filterCarbonLedger = useCallback((ledger: any[]): any[] => {

    if (!Array.isArray(ledger)) return [];

    return ledger.filter(item => classifyRecord(item, methToFamily, activeSector, isSandboxed));

  }, [methToFamily, activeSector, isSandboxed]);



  const filterAudits = useCallback((audits: any[]): any[] => {

    if (!Array.isArray(audits)) return [];

    return audits.filter(item => classifyRecord(item, methToFamily, activeSector, isSandboxed));

  }, [methToFamily, activeSector, isSandboxed]);



  return (

    <WorkspaceContext.Provider

      value={{

        user,

        activeSector,

        activeMethodology,

        activeProject,

        isSandboxed,

        allowedSectors,

        moduleRegistry,

        isLoading,

        error,

        changeSector,

        changeMethodology,

        changeProject,

        filterProperties,

        filterActivities,

        filterCarbonLedger,

        filterAudits,

        refreshUser,

        isSidebarCollapsed,

        setIsSidebarCollapsed,

        methToFamily,

        workspaceError,

      }}

    >

      {children}

    </WorkspaceContext.Provider>

  );

};



export const useWorkspace = (): WorkspaceContextType => {

  const context = useContext(WorkspaceContext);

  if (!context) {

    throw new Error("useWorkspace must be used within a WorkspaceProvider");

  }

  return context;

};
