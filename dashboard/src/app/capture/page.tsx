"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, MapPin, Database } from "lucide-react";

export default function GenericCapturePage() {
  const [methodology, setMethodology] = useState("");
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#06090A] text-white p-6">
      <header className="mb-6">
        <h1 className="text-xl font-bold">Standalone Field Capture</h1>
        <p className="text-zinc-400 text-sm">Dynamic Metadata-Driven Collection</p>
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
          onClick={() => alert("Capture started for: " + methodology)}
        >
          Initialize Capture Form
        </button>
      </div>
    </div>
  );
}
