"""
=============================================================================
VeriField Nexus — STAC (SpatioTemporal Asset Catalog) Discovery Client
=============================================================================
Interacts with authoritative STAC 1.0.0 public endpoints (e.g. AWS Element84
Earth Search) to discover real satellite scenes and verify Cloud-Optimized
GeoTIFF (COG) raster asset streaming via HTTP Range requests.

Supports:
- Sentinel-2 L2A ('sentinel-2-l2a')
- Sentinel-1 GRD ('sentinel-1-grd')
- Landsat Collection 2 Level 2 ('landsat-c2-l2')
=============================================================================
"""

import ipaddress
import json
import logging
import socket
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.domains.earth_observation.models import (
    EOObservationType,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.base import RawSceneMetadata

logger = logging.getLogger(__name__)

ELEMENT84_STAC_ENDPOINT = "https://earth-search.aws.element84.com/v1"

# ─── SSRF Protection Constants ───

# Allowlisted hostnames for COG asset verification (public satellite data archives)
ALLOWED_COG_HOSTS = frozenset({
    "sentinel-cogs.s3.us-west-2.amazonaws.com",
    "sentinel-s2-l2a-cogs.s3.amazonaws.com",
    "landsatlook.usgs.gov",
    "data.lpdaac.earthdatacloud.nasa.gov",
    "e84-earth-search-cogs.s3.us-west-2.amazonaws.com",
    "earth-search.aws.element84.com",
    "browser.dataspace.copernicus.eu",
    "api.planet.com",
})


def _is_private_ip(ip_str: str) -> bool:
    """Returns True if the IP address is private, loopback, link-local, or cloud metadata."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            # AWS/GCP/Azure metadata endpoint
            or ip_str in ("169.254.169.254", "metadata.google.internal")
        )
    except ValueError:
        return True  # If we can't parse it, reject it


def validate_cog_url(url: str, enforce_allowlist: bool = True) -> str:
    """
    Validates a URL for SSRF safety before making an outbound request.

    Enforces:
    - HTTPS scheme only (HTTP allowed only in explicit test mode)
    - Hostname allowlist for known satellite data providers
    - DNS resolution check to reject hostnames resolving to private IPs
    - Rejects localhost, loopback, private ranges, link-local, cloud metadata
    - Rejects file://, ftp://, gopher://, and other non-HTTP schemes

    Returns the validated URL string.
    Raises ValueError on any violation.
    """
    parsed = urlparse(url)

    # 1. Scheme validation
    if parsed.scheme not in ("https", "http"):
        raise ValueError(
            f"SSRF_BLOCKED: Scheme '{parsed.scheme}' is not allowed. Only HTTPS is permitted."
        )

    if parsed.scheme == "http" and enforce_allowlist:
        raise ValueError(
            "SSRF_BLOCKED: HTTP scheme is not allowed for COG verification. Use HTTPS."
        )

    # 2. Hostname presence
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("SSRF_BLOCKED: URL has no hostname.")

    hostname_lower = hostname.lower()

    # 3. Reject obviously dangerous hostnames
    if hostname_lower in (
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "[::1]",
        "metadata.google.internal",
    ):
        raise ValueError(
            f"SSRF_BLOCKED: Hostname '{hostname}' resolves to a local/private address."
        )

    # 4. Hostname allowlist check
    if enforce_allowlist and hostname_lower not in ALLOWED_COG_HOSTS:
        raise ValueError(
            f"SSRF_BLOCKED: Hostname '{hostname}' is not in the allowed COG host list. "
            f"Allowed hosts: {', '.join(sorted(ALLOWED_COG_HOSTS))}"
        )

    # 5. DNS resolution check — prevent DNS rebinding to private IPs
    try:
        resolved_ips = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
        for family, socktype, proto, canonname, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                raise ValueError(
                    f"SSRF_BLOCKED: Hostname '{hostname}' resolves to private/internal IP '{ip_str}'."
                )
    except socket.gaierror:
        raise ValueError(
            f"SSRF_BLOCKED: Cannot resolve hostname '{hostname}'."
        )

    return url


class SSRFRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Prevents SSRF via HTTP redirects by strictly validating every redirect
    target before the request is followed.
    Enforces maximum redirect depth and rejects targets resolving to private,
    loopback, link-local, cloud metadata, or unapproved hostnames.
    """

    def __init__(self, enforce_allowlist: bool = True, max_redirects: int = 3):
        super().__init__()
        self.enforce_allowlist = enforce_allowlist
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise ValueError(f"SSRF_BLOCKED: Max redirect depth ({self.max_redirects}) exceeded.")
        # Validate the redirect destination URL BEFORE following
        validate_cog_url(newurl, enforce_allowlist=self.enforce_allowlist)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _sanitize_url_for_log(url: str) -> str:
    """Strips query parameters from URLs to prevent logging signed tokens or credentials."""
    parsed = urlparse(url)
    # Return scheme://hostname/path without query string or fragment
    sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return sanitized


class STACClient:
    """
    Client for querying STAC 1.0.0 API endpoints and validating COG raster assets.
    """

    def __init__(self, endpoint_url: str = ELEMENT84_STAC_ENDPOINT, timeout_seconds: int = 35):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_items(
        self,
        collections: List[str],
        bbox: Optional[List[float]] = None,
        intersects: Optional[Dict[str, Any]] = None,
        datetime_range: Optional[str] = None,
        max_cloud_cover: Optional[float] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Executes a STAC /search POST query against the configured catalog endpoint.
        Returns the raw GeoJSON Feature items.
        """
        search_url = f"{self.endpoint_url}/search"
        payload: Dict[str, Any] = {
            "collections": collections,
            "limit": limit,
        }

        if bbox and len(bbox) == 4:
            payload["bbox"] = bbox
        elif intersects:
            payload["intersects"] = intersects

        if datetime_range:
            payload["datetime"] = datetime_range

        if max_cloud_cover is not None and "sentinel-1-grd" not in collections:
            payload["query"] = {"eo:cloud_cover": {"lte": max_cloud_cover}}

        data_bytes = json.dumps(payload).encode("utf-8")
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            req = urllib.request.Request(
                search_url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "VeriField-Nexus-STAC/1.0",
                    "Accept": "application/geo+json, application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if resp.status != 200:
                        logger.warning("STAC search returned HTTP status %s", resp.status)
                        return []
                    body = json.loads(resp.read().decode("utf-8"))
                    return body.get("features", [])
            except Exception as exc:
                if attempt < max_attempts:
                    logger.warning("STAC search attempt %s failed against %s (%s). Retrying...", attempt, search_url, exc)
                    import time
                    time.sleep(1.0)
                else:
                    logger.warning("STAC search query failed against %s after %s attempts: %s", search_url, max_attempts, exc)
                    return []

    def verify_asset_range_access(
        self,
        asset_url: str,
        byte_range: str = "bytes=0-1023",
        enforce_allowlist: bool = True,
    ) -> Dict[str, Any]:
        """
        Validates Cloud-Optimized GeoTIFF (COG) accessibility using HTTP Range requests.
        Verifies HTTP 206 Partial Content response and GeoTIFF header magic bytes.

        SSRF Protection:
        - Validates URL scheme (HTTPS only in production)
        - Validates hostname against allowlist of known satellite data providers
        - Resolves DNS and rejects private/loopback/link-local/metadata IPs
        - Limits response read to 2048 bytes
        - Sanitizes URLs in response (strips query params that may contain tokens)
        """
        # ─── SSRF Validation ───
        try:
            validate_cog_url(asset_url, enforce_allowlist=enforce_allowlist)
        except ValueError as ssrf_err:
            logger.warning("SSRF validation blocked COG verification: %s", ssrf_err)
            return {
                "asset_url": _sanitize_url_for_log(asset_url),
                "http_status": 403,
                "error": str(ssrf_err),
                "is_valid_geotiff_header": False,
                "ssrf_blocked": True,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        req = urllib.request.Request(
            asset_url,
            headers={
                "Range": byte_range,
                "User-Agent": "VeriField-Nexus-COG-Verifier/1.0",
            },
        )
        opener = urllib.request.build_opener(SSRFRedirectHandler(enforce_allowlist=enforce_allowlist))
        try:
            with opener.open(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                content_range = resp.headers.get("Content-Range", "")
                content_type = resp.headers.get("Content-Type", "")
                # Limit read to 2048 bytes to prevent abuse
                body = resp.read(2048)
                magic_bytes = body[:4].hex() if len(body) >= 4 else ""

                # Valid TIFF headers: Little-endian ('49492a00') or Big-endian ('4d4d002a')
                is_valid_geotiff = magic_bytes in ("49492a00", "4d4d002a")

                return {
                    "asset_url": _sanitize_url_for_log(asset_url),
                    "http_status": status,
                    "is_partial_content": status == 206,
                    "content_range": content_range,
                    "content_type": content_type,
                    "bytes_read": len(body),
                    "magic_bytes_hex": magic_bytes,
                    "is_valid_geotiff_header": is_valid_geotiff,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
        except ValueError as ssrf_err:
            # Catch any SSRF errors that slip through during redirect
            return {
                "asset_url": _sanitize_url_for_log(asset_url),
                "http_status": 403,
                "error": str(ssrf_err),
                "is_valid_geotiff_header": False,
                "ssrf_blocked": True,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            return {
                "asset_url": _sanitize_url_for_log(asset_url),
                "http_status": getattr(exc, "code", 500),
                "error": str(exc),
                "is_valid_geotiff_header": False,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def map_stac_item_to_raw_scene(
        item: Dict[str, Any],
        provider_code: str,
        platform: str,
        sensor: str,
        product_code: str,
        observation_type: EOObservationType,
        spatial_resolution_m: float,
        processing_level: str = "L2A",
    ) -> RawSceneMetadata:
        """
        Maps a standard STAC GeoJSON item into a VeriField RawSceneMetadata instance.
        """
        scene_id = item.get("id", "UNKNOWN_SCENE")
        properties = item.get("properties", {})
        geometry = item.get("geometry", {})
        bbox = item.get("bbox", [0.0, 0.0, 0.0, 0.0])

        dt_str = properties.get("datetime")
        if dt_str:
            try:
                acq_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                acq_dt = datetime.now(timezone.utc)
        else:
            acq_dt = datetime.now(timezone.utc)

        cloud_cover = properties.get("eo:cloud_cover")
        if cloud_cover is not None:
            cloud_cover = float(cloud_cover)

        # Extract band asset URLs
        assets = item.get("assets", {})
        raw_band_uris: Dict[str, str] = {}
        for band_key, asset_info in assets.items():
            if isinstance(asset_info, dict) and "href" in asset_info:
                raw_band_uris[band_key] = asset_info["href"]

        # Default visual or primary asset URI
        asset_uri = (
            raw_band_uris.get("visual")
            or raw_band_uris.get("rendered_preview")
            or raw_band_uris.get("red")
            or raw_band_uris.get("vv")
            or (list(raw_band_uris.values())[0] if raw_band_uris else None)
        )

        raw_platform = str(properties.get("platform", platform))
        if "sentinel-2" in raw_platform.lower():
            canon_platform = "Sentinel-2" + (raw_platform[-1].upper() if raw_platform[-1].lower() in ("a", "b") else "")
        elif "sentinel-1" in raw_platform.lower():
            canon_platform = "Sentinel-1" + (raw_platform[-1].upper() if raw_platform[-1].lower() in ("a", "b") else "")
        elif "landsat" in raw_platform.lower():
            canon_platform = "Landsat-" + (raw_platform.split("-")[-1] if "-" in raw_platform else "8/9")
        else:
            canon_platform = raw_platform or platform

        return RawSceneMetadata(
            scene_id=scene_id,
            provider_code=provider_code,
            platform=canon_platform,
            sensor=sensor,
            product_code=product_code,
            observation_type=observation_type,
            acquisition_timestamp=acq_dt,
            spatial_resolution_m=spatial_resolution_m,
            bounding_box=bbox,
            geometry_geojson=geometry,
            processing_level=processing_level,
            cloud_cover_pct=cloud_cover,
            raw_band_uris=raw_band_uris,
            raw_band_checksums={},
            asset_uri=asset_uri,
            quality_status=EOQualityStatus.USABLE,
            quality_flags={"stac_properties": {k: v for k, v in properties.items() if isinstance(v, (str, int, float, bool))}},
            lineage_manifest={"stac_item_id": scene_id, "stac_collection": item.get("collection")},
        )


default_stac_client = STACClient()
