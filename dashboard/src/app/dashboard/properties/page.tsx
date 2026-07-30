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

import { fetchProperties, createProject, fetchMethodologies } from "@/lib/api";

import type { Property } from "@/lib/types";

import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";



export default function PropertiesPage() {

  const toast = useToast();

  const { filterProperties, activeSector, activeMethodology, moduleRegistry } = useWorkspace();

  const [properties, setProperties] = useState<Property[]>([]);

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

    try {

      const res = await fetchProperties();

      setProperties(res.properties);

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



        <button

          onClick={() => setShowModal(true)}

          className="flex items-center gap-2 px-4 py-2 bg-[#00B47A] hover:bg-[#009b68] text-slate-950 font-extrabold text-xs rounded-xl shadow-md transition-all active:scale-[0.98] cursor-pointer shrink-0"

        >

          <Plus size={16} />

          <span>Create New Project</span>

        </button>

      </div>



      {/* 📊 DYNAMIC METRICS SUMMARY CARDS */}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">



        {/* Total Assets Summary */}

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Monitored Assets</p>

            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">

              {isLoading ? "..." : totalAssetsCount}

            </p>

            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Registered stoves & cookers</p>

          </div>

          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">

            <Layers size={18} />

          </div>

        </div>



        {/* Total Carbon Offsets Dynamic Sum */}

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-500/30 transition-all">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Verified Emissions Offsets</p>

            <p className="text-2xl font-black text-blue-400 tracking-tight">

              {isLoading ? "..." : `${totalCarbonOffset.toLocaleString()} kg`}

            </p>

            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Avoided CO₂ output</p>

          </div>

          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">

            <TreePine size={18} />

          </div>

        </div>



        {/* Verified Gold Status Counts */}

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-500/30 transition-all">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Certified Gold Standard</p>

            <p className="text-2xl font-black text-[#00B47A] tracking-tight">

              {isLoading ? "..." : verifiedAssetsCount}

            </p>

            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Fully verified MRV status</p>

          </div>

          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-purple-500 group-hover:text-white transition-all duration-300">

            <ShieldCheck size={18} />

          </div>

        </div>



      </div>



      {/* 🧭 SNAPPY REAL-TIME TOOLBAR */}

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">

        <div className="relative w-full max-w-md group">

          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] group-focus-within:text-[#00B47A] transition-colors" />

          <input

            type="text"

            value={searchQuery}

            onChange={(e) => setSearchQuery(e.target.value)}

            placeholder="Search assets by name, type, or region..."

            className="w-full pl-11 pr-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-slate-500 focus:border-[#00B47A]/40 focus:ring-1 focus:ring-[#00B47A]/30 focus:outline-none transition-all shadow-inner font-semibold"

          />

        </div>



        <span className="text-[10px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-widest shrink-0 self-end sm:self-center">

          Active ledger: {filteredProperties.length} results

        </span>

      </div>



      {/* 🧭 ASSETS GRID CONTAINER */}

      {isLoading ? (

        <div className="flex flex-col items-center justify-center py-16 space-y-3">

          <div className="w-7 h-7 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />

          <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">

            Retrieving secure MRV properties...

          </p>

        </div>

      ) : filteredProperties.length === 0 ? (

        <div className="p-12 text-center flex flex-col items-center justify-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md mx-auto shadow-sm">

          <Building2 size={36} className="text-[var(--color-text-muted)] mb-3 animate-pulse" />

          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">No Assets Matched</h3>

          <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">

            There are no registered assets matching your query search. Please try adjusting your parameters.

          </p>

        </div>

      ) : (

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">

          {filteredProperties.map((property) => {

            const Icon = getIcon(property.property_type);

            const metrics = property.sustainability_metrics as any || {};

            const isVerified = metrics?.status?.toLowerCase().includes("verif");

            const isFlagged = metrics?.status?.toLowerCase().includes("flag");



            return (

              <Link

                href={`/dashboard/properties/${property.id}`}

                key={property.id}

                className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden hover:border-[#00B47A]/30 hover:shadow-lg hover:shadow-black/10 transition-all duration-300 group flex flex-col justify-between"

              >

                {/* Upper Module */}

                <div className="p-4.5">

                  <div className="flex items-start justify-between mb-3.5">

                    <div className="w-10 h-10 rounded-xl bg-[#00B47A]/5 border border-[#00B47A]/10 group-hover:bg-[#00B47A] group-hover:text-white flex items-center justify-center text-[#00B47A] transition-all duration-300 shrink-0">

                      <Icon size={18} />

                    </div>

                    <span className="px-2.5 py-0.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[9px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider">

                      {property.property_type}

                    </span>

                  </div>



                  <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[#00B47A] transition-colors truncate" title={property.name}>

                    {property.name}

                  </h3>

                  <p className="text-xs text-[var(--color-text-secondary)] mt-1 line-clamp-2 min-h-[32px] font-medium leading-relaxed">

                    {property.address || "No region/address was registered."}

                  </p>

                </div>



                {/* Lower Module / Sustainability Info */}

                <div className="p-4.5 bg-[var(--color-background)]/50 border-t border-[var(--color-border)] flex-1 flex flex-col justify-end">

                  <div className="flex items-center gap-1.5 mb-3">

                    <Leaf size={13} className="text-[#00B47A]" />

                    <span className="text-[9px] font-extrabold text-[#00B47A] uppercase tracking-widest">

                      Sustainability Profile

                    </span>

                  </div>



                  <div className="grid grid-cols-3 gap-2">



                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner">

                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Energy Score</p>

                      <p className="text-xs font-black text-[#00B47A] font-mono">

                        {metrics?.energy_score || 'N/A'}

                      </p>

                    </div>



                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner">

                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Offset CO₂</p>

                      <p className="text-xs font-black text-blue-400 font-mono truncate">

                        {metrics?.carbon_offset_kg ? `${metrics.carbon_offset_kg}kg` : 'N/A'}

                      </p>

                    </div>



                    <div className="bg-[var(--color-surface)] rounded-xl p-2.5 border border-[var(--color-border)] shadow-inner overflow-hidden">

                      <p className="text-[8px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider mb-0.5">Status</p>

                      <p className={`text-[10px] font-extrabold uppercase truncate ${

                        isVerified

                          ? "text-[#00B47A]"

                          : isFlagged

                          ? "text-red-500"

                          : "text-amber-500"

                      }`} title={metrics?.status || 'Unverified'}>

                        {metrics?.status || 'Unverified'}

                      </p>

                    </div>



                  </div>



                  {/* Micro-interaction Hover Indicator */}

                  <div className="mt-3.5 pt-2.5 border-t border-[var(--color-border)]/5 flex items-center justify-between text-[9px] font-extrabold text-[var(--color-text-secondary)] uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity duration-300">

                    <span>Inspect Ledger Details</span>

                    <ArrowRight size={12} className="text-[#00B47A] transform translate-x-0 group-hover:translate-x-1 transition-transform" />

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

                    {activeMethodology || "AMS-II.G"} (Locked)

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
