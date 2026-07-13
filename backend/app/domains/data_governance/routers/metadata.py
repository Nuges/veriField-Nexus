from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.db.session import get_db
from app.domains.data_governance.services.metadata import DataGovernanceService

router = APIRouter()


@router.get("/assets", tags=["Data Governance"])
async def list_data_assets(
    db: AsyncSession = Depends(get_db), user=Depends(require_permission("admin:all"))
):
    """
    List all registered data assets in the Enterprise Governance Catalogue.
    Requires SUPER_ADMIN permissions.
    """
    DataGovernanceService(db)
    # Using raw query to dump all since it's a superadmin tool
    from sqlalchemy.future import select

    from app.domains.data_governance.models.metadata import DataAssetCatalogue

    result = await db.execute(select(DataAssetCatalogue))
    assets = result.scalars().all()
    return {"data_assets": assets}


@router.get("/gdpr/pii-registry", tags=["Data Governance"])
async def get_pii_registry(
    db: AsyncSession = Depends(get_db), user=Depends(require_permission("admin:all"))
):
    """
    Returns the GDPR PII Data Registry outlining all logical assets that store PII.
    """
    svc = DataGovernanceService(db)
    assets = await svc.get_pii_assets()
    return {"pii_assets": assets}
