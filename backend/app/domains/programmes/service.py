from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.programmes.models import ClimateProgramme
from app.domains.programmes.repository import ProgrammeRepository
from app.domains.programmes.schemas import ProgrammeCreate


class ProgrammeService:
    def __init__(self, repository: ProgrammeRepository):
        self.repository = repository

    async def get_programme(self, programme_id: UUID) -> Optional[ClimateProgramme]:
        return await self.repository.get_by_id(programme_id)

    async def list_programmes(
        self, skip: int = 0, limit: int = 100
    ) -> List[ClimateProgramme]:
        return await self.repository.list_all(skip=skip, limit=limit)

    async def create_programme(
        self,
        payload: ProgrammeCreate,
        actor_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> ClimateProgramme:
        programme = ClimateProgramme(
            name=payload.name,
            org_id=payload.org_id,
            jurisdiction_id=payload.jurisdiction_id,
            funding_sources=payload.funding_sources,
            budget=payload.budget,
            status=payload.status,
            version=payload.version,
        )
        return await self.repository.create(programme)
