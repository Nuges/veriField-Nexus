// =============================================================================
// VeriField Nexus — Sector Guidance Overlays
// =============================================================================
// Methodological and sector-specific terminology overlays.
// Prevents cross-contamination of sector concepts.
// =============================================================================

import { canonicalSectorCode } from "../moduleRegistry";
import { SectorGuidanceOverlay } from "./types";

export const SECTOR_OVERLAYS: Record<string, SectorGuidanceOverlay> = {
  cookstoves: {
    sectorName: "Clean Cookstoves",
    protocol: "AMS-II.G / VMR0006",
    contextTerminology: "cookstove deployments, thermal usage logs, and non-renewable biomass displacement",
    recommendationOverlay: {
      "/dashboard": "Clean cookstove project records and usage telemetry synchronized in database. Thermal usage and fuel savings active.",
      "/dashboard/projects": "Active cookstove project properties registered under licensed tenant organization. Spatial bounds validated.",
      "/dashboard/methodologies": "Methodology parameters locked. AST equations verified against AMS-II.G / Gold Standard protocols.",
      "/dashboard/assets": "Registered cookstove assets active in database. IoT sensor telemetry signals synchronized with 0 hardware errors.",
      "/dashboard/operations": "Field inspection queue active. Cookstove survey logs, GPS coordinates, and thermal evidence synchronized.",
      "/dashboard/monitoring": "Cookstove IoT telemetry streaming is nominal. Telemetry ingestion rate is stable across active assets.",
      "/dashboard/verifications": "Cookstove usage batch verified against thermal log datasets with cryptographic SHA-256 attestation."
    },
    suggestedQueriesOverlay: {
      "/dashboard/monitoring": [
        "Which cookstove units have missing thermal telemetry?",
        "Are there stove deployments with non-reporting sensors?",
        "What is the daily average stove usage time?",
        "Are there thermal anomalies detected in current batch?"
      ],
      "/dashboard/projects": [
        "Which cookstove projects require baseline survey completion?",
        "What are the target household deployment numbers?",
        "Which projects are pending methodology validation?",
        "Are there spatial boundary overlaps between projects?"
      ],
      "/dashboard/sensors": [
        "Which cookstove temperature loggers are offline?",
        "Are battery levels sufficient on deployed dataloggers?",
        "Which units have irregular transmission intervals?",
        "Are there unassigned IoT loggers in inventory?"
      ]
    }
  },

  hybrid_energy: {
    sectorName: "Hybrid Energy & Mini-Grids",
    protocol: "ACM0002 / AMS-I.F",
    contextTerminology: "solar generation arrays, smart inverters, meter telemetry, and grid emission factors",
    recommendationOverlay: {
      "/dashboard": "Solar and hybrid energy telemetry synchronized in database. Real-time generation, inverter power, and grid emissions offset active.",
      "/dashboard/projects": "Active solar generation project properties registered under licensed tenant organization. Generation arrays validated.",
      "/dashboard/methodologies": "Methodology parameters locked. Grid emission displacement equations verified against ACM0002 / AMS-I.F protocols.",
      "/dashboard/assets": "Registered solar and hybrid generation assets active in database. Inverter telemetry signals synchronized with 0 hardware errors.",
      "/dashboard/operations": "Generation telemetry stream active. Inverter output feeds and solar generation records synchronized.",
      "/dashboard/monitoring": "Inverter IoT gateway latency is nominal. Power output and generation telemetry stream is stable across active assets.",
      "/dashboard/verifications": "Generation batch verified against smart meter logs with cryptographic SHA-256 attestation."
    },
    suggestedQueriesOverlay: {
      "/dashboard/monitoring": [
        "Which mini-grid inverters show communication loss?",
        "Are there generation drops below baseline projections?",
        "What is the cumulative kilowatt-hour generation today?",
        "Which smart meters have reporting latency over 1 hour?"
      ],
      "/dashboard/projects": [
        "What is the commissioned generation capacity per project?",
        "Which mini-grid projects are pending grid interconnection review?",
        "Are baseline diesel displacement calculations up to date?",
        "Which sites require inverter firmware updates?"
      ],
      "/dashboard/sensors": [
        "Which smart meters are currently reporting offline?",
        "Are solar irradiance sensors operating within calibration limits?",
        "Which power gateways have high ping latency?",
        "Are there unassigned energy monitoring meters?"
      ]
    }
  },

  biochar: {
    sectorName: "Biochar & Carbon Removal",
    protocol: "VM0042 / EBC",
    contextTerminology: "pyrolysis kilns, feedstock characterization, carbon permanence assays, and batch production logs",
    recommendationOverlay: {
      "/dashboard": "Biochar production batches and pyrolysis logs synchronized in database. Permanent carbon removal active.",
      "/dashboard/projects": "Active biochar production properties registered under licensed tenant organization. Feedstock sources validated.",
      "/dashboard/methodologies": "Methodology parameters locked. Carbon stability ratios verified against VM0042 / EBC protocols.",
      "/dashboard/assets": "Registered biochar pyrolyzers and processing assets active. Thermal sensor telemetry synchronized with 0 hardware errors.",
      "/dashboard/operations": "Pyrolysis batch queue active. Feedstock logs, kiln temperature logs, and carbonization evidence synchronized.",
      "/dashboard/monitoring": "Pyrolyzer IoT gateway latency is nominal. Pyrolysis temperature stream is stable across active assets.",
      "/dashboard/verifications": "Biochar batch verified against laboratory carbon characterization assays with SHA-256 attestation."
    },
    suggestedQueriesOverlay: {
      "/dashboard/monitoring": [
        "Which pyrolyzers failed minimum temperature threshold (600°C)?",
        "Are there biomass feedstock batches pending lab assay results?",
        "What is the current monthly sequestered carbon dioxide equivalent?",
        "Are thermocouple temperature streams continuous?"
      ],
      "/dashboard/projects": [
        "Which biochar production facilities have open compliance items?",
        "What are the certified feedstock sourcing boundaries?",
        "Which batches are pending permanence certification?",
        "Are lab assay certificates linked to recent batches?"
      ],
      "/dashboard/sensors": [
        "Which pyrolyzer temperature sensors are offline?",
        "Are scale weight sensors calibrated for batch weighing?",
        "Which telemetry loggers show clock drift?",
        "Are there unlinked temperature probes?"
      ]
    }
  },

  ev_mobility: {
    sectorName: "Electric Vehicles & Mobility",
    protocol: "AMS-III.C",
    contextTerminology: "EV charging stations, fleet telematics, kilowatt-hour charging sessions, and fossil fuel displacement",
    recommendationOverlay: {
      "/dashboard": "EV charging telemetry and fleet session records synchronized in database. Fossil fuel displacement active.",
      "/dashboard/projects": "Active EV mobility project properties registered under licensed tenant organization. Route boundaries validated.",
      "/dashboard/methodologies": "Methodology parameters locked. Fossil fuel displacement models verified against AMS-III.C protocol.",
      "/dashboard/assets": "Registered EV charging stations and fleet telemetry active. Charging session events synchronized with 0 hardware errors.",
      "/dashboard/operations": "Fleet evidence queue active. EV charging sessions, odometer logs, and battery telemetry synchronized.",
      "/dashboard/monitoring": "EV telemetry gateway latency is nominal. Charging load and session stream is stable across active assets.",
      "/dashboard/verifications": "EV charging batch verified against telemetry records with SHA-256 cryptographic attestation match."
    },
    suggestedQueriesOverlay: {
      "/dashboard/monitoring": [
        "Which EV charging stations show network disconnects?",
        "Are there charging sessions with incomplete energy data?",
        "What is total fossil fuel displacement achieved this month?",
        "Which vehicles show abnormal battery degradation curves?"
      ],
      "/dashboard/projects": [
        "Which fleet charging hubs are operational?",
        "What is the validated fleet baseline fuel consumption?",
        "Are vehicle route compliance records complete?",
        "Which charging assets are pending commissioning?"
      ],
      "/dashboard/sensors": [
        "Which charger metering units are non-reporting?",
        "Are vehicle telematics GPS trackers online?",
        "Which charging points have communication faults?",
        "Are there unassigned vehicle telematics dongles?"
      ]
    }
  }
};

export const NEUTRAL_OVERLAY: SectorGuidanceOverlay = {
  sectorName: "Digital MRV Platform",
  protocol: "VeriField CIOS Standard",
  contextTerminology: "operational telemetry, reporting continuity, and verified activity records",
  recommendationOverlay: {},
  suggestedQueriesOverlay: {}
};

export function getSectorOverlay(sector?: string | null): SectorGuidanceOverlay {
  if (!sector) return NEUTRAL_OVERLAY;
  const canonical = canonicalSectorCode(sector);
  return SECTOR_OVERLAYS[canonical] || NEUTRAL_OVERLAY;
}
