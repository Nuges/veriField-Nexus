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
