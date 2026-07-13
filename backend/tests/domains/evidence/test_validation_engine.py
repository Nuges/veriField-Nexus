from datetime import datetime, timedelta, timezone

import pytest

from app.domains.evidence.validation_engine import EvidenceValidationEngine


@pytest.fixture
def engine():
    return EvidenceValidationEngine()


def test_all_required_evidence_present(engine):
    requirements = [
        {"evidence_type": "photo", "rule_type": "required", "min_count": 1},
        {"evidence_type": "gps", "rule_type": "required", "min_count": 1},
    ]
    submitted = [
        {
            "evidence_type": "photo",
            "file_uri": "s3://bucket/photo.jpg",
            "file_hash": "abc123",
            "metadata_json": {},
        },
        {
            "evidence_type": "gps",
            "file_uri": "s3://bucket/gps.csv",
            "file_hash": "def456",
            "metadata_json": {},
        },
    ]
    result = engine.validate_submission(requirements, submitted)
    assert result["is_complete"] is True
    assert len(result["missing"]) == 0


def test_missing_required_evidence(engine):
    requirements = [
        {"evidence_type": "photo", "rule_type": "required", "min_count": 2},
    ]
    submitted = [
        {
            "evidence_type": "photo",
            "file_uri": "s3://bucket/photo.jpg",
            "file_hash": "abc123",
            "metadata_json": {},
        },
    ]
    result = engine.validate_submission(requirements, submitted)
    assert result["is_complete"] is False
    assert "photo" in result["missing"]


def test_optional_evidence_not_required(engine):
    requirements = [
        {"evidence_type": "video", "rule_type": "optional", "min_count": 1},
    ]
    submitted = []
    result = engine.validate_submission(requirements, submitted)
    # Optional evidence missing should NOT block completion
    assert result["is_complete"] is True


def test_gps_bounding_box_validation(engine):
    requirements = [
        {
            "evidence_type": "gps",
            "rule_type": "required",
            "gps_required": True,
            "gps_bounding_box": {
                "min_lat": -5,
                "max_lat": 5,
                "min_lon": 30,
                "max_lon": 40,
            },
        },
    ]
    # Valid GPS
    submitted_valid = [
        {
            "evidence_type": "gps",
            "file_uri": "s3://gps.csv",
            "file_hash": "aaa",
            "metadata_json": {"latitude": 1.5, "longitude": 35.0},
        },
    ]
    result = engine.validate_submission(requirements, submitted_valid)
    assert result["is_complete"] is True

    # Invalid GPS (outside box)
    submitted_invalid = [
        {
            "evidence_type": "gps",
            "file_uri": "s3://gps.csv",
            "file_hash": "aaa",
            "metadata_json": {"latitude": 50.0, "longitude": 35.0},
        },
    ]
    result = engine.validate_submission(requirements, submitted_invalid)
    assert result["is_complete"] is False


def test_max_age_validation(engine):
    now = datetime.now(timezone.utc)
    requirements = [
        {"evidence_type": "sensor_data", "rule_type": "required", "max_age_hours": 24},
    ]
    # Fresh evidence
    submitted_fresh = [
        {
            "evidence_type": "sensor_data",
            "file_uri": "s3://sensor.json",
            "file_hash": "xxx",
            "metadata_json": {},
            "created_at": now,
        },
    ]
    result = engine.validate_submission(requirements, submitted_fresh)
    assert result["is_complete"] is True

    # Stale evidence
    submitted_stale = [
        {
            "evidence_type": "sensor_data",
            "file_uri": "s3://sensor.json",
            "file_hash": "xxx",
            "metadata_json": {},
            "created_at": now - timedelta(hours=48),
        },
    ]
    result = engine.validate_submission(requirements, submitted_stale)
    assert result["is_complete"] is False


def test_file_type_validation(engine):
    requirements = [
        {
            "evidence_type": "photo",
            "rule_type": "required",
            "file_types": ["jpg", "png"],
        },
    ]
    # Valid type
    submitted_valid = [
        {
            "evidence_type": "photo",
            "file_uri": "s3://bucket/photo.jpg",
            "file_hash": "abc",
            "metadata_json": {},
        },
    ]
    result = engine.validate_submission(requirements, submitted_valid)
    assert result["is_complete"] is True

    # Invalid type
    submitted_invalid = [
        {
            "evidence_type": "photo",
            "file_uri": "s3://bucket/photo.bmp",
            "file_hash": "abc",
            "metadata_json": {},
        },
    ]
    result = engine.validate_submission(requirements, submitted_invalid)
    assert result["is_complete"] is False


def test_conditional_evidence(engine):
    requirements = [
        {
            "evidence_type": "lab_report",
            "rule_type": "conditional",
            "condition_expression": "methodology_type == biochar",
        },
    ]
    # Condition not met — should skip, so complete
    result = engine.validate_submission(
        requirements, [], context={"methodology_type": "generic"}
    )
    assert result["is_complete"] is True

    # Condition met but evidence missing — should fail
    result = engine.validate_submission(
        requirements, [], context={"methodology_type": "biochar"}
    )
    assert result["is_complete"] is False
    assert "lab_report" in result["missing"]


def test_missing_gps_coordinates(engine):
    requirements = [
        {"evidence_type": "photo", "rule_type": "required", "gps_required": True},
    ]
    submitted = [
        {
            "evidence_type": "photo",
            "file_uri": "s3://photo.jpg",
            "file_hash": "abc",
            "metadata_json": {},
        },
    ]
    result = engine.validate_submission(requirements, submitted)
    assert result["is_complete"] is False
    assert any("GPS" in e for r in result["results"] for e in r["errors"])
