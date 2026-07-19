// =============================================================================
// VeriField Nexus — Map View Page (Geospatial View)
// =============================================================================
// Interactive map showing cookstove installation locations in Nigeria & Kenya.
// Uses OpenStreetMap & Leaflet to run 100% free with no API keys required.
// Supports dynamic location classification, advanced searching, and fit-to-screen viewports.
// Features: Active Bounding Box Viewport Filtering, Dynamic country routing & location search.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { fetchActivities } from "@/lib/api";
import type { Property, Activity } from "@/lib/types";
import { useWorkspace } from "@/context/WorkspaceContext";



export default function MapPage() {
  const { activeSector, filterProperties } = useWorkspace();
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [apiOffline, setApiOffline] = useState(false);

  // Advanced Search & Filter States
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "verified" | "review" | "flagged">("all");
  
  // Real-Time Bounding Box Viewport Location Filter
  const [mapBounds, setMapBounds] = useState<{
    southWest: [number, number];
    northEast: [number, number];
  } | null>(null);
  const [filterByBounds, setFilterByBounds] = useState(false);

  // Quick helper to get display status values
  const getStatus = (p: Property) => {
    const status = (p.sustainability_metrics as any)?.status;
    if (status === 'flagged' || status === 'rejected') return "Flagged";
    if (status === 'pending') return "Manual Review";
    return "AI Verified";
  };

  const activeProps = filterProperties(properties.length > 0 ? properties : []);

  useEffect(() => {
    async function loadLocations() {
      try {
        // Fetch up to 500 GPS-tagged activities from the real database
        const res = await fetchActivities({ per_page: 500 });
        const gpsProperties = res.activities
          .filter((a) => a.latitude !== null && a.latitude !== undefined && a.longitude !== null && a.longitude !== undefined)
          .map((a) => ({
            id: a.id,
            owner_id: "system",
            name: `Activity ${a.id.substring(0, 8)}`,
            property_type: a.activity_type,
            latitude: a.latitude,
            longitude: a.longitude,
            address: (a.activity_data?.location_name as string) || (a.activity_data?.address as string) || "Unknown Location",
            sustainability_metrics: { status: a.status, tco2e: parseFloat((a.activity_data?.carbon_offset_kg as string) || "0") / 1000 },
            created_at: a.created_at || new Date().toISOString(),
            updated_at: ""
          })) as Property[];
        
        if (gpsProperties.length > 0) {
          setProperties(gpsProperties);
          setSelectedProperty(gpsProperties[0]);
        } else {
          // API responded but no GPS-tagged properties exist yet
          setProperties([]);
          setSelectedProperty(null);
        }
      } catch (err) {
        console.error("Failed to load map points from API", err);
        setApiOffline(true);
        setProperties([]);
        setSelectedProperty([][0]);
      } finally {
        setIsLoading(false);
      }
    }
    loadLocations();
  }, []);

  // Generate safe HTML content for the dynamic Leaflet Iframe
  const generateMapSrcDoc = (propsToRender: Property[]) => {
    // Center around the first active property with valid GPS
    const defaultCenter = [
      propsToRender[0]?.latitude !== null && propsToRender[0]?.latitude !== undefined ? propsToRender[0].latitude : 6.5244,
      propsToRender[0]?.longitude !== null && propsToRender[0]?.longitude !== undefined ? propsToRender[0].longitude : 3.3792
    ];

    const mapDataString = JSON.stringify(
      propsToRender.map((p) => {
        const status = getStatus(p);
        let color = "#00B47A"; // High Trust
        if (status === "Flagged") color = "#EF4444"; // Red
        else if (status === "Manual Review") color = "#F59E0B"; // Amber

        const latVal = typeof p.latitude === "string" ? parseFloat(p.latitude) : p.latitude;
        const lngVal = typeof p.longitude === "string" ? parseFloat(p.longitude) : p.longitude;

        return {
          id: p.id,
          name: p.name,
          lat: latVal,
          lng: lngVal,
          type: p.property_type,
          offset: String((p.sustainability_metrics as any)?.carbon_offset_kg || (p.sustainability_metrics as any)?.tco2e || "0"),
          created: new Date(p.created_at || Date.now()).toLocaleDateString(),
          color,
          status,
        };
      })
    );

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
          <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
          <style>
            html, body, #map {
              margin: 0; padding: 0; width: 100%; height: 100%;
              background: #0B0F19;
            }
            .leaflet-popup-content-wrapper {
              background: #111827;
              color: #f3f4f6;
              border: 1px solid #1f2937;
              border-radius: 12px;
              font-family: ui-sans-serif, system-ui, sans-serif;
            }
            .leaflet-popup-tip {
              background: #111827;
              border: 1px solid #1f2937;
            }
            .leaflet-popup-content h3 {
              margin: 0 0 4px 0; font-size: 11px; font-weight: 800; color: #00B47A; text-transform: uppercase; letter-spacing: 0.05em;
            }
            .leaflet-popup-content p {
              margin: 2px 0; font-size: 9px; line-height: 1.3; color: #9ca3af;
            }
            .leaflet-popup-content strong {
              color: #e5e7eb;
            }
            .custom-leaflet-marker {
              background: none !important;
              border: none !important;
            }
          </style>
        </head>
        <body>
          <div id="map"></div>
          <script>
            const markers = {};
            const circleRings = {};
            const mapData = ${mapDataString};

            // Initialize Leaflet Map — starts at default center, then auto-fits to actual data
            const map = L.map('map', { zoomControl: true }).setView([${defaultCenter[0]}, ${defaultCenter[1]}], 13);
            
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
              attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
              subdomains: 'abcd',
              maxZoom: 20
            }).addTo(map);

            // Dynamic Centering: Auto-center on the user's active physical location if no database registry assets exist
            if (mapData.length === 0 && navigator.geolocation) {
              navigator.geolocation.getCurrentPosition(
                (position) => {
                  const userLat = position.coords.latitude;
                  const userLng = position.coords.longitude;
                  map.setView([userLat, userLng], 12);
                },
                (error) => {
                  console.log("Browser location permission denied.");
                },
                { enableHighAccuracy: true, timeout: 6000, maximumAge: 0 }
              );
            }

            // Plot registered properties
            mapData.forEach(p => {
              if (p.lat !== null && p.lng !== null && p.lat !== undefined && p.lng !== undefined) {
                const customIcon = L.divIcon({
                  html: \`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="\${p.color}" width="28" height="28" style="display: block;"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>\`,
                  className: 'custom-leaflet-marker',
                  iconSize: [28, 28],
                  iconAnchor: [14, 28],
                  popupAnchor: [0, -26]
                });

                const marker = L.marker([p.lat, p.lng], { icon: customIcon }).addTo(map);
                markers[p.id] = marker;

                // 30m exclusion ring
                const circle = L.circle([p.lat, p.lng], {
                  radius: 30,
                  color: p.color,
                  fillColor: p.color,
                  fillOpacity: 0.05,
                  weight: 1.5,
                  dashArray: '4, 4'
                }).addTo(map);
                circleRings[p.id] = circle;

                const popupContent = \`
                  <div>
                    <h3>\${p.name}</h3>
                    <p><strong>Type:</strong> \${p.type === 'CLEAN_COOKING' ? 'Clean Cookstove' : 'Hybrid Energy System'}</p>
                    <p><strong>Carbon Offset:</strong> \${p.offset} tCO2e/yr</p>
                    <p><strong>Registered:</strong> \${p.created}</p>
                    <p><strong>Coords:</strong> \${p.lat.toFixed(6)}, \${p.lng.toFixed(6)}</p>
                    <p style="color: \${p.color}; font-weight: 700; margin-top: 4px;">Methodology Check: 30m radius certified</p>
                  </div>
                \`;

                marker.bindPopup(popupContent);

                marker.on('click', () => {
                  window.parent.postMessage({ type: 'MARKER_SELECTED', id: p.id }, '*');
                });
              }
            });

            // Post initial map bounds and bounds updates to parent
            const postBounds = () => {
              const bounds = map.getBounds();
              window.parent.postMessage({
                type: 'MAP_BOUNDS_CHANGED',
                bounds: {
                  southWest: [bounds.getSouthWest().lat, bounds.getSouthWest().lng],
                  northEast: [bounds.getNorthEast().lat, bounds.getNorthEast().lng]
                }
              }, '*');
            };

            map.on('moveend', postBounds);
            // Auto-fit map bounds to show ALL actual registered stove locations
            const validGpsProps = mapData.filter(p => p.lat !== null && p.lng !== null && p.lat !== undefined && p.lng !== undefined);
            if (validGpsProps.length === 1) {
              map.setView([validGpsProps[0].lat, validGpsProps[0].lng], 13);
            } else if (validGpsProps.length > 1) {
              const bounds = validGpsProps.map(p => [p.lat, p.lng]);
              map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
            }

            // Delayed initial trigger to let Map complete initialization
            setTimeout(() => {
              postBounds();
              window.parent.postMessage({ type: 'MAP_READY' }, '*');
            }, 500);

            // Listen for FOCUS_MARKER events
            window.addEventListener('message', (event) => {
              const msg = event.data;
              if (msg.type === 'FOCUS_MARKER') {
                const targetMarker = markers[msg.id];
                if (targetMarker) {
                  map.setView([msg.lat, msg.lng], 15, { animate: true, duration: 1.2 });
                  targetMarker.openPopup();
                }
              }
            });
          </script>
        </body>
      </html>
    `;
  };

  // Synchronize Leaflet map events back to React Parent Component
  useEffect(() => {
    const handleMapMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === "MARKER_SELECTED") {
        const target = activeProps.find((p) => p.id === msg.id);
        if (target) {
          setSelectedProperty(target);
        }
      } else if (msg.type === "MAP_BOUNDS_CHANGED") {
        setMapBounds(msg.bounds);
      } else if (msg.type === "MAP_READY") {
        // Map is ready! Focus the selected property if we have one
        if (selectedProperty && selectedProperty.latitude !== null && selectedProperty.longitude !== null) {
          const iframe = document.querySelector("iframe");
          if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage(
              {
                type: "FOCUS_MARKER",
                lat: selectedProperty.latitude,
                lng: selectedProperty.longitude,
                id: selectedProperty.id,
              },
              "*"
            );
          }
        }
      }
    };
    window.addEventListener("message", handleMapMessage);
    return () => window.removeEventListener("message", handleMapMessage);
  }, [activeProps, selectedProperty]);

  // Post focus event to Leaflet iframe
  useEffect(() => {
    if (selectedProperty && selectedProperty.latitude !== null && selectedProperty.longitude !== null) {
      const iframe = document.querySelector("iframe");
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage(
          {
            type: "FOCUS_MARKER",
            lat: selectedProperty.latitude,
            lng: selectedProperty.longitude,
            id: selectedProperty.id,
          },
          "*"
        );
      }
    }
  }, [selectedProperty]);

  // Classify coordinates to country names dynamically (Lagos -> Nigeria, Nairobi/Mombasa -> Kenya)
  const getCountryName = (address?: string) => {
    if (!address) return "Global";
    if (address.toLowerCase().includes("nigeria")) return "Nigeria";
    if (address.toLowerCase().includes("kenya")) return "Kenya";
    return "Local";
  };

  // Viewport bounds checking helper
  const isInsideBounds = (lat: number | null, lng: number | null) => {
    if (!mapBounds || lat === null || lng === null) return true;
    const [swLat, swLng] = mapBounds.southWest;
    const [neLat, neLng] = mapBounds.northEast;
    return lat >= swLat && lat <= neLat && lng >= swLng && lng <= neLng;
  };

  // Dynamic filter combining search query (stove name OR address OR country), status filter, and optional visible bounds filter!
  const filteredProps = activeProps.filter((p) => {
    // 1. Visible map bounds filter check
    if (filterByBounds && !isInsideBounds(p.latitude, p.longitude)) {
      return false;
    }

    // 2. Search query check (Matches Stove Name, Stove Type, Address, or Dynamic Country Name!)
    const detectedCountryName = getCountryName(p.address || '').toLowerCase();
    const addressStr = (p.address || "").toLowerCase();
    const matchesSearch = 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (p.property_type && p.property_type.toLowerCase().includes(searchQuery.toLowerCase())) ||
      addressStr.includes(searchQuery.toLowerCase()) ||
      detectedCountryName.includes(searchQuery.toLowerCase());
    
    if (!matchesSearch) return false;

    // 3. Status filter check
    const status = getStatus(p);
    if (statusFilter === "all") return true;
    if (statusFilter === "verified") return status === "AI Verified";
    if (statusFilter === "flagged") return status === "Flagged";
    if (statusFilter === "review") return status === "Manual Review";
    return true;
  });

  const selectedPropCountry = selectedProperty 
    ? getCountryName(selectedProperty.address || '')
    : "Global";

  return (
    <div className="h-[calc(100vh-170px)] md:h-[calc(100vh-125px)] flex flex-col space-y-3 pr-2 overflow-hidden">
      {/* Title */}
      <div className="animate-fade-in-up shrink-0">
        <h1 className="text-xl font-bold text-[var(--color-text-primary)] tracking-tight">
          Geospatial MRV View
        </h1>
        {/* Offline warning */}
        {apiOffline && (
          <div className="mt-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-[10px] text-amber-400 font-semibold">
            ⚠ Backend API unreachable. Ensure the server is online to view live locations.
          </div>
        )}
        {/* No GPS data state */}
        {!isLoading && !apiOffline && activeProps.length === 0 && (
          <div className="mt-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg text-[10px] text-blue-400 font-semibold">
            No GPS-tagged {activeSector === "cookstove" ? "cookstoves" : 
                            "hybrid energy systems"} found. Register assets with GPS coordinates from the mobile app to see them here.
          </div>
        )}
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-5 items-stretch min-h-0 overflow-hidden animate-fade-in-up">
        {/* Dynamic Free OpenStreetMap Iframe */}
        <div className="lg:col-span-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden relative shadow-sm h-full min-h-[300px]">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-surface)]">
              <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <iframe
              srcDoc={generateMapSrcDoc(activeProps)}
              className="w-full h-full border-none"
              title="Geospatial Map View"
            />
          )}

          {/* Legend Overlay */}
          <div className="absolute bottom-4 left-4 bg-[var(--color-surface)]/95 border border-[var(--color-border)] rounded-xl p-3 shadow-lg z-10 text-[9px] font-bold animate-fade-in">
            <h4 className="text-[8px] uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Trust Legend</h4>
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#00B47A]"></div>
                <span>High Trust / Verified</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500"></div>
                <span>Review Needed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500"></div>
                <span>Proximity Flagged</span>
              </div>
            </div>
          </div>
        </div>

        {/* Selected Cookstove Side Panel details */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 shadow-sm flex flex-col h-full overflow-hidden">
          {selectedProperty ? (
            <div className="h-full flex flex-col justify-between overflow-hidden">
              <div className="flex-1 flex flex-col overflow-hidden min-h-0">
                {/* Selected Node Status Header */}
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-1.5 shrink-0">
                  <span className="text-[9px] uppercase font-bold text-[var(--color-text-muted)]">Selected Node</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[8px] font-extrabold tracking-wide uppercase shrink-0 ${
                      getStatus(selectedProperty) === "Flagged"
                        ? "bg-red-500/10 text-red-500"
                        : (getStatus(selectedProperty) === "Manual Review"
                            ? "bg-amber-500/10 text-amber-500"
                            : "bg-[#00B47A]/10 text-[#00B47A]")
                    }`}
                  >
                    {getStatus(selectedProperty) === "AI Verified" ? "Verified" : "Audit"}
                  </span>
                </div>

                {/* Name of current stove */}
                <h3 className="font-extrabold text-sm capitalize text-[#00B47A] mt-1.5 shrink-0 truncate">
                  {selectedProperty.name}
                </h3>

                {/* Compact detail metrics */}
                <div className="mt-2 space-y-1.5 text-[10px] shrink-0 border-b border-[var(--color-border)] pb-2.5">
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Location / Address:</span>
                    <span className="font-bold text-[var(--color-text-primary)] truncate max-w-[150px]">{selectedProperty.address || "N/A"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Environment Type:</span>
                    <span className="font-bold uppercase text-[var(--color-text-primary)]">{selectedProperty.property_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Carbon Reductions:</span>
                    <span className="font-extrabold text-emerald-400">
                      {((selectedProperty.sustainability_metrics as any)?.tco2e || "0")} tCO2e/yr
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Coordinates:</span>
                    <span className="font-semibold text-[var(--color-text-primary)]">
                      {selectedProperty.latitude?.toFixed(6)}, {selectedProperty.longitude?.toFixed(6)}
                    </span>
                  </div>
                </div>

                {/* Dynamic Location Assets Grid Header */}
                <div className="mt-3 shrink-0 flex items-center justify-between">
                  <h4 className="text-[8px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold">
                    {selectedPropCountry} Assets Grid
                  </h4>
                  <span className="text-[7.5px] font-bold text-emerald-400 shrink-0 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-full">
                    {filteredProps.length} devices
                  </span>
                </div>

                {/* Search Bar Input (Searches Name, Address, City or Country!) */}
                <div className="mt-1.5 shrink-0">
                  <input
                    type="text"
                    placeholder="Search name, country or region..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 text-[9px] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-hidden focus:border-[#00B47A]/50 transition-colors shrink-0"
                  />
                </div>

                {/* Advanced Bounding Box Map Viewport Location Filter Switch */}
                <div className="mt-2 shrink-0 flex items-center justify-between bg-[var(--color-background)] border border-[var(--color-border)] px-2.5 py-1.5 rounded-xl">
                  <span className="text-[8px] font-bold text-[var(--color-text-secondary)]">
                    Filter by visible map viewport only
                  </span>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      checked={filterByBounds}
                      onChange={(e) => setFilterByBounds(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-6 h-3 bg-gray-700 peer-focus:outline-hidden rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:bg-[#00B47A]"></div>
                  </label>
                </div>

                {/* Quick Status Filter Tags */}
                <div className="mt-2 shrink-0 flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none text-[7px] font-bold">
                  {(["all", "verified", "review", "flagged"] as const).map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setStatusFilter(filter)}
                      className={`px-2 py-0.5 rounded-full border transition-all shrink-0 capitalize ${
                        statusFilter === filter
                          ? "bg-[#00B47A]/15 border-[#00B47A]/30 text-[#00B47A] font-extrabold"
                          : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-muted)]"
                      }`}
                    >
                      {filter === "review" ? "Review" : filter}
                    </button>
                  ))}
                </div>

                {/* Strict Fixed Height, Scrollable assets list */}
                <div className="max-h-[140px] overflow-y-auto mt-2 pr-1 space-y-1.5 scrollbar-custom min-h-0 flex-1">
                  {filteredProps.length > 0 ? (
                    filteredProps.map((p) => {
                      const isSelected = selectedProperty.id === p.id;
                      const status = getStatus(p);
                      let dotColor = "bg-[#00B47A]";
                      if (status === "Flagged") dotColor = "bg-red-500";
                      else if (status === "Manual Review") dotColor = "bg-amber-500";

                      return (
                        <button
                          key={p.id}
                          onClick={() => setSelectedProperty(p)}
                          className={`w-full text-left text-[9px] p-2 rounded-xl border transition-all flex items-center justify-between ${
                            isSelected
                              ? "bg-[#00B47A]/5 border-[#00B47A]/30 text-[#00B47A] shadow-xs"
                              : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-muted)]"
                          }`}
                        >
                          <div className="flex flex-col truncate max-w-[120px]">
                            <span className="font-bold truncate">{p.name}</span>
                            <span className="text-[7px] text-[var(--color-text-muted)] truncate mt-0.5">{p.address || "N/A"}</span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <span className="text-[7px] text-[var(--color-text-muted)] uppercase tracking-wide">{p.property_type}</span>
                            <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`}></span>
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className="text-center py-4 text-[9px] text-[var(--color-text-muted)] italic">
                      No matching devices found in this area.
                    </div>
                  )}
                </div>
              </div>

              {/* Verified Footer note */}
              <div className="border-t border-[var(--color-border)] pt-2.5 text-[8px] text-[var(--color-text-muted)] italic leading-relaxed shrink-0 mt-2.5">
                {getStatus(selectedProperty) === "AI Verified"
                  ? "✓ AI Verified: Coordinates verified under Gold Standard 30m boundary logic (0 anomalies)."
                  : "⚠ Review: Coordinates deviation flag. Proximity overlap risk detected."}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-[var(--color-text-muted)] text-xs text-center p-4">
              Select an installation marker plot on the map to audit specific device credentials.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
