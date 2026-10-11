import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_access_request_approval_decoupled_from_methodology(
    async_client: AsyncClient, admin_token_headers: dict
):
    """Verifies that an access request without a methodology can be approved smoothly,
    provisioning the organization, user, role, and sector entitlements."""
    unique_email = f"decoupled_{uuid.uuid4().hex[:8]}@example.com"
    req_payload = {
        "full_name": "Decoupled Org Admin",
        "email": unique_email,
        "organization_name": f"Decoupled Enterprise {uuid.uuid4().hex[:4]}",
        "country": "Nigeria",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": None,
        "project_name": "Flexible Carbon Asset",
    }
    create_res = await async_client.post("/api/v1/access-requests", json=req_payload)
    assert create_res.status_code == 200, create_res.text

    # Fetch request ID
    get_res = await async_client.get("/api/v1/access-requests", headers=admin_token_headers)
    assert get_res.status_code == 200
    items = get_res.json()
    match = next((item for item in items if item["email"] == unique_email), None)
    assert match is not None
    req_id = match["id"]

    # Super admin approves via /api/v1/admin/access-requests/{request_id}/approve
    approve_res = await async_client.post(
        f"/api/v1/admin/access-requests/{req_id}/approve",
        headers=admin_token_headers,
    )
    assert approve_res.status_code == 200, approve_res.text
    approval_data = approve_res.json()
    assert approval_data["status"] == "APPROVED"
    assert "user_id" in approval_data
    assert "organization_id" in approval_data


@pytest.mark.asyncio
async def test_access_request_approval_with_stale_uuid_alias(
    async_client: AsyncClient, admin_token_headers: dict
):
    """Verifies that an access request submitted with the stale UUID alias
    'ec739cc0-517a-4fa0-9ff3-ed4cc6d17667' resolves to VM0042 without throwing an error."""
    unique_email = f"alias_{uuid.uuid4().hex[:8]}@example.com"
    req_payload = {
        "full_name": "Alias Org Admin",
        "email": unique_email,
        "organization_name": f"Alias Enterprise {uuid.uuid4().hex[:4]}",
        "country": "Kenya",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667",
        "project_name": "Grassland Restoration Asset",
    }
    create_res = await async_client.post("/api/v1/access-requests", json=req_payload)
    assert create_res.status_code == 200, create_res.text

    get_res = await async_client.get("/api/v1/access-requests", headers=admin_token_headers)
    assert get_res.status_code == 200
    match = next((item for item in get_res.json() if item["email"] == unique_email), None)
    assert match is not None
    req_id = match["id"]

    # Super admin approves - must not crash with missing methodology error
    approve_res = await async_client.post(
        f"/api/v1/admin/access-requests/{req_id}/approve",
        headers=admin_token_headers,
    )
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_methodology_catalog_and_filtering_endpoints(async_client: AsyncClient):
    """Verifies normalized catalog endpoints, sector filtering, registry filtering, and sub-routes."""
    # 1. List methodologies
    all_res = await async_client.get("/api/v1/methodologies")
    assert all_res.status_code == 200
    all_data = all_res.json()
    assert isinstance(all_data, list)
    assert len(all_data) >= 5

    # 2. Sector filtering
    agri_res = await async_client.get("/api/v1/methodologies?sector=AGRICULTURE_LAND_USE")
    assert agri_res.status_code == 200
    agri_data = agri_res.json()
    agri_codes = {m["code"] for m in agri_data}
    assert "VM0042" in agri_codes
    assert "VM0051" in agri_codes
    assert "VM0047" in agri_codes
    assert "VM0032" in agri_codes

    # 3. Registry filtering
    verra_res = await async_client.get("/api/v1/methodologies?registry=VERRA")
    assert verra_res.status_code == 200
    verra_data = verra_res.json()
    assert len(verra_data) >= 4
    for item in verra_data:
        reg_code = item.get("registry_code") or (item.get("registry", {}).get("code") if isinstance(item.get("registry"), dict) else "")
        assert reg_code in ("VERRA", "VCS")

    # 4. Detail endpoint by code
    vm42_res = await async_client.get("/api/v1/methodologies/VM0042")
    assert vm42_res.status_code == 200
    vm42_data = vm42_res.json()
    assert vm42_data["code"] == "VM0042"
    support_state = vm42_data.get("verifield_support_state") or vm42_data.get("ui_config", {}).get("verifield_support_state")
    assert support_state == "FULL"

    # 5. Detail endpoint by stale alias
    alias_res = await async_client.get("/api/v1/methodologies/ec739cc0-517a-4fa0-9ff3-ed4cc6d17667")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert alias_data["code"] == "VM0042"

    # 6. Versions sub-route
    ver_res = await async_client.get("/api/v1/methodologies/VM0042/versions")
    assert ver_res.status_code == 200
    ver_data = ver_res.json()
    assert isinstance(ver_data, list)
    versions = [v["version"] for v in ver_data]
    assert "2.1" in versions or "2.2" in versions

    # 7. Applicability sub-route
    app_res = await async_client.get("/api/v1/methodologies/VM0042/applicability")
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert "applicability_summary" in app_data

    # 8. Capabilities sub-route: VM0042 is FULL, VM0051 is MRV_ONLY
    cap42_res = await async_client.get("/api/v1/methodologies/VM0042/capabilities")
    assert cap42_res.status_code == 200
    cap42 = cap42_res.json()
    assert cap42["calculation_engine_enabled"] is True
    assert cap42["verifield_support_state"] == "FULL"

    cap51_res = await async_client.get("/api/v1/methodologies/VM0051/capabilities")
    assert cap51_res.status_code == 200
    cap51 = cap51_res.json()
    assert cap51["calculation_engine_enabled"] is False
    assert cap51["verifield_support_state"] == "MRV_ONLY"
    assert "not yet enabled" in cap51["calculation_engine_notes"]


