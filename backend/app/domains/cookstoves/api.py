from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func

from typing import List, Optional

from uuid import UUID



from app.db.session import get_db

from app.domains.cookstoves.models import HouseholdBeneficiary, CookstoveDevice, UsageSurvey

from app.domains.cookstoves.schemas import HouseholdCreate, CookstoveDeviceCreate, UsageSurveyCreate, UsageSurveyResponse, CookstoveSummaryResponse

from app.domains.cookstoves.service import CookstoveQuantificationEngine



router = APIRouter()



@router.post("/households", status_code=status.HTTP_201_CREATED)

async def register_household(

    data: HouseholdCreate,

    db: AsyncSession = Depends(get_db)

):

    hh = HouseholdBeneficiary(**data.model_dump())

    db.add(hh)

    await db.commit()

    await db.refresh(hh)

    return hh



@router.get("/households")

async def list_households(

    project_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    stmt = select(HouseholdBeneficiary)

    if project_id:

        stmt = stmt.where(HouseholdBeneficiary.project_id == project_id)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.post("/devices", status_code=status.HTTP_201_CREATED)

async def register_cookstove_device(

    data: CookstoveDeviceCreate,

    db: AsyncSession = Depends(get_db)

):

    stove = CookstoveDevice(**data.model_dump())

    db.add(stove)

    await db.commit()

    await db.refresh(stove)

    return stove



@router.get("/devices")

async def list_cookstove_devices(

    household_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    stmt = select(CookstoveDevice)

    if household_id:

        stmt = stmt.where(CookstoveDevice.household_id == household_id)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.post("/surveys", response_model=UsageSurveyResponse, status_code=status.HTTP_201_CREATED)

async def record_usage_survey(

    data: UsageSurveyCreate,

    db: AsyncSession = Depends(get_db)

):

    stove = await db.get(CookstoveDevice, data.stove_id)

    if not stove:

        raise HTTPException(status_code=404, detail="Cookstove Device not found")



    hh = await db.get(HouseholdBeneficiary, stove.household_id)

    if not hh:

        raise HTTPException(status_code=404, detail="Household Beneficiary not found")



    reduction_tco2e, has_fraud, fraud_reason = CookstoveQuantificationEngine.calculate_emissions_reduction(data, hh, stove)



    survey = UsageSurvey(

        stove_id=data.stove_id,

        surveyor_user_id=data.surveyor_user_id,

        survey_date=data.survey_date,

        is_stove_in_use=data.is_stove_in_use,

        reported_daily_usage_hours=data.reported_daily_usage_hours,

        fuel_consumed_kg_per_day=data.fuel_consumed_kg_per_day,

        thermal_tampering_detected=data.thermal_tampering_detected,

        is_primary_cooking_method=data.is_primary_cooking_method,

        calculated_co2e_reduction_tonnes=reduction_tco2e,

        has_fraud_flag=has_fraud,

        fraud_reason=fraud_reason

    )

    db.add(survey)

    await db.commit()

    await db.refresh(survey)

    return survey



@router.get("/summary", response_model=CookstoveSummaryResponse)

async def get_cookstoves_summary(

    project_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    hh_stmt = select(func.count(HouseholdBeneficiary.id))

    if project_id:

        hh_stmt = hh_stmt.where(HouseholdBeneficiary.project_id == project_id)

    total_hh = (await db.execute(hh_stmt)).scalar() or 0



    st_stmt = select(func.count(CookstoveDevice.id))

    if project_id:

        st_stmt = st_stmt.join(HouseholdBeneficiary).where(HouseholdBeneficiary.project_id == project_id)

    total_st = (await db.execute(st_stmt)).scalar() or 0



    surv_stmt = select(

        func.count(UsageSurvey.id).label("total_surveys"),

        func.count(UsageSurvey.id).filter(UsageSurvey.is_stove_in_use == True).label("active_surveys"),

        func.coalesce(func.sum(UsageSurvey.calculated_co2e_reduction_tonnes), 0.0).label("total_co2e"),

        func.count(UsageSurvey.id).filter(UsageSurvey.has_fraud_flag == True).label("fraud_count")

    )

    if project_id:

        surv_stmt = surv_stmt.join(CookstoveDevice).join(HouseholdBeneficiary).where(HouseholdBeneficiary.project_id == project_id)



    res = await db.execute(surv_stmt)

    row = res.one()



    tot_surv = row.total_surveys or 0

    active_rate = (row.active_surveys / tot_surv * 100.0) if tot_surv > 0 else 100.0



    return {

        "total_households": total_hh,

        "total_stoves_deployed": total_st,

        "active_usage_rate_pct": round(active_rate, 1),

        "total_co2e_reduced_tonnes": float(row.total_co2e),

        "fraud_alerts_count": row.fraud_count or 0

    }
