from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.methodologies.models import (Methodology, MethodologyFamily,
                                              MethodologyRegistry,
                                              MethodologyVersion)
from app.domains.methodologies.services.migration_service import \
    MigrationService


@pytest.mark.asyncio
async def test_migration_service_creates_records():
    mock_db = AsyncMock()
    # Mock execute().scalar_one_or_none() to always return None to force creation
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    service = MigrationService(mock_db)

    await service.migrate_cookstoves()

    # Check that db.add was called multiple times
    assert mock_db.add.call_count > 0
    assert mock_db.commit.call_count == 1

    added_objects = [call[0][0] for call in mock_db.add.call_args_list]

    # We should have created registries
    registries = [obj for obj in added_objects if isinstance(obj, MethodologyRegistry)]
    assert len(registries) >= 2
    assert any(r.code == "VERRA" for r in registries)

    # We should have created families
    families = [obj for obj in added_objects if isinstance(obj, MethodologyFamily)]
    assert len(families) == 1
    assert families[0].code == "COOKSTOVES"

    # We should have created methodologies
    methodologies = [obj for obj in added_objects if isinstance(obj, Methodology)]
    assert len(methodologies) >= 1
    assert any(m.code == "VM0006" for m in methodologies)

    # We should have created versions
    versions = [obj for obj in added_objects if isinstance(obj, MethodologyVersion)]
    assert len(versions) >= 1