@pytest.mark.asyncio
async def test_project_creation_methodology_capabilities_and_gating(db_session):
    """Verifies that project creation dynamically sets calculation capability:
    - VM0042: calculation_engine_enabled = True
    - VM0051: calculation_engine_enabled = False (MRV Only)
    - VM0047: calculation_engine_enabled = False (MRV Only)
    - Stale UUID alias ec739cc0-517a-4fa0-9ff3-ed4cc6d17667 resolves cleanly
    """
    from app.domains.projects.service import ProjectService
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.schemas import ProjectCreate
    from app.domains.organizations.models import Organization

    repo = ProjectRepository(db_session)
    svc = ProjectService(repo)

    # 1. Create test organization licensed for agriculture
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Test Agri Org {uuid.uuid4().hex[:6]}",
        org_type="Project Developer",
        plan="PRO",
        licensed_sectors=["AGRICULTURE_LAND_USE"],
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.commit()

    # 2. Create project with VM0042
    p_vm42 = await svc.create_project(
        ProjectCreate(
            name="Agri VM0042 Project",
            country="Nigeria",
            methodology_id=uuid.UUID("f238258b-f8ec-4e5a-91cf-7537422796d3"),
        ),
        organization_id=org_id,
    )
    assert p_vm42.baseline_parameters.get("calculation_engine_enabled") is True
    assert p_vm42.baseline_parameters.get("methodology_code") == "VM0042"

    # 3. Create project with VM0051 (Rice)
    p_vm51 = await svc.create_project(
        ProjectCreate(
            name="Rice VM0051 Project",
            country="Nigeria",
            methodology_id=uuid.UUID("615f5d40-f86a-4fdb-af23-d9f79d90d159"),
        ),
        organization_id=org_id,
    )
    assert p_vm51.baseline_parameters.get("calculation_engine_enabled") is False
    assert "not yet enabled" in p_vm51.baseline_parameters.get("calculation_engine_notes", "")
    assert p_vm51.baseline_parameters.get("methodology_code") == "VM0051"

    # 4. Create project with VM0047 (ARR)
    p_vm47 = await svc.create_project(
        ProjectCreate(
            name="Forestry VM0047 Project",
            country="Kenya",
            methodology_id=uuid.UUID("9cc408db-c2bd-4df3-b488-44e8cff7fb73"),
        ),
        organization_id=org_id,
    )
    assert p_vm47.baseline_parameters.get("calculation_engine_enabled") is False
    assert "not yet enabled" in p_vm47.baseline_parameters.get("calculation_engine_notes", "")
    assert p_vm47.baseline_parameters.get("methodology_code") == "VM0047"

    # 5. Create project using stale UUID alias
    p_alias = await svc.create_project(
        ProjectCreate(
            name="Stale Alias Project",
            country="Nigeria",
            methodology_id=uuid.UUID("ec739cc0-517a-4fa0-9ff3-ed4cc6d17667"),
        ),
        organization_id=org_id,
    )
    assert p_alias.baseline_parameters.get("methodology_code") == "VM0042"
    assert p_alias.baseline_parameters.get("calculation_engine_enabled") is True


