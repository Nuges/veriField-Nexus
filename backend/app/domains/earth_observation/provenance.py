"""
=============================================================================
VeriField Nexus — Earth Observation Cryptographic Provenance
=============================================================================
Computes deterministic, reproducible SHA-256 digests for:
- Satellite observation scenes (sensor, footprint, timestamps, band checksums)
- Derived spectral layers (source scene hash, formula, version, statistics)
- Baseline snapshot packages (boundary version, observation manifests)
- Spatial anomaly records (source observations, delta metrics)
=============================================================================
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_scene_provenance_hash(
    provider: str,
    scene_id: str,
    acquisition_timestamp: datetime,
    spatial_resolution_m: float,
    processing_level: str,
    bounding_box: Optional[List[float]] = None,
    indices_summary: Optional[Dict[str, float]] = None,
    raw_band_checksums: Optional[Dict[str, str]] = None,
) -> str:
    """
    Computes canonical SHA-256 hash representing the exact provenance of an EO observation.
    """
    canonical_payload = {
        "provider": str(provider),
        "scene_id": str(scene_id),
        "timestamp_iso": acquisition_timestamp.isoformat() if isinstance(acquisition_timestamp, datetime) else str(acquisition_timestamp),
        "spatial_resolution_m": float(spatial_resolution_m),
        "processing_level": str(processing_level),
        "bbox": [round(float(c), 6) for c in (bounding_box or [])],
        "indices": {k: round(float(v), 5) for k, v in sorted((indices_summary or {}).items())},
        "bands": {k: str(v) for k, v in sorted((raw_band_checksums or {}).items())},
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_derived_layer_provenance_hash(
    source_observation_hash: str,
    layer_type: str,
    formula_identifier: str,
    processor_version: str,
    statistics: Optional[Dict[str, float]] = None,
    aoi_id: Optional[str] = None,
) -> str:
    """
    Computes canonical SHA-256 digest linking a derived spectral layer directly
    to its parent observation scene and processing version.
    """
    canonical_payload = {
        "source_observation_hash": str(source_observation_hash),
        "layer_type": str(layer_type),
        "formula_identifier": str(formula_identifier),
        "processor_version": str(processor_version),
        "statistics": {k: round(float(v), 5) for k, v in sorted((statistics or {}).items())},
        "aoi_id": str(aoi_id or ""),
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_baseline_package_hash(
    project_id: str,
    boundary_version_number: int,
    observation_provenance_hashes: List[str],
    evidence_hashes: List[str],
    soil_sample_hashes: List[str],
    baseline_date_iso: str,
) -> str:
    """
    Computes an immutable manifest digest for a locked project baseline snapshot.
    """
    canonical_payload = {
        "project_id": str(project_id),
        "boundary_version": int(boundary_version_number),
        "observation_hashes": sorted(observation_provenance_hashes),
        "evidence_hashes": sorted(evidence_hashes),
        "soil_sample_hashes": sorted(soil_sample_hashes),
        "baseline_date": str(baseline_date_iso),
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
