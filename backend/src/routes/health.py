"""
=============================================================================
VeriField Nexus — Health Check Route
=============================================================================
Quick, lightweight endpoint for monitoring system availability.
=============================================================================
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["System Health"])


class HealthStatusResponse(BaseModel):
    status: str
    network: str
    version: str


@router.get("", response_model=HealthStatusResponse, summary="Get API status")
async def get_health():
    """
    Checks backend service status.
    
    Returns:
        HealthStatusResponse containing service status, version, and network.
    """
    return HealthStatusResponse(
        status="operational",
        network="solana-devnet",
        version="1.0.0"
    )
