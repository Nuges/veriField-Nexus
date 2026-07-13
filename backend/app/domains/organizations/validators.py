from fastapi import HTTPException, status

from app.domains.organizations.models import Organization


def validate_max_installations(org: Organization, current_count: int) -> None:
    """Checks if the organization has exceeded its package limit for installations."""
    if current_count >= org.max_installations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization capacity limit reached ({org.max_installations} maximum properties/assets).",
        )
