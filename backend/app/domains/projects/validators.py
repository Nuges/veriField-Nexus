from typing import List

from fastapi import HTTPException


def validate_project_methodology(
    methodology_id: str, approved_methodologies: List[str]
):
    """Checks if the project methodology belongs to the approved list for the country jurisdiction."""
    if methodology_id not in approved_methodologies:
        raise HTTPException(
            status_code=400,
            detail=f"Methodology '{methodology_id}' is not approved for this jurisdiction. Approved: {approved_methodologies}",
        )
