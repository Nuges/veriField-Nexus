"""
VeriField Nexus — Canonical Operating Sectors API & Contract Tests
Verifies that:
1. Backend accepts strictly the 5 canonical sector values:
   COOKSTOVES, HYBRID_ENERGY, BIOCHAR, EV_MOBILITY, AGRICULTURE_LAND_USE.
2. Backend strictly rejects arbitrary family and test fixture strings:
   'Test Family', 'Biochar Removal Family', free-text strings with HTTP 422.
"""

import pytest
import uuid
from pydantic import ValidationError
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.sectors import (
    CanonicalSector,
    CANONICAL_SECTOR_CODES,
    CANONICAL_SECTOR_LABELS,
    CANONICAL_SECTOR_UUID_MAP,
    normalize_to_canonical_sector,
    is_canonical_sector,
)
from app.domains.organizations.routers.access_requests import AccessRequestCreate


def test_canonical_sectors_configuration():
    """Assert exactly 5 canonical sector codes and their exact platform labels."""
    assert len(CANONICAL_SECTOR_CODES) == 5
    expected_codes = [
        "COOKSTOVES",
        "HYBRID_ENERGY",
        "BIOCHAR",
        "EV_MOBILITY",
        "AGRICULTURE_LAND_USE",
    ]
    assert CANONICAL_SECTOR_CODES == expected_codes

    assert CANONICAL_SECTOR_LABELS[CanonicalSector.COOKSTOVES] == "Clean Cookstoves"
    assert CANONICAL_SECTOR_LABELS[CanonicalSector.HYBRID_ENERGY] == "Hybrid Energy & Mini-grids"
    assert CANONICAL_SECTOR_LABELS[CanonicalSector.BIOCHAR] == "Biochar Carbon Removal"
    assert CANONICAL_SECTOR_LABELS[CanonicalSector.EV_MOBILITY] == "EV Mobility"
    assert CANONICAL_SECTOR_LABELS[CanonicalSector.AGRICULTURE_LAND_USE] == "Agriculture & Land Use"


def test_canonical_sector_normalization():
    """Assert case-insensitivity and alias normalization."""
    for code in CANONICAL_SECTOR_CODES:
        assert normalize_to_canonical_sector(code) == CanonicalSector(code)
        assert normalize_to_canonical_sector(code.lower()) == CanonicalSector(code)
        assert is_canonical_sector(code) is True

    # Known aliases
    assert normalize_to_canonical_sector("clean cookstoves") == CanonicalSector.COOKSTOVES
    assert normalize_to_canonical_sector("hybrid energy & mini-grids") == CanonicalSector.HYBRID_ENERGY
    assert normalize_to_canonical_sector("biochar carbon removal") == CanonicalSector.BIOCHAR
    assert normalize_to_canonical_sector("ev mobility") == CanonicalSector.EV_MOBILITY
    assert normalize_to_canonical_sector("agriculture & land use") == CanonicalSector.AGRICULTURE_LAND_USE

    # Canonical DB UUIDs
    assert normalize_to_canonical_sector("9a7a4370-71e6-44f5-9870-975823b8ccb9") == CanonicalSector.AGRICULTURE_LAND_USE
    assert normalize_to_canonical_sector("d77b6543-f0f1-4784-a840-cd77e0876a91") == CanonicalSector.BIOCHAR
    assert normalize_to_canonical_sector("ab748cb8-3b7c-4e07-aec7-d1dc5f3dcf3a") == CanonicalSector.COOKSTOVES
    assert normalize_to_canonical_sector("15fa60cc-d06a-4ef1-ae14-0359e1bd3674") == CanonicalSector.HYBRID_ENERGY
    assert normalize_to_canonical_sector("ab17ade7-8938-44b1-a24d-bc797a65e056") == CanonicalSector.EV_MOBILITY


def test_disallowed_family_and_test_strings_rejected():
    """Assert test fixture names and non-canonical strings return None."""
    disallowed = [
        "Test Family",
        "Biochar Removal Family",
        "Biochar Removal Family Lock",
        "FAM-282bf4",
        "random_unknown_sector",
        "free-text-sector",
        "00000000-0000-0000-0000-000000000000",
    ]
    for val in disallowed:
        assert normalize_to_canonical_sector(val) is None
        assert is_canonical_sector(val) is False


def test_access_request_create_schema_accepts_canonical_sectors():
    """Assert Pydantic schema accepts all 5 canonical sectors."""
    for code in CANONICAL_SECTOR_CODES:
        req = AccessRequestCreate(
            full_name="Valid Applicant",
            email=f"valid.{code.lower()}@example.com",
            organization_name=f"Org {code}",
            sector_id=code,
        )
        assert req.sector_id == code


def test_access_request_create_schema_rejects_invalid_sectors():
    """Assert Pydantic schema raises ValidationError for unauthorized sector values."""
    invalid_sectors = [
        "Test Family",
        "Biochar Removal Family",
        "Arbitrary Sector",
        "UNKNOWN",
        "invalid-not-a-uuid",
    ]
    for invalid in invalid_sectors:
        with pytest.raises(ValidationError) as exc_info:
            AccessRequestCreate(
                full_name="Invalid Applicant",
                email="invalid@example.com",
                organization_name="Invalid Org",
                sector_id=invalid,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sector_id",) for e in errors)
        assert "Primary Operating Sector must be one of the canonical platform sectors" in str(errors)


@pytest.mark.asyncio
async def test_access_request_api_accepts_all_canonical_sectors():
    """Assert HTTP POST /api/v1/access-requests accepts all 5 canonical sectors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for code in CANONICAL_SECTOR_CODES:
            uid = uuid.uuid4().hex[:8]
            payload = {
                "full_name": f"User {code}",
                "email": f"applicant.{code.lower()}.{uid}@example.com",
                "organization_name": f"Org {code} {uid}",
                "sector_id": code,
                "project_name": f"Project {code}",
            }
            res = await client.post("/api/v1/access-requests", json=payload)
            # Both 200 OK and 201 Created are acceptable success statuses
            assert res.status_code in (200, 201), f"Failed for canonical sector {code}: {res.text}"
            data = res.json()
            assert data.get("status") == "success"


@pytest.mark.asyncio
async def test_access_request_api_rejects_test_family_and_invalid_values_with_422():
    """Assert HTTP POST /api/v1/access-requests rejects 'Test Family', 'Biochar Removal Family', and arbitrary UUIDs with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        invalid_cases = [
            "Test Family",
            "Biochar Removal Family",
            "NonExistentSector123",
            "free text sector",
            "00000000-0000-0000-0000-000000000000",
        ]
        for invalid in invalid_cases:
            uid = uuid.uuid4().hex[:8]
            payload = {
                "full_name": "Rejected Applicant",
                "email": f"applicant.rejected.{uid}@example.com",
                "organization_name": f"Rejected Org {uid}",
                "sector_id": invalid,
            }
            res = await client.post("/api/v1/access-requests", json=payload)
            assert res.status_code == 422, f"Expected 422 for '{invalid}', got {res.status_code}: {res.text}"
            err_json = res.json()
            assert "detail" in err_json
            detail_str = str(err_json["detail"])
            assert "Primary Operating Sector must be one of the canonical platform sectors" in detail_str
