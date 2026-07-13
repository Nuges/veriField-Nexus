import uuid
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.jurisdictions.models import (ComplianceFramework,
                                              GovernanceAuthority,
                                              Jurisdiction, MethodologyPackage,
                                              RegistryAdapter, ValidationBody)
from app.domains.programmes.models import ClimateProgramme


class GovernanceMetadataResolver:
    """
    Core engine for resolving governance metadata context.
    Traverses the Jurisdiction hierarchy to build a unified context
    for UI applications and the Compliance Engine.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_jurisdiction_chain(
        self, jurisdiction_id: uuid.UUID
    ) -> List[Jurisdiction]:
        """
        Traverse upwards to get the full inheritance chain
        from the specified node up to GLOBAL.
        """
        chain = []
        current_id = jurisdiction_id

        while current_id:
            res = await self.db.execute(
                select(Jurisdiction).where(Jurisdiction.id == current_id)
            )
            jurisdiction = res.scalar_one_or_none()
            if not jurisdiction:
                break

            chain.append(jurisdiction)
            current_id = jurisdiction.parent_id

        return chain

    async def resolve_context(self, jurisdiction_id: uuid.UUID) -> Dict[str, Any]:
        """
        Resolve the full Governance Context for a jurisdiction.
        Cascades properties from parent -> child.
        """
        chain = await self.get_jurisdiction_chain(jurisdiction_id)
        if not chain:
            raise HTTPException(status_code=404, detail="Jurisdiction not found")

        # Reverse the chain so we apply GLOBAL first, then overwrite with NATIONAL, etc.
        chain.reverse()

        context = {
            "jurisdiction_id": str(jurisdiction_id),
            "hierarchy": [j.level for j in chain],
            "metadata": {},
            "active_frameworks": [],
            "approved_methodologies": [],
            "registries": [],
        }

        # For simplicity in this implementation, we will cascade the JSONB metadata
        # Child keys overwrite parent keys.
        for j in chain:
            if j.metadata_context:
                context["metadata"].update(j.metadata_context)

        # Load related models for the primary jurisdiction
        primary = chain[-1]

        # Authorities
        res_auth = await self.db.execute(
            select(GovernanceAuthority).where(
                GovernanceAuthority.jurisdiction_id == primary.id
            )
        )
        authorities = res_auth.scalars().all()
        context["authorities"] = [
            {"id": str(a.id), "name": a.name, "type": a.authority_type}
            for a in authorities
        ]

        # Frameworks
        res_fw = await self.db.execute(
            select(ComplianceFramework).where(
                ComplianceFramework.jurisdiction_id == primary.id
            )
        )
        frameworks = res_fw.scalars().all()
        context["active_frameworks"] = [
            {"id": str(f.id), "name": f.name, "version": f.version} for f in frameworks
        ]

        # Programs
        res_prog = await self.db.execute(
            select(ClimateProgramme).where(
                ClimateProgramme.jurisdiction_id == primary.id
            )
        )
        programs = res_prog.scalars().all()
        context["climate_programmes"] = [
            {"id": str(p.id), "name": p.name, "status": p.status} for p in programs
        ]

        # Methodologies
        res_meth = await self.db.execute(select(MethodologyPackage))
        methodologies = res_meth.scalars().all()
        context["approved_methodologies"] = [
            {"id": str(m.id), "name": m.name, "version": m.version, "status": m.status}
            for m in methodologies
        ]

        # Registries
        res_reg = await self.db.execute(select(RegistryAdapter))
        registries = res_reg.scalars().all()
        context["registries"] = [
            {
                "id": str(r.id),
                "name": r.name,
                "type": r.adapter_type,
                "status": r.status,
            }
            for r in registries
        ]

        # VVBs
        res_vvb = await self.db.execute(select(ValidationBody))
        vvbs = res_vvb.scalars().all()
        context["vvbs"] = [
            {
                "id": str(v.id),
                "name": v.name,
                "accreditation": v.accreditation_number,
                "scopes": v.scopes,
                "status": v.status,
            }
            for v in vvbs
        ]

        # Spatial Boundary
        context["spatial_boundary"] = primary.spatial_boundary

        # Domain Health Computation
        health_score = 100.0
        if not context["spatial_boundary"]:
            health_score -= 20.0
        if not context["active_frameworks"]:
            health_score -= 30.0
        if not context["vvbs"]:
            health_score -= 10.0
        if not context["authorities"]:
            health_score -= 15.0

        context["health_score"] = max(0.0, health_score)

        return context


class JurisdictionService:
    def __init__(self, repository):
        self.repository = repository

    async def create_jurisdiction(self, data: dict, actor_id: str) -> Jurisdiction:
        if await self.repository.get_by_code(data["code"]):
            raise HTTPException(
                status_code=400, detail="Jurisdiction code already exists"
            )

        jurisdiction = Jurisdiction(**data)
        jurisdiction = await self.repository.create(jurisdiction)

        from app.core.event_bus import EventBus

        await EventBus.publish(
            stream_name="governance_events",
            event_type="JurisdictionCreated",
            payload={
                "jurisdiction_id": str(jurisdiction.id),
                "code": jurisdiction.code,
            },
            actor_id=actor_id,
        )

        return jurisdiction

    async def update_jurisdiction(
        self, jurisdiction_id: uuid.UUID, updates: dict, actor_id: str
    ) -> Jurisdiction:
        jurisdiction = await self.repository.get_by_id(jurisdiction_id)
        if not jurisdiction:
            raise HTTPException(status_code=404, detail="Jurisdiction not found")

        old_state = {
            "status": jurisdiction.status,
            "health_score": jurisdiction.health_score,
        }

        for key, value in updates.items():
            if hasattr(jurisdiction, key) and key not in [
                "id",
                "version",
                "created_at",
                "updated_at",
            ]:
                setattr(jurisdiction, key, value)

        jurisdiction = await self.repository.update(jurisdiction)

        from app.core.event_bus import EventBus

        await EventBus.publish(
            stream_name="governance_events",
            event_type="JurisdictionUpdated",
            payload={
                "jurisdiction_id": str(jurisdiction.id),
                "updates": updates,
                "old_state": old_state,
            },
            actor_id=actor_id,
        )

        return jurisdiction

    async def delete_jurisdiction(
        self, jurisdiction_id: uuid.UUID, actor_id: str
    ) -> Jurisdiction:
        jurisdiction = await self.repository.get_by_id(jurisdiction_id)
        if not jurisdiction:
            raise HTTPException(status_code=404, detail="Jurisdiction not found")

        jurisdiction = await self.repository.soft_delete(jurisdiction)

        from app.core.event_bus import EventBus

        await EventBus.publish(
            stream_name="governance_events",
            event_type="JurisdictionDeleted",
            payload={"jurisdiction_id": str(jurisdiction.id)},
            actor_id=actor_id,
        )

        return jurisdiction

    async def get_jurisdiction(self, jurisdiction_id: uuid.UUID) -> Jurisdiction:
        jurisdiction = await self.repository.get_by_id(jurisdiction_id)
        if not jurisdiction:
            raise HTTPException(status_code=404, detail="Jurisdiction not found")
        return jurisdiction

    async def list_jurisdictions(
        self, limit: int = 100, offset: int = 0
    ) -> List[Jurisdiction]:
        return await self.repository.list_all(limit, offset)
