from app.domains.ledger.models import AuditTrail, Signature


def test_signature_creation():
    sig = Signature(
        id="123e4567-e89b-12d3-a456-426614174000",
        project_id="123e4567-e89b-12d3-a456-426614174001",
        signature_hash="0xabcd",
    )
    assert sig.signature_hash == "0xabcd"


def test_audit_trail_creation():
    audit = AuditTrail(
        id="123e4567-e89b-12d3-a456-426614174000",
        action_type="CREATE",
        before_state={},
        after_state={"status": "active"},
    )
    assert audit.action_type == "CREATE"


def test_audit_trail_reason():
    audit = AuditTrail(
        id="123e4567-e89b-12d3-a456-426614174000",
        action_type="CREATE",
        reason="Admin request",
    )
    assert audit.reason == "Admin request"


import pytest
import uuid

@pytest.mark.asyncio
async def test_execute_carbon_minting_endpoint(db_session):
    from app.domains.ledger.api import execute_carbon_minting, MintRequest
    from app.domains.authentication.models import User
    from app.domains.projects.models import Project, CarbonCalculation

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    proj = Project(
        id=proj_id,
        name="Solana Carbon Test Project",
        organization_id=org_id,
        country="Nigeria",
    )
    db_session.add(proj)

    calc = CarbonCalculation(
        id=uuid.uuid4(),
        project_id=proj_id,
        tco2e_generated=15.75,
        status="calculated",
    )
    db_session.add(calc)
    await db_session.commit()

    user = User(
        id=uuid.uuid4(),
        email="carbon_trader@verifield.io",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )

    req = MintRequest(
        project_id=proj_id,
        target_chain="solana-devnet",
        recipient_wallet="VF_Treasury_Solana_Wallet_123",
    )

    res = await execute_carbon_minting(data=req, db=db_session, current_user=user)

    assert res["status"] == "MINTED"
    assert res["total_tco2e"] == 15.75
    assert "VF-NGA-SOL" in res["serial_number"]
    assert res["target_chain"] == "solana-devnet"
    assert res["transaction_signature"].startswith("5KtP")
    assert res["records_minted"] == 1

