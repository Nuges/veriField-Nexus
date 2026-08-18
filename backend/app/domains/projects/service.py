from datetime import datetime, timezone

from typing import List, Optional

from uuid import UUID



from sqlalchemy import func, select



from app.domains.organizations.models import Organization

from app.domains.methodologies.models import MethodologyFamily, Methodology

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

        if payload.methodology_id:
            try:
                meth = await self.repository.db.get(Methodology, payload.methodology_id)
            except Exception:
                pass
            if not meth:
                m_res = await self.repository.db.execute(
                    select(Methodology).where(func.lower(Methodology.code) == str(payload.methodology_id).lower())
                )
                meth = m_res.scalar_one_or_none()
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
        elif payload.sector_id or payload.sector:
            # Resolve primary active methodology for the given sector
            sec_target = None
            if payload.sector_id:
                try:
                    sec_target = await self.repository.db.get(MethodologyFamily, payload.sector_id)
                except Exception:
                    pass
            if not sec_target and payload.sector:
                s_res = await self.repository.db.execute(
                    select(MethodologyFamily).where(func.upper(MethodologyFamily.code) == str(payload.sector).upper())
                )
                sec_target = s_res.scalar_one_or_none()

            if sec_target:
                m_res = await self.repository.db.execute(
                    select(Methodology).where(Methodology.family_id == sec_target.id, Methodology.is_active == True).order_by(Methodology.created_at.asc()).limit(1)
                )
                meth = m_res.scalar_one_or_none()

            if not meth:
                raise HTTPException(
                    status_code=400,
                    detail="No active methodology available for the selected sector."
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Methodology is required to create a project."
            )

        sector = await self.repository.db.get(MethodologyFamily, meth.family_id)
        if not sector:
            raise HTTPException(
                status_code=400,
                detail="Methodology has no valid sector family."
            )

        # Enforce Sector-Methodology invariant (project.sector_id == methodology.family_id)
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
        if sector.code.upper() not in org_licenses:
            raise HTTPException(
                status_code=403,
                detail=f"Organization is not licensed for sector {sector.code}."
            )

        stmt = select(func.count(Project.id))
        res = await self.repository.db.execute(stmt)
        count = res.scalar() or 0
        project_code = payload.project_code or f"VF-{prefix}-{count + 1:03d}"

        project = Project(
            project_code=project_code,
            name=payload.name,
            country=payload.country,
            organization_id=organization_id,
            jurisdiction_id=jurisdiction_id,
            sector_id=sector.id,
            programme_id=payload.programme_id,
            methodology_id=meth.id,
            methodology_version_id=payload.methodology_version_id,
            registry_id=payload.registry_id,
            baseline_source=payload.baseline_source,
            diesel_emission_factor=payload.diesel_emission_factor,
            grid_emission_factor=payload.grid_emission_factor,
            crediting_start=payload.crediting_start,
            crediting_end=payload.crediting_end,
            baseline_parameters=payload.baseline_parameters or {},
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

            project.baseline_parameters = payload.baseline_parameters



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
