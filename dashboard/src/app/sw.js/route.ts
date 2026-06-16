// =============================================================================
// VeriField Nexus — Dynamic PWA Service Worker Route Handler
// =============================================================================
// Serves a self-destructing cleaner script in development mode to prevent Next.js
// compilation / cache blockage, and serves the offline-first Service Worker
// in production.
// =============================================================================

import { NextResponse } from "next/server";

export async function GET() {
  const isProd = process.env.NODE_ENV === "production";

  // Development: Self-destructing script that purges caches, unregisters itself, and reloads
  const devScript = `
    console.log("[SW] Development mode detected. Executing self-destruct cleaner...");
    self.addEventListener("install", (event) => {
      self.skipWaiting();
    });
    self.addEventListener("activate", (event) => {
      event.waitUntil(
        caches.keys().then((cacheNames) => {
          return Promise.all(
            cacheNames.map((cacheName) => {
              console.log("[SW] Deleting stale cache:", cacheName);
              return caches.delete(cacheName);
            })
          );
        }).then(() => {
          return self.registration.unregister();
        }).then(() => {
          console.log("[SW] Service worker unregistered and caches purged. Reloading clients...");
          return self.clients.matchAll();
        }).then((clients) => {
          clients.forEach((client) => {
            if (client.url) {
              client.navigate(client.url);
            }
          });
        })
      );
    });
    // Do NOT intercept any fetch requests in dev mode
  `;

  // Production: Full stale-while-revalidate offline PWA cache
  const prodScript = `
    const CACHE_NAME = "verifield-capture-v1";
    const PRECACHE_ASSETS = [
      "/capture",
      "/login",
      "/logo-green.png",
      "/logo-black.png",
      "/favicon.ico",
      "/manifest.json"
    ];

    self.addEventListener("install", (event) => {
      event.waitUntil(
        caches
          .open(CACHE_NAME)
          .then((cache) => cache.addAll(PRECACHE_ASSETS))
          .then(() => self.skipWaiting())
      );
    });

    self.addEventListener("activate", (event) => {
      event.waitUntil(
        caches
          .keys()
          .then((cacheNames) => {
            return Promise.all(
              cacheNames.map((cache) => {
                if (cache !== CACHE_NAME) {
                  return caches.delete(cache);
                }
              })
            );
          })
          .then(() => self.clients.claim())
      );
    });

    self.addEventListener("fetch", (event) => {
      const { request } = event;
      const url = new URL(request.url);

      if (request.method !== "GET") return;
      if (!url.protocol.startsWith("http")) return;
      if (url.origin !== self.location.origin) return;

      if (
        url.pathname.includes("/_next/webpack-hmr") ||
        url.pathname.includes("hot-update") ||
        url.pathname.includes("/__nextjs")
      ) {
        return;
      }

      // API Requests - Network First, fallback to cache
      if (url.pathname.startsWith("/api/")) {
        event.respondWith(
          fetch(request)
            .then((response) => {
              if (response && response.status === 200) {
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(request, responseClone);
                });
              }
              return response;
            })
            .catch(() => {
              return caches.match(request).then((cachedResponse) => {
                if (cachedResponse) return cachedResponse;
                return new Response(
                  JSON.stringify({ detail: "Offline: Server unreachable", offline: true }),
                  { status: 503, headers: { "Type": "application/json" } }
                );
              });
            })
        );
        return;
      }

      // Static Assets - Cache First
      if (url.pathname.includes("/_next/static/") || url.pathname.includes("/static/")) {
        event.respondWith(
          caches.match(request).then((cachedResponse) => {
            if (cachedResponse) return cachedResponse;
            return fetch(request).then((response) => {
              if (response && response.status === 200) {
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(request, responseClone);
                });
              }
              return response;
            });
          })
        );
        return;
      }

      // Standalone page HTML - Stale-While-Revalidate
      event.respondWith(
        caches.match(request).then((cachedResponse) => {
          const networkFetch = fetch(request).then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              const responseClone = networkResponse.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseClone);
              });
            }
            return networkResponse;
          });

          if (cachedResponse) {
            networkFetch.catch(() => {});
            return cachedResponse;
          }

          return networkFetch.catch((err) => {
            if (request.headers.get("accept")?.includes("text/html")) {
              return caches.match("/capture").then((fallback) => {
                if (fallback) return fallback;
                throw err;
              });
            }
            throw err;
          });
        })
      );
    });
  `;

  return new NextResponse(isProd ? prodScript : devScript, {
    headers: {
      "Content-Type": "application/javascript",
      "Cache-Control": "no-store, no-cache, must-revalidate",
    },
  });
}
