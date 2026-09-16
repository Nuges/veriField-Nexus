import uuid
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domains.agriculture.models import LandUnit
from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharLabAnalysis,
    BiocharMaterialTransaction,
    BiocharStorageEvent,
    BiocharTransportEvent,
    FacilityReactor,
    FeedstockLot,
    FeedstockRunAllocation,
    FeedstockSource,
    ProductionFacility,
    ProductionRun,
)
from app.domains.biochar.schemas import (
    ChainOfCustodyNode,
    ChainOfCustodyResponse,
)


class BiocharLineageService:
    """
    End-to-End Chain-of-Custody & Lineage Traversal Service.
    Connects Feedstock Origin -> Pyrolysis Run -> Lab Quality -> Logistics -> Terminal End-Use.
    """

    @staticmethod
    async def get_batch_chain_of_custody(
        db: AsyncSession,
        batch_id: UUID,
    ) -> ChainOfCustodyResponse:
        stmt_batch = select(BiocharBatch).where(BiocharBatch.id == batch_id)
        res_batch = await db.execute(stmt_batch)
        batch = res_batch.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Biochar Batch {batch_id} not found.",
            )

        nodes: List[ChainOfCustodyNode] = []
        upstream_chain: List[str] = []
        downstream_chain: List[str] = []
        evidence_hashes: List[str] = []

        # 1. Add Batch Node
        batch_node = ChainOfCustodyNode(
            node_type="BATCH",
            node_id=str(batch.id),
            title=f"Biochar Batch {batch.batch_number}",
            details={
                "batch_number": batch.batch_number,
                "facility_name": batch.facility_name,
                "biochar_yield_tonnes": batch.biochar_yield_tonnes,
                "fixed_carbon_pct": batch.fixed_carbon_pct,
                "molar_h_c_ratio": batch.molar_h_c_ratio,
                "quality_grade": batch.quality_grade,
                "status": batch.status,
                "carbon_claim_registry": batch.carbon_claim_registry,
                "carbon_claim_methodology": batch.carbon_claim_methodology,
            },
            hash=batch.batch_digest_hash,
        )
        nodes.append(batch_node)
        if batch.batch_digest_hash:
            evidence_hashes.append(batch.batch_digest_hash)

        # 2. Upstream: Production Run, Reactor, Facility
        if batch.production_run_id:
            stmt_run = select(ProductionRun).where(ProductionRun.id == batch.production_run_id)
            res_run = await db.execute(stmt_run)
            run = res_run.scalar_one_or_none()
            if run:
                upstream_chain.append(f"Run:{run.run_number}")
                nodes.append(
                    ChainOfCustodyNode(
                        node_type="RUN",
                        node_id=str(run.id),
                        title=f"Production Run {run.run_number}",
                        details={
                            "run_number": run.run_number,
                            "avg_pyrolysis_temp_celsius": run.avg_pyrolysis_temp_celsius,
                            "residence_time_minutes": run.residence_time_minutes,
                            "total_feedstock_input_tonnes": run.total_feedstock_input_tonnes,
                            "output_biochar_mass_tonnes": run.output_biochar_mass_tonnes,
                            "qa_status": run.qa_status,
                        },
                    )
                )

                # Facility & Reactor
                if run.facility_id:
                    stmt_fac = select(ProductionFacility).where(ProductionFacility.id == run.facility_id)
                    res_fac = await db.execute(stmt_fac)
                    fac = res_fac.scalar_one_or_none()
                    if fac:
                        upstream_chain.append(f"Facility:{fac.facility_code}")
                        nodes.append(
                            ChainOfCustodyNode(
                                node_type="FACILITY",
                                node_id=str(fac.id),
                                title=f"Facility {fac.facility_name}",
                                details={
                                    "facility_code": fac.facility_code,
                                    "facility_status": fac.facility_status,
                                    "technology_type": fac.technology_type,
                                    "location": fac.location,
                                },
                            )
                        )

                if run.reactor_id:
                    stmt_reac = select(FacilityReactor).where(FacilityReactor.id == run.reactor_id)
                    res_reac = await db.execute(stmt_reac)
                    reac = res_reac.scalar_one_or_none()
                    if reac:
                        nodes.append(
                            ChainOfCustodyNode(
                                node_type="REACTOR",
                                node_id=str(reac.id),
                                title=f"Reactor {reac.reactor_code}",
                                details={
                                    "reactor_code": reac.reactor_code,
                                    "technology_type": reac.technology_type,
                                    "operating_temp_range": f"{reac.operating_temp_min_c}C - {reac.operating_temp_max_c}C",
                                },
                            )
                        )

                # Feedstock Run Allocations -> Lots -> Sources
                stmt_allocs = select(FeedstockRunAllocation).where(FeedstockRunAllocation.production_run_id == run.id)
                res_allocs = await db.execute(stmt_allocs)
                allocations = res_allocs.scalars().all()

                for alloc in allocations:
                    stmt_lot = select(FeedstockLot).where(FeedstockLot.id == alloc.lot_id)
                    res_lot = await db.execute(stmt_lot)
                    lot = res_lot.scalar_one_or_none()
                    if lot:
                        upstream_chain.append(f"Lot:{lot.lot_number}")
                        nodes.append(
                            ChainOfCustodyNode(
                                node_type="LOT",
                                node_id=str(lot.id),
                                title=f"Feedstock Lot {lot.lot_number}",
                                details={
                                    "lot_number": lot.lot_number,
                                    "feedstock_type": lot.feedstock_type,
                                    "mass_received_tonnes": lot.mass_received_tonnes,
                                    "moisture_content_pct": lot.moisture_content_pct,
                                    "allocated_to_this_run": alloc.allocated_wet_mass_tonnes,
                                    "storage_location": lot.storage_location,
                                },
                                hash=lot.evidence_hash,
                            )
                        )
                        if lot.evidence_hash:
                            evidence_hashes.append(lot.evidence_hash)

                        # Source
                        stmt_src = select(FeedstockSource).where(FeedstockSource.id == lot.source_id)
                        res_src = await db.execute(stmt_src)
                        src = res_src.scalar_one_or_none()
                        if src:
                            upstream_chain.append(f"Source:{src.source_code}")
                            src_details = {
                                "source_code": src.source_code,
                                "source_name": src.source_name,
                                "source_type": src.source_type,
                                "biomass_type": src.biomass_type,
                                "waste_status": src.waste_status,
                                "baseline_fate": src.baseline_fate,
                                "supplier_name": src.supplier_name,
                            }
                            if src.source_land_unit_id:
                                stmt_lu = select(LandUnit).where(LandUnit.id == src.source_land_unit_id)
                                res_lu = await db.execute(stmt_lu)
                                lu = res_lu.scalar_one_or_none()
                                if lu:
                                    src_details["linked_land_unit_name"] = lu.name
                                    src_details["linked_land_unit_id"] = str(lu.id)

                            nodes.append(
                                ChainOfCustodyNode(
                                    node_type="SOURCE",
                                    node_id=str(src.id),
                                    title=f"Source {src.source_name}",
                                    details=src_details,
                                )
                            )

        # 3. Lab Analyses
        stmt_labs = select(BiocharLabAnalysis).where(BiocharLabAnalysis.batch_id == batch.id)
        res_labs = await db.execute(stmt_labs)
        labs = res_labs.scalars().all()
        for lab in labs:
            nodes.append(
                ChainOfCustodyNode(
                    node_type="LAB",
                    node_id=str(lab.id),
                    title=f"Lab Analysis ({lab.laboratory_name})",
                    details={
                        "sample_id": lab.sample_id,
                        "laboratory_name": lab.laboratory_name,
                        "test_method": lab.test_method,
                        "molar_h_c_ratio": lab.molar_h_c_ratio,
                        "organic_carbon_pct": lab.organic_carbon_pct,
                        "fixed_carbon_pct": lab.fixed_carbon_pct,
                        "heavy_metals_pass": lab.heavy_metals_pass,
                        "qa_status": lab.qa_status,
                    },
                    hash=lab.lab_report_hash,
                )
            )
            if lab.lab_report_hash:
                evidence_hashes.append(lab.lab_report_hash)

        # 4. Storage Events
        stmt_stor = select(BiocharStorageEvent).where(BiocharStorageEvent.batch_id == batch.id)
        res_stor = await db.execute(stmt_stor)
        storage_events = res_stor.scalars().all()
        for s in storage_events:
            nodes.append(
                ChainOfCustodyNode(
                    node_type="STORAGE",
                    node_id=str(s.id),
                    title=f"Storage at {s.storage_facility_name}",
                    details={
                        "facility": s.storage_facility_name,
                        "location": s.storage_location,
                        "quantity_stored_tonnes": s.quantity_stored_tonnes,
                        "loss_tonnes": s.loss_or_damage_tonnes,
                        "conditions": s.storage_conditions,
                    },
                )
            )

        # 5. Downstream: Transport Events
        stmt_trans = select(BiocharTransportEvent).where(BiocharTransportEvent.reference_id == batch.id)
        res_trans = await db.execute(stmt_trans)
        transports = res_trans.scalars().all()
        for t in transports:
            downstream_chain.append(f"Transport:{t.transport_mode}:{t.distance_km}km")
            nodes.append(
                ChainOfCustodyNode(
                    node_type="TRANSPORT",
                    node_id=str(t.id),
                    title=f"Transport to {t.destination_address}",
                    details={
                        "origin": t.origin_address,
                        "destination": t.destination_address,
                        "mass_tonnes": t.mass_transported_tonnes,
                        "distance_km": t.distance_km,
                        "mode": t.transport_mode,
                        "carrier": t.carrier_name,
                        "pod_ref": t.proof_of_delivery_ref,
                        "status": t.status,
                    },
                    hash=t.pod_document_hash,
                )
            )
            if t.pod_document_hash:
                evidence_hashes.append(t.pod_document_hash)

        # 6. Downstream: Terminal End-Use Records
        stmt_eu = select(BiocharEndUseRecord).where(BiocharEndUseRecord.batch_id == batch.id)
        res_eu = await db.execute(stmt_eu)
        end_uses = res_eu.scalars().all()
        for eu in end_uses:
            downstream_chain.append(f"EndUse:{eu.end_use_type}:{eu.applied_quantity_tonnes}t")
            eu_details = {
                "end_use_type": eu.end_use_type,
                "applied_quantity_tonnes": eu.applied_quantity_tonnes,
                "event_date": eu.event_date.isoformat(),
                "verification_status": eu.verification_status,
            }
            if eu.end_use_type == "SOIL_APPLICATION":
                eu_details["application_rate_tonnes_per_ha"] = eu.application_rate_tonnes_per_ha
                eu_details["area_hectares"] = eu.area_hectares
                eu_details["crop_type"] = eu.crop_type
                if eu.source_land_unit_id:
                    stmt_lu = select(LandUnit).where(LandUnit.id == eu.source_land_unit_id)
                    res_lu = await db.execute(stmt_lu)
                    lu = res_lu.scalar_one_or_none()
                    if lu:
                        eu_details["applied_land_unit_name"] = lu.name
                        eu_details["applied_land_unit_id"] = str(lu.id)
            else:
                eu_details["product_category"] = eu.product_category
                eu_details["recipient_organization"] = eu.recipient_organization
                eu_details["durability_classification"] = eu.durability_classification

            nodes.append(
                ChainOfCustodyNode(
                    node_type="END_USE",
                    node_id=str(eu.id),
                    title=f"End-Use: {eu.end_use_type}",
                    details=eu_details,
                )
            )

        # Check if full traceability is complete
        has_upstream = bool(upstream_chain)
        has_lab = bool(labs)
        has_downstream = bool(end_uses or transports)
        traceability_complete = has_upstream and has_lab and has_downstream

        return ChainOfCustodyResponse(
            batch_id=batch.id,
            batch_number=batch.batch_number,
            traceability_complete=traceability_complete,
            nodes=nodes,
            upstream_chain=upstream_chain,
            downstream_chain=downstream_chain,
            evidence_hashes=evidence_hashes,
        )
