"""
=============================================================================
VeriField Nexus — Data Lineage & Traceability Engine
=============================================================================
Provides end-to-end auditability and provenance tracking:
Monitored Parameter -> IoT Sensor / Field Device -> Raw Observation ->
QA/QC Filtering -> Calculation Run -> Emission Reduction -> Registry Document Section
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.evidence.models import Evidence
from app.domains.methodologies.models.base_registry import Methodology
from app.domains.projects.models import Project


class DataLineageEngine:
    """Computes transparent data lineage for any quantified MRV metric."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_data_lineage(
        self,
        project_id: UUID,
        monitoring_period_start: Optional[datetime] = None,
        monitoring_period_end: Optional[datetime] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Extracts full provenance graph for a project across all sectors.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        # 1. Fetch Project & Methodology
        p_stmt = select(Project).where(Project.id == project_id)
        p_res = await self.db.execute(p_stmt)
        project = p_res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        methodology_code = "GENERIC_MRV"
        methodology_name = "Generic MRV Methodology"
        if project.methodology_id:
            m_stmt = select(Methodology).where(Methodology.id == project.methodology_id)
            m_res = await self.db.execute(m_stmt)
            meth = m_res.scalar_one_or_none()
            if meth:
                methodology_code = meth.code
                methodology_name = meth.name

        # 2. Fetch Assets
        a_stmt = select(Asset).where(Asset.project_id == project_id)
        a_res = await self.db.execute(a_stmt)
        assets = a_res.scalars().all()

        # 3. Fetch Activities via assets or org
        asset_ids = [a.id for a in assets]
        if asset_ids:
            act_stmt = select(Activity).where(Activity.asset_id.in_(asset_ids))
        elif project.organization_id:
            act_stmt = select(Activity).where(Activity.organization_id == project.organization_id)
        else:
            act_stmt = select(Activity).where(Activity.id.is_(None))

        if monitoring_period_start:
            act_stmt = act_stmt.where(Activity.submitted_at >= monitoring_period_start)
        if monitoring_period_end:
            act_stmt = act_stmt.where(Activity.submitted_at <= monitoring_period_end)
        act_res = await self.db.execute(act_stmt)
        activities = act_res.scalars().all()

        # 4. Fetch Evidence items
        act_ids = [act.id for act in activities]
        if act_ids:
            ev_stmt = select(Evidence).where(Evidence.activity_id.in_(act_ids))
            ev_res = await self.db.execute(ev_stmt)
            evidence_items = ev_res.scalars().all()
        else:
            evidence_items = []

        # 5. Build Parameter Lineage Nodes
        parameter_lineage = []
        total_co2_kg = 0.0
        verified_count = 0
        flagged_count = 0

        for act in activities:
            data = act.activity_data or {}
            val_kg = 0.0
            if isinstance(data, dict):
                if "emission_reduction_kg" in data:
                    val_kg = float(data["emission_reduction_kg"])
                elif "carbon_offset_tons" in data:
                    val_kg = float(data["carbon_offset_tons"]) * 1000.0
                elif "co2e_reduction_tonnes" in data:
                    val_kg = float(data["co2e_reduction_tonnes"]) * 1000.0
            total_co2_kg += val_kg

            trust = float(act.trust_score) if act.trust_score else 0.0
            if trust >= 80.0:
                verified_count += 1
            else:
                flagged_count += 1

            # Match evidence
            matched_evidence = [
                {
                    "evidence_id": str(e.id),
                    "evidence_type": e.evidence_type,
                    "sha256": getattr(e, "file_hash", getattr(e, "sha256_hash", None)),
                    "captured_at": e.created_at.isoformat() if getattr(e, "created_at", None) else None,
                }
                for e in evidence_items
                if e.activity_id == act.id or (hasattr(e, "asset_id") and e.asset_id == act.asset_id)
            ]

            lineage_node = {
                "activity_id": str(act.id),
                "asset_id": str(act.asset_id) if act.asset_id else None,
                "activity_type": act.activity_type,
                "submitted_at": act.submitted_at.isoformat() if act.submitted_at else None,
                "trust_score": trust,
                "qa_qc_status": "APPROVED" if trust >= 80.0 else "FLAGGED_FOR_REVIEW",
                "emission_reduction_kg": val_kg,
                "emission_reduction_tco2e": round(val_kg / 1000.0, 4),
                "evidence_attachments": matched_evidence,
                "data_provenance": {
                    "source_type": "IOT_TELEMETRY" if act.activity_type in ["meter_reading", "sensor_stream", "telemetry"] else "FIELD_MOBILE_PWA",
                    "hash": hashlib.sha256(f"{act.id}:{act.submitted_at}:{val_kg}".encode("utf-8")).hexdigest(),
                },
            }
            parameter_lineage.append(lineage_node)

        # 6. Construct Provenance Summary
        return {
            "project_id": str(project.id),
            "project_code": project.project_code if hasattr(project, "project_code") else str(project.id)[:8],
            "project_name": project.name,
            "methodology": {
                "code": methodology_code,
                "name": methodology_name,
                "calculation_model": "AST_DETERMINISTIC_SANDBOX_V1",
            },
            "summary_metrics": {
                "total_assets_enrolled": len(assets),
                "total_activities_processed": len(activities),
                "verified_activities_count": verified_count,
                "flagged_activities_count": flagged_count,
                "total_emission_reductions_tco2e": round(total_co2_kg / 1000.0, 4),
                "lineage_integrity_score": round((verified_count / len(activities) * 100.0) if activities else 100.0, 2),
            },
            "lineage_records": parameter_lineage[:100],  # Return first 100 in summary
            "generated_at": eval_time.isoformat(),
            "lineage_digest": hashlib.sha256(f"{project.id}:{total_co2_kg}:{len(activities)}".encode("utf-8")).hexdigest(),
        }
