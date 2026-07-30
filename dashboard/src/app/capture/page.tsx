"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import { Camera, MapPin, Database } from "lucide-react";

import { useToast } from "@/components/Toast";



export default function GenericCapturePage() {

  const [methodology, setMethodology] = useState("");

  const router = useRouter();

  const toast = useToast();



  return (

    <div className="min-h-screen bg-[#06090A] text-white p-6">

      <header className="mb-6 flex items-center justify-between border-b border-zinc-800 pb-4">

        <div>

          <img

            src="/logo-white.png"

            alt="VeriField Capture"

            className="h-6 w-auto object-contain mb-1"

          />

          <p className="text-zinc-400 text-xs">Field Agent Collection & Revisit PWA</p>

        </div>

        <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">

          OFFLINE QUEUE READY

        </span>

      </header>

      <div className="space-y-4">

        <div>

          <label className="text-sm font-semibold mb-1 block">Methodology Target</label>

          <input

            type="text"

            value={methodology}

            onChange={e => setMethodology(e.target.value)}

            placeholder="e.g. Direct Air Capture"

            className="w-full px-4 py-3 rounded-xl bg-[#090F10] border border-[#213233] text-white focus:border-[#00B47A]"

          />

        </div>

        <button

          className="w-full py-3 rounded-xl bg-emerald-500 font-bold"

          onClick={() => toast.info("Capture Initiated", `Capture started for: ${methodology}`)}

        >

          Initialize Capture Form

        </button>

      </div>

    </div>

  );

}
