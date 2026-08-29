from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.security import get_current_user
from app.domains.authentication.models import User

router = APIRouter()

async def ensure_community_tables(db: AsyncSession):
    """Ensure community validation and comment tables exist across SQLite and PostgreSQL."""
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS community_validations (
            id VARCHAR(64) PRIMARY KEY,
            validator_id VARCHAR(64),
            asset_id VARCHAR(64),
            response TEXT,
            upvotes INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS community_comments (
            id VARCHAR(64) PRIMARY KEY,
            validation_id VARCHAR(64),
            user_id VARCHAR(64),
            comment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db.commit()

@router.get("")
async def get_community_feed(page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db)):
    await ensure_community_tables(db)
    offset = (page - 1) * per_page
    
    # Query community_validations joined with users safely
    query = text("""
        SELECT cv.id, cv.response, cv.timestamp, cv.upvotes, cv.asset_id,
               u.full_name as user_name, u.role as user_role
        FROM community_validations cv
        LEFT JOIN users u ON cv.validator_id = CAST(u.id AS VARCHAR) OR cv.validator_id = u.id
        ORDER BY cv.timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, {"limit": per_page, "offset": offset})
    rows = result.mappings().all()
    
    count_query = text("SELECT COUNT(*) FROM community_validations")
    total = (await db.execute(count_query)).scalar() or 0
    
    posts = []
    for r in rows:
        c_query = text("""
            SELECT cc.id, cc.comment, cc.timestamp, u.full_name as user_name, u.role as user_role 
            FROM community_comments cc
            LEFT JOIN users u ON cc.user_id = CAST(u.id AS VARCHAR) OR cc.user_id = u.id
            WHERE cc.validation_id = :val_id
            ORDER BY cc.timestamp ASC
        """)
        c_res = await db.execute(c_query, {"val_id": str(r.id)})
        comments = [dict(c) for c in c_res.mappings().all()]
        
        posts.append({
            "id": str(r.id),
            "user_name": r.user_name or "Community Validator",
            "user_role": r.user_role or "COMMUNITY_OFFICER",
            "action": "validated an installation",
            "content": f"Provided feedback: {r.response}",
            "property_name": "Field Carbon Asset",
            "property_type": "Clean Energy",
            "response": r.response,
            "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, "isoformat") else str(r.timestamp or ""),
            "upvotes": r.upvotes or 0,
            "comments": comments
        })
        
    return {
        "posts": posts,
        "total": total,
        "page": page,
        "per_page": per_page
    }

@router.post("/{post_id}/upvote")
async def upvote_community_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = text("UPDATE community_validations SET upvotes = upvotes + 1 WHERE id = :id RETURNING upvotes")
    res = await db.execute(query, {"id": post_id})
    await db.commit()
    upvotes = res.scalar() or 0
    return {"id": post_id, "upvotes": upvotes}

@router.post("/{post_id}/comments")
async def add_community_comment(
    post_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    from datetime import datetime, timezone
    new_id = str(uuid.uuid4())
    query = text("""
        INSERT INTO community_comments (id, validation_id, user_id, comment, timestamp)
        VALUES (:id, :vid, :uid, :cmt, :ts)
    """)
    await db.execute(query, {
        "id": new_id,
        "vid": post_id,
        "uid": current_user.id,
        "cmt": payload.get("comment", ""),
        "ts": datetime.now(timezone.utc)
    })
    await db.commit()
    return {"success": True}
