import jsonschema
from fastapi import HTTPException


def validate_activity_data(activity_data: dict, schema: dict) -> None:
    """Validates activity telemetry data against JSON schema from the sector plugin."""
    if not schema:
        return
    try:
        jsonschema.validate(instance=activity_data, schema=schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(
            status_code=400, detail=f"Activity data validation failed: {e.message}"
        )
