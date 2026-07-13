from app.domains.assets.models import Asset


def test_asset_creation():
    """Asset can be instantiated with required fields from the current schema."""
    asset = Asset(
        id="123e4567-e89b-12d3-a456-426614174000",
        organization_id="123e4567-e89b-12d3-a456-426614174002",
        project_id="123e4567-e89b-12d3-a456-426614174001",
        name="Test Asset",
    )
    assert asset.name == "Test Asset"


def test_asset_status():
    """Asset status defaults correctly and can be overridden."""
    asset = Asset(
        id="123e4567-e89b-12d3-a456-426614174000",
        organization_id="123e4567-e89b-12d3-a456-426614174002",
        project_id="123e4567-e89b-12d3-a456-426614174001",
        name="Test Asset",
        status="active",
    )
    assert asset.status == "active"


def test_asset_metadata():
    """Asset attributes JSONB field stores arbitrary metadata."""
    asset = Asset(
        id="123e4567-e89b-12d3-a456-426614174000",
        organization_id="123e4567-e89b-12d3-a456-426614174002",
        project_id="123e4567-e89b-12d3-a456-426614174001",
        name="Test Asset",
        attributes={"manufacturer": "Envirofit"},
    )
    assert asset.attributes["manufacturer"] == "Envirofit"
