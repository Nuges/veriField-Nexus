"""
=============================================================================
VeriField Nexus — Simulated Solana Anchoring Service
=============================================================================
Generates cryptographic proof signatures and slots to anchor verified
environmental assets on-chain.
=============================================================================
"""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity import Activity

def generate_base58_signature(length: int = 88) -> str:
    """Generate a random base58-like signature of specified length."""
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return "".join(secrets.choice(chars) for _ in range(length))

def calculate_activity_payload_hash(activity: Activity) -> str:
    """
    Computes a deterministic cryptographic SHA-256 hash of the installation record.
    Forces order consistency by sorting JSON keys.
    """
    # Exclude dynamic/volatile database fields for strict state matching
    payload_data = {
        "id": str(activity.id),
        "activity_type": activity.activity_type,
        "latitude": activity.latitude,
        "longitude": activity.longitude,
        "captured_at": activity.captured_at.isoformat() if activity.captured_at else None,
        "image_hash": activity.image_hash,
        "user_id": str(activity.user_id)
    }
    
    # Secure string dump
    serialized = json.dumps(payload_data, sort_keys=True)
    return "sha256_" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()

async def anchor_activity_on_chain(activity: Activity, db: AsyncSession) -> None:
    """
    Simulates broadcasting the installation state hash to a Solana smart contract.
    Updates the activity's JSONB data with transaction details.
    """
    act_data = activity.activity_data or {}
    
    # Avoid duplicate anchoring
    if "on_chain" in act_data:
        return
        
    # Calculate state cryptographic hash
    payload_hash = calculate_activity_payload_hash(activity)
    
    # Generate mock transaction data
    tx_signature = generate_base58_signature(88)
    block_height = 200000000 + secrets.randbelow(20000000)
    slot = block_height + secrets.randbelow(8) + 1
    
    # Write to activity JSON payload block
    act_data["on_chain"] = {
        "signature": tx_signature,
        "block_height": block_height,
        "slot": slot,
        "payload_hash": payload_hash,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    activity.activity_data = act_data
    db.add(activity)
    
    # Commit changes back to session
    await db.commit()
    await db.refresh(activity)
