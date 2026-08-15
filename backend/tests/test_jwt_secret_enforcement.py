"""
Security Tests: JWT Secret Enforcement
Verifies that VeriField Nexus refuses to operate with a default/missing JWT secret in production mode.
"""
import pytest
from unittest.mock import patch
import os


def _make_settings(**overrides):
    """Create a Settings instance with specific overrides for testing."""
    env = {
        "SUPABASE_URL": "",
        "SUPABASE_KEY": "",
        "DATABASE_URL": "",
        "JWT_SECRET": "",
        "DEV_MODE": "false",
        "DEBUG": "false",
    }
    env.update({k.upper(): str(v) for k, v in overrides.items()})
    with patch.dict(os.environ, env, clear=False):
        from app.core.config import Settings
        return Settings(**{k.lower(): v for k, v in overrides.items()})


def test_production_missing_jwt_secret_raises():
    """Production mode (dev_mode=False, debug=False) with no JWT_SECRET must fail."""
    s = _make_settings(dev_mode=False, debug=False, jwt_secret="")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _ = s.effective_jwt_secret


def test_production_default_dev_secret_raises():
    """Production mode with the dev-only default secret must fail."""
    s = _make_settings(dev_mode=False, debug=False, jwt_secret="verifield-dev-secret-key")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _ = s.effective_jwt_secret


def test_production_valid_secret_succeeds():
    """Production mode with a valid explicit secret must return it."""
    s = _make_settings(dev_mode=False, debug=False, jwt_secret="my-strong-production-secret-2026")
    assert s.effective_jwt_secret == "my-strong-production-secret-2026"


def test_dev_mode_no_secret_returns_dev_default():
    """Dev mode (dev_mode=True, debug=True) with no secret falls back to dev default."""
    s = _make_settings(dev_mode=True, debug=True, jwt_secret="")
    assert s.effective_jwt_secret == "verifield-dev-secret-key"


def test_dev_mode_custom_secret_used():
    """Dev mode with a custom secret uses the custom secret."""
    s = _make_settings(dev_mode=True, debug=True, jwt_secret="custom-dev-secret")
    assert s.effective_jwt_secret == "custom-dev-secret"


if __name__ == "__main__":
    test_production_missing_jwt_secret_raises()
    print("PASS: production_missing_jwt_secret_raises")
    test_production_default_dev_secret_raises()
    print("PASS: production_default_dev_secret_raises")
    test_production_valid_secret_succeeds()
    print("PASS: production_valid_secret_succeeds")
    test_dev_mode_no_secret_returns_dev_default()
    print("PASS: dev_mode_no_secret_returns_dev_default")
    test_dev_mode_custom_secret_used()
    print("PASS: dev_mode_custom_secret_used")
    print("\nAll 5 JWT secret enforcement tests passed.")
