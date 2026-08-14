from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func

from typing import List, Optional

from uuid import UUID



from app.db.session import get_db

from app.core.security import get_current_user

from app.domains.authentication.models import User

from app.core.abac import ABACEngine

from app.domains.projects.models import Project

from app.domains.biochar.models import BiocharBatch, BiocharInventory

from app.domains.biochar.schemas import BiocharBatchCreate, BiocharBatchResponse, BiocharSummaryResponse

from app.domains.biochar.service import BiocharQuantificationEngine



router = APIRouter()



@router.post("/batches", response_model=BiocharBatchResponse, status_code=status.HTTP_201_CREATED)

async def create_biochar_batch(

    data: BiocharBatchCreate,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    abac = ABACEngine(db, current_user)

    await abac.enforce_project_access(data.project_id)



    net_co2e, perm_factor, grade, has_anomaly, anomaly_reason = BiocharQuantificationEngine.calculate_removal_and_grade(data)



    from datetime import datetime, timezone

    batch = BiocharBatch(

        project_id=data.project_id,

        created_at=datetime.now(timezone.utc),

        batch_number=data.batch_number,

        facility_name=data.facility_name,

        kiln_id=data.kiln_id,

        feedstock_type=data.feedstock_type,

        feedstock_weight_tonnes=data.feedstock_weight_tonnes,

        moisture_content_pct=data.moisture_content_pct,

        origin_location=data.origin_location,

        pyrolysis_temp_celsius=data.pyrolysis_temp_celsius,

        residence_time_minutes=data.residence_time_minutes,

        biochar_yield_tonnes=data.biochar_yield_tonnes,

        fixed_carbon_pct=data.fixed_carbon_pct,

        ash_content_pct=data.ash_content_pct,

        molar_h_c_ratio=data.molar_h_c_ratio,

        carbon_permanence_factor=perm_factor,

        net_co2e_removed_tonnes=net_co2e,

        quality_grade=grade,

        lab_report_number=data.lab_report_number,

        lab_document_url=data.lab_document_url,

        has_anomaly=has_anomaly,

        anomaly_reason=anomaly_reason,

        status="PRODUCED",

    )

    db.add(batch)

    await db.commit()

    await db.refresh(batch)

    return batch



@router.get("/batches", response_model=List[BiocharBatchResponse])

async def list_biochar_batches(

    project_id: Optional[UUID] = None,

    limit: int = 50,

    offset: int = 0,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    stmt = select(BiocharBatch)

    if project_id:

        abac = ABACEngine(db, current_user)

        await abac.enforce_project_access(project_id)

        stmt = stmt.where(BiocharBatch.project_id == project_id)

    elif current_user.role != "SUPER_ADMIN":

        if not current_user.organization_id:

            return []

        org_projects = select(Project.id).where(Project.organization_id == current_user.organization_id)

        stmt = stmt.where(BiocharBatch.project_id.in_(org_projects))



    stmt = stmt.order_by(BiocharBatch.created_at.desc()).limit(limit).offset(offset)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.get("/summary", response_model=BiocharSummaryResponse)

async def get_biochar_summary(

    project_id: Optional[UUID] = None,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    stmt = select(

        func.count(BiocharBatch.id).label("total_batches"),

        func.coalesce(func.sum(BiocharBatch.feedstock_weight_tonnes), 0.0).label("total_feedstock"),

        func.coalesce(func.sum(BiocharBatch.biochar_yield_tonnes), 0.0).label("total_yield"),

        func.coalesce(func.sum(BiocharBatch.net_co2e_removed_tonnes), 0.0).label("total_co2e"),

        func.count(BiocharBatch.id).filter(BiocharBatch.quality_grade == "GRADE_A").label("grade_a_count"),

        func.count(BiocharBatch.id).filter(BiocharBatch.has_anomaly == True).label("anomaly_count"),

    )



    if project_id:

        abac = ABACEngine(db, current_user)

        await abac.enforce_project_access(project_id)

        stmt = stmt.where(BiocharBatch.project_id == project_id)

    elif current_user.role != "SUPER_ADMIN":

        if not current_user.organization_id:

            return {

                "total_batches": 0,

                "total_feedstock_tonnes": 0.0,

                "total_biochar_produced_tonnes": 0.0,

                "total_net_co2e_removed_tonnes": 0.0,

                "grade_a_percentage": 0.0,

                "detected_anomalies_count": 0,

            }

        org_projects = select(Project.id).where(Project.organization_id == current_user.organization_id)

        stmt = stmt.where(BiocharBatch.project_id.in_(org_projects))



    res = await db.execute(stmt)

    row = res.one()



    total_b = row.total_batches or 0

    grade_a_pct = (row.grade_a_count / total_b * 100.0) if total_b > 0 else 0.0



    return {

        "total_batches": total_b,

        "total_feedstock_tonnes": float(row.total_feedstock),

        "total_biochar_produced_tonnes": float(row.total_yield),

        "total_net_co2e_removed_tonnes": float(row.total_co2e),

        "grade_a_percentage": round(grade_a_pct, 1),

        "detected_anomalies_count": row.anomaly_count or 0,

    }
