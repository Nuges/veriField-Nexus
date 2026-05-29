"""
=============================================================================
VeriField Nexus — Community Validations API Routes
=============================================================================
CRUD operations for community validation/feed. Supports:
- Submitting validations
- Listing validations as a feed
- Upvoting (placeholder for future)
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.user import User
from app.models.community_validation import CommunityValidation, CommunityComment
from app.models.property import Property
from app.schemas.community import (
    CommunityValidationCreate,
    CommunityValidationResponse, CommunityValidationListResponse,
    CommunityFeedItem, CommunityFeedResponse,
    CommunityCommentCreate, CommunityCommentResponse,
)

router = APIRouter(prefix="/community", tags=["Community"])


def _serialize_validation(v: CommunityValidation) -> CommunityValidationResponse:
    """Convert a CommunityValidation ORM instance to response model."""
    return CommunityValidationResponse(
        id=v.id,
        asset_id=v.asset_id,
        validator_id=v.validator_id,
        response=v.response,
        timestamp=v.timestamp,
        property_name=v.property.name if v.property else None,
        property_type=v.property.property_type if v.property else None,
        validator_name=v.validator.full_name if v.validator else None,
        validator_role=v.validator.role if v.validator else None,
    )


def _to_feed_item(v: CommunityValidation) -> CommunityFeedItem:
    """Convert a CommunityValidation to a feed-style item."""
    action_map = {
        "yes": "validated an activity",
        "no": "flagged an activity",
        "pending": "submitted a review",
    }
    action = action_map.get(v.response, "shared an update")

    content_map = {
        "yes": f"Confirmed that the activity at {v.property.name if v.property else 'an asset'} is legitimate and operational.",
        "no": f"Raised a flag on the activity at {v.property.name if v.property else 'an asset'} — needs further review.",
        "pending": f"Submitted a review for {v.property.name if v.property else 'an asset'} — awaiting confirmation.",
    }
    content = content_map.get(v.response, "Shared an update.")

    serialized_comments = []
    if hasattr(v, "comments") and v.comments:
        for c in v.comments:
            serialized_comments.append(
                CommunityCommentResponse(
                    id=c.id,
                    validation_id=c.validation_id,
                    user_id=c.user_id,
                    user_name=c.user.full_name if c.user else "Unknown",
                    user_role=c.user.role if c.user else "member",
                    comment=c.comment,
                    timestamp=c.timestamp,
                )
            )

    return CommunityFeedItem(
        id=v.id,
        user_name=v.validator.full_name if v.validator else "Unknown",
        user_role=v.validator.role if v.validator else "member",
        action=action,
        content=content,
        property_name=v.property.name if v.property else None,
        property_type=v.property.property_type if v.property else None,
        response=v.response,
        timestamp=v.timestamp,
        upvotes=v.upvotes or 0,
        comments=serialized_comments,
    )


# =============================================================================
# POST /api/v1/community — Submit a community validation
# =============================================================================
@router.post(
    "",
    response_model=CommunityValidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a community validation",
)
async def create_community_validation(
    payload: CommunityValidationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a community validation response for an asset."""
    # Validate asset exists
    prop_result = await db.execute(select(Property).where(Property.id == payload.asset_id))
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property/asset not found")

    # Prevent duplicate validations by same user on same asset
    existing = await db.execute(
        select(CommunityValidation).where(
            and_(
                CommunityValidation.asset_id == payload.asset_id,
                CommunityValidation.validator_id == user.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You have already submitted a validation for this asset",
        )

    validation = CommunityValidation(
        asset_id=payload.asset_id,
        validator_id=user.id,
        response=payload.response,
    )
    db.add(validation)
    await db.commit()

    # --- Trust Bonus/Penalty: Apply to related activities for this asset ---
    try:
        from app.models.activity import Activity
        act_result = await db.execute(
            select(Activity).where(
                and_(
                    Activity.property_id == payload.asset_id,
                    Activity.status.in_(["pending", "review", "verified"]),
                )
            )
        )
        related_activities = act_result.scalars().all()

        bonus = 5.0 if payload.response == "yes" else (-10.0 if payload.response == "no" else 0.0)

        for act in related_activities:
            if act.trust_score is not None:
                new_score = max(0.0, min(100.0, act.trust_score + bonus))
                act.trust_score = new_score
                # Re-evaluate status based on new score
                if new_score >= 80:
                    act.status = "verified"
                elif new_score >= 50:
                    act.status = "review"
                else:
                    act.status = "flagged"
                # Log the community adjustment in trust_flags
                flags = act.trust_flags or {}
                flags[f"community_{payload.response}"] = True
                flags["community_bonus"] = bonus
                act.trust_flags = flags

        if related_activities:
            await db.commit()
    except Exception:
        pass  # Don't fail the validation if bonus application fails

    # Reload with relationships
    result = await db.execute(
        select(CommunityValidation)
        .options(
            selectinload(CommunityValidation.property),
            selectinload(CommunityValidation.validator),
        )
        .where(CommunityValidation.id == validation.id)
    )
    validation = result.scalar_one()
    return _serialize_validation(validation)


# =============================================================================
# GET /api/v1/community — List validations as a feed
# =============================================================================
@router.get(
    "",
    response_model=CommunityFeedResponse,
    summary="Get community feed",
)
async def get_community_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the community validation feed — all validations ordered by time."""
    query = (
        select(CommunityValidation)
        .options(
            selectinload(CommunityValidation.property),
            selectinload(CommunityValidation.validator),
            selectinload(CommunityValidation.comments).selectinload(CommunityComment.user),
        )
    )
    count_query = select(func.count(CommunityValidation.id))

    if user and user.organization:
        query = query.join(Property, CommunityValidation.asset_id == Property.id).join(User, Property.owner_id == User.id).where(User.organization == user.organization)
        count_query = count_query.join(Property, CommunityValidation.asset_id == Property.id).join(User, Property.owner_id == User.id).where(User.organization == user.organization)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(CommunityValidation.timestamp.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    validations = result.scalars().all()

    return CommunityFeedResponse(
        posts=[_to_feed_item(v) for v in validations],
        total=total, page=page, per_page=per_page,
    )


# =============================================================================
# GET /api/v1/community/validations — Raw validations list
# =============================================================================
@router.get(
    "/validations",
    response_model=CommunityValidationListResponse,
    summary="List raw community validations",
)
async def list_community_validations(
    asset_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List community validations with optional asset filter."""
    query = (
        select(CommunityValidation)
        .options(
            selectinload(CommunityValidation.property),
            selectinload(CommunityValidation.validator),
        )
    )
    count_query = select(func.count(CommunityValidation.id))

    conditions = []
    if asset_id:
        conditions.append(CommunityValidation.asset_id == asset_id)
    if user and user.organization:
        query = query.join(Property, CommunityValidation.asset_id == Property.id).join(User, Property.owner_id == User.id)
        count_query = count_query.join(Property, CommunityValidation.asset_id == Property.id).join(User, Property.owner_id == User.id)
        conditions.append(User.organization == user.organization)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(CommunityValidation.timestamp.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    validations = result.scalars().all()

    return CommunityValidationListResponse(
        validations=[_serialize_validation(v) for v in validations],
        total=total, page=page, per_page=per_page,
    )


# =============================================================================
# POST /api/v1/community/{validation_id}/upvote — Upvote/like validation
# =============================================================================
@router.post(
    "/{validation_id}/upvote",
    response_model=CommunityFeedItem,
    summary="Upvote/like a community validation post",
)
async def upvote_community_post(
    validation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Increment upvotes count for a community validation post."""
    result = await db.execute(
        select(CommunityValidation)
        .options(
            selectinload(CommunityValidation.property),
            selectinload(CommunityValidation.validator),
            selectinload(CommunityValidation.comments).selectinload(CommunityComment.user),
        )
        .where(CommunityValidation.id == validation_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Validation post not found")

    post.upvotes = (post.upvotes or 0) + 1
    await db.commit()
    await db.refresh(post)

    return _to_feed_item(post)


# =============================================================================
# POST /api/v1/community/{validation_id}/comments — Add a comment/reply
# =============================================================================
@router.post(
    "/{validation_id}/comments",
    response_model=CommunityCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment/reply to a community validation post",
)
async def add_community_comment(
    validation_id: UUID,
    payload: CommunityCommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new comment/reply to a community validation post."""
    result = await db.execute(
        select(CommunityValidation).where(CommunityValidation.id == validation_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Validation post not found")

    import uuid
    from datetime import datetime, timezone
    comment = CommunityComment(
        id=uuid.uuid4(),
        validation_id=validation_id,
        user_id=user.id,
        comment=payload.comment,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(comment)
    await db.commit()

    # Load comment with user relations
    comment_result = await db.execute(
        select(CommunityComment)
        .options(selectinload(CommunityComment.user))
        .where(CommunityComment.id == comment.id)
    )
    comment = comment_result.scalar_one()

    return CommunityCommentResponse(
        id=comment.id,
        validation_id=comment.validation_id,
        user_id=comment.user_id,
        user_name=comment.user.full_name if comment.user else "Unknown",
        user_role=comment.user.role if comment.user else "member",
        comment=comment.comment,
        timestamp=comment.timestamp,
    )
