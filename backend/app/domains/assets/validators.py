import jsonschema
from fastapi import HTTPException


def validate_asset_attributes(attributes: dict, schema: dict) -> None:
    """
    Validates dynamic asset attributes against the JSON schema supplied by the sector plugin.
    """
    if not schema:
        return

    try:
        jsonschema.validate(instance=attributes, schema=schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Asset attributes schema validation failed: {e.message}",
        )
