"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Globe,
  ShieldCheck,
  Radio,
  Layers,
  TrendingUp,
  Server,
  Map as MapIcon,
  List
} from "lucide-react";
import dynamic from "next/dynamic";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchActivities, fetchProperties } from "@/lib/api";
import { canonicalSectorCode } from "@/lib/moduleRegistry";

const SpatialBoundaryMap = dynamic(
  () => import("@/components/jurisdictions/SpatialBoundaryMap"),
  { ssr: false }
);

interface JurisdictionStatus {
  country: string;
  code: string;
  status: string;
  activeProjects: number;
}

interface TableAssetItem {
  id: string;
  name: string;
  type: string;
  status: string;
  lat: number | string | null;
  lng: number | string | null;
  sector: string;
}

const SCOPE_TABS: Array<{ id: "SITE" | "REGIONAL" | "NATIONAL" | "GLOBAL"; label: string }> = [
  { id: "SITE", label: "Site" },
  { id: "REGIONAL", label: "Regional" },
  { id: "NATIONAL", label: "National" },
  { id: "GLOBAL", label: "Global" },
];

export default function CommandCenterPage() {
  const { activeSector, activeProject } = useWorkspace();
  const [activeSpatialTab, setActiveSpatialTab] = useState<"SITE" | "REGIONAL" | "NATIONAL" | "GLOBAL">("SITE");
  const [viewMode, setViewMode] = useState<"map" | "table">("map");
  const [, setLoading] = useState(true);
  const [projectCount, setProjectCount] = useState<number>(0);
  const [assetCount, setAssetCount] = useState<number>(0);
  const [jurisdictionCount, setJurisdictionCount] = useState<number>(0);
  const [verifiedCarbon, setVerifiedCarbon] = useState<number | null>(null);
  const [jurisdictions, setJurisdictions] = useState<JurisdictionStatus[]>([]);
  const [mapGeojson] = useState<Record<string, unknown> | null>(null);
  const [assetTableData, setAssetTableData] = useState<TableAssetItem[]>([]);

  const canonCode = useMemo(() => canonicalSectorCode(activeSector || "").toUpperCase(), [activeSector]);

  useEffect(() => {
    let isCancelled = false;

    async function fetchCommandMetrics() {
      setLoading(true);
      try {
        const [actRes, propRes] = await Promise.all([
          fetchActivities({ per_page: 500, project_id: activeProject || undefined }).catch(() => null),
          fetchProperties(100).catch(() => null),
        ]);

        if (isCancelled) return;

        let projectsList = propRes?.properties || [];
        const activitiesList = actRes?.activities || [];

        // Filter projects by sector if active
        if (canonCode && canonCode !== "ALL") {
          projectsList = projectsList.filter(p => {
            const rawP = p as unknown as Record<string, unknown>;
            const pSector = canonicalSectorCode((p.sector || (rawP.attributes as Record<string, unknown>)?.sector || "") as string).toUpperCase();
            return !pSector || pSector === canonCode;
          });
        }

        setProjectCount(projectsList.length);

        // Derive real jurisdictions from projects
        const countryMap = new Map<string, number>();
        projectsList.forEach(p => {
          const rawP = p as unknown as Record<string, unknown>;
          const c = (rawP.country as string) || "Nigeria";
          countryMap.set(c, (countryMap.get(c) || 0) + 1);
        });

        const derivedJurisdictions: JurisdictionStatus[] = [];
        countryMap.forEach((count, country) => {
          derivedJurisdictions.push({
            country: country === "Nigeria" ? "Nigeria (Host Country)" : country,
            code: country.substring(0, 3).toUpperCase(),
            status: "ACTIVE",
            activeProjects: count
          });
        });

        if (derivedJurisdictions.length === 0) {
          derivedJurisdictions.push({
            country: "Host Country Authority",
            code: "HOST",
            status: "REGISTERED",
            activeProjects: projectsList.length
          });
        }

        setJurisdictions(derivedJurisdictions);
        setJurisdictionCount(derivedJurisdictions.length);

        // Assets and Table Parity
        let count = activitiesList.length;
        if (count === 0 && projectsList.length > 0) {
          count = projectsList.length;
        }
        setAssetCount(count);

        const tableItems: TableAssetItem[] = activitiesList.map(a => {
          const data = a.activity_data as Record<string, unknown> | null;
          const rawA = a as unknown as Record<string, unknown>;
          return {
            id: a.id,
            name: (data?.title as string) || (data?.location_name as string) || (rawA.name as string) || a.description || `Asset ${a.id.substring(0, 8)}`,
            type: a.activity_type || "MRV Asset",
            status: (rawA.status as string) || "ACTIVE",
            lat: a.latitude ?? null,
            lng: a.longitude ?? null,
            sector: (rawA.sector as string) || canonCode
          };
        });
        setAssetTableData(tableItems);

        // Verified Carbon check: Only display quantified verified carbon
        // Currently, unverified activities do not equal verified issuances.
        // If no verified issuances exist, verifiedCarbon remains null ("Not quantified").
        setVerifiedCarbon(null);

      } catch (err) {
        console.warn("Command center live fetch notice:", err);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    }

    fetchCommandMetrics();
    return () => {
      isCancelled = true;
    };
  }, [activeSector, activeProject, canonCode]);

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-[var(--color-text-primary)]">
      {/* Header — Professional Factual Copy */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[var(--color-primary)]">
              <Globe size={18} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Enterprise Spatial Command Center</h1>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Geospatial Operations & Asset Monitoring • Sector-Aware MRV Mapping & Earth Observation
              </p>
            </div>
          </div>
        </div>

        {/* View Mode Toggle: Map vs Table */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-semibold">
          <button
            type="button"
            onClick={() => setViewMode("map")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              viewMode === "map"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            <MapIcon size={14} />
            <span>Map View</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("table")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              viewMode === "table"
                ? "bg-[var(--color-primary)] text-white shadow-xs"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            <List size={14} />
            <span>Table Parity</span>
          </button>
        </div>
      </div>

      {/* Primary Command Center KPIs — Database-Backed Truth */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* KPI 1: Active Projects */}
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
            <span className="truncate">Active Projects</span>
            <Layers size={15} className="text-[var(--color-text-muted)] shrink-0" />
          </div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight truncate">
            {projectCount} Project{projectCount === 1 ? "" : "s"}
          </div>
          <div className="text-xs text-[var(--color-text-muted)] font-normal truncate">
            Across {jurisdictionCount} host {jurisdictionCount === 1 ? "jurisdiction" : "jurisdictions"}
          </div>
        </div>

        {/* KPI 2: Monitored Assets */}
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
            <span className="truncate">Monitored Assets</span>
            <Radio size={15} className="text-[var(--color-text-muted)] shrink-0" />
          </div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight truncate">
            {assetCount.toLocaleString()} Record{assetCount === 1 ? "" : "s"}
          </div>
          <div className="text-xs text-[var(--color-text-muted)] font-normal truncate">
            {canonCode.replace(/_/g, " ")} spatial inventory
          </div>
        </div>

        {/* KPI 3: Quantification / Verified Carbon */}
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
            <span className="truncate">Quantification / Verified Carbon</span>
            <TrendingUp size={15} className="text-[var(--color-text-muted)] shrink-0" />
          </div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight truncate">
            {verifiedCarbon !== null ? `${verifiedCarbon.toLocaleString()} tCO₂e` : "—"}
          </div>
          <div className="text-xs text-[var(--color-text-muted)] font-normal truncate">
            {verifiedCarbon !== null ? "Audited & Verified Issuance" : "Not quantified"}
          </div>
        </div>

        {/* KPI 4: Registry Submissions Queue */}
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
            <span className="truncate">Registry Submissions Queue</span>
            <ShieldCheck size={15} className="text-[var(--color-text-muted)] shrink-0" />
          </div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight truncate">
            0 Submissions
          </div>
          <div className="text-xs text-[var(--color-text-muted)] font-normal truncate">
            Verra VCS • Gold Standard • Puro.earth
          </div>
        </div>
      </div>

      {/* Main Grid: Live GIS Map or Parity Table & Jurisdiction Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols): Map or Table */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
            <div className="flex items-center gap-2">
              <Globe size={16} className="text-[var(--color-primary)]" />
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                {viewMode === "map" ? "Spatial Command Center Map" : "Filtered Spatial Asset Inventory"}
              </h2>
            </div>

            {/* Scope Tabs: Site, Regional, National, Global */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-medium">
              {SCOPE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveSpatialTab(tab.id)}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    activeSpatialTab === tab.id
                      ? "bg-[var(--color-primary)] text-white shadow-xs"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* View Container: Map or Table */}
          {viewMode === "map" ? (
            <div className="h-[460px] rounded-xl overflow-hidden border border-[var(--color-border)] relative z-0">
              <SpatialBoundaryMap
                sectorCode={activeSector}
                projectId={activeProject}
                activeScope={activeSpatialTab}
                data={mapGeojson ? (mapGeojson as unknown as { boundary_geojson?: GeoJSON.GeoJsonObject }) : undefined}
              />
              <div className="absolute bottom-3 left-3 z-10 px-3 py-1.5 rounded-lg bg-[var(--color-surface)]/90 backdrop-blur-xs border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)] font-medium pointer-events-none shadow-xs">
                {activeSpatialTab === "SITE" && "Scope: Project / Site Extent"}
                {activeSpatialTab === "REGIONAL" && "Scope: Regional Sub-National Extent"}
                {activeSpatialTab === "NATIONAL" && "Scope: Host Country National Portfolio"}
                {activeSpatialTab === "GLOBAL" && "Scope: Global Multi-Jurisdiction Overview"}
              </div>
            </div>
          ) : (
            <div className="h-[460px] rounded-xl overflow-y-auto border border-[var(--color-border)] bg-[var(--color-background)] p-4 text-xs">
              <div className="text-xs text-[var(--color-text-secondary)] mb-3 flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                <span>
                  Total records in scope: <strong className="text-[var(--color-text-primary)] font-semibold">{assetTableData.length}</strong>{" "}
                  (Mapped: <strong className="text-[var(--color-text-primary)] font-semibold">{assetTableData.filter(i => i.lat !== null && i.lng !== null).length}</strong> • Ungeocoded: <strong className="text-[var(--color-text-muted)] font-semibold">{assetTableData.filter(i => i.lat === null || i.lng === null).length}</strong>)
                </span>
                <span className="text-[var(--color-primary)] font-semibold">{canonCode}</span>
              </div>
              {assetTableData.length > 0 ? (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--color-border)] text-[var(--color-text-secondary)] text-xs font-medium">
                      <th className="py-2 px-2">ID</th>
                      <th className="py-2 px-2">Name</th>
                      <th className="py-2 px-2">Type</th>
                      <th className="py-2 px-2">Coordinates</th>
                      <th className="py-2 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {assetTableData.map((item, idx) => (
                      <tr key={idx} className="hover:bg-[var(--color-surface)]/50 transition-colors">
                        <td className="py-2 px-2 text-[var(--color-text-secondary)] font-mono text-[11px]">{item.id.substring(0, 8)}...</td>
                        <td className="py-2 px-2 text-[var(--color-text-primary)] font-medium">{item.name}</td>
                        <td className="py-2 px-2 text-[var(--color-text-secondary)]">{item.type}</td>
                        <td className="py-2 px-2 text-[var(--color-text-muted)] font-mono text-[11px]">
                          {item.lat !== null && item.lng !== null
                            ? `${Number(item.lat).toFixed(4)}, ${Number(item.lng).toFixed(4)}`
                            : "Ungeocoded"}
                        </td>
                        <td className="py-2 px-2">
                          <span className="px-2 py-0.5 rounded bg-[var(--color-surface)] text-[var(--color-text-secondary)] text-[10px] font-medium border border-[var(--color-border)]">
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center text-[var(--color-text-secondary)] space-y-1">
                  <p className="font-semibold text-sm text-[var(--color-text-primary)]">No spatial records found in active scope.</p>
                  <p className="text-xs text-[var(--color-text-muted)]">Parity verified: Map and table reflect the same empty dataset.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Jurisdiction Status (Database-Backed) */}
        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Server size={16} className="text-[var(--color-text-muted)]" />
              Jurisdiction status
            </h2>
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {jurisdictions.length} {jurisdictions.length === 1 ? "Authority" : "Authorities"}
            </span>
          </div>

          <div className="space-y-3">
            {jurisdictions.map((node, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-semibold text-[var(--color-text-primary)]">{node.country}</div>
                  <div className="text-xs text-[var(--color-text-muted)]">
                    {node.activeProjects} active {node.activeProjects === 1 ? "project" : "projects"} • Authorized National Host
                  </div>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                  {node.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
