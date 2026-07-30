"""

=============================================================================

VeriField Nexus — AES-256-GCM Encryption Service

=============================================================================

Application-level encryption for sensitive data at rest. Uses the

`cryptography` library (already in requirements.txt).

=============================================================================

"""



import base64

import logging

import os

import secrets

from typing import Optional



from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from cryptography.hazmat.primitives import hashes



logger = logging.getLogger("verifield.encryption")



_encryption_service: Optional["EncryptionService"] = None





class EncryptionService:

    """

    AES-256-GCM encryption service for sensitive data at rest.

    Provides authenticated encryption with associated data (AEAD).

    """



    NONCE_SIZE = 12  # 96-bit nonce for AES-GCM

    KEY_SIZE = 32  # 256-bit key



    def __init__(self, key: Optional[bytes] = None):

        if key:

            self._key = key

        else:

            env_key = os.environ.get("VERIFIELD_ENCRYPTION_KEY", "")

            if env_key:

                try:

                    self._key = base64.b64decode(env_key)

                    if len(self._key) != self.KEY_SIZE:

                        raise ValueError(

                            f"Key must be {self.KEY_SIZE} bytes, got {len(self._key)}"

                        )

                except Exception:

                    # Try hex decoding

                    try:

                        self._key = bytes.fromhex(env_key)

                    except ValueError:

                        logger.warning(

                            "VERIFIELD_ENCRYPTION_KEY is set but invalid. "

                            "Generating ephemeral key. SET A PROPER KEY IN PRODUCTION."

                        )

                        self._key = AESGCM.generate_key(bit_length=256)

            else:

                logger.warning(

                    "VERIFIELD_ENCRYPTION_KEY not set. Generating ephemeral key. "

                    "Data encrypted with this key will NOT survive restarts. "

                    "Set VERIFIELD_ENCRYPTION_KEY in .env for production."

                )

                self._key = AESGCM.generate_key(bit_length=256)



        self._aesgcm = AESGCM(self._key)



    def encrypt(self, plaintext: str) -> str:

        """

        Encrypt a string with AES-256-GCM.

        Returns base64(nonce + ciphertext + tag).

        """

        if not plaintext:

            return plaintext

        nonce = secrets.token_bytes(self.NONCE_SIZE)

        ct = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        return base64.b64encode(nonce + ct).decode("utf-8")



    def decrypt(self, ciphertext: str) -> str:

        """

        Decrypt a base64-encoded AES-256-GCM ciphertext.

        """

        if not ciphertext:

            return ciphertext

        try:

            raw = base64.b64decode(ciphertext)

            nonce = raw[: self.NONCE_SIZE]

            ct = raw[self.NONCE_SIZE :]

            return self._aesgcm.decrypt(nonce, ct, None).decode("utf-8")

        except Exception as e:

            raise ValueError(f"Encryption integrity check failed: {e}") from e



    def encrypt_bytes(self, data: bytes) -> bytes:

        """Encrypt binary data with AES-256-GCM."""

        if not data:

            return data

        nonce = secrets.token_bytes(self.NONCE_SIZE)

        ct = self._aesgcm.encrypt(nonce, data, None)

        return nonce + ct



    def decrypt_bytes(self, data: bytes) -> bytes:

        """Decrypt binary data encrypted with AES-256-GCM."""

        if not data:

            return data

        nonce = data[: self.NONCE_SIZE]

        ct = data[self.NONCE_SIZE :]

        return self._aesgcm.decrypt(nonce, ct, None)



    @staticmethod

    def derive_key(password: str, salt: bytes) -> bytes:

        """Derive a 256-bit key from a password using PBKDF2-SHA256."""

        kdf = PBKDF2HMAC(

            algorithm=hashes.SHA256(),

            length=32,

            salt=salt,

            iterations=600_000,

        )

        return kdf.derive(password.encode("utf-8"))



    @staticmethod

    def generate_salt() -> bytes:

        """Generate a 16-byte random salt."""

        return secrets.token_bytes(16)





def get_encryption_service() -> EncryptionService:

    """Singleton factory for the encryption service."""

    global _encryption_service

    if _encryption_service is None:

        _encryption_service = EncryptionService()

    return _encryption_service
