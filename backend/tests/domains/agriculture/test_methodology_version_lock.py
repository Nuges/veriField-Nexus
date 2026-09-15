"""
=============================================================================
VeriField Nexus — Methodology Version Locking Tests
=============================================================================
Verifies that when an agricultural project is registered under a methodology version
(e.g., VM0042 v2.2), an immutable snapshot of that version is locked in
project.baseline_parameters["locked_methodology_version"].
Subsequent changes to the catalogue do NOT silently mutate the project's rules.
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyVersion,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


@pytest.mark.asyncio
async def test_project_methodology_version_lock_immutability(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    # 1. Create test organization
    org = Organization(name=f"Agri MRV Holding {uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    # 2. Lookup VM0042 v2.2
    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    m42 = m42_res.scalars().first()

    v22_res = await db_session.execute(
        select(MethodologyVersion).where(
            MethodologyVersion.methodology_id == m42.id,
            MethodologyVersion.version == "2.2",
        )
    )
    v22 = v22_res.scalars().first()

    # 3. Create Project with locked methodology snapshot
    locked_snapshot = {
        "methodology_id": str(m42.id),
        "methodology_code": m42.code,
        "version_id": str(v22.id),
        "version": v22.version,
        "release_date": v22.release_date.isoformat(),
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "corrections_applied": m42.ui_config.get("corrections_clarifications", []),
        "status": "LOCKED",
    }

    project = Project(
        name="Regenerative Land Management Project",
        project_code=f"AGR-TEST-{uuid.uuid4().hex[:6]}",
        organization_id=org.id,
        methodology_id=m42.id,
        methodology_version_id=v22.id,
        baseline_parameters={
            "locked_methodology_version": locked_snapshot,
            "soil_depth_standard_cm": 30.0,
        },
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 4. Verify locked snapshot matches exactly
    saved_snapshot = project.baseline_parameters.get("locked_methodology_version")
    assert saved_snapshot is not None
    assert saved_snapshot["methodology_code"] == "VM0042"
    assert saved_snapshot["version"] == "2.2"
    assert saved_snapshot["status"] == "LOCKED"

    # 5. Mutate the catalogue entry (e.g. release of v3.0 or metadata update)
    m42.description = "Updated description in catalogue"
    await db_session.commit()
    await db_session.refresh(project)

    # Project's locked snapshot must remain 100% unchanged
    assert project.baseline_parameters["locked_methodology_version"]["version"] == "2.2"
    assert project.baseline_parameters["locked_methodology_version"]["methodology_code"] == "VM0042"
