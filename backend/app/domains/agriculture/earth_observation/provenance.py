"""
=============================================================================
VeriField Nexus — Earth Observation Cryptographic Provenance
=============================================================================
Generates reproducible SHA-256 digests for satellite observations:
- Links scene ID, sensor telemetry, acquisition timestamp, footprint,
  and processing steps.
- Assures immutable audit trail for verification dossiers and ledger entries.
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
    bounding_box: List[float],
    indices_summary: Optional[Dict[str, float]] = None,
    raw_band_checksums: Optional[Dict[str, str]] = None,
) -> str:
    """
    Computes a canonical SHA-256 hash representing the exact provenance of an EO observation.
    """
    canonical_payload = {
        "provider": str(provider),
        "scene_id": str(scene_id),
        "timestamp_iso": acquisition_timestamp.isoformat(),
        "spatial_resolution_m": float(spatial_resolution_m),
        "processing_level": str(processing_level),
        "bbox": [round(float(c), 6) for c in bounding_box] if bounding_box else [],
        "indices": {k: round(float(v), 5) for k, v in sorted((indices_summary or {}).items())},
        "bands": {k: str(v) for k, v in sorted((raw_band_checksums or {}).items())},
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
