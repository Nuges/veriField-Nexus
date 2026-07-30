"""

=============================================================================

VeriField Nexus — Multi-Factor Authentication (MFA) Service

=============================================================================

Production TOTP-based MFA with QR code generation, recovery codes, and

verification. Uses pyotp for TOTP and the cryptography library for key ops.

=============================================================================

"""



import base64

import hashlib

import io

import logging

import secrets

from typing import List, Optional, Tuple



import pyotp



logger = logging.getLogger("verifield.mfa")



# QR code is optional — degrade gracefully if not installed

try:

    import qrcode

    HAS_QRCODE = True

except ImportError:

    HAS_QRCODE = False

    logger.warning("qrcode package not installed — QR code generation disabled")





class MFAService:

    """

    TOTP-based Multi-Factor Authentication service.

    Implements RFC 6238 with 30-second intervals and 6-digit codes.

    """



    ISSUER = "VeriField Nexus"

    DIGITS = 6

    INTERVAL = 30

    RECOVERY_CODE_COUNT = 8

    RECOVERY_CODE_LENGTH = 10



    @staticmethod

    def generate_secret() -> str:

        """Generate a new base32-encoded TOTP secret."""

        return pyotp.random_base32(length=32)



    @staticmethod

    def generate_provisioning_uri(

        secret: str,

        email: str,

        issuer: str = "VeriField Nexus",

    ) -> str:

        """Generate an otpauth:// URI for authenticator app enrollment."""

        totp = pyotp.TOTP(secret, digits=MFAService.DIGITS, interval=MFAService.INTERVAL)

        return totp.provisioning_uri(name=email, issuer_name=issuer)



    @staticmethod

    def generate_qr_code_base64(provisioning_uri: str) -> Optional[str]:

        """Generate a base64-encoded PNG QR code from a provisioning URI."""

        if not HAS_QRCODE:

            return None

        try:

            qr = qrcode.QRCode(version=1, box_size=6, border=2)

            qr.add_data(provisioning_uri)

            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()

            img.save(buffer, format="PNG")

            buffer.seek(0)

            return base64.b64encode(buffer.read()).decode("utf-8")

        except Exception as e:

            logger.error(f"QR code generation failed: {e}")

            return None



    @staticmethod

    def verify_totp(secret: str, code: str) -> bool:

        """

        Verify a 6-digit TOTP code against the secret.

        Allows ±1 time window (valid_window=1) for clock drift tolerance.

        """

        if not code or not secret:

            return False

        try:

            totp = pyotp.TOTP(secret, digits=MFAService.DIGITS, interval=MFAService.INTERVAL)

            return totp.verify(code, valid_window=1)

        except Exception as e:

            logger.error(f"TOTP verification error: {e}")

            return False



    @staticmethod

    def generate_recovery_codes(

        count: int = 8,

    ) -> List[str]:

        """Generate human-readable recovery codes (e.g., 'A3F7-K9M2-X1PQ')."""

        codes = []

        for _ in range(count):

            raw = secrets.token_hex(MFAService.RECOVERY_CODE_LENGTH)

            # Format as XXX-XXX-XXXX for readability

            formatted = f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}".upper()

            codes.append(formatted)

        return codes



    @staticmethod

    def hash_recovery_code(code: str) -> str:

        """SHA-256 hash a recovery code for secure storage."""

        normalized = code.strip().upper().replace("-", "").replace(" ", "")

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()



    @staticmethod

    def verify_recovery_code(

        code: str,

        hashed_codes: List[str],

    ) -> Tuple[bool, List[str]]:

        """

        Verify a recovery code against the stored hashes.

        Returns (is_valid, remaining_hashed_codes) — the used code is consumed.

        """

        code_hash = MFAService.hash_recovery_code(code)

        if code_hash in hashed_codes:

            remaining = [h for h in hashed_codes if h != code_hash]

            return True, remaining

        return False, hashed_codes
