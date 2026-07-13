from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.data_governance.models.metadata import DataAssetCatalogue


class DataGovernanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_asset(
        self,
        asset_name: str,
        domain_owner: str,
        pii_fields: List[str] = None,
        retention_days: int = 2555,
    ) -> DataAssetCatalogue:
        """Registers a new logical data asset into the enterprise governance catalogue."""
        existing = await self.db.execute(
            select(DataAssetCatalogue).where(
                DataAssetCatalogue.asset_name == asset_name
            )
        )
        asset = existing.scalars().first()

        if not asset:
            asset = DataAssetCatalogue(
                asset_name=asset_name,
                domain_owner=domain_owner,
                contains_pii=bool(pii_fields),
                pii_fields=pii_fields or [],
                retention_period_days=retention_days,
            )
            self.db.add(asset)
            await self.db.commit()
            await self.db.refresh(asset)

        return asset

    async def get_pii_assets(self) -> List[DataAssetCatalogue]:
        """Fetches all assets containing PII for GDPR audits."""
        result = await self.db.execute(
            select(DataAssetCatalogue).where(DataAssetCatalogue.contains_pii)
        )
        return result.scalars().all()
