from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.reporting.repository import ReportRepository
from app.domains.reporting.schemas import ReportCreate, ReportResponse
from app.domains.reporting.service import ReportingService

router = APIRouter(tags=["Reporting"])


def get_reporting_service(db: AsyncSession = Depends(get_db)) -> ReportingService:
    repository = ReportRepository(db)
    return ReportingService(repository)


@router.get("/", response_model=List[ReportResponse])
async def list_org_reports(
    org_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    # In a full impl, check if current_user belongs to org_id
    return await service.list_reports(org_id, skip=skip, limit=limit)


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.generate_report(data, creator_id=current_user.id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/metrics/overview")
async def get_metrics_overview(
    org_id: Optional[UUID] = None,
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.domains.reporting.services.analytics import AnalyticsService
    analytics_service = AnalyticsService(db)
    
    # Project specific filtering would be handled by project_id here if passed
    # For now, pass org_id
    metrics = await analytics_service.get_dashboard_metrics(org_id=org_id)
    return metrics


@router.get("/carbon/ledger")
async def get_carbon_ledger(
    include_log: bool = False,
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.domains.projects.models import CarbonCalculation
    from app.domains.projects.models import Project
    from app.domains.methodologies.providers.factory import MethodologyProviderFactory
    
    stmt = select(CarbonCalculation, Project).outerjoin(Project, CarbonCalculation.project_id == Project.id).order_by(CarbonCalculation.created_at.desc())
    res = await db.execute(stmt)
    
    data = []
    for calc, proj in res.all():
        # Dynamically resolve methodology and price via Provider
        methodology_code = proj.methodology_id if proj and hasattr(proj, 'methodology_id') and proj.methodology_id else "DEFAULT"
        
        provider = MethodologyProviderFactory.get_provider(methodology_code)
        price = await provider.get_carbon_price()
        
        data.append({
            "id": str(calc.id),
            "project_name": proj.name if proj else "Unknown Project",
            "methodology": methodology_code,
            "tco2e": calc.tco2e_generated,
            "estimated_value": float(calc.tco2e_generated) * price,
            "unit_price": price,
            "uncertainty": 0,
            "status": "calculated",
            "date": calc.created_at.isoformat()
        })
        
    return {"data": data}


@router.get("/metrics/anomalies")
async def get_anomalies(
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.domains.activities.models import Activity
    
    stmt = select(Activity).where(Activity.status == "flagged").order_by(Activity.created_at.desc())
    res = await db.execute(stmt)
    
    anomalies = []
    for act in res.scalars().all():
        # Derive flag_type based on trust_flags keys if available
        flag_type = "anomaly"
        if act.trust_flags:
            if act.trust_flags.get("image_duplicate"):
                flag_type = "image_duplicate"
            elif act.trust_flags.get("gps_mismatch"):
                flag_type = "gps_anomaly"
                
        reason = act.trust_flags.get("fraud_flag") if act.trust_flags else "Suspicious data"
        
        anomalies.append({
            "id": str(act.id),
            "activity_id": str(act.id),
            "flag_type": flag_type,
            "description": str(reason),
            "activity_status": act.status,
            "severity": "high",
            "created_at": act.created_at.isoformat()
        })
        
    return {"anomalies": anomalies, "total": len(anomalies)}

@router.post("/metrics/anomalies/{flag_id}/resolve")
async def resolve_anomaly(
    flag_id: str,
    action: str, # 'verify' or 'reject'
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.domains.activities.models import Activity
    act = await db.get(Activity, flag_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    if action == "verify":
        act.status = "verified"
        if not act.asset_id:
            from app.domains.assets.service import AssetService
            from app.domains.assets.repository import AssetRepository
            from app.domains.assets.schemas import AssetCreate
            from app.domains.projects.models import Project
            from sqlalchemy import select
            
            org_id = act.organization_id
            project_id = None
            if act.property_id:
                from app.domains.workspaces.models import Workspace
                workspace = await db.get(Workspace, act.property_id)
                if workspace and workspace.project_id:
                    project_id = workspace.project_id
            
            if not project_id:
                proj_stmt = select(Project).where(Project.organization_id == org_id).limit(1)
                proj_res = await db.execute(proj_stmt)
                fallback_proj = proj_res.scalar_one_or_none()
                if fallback_proj:
                    project_id = fallback_proj.id
            
            if project_id:
                data = act.activity_data or {}
                asset_ident = data.get("stove_id") or data.get("serial_number") or data.get("head_name")
                if asset_ident:
                    asset_name = f"{act.activity_type.replace('_', ' ').title()} - {asset_ident}"
                else:
                    asset_name = f"Asset from Activity {str(act.id)[:8]}"

                asset_service = AssetService(AssetRepository(db))
                new_asset_schema = AssetCreate(
                    project_id=project_id,
                    name=asset_name,
                    latitude=act.latitude,
                    longitude=act.longitude,
                    attributes=data
                )
                new_asset = await asset_service.create_asset(new_asset_schema, org_id)
                act.asset_id = new_asset.id
    elif action == "reject":
        act.status = "rejected"
        
    await db.commit()
    return {"status": "success", "activity_id": str(act.id)}

@router.get("/metrics/trends")
async def get_trends(
    days: int = 30,
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func
    from app.domains.activities.models import Activity
    
    stmt = select(Activity.activity_type, func.count(Activity.id).label("count")).group_by(Activity.activity_type)
    res = await db.execute(stmt)
    rows = res.all()
    
    activity_types = [{"activity_type": r[0] or "Unknown", "count": r[1]} for r in rows]

    return {
        "daily_submissions": [],
        "activity_types": activity_types,
        "trust_distribution": {
            "high": 0,
            "medium": 0,
            "low": 0,
            "unscored": 0
        }
    }

@router.get("/metrics/agents")
async def get_agent_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, func, case
    from app.domains.authentication.models import User
    from app.domains.activities.models import Activity
    
    stmt = (
        select(
            User,
            func.count(Activity.id).label("total_sub"),
            func.avg(Activity.trust_score).label("avg_trust"),
            func.sum(case((Activity.status == "flagged", 1), else_=0)).label("flagged_count")
        )
        .outerjoin(Activity, Activity.user_id == User.id)
        .where(User.role.in_(["field_agent", "FIELD_AGENT"]))
        .group_by(User.id)
    )
    
    res = await db.execute(stmt)
    rows = res.all()
    
    agents = []
    suspicious_count = 0
    
    for u, total_sub, avg_trust, flagged_count in rows:
        total_sub = total_sub or 0
        flagged_count = flagged_count or 0
        flag_rate = (flagged_count / total_sub * 100) if total_sub > 0 else 0
        
        suspicious = u.status in ["suspended", "revoked"]
        if suspicious:
            suspicious_count += 1
            
        agents.append({
            "id": str(u.id),
            "full_name": u.full_name or "Unknown Agent",
            "email": u.email,
            "role": u.role,
            "status": u.status or "active",
            "organization": "VeriField",
            "total_submissions": total_sub,
            "flagged_count": flagged_count,
            "flag_rate": round(flag_rate, 2),
            "avg_trust_score": round(float(avg_trust), 2) if avg_trust is not None else None,
            "suspicious": suspicious
        })
        
    return {
        "total_agents": len(agents),
        "suspicious_count": suspicious_count,
        "agents": agents
    }
