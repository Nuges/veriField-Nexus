"use client";

import { motion } from "framer-motion";

export function PilotMapSection() {
  return (
    <section className="bg-white text-[#0A0A0A] py-24 lg:py-32 border-b border-zinc-200">
      <div className="max-w-[1280px] mx-auto px-6">
        
        <div className="flex flex-col lg:flex-row gap-16 items-start">
          <div className="lg:w-1/3">
            <h2 className="text-3xl font-semibold tracking-tight mb-6">Current Deployment Pipeline</h2>
            <p className="text-zinc-600 mb-10 leading-relaxed text-lg">
              VeriField is actively managing early-stage deployments and pilot programmes, focusing initially on the African continent to address critical monitoring infrastructure gaps in emerging markets.
            </p>

            <div className="flex flex-col gap-8">
              <div>
                <h4 className="text-sm font-semibold tracking-widest text-zinc-400 uppercase mb-2">Primary Region</h4>
                <p className="text-xl font-medium text-zinc-900">Nigeria & West Africa</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="border-l-2 border-[#00B47A] pl-4">
                  <p className="text-3xl font-semibold tracking-tight">40k+</p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Assets Tracked</p>
                </div>
                <div className="border-l-2 border-zinc-200 pl-4">
                  <p className="text-3xl font-semibold tracking-tight">5</p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mt-1">Methodologies</p>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:w-2/3 w-full bg-zinc-50 border border-zinc-200 rounded-2xl p-8 min-h-[500px] flex items-center justify-center relative overflow-hidden">
            {/* Minimalist Africa Map Abstract Representation using pure CSS/SVG */}
            <div className="absolute inset-0 opacity-[0.05]" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
            
            <div className="relative z-10 text-center">
               {/* Since we can't easily load an accurate SVG map of Africa without an asset, we'll use a high-end data visualization abstract box that "represents" spatial data. */}
               <div className="w-[300px] h-[300px] sm:w-[400px] sm:h-[400px] relative border border-zinc-200 rounded-full flex items-center justify-center bg-white shadow-sm">
                  <div className="absolute w-full h-full border border-zinc-100 rounded-full animate-[spin_60s_linear_infinite]" />
                  <div className="absolute w-[80%] h-[80%] border border-[#00B47A]/20 rounded-full" />
                  
                  {/* Simulated Data Nodes in West Africa */}
                  <div className="absolute top-[40%] left-[35%]">
                    <motion.div 
                      className="w-3 h-3 bg-[#00B47A] rounded-full relative z-20"
                      animate={{ scale: [1, 1.5, 1] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-[#00B47A]/20 rounded-full animate-ping" />
                    <span className="absolute top-4 left-4 text-xs font-semibold bg-white border border-zinc-200 px-2 py-0.5 rounded shadow-sm">Nigeria Pilot</span>
                  </div>

                  {/* Connected Nodes */}
                  <div className="absolute top-[30%] right-[30%] w-2 h-2 bg-zinc-300 rounded-full" />
                  <div className="absolute bottom-[40%] right-[40%] w-2 h-2 bg-zinc-300 rounded-full" />
                  <div className="absolute bottom-[20%] left-[40%] w-2 h-2 bg-zinc-300 rounded-full" />
                  
                  {/* Connection Lines */}
                  <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 400">
                    <path d="M 140 160 L 280 120" stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray="4 4" fill="none" />
                    <path d="M 140 160 L 240 240" stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray="4 4" fill="none" />
                  </svg>
               </div>
            </div>
            <div className="absolute bottom-6 right-6 text-xs font-mono text-zinc-400">GEO_DATA_NODE_AFRICA_W</div>
          </div>
        </div>

      </div>
    </section>
  );
}