def test_cross_sector_negative_invariants_and_supporting_tools():
    """Section 14: Verifies cross-sector negative assertions and supporting module separation."""
    from app.core.sectors import is_methodology_valid_for_sector

    # 1. Cannot create Cookstove project using VM0042
    valid_cs_42, reason_cs_42 = is_methodology_valid_for_sector("COOKSTOVES", "VM0042")
    assert valid_cs_42 is False
    assert "belongs to sector 'Agriculture & Land Use'" in reason_cs_42

    # 2. Cannot create EV project using VM0044
    valid_ev_44, reason_ev_44 = is_methodology_valid_for_sector("EV_MOBILITY", "VM0044")
    assert valid_ev_44 is False
    assert "belongs to sector 'Biochar Carbon Removal'" in reason_ev_44

    # 3. Cannot create Agriculture project using AMS-I.F
    valid_ag_am1, reason_ag_am1 = is_methodology_valid_for_sector("AGRICULTURE_LAND_USE", "AMS_I_F")
    assert valid_ag_am1 is False
    assert "belongs to sector 'Hybrid Energy & Mini-grids'" in reason_ag_am1

    # 4. Cannot create Biochar project using VM0038
    valid_bc_38, reason_bc_38 = is_methodology_valid_for_sector("BIOCHAR", "VM0038")
    assert valid_bc_38 is False
    assert "belongs to sector 'EV Mobility'" in reason_bc_38

    # 5. Supporting modules cannot be selected as primary methodology
    disallowed = ["VMD0049", "VT0014", "VMD0053", "VMD0054", "BM_T_001", "GS_AGRI_ACT_REQ"]
    for tool_code in disallowed:
        valid_tool, reason_tool = is_methodology_valid_for_sector("AGRICULTURE_LAND_USE", tool_code)
        assert valid_tool is False, f"Supporting tool {tool_code} must not be valid as primary"
        assert "supporting module/tool" in reason_tool

        valid_ev_tool, reason_ev_tool = is_methodology_valid_for_sector("EV_MOBILITY", tool_code)
        assert valid_ev_tool is False
        assert "supporting module/tool" in reason_ev_tool


