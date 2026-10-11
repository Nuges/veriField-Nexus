from datetime import datetime, timezone

from typing import List, Optional

from uuid import UUID



from sqlalchemy import func, select



from app.domains.organizations.models import Organization

from app.domains.methodologies.models import MethodologyFamily, Methodology, MethodologyRegistry

from fastapi import HTTPException

from app.domains.projects.events import (publish_project_approved,

                                         publish_project_created)

from app.domains.projects.models import Project

from app.domains.projects.repository import ProjectRepository

from app.domains.projects.schemas import ProjectCreate, ProjectUpdate





class ProjectService:

    def __init__(self, repository: ProjectRepository):

        self.repository = repository



    async def get_project(

        self, project_id: UUID, organization_id: Optional[UUID] = None

    ) -> Optional[Project]:

        return await self.repository.get_by_id(project_id, organization_id)



    async def get_project_by_code(

        self, code: str, organization_id: Optional[UUID] = None

    ) -> Optional[Project]:

        return await self.repository.get_by_code(code, organization_id)



    async def list_projects(

        self, organization_id: UUID, methodology_id: Optional[UUID] = None

    ) -> List[Project]:

        return await self.repository.list_by_organization(

            organization_id, methodology_id

        )



    async def create_project(

        self, payload: ProjectCreate, organization_id: UUID

    ) -> Project:

        # Generate project code dynamically: e.g. VF-GP-001

        prefix = "GP"

        jurisdiction_id = None

        meth = None
        sector = None

        from app.core.sectors import (
            resolve_methodology_code,
            validate_methodology_version_selection,
            GLOBAL_METHODOLOGY_CATALOG,
        )

        if payload.methodology_id:
            raw_meth_str = str(payload.methodology_id).strip()
            # 1. Try DB by UUID
            try:
                meth_uuid = UUID(raw_meth_str)
                meth = await self.repository.db.get(Methodology, meth_uuid)
            except (ValueError, TypeError):
                pass

            # 2. Try resolving alias or code
            resolved_code = resolve_methodology_code(raw_meth_str) or raw_meth_str
            if not meth:
                m_res = await self.repository.db.execute(
                    select(Methodology).where(func.lower(Methodology.code) == resolved_code.lower())
                )
                meth = m_res.scalar_one_or_none()

            # 3. If in GLOBAL_METHODOLOGY_CATALOG, auto-provision methodology record in DB
            if not meth and resolved_code in GLOBAL_METHODOLOGY_CATALOG:
                import uuid as _uuid
                cat_entry = GLOBAL_METHODOLOGY_CATALOG[resolved_code]
                cat_sec = cat_entry["sector"]

                # Find or create MethodologyFamily
                s_res = await self.repository.db.execute(
                    select(MethodologyFamily).where(func.upper(MethodologyFamily.code) == cat_sec.value.upper())
                )
                sec_fam = s_res.scalar_one_or_none()
                if not sec_fam:
                    sec_fam = MethodologyFamily(
                        id=_uuid.uuid4(),
                        code=cat_sec.value,
                        name=cat_sec.value.replace("_", " ").title(),
                    )
                    self.repository.db.add(sec_fam)
                    await self.repository.db.flush()

                # Find or create MethodologyRegistry
                reg_code = cat_entry.get("registry_code", "VERRA")
                r_res = await self.repository.db.execute(
                    select(MethodologyRegistry).where(func.upper(MethodologyRegistry.code) == reg_code.upper())
                )
                reg_obj = r_res.scalar_one_or_none()
                if not reg_obj:
                    reg_obj = MethodologyRegistry(
                        id=_uuid.uuid5(_uuid.NAMESPACE_DNS, f"registry.{reg_code}"),
                        code=reg_code,
                        name=cat_entry.get("registry_name", reg_code),
                        description=cat_entry.get("registry_name"),
                        is_active=True,
                    )
                    self.repository.db.add(reg_obj)
                    await self.repository.db.flush()

                meth_id = UUID(cat_entry["id"])
                meth = Methodology(
                    id=meth_id,
                    code=cat_entry["code"],
                    name=cat_entry["name"],
                    description=cat_entry.get("description"),
                    registry_id=reg_obj.id,
                    family_id=sec_fam.id,
                    is_active=True,
                )
                self.repository.db.add(meth)
                await self.repository.db.flush()

            if not meth:
                raise HTTPException(
                    status_code=400,
                    detail="Methodology does not exist."
                )
            if not meth.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="Methodology is inactive."
                )

            sector = await self.repository.db.get(MethodologyFamily, meth.family_id)
            if not sector:
                raise HTTPException(
                    status_code=400,
                    detail="Methodology has no valid sector family."
                )
        elif payload.sector_id or payload.sector:
            # Sector-only project configuration
            if payload.sector_id:
                try:
                    sector = await self.repository.db.get(MethodologyFamily, payload.sector_id)
                except Exception:
                    pass
            if not sector and payload.sector:
                s_res = await self.repository.db.execute(
                    select(MethodologyFamily).where(func.upper(MethodologyFamily.code) == str(payload.sector).upper())
                )
                sector = s_res.scalar_one_or_none()

            if not sector:
                raise HTTPException(
                    status_code=400,
                    detail="Selected sector family does not exist."
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Sector or methodology is required to create a project."
            )

        # Enforce Sector-Methodology invariant if both are specified
        if meth and sector:
            if payload.sector_id:
                if str(payload.sector_id).lower() != str(sector.id).lower() and str(payload.sector_id).lower() != str(meth.family_id).lower():
                    raise HTTPException(
                        status_code=400,
                        detail="Selected methodology does not belong to the selected sector."
                    )
            if payload.sector:
                clean_sec = str(payload.sector).strip().upper()
                sec_code = str(sector.code).strip().upper()
                if clean_sec != sec_code and clean_sec not in sec_code and sec_code not in clean_sec:
                    raise HTTPException(
                        status_code=400,
                        detail="Selected methodology does not belong to the selected sector."
                    )

        org = await self.repository.db.get(Organization, organization_id)
        if not org:
            raise HTTPException(
                status_code=404,
                detail="Organization not found."
            )

        org_licenses = [s.upper() for s in (org.licensed_sectors or [])]
        if sector and sector.code.upper() not in org_licenses:
            raise HTTPException(
                status_code=403,
                detail=f"Organization is not licensed for sector {sector.code}."
            )

        # Check calculation engine enablement and validate methodology version
        baseline_params = dict(payload.baseline_parameters or {})
        if meth:
            baseline_params["methodology_code"] = meth.code

            # Extract requested version candidate
            version_candidate = payload.methodology_version
            if not version_candidate and payload.baseline_parameters:
                version_candidate = payload.baseline_parameters.get("methodology_version") or payload.baseline_parameters.get("version")
            if not version_candidate and payload.methodology_id and isinstance(payload.methodology_id, str) and ":" in payload.methodology_id:
                parts = payload.methodology_id.strip().split(":")
                if len(parts) >= 2 and any(c.isdigit() for c in parts[-1]):
                    version_candidate = parts[-1]

            is_ver_valid, ver_error, active_ver = validate_methodology_version_selection(meth.code, version_candidate)
            if not is_ver_valid:
                raise HTTPException(
                    status_code=400,
                    detail=ver_error,
                )

            selected_version = active_ver or version_candidate
            baseline_params["methodology_version"] = selected_version

            if meth.code.upper() in GLOBAL_METHODOLOGY_CATALOG:
                cat_entry = GLOBAL_METHODOLOGY_CATALOG[meth.code.upper()]
                calc_status = cat_entry.get("calculation_support_status", "NOT_IMPLEMENTED")
                support_state = getattr(cat_entry.get("verifield_support_state"), "value", str(cat_entry.get("verifield_support_state")))
                baseline_params["verifield_support_state"] = support_state
                baseline_params["calculation_engine_enabled"] = (calc_status == "ENABLED")
                if calc_status != "ENABLED":
                    baseline_params["calculation_note"] = "VeriField calculation engine for this methodology is not yet enabled."
                    baseline_params["calculation_engine_notes"] = baseline_params["calculation_note"]

        if payload.project_code:
            project_code = payload.project_code
        else:
            stmt = select(func.count(Project.id))
            res = await self.repository.db.execute(stmt)
            count = res.scalar() or 0
            candidate_num = count + 1
            while True:
                candidate_code = f"VF-{prefix}-{candidate_num:03d}"
                exists_stmt = select(func.count(Project.id)).where(Project.project_code == candidate_code)
                exists_res = await self.repository.db.execute(exists_stmt)
                if (exists_res.scalar() or 0) == 0:
                    project_code = candidate_code
                    break
                candidate_num += 1

        resolved_version_id = None
        if payload.methodology_version_id:
            if isinstance(payload.methodology_version_id, UUID):
                resolved_version_id = payload.methodology_version_id
            else:
                try:
                    resolved_version_id = UUID(str(payload.methodology_version_id))
                except (ValueError, TypeError):
                    resolved_version_id = None

        project = Project(
            project_code=project_code,
            name=payload.name,
            country=payload.country,
            organization_id=organization_id,
            jurisdiction_id=jurisdiction_id,
            sector_id=sector.id,
            programme_id=payload.programme_id,
            methodology_id=meth.id if meth else None,
            methodology_version_id=resolved_version_id,
            registry_id=payload.registry_id,
            baseline_source=payload.baseline_source,
            diesel_emission_factor=payload.diesel_emission_factor,
            grid_emission_factor=payload.grid_emission_factor,
            crediting_start=payload.crediting_start,
            crediting_end=payload.crediting_end,
            baseline_parameters=baseline_params,
            created_at=datetime.now(timezone.utc),
        )



        created = await self.repository.create(project)

        await publish_project_created(

            str(created.id), str(organization_id), str(created.methodology_id)

        )

        return created



    async def update_project(

        self, project_id: UUID, payload: ProjectUpdate, organization_id: UUID

    ) -> Optional[Project]:

        project = await self.repository.get_by_id(project_id, organization_id)

        if not project:

            return None



        if payload.name is not None:

            project.name = payload.name

        if payload.registry_id is not None:

            project.registry_id = payload.registry_id

        if payload.crediting_start is not None:

            project.crediting_start = payload.crediting_start

        if payload.crediting_end is not None:

            project.crediting_end = payload.crediting_end

        if payload.baseline_parameters is not None:
            existing_locked = (project.baseline_parameters or {}).get("locked_methodology_version")
            new_params = dict(payload.baseline_parameters)
            if existing_locked and existing_locked.get("status") == "LOCKED":
                new_params["locked_methodology_version"] = existing_locked
            project.baseline_parameters = new_params



        return await self.repository.update(project)



    async def approve_project(

        self, project_id: UUID, organization_id: UUID

    ) -> Optional[Project]:

        project = await self.repository.get_by_id(project_id, organization_id)

        if not project:

            return None

        # Publish project approved event (triggers signature initialization in background)

        await publish_project_approved(str(project.id), str(organization_id))

        return project



class CarbonCalculationService:

    def __init__(self, db):

        self.db = db

        from app.domains.projects.repository import CarbonCalculationRepository

        self.repository = CarbonCalculationRepository(db)



    async def create_calculation(self, payload: dict):

        return await self.repository.create(payload)



    async def get_project_ledger(self, project_id: UUID):

        return await self.repository.list_by_project(project_id)
