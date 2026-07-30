"use client";



import { useEffect } from "react";

import { useRouter } from "next/navigation";



export default function MapPage() {

  const router = useRouter();



  useEffect(() => {

    router.replace("/dashboard/command-center");

  }, [router]);



  return (

    <div className="flex items-center justify-center min-h-[400px] text-xs font-mono text-[var(--color-text-secondary)]">

      Redirecting to Unified Spatial Command Center...

    </div>

  );

}
