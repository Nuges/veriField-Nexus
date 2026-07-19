from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import MethodologyFamily, Methodology

router = APIRouter()

@router.get("")
async def list_sectors(db: AsyncSession = Depends(get_db)):
    """Returns all sectors (MethodologyFamilies)."""
    stmt = select(MethodologyFamily)
    res = await db.execute(stmt)
    families = res.scalars().all()
    return [{"id": str(f.id), "code": f.code, "name": f.name, "description": f.description} for f in families]

@router.get("/{sector_id}")
async def get_sector(sector_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns a specific sector."""
    stmt = select(MethodologyFamily).where(MethodologyFamily.id == sector_id)
    res = await db.execute(stmt)
    family = res.scalar_one_or_none()
    if not family:
        raise HTTPException(status_code=404, detail="Sector not found")
    return {"id": str(family.id), "code": family.code, "name": family.name, "description": family.description}

@router.get("/{sector_id}/methodologies")
async def get_methodologies_by_sector(sector_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns methodologies belonging strictly to this sector."""
    stmt = select(Methodology).where(Methodology.family_id == sector_id, Methodology.is_active == True)
    res = await db.execute(stmt)
    methodologies = res.scalars().all()
    return [{"id": str(m.id), "code": m.code, "name": m.name, "description": m.description} for m in methodologies]
