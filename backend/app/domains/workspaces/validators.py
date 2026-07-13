from fastapi import HTTPException


def validate_coordinates(lat: Optional[float], lon: Optional[float]):
    if lat is not None and (lat < -90 or lat > 90):
        raise HTTPException(
            status_code=400, detail="Latitude must be between -90 and 90"
        )
    if lon is not None and (lon < -180 or lon > 180):
        raise HTTPException(
            status_code=400, detail="Longitude must be between -180 and 180"
        )
