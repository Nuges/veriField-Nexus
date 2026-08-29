// =============================================================================

// VeriField Nexus — Properties/Assets Page

// =============================================================================

// Executive carbon assets directory and live sustainability verification ledger.

// =============================================================================



"use client";



import { useEffect, useState } from "react";

import Link from "next/link";

import {

  Plus,

  Search,

  Building2,

  Home,

  Factory,

  Leaf,

  Sparkles,

  ArrowRight,

  ShieldCheck,

  TreePine,

  CloudLightning,

  Layers,

  X,

  Loader2

} from "lucide-react";

import { fetchProperties, createProject, fetchProjects, fetchMethodologies } from "@/lib/api";

import type { Property } from "@/lib/types";

import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";



export default function PropertiesPage() {
  const toast = useToast();
  const { filterProperties, activeSector, activeMethodology, moduleRegistry } = useWorkspace();
  const [properties, setProperties] = useState<Property[]>([]);
  const [realProjects, setRealProjects] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    country: "Nigeria",
    baseline_source: "diesel_generator",
    diesel_emission_factor: 2.68,
    grid_emission_factor: 0.7,
    crediting_start: "",
    crediting_end: ""
  });

  const loadProps = async () => {
    setIsLoading(true);
    try {
      const [resProps, resProjects] = await Promise.allSettled([
        fetchProperties(),
        fetchProjects()
      ]);

      if (resProps.status === "fulfilled") {
        setProperties(resProps.value?.properties || []);
      }
      if (resProjects.status === "fulfilled") {
        const items = resProjects.value?.items || (Array.isArray(resProjects.value) ? resProjects.value : []);
        setRealProjects(items);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProps();
  }, []);



  const handleCreateProject = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!formData.name.trim()) {

      toast.error("Validation Error", "Please enter a valid project name.");

      return;

    }



    setIsSubmitting(true);

    try {

      // Find current methodology ID or fallback

      const activeModule = activeSector ? moduleRegistry[activeSector] : null;

      const methodologyId = activeModule?.methodology_id || "fe2f48fe-e99b-44eb-8b2b-72b330317e6a";



      await createProject({

        name: formData.name,

        country: formData.country,

        methodology_id: methodologyId,

        baseline_source: formData.baseline_source,

        diesel_emission_factor: Number(formData.diesel_emission_factor),

        grid_emission_factor: Number(formData.grid_emission_factor),

        crediting_start: formData.crediting_start || undefined,

        crediting_end: formData.crediting_end || undefined

      });



      toast.success("Project Registered", `Project "${formData.name}" onboarded successfully.`);

      setShowModal(false);

      setFormData({

        name: "",

        country: "Nigeria",

        baseline_source: "diesel_generator",

        diesel_emission_factor: 2.68,

        grid_emission_factor: 0.7,

        crediting_start: "",

        crediting_end: ""

      });

      loadProps();

    } catch (err: any) {

      console.error("Project creation failed:", err);

      toast.error("Creation Failed", err.message || "Failed to register project.");

    } finally {

      setIsSubmitting(false);

    }

  };



  const getIcon = (type: string) => {

    switch (type) {

      case 'residential': return Home;

      case 'commercial': return Building2;

      case 'industrial': return Factory;

      default: return Building2;

    }

  };



  // Filter properties by active workspace sector context

  const isolatedProperties = filterProperties(properties);



  // Derive dynamic dashboard stats from the assets

  const totalAssetsCount = isolatedProperties.length;

  const verifiedAssetsCount = isolatedProperties.filter(

    p => (p.sustainability_metrics as any)?.status?.toLowerCase().includes("verif")

  ).length;



  const totalCarbonOffset = isolatedProperties.reduce(

    (acc, p) => acc + (Number((p.sustainability_metrics as any)?.carbon_offset_kg) || 0),

    0

  );



  // Snappy client-side search query matching

  const filteredProperties = isolatedProperties.filter(p => {

    if (!searchQuery) return true;

    const query = searchQuery.toLowerCase();

    return (

      (p.name || "").toLowerCase().includes(query) ||

      (p.property_type || "").toLowerCase().includes(query) ||

      (p.address || "").toLowerCase().includes(query)

    );

  });



  return (

    <div className="space-y-6 animate-fade-in-up">



      {/* 👑 EXECUTIVE TITLE & ACTION BUTTON */}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">

        <div>

          <div className="flex items-center gap-2">

            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">

              MRV Registry

            </span>

          </div>

          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">

            Registered Carbon Assets & Projects

          </h1>

          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit energy efficiency scores, inspect geographical placements, and onboard new climate projects.
          </p>
        </div>
      </div>



      {/* 📊 DYNAMIC METRICS SUMMARY CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Total Assets Summary */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">
              {activeSector === "ev_mobility" ? "Registered EV Fleets & Stations" :
               activeSector === "hybrid_energy" ? "Registered Solar Mini-grids" :
               activeSector === "biochar" ? "Registered Biochar Pyrolyzers" :
               activeSector === "cookstoves" ? "Monitored Stove Devices" : "Monitored Carbon Assets"}
            </p>
            <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
              {isLoading ? "..." : totalAssetsCount}
            </p>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              {realProjects.length} Active Project{realProjects.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="w-9 h-9 bg-emerald-50 dark:bg-emerald-950/40 rounded-md text-[#008A5E] flex items-center justify-center shrink-0">
            <Layers size={18} />
          </div>
        </div>

        {/* Total Carbon Offsets Dynamic Sum */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">Verified Emissions Offsets</p>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 tracking-tight">
              {isLoading ? "..." : `${totalCarbonOffset.toLocaleString()} kg`}
            </p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Avoided CO₂ output</p>
          </div>
          <div className="w-9 h-9 bg-blue-50 dark:bg-blue-950/40 rounded-md text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <TreePine size={18} />
          </div>
        </div>

        {/* Verified Gold Status Counts */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">Certified Gold Standard</p>
            <p className="text-2xl font-bold text-[#008A5E] tracking-tight">
              {isLoading ? "..." : verifiedAssetsCount}
            </p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Fully verified MRV status</p>
          </div>
          <div className="w-9 h-9 bg-emerald-50 dark:bg-emerald-950/40 rounded-md text-[#008A5E] flex items-center justify-center shrink-0">
            <ShieldCheck size={18} />
          </div>
        </div>
      </div>

      {/* 📁 REGISTERED CLIMATE PROJECTS ROSTER */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E]">
              <Building2 size={18} />
            </div>
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
                Registered Climate Projects ({realProjects.length})
              </h2>
              <p className="text-[11px] text-[var(--color-text-secondary)]">
                All onboarded climate projects, methodologies, and spatial boundaries for your organization.
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-3 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
          >
            <Plus size={13} />
            <span>+ Create New Project</span>
          </button>
        </div>

        {realProjects.length === 0 ? (
          <div className="p-6 text-center bg-[var(--color-background)] rounded-md border border-[var(--color-border)] space-y-1.5">
            <p className="text-xs font-semibold text-[var(--color-text-primary)]">No Projects Registered Yet</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Click "+ Create New Project" to onboard your first project.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-[11px] font-semibold text-[var(--color-text-secondary)] bg-[#F8FAFC] dark:bg-slate-900">
                  <th className="py-2.5 px-3">Project Name</th>
                  <th className="py-2.5 px-3">Project Code</th>
                  <th className="py-2.5 px-3">Country</th>
                  <th className="py-2.5 px-3">Methodology</th>
                  <th className="py-2.5 px-3">Crediting Period</th>
                  <th className="py-2.5 px-3">Date Registered</th>
                  <th className="py-2.5 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)] text-xs">
                {realProjects.map((proj) => (
                  <tr key={proj.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-2.5 px-3 font-medium text-[var(--color-text-primary)]">
                      {proj.name}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-[var(--color-text-muted)]">
                      {proj.project_code || "VF-GP-001"}
                    </td>
                    <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">
                      {proj.country || "Nigeria"}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-[#008A5E]">
                      {proj.methodology_id ? "AMS-III.C" : "AMS-II.G"}
                    </td>
                    <td className="py-2.5 px-3 text-[var(--color-text-secondary)] text-[11px]">
                      {proj.crediting_start ? `${proj.crediting_start} → ${proj.crediting_end || "Ongoing"}` : "Standard 10-Year"}
                    </td>
                    <td className="py-2.5 px-3 text-[var(--color-text-muted)] text-[11px]">
                      {proj.created_at ? new Date(proj.created_at).toLocaleDateString() : "Active"}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-[#008A5E] dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                        Active
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 🧭 MONITORED CARBON ASSETS & DEVICES DIRECTORY TOOLBAR */}
      <div className="pt-3 border-t border-[var(--color-border)] space-y-3">
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              Monitored Assets & Device Telemetry
            </h3>
            <p className="text-[11px] text-[var(--color-text-secondary)]">
              Physical hardware devices, chargers, and sensors bound to onboarded projects.
            </p>
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets by name or region..."
              className="w-full pl-8 pr-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[#008A5E] focus:outline-none transition-colors"
            />
          </div>
        </div>
      </div>

      {/* 🧭 ASSETS GRID CONTAINER */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12 space-y-2.5">
          <div className="w-6 h-6 border-2 border-[#008A5E] border-t-transparent rounded-full animate-spin" />
          <p className="text-[var(--color-text-secondary)] text-xs font-medium">
            Loading registered assets...
          </p>
        </div>
      ) : filteredProperties.length === 0 ? (
        <div className="p-8 text-center flex flex-col items-center justify-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg max-w-md mx-auto">
          <Building2 size={28} className="text-[var(--color-text-muted)] mb-2" />
          <h3 className="text-xs font-semibold text-[var(--color-text-primary)]">No Assets Found</h3>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">
            There are no registered assets matching your search query.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredProperties.map((property) => {
            const Icon = getIcon(property.property_type);
            const metrics = property.sustainability_metrics as any || {};
            const isVerified = metrics?.status?.toLowerCase().includes("verif");
            const isFlagged = metrics?.status?.toLowerCase().includes("flag");

            return (
              <Link
                href={`/dashboard/properties/${property.id}`}
                key={property.id}
                className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden hover:border-slate-300 dark:hover:border-slate-700 transition-colors flex flex-col justify-between"
              >
                {/* Upper Module */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2.5">
                    <div className="w-8 h-8 rounded-md bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center text-[#008A5E] shrink-0">
                      <Icon size={16} />
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-secondary)] capitalize">
                      {property.property_type}
                    </span>
                  </div>

                  <h3 className="text-xs font-semibold text-[var(--color-text-primary)] truncate" title={property.name}>
                    {property.name}
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5 line-clamp-1">
                    {property.address || "Location unassigned"}
                  </p>
                </div>

                {/* Lower Module / Sustainability Info */}
                <div className="p-3 bg-slate-50/60 dark:bg-slate-900/40 border-t border-[var(--color-border)]">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-[var(--color-surface)] rounded-md p-1.5 border border-[var(--color-border)]">
                      <p className="text-[9px] text-[var(--color-text-muted)] font-medium uppercase">Score</p>
                      <p className="text-xs font-bold text-[#008A5E]">
                        {metrics?.energy_score || 'N/A'}
                      </p>
                    </div>

                    <div className="bg-[var(--color-surface)] rounded-md p-1.5 border border-[var(--color-border)]">
                      <p className="text-[9px] text-[var(--color-text-muted)] font-medium uppercase">Offset</p>
                      <p className="text-xs font-bold text-blue-600 dark:text-blue-400 truncate">
                        {metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg}kg` : 'N/A'}
                      </p>
                    </div>

                    <div className="bg-[var(--color-surface)] rounded-md p-1.5 border border-[var(--color-border)]">
                      <p className="text-[9px] text-[var(--color-text-muted)] font-medium uppercase">Status</p>
                      <p className={`text-[10px] font-semibold truncate ${
                        isVerified
                          ? "text-[#008A5E]"
                          : isFlagged
                          ? "text-red-600 dark:text-red-400"
                          : "text-amber-600 dark:text-amber-400"
                      }`} title={metrics?.status || 'Unverified'}>
                        {metrics?.status || 'Active'}
                      </p>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* ➕ CREATE NEW PROJECT ONBOARDING MODAL */}

      {showModal && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-scale-up">



            {/* Modal Header */}

            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">

              <div>

                <span className="text-[9px] font-black uppercase tracking-widest text-[#00B47A]">

                  PROJECT ONBOARDING

                </span>

                <h2 className="text-base font-bold text-[var(--color-text-primary)]">

                  Register New Climate Project

                </h2>

              </div>

              <button

                onClick={() => setShowModal(false)}

                className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)] transition-all"

              >

                <X size={18} />

              </button>

            </div>



            {/* Modal Form Body */}

            <form onSubmit={handleCreateProject} className="p-5 space-y-4">



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                  Project Name *

                </label>

                <input

                  type="text"

                  required

                  value={formData.name}

                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}

                  placeholder="e.g. Kano Clean Cooking Expansion Project"

                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                />

              </div>



              <div className="grid grid-cols-2 gap-3">

                <div>

                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Host Country

                  </label>

                  <select

                    value={formData.country}

                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  >

                    <option value="Nigeria">Nigeria</option>

                    <option value="Kenya">Kenya</option>

                    <option value="Ghana">Ghana</option>

                    <option value="Rwanda">Rwanda</option>

                    <option value="South Africa">South Africa</option>

                  </select>

                </div>



                <div>

                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Active Sector & Methodology

                  </label>

                  <div className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-[11px] font-mono font-bold text-[#00B47A] truncate">

                    {activeMethodology || (activeSector === "hybrid_energy" ? "ACM0002" : activeSector === "biochar" ? "VM0042" : activeSector === "ev_mobility" ? "AMS-III.C" : "AMS-II.G")} (Locked)

                  </div>

                </div>

              </div>



              <div className="grid grid-cols-3 gap-3">

                <div>

                  <label className="text-[9px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Baseline Source

                  </label>

                  <input

                    type="text"

                    value={formData.baseline_source}

                    onChange={(e) => setFormData({ ...formData, baseline_source: e.target.value })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  />

                </div>



                <div>

                  <label className="text-[9px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Diesel Factor (kg/L)

                  </label>

                  <input

                    type="number"

                    step="0.01"

                    value={formData.diesel_emission_factor}

                    onChange={(e) => setFormData({ ...formData, diesel_emission_factor: Number(e.target.value) })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  />

                </div>



                <div>

                  <label className="text-[9px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Grid Factor (kg/kWh)

                  </label>

                  <input

                    type="number"

                    step="0.01"

                    value={formData.grid_emission_factor}

                    onChange={(e) => setFormData({ ...formData, grid_emission_factor: Number(e.target.value) })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  />

                </div>

              </div>



              <div className="grid grid-cols-2 gap-3">

                <div>

                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Crediting Start Date

                  </label>

                  <input

                    type="date"

                    value={formData.crediting_start}

                    onChange={(e) => setFormData({ ...formData, crediting_start: e.target.value })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  />

                </div>



                <div>

                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)] block mb-1">

                    Crediting End Date

                  </label>

                  <input

                    type="date"

                    value={formData.crediting_end}

                    onChange={(e) => setFormData({ ...formData, crediting_end: e.target.value })}

                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs font-semibold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                  />

                </div>

              </div>



              {/* Modal Actions */}

              <div className="pt-3 border-t border-[var(--color-border)] flex items-center justify-end gap-2">

                <button

                  type="button"

                  onClick={() => setShowModal(false)}

                  className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] transition-all cursor-pointer"

                >

                  Cancel

                </button>



                <button

                  type="submit"

                  disabled={isSubmitting}

                  className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-extrabold bg-[#00B47A] hover:bg-[#009b68] text-slate-950 transition-all shadow-md active:scale-[0.98] cursor-pointer disabled:opacity-50"

                >

                  {isSubmitting ? (

                    <>

                      <Loader2 size={14} className="animate-spin" />

                      <span>Registering...</span>

                    </>

                  ) : (

                    <span>Register Project</span>

                  )}

                </button>

              </div>



            </form>



          </div>

        </div>

      )}



    </div>

  );

}
