import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.security import get_current_user
from app.domains.authentication.models import User

router = APIRouter()

DEFAULT_SETTINGS = {
    "gps_weight": 30,
    "image_weight": 40,
    "frequency_weight": 30,
    "gps_max_distance_km": 5.0,
    "max_submissions_per_hour": 10,
    "image_hash_threshold": 12,
    "suspicious_hours_start": 2,
    "suspicious_hours_end": 5,
}

@router.get("")
async def get_settings(
    sector_id: Optional[str] = Query(None, description="Optional sector ID for sector-specific settings"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns system and anomaly settings isolated by organization and sector.
    - If user belongs to an organization, retrieves settings specific to their organization.
    - If sector_id is provided, retrieves sector-specific override if present.
    - If no organization record exists yet, returns platform defaults.
    """
    org_id = str(current_user.organization_id) if current_user.organization_id else None

    try:
        if org_id:
            # 1. Check for sector-specific settings first if sector_id is passed
            if sector_id:
                clean_sec = str(sector_id).strip()
                res = await db.execute(
                    text("SELECT * FROM system_settings WHERE organization_id = :org_id AND (sector_id = :sec_id OR sector_id = :clean_sec) LIMIT 1"),
                    {"org_id": org_id, "sec_id": clean_sec, "clean_sec": clean_sec.replace("-", "")}
                )
                row = res.mappings().first()
                if row:
                    return dict(row)

            # 2. Check for organization-wide settings
            res = await db.execute(
                text("SELECT * FROM system_settings WHERE organization_id = :org_id AND (sector_id IS NULL OR sector_id = '') LIMIT 1"),
                {"org_id": org_id}
            )
            row = res.mappings().first()
            if row:
                return dict(row)

        elif current_user.role == "SUPER_ADMIN":
            # Global platform default template
            res = await db.execute(
                text("SELECT * FROM system_settings WHERE organization_id IS NULL LIMIT 1")
            )
            row = res.mappings().first()
            if row:
                return dict(row)

    except Exception:
        pass

    # Default fallback with organization context
    resp = dict(DEFAULT_SETTINGS)
    if org_id:
        resp["organization_id"] = org_id
    if sector_id:
        resp["sector_id"] = sector_id
    return resp


@router.patch("")
async def update_settings(
    data: dict,
    sector_id: Optional[str] = Query(None, description="Optional sector ID for sector-specific settings"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates system and anomaly settings with strict account and sector isolation.
    - Only administrators (SUPER_ADMIN, ORG_ADMIN, ADMIN) can update settings.
    - ORG_ADMIN settings are strictly scoped to their own organization.
    - Changes never leak to other accounts or sectors.
    """
    if current_user.role not in ["SUPER_ADMIN", "ADMIN", "ORG_ADMIN", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can update system settings."
        )

    org_id = str(current_user.organization_id) if current_user.organization_id else None
    target_sector_id = data.get("sector_id") or sector_id
    if target_sector_id:
        target_sector_id = str(target_sector_id).strip()

    allowed_keys = [
        "gps_weight", "image_weight", "frequency_weight",
        "gps_max_distance_km", "max_submissions_per_hour",
        "image_hash_threshold", "suspicious_hours_start", "suspicious_hours_end"
    ]

    # Validate and normalize dimension weights if present
    gw = data.get("gps_weight")
    iw = data.get("image_weight")
    fw = data.get("frequency_weight")
    if gw is not None or iw is not None or fw is not None:
        current = await get_settings(sector_id=target_sector_id, current_user=current_user, db=db)
        g_val = float(gw if gw is not None else current.get("gps_weight", 30))
        i_val = float(iw if iw is not None else current.get("image_weight", 40))
        f_val = float(fw if fw is not None else current.get("frequency_weight", 30))
        total = g_val + i_val + f_val
        if total > 0 and abs(total - 100.0) > 0.01:
            data["gps_weight"] = round((g_val / total) * 100.0, 1)
            data["image_weight"] = round((i_val / total) * 100.0, 1)
            data["frequency_weight"] = round(100.0 - data["gps_weight"] - data["image_weight"], 1)

    # Check if an existing row exists for this exact organization (+ sector)
    existing_row = None
    try:
        if org_id:
            if target_sector_id:
                clean_sec = target_sector_id.replace("-", "")
                res = await db.execute(
                    text("SELECT id FROM system_settings WHERE organization_id = :org_id AND (sector_id = :sec_id OR sector_id = :clean_sec) LIMIT 1"),
                    {"org_id": org_id, "sec_id": target_sector_id, "clean_sec": clean_sec}
                )
            else:
                res = await db.execute(
                    text("SELECT id FROM system_settings WHERE organization_id = :org_id AND (sector_id IS NULL OR sector_id = '') LIMIT 1"),
                    {"org_id": org_id}
                )
            existing_row = res.fetchone()
        elif current_user.role == "SUPER_ADMIN":
            res = await db.execute(
                text("SELECT id FROM system_settings WHERE organization_id IS NULL LIMIT 1")
            )
            existing_row = res.fetchone()
    except Exception:
        pass

    if existing_row:
        # Update existing isolated record
        existing_id = str(existing_row[0])
        sets = []
        params = {"rec_id": existing_id}
        for k in allowed_keys:
            if k in data:
                sets.append(f"{k} = :{k}")
                params[k] = data[k]

        if sets:
            try:
                query = text(f"UPDATE system_settings SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = :rec_id")
                await db.execute(query, params)
                await db.commit()
            except Exception:
                await db.rollback()
    else:
        # Insert a new isolated record for this organization (+ sector)
        new_id = str(uuid.uuid4())
        cols = ["id", "organization_id", "sector_id"]
        vals = [":id", ":organization_id", ":sector_id"]
        params = {
            "id": new_id,
            "organization_id": org_id,
            "sector_id": target_sector_id
        }
        for k in allowed_keys:
            cols.append(k)
            vals.append(f":{k}")
            params[k] = data.get(k, DEFAULT_SETTINGS[k])

        try:
            query = text(f"INSERT INTO system_settings ({', '.join(cols)}) VALUES ({', '.join(vals)})")
            await db.execute(query, params)
            await db.commit()
        except Exception:
            await db.rollback()

    return await get_settings(sector_id=target_sector_id, current_user=current_user, db=db)
