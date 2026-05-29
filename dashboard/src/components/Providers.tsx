// =============================================================================
// VeriField Nexus — Client Providers Wrapper
// =============================================================================
// Wraps client-side providers (Toast, etc.) for the root layout.
// =============================================================================

"use client";

import { ToastProvider } from "@/components/Toast";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}
