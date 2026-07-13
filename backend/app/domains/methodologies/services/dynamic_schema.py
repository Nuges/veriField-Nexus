"""
Dynamic UI Schema Engine

Generates complete workspace schemas for the frontend from methodology metadata.
The frontend renders forms, tables, charts, and filters entirely from this schema.
Zero hardcoded UI per sector.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.methodologies.models.base_registry import (Methodology,
                                                            MethodologyVersion)
from app.domains.methodologies.models.components import (
    CalculationRule, EvidenceTemplate, MonitoringTemplate, ValidationRule,
    VersionCalculationRule, VersionEvidenceTemplate, VersionMonitoringTemplate,
    VersionValidationRule)
from app.domains.methodologies.models.workflow import Workflow, WorkflowStage


class DynamicSchemaEngine:
    """
    Generates a complete workspace schema for a methodology version.
    The schema drives the entire UI: forms, tables, charts, validation, workflows.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_workspace_schema(self, methodology_id: UUID) -> Dict[str, Any]:
        """
        Generate the complete workspace schema for a methodology.
        Returns everything the frontend needs to render the full workspace.
        """
        # Find active version
        stmt = (
            select(MethodologyVersion)
            .where(
                MethodologyVersion.methodology_id == methodology_id,
                MethodologyVersion.status == "active",
            )
            .order_by(MethodologyVersion.release_date.desc())
        )
        result = await self.db.execute(stmt)
        version = result.scalars().first()

        if not version:
            return {"error": "No active methodology version found"}

        # Get methodology info
        meth_result = await self.db.execute(
            select(Methodology)
            .options(
                selectinload(Methodology.registry), selectinload(Methodology.family)
            )
            .where(Methodology.id == methodology_id)
        )
        methodology = meth_result.scalars().first()

        # Build all schema sections in parallel-ish fashion
        form_schema = await self._build_form_schema(version.id)
        evidence_schema = await self._build_evidence_schema(version.id)
        calculation_schema = await self._build_calculation_schema(version.id)
        validation_schema = await self._build_validation_schema(version.id)
        workflow_schema = await self._build_workflow_schema(version.id)

        return {
            "methodology": {
                "id": str(methodology.id) if methodology else None,
                "code": methodology.code if methodology else None,
                "name": methodology.name if methodology else None,
                "registry": (
                    methodology.registry.name
                    if methodology and methodology.registry
                    else None
                ),
                "family": (
                    methodology.family.name
                    if methodology and methodology.family
                    else None
                ),
                "version": version.version,
                "version_id": str(version.id),
            },
            "form_schema": form_schema,
            "evidence_requirements": evidence_schema,
            "calculation_rules": calculation_schema,
            "validation_rules": validation_schema,
            "workflow": workflow_schema,
        }

    async def _build_form_schema(self, version_id: UUID) -> Dict[str, Any]:
        """Build JSON Schema for activity data entry forms."""
        stmt = (
            select(VersionMonitoringTemplate, MonitoringTemplate)
            .join(
                MonitoringTemplate,
                VersionMonitoringTemplate.template_id == MonitoringTemplate.id,
            )
            .where(VersionMonitoringTemplate.version_id == version_id)
        )

        results = await self.db.execute(stmt)

        schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "ui_order": [],
        }

        for version_template, template in results.all():
            field = {
                "type": template.data_type,
                "title": template.name,
                "description": template.description or "",
            }
            if template.unit:
                field["unit"] = template.unit
            if template.validation_schema:
                field.update(template.validation_schema)

            schema["properties"][template.code] = field
            schema["ui_order"].append(template.code)

            if version_template.is_required:
                schema["required"].append(template.code)

        return schema

    async def _build_evidence_schema(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Build evidence requirements list from methodology metadata."""
        stmt = (
            select(VersionEvidenceTemplate, EvidenceTemplate)
            .join(
                EvidenceTemplate,
                VersionEvidenceTemplate.template_id == EvidenceTemplate.id,
            )
            .where(VersionEvidenceTemplate.version_id == version_id)
        )

        results = await self.db.execute(stmt)

        evidence_reqs = []
        for version_ev, template in results.all():
            evidence_reqs.append(
                {
                    "evidence_type": template.evidence_type,
                    "name": template.name,
                    "description": template.description or "",
                    "rule_type": "required" if template.is_mandatory else "optional",
                    "frequency": version_ev.frequency,
                }
            )

        return evidence_reqs

    async def _build_calculation_schema(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Build calculation rules list from methodology metadata."""
        stmt = (
            select(VersionCalculationRule, CalculationRule)
            .join(CalculationRule, VersionCalculationRule.rule_id == CalculationRule.id)
            .where(VersionCalculationRule.version_id == version_id)
            .order_by(VersionCalculationRule.execution_order)
        )

        results = await self.db.execute(stmt)

        calc_rules = []
        for version_rule, rule in results.all():
            calc_rules.append(
                {
                    "code": rule.code,
                    "name": rule.name,
                    "formula": rule.formula,
                    "output_parameter": rule.code,
                    "inputs_schema": rule.inputs_schema,
                    "outputs_schema": rule.outputs_schema,
                    "execution_order": version_rule.execution_order,
                }
            )

        return calc_rules

    async def _build_validation_schema(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Build validation rules list from methodology metadata."""
        stmt = (
            select(VersionValidationRule, ValidationRule)
            .join(ValidationRule, VersionValidationRule.rule_id == ValidationRule.id)
            .where(VersionValidationRule.version_id == version_id)
        )

        results = await self.db.execute(stmt)

        val_rules = []
        for _, rule in results.all():
            val_rules.append(
                {
                    "code": rule.code,
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "expression": rule.expression,
                    "error_message": rule.error_message,
                    "severity": "warning",
                    "action": "flag",
                }
            )

        return val_rules

    async def _build_workflow_schema(
        self, version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Build workflow definition from methodology metadata."""
        stmt = (
            select(Workflow)
            .options(selectinload(Workflow.stages).selectinload(WorkflowStage.tasks))
            .where(Workflow.version_id == version_id)
        )

        result = await self.db.execute(stmt)
        workflow = result.scalars().first()

        if not workflow:
            return None

        stages = []
        for stage in sorted(workflow.stages, key=lambda s: s.sequence_order):
            tasks = []
            for task in sorted(stage.tasks, key=lambda t: t.sequence_order):
                tasks.append(
                    {
                        "id": str(task.id),
                        "name": task.name,
                        "task_type": task.task_type,
                        "sequence_order": task.sequence_order,
                        "schema_definition": task.schema_definition,
                    }
                )
            stages.append(
                {
                    "id": str(stage.id),
                    "name": stage.name,
                    "sequence_order": stage.sequence_order,
                    "required_role": stage.required_role,
                    "tasks": tasks,
                }
            )

        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "trigger_event": workflow.trigger_event,
            "stages": stages,
        }
