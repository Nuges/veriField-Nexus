import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.methodologies.models import (CalculationRule, Methodology,
                                              MethodologyFamily,
                                              MethodologyRegistry,
                                              MethodologyVersion, Workflow,
                                              WorkflowStage, WorkflowTask)


class MigrationService:
    """
    Transforms legacy plugin logic into CIOS Database Metadata Seeds.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def migrate_cookstoves(self):
        """
        Migrates Cookstoves sector methodologies into metadata-driven DB configurations.
        """
        # 1. Ensure Registries Exist
        verra, _ = await self.get_or_create_registry("VERRA", "Verra")
        gs, _ = _ = await self.get_or_create_registry("GS", "Gold Standard")

        # 2. Ensure Methodology Family Exists
        family, _ = await self.get_or_create_family("COOKSTOVES", "Clean Cookstoves")

        # 3. Migrate VM0006
        vm0006_meta = {
            "id": "VM0006",
            "name": "Methodology for Installation of High Efficiency Firewood Cookstoves",
            "version": "v1.1",
            "status": "Active",
        }
        vm0006_meth, _ = await self.get_or_create_methodology(
            code=vm0006_meta["id"],
            name=vm0006_meta["name"],
            registry_id=verra.id,
            family_id=family.id,
        )
        vm0006_version, created_vm = await self.get_or_create_version(
            methodology_id=vm0006_meth.id, version_str=vm0006_meta["version"]
        )

        # VM0006 Calculation Rules
        if created_vm:
            calc_rule = CalculationRule(
                code="VM0006_CALC_V1",
                name="VM0006 ER Calculation",
                formula="((baseline_fuel_kg_yr - project_fuel_kg_yr)/1000) * ncv_tj_ton * ef_tco2_tj * fraction_non_renewable_biomass * sum_usage_rate_percentage",
                inputs_schema={},
                outputs_schema={
                    "type": "object",
                    "properties": {"final_tco2e": {"type": "number"}},
                },
            )
            self.db.add(calc_rule)

            # Basic Workflow
            workflow = Workflow(
                version_id=vm0006_version.id,
                name="VM0006 Standard Workflow",
                trigger_event="activity_created",
            )
            self.db.add(workflow)
            await self.db.flush()

            stage1 = WorkflowStage(
                workflow_id=workflow.id, name="Data Collection", sequence_order=1
            )
            stage2 = WorkflowStage(
                workflow_id=workflow.id, name="Verification", sequence_order=2
            )
            self.db.add_all([stage1, stage2])

            await self.db.flush()

            task1 = WorkflowTask(
                stage_id=stage1.id,
                name="Upload Stove Photo",
                task_type="evidence_upload",
                sequence_order=1,
            )
            task2 = WorkflowTask(
                stage_id=stage2.id,
                name="Verify Baseline Data",
                task_type="approval",
                sequence_order=2,
            )
            self.db.add_all([task1, task2])

        await self.db.commit()

    async def get_or_create_registry(
        self, code: str, name: str
    ) -> tuple[MethodologyRegistry, bool]:
        result = await self.db.execute(select(MethodologyRegistry).filter_by(code=code))
        registry = result.scalar_one_or_none()
        if registry:
            return registry, False
        registry = MethodologyRegistry(code=code, name=name)
        self.db.add(registry)
        await self.db.flush()
        return registry, True

    async def get_or_create_family(
        self, code: str, name: str
    ) -> tuple[MethodologyFamily, bool]:
        result = await self.db.execute(select(MethodologyFamily).filter_by(code=code))
        family = result.scalar_one_or_none()
        if family:
            return family, False
        family = MethodologyFamily(code=code, name=name)
        self.db.add(family)
        await self.db.flush()
        return family, True

    async def get_or_create_methodology(
        self, code: str, name: str, registry_id: uuid.UUID, family_id: uuid.UUID
    ) -> tuple[Methodology, bool]:
        result = await self.db.execute(select(Methodology).filter_by(code=code))
        meth = result.scalar_one_or_none()
        if meth:
            return meth, False
        meth = Methodology(
            code=code, name=name, registry_id=registry_id, family_id=family_id
        )
        self.db.add(meth)
        await self.db.flush()
        return meth, True

    async def get_or_create_version(
        self, methodology_id: uuid.UUID, version_str: str
    ) -> tuple[MethodologyVersion, bool]:
        result = await self.db.execute(
            select(MethodologyVersion).filter_by(
                methodology_id=methodology_id, version=version_str
            )
        )
        ver = result.scalar_one_or_none()
        if ver:
            return ver, False
        from datetime import date

        ver = MethodologyVersion(
            methodology_id=methodology_id,
            version=version_str,
            release_date=date.today(),
        )
        self.db.add(ver)
        await self.db.flush()
        return ver, True
