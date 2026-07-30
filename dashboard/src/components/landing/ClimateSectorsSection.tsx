"use client";



import { useEffect, useState } from "react";

import { motion } from "framer-motion";

import { Zap, Flame, Leaf, Car, Layers } from "lucide-react";

import { fetchPublicSectors } from "@/lib/api";



const SECTOR_ICONS: Record<string, any> = {

  COOKSTOVES: Flame,

  HYBRID_ENERGY: Zap,

  BIOCHAR: Leaf,

  EV_MOBILITY: Car,

};



export function ClimateSectorsSection() {

  const [sectors, setSectors] = useState<any[]>([]);

  const [isLoading, setIsLoading] = useState(true);



  useEffect(() => {

    async function loadSectors() {

      try {

        const data = await fetchPublicSectors();

        setSectors(data);

      } catch (err) {

        console.error("Failed to load sectors dynamically:", err);

      } finally {

        setIsLoading(false);

      }

    }

    loadSectors();

  }, []);



  return (

    <section id="industries" className="bg-[#050505] text-white py-24 lg:py-32 border-b border-zinc-900">

      <div className="max-w-[1280px] mx-auto px-6">



        <div className="mb-20 text-center max-w-2xl mx-auto">

          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">Supported Sectors</h2>

          <p className="text-zinc-400 text-lg">

            VeriField is not limited to a single asset class. Our methodology engine is built to support the entire spectrum of global climate infrastructure.

          </p>

        </div>



        {/* Dynamic Production Sectors */}

        {isLoading ? (

          <div className="py-12 text-center text-zinc-500 font-mono text-xs">

            Loading platform sector metadata...

          </div>

        ) : sectors.length === 0 ? (

          <div className="p-8 text-center bg-zinc-900/40 border border-zinc-800 rounded-2xl text-zinc-400 text-sm">

            Sector methodology families will populate dynamically as enabled on the platform.

          </div>

        ) : (

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">

            {sectors.map((sector, idx) => {

              const IconComp = SECTOR_ICONS[sector.code] || Layers;

              const typesCount = sector.project_types?.length || 0;

              const typesText = sector.project_types?.map((p: any) => p.name).join(", ");

              return (

                <motion.div

                  key={sector.id || idx}

                  initial={{ opacity: 0, y: 10 }}

                  whileInView={{ opacity: 1, y: 0 }}

                  viewport={{ once: true }}

                  transition={{ duration: 0.5, delay: idx * 0.1 }}

                  className="group p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/40 transition-colors"

                >

                  <div className="flex items-center gap-4 mb-4">

                    <div className="w-12 h-12 rounded-xl bg-[#0A0A0A] border border-zinc-800 flex items-center justify-center shadow-sm">

                      <IconComp size={22} className="text-[#00B47A]" strokeWidth={1.5} />

                    </div>

                    <div>

                      <h3 className="text-xl font-semibold text-white tracking-tight">{sector.name}</h3>

                      <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest">{sector.code}</span>

                    </div>

                  </div>

                  <p className="text-zinc-400 leading-relaxed text-sm">

                    {sector.description || `${sector.name} digital MRV and operational methodology engine. Supports ${typesCount} project types.`}

                  </p>

                  {typesText ? (

                    <div className="mt-4 pt-4 border-t border-zinc-800/60 text-xs text-zinc-500 font-mono">

                      <strong className="text-zinc-400">Supported Types:</strong> {typesText}

                    </div>

                  ) : null}

                </motion.div>

              );

            })}

          </div>

        )}



        {/* Frameworks & Standards */}

        <div className="text-center pt-20 border-t border-zinc-900 mt-20">

          <h3 className="text-sm font-semibold tracking-widest text-zinc-500 uppercase mb-12">Frameworks & Standards</h3>

          <div className="flex flex-wrap justify-center gap-x-12 gap-y-8 items-center opacity-60 grayscale hover:grayscale-0 transition-all duration-500">

            <span className="text-xl font-bold font-serif tracking-tight text-white">Verra</span>

            <span className="text-xl font-bold tracking-tighter text-white">Gold Standard</span>

            <span className="text-xl font-bold font-mono text-white">CDM</span>

            <span className="text-xl font-medium tracking-tight border border-current px-3 py-1 rounded-sm text-white">Article 6</span>

            <span className="text-xl font-bold tracking-widest text-white">ISO 14064</span>

            <span className="text-sm font-medium border-l-2 pl-4 py-1 border-current text-white">Nigeria Climate<br/>Change Act</span>

          </div>

        </div>



      </div>

    </section>

  );

}