@pytest.mark.asyncio
async def test_all_canonical_sector_capabilities_and_applicability_endpoints(async_client: AsyncClient):
    """Verifies capabilities and applicability endpoints for all 15 authoritative methodologies across all 5 sectors."""
    matrix = [
        # (code, expected_support, expected_calc_enabled, expected_version, expected_stable_id)
        ("VM0042", "FULL", True, "2.2", "VERRA:VM0042:2.2"),
        ("VM0051", "MRV_ONLY", False, "1.1", "VERRA:VM0051:1.1"),
        ("VM0047", "MRV_ONLY", False, "1.1", "VERRA:VM0047:1.1"),
        ("VM0032", "CATALOG_ONLY", False, "1.0", "VERRA:VM0032:1.0"),
        ("VM0044", "FULL", True, "1.2", "VERRA:VM0044:1.2"),
        ("PURO_BIOCHAR_2025", "FULL", True, "Edition 2025 v2", "PURO_STANDARD:PURO_BIOCHAR_2025:2025"),
        ("BIOCHAR_C_SINK", "CATALOG_ONLY", False, "3.3", "CSI:BIOCHAR_C_SINK:3.3"),
        ("GS_MECD", "MRV_ONLY", False, "2.0", "GOLD_STANDARD:GS_MECD:2.0"),
        ("VM0050", "CATALOG_ONLY", False, "1.0", "VERRA:VM0050:1.0"),
        ("AMS_II_G", "CATALOG_ONLY", False, "14.0", "UNFCCC:AMS-II.G:14.0"),
        ("AMS_I_F", "MRV_ONLY", False, "5.0", "UNFCCC:AMS-I.F:5.0"),
        ("AMS_I_L", "CATALOG_ONLY", False, "5.0", "UNFCCC:AMS-I.L:5.0"),
        ("ACM0002", "CATALOG_ONLY", False, "22.0", "UNFCCC:ACM0002:22.0"),
        ("VM0038", "MRV_ONLY", False, "1.1", "VERRA:VM0038:1.1"),
        ("AMS_III_C", "CATALOG_ONLY", False, "16.0", "UNFCCC:AMS-III.C:16.0"),
    ]

    for code, exp_support, exp_calc, exp_ver, exp_stable_id in matrix:
        # Capabilities
        cap_res = await async_client.get(f"/api/v1/methodologies/{code}/capabilities")
        assert cap_res.status_code == 200, f"Failed capabilities for {code}: {cap_res.text}"
        cap_data = cap_res.json()
        assert cap_data["verifield_support_state"] == exp_support, f"Support mismatch for {code}"
        assert cap_data["calculation_engine_enabled"] is exp_calc, f"Calc engine mismatch for {code}"
        assert cap_data["current_version"] == exp_ver, f"Version mismatch for {code}: expected {exp_ver}, got {cap_data.get('current_version')}"
        assert cap_data["stable_identifier"] == exp_stable_id, f"Stable ID mismatch for {code}"
        assert cap_data["selectable_for_new_projects"] is True
        assert cap_data["last_verified_at"] == "2026-10-11"
        assert cap_data["source_authority"] is not None
        if not exp_calc:
            assert "not yet enabled" in cap_data["calculation_engine_notes"]
        else:
            assert "active" in cap_data["calculation_engine_notes"].lower()

        # Applicability
        app_res = await async_client.get(f"/api/v1/methodologies/{code}/applicability")
        assert app_res.status_code == 200, f"Failed applicability for {code}: {app_res.text}"
        app_data = app_res.json()
        assert "applicability_summary" in app_data
        assert len(app_data["applicability_summary"]) > 10


