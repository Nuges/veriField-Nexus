"""
=============================================================================
Unit Tests for MFA, Encryption, SSO, and ABAC Security
=============================================================================
"""

import pytest
from app.core.mfa import MFAService
from app.core.encryption import EncryptionService
from app.core.sso import SSOProviderFactory
from app.core.abac import ABACEngine
from app.domains.authentication.models import User
from uuid import uuid4
import pytest
from fastapi import HTTPException

def test_mfa_lifecycle():
    # 1. Secret generation
    secret = MFAService.generate_secret()
    assert isinstance(secret, str)
    assert len(secret) > 10

    # 2. Provisioning URI & QR Code
    uri = MFAService.generate_provisioning_uri(secret, "test@verifield.io")
    assert "test%40verifield.io" in uri or "test@verifield.io" in uri
    assert secret in uri

    qr = MFAService.generate_qr_code_base64(uri)
    assert isinstance(qr, str)
    assert len(qr) > 50

    # 3. TOTP generation & verification
    import pyotp
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    assert MFAService.verify_totp(secret, valid_code) is True
    assert MFAService.verify_totp(secret, "000000") is False

    # 4. Recovery codes
    codes = MFAService.generate_recovery_codes(count=8)
    assert len(codes) == 8
    hashes = [MFAService.hash_recovery_code(c) for c in codes]

    # Verify recovery code
    valid, remaining = MFAService.verify_recovery_code(codes[0], hashes)
    assert valid is True
    assert len(remaining) == 7

    # Verify already-used code fails
    valid_retry, _ = MFAService.verify_recovery_code(codes[0], remaining)
    assert valid_retry is False


def test_encryption_decryption_lifecycle():
    key_bytes = b"verifield-test-secret-key-32byte"
    service = EncryptionService(key=key_bytes)

    payload = "Sensitive GPS: 6.5244 N, 3.3792 E - Sensor Hardware ID: VF-90210"
    encrypted = service.encrypt(payload)

    assert encrypted != payload
    assert len(encrypted) > 20

    decrypted = service.decrypt(encrypted)
    assert decrypted == payload

    # Tampered ciphertext fails
    tampered = encrypted[:-4] + "AAAA"
    with pytest.raises(ValueError, match="integrity check failed"):
        service.decrypt(tampered)


@pytest.mark.asyncio
async def test_sso_provider_factory():
    provider = SSOProviderFactory.get_provider(
        "google",
        client_id="test-client-id",
        client_secret="test-secret",
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
    )
    provider._discovery_cache = {"authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth"}
    url = await provider.get_authorization_url(redirect_uri="http://localhost:3000/login", state="xyz123")
    assert "accounts.google.com" in url or "google" in url.lower()
    assert "client_id=test-client-id" in url

    provider_entra = SSOProviderFactory.get_provider(
        "azure",
        client_id="entra-id",
        client_secret="entra-secret",
        discovery_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    )
    provider_entra._discovery_cache = {"authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"}
    url_entra = await provider_entra.get_authorization_url(redirect_uri="http://localhost:3000/login", state="abc")
    assert "login.microsoftonline.com" in url_entra or "microsoft" in url_entra.lower()



def test_abac_security_enforcement():
    # User roles
    auditor = User(id=uuid4(), email="auditor@verifield.io", role="VVB_AUDITOR", status="active")
    agent = User(id=uuid4(), email="field@verifield.io", role="FIELD_AGENT", status="active")

    # Auditor accessing sensitive GPS metadata gets full access
    abac_auditor = ABACEngine(db=None, user=auditor)
    assert abac_auditor.enforce_sensitive_data_access("GPS_METADATA") == "full"

    # Field agent trying to access personal identification data is forbidden (raises 403)
    abac_agent = ABACEngine(db=None, user=agent)
    with pytest.raises(HTTPException) as exc_info:
        abac_agent.enforce_sensitive_data_access("PERSONAL_IDENTIFICATION")
    assert exc_info.value.status_code == 403

