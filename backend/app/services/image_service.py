"""
=============================================================================
VeriField Nexus — Image Service
=============================================================================
Handles image hash generation for duplicate detection.
Uses perceptual hashing (pHash) to create fingerprints of images.
=============================================================================
"""

import hashlib
import io
from typing import Optional

try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False


class ImageService:
    """Service for image processing and hash generation."""

    @staticmethod
    def generate_perceptual_hash(image_bytes: bytes) -> Optional[str]:
        """
        Generate a perceptual hash (pHash) from image bytes.
        pHash is robust to minor image modifications (resize, compression).
        
        Returns:
            Hex-encoded hash string, or None if processing fails
        """
        if not IMAGEHASH_AVAILABLE:
            # Fallback to SHA256 if imagehash not installed
            return hashlib.sha256(image_bytes).hexdigest()[:16]
        try:
            image = Image.open(io.BytesIO(image_bytes))
            phash = imagehash.phash(image)
            return str(phash)
        except Exception:
            return None

    @staticmethod
    def generate_sha256_hash(image_bytes: bytes) -> str:
        """Generate SHA256 hash for exact duplicate detection."""
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def compare_hashes(hash1: str, hash2: str) -> int:
        """
        Calculate hamming distance between two hex-encoded hashes.
        Lower distance = more similar images.
        """
        try:
            val1, val2 = int(hash1, 16), int(hash2, 16)
            return bin(val1 ^ val2).count("1")
        except (ValueError, TypeError):
            return 64  # Max distance if invalid
