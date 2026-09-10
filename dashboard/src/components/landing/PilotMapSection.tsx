"use client";



import { useEffect, useState } from "react";

import { motion } from "framer-motion";

import { fetchPublicOverview } from "@/lib/api";

import { Building, Layers, MapPin, ShieldCheck } from "lucide-react";



export function PilotMapSection() {

  const [stats, setStats] = useState<{

    sectors: number;

    methodologies: number;

    projects: number;

    assets: number;

    activities: number;

    organizations: number;

    status: string;

  } | null>(null);

  const [isLoading, setIsLoading] = useState(true);



  useEffect(() => {

    async function loadOverview() {

      try {

        const data = await fetchPublicOverview();

        setStats(data);

      } catch (err) {

        console.error("Failed to fetch public platform overview:", err);

      } finally {

        setIsLoading(false);

      }

    }

    loadOverview();

  }, []);



  return (

    <section className="bg-white text-[#0A0A0A] py-24 lg:py-32 border-b border-zinc-200">

      <div className="max-w-[1280px] mx-auto px-6">



        <div className="flex flex-col lg:flex-row gap-16 items-start">

          <div className="lg:w-1/3">

            <h2 className="text-3xl font-semibold tracking-tight mb-6">Live Platform Scope</h2>

            <p className="text-zinc-600 mb-10 leading-relaxed text-lg">

              VeriField provides digital MRV infrastructure to deploy, monitor, and verify climate assets across registered organizations and project developers.

            </p>



            <div className="flex flex-col gap-8">
              <div className="flex items-center text-xs text-zinc-600">
                <span>Platform Status: <strong className="font-semibold text-zinc-900">{stats?.status === "OPERATIONAL" || !stats?.status ? "Operational" : stats.status}</strong></span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="border-l-2 border-[#00B47A] pl-4">
                  <p className="text-3xl font-semibold tracking-tight">
                    {isLoading ? "..." : (stats?.assets ?? 0)}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Assets Tracked</p>
                </div>

                <div className="border-l-2 border-zinc-200 pl-4">
                  <p className="text-3xl font-semibold tracking-tight">
                    {isLoading ? "..." : (stats?.methodologies ?? 0)}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Methodologies</p>
                </div>

                <div className="border-l-2 border-zinc-200 pl-4">
                  <p className="text-3xl font-semibold tracking-tight">
                    {isLoading ? "..." : (stats?.projects ?? 0)}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Active Projects</p>
                </div>

                <div className="border-l-2 border-zinc-200 pl-4">
                  <p className="text-3xl font-semibold tracking-tight">
                    {isLoading ? "..." : (stats?.organizations ?? 0)}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Organizations</p>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:w-2/3 w-full bg-zinc-50/80 border border-zinc-200 rounded-2xl p-6 sm:p-8 flex flex-col justify-between">
            {/* Header */}
            <div className="flex items-center pb-5 border-b border-zinc-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-[#00B47A]">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-zinc-900 tracking-tight">Multi-Tenant Spatial Governance</h3>
                  <p className="text-xs text-zinc-500">Cryptographic evidence boundaries and role-based data isolation</p>
                </div>
              </div>
            </div>

            {/* Structured Governance Matrix */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6">
              <div className="p-4 rounded-xl bg-white border border-zinc-200 space-y-2">
                <div className="flex items-center gap-2 text-zinc-800">
                  <Building size={16} className="text-zinc-600" />
                  <h4 className="text-xs font-semibold text-zinc-900">Tenant Isolation</h4>
                </div>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Strict organizational boundary enforcement preventing cross-tenant data access and unauthorized exposure.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-zinc-200 space-y-2">
                <div className="flex items-center gap-2 text-zinc-800">
                  <MapPin size={16} className="text-[#00B47A]" />
                  <h4 className="text-xs font-semibold text-zinc-900">Spatial Geometry</h4>
                </div>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Geospatial polygon boundaries, GPS geotagging, and verifiable field coordinates tied to asset locations.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-zinc-200 space-y-2">
                <div className="flex items-center gap-2 text-zinc-800">
                  <Layers size={16} className="text-emerald-600" />
                  <h4 className="text-xs font-semibold text-zinc-900">Audit Verification</h4>
                </div>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Independent VVB auditor workflows, tamper-evident data lineage, and deterministic issuance validation.
                </p>
              </div>
            </div>
          </div>

        </div>



      </div>

    </section>

  );

}
