from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

from .repository import ProgrammeRepository
from .schemas import ProgrammeCreate, ProgrammeResponse
from .service import ProgrammeService

router = APIRouter()


def get_programme_service(db: AsyncSession = Depends(get_db)) -> ProgrammeService:
    repository = ProgrammeRepository(db)
    return ProgrammeService(repository)


@router.get("/", response_model=List[ProgrammeResponse])
async def list_programmes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    service: ProgrammeService = Depends(get_programme_service),
):
    return await service.list_programmes(skip=skip, limit=limit)


@router.post("/", response_model=ProgrammeResponse, status_code=status.HTTP_201_CREATED)
async def create_programme(
    data: ProgrammeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProgrammeService = Depends(get_programme_service),
):
    if current_user.role not in ["SUPER_ADMIN", "COMPLIANCE_ADMIN", "ORG_ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to create programmes"
        )

    return await service.create_programme(data, actor_id=current_user.id, db=db)


@router.get("/{programme_id}", response_model=ProgrammeResponse)
async def get_programme(
    programme_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: ProgrammeService = Depends(get_programme_service),
):
    programme = await service.get_programme(programme_id)
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    return programme
