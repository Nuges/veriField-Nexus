"""
=============================================================================
VeriField Nexus — Asset Verification Route
=============================================================================
Main ingestion endpoint for submitting climate asset verification evidence.
=============================================================================
"""

from fastapi import APIRouter, HTTPException, status
from src.models.verification import VerificationRequest, VerificationResponse
from src.services.verification_engine import VerificationEngine

router = APIRouter(prefix="/verify", tags=["Asset Verification"])


@router.post(
    "",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit environmental verification record"
)
async def verify_asset(payload: VerificationRequest):
    """
    Submits a raw environmental evidence log for verification.
    
    The engine validates formatting, runs the trust scoring heuristic,
    and returns a structured record with a simulated Solana transaction hash.
    
    Args:
        payload: VerificationRequest containing GPS, timestamp, and imageHash.
        
    Returns:
        VerificationResponse containing trust score and anchored transaction details.
    """
    engine = VerificationEngine()
    result = await engine.process_verification(payload)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process verification payload"
        )
    return result
export_router = router