@pytest.mark.asyncio
async def test_gated_sectors_project_creation_has_disabled_calculations(db_session):
    """Verifies that project creation in gated sectors strictly produces calculation_engine_enabled = False."""
    from app.domains.projects.service import ProjectService
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.schemas import ProjectCreate
    from app.domains.organizations.models import Organization

    repo = ProjectRepository(db_session)
    svc = ProjectService(repo)

    # 1. Organization licensed for all 5 sectors
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Global Multi-Sector Org {uuid.uuid4().hex[:6]}",
        org_type="Project Developer",
        plan="PRO",
        licensed_sectors=[
            "COOKSTOVES",
            "HYBRID_ENERGY",
            "BIOCHAR",
            "EV_MOBILITY",
            "AGRICULTURE_LAND_USE",
        ],
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.commit()

    # 2. Cookstove project with GS_MECD (ID: 183ce6d6-d193-41ca-be0e-1096e1971c69 in DB)
    p_cs = await svc.create_project(
        ProjectCreate(
            name="Cookstove Pilot Project",
            country="Kenya",
            methodology_id=uuid.UUID("183ce6d6-d193-41ca-be0e-1096e1971c69"),
        ),
        organization_id=org_id,
    )
    assert p_cs.baseline_parameters.get("calculation_engine_enabled") is False
    assert "not yet enabled" in p_cs.baseline_parameters.get("calculation_engine_notes", "")

    # 3. Hybrid energy project with AMS_I_F (ID: b007c7e9-2f2a-4155-85ae-371d66c97152 in DB)
    p_he = await svc.create_project(
        ProjectCreate(
            name="Minigrid Solar-Diesel Project",
            country="Nigeria",
            methodology_id=uuid.UUID("b007c7e9-2f2a-4155-85ae-371d66c97152"),
        ),
        organization_id=org_id,
    )
    assert p_he.baseline_parameters.get("calculation_engine_enabled") is False
    assert "not yet enabled" in p_he.baseline_parameters.get("calculation_engine_notes", "")

    # 4. EV mobility project with VM0038 (ID: f835e2ce-630d-4479-97ad-ef0a25e405af in DB)
    p_ev = await svc.create_project(
        ProjectCreate(
            name="EV Fleet Charging Project",
            country="Rwanda",
            methodology_id=uuid.UUID("f835e2ce-630d-4479-97ad-ef0a25e405af"),
        ),
        organization_id=org_id,
    )
    assert p_ev.baseline_parameters.get("calculation_engine_enabled") is False
    assert "not yet enabled" in p_ev.baseline_parameters.get("calculation_engine_notes", "")

    # 5. Biochar project with VM0044 (ID: cd093f0e-0353-449e-a56b-484398ea0f9e in DB)
    p_bc = await svc.create_project(
        ProjectCreate(
            name="Biochar Pyrolysis Project",
            country="Germany",
            methodology_id=uuid.UUID("cd093f0e-0353-449e-a56b-484398ea0f9e"),
        ),
        organization_id=org_id,
    )
    assert p_bc.baseline_parameters.get("calculation_engine_enabled") is True


@pytest.mark.asyncio
async def test_authoritative_methodology_version_selection_and_historical_rejection(db_session):
    """Verifies that new project creation strictly guards against selecting historical methodology versions:
    - Cookstoves AMS-II.G: reject v13.0, allow v14.0
    - Hybrid Energy AMS-I.L: reject v3.0, allow v5.0
    - Hybrid Energy ACM0002: reject v21.0, allow v22.0
    """
    from app.domains.projects.service import ProjectService
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.schemas import ProjectCreate
    from app.domains.organizations.models import Organization
    from fastapi import HTTPException

    repo = ProjectRepository(db_session)
    svc = ProjectService(repo)

    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Version Selection Enterprise {uuid.uuid4().hex[:6]}",
        org_type="Project Developer",
        plan="PRO",
        licensed_sectors=["COOKSTOVES", "HYBRID_ENERGY", "AGRICULTURE_LAND_USE"],
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.commit()

    # 1. Clean Cookstoves: Reject AMS-II.G v13.0
    with pytest.raises(HTTPException) as exc_info:
        await svc.create_project(
            ProjectCreate(
                name="Cookstoves Rejected v13",
                country="Kenya",
                methodology_id=uuid.UUID("9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98"),
                methodology_version="13.0",
            ),
            organization_id=org_id,
        )
    assert exc_info.value.status_code == 400
    assert "Version '13.0' of AMS_II_G is historical/inactive and cannot be selected for new projects. Active version is 14.0." in str(exc_info.value.detail)

    # 2. Clean Cookstoves: Allow AMS-II.G v14.0
    p_cs_active = await svc.create_project(
        ProjectCreate(
            name="Cookstoves Active v14",
            country="Kenya",
            methodology_id=uuid.UUID("9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98"),
            methodology_version="14.0",
        ),
        organization_id=org_id,
    )
    assert p_cs_active.baseline_parameters.get("methodology_version") == "14.0"

    # 3. Hybrid Energy: Reject AMS-I.L v3.0
    with pytest.raises(HTTPException) as exc_il:
        await svc.create_project(
            ProjectCreate(
                name="Hybrid Rejected v3",
                country="Nigeria",
                methodology_id=uuid.UUID("cfed120a-8ed3-554d-9bfa-86e62b8fd4cf"),
                methodology_version="3.0",
            ),
            organization_id=org_id,
        )
    assert exc_il.value.status_code == 400
    assert "Version '3.0' of AMS_I_L is historical/inactive and cannot be selected for new projects. Active version is 5.0." in str(exc_il.value.detail)

    # 4. Hybrid Energy: Allow AMS-I.L v5.0
    p_il_active = await svc.create_project(
        ProjectCreate(
            name="Hybrid Active v5",
            country="Nigeria",
            methodology_id=uuid.UUID("cfed120a-8ed3-554d-9bfa-86e62b8fd4cf"),
            methodology_version="5.0",
        ),
        organization_id=org_id,
    )
    assert p_il_active.baseline_parameters.get("methodology_version") == "5.0"

    # 5. Hybrid Energy: Reject ACM0002 v21.0
    with pytest.raises(HTTPException) as exc_acm:
        await svc.create_project(
            ProjectCreate(
                name="Grid Renewable Rejected v21",
                country="Ghana",
                methodology_id=uuid.UUID("4b131d9b-3d26-5870-aa53-c97fd58b8020"),
                methodology_version="21.0",
            ),
            organization_id=org_id,
        )
    assert exc_acm.value.status_code == 400
    assert "Version '21.0' of ACM0002 is historical/inactive and cannot be selected for new projects. Active version is 22.0." in str(exc_acm.value.detail)

    # 6. Hybrid Energy: Allow ACM0002 v22.0
    p_acm_active = await svc.create_project(
        ProjectCreate(
            name="Grid Renewable Active v22",
            country="Ghana",
            methodology_id=uuid.UUID("4b131d9b-3d26-5870-aa53-c97fd58b8020"),
            methodology_version="22.0",
        ),
        organization_id=org_id,
    )
    assert p_acm_active.baseline_parameters.get("methodology_version") == "22.0"

    # 7. Defaulting when version omitted: automatically provisions active version
    p_def = await svc.create_project(
        ProjectCreate(
            name="Cookstoves Default Version",
            country="Kenya",
            methodology_id=uuid.UUID("9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98"),
        ),
        organization_id=org_id,
    )
    assert p_def.baseline_parameters.get("methodology_version") == "14.0"


