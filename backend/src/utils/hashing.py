"""
=============================================================================
VeriField Nexus — Cryptographic & Signature Utilities
=============================================================================
Provides helper functions for payload hashing and simulated Solana on-chain
transaction signature generation.
=============================================================================
"""

import hashlib
import time


def generate_signature_hash(image_hash: str, trust_score: int) -> str:
    """
    Simulates a Solana Devnet transaction signature based on proof metadata.
    
    Generates a cryptographic hash combining evidence hash, trust score,
    and current timestamp to represent an anchored transaction.
    
    Args:
        image_hash: The cryptographic SHA-256 evidence identifier.
        trust_score: Calculated trust evaluation score.
        
    Returns:
        64-character SHA-256 simulated signature hex string.
    """
    raw_payload = f"{image_hash}-{trust_score}-{time.time_ns()}".encode("utf-8")
    signature = hashlib.sha256(raw_payload).hexdigest()
    return f"sol_tx_{signature}"
