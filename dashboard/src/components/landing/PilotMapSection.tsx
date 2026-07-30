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

              <div>

                <h4 className="text-sm font-semibold tracking-widest text-zinc-400 uppercase mb-2">PLATFORM STATUS</h4>

                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[#00B47A] text-xs font-mono font-bold">

                  <span className="w-2 h-2 rounded-full bg-[#00B47A] animate-pulse" />

                  <span>{stats?.status || "OPERATIONAL"}</span>

                </div>

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



          <div className="lg:w-2/3 w-full bg-zinc-50 border border-zinc-200 rounded-2xl p-8 min-h-[500px] flex items-center justify-center relative overflow-hidden">

            {/* Enterprise Architecture Spatial Topology Visual */}

            <div className="absolute inset-0 opacity-[0.05]" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '24px 24px' }} />



            <div className="relative z-10 text-center w-full max-w-lg">

               <div className="p-8 bg-white border border-zinc-200 rounded-2xl shadow-sm space-y-6">

                 <div className="w-12 h-12 rounded-xl bg-emerald-50 text-[#00B47A] border border-emerald-100 flex items-center justify-center mx-auto">

                   <ShieldCheck size={24} />

                 </div>

                 <div>

                   <h3 className="text-xl font-bold text-zinc-900 tracking-tight">Multi-Tenant Spatial Topology</h3>

                   <p className="text-xs text-zinc-500 mt-2 leading-relaxed">

                     Every project bound to VeriField Nexus executes under strict tenant isolation, cryptographic evidence hashing, and canonical verification stage classification.

                   </p>

                 </div>



                 <div className="grid grid-cols-3 gap-2 pt-4 border-t border-zinc-100 text-center">

                   <div className="p-2 rounded-lg bg-zinc-50">

                     <Building size={16} className="text-zinc-600 mx-auto mb-1" />

                     <span className="text-[10px] font-mono text-zinc-500 block uppercase">Organization Scope</span>

                   </div>

                   <div className="p-2 rounded-lg bg-zinc-50">

                     <MapPin size={16} className="text-[#00B47A] mx-auto mb-1" />

                     <span className="text-[10px] font-mono text-zinc-500 block uppercase">Project Geometry</span>

                   </div>

                   <div className="p-2 rounded-lg bg-zinc-50">

                     <Layers size={16} className="text-emerald-600 mx-auto mb-1" />

                     <span className="text-[10px] font-mono text-zinc-500 block uppercase">AST Engine</span>

                   </div>

                 </div>

               </div>

            </div>

            <div className="absolute bottom-6 right-6 text-xs font-mono text-zinc-400">VERIFIELD_CORE_TOPOLOGY</div>

          </div>

        </div>



      </div>

    </section>

  );

}
