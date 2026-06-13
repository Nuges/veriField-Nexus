// =============================================================================
// VeriField Nexus — Client Providers Wrapper
// =============================================================================
// Wraps client-side providers (Toast, etc.) for the root layout.
// =============================================================================

"use client";

import { ToastProvider } from "@/components/Toast";
import { useEffect, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      if (process.env.NODE_ENV === "production") {
        window.addEventListener("load", () => {
          navigator.serviceWorker
            .register("/sw.js")
            .then((reg) => {
              console.log("Service Worker registered successfully with scope:", reg.scope);
            })
            .catch((err) => {
              console.error("Service Worker registration failed:", err);
            });
        });
      } else {
        // Unregister service worker in development mode to prevent Next.js hot-reload issues
        navigator.serviceWorker.getRegistrations().then((registrations) => {
          for (const registration of registrations) {
            registration.unregister().then((success) => {
              if (success) {
                console.log("Unregistered active service worker in development mode.");
              }
            });
          }
        });
      }
    }
  }, []);

  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}
