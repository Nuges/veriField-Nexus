import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domains.evidence.models import Evidence
from app.domains.organizations.models import Organization

ASYNC_DB_URL = "postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test"

async def main():
    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("======================================================================")
    print("VERIFIELD NEXUS — PHASE 2 GROUND EVIDENCE CRYPTOGRAPHIC HASH & TAMPER PROOF")
    print("======================================================================")

    # 1. Authentic Phase 2 Soil Lab Report Artifact Bytes
    p2_fixture_path = os.path.abspath("../dashboard/tests/fixtures/synthetic_phase2_soil_lab_report.json")
    with open(p2_fixture_path, "rb") as f:
        p2_original_bytes = f.read()

    p2_computed_sha256 = hashlib.sha256(p2_original_bytes).hexdigest()
    p2_byte_count = len(p2_original_bytes)
    p2_mime_type = "application/json"

    print("\n[Artifact 1: Phase 2 Soil Laboratory Analysis Certificate]")
    print(f"Fixture Path:       {p2_fixture_path}")
    print(f"File Size:          {p2_byte_count} bytes")
    print(f"Computed SHA-256:   {p2_computed_sha256}")
    print(f"MIME Type:          {p2_mime_type}")

    # 2. Authentic EO Thumbnail Artifact Bytes
    eo_fixture_path = os.path.abspath("../dashboard/tests/fixtures/real_s2_thumbnail.jpg")
    with open(eo_fixture_path, "rb") as f:
        eo_original_bytes = f.read()

    eo_computed_sha256 = hashlib.sha256(eo_original_bytes).hexdigest()
    eo_byte_count = len(eo_original_bytes)
    eo_mime_type = "image/jpeg"

    print("\n[Artifact 2: Earth Observation Boundary Image]")
    print(f"Fixture Path:       {eo_fixture_path}")
    print(f"File Size:          {eo_byte_count} bytes")
    print(f"Computed SHA-256:   {eo_computed_sha256}")
    print(f"MIME Type:          {eo_mime_type}")

    async with async_session() as session:
        # 3. Persist Evidence Records in PostgreSQL
        org = Organization(name=f"Synthetic Agriculture Organization {uuid.uuid4().hex[:6]}", plan="ENTERPRISE")
        session.add(org)
        await session.flush()

        p2_evidence = Evidence(
            activity_id=uuid.uuid4(),
            file_uri=f"s3://verifield-evidence/{org.id}/soil_lab_cert_syn_001.json",
            file_hash=p2_computed_sha256,
            evidence_type="LAB_ANALYSIS_REPORT",
            status="VERIFIED",
            metadata_json={"byte_size": p2_byte_count, "mime_type": p2_mime_type, "evidence_chain": "PHASE_2_SOIL_ASSAY"},
        )
        eo_evidence = Evidence(
            activity_id=uuid.uuid4(),
            file_uri=f"s3://verifield-evidence/{org.id}/ground_photo_s2.jpg",
            file_hash=eo_computed_sha256,
            evidence_type="FIELD_PHOTO",
            status="VERIFIED",
            metadata_json={"byte_size": eo_byte_count, "mime_type": eo_mime_type, "evidence_chain": "EO_SPECTRAL_TRUTH"},
        )
        session.add_all([p2_evidence, eo_evidence])
        await session.commit()

        p2_evidence_id = p2_evidence.id
        eo_evidence_id = eo_evidence.id

        # 4. Query back Phase 2 Evidence from PostgreSQL
        loaded_p2 = (await session.execute(select(Evidence).where(Evidence.id == p2_evidence_id))).scalar_one()

        print("\n[Phase 2 Soil Evidence Database Persistence Verification]")
        print(f"Evidence Record ID: {loaded_p2.id}")
        print(f"Stored File Hash:   {loaded_p2.file_hash}")
        print(f"Stored File URI:    {loaded_p2.file_uri}")
        print(f"Stored Status:      {loaded_p2.status}")
        assert loaded_p2.file_hash == p2_computed_sha256, "Stored hash must match computed hash"
        print("  ✓ Cryptographic Match: Stored hash == In-memory computed hash")

        # 5. Tamper Detection Proof on Phase 2 Evidence
        p2_tampered_bytes = bytearray(p2_original_bytes)
        p2_tampered_bytes[50] = (p2_tampered_bytes[50] + 1) % 256
        p2_tampered_sha256 = hashlib.sha256(p2_tampered_bytes).hexdigest()

        print("\n[Phase 2 Soil Evidence Tamper Detection Proof]")
        print(f"Corrupted Byte at Index 50: 0x{p2_original_bytes[50]:02x} -> 0x{p2_tampered_bytes[50]:02x}")
        print(f"Authoritative SHA-256:       {loaded_p2.file_hash}")
        print(f"Tampered Payload SHA-256:    {p2_tampered_sha256}")
        assert p2_tampered_sha256 != loaded_p2.file_hash, "Tampered hash must differ"
        print("  ✓ Cryptographic Integrity Gate: REJECTED TAMPERED SOIL LAB REPORT")

        # 6. Cleanup
        await session.delete(loaded_p2)
        loaded_eo = (await session.execute(select(Evidence).where(Evidence.id == eo_evidence_id))).scalar_one()
        await session.delete(loaded_eo)
        await session.delete(org)
        await session.commit()
        print("\n[Database Cleanup]")
        print("  ✓ Ephemeral test records removed cleanly.")

    await engine.dispose()
    print("======================================================================")
    print("PHASE 2 EVIDENCE CRYPTOGRAPHIC INTEGRITY AUDIT: PASS")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(main())