@pytest.mark.asyncio
async def test_historical_project_reading_preserves_immutable_version_without_migration(db_session):
    """Verifies that an existing project storing historical version metadata (e.g. v13.0 or v21.0)
    continues to be read cleanly by the service without failing or undergoing silent migration."""
    from app.domains.projects.service import ProjectService
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.models import Project
    from app.domains.organizations.models import Organization

    repo = ProjectRepository(db_session)
    svc = ProjectService(repo)

    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Historical Reading Org {uuid.uuid4().hex[:6]}",
        org_type="Project Developer",
        plan="PRO",
        licensed_sectors=["COOKSTOVES"],
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.commit()

    # Pre-existing project created under historical v13.0 regime
    hist_proj_id = uuid.uuid4()
    hist_proj = Project(
        id=hist_proj_id,
        project_code=f"VF-HIST-{uuid.uuid4().hex[:6]}",
        name="Historical Cookstove Project v13",
        country="Uganda",
        organization_id=org_id,
        sector_id=uuid.UUID("dff43d66-631b-4f08-8763-aaab12d0d5ee"),
        methodology_id=uuid.UUID("9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98"),
        baseline_parameters={
            "methodology_code": "AMS_II_G",
            "methodology_version": "13.0",
            "status": "HISTORICAL_RECORDS_PRESERVED",
        },
    )
    db_session.add(hist_proj)
    await db_session.commit()

    # Read project via service
    loaded = await svc.get_project(hist_proj_id, organization_id=org_id)
    assert loaded is not None
    assert loaded.id == hist_proj_id
    # Crucial regression protection: No silent migration to 14.0
    assert loaded.baseline_parameters.get("methodology_version") == "13.0"
    assert loaded.baseline_parameters.get("status") == "HISTORICAL_RECORDS_PRESERVED"


