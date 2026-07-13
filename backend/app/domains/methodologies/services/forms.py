from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.methodologies.models.components import (
    MonitoringTemplate, VersionMonitoringTemplate)


class FormGenerationService:
    """
    Generates dynamic JSON schemas from Monitoring Templates for a specific Methodology Version.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_schema_for_version(self, version_id: UUID) -> Dict[str, Any]:
        """
        Builds a JSON Schema object from all monitoring templates attached to the methodology version.
        """
        stmt = (
            select(VersionMonitoringTemplate, MonitoringTemplate)
            .join(
                MonitoringTemplate,
                VersionMonitoringTemplate.template_id == MonitoringTemplate.id,
            )
            .where(VersionMonitoringTemplate.version_id == version_id)
        )

        results = await self.db.execute(stmt)

        schema = {"type": "object", "properties": {}, "required": []}

        for version_template, template in results.all():
            field_schema = {
                "type": template.data_type,
                "title": template.name,
                "description": template.description,
            }
            if template.unit:
                field_schema["unit"] = template.unit

            # Merge in additional validation schema (min, max, etc.)
            if template.validation_schema:
                field_schema.update(template.validation_schema)

            schema["properties"][template.code] = field_schema

            if version_template.is_required:
                schema["required"].append(template.code)

        return schema
