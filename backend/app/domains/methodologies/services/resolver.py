from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily

class MethodologyResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_from_context(self, category_text: str) -> List[str]:
        """
        Dynamically resolves methodology codes based on registry metadata,
        eliminating hardcoded sector mapping.
        """
        if not category_text:
            return []
            
        stmt = (
            select(Methodology.code)
            .join(MethodologyFamily)
            .where(
                or_(
                    MethodologyFamily.name.ilike(f"%{category_text}%"),
                    MethodologyFamily.code.ilike(f"%{category_text}%"),
                    Methodology.name.ilike(f"%{category_text}%"),
                    Methodology.code.ilike(f"%{category_text}%")
                )
            )
            .distinct()
        )
        
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]
