// =============================================================================
// VeriField Nexus — Client Providers Wrapper
// =============================================================================
// Wraps client-side providers (Toast, etc.) for the root layout.
// Handles aggressive service worker cleanup in development to prevent
// stale cached assets from causing infinite loading on mobile devices.
// =============================================================================

"use client";

import { ToastProvider } from "@/components/Toast";
import { useEffect, type ReactNode } from "react";

/**
 * Aggressively purge all service workers AND their caches.
 * This is critical for iPhone PWA — stale SW caches serve old HTML/JS
 * bundles that reference non-existent chunk files, causing infinite loading.
 */
async function purgeAllServiceWorkers() {
  try {
    // 1. Unregister every active service worker
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      const success = await registration.unregister();
      if (success) {
        console.log("[SW Cleanup] Unregistered service worker:", registration.scope);
      }
    }

    // 2. Purge ALL caches (stale HTML, JS chunks, API responses)
    const cacheNames = await caches.keys();
    for (const cacheName of cacheNames) {
      await caches.delete(cacheName);
      console.log("[SW Cleanup] Deleted cache:", cacheName);
    }

    if (registrations.length > 0 || cacheNames.length > 0) {
      console.log("[SW Cleanup] All service workers and caches purged.");
    }
  } catch (err) {
    console.error("[SW Cleanup] Failed to purge:", err);
  }
}

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
        // Development: aggressively purge ALL service workers and caches
        // to prevent stale cached assets from causing infinite loading on iPhone
        purgeAllServiceWorkers();
      }
    }
  }, []);

  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}

