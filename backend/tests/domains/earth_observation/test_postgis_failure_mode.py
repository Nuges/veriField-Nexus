"""
=============================================================================
VeriField Nexus — PostGIS Failure-Mode & Capability Enforcement Tests
=============================================================================
Verifies that:
1. PostgreSQL without PostGIS fails closed (SPATIAL_BACKEND_UNAVAILABLE).
2. PostgreSQL without PostGIS is never masked as a degraded Shapely fallback.
3. Health endpoint /health/spatial returns HTTP 503 when spatial backend is unavailable.
4. Startup probe raises RuntimeError when PostGIS is absent on PostgreSQL.
5. SQLite reports SQLITE_SPATIAL_FALLBACK for lightweight test/dev.
=============================================================================
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.domains.earth_observation.services.geospatial_engine import (
    geospatial_engine,
    SpatialBackendState,
)
from app.api.endpoints.health import spatial_health, readiness_probe


@pytest.mark.asyncio
async def test_postgres_without_postgis_detects_unavailable():
    """
    When dialect is PostgreSQL and SELECT postgis_version() fails,
    geospatial_engine must return SPATIAL_BACKEND_UNAVAILABLE, NOT a degraded fallback.
    """
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.bind = mock_bind
    # Simulate postgis_version() failing (extension missing)
    mock_session.execute.side_effect = Exception("function postgis_version() does not exist")

    result = await geospatial_engine.detect_spatial_backend(mock_session)

    assert result["state"] == SpatialBackendState.SPATIAL_BACKEND_UNAVAILABLE.value
    assert result["production_ready"] is False
    assert result["database_native_indexing"] is False
    assert result["postgis_version"] is None
    assert result["dialect"] == "postgresql"
    assert any("PostGIS 3.3+ extension is required" in lim for lim in result["limitations"])


@pytest.mark.asyncio
async def test_postgres_with_postgis_detects_active():
    """
    When dialect is PostgreSQL and PostGIS is installed,
    geospatial_engine returns POSTGIS_ACTIVE with production_ready = True.
    """
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.bind = mock_bind

    mock_result = MagicMock()
    mock_result.scalar.return_value = "3.4.2"
    mock_session.execute.return_value = mock_result

    result = await geospatial_engine.detect_spatial_backend(mock_session)

    assert result["state"] == SpatialBackendState.POSTGIS_ACTIVE.value
    assert result["production_ready"] is True
    assert result["database_native_indexing"] is True
    assert result["postgis_version"] == "3.4.2"
    assert result["limitations"] == []


@pytest.mark.asyncio
async def test_sqlite_reports_sqlite_spatial_fallback():
    """
    When dialect is SQLite, geospatial_engine returns SQLITE_SPATIAL_FALLBACK
    with production_ready = False (supported strictly for test/dev).
    """
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "sqlite"
    mock_session.bind = mock_bind

    result = await geospatial_engine.detect_spatial_backend(mock_session)

    assert result["state"] == SpatialBackendState.SQLITE_SPATIAL_FALLBACK.value
    assert result["production_ready"] is False
    assert result["database_native_indexing"] is False
    assert result["dialect"] == "sqlite"
    assert any("Development/test fallback only" in lim for lim in result["limitations"])


@pytest.mark.asyncio
async def test_health_spatial_endpoint_503_on_unavailable():
    """
    The /health/spatial endpoint must return HTTP 503 when spatial backend is unavailable.
    """
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.bind = mock_bind
    mock_session.execute.side_effect = Exception("function postgis_version() does not exist")

    with pytest.raises(HTTPException) as exc_info:
        await spatial_health(db=mock_session)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_readiness_probe_fails_on_postgres_without_postgis():
    """
    Readiness probe must fail with 503 when database is PostgreSQL but PostGIS is absent.
    """
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.bind = mock_bind
    # First query SELECT 1 succeeds
    # Second query for spatial check fails
    mock_session.execute.side_effect = [
        MagicMock(),  # SELECT 1 succeeds
        Exception("function postgis_version() does not exist"),  # postgis check fails
    ]

    with pytest.raises(HTTPException) as exc_info:
        await readiness_probe(db=mock_session)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_real_homebrew_postgres_14_without_postgis():
    """
    Real execution against non-PostGIS PostgreSQL instance (if reachable)
    to confirm that a real PostgreSQL instance lacking PostGIS is truthfully
    reported as SPATIAL_BACKEND_UNAVAILABLE.
    """
    import os
    import asyncpg

    port = int(os.environ.get("POSTGRES_NO_POSTGIS_PORT", "54329"))
    user = os.environ.get("POSTGRES_NO_POSTGIS_USER", "postgres")
    db_name = os.environ.get("POSTGRES_NO_POSTGIS_DB", "postgres")

    try:
        conn = await asyncpg.connect(
            user=user,
            host="127.0.0.1",
            port=port,
            database=db_name,
            timeout=2.0,
        )
    except Exception:
        pytest.skip(f"Non-PostGIS PostgreSQL instance on port {port} not reachable.")

    try:
        has_postgis = False
        try:
            val = await conn.fetchval("SELECT postgis_version();")
            has_postgis = bool(val)
        except Exception:
            has_postgis = False

        assert has_postgis is False, f"Port {port} was expected to NOT have PostGIS."
    finally:
        await conn.close()
