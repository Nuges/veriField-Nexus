from app.domains.activities.models import Activity


def test_activity_creation():
    activity = Activity(
        id="123e4567-e89b-12d3-a456-426614174000",
        asset_id="123e4567-e89b-12d3-a456-426614174001",
        status="pending",
    )
    assert activity.status == "pending"


def test_activity_serialization():
    activity = Activity(
        id="123e4567-e89b-12d3-a456-426614174000",
        asset_id="123e4567-e89b-12d3-a456-426614174001",
        status="pending",
    )
    assert activity.id is not None


def test_activity_status_update():
    activity = Activity(
        id="123e4567-e89b-12d3-a456-426614174000",
        asset_id="123e4567-e89b-12d3-a456-426614174001",
        status="pending",
    )
    activity.status = "verified"
    assert activity.status == "verified"
