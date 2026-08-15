from uuid import UUID



from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.security import get_current_user

from app.db.session import get_db

from app.domains.authentication.models import User



from .repository import EvidenceRepository

from .schemas import EvidenceCreate, EvidenceResponse, EvidenceUpdate

from .service import EvidenceService



router = APIRouter()





def get_evidence_service(db: AsyncSession = Depends(get_db)) -> EvidenceService:

    repository = EvidenceRepository(db)

    return EvidenceService(repository)





@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    data: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: EvidenceService = Depends(get_evidence_service),
):
    if current_user.role != "SUPER_ADMIN":
        from sqlalchemy import select
        from app.domains.activities.models import Activity
        result = await db.execute(select(Activity).where(Activity.id == data.activity_id))
        activity = result.scalar_one_or_none()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        if activity.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Activity does not belong to your organization."
            )

    return await service.upload_evidence(data, uploader_id=current_user.id, db=db)





@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: EvidenceService = Depends(get_evidence_service),
):
    from app.core.abac import verify_abac_policy
    await verify_abac_policy(current_user, "read", "Evidence", evidence_id, db)

    evidence = await service.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence





@router.put("/{evidence_id}/verify", response_model=EvidenceResponse)
async def verify_evidence(
    evidence_id: UUID,
    data: EvidenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: EvidenceService = Depends(get_evidence_service),
):
    from app.core.abac import verify_abac_policy
    await verify_abac_policy(current_user, "review", "Evidence", evidence_id, db)

    if current_user.role not in ["SUPER_ADMIN", "VERIFIER", "COMPLIANCE_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to verify evidence")



    evidence = await service.verify_evidence(

        evidence_id, data, verifier_id=current_user.id, db=db

    )

    if not evidence:

        raise HTTPException(status_code=404, detail="Evidence not found")



    return evidence
