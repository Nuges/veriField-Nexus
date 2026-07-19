from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("")
async def get_community_feed(page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * per_page
    # Query community_validations joined with users and assets
    query = text("""
        SELECT cv.id, cv.response, cv.timestamp, cv.upvotes, 
               u.full_name as user_name, u.role as user_role,
               a.name as property_name, a.asset_type_id as property_type
        FROM community_validations cv
        JOIN users u ON cv.validator_id = u.id
        LEFT JOIN assets a ON cv.asset_id = a.id
        ORDER BY cv.timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, {"limit": per_page, "offset": offset})
    rows = result.mappings().all()
    
    # Query comments
    count_query = text("SELECT COUNT(*) FROM community_validations")
    total = (await db.execute(count_query)).scalar() or 0
    
    posts = []
    for r in rows:
        c_query = text("""
            SELECT cc.id, cc.comment, cc.timestamp, u.full_name as user_name, u.role as user_role 
            FROM community_comments cc
            JOIN users u ON cc.user_id = u.id
            WHERE cc.validation_id = :val_id
            ORDER BY cc.timestamp ASC
        """)
        c_res = await db.execute(c_query, {"val_id": r.id})
        comments = [dict(c) for c in c_res.mappings().all()]
        
        posts.append({
            "id": str(r.id),
            "user_name": r.user_name,
            "user_role": r.user_role,
            "action": "validated an installation",
            "content": f"Provided feedback: {r.response}",
            "property_name": r.property_name,
            "property_type": r.property_type,
            "response": r.response,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
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
async def upvote_community_post(post_id: str, db: AsyncSession = Depends(get_db)):
    query = text("UPDATE community_validations SET upvotes = upvotes + 1 WHERE id = :id RETURNING upvotes")
    res = await db.execute(query, {"id": post_id})
    await db.commit()
    upvotes = res.scalar() or 0
    return {"id": post_id, "upvotes": upvotes}

@router.post("/{post_id}/comments")
async def add_community_comment(post_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    # Assuming user_id is superadmin for now since no auth is attached, or we require auth
    # For simplicity, getting first user
    user = await db.execute(text("SELECT id FROM users LIMIT 1"))
    u_id = user.scalar()
    
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
        "uid": u_id,
        "cmt": payload.get("comment", ""),
        "ts": datetime.now(timezone.utc)
    })
    await db.commit()
    return {"success": True}
